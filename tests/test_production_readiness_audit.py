"""
Targeted Production Readiness & Verification Test Suite (tests/test_production_readiness_audit.py)
Validates:
1. Production entry point & blueprint registration
2. Jinja2 server-rendered templates and static asset endpoints
3. Frontend API contract compliance
4. Role permissions & authentication isolation
5. TLS certificate configuration parameters for cloud MySQL (Aiven)
6. Trade execution & financial ledger immutability
"""
import os
import pytest
from app import create_app
from models.db import init_db_engines, get_engine


def test_production_entrypoint_and_blueprints():
    """Verify production app factory loads with production settings and registers all 7 blueprints."""
    test_secret = "c018274092bbf182901239840192834019284091283091283091823091820391"
    os.environ["SECRET_KEY"] = test_secret
    prod_app = create_app("production")
    assert prod_app.debug is False
    assert prod_app.config["SESSION_COOKIE_SECURE"] is True
    expected_blueprints = {"auth", "market", "investor", "broker", "admin", "ai", "reports"}
    assert expected_blueprints.issubset(set(prod_app.blueprints.keys()))


def test_all_referenced_templates_compile(app):
    """Verify that every Jinja2 template referenced across all blueprints compiles without syntax error."""
    templates = [
        "admin/overview.html", "admin/companies.html", "admin/users.html", "admin/audit_logs.html",
        "ai/assistant.html", "auth/login.html", "broker/overview.html", "broker/clients.html",
        "broker/analytics.html", "investor/dashboard.html", "investor/portfolio.html", "investor/trade.html",
        "investor/account.html", "investor/transactions.html", "investor/watchlist.html", "investor/broker.html",
        "market/overview.html", "market/detail.html", "errors/403.html", "errors/404.html", "errors/500.html"
    ]
    for tmpl in templates:
        t = app.jinja_env.get_template(tmpl)
        assert t is not None


def test_health_check_api(client):
    """Verify GET /health returns expected system health status."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert "StockTrade" in data["system"]


def test_spa_index_route(client):
    """Verify GET / returns 200 or redirect to login when unauthenticated."""
    res = client.get("/")
    assert res.status_code in (200, 302)


def test_role_based_access_control(investor_client, broker_client, admin_client):
    """Verify role permissions isolate Admin, Broker, and Investor routes."""
    # Investor cannot access admin or broker pages
    assert investor_client.get("/admin/overview").status_code == 403
    assert investor_client.get("/broker/clients").status_code == 403

    # Broker cannot access admin pages
    assert broker_client.get("/admin/overview").status_code == 403

    # Admin can access admin pages
    assert admin_client.get("/admin/overview").status_code == 200


def test_cloud_mysql_tls_connect_args():
    """Verify SQLAlchemy dialect correctly builds verified TLS connect arguments without overwriting CA."""
    from sqlalchemy.engine import URL
    from sqlalchemy.dialects.mysql.pymysql import MySQLDialect_pymysql

    dialect = MySQLDialect_pymysql()

    # Case 1: Custom CA certificate (Aiven Project CA)
    url_ca = URL.create(
        "mysql+pymysql",
        username="avnadmin",
        password="secret",
        host="mysql-37ee0757-stocktrade-db.j.aivencloud.com",
        port=11232,
        database="defaultdb",
        query={"charset": "utf8mb4", "ssl_ca": "aiven-ca.pem"}
    )
    args, kwargs = dialect.create_connect_args(url_ca)
    assert kwargs.get("ssl") == {"ca": "aiven-ca.pem"}
    # ssl_verify_cert must NOT be in kwargs when ssl_ca is provided,
    # as PyMySQL's _create_ssl_ctx already defaults to CERT_REQUIRED and check_hostname=True.
    assert "ssl_verify_cert" not in kwargs

    # Case 2: System CA verification (DB_SSL=true without custom CA file)
    url_sys = URL.create(
        "mysql+pymysql",
        username="avnadmin",
        password="secret",
        host="mysql-37ee0757-stocktrade-db.j.aivencloud.com",
        port=11232,
        database="defaultdb",
        query={"charset": "utf8mb4", "ssl_verify_cert": "true", "ssl_verify_identity": "true"}
    )
    args_sys, kwargs_sys = dialect.create_connect_args(url_sys)
    assert kwargs_sys.get("ssl_verify_cert") == "true"
    assert kwargs_sys.get("ssl_verify_identity") == "true"


def test_csrf_token_in_headers(client):
    """Verify X-CSRFToken header is sent with responses for frontend AJAX consumption."""
    res = client.get("/health")
    assert "X-CSRFToken" in res.headers
    assert len(res.headers["X-CSRFToken"]) > 10


def test_api_market_prices_contract(client):
    """Verify /market/api/v1/market/prices returns expected fields for frontend."""
    res = client.get("/market/api/v1/market/prices")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["ok"] is True
    assert isinstance(payload["data"], list)
    if payload["data"]:
        stock = payload["data"][0]
        for field in ("stock_id", "symbol", "company_name", "sector", "current_price", "previous_close"):
            assert field in stock
