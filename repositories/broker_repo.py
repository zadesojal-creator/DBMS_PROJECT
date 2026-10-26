"""
Broker Repository (repositories/broker_repo.py)
Data access operations for broker client relationships and commission analytics.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from sqlalchemy import text, insert
from models.db import get_db_connection, get_db_transaction
from models.schema import users_table, accounts_table, account_ledger_table, broker_clients_table

class BrokerRepository:
    @staticmethod
    def get_clients(broker_id: int) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            query = """
                SELECT 
                    broker_id, investor_id, 
                    investor_name, investor_name AS full_name,
                    investor_email, investor_email AS email,
                    investor_name AS username,
                    investor_status, assigned_at, virtual_balance, total_trades,
                    total_volume, total_commission_generated
                FROM v_broker_client_summary
                WHERE broker_id = :broker_id
                ORDER BY investor_name ASC
            """
            rows = conn.execute(text(query), {"broker_id": broker_id}).mappings().all()
            return [dict(r) for r in rows]

    @staticmethod
    def is_assigned(broker_id: int, investor_id: int) -> bool:
        with get_db_connection() as conn:
            query = """
                SELECT 1 FROM Broker_Clients 
                WHERE broker_id = :broker_id AND investor_id = :investor_id AND status = 'ACTIVE'
                LIMIT 1
            """
            return conn.execute(text(query), {"broker_id": broker_id, "investor_id": investor_id}).scalar() is not None

    @staticmethod
    def get_assigned_broker_for_investor(investor_id: int) -> Optional[Dict[str, Any]]:
        """Returns active assigned broker details for an investor."""
        with get_db_connection() as conn:
            query = """
                SELECT 
                    u.id AS broker_id,
                    u.full_name AS broker_name,
                    u.email AS broker_email,
                    u.phone AS broker_phone,
                    bc.assigned_at
                FROM Broker_Clients bc
                JOIN Users u ON bc.broker_id = u.id
                WHERE bc.investor_id = :investor_id AND bc.status = 'ACTIVE'
                LIMIT 1
            """
            row = conn.execute(text(query), {"investor_id": investor_id}).mappings().first()
            if not row:
                return None
            res = dict(row)
            if res.get("assigned_at") and hasattr(res["assigned_at"], "strftime"):
                res["assigned_at"] = res["assigned_at"].strftime("%Y-%m-%d %H:%M:%S")
            return res

    @staticmethod
    def onboard_client(
        broker_id: int, username: str, email: str, full_name: str,
        password_hash: str, phone: Optional[str] = None, grant_amount: Decimal = Decimal('100000.00')
    ) -> int:
        """Atomically creates investor user, account, opening grant ledger entry, and active Broker_Clients row."""
        with get_db_transaction() as conn:
            # 1. Create User
            u_stmt = insert(users_table).values(
                username=username.strip(),
                email=email.strip().lower(),
                password_hash=password_hash,
                full_name=full_name.strip(),
                phone=phone.strip() if phone else None,
                role='INVESTOR',
                status='ACTIVE',
                is_demo=False,
                failed_login_attempts=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            u_res = conn.execute(u_stmt)
            investor_id = u_res.inserted_primary_key[0]

            # 2. Create Account
            a_stmt = insert(accounts_table).values(
                user_id=investor_id,
                virtual_balance=grant_amount,
                currency='INR',
                status='ACTIVE',
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            a_res = conn.execute(a_stmt)
            account_id = a_res.inserted_primary_key[0]

            # 3. Create Opening Grant Ledger Entry
            al_stmt = insert(account_ledger_table).values(
                account_id=account_id,
                entry_type='OPENING_GRANT',
                amount=grant_amount,
                balance_after=grant_amount,
                reference_type='SYSTEM',
                reference_id=f"GRANT_{account_id}",
                note='Virtual Signup Grant',
                created_at=datetime.utcnow()
            )
            conn.execute(al_stmt)

            # 4. Create Active Broker_Clients Row
            bc_stmt = insert(broker_clients_table).values(
                broker_id=broker_id,
                investor_id=investor_id,
                status='ACTIVE',
                assigned_at=datetime.utcnow(),
                ended_at=None
            )
            conn.execute(bc_stmt)

            return investor_id

    @staticmethod
    def assign_client(broker_id: int, investor_id: int) -> bool:
        """Assigns an investor to a broker as ACTIVE."""
        with get_db_transaction() as conn:
            conn.execute(text("""
                INSERT INTO Broker_Clients (broker_id, investor_id, status, assigned_at)
                VALUES (:broker_id, :investor_id, 'ACTIVE', CURRENT_TIMESTAMP)
            """), {"broker_id": broker_id, "investor_id": investor_id})
            return True

    @staticmethod
    def end_assignment(broker_id: int, investor_id: int) -> bool:
        with get_db_transaction() as conn:
            query = """
                UPDATE Broker_Clients 
                SET status = 'ENDED', ended_at = CURRENT_TIMESTAMP
                WHERE broker_id = :broker_id AND investor_id = :investor_id AND status = 'ACTIVE'
            """
            res = conn.execute(text(query), {"broker_id": broker_id, "investor_id": investor_id})
            return res.rowcount > 0

    @staticmethod
    def get_commission_analytics(broker_id: int) -> Dict[str, Any]:
        with get_db_connection() as conn:
            # Total commission
            q_total = """
                SELECT 
                    COALESCE(SUM(commission_amount), 0.00) AS total_commission,
                    COUNT(id) AS total_commission_trades,
                    COALESCE(SUM(base_brokerage), 0.00) AS total_brokerage_generated
                FROM Commissions
                WHERE broker_id = :broker_id
            """
            total_stats = dict(conn.execute(text(q_total), {"broker_id": broker_id}).mappings().first())

            # Today's commission
            q_today = """
                SELECT COALESCE(SUM(commission_amount), 0.00)
                FROM Commissions
                WHERE broker_id = :broker_id AND DATE(created_at) = CURRENT_DATE
            """
            today_comm = conn.execute(text(q_today), {"broker_id": broker_id}).scalar() or Decimal('0.00')

            # This month's commission
            q_month = """
                SELECT COALESCE(SUM(commission_amount), 0.00)
                FROM Commissions
                WHERE broker_id = :broker_id 
                  AND YEAR(created_at) = YEAR(CURRENT_DATE) 
                  AND MONTH(created_at) = MONTH(CURRENT_DATE)
            """
            month_comm = conn.execute(text(q_month), {"broker_id": broker_id}).scalar() or Decimal('0.00')

            # Monthly trend
            q_trend = """
                SELECT 
                    DATE_FORMAT(created_at, '%Y-%m') AS month_label,
                    COUNT(id) AS trade_count,
                    COALESCE(SUM(commission_amount), 0.00) AS commission_earned
                FROM Commissions
                WHERE broker_id = :broker_id
                GROUP BY DATE_FORMAT(created_at, '%Y-%m')
                ORDER BY month_label ASC
                LIMIT 12
            """
            trend = [dict(r) for r in conn.execute(text(q_trend), {"broker_id": broker_id}).mappings().all()]

            # Top clients by commission
            q_top = """
                SELECT 
                    c.investor_id, u.full_name AS investor_name,
                    COUNT(c.id) AS trades,
                    COALESCE(SUM(c.commission_amount), 0.00) AS commission_generated
                FROM Commissions c
                JOIN Users u ON c.investor_id = u.id
                WHERE c.broker_id = :broker_id
                GROUP BY c.investor_id, u.full_name
                ORDER BY commission_generated DESC
                LIMIT 5
            """
            top_clients = [dict(r) for r in conn.execute(text(q_top), {"broker_id": broker_id}).mappings().all()]

            # Complete investor-wise commission breakdown
            q_investors = """
                SELECT 
                    bcs.investor_id,
                    bcs.investor_name,
                    bcs.investor_email,
                    bcs.investor_status,
                    bcs.assigned_at,
                    bcs.virtual_balance,
                    bcs.total_trades,
                    bcs.total_volume,
                    bcs.total_commission_generated,
                    COALESCE(bd.buy_count, 0) AS buy_trades,
                    COALESCE(bd.sell_count, 0) AS sell_trades,
                    bd.last_trade_at
                FROM v_broker_client_summary bcs
                LEFT JOIN (
                    SELECT 
                        bc.investor_id,
                        SUM(CASE WHEN t.side = 'BUY' THEN 1 ELSE 0 END) AS buy_count,
                        SUM(CASE WHEN t.side = 'SELL' THEN 1 ELSE 0 END) AS sell_count,
                        MAX(t.executed_at) AS last_trade_at
                    FROM Broker_Clients bc
                    JOIN Transactions t ON bc.investor_id = t.user_id
                    WHERE bc.broker_id = :broker_id AND bc.status = 'ACTIVE'
                    GROUP BY bc.investor_id
                ) bd ON bcs.investor_id = bd.investor_id
                WHERE bcs.broker_id = :broker_id
                ORDER BY bcs.total_commission_generated DESC, bcs.total_volume DESC
            """
            investor_rows = [dict(r) for r in conn.execute(text(q_investors), {"broker_id": broker_id}).mappings().all()]
            total_comm_dec = Decimal(str(total_stats["total_commission"]))

            investor_commissions = []
            for inv in investor_rows:
                comm_gen = Decimal(str(inv["total_commission_generated"]))
                pct = float((comm_gen / total_comm_dec * 100)) if total_comm_dec > 0 else 0.0
                trades_cnt = int(inv["total_trades"])
                vol = Decimal(str(inv["total_volume"]))
                avg_size = float(vol / trades_cnt) if trades_cnt > 0 else 0.0
                investor_commissions.append({
                    "investor_id": inv["investor_id"],
                    "investor_name": inv["investor_name"],
                    "investor_email": inv["investor_email"],
                    "investor_status": inv["investor_status"],
                    "assigned_at": inv["assigned_at"].strftime("%Y-%m-%d %H:%M") if hasattr(inv["assigned_at"], "strftime") else str(inv["assigned_at"]),
                    "virtual_balance": float(inv["virtual_balance"]),
                    "total_trades": trades_cnt,
                    "buy_trades": int(inv["buy_trades"]),
                    "sell_trades": int(inv["sell_trades"]),
                    "total_volume": float(vol),
                    "commission_generated": float(comm_gen),
                    "contribution_pct": round(pct, 2),
                    "avg_trade_size": round(avg_size, 2),
                    "last_activity": inv["last_trade_at"].strftime("%Y-%m-%d %H:%M") if inv.get("last_trade_at") and hasattr(inv["last_trade_at"], "strftime") else (inv["assigned_at"].strftime("%Y-%m-%d %H:%M") if hasattr(inv["assigned_at"], "strftime") else None)
                })

            # Trade Analysis: side breakdown and top stocks
            q_sides = """
                SELECT 
                    t.side,
                    COUNT(t.id) AS order_count,
                    COALESCE(SUM(t.gross_amount), 0.00) AS turnover,
                    COALESCE(SUM(c.commission_amount), 0.00) AS commission
                FROM Transactions t
                JOIN Broker_Clients bc ON t.user_id = bc.investor_id AND bc.status = 'ACTIVE'
                LEFT JOIN Commissions c ON t.id = c.transaction_id AND c.broker_id = :broker_id
                WHERE bc.broker_id = :broker_id
                GROUP BY t.side
            """
            side_stats = {r["side"]: dict(r) for r in conn.execute(text(q_sides), {"broker_id": broker_id}).mappings().all()}

            q_top_stocks = """
                SELECT 
                    s.symbol,
                    s.company_name,
                    COUNT(t.id) AS total_orders,
                    SUM(t.quantity) AS total_quantity,
                    COALESCE(SUM(t.gross_amount), 0.00) AS total_turnover,
                    COALESCE(SUM(c.commission_amount), 0.00) AS commission_generated
                FROM Transactions t
                JOIN Stocks s ON t.stock_id = s.id
                JOIN Broker_Clients bc ON t.user_id = bc.investor_id AND bc.status = 'ACTIVE'
                LEFT JOIN Commissions c ON t.id = c.transaction_id AND c.broker_id = :broker_id
                WHERE bc.broker_id = :broker_id
                GROUP BY s.id, s.symbol, s.company_name
                ORDER BY total_turnover DESC
                LIMIT 5
            """
            top_stocks = [{
                "symbol": r["symbol"],
                "company_name": r["company_name"],
                "total_orders": r["total_orders"],
                "total_quantity": int(r["total_quantity"]),
                "total_turnover": float(r["total_turnover"]),
                "commission_generated": float(r["commission_generated"])
            } for r in conn.execute(text(q_top_stocks), {"broker_id": broker_id}).mappings().all()]

            total_turnover = sum(float(r.get("turnover", 0)) for r in side_stats.values())

            trade_analysis = {
                "total_turnover": round(total_turnover, 2),
                "buy_orders": side_stats.get("BUY", {}).get("order_count", 0),
                "buy_turnover": float(side_stats.get("BUY", {}).get("turnover", 0)),
                "buy_commission": float(side_stats.get("BUY", {}).get("commission", 0)),
                "sell_orders": side_stats.get("SELL", {}).get("order_count", 0),
                "sell_turnover": float(side_stats.get("SELL", {}).get("turnover", 0)),
                "sell_commission": float(side_stats.get("SELL", {}).get("commission", 0)),
                "top_stocks": top_stocks
            }

            return {
                "total_commission": Decimal(str(total_stats["total_commission"])),
                "total_trades": total_stats["total_commission_trades"],
                "today_commission": Decimal(str(today_comm)),
                "this_month_commission": Decimal(str(month_comm)),
                "monthly_trend": trend,
                "top_clients": top_clients,
                "investor_commissions": investor_commissions,
                "trade_analysis": trade_analysis
            }
