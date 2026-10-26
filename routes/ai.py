"""
AI SQL Assistant Blueprint (routes/ai.py)
Provides natural language to SQL generation, AST validation, and read-only execution.
"""
import json
import re
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from models.db import get_db_connection
from services.auth_service import role_required
from services.llm_router import LLMRouter
from services.rag_service import RAGService
from services.sql_validator import SQLValidator
from services.query_executor import QueryExecutor
from services.intent_service import IntentService
from services.semantic_validator import SemanticValidator

ai_bp = Blueprint("ai", __name__, url_prefix="/ai")

@ai_bp.route("/assistant")
@login_required
def assistant():
    return render_template("ai/assistant.html", user=current_user)

# ==============================================================================
# REST API Endpoints (/api/v1/ai/...)
# ==============================================================================

@ai_bp.route("/api/v1/ai/generate", methods=["POST"])
@login_required
def api_generate():
    """
    Stage 1: Retrieve RAG context & generate structured SQL via LLM Router or Semantic Intent Fallback.
    Returns {sql, tables, explanation, validation_status, provider}.
    """
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "").strip()

    if not prompt:
        return jsonify({"ok": False, "error": {"code": "BAD_REQUEST", "message": "Prompt is required"}}), 400

    role = current_user.role

    # Step 1: Resolve grounded intent
    intent = IntentService.get_instance().resolve_intent(prompt, role)
    if not intent.is_supported:
        QueryExecutor.log_query_history(
            user_id=current_user.id,
            prompt=prompt,
            sql=None,
            tables_used=[],
            validation_status="REJECTED",
            execution_status="SKIPPED",
            error_code="UNSUPPORTED_DOMAIN",
            provider="INTENT_GUARD"
        )
        return jsonify({
            "ok": True,
            "data": {
                "sql": "-- Request outside supported database domain",
                "tables": [],
                "explanation": intent.clarification_message or intent.explanation or "Subject not in database.",
                "validation_status": "REJECTED",
                "provider": "INTENT_GUARD",
                "attempts": []
            }
        }), 200

    rag_context = RAGService.get_context_for_role(role, prompt, intent=intent)

    messages = [
        {
            "role": "system",
            "content": f"""You are a read-only SQL generator for a financial database.
{rag_context}

RULES:
1. Return STRICT JSON with keys: "sql", "tables", "explanation".
2. Use ONLY the allowed views for {role}.
3. Root statement MUST be a SELECT. No INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE.
4. For Investor queries on holdings/transactions, ALWAYS include `WHERE user_id = @current_user_id`.
5. For Broker queries on clients/commissions, ALWAYS include `WHERE broker_id = @current_user_id`.
6. For Admin queries, use system-wide views (e.g. `v_admin_user_audit` for accounts/failed logins, `v_admin_audit_logs` for security logs, `v_admin_trade_facts` for trade turnover, `v_market_latest` for equities).
7. If the user asks about a specific sector (e.g. Banking, Chemicals, Logistics), you MUST include `WHERE sector = '...'`.
8. Enforce a LIMIT 500 max, but do NOT arbitrarily add `LIMIT 10` if the user asked for all records.
9. Do not wrap in markdown backticks. Return raw JSON object.
"""
        },
        {"role": "user", "content": prompt}
    ]

    router = LLMRouter.get_instance()
    completion = router.complete(messages, json_mode=True)
    provider_used = completion["provider_used"]
    content = completion.get("content")

    sql_obj = None
    if content:
        try:
            cleaned = re.sub(r'^```json\s*|\s*```$', '', content.strip(), flags=re.MULTILINE)
            sql_obj = json.loads(cleaned)
        except Exception:
            pass

    use_fallback = False
    fallback_reason = None

    if not sql_obj or "sql" not in sql_obj:
        use_fallback = True
        fallback_reason = "NO_LLM_OUTPUT"
    else:
        # Check AST safety
        raw_sql = sql_obj.get("sql", "")
        is_safe, sanitized_sql, ast_err, tables_used = SQLValidator.validate_sql(raw_sql, role)
        if not is_safe:
            use_fallback = True
            fallback_reason = f"AST_SAFETY: {ast_err}"
        else:
            # Check Semantic Consistency
            is_sem_ok, sem_code, sem_err = SemanticValidator.validate_consistency(prompt, intent, sanitized_sql, role)
            if not is_sem_ok:
                use_fallback = True
                fallback_reason = f"SEMANTIC_MISMATCH: {sem_err}"

    if use_fallback:
        sql_obj = SemanticValidator.get_corrected_or_fallback_sql(prompt, intent, role, reason=fallback_reason)
        is_safe, sanitized_sql, ast_err, tables_used = SQLValidator.validate_sql(sql_obj["sql"], role)
        if fallback_reason == "NO_LLM_OUTPUT":
            provider_used = "TEMPLATE_FALLBACK"
        else:
            provider_used = f"{provider_used} (Semantic Guard: {fallback_reason})"

    return jsonify({
        "ok": True,
        "data": {
            "sql": sanitized_sql,
            "tables": tables_used,
            "explanation": sql_obj.get("explanation", "Generated query"),
            "validation_status": "VALID",
            "provider": provider_used,
            "attempts": completion.get("attempts", [])
        }
    }), 200

@ai_bp.route("/api/v1/ai/execute", methods=["POST"])
@login_required
def api_execute():
    """
    Stage 3: Explicit execution of validated SQL under stocktrade_ai_ro with session tenancy.
    Used for Manual SQL mode as well as direct validated SQL execution.
    """
    data = request.get_json(silent=True) or {}
    raw_sql = data.get("sql", "").strip()
    prompt = data.get("prompt", "")
    provider = data.get("provider", "MANUAL_SQL")

    if not raw_sql:
        return jsonify({"ok": False, "error": {"code": "BAD_REQUEST", "message": "SQL query is required"}}), 400

    # Re-validate immediately before execution using AST allowlist and tenant derivation
    is_valid, sanitized_sql, val_err, tables_used = SQLValidator.validate_sql(raw_sql, current_user.role)
    if not is_valid:
        # Audit log the rejected query attempt
        QueryExecutor.log_query_history(
            user_id=current_user.id,
            prompt=prompt or "Manual SQL Query",
            sql=raw_sql,
            tables_used=[],
            validation_status="REJECTED",
            execution_status="SKIPPED",
            error_code=val_err[:64] if val_err else "VALIDATION_FAILED",
            provider=provider
        )
        return jsonify({"ok": False, "error": {"code": "VALIDATION_FAILED", "message": val_err}}), 422

    # Execute under stocktrade_ai_ro with parameterized tenant scoping
    result = QueryExecutor.execute_scoped_query(
        user_id=current_user.id,
        role=current_user.role,
        sql=sanitized_sql,
        prompt=prompt or "Manual SQL Query",
        provider=provider,
        tables_used=tables_used
    )

    if not result.get("ok"):
        return jsonify({
            "ok": False,
            "error": {"code": "EXECUTION_ERROR", "message": result.get("error")},
            "data": {
                "duration_ms": result.get("duration_ms", 0),
                "executed_sql": sanitized_sql
            }
        }), 500

    return jsonify({
        "ok": True,
        "data": {
            "executed_sql": sanitized_sql,
            "columns": result.get("columns", []),
            "rows": result.get("rows", []),
            "results": result.get("rows", []),
            "row_count": result.get("row_count", 0),
            "duration_ms": result.get("duration_ms", 0),
            "summary": result.get("summary", ""),
            "explanation": result.get("explanation", ""),
            "key_metrics": result.get("key_metrics", []),
            "tables_used": tables_used,
            "ast_validated": True,
            "provider": provider
        }
    }), 200

@ai_bp.route("/api/v1/ai/query", methods=["POST"])
@login_required
def api_query():
    """Combined generate + execute endpoint for UI Assistant."""
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"ok": False, "error": {"code": "BAD_REQUEST", "message": "Prompt is required"}}), 400

    role = current_user.role

    # Step 1: Resolve grounded intent
    intent = IntentService.get_instance().resolve_intent(prompt, role)
    if not intent.is_supported:
        QueryExecutor.log_query_history(
            user_id=current_user.id,
            prompt=prompt,
            sql=None,
            tables_used=[],
            validation_status="REJECTED",
            execution_status="SKIPPED",
            error_code="UNSUPPORTED_DOMAIN",
            provider="INTENT_GUARD"
        )
        return jsonify({
            "ok": True,
            "data": {
                "generated_sql": "-- Request outside supported database domain",
                "executed_sql": "-- Request outside supported database domain",
                "provider_used": "INTENT_GUARD",
                "ast_validated": False,
                "columns": [],
                "results": [],
                "rows": [],
                "row_count": 0,
                "duration_ms": 0,
                "summary": intent.clarification_message or intent.explanation or "Request is outside the supported database schema.",
                "explanation": intent.explanation or "The StockTrade database manages equities, market prices, investor portfolios, broker commissions, and security audit logs.",
                "key_metrics": [{"label": "Status", "value": "Unsupported Domain"}],
                "tables_used": []
            }
        }), 200

    rag_context = RAGService.get_context_for_role(role, prompt, intent=intent)
    messages = [
        {
            "role": "system",
            "content": f"""You are a read-only SQL generator for a financial database.
{rag_context}

RULES:
1. Return STRICT JSON with keys: "sql", "tables", "explanation".
2. Use ONLY the allowed views for {role}.
3. Root statement MUST be a SELECT. No INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE.
4. For Investor queries on holdings/transactions, ALWAYS include `WHERE user_id = @current_user_id`.
5. For Broker queries on clients/commissions, ALWAYS include `WHERE broker_id = @current_user_id`.
6. For Admin queries, use system-wide views (e.g. `v_admin_user_audit` for accounts/failed logins, `v_admin_audit_logs` for security logs, `v_admin_trade_facts` for trade turnover, `v_market_latest` for equities).
7. If the user asks about a specific sector (e.g. Banking, Chemicals, Logistics), you MUST include `WHERE sector = '...'`.
8. Enforce a LIMIT 500 max, but do NOT arbitrarily add `LIMIT 10` if the user asked for all records.
9. Do not wrap in markdown backticks. Return raw JSON object.
"""
        },
        {"role": "user", "content": prompt}
    ]

    router = LLMRouter.get_instance()
    completion = router.complete(messages, json_mode=True)
    content = completion.get("content")
    provider_used = completion.get("provider_used", "TEMPLATE_FALLBACK")

    sql_obj = None
    if content:
        try:
            cleaned = re.sub(r'^```json\s*|\s*```$', '', content.strip(), flags=re.MULTILINE)
            sql_obj = json.loads(cleaned)
        except Exception:
            pass

    use_fallback = False
    fallback_reason = None

    if not sql_obj or "sql" not in sql_obj:
        use_fallback = True
        fallback_reason = "NO_LLM_OUTPUT"
    else:
        # Check AST safety
        raw_sql = sql_obj.get("sql", "")
        is_safe, sanitized_sql, ast_err, tables_used = SQLValidator.validate_sql(raw_sql, role)
        if not is_safe:
            use_fallback = True
            fallback_reason = f"AST_SAFETY: {ast_err}"
        else:
            # Check Semantic Consistency
            is_sem_ok, sem_code, sem_err = SemanticValidator.validate_consistency(prompt, intent, sanitized_sql, role)
            if not is_sem_ok:
                use_fallback = True
                fallback_reason = f"SEMANTIC_MISMATCH: {sem_err}"

    if use_fallback:
        sql_obj = SemanticValidator.get_corrected_or_fallback_sql(prompt, intent, role, reason=fallback_reason)
        is_safe, sanitized_sql, ast_err, tables_used = SQLValidator.validate_sql(sql_obj["sql"], role)
        if fallback_reason == "NO_LLM_OUTPUT":
            provider_used = "TEMPLATE_FALLBACK"
        else:
            provider_used = f"{provider_used} (Semantic Guard: {fallback_reason})"

    result = QueryExecutor.execute_scoped_query(
        user_id=current_user.id,
        role=role,
        sql=sanitized_sql,
        prompt=prompt,
        provider=provider_used,
        tables_used=tables_used
    )

    if not result.get("ok"):
        return jsonify({"ok": False, "error": {"code": "EXECUTION_ERROR", "message": result.get("error")}}), 500

    return jsonify({
        "ok": True,
        "data": {
            "generated_sql": sanitized_sql,
            "executed_sql": sanitized_sql,
            "provider_used": provider_used,
            "ast_validated": is_safe,
            "columns": result.get("columns", []),
            "results": result.get("rows", []),
            "rows": result.get("rows", []),
            "row_count": result.get("row_count", 0),
            "duration_ms": result.get("duration_ms", 0),
            "summary": result.get("summary", "Query executed successfully."),
            "explanation": sql_obj.get("explanation") or result.get("explanation", ""),
            "key_metrics": result.get("key_metrics", []),
            "tables_used": tables_used
        }
    }), 200

@ai_bp.route("/api/v1/ai/history", methods=["GET"])
@login_required
def api_history():
    """Returns recent AI query audit history for the authenticated user."""
    limit = min(request.args.get("limit", default=20, type=int), 100)
    with get_db_connection() as conn:
        rows = conn.execute(
            text("""
                SELECT id, prompt, generated_sql, validation_status, execution_status,
                       error_code, duration_ms, row_count, provider, created_at
                FROM AI_Query_History
                WHERE user_id = :uid
                ORDER BY created_at DESC, id DESC
                LIMIT :lim
            """),
            {"uid": current_user.id, "lim": limit}
        ).mappings().all()

        data = [
            {
                "id": r["id"],
                "prompt": r["prompt"],
                "generated_sql": r["generated_sql"],
                "validation_status": r["validation_status"],
                "execution_status": r["execution_status"],
                "error_code": r["error_code"],
                "duration_ms": r["duration_ms"],
                "row_count": r["row_count"],
                "provider": r["provider"],
                "created_at": r["created_at"].strftime("%Y-%m-%d %H:%M:%S") if r["created_at"] else None
            }
            for r in rows
        ]
    return jsonify({"ok": True, "data": data}), 200

@ai_bp.route("/api/v1/ai/schema", methods=["GET"])
@login_required
def api_schema():
    """Returns role-specific allowed views, columns, and sample queries for the Manual SQL editor."""
    role = current_user.role
    schemas = {
        "INVESTOR": [
            {
                "view": "v_investor_portfolio",
                "description": "Your current holdings, cost basis, live market values, and unrealized returns.",
                "columns": ["symbol", "company_name", "sector", "quantity", "avg_cost", "cost_basis", "current_price", "market_value", "unrealized_pnl", "return_pct", "day_change_pct"],
                "sample": "SELECT symbol, quantity, avg_cost, current_price, market_value, unrealized_pnl FROM v_investor_portfolio ORDER BY market_value DESC;"
            },
            {
                "view": "v_investor_transactions",
                "description": "Your executed trade transactions, prices, quantities, and brokerage fees.",
                "columns": ["transaction_id", "symbol", "company_name", "sector", "side", "quantity", "execution_price", "gross_amount", "brokerage_fee", "net_amount", "realized_pnl", "executed_at"],
                "sample": "SELECT symbol, side, quantity, execution_price, gross_amount, brokerage_fee, executed_at FROM v_investor_transactions ORDER BY executed_at DESC LIMIT 10;"
            },
            {
                "view": "v_market_latest",
                "description": "Real-time quotes, sector, previous close, day change, day high/low, and trading volume for all 100 equities.",
                "columns": ["stock_id", "symbol", "company_name", "sector", "exchange", "current_price", "previous_close", "day_change", "day_change_pct", "day_high", "day_low", "volume"],
                "sample": "SELECT symbol, company_name, sector, current_price, day_change_pct, volume FROM v_market_latest ORDER BY day_change_pct DESC LIMIT 10;"
            }
        ],
        "BROKER": [
            {
                "view": "v_broker_client_summary",
                "description": "Summary of active clients, cash balances, trade counts, and commissions.",
                "columns": ["investor_id", "investor_name", "investor_email", "investor_status", "assigned_at", "virtual_balance", "total_trades", "total_volume", "total_commission_generated"],
                "sample": "SELECT investor_name, virtual_balance, total_trades, total_commission_generated FROM v_broker_client_summary ORDER BY total_commission_generated DESC;"
            },
            {
                "view": "v_broker_client_transactions",
                "description": "All trade transactions executed by your assigned clients.",
                "columns": ["transaction_id", "investor_id", "investor_name", "symbol", "company_name", "side", "quantity", "execution_price", "gross_amount", "brokerage_fee", "broker_commission_earned", "executed_at"],
                "sample": "SELECT investor_name, symbol, side, quantity, execution_price, broker_commission_earned, executed_at FROM v_broker_client_transactions ORDER BY executed_at DESC LIMIT 15;"
            },
            {
                "view": "v_broker_commissions",
                "description": "Breakdown of individual commission payouts generated from client trades.",
                "columns": ["commission_id", "transaction_id", "investor_id", "investor_name", "symbol", "side", "quantity", "base_brokerage", "rate_applied", "commission_amount", "created_at"],
                "sample": "SELECT investor_name, symbol, base_brokerage, rate_applied, commission_amount, created_at FROM v_broker_commissions ORDER BY created_at DESC LIMIT 10;"
            },
            {
                "view": "v_market_latest",
                "description": "Real-time market quotes and volume.",
                "columns": ["stock_id", "symbol", "company_name", "sector", "current_price", "day_change_pct", "volume"],
                "sample": "SELECT symbol, current_price, day_change_pct, volume FROM v_market_latest ORDER BY current_price DESC LIMIT 10;"
            }
        ],
        "ADMIN": [
            {
                "view": "v_admin_user_audit",
                "description": "User accounts, roles, statuses, failed login attempt counters, and lockout expiry timestamps.",
                "columns": ["user_id", "username", "email", "full_name", "role", "status", "failed_login_attempts", "locked_until", "last_login_at", "created_at"],
                "sample": "SELECT username, role, status, failed_login_attempts, locked_until FROM v_admin_user_audit WHERE failed_login_attempts > 0 OR locked_until IS NOT NULL;"
            },
            {
                "view": "v_admin_audit_logs",
                "description": "Security audit logs, failed login events, security lockouts, and administrative action trail.",
                "columns": ["log_id", "user_id", "username", "role", "action", "entity_type", "entity_id", "ip_address", "created_at"],
                "sample": "SELECT username, role, action, ip_address, created_at FROM v_admin_audit_logs WHERE action IN ('LOGIN_FAILED', 'SECURITY_LOCKOUT') ORDER BY created_at DESC LIMIT 20;"
            },
            {
                "view": "v_admin_trade_facts",
                "description": "Platform-wide transaction history with investor and broker attributions.",
                "columns": ["transaction_id", "executed_at", "side", "quantity", "execution_price", "gross_amount", "brokerage_fee", "investor_id", "investor_name", "symbol", "sector", "broker_id", "broker_commission"],
                "sample": "SELECT sector, COUNT(*) AS trade_count, SUM(gross_amount) AS total_volume, SUM(brokerage_fee) AS total_fees FROM v_admin_trade_facts GROUP BY sector ORDER BY total_volume DESC;"
            },
            {
                "view": "v_market_latest",
                "description": "Real-time prices, volume, and sector classifications for all listed equities.",
                "columns": ["stock_id", "symbol", "company_name", "sector", "current_price", "previous_close", "day_change_pct", "volume"],
                "sample": "SELECT sector, COUNT(*) AS stock_count, ROUND(AVG(current_price), 2) AS avg_price FROM v_market_latest GROUP BY sector ORDER BY stock_count DESC;"
            },
            {
                "view": "stocks",
                "description": "Master catalog of listed companies on the exchange.",
                "columns": ["id", "symbol", "company_name", "sector", "exchange", "status", "created_at"],
                "sample": "SELECT sector, status, COUNT(*) AS total FROM stocks GROUP BY sector, status;"
            },
            {
                "view": "commission_rules",
                "description": "Configured investor brokerage and broker commission rates.",
                "columns": ["id", "rule_type", "rate", "min_fee", "effective_from", "is_active"],
                "sample": "SELECT rule_type, rate, min_fee, is_active FROM commission_rules WHERE is_active = TRUE;"
            }
        ]
    }
    return jsonify({
        "ok": True,
        "data": {
            "role": role,
            "allowed_views": schemas.get(role, [])
        }
    }), 200

@ai_bp.route("/api/v1/ai/providers", methods=["GET"])
@role_required("ADMIN")
def api_providers():
    """Returns AI provider statuses for Admin console."""
    router = LLMRouter.get_instance()
    return jsonify({"ok": True, "data": router.get_provider_status()}), 200

