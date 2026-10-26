"""
Investor Dashboard & Portfolio Blueprint (routes/investor.py)
Provides web views and REST APIs for portfolio metrics, trade execution, and deposits.
"""
from decimal import Decimal
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user, login_required
from services.auth_service import role_required
from services.trading_service import TradingService
from services.portfolio_service import PortfolioService
from repositories.account_repo import AccountRepository
from repositories.holding_repo import HoldingRepository
from repositories.order_repo import OrderRepository
from repositories.transaction_repo import TransactionRepository
from repositories.stock_repo import StockRepository
from repositories.watchlist_repo import WatchlistRepository
from repositories.alert_repo import AlertRepository
from repositories.broker_repo import BrokerRepository

investor_bp = Blueprint("investor", __name__, url_prefix="/investor")

# Web Views
@investor_bp.route("/dashboard")
@role_required("INVESTOR")
def dashboard():
    account = AccountRepository.get_by_user_id(current_user.id)
    holdings = HoldingRepository.get_by_user(current_user.id)
    recent_transactions = TransactionRepository.get_by_user(current_user.id, limit=5)
    return render_template(
        "investor/dashboard.html",
        account=account,
        holdings=holdings,
        recent_transactions=recent_transactions
    )

@investor_bp.route("/portfolio")
@role_required("INVESTOR")
def portfolio():
    account = AccountRepository.get_by_user_id(current_user.id)
    holdings = HoldingRepository.get_by_user(current_user.id)
    return render_template("investor/portfolio.html", account=account, holdings=holdings)

@investor_bp.route("/trade")
@role_required("INVESTOR")
def trade():
    account = AccountRepository.get_by_user_id(current_user.id)
    stocks = StockRepository.get_market_overview()
    return render_template("investor/trade.html", account=account, stocks=stocks)

@investor_bp.route("/account")
@role_required("INVESTOR")
def account():
    account = AccountRepository.get_by_user_id(current_user.id)
    summary = PortfolioService.get_portfolio_summary(current_user.id)
    return render_template("investor/account.html", account=account, summary=summary)

@investor_bp.route("/transactions")
@role_required("INVESTOR")
def transactions():
    transactions = TransactionRepository.get_by_user(current_user.id, limit=50)
    return render_template("investor/transactions.html", transactions=transactions)

@investor_bp.route("/watchlist")
@role_required("INVESTOR")
def watchlist():
    return render_template("investor/watchlist.html")

@investor_bp.route("/broker")
@role_required("INVESTOR")
def broker():
    return render_template("investor/broker.html")

# ==============================================================================
# REST API Endpoints (/api/v1/investor/...)
# ==============================================================================

@investor_bp.route("/api/v1/investor/summary", methods=["GET"])
@role_required("INVESTOR")
def api_summary():
    """Returns canonical portfolio summary computed directly from database."""
    summary = PortfolioService.get_portfolio_summary(current_user.id)
    # Serialize Decimals to float for JSON response
    serialized = {
        k: float(v) if isinstance(v, Decimal) else v
        for k, v in summary.items()
    }
    # Ensure portfolio_value is explicitly set as alias of total_portfolio_value
    serialized["portfolio_value"] = serialized.get("total_portfolio_value", 0.0)
    # Include assigned broker details
    assigned_broker = BrokerRepository.get_assigned_broker_for_investor(current_user.id)
    serialized["assigned_broker"] = assigned_broker
    serialized["brokerage_policy"] = {
        "rate": 0.0010,
        "rate_pct": 0.10,
        "min_fee": 1.00,
        "broker_commission_rate": 0.40,
        "broker_commission_rate_pct": 40.0
    }
    return jsonify({"ok": True, "data": serialized}), 200

@investor_bp.route("/api/v1/investor/trade", methods=["POST"])
@investor_bp.route("/api/v1/investor/orders", methods=["POST"])
@role_required("INVESTOR")
def api_trade():
    """
    Executes a market order atomically via sp_execute_trade.
    Browser sends only stock_id, side, quantity, and client-generated idempotency_key.
    Authoritative price is read inside server-side transaction.
    """
    data = request.get_json(silent=True) or {}
    stock_id = data.get("stock_id")
    side = data.get("side", "").strip().upper()
    quantity = data.get("quantity")
    idempotency_key = data.get("idempotency_key")
    estimated_quote = data.get("quoted_price") or data.get("estimated_quote")

    if not stock_id or not isinstance(stock_id, int):
        return jsonify({"ok": False, "error": {"code": "BAD_REQUEST", "message": "Valid stock_id is required"}}), 400
    if side not in ("BUY", "SELL"):
        return jsonify({"ok": False, "error": {"code": "BAD_REQUEST", "message": "Side must be BUY or SELL"}}), 400
    if not quantity or not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"ok": False, "error": {"code": "BAD_REQUEST", "message": "Quantity must be a positive integer"}}), 400
    if not idempotency_key:
        return jsonify({"ok": False, "error": {"code": "BAD_REQUEST", "message": "idempotency_key is required"}}), 400

    est_quote_dec = Decimal(str(estimated_quote)) if estimated_quote else None

    result = TradingService.execute_market_order(
        user_id=current_user.id,
        stock_id=stock_id,
        side=side,
        quantity=quantity,
        idempotency_key=idempotency_key,
        estimated_quote=est_quote_dec
    )

    if result["status"] == "REJECTED":
        return jsonify({"ok": False, "error": {"code": "ORDER_REJECTED", "message": result["message"]}}), 422
    elif result["status"] == "FAILED":
        return jsonify({"ok": False, "error": {"code": "ORDER_FAILED", "message": result["message"]}}), 500

    return jsonify({"ok": True, "data": result}), 200

@investor_bp.route("/api/v1/investor/deposit", methods=["POST"])
@role_required("INVESTOR")
def api_deposit():
    """
    Simulated virtual funds deposit:
    Validates amount (min ₹100, max ₹10,00,000, daily cap ₹50,00,000).
    Atomic update of virtual balance and Account_Ledger entry.
    """
    data = request.get_json(silent=True) or {}
    amount_raw = data.get("amount")

    if amount_raw is None:
        return jsonify({"ok": False, "error": {"code": "BAD_REQUEST", "message": "Amount is required"}}), 400

    try:
        amount = Decimal(str(amount_raw))
    except Exception:
        return jsonify({"ok": False, "error": {"code": "BAD_REQUEST", "message": "Invalid numeric amount"}}), 400

    try:
        idempotency_key = data.get("idempotency_key")
        res = TradingService.process_deposit(current_user.id, amount, idempotency_key=idempotency_key)
        return jsonify({"ok": True, "data": res}), 200
    except ValueError as ve:
        return jsonify({"ok": False, "error": {"code": "VALIDATION_ERROR", "message": str(ve)}}), 422

@investor_bp.route("/api/v1/investor/holdings", methods=["GET"])
@role_required("INVESTOR")
def api_holdings():
    """Returns active portfolio holdings."""
    holdings = HoldingRepository.get_by_user(current_user.id)
    serialized = [{
        k: float(v) if isinstance(v, Decimal) else (v.strftime("%Y-%m-%d %H:%M:%S") if hasattr(v, "strftime") else v)
        for k, v in h.items()
    } for h in holdings]
    return jsonify({"ok": True, "data": serialized}), 200

@investor_bp.route("/api/v1/investor/orders", methods=["GET"])
@role_required("INVESTOR")
def api_orders():
    """Returns investor order history."""
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    orders = OrderRepository.get_by_user(current_user.id, limit=limit, offset=offset)
    serialized = [{
        k: float(v) if isinstance(v, Decimal) else (v.strftime("%Y-%m-%d %H:%M:%S") if hasattr(v, "strftime") else v)
        for k, v in o.items()
    } for o in orders]
    return jsonify({"ok": True, "data": serialized}), 200

@investor_bp.route("/api/v1/investor/transactions", methods=["GET"])
@role_required("INVESTOR")
def api_transactions():
    """Returns financial transaction history."""
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    transactions = TransactionRepository.get_by_user(current_user.id, limit=limit, offset=offset)
    serialized = [{
        k: float(v) if isinstance(v, Decimal) else (v.strftime("%Y-%m-%d %H:%M:%S") if hasattr(v, "strftime") else v)
        for k, v in t.items()
    } for t in transactions]
    return jsonify({"ok": True, "data": serialized}), 200

@investor_bp.route("/api/v1/investor/reconciliation", methods=["GET"])
@role_required("INVESTOR")
def api_reconciliation():
    """Verifies cash and share quantity reconciliation invariants."""
    res = PortfolioService.verify_reconciliation_invariants(current_user.id)
    return jsonify({"ok": True, "data": res}), 200

# ==============================================================================
# Watchlist Endpoints
# ==============================================================================

@investor_bp.route("/api/v1/investor/watchlist", methods=["GET"])
@role_required("INVESTOR")
def api_get_watchlist():
    """Returns investor's saved watchlist stocks with real-time market quotes."""
    items = WatchlistRepository.get_by_user(current_user.id)
    serialized = [{
        k: float(v) if isinstance(v, Decimal) else (v.strftime("%Y-%m-%d %H:%M:%S") if hasattr(v, "strftime") else v)
        for k, v in item.items()
    } for item in items]
    return jsonify({"ok": True, "data": serialized}), 200

@investor_bp.route("/api/v1/investor/watchlist", methods=["POST"])
@role_required("INVESTOR")
def api_add_watchlist():
    """Adds a stock to the investor's watchlist."""
    data = request.get_json(silent=True) or {}
    stock_id = data.get("stock_id")
    if not stock_id or not isinstance(stock_id, int):
        return jsonify({"ok": False, "error": {"code": "BAD_REQUEST", "message": "Valid integer stock_id is required"}}), 400
    try:
        WatchlistRepository.add(current_user.id, stock_id)
        return jsonify({"ok": True, "data": {"message": "Stock added to watchlist", "stock_id": stock_id}}), 200
    except ValueError as ve:
        return jsonify({"ok": False, "error": {"code": "NOT_FOUND", "message": str(ve)}}), 404

@investor_bp.route("/api/v1/investor/watchlist/<int:stock_id>", methods=["DELETE"])
@role_required("INVESTOR")
def api_remove_watchlist(stock_id: int):
    """Removes a stock from the investor's watchlist."""
    removed = WatchlistRepository.remove(current_user.id, stock_id)
    return jsonify({"ok": True, "data": {"removed": removed, "stock_id": stock_id}}), 200

# ==============================================================================
# Price Alerts Endpoints
# ==============================================================================

@investor_bp.route("/api/v1/investor/alerts", methods=["GET"])
@role_required("INVESTOR")
def api_get_alerts():
    """Returns price threshold alerts configured by the investor."""
    status = request.args.get("status")
    alerts = AlertRepository.get_by_user(current_user.id, status=status)
    serialized = [{
        k: float(v) if isinstance(v, Decimal) else (v.strftime("%Y-%m-%d %H:%M:%S") if hasattr(v, "strftime") else v)
        for k, v in a.items()
    } for a in alerts]
    return jsonify({"ok": True, "data": serialized}), 200

@investor_bp.route("/api/v1/investor/alerts", methods=["POST"])
@role_required("INVESTOR")
def api_create_alert():
    """Creates a price threshold alert (condition: ABOVE or BELOW target_price)."""
    data = request.get_json(silent=True) or {}
    stock_id = data.get("stock_id")
    target_price_raw = data.get("target_price")
    condition_type = (data.get("condition_type") or "").strip().upper()

    if not stock_id or not isinstance(stock_id, int):
        return jsonify({"ok": False, "error": {"code": "BAD_REQUEST", "message": "Valid integer stock_id is required"}}), 400
    if condition_type not in ('ABOVE', 'BELOW'):
        return jsonify({"ok": False, "error": {"code": "BAD_REQUEST", "message": "condition_type must be ABOVE or BELOW"}}), 400

    try:
        target_price = Decimal(str(target_price_raw))
        if target_price <= Decimal('0'):
            raise ValueError()
    except Exception:
        return jsonify({"ok": False, "error": {"code": "BAD_REQUEST", "message": "target_price must be a positive number"}}), 400

    try:
        alert_id = AlertRepository.create(current_user.id, stock_id, target_price, condition_type)
        return jsonify({"ok": True, "data": {"alert_id": alert_id, "message": "Price alert created successfully"}}), 201
    except ValueError as ve:
        return jsonify({"ok": False, "error": {"code": "BAD_REQUEST", "message": str(ve)}}), 400

@investor_bp.route("/api/v1/investor/alerts/<int:alert_id>", methods=["DELETE"])
@role_required("INVESTOR")
def api_cancel_alert(alert_id: int):
    """Cancels or removes a price threshold alert."""
    cancelled = AlertRepository.cancel(current_user.id, alert_id)
    if not cancelled:
        deleted = AlertRepository.delete(current_user.id, alert_id)
        if not deleted:
            return jsonify({"ok": False, "error": {"code": "NOT_FOUND", "message": "Alert not found or already cancelled"}}), 404
    return jsonify({"ok": True, "data": {"alert_id": alert_id, "status": "CANCELLED"}}), 200

# ==============================================================================
# Assigned Broker & Statement Endpoints
# ==============================================================================

@investor_bp.route("/api/v1/investor/broker", methods=["GET"])
@role_required("INVESTOR")
def api_investor_broker():
    """Returns investor's assigned broker details and active commission/brokerage policy."""
    broker = BrokerRepository.get_assigned_broker_for_investor(current_user.id)
    policy = {
        "brokerage_rate": 0.0010,
        "brokerage_rate_pct": 0.10,
        "brokerage_min_fee": 1.00,
        "broker_commission_rate": 0.40,
        "broker_commission_rate_pct": 40.0,
        "description": "Standard SEBI simulated investor brokerage (0.10%, min ₹1.00 per trade). Assigned broker receives 40% platform commission."
    }
    return jsonify({"ok": True, "data": {"broker": broker, "policy": policy}}), 200

@investor_bp.route("/api/v1/investor/statement", methods=["GET"])
@role_required("INVESTOR")
def api_investor_statement():
    """Exports comprehensive transaction statement as CSV for current investor."""
    from routes.reports import export_transactions_csv
    return export_transactions_csv()

