-- ==============================================================================
-- StockTrade Demo Users, Accounts & Sample Trades (seed_demo_users.sql)
-- Idempotent Seeding for College Evaluation
-- ==============================================================================

-- 1. Insert Users (Admin, 2 Brokers, 6 Investors)
INSERT INTO Users (id, username, email, password_hash, full_name, role, status, is_demo) VALUES
-- Admin
(1, 'admin', 'admin@stocktrade.local', 'scrypt:32768:8:1$jYdA2SjNL4Lu50gA$51fa154422e47ff80d0deac93407070f442d355d0a9335b612313d61ca46e90b6e090dd86cebac0b69d4b5d55a5399709c9e802c3981774fd3145cdf115afe48', 'System Administrator', 'ADMIN', 'ACTIVE', TRUE),

-- Brokers
(2, 'broker_arun', 'arun@stocktrade.local', 'scrypt:32768:8:1$X1634xhMKfmTQ3BO$17ea7263b245b5cdfdacd5e68e96d7060d12c2c62552d598b5e58e509df1bd9e009fb9027d43364bc3b0a0536f3760279150b03f3fbf020335115dd858c5d885', 'Arun Mehta (Apex Capital)', 'BROKER', 'ACTIVE', TRUE),
(3, 'broker_priya', 'priya@stocktrade.local', 'scrypt:32768:8:1$X1634xhMKfmTQ3BO$17ea7263b245b5cdfdacd5e68e96d7060d12c2c62552d598b5e58e509df1bd9e009fb9027d43364bc3b0a0536f3760279150b03f3fbf020335115dd858c5d885', 'Priya Sharma (BlueChip Securities)', 'BROKER', 'ACTIVE', TRUE),

-- Investors
(4, 'investor_rahul', 'rahul@gmail.com', 'scrypt:32768:8:1$PvVTyrAMKzpnLTJm$0bc0b8e5ea9a2605e2a4bcfaa76de3dbbdd4c9a9752f48d48180483204024fd72c9d09189515eaacedebcbd8ab8b557f1ddc24a0eedee9962993fe4297857e0e', 'Rahul Verma', 'INVESTOR', 'ACTIVE', TRUE),
(5, 'investor_sneha', 'sneha@gmail.com', 'scrypt:32768:8:1$PvVTyrAMKzpnLTJm$0bc0b8e5ea9a2605e2a4bcfaa76de3dbbdd4c9a9752f48d48180483204024fd72c9d09189515eaacedebcbd8ab8b557f1ddc24a0eedee9962993fe4297857e0e', 'Sneha Patel', 'INVESTOR', 'ACTIVE', TRUE),
(6, 'investor_vikram', 'vikram@gmail.com', 'scrypt:32768:8:1$PvVTyrAMKzpnLTJm$0bc0b8e5ea9a2605e2a4bcfaa76de3dbbdd4c9a9752f48d48180483204024fd72c9d09189515eaacedebcbd8ab8b557f1ddc24a0eedee9962993fe4297857e0e', 'Vikram Malhotra', 'INVESTOR', 'ACTIVE', TRUE),
(7, 'investor_ananya', 'ananya@gmail.com', 'scrypt:32768:8:1$PvVTyrAMKzpnLTJm$0bc0b8e5ea9a2605e2a4bcfaa76de3dbbdd4c9a9752f48d48180483204024fd72c9d09189515eaacedebcbd8ab8b557f1ddc24a0eedee9962993fe4297857e0e', 'Ananya Roy', 'INVESTOR', 'ACTIVE', TRUE),
(8, 'investor_karan', 'karan@gmail.com', 'scrypt:32768:8:1$PvVTyrAMKzpnLTJm$0bc0b8e5ea9a2605e2a4bcfaa76de3dbbdd4c9a9752f48d48180483204024fd72c9d09189515eaacedebcbd8ab8b557f1ddc24a0eedee9962993fe4297857e0e', 'Karan Singhania', 'INVESTOR', 'ACTIVE', TRUE),
(9, 'investor_rohit', 'rohit@gmail.com', 'scrypt:32768:8:1$PvVTyrAMKzpnLTJm$0bc0b8e5ea9a2605e2a4bcfaa76de3dbbdd4c9a9752f48d48180483204024fd72c9d09189515eaacedebcbd8ab8b557f1ddc24a0eedee9962993fe4297857e0e', 'Rohit Sen (Independent)', 'INVESTOR', 'ACTIVE', TRUE)
ON DUPLICATE KEY UPDATE full_name=VALUES(full_name);

-- 2. Insert Accounts (Only Investors have virtual balances, initially 1,00,000 INR)
INSERT INTO Accounts (id, user_id, virtual_balance, currency, status) VALUES
(1, 4, 100000.00, 'INR', 'ACTIVE'),
(2, 5, 100000.00, 'INR', 'ACTIVE'),
(3, 6, 100000.00, 'INR', 'ACTIVE'),
(4, 7, 100000.00, 'INR', 'ACTIVE'),
(5, 8, 100000.00, 'INR', 'ACTIVE'),
(6, 9, 100000.00, 'INR', 'ACTIVE')
ON DUPLICATE KEY UPDATE status=VALUES(status);

-- 3. Opening Grant Ledger Entries (Only if ledger empty for that account)
INSERT INTO Account_Ledger (account_id, entry_type, amount, balance_after, reference_type, reference_id, note)
SELECT a.id, 'OPENING_GRANT', 100000.00, 100000.00, 'SYSTEM', CONCAT('GRANT_', a.id), 'Virtual Opening Signup Grant'
FROM Accounts a
WHERE NOT EXISTS (
    SELECT 1 FROM Account_Ledger al 
    WHERE al.account_id = a.id AND al.entry_type = 'OPENING_GRANT'
);

-- 4. Broker-Client Relationship Assignments
-- Broker Arun (id=2) manages Rahul (4), Sneha (5), Vikram (6)
-- Broker Priya (id=3) manages Ananya (7), Karan (8)
-- Rohit (9) is independent (no active broker)
INSERT INTO Broker_Clients (broker_id, investor_id, status, assigned_at) VALUES
(2, 4, 'ACTIVE', CURRENT_TIMESTAMP),
(2, 5, 'ACTIVE', CURRENT_TIMESTAMP),
(2, 6, 'ACTIVE', CURRENT_TIMESTAMP),
(3, 7, 'ACTIVE', CURRENT_TIMESTAMP),
(3, 8, 'ACTIVE', CURRENT_TIMESTAMP)
ON DUPLICATE KEY UPDATE status=VALUES(status);
