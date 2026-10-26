-- ==============================================================================
-- StockTrade Purpose-Built Database Views (views.sql)
-- Safe, Restricted Projection Surface for Application & AI Read-Only Assistant
-- ==============================================================================

-- 1. Latest Market Prices & Metrics
CREATE OR REPLACE VIEW v_market_latest AS
SELECT 
    s.id AS stock_id,
    s.symbol,
    s.company_name,
    s.sector,
    s.exchange,
    s.status,
    cp.price AS current_price,
    cp.previous_close,
    ROUND(cp.price - cp.previous_close, 4) AS day_change,
    ROUND(((cp.price - cp.previous_close) / NULLIF(cp.previous_close, 0)) * 100, 2) AS day_change_pct,
    cp.day_open,
    cp.day_high,
    cp.day_low,
    cp.volume,
    cp.updated_at
FROM Stocks s
JOIN Current_Prices cp ON s.id = cp.stock_id;

-- 2. Investor Portfolio View (Safe, no passwords, computed values)
CREATE OR REPLACE VIEW v_investor_portfolio AS
SELECT 
    h.user_id,
    h.stock_id,
    s.symbol,
    s.company_name,
    s.sector,
    h.quantity,
    h.avg_cost,
    ROUND(h.quantity * h.avg_cost, 2) AS cost_basis,
    cp.price AS current_price,
    ROUND(h.quantity * cp.price, 2) AS market_value,
    ROUND(h.quantity * (cp.price - h.avg_cost), 2) AS unrealized_pnl,
    CASE 
        WHEN (h.quantity * h.avg_cost) > 0 
        THEN ROUND(((cp.price - h.avg_cost) / h.avg_cost) * 100, 2) 
        ELSE NULL 
    END AS return_pct,
    ROUND(cp.price - cp.previous_close, 4) AS day_change,
    ROUND(((cp.price - cp.previous_close) / NULLIF(cp.previous_close, 0)) * 100, 2) AS day_change_pct,
    h.updated_at
FROM Holdings h
JOIN Stocks s ON h.stock_id = s.id
JOIN Current_Prices cp ON s.id = cp.stock_id
WHERE h.quantity > 0;

-- 3. Investor Transactions History View
CREATE OR REPLACE VIEW v_investor_transactions AS
SELECT 
    t.id AS transaction_id,
    t.order_id,
    t.user_id,
    t.stock_id,
    s.symbol,
    s.company_name,
    s.sector,
    t.side,
    t.quantity,
    t.execution_price,
    t.gross_amount,
    t.brokerage_fee,
    t.net_amount,
    t.realized_pnl,
    t.executed_at
FROM Transactions t
JOIN Stocks s ON t.stock_id = s.id;

-- 4. Broker Client Transactions View (Filtered by Broker Assignment)
CREATE OR REPLACE VIEW v_broker_client_transactions AS
SELECT 
    t.id AS transaction_id,
    bc.broker_id,
    t.user_id AS investor_id,
    u.full_name AS investor_name,
    t.stock_id,
    s.symbol,
    s.company_name,
    t.side,
    t.quantity,
    t.execution_price,
    t.gross_amount,
    t.brokerage_fee,
    t.net_amount,
    c.commission_amount AS broker_commission_earned,
    t.executed_at
FROM Transactions t
JOIN Broker_Clients bc ON t.user_id = bc.investor_id AND bc.status = 'ACTIVE'
JOIN Users u ON t.user_id = u.id
JOIN Stocks s ON t.stock_id = s.id
LEFT JOIN Commissions c ON t.id = c.transaction_id;

-- 5. Broker Commissions View
CREATE OR REPLACE VIEW v_broker_commissions AS
SELECT 
    c.id AS commission_id,
    c.transaction_id,
    c.broker_id,
    c.investor_id,
    u.full_name AS investor_name,
    s.symbol,
    t.side,
    t.quantity,
    t.execution_price,
    c.base_brokerage,
    c.rate_applied,
    c.commission_amount,
    c.created_at
FROM Commissions c
JOIN Users u ON c.investor_id = u.id
JOIN Transactions t ON c.transaction_id = t.id
JOIN Stocks s ON t.stock_id = s.id;

-- 6. Broker Clients Summary View
CREATE OR REPLACE VIEW v_broker_client_summary AS
SELECT 
    bc.broker_id,
    bc.investor_id,
    u.full_name AS investor_name,
    u.email AS investor_email,
    u.status AS investor_status,
    bc.assigned_at,
    a.virtual_balance,
    COUNT(DISTINCT t.id) AS total_trades,
    COALESCE(SUM(t.gross_amount), 0.00) AS total_volume,
    COALESCE(SUM(c.commission_amount), 0.00) AS total_commission_generated
FROM Broker_Clients bc
JOIN Users u ON bc.investor_id = u.id
JOIN Accounts a ON u.id = a.user_id
LEFT JOIN Transactions t ON u.id = t.user_id
LEFT JOIN Commissions c ON t.id = c.transaction_id AND c.broker_id = bc.broker_id
WHERE bc.status = 'ACTIVE'
GROUP BY bc.broker_id, bc.investor_id, u.full_name, u.email, u.status, bc.assigned_at, a.virtual_balance;

-- 7. Admin Global Trade Facts View (Safe Aggregations for Admin AI & Analytics)
CREATE OR REPLACE VIEW v_admin_trade_facts AS
SELECT 
    t.id AS transaction_id,
    t.executed_at,
    t.side,
    t.quantity,
    t.execution_price,
    t.gross_amount,
    t.brokerage_fee,
    t.user_id AS investor_id,
    u.full_name AS investor_name,
    s.id AS stock_id,
    s.symbol,
    s.sector,
    bc.broker_id,
    c.commission_amount AS broker_commission
FROM Transactions t
JOIN Users u ON t.user_id = u.id
JOIN Stocks s ON t.stock_id = s.id
LEFT JOIN Broker_Clients bc ON t.user_id = bc.investor_id AND bc.status = 'ACTIVE'
LEFT JOIN Commissions c ON t.id = c.transaction_id;

-- 8. Admin User Account & Security Audit View (Safe, no password hashes)
CREATE OR REPLACE VIEW v_admin_user_audit AS
SELECT 
    u.id AS user_id,
    u.username,
    u.email,
    u.full_name,
    u.role,
    u.status,
    u.failed_login_attempts,
    u.locked_until,
    u.last_login_at,
    u.created_at
FROM Users u;

-- 9. Admin Security Audit Logs View
CREATE OR REPLACE VIEW v_admin_audit_logs AS
SELECT 
    a.id AS log_id,
    a.user_id,
    COALESCE(u.username, a.entity_id, 'unregistered_or_invalid') AS username,
    COALESCE(u.role, 'UNKNOWN') AS role,
    a.action,
    a.entity_type,
    a.entity_id,
    a.ip_address,
    a.created_at
FROM Audit_Logs a
LEFT JOIN Users u ON a.user_id = u.id;

