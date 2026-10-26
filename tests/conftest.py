import os
import sys
import pytest
import pymysql
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

from app import create_app
from models.user import User

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
TEST_DB_NAME = os.getenv("TEST_DB_NAME", "stocktrade_test")
APP_USER = os.getenv("DB_USER", "stocktrade_app")
APP_PASSWORD = os.getenv("DB_PASSWORD", "StockTradeApp@2026!")

@pytest.fixture(scope="session")
def db_conn():
    """Provides a connection to the dedicated test database."""
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=APP_USER,
        password=APP_PASSWORD,
        database=TEST_DB_NAME,
        charset="utf8mb4",
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor
    )
    yield conn
    conn.close()

@pytest.fixture
def cursor(db_conn):
    """Provides a fresh cursor per test."""
    with db_conn.cursor() as cur:
        yield cur

@pytest.fixture(scope="session")
def app():
    """Provides the Flask application instance configured for testing."""
    application = create_app("testing")
    yield application

@pytest.fixture
def client(app):
    """Provides an unauthenticated Flask test client."""
    return app.test_client()

@pytest.fixture
def admin_client(app):
    """Provides an authenticated ADMIN test client."""
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = '1'
        sess['_fresh'] = True
    return client

@pytest.fixture
def broker_client(app):
    """Provides an authenticated BROKER test client (Broker Arun, id=2)."""
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = '2'
        sess['_fresh'] = True
    return client

@pytest.fixture
def broker2_client(app):
    """Provides an authenticated BROKER test client (Broker Priya, id=3)."""
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = '3'
        sess['_fresh'] = True
    return client

@pytest.fixture
def investor_client(app):
    """Provides an authenticated INVESTOR test client (Rahul Verma, id=4)."""
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = '4'
        sess['_fresh'] = True
    return client
