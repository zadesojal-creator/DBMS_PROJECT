"""
StockTrade Configuration Module (config.py)
Typed environment configurations for Development, Testing, and Production.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "stocktrade-insecure-default-change-me-immediately-32b")
    
    # Session & Cookie Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("FLASK_ENV") == "production"
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_CHECK_DEFAULT = True

    # Database Configuration
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_NAME = os.getenv("DB_NAME", "stocktrade")
    DB_USER = os.getenv("DB_USER", "stocktrade_app")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "StockTradeApp@2026!")
    
    DB_AI_USER = os.getenv("DB_AI_USER", "stocktrade_ai_ro")
    DB_AI_PASSWORD = os.getenv("DB_AI_PASSWORD", "StockTradeAiRo@2026!")

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    @property
    def AI_DATABASE_URI(self) -> str:
        return f"mysql+pymysql://{self.DB_AI_USER}:{self.DB_AI_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    # Financial & Trading Parameters
    SIGNUP_GRANT_AMOUNT = float(os.getenv("SIGNUP_GRANT_AMOUNT", "100000.00"))
    INVESTOR_BROKERAGE_RATE = float(os.getenv("INVESTOR_BROKERAGE_RATE", "0.0010"))
    INVESTOR_BROKERAGE_MIN_FEE = float(os.getenv("INVESTOR_BROKERAGE_MIN_FEE", "1.00"))
    BROKER_COMMISSION_RATE = float(os.getenv("BROKER_COMMISSION_RATE", "0.40"))
    PRICE_MOVED_TOLERANCE_PCT = float(os.getenv("PRICE_MOVED_TOLERANCE_PCT", "0.01"))

    # Market Simulator Parameters
    SIMULATOR_TICK_INTERVAL_SEC = float(os.getenv("SIMULATOR_TICK_INTERVAL_SEC", "0.50"))
    SIMULATOR_DB_FLUSH_SEC = float(os.getenv("SIMULATOR_DB_FLUSH_SEC", "1.0"))
    SIMULATOR_INTERVAL_SECONDS = int(os.getenv("SIMULATOR_INTERVAL_SECONDS", "5"))
    ALWAYS_OPEN = os.getenv("ALWAYS_OPEN", "true").lower() == "true"
    MAX_TICK_PCT = float(os.getenv("MAX_TICK_PCT", "0.005"))
    CIRCUIT_LIMIT_PCT = float(os.getenv("CIRCUIT_LIMIT_PCT", "0.10"))

    # Rate Limiting
    RATELIMIT_DEFAULT = "120 per minute"
    RATELIMIT_STORAGE_URI = "memory://"

class DevelopmentConfig(Config):
    """Local development configuration."""
    DEBUG = True

class TestingConfig(Config):
    """Test configuration using separate test database."""
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False  # Disabled for automated tests unless explicitly testing CSRF
    DB_NAME = os.getenv("TEST_DB_NAME", "stocktrade_test")
    RATELIMIT_ENABLED = False

class ProductionConfig(Config):
    """Hardened production configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True

config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
