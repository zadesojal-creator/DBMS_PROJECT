"""
Order Repository (repositories/order_repo.py)
Data access operations for Orders table.
"""
from typing import Optional, Dict, Any, List
from sqlalchemy import select, text
from models.db import get_db_connection
from models.schema import orders_table, stocks_table

class OrderRepository:
    @staticmethod
    def get_by_id(order_id: int) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            stmt = select(orders_table).where(orders_table.c.id == order_id)
            row = conn.execute(stmt).mappings().first()
            return dict(row) if row else None

    @staticmethod
    def get_by_idempotency(user_id: int, idempotency_key: str) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            stmt = (
                select(orders_table)
                .where(orders_table.c.user_id == user_id)
                .where(orders_table.c.idempotency_key == idempotency_key)
            )
            row = conn.execute(stmt).mappings().first()
            return dict(row) if row else None

    @staticmethod
    def get_by_user(user_id: int, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            query = """
                SELECT 
                    o.id AS order_id, o.user_id, o.stock_id, s.symbol, s.company_name,
                    o.side, o.quantity, o.estimated_price, o.executed_price,
                    o.status, o.reject_reason, o.idempotency_key, o.created_at, o.executed_at
                FROM Orders o
                JOIN Stocks s ON o.stock_id = s.id
                WHERE o.user_id = :user_id
                ORDER BY o.created_at DESC
                LIMIT :limit OFFSET :offset
            """
            rows = conn.execute(text(query), {
                "user_id": user_id, "limit": limit, "offset": offset
            }).mappings().all()
            return [dict(r) for r in rows]

    @staticmethod
    def get_total_count(user_id: int) -> int:
        with get_db_connection() as conn:
            stmt = text("SELECT COUNT(*) FROM Orders WHERE user_id = :user_id")
            return conn.execute(stmt, {"user_id": user_id}).scalar() or 0
