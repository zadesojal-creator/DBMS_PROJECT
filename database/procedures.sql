-- ==============================================================================
-- StockTrade Stored Procedures (procedures.sql)
-- sp_execute_trade: Authoritative Atomic Trade Execution with Strict Row Locking
-- ==============================================================================

DELIMITER $$

DROP PROCEDURE IF EXISTS sp_execute_trade$$

CREATE PROCEDURE sp_execute_trade(
    IN p_user_id BIGINT,
    IN p_stock_id BIGINT,
    IN p_side VARCHAR(4),
    IN p_quantity INT,
    IN p_idempotency_key VARCHAR(64),
    OUT p_order_id BIGINT,
    OUT p_transaction_id BIGINT,
    OUT p_execution_price DECIMAL(12,4),
    OUT p_status VARCHAR(20),
    OUT p_message VARCHAR(255)
)
proc_label: BEGIN
    -- Local variables
    DECLARE v_account_id BIGINT;
    DECLARE v_virtual_balance DECIMAL(15,2);
    DECLARE v_account_status VARCHAR(20);
    DECLARE v_stock_status VARCHAR(20);
    DECLARE v_curr_price DECIMAL(12,4);
    DECLARE v_holding_id BIGINT DEFAULT NULL;
    DECLARE v_holding_qty INT DEFAULT 0;
    DECLARE v_holding_avg_cost DECIMAL(12,4) DEFAULT 0.0000;
    
    DECLARE v_gross_amount DECIMAL(15,2);
    DECLARE v_brokerage_rate DECIMAL(6,5) DEFAULT 0.0010;
    DECLARE v_brokerage_min DECIMAL(15,2) DEFAULT 1.00;
    DECLARE v_brokerage_fee DECIMAL(15,2);
    DECLARE v_net_amount DECIMAL(15,2);
    DECLARE v_balance_after DECIMAL(15,2);
    DECLARE v_balance_after_fee DECIMAL(15,2);
    DECLARE v_realized_pnl DECIMAL(15,2) DEFAULT 0.00;
    DECLARE v_new_avg_cost DECIMAL(12,4);
    DECLARE v_new_qty INT;
    
    DECLARE v_active_broker_id BIGINT DEFAULT NULL;
    DECLARE v_broker_commission_rate DECIMAL(6,5) DEFAULT 0.40;
    DECLARE v_commission_amount DECIMAL(15,2) DEFAULT 0.00;
    
    DECLARE v_existing_order_id BIGINT DEFAULT NULL;
    DECLARE v_existing_status VARCHAR(20);

    -- Declare exit handler for SQLEXCEPTION
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        GET DIAGNOSTICS CONDITION 1 p_message = MESSAGE_TEXT;
        ROLLBACK;
        SET p_status = 'FAILED';
        SET p_order_id = NULL;
        SET p_transaction_id = NULL;
        SET p_execution_price = NULL;
    END;

    -- 1. Check idempotency first (outside locking transaction)
    SELECT id, status, executed_price 
    INTO v_existing_order_id, v_existing_status, p_execution_price
    FROM Orders 
    WHERE user_id = p_user_id AND idempotency_key = p_idempotency_key
    LIMIT 1;

    IF v_existing_order_id IS NOT NULL THEN
        SET p_order_id = v_existing_order_id;
        SET p_status = v_existing_status;
        SELECT id INTO p_transaction_id FROM Transactions WHERE order_id = v_existing_order_id LIMIT 1;
        SET p_message = 'Order already processed (idempotent replay)';
        LEAVE proc_label;
    END IF;

    -- 2. Input parameter validation
    IF p_quantity <= 0 THEN
        SET p_status = 'REJECTED';
        SET p_message = 'Quantity must be a positive integer';
        LEAVE proc_label;
    END IF;

    IF p_side NOT IN ('BUY', 'SELL') THEN
        SET p_status = 'REJECTED';
        SET p_message = 'Side must be either BUY or SELL';
        LEAVE proc_label;
    END IF;

    -- Fetch active brokerage rule
    SELECT rate, min_fee INTO v_brokerage_rate, v_brokerage_min
    FROM Commission_Rules
    WHERE rule_type = 'INVESTOR_BROKERAGE' AND is_active = TRUE
    ORDER BY effective_from DESC LIMIT 1;

    -- Fetch active broker commission rule
    SELECT rate INTO v_broker_commission_rate
    FROM Commission_Rules
    WHERE rule_type = 'BROKER_COMMISSION' AND is_active = TRUE
    ORDER BY effective_from DESC LIMIT 1;

    -- 3. BEGIN ATOMIC TRANSACTION WITH ORDERED LOCKING
    START TRANSACTION;

    -- Lock Order Step 1: Lock User Account row
    SELECT id, virtual_balance, status 
    INTO v_account_id, v_virtual_balance, v_account_status
    FROM Accounts
    WHERE user_id = p_user_id
    FOR UPDATE;

    IF v_account_id IS NULL OR v_account_status != 'ACTIVE' THEN
        ROLLBACK;
        SET p_status = 'REJECTED';
        SET p_message = 'User account not found or inactive';
        LEAVE proc_label;
    END IF;

    -- Re-check idempotency under lock to handle simultaneous requests with identical idempotency key
    SELECT id, status, executed_price 
    INTO v_existing_order_id, v_existing_status, p_execution_price
    FROM Orders 
    WHERE user_id = p_user_id AND idempotency_key = p_idempotency_key
    LIMIT 1;

    IF v_existing_order_id IS NOT NULL THEN
        ROLLBACK;
        SET p_order_id = v_existing_order_id;
        SET p_status = v_existing_status;
        SELECT id INTO p_transaction_id FROM Transactions WHERE order_id = v_existing_order_id LIMIT 1;
        SET p_message = 'Order already processed (idempotent replay)';
        LEAVE proc_label;
    END IF;

    -- Lock Order Step 2: Lock Holding row (if existing)
    SELECT id, quantity, avg_cost
    INTO v_holding_id, v_holding_qty, v_holding_avg_cost
    FROM Holdings
    WHERE user_id = p_user_id AND stock_id = p_stock_id
    FOR UPDATE;

    -- Lock Order Step 3: Lock Current_Prices row and check Stock status
    SELECT s.status, cp.price
    INTO v_stock_status, v_curr_price
    FROM Stocks s
    JOIN Current_Prices cp ON s.id = cp.stock_id
    WHERE s.id = p_stock_id
    FOR UPDATE;

    IF v_stock_status IS NULL OR v_stock_status != 'ACTIVE' THEN
        ROLLBACK;
        IF v_stock_status = 'INACTIVE' THEN
            INSERT INTO Orders (user_id, stock_id, side, quantity, estimated_price, executed_price, status, reject_reason, idempotency_key)
            VALUES (p_user_id, p_stock_id, p_side, p_quantity, COALESCE(v_curr_price, 0.0000), COALESCE(v_curr_price, 0.0000), 'REJECTED', 'Stock is inactive', p_idempotency_key);
            SET p_order_id = LAST_INSERT_ID();
            COMMIT;
        END IF;
        SET p_status = 'REJECTED';
        SET p_message = 'Stock is inactive or not found';
        LEAVE proc_label;
    END IF;

    -- Missing or invalid price check
    IF v_curr_price IS NULL OR v_curr_price <= 0.0000 THEN
        ROLLBACK;
        INSERT INTO Orders (user_id, stock_id, side, quantity, estimated_price, executed_price, status, reject_reason, idempotency_key)
        VALUES (p_user_id, p_stock_id, p_side, p_quantity, 0.0000, 0.0000, 'REJECTED', 'Current market price unavailable', p_idempotency_key);
        SET p_order_id = LAST_INSERT_ID();
        COMMIT;
        SET p_status = 'REJECTED';
        SET p_message = 'Current market price unavailable';
        LEAVE proc_label;
    END IF;

    -- 4. Financial Calculations with Decimal Precision
    SET p_execution_price = v_curr_price;
    SET v_gross_amount = ROUND(p_quantity * v_curr_price, 2);
    
    -- Brokerage fee calculation: max(min_fee, trade_value * rate)
    SET v_brokerage_fee = ROUND(v_gross_amount * v_brokerage_rate, 2);
    IF v_brokerage_fee < v_brokerage_min THEN
        SET v_brokerage_fee = v_brokerage_min;
    END IF;

    -- 5. Side-Specific Validation & Cost Basis Updates
    IF p_side = 'BUY' THEN
        -- Net cash required: trade_value + brokerage_fee
        SET v_net_amount = v_gross_amount + v_brokerage_fee;

        IF v_virtual_balance < v_net_amount THEN
            ROLLBACK;
            -- Record rejected order for audit
            INSERT INTO Orders (user_id, stock_id, side, quantity, estimated_price, executed_price, status, reject_reason, idempotency_key)
            VALUES (p_user_id, p_stock_id, 'BUY', p_quantity, v_curr_price, v_curr_price, 'REJECTED', 'Insufficient cash balance', p_idempotency_key);
            SET p_order_id = LAST_INSERT_ID();
            COMMIT;
            SET p_status = 'REJECTED';
            SET p_message = 'Insufficient funds for trade value and brokerage';
            LEAVE proc_label;
        END IF;

        -- Calculate new weighted average cost
        -- new_avg = (old_qty * old_avg + qty * price) / (old_qty + qty)
        SET v_new_qty = COALESCE(v_holding_qty, 0) + p_quantity;
        SET v_new_avg_cost = ROUND(((COALESCE(v_holding_qty, 0) * COALESCE(v_holding_avg_cost, 0.0000)) + (p_quantity * v_curr_price)) / v_new_qty, 4);

        -- Update or insert Holdings
        IF v_holding_id IS NOT NULL THEN
            UPDATE Holdings 
            SET quantity = v_new_qty, avg_cost = v_new_avg_cost, updated_at = CURRENT_TIMESTAMP
            WHERE id = v_holding_id;
        ELSE
            INSERT INTO Holdings (user_id, stock_id, quantity, avg_cost)
            VALUES (p_user_id, p_stock_id, v_new_qty, v_new_avg_cost);
        END IF;

        -- Compute account balance updates
        SET v_balance_after = v_virtual_balance - v_gross_amount;
        SET v_balance_after_fee = v_balance_after - v_brokerage_fee;

        -- Update Account Balance atomically
        UPDATE Accounts SET virtual_balance = v_balance_after_fee WHERE id = v_account_id;

    ELSE -- SELL
        IF COALESCE(v_holding_qty, 0) < p_quantity THEN
            ROLLBACK;
            INSERT INTO Orders (user_id, stock_id, side, quantity, estimated_price, executed_price, status, reject_reason, idempotency_key)
            VALUES (p_user_id, p_stock_id, 'SELL', p_quantity, v_curr_price, v_curr_price, 'REJECTED', 'Insufficient share holdings', p_idempotency_key);
            SET p_order_id = LAST_INSERT_ID();
            COMMIT;
            SET p_status = 'REJECTED';
            SET p_message = 'Insufficient share holdings to sell';
            LEAVE proc_label;
        END IF;

        -- Realised P&L = (sell_price - avg_cost) * qty - sell_brokerage
        SET v_realized_pnl = ROUND(((v_curr_price - v_holding_avg_cost) * p_quantity) - v_brokerage_fee, 2);
        SET v_new_qty = v_holding_qty - p_quantity;

        -- Update Holdings
        UPDATE Holdings 
        SET quantity = v_new_qty, updated_at = CURRENT_TIMESTAMP
        WHERE id = v_holding_id;

        -- Compute account balance updates (net amount added is gross - brokerage)
        SET v_balance_after = v_virtual_balance + v_gross_amount;
        SET v_balance_after_fee = v_balance_after - v_brokerage_fee;

        -- Update Account Balance atomically
        UPDATE Accounts SET virtual_balance = v_balance_after_fee WHERE id = v_account_id;
    END IF;

    -- 6. Insert Order as EXECUTED
    INSERT INTO Orders (
        user_id, stock_id, side, quantity, estimated_price, executed_price, 
        status, reject_reason, idempotency_key, executed_at
    ) VALUES (
        p_user_id, p_stock_id, p_side, p_quantity, v_curr_price, v_curr_price, 
        'EXECUTED', NULL, p_idempotency_key, CURRENT_TIMESTAMP
    );
    SET p_order_id = LAST_INSERT_ID();

    -- 7. Insert Financial Transaction Row
    INSERT INTO Transactions (
        order_id, user_id, stock_id, side, quantity, execution_price, 
        gross_amount, brokerage_fee, net_amount, realized_pnl, executed_at
    ) VALUES (
        p_order_id, p_user_id, p_stock_id, p_side, p_quantity, v_curr_price,
        v_gross_amount, v_brokerage_fee, 
        IF(p_side = 'BUY', v_gross_amount + v_brokerage_fee, v_gross_amount - v_brokerage_fee),
        v_realized_pnl, CURRENT_TIMESTAMP
    );
    SET p_transaction_id = LAST_INSERT_ID();

    -- 8. Append Immutable Ledger Entries
    -- Trade principal ledger row
    IF p_side = 'BUY' THEN
        INSERT INTO Account_Ledger (
            account_id, entry_type, amount, balance_after, reference_type, reference_id, note
        ) VALUES (
            v_account_id, 'BUY', -v_gross_amount, v_balance_after, 'TRANSACTION', CAST(p_transaction_id AS CHAR), 
            CONCAT('Bought ', p_quantity, ' shares @ ', v_curr_price)
        );
    ELSE
        INSERT INTO Account_Ledger (
            account_id, entry_type, amount, balance_after, reference_type, reference_id, note
        ) VALUES (
            v_account_id, 'SELL', v_gross_amount, v_balance_after, 'TRANSACTION', CAST(p_transaction_id AS CHAR), 
            CONCAT('Sold ', p_quantity, ' shares @ ', v_curr_price)
        );
    END IF;

    -- Fee ledger row
    INSERT INTO Account_Ledger (
        account_id, entry_type, amount, balance_after, reference_type, reference_id, note
    ) VALUES (
        v_account_id, 'FEE', -v_brokerage_fee, v_balance_after_fee, 'TRANSACTION', CAST(p_transaction_id AS CHAR), 
        CONCAT('Investor brokerage on trade #', p_transaction_id)
    );

    -- 9. Check Broker Assignment & Record Commission (Platform-funded, reporting only)
    SELECT broker_id INTO v_active_broker_id
    FROM Broker_Clients
    WHERE investor_id = p_user_id AND status = 'ACTIVE'
    LIMIT 1;

    IF v_active_broker_id IS NOT NULL THEN
        SET v_commission_amount = ROUND(v_brokerage_fee * v_broker_commission_rate, 2);
        IF v_commission_amount > 0.00 THEN
            INSERT INTO Commissions (
                transaction_id, broker_id, investor_id, base_brokerage, rate_applied, commission_amount
            ) VALUES (
                p_transaction_id, v_active_broker_id, p_user_id, v_brokerage_fee, v_broker_commission_rate, v_commission_amount
            );
        END IF;
    END IF;

    -- 10. Audit Log
    INSERT INTO Audit_Logs (user_id, action, entity_type, entity_id, details)
    VALUES (p_user_id, 'EXECUTE_TRADE', 'ORDER', CAST(p_order_id AS CHAR), 
            JSON_OBJECT('side', p_side, 'qty', p_quantity, 'price', v_curr_price, 'gross', v_gross_amount, 'fee', v_brokerage_fee));

    COMMIT;

    SET p_status = 'EXECUTED';
    SET p_message = 'Trade executed successfully';
END$$

-- ==============================================================================
-- sp_reconcile_financial_integrity: System-Wide Audit of All 7 Financial Invariants
-- ==============================================================================
DROP PROCEDURE IF EXISTS sp_reconcile_financial_integrity$$

CREATE PROCEDURE sp_reconcile_financial_integrity()
BEGIN
    SELECT 
        '1. Account Cash Balance vs Ledger Sum' AS audit_check,
        COUNT(*) AS discrepancies_found
    FROM (
        SELECT a.id 
        FROM Accounts a 
        LEFT JOIN Account_Ledger al ON a.id = al.account_id 
        GROUP BY a.id, a.virtual_balance 
        HAVING a.virtual_balance != COALESCE(SUM(al.amount), 0.00)
    ) c1
    UNION ALL
    SELECT 
        '2. Holdings Quantity vs Net Executed Trades' AS audit_check,
        COUNT(*) AS discrepancies_found
    FROM (
        SELECT h.user_id, h.stock_id 
        FROM Holdings h 
        LEFT JOIN Transactions t ON h.user_id = t.user_id AND h.stock_id = t.stock_id 
        GROUP BY h.user_id, h.stock_id, h.quantity 
        HAVING h.quantity != COALESCE(SUM(CASE WHEN t.side = 'BUY' THEN t.quantity ELSE -t.quantity END), 0)
    ) c2
    UNION ALL
    SELECT 
        '3. Executed Orders Missing Transactions' AS audit_check,
        COUNT(*) AS discrepancies_found
    FROM Orders o 
    LEFT JOIN Transactions t ON o.id = t.order_id 
    WHERE o.status = 'EXECUTED' AND t.id IS NULL
    UNION ALL
    SELECT 
        '4. Completed Transactions Missing Ledger Entries' AS audit_check,
        COUNT(*) AS discrepancies_found
    FROM Transactions t 
    WHERE NOT EXISTS (
        SELECT 1 FROM Account_Ledger al 
        WHERE al.reference_type = 'TRANSACTION' 
          AND al.reference_id = CAST(t.id AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_unicode_ci 
          AND al.entry_type IN ('BUY', 'SELL')
    ) OR NOT EXISTS (
        SELECT 1 FROM Account_Ledger al 
        WHERE al.reference_type = 'TRANSACTION' 
          AND al.reference_id = CAST(t.id AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_unicode_ci 
          AND al.entry_type = 'FEE'
    )
    UNION ALL
    SELECT 
        '5. Inconsistent Broker Commission Amounts' AS audit_check,
        COUNT(*) AS discrepancies_found
    FROM Transactions t
    JOIN Broker_Clients bc ON t.user_id = bc.investor_id 
        AND bc.status = 'ACTIVE' 
        AND t.executed_at >= bc.assigned_at 
        AND (bc.ended_at IS NULL OR t.executed_at <= bc.ended_at)
    LEFT JOIN Commissions c ON t.id = c.transaction_id
    JOIN Commission_Rules cr ON cr.rule_type = 'BROKER_COMMISSION' AND cr.is_active = TRUE
    WHERE c.id IS NULL OR c.commission_amount != ROUND(t.brokerage_fee * cr.rate, 2)
    UNION ALL
    SELECT 
        '6. Duplicate Financial Order Transactions' AS audit_check,
        COUNT(*) AS discrepancies_found
    FROM (
        SELECT order_id FROM Transactions GROUP BY order_id HAVING COUNT(*) > 1
    ) c6
    UNION ALL
    SELECT 
        '7. Missing or Corrupt Opening Grants' AS audit_check,
        COUNT(*) AS discrepancies_found
    FROM (
        SELECT a.id 
        FROM Accounts a 
        JOIN Users u ON a.user_id = u.id 
        LEFT JOIN Account_Ledger al ON a.id = al.account_id AND al.entry_type = 'OPENING_GRANT' 
        WHERE u.role = 'INVESTOR' 
        GROUP BY a.id 
        HAVING COUNT(al.id) != 1 OR COALESCE(SUM(al.amount), 0.00) != 100000.00
    ) c7;
END$$

DELIMITER ;
