-- ==============================================================================
-- StockTrade Database Triggers (triggers.sql)
-- Enforces Financial Immutability, Role Validation, and Integrity
-- ==============================================================================

DELIMITER $$

-- 1. Ledger Immutability: Block all UPDATE operations on Account_Ledger
DROP TRIGGER IF EXISTS trg_ledger_block_update$$
CREATE TRIGGER trg_ledger_block_update
BEFORE UPDATE ON Account_Ledger
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Account_Ledger is strictly append-only: updates are prohibited';
END$$

-- 2. Ledger Immutability: Block all DELETE operations on Account_Ledger
DROP TRIGGER IF EXISTS trg_ledger_block_delete$$
CREATE TRIGGER trg_ledger_block_delete
BEFORE DELETE ON Account_Ledger
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Account_Ledger is strictly append-only: deletions are prohibited';
END$$

-- 3. Broker-Client Role Validation: Verify roles before insertion
DROP TRIGGER IF EXISTS trg_broker_clients_role_insert$$
CREATE TRIGGER trg_broker_clients_role_insert
BEFORE INSERT ON Broker_Clients
FOR EACH ROW
BEGIN
    DECLARE v_broker_role VARCHAR(20);
    DECLARE v_investor_role VARCHAR(20);

    SELECT role INTO v_broker_role FROM Users WHERE id = NEW.broker_id;
    SELECT role INTO v_investor_role FROM Users WHERE id = NEW.investor_id;

    IF v_broker_role IS NULL OR v_broker_role != 'BROKER' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Broker assignment error: broker_id must have role BROKER';
    END IF;

    IF v_investor_role IS NULL OR v_investor_role != 'INVESTOR' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Broker assignment error: investor_id must have role INVESTOR';
    END IF;
END$$

-- 4. Broker-Client Role Validation: Verify roles before update
DROP TRIGGER IF EXISTS trg_broker_clients_role_update$$
CREATE TRIGGER trg_broker_clients_role_update
BEFORE UPDATE ON Broker_Clients
FOR EACH ROW
BEGIN
    DECLARE v_broker_role VARCHAR(20);
    DECLARE v_investor_role VARCHAR(20);

    SELECT role INTO v_broker_role FROM Users WHERE id = NEW.broker_id;
    SELECT role INTO v_investor_role FROM Users WHERE id = NEW.investor_id;

    IF v_broker_role != 'BROKER' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Broker assignment error: broker_id must have role BROKER';
    END IF;

    IF v_investor_role != 'INVESTOR' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Broker assignment error: investor_id must have role INVESTOR';
    END IF;
END$$

-- 5. Transactions Immutability: Block all UPDATE operations
DROP TRIGGER IF EXISTS trg_transactions_block_update$$
CREATE TRIGGER trg_transactions_block_update
BEFORE UPDATE ON Transactions
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Transactions table is strictly append-only: updates are prohibited';
END$$

-- 6. Transactions Immutability: Block all DELETE operations
DROP TRIGGER IF EXISTS trg_transactions_block_delete$$
CREATE TRIGGER trg_transactions_block_delete
BEFORE DELETE ON Transactions
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Transactions table is strictly append-only: deletions are prohibited';
END$$

-- 7. Commissions Immutability: Block all UPDATE operations
DROP TRIGGER IF EXISTS trg_commissions_block_update$$
CREATE TRIGGER trg_commissions_block_update
BEFORE UPDATE ON Commissions
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Commissions table is strictly append-only: updates are prohibited';
END$$

-- 8. Commissions Immutability: Block all DELETE operations
DROP TRIGGER IF EXISTS trg_commissions_block_delete$$
CREATE TRIGGER trg_commissions_block_delete
BEFORE DELETE ON Commissions
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Commissions table is strictly append-only: deletions are prohibited';
END$$

-- 9. Orders Terminal Immutability: Prevent updates to completed orders
DROP TRIGGER IF EXISTS trg_orders_block_terminal_update$$
CREATE TRIGGER trg_orders_block_terminal_update
BEFORE UPDATE ON Orders
FOR EACH ROW
BEGIN
    IF OLD.status IN ('EXECUTED', 'REJECTED', 'FAILED') THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Terminal orders are immutable: updates to completed orders are prohibited';
    END IF;
END$$

-- 10. Orders Immutability: Prevent deletion of orders audit trail
DROP TRIGGER IF EXISTS trg_orders_block_delete$$
CREATE TRIGGER trg_orders_block_delete
BEFORE DELETE ON Orders
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Orders are immutable audit records: deletions are prohibited';
END$$

-- 11. Audit_Logs Immutability: Block updates and deletions
DROP TRIGGER IF EXISTS trg_audit_logs_block_update$$
CREATE TRIGGER trg_audit_logs_block_update
BEFORE UPDATE ON Audit_Logs
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Audit_Logs table is strictly append-only: updates are prohibited';
END$$

DROP TRIGGER IF EXISTS trg_audit_logs_block_delete$$
CREATE TRIGGER trg_audit_logs_block_delete
BEFORE DELETE ON Audit_Logs
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Audit_Logs table is strictly append-only: deletions are prohibited';
END$$

-- 12. Order_Events Audit Trail: Automatically record order lifecycle events
DROP TRIGGER IF EXISTS trg_orders_audit_insert$$
CREATE TRIGGER trg_orders_audit_insert
AFTER INSERT ON Orders
FOR EACH ROW
BEGIN
    INSERT INTO Order_Events (order_id, from_status, to_status, reason)
    VALUES (NEW.id, 'NEW', NEW.status, NEW.reject_reason);
END$$

DROP TRIGGER IF EXISTS trg_orders_audit_update$$
CREATE TRIGGER trg_orders_audit_update
AFTER UPDATE ON Orders
FOR EACH ROW
BEGIN
    IF OLD.status != NEW.status THEN
        INSERT INTO Order_Events (order_id, from_status, to_status, reason)
        VALUES (NEW.id, OLD.status, NEW.status, NEW.reject_reason);
    END IF;
END$$

-- 13. Order_Events Immutability: Block all UPDATE and DELETE operations
DROP TRIGGER IF EXISTS trg_order_events_block_update$$
CREATE TRIGGER trg_order_events_block_update
BEFORE UPDATE ON Order_Events
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Order_Events audit trail is strictly append-only: updates are prohibited';
END$$

DROP TRIGGER IF EXISTS trg_order_events_block_delete$$
CREATE TRIGGER trg_order_events_block_delete
BEFORE DELETE ON Order_Events
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Order_Events audit trail is strictly append-only: deletions are prohibited';
END$$

DELIMITER ;
