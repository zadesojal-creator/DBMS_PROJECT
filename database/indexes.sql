-- ==============================================================================
-- StockTrade Performance & Covering Indexes (indexes.sql)
-- Optimizes high-throughput time-series, ledger reconciliation, and joins
-- ==============================================================================

-- 1. High-frequency price observations (time-series chart queries & rollups)
CREATE INDEX idx_stock_prices_stock_time 
    ON Stock_Prices (stock_id, recorded_at DESC);

CREATE INDEX idx_stock_prices_time 
    ON Stock_Prices (recorded_at);

-- 2. Orders & Execution lookups
CREATE INDEX idx_orders_user_time 
    ON Orders (user_id, created_at DESC);

CREATE INDEX idx_orders_stock_status 
    ON Orders (stock_id, status);

-- 3. Financial Transactions history & filtering
CREATE INDEX idx_trans_user_time 
    ON Transactions (user_id, executed_at DESC);

CREATE INDEX idx_trans_stock_time 
    ON Transactions (stock_id, executed_at DESC);

-- 4. Account Ledger queries (reconciliation invariant & statements)
CREATE INDEX idx_ledger_account_time 
    ON Account_Ledger (account_id, created_at DESC);

CREATE INDEX idx_ledger_ref 
    ON Account_Ledger (reference_type, reference_id);

-- 5. Broker Commission queries & aggregations
CREATE INDEX idx_commissions_broker_time 
    ON Commissions (broker_id, created_at DESC);

CREATE INDEX idx_commissions_investor 
    ON Commissions (investor_id);

-- 6. Price Alerts active monitor (used by background tick simulator)
CREATE INDEX idx_alerts_active_stock 
    ON Price_Alerts (status, stock_id);

-- 7. Broker Client relationships
CREATE INDEX idx_bc_broker_status 
    ON Broker_Clients (broker_id, status);

CREATE INDEX idx_bc_investor_status 
    ON Broker_Clients (investor_id, status);
