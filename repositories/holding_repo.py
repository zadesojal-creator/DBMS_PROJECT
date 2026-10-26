"""
Holding Repository (repositories/holding_repo.py)
Data access operations for investor holdings and portfolio positions.
"""
from typing import Optional, Dict, Any, List
from sqlalchemy import text
from models.db import get_db_connection

class HoldingRepository:
    @staticmethod
    def get_by_user(user_id: int) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            query = """
                SELECT 
                    user_id, stock_id, symbol, company_name, sector,
                    quantity, avg_cost, cost_basis, current_price,
                    market_value, unrealized_pnl, return_pct, day_change,
                    day_change_pct, updated_at
                FROM v_investor_portfolio
                WHERE user_id = :user_id AND quantity > 0
                ORDER BY market_value DESC
            """
            rows = conn.execute(text(query), {"user_id": user_id}).mappings().all()
            return [dict(r) for r in rows]

    @staticmethod
    def get_by_user_and_stock(user_id: int, stock_id: int) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            query = """
                SELECT 
                    user_id, stock_id, symbol, company_name, sector,
                    quantity, avg_cost, cost_basis, current_price,
                    market_value, unrealized_pnl, return_pct, day_change,
                    day_change_pct, updated_at
                FROM v_investor_portfolio
                WHERE user_id = :user_id AND stock_id = :stock_id
            """
            row = conn.execute(text(query), {"user_id": user_id, "stock_id": stock_id}).mappings().first()
            return dict(row) if row else None
