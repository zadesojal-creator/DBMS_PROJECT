"""
Database Constraints, Triggers, Views & Procedures Smoke Tests (test_database.py)
Validates:
- FK ON DELETE RESTRICT enforcement
- CHECK constraints (negative balance, 0 quantity)
- Triggers (Ledger append-only immutability, role validation)
- sp_execute_trade atomicity, insufficient cash rejection, and idempotent replay
"""
import uuid
import pytest
import pymysql

def test_fk_on_delete_restrict_user(db_conn):
    """Deleting a user who has an associated account must fail with FK violation."""
    with db_conn.cursor() as cur:
        with pytest.raises(pymysql.err.IntegrityError) as exc_info:
            cur.execute("DELETE FROM Users WHERE id = 4") # Rahul Verma owns an account
        assert exc_info.value.args[0] in (1217, 1451) # Foreign key constraint fails

def test_check_constraint_negative_balance(db_conn):
    """Updating virtual balance to negative must be rejected by chk_accounts_balance."""
    with db_conn.cursor() as cur:
        with pytest.raises(pymysql.err.OperationalError) as exc_info:
            cur.execute("UPDATE Accounts SET virtual_balance = -500.00 WHERE id = 1")
        assert exc_info.value.args[0] == 3819 # Check constraint 'chk_accounts_balance' is violated

def test_check_constraint_zero_order_quantity(db_conn):
    """Inserting an order with quantity 0 must be rejected by chk_order_qty."""
    with db_conn.cursor() as cur:
        with pytest.raises(pymysql.err.OperationalError) as exc_info:
            cur.execute("""
                INSERT INTO Orders (user_id, stock_id, side, quantity, estimated_price, status, idempotency_key)
                VALUES (4, 1, 'BUY', 0, 1000.00, 'PENDING', %s)
            """, (str(uuid.uuid4()),))
        assert exc_info.value.args[0] == 3819 # Check constraint 'chk_order_qty' is violated

def test_trigger_ledger_immutability_update(db_conn):
    """Updating Account_Ledger rows must be blocked by trg_ledger_block_update with SQLSTATE 45000."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT id FROM Account_Ledger LIMIT 1")
        row = cur.fetchone()
        assert row is not None
        ledger_id = row['id']
        
        with pytest.raises(pymysql.err.OperationalError) as exc_info:
            cur.execute("UPDATE Account_Ledger SET amount = 999999.00 WHERE id = %s", (ledger_id,))
        assert "strictly append-only" in str(exc_info.value)

def test_trigger_ledger_immutability_delete(db_conn):
    """Deleting Account_Ledger rows must be blocked by trg_ledger_block_delete with SQLSTATE 45000."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT id FROM Account_Ledger LIMIT 1")
        ledger_id = cur.fetchone()['id']
        
        with pytest.raises(pymysql.err.OperationalError) as exc_info:
            cur.execute("DELETE FROM Account_Ledger WHERE id = %s", (ledger_id,))
        assert "strictly append-only" in str(exc_info.value)

def test_trigger_broker_client_role_validation(db_conn):
    """Assigning a non-broker as broker_id must be blocked by trg_broker_clients_role_insert."""
    with db_conn.cursor() as cur:
        with pytest.raises(pymysql.err.OperationalError) as exc_info:
            # User 4 is an INVESTOR, attempting to assign them as a broker to User 5
            cur.execute("INSERT INTO Broker_Clients (broker_id, investor_id, status) VALUES (4, 5, 'ACTIVE')")
        assert "broker_id must have role BROKER" in str(exc_info.value)

def test_sp_execute_trade_success_and_idempotency(db_conn):
    """Verify sp_execute_trade completes trade atomically and respects idempotency key."""
    with db_conn.cursor() as cur:
        # Check initial balance of Sneha Patel (id=5, account id=2)
        cur.execute("SELECT virtual_balance FROM Accounts WHERE user_id = 5")
        initial_balance = cur.fetchone()['virtual_balance']
        
        # Sneha buys 2 shares of WIPRO (id=3, ref price approx 535)
        cur.execute("SELECT stock_id, price FROM Current_Prices WHERE stock_id = 3")
        wipro = cur.fetchone()
        stock_id = 3
        price = wipro['price']
        
        idempotency_key = f"TEST_SP_EXECUTE_{uuid.uuid4()}"
        
        # Execute procedure
        cur.callproc("sp_execute_trade", (5, stock_id, 'BUY', 2, idempotency_key, 0, 0, 0.0, '', ''))
        cur.execute("SELECT @_sp_execute_trade_5, @_sp_execute_trade_6, @_sp_execute_trade_7, @_sp_execute_trade_8, @_sp_execute_trade_9")
        order_id, trans_id, exec_price, status, msg = cur.fetchone().values()
        
        assert status == 'EXECUTED'
        assert order_id > 0
        assert trans_id > 0
        assert exec_price > 0
        
        # Verify account balance decreased by gross + brokerage
        cur.execute("SELECT virtual_balance FROM Accounts WHERE user_id = 5")
        new_balance = cur.fetchone()['virtual_balance']
        assert new_balance < initial_balance
        
        # Re-run same idempotency key: must NOT debit money again, must return same order
        cur.callproc("sp_execute_trade", (5, stock_id, 'BUY', 2, idempotency_key, 0, 0, 0.0, '', ''))
        cur.execute("SELECT @_sp_execute_trade_5, @_sp_execute_trade_6, @_sp_execute_trade_7, @_sp_execute_trade_8, @_sp_execute_trade_9")
        order_id2, trans_id2, exec_price2, status2, msg2 = cur.fetchone().values()
        
        assert order_id2 == order_id
        assert status2 == 'EXECUTED'
        assert "idempotent" in msg2.lower()
        
        # Balance must remain unchanged after replay
        cur.execute("SELECT virtual_balance FROM Accounts WHERE user_id = 5")
        assert cur.fetchone()['virtual_balance'] == new_balance

def test_sp_execute_trade_insufficient_funds_rejection(db_conn):
    """Trading with insufficient cash must be rejected cleanly with REJECTED status."""
    with db_conn.cursor() as cur:
        # Sneha tries to buy 1,000,000 shares of MRF / UltraTech (exceeding balance)
        idempotency_key = f"TEST_REJECT_{uuid.uuid4()}"
        cur.callproc("sp_execute_trade", (5, 1, 'BUY', 1000000, idempotency_key, 0, 0, 0.0, '', ''))
        cur.execute("SELECT @_sp_execute_trade_5, @_sp_execute_trade_6, @_sp_execute_trade_7, @_sp_execute_trade_8, @_sp_execute_trade_9")
        order_id, trans_id, exec_price, status, msg = cur.fetchone().values()
        
        assert status == 'REJECTED'
        assert "insufficient" in msg.lower()

def test_trigger_transactions_immutability(db_conn):
    """Updating or deleting a Transactions row must be blocked by triggers with SQLSTATE 45000."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT id FROM Transactions LIMIT 1")
        row = cur.fetchone()
        if not row:
            pytest.skip("No transaction rows available for immutability check")
        tx_id = row['id']

        with pytest.raises(pymysql.err.OperationalError) as exc_update:
            cur.execute("UPDATE Transactions SET gross_amount = 1.00 WHERE id = %s", (tx_id,))
        assert "strictly append-only" in str(exc_update.value)

        with pytest.raises(pymysql.err.OperationalError) as exc_delete:
            cur.execute("DELETE FROM Transactions WHERE id = %s", (tx_id,))
        assert "strictly append-only" in str(exc_delete.value)

def test_trigger_commissions_immutability(db_conn):
    """Updating or deleting a Commissions row must be blocked by triggers with SQLSTATE 45000."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT id FROM Commissions LIMIT 1")
        row = cur.fetchone()
        if not row:
            pytest.skip("No commissions rows available for immutability check")
        comm_id = row['id']

        with pytest.raises(pymysql.err.OperationalError) as exc_update:
            cur.execute("UPDATE Commissions SET commission_amount = 0.00 WHERE id = %s", (comm_id,))
        assert "strictly append-only" in str(exc_update.value)

        with pytest.raises(pymysql.err.OperationalError) as exc_delete:
            cur.execute("DELETE FROM Commissions WHERE id = %s", (comm_id,))
        assert "strictly append-only" in str(exc_delete.value)

def test_trigger_orders_terminal_immutability(db_conn):
    """Orders in terminal state (EXECUTED/REJECTED/CANCELLED) cannot be modified or deleted."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT id FROM Orders WHERE status IN ('EXECUTED', 'REJECTED') LIMIT 1")
        row = cur.fetchone()
        if not row:
            pytest.skip("No terminal orders available")
        order_id = row['id']

        with pytest.raises(pymysql.err.OperationalError) as exc_update:
            cur.execute("UPDATE Orders SET quantity = 9999 WHERE id = %s", (order_id,))
        assert "immutable" in str(exc_update.value).lower()

        with pytest.raises(pymysql.err.OperationalError) as exc_delete:
            cur.execute("DELETE FROM Orders WHERE id = %s", (order_id,))
        assert "deletions are prohibited" in str(exc_delete.value).lower()

def test_trigger_audit_logs_immutability(db_conn):
    """Audit_Logs rows can never be updated or deleted."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT id FROM Audit_Logs LIMIT 1")
        row = cur.fetchone()
        if not row:
            cur.execute("INSERT INTO Audit_Logs (user_id, action, resource_type) VALUES (1, 'TEST', 'SYSTEM')")
            db_conn.commit()
            cur.execute("SELECT id FROM Audit_Logs LIMIT 1")
            row = cur.fetchone()
        log_id = row['id']

        with pytest.raises(pymysql.err.OperationalError) as exc_update:
            cur.execute("UPDATE Audit_Logs SET action = 'HACK' WHERE id = %s", (log_id,))
        assert "strictly append-only" in str(exc_update.value)

        with pytest.raises(pymysql.err.OperationalError) as exc_delete:
            cur.execute("DELETE FROM Audit_Logs WHERE id = %s", (log_id,))
        assert "strictly append-only" in str(exc_delete.value)

def test_domain_check_constraints_v2(db_conn):
    """Domain check constraints prevent negative transaction figures and invalid commission rates."""
    with db_conn.cursor() as cur:
        # 1. Negative Commission Rule Rate (> 1.0)
        with pytest.raises(pymysql.err.OperationalError) as exc_rate:
            cur.execute("""
                INSERT INTO Commission_Rules (rule_type, rate, min_fee, effective_from, is_active)
                VALUES ('INVESTOR_BROKERAGE', 1.50, 5.00, CURRENT_TIMESTAMP, TRUE)
            """)
        assert exc_rate.value.args[0] == 3819

        # 2. Negative Price Alert target_price
        with pytest.raises(pymysql.err.OperationalError) as exc_alert:
            cur.execute("""
                INSERT INTO Price_Alerts (user_id, stock_id, target_price, condition_type)
                VALUES (4, 1, -100.00, 'ABOVE')
            """)
        assert exc_alert.value.args[0] == 3819

def test_order_events_audit_trail(db_conn):
    """Triggers trg_orders_audit_insert and trg_orders_audit_update log lifecycle to Order_Events."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM Order_Events")
        initial_events = cur.fetchone()['cnt']

        test_key = f"ORDER_EVENT_TEST_{uuid.uuid4()}"
        cur.execute("""
            INSERT INTO Orders (user_id, stock_id, side, quantity, estimated_price, status, idempotency_key)
            VALUES (4, 1, 'BUY', 5, 4000.00, 'PENDING', %s)
        """, (test_key,))
        order_id = cur.lastrowid
        db_conn.commit()

        # Update order status to REJECTED
        cur.execute("UPDATE Orders SET status = 'REJECTED' WHERE id = %s", (order_id,))
        db_conn.commit()

        cur.execute("SELECT from_status, to_status FROM Order_Events WHERE order_id = %s ORDER BY id ASC", (order_id,))
        events = cur.fetchall()

        assert len(events) == 2
        assert events[0]['from_status'] == 'NEW'
        assert events[0]['to_status'] == 'PENDING'
        assert events[1]['from_status'] == 'PENDING'
        assert events[1]['to_status'] == 'REJECTED'

def test_trigger_order_events_immutability(db_conn):
    """Order_Events table is append-only: updates and deletes are blocked with SQLSTATE 45000."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT id FROM Order_Events LIMIT 1")
        row = cur.fetchone()
        if not row:
            pytest.skip("No order events available for immutability test")
        event_id = row['id']

        with pytest.raises(pymysql.err.OperationalError) as exc_update:
            cur.execute("UPDATE Order_Events SET to_status = 'EXECUTED' WHERE id = %s", (event_id,))
        assert "strictly append-only" in str(exc_update.value)

        with pytest.raises(pymysql.err.OperationalError) as exc_delete:
            cur.execute("DELETE FROM Order_Events WHERE id = %s", (event_id,))
        assert "strictly append-only" in str(exc_delete.value)

def test_sp_execute_trade_inactive_stock_rejection(db_conn):
    """Trading an inactive stock must reject the order and persist the rejection record without financial side effects."""
    sym = f"INACT_{uuid.uuid4().hex[:6].upper()}"
    with db_conn.cursor() as cur:
        # Create a temporary inactive stock
        cur.execute("""
            INSERT INTO Stocks (symbol, company_name, sector, exchange, status)
            VALUES (%s, 'Delisted Corp', 'Technology', 'NSE', 'INACTIVE')
        """, (sym,))
        stock_id = cur.lastrowid
        cur.execute("""
            INSERT INTO Current_Prices (stock_id, price, previous_close, day_open, day_high, day_low, volume) 
            VALUES (%s, 100.00, 100.00, 100.00, 105.00, 99.00, 1000)
        """, (stock_id,))
        db_conn.commit()

        key = f"TEST_INACTIVE_{uuid.uuid4()}"
        cur.callproc("sp_execute_trade", (4, stock_id, 'BUY', 10, key, 0, 0, 0.0, '', ''))
        cur.execute("SELECT @_sp_execute_trade_5, @_sp_execute_trade_6, @_sp_execute_trade_7, @_sp_execute_trade_8, @_sp_execute_trade_9")
        order_id, trans_id, exec_price, status, msg = cur.fetchone().values()

        assert status == 'REJECTED'
        assert "inactive" in msg.lower()
        assert order_id > 0
        assert trans_id is None

        # Confirm rejected order persisted in Orders
        cur.execute("SELECT status, reject_reason FROM Orders WHERE id = %s", (order_id,))
        ord_row = cur.fetchone()
        assert ord_row['status'] == 'REJECTED'
        assert 'inactive' in ord_row['reject_reason'].lower()


