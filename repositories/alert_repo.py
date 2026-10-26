"""
Alert Repository (repositories/alert_repo.py)
Data access operations for investor price threshold alerts.
"""
from decimal import Decimal
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from models.db import get_db_connection, get_db_transaction

class AlertRepository:
    @staticmethod
    def get_by_user(user_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns price alerts configured by the user, with current price."""
        with get_db_connection() as conn:
            query = """
                SELECT 
                    a.id AS alert_id,
                    a.stock_id,
                    s.symbol,
                    s.company_name,
                    s.sector,
                    a.target_price,
                    a.condition_type,
                    a.status,
                    cp.price AS current_price,
                    a.created_at,
                    a.triggered_at
                FROM Price_Alerts a
                JOIN Stocks s ON a.stock_id = s.id
                LEFT JOIN Current_Prices cp ON s.id = cp.stock_id
                WHERE a.user_id = :user_id
            """
            params: Dict[str, Any] = {"user_id": user_id}
            if status:
                query += " AND a.status = :status"
                params["status"] = status.upper()
            query += " ORDER BY a.created_at DESC"
            
            rows = conn.execute(text(query), params).mappings().all()
            return [dict(r) for r in rows]

    @staticmethod
    def create(user_id: int, stock_id: int, target_price: Decimal, condition_type: str) -> int:
        """Creates a new active price alert."""
        condition_upper = condition_type.strip().upper()
        if condition_upper not in ('ABOVE', 'BELOW'):
            raise ValueError("condition_type must be 'ABOVE' or 'BELOW'.")
        if target_price <= Decimal('0.00'):
            raise ValueError("target_price must be greater than zero.")

        with get_db_transaction() as conn:
            # Check stock exists
            stock_exists = conn.execute(
                text("SELECT id FROM Stocks WHERE id = :stock_id"),
                {"stock_id": stock_id}
            ).scalar()
            if not stock_exists:
                raise ValueError("Stock does not exist.")

            stmt = text("""
                INSERT INTO Price_Alerts (user_id, stock_id, target_price, condition_type, status, created_at)
                VALUES (:user_id, :stock_id, :target_price, :condition_type, 'ACTIVE', CURRENT_TIMESTAMP)
            """)
            res = conn.execute(stmt, {
                "user_id": user_id,
                "stock_id": stock_id,
                "target_price": target_price,
                "condition_type": condition_upper
            })
            return res.lastrowid

    @staticmethod
    def cancel(user_id: int, alert_id: int) -> bool:
        """Cancels an active alert."""
        with get_db_transaction() as conn:
            stmt = text("""
                UPDATE Price_Alerts 
                SET status = 'CANCELLED'
                WHERE id = :alert_id AND user_id = :user_id AND status = 'ACTIVE'
            """)
            res = conn.execute(stmt, {"alert_id": alert_id, "user_id": user_id})
            return res.rowcount > 0

    @staticmethod
    def delete(user_id: int, alert_id: int) -> bool:
        """Deletes an alert completely."""
        with get_db_transaction() as conn:
            stmt = text("DELETE FROM Price_Alerts WHERE id = :alert_id AND user_id = :user_id")
            res = conn.execute(stmt, {"alert_id": alert_id, "user_id": user_id})
            return res.rowcount > 0
