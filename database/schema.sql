-- ==============================================================================
-- StockTrade Database Schema (schema.sql)
-- MySQL 8.0+ (InnoDB, utf8mb4)
-- Strict Referential Integrity (ON DELETE RESTRICT), Check Constraints, Decimals
-- ==============================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS Users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NULL,
    role ENUM('ADMIN', 'BROKER', 'INVESTOR') NOT NULL,
    status ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    is_demo BOOLEAN NOT NULL DEFAULT FALSE,
    failed_login_attempts INT NOT NULL DEFAULT 0,
    locked_until TIMESTAMP NULL DEFAULT NULL,
    last_login_at TIMESTAMP NULL DEFAULT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_role_status (role, status),
    INDEX idx_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Accounts Table (1:1 with Investor/Broker)
CREATE TABLE IF NOT EXISTS Accounts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    virtual_balance DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    status ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_accounts_user FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE RESTRICT,
    CONSTRAINT chk_accounts_balance CHECK (virtual_balance >= 0.00)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Stocks Table
CREATE TABLE IF NOT EXISTS Stocks (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    company_name VARCHAR(150) NOT NULL,
    sector VARCHAR(50) NOT NULL,
    exchange ENUM('NSE', 'BSE') NOT NULL DEFAULT 'NSE',
    status ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_stocks_sector (sector),
    INDEX idx_stocks_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Current_Prices Table (1:1 cache per stock)
CREATE TABLE IF NOT EXISTS Current_Prices (
    stock_id BIGINT PRIMARY KEY,
    price DECIMAL(12,4) NOT NULL,
    previous_close DECIMAL(12,4) NOT NULL,
    day_open DECIMAL(12,4) NOT NULL,
    day_high DECIMAL(12,4) NOT NULL,
    day_low DECIMAL(12,4) NOT NULL,
    volume BIGINT UNSIGNED NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_curr_prices_stock FOREIGN KEY (stock_id) REFERENCES Stocks(id) ON DELETE RESTRICT,
    CONSTRAINT chk_curr_price_positive CHECK (price > 0.0000)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Stock_Prices Table (1-minute observations)
CREATE TABLE IF NOT EXISTS Stock_Prices (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_id BIGINT NOT NULL,
    price DECIMAL(12,4) NOT NULL,
    volume INT UNSIGNED NOT NULL DEFAULT 0,
    source ENUM('SEEDED', 'SIMULATED') NOT NULL DEFAULT 'SIMULATED',
    recorded_at TIMESTAMP NOT NULL,
    CONSTRAINT fk_stock_prices_stock FOREIGN KEY (stock_id) REFERENCES Stocks(id) ON DELETE RESTRICT,
    CONSTRAINT chk_stock_price_val CHECK (price > 0.0000)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Stock_Price_Hourly Table (Aggregated Rollups)
CREATE TABLE IF NOT EXISTS Stock_Price_Hourly (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_id BIGINT NOT NULL,
    bucket_start TIMESTAMP NOT NULL,
    open_price DECIMAL(12,4) NOT NULL,
    high_price DECIMAL(12,4) NOT NULL,
    low_price DECIMAL(12,4) NOT NULL,
    close_price DECIMAL(12,4) NOT NULL,
    volume BIGINT UNSIGNED NOT NULL DEFAULT 0,
    CONSTRAINT fk_hourly_stock FOREIGN KEY (stock_id) REFERENCES Stocks(id) ON DELETE RESTRICT,
    UNIQUE KEY uq_stock_hourly (stock_id, bucket_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Orders Table
CREATE TABLE IF NOT EXISTS Orders (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    stock_id BIGINT NOT NULL,
    side ENUM('BUY', 'SELL') NOT NULL,
    quantity INT UNSIGNED NOT NULL,
    estimated_price DECIMAL(12,4) NOT NULL,
    executed_price DECIMAL(12,4) NULL,
    status ENUM('PENDING', 'EXECUTED', 'REJECTED', 'FAILED') NOT NULL DEFAULT 'PENDING',
    reject_reason VARCHAR(255) NULL,
    idempotency_key VARCHAR(64) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP NULL DEFAULT NULL,
    CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE RESTRICT,
    CONSTRAINT fk_orders_stock FOREIGN KEY (stock_id) REFERENCES Stocks(id) ON DELETE RESTRICT,
    CONSTRAINT chk_order_qty CHECK (quantity > 0),
    UNIQUE KEY uq_orders_user_idempotency (user_id, idempotency_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. Holdings Table
CREATE TABLE IF NOT EXISTS Holdings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    stock_id BIGINT NOT NULL,
    quantity INT UNSIGNED NOT NULL DEFAULT 0,
    avg_cost DECIMAL(12,4) NOT NULL DEFAULT 0.0000,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_holdings_user FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE RESTRICT,
    CONSTRAINT fk_holdings_stock FOREIGN KEY (stock_id) REFERENCES Stocks(id) ON DELETE RESTRICT,
    CONSTRAINT chk_holdings_qty CHECK (quantity >= 0),
    UNIQUE KEY uq_holdings_user_stock (user_id, stock_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. Transactions Table (Financial Trade Records)
CREATE TABLE IF NOT EXISTS Transactions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT NOT NULL UNIQUE,
    user_id BIGINT NOT NULL,
    stock_id BIGINT NOT NULL,
    side ENUM('BUY', 'SELL') NOT NULL,
    quantity INT UNSIGNED NOT NULL,
    execution_price DECIMAL(12,4) NOT NULL,
    gross_amount DECIMAL(15,2) NOT NULL,
    brokerage_fee DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    net_amount DECIMAL(15,2) NOT NULL,
    realized_pnl DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    executed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_trans_order FOREIGN KEY (order_id) REFERENCES Orders(id) ON DELETE RESTRICT,
    CONSTRAINT fk_trans_user FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE RESTRICT,
    CONSTRAINT fk_trans_stock FOREIGN KEY (stock_id) REFERENCES Stocks(id) ON DELETE RESTRICT,
    CONSTRAINT chk_trans_qty CHECK (quantity > 0),
    CONSTRAINT chk_trans_price CHECK (execution_price > 0.0000),
    CONSTRAINT chk_trans_gross CHECK (gross_amount >= 0.00),
    CONSTRAINT chk_trans_brokerage CHECK (brokerage_fee >= 0.00)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. Account_Ledger Table (Strictly Append-Only)
CREATE TABLE IF NOT EXISTS Account_Ledger (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    account_id BIGINT NOT NULL,
    entry_type ENUM('OPENING_GRANT', 'DEPOSIT', 'BUY', 'SELL', 'FEE', 'ADJUSTMENT') NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    balance_after DECIMAL(15,2) NOT NULL,
    reference_type VARCHAR(50) NOT NULL,
    reference_id VARCHAR(64) NOT NULL,
    note VARCHAR(255) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ledger_account FOREIGN KEY (account_id) REFERENCES Accounts(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. Broker_Clients Table (M:N Assignment History with One Active Broker per Investor)
CREATE TABLE IF NOT EXISTS Broker_Clients (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    broker_id BIGINT NOT NULL,
    investor_id BIGINT NOT NULL,
    status ENUM('ACTIVE', 'ENDED') NOT NULL DEFAULT 'ACTIVE',
    assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL DEFAULT NULL,
    -- Generated column for active broker constraint: only non-null when ACTIVE
    active_investor_key BIGINT GENERATED ALWAYS AS (IF(status = 'ACTIVE', investor_id, NULL)) VIRTUAL,
    CONSTRAINT fk_bc_broker FOREIGN KEY (broker_id) REFERENCES Users(id) ON DELETE RESTRICT,
    CONSTRAINT fk_bc_investor FOREIGN KEY (investor_id) REFERENCES Users(id) ON DELETE RESTRICT,
    UNIQUE KEY uq_one_active_broker_per_investor (active_investor_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 12. Commission_Rules Table
CREATE TABLE IF NOT EXISTS Commission_Rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rule_type ENUM('INVESTOR_BROKERAGE', 'BROKER_COMMISSION') NOT NULL,
    rate DECIMAL(6,5) NOT NULL,
    min_fee DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    effective_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_comm_rule_rate CHECK (rate >= 0.00000 AND rate <= 1.00000),
    CONSTRAINT chk_comm_rule_min_fee CHECK (min_fee >= 0.00)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 13. Commissions Table (Platform-funded, 1:1 with executed transactions)
CREATE TABLE IF NOT EXISTS Commissions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    transaction_id BIGINT NOT NULL UNIQUE,
    broker_id BIGINT NOT NULL,
    investor_id BIGINT NOT NULL,
    base_brokerage DECIMAL(15,2) NOT NULL,
    rate_applied DECIMAL(6,5) NOT NULL,
    commission_amount DECIMAL(15,2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_comm_trans FOREIGN KEY (transaction_id) REFERENCES Transactions(id) ON DELETE RESTRICT,
    CONSTRAINT fk_comm_broker FOREIGN KEY (broker_id) REFERENCES Users(id) ON DELETE RESTRICT,
    CONSTRAINT fk_comm_investor FOREIGN KEY (investor_id) REFERENCES Users(id) ON DELETE RESTRICT,
    CONSTRAINT chk_comm_amount CHECK (commission_amount >= 0.00),
    CONSTRAINT chk_comm_base CHECK (base_brokerage >= 0.00)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 14. Watchlist Table
CREATE TABLE IF NOT EXISTS Watchlist (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    stock_id BIGINT NOT NULL,
    added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_wl_user FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE RESTRICT,
    CONSTRAINT fk_wl_stock FOREIGN KEY (stock_id) REFERENCES Stocks(id) ON DELETE RESTRICT,
    UNIQUE KEY uq_watchlist_user_stock (user_id, stock_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 15. Price_Alerts Table
CREATE TABLE IF NOT EXISTS Price_Alerts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    stock_id BIGINT NOT NULL,
    target_price DECIMAL(12,4) NOT NULL,
    condition_type ENUM('ABOVE', 'BELOW') NOT NULL,
    status ENUM('ACTIVE', 'TRIGGERED', 'CANCELLED') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    triggered_at TIMESTAMP NULL DEFAULT NULL,
    CONSTRAINT fk_alert_user FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE RESTRICT,
    CONSTRAINT fk_alert_stock FOREIGN KEY (stock_id) REFERENCES Stocks(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 16. Audit_Logs Table
CREATE TABLE IF NOT EXISTS Audit_Logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NULL,
    action VARCHAR(64) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(64) NULL,
    details JSON NULL,
    ip_address VARCHAR(45) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE RESTRICT,
    INDEX idx_audit_created (created_at),
    INDEX idx_audit_action (action)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 17. AI_Query_History Table
CREATE TABLE IF NOT EXISTS AI_Query_History (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    prompt TEXT NOT NULL,
    generated_sql TEXT NULL,
    tables_used JSON NULL,
    validation_status ENUM('VALID', 'REJECTED') NOT NULL,
    execution_status ENUM('SUCCESS', 'FAILED', 'SKIPPED') NOT NULL,
    error_code VARCHAR(64) NULL,
    duration_ms INT UNSIGNED NULL,
    row_count INT UNSIGNED NULL,
    provider VARCHAR(32) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ai_history_user FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE RESTRICT,
    INDEX idx_ai_history_user (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 18. Saved_Reports Table
CREATE TABLE IF NOT EXISTS Saved_Reports (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT NULL,
    query_sql TEXT NOT NULL,
    last_run_at TIMESTAMP NULL DEFAULT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_saved_reports_user FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 19. System_Settings Table
CREATE TABLE IF NOT EXISTS System_Settings (
    key_name VARCHAR(64) PRIMARY KEY,
    value_text TEXT NOT NULL,
    description VARCHAR(255) NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 20. System_Events Table
CREATE TABLE IF NOT EXISTS System_Events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(64) NOT NULL,
    severity ENUM('INFO', 'WARNING', 'ERROR', 'CRITICAL') NOT NULL DEFAULT 'INFO',
    details JSON NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_events_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 21. Portfolio_Snapshots Table (Daily Historical Performance)
CREATE TABLE IF NOT EXISTS Portfolio_Snapshots (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    snapshot_date DATE NOT NULL,
    cash_balance DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    holdings_value DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    total_portfolio_value DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    total_pnl DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_snap_user FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE RESTRICT,
    UNIQUE KEY uq_user_snapshot_date (user_id, snapshot_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 22. Order_Events Table (Append-Only Event Sourcing for Order Lifecycle)
CREATE TABLE IF NOT EXISTS Order_Events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT NOT NULL,
    from_status ENUM('NEW', 'PENDING', 'EXECUTED', 'REJECTED', 'FAILED', 'CANCELLED') NULL,
    to_status ENUM('PENDING', 'EXECUTED', 'REJECTED', 'FAILED', 'CANCELLED') NOT NULL,
    reason VARCHAR(255) NULL,
    event_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_oe_order FOREIGN KEY (order_id) REFERENCES Orders(id) ON DELETE RESTRICT,
    INDEX idx_oe_order_time (order_id, event_timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
