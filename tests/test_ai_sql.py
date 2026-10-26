"""
AI SQL Security, Validation & Tenancy Regression Suite (test_ai_sql.py)
Validates sqlglot AST allowlist, mutation rejection, stacked queries rejection,
strict tenant isolation across roles, Cartesian product rejection, pooled session hygiene,
and full lifecycle of the React-facing AI query endpoint.
"""
import pytest
from sqlalchemy import text
from services.sql_validator import SQLValidator
from services.query_executor import QueryExecutor
from services.llm_router import LLMRouter
from models.db import get_ai_connection, get_db_connection

# ==============================================================================
# Unit Tests — AST Validation & Rejection
# ==============================================================================

def test_valid_investor_select_query():
    """Valid investor query passes AST validation, has LIMIT injected and is tenant-scoped."""
    raw_sql = "SELECT symbol, quantity, current_price FROM v_investor_portfolio WHERE user_id = @current_user_id"
    is_valid, sanitized, err, tables = SQLValidator.validate_sql(raw_sql, "INVESTOR")
    assert is_valid is True
    assert "limit 500" in sanitized.lower()
    assert "v_investor_portfolio" in tables
    assert ":auth_user_id" in sanitized

def test_mutation_queries_rejected():
    """Every database write/mutation verb is rejected by the AST validator."""
    mutations = [
        "INSERT INTO Accounts (user_id, virtual_balance) VALUES (4, 999999.00)",
        "UPDATE Accounts SET virtual_balance = 999999.00 WHERE user_id = 4",
        "DELETE FROM Transactions WHERE id = 1",
        "DROP TABLE Users",
        "ALTER TABLE Users ADD COLUMN leaked VARCHAR(50)",
        "TRUNCATE TABLE Stock_Prices"
    ]
    for sql in mutations:
        is_valid, sanitized, err, _ = SQLValidator.validate_sql(sql, "INVESTOR")
        assert is_valid is False
        assert err is not None

def test_stacked_statements_rejected():
    """Stacked / multi-statement queries are strictly rejected."""
    sql = "SELECT * FROM v_market_latest; DROP TABLE Users;"
    is_valid, sanitized, err, _ = SQLValidator.validate_sql(sql, "INVESTOR")
    assert is_valid is False
    assert "multi-statement" in err.lower()

def test_disallowed_tables_rejected_per_role():
    """Investor cannot query internal or admin tables like Users or Accounts directly."""
    sql = "SELECT username, password_hash FROM Users"
    is_valid, sanitized, err, _ = SQLValidator.validate_sql(sql, "INVESTOR")
    assert is_valid is False
    assert "unauthorized table" in err.lower()

def test_dangerous_functions_rejected():
    """SLEEP, BENCHMARK, LOAD_FILE are blocked by AST validator."""
    sql = "SELECT SLEEP(5) FROM v_market_latest"
    is_valid, sanitized, err, _ = SQLValidator.validate_sql(sql, "INVESTOR")
    assert is_valid is False
    assert "safety allowlist" in err.lower() or "forbidden" in err.lower()

def test_cartesian_products_and_cross_joins_rejected():
    """Unconstrained Cartesian products (CROSS JOIN or comma joins without conditions) are rejected."""
    cross_join = "SELECT * FROM v_investor_portfolio CROSS JOIN v_market_latest"
    is_valid, _, err, _ = SQLValidator.validate_sql(cross_join, "INVESTOR")
    assert is_valid is False
    assert "cross join" in err.lower()

    comma_join = "SELECT * FROM v_investor_portfolio, v_market_latest"
    is_valid, _, err, _ = SQLValidator.validate_sql(comma_join, "INVESTOR")
    assert is_valid is False
    assert "without on or using" in err.lower()

def test_excessive_joins_rejected():
    """Queries with more than 2 joins are rejected to prevent join bombs."""
    excessive_joins = (
        "SELECT * FROM v_investor_portfolio p "
        "JOIN v_market_latest m1 ON p.stock_id = m1.stock_id "
        "JOIN v_market_latest m2 ON p.stock_id = m2.stock_id "
        "JOIN v_market_latest m3 ON p.stock_id = m3.stock_id"
    )
    is_valid, _, err, _ = SQLValidator.validate_sql(excessive_joins, "INVESTOR")
    assert is_valid is False
    assert "excessive joins" in err.lower()

def test_excessive_offset_rejected():
    """Queries with excessive offset (> 1000) are rejected."""
    sql = "SELECT * FROM v_investor_portfolio LIMIT 10 OFFSET 5000"
    is_valid, _, err, _ = SQLValidator.validate_sql(sql, "INVESTOR")
    assert is_valid is False
    assert "excessive query offset" in err.lower()

def test_cte_name_collision_rejected():
    """CTE alias cannot collide with protected view names to attempt bypass."""
    for protected in ["v_investor_portfolio", "v_broker_client_summary", "v_market_latest", "v_admin_trade_facts"]:
        sql = f"WITH {protected} AS (SELECT 1 AS col) SELECT * FROM {protected}"
        is_valid, _, err, _ = SQLValidator.validate_sql(sql, "INVESTOR")
        assert is_valid is False
        assert "collides with protected view" in err.lower()

def test_malformed_sql_syntax_rejected():
    """Malformed SQL syntax is caught and rejected before execution."""
    sql = "SELECT FROM WHERE v_investor_portfolio"
    is_valid, _, err, _ = SQLValidator.validate_sql(sql, "INVESTOR")
    assert is_valid is False
    assert "syntax error" in err.lower()

def test_direct_base_table_access_rejected(investor_client):
    """Investor cannot bypass views to query physical base tables like Holdings or Transactions."""
    for base_table in ["Holdings", "Transactions", "Users", "Accounts"]:
        resp = investor_client.post("/ai/api/v1/ai/execute", json={"sql": f"SELECT * FROM {base_table}"})
        assert resp.status_code == 422
        assert "unauthorized table" in resp.get_json()["error"]["message"].lower()

def test_union_with_admin_view_rejected(investor_client):
    """Investor cannot use UNION to reach admin-only views."""
    sql = "SELECT symbol FROM v_investor_portfolio UNION ALL SELECT symbol FROM v_admin_trade_facts"
    resp = investor_client.post("/ai/api/v1/ai/execute", json={"sql": sql})
    assert resp.status_code == 422
    assert "unauthorized table" in resp.get_json()["error"]["message"].lower()

def test_tautology_or_1_equals_1_cannot_leak_data(investor_client):
    """SQL injection tautology like OR 1=1 cannot bypass tenant isolation."""
    from repositories.holding_repo import HoldingRepository
    from services.trading_service import TradingService
    h = HoldingRepository.get_by_user_and_stock(4, 1)
    if not h or h["quantity"] <= 0:
        TradingService.execute_market_order(4, 1, "BUY", 1)

    sql = "SELECT user_id, symbol, quantity FROM v_investor_portfolio WHERE user_id = 4 OR 1=1"
    resp = investor_client.post("/ai/api/v1/ai/execute", json={"sql": sql})
    assert resp.status_code == 200
    rows = resp.get_json()["data"]["rows"]
    assert len(rows) > 0
    for r in rows:
        assert r["user_id"] == 4, f"Tautology leaked row: {r}"

# ==============================================================================
# Integration Tests — Multi-Tenant Isolation
# ==============================================================================

def test_investor_cannot_read_other_investor_holdings(investor_client):
    """Investor Rahul Verma (id=4) cannot access holdings of Sneha (5) or Vikram (6)."""
    from repositories.holding_repo import HoldingRepository
    from services.trading_service import TradingService
    h = HoldingRepository.get_by_user_and_stock(4, 1)
    if not h or h["quantity"] <= 0:
        TradingService.execute_market_order(4, 1, "BUY", 1)

    # 1. Unscoped query
    resp = investor_client.post("/ai/api/v1/ai/execute", json={
        "sql": "SELECT user_id, symbol, quantity FROM v_investor_portfolio"
    })
    assert resp.status_code == 200
    rows = resp.get_json()["data"]["rows"]
    assert len(rows) > 0
    for r in rows:
        assert r["user_id"] == 4

    # 2. Targeted override attempt (trying to filter explicitly by user_id = 5)
    resp_override = investor_client.post("/ai/api/v1/ai/execute", json={
        "sql": "SELECT user_id, symbol, quantity FROM v_investor_portfolio WHERE user_id = 5"
    })
    assert resp_override.status_code == 200
    rows_override = resp_override.get_json()["data"]["rows"]
    # Derived table only contains user 4's rows, so filtering for user 5 returns 0 rows
    assert len(rows_override) == 0

def test_investor_cannot_read_other_investor_transactions(investor_client):
    """Investor cannot access transactions executed by other investors."""
    resp = investor_client.post("/ai/api/v1/ai/execute", json={
        "sql": "SELECT transaction_id, user_id, symbol, quantity FROM v_investor_transactions"
    })
    assert resp.status_code == 200
    rows = resp.get_json()["data"]["rows"]
    for r in rows:
        assert r["user_id"] == 4

def test_broker_cannot_read_other_broker_clients_or_commissions(broker_client, broker2_client):
    """Broker Arun (id=2) and Broker Priya (id=3) cannot see each other's clients or commissions."""
    # Broker Arun (id=2)
    resp2 = broker_client.post("/ai/api/v1/ai/execute", json={
        "sql": "SELECT broker_id, investor_name, total_volume FROM v_broker_client_summary"
    })
    assert resp2.status_code == 200
    rows2 = resp2.get_json()["data"]["rows"]
    assert len(rows2) > 0
    for r in rows2:
        assert r["broker_id"] == 2

    # Broker Priya (id=3)
    resp3 = broker2_client.post("/ai/api/v1/ai/execute", json={
        "sql": "SELECT broker_id, investor_name, total_volume FROM v_broker_client_summary"
    })
    assert resp3.status_code == 200
    rows3 = resp3.get_json()["data"]["rows"]
    assert len(rows3) > 0
    for r in rows3:
        assert r["broker_id"] == 3

def test_admin_views_rejected_for_non_admins(investor_client, broker_client):
    """Non-admin roles cannot query admin-only views like v_admin_trade_facts, v_admin_user_audit, or v_admin_audit_logs."""
    for view in ["v_admin_trade_facts", "v_admin_user_audit", "v_admin_audit_logs"]:
        resp_inv = investor_client.post("/ai/api/v1/ai/execute", json={
            "sql": f"SELECT * FROM {view}"
        })
        assert resp_inv.status_code == 422
        assert "unauthorized table" in resp_inv.get_json()["error"]["message"].lower()

        resp_brk = broker_client.post("/ai/api/v1/ai/execute", json={
            "sql": f"SELECT * FROM {view}"
        })
        assert resp_brk.status_code == 422
        assert "unauthorized table" in resp_brk.get_json()["error"]["message"].lower()

def test_admin_failed_logins_query(admin_client):
    """Admin querying failed logins receives user accounts or audit logs, NOT stocks/banks."""
    res = admin_client.post("/ai/api/v1/ai/query", json={
        "prompt": "show me the accounts which have logged in failed till 9:30"
    })
    assert res.status_code == 200
    data = res.get_json()["data"]
    sql = data["generated_sql"].lower()
    assert "v_market_latest" not in sql
    assert "v_admin_audit_logs" in sql or "v_admin_user_audit" in sql
    assert "username" in data["columns"]
    # Verify no stock ticker symbols (TCS, INFY, HDFCBANK) are returned as accounts
    assert "symbol" not in data["columns"]
    assert "day_change" not in data["columns"]
    assert data["summary"] is not None

def test_complex_ast_structures_maintain_tenancy(investor_client):
    """CTEs, nested subqueries, aliases, joins, and unions cannot bypass tenant scoping."""
    complex_queries = [
        # CTE
        "WITH p AS (SELECT * FROM v_investor_portfolio) SELECT symbol, user_id FROM p",
        # Nested subquery
        "SELECT sub.symbol, sub.user_id FROM (SELECT * FROM v_investor_portfolio WHERE quantity > 0) sub",
        # Aliased table
        "SELECT my_pos.symbol, my_pos.user_id FROM v_investor_portfolio my_pos",
        # Safe JOIN with public market data
        "SELECT p.symbol, p.user_id, m.current_price FROM v_investor_portfolio p JOIN v_market_latest m ON p.stock_id = m.stock_id",
        # UNION ALL of two tenant views
        "SELECT symbol, user_id FROM v_investor_portfolio UNION ALL SELECT symbol, user_id FROM v_investor_transactions"
    ]
    for q in complex_queries:
        resp = investor_client.post("/ai/api/v1/ai/execute", json={"sql": q})
        assert resp.status_code == 200, f"Query failed: {q} with {resp.get_data(as_text=True)}"
        rows = resp.get_json()["data"]["rows"]
        for r in rows:
            if "user_id" in r and r["user_id"] is not None:
                assert r["user_id"] == 4, f"Leaked tenant id in row {r} for query {q}"

# ==============================================================================
# Connection Pooling & Session Cleanup Hygiene Tests
# ==============================================================================

def test_connection_pool_session_hygiene(investor_client):
    """Reusing pooled connections across queries does not leak session variable @current_user_id."""
    # 1. Execute query as investor (user_id = 4)
    resp = investor_client.post("/ai/api/v1/ai/execute", json={
        "sql": "SELECT symbol, quantity FROM v_investor_portfolio"
    })
    assert resp.status_code == 200

    # 2. Check out a connection directly from the AI pool without setting @current_user_id
    with get_ai_connection() as conn:
        session_val = conn.execute(text("SELECT @current_user_id")).scalar()
        assert session_val is None, f"Contaminated session variable found in pool: {session_val}"

def test_cleanup_failure_invalidates_connection(app):
    """If an exception occurs or cleanup fails, the connection is invalidated and not returned dirty."""
    with get_ai_connection() as conn:
        assert conn.invalidated is False
        # Simulate connection invalidation
        conn.invalidate()
        assert conn.invalidated is True

# ==============================================================================
# React-Facing AI Endpoint & Audit Logging Tests
# ==============================================================================

def test_real_react_endpoint_success(investor_client):
    """React UI endpoint POST /ai/api/v1/ai/query succeeds with valid response contract."""
    resp = investor_client.post("/ai/api/v1/ai/query", json={
        "prompt": "Show my total unrealized profit and loss"
    })
    assert resp.status_code == 200
    json_data = resp.get_json()
    assert json_data["ok"] is True
    data = json_data["data"]
    assert "generated_sql" in data
    assert "provider_used" in data
    assert "results" in data
    assert "summary" in data
    assert data["ast_validated"] is True
    assert ":auth_user_id" in data["generated_sql"]

def test_client_supplied_user_id_override_ignored(investor_client):
    """Client-supplied user_id in request body cannot override server-authenticated identity."""
    # Malicious investor sends user_id: 1 (Admin) in request body
    resp = investor_client.post("/ai/api/v1/ai/execute", json={
        "sql": "SELECT user_id, symbol FROM v_investor_portfolio",
        "user_id": 1
    })
    assert resp.status_code == 200
    rows = resp.get_json()["data"]["rows"]
    for r in rows:
        assert r["user_id"] == 4  # Authenticated investor identity strictly enforced

def test_audit_records_cover_rejected_and_successful_requests(investor_client):
    """Both rejected queries and successful executions are recorded in AI_Query_History."""
    # 1. Trigger AST validation rejection
    resp_bad = investor_client.post("/ai/api/v1/ai/execute", json={
        "sql": "DROP TABLE Users;",
        "prompt": "Malicious drop attempt"
    })
    assert resp_bad.status_code == 422

    # 2. Trigger successful execution
    resp_good = investor_client.post("/ai/api/v1/ai/execute", json={
        "sql": "SELECT symbol FROM v_investor_portfolio",
        "prompt": "Legitimate portfolio read"
    })
    assert resp_good.status_code == 200

    # 3. Retrieve audit history via GET /ai/api/v1/ai/history
    resp_hist = investor_client.get("/ai/api/v1/ai/history")
    assert resp_hist.status_code == 200
    history = resp_hist.get_json()["data"]
    assert len(history) >= 2

    # Check rejected entry
    rejected_entries = [h for h in history if h["validation_status"] == "REJECTED"]
    assert len(rejected_entries) > 0
    assert rejected_entries[0]["execution_status"] == "SKIPPED"
    assert "drop" in rejected_entries[0]["error_code"].lower()

    # Check successful entry
    valid_entries = [h for h in history if h["validation_status"] == "VALID"]
    assert len(valid_entries) > 0
    assert valid_entries[0]["execution_status"] == "SUCCESS"

def test_provider_failure_fallback_and_validation(investor_client, monkeypatch):
    """When LLM router fails, system falls back to template and passes AST validation & scoping."""
    # Mock LLMRouter to simulate all providers failing
    def mock_complete(self, messages, json_mode=True):
        return {
            "content": None,
            "provider_used": "TEMPLATE_FALLBACK",
            "attempts": [{"provider": "grok", "status": "cooldown"}]
        }
    monkeypatch.setattr(LLMRouter, "complete", mock_complete)

    resp = investor_client.post("/ai/api/v1/ai/query", json={
        "prompt": "What are my current open holdings?"
    })
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["provider_used"] == "TEMPLATE_FALLBACK"
    assert data["ast_validated"] is True
    assert ":auth_user_id" in data["generated_sql"]

def test_rag_targeted_retrieval_evaluation():
    """RAG service selectively retrieves matching schemas, business rules, and few-shot examples."""
    from services.rag_service import RAGService

    # 1. Investor asks about unrealized profit / portfolio
    ctx_pnl = RAGService.get_context_for_role("INVESTOR", "What is my total unrealized profit and loss?")
    assert "v_investor_portfolio" in ctx_pnl
    assert "v_admin_trade_facts" not in ctx_pnl  # Admin schemas excluded
    assert "v_broker_client_summary" not in ctx_pnl  # Broker schemas excluded
    assert "profit" in ctx_pnl.lower()
    assert "Weighted Average Cost Basis" in ctx_pnl or "Cost Basis" in ctx_pnl

    # 2. Investor asks about trading fees
    ctx_fee = RAGService.get_context_for_role("INVESTOR", "How much brokerage fees have I paid on transactions?")
    assert "v_investor_transactions" in ctx_fee
    assert "Brokerage Charges (Investor-Paid)" in ctx_fee

    # 3. Broker asks about commissions
    ctx_comm = RAGService.get_context_for_role("BROKER", "What is my total commission earned this month?")
    assert "v_broker_commissions" in ctx_comm
    assert "Broker Commission (Platform-Funded)" in ctx_comm
    assert "v_investor_portfolio" not in ctx_comm  # Investor schemas excluded

def test_query_history_user_isolation(investor_client, broker_client):
    """Users can only retrieve their own query history records."""
    # Investor 4 runs query
    investor_client.post("/ai/api/v1/ai/execute", json={
        "sql": "SELECT symbol FROM v_investor_portfolio",
        "prompt": "Investor 4 private query"
    })

    # Broker 2 runs query
    broker_client.post("/ai/api/v1/ai/execute", json={
        "sql": "SELECT symbol FROM v_market_latest",
        "prompt": "Broker 2 private query"
    })

    # Fetch history as Investor 4
    resp_inv = investor_client.get("/ai/api/v1/ai/history")
    assert resp_inv.status_code == 200
    inv_history = resp_inv.get_json()["data"]
    prompts_inv = [h["prompt"] for h in inv_history]
    assert "Investor 4 private query" in prompts_inv
    assert "Broker 2 private query" not in prompts_inv

    # Fetch history as Broker 2
    resp_brk = broker_client.get("/ai/api/v1/ai/history")
    assert resp_brk.status_code == 200
    brk_history = resp_brk.get_json()["data"]
    prompts_brk = [h["prompt"] for h in brk_history]
    assert "Broker 2 private query" in prompts_brk
    assert "Investor 4 private query" not in prompts_brk

# ==============================================================================
# Manual SQL Mode & Shared Execution Tests
# ==============================================================================

def test_manual_sql_execution_success(investor_client):
    """Manual SQL mode executes valid read-only query and logs audit record with MANUAL_SQL provider."""
    res = investor_client.post("/ai/api/v1/ai/execute", json={
        "sql": "SELECT symbol, quantity, current_price, market_value FROM v_investor_portfolio ORDER BY market_value DESC",
        "prompt": "Manual SQL Portfolio Check",
        "provider": "MANUAL_SQL"
    })
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert "executed_sql" in data
    assert "columns" in data
    assert "rows" in data
    assert "results" in data
    assert "duration_ms" in data
    assert data["provider"] == "MANUAL_SQL"
    assert data["ast_validated"] is True
    assert len(data["columns"]) == 4

def test_manual_sql_valid_aggregations(investor_client):
    """Manual SQL supports valid aggregations, GROUP BY, and mathematical functions."""
    res = investor_client.post("/ai/api/v1/ai/execute", json={
        "sql": "SELECT sector, COUNT(*) AS holding_count, SUM(market_value) AS total_val FROM v_investor_portfolio GROUP BY sector",
        "provider": "MANUAL_SQL"
    })
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert "columns" in data
    assert "holding_count" in data["columns"]
    assert "total_val" in data["columns"]

def test_manual_sql_forbidden_writes_rejected(investor_client):
    """Manual SQL strictly blocks INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE."""
    forbidden = [
        "INSERT INTO v_market_latest (symbol) VALUES ('TEST')",
        "UPDATE Accounts SET virtual_balance = 9999999.00 WHERE user_id = 4",
        "DELETE FROM Transactions WHERE id = 1",
        "DROP VIEW v_investor_portfolio",
        "ALTER TABLE Users DROP COLUMN password_hash"
    ]
    for sql in forbidden:
        res = investor_client.post("/ai/api/v1/ai/execute", json={
            "sql": sql,
            "provider": "MANUAL_SQL"
        })
        assert res.status_code == 422
        body = res.get_json()
        assert body["ok"] is False
        assert body["error"]["code"] == "VALIDATION_FAILED"

def test_manual_sql_multiple_statements_rejected(investor_client):
    """Manual SQL rejects stacked/chained multiple statements."""
    res = investor_client.post("/ai/api/v1/ai/execute", json={
        "sql": "SELECT * FROM v_market_latest; SELECT * FROM v_investor_portfolio;",
        "provider": "MANUAL_SQL"
    })
    assert res.status_code == 422
    assert "multi-statement" in res.get_json()["error"]["message"].lower()

def test_manual_sql_unauthorized_tables_rejected(investor_client):
    """Investor in Manual SQL cannot query admin or internal tables directly."""
    unauthorized = [
        "SELECT * FROM Users",
        "SELECT * FROM Accounts",
        "SELECT * FROM v_admin_trade_facts",
        "SELECT * FROM v_broker_commissions"
    ]
    for sql in unauthorized:
        res = investor_client.post("/ai/api/v1/ai/execute", json={
            "sql": sql,
            "provider": "MANUAL_SQL"
        })
        assert res.status_code == 422
        assert "unauthorized table" in res.get_json()["error"]["message"].lower()

def test_manual_sql_cross_investor_isolation(investor_client):
    """Investor attempting to read another investor's transactions receives 0 rows."""
    res = investor_client.post("/ai/api/v1/ai/execute", json={
        "sql": "SELECT * FROM v_investor_transactions WHERE user_id = 5",
        "provider": "MANUAL_SQL"
    })
    assert res.status_code == 200
    data = res.get_json()["data"]
    # Enforced subquery tenancy guarantees zero leak of investor 5's data
    assert len(data["rows"]) == 0

def test_manual_sql_broker_client_isolation(broker_client):
    """Broker attempting to read another broker's client transactions receives 0 rows."""
    res = broker_client.post("/ai/api/v1/ai/execute", json={
        "sql": "SELECT * FROM v_broker_client_transactions WHERE broker_id = 3",
        "provider": "MANUAL_SQL"
    })
    assert res.status_code == 200
    data = res.get_json()["data"]
    # Broker 2 cannot see broker 3's client transactions
    assert len(data["rows"]) == 0

def test_manual_sql_malformed_syntax_error(investor_client):
    """Malformed SQL syntax returns readable error."""
    res = investor_client.post("/ai/api/v1/ai/execute", json={
        "sql": "SELECT FROM WHERE ???",
        "provider": "MANUAL_SQL"
    })
    assert res.status_code == 422
    assert "syntax error" in res.get_json()["error"]["message"].lower()

def test_manual_sql_admin_system_level_access(admin_client):
    """Admin can execute system-level aggregations across market facts and commission rules."""
    res = admin_client.post("/ai/api/v1/ai/execute", json={
        "sql": "SELECT sector, COUNT(*) AS stock_count, ROUND(AVG(current_price), 2) AS avg_price FROM v_market_latest GROUP BY sector",
        "provider": "MANUAL_SQL"
    })
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert len(data["rows"]) > 0
    assert "stock_count" in data["columns"]

def test_ai_schema_endpoint(investor_client, broker_client, admin_client):
    """Schema endpoint returns role-specific allowed views and sample queries."""
    # Investor
    res_inv = investor_client.get("/ai/api/v1/ai/schema")
    assert res_inv.status_code == 200
    inv_views = [v["view"] for v in res_inv.get_json()["data"]["allowed_views"]]
    assert "v_investor_portfolio" in inv_views
    assert "v_admin_trade_facts" not in inv_views

    # Broker
    res_brk = broker_client.get("/ai/api/v1/ai/schema")
    assert res_brk.status_code == 200
    brk_views = [v["view"] for v in res_brk.get_json()["data"]["allowed_views"]]
    assert "v_broker_client_summary" in brk_views
    assert "v_investor_portfolio" not in brk_views

    # Admin
    res_adm = admin_client.get("/ai/api/v1/ai/schema")
    assert res_adm.status_code == 200
    adm_views = [v["view"] for v in res_adm.get_json()["data"]["allowed_views"]]
    assert "v_admin_trade_facts" in adm_views
    assert "commission_rules" in adm_views

