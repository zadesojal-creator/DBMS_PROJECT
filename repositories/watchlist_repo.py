"""
Watchlist Repository (repositories/watchlist_repo.py)
Data access operations for investor stock watchlists.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from models.db import get_db_connection, get_db_transaction

class WatchlistRepository:
    @staticmethod
    def get_by_user(user_id: int) -> List[Dict[str, Any]]:
        """Returns all stocks saved in the user's watchlist with latest live quotes."""
        with get_db_connection() as conn:
            query = """
                SELECT 
                    w.id AS watchlist_id,
                    w.stock_id,
                    s.symbol,
                    s.company_name,
                    s.sector,
                    s.exchange,
                    s.status AS stock_status,
                    cp.price AS current_price,
                    cp.previous_close,
                    (cp.price - cp.previous_close) AS day_change,
                    ROUND(((cp.price - cp.previous_close) / NULLIF(cp.previous_close, 0)) * 100, 2) AS day_change_pct,
                    cp.day_high,
                    cp.day_low,
                    cp.volume,
                    w.added_at
                FROM Watchlist w
                JOIN Stocks s ON w.stock_id = s.id
                LEFT JOIN Current_Prices cp ON s.id = cp.stock_id
                WHERE w.user_id = :user_id
                ORDER BY s.symbol ASC
            """
            rows = conn.execute(text(query), {"user_id": user_id}).mappings().all()
            return [dict(r) for r in rows]

    @staticmethod
    def add(user_id: int, stock_id: int) -> bool:
        """Adds a stock to the user's watchlist idempotently."""
        with get_db_transaction() as conn:
            # Check if stock exists
            stock_exists = conn.execute(
                text("SELECT id FROM Stocks WHERE id = :stock_id"),
                {"stock_id": stock_id}
            ).scalar()
            if not stock_exists:
                raise ValueError("Stock does not exist.")

            # Insert ignore
            stmt = text("""
                INSERT INTO Watchlist (user_id, stock_id, added_at)
                VALUES (:user_id, :stock_id, CURRENT_TIMESTAMP)
                ON DUPLICATE KEY UPDATE added_at = added_at
            """)
            conn.execute(stmt, {"user_id": user_id, "stock_id": stock_id})
            return True

    @staticmethod
    def remove(user_id: int, stock_id: int) -> bool:
        """Removes a stock from user's watchlist."""
        with get_db_transaction() as conn:
            stmt = text("DELETE FROM Watchlist WHERE user_id = :user_id AND stock_id = :stock_id")
            res = conn.execute(stmt, {"user_id": user_id, "stock_id": stock_id})
            return res.rowcount > 0

    @staticmethod
    def is_in_watchlist(user_id: int, stock_id: int) -> bool:
        """Checks if a stock is in user's watchlist."""
        with get_db_connection() as conn:
            stmt = text("SELECT 1 FROM Watchlist WHERE user_id = :user_id AND stock_id = :stock_id LIMIT 1")
            return conn.execute(stmt, {"user_id": user_id, "stock_id": stock_id}).scalar() is not None
