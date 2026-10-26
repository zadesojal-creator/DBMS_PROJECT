"""
Market Simulator & Background Price Worker (services/market_simulator.py)
High-Frequency In-Memory Simulation Engine with Decoupled Database Persistence:
- Target one simulation tick every 500 milliseconds (0.50s interval, 2 ticks/sec) stochastic random walk with independent streams per symbol.
- Latest valid price as starting point; bounded volatility and circuit filters per sector.
- Decoupled batch database persistence (1.0s interval) to prevent MySQL connection exhaustion.
- Server-Sent Events (SSE) subscriber broadcasting for push-based real-time frontend streaming.
- MySQL advisory lock (GET_LOCK) to ensure single-worker execution across multi-process deployments.
- Deterministic test mode with injectable random seed / custom generator.
"""
import os
import time
import queue
import random
import threading
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List
from sqlalchemy import text
from database.backfill_prices import simulate_next_price, round_tick, SECTOR_VOLATILITY
from models.db import get_engine, get_db_connection

class MarketSimulator:
    _instance: Optional['MarketSimulator'] = None
    _singleton_lock = threading.Lock()

    def __init__(self, interval_seconds: float = 0.50, always_open: bool = True):
        # Configurable tick interval (default 0.50s for 2 ticks/sec per specification)
        env_interval = os.getenv("SIMULATOR_TICK_INTERVAL_SEC")
        self.tick_interval_seconds = float(env_interval) if env_interval else interval_seconds
        self.db_flush_interval = float(os.getenv("SIMULATOR_DB_FLUSH_SEC", "1.0"))
        self.volatility_multiplier = float(os.getenv("SIMULATOR_VOLATILITY_MULT", "1.0"))
        self.max_tick_pct = Decimal(str(os.getenv("MAX_TICK_PCT", "0.005")))
        self.circuit_limit_pct = Decimal(str(os.getenv("CIRCUIT_LIMIT_PCT", "0.10")))
        self.always_open = always_open
        self.is_paused = False

        self._stop_event = threading.Event()
        self._tick_thread: Optional[threading.Thread] = None
        self._flush_thread: Optional[threading.Thread] = None

        self._stocks: Dict[int, Dict[str, Any]] = {}
        self._stock_rngs: Dict[int, random.Random] = {}
        self._base_seed = int(os.getenv("SIMULATOR_BASE_SEED", "42"))
        self._cache_lock = threading.RLock()

        self._subscribers: List[queue.Queue] = []
        self._subscribers_lock = threading.Lock()

        self.tick_count = 0
        self.last_tick_time: Optional[datetime] = None
        self.last_flush_time: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.measured_tick_interval_ms: float = self.tick_interval_seconds * 1000.0
        self._last_tick_ts: float = 0.0
        self._lock_conn = None

    @classmethod
    def get_instance(cls, interval_seconds: float = 0.50, always_open: bool = True) -> 'MarketSimulator':
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = MarketSimulator(interval_seconds, always_open)
            return cls._instance

    def set_seed(self, seed: int):
        """Sets a deterministic random seed across all symbol generators (ideal for reproducible tests)."""
        self._base_seed = seed
        with self._cache_lock:
            for s_id in self._stocks:
                self._stock_rngs[s_id] = random.Random(seed + s_id * 1009)

    def _acquire_advisory_lock(self) -> bool:
        """Acquire MySQL advisory lock on a dedicated connection so only ONE worker flushes to DB."""
        if self._lock_conn is not None:
            return True
        try:
            engine = get_engine()
            conn = engine.connect()
            res = conn.execute(text("SELECT GET_LOCK('stocktrade_simulator', 0)")).scalar()
            if res == 1:
                self._lock_conn = conn
                return True
            else:
                conn.close()
                return False
        except Exception:
            return False

    def _release_advisory_lock(self):
        """Release MySQL advisory lock and close the dedicated lock connection."""
        if self._lock_conn is not None:
            try:
                self._lock_conn.execute(text("SELECT RELEASE_LOCK('stocktrade_simulator')"))
                self._lock_conn.close()
            except Exception:
                pass
            self._lock_conn = None

    def hydrate_from_db(self):
        """Loads all active stock prices from v_market_latest into in-memory dictionary."""
        try:
            engine = get_engine()
            with engine.connect() as conn:
                query = """
                    SELECT 
                        stock_id, symbol, company_name, sector, exchange, status,
                        current_price, previous_close, day_change, day_change_pct,
                        day_open, day_high, day_low, volume, updated_at
                    FROM v_market_latest
                    WHERE status = 'ACTIVE'
                    ORDER BY symbol ASC
                """
                rows = conn.execute(text(query)).mappings().all()
                with self._cache_lock:
                    for r in rows:
                        s_id = r["stock_id"]
                        curr_p = float(r["current_price"]) if r["current_price"] is not None else 100.0
                        prev_c = float(r["previous_close"]) if r["previous_close"] is not None else curr_p
                        d_change = float(r["day_change"]) if r["day_change"] is not None else round(curr_p - prev_c, 4)
                        d_change_pct = float(r["day_change_pct"]) if r["day_change_pct"] is not None else (
                            round((d_change / prev_c) * 100, 2) if prev_c > 0 else 0.0
                        )

                        if s_id not in self._stock_rngs:
                            self._stock_rngs[s_id] = random.Random(self._base_seed + s_id * 1009)
                        
                        self._stocks[s_id] = {
                            "stock_id": s_id,
                            "id": s_id,
                            "symbol": r["symbol"],
                            "company_name": r["company_name"],
                            "sector": r["sector"],
                            "exchange": r["exchange"],
                            "status": r["status"],
                            "price": curr_p,
                            "current_price": curr_p,
                            "previous_close": prev_c,
                            "day_change": d_change,
                            "change": d_change,
                            "day_change_pct": d_change_pct,
                            "change_pct": d_change_pct,
                            "day_open": float(r["day_open"]) if r["day_open"] is not None else curr_p,
                            "day_high": float(r["day_high"]) if r["day_high"] is not None else curr_p,
                            "day_low": float(r["day_low"]) if r["day_low"] is not None else curr_p,
                            "volume": int(r["volume"]) if r["volume"] is not None else 100000,
                            "updated_at": r["updated_at"].strftime("%Y-%m-%d %H:%M:%S") if r["updated_at"] else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
        except Exception as e:
            self.last_error = f"Hydration failed: {e}"

    def sync_stock_to_db(self, stock_id: int):
        """Immediately flushes the latest in-memory quote for a stock to MySQL Current_Prices."""
        with self._cache_lock:
            st = self._stocks.get(stock_id)
        if not st:
            return
        try:
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE Current_Prices
                    SET price = :price, day_high = :day_high, day_low = :day_low,
                        volume = :volume, updated_at = :updated_at
                    WHERE stock_id = :stock_id
                """), {
                    "price": st["price"],
                    "day_high": st["day_high"],
                    "day_low": st["day_low"],
                    "volume": st["volume"],
                    "updated_at": st["updated_at"],
                    "stock_id": stock_id
                })
                conn.commit()
        except Exception as e:
            self.last_error = f"Sync stock {stock_id} failed: {e}"

    def _tick_in_memory(self):
        """Single controlled stochastic tick across all active stocks in memory."""
        if self.is_paused:
            return

        now = datetime.now()
        now_ts = time.time()
        if self._last_tick_ts > 0:
            dt_ms = (now_ts - self._last_tick_ts) * 1000.0
            self.measured_tick_interval_ms = round(0.9 * self.measured_tick_interval_ms + 0.1 * dt_ms, 2)
        self._last_tick_ts = now_ts

        # Market hours check if not always_open (09:15 to 15:30 IST, Mon-Fri)
        if not self.always_open:
            if now.weekday() >= 5:
                return
            curr_time = now.time()
            if curr_time < datetime.strptime("09:15", "%H:%M").time() or curr_time > datetime.strptime("15:30", "%H:%M").time():
                return

        deltas = []
        now_str = now.strftime('%Y-%m-%d %H:%M:%S')

        with self._cache_lock:
            if not self._stocks:
                self.hydrate_from_db()
                if not self._stocks:
                    return

            for stock_id, st in self._stocks.items():
                curr_p = Decimal(str(st['price']))
                prev_c = Decimal(str(st['previous_close']))
                d_high = Decimal(str(st['day_high']))
                d_low = Decimal(str(st['day_low']))
                vol = int(st['volume'])

                # Use the symbol's independent pseudo-random stream
                rng = self._stock_rngs.get(stock_id)
                if not rng:
                    rng = random.Random(self._base_seed + stock_id * 1009)
                    self._stock_rngs[stock_id] = rng

                # Stochastic bounded random walk with sector volatility
                sector = st.get('sector', '')
                base_vol = Decimal(str(SECTOR_VOLATILITY.get(sector, 0.0030)))
                vol = base_vol * Decimal(str(self.volatility_multiplier))

                # Slight mean reversion pull towards previous close baseline
                pull = Decimal('-0.02') * ((curr_p - prev_c) / prev_c) if prev_c > Decimal('0') else Decimal('0')
                noise = Decimal(str(rng.gauss(0.0, float(vol))))
                raw_return = pull + noise

                # Clamp return to bounded tick limit
                clamped_return = max(min(raw_return, self.max_tick_pct), -self.max_tick_pct)
                new_p = curr_p * (Decimal('1') + clamped_return)

                # Circuit limit boundaries
                lower_circuit = prev_c * (Decimal('1') - self.circuit_limit_pct)
                upper_circuit = prev_c * (Decimal('1') + self.circuit_limit_pct)
                new_p = max(min(new_p, upper_circuit), lower_circuit)

                if new_p < Decimal('0.05'):
                    new_p = Decimal('0.05')
                new_p = round_tick(new_p)

                new_p_float = float(new_p)
                prev_c_float = float(prev_c)
                new_high = max(float(d_high), new_p_float)
                new_low = min(float(d_low), new_p_float)
                tick_vol = 10 + (rng.randint(1, 150))
                new_vol = vol + tick_vol
                change = round(new_p_float - prev_c_float, 4)
                change_pct = round((change / prev_c_float) * 100, 2) if prev_c_float > 0 else 0.0

                st['price'] = new_p_float
                st['current_price'] = new_p_float
                st['day_high'] = new_high
                st['day_low'] = new_low
                st['volume'] = new_vol
                st['day_change'] = change
                st['change'] = change
                st['day_change_pct'] = change_pct
                st['change_pct'] = change_pct
                st['updated_at'] = now_str

                deltas.append({
                    'stock_id': stock_id,
                    'symbol': st['symbol'],
                    'price': new_p_float,
                    'current_price': new_p_float,
                    'day_high': new_high,
                    'day_low': new_low,
                    'volume': new_vol,
                    'day_change': change,
                    'change': change,
                    'day_change_pct': change_pct,
                    'change_pct': change_pct,
                    'updated_at': now_str
                })

            self.tick_count += 1
            self.last_tick_time = now

        if deltas and self._subscribers:
            self._broadcast(deltas)

    def _flush_to_db(self, force: bool = False):
        """Batched persistence of in-memory prices to MySQL Current_Prices and Price_Alerts evaluation."""
        if not force and not self._acquire_advisory_lock():
            return

        with self._cache_lock:
            if not self._stocks:
                return
            items = list(self._stocks.values())

        try:
            engine = get_engine()
            with engine.connect() as conn:
                cursor = conn.connection.cursor()
                update_params = [
                    (it['price'], it['day_high'], it['day_low'], it['volume'], it['updated_at'], it['stock_id'])
                    for it in items
                ]
                cursor.executemany("""
                    UPDATE Current_Prices 
                    SET price = %s, day_high = %s, day_low = %s, volume = %s, updated_at = %s 
                    WHERE stock_id = %s
                """, update_params)

                # Sample latest prices into Stock_Prices for OHLC history aggregation
                now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                insert_params = [
                    (it['stock_id'], it['price'], 100, 'SIMULATED', now_str)
                    for it in items
                ]
                cursor.executemany("""
                    INSERT INTO Stock_Prices (stock_id, price, volume, source, recorded_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, insert_params)

                # Evaluate active Price_Alerts
                conn.execute(text("""
                    UPDATE Price_Alerts a
                    JOIN Current_Prices cp ON a.stock_id = cp.stock_id
                    SET a.status = 'TRIGGERED', a.triggered_at = CURRENT_TIMESTAMP
                    WHERE a.status = 'ACTIVE' AND (
                        (a.condition_type = 'ABOVE' AND cp.price >= a.target_price) OR
                        (a.condition_type = 'BELOW' AND cp.price <= a.target_price)
                    )
                """))
                conn.commit()
                self.last_flush_time = datetime.now()
                self.last_error = None
        except Exception as e:
            self.last_error = str(e)

    def tick(self):
        """Executes a single in-memory tick and synchronously flushes to DB (ideal for tests and manual sync)."""
        self._tick_in_memory()
        self._flush_to_db(force=True)

    def _run_tick_loop(self):
        """Continuous stochastic tick loop running at tick_interval_seconds."""
        while not self._stop_event.is_set():
            start_t = time.perf_counter()
            try:
                self._tick_in_memory()
            except Exception as e:
                self.last_error = str(e)
            elapsed = time.perf_counter() - start_t
            sleep_time = max(0.01, self.tick_interval_seconds - elapsed)
            time.sleep(sleep_time)

    def _run_flush_loop(self):
        """Decoupled periodic flush worker syncing in-memory prices to database."""
        while not self._stop_event.is_set():
            time.sleep(self.db_flush_interval)
            try:
                self._flush_to_db()
            except Exception as e:
                self.last_error = str(e)

    def start(self):
        """Starts background in-memory ticking and periodic DB flushing workers."""
        if self._tick_thread is not None and self._tick_thread.is_alive():
            return

        self._stop_event.clear()
        self.hydrate_from_db()

        self._tick_thread = threading.Thread(target=self._run_tick_loop, daemon=True, name="MarketSimulatorTickThread")
        self._flush_thread = threading.Thread(target=self._run_flush_loop, daemon=True, name="MarketSimulatorFlushThread")

        self._tick_thread.start()
        self._flush_thread.start()
        print(f"[MarketSimulator] Started market simulator ({self.tick_interval_seconds:.2f}s tick, ~{1.0/self.tick_interval_seconds:.1f} ticks/sec) with decoupled DB persistence ({self.db_flush_interval}s).")

    def stop(self):
        """Stops background threads, flushes cache to DB, and releases advisory lock."""
        self._stop_event.set()
        if self._tick_thread and self._tick_thread.is_alive():
            self._tick_thread.join(timeout=1.0)
        if self._flush_thread and self._flush_thread.is_alive():
            self._flush_thread.join(timeout=1.0)
        self._flush_to_db(force=True)
        self._release_advisory_lock()

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def subscribe(self) -> queue.Queue:
        """Subscribe to real-time tick delta broadcasts."""
        q = queue.Queue(maxsize=100)
        with self._subscribers_lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        """Unsubscribe from broadcasts."""
        with self._subscribers_lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def _broadcast(self, deltas: List[Dict[str, Any]]):
        """Broadcast tick updates to all active queues non-blockingly."""
        with self._subscribers_lock:
            for q in list(self._subscribers):
                try:
                    q.put_nowait(deltas)
                except queue.Full:
                    try:
                        q.get_nowait()
                        q.put_nowait(deltas)
                    except Exception:
                        pass

    def get_prices(self, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns in-memory cached prices, hydrating from DB if cache is empty."""
        with self._cache_lock:
            if not self._stocks:
                self.hydrate_from_db()
            items = list(self._stocks.values())

        if since:
            return [it for it in items if it.get("updated_at") and it["updated_at"] > since]
        return sorted(items, key=lambda s: s["symbol"])

    def get_quote(self, stock_id: int) -> Optional[Dict[str, Any]]:
        """Returns live in-memory quote for a given stock ID."""
        with self._cache_lock:
            if not self._stocks:
                self.hydrate_from_db()
            return self._stocks.get(stock_id)

    def get_status(self) -> Dict[str, Any]:
        """Returns health status, stale detection, measured tick rate, and subscriber count."""
        now = datetime.now()
        is_fresh = False
        is_amber = False
        is_red = False

        if self.last_tick_time:
            diff_sec = (now - self.last_tick_time).total_seconds()
            if diff_sec <= max(3.0, self.tick_interval_seconds * 10):
                is_fresh = True
            elif diff_sec <= 10.0:
                is_amber = True
            else:
                is_red = True
        else:
            is_amber = True

        status_label = "HEALTHY" if is_fresh else ("STALE" if is_amber else "DOWN")

        return {
            "is_running": (self._tick_thread is not None and self._tick_thread.is_alive() and not self.is_paused),
            "is_paused": self.is_paused,
            "status": status_label,
            "indicator": "green" if is_fresh else ("amber" if is_amber else "red"),
            "interval_seconds": self.tick_interval_seconds,
            "tick_interval_ms": int(self.tick_interval_seconds * 1000),
            "measured_tick_interval_ms": self.measured_tick_interval_ms,
            "ticks_per_second": round(1000.0 / self.measured_tick_interval_ms, 1) if self.measured_tick_interval_ms > 0 else 0,
            "ticks_completed": self.tick_count,
            "last_tick_time": self.last_tick_time.strftime("%H:%M:%S") if self.last_tick_time else None,
            "last_flush_time": self.last_flush_time.strftime("%H:%M:%S") if self.last_flush_time else None,
            "subscribers_count": len(self._subscribers),
            "last_error": self.last_error
        }
