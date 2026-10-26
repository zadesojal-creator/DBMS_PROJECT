"""
Market Overview & Real-Time Price Polling Blueprint (routes/market.py)
Delivers polling deltas, OHLC chart data, and market directory APIs.
"""
import json
import queue
from datetime import datetime, timedelta
from typing import Optional
from flask import Blueprint, render_template, request, jsonify, Response
from flask_login import login_required
from sqlalchemy import text
from models.db import get_db_connection
from repositories.stock_repo import StockRepository
from services.market_simulator import MarketSimulator

market_bp = Blueprint("market", __name__, url_prefix="/market")

@market_bp.route("/")
@login_required
def overview():
    stocks = StockRepository.get_market_overview()
    return render_template("market/overview.html", stocks=stocks)

@market_bp.route("/<symbol>")
@login_required
def stock_detail(symbol: str):
    stock = StockRepository.get_by_symbol(symbol)
    if not stock:
        return render_template("errors/404.html", message="Stock not found"), 404
    quote = StockRepository.get_quote(stock["id"])
    return render_template("market/detail.html", stock=stock, quote=quote)

# ==============================================================================
# REST API Endpoints (/api/v1/market/...)
# ==============================================================================

@market_bp.route("/api/v1/market/prices", methods=["GET"])
def api_prices():
    """
    Real-time price delivery: polling endpoint with since timestamp filter.
    Returns identical current prices for all roles with full metadata
    (company_name, sector, current_price, previous_close, day_change, day_change_pct).
    """
    since = request.args.get("since")
    sim = MarketSimulator.get_instance()
    sim_status = sim.get_status()

    # Fast-path: query in-memory cached prices from simulator
    data = sim.get_prices(since=since)

    # Fallback to database if simulator cache is empty (e.g. cold start)
    if not data:
        with get_db_connection() as conn:
            query = """
                SELECT 
                    stock_id, symbol, company_name, sector, exchange, status,
                    current_price, previous_close, day_change, day_change_pct,
                    day_open, day_high, day_low, volume, updated_at
                FROM v_market_latest
            """
            params = {}
            if since:
                query += " WHERE updated_at > :since"
                params["since"] = since
            query += " ORDER BY symbol ASC"

            rows = conn.execute(text(query), params).mappings().all()

            data = [{
                "stock_id": r["stock_id"],
                "id": r["stock_id"],
                "symbol": r["symbol"],
                "company_name": r["company_name"],
                "sector": r["sector"],
                "exchange": r["exchange"],
                "status": r["status"],
                "price": float(r["current_price"]),
                "current_price": float(r["current_price"]),
                "previous_close": float(r["previous_close"]),
                "day_change": float(r["day_change"]),
                "change": float(r["day_change"]),
                "day_change_pct": float(r["day_change_pct"]),
                "change_pct": float(r["day_change_pct"]),
                "day_open": float(r["day_open"]),
                "day_high": float(r["day_high"]),
                "day_low": float(r["day_low"]),
                "volume": int(r["volume"]),
                "updated_at": r["updated_at"].strftime("%Y-%m-%d %H:%M:%S") if r["updated_at"] else None
            } for r in rows]

    return jsonify({
        "ok": True,
        "data": data,
        "simulator": sim_status,
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }), 200

@market_bp.route("/api/v1/market/stream", methods=["GET"])
def api_market_stream():
    """
    Server-Sent Events (SSE) streaming endpoint for push-based real-time price updates.
    Sends initial snapshot event upon connection, followed by high-frequency tick deltas.
    """
    sim = MarketSimulator.get_instance()
    q = sim.subscribe()

    def event_stream():
        try:
            # 1. Initial full snapshot
            snapshot = sim.get_prices()
            yield f"event: snapshot\ndata: {json.dumps(snapshot)}\n\n"

            # 2. Continuous tick updates or keepalive
            while True:
                try:
                    deltas = q.get(timeout=10.0)
                    yield f"event: tick\ndata: {json.dumps(deltas)}\n\n"
                except queue.Empty:
                    yield ": keepalive\n\n"
        except GeneratorExit:
            sim.unsubscribe(q)
        except Exception:
            sim.unsubscribe(q)

    response = Response(event_stream(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    response.headers["Connection"] = "keep-alive"
    return response

@market_bp.route("/api/v1/market/stocks", methods=["GET"])
def api_stocks():
    """Returns directory of all 100 stocks with current quotes and sector filtering."""
    sector = request.args.get("sector")
    search = request.args.get("search")
    stocks = StockRepository.get_market_overview(sector=sector, search=search)
    return jsonify({
        "ok": True,
        "data": stocks
    }), 200

@market_bp.route("/api/v1/market/history", methods=["GET"])
def api_history():
    """
    Aggregated OHLC historical bucket data (1m, 5m, 1h).
    Computed in SQL using FLOOR(UNIX_TIMESTAMP(recorded_at)/bucket).
    Omitted when empty; never interpolated.
    """
    stock_id = request.args.get("stock_id", type=int)
    symbol = request.args.get("symbol")
    interval = request.args.get("interval", "1h").lower()
    
    if not stock_id and symbol:
        stock = StockRepository.get_by_symbol(symbol)
        if stock:
            stock_id = stock["id"]

    if not stock_id:
        return jsonify({
            "ok": False,
            "error": {"code": "BAD_REQUEST", "message": "stock_id or symbol is required"}
        }), 400

    interval_seconds = 3600
    if interval == "1m":
        interval_seconds = 60
    elif interval == "5m":
        interval_seconds = 300
    elif interval == "1h":
        interval_seconds = 3600
    else:
        return jsonify({
            "ok": False,
            "error": {"code": "BAD_REQUEST", "message": "Invalid interval. Allowed: 1m, 5m, 1h"}
        }), 400

    # Default time range: 7 days for 1h/5m, bounded to 1 day for 1m
    now = datetime.now()
    if interval == "1m":
        start_time = now - timedelta(days=1)
    else:
        start_time = now - timedelta(days=7)

    with get_db_connection() as conn:
        ohlc_query = """
            WITH BucketedPrices AS (
                SELECT 
                    id,
                    price,
                    volume,
                    recorded_at,
                    FROM_UNIXTIME(FLOOR(UNIX_TIMESTAMP(recorded_at) / :bucket) * :bucket) AS bucket_start,
                    FIRST_VALUE(price) OVER (
                        PARTITION BY FLOOR(UNIX_TIMESTAMP(recorded_at) / :bucket) 
                        ORDER BY recorded_at ASC, id ASC
                    ) AS open_price,
                    FIRST_VALUE(price) OVER (
                        PARTITION BY FLOOR(UNIX_TIMESTAMP(recorded_at) / :bucket) 
                        ORDER BY recorded_at DESC, id DESC
                    ) AS close_price
                FROM Stock_Prices
                WHERE stock_id = :stock_id AND recorded_at >= :start_time
            )
            SELECT 
                bucket_start,
                open_price,
                MAX(price) AS high_price,
                MIN(price) AS low_price,
                close_price,
                SUM(volume) AS volume,
                COUNT(id) AS observation_count
            FROM BucketedPrices
            GROUP BY bucket_start, open_price, close_price
            ORDER BY bucket_start ASC
            LIMIT 5000
        """
        rows = conn.execute(text(ohlc_query), {
            "stock_id": stock_id,
            "bucket": interval_seconds,
            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S")
        }).mappings().all()

        candles = [{
            "time": r["bucket_start"].strftime("%Y-%m-%d %H:%M"),
            "bucket": r["bucket_start"].strftime("%Y-%m-%d %H:%M"),
            "open": float(r["open_price"]),
            "high": float(r["high_price"]),
            "low": float(r["low_price"]),
            "close": float(r["close_price"]),
            "volume": int(r["volume"]),
            "ticks": int(r["observation_count"])
        } for r in rows]

    return jsonify({
        "ok": True,
        "data": {
            "stock_id": stock_id,
            "interval": interval,
            "count": len(candles),
            "candles": candles,
            "truncated": len(candles) >= 5000
        }
    }), 200

@market_bp.route("/api/v1/market/status", methods=["GET"])
def api_status():
    """Returns simulator status, freshness indicator, and ticks completed."""
    sim = MarketSimulator.get_instance()
    status = sim.get_status()
    return jsonify({
        "ok": True,
        "data": status
    }), 200

