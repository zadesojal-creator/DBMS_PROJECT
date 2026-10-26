"""
Portfolio Service (services/portfolio_service.py)
Canonical calculation of portfolio metrics, holdings value, and reconciliation invariant.
Reused consistently by Dashboard, API, Reports, and AI SQL Assistant.
"""
from decimal import Decimal
from typing import Dict, Any, List
from sqlalchemy import text
from models.db import get_db_connection
from repositories.account_repo import AccountRepository
from repositories.holding_repo import HoldingRepository
from repositories.transaction_repo import TransactionRepository
from repositories.ledger_repo import LedgerRepository

class PortfolioService:
    @staticmethod
    def get_portfolio_summary(user_id: int) -> Dict[str, Any]:
        """
        Computes canonical portfolio metrics directly from database rows:
        1. Available cash (ledger sum)
        2. Holdings market value
        3. Total portfolio value
        4. Unrealized P&L
        5. Realized P&L
        6. Total P&L
        7. Overall return %
        8. Today's approximate P&L
        """
        account = AccountRepository.get_by_user_id(user_id)
        if not account:
            return {
                "available_cash": Decimal('0.00'),
                "holdings_market_value": Decimal('0.00'),
                "total_portfolio_value": Decimal('0.00'),
                "total_invested_cost": Decimal('0.00'),
                "unrealized_pnl": Decimal('0.00'),
                "realized_pnl": Decimal('0.00'),
                "total_pnl": Decimal('0.00'),
                "return_pct": None,
                "today_pnl_approx": Decimal('0.00'),
                "holdings_count": 0,
                "is_reconciled": True
            }

        account_id = account['id']
        cash_balance, ledger_sum, is_reconciled = LedgerRepository.reconcile(account_id)

        holdings = HoldingRepository.get_by_user(user_id)
        realized_pnl = TransactionRepository.get_realized_pnl_total(user_id)

        holdings_market_val = Decimal('0.00')
        total_cost_basis = Decimal('0.00')
        unrealized_pnl = Decimal('0.00')
        today_pnl_approx = Decimal('0.00')

        for h in holdings:
            qty = Decimal(str(h['quantity']))
            avg_c = Decimal(str(h['avg_cost']))
            curr_p = Decimal(str(h['current_price']))
            prev_c = Decimal(str(h.get('previous_close', curr_p)))

            cost = (qty * avg_c)
            m_val = (qty * curr_p)
            unrel = (qty * (curr_p - avg_c))
            today_change = (qty * (curr_p - prev_c))

            total_cost_basis += cost
            holdings_market_val += m_val
            unrealized_pnl += unrel
            today_pnl_approx += today_change

        total_portfolio_val = cash_balance + holdings_market_val
        total_pnl = realized_pnl + unrealized_pnl

        return_pct = None
        if total_cost_basis > Decimal('0.00'):
            return_pct = float(round((total_pnl / total_cost_basis) * Decimal('100.0'), 2))

        return {
            "available_cash": cash_balance,
            "holdings_market_value": holdings_market_val,
            "total_portfolio_value": total_portfolio_val,
            "total_invested_cost": total_cost_basis,
            "unrealized_pnl": unrealized_pnl,
            "realized_pnl": realized_pnl,
            "total_pnl": total_pnl,
            "return_pct": return_pct,
            "today_pnl_approx": today_pnl_approx,
            "holdings_count": len(holdings),
            "is_reconciled": is_reconciled
        }

    @staticmethod
    def get_sector_allocation(user_id: int) -> List[Dict[str, Any]]:
        """Computes portfolio sector allocation for charts and risk analysis."""
        with get_db_connection() as conn:
            query = """
                SELECT 
                    sector,
                    COALESCE(SUM(market_value), 0.00) AS total_value,
                    COUNT(stock_id) AS holding_count
                FROM v_investor_portfolio
                WHERE user_id = :user_id AND quantity > 0
                GROUP BY sector
                ORDER BY total_value DESC
            """
            rows = conn.execute(text(query), {"user_id": user_id}).mappings().all()
            return [dict(r) for r in rows]

    @staticmethod
    def verify_reconciliation_invariants(user_id: int) -> Dict[str, Any]:
        """
        Exhaustively verifies both accounting invariants:
        1. Accounts.virtual_balance == SUM(Account_Ledger.amount)
        2. Holdings.qty == SUM(buys) - SUM(sells) per stock
        """
        account = AccountRepository.get_by_user_id(user_id)
        if not account:
            return {"cash_reconciled": True, "holdings_reconciled": True}

        # 1. Cash invariant
        b, l_sum, cash_reconciled = LedgerRepository.reconcile(account['id'])

        # 2. Holdings quantity invariant per stock
        with get_db_connection() as conn:
            q = """
                SELECT 
                    h.stock_id,
                    h.quantity AS holding_qty,
                    COALESCE(SUM(CASE WHEN t.side = 'BUY' THEN t.quantity ELSE -t.quantity END), 0) AS transaction_qty
                FROM Holdings h
                LEFT JOIN Transactions t ON h.user_id = t.user_id AND h.stock_id = t.stock_id
                WHERE h.user_id = :user_id
                GROUP BY h.stock_id, h.quantity
            """
            rows = conn.execute(text(q), {"user_id": user_id}).mappings().all()
            holdings_reconciled = all(int(r['holding_qty']) == int(r['transaction_qty']) for r in rows)

        return {
            "cash_reconciled": cash_reconciled,
            "holdings_reconciled": holdings_reconciled,
            "virtual_balance": float(b),
            "ledger_sum": float(l_sum)
        }
