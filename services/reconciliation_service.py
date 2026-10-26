"""
Financial Reconciliation Service (services/reconciliation_service.py)
Implements comprehensive system-wide audits across 7 core financial invariants:
1. Operational account balances vs. ledger signed amounts sum
2. Holdings share quantities vs. net executed transactions (buys - sells)
3. Completed orders without corresponding financial transactions
4. Transactions missing required principal or fee ledger journal records
5. Broker commissions inconsistent with active assignments and platform rules
6. Duplicate financial events (order transactions, commissions, idempotency keys)
7. Missing, duplicate, or corrupted opening virtual cash grants (₹1,00,000 baseline)

Treats Accounts.virtual_balance as operational and Account_Ledger as the authoritative source.
Reports discrepancies with zero silent modifications.
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List
from sqlalchemy import text
from models.db import get_engine, get_db_connection

class ReconciliationService:
    @staticmethod
    def run_full_reconciliation() -> Dict[str, Any]:
        """
        Executes all 7 system-wide financial integrity audits.
        Returns a structured dictionary with overall status, discrepancy counts, and itemized findings.
        """
        discrepancies: Dict[str, List[Dict[str, Any]]] = {
            "account_balance_mismatches": [],
            "holding_quantity_mismatches": [],
            "executed_orders_without_transactions": [],
            "transactions_missing_ledger": [],
            "commission_inconsistencies": [],
            "duplicate_financial_events": [],
            "opening_grant_inconsistencies": []
        }

        with get_db_connection() as conn:
            # Check 1: Account Balance vs. Ledger Sum
            q1 = text("""
                SELECT 
                    a.id AS account_id,
                    a.user_id,
                    u.username,
                    a.virtual_balance AS operational_balance,
                    COALESCE(SUM(al.amount), 0.00) AS ledger_sum,
                    ROUND(a.virtual_balance - COALESCE(SUM(al.amount), 0.00), 2) AS discrepancy_amount
                FROM Accounts a
                JOIN Users u ON a.user_id = u.id
                LEFT JOIN Account_Ledger al ON a.id = al.account_id
                GROUP BY a.id, a.user_id, u.username, a.virtual_balance
                HAVING a.virtual_balance != COALESCE(SUM(al.amount), 0.00)
            """)
            for row in conn.execute(q1).mappings().all():
                discrepancies["account_balance_mismatches"].append({
                    "account_id": row["account_id"],
                    "user_id": row["user_id"],
                    "username": row["username"],
                    "operational_balance": float(row["operational_balance"]),
                    "ledger_sum": float(row["ledger_sum"]),
                    "discrepancy_amount": float(row["discrepancy_amount"])
                })

            # Check 2: Holdings Quantity vs. Net Traded Shares
            q2 = text("""
                SELECT 
                    h.user_id,
                    u.username,
                    h.stock_id,
                    s.symbol,
                    h.quantity AS holding_quantity,
                    COALESCE(SUM(CASE WHEN t.side = 'BUY' THEN t.quantity ELSE -t.quantity END), 0) AS net_traded_quantity,
                    (h.quantity - COALESCE(SUM(CASE WHEN t.side = 'BUY' THEN t.quantity ELSE -t.quantity END), 0)) AS discrepancy_quantity
                FROM Holdings h
                JOIN Users u ON h.user_id = u.id
                JOIN Stocks s ON h.stock_id = s.id
                LEFT JOIN Transactions t ON h.user_id = t.user_id AND h.stock_id = t.stock_id
                GROUP BY h.user_id, u.username, h.stock_id, s.symbol, h.quantity
                HAVING h.quantity != COALESCE(SUM(CASE WHEN t.side = 'BUY' THEN t.quantity ELSE -t.quantity END), 0)
            """)
            for row in conn.execute(q2).mappings().all():
                discrepancies["holding_quantity_mismatches"].append({
                    "user_id": row["user_id"],
                    "username": row["username"],
                    "stock_id": row["stock_id"],
                    "symbol": row["symbol"],
                    "holding_quantity": row["holding_quantity"],
                    "net_traded_quantity": int(row["net_traded_quantity"]),
                    "discrepancy_quantity": int(row["discrepancy_quantity"])
                })

            # Check 3: Executed Orders without Associated Transactions
            q3 = text("""
                SELECT 
                    o.id AS order_id,
                    o.user_id,
                    u.username,
                    o.stock_id,
                    s.symbol,
                    o.side,
                    o.quantity,
                    o.executed_price,
                    o.created_at
                FROM Orders o
                JOIN Users u ON o.user_id = u.id
                JOIN Stocks s ON o.stock_id = s.id
                LEFT JOIN Transactions t ON o.id = t.order_id
                WHERE o.status = 'EXECUTED' AND t.id IS NULL
            """)
            for row in conn.execute(q3).mappings().all():
                discrepancies["executed_orders_without_transactions"].append({
                    "order_id": row["order_id"],
                    "user_id": row["user_id"],
                    "username": row["username"],
                    "symbol": row["symbol"],
                    "side": row["side"],
                    "quantity": row["quantity"],
                    "executed_price": float(row["executed_price"]) if row["executed_price"] else None,
                    "created_at": str(row["created_at"])
                })

            # Check 4: Completed Transactions Missing Required Ledger Entries
            q4 = text("""
                SELECT 
                    t.id AS transaction_id,
                    t.order_id,
                    t.user_id,
                    t.stock_id,
                    t.side,
                    t.quantity,
                    t.net_amount,
                    t.executed_at
                FROM Transactions t
                WHERE NOT EXISTS (
                    SELECT 1 
                    FROM Account_Ledger al 
                    WHERE al.reference_type = 'TRANSACTION' 
                      AND al.reference_id = CAST(t.id AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_unicode_ci
                      AND al.entry_type IN ('BUY', 'SELL')
                ) OR NOT EXISTS (
                    SELECT 1 
                    FROM Account_Ledger al 
                    WHERE al.reference_type = 'TRANSACTION' 
                      AND al.reference_id = CAST(t.id AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_unicode_ci
                      AND al.entry_type = 'FEE'
                )
            """)
            for row in conn.execute(q4).mappings().all():
                discrepancies["transactions_missing_ledger"].append({
                    "transaction_id": row["transaction_id"],
                    "order_id": row["order_id"],
                    "user_id": row["user_id"],
                    "side": row["side"],
                    "quantity": row["quantity"],
                    "net_amount": float(row["net_amount"]),
                    "executed_at": str(row["executed_at"])
                })

            # Check 5: Broker Commission Inconsistencies
            q5 = text("""
                SELECT 
                    t.id AS transaction_id,
                    t.user_id AS investor_id,
                    bc.broker_id,
                    t.brokerage_fee,
                    c.id AS commission_id,
                    c.commission_amount AS recorded_commission,
                    ROUND(t.brokerage_fee * cr.rate, 2) AS expected_commission,
                    ROUND(COALESCE(c.commission_amount, 0.00) - ROUND(t.brokerage_fee * cr.rate, 2), 2) AS discrepancy_amount
                FROM Transactions t
                JOIN Broker_Clients bc ON t.user_id = bc.investor_id 
                    AND bc.status = 'ACTIVE'
                    AND t.executed_at >= bc.assigned_at
                    AND (bc.ended_at IS NULL OR t.executed_at <= bc.ended_at)
                LEFT JOIN Commissions c ON t.id = c.transaction_id
                JOIN Commission_Rules cr ON cr.rule_type = 'BROKER_COMMISSION' AND cr.is_active = TRUE
                WHERE c.id IS NULL OR c.commission_amount != ROUND(t.brokerage_fee * cr.rate, 2)
            """)
            for row in conn.execute(q5).mappings().all():
                discrepancies["commission_inconsistencies"].append({
                    "transaction_id": row["transaction_id"],
                    "investor_id": row["investor_id"],
                    "broker_id": row["broker_id"],
                    "brokerage_fee": float(row["brokerage_fee"]),
                    "recorded_commission": float(row["recorded_commission"]) if row["recorded_commission"] is not None else None,
                    "expected_commission": float(row["expected_commission"]),
                    "discrepancy_amount": float(row["discrepancy_amount"])
                })

            # Check 6: Duplicate Financial Events
            q6a = text("""
                SELECT order_id, COUNT(*) AS count 
                FROM Transactions 
                GROUP BY order_id 
                HAVING COUNT(*) > 1
            """)
            for row in conn.execute(q6a).mappings().all():
                discrepancies["duplicate_financial_events"].append({
                    "type": "DUPLICATE_ORDER_TRANSACTION",
                    "order_id": row["order_id"],
                    "count": row["count"]
                })

            q6b = text("""
                SELECT transaction_id, COUNT(*) AS count 
                FROM Commissions 
                GROUP BY transaction_id 
                HAVING COUNT(*) > 1
            """)
            for row in conn.execute(q6b).mappings().all():
                discrepancies["duplicate_financial_events"].append({
                    "type": "DUPLICATE_TRANSACTION_COMMISSION",
                    "transaction_id": row["transaction_id"],
                    "count": row["count"]
                })

            q6c = text("""
                SELECT user_id, idempotency_key, COUNT(*) AS count 
                FROM Orders 
                WHERE status = 'EXECUTED' 
                GROUP BY user_id, idempotency_key 
                HAVING COUNT(*) > 1
            """)
            for row in conn.execute(q6c).mappings().all():
                discrepancies["duplicate_financial_events"].append({
                    "type": "DUPLICATE_IDEMPOTENCY_EXECUTION",
                    "user_id": row["user_id"],
                    "idempotency_key": row["idempotency_key"],
                    "count": row["count"]
                })

            # Check 7: Missing or Inconsistent Opening Grants
            q7 = text("""
                SELECT 
                    a.id AS account_id,
                    a.user_id,
                    u.username,
                    u.role,
                    COUNT(al.id) AS grant_count,
                    COALESCE(SUM(al.amount), 0.00) AS total_grant_amount
                FROM Accounts a
                JOIN Users u ON a.user_id = u.id
                LEFT JOIN Account_Ledger al ON a.id = al.account_id AND al.entry_type = 'OPENING_GRANT'
                WHERE u.role = 'INVESTOR'
                GROUP BY a.id, a.user_id, u.username, u.role
                HAVING COUNT(al.id) != 1 OR COALESCE(SUM(al.amount), 0.00) != 100000.00
            """)
            for row in conn.execute(q7).mappings().all():
                discrepancies["opening_grant_inconsistencies"].append({
                    "account_id": row["account_id"],
                    "user_id": row["user_id"],
                    "username": row["username"],
                    "grant_count": row["grant_count"],
                    "total_grant_amount": float(row["total_grant_amount"])
                })

        total_issues = sum(len(items) for items in discrepancies.values())
        status = "HEALTHY" if total_issues == 0 else "DISCREPANCIES_DETECTED"

        return {
            "status": status,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_discrepancies": total_issues,
            "discrepancy_counts": {k: len(v) for k, v in discrepancies.items()},
            "summary": f"System status {status}: {total_issues} discrepancy(ies) detected across 7 financial invariants.",
            "details": discrepancies,
            "discrepancies": discrepancies
        }
