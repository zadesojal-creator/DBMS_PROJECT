-- ==============================================================================
-- StockTrade Default Commission Rules & System Settings (seed_settings_rules.sql)
-- ==============================================================================

-- 1. Commission Rules
INSERT INTO Commission_Rules (rule_type, rate, min_fee, effective_from, is_active)
SELECT 'INVESTOR_BROKERAGE', 0.0010, 1.00, CURRENT_TIMESTAMP, TRUE
WHERE NOT EXISTS (SELECT 1 FROM Commission_Rules WHERE rule_type = 'INVESTOR_BROKERAGE');

INSERT INTO Commission_Rules (rule_type, rate, min_fee, effective_from, is_active)
SELECT 'BROKER_COMMISSION', 0.4000, 0.00, CURRENT_TIMESTAMP, TRUE
WHERE NOT EXISTS (SELECT 1 FROM Commission_Rules WHERE rule_type = 'BROKER_COMMISSION');

-- 2. System Settings
INSERT INTO System_Settings (key_name, value_text, description) VALUES
('SIMULATOR_INTERVAL_SECONDS', '5', 'Interval in seconds between market price ticks'),
('ALWAYS_OPEN', 'true', 'Simulate trading continuously 24x7 for college demo purposes'),
('MAX_TICK_PCT', '0.005', 'Maximum percentage change clamped per tick (0.5%)'),
('CIRCUIT_LIMIT_PCT', '0.10', 'Daily circuit limit percentage (10%) from previous close'),
('PRICE_MOVED_TOLERANCE_PCT', '0.01', 'Tolerance threshold (1%) before requiring reconfirmation'),
('MARKET_START_TIME', '09:15:00', 'Official simulated market opening time (IST)'),
('MARKET_END_TIME', '15:30:00', 'Official simulated market closing time (IST)'),
('SIGNUP_GRANT_AMOUNT', '100000.00', 'Virtual signup grant credited to each new investor')
ON DUPLICATE KEY UPDATE value_text = VALUES(value_text), description = VALUES(description);
