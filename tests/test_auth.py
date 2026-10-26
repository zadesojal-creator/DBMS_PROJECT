"""
Authentication Suite (test_auth.py)
Validates login, logout, password verification, lockout after 5 attempts, and deactivated accounts.
"""
import pytest
from repositories.user_repo import UserRepository
from services.auth_service import AuthService

def test_login_success(client):
    """Admin logs in successfully with valid credentials."""
    resp = client.post("/api/v1/auth/login", json={
        "identifier": "admin",
        "password": "Admin@StockTrade2026"
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["data"]["role"] == "ADMIN"
    assert data["data"]["username"] == "admin"

def test_login_invalid_password(client):
    """Failed login attempt returns 401 and decrements attempts."""
    u = UserRepository.get_by_username("investor_sneha")
    if u:
        UserRepository.reset_failed_logins(u["id"])
    resp = client.post("/api/v1/auth/login", json={
        "identifier": "investor_sneha",
        "password": "WrongPassword123!"
    })
    assert resp.status_code == 401
    data = resp.get_json()
    assert data["ok"] is False
    assert "Invalid email/username or password" in data["error"]["message"]

def test_login_brute_force_lockout(client):
    """Account gets locked for 15 minutes after 5 consecutive failed login attempts."""
    user = UserRepository.get_by_username("investor_karan")
    assert user is not None
    UserRepository.reset_failed_logins(user["id"])

    # Attempt 4 failed logins
    for i in range(4):
        resp = client.post("/api/v1/auth/login", json={
            "identifier": "investor_karan",
            "password": f"Wrong_{i}"
        })
        assert resp.status_code == 401
        assert "attempts remaining" in resp.get_json()["error"]["message"]

    # 5th failed attempt triggers lockout
    resp5 = client.post("/api/v1/auth/login", json={
        "identifier": "investor_karan",
        "password": "Wrong_5"
    })
    assert resp5.status_code == 401
    assert "locked" in resp5.get_json()["error"]["message"].lower()

    # Even with correct password, locked account is rejected
    resp_correct = client.post("/api/v1/auth/login", json={
        "identifier": "investor_karan",
        "password": "Investor@StockTrade2026"
    })
    assert resp_correct.status_code == 401
    assert "locked" in resp_correct.get_json()["error"]["message"].lower()

    # Reset for subsequent tests
    UserRepository.reset_failed_logins(user["id"])

def test_login_deactivated_user(client):
    """Deactivated accounts cannot authenticate."""
    user = UserRepository.get_by_username("investor_rohit")
    assert user is not None
    UserRepository.update_status(user["id"], "INACTIVE")

    resp = client.post("/api/v1/auth/login", json={
        "identifier": "investor_rohit",
        "password": "Investor@StockTrade2026"
    })
    assert resp.status_code == 401
    assert "inactive" in resp.get_json()["error"]["message"].lower()

    # Restore status
    UserRepository.update_status(user["id"], "ACTIVE")

def test_logout_clears_session(admin_client):
    """Logout invalidates session and /me returns 401."""
    # Verify currently authenticated
    me_resp = admin_client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.get_json()["data"]["username"] == "admin"

    # Logout
    logout_resp = admin_client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 200

    # Next call to /me must fail with 401
    me_after = admin_client.get("/api/v1/auth/me")
    assert me_after.status_code == 401

def test_session_endpoint_lifecycle(client, investor_client):
    """Session endpoint reports authentication status and CSRF token."""
    # Unauthenticated client
    resp = client.get("/api/v1/auth/session")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["authenticated"] is False
    assert "csrf_token" in data

    # Authenticated investor client
    resp_auth = investor_client.get("/api/v1/auth/session")
    assert resp_auth.status_code == 200
    data_auth = resp_auth.get_json()["data"]
    assert data_auth["authenticated"] is True
    assert data_auth["user"]["role"] == "INVESTOR"
    assert "csrf_token" in data_auth

def test_spa_root_served(client):
    """Root route serves compiled React SPA index.html."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "StockTrade" in html
    assert "root" in html

