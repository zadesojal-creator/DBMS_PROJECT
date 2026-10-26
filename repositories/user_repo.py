"""
User Repository (repositories/user_repo.py)
Data access operations for Users table using parameterized SQLAlchemy Core.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import select, update, insert
from models.db import get_db_connection, get_db_transaction
from models.schema import users_table

class UserRepository:
    @staticmethod
    def get_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            stmt = select(users_table).where(users_table.c.id == user_id)
            row = conn.execute(stmt).mappings().first()
            return dict(row) if row else None

    @staticmethod
    def get_by_email(email: str) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            stmt = select(users_table).where(users_table.c.email == email.strip().lower())
            row = conn.execute(stmt).mappings().first()
            return dict(row) if row else None

    @staticmethod
    def get_by_username(username: str) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            stmt = select(users_table).where(users_table.c.username == username.strip())
            row = conn.execute(stmt).mappings().first()
            return dict(row) if row else None

    @staticmethod
    def record_failed_login(user_id: int) -> int:
        """Increments failed attempts; locks account for 15 minutes if attempts >= 5."""
        with get_db_transaction() as conn:
            user = conn.execute(select(users_table.c.failed_login_attempts).where(users_table.c.id == user_id)).first()
            if not user:
                return 0
            attempts = user[0] + 1
            locked_until = None
            if attempts >= 5:
                locked_until = datetime.utcnow() + timedelta(minutes=15)
            
            stmt = (
                update(users_table)
                .where(users_table.c.id == user_id)
                .values(failed_login_attempts=attempts, locked_until=locked_until)
            )
            conn.execute(stmt)
            return attempts

    @staticmethod
    def reset_failed_logins(user_id: int):
        with get_db_transaction() as conn:
            stmt = (
                update(users_table)
                .where(users_table.c.id == user_id)
                .values(failed_login_attempts=0, locked_until=None)
            )
            conn.execute(stmt)

    @staticmethod
    def update_last_login(user_id: int):
        with get_db_transaction() as conn:
            stmt = (
                update(users_table)
                .where(users_table.c.id == user_id)
                .values(last_login_at=datetime.utcnow(), failed_login_attempts=0, locked_until=None)
            )
            conn.execute(stmt)

    @staticmethod
    def create_user(
        username: str, email: str, password_hash: str, full_name: str,
        role: str, phone: Optional[str] = None, is_demo: bool = False
    ) -> int:
        with get_db_transaction() as conn:
            stmt = insert(users_table).values(
                username=username.strip(),
                email=email.strip().lower(),
                password_hash=password_hash,
                full_name=full_name.strip(),
                phone=phone.strip() if phone else None,
                role=role.upper(),
                status='ACTIVE',
                is_demo=is_demo,
                failed_login_attempts=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            result = conn.execute(stmt)
            return result.inserted_primary_key[0]

    @staticmethod
    def list_users(role: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            stmt = select(
                users_table.c.id, users_table.c.username, users_table.c.email,
                users_table.c.full_name, users_table.c.phone, users_table.c.role,
                users_table.c.status, users_table.c.is_demo, users_table.c.last_login_at,
                users_table.c.created_at
            )
            if role:
                stmt = stmt.where(users_table.c.role == role.upper())
            if status:
                stmt = stmt.where(users_table.c.status == status.upper())
            stmt = stmt.order_by(users_table.c.id.asc())
            rows = conn.execute(stmt).mappings().all()
            return [dict(r) for r in rows]

    @staticmethod
    def update_status(user_id: int, status: str):
        with get_db_transaction() as conn:
            stmt = (
                update(users_table)
                .where(users_table.c.id == user_id)
                .values(status=status.upper(), updated_at=datetime.utcnow())
            )
            conn.execute(stmt)
