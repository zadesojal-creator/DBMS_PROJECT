"""
Database Engine & Connection Pool Management (models/db.py)
SQLAlchemy 2.x Core explicit parameterized SQL with connection pooling.
"""
import os
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
        if k in os.environ and os.environ[k]:
            return os.environ[k]
        if hasattr(config, k):
            v = getattr(config, k)
            if v is not None:
                return v
        elif hasattr(config, "get"):
            v = config.get(k)
            if v is not None:
                return v
        return default

    db_host = get_val("DB_HOST", "localhost")
    db_port = get_val("DB_PORT", 3306)
    db_name = get_val("DB_NAME", "stocktrade")

    db_user = get_val("DB_USER")
    if not db_user or (db_user == "stocktrade_app" and get_val("DB_ROOT_USER") and db_host not in ("localhost", "127.0.0.1")):
        db_user = get_val("DB_ROOT_USER")
    if not db_user:
        db_user = "stocktrade_app"

    db_pass = get_val("DB_PASSWORD")
    if not db_pass or (db_pass == "StockTradeApp@2026!" and get_val("DB_ROOT_PASSWORD") and db_host not in ("localhost", "127.0.0.1")):
        db_pass = get_val("DB_ROOT_PASSWORD")
    if not db_pass:
        db_pass = "StockTradeApp@2026!"
    
    db_ai_user = get_val("DB_AI_USER")
    db_ai_pass = get_val("DB_AI_PASSWORD")
    if not db_ai_user or (db_ai_user == "stocktrade_ai_ro" and db_host not in ("localhost", "127.0.0.1")):
        db_ai_user = db_user
        db_ai_pass = db_pass

    db_ssl = str(get_val("DB_SSL", "false")).lower() in ("true", "1", "yes")
    db_ssl_ca = str(get_val("DB_SSL_CA", "") or "").strip()
    db_ssl_ca_content = str(get_val("DB_SSL_CA_CONTENT", "") or get_val("AIVEN_CA_CERT", "") or "").strip()

    # If db_ssl_ca is relative, resolve relative to project root
    if db_ssl_ca and not os.path.isabs(db_ssl_ca):
        from pathlib import Path
        base_dir = Path(__file__).resolve().parent.parent
        candidate = base_dir / db_ssl_ca
        if candidate.is_file():
            db_ssl_ca = str(candidate)

    # Prefer DB_SSL_CA_CONTENT if DB_SSL_CA is omitted or points to a non-existent file (e.g., gitignored aiven-ca.pem)
    if db_ssl_ca_content and (not db_ssl_ca or not os.path.isfile(db_ssl_ca)):
        import tempfile
        normalized_ca = db_ssl_ca_content.replace("\\r\\n", "\n").replace("\\n", "\n").strip() + "\n"
        ca_temp = os.path.join(tempfile.gettempdir(), "stocktrade_aiven_ca.pem")
        with open(ca_temp, "w", encoding="utf-8") as f:
            f.write(normalized_ca)
        db_ssl_ca = ca_temp

    if db_ssl_ca and not os.path.isfile(db_ssl_ca):
        raise FileNotFoundError(
            f"DB_SSL_CA file not found at '{db_ssl_ca}'. On Render/cloud hosts, remove DB_SSL_CA "
            "and set DB_SSL_CA_CONTENT to the contents of aiven-ca.pem, or upload aiven-ca.pem as a Secret File."
        )

    query_params = {"charset": "utf8mb4"}

    if db_ssl_ca:
        # PyMySQL's _create_ssl_ctx automatically enforces ssl.CERT_REQUIRED
        # and hostname verification when 'ca' is provided. Passing ssl_verify_cert
        # causes PyMySQL to wipe the ca parameter due to an internal kwargs overwrite.
        query_params["ssl_ca"] = db_ssl_ca
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
