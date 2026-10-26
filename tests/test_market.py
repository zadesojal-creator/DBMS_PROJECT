"""
Market & Price Simulator Test Suite (test_market.py)
Validates shared prices across roles, OHLC aggregation, bounds, and simulator status.
"""
import pytest
from services.market_simulator import MarketSimulator

def test_shared_prices_across_roles(admin_client, broker_client, investor_client):
    """All roles read identical current market prices from the same source."""
    resp_admin = admin_client.get("/market/api/v1/market/prices")
    resp_broker = broker_client.get("/market/api/v1/market/prices")
    resp_investor = investor_client.get("/market/api/v1/market/prices")

    assert resp_admin.status_code == 200
    assert resp_broker.status_code == 200
    assert resp_investor.status_code == 200

    prices_admin = {s["stock_id"]: s["price"] for s in resp_admin.get_json()["data"]}
    prices_broker = {s["stock_id"]: s["price"] for s in resp_broker.get_json()["data"]}
    prices_investor = {s["stock_id"]: s["price"] for s in resp_investor.get_json()["data"]}

    # Assert exact price parity across all roles
    assert prices_admin == prices_broker == prices_investor

def test_simulator_status_and_stale_detection(client):
    """Simulator exposes health status, ticks count, and freshness indicator."""
    sim = MarketSimulator.get_instance()
    status = sim.get_status()
    assert "status" in status
    assert status["indicator"] in ("green", "amber", "red")
    assert "ticks_completed" in status

def test_market_history_ohlc_aggregation(client, monkeypatch):
    """History endpoint correctly aggregates time-series into OHLC buckets."""
    from datetime import datetime, timedelta
    from models.db import get_db_connection
    from sqlalchemy import text

    # Query latest recorded price for TCS in test database to establish deterministic clock
    with get_db_connection() as conn:
        latest = conn.execute(
            text("SELECT MAX(recorded_at) FROM Stock_Prices WHERE stock_id = 1")
        ).scalar()

    # Anchor clock to 31 minutes after latest seed observation, or fixed anchor if empty
    clock_time = (latest + timedelta(minutes=31)) if latest else datetime(2026, 10, 14, 16, 0, 0)

    class DeterministicClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(clock_time.year, clock_time.month, clock_time.day,
                       clock_time.hour, clock_time.minute, clock_time.second)

    monkeypatch.setattr("routes.market.datetime", DeterministicClock)

    resp = client.get("/market/api/v1/market/history?symbol=TCS&interval=1h")
    assert resp.status_code == 200
    json_data = resp.get_json()
    assert json_data["ok"] is True
    data = json_data["data"]
    assert data["interval"] == "1h"
    assert "candles" in data
    assert len(data["candles"]) > 0

    candle = data["candles"][0]
    assert "open" in candle
    assert "high" in candle
    assert "low" in candle
    assert "close" in candle
    assert "volume" in candle
    assert candle["high"] >= candle["low"]

def test_market_history_invalid_interval(client):
    """Invalid interval is rejected with 400."""
    resp = client.get("/market/api/v1/market/history?symbol=TCS&interval=2h")
    assert resp.status_code == 400
    assert "invalid interval" in resp.get_json()["error"]["message"].lower()

def test_all_stocks_positive_prices_and_metadata(client):
    """Every stock receives valid positive price, previous close, and full metadata."""
    resp = client.get("/market/api/v1/market/prices")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert len(data) >= 100

    for s in data:
        assert s["stock_id"] > 0
        assert s["symbol"]
        assert s["company_name"], f"Stock {s['symbol']} missing company_name"
        assert s["sector"], f"Stock {s['symbol']} missing sector"
        assert s["price"] > 0, f"Stock {s['symbol']} has invalid price {s['price']}"
        assert s["current_price"] > 0
        assert s["current_price"] == s["price"]
        assert s["previous_close"] > 0, f"Stock {s['symbol']} has invalid prev close {s['previous_close']}"
        assert s["day_open"] > 0
        assert s["day_high"] >= s["day_low"]
        assert s["volume"] >= 0
        assert s["day_change"] == s["change"]
        assert s["day_change_pct"] == s["change_pct"]

def test_stock_specific_previous_close_not_default_995(client):
    """Stocks have authentic, realistic previous closes rather than a single hardcoded default (995.00)."""
    resp = client.get("/market/api/v1/market/prices")
    assert resp.status_code == 200
    data = resp.get_json()["data"]

    stock_map = {s["symbol"]: s for s in data}

    # Verify key stocks have distinct, realistic previous closes
    assert stock_map["TCS"]["previous_close"] > 3500.0
    assert stock_map["MARUTI"]["previous_close"] > 10000.0
    assert stock_map["ABB"]["previous_close"] > 7000.0
    assert stock_map["IDEA"]["previous_close"] < 20.0
    assert stock_map["RELIANCE"]["previous_close"] > 2500.0

    # Ensure wide distribution across all 100+ stocks
    unique_prev_closes = {s["previous_close"] for s in data}
    assert len(unique_prev_closes) > 30

def test_price_change_and_percent_formula_accuracy(client):
    """Validates: change = current_price - previous_close and change_pct = (change / previous_close) * 100."""
    resp = client.get("/market/api/v1/market/prices")
    assert resp.status_code == 200
    data = resp.get_json()["data"]

    for s in data:
        expected_change = round(s["current_price"] - s["previous_close"], 4)
        expected_pct = round((expected_change / s["previous_close"]) * 100, 2)

        assert abs(s["day_change"] - expected_change) < 0.001
        assert abs(s["day_change_pct"] - expected_pct) < 0.02

def test_division_by_zero_safeguard_in_simulation():
    """simulate_next_price gracefully handles zero or negative reference prices and previous closes."""
    from decimal import Decimal
    from database.backfill_prices import simulate_next_price

    # Case 1: reference_price = 0
    p1 = simulate_next_price(
        current_price=Decimal('100.00'),
        reference_price=Decimal('0.00'),
        previous_close=Decimal('100.00'),
        sector='Information Technology'
    )
    assert p1 > Decimal('0')

    # Case 2: previous_close = 0
    p2 = simulate_next_price(
        current_price=Decimal('100.00'),
        reference_price=Decimal('100.00'),
        previous_close=Decimal('0.00'),
        sector='Banking'
    )
    assert p2 > Decimal('0')

    # Case 3: current_price <= 0 and reference_price <= 0
    p3 = simulate_next_price(
        current_price=Decimal('0.00'),
        reference_price=Decimal('0.00'),
        previous_close=Decimal('0.00'),
        sector='Automotive'
    )
    assert p3 > Decimal('0')

def test_high_frequency_in_memory_tick_speed():
    """In-memory tick engine executes 50 ticks (1 second of 20 ms ticks) in sub-second time."""
    import time
    sim = MarketSimulator.get_instance()
    sim.hydrate_from_db()

    start_ticks = sim.tick_count
    t0 = time.perf_counter()
    for _ in range(50):
        sim._tick_in_memory()
    elapsed = time.perf_counter() - t0

    # 50 in-memory ticks across 100 stocks must execute in well under 500 ms in Python
    assert elapsed < 0.50, f"50 in-memory ticks took {elapsed:.4f}s, exceeding 500ms budget"
    assert sim.tick_count == start_ticks + 50
    assert sim.measured_tick_interval_ms > 0

def test_decoupled_batch_persistence_flush():
    """Batch persistence writes in-memory prices to database without error."""
    sim = MarketSimulator.get_instance()
    sim.hydrate_from_db()
    sim._tick_in_memory()
    sim._flush_to_db(force=True)

    assert sim.last_error is None
    assert sim.last_flush_time is not None

def test_sse_stream_initial_snapshot(client):
    """SSE endpoint /market/api/v1/market/stream connects and serves text/event-stream."""
    resp = client.get("/market/api/v1/market/stream")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("Content-Type", "")

def test_independent_stochastic_streams_per_symbol():
    """Different symbols use independent pseudo-random streams and do not move in lockstep."""
    sim = MarketSimulator.get_instance()
    sim.hydrate_from_db()

    # Track returns for 5 distinct symbols over 10 ticks
    stocks_to_track = [1, 2, 9, 39, 50] # TCS, INFY, HDFCBANK, RELIANCE, MARUTI
    returns_history = {sid: [] for sid in stocks_to_track}

    for _ in range(10):
        quotes_before = {sid: sim.get_quote(sid)["price"] for sid in stocks_to_track}
        sim._tick_in_memory()
        for sid in stocks_to_track:
            new_p = sim.get_quote(sid)["price"]
            pct = (new_p - quotes_before[sid]) / quotes_before[sid]
            returns_history[sid].append(pct)

    # Check that TCS and INFY returns are not identical
    assert returns_history[1] != returns_history[2]
    # Check that MARUTI and RELIANCE returns are not identical
    assert returns_history[39] != returns_history[50]

def test_deterministic_seeded_simulation():
    """Setting explicit base seed reproduces identical price trajectories."""
    sim = MarketSimulator.get_instance()
    sim.hydrate_from_db()

    # Run pass 1 with seed 777
    sim.set_seed(777)
    sim.hydrate_from_db()
    for _ in range(5):
        sim._tick_in_memory()
    pass1_tcs = sim.get_quote(1)["price"]
    pass1_maruti = sim.get_quote(50)["price"]

    # Run pass 2 with seed 777
    sim.set_seed(777)
    sim.hydrate_from_db()
    for _ in range(5):
        sim._tick_in_memory()
    pass2_tcs = sim.get_quote(1)["price"]
    pass2_maruti = sim.get_quote(50)["price"]

    assert pass1_tcs == pass2_tcs
    assert pass1_maruti == pass2_maruti

def test_sync_stock_authoritative_price_to_db():
    """sync_stock_to_db updates MySQL Current_Prices immediately with in-memory quote."""
    from models.db import get_db_connection
    from sqlalchemy import text

    sim = MarketSimulator.get_instance()
    sim.hydrate_from_db()
    sim._tick_in_memory()

    # Get in-memory quote for stock 1
    quote = sim.get_quote(1)
    assert quote is not None
    sim.sync_stock_to_db(1)

    # Verify Current_Prices in MySQL matches exactly
    with get_db_connection() as conn:
        db_price = conn.execute(text("SELECT price FROM Current_Prices WHERE stock_id = 1")).scalar()
        assert float(db_price) == quote["price"]
