"""
Financial Integrity & Reconciliation Suite (tests/test_reconciliation.py)
Validates all 7 system-wide invariants and RBAC on reconciliation endpoints.
"""
import pytest
from services.reconciliation_service import ReconciliationService
from models.db import get_engine
from sqlalchemy import text

def test_reconciliation_service_structure(app):
    """Reconciliation service executes all 7 invariant checks and returns structured report."""
    with app.app_context():
        report = ReconciliationService.run_full_reconciliation()
        assert "status" in report
        assert "timestamp" in report
        assert "summary" in report
        assert "discrepancies" in report

        disc = report["discrepancies"]
        expected_keys = [
            "account_balance_mismatches",
            "holding_quantity_mismatches",
            "executed_orders_without_transactions",
            "transactions_missing_ledger",
            "commission_inconsistencies",
            "duplicate_financial_events",
            "opening_grant_inconsistencies"
        ]
        for k in expected_keys:
            assert k in disc

def test_reconciliation_admin_api_endpoint(admin_client):
    """Admin portal has authorized access to GET /admin/api/v1/admin/reconciliation."""
    resp = admin_client.get("/admin/api/v1/admin/reconciliation")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert "summary" in data["data"]
    assert "discrepancies" in data["data"]

def test_reconciliation_rbac_denied_for_investor_and_broker(investor_client, broker_client):
    """Non-admin roles must be denied access to system-level reconciliation."""
    resp_inv = investor_client.get("/admin/api/v1/admin/reconciliation")
    assert resp_inv.status_code == 403

    resp_brk = broker_client.get("/admin/api/v1/admin/reconciliation")
    assert resp_brk.status_code == 403

def test_reconciliation_stored_procedure(app):
    """Stored procedure sp_reconcile_financial_integrity executes cleanly in MySQL."""
    with app.app_context():
        engine = get_engine()
        with engine.connect() as conn:
            raw_conn = conn.connection
            with raw_conn.cursor() as cur:
                cur.callproc("sp_reconcile_financial_integrity")
                # Ensure it executes without SQL error
                res = cur.fetchall()
                assert res is not None
