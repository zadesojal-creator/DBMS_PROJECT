"""
Investor Features Test Suite (tests/test_investor_features.py)
Tests Watchlist, Price Alerts, Assigned Broker details, Statement CSV export, and Simulator cadence.
"""
from decimal import Decimal
import pytest
from repositories.watchlist_repo import WatchlistRepository
from repositories.alert_repo import AlertRepository
from repositories.broker_repo import BrokerRepository
from services.market_simulator import MarketSimulator
from config import Config

def test_simulator_500ms_interval():
    """Validates that simulator is configured for 500 ms (0.50s, 2 ticks/sec) per master specification."""
    sim = MarketSimulator.get_instance(interval_seconds=0.50)
    assert sim.tick_interval_seconds == 0.50
    assert Config.SIMULATOR_TICK_INTERVAL_SEC == 0.50

def test_watchlist_crud_endpoints(investor_client):
    """Verifies adding, listing, duplicate handling, and removing watchlist items."""
    # 1. Clear any existing watchlist for user 4
    items = WatchlistRepository.get_by_user(4)
    for it in items:
        WatchlistRepository.remove(4, it["stock_id"])

    # 2. Add stock 1 (RELIANCE)
    res_add = investor_client.post("/investor/api/v1/investor/watchlist", json={"stock_id": 1})
    assert res_add.status_code == 200
    assert res_add.json["ok"] is True

    # 3. Add stock 1 again (idempotent duplicate should succeed without error)
    res_dup = investor_client.post("/investor/api/v1/investor/watchlist", json={"stock_id": 1})
    assert res_dup.status_code == 200
    assert res_dup.json["ok"] is True

    # 4. List watchlist
    res_list = investor_client.get("/investor/api/v1/investor/watchlist")
    assert res_list.status_code == 200
    assert res_list.json["ok"] is True
    watchlist_items = res_list.json["data"]
    assert len(watchlist_items) >= 1
    found = next((i for i in watchlist_items if i["stock_id"] == 1), None)
    assert found is not None
    assert found["symbol"] == "TCS"
    assert "current_price" in found
    assert "day_change" in found
    assert "day_change_pct" in found

    # 5. Remove stock 1
    res_del = investor_client.delete("/investor/api/v1/investor/watchlist/1")
    assert res_del.status_code == 200
    assert res_del.json["ok"] is True

    # 6. Verify removal
    res_list_after = investor_client.get("/investor/api/v1/investor/watchlist")
    assert not any(i["stock_id"] == 1 for i in res_list_after.json["data"])

def test_watchlist_validation(investor_client):
    """Verifies invalid stock_id is rejected."""
    res_bad = investor_client.post("/investor/api/v1/investor/watchlist", json={"stock_id": "invalid"})
    assert res_bad.status_code == 400

    res_nonexistent = investor_client.post("/investor/api/v1/investor/watchlist", json={"stock_id": 999999})
    assert res_nonexistent.status_code == 404

def test_price_alerts_crud_and_validation(investor_client):
    """Tests creating, listing, and cancelling price alerts."""
    # 1. Validation rejection
    bad_res1 = investor_client.post("/investor/api/v1/investor/alerts", json={
        "stock_id": 1,
        "target_price": -50.0,
        "condition_type": "ABOVE"
    })
    assert bad_res1.status_code == 400

    bad_res2 = investor_client.post("/investor/api/v1/investor/alerts", json={
        "stock_id": 1,
        "target_price": 2500.0,
        "condition_type": "BETWEEN"
    })
    assert bad_res2.status_code == 400

    # 2. Create active alert
    res_create = investor_client.post("/investor/api/v1/investor/alerts", json={
        "stock_id": 1,
        "target_price": 3200.00,
        "condition_type": "ABOVE"
    })
    assert res_create.status_code == 201
    assert res_create.json["ok"] is True
    alert_id = res_create.json["data"]["alert_id"]
    assert alert_id > 0

    try:
        # 3. List active alerts
        res_list = investor_client.get("/investor/api/v1/investor/alerts?status=ACTIVE")
        assert res_list.status_code == 200
        assert res_list.json["ok"] is True
        active_alerts = res_list.json["data"]
        created_alert = next((a for a in active_alerts if a["alert_id"] == alert_id), None)
        assert created_alert is not None
        assert created_alert["symbol"] == "TCS"
        assert created_alert["condition_type"] == "ABOVE"
        assert created_alert["status"] == "ACTIVE"

        # 4. Cancel alert
        res_cancel = investor_client.delete(f"/investor/api/v1/investor/alerts/{alert_id}")
        assert res_cancel.status_code == 200
        assert res_cancel.json["ok"] is True

        # 5. Verify status is CANCELLED
        res_all = investor_client.get("/investor/api/v1/investor/alerts")
        cancelled_alert = next((a for a in res_all.json["data"] if a["alert_id"] == alert_id), None)
        assert cancelled_alert is not None
        assert cancelled_alert["status"] == "CANCELLED"
    finally:
        # Cleanup
        AlertRepository.delete(4, alert_id)

def test_assigned_broker_endpoints(investor_client):
    """Verifies that investor portfolio summary and broker endpoint include assigned broker details."""
    # 1. Summary endpoint
    res_sum = investor_client.get("/investor/api/v1/investor/summary")
    assert res_sum.status_code == 200
    assert res_sum.json["ok"] is True
    data = res_sum.json["data"]
    assert "assigned_broker" in data
    assert "brokerage_policy" in data
    assert "portfolio_value" in data
    assert data["portfolio_value"] >= 0.0

    # User 4 (Rahul Verma) is assigned to Broker Arun (id=2)
    broker = data["assigned_broker"]
    if broker:
        assert broker["broker_id"] == 2
        assert broker["broker_name"] == "Arun Mehta (Apex Capital)"
        assert broker["broker_email"] == "arun@stocktrade.local"

    policy = data["brokerage_policy"]
    assert policy["rate"] == 0.0010
    assert policy["rate_pct"] == 0.10
    assert policy["min_fee"] == 1.00

    # 2. Dedicated broker endpoint
    res_broker = investor_client.get("/investor/api/v1/investor/broker")
    assert res_broker.status_code == 200
    assert res_broker.json["ok"] is True
    b_data = res_broker.json["data"]
    assert "broker" in b_data
    assert "policy" in b_data
    assert b_data["policy"]["brokerage_min_fee"] == 1.00

def test_investor_statement_csv(investor_client):
    """Verifies that investor transaction statement CSV download generates valid CSV."""
    res = investor_client.get("/investor/api/v1/investor/statement")
    assert res.status_code == 200
    assert res.mimetype == "text/csv"
    assert "Content-Disposition" in res.headers
    assert "stocktrade_transactions.csv" in res.headers["Content-Disposition"]
    csv_text = res.data.decode("utf-8")
    assert "Transaction ID,Date Time,Symbol,Side,Quantity,Execution Price,Gross Amount,Brokerage Fee,Net Amount" in csv_text
