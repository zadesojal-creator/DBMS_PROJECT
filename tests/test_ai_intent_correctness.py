"""
Integration Tests for General AI SQL Intent-Correctness & Semantic Consistency
(tests/test_ai_intent_correctness.py)
Verifies that user queries answer the actual subject, entities, constraints,
and scope requested, without silent substitution of unrelated queries.
"""
import pytest
from services.intent_service import IntentService
from services.semantic_validator import SemanticValidator

# ==============================================================================
# 1. Sector & Entity Disambiguation Tests
# ==============================================================================

def test_sector_intent_banking_returns_only_banks(admin_client):
    """Asking about banks must return only Banking sector companies with full matching count."""
    res = admin_client.post("/ai/api/v1/ai/query", json={"prompt": "Show me all banking stocks"})
    assert res.status_code == 200
    data = res.get_json()["data"]

    assert data["row_count"] >= 8
    symbols = [r["symbol"] for r in data["rows"]]
    assert "HDFCBANK" in symbols
    assert "SBIN" in symbols
    assert "ICICIBANK" in symbols
    assert "AXISBANK" in symbols

    # Must NOT contain tech or chemical stocks
    assert "TCS" not in symbols
    assert "PIDILITIND" not in symbols

    for row in data["rows"]:
        assert row["sector"] == "Banking"

    assert "sector = 'Banking'" in data["executed_sql"] or 'sector = "Banking"' in data["executed_sql"]
    assert "Banking sector" in data["summary"] or "Banking" in data["summary"]

def test_sector_intent_chemicals_returns_only_chemicals(investor_client):
    """Asking about chemical companies must return Chemicals sector equities."""
    res = investor_client.post("/ai/api/v1/ai/query", json={"prompt": "What are the chemical companies in the market?"})
    assert res.status_code == 200
    data = res.get_json()["data"]

    assert data["row_count"] >= 8
    symbols = [r["symbol"] for r in data["rows"]]
    assert "PIDILITIND" in symbols
    assert "SRF" in symbols
    assert "TATACHEM" in symbols

    # Must NOT contain banking or telecom stocks
    assert "HDFCBANK" not in symbols
    assert "BHARTIARTL" not in symbols

    for row in data["rows"]:
        assert row["sector"] == "Chemicals"

def test_sector_intent_logistics_and_delivery(admin_client):
    """Asking about delivery companies must return Logistics sector equities (DELHIVERY, BLUEDART, CONCOR)."""
    res = admin_client.post("/ai/api/v1/ai/query", json={"prompt": "Show delivery companies"})
    assert res.status_code == 200
    data = res.get_json()["data"]

    assert data["row_count"] >= 3
    symbols = [r["symbol"] for r in data["rows"]]
    assert "DELHIVERY" in symbols
    assert "BLUEDART" in symbols
    assert "CONCOR" in symbols

    # Must NOT return TCS, Reliance, or HDFC
    assert "TCS" not in symbols
    assert "RELIANCE" not in symbols

# ==============================================================================
# 2. Administrative Security & Failed Logins Tests
# ==============================================================================

def test_admin_failed_logins_till_time(admin_client):
    """
    When an admin asks for accounts which have logged in failed till 9:30,
    the assistant must query security audit logs, NOT banks or equities!
    """
    res = admin_client.post("/ai/api/v1/ai/query", json={
        "prompt": "Show me the accounts which have logged in failed till 9:30"
    })
    assert res.status_code == 200
    data = res.get_json()["data"]

    # Target view must be v_admin_audit_logs, NOT v_market_latest
    assert "v_admin_audit_logs" in data["tables_used"]
    assert "v_market_latest" not in data["tables_used"]

    # Must filter by failed login and time constraint
    sql_lower = data["executed_sql"].lower()
    assert "login_failed" in sql_lower or "security_lockout" in sql_lower or "action" in sql_lower
    assert "09:30" in sql_lower

    # Explanation and summary must describe security audit events, not stocks
    assert "failed login" in data["summary"].lower() or "audit" in data["summary"].lower() or "event" in data["summary"].lower()

def test_admin_user_accounts_failed_attempts(admin_client):
    """Asking which user accounts have failed attempts must query v_admin_user_audit."""
    res = admin_client.post("/ai/api/v1/ai/query", json={
        "prompt": "Which user accounts currently have failed login attempts or are locked?"
    })
    assert res.status_code == 200
    data = res.get_json()["data"]

    assert "v_admin_user_audit" in data["tables_used"]
    sql_lower = data["executed_sql"].lower()
    assert "failed_login_attempts" in sql_lower or "locked_until" in sql_lower

# ==============================================================================
# 3. Domain Separation: Holdings vs Transactions vs Clients vs Commissions
# ==============================================================================

def test_investor_transactions_vs_holdings_separation(investor_client):
    """Asking for transactions must query v_investor_transactions, not holdings."""
    res_tx = investor_client.post("/ai/api/v1/ai/query", json={
        "prompt": "Show my executed transactions and trades with brokerage"
    })
    assert res_tx.status_code == 200
    data_tx = res_tx.get_json()["data"]
    assert "v_investor_transactions" in data_tx["tables_used"]
    assert "v_investor_portfolio" not in data_tx["tables_used"]

    # Asking for holdings must query v_investor_portfolio, not transactions
    res_hold = investor_client.post("/ai/api/v1/ai/query", json={
        "prompt": "What are my current open stock holdings and unrealized P&L?"
    })
    assert res_hold.status_code == 200
    data_hold = res_hold.get_json()["data"]
    assert "v_investor_portfolio" in data_hold["tables_used"]
    assert "v_investor_transactions" not in data_hold["tables_used"]

def test_broker_clients_vs_commissions_separation(broker_client):
    """Broker queries for clients must target v_broker_client_summary, commissions target v_broker_commissions."""
    res_clients = broker_client.post("/ai/api/v1/ai/query", json={
        "prompt": "Show all active clients assigned to me with their balances"
    })
    assert res_clients.status_code == 200
    data_clients = res_clients.get_json()["data"]
    assert "v_broker_client_summary" in data_clients["tables_used"]

    res_comm = broker_client.post("/ai/api/v1/ai/query", json={
        "prompt": "What is the total commission I have earned across client trades?"
    })
    assert res_comm.status_code == 200
    data_comm = res_comm.get_json()["data"]
    assert "v_broker_commissions" in data_comm["tables_used"]

# ==============================================================================
# 4. Scope, Ranking, and Result Limits
# ==============================================================================

def test_all_matching_scope_no_arbitrary_limit_10(investor_client):
    """Asking for 'all automotive companies' must return all matching records without arbitrary LIMIT 10."""
    res = investor_client.post("/ai/api/v1/ai/query", json={
        "prompt": "List all companies in the Automotive sector"
    })
    assert res.status_code == 200
    data = res.get_json()["data"]

    # All 8 automotive companies must be returned
    assert data["row_count"] == 8
    symbols = [r["symbol"] for r in data["rows"]]
    assert "TATAMOTORS" in symbols
    assert "MARUTI" in symbols
    assert "BAJAJ-AUTO" in symbols
    assert "HEROMOTOCO" in symbols

def test_explicit_top_n_ranking_respected(investor_client):
    """Asking for top 3 highest priced stocks must return exactly 3 rows sorted by price descending."""
    res = investor_client.post("/ai/api/v1/ai/query", json={
        "prompt": "Top 3 highest priced stocks in the market"
    })
    assert res.status_code == 200
    data = res.get_json()["data"]

    assert data["row_count"] == 3
    prices = [r["current_price"] for r in data["rows"]]
    # Must be sorted descending
    assert prices == sorted(prices, reverse=True)

# ==============================================================================
# 5. Empty Results & Unsupported Request Handling
# ==============================================================================

def test_empty_result_honesty_no_popular_stocks_substitution(investor_client):
    """Querying a non-existent entity or sector must return an accurate empty result, not popular stocks."""
    res = investor_client.post("/ai/api/v1/ai/query", json={
        "prompt": "Show companies in the Biotechnology sector"
    })
    assert res.status_code == 200
    data = res.get_json()["data"]

    # Must return 0 rows honestly
    assert data["row_count"] == 0
    # Must NOT substitute TCS, Reliance, or HDFC!
    assert len(data["rows"]) == 0
    assert "No " in data["summary"] or "0" in str(data["key_metrics"])

def test_unsupported_out_of_domain_request(admin_client):
    """Out-of-domain questions must return honest explanation without executing SQL."""
    res = admin_client.post("/ai/api/v1/ai/query", json={
        "prompt": "What is the capital of France and what is the weather today?"
    })
    assert res.status_code == 200
    data = res.get_json()["data"]

    assert data["row_count"] == 0
    assert "outside" in data["explanation"].lower() or "database" in data["summary"].lower()

# ==============================================================================
# 6. Synonym Resolution & Informal Phrasing
# ==============================================================================

def test_synonym_phrasings_resolve_to_canonical_sectors():
    """Verifies that IntentService resolves synonyms, stems, and informal words."""
    resolver = IntentService.get_instance()

    # Banks
    intent_bank = resolver.resolve_intent("show me top lenders in the market", "INVESTOR")
    assert intent_bank.sector == "Banking"

    # Chemicals
    intent_chem = resolver.resolve_intent("chems stocks that gained today", "INVESTOR")
    assert intent_chem.sector == "Chemicals"

    # Delivery / Logistics
    intent_del = resolver.resolve_intent("courier and delivery companies", "INVESTOR")
    assert intent_del.sector == "Logistics"

    # Tech
    intent_tech = resolver.resolve_intent("software and tech companies", "INVESTOR")
    assert intent_tech.sector == "Information Technology"

    # Pharma
    intent_pharma = resolver.resolve_intent("medicine and pharma companies", "INVESTOR")
    assert intent_pharma.sector == "Healthcare & Pharma"

    # Cars / Auto
    intent_auto = resolver.resolve_intent("car and vehicle makers", "INVESTOR")
    assert intent_auto.sector == "Automotive"

# ==============================================================================
# 7. Semantic Consistency Validator Unit Tests
# ==============================================================================

def test_semantic_validator_blocks_unrelated_query():
    """SemanticValidator must reject a generic popular-stocks query when a sector was requested."""
    resolver = IntentService.get_instance()
    intent = resolver.resolve_intent("Show me banking companies", "INVESTOR")

    # Bad query that dropped the sector filter and simply ordered by volume
    bad_sql = "SELECT symbol, company_name, current_price, volume FROM v_market_latest ORDER BY volume DESC LIMIT 10;"
    is_valid, err_code, err_msg = SemanticValidator.validate_consistency("Show me banking companies", intent, bad_sql, "INVESTOR")

    assert is_valid is False
    assert err_code == "MISSING_SECTOR_FILTER"

def test_semantic_validator_blocks_domain_mismatch():
    """SemanticValidator must reject market queries when user requested failed logins."""
    resolver = IntentService.get_instance()
    intent = resolver.resolve_intent("Show accounts which have logged in failed till 9:30", "ADMIN")

    # Bad query that queried market prices instead of audit logs
    bad_sql = "SELECT symbol, current_price FROM v_market_latest LIMIT 10;"
    is_valid, err_code, err_msg = SemanticValidator.validate_consistency(
        "Show accounts which have logged in failed till 9:30", intent, bad_sql, "ADMIN"
    )

    assert is_valid is False
    assert err_code == "DOMAIN_MISMATCH"

# ==============================================================================
# 8. Consecutive Executions No Stale State Leakage
# ==============================================================================

def test_consecutive_requests_no_stale_state(investor_client):
    """Submitting consecutive queries of different domains must never cross-contaminate results."""
    # 1. Query Banking
    res1 = investor_client.post("/ai/api/v1/ai/query", json={"prompt": "Show banking companies"})
    data1 = res1.get_json()["data"]
    sectors1 = set(r["sector"] for r in data1["rows"])
    assert sectors1 == {"Banking"}

    # 2. Query Chemicals
    res2 = investor_client.post("/ai/api/v1/ai/query", json={"prompt": "Show chemical companies"})
    data2 = res2.get_json()["data"]
    sectors2 = set(r["sector"] for r in data2["rows"])
    assert sectors2 == {"Chemicals"}
    assert "Banking" not in sectors2
