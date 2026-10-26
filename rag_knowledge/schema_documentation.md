# StockTrade Database View Schemas for AI SQL Assistant

## 1. Investor Allowed Views

### v_investor_portfolio
- `user_id` (BIGINT, Ownership Column): The investor's user ID.
- `stock_id` (BIGINT, Foreign Key -> Stocks.id): Stock identifier.
- `symbol` (VARCHAR): Stock ticker symbol (e.g. 'TCS', 'INFY', 'RELIANCE').
- `company_name` (VARCHAR): Full legal corporate name.
- `sector` (VARCHAR): Industrial sector (e.g. 'Information Technology', 'Banking', 'Energy').
- `quantity` (INT): Number of shares currently held (always > 0 in this view).
- `avg_cost` (DECIMAL): Weighted average purchase cost per share.
- `cost_basis` (DECIMAL): Total invested cost basis (`quantity * avg_cost`).
- `current_price` (DECIMAL): Authoritative simulated current share price.
- `market_value` (DECIMAL): Current holding market value (`quantity * current_price`).
- `unrealized_pnl` (DECIMAL): Open profit/loss (`market_value - cost_basis`).
- `return_pct` (DECIMAL): Return percentage on position (`((current_price - avg_cost) / avg_cost) * 100`).
- `day_change` (DECIMAL): Day price change compared to previous close.
- `day_change_pct` (DECIMAL): Percentage price change today.
- `updated_at` (TIMESTAMP): Holding record last updated timestamp.

### v_investor_transactions
- `transaction_id` (BIGINT, Primary Key): Unique financial transaction ID.
- `order_id` (BIGINT, Foreign Key -> Orders.id): Associated market order ID.
- `user_id` (BIGINT, Ownership Column): The investor's user ID.
- `stock_id` (BIGINT, Foreign Key -> Stocks.id): Stock identifier.
- `symbol` (VARCHAR): Stock ticker symbol.
- `company_name` (VARCHAR): Company name.
- `sector` (VARCHAR): Industrial sector.
- `side` (ENUM): 'BUY' or 'SELL'.
- `quantity` (INT): Number of shares traded.
- `execution_price` (DECIMAL): Share price at which transaction was executed.
- `gross_amount` (DECIMAL): Trade principal value (`quantity * execution_price`).
- `brokerage_fee` (DECIMAL): Investor-paid brokerage (`max(1.00, gross * 0.0010)`).
- `net_amount` (DECIMAL): Cash debited on BUY (`gross + fee`) or credited on SELL (`gross - fee`).
- `realized_pnl` (DECIMAL): Realized profit/loss on SELL trades; NULL on BUY trades.
- `executed_at` (TIMESTAMP): Trade execution timestamp.

### v_market_latest (Shared / Public)
- `stock_id` (BIGINT, Primary Key): Stock identifier.
- `symbol` (VARCHAR): Stock ticker symbol.
- `company_name` (VARCHAR): Company name.
- `sector` (VARCHAR): Industrial sector.
- `exchange` (VARCHAR): Exchange identifier ('NSE', 'BSE').
- `status` (VARCHAR): Stock trading status ('ACTIVE', 'HALTED').
- `current_price` (DECIMAL): Authoritative current price.
- `previous_close` (DECIMAL): Previous market closing price.
- `day_change` (DECIMAL): Today's price change (`current_price - previous_close`).
- `day_change_pct` (DECIMAL): Today's percentage price change.
- `day_open` (DECIMAL): Today's opening price.
- `day_high` (DECIMAL): Today's highest intraday price.
- `day_low` (DECIMAL): Today's lowest intraday price.
- `volume` (BIGINT): Total shares traded today.
- `updated_at` (TIMESTAMP): Price tick timestamp.

---

## 2. Broker Allowed Views

### v_broker_client_transactions
- `transaction_id` (BIGINT, Primary Key): Unique transaction ID.
- `broker_id` (BIGINT, Ownership Column): The broker's user ID.
- `investor_id` (BIGINT, Foreign Key -> Users.id): Assigned investor client user ID.
- `investor_name` (VARCHAR): Full name of the assigned investor.
- `stock_id` (BIGINT, Foreign Key -> Stocks.id): Stock identifier.
- `symbol` (VARCHAR): Stock ticker symbol.
- `company_name` (VARCHAR): Company name.
- `side` (ENUM): 'BUY' or 'SELL'.
- `quantity` (INT): Number of shares traded.
- `execution_price` (DECIMAL): Share price.
- `gross_amount` (DECIMAL): Trade gross value.
- `brokerage_fee` (DECIMAL): Total brokerage collected from investor.
- `net_amount` (DECIMAL): Net cash amount of transaction.
- `broker_commission_earned` (DECIMAL): Platform-funded commission credited to broker (40% of brokerage).
- `executed_at` (TIMESTAMP): Transaction execution timestamp.

### v_broker_commissions
- `commission_id` (BIGINT, Primary Key): Unique commission ID.
- `transaction_id` (BIGINT, Foreign Key -> Transactions.id): Associated trade.
- `broker_id` (BIGINT, Ownership Column): The broker's user ID.
- `investor_id` (BIGINT, Foreign Key -> Users.id): Client who generated the trade.
- `investor_name` (VARCHAR): Client's name.
- `symbol` (VARCHAR): Traded stock symbol.
- `side` (ENUM): 'BUY' or 'SELL'.
- `quantity` (INT): Shares traded.
- `execution_price` (DECIMAL): Share price.
- `base_brokerage` (DECIMAL): Investor-paid brokerage amount.
- `rate_applied` (DECIMAL): Commission rate applied (e.g. 0.4000).
- `commission_amount` (DECIMAL): Net commission credited to broker (`base_brokerage * rate_applied`).
- `created_at` (TIMESTAMP): Commission accrual timestamp.

### v_broker_client_summary
- `broker_id` (BIGINT, Ownership Column): The broker's user ID.
- `investor_id` (BIGINT, Foreign Key -> Users.id): Client identifier.
- `investor_name` (VARCHAR): Client full name.
- `investor_email` (VARCHAR): Client email address.
- `investor_status` (VARCHAR): Client status ('ACTIVE', 'SUSPENDED').
- `assigned_at` (TIMESTAMP): Timestamp when client was assigned to broker.
- `virtual_balance` (DECIMAL): Current available virtual cash balance in client account.
- `total_trades` (BIGINT): Total number of executed trades by this client.
- `total_volume` (DECIMAL): Total gross trade volume generated by this client.
- `total_commission_generated` (DECIMAL): Total commission earned by broker from this client.

---

## 3. Admin Allowed Views

### v_admin_user_audit
- `user_id` (BIGINT, Primary Key): Unique user identifier.
- `username` (VARCHAR): User login handle (e.g. 'admin', 'broker_arun', 'investor_rahul').
- `email` (VARCHAR): Account email address.
- `full_name` (VARCHAR): Full name of the user.
- `role` (ENUM): 'ADMIN', 'BROKER', 'INVESTOR'.
- `status` (ENUM): 'ACTIVE', 'INACTIVE'.
- `failed_login_attempts` (INT): Count of consecutive failed password attempts (resets on success).
- `locked_until` (TIMESTAMP, Nullable): Lockout expiry timestamp if account is under brute-force lock.
- `last_login_at` (TIMESTAMP, Nullable): Most recent successful login timestamp.
- `created_at` (TIMESTAMP): Account registration timestamp.

### v_admin_audit_logs
- `log_id` (BIGINT, Primary Key): Unique audit event log ID.
- `user_id` (BIGINT, Nullable): User associated with event.
- `username` (VARCHAR, Nullable): Username of account.
- `role` (VARCHAR, Nullable): User role.
- `action` (VARCHAR): Audit action name (e.g. 'LOGIN_FAILED', 'LOGIN_SUCCESS', 'SECURITY_LOCKOUT', 'EXECUTE_TRADE', 'SYSTEM_SHUTDOWN').
- `entity_type` (VARCHAR): Entity affected (e.g. 'USER', 'ORDER', 'CONFIG').
- `entity_id` (VARCHAR): ID of affected entity.
- `ip_address` (VARCHAR): Remote client IP address.
- `created_at` (TIMESTAMP): Event occurrence timestamp.

### v_admin_trade_facts
- `transaction_id` (BIGINT, Primary Key): Transaction identifier.
- `executed_at` (TIMESTAMP): Trade execution timestamp.
- `side` (ENUM): 'BUY' or 'SELL'.
- `quantity` (INT): Number of shares traded.
- `execution_price` (DECIMAL): Share price.
- `gross_amount` (DECIMAL): Principal turnover value.
- `brokerage_fee` (DECIMAL): Platform brokerage collected.
- `investor_id` (BIGINT, Foreign Key -> Users.id): Investor ID.
- `investor_name` (VARCHAR): Full name of investor.
- `stock_id` (BIGINT, Foreign Key -> Stocks.id): Stock ID.
- `symbol` (VARCHAR): Stock ticker symbol.
- `sector` (VARCHAR): Sector.
- `broker_id` (BIGINT, Nullable): Assigned broker ID (if investor has an assigned broker).
- `broker_commission` (DECIMAL, Nullable): Commission credited to broker.

### Stocks (Base Table)
- `id` (BIGINT, Primary Key): Stock identifier.
- `symbol` (VARCHAR, Unique): Ticker symbol.
- `company_name` (VARCHAR): Company name.
- `sector` (VARCHAR): Sector.
- `exchange` (VARCHAR): Exchange.
- `status` (VARCHAR): 'ACTIVE' or 'HALTED'.

### Commission_Rules (Base Table)
- `id` (INT, Primary Key): Rule identifier.
- `rule_type` (ENUM): 'INVESTOR_BROKERAGE' or 'BROKER_COMMISSION'.
- `rate` (DECIMAL): Fee rate (e.g. 0.0010 for investor brokerage, 0.4000 for broker commission share).
- `min_fee` (DECIMAL): Minimum fee per trade (₹1.00 for investor brokerage).
- `effective_from` (TIMESTAMP): Rule effective start timestamp.
- `is_active` (BOOLEAN): TRUE if currently active.
