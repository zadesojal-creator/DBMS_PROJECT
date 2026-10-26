"""
SQLAlchemy Core Table Definitions (models/schema.py)
Maps all 21 tables in StockTrade for parameterized Core queries.
"""
from sqlalchemy import (
    MetaData, Table, Column, BigInteger, Integer, String, Text,
    Numeric, Enum, Boolean, DateTime, Date, ForeignKey, UniqueConstraint
)

metadata = MetaData()

users_table = Table(
    "Users", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("username", String(50), nullable=False, unique=True),
    Column("email", String(100), nullable=False, unique=True),
    Column("password_hash", String(255), nullable=False),
    Column("full_name", String(100), nullable=False),
    Column("phone", String(20), nullable=True),
    Column("role", Enum("ADMIN", "BROKER", "INVESTOR", name="user_role"), nullable=False),
    Column("status", Enum("ACTIVE", "INACTIVE", name="user_status"), nullable=False, default="ACTIVE"),
    Column("is_demo", Boolean, nullable=False, default=False),
    Column("failed_login_attempts", Integer, nullable=False, default=0),
    Column("locked_until", DateTime, nullable=True),
    Column("last_login_at", DateTime, nullable=True),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False)
)

accounts_table = Table(
    "Accounts", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("user_id", BigInteger, ForeignKey("Users.id", ondelete="RESTRICT"), nullable=False, unique=True),
    Column("virtual_balance", Numeric(15, 2), nullable=False, default=0.00),
    Column("currency", String(3), nullable=False, default="INR"),
    Column("status", Enum("ACTIVE", "INACTIVE", name="account_status"), nullable=False, default="ACTIVE"),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False)
)

stocks_table = Table(
    "Stocks", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("symbol", String(20), nullable=False, unique=True),
    Column("company_name", String(150), nullable=False),
    Column("sector", String(50), nullable=False),
    Column("exchange", Enum("NSE", "BSE", name="stock_exchange"), nullable=False, default="NSE"),
    Column("status", Enum("ACTIVE", "INACTIVE", name="stock_status"), nullable=False, default="ACTIVE"),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False)
)

current_prices_table = Table(
    "Current_Prices", metadata,
    Column("stock_id", BigInteger, ForeignKey("Stocks.id", ondelete="RESTRICT"), primary_key=True),
    Column("price", Numeric(12, 4), nullable=False),
    Column("previous_close", Numeric(12, 4), nullable=False),
    Column("day_open", Numeric(12, 4), nullable=False),
    Column("day_high", Numeric(12, 4), nullable=False),
    Column("day_low", Numeric(12, 4), nullable=False),
    Column("volume", BigInteger, nullable=False, default=0),
    Column("updated_at", DateTime, nullable=False)
)

stock_prices_table = Table(
    "Stock_Prices", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("stock_id", BigInteger, ForeignKey("Stocks.id", ondelete="RESTRICT"), nullable=False),
    Column("price", Numeric(12, 4), nullable=False),
    Column("volume", Integer, nullable=False, default=0),
    Column("source", Enum("SEEDED", "SIMULATED", name="price_source"), nullable=False, default="SIMULATED"),
    Column("recorded_at", DateTime, nullable=False)
)

orders_table = Table(
    "Orders", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("user_id", BigInteger, ForeignKey("Users.id", ondelete="RESTRICT"), nullable=False),
    Column("stock_id", BigInteger, ForeignKey("Stocks.id", ondelete="RESTRICT"), nullable=False),
    Column("side", Enum("BUY", "SELL", name="order_side"), nullable=False),
    Column("quantity", Integer, nullable=False),
    Column("estimated_price", Numeric(12, 4), nullable=False),
    Column("executed_price", Numeric(12, 4), nullable=True),
    Column("status", Enum("PENDING", "EXECUTED", "REJECTED", "FAILED", name="order_status"), nullable=False, default="PENDING"),
    Column("reject_reason", String(255), nullable=True),
    Column("idempotency_key", String(64), nullable=False),
    Column("created_at", DateTime, nullable=False),
    Column("executed_at", DateTime, nullable=True),
    UniqueConstraint("user_id", "idempotency_key", name="uq_orders_user_idempotency")
)

holdings_table = Table(
    "Holdings", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("user_id", BigInteger, ForeignKey("Users.id", ondelete="RESTRICT"), nullable=False),
    Column("stock_id", BigInteger, ForeignKey("Stocks.id", ondelete="RESTRICT"), nullable=False),
    Column("quantity", Integer, nullable=False, default=0),
    Column("avg_cost", Numeric(12, 4), nullable=False, default=0.0000),
    Column("updated_at", DateTime, nullable=False),
    UniqueConstraint("user_id", "stock_id", name="uq_holdings_user_stock")
)

transactions_table = Table(
    "Transactions", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("order_id", BigInteger, ForeignKey("Orders.id", ondelete="RESTRICT"), nullable=False, unique=True),
    Column("user_id", BigInteger, ForeignKey("Users.id", ondelete="RESTRICT"), nullable=False),
    Column("stock_id", BigInteger, ForeignKey("Stocks.id", ondelete="RESTRICT"), nullable=False),
    Column("side", Enum("BUY", "SELL", name="trans_side"), nullable=False),
    Column("quantity", Integer, nullable=False),
    Column("execution_price", Numeric(12, 4), nullable=False),
    Column("gross_amount", Numeric(15, 2), nullable=False),
    Column("brokerage_fee", Numeric(15, 2), nullable=False, default=0.00),
    Column("net_amount", Numeric(15, 2), nullable=False),
    Column("realized_pnl", Numeric(15, 2), nullable=False, default=0.00),
    Column("executed_at", DateTime, nullable=False)
)

account_ledger_table = Table(
    "Account_Ledger", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("account_id", BigInteger, ForeignKey("Accounts.id", ondelete="RESTRICT"), nullable=False),
    Column("entry_type", Enum("OPENING_GRANT", "DEPOSIT", "BUY", "SELL", "FEE", "ADJUSTMENT", name="ledger_entry_type"), nullable=False),
    Column("amount", Numeric(15, 2), nullable=False),
    Column("balance_after", Numeric(15, 2), nullable=False),
    Column("reference_type", String(50), nullable=False),
    Column("reference_id", String(64), nullable=False),
    Column("note", String(255), nullable=True),
    Column("created_at", DateTime, nullable=False)
)

broker_clients_table = Table(
    "Broker_Clients", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("broker_id", BigInteger, ForeignKey("Users.id", ondelete="RESTRICT"), nullable=False),
    Column("investor_id", BigInteger, ForeignKey("Users.id", ondelete="RESTRICT"), nullable=False),
    Column("status", Enum("ACTIVE", "ENDED", name="bc_status"), nullable=False, default="ACTIVE"),
    Column("assigned_at", DateTime, nullable=False),
    Column("ended_at", DateTime, nullable=True)
)

commission_rules_table = Table(
    "Commission_Rules", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("rule_type", Enum("INVESTOR_BROKERAGE", "BROKER_COMMISSION", name="comm_rule_type"), nullable=False),
    Column("rate", Numeric(6, 5), nullable=False),
    Column("min_fee", Numeric(15, 2), nullable=False, default=0.00),
    Column("effective_from", DateTime, nullable=False),
    Column("is_active", Boolean, nullable=False, default=True),
    Column("created_at", DateTime, nullable=False)
)

commissions_table = Table(
    "Commissions", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("transaction_id", BigInteger, ForeignKey("Transactions.id", ondelete="RESTRICT"), nullable=False, unique=True),
    Column("broker_id", BigInteger, ForeignKey("Users.id", ondelete="RESTRICT"), nullable=False),
    Column("investor_id", BigInteger, ForeignKey("Users.id", ondelete="RESTRICT"), nullable=False),
    Column("base_brokerage", Numeric(15, 2), nullable=False),
    Column("rate_applied", Numeric(6, 5), nullable=False),
    Column("commission_amount", Numeric(15, 2), nullable=False),
    Column("created_at", DateTime, nullable=False)
)

watchlist_table = Table(
    "Watchlist", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("user_id", BigInteger, ForeignKey("Users.id", ondelete="RESTRICT"), nullable=False),
    Column("stock_id", BigInteger, ForeignKey("Stocks.id", ondelete="RESTRICT"), nullable=False),
    Column("added_at", DateTime, nullable=False),
    UniqueConstraint("user_id", "stock_id", name="uq_watchlist_user_stock")
)

price_alerts_table = Table(
    "Price_Alerts", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("user_id", BigInteger, ForeignKey("Users.id", ondelete="RESTRICT"), nullable=False),
    Column("stock_id", BigInteger, ForeignKey("Stocks.id", ondelete="RESTRICT"), nullable=False),
    Column("target_price", Numeric(12, 4), nullable=False),
    Column("condition_type", Enum("ABOVE", "BELOW", name="alert_condition"), nullable=False),
    Column("status", Enum("ACTIVE", "TRIGGERED", "CANCELLED", name="alert_status"), nullable=False, default="ACTIVE"),
    Column("created_at", DateTime, nullable=False),
    Column("triggered_at", DateTime, nullable=True)
)

audit_logs_table = Table(
    "Audit_Logs", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("user_id", BigInteger, ForeignKey("Users.id", ondelete="RESTRICT"), nullable=True),
    Column("action", String(64), nullable=False),
    Column("entity_type", String(64), nullable=False),
    Column("entity_id", String(64), nullable=True),
    Column("details", Text, nullable=True),
    Column("ip_address", String(45), nullable=True),
    Column("created_at", DateTime, nullable=False)
)

ai_query_history_table = Table(
    "AI_Query_History", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("user_id", BigInteger, ForeignKey("Users.id", ondelete="RESTRICT"), nullable=False),
    Column("prompt", Text, nullable=False),
    Column("generated_sql", Text, nullable=True),
    Column("tables_used", Text, nullable=True),
    Column("validation_status", Enum("VALID", "REJECTED", name="ai_val_status"), nullable=False),
    Column("execution_status", Enum("SUCCESS", "FAILED", "SKIPPED", name="ai_exec_status"), nullable=False),
    Column("error_code", String(64), nullable=True),
    Column("duration_ms", Integer, nullable=True),
    Column("row_count", Integer, nullable=True),
    Column("provider", String(32), nullable=True),
    Column("created_at", DateTime, nullable=False)
)

saved_reports_table = Table(
    "Saved_Reports", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("user_id", BigInteger, ForeignKey("Users.id", ondelete="RESTRICT"), nullable=False),
    Column("name", String(100), nullable=False),
    Column("description", Text, nullable=True),
    Column("query_sql", Text, nullable=False),
    Column("last_run_at", DateTime, nullable=True),
    Column("created_at", DateTime, nullable=False)
)

system_settings_table = Table(
    "System_Settings", metadata,
    Column("key_name", String(64), primary_key=True),
    Column("value_text", Text, nullable=False),
    Column("description", String(255), nullable=True),
    Column("updated_at", DateTime, nullable=False)
)

system_events_table = Table(
    "System_Events", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("event_type", String(64), nullable=False),
    Column("severity", Enum("INFO", "WARNING", "ERROR", "CRITICAL", name="event_severity"), nullable=False, default="INFO"),
    Column("details", Text, nullable=True),
    Column("created_at", DateTime, nullable=False)
)

portfolio_snapshots_table = Table(
    "Portfolio_Snapshots", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("user_id", BigInteger, ForeignKey("Users.id", ondelete="RESTRICT"), nullable=False),
    Column("snapshot_date", Date, nullable=False),
    Column("cash_balance", Numeric(15, 2), nullable=False, default=0.00),
    Column("holdings_value", Numeric(15, 2), nullable=False, default=0.00),
    Column("total_portfolio_value", Numeric(15, 2), nullable=False, default=0.00),
    Column("total_pnl", Numeric(15, 2), nullable=False, default=0.00),
    Column("created_at", DateTime, nullable=False),
    UniqueConstraint("user_id", "snapshot_date", name="uq_user_snapshot_date")
)
