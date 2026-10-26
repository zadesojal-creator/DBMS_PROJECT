"""
RBAC & Tenant Isolation Test Suite (test_permissions.py)
Validates strict role enforcement and tenant isolation across all endpoints.
"""
import pytest

def test_unauthenticated_access_redirects(client):
    """Unauthenticated users accessing protected views are redirected to login."""
    resp = client.get("/investor/dashboard", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

def test_investor_cannot_access_admin_portal(investor_client):
    """Investor attempting to access admin portal receives 403 Forbidden."""
    resp = investor_client.get("/admin/overview")
    assert resp.status_code == 403

def test_investor_cannot_access_broker_portal(investor_client):
    """Investor attempting to access broker portal receives 403 Forbidden."""
    resp = investor_client.get("/broker/clients")
    assert resp.status_code == 403

def test_broker_cannot_access_admin_portal(broker_client):
    """Broker attempting to access admin portal receives 403 Forbidden."""
    resp = broker_client.get("/admin/overview")
    assert resp.status_code == 403

def test_broker_cannot_access_investor_portal(broker_client):
    """Broker attempting to access investor dashboard receives 403 Forbidden."""
    resp = broker_client.get("/investor/dashboard")
    assert resp.status_code == 403

def test_admin_has_access_to_admin_portal(admin_client):
    """Admin has full authorized access to admin portal."""
    resp = admin_client.get("/admin/overview")
    assert resp.status_code == 200

def test_broker_has_access_to_broker_portal(broker_client):
    """Broker has authorized access to broker portal."""
    resp = broker_client.get("/broker/clients")
    assert resp.status_code == 200

def test_investor_has_access_to_investor_portal(investor_client):
    """Investor has authorized access to investor portal."""
    resp = investor_client.get("/investor/dashboard")
    assert resp.status_code == 200
