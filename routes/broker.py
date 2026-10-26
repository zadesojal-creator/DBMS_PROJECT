"""
Broker Dashboard & Client Management Blueprint (routes/broker.py)
Provides web views and REST APIs for client onboarding, tenant isolation, and commission analytics.
"""
from decimal import Decimal
from werkzeug.security import generate_password_hash
from flask import Blueprint, render_template, request, jsonify, abort
from flask_login import current_user
from services.auth_service import role_required
from repositories.broker_repo import BrokerRepository
from repositories.stock_repo import StockRepository
from repositories.holding_repo import HoldingRepository
from repositories.transaction_repo import TransactionRepository
from repositories.account_repo import AccountRepository
from repositories.user_repo import UserRepository
from models.db import get_db_connection
from sqlalchemy import text

broker_bp = Blueprint("broker", __name__, url_prefix="/broker")

# Web Views
@broker_bp.route("/overview")
@role_required("BROKER")
def overview():
    stocks = StockRepository.get_market_overview()
    return render_template("broker/overview.html", stocks=stocks)

@broker_bp.route("/clients")
@role_required("BROKER")
def clients():
    client_list = BrokerRepository.get_clients(current_user.id)
    return render_template("broker/clients.html", clients=client_list)

@broker_bp.route("/analytics")
@role_required("BROKER")
def analytics():
    stats = BrokerRepository.get_commission_analytics(current_user.id)
    return render_template("broker/analytics.html", stats=stats)

# ==============================================================================
# REST API Endpoints (/api/v1/broker/...)
# ==============================================================================

@broker_bp.route("/api/v1/broker/clients", methods=["GET"])
@role_required("BROKER")
def api_clients():
    """Returns active clients assigned to the authenticated broker."""
    client_list = BrokerRepository.get_clients(current_user.id)
    serialized = [{
        k: float(v) if isinstance(v, Decimal) else (v.strftime("%Y-%m-%d %H:%M:%S") if hasattr(v, "strftime") else v)
        for k, v in c.items()
    } for c in client_list]
    return jsonify({"ok": True, "data": serialized}), 200

@broker_bp.route("/api/v1/broker/clients", methods=["POST"])
@role_required("BROKER")
def api_onboard_client():
    """
    Onboards a new investor client atomically:
    Creates user, account with virtual grant, and active Broker_Clients assignment.
    """
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    full_name = data.get("full_name", "").strip()
    password = data.get("password", "")
    phone = data.get("phone", "").strip()

    if not username or not email or not full_name or not password:
        return jsonify({
            "ok": False,
            "error": {"code": "BAD_REQUEST", "message": "username, email, full_name, and password are required"}
        }), 400

    if len(password) < 8:
        return jsonify({
            "ok": False,
            "error": {"code": "VALIDATION_ERROR", "message": "Password must be at least 8 characters"}
        }), 422

    pw_hash = generate_password_hash(password)
    try:
        investor_id = BrokerRepository.onboard_client(
            broker_id=current_user.id,
            username=username,
            email=email,
            full_name=full_name,
            password_hash=pw_hash,
            phone=phone if phone else None
        )
        return jsonify({
            "ok": True,
            "data": {
                "investor_id": investor_id,
                "username": username,
                "email": email,
                "message": "Investor client onboarded successfully with opening virtual grant"
            }
        }), 201
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": {"code": "ONBOARDING_FAILED", "message": str(e)}
        }), 400

@broker_bp.route("/api/v1/broker/clients/<int:investor_id>/end", methods=["POST"])
@role_required("BROKER")
def api_end_assignment(investor_id: int):
    """Ends relationship with an assigned investor (tenant isolation enforced)."""
    if not BrokerRepository.is_assigned(current_user.id, investor_id):
        return jsonify({"ok": False, "error": {"code": "NOT_FOUND", "message": "Client not found under this broker"}}), 404

    success = BrokerRepository.end_assignment(current_user.id, investor_id)
    return jsonify({"ok": True, "data": {"success": success, "message": "Client relationship ended"}}), 200

@broker_bp.route("/api/v1/broker/client-profile", methods=["GET"])
@role_required("BROKER")
def api_client_profile():
    """
    Returns full profile of an assigned investor:
    Holdings, balance, transactions, and commissions.
    Tenant isolation: Returns 404 (not 403) if client is not assigned to caller.
    """
    investor_id = request.args.get("investor_id", type=int)
    if not investor_id:
        return jsonify({"ok": False, "error": {"code": "BAD_REQUEST", "message": "investor_id is required"}}), 400

    if not BrokerRepository.is_assigned(current_user.id, investor_id):
        # Return 404 to avoid leaking existence of other brokers' clients
        return jsonify({"ok": False, "error": {"code": "NOT_FOUND", "message": "Client not found"}}), 404

    investor_user = UserRepository.get_by_id(investor_id)
    account = AccountRepository.get_by_user_id(investor_id)
    holdings = HoldingRepository.get_by_user(investor_id)
    transactions = TransactionRepository.get_by_user(investor_id, limit=20)

    # Calculate total commissions earned from this client
    with get_db_connection() as conn:
        q_comm = "SELECT COALESCE(SUM(commission_amount), 0.00) FROM Commissions WHERE broker_id = :b_id AND investor_id = :i_id"
        total_comm = conn.execute(text(q_comm), {"b_id": current_user.id, "i_id": investor_id}).scalar() or Decimal('0.00')

    return jsonify({
        "ok": True,
        "data": {
            "investor_id": investor_id,
            "virtual_balance": float(account["virtual_balance"]) if account else 0.0,
            "balance": float(account["virtual_balance"]) if account else 0.0,
            "client": {
                "id": investor_id,
                "full_name": investor_user["full_name"] if investor_user else f"Investor #{investor_id}",
                "username": investor_user["username"] if investor_user else "",
                "email": investor_user["email"] if investor_user else ""
            },
            "total_commissions": float(total_comm),
            "holdings": [{
                k: float(v) if isinstance(v, Decimal) else v for k, v in h.items()
            } for h in holdings],
            "recent_transactions": [{
                k: float(v) if isinstance(v, Decimal) else (v.strftime("%Y-%m-%d %H:%M:%S") if hasattr(v, "strftime") else v)
                for k, v in t.items()
            } for t in transactions]
        }
    }), 200

@broker_bp.route("/api/v1/broker/analytics", methods=["GET"])
@role_required("BROKER")
def api_analytics():
    """Returns platform commission statistics, monthly trend, investor-wise breakdown, and trade analysis."""
    stats = BrokerRepository.get_commission_analytics(current_user.id)
    serialized = {
        "total_commission": float(stats["total_commission"]),
        "total_commissions": float(stats["total_commission"]),
        "total_trades": stats["total_trades"],
        "today_commission": float(stats["today_commission"]),
        "this_month_commission": float(stats["this_month_commission"]),
        "monthly_trend": [{
            "month": m["month_label"],
            "trades": m["trade_count"],
            "commission": float(m["commission_earned"])
        } for m in stats["monthly_trend"]],
        "top_clients": [{
            "investor_id": c["investor_id"],
            "investor_name": c["investor_name"],
            "trades": c["trades"],
            "commission": float(c["commission_generated"])
        } for c in stats["top_clients"]],
        "investor_commissions": stats.get("investor_commissions", []),
        "trade_analysis": stats.get("trade_analysis", {})
    }
    return jsonify({"ok": True, "data": serialized}), 200
