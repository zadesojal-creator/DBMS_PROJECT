"""
Account Repository (repositories/account_repo.py)
Data access operations for investor accounts and balances.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from sqlalchemy import select, update, insert
from models.db import get_db_connection, get_db_transaction
from models.schema import accounts_table

class AccountRepository:
    @staticmethod
    def get_by_user_id(user_id: int) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            stmt = select(accounts_table).where(accounts_table.c.user_id == user_id)
            row = conn.execute(stmt).mappings().first()
            return dict(row) if row else None

    @staticmethod
    def get_by_id(account_id: int) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            stmt = select(accounts_table).where(accounts_table.c.id == account_id)
            row = conn.execute(stmt).mappings().first()
            return dict(row) if row else None

    @staticmethod
    def create_account(user_id: int, initial_balance: Decimal = Decimal('100000.00')) -> int:
        with get_db_transaction() as conn:
            stmt = insert(accounts_table).values(
                user_id=user_id,
                virtual_balance=initial_balance,
                currency='INR',
                status='ACTIVE',
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            result = conn.execute(stmt)
            return result.inserted_primary_key[0]

    @staticmethod
    def update_balance(account_id: int, new_balance: Decimal):
        with get_db_transaction() as conn:
            stmt = (
                update(accounts_table)
                .where(accounts_table.c.id == account_id)
                .values(virtual_balance=new_balance, updated_at=datetime.utcnow())
            )
            conn.execute(stmt)
