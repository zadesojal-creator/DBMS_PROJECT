"""
Ledger Repository (repositories/ledger_repo.py)
Append-only accounting journal operations and mathematical reconciliation invariant verification.
"""
from decimal import Decimal
from typing import Dict, Any, List, Tuple
from sqlalchemy import text, insert
from models.db import get_db_connection, get_db_transaction
from models.schema import account_ledger_table

class LedgerRepository:
    @staticmethod
    def get_by_account(account_id: int, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            query = """
                SELECT 
                    id, account_id, entry_type, amount, balance_after,
                    reference_type, reference_id, note, created_at
                FROM Account_Ledger
                WHERE account_id = :account_id
                ORDER BY created_at DESC, id DESC
                LIMIT :limit OFFSET :offset
            """
            rows = conn.execute(text(query), {
                "account_id": account_id, "limit": limit, "offset": offset
            }).mappings().all()
            return [dict(r) for r in rows]

    @staticmethod
    def append_entry(
        account_id: int, entry_type: str, amount: Decimal, balance_after: Decimal,
        reference_type: str, reference_id: str, note: str = ""
    ) -> int:
        with get_db_transaction() as conn:
            stmt = insert(account_ledger_table).values(
                account_id=account_id,
                entry_type=entry_type,
                amount=amount,
                balance_after=balance_after,
                reference_type=reference_type,
                reference_id=reference_id,
                note=note
            )
            res = conn.execute(stmt)
            return res.inserted_primary_key[0]

    @staticmethod
    def reconcile(account_id: int) -> Tuple[Decimal, Decimal, bool]:
        """
        Verifies the core accounting invariant:
        Accounts.virtual_balance == SUM(Account_Ledger.amount)
        """
        with get_db_connection() as conn:
            query = """
                SELECT 
                    a.virtual_balance,
                    COALESCE(SUM(al.amount), 0.00) AS ledger_sum
                FROM Accounts a
                LEFT JOIN Account_Ledger al ON a.id = al.account_id
                WHERE a.id = :account_id
                GROUP BY a.id, a.virtual_balance
            """
            row = conn.execute(text(query), {"account_id": account_id}).mappings().first()
            if not row:
                return Decimal('0.00'), Decimal('0.00'), True
            balance = Decimal(str(row['virtual_balance']))
            ledger_sum = Decimal(str(row['ledger_sum']))
            is_reconciled = (balance == ledger_sum)
            return balance, ledger_sum, is_reconciled
