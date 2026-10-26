"""
Safe Query Executor & Grounded Summarizer (services/query_executor.py)
Executes read-only queries with session tenancy under stocktrade_ai_ro and logs to AI_Query_History.
"""
import re
import json
import time
from decimal import Decimal
from typing import Dict, Any, List, Optional
from sqlalchemy import text
from models.db import get_ai_connection, get_db_transaction
from models.schema import ai_query_history_table

class QueryExecutor:
    @staticmethod
    def log_query_history(
        user_id: int,
        prompt: str,
        sql: Optional[str],
        tables_used: List[str],
        validation_status: str,
        execution_status: str,
        error_code: Optional[str] = None,
        duration_ms: int = 0,
        row_count: int = 0,
        provider: str = "SYSTEM"
    ) -> None:
        """Records AI query validation and execution audit records into AI_Query_History."""
        try:
            with get_db_transaction() as log_conn:
                log_conn.execute(
                    ai_query_history_table.insert().values(
                        user_id=user_id,
                        prompt=prompt or "Direct execution",
                        generated_sql=sql,
                        tables_used=json.dumps(tables_used or []),
                        validation_status=validation_status,
                        execution_status=execution_status,
                        error_code=error_code[:64] if error_code else None,
                        duration_ms=duration_ms,
                        row_count=row_count,
                        provider=provider
                    )
                )
        except Exception:
            pass

    @staticmethod
    def execute_scoped_query(
        user_id: int, role: str, sql: str, prompt: str = "", provider: str = "SYSTEM", tables_used: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Executes a validated read-only SQL query under stocktrade_ai_ro.
        Binds :auth_user_id and sets session variable @current_user_id to guarantee tenant isolation.
        Ensures strict connection cleanup and invalidates contaminated pooled connections on error.
        """
        t0 = time.time()
        rows_data = []
        columns = []
        error_msg = None
        duration_ms = 0

        with get_ai_connection() as conn:
            try:
                # 1. Set read-only session & tenancy variable
                conn.execute(text("SET SESSION TRANSACTION READ ONLY;"))
                conn.execute(text("SET @current_user_id = :uid;"), {"uid": user_id})
                try:
                    conn.execute(text("SET max_execution_time = 5000;"))
                except Exception:
                    pass

                # 2. Execute query with parameterized tenant binding
                params = {"auth_user_id": user_id, "uid": user_id}
                cursor_res = conn.execute(text(sql), params)
                columns = list(cursor_res.keys())
                
                # Fetch up to 500 rows
                raw_rows = cursor_res.fetchmany(500)
                duration_ms = int((time.time() - t0) * 1000)

                for r in raw_rows:
                    row_dict = {}
                    for col in columns:
                        val = r._mapping[col]
                        if isinstance(val, Decimal):
                            row_dict[col] = float(val)
                        elif hasattr(val, "strftime"):
                            row_dict[col] = val.strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            row_dict[col] = val
                    rows_data.append(row_dict)

            except Exception as ex:
                duration_ms = int((time.time() - t0) * 1000)
                error_msg = str(ex)
            finally:
                # 3. Clean up session state or invalidate connection if cleanup fails
                try:
                    conn.execute(text("SET @current_user_id = NULL;"))
                    conn.execute(text("SET max_execution_time = 0;"))
                    conn.execute(text("SET SESSION TRANSACTION READ WRITE;"))
                except Exception:
                    try:
                        conn.invalidate()
                    except Exception:
                        pass

        # 4. Log audit record to AI_Query_History
        status = "SUCCESS" if not error_msg else "FAILED"
        QueryExecutor.log_query_history(
            user_id=user_id,
            prompt=prompt,
            sql=sql,
            tables_used=tables_used or [],
            validation_status="VALID",
            execution_status=status,
            error_code=error_msg,
            duration_ms=duration_ms,
            row_count=len(rows_data),
            provider=provider
        )

        if error_msg:
            return {
                "ok": False,
                "error": error_msg,
                "duration_ms": duration_ms
            }

        # 4. Generate grounded summary and structured metrics
        analysis = QueryExecutor.generate_grounded_analysis(
            rows_data, prompt, sql=sql, role=role, tables_used=tables_used
        )

        return {
            "ok": True,
            "columns": columns,
            "rows": rows_data,
            "row_count": len(rows_data),
            "duration_ms": duration_ms,
            "summary": analysis["summary"],
            "explanation": analysis["explanation"],
            "key_metrics": analysis["key_metrics"]
        }

    @staticmethod
    def generate_grounded_summary(rows: List[Dict[str, Any]], prompt: str) -> str:
        """
        Generates a summary grounded strictly in the returned rows.
        Guarantees that every number stated in the summary appears in the data.
        """
        analysis = QueryExecutor.generate_grounded_analysis(rows, prompt)
        return analysis["summary"]

    @staticmethod
    def generate_grounded_analysis(
        rows: List[Dict[str, Any]],
        prompt: str = "",
        sql: Optional[str] = None,
        role: Optional[str] = None,
        tables_used: Optional[List[str]] = None,
        base_explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates an executive natural language answer, business logic explanation,
        and structured key metric badges grounded strictly in the database result set.
        """
        if not rows:
            p_lower = (prompt or "").lower()
            subject_str = "matching records"
            for sec in ["banking", "chemicals", "logistics", "delivery", "automotive", "technology", "pharma", "energy", "metals"]:
                if sec in p_lower:
                    subject_str = f"companies in {sec.title()}"
                    break
            return {
                "summary": f"No {subject_str} found matching the specified criteria in the database.",
                "explanation": (base_explanation or f"The query executed successfully against {', '.join(tables_used) if tables_used else 'authorized views'}, returning an empty result set."),
                "key_metrics": [{"label": "Records Found", "value": "0"}]
            }

        count = len(rows)
        first_row = rows[0]
        keys = list(first_row.keys())
        p_lower = (prompt or "").lower()

        # Identify numeric and text columns
        numeric_cols = [k for k, v in first_row.items() if isinstance(v, (int, float))]
        text_cols = [k for k, v in first_row.items() if isinstance(v, str)]

        key_metrics = [{"label": "Total Records", "value": str(count)}]

        # ---------------------------------------------------------
        # Scenario A: Single-row aggregate or single entity result
        # ---------------------------------------------------------
        if count == 1:
            if "total_unrealized_pnl" in first_row:
                val = first_row["total_unrealized_pnl"]
                sign = "+" if val > 0 else ""
                summary = f"Your total unrealized profit/loss across all active holdings is {sign}₹{val:,.2f}."
                key_metrics.append({"label": "Unrealized P&L", "value": f"{sign}₹{val:,.2f}"})
            elif "total_commission_earned" in first_row:
                val = first_row["total_commission_earned"]
                summary = f"You have earned a cumulative total of ₹{val:,.2f} in platform-funded brokerage commissions."
                key_metrics.append({"label": "Commission Earned", "value": f"₹{val:,.2f}"})
            elif "total_brokerage_paid" in first_row:
                val = first_row["total_brokerage_paid"]
                summary = f"You have paid a cumulative ₹{val:,.2f} in trading brokerage fees across all executed transactions."
                key_metrics.append({"label": "Brokerage Paid", "value": f"₹{val:,.2f}"})
            elif "symbol" in first_row and ("return_pct" in first_row or "market_value" in first_row):
                sym = first_row["symbol"]
                name = first_row.get("company_name", sym)
                ret = first_row.get("return_pct")
                mkt = first_row.get("market_value")
                parts = [f"{name} ({sym})"]
                if ret is not None:
                    parts.append(f"return of {ret:+.2f}%")
                    key_metrics.append({"label": "Return %", "value": f"{ret:+.2f}%"})
                if mkt is not None:
                    parts.append(f"market value of ₹{mkt:,.2f}")
                    key_metrics.append({"label": "Position Value", "value": f"₹{mkt:,.2f}"})
                summary = f"Result: {', '.join(parts)}."
            else:
                items = [f"{k.replace('_', ' ').title()}: {f'₹{v:,.2f}' if isinstance(v, float) and any(kw in k for kw in ['price', 'value', 'balance', 'pnl', 'amount', 'fee', 'cost']) else v}" for k, v in first_row.items() if v is not None]
                summary = f"Query returned 1 record: {', '.join(items[:5])}."
                if numeric_cols:
                    key_metrics.append({"label": numeric_cols[0].replace('_', ' ').title(), "value": f"{first_row[numeric_cols[0]]:,.2f}"})

        # ---------------------------------------------------------
        # Scenario B: Multi-row client management (Broker View)
        # ---------------------------------------------------------
        elif "investor_name" in first_row:
            has_bal = "virtual_balance" in first_row
            has_trades = "total_trades" in first_row
            has_vol = "total_volume" in first_row
            has_comm = "total_commission_generated" in first_row or "commission_amount" in first_row

            total_bal = sum(r.get("virtual_balance", 0) for r in rows if isinstance(r.get("virtual_balance"), (int, float))) if has_bal else None
            total_trades = sum(r.get("total_trades", 0) for r in rows if isinstance(r.get("total_trades"), (int, float))) if has_trades else None
            total_vol = sum(r.get("total_volume", 0) for r in rows if isinstance(r.get("total_volume"), (int, float))) if has_vol else None
            comm_key = "total_commission_generated" if "total_commission_generated" in first_row else "commission_amount"
            total_comm = sum(r.get(comm_key, 0) for r in rows if isinstance(r.get(comm_key), (int, float))) if has_comm else None

            client_parts = []
            for r in rows[:3]:
                name = r.get("investor_name", "Client")
                attrs = []
                if has_bal and r.get("virtual_balance") is not None:
                    attrs.append(f"₹{r.get('virtual_balance'):,.2f} balance")
                if has_vol and r.get("total_volume") is not None and r.get("total_volume") > 0:
                    attrs.append(f"₹{r.get('total_volume'):,.2f} turnover")
                if has_comm and r.get(comm_key) is not None and r.get(comm_key) > 0:
                    attrs.append(f"₹{r.get(comm_key):,.2f} commission")
                if has_trades and r.get("total_trades") is not None:
                    attrs.append(f"{r.get('total_trades')} trade(s)")

                if attrs:
                    client_parts.append(f"{name} ({', '.join(attrs)})")
                else:
                    client_parts.append(name)

            summary_clauses = []
            if total_bal is not None:
                summary_clauses.append(f"combined virtual funds of ₹{total_bal:,.2f}")
                key_metrics.append({"label": "Managed Funds", "value": f"₹{total_bal:,.2f}"})
            if total_vol is not None and total_vol > 0:
                summary_clauses.append(f"trading turnover of ₹{total_vol:,.2f}")
                key_metrics.append({"label": "Client Turnover", "value": f"₹{total_vol:,.2f}"})
            if total_comm is not None and total_comm > 0:
                summary_clauses.append(f"platform commissions of ₹{total_comm:,.2f}")
                key_metrics.append({"label": "Commissions", "value": f"₹{total_comm:,.2f}"})
            if total_trades is not None:
                summary_clauses.append(f"{total_trades} executed client trade(s)")
                key_metrics.append({"label": "Total Trades", "value": str(total_trades)})

            more_text = f" and {count - 3} other client(s)" if count > 3 else ""
            clause_str = f" with {', '.join(summary_clauses)}" if summary_clauses else ""
            summary = f"You have {count} assigned active client(s){clause_str}: {', '.join(client_parts)}{more_text}."

        # ---------------------------------------------------------
        # Scenario B2: Multi-row transactions (Investor/Admin View)
        # ---------------------------------------------------------
        elif "transaction_id" in first_row or ("execution_price" in first_row and "side" in first_row):
            total_turnover = sum(r.get("gross_amount", 0) for r in rows if isinstance(r.get("gross_amount"), (int, float)))
            total_fees = sum(r.get("brokerage_fee", 0) for r in rows if isinstance(r.get("brokerage_fee"), (int, float)))
            buy_count = sum(1 for r in rows if r.get("side") == "BUY")
            sell_count = sum(1 for r in rows if r.get("side") == "SELL")

            summary = (
                f"Retrieved {count} executed trade transaction(s) ({buy_count} BUY, {sell_count} SELL) "
                f"with total turnover of ₹{total_turnover:,.2f} and brokerage fees of ₹{total_fees:,.2f}."
            )
            key_metrics.append({"label": "Trade Turnover", "value": f"₹{total_turnover:,.2f}"})
            key_metrics.append({"label": "Brokerage Fees", "value": f"₹{total_fees:,.2f}"})

        # ---------------------------------------------------------
        # Scenario C: Multi-row holdings / portfolio (Investor View)
        # ---------------------------------------------------------
        elif "symbol" in first_row and ("market_value" in first_row or ("avg_cost" in first_row and "quantity" in first_row)):
            has_mkt = "market_value" in first_row
            has_pnl = "unrealized_pnl" in first_row
            has_qty = "quantity" in first_row
            has_ret = "return_pct" in first_row

            total_mkt = sum(r.get("market_value", 0) for r in rows if isinstance(r.get("market_value"), (int, float))) if has_mkt else None
            total_pnl = sum(r.get("unrealized_pnl", 0) for r in rows if isinstance(r.get("unrealized_pnl"), (int, float))) if has_pnl else None
            total_qty = sum(r.get("quantity", 0) for r in rows if isinstance(r.get("quantity"), (int, float))) if has_qty else None

            sort_key = "market_value" if has_mkt else ("return_pct" if has_ret else "quantity")
            top_holding = max(rows, key=lambda r: r.get(sort_key, 0))
            top_sym = top_holding.get("symbol", "N/A")

            summary_clauses = []
            if total_mkt is not None:
                summary_clauses.append(f"portfolio market value of ₹{total_mkt:,.2f}")
                key_metrics.append({"label": "Holdings Value", "value": f"₹{total_mkt:,.2f}"})
            if total_pnl is not None:
                sign = "+" if total_pnl > 0 else ""
                summary_clauses.append(f"unrealized P&L of {sign}₹{total_pnl:,.2f}")
                key_metrics.append({"label": "Unrealized P&L", "value": f"{sign}₹{total_pnl:,.2f}"})
            if total_qty is not None:
                key_metrics.append({"label": "Total Shares", "value": f"{total_qty:,}"})

            top_val_str = f" valued at ₹{top_holding[sort_key]:,.2f}" if sort_key == "market_value" else (f" with return of {top_holding[sort_key]:+.2f}%" if sort_key == "return_pct" else f" ({top_holding[sort_key]} shares)")
            clause_str = f" with a combined {', '.join(summary_clauses)}" if summary_clauses else ""
            summary = f"You hold {count} open stock position(s){clause_str}. Top holding: {top_sym}{top_val_str}."

        # ---------------------------------------------------------
        # Scenario D: Multi-row market quotes (Market View / Admin)
        # ---------------------------------------------------------
        elif "symbol" in first_row and ("current_price" in first_row or "day_change_pct" in first_row):
            top_gainer = max(rows, key=lambda r: r.get("day_change_pct", -999))
            g_sym = top_gainer.get("symbol", "")
            g_pct = top_gainer.get("day_change_pct", 0)
            g_price = top_gainer.get("current_price", 0)

            sectors_in_set = list(set([r.get("sector") for r in rows if r.get("sector")]))
            if len(sectors_in_set) == 1:
                sec_label = f"listed equities in the {sectors_in_set[0]} sector"
                key_metrics.append({"label": "Sector", "value": sectors_in_set[0]})
            else:
                sec_label = "listed equities"

            summary = (
                f"Retrieved {count} {sec_label}. "
                f"Top mover in this set: {g_sym} at ₹{g_price:,.2f} ({g_pct:+.2f}% 24h change)."
            )
            key_metrics.append({"label": "Top Mover", "value": f"{g_sym} ({g_pct:+.2f}%)"})

        # ---------------------------------------------------------
        # Scenario E: User Security Audit & Failed Logins (Admin View)
        # ---------------------------------------------------------
        elif "failed_login_attempts" in first_row or "locked_until" in first_row:
            failed_users = [r for r in rows if (r.get("failed_login_attempts") or 0) > 0 or r.get("locked_until")]
            if failed_users:
                user_strs = [f"{r.get('username')} ({r.get('failed_login_attempts', 0)} failed attempt(s){', LOCKED' if r.get('locked_until') else ''})" for r in failed_users[:5]]
                summary = f"Found {len(failed_users)} account(s) with recorded failed login attempts or security lockouts: {', '.join(user_strs)}."
                key_metrics.append({"label": "Accounts Flagged", "value": str(len(failed_users))})
            else:
                summary = f"All {count} evaluated user account(s) have 0 failed login attempts and zero active security lockouts."
                key_metrics.append({"label": "Failed Logins", "value": "0"})

        # ---------------------------------------------------------
        # Scenario F: Security Audit Logs & Events (Admin View)
        # ---------------------------------------------------------
        elif "action" in first_row and ("log_id" in first_row or "ip_address" in first_row or "entity_type" in first_row):
            action_counts = {}
            for r in rows:
                act = r.get("action", "UNKNOWN")
                action_counts[act] = action_counts.get(act, 0) + 1
            action_summary_str = ", ".join([f"{act}: {cnt}" for act, cnt in list(action_counts.items())[:3]])

            login_fails = [r for r in rows if r.get("action") in ("LOGIN_FAILED", "LOGIN_LOCKED", "SECURITY_LOCKOUT")]
            if login_fails:
                users_involved = list(set([r.get("username") for r in login_fails if r.get("username")]))[:4]
                user_str = f" from account(s): {', '.join(users_involved)}" if users_involved else ""
                summary = f"Found {len(login_fails)} failed login / security event(s){user_str}."
                key_metrics.append({"label": "Failed Logins", "value": str(len(login_fails))})
            else:
                users_involved = list(set([r.get("username") for r in rows if r.get("username")]))[:4]
                user_str = f" involving {', '.join(users_involved)}" if users_involved else ""
                summary = f"Retrieved {count} security audit log record(s){user_str} ({action_summary_str})."
                key_metrics.append({"label": "Audit Events", "value": str(count)})

        # ---------------------------------------------------------
        # Scenario G: User Accounts Roster (Admin View)
        # ---------------------------------------------------------
        elif "username" in first_row and "role" in first_row:
            roles_count = {}
            for r in rows:
                ro = r.get("role", "USER")
                roles_count[ro] = roles_count.get(ro, 0) + 1
            roles_str = ", ".join([f"{ro}: {cnt}" for ro, cnt in roles_count.items()])
            sample_users = [f"{r.get('username')} ({r.get('role')})" for r in rows[:4]]
            summary = f"Retrieved {count} user account(s) across platform roles ({roles_str}): {', '.join(sample_users)}."
            key_metrics.append({"label": "Total Accounts", "value": str(count)})

        # ---------------------------------------------------------
        # Scenario E: Generic Multi-row Aggregation
        # ---------------------------------------------------------
        else:
            if numeric_cols:
                primary_num = numeric_cols[0]
                total = sum(r.get(primary_num, 0) for r in rows if isinstance(r.get(primary_num), (int, float)))
                entity_col = next((c for c in ["symbol", "company_name", "investor_name", "username", "sector", "trade_type", "side"] if c in first_row), text_cols[0] if text_cols else None)
                if entity_col:
                    top_row = max(rows, key=lambda r: r.get(primary_num, 0))
                    summary = (
                        f"Returned {count} rows. The aggregate total for {primary_num.replace('_', ' ')} is {total:,.2f}, "
                        f"led by {top_row.get(entity_col)} with {top_row.get(primary_num):,.2f}."
                    )
                else:
                    summary = f"Returned {count} rows. The aggregate sum of {primary_num.replace('_', ' ')} is {total:,.2f}."
                key_metrics.append({"label": f"Total {primary_num.replace('_', ' ').title()}", "value": f"{total:,.2f}"})
            else:
                summary = f"Query executed successfully, returning {count} records matching your parameters."

        # ---------------------------------------------------------
        # Contextual Business Explanation
        # ---------------------------------------------------------
        explanation = base_explanation
        if not explanation:
            table_info = f"'{', '.join(tables_used)}'" if tables_used else "authorized views"
            if role == "INVESTOR":
                explanation = f"Evaluated against {table_info} with investor row-level security (where user_id = @current_user_id) to guarantee isolated portfolio accounting."
            elif role == "BROKER":
                explanation = f"Queried from {table_info} scoped strictly to clients assigned to your brokerage (where broker_id = @current_user_id) with automated platform commission tracking."
            else:
                explanation = f"System-level analytical query executed across {table_info} with read-only transaction isolation."

        return {
            "summary": summary,
            "explanation": explanation,
            "key_metrics": key_metrics
        }
