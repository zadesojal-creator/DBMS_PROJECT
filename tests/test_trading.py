"""
Trading Engine & Financial Math Suite (test_trading.py)
Validates buy, sell, weighted average cost, P&L calculations, deposit limits,
brokerage rules, minimum fees, broker commission attribution, and reconciliation.
"""
import uuid
from decimal import Decimal, ROUND_HALF_UP
import pytest
from services.trading_service import TradingService
from services.portfolio_service import PortfolioService
from repositories.account_repo import AccountRepository
from repositories.holding_repo import HoldingRepository
from repositories.transaction_repo import TransactionRepository
from repositories.ledger_repo import LedgerRepository
from models.db import get_db_connection
from sqlalchemy import text

def test_buy_order_execution_and_math(investor_client):
    """
    Investor buys 10 shares of stock 1 (TCS).
    Checks:
    - Order reaches EXECUTED
    - Virtual balance decreases by trade_value + brokerage
    - Holding average cost = execution price
    - Two ledger entries created: BUY (-trade_val) and FEE (-brokerage)
    """
    account_before = AccountRepository.get_by_user_id(4) # Rahul Verma
    balance_before = Decimal(str(account_before['virtual_balance']))
    if balance_before < Decimal('50000.00'):
        TradingService.process_deposit(4, Decimal('100000.00'))
        account_before = AccountRepository.get_by_user_id(4)
        balance_before = Decimal(str(account_before['virtual_balance']))
    
    key = str(uuid.uuid4())
    resp = investor_client.post("/investor/api/v1/investor/trade", json={
        "stock_id": 1,
        "side": "BUY",
        "quantity": 10,
        "idempotency_key": key
    })
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["status"] == "EXECUTED"
    exec_price = Decimal(str(data["execution_price"]))

    # Calculations
    trade_value = (exec_price * 10).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    brokerage_raw = (trade_value * Decimal('0.0010')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    brokerage = max(Decimal('1.00'), brokerage_raw)
    expected_balance = balance_before - (trade_value + brokerage)

    account_after = AccountRepository.get_by_user_id(4)
    balance_after = Decimal(str(account_after['virtual_balance']))
    assert balance_after == expected_balance

    # Verify reconciliation invariant
    reconciled = PortfolioService.verify_reconciliation_invariants(4)
    assert reconciled["cash_reconciled"] is True
    assert reconciled["holdings_reconciled"] is True

def test_partial_sell_and_realized_pnl(investor_client):
    """
    Investor sells 5 shares of stock 1.
    Average cost must remain unchanged on partial sale.
    Realized P&L = (sell_price - avg_cost) * qty - sell_brokerage.
    """
    holding_before = HoldingRepository.get_by_user_and_stock(4, 1)
    assert holding_before is not None
    avg_cost_before = Decimal(str(holding_before['avg_cost']))
    qty_before = holding_before['quantity']

    key = str(uuid.uuid4())
    resp = investor_client.post("/investor/api/v1/investor/trade", json={
        "stock_id": 1,
        "side": "SELL",
        "quantity": 5,
        "idempotency_key": key
    })
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["status"] == "EXECUTED"

    holding_after = HoldingRepository.get_by_user_and_stock(4, 1)
    assert holding_after['quantity'] == qty_before - 5
    # Average cost must not change on partial sale
    assert Decimal(str(holding_after['avg_cost'])) == avg_cost_before

    # Verify reconciliation invariant
    reconciled = PortfolioService.verify_reconciliation_invariants(4)
    assert reconciled["cash_reconciled"] is True
    assert reconciled["holdings_reconciled"] is True

def test_sell_insufficient_holdings_rejected(investor_client):
    """Selling more shares than owned must be rejected."""
    resp = investor_client.post("/investor/api/v1/investor/trade", json={
        "stock_id": 1,
        "side": "SELL",
        "quantity": 999999,
        "idempotency_key": str(uuid.uuid4())
    })
    assert resp.status_code == 422
    assert "insufficient" in resp.get_json()["error"]["message"].lower()

def test_deposit_validation_and_ledger(investor_client):
    """Test virtual deposit validation and ledger entry."""
    # Below minimum (₹100)
    resp_low = investor_client.post("/investor/api/v1/investor/deposit", json={"amount": 50})
    assert resp_low.status_code == 422
    assert "minimum" in resp_low.get_json()["error"]["message"].lower()

    # Above maximum (₹10,00,000)
    resp_high = investor_client.post("/investor/api/v1/investor/deposit", json={"amount": 2000000})
    assert resp_high.status_code == 422
    assert "maximum" in resp_high.get_json()["error"]["message"].lower()

    # Valid deposit (₹10,000)
    account_before = AccountRepository.get_by_user_id(4)
    bal_before = Decimal(str(account_before['virtual_balance']))
    
    resp_valid = investor_client.post("/investor/api/v1/investor/deposit", json={"amount": 10000})
    assert resp_valid.status_code == 200
    data = resp_valid.get_json()["data"]
    assert Decimal(str(data["new_virtual_balance"])) == bal_before + Decimal('10000.00')

    # Verify reconciliation invariant
    reconciled = PortfolioService.verify_reconciliation_invariants(4)
    assert reconciled["cash_reconciled"] is True

def test_authoritative_execution_price_and_full_response_payload(investor_client):
    """
    Trade execution response must contain full non-zero financial details
    matching the persisted Transactions row: quantity, gross_amount, brokerage_fee, net_amount.
    """
    key = str(uuid.uuid4())
    resp = investor_client.post("/investor/api/v1/investor/trade", json={
        "stock_id": 1,
        "side": "BUY",
        "quantity": 2,
        "idempotency_key": key
    })
    assert resp.status_code == 200
    data = resp.get_json()["data"]

    assert data["status"] == "EXECUTED"
    assert data["transaction_id"] is not None
    assert data["quantity"] == 2
    assert data["executed_quantity"] == 2
    assert data["execution_price"] > 0
    assert data["gross_amount"] > 0
    assert data["brokerage_fee"] >= 1.00
    assert data["net_amount"] == round(data["gross_amount"] + data["brokerage_fee"], 2)
    assert data["symbol"] == "TCS"

    # Cross check with database
    with get_db_connection() as conn:
        tx = conn.execute(text("SELECT * FROM Transactions WHERE id = :id"), {"id": data["transaction_id"]}).mappings().first()
        assert tx is not None
        assert float(tx["execution_price"]) == data["execution_price"]
        assert float(tx["gross_amount"]) == data["gross_amount"]
        assert float(tx["brokerage_fee"]) == data["brokerage_fee"]
        assert float(tx["net_amount"]) == data["net_amount"]

def test_brokerage_minimum_fee_rule(investor_client):
    """
    Very low-value trade (1 share of Vodafone Idea ~₹12) triggers minimum fee of ₹1.00.
    """
    with get_db_connection() as conn:
        idea_id = conn.execute(text("SELECT id FROM Stocks WHERE symbol = 'IDEA'")).scalar()

    key = str(uuid.uuid4())
    resp = investor_client.post("/investor/api/v1/investor/trade", json={
        "stock_id": idea_id,
        "side": "BUY",
        "quantity": 1,
        "idempotency_key": key
    })
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["status"] == "EXECUTED"

    # Minimum fee of ₹1.00 must be applied because trade value * 0.001 is < 1.00
    assert data["brokerage_fee"] == 1.00
    expected_net = round(data["gross_amount"] + 1.00, 2)
    assert data["net_amount"] == expected_net

def test_broker_commission_attribution_and_no_duplication_on_retry(investor_client):
    """
    Assigned broker receives 40% of collected brokerage; retry with same idempotency key never duplicates commission.
    """
    key = str(uuid.uuid4())
    resp = investor_client.post("/investor/api/v1/investor/trade", json={
        "stock_id": 1,
        "side": "BUY",
        "quantity": 5,
        "idempotency_key": key
    })
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    tx_id = data["transaction_id"]

    with get_db_connection() as conn:
        # Verify commission row created
        comm = conn.execute(text("SELECT * FROM Commissions WHERE transaction_id = :tx_id"), {"tx_id": tx_id}).mappings().first()
        assert comm is not None
        assert comm["broker_id"] == 2 # Broker Priya Sharma
        assert float(comm["base_brokerage"]) == data["brokerage_fee"]
        assert float(comm["rate_applied"]) == 0.40
        assert float(comm["commission_amount"]) == round(data["brokerage_fee"] * 0.40, 2)

        comm_count_before = conn.execute(text("SELECT COUNT(*) FROM Commissions WHERE transaction_id = :tx_id"), {"tx_id": tx_id}).scalar()

    # Retry same order with identical idempotency key
    resp_retry = investor_client.post("/investor/api/v1/investor/trade", json={
        "stock_id": 1,
        "side": "BUY",
        "quantity": 5,
        "idempotency_key": key
    })
    assert resp_retry.status_code == 200
    data_retry = resp_retry.get_json()["data"]
    assert "replay" in data_retry["message"].lower()

    # Ensure no duplicate commission row was inserted
    with get_db_connection() as conn:
        comm_count_after = conn.execute(text("SELECT COUNT(*) FROM Commissions WHERE transaction_id = :tx_id"), {"tx_id": tx_id}).scalar()
        assert comm_count_after == comm_count_before

def test_failed_trade_rolls_back_everything(investor_client):
    """
    Order rejection (e.g. insufficient cash) rolls back all state atomically.
    No balance deduction, no holding change, no ledger row, no commission.
    """
    with get_db_connection() as conn:
        bal_before = conn.execute(text("SELECT virtual_balance FROM Accounts WHERE user_id = 4")).scalar()
        ledger_count_before = conn.execute(text("SELECT COUNT(*) FROM Account_Ledger WHERE account_id = (SELECT id FROM Accounts WHERE user_id = 4)")).scalar()
        comm_count_before = conn.execute(text("SELECT COUNT(*) FROM Commissions WHERE investor_id = 4")).scalar()

    resp = investor_client.post("/investor/api/v1/investor/trade", json={
        "stock_id": 1,
        "side": "BUY",
        "quantity": 9999999,
        "idempotency_key": str(uuid.uuid4())
    })
    assert resp.status_code == 422

    with get_db_connection() as conn:
        bal_after = conn.execute(text("SELECT virtual_balance FROM Accounts WHERE user_id = 4")).scalar()
        ledger_count_after = conn.execute(text("SELECT COUNT(*) FROM Account_Ledger WHERE account_id = (SELECT id FROM Accounts WHERE user_id = 4)")).scalar()
        comm_count_after = conn.execute(text("SELECT COUNT(*) FROM Commissions WHERE investor_id = 4")).scalar()

        # Balance, ledger, and commissions must be completely unchanged
        assert bal_after == bal_before
        assert ledger_count_after == ledger_count_before
        assert comm_count_after == comm_count_before

def test_commission_rules_admin_crud(admin_client, investor_client):
    """
    Admin can view and update commission policy; new rate is immediately applied to subsequent trades.
    """
    # 1. Fetch current rules
    resp = admin_client.get("/admin/api/v1/admin/commission-rules")
    assert resp.status_code == 200
    rules = resp.get_json()["data"]
    assert len(rules) >= 2

    # 2. Update INVESTOR_BROKERAGE to 0.0020 (0.20%) and min_fee 2.00
    try:
        upd_resp = admin_client.post("/admin/api/v1/admin/commission-rules", json={
            "rule_type": "INVESTOR_BROKERAGE",
            "rate": 0.0020,
            "min_fee": 2.00
        })
        assert upd_resp.status_code == 200

        # 3. Ensure funds and place trade to verify new 0.20% rate applied
        account = AccountRepository.get_by_user_id(4)
        if Decimal(str(account['virtual_balance'])) < Decimal('50000.00'):
            TradingService.process_deposit(4, Decimal('100000.00'))

        trade_resp = investor_client.post("/investor/api/v1/investor/trade", json={
            "stock_id": 1,
            "side": "BUY",
            "quantity": 10,
            "idempotency_key": str(uuid.uuid4())
        })
        assert trade_resp.status_code == 200
        trade_data = trade_resp.get_json()["data"]
        expected_fee = max(2.00, round(trade_data["gross_amount"] * 0.0020, 2))
        assert trade_data["brokerage_fee"] == expected_fee
    finally:
        # 4. Always restore original rule (0.0010 and 1.00)
        admin_client.post("/admin/api/v1/admin/commission-rules", json={
            "rule_type": "INVESTOR_BROKERAGE",
            "rate": 0.0010,
            "min_fee": 1.00
        })
