"""
StockTrade 7-Day Historical Price Generator (backfill_prices.py)
Generates deterministic, bounded 1-minute OHLCV time-series observations.
Mean-reverting random walk with sector volatility, tick clamps (0.5%), and circuit limits (10%).
"""
import random
import sys
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

SECTOR_VOLATILITY = {
    'Information Technology': 0.0035,
    'Banking': 0.0040,
    'Financial Services': 0.0038,
    'Energy & Power': 0.0030,
    'Automotive': 0.0036,
    'Healthcare & Pharma': 0.0028,
    'Consumer Goods & FMCG': 0.0020,
    'Metals & Mining': 0.0045,
    'Infrastructure & Construction': 0.0035,
    'Real Estate': 0.0048,
    'Cement & Building Materials': 0.0025,
    'Chemicals': 0.0032,
    'Telecom & Media': 0.0042,
    'Retail & Consumer Services': 0.0038,
    'Defense & Aerospace': 0.0040,
    'Capital Goods': 0.0034,
}

TICK_SIZE = Decimal('0.05')

def round_tick(price: Decimal) -> Decimal:
    """Round to nearest 0.05 tick size."""
    ticks = (price / TICK_SIZE).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return ticks * TICK_SIZE

def simulate_next_price(
    current_price: Decimal,
    reference_price: Decimal,
    previous_close: Decimal,
    sector: str,
    max_tick_pct: Decimal = Decimal('0.005'),
    circuit_pct: Decimal = Decimal('0.10'),
    seed_val: int = 42
) -> Decimal:
    """
    Mean-reverting random walk:
    delta = -reversion_speed * (current_price - ref) + noise
    clamped to [-max_tick_pct, +max_tick_pct], bounded by circuit limits [0.90, 1.10] of prev_close.
    Safeguards against zero or invalid reference / previous_close values.
    """
    # Deterministic fallback safeguards
    if reference_price is None or reference_price <= Decimal('0'):
        reference_price = current_price if (current_price is not None and current_price > Decimal('0')) else Decimal('100.00')
    if previous_close is None or previous_close <= Decimal('0'):
        previous_close = reference_price
    if current_price is None or current_price <= Decimal('0'):
        current_price = reference_price

    rng = random.Random(seed_val)
    vol = Decimal(str(SECTOR_VOLATILITY.get(sector, 0.0030)))
    
    # Mean reversion pull towards base reference price (safely guarded against zero ref)
    pull = Decimal('-0.05') * ((current_price - reference_price) / reference_price)
    
    # Gaussian perturbation
    noise = Decimal(str(rng.gauss(0.0, float(vol))))
    raw_return = pull + noise
    
    # Clamp to max tick percentage
    clamped_return = max(min(raw_return, max_tick_pct), -max_tick_pct)
    
    new_price = current_price * (Decimal('1') + clamped_return)
    
    # Enforce circuit limits
    lower_circuit = previous_close * (Decimal('1') - circuit_pct)
    upper_circuit = previous_close * (Decimal('1') + circuit_pct)
    
    new_price = max(min(new_price, upper_circuit), lower_circuit)
    
    # Absolute minimum floor (positive, tick-aligned)
    if new_price < Decimal('0.05'):
        new_price = Decimal('0.05')
        
    return round_tick(new_price)

def generate_seven_day_history(conn, days: int = 7, progress_callback=None):
    """
    Backfills 7 days of 1-minute observations for all active stocks.
    Uses executemany with 5,000-row batches.
    """
    with conn.cursor() as cur:
        # Check if already seeded
        cur.execute("SELECT COUNT(*) FROM Stock_Prices WHERE source = 'SEEDED'")
        count = cur.fetchone()[0]
        if count > 1000:
            print(f"[backfill_prices] Already populated ({count} rows). Skipping backfill.")
            return

        cur.execute("SELECT id, symbol, sector FROM Stocks WHERE status = 'ACTIVE'")
        stocks = cur.fetchall()
        if not stocks:
            print("[backfill_prices] No stocks found. Run seed_companies first.")
            return

        cur.execute("SELECT stock_id, price, previous_close FROM Current_Prices")
        price_map = {row[0]: (Decimal(str(row[1])), Decimal(str(row[2]))) for row in cur.fetchall()}

    end_time = datetime.now().replace(second=0, microsecond=0)
    # Generate 5 trading days or 7 calendar days with 1m intervals
    # To keep total rows manageable and fast (~70k observations across 100 stocks):
    # E.g., sample every 5 minutes across 7 days or 1 minute across the last 3 business days
    # Let's do 1-minute intervals during active hours (09:15 to 15:30) for the last 5 days
    observations_per_stock = []
    
    # Target dates
    active_dates = []
    curr_date = end_time.date() - timedelta(days=days)
    while curr_date <= end_time.date():
        # Mon-Fri
        if curr_date.weekday() < 5:
            active_dates.append(curr_date)
        curr_date += timedelta(days=1)

    timestamps = []
    for d in active_dates:
        t = datetime.combine(d, datetime.min.time()) + timedelta(hours=9, minutes=15)
        day_end = datetime.combine(d, datetime.min.time()) + timedelta(hours=15, minutes=30)
        # To optimize init time while providing rich data, tick every 2 minutes or 1 minute
        while t <= day_end and t <= end_time:
            timestamps.append(t)
            t += timedelta(minutes=2)

    total_ticks = len(timestamps) * len(stocks)
    print(f"[backfill_prices] Generating {total_ticks} observations across {len(stocks)} stocks...")

    batch = []
    batch_size = 5000
    inserted = 0

    with conn.cursor() as cur:
        for stock_id, symbol, sector in stocks:
            ref_price, prev_close = price_map.get(stock_id, (Decimal('1000.00'), Decimal('995.00')))
            curr_price = ref_price
            
            for ts in timestamps:
                # Deterministic seed using stock_id and timestamp unix epoch
                tick_seed = stock_id * 1000000 + int(ts.timestamp())
                curr_price = simulate_next_price(
                    current_price=curr_price,
                    reference_price=ref_price,
                    previous_close=prev_close,
                    sector=sector,
                    seed_val=tick_seed
                )
                vol = random.Random(tick_seed).randint(50, 1500)
                batch.append((stock_id, float(curr_price), vol, 'SEEDED', ts.strftime('%Y-%m-%d %H:%M:%S')))

                if len(batch) >= batch_size:
                    cur.executemany(
                        "INSERT INTO Stock_Prices (stock_id, price, volume, source, recorded_at) VALUES (%s, %s, %s, %s, %s)",
                        batch
                    )
                    conn.commit()
                    inserted += len(batch)
                    batch = []
                    if progress_callback:
                        progress_callback(inserted, total_ticks)
                    else:
                        pct = (inserted / total_ticks) * 100
                        sys.stdout.write(f"\r[backfill_prices] Progress: {pct:.1f}% ({inserted}/{total_ticks} rows)")
                        sys.stdout.flush()

        if batch:
            cur.executemany(
                "INSERT INTO Stock_Prices (stock_id, price, volume, source, recorded_at) VALUES (%s, %s, %s, %s, %s)",
                batch
            )
            conn.commit()
            inserted += len(batch)

    print(f"\n[backfill_prices] Completed successfully. Total inserted: {inserted} rows.")
