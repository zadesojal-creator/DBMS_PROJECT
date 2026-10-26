"""
Database Engine & Connection Pool Management (models/db.py)
SQLAlchemy 2.x Core explicit parameterized SQL with connection pooling.
"""
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, Engine, Connection
from config import Config

_engine: Engine | None = None
_ai_engine: Engine | None = None

def init_db_engines(config):
    """Initializes connection pools for application DML and AI read-only assistant."""
    global _engine, _ai_engine
    
    # Extract params whether config is Flask app.config or a Config class
    def get_val(k, default=""):
        if hasattr(config, k):
            return getattr(config, k)
        elif hasattr(config, "get"):
            return config.get(k, default)
        return default

    db_user = get_val("DB_USER", "stocktrade_app")
    db_pass = get_val("DB_PASSWORD", "StockTradeApp@2026!")
    db_host = get_val("DB_HOST", "localhost")
    db_port = get_val("DB_PORT", 3306)
    db_name = get_val("DB_NAME", "stocktrade")
    
    db_ai_user = get_val("DB_AI_USER", "stocktrade_ai_ro")
    db_ai_pass = get_val("DB_AI_PASSWORD", "StockTradeAiRo@2026!")

    db_ssl = str(get_val("DB_SSL", "false")).lower() in ("true", "1", "yes")
    db_ssl_ca = get_val("DB_SSL_CA", "")

    query_params = {"charset": "utf8mb4"}

    if db_ssl_ca:
     query_params["ssl_ca"] = db_ssl_ca
     query_params["ssl_verify_cert"] = "true"
     query_params["ssl_verify_identity"] = "true"
    elif db_ssl:
     query_params["ssl_verify_cert"] = "true"
     query_params["ssl_verify_identity"] = "true"
    from sqlalchemy.engine import URL

    app_url = URL.create(
        "mysql+pymysql",
        username=db_user,
        password=db_pass,
        host=db_host,
        port=int(db_port),
        database=db_name,
        query=query_params
    )
    ai_url = URL.create(
        "mysql+pymysql",
        username=db_ai_user,
        password=db_ai_pass,
        host=db_host,
        port=int(db_port),
        database=db_name,
        query=query_params
    )

    _engine = create_engine(
        app_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=1800,
        future=True
    )
    _ai_engine = create_engine(
        ai_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=1800,
        future=True
    )

def get_engine() -> Engine:
    """Returns the primary SQLAlchemy Core engine."""
    if _engine is None:
        raise RuntimeError("Database engine is not initialized. Call init_db_engines() first.")
    return _engine

def get_ai_engine() -> Engine:
    """Returns the read-only AI assistant engine."""
    if _ai_engine is None:
        raise RuntimeError("AI Database engine is not initialized. Call init_db_engines() first.")
    return _ai_engine

@contextmanager
def get_db_connection() -> Generator[Connection, None, None]:
    """Provides a connection from the primary pool."""
    engine = get_engine()
    with engine.connect() as conn:
        yield conn

@contextmanager
def get_db_transaction() -> Generator[Connection, None, None]:
    """Provides a transaction-managed connection from the primary pool."""
    engine = get_engine()
    with engine.begin() as conn:
        yield conn

@contextmanager
def get_ai_connection() -> Generator[Connection, None, None]:
    """Provides a connection from the read-only AI pool."""
    engine = get_ai_engine()
    with engine.connect() as conn:
        yield conn
