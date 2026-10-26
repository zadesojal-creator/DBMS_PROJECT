"""
Stock Repository (repositories/stock_repo.py)
Data access operations for Stocks, Current_Prices, and Market Quotes.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from sqlalchemy import select, update, insert, delete, text
from models.db import get_db_connection, get_db_transaction
from models.schema import stocks_table, current_prices_table

class StockRepository:
    @staticmethod
    def get_by_id(stock_id: int) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            stmt = select(stocks_table).where(stocks_table.c.id == stock_id)
            row = conn.execute(stmt).mappings().first()
            return dict(row) if row else None

    @staticmethod
    def get_by_symbol(symbol: str) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            stmt = select(stocks_table).where(stocks_table.c.symbol == symbol.strip().upper())
            row = conn.execute(stmt).mappings().first()
            return dict(row) if row else None

    @staticmethod
    def get_market_overview(sector: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            query = """
                SELECT 
                    stock_id, symbol, company_name, sector, exchange, status,
                    current_price, previous_close, day_change, day_change_pct,
                    day_open, day_high, day_low, volume, updated_at
                FROM v_market_latest
                WHERE 1=1
            """
            params: Dict[str, Any] = {}
            if sector:
                query += " AND sector = :sector"
                params['sector'] = sector
            if search:
                query += " AND (symbol LIKE :search OR company_name LIKE :search)"
                params['search'] = f"%{search.strip()}%"
            query += " ORDER BY symbol ASC"
            
            rows = conn.execute(text(query), params).mappings().all()
            return [dict(r) for r in rows]

    @staticmethod
    def get_quote(stock_id: int) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            query = """
                SELECT 
                    stock_id, symbol, company_name, sector, exchange, status,
                    current_price, previous_close, day_change, day_change_pct,
                    day_open, day_high, day_low, volume, updated_at
                FROM v_market_latest
                WHERE stock_id = :stock_id
            """
            row = conn.execute(text(query), {"stock_id": stock_id}).mappings().first()
            return dict(row) if row else None

    @staticmethod
    def create_stock(symbol: str, company_name: str, sector: str, exchange: str = 'NSE', ref_price: Decimal = Decimal('100.00')) -> int:
        with get_db_transaction() as conn:
            # 1. Insert stock
            stmt = insert(stocks_table).values(
                symbol=symbol.strip().upper(),
                company_name=company_name.strip(),
                sector=sector.strip(),
                exchange=exchange.strip().upper(),
                status='ACTIVE',
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            result = conn.execute(stmt)
            stock_id = result.inserted_primary_key[0]

            # 2. Insert initial Current_Prices cache
            cp_stmt = insert(current_prices_table).values(
                stock_id=stock_id,
                price=ref_price,
                previous_close=ref_price,
                day_open=ref_price,
                day_high=ref_price,
                day_low=ref_price,
                volume=0,
                updated_at=datetime.utcnow()
            )
            conn.execute(cp_stmt)
            return stock_id

    @staticmethod
    def update_stock(stock_id: int, company_name: str, sector: str, status: str):
        with get_db_transaction() as conn:
            stmt = (
                update(stocks_table)
                .where(stocks_table.c.id == stock_id)
                .values(
                    company_name=company_name.strip(),
                    sector=sector.strip(),
                    status=status.upper(),
                    updated_at=datetime.utcnow()
                )
            )
            conn.execute(stmt)

    @staticmethod
    def hard_delete_stock(stock_id: int) -> bool:
        """
        Guarded hard-delete: Allowed if and only if zero orders, zero holdings,
        zero alerts, and no simulated prices exist beyond initial seed rows.
        """
        with get_db_transaction() as conn:
            # Check orders
            orders_cnt = conn.execute(text("SELECT COUNT(*) FROM Orders WHERE stock_id = :id"), {"id": stock_id}).scalar()
            if orders_cnt > 0:
                raise ValueError("Cannot hard-delete stock with existing trading orders. Use deactivation.")

            # Check holdings
            holdings_cnt = conn.execute(text("SELECT COUNT(*) FROM Holdings WHERE stock_id = :id AND quantity > 0"), {"id": stock_id}).scalar()
            if holdings_cnt > 0:
                raise ValueError("Cannot hard-delete stock currently held by investors.")

            # Check price alerts
            alerts_cnt = conn.execute(text("SELECT COUNT(*) FROM Price_Alerts WHERE stock_id = :id"), {"id": stock_id}).scalar()
            if alerts_cnt > 0:
                raise ValueError("Cannot hard-delete stock with configured price alerts.")

            # Check non-seeded prices
            sim_prices = conn.execute(text("SELECT COUNT(*) FROM Stock_Prices WHERE stock_id = :id AND source = 'SIMULATED'"), {"id": stock_id}).scalar()
            if sim_prices > 0:
                raise ValueError("Cannot hard-delete stock with active simulated trade history.")

            # Delete seeded prices and current price
            conn.execute(text("DELETE FROM Stock_Prices WHERE stock_id = :id"), {"id": stock_id})
            conn.execute(delete(current_prices_table).where(current_prices_table.c.stock_id == stock_id))
            conn.execute(delete(stocks_table).where(stocks_table.c.id == stock_id))
            return True
