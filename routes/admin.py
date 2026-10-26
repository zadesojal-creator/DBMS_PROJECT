"""
Admin Console Blueprint (routes/admin.py)
Provides web views and REST APIs for company CRUD, user management, and simulator controls.
"""
from decimal import Decimal
from werkzeug.security import generate_password_hash
from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from services.auth_service import role_required
from repositories.stock_repo import StockRepository
from repositories.user_repo import UserRepository
from repositories.audit_repo import AuditRepository
from sqlalchemy import text
from models.db import get_db_connection
from services.market_simulator import MarketSimulator

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# Web Views
@admin_bp.route("/overview")
@role_required("ADMIN")
def overview():
    stocks = StockRepository.get_market_overview()
    users = UserRepository.list_users()
    return render_template("admin/overview.html", stocks=stocks, users=users)

@admin_bp.route("/companies")
@role_required("ADMIN")
def companies():
    stocks = StockRepository.get_market_overview()
    return render_template("admin/companies.html", stocks=stocks)

@admin_bp.route("/users")
@role_required("ADMIN")
def users():
    user_list = UserRepository.list_users()
    return render_template("admin/users.html", users=user_list)

@admin_bp.route("/audit-logs")
@role_required("ADMIN")
def audit_logs():
    logs = AuditRepository.list_logs(limit=100)
    return render_template("admin/audit_logs.html", logs=logs)

# ==============================================================================
# REST API Endpoints (/api/v1/admin/...)
# ==============================================================================

@admin_bp.route("/api/v1/admin/companies", methods=["GET"])
@role_required("ADMIN")
def api_companies():
    sector = request.args.get("sector")
    search = request.args.get("search")
    stocks = StockRepository.get_market_overview(sector=sector, search=search)
    return jsonify({"ok": True, "data": stocks}), 200

@admin_bp.route("/api/v1/admin/companies", methods=["POST"])
@role_required("ADMIN")
def api_create_company():
    data = request.get_json(silent=True) or {}
    symbol = data.get("symbol", "").strip().upper()
    company_name = data.get("company_name", "").strip()
    sector = data.get("sector", "").strip()
    exchange = data.get("exchange", "NSE").strip().upper()
    ref_price_raw = data.get("reference_price", 100.0)

    if not symbol or not company_name or not sector:
        return jsonify({"ok": False, "error": {"code": "BAD_REQUEST", "message": "symbol, company_name, and sector are required"}}), 400

    existing = StockRepository.get_by_symbol(symbol)
    if existing:
        return jsonify({"ok": False, "error": {"code": "DUPLICATE_SYMBOL", "message": f"Company with symbol {symbol} already exists"}}), 409

    try:
        ref_price = Decimal(str(ref_price_raw))
        stock_id = StockRepository.create_stock(symbol, company_name, sector, exchange, ref_price)
        AuditRepository.log(current_user.id, 'CREATE_STOCK', 'STOCK', str(stock_id), {"symbol": symbol, "name": company_name})
        return jsonify({
            "ok": True,
            "data": {"stock_id": stock_id, "symbol": symbol, "message": "Company created successfully"}
        }), 201
    except Exception as e:
        return jsonify({"ok": False, "error": {"code": "CREATE_FAILED", "message": str(e)}}), 400

@admin_bp.route("/api/v1/admin/companies/<int:stock_id>", methods=["PUT"])
@role_required("ADMIN")
def api_update_company(stock_id: int):
    stock = StockRepository.get_by_id(stock_id)
    if not stock:
        return jsonify({"ok": False, "error": {"code": "NOT_FOUND", "message": "Stock not found"}}), 404

    data = request.get_json(silent=True) or {}
    company_name = data.get("company_name", stock["company_name"])
    sector = data.get("sector", stock["sector"])
    status = data.get("status", stock["status"])

    try:
        StockRepository.update_stock(stock_id, company_name, sector, status)
        AuditRepository.log(current_user.id, 'UPDATE_STOCK', 'STOCK', str(stock_id), {"status": status})
        return jsonify({"ok": True, "data": {"message": "Company updated successfully"}}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": {"code": "UPDATE_FAILED", "message": str(e)}}), 400

@admin_bp.route("/api/v1/admin/companies/<int:stock_id>", methods=["DELETE"])
@role_required("ADMIN")
def api_delete_company(stock_id: int):
    stock = StockRepository.get_by_id(stock_id)
    if not stock:
        return jsonify({"ok": False, "error": {"code": "NOT_FOUND", "message": "Stock not found"}}), 404

    try:
        StockRepository.hard_delete_stock(stock_id)
        AuditRepository.log(current_user.id, 'DELETE_STOCK', 'STOCK', str(stock_id), {"symbol": stock["symbol"]})
        return jsonify({"ok": True, "data": {"message": "Stock hard-deleted successfully"}}), 200
    except ValueError as ve:
        return jsonify({"ok": False, "error": {"code": "DELETE_BLOCKED", "message": str(ve)}}), 409

@admin_bp.route("/api/v1/admin/users", methods=["GET"])
@role_required("ADMIN")
def api_users():
    role = request.args.get("role")
    status = request.args.get("status")
    users = UserRepository.list_users(role=role, status=status)
    serialized = [{
        k: (v.strftime("%Y-%m-%d %H:%M:%S") if hasattr(v, "strftime") else v)
        for k, v in u.items()
    } for u in users]
    return jsonify({"ok": True, "data": serialized}), 200

@admin_bp.route("/api/v1/admin/users/<int:user_id>/status", methods=["PUT"])
@role_required("ADMIN")
def api_update_user_status(user_id: int):
    data = request.get_json(silent=True) or {}
    status = data.get("status", "").strip().upper()
    if status not in ("ACTIVE", "INACTIVE"):
        return jsonify({"ok": False, "error": {"code": "BAD_REQUEST", "message": "Status must be ACTIVE or INACTIVE"}}), 400

    UserRepository.update_status(user_id, status)
    AuditRepository.log(current_user.id, 'UPDATE_USER_STATUS', 'USER', str(user_id), {"new_status": status})
    return jsonify({"ok": True, "data": {"message": f"User status set to {status}"}}), 200

@admin_bp.route("/api/v1/admin/overview", methods=["GET"])
@role_required("ADMIN")
def api_overview():
    with get_db_connection() as conn:
        users_count = conn.execute(text("SELECT COUNT(*) FROM Users")).scalar() or 0
        stocks_count = conn.execute(text("SELECT COUNT(*) FROM Stocks WHERE status = 'ACTIVE'")).scalar() or 0
        orders_count = conn.execute(text("SELECT COUNT(*) FROM Orders")).scalar() or 0
        capital = conn.execute(text("SELECT COALESCE(SUM(virtual_balance), 0) FROM Accounts")).scalar() or Decimal('0.00')

    return jsonify({
        "ok": True,
        "data": {
            "total_users": users_count,
            "total_stocks": stocks_count,
            "total_orders": orders_count,
            "total_capital": float(capital)
        }
    }), 200

@admin_bp.route("/api/v1/admin/simulator", methods=["GET"])
@admin_bp.route("/api/v1/admin/simulator/status", methods=["GET"])
@role_required("ADMIN")
def api_simulator_status():
    sim = MarketSimulator.get_instance()
    return jsonify({"ok": True, "data": sim.get_status()}), 200

@admin_bp.route("/api/v1/admin/simulator/control", methods=["POST"])
@role_required("ADMIN")
def api_simulator_control():
    data = request.get_json(silent=True) or {}
    action = data.get("action", "")
    sim = MarketSimulator.get_instance()
    if action == "pause":
        sim.pause()
    elif action == "resume":
        sim.resume()
    elif action == "tick":
        sim.tick()
    return jsonify({"ok": True, "data": sim.get_status()}), 200

@admin_bp.route("/api/v1/admin/users/<int:user_id>/reset-lockout", methods=["POST"])
@role_required("ADMIN")
def api_reset_lockout(user_id: int):
    UserRepository.reset_failed_logins(user_id)
    AuditRepository.log(current_user.id, 'RESET_LOCKOUT', 'USER', str(user_id), {})
    return jsonify({"ok": True, "data": {"message": "Lockout reset successfully"}}), 200

@admin_bp.route("/api/v1/admin/simulator/pause", methods=["POST"])
@role_required("ADMIN")
def api_simulator_pause():
    sim = MarketSimulator.get_instance()
    sim.pause()
    return jsonify({"ok": True, "data": sim.get_status()}), 200

@admin_bp.route("/api/v1/admin/simulator/resume", methods=["POST"])
@role_required("ADMIN")
def api_simulator_resume():
    sim = MarketSimulator.get_instance()
    sim.resume()
    return jsonify({"ok": True, "data": sim.get_status()}), 200

@admin_bp.route("/api/v1/admin/audit-logs", methods=["GET"])
@role_required("ADMIN")
def api_audit_logs():
    limit = request.args.get("limit", 100, type=int)
    action = request.args.get("action")
    logs = AuditRepository.list_logs(limit=limit, action=action)
    serialized = [{
        k: (v.strftime("%Y-%m-%d %H:%M:%S") if hasattr(v, "strftime") else v)
        for k, v in log.items()
    } for log in logs]
    return jsonify({"ok": True, "data": serialized}), 200

@admin_bp.route("/api/v1/admin/commission-rules", methods=["GET"])
@role_required("ADMIN")
def api_get_commission_rules():
    """Returns active and historical brokerage and commission rules."""
    with get_db_connection() as conn:
        rows = conn.execute(text("""
            SELECT id, rule_type, rate, min_fee, effective_from, is_active, created_at
            FROM Commission_Rules
            ORDER BY is_active DESC, effective_from DESC
        """)).mappings().all()
        serialized = [{
            "id": r["id"],
            "rule_type": r["rule_type"],
            "rate": float(r["rate"]),
            "rate_pct": float(r["rate"] * 100),
            "min_fee": float(r["min_fee"]),
            "effective_from": r["effective_from"].strftime("%Y-%m-%d %H:%M:%S") if r["effective_from"] else None,
            "is_active": bool(r["is_active"])
        } for r in rows]
    return jsonify({"ok": True, "data": serialized}), 200

@admin_bp.route("/api/v1/admin/commission-rules", methods=["POST"])
@role_required("ADMIN")
def api_update_commission_rule():
    """Updates or activates a new brokerage policy rule."""
    data = request.get_json(silent=True) or {}
    rule_type = data.get("rule_type")
    rate_raw = data.get("rate")
    min_fee_raw = data.get("min_fee", 0.0)

    if rule_type not in ("INVESTOR_BROKERAGE", "BROKER_COMMISSION"):
        return jsonify({"ok": False, "error": {"code": "BAD_REQUEST", "message": "Invalid rule_type"}}), 400

    try:
        rate = Decimal(str(rate_raw))
        min_fee = Decimal(str(min_fee_raw))
    except Exception:
        return jsonify({"ok": False, "error": {"code": "BAD_REQUEST", "message": "Numeric rate and min_fee required"}}), 400

    if rate < Decimal('0') or rate > Decimal('1'):
        return jsonify({"ok": False, "error": {"code": "BAD_REQUEST", "message": "Rate must be between 0 and 1"}}), 400
    if min_fee < Decimal('0'):
        return jsonify({"ok": False, "error": {"code": "BAD_REQUEST", "message": "min_fee must be non-negative"}}), 400

    with get_db_connection() as conn:
        # Deactivate old rules of same type
        conn.execute(text("UPDATE Commission_Rules SET is_active = FALSE WHERE rule_type = :rtype"), {"rtype": rule_type})
        # Insert new active rule
        conn.execute(text("""
            INSERT INTO Commission_Rules (rule_type, rate, min_fee, effective_from, is_active)
            VALUES (:rtype, :rate, :min_fee, CURRENT_TIMESTAMP, TRUE)
        """), {"rtype": rule_type, "rate": rate, "min_fee": min_fee})
        conn.commit()

    AuditRepository.log(current_user.id, 'UPDATE_COMMISSION_RULE', 'POLICY', rule_type, {
        "rate": float(rate), "min_fee": float(min_fee)
    })
    return jsonify({"ok": True, "data": {"message": f"Rule {rule_type} updated successfully"}}), 200

@admin_bp.route("/api/v1/admin/reconciliation", methods=["GET"])
@role_required("ADMIN")
def api_reconciliation():
    """
    Executes system-wide financial integrity audit across all 7 core financial invariants:
    1. Operational cash vs. signed ledger sum
    2. Share holdings vs. net executed buy/sell volume
    3. Executed orders without transactions
    4. Transactions without ledger entries
    5. Commissions vs. active brokerage rules
    6. Duplicate transactions / commissions / idempotency keys
    7. Opening virtual cash grants (₹1,00,000 baseline)
    """
    from services.reconciliation_service import ReconciliationService
    report = ReconciliationService.run_full_reconciliation()
    return jsonify({"ok": True, "data": report}), 200


