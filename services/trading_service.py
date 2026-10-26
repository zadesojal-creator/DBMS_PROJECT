"""
Trading Engine & Deposit Service (services/trading_service.py)
Orchestrates atomic market orders via sp_execute_trade and virtual deposits.
"""
import time
import random
import uuid
from decimal import Decimal
from typing import Dict, Any, Optional
from sqlalchemy import text
from models.db import get_engine, get_db_transaction
from repositories.account_repo import AccountRepository
from repositories.ledger_repo import LedgerRepository
from repositories.audit_repo import AuditRepository

class TradingService:
    @staticmethod
    def execute_market_order(
        user_id: int, stock_id: int, side: str, quantity: int,
        idempotency_key: Optional[str] = None, estimated_quote: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Executes a market order atomically via sp_execute_trade.
        Guarantees ACID atomicity, ordered row-locking, authoritative price execution, and idempotency.
        """
        if not idempotency_key:
            idempotency_key = str(uuid.uuid4())

        # 1. Sync authoritative simulated price to MySQL Current_Prices
        try:
            from services.market_simulator import MarketSimulator
            sim = MarketSimulator.get_instance()
            sim.sync_stock_to_db(stock_id)
        except Exception:
            pass

        # 2. Call sp_execute_trade with bounded exponential backoff for deadlocks (1213 / 1205)
        engine = get_engine()
        res = None
        max_retries = 3
        backoff_base = 0.05

        for attempt in range(max_retries):
            try:
                with engine.connect() as conn:
                    raw_conn = conn.connection
                    with raw_conn.cursor() as cur:
                        cur.callproc("sp_execute_trade", (
                            user_id, stock_id, side.upper(), quantity, idempotency_key,
                            0, 0, 0.0, '', ''
                        ))
                        cur.execute("""
                            SELECT 
                                @_sp_execute_trade_5 AS order_id,
                                @_sp_execute_trade_6 AS transaction_id,
                                @_sp_execute_trade_7 AS execution_price,
                                @_sp_execute_trade_8 AS status,
                                @_sp_execute_trade_9 AS message
                        """)
                        res = cur.fetchone()
                break
            except Exception as exc:
                err_code = None
                if hasattr(exc, 'orig') and hasattr(exc.orig, 'args') and len(exc.orig.args) > 0:
                    err_code = exc.orig.args[0]
                elif hasattr(exc, 'args') and len(exc.args) > 0:
                    err_code = exc.args[0]

                if err_code in (1213, 1205) and attempt < max_retries - 1:
                    sleep_time = backoff_base * (2 ** attempt) + random.uniform(0.01, 0.05)
                    time.sleep(sleep_time)
                    continue
                raise

        order_id = res[0]
        transaction_id = res[1]
        exec_price = Decimal(str(res[2])) if res[2] is not None else Decimal('0.00')
        status = res[3]
        message = res[4]

        # 3. Price tolerance check if estimated quote was provided
        if status == 'EXECUTED' and estimated_quote and estimated_quote > 0:
            diff_pct = abs(exec_price - estimated_quote) / estimated_quote
            if diff_pct > Decimal('0.01'):
                message += f" (Price moved {float(diff_pct*100):.2f}% from estimated quote)"

        # 4. Fetch full persisted financial execution details from Transactions table
        tx_row = None
        comm_row = None
        if transaction_id:
            with engine.connect() as conn:
                tx_row = conn.execute(text("""
                    SELECT 
                        t.id, t.order_id, t.user_id, t.stock_id, t.side, t.quantity,
                        t.execution_price, t.gross_amount, t.brokerage_fee, t.net_amount,
                        t.realized_pnl, t.executed_at, s.symbol, s.company_name
                    FROM Transactions t
                    JOIN Stocks s ON t.stock_id = s.id
                    WHERE t.id = :tx_id
                """), {"tx_id": transaction_id}).mappings().first()

                comm_row = conn.execute(text("""
                    SELECT broker_id, base_brokerage, rate_applied, commission_amount
                    FROM Commissions
                    WHERE transaction_id = :tx_id
                """), {"tx_id": transaction_id}).mappings().first()

        executed_qty = int(tx_row["quantity"]) if tx_row else quantity
        final_price = float(tx_row["execution_price"]) if tx_row else float(exec_price)
        gross_amt = float(tx_row["gross_amount"]) if tx_row else float(final_price * executed_qty)
        brokerage = float(tx_row["brokerage_fee"]) if tx_row else 0.0
        net_amt = float(tx_row["net_amount"]) if tx_row else (
            gross_amt + brokerage if side.upper() == 'BUY' else gross_amt - brokerage
        )
        realized_pnl = float(tx_row["realized_pnl"]) if (tx_row and tx_row["realized_pnl"] is not None) else 0.0
        symbol = tx_row["symbol"] if tx_row else ""
        company_name = tx_row["company_name"] if tx_row else ""
        executed_at = tx_row["executed_at"].strftime("%Y-%m-%d %H:%M:%S") if (tx_row and tx_row["executed_at"]) else None

        return {
            "order_id": order_id,
            "transaction_id": transaction_id,
            "side": side.upper(),
            "symbol": symbol,
            "company_name": company_name,
            "quantity": executed_qty,
            "executed_quantity": executed_qty,
            "execution_price": final_price,
            "gross_amount": gross_amt,
            "gross_value": gross_amt,
            "brokerage_fee": brokerage,
            "brokerage": brokerage,
            "net_amount": net_amt,
            "realized_pnl": realized_pnl,
            "broker_id": comm_row["broker_id"] if comm_row else None,
            "broker_commission": float(comm_row["commission_amount"]) if comm_row else 0.0,
            "executed_at": executed_at,
            "status": status,
            "message": message,
            "idempotency_key": idempotency_key
        }

    @staticmethod
    def process_deposit(
        user_id: int, amount: Decimal, idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Simulated Deposit:
        Validates amount (min ₹100, max ₹10,00,000 per deposit, daily cap ₹50,00,000).
        Guarantees strict concurrency safety via row-locking (SELECT ... FOR UPDATE),
        atomic account balance + ledger entry update, and idempotency key caching.
        """
        if amount < Decimal('100.00'):
            raise ValueError("Minimum virtual deposit amount is ₹ 100.00")
        if amount > Decimal('1000000.00'):
            raise ValueError("Maximum virtual deposit per transaction is ₹ 10,00,000.00")

        # 1. Idempotency Check
        if idempotency_key:
            with get_engine().connect() as conn:
                existing = conn.execute(text("""
                    SELECT al.id, al.account_id, al.amount, al.balance_after, al.created_at
                    FROM Account_Ledger al
                    JOIN Accounts a ON al.account_id = a.id
                    WHERE a.user_id = :user_id 
                      AND al.reference_type = 'SIMULATED_GATEWAY' 
                      AND al.reference_id = :key
                """), {"user_id": user_id, "key": idempotency_key}).mappings().first()
                if existing:
                    return {
                        "account_id": existing["account_id"],
                        "reference_id": idempotency_key,
                        "deposited_amount": float(existing["amount"]),
                        "new_virtual_balance": float(existing["balance_after"]),
                        "idempotent_replayed": True,
                        "message": "Virtual funds deposit already processed (idempotent replay)"
                    }

        ref_id = idempotency_key if idempotency_key else f"DEP_{uuid.uuid4().hex[:12].upper()}"

        # 2. Atomic Locked Transaction (pessimistic row locking on Accounts row)
        with get_db_transaction() as conn:
            acc_row = conn.execute(text("""
                SELECT id, virtual_balance, status 
                FROM Accounts 
                WHERE user_id = :user_id 
                FOR UPDATE
            """), {"user_id": user_id}).mappings().first()

            if not acc_row or acc_row['status'] != 'ACTIVE':
                raise ValueError("Active investor account not found")

            account_id = acc_row['id']
            current_balance = Decimal(str(acc_row['virtual_balance']))

            # Daily deposit limit check computed inside the transaction lock
            daily_sum_q = """
                SELECT COALESCE(SUM(amount), 0.00)
                FROM Account_Ledger
                WHERE account_id = :account_id 
                  AND entry_type = 'DEPOSIT' 
                  AND DATE(created_at) = CURRENT_DATE
            """
            daily_sum = conn.execute(text(daily_sum_q), {"account_id": account_id}).scalar()
            if Decimal(str(daily_sum)) + amount > Decimal('5000000.00'):
                raise ValueError("Daily virtual deposit cap of ₹ 50,00,000.00 exceeded")

            new_balance = current_balance + amount

            # Update Account balance
            conn.execute(
                text("UPDATE Accounts SET virtual_balance = :balance WHERE id = :id"),
                {"balance": new_balance, "id": account_id}
            )

            # Append ledger entry
            conn.execute(text("""
                INSERT INTO Account_Ledger (account_id, entry_type, amount, balance_after, reference_type, reference_id, note)
                VALUES (:account_id, 'DEPOSIT', :amount, :balance_after, 'SIMULATED_GATEWAY', :ref_id, 'Virtual Cash Deposit')
            """), {
                "account_id": account_id,
                "amount": amount,
                "balance_after": new_balance,
                "ref_id": ref_id
            })

        AuditRepository.log(user_id, 'DEPOSIT', 'ACCOUNT', str(account_id), {
            "amount": float(amount), "new_balance": float(new_balance), "ref": ref_id
        })

        return {
            "reference_id": ref_id,
            "deposited_amount": float(amount),
            "new_virtual_balance": float(new_balance),
            "idempotent_replayed": False,
            "message": "Virtual funds deposited successfully"
        }
