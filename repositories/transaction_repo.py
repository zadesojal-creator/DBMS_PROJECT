"""
Transaction Repository (repositories/transaction_repo.py)
Data access operations for executed trades and transaction statements.
"""
from decimal import Decimal
from typing import Optional, Dict, Any, List
from sqlalchemy import text
from models.db import get_db_connection

class TransactionRepository:
    @staticmethod
    def get_by_user(
        user_id: int, side: Optional[str] = None, stock_id: Optional[int] = None,
        limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            query = """
                SELECT 
                    transaction_id, order_id, user_id, stock_id, symbol,
                    company_name, sector, side, quantity, execution_price,
                    gross_amount, brokerage_fee, net_amount, realized_pnl, executed_at
                FROM v_investor_transactions
                WHERE user_id = :user_id
            """
            params: Dict[str, Any] = {"user_id": user_id, "limit": limit, "offset": offset}
            if side:
                query += " AND side = :side"
                params["side"] = side.upper()
            if stock_id:
                query += " AND stock_id = :stock_id"
                params["stock_id"] = stock_id
            query += " ORDER BY executed_at DESC LIMIT :limit OFFSET :offset"
            
            rows = conn.execute(text(query), params).mappings().all()
            return [dict(r) for r in rows]

    @staticmethod
    def get_total_count(user_id: int) -> int:
        with get_db_connection() as conn:
            stmt = text("SELECT COUNT(*) FROM Transactions WHERE user_id = :user_id")
            return conn.execute(stmt, {"user_id": user_id}).scalar() or 0

    @staticmethod
    def get_realized_pnl_total(user_id: int) -> Decimal:
        with get_db_connection() as conn:
            stmt = text("SELECT COALESCE(SUM(realized_pnl), 0.00) FROM Transactions WHERE user_id = :user_id")
            val = conn.execute(stmt, {"user_id": user_id}).scalar()
            return Decimal(str(val)) if val is not None else Decimal('0.00')

    @staticmethod
    def get_by_broker(broker_id: int, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            query = """
                SELECT 
                    transaction_id, broker_id, investor_id, investor_name,
                    stock_id, symbol, company_name, side, quantity,
                    execution_price, gross_amount, brokerage_fee, net_amount,
                    broker_commission_earned, executed_at
                FROM v_broker_client_transactions
                WHERE broker_id = :broker_id
                ORDER BY executed_at DESC
                LIMIT :limit OFFSET :offset
            """
            rows = conn.execute(text(query), {
                "broker_id": broker_id, "limit": limit, "offset": offset
            }).mappings().all()
            return [dict(r) for r in rows]
