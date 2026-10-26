"""
Semantic Consistency Validator (services/semantic_validator.py)
Validates that generated SQL preserves the user's intent, accesses the correct domain,
enforces explicit constraints (sector, symbol, time, logins), and does not substitute
unrelated queries.
"""
from typing import Tuple, Optional, List, Dict, Any
import re
import sqlglot
from sqlglot import exp
from services.intent_service import Intent, IntentService

class SemanticValidator:
    @staticmethod
    def validate_consistency(
        prompt: str,
        intent: Intent,
        raw_sql: str,
        role: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates semantic consistency between user prompt, extracted intent, and generated SQL.
        Returns (is_consistent, error_code, error_message).
        """
        if not raw_sql or not raw_sql.strip():
            return False, "EMPTY_SQL", "SQL query is empty."

        if not intent.is_supported:
            return False, "UNSUPPORTED_REQUEST", intent.explanation or "Request is not supported by database schema."

        clean_sql = raw_sql.strip().rstrip(";")
        try:
            parsed = sqlglot.parse(clean_sql, read="mysql")
            if not parsed or len(parsed) != 1:
                return False, "SYNTAX_ERROR", "Query must be a single parseable SQL statement."
            ast = parsed[0]
        except Exception as e:
            return False, "SYNTAX_ERROR", f"SQL Parse Error: {str(e)}"

        # Extract queried tables/views
        tables_queried = [t.name.lower() for t in ast.find_all(exp.Table)]
        if not tables_queried:
            return False, "NO_TABLES", "Query does not select from any tables or views."

        lower_sql = clean_sql.lower()
        where_node = ast.find(exp.Where)
        where_str = where_node.sql(dialect="mysql").lower() if where_node else ""

        # ----------------------------------------------------------------------
        # Check 1: Target View & Domain Consistency
        # ----------------------------------------------------------------------
        if intent.domain == "ADMIN_AUDIT":
            # Must query audit logs
            if "v_admin_audit_logs" not in tables_queried:
                return False, "DOMAIN_MISMATCH", f"Expected query on 'v_admin_audit_logs' for security/login events, but query targeted '{', '.join(tables_queried)}'."
            if intent.failed_login_only:
                if not any(kw in where_str for kw in ["login_failed", "login_locked", "security_lockout", "action"]):
                    return False, "MISSING_LOGIN_FILTER", "Query must filter by failed login action ('LOGIN_FAILED' or 'SECURITY_LOCKOUT')."
            if intent.time_filter and intent.time_filter != "today" and intent.time_filter != "this_month":
                time_clean = intent.time_filter[:5] # e.g. "09:30"
                if time_clean not in where_str and intent.time_filter not in where_str:
                    return False, "MISSING_TIME_FILTER", f"Query must filter for time '{intent.time_filter}'."

        elif intent.domain == "ADMIN_USERS":
            if "v_admin_user_audit" not in tables_queried and "v_admin_audit_logs" not in tables_queried:
                return False, "DOMAIN_MISMATCH", f"Expected query on 'v_admin_user_audit' for user accounts, but query targeted '{', '.join(tables_queried)}'."
            if intent.failed_login_only:
                if not any(kw in where_str for kw in ["failed_login_attempts", "locked_until", "login_failed"]):
                    return False, "MISSING_LOGIN_FILTER", "Query must filter for accounts with failed login attempts or lockouts."

        elif intent.domain == "INVESTOR_TRANSACTIONS":
            if "v_investor_transactions" not in tables_queried:
                return False, "DOMAIN_MISMATCH", f"Expected query on 'v_investor_transactions' for executed trades/brokerage, but query targeted '{', '.join(tables_queried)}'."

        elif intent.domain == "INVESTOR_PORTFOLIO":
            if "v_investor_portfolio" not in tables_queried:
                return False, "DOMAIN_MISMATCH", f"Expected query on 'v_investor_portfolio' for holdings/portfolio, but query targeted '{', '.join(tables_queried)}'."

        elif intent.domain == "BROKER_CLIENTS":
            if "v_broker_client_summary" not in tables_queried:
                return False, "DOMAIN_MISMATCH", f"Expected query on 'v_broker_client_summary' for assigned clients, but query targeted '{', '.join(tables_queried)}'."

        elif intent.domain == "BROKER_COMMISSIONS":
            if "v_broker_commissions" not in tables_queried:
                return False, "DOMAIN_MISMATCH", f"Expected query on 'v_broker_commissions' for commissions earned, but query targeted '{', '.join(tables_queried)}'."

        elif intent.domain == "ADMIN_PLATFORM_TRADES":
            if "v_admin_trade_facts" not in tables_queried:
                return False, "DOMAIN_MISMATCH", f"Expected query on 'v_admin_trade_facts' for platform turnover, but query targeted '{', '.join(tables_queried)}'."

        elif intent.domain == "MARKET_EQUITIES":
            if "v_market_latest" not in tables_queried and "stocks" not in tables_queried:
                return False, "DOMAIN_MISMATCH", f"Expected query on 'v_market_latest' for market equities, but query targeted '{', '.join(tables_queried)}'."

        # ----------------------------------------------------------------------
        # Check 2: Explicit Constraint Preservation (Sector, Symbol)
        # ----------------------------------------------------------------------
        if intent.sector and intent.domain in ("MARKET_EQUITIES", "INVESTOR_PORTFOLIO", "INVESTOR_TRANSACTIONS"):
            sec_lower = intent.sector.lower()
            # If Logistics, allow Delivery or Delhviery mention
            if intent.sector == "Logistics" and ("delivery" in where_str or "delhivery" in where_str or "logistics" in where_str):
                pass
            elif sec_lower not in where_str:
                return False, "MISSING_SECTOR_FILTER", f"User requested sector '{intent.sector}', but WHERE clause does not filter by this sector."

        if intent.symbol and intent.domain in ("MARKET_EQUITIES", "INVESTOR_PORTFOLIO", "INVESTOR_TRANSACTIONS"):
            sym_lower = intent.symbol.lower()
            if sym_lower not in where_str and (not intent.company_name_query or intent.company_name_query.lower() not in where_str):
                return False, "MISSING_SYMBOL_FILTER", f"User requested symbol/company '{intent.symbol}', but WHERE clause does not filter for it."

        # ----------------------------------------------------------------------
        # Check 3: Scope and Arbitrary Truncation
        # ----------------------------------------------------------------------
        limit_node = ast.find(exp.Limit)
        if limit_node and intent.scope == "ALL":
            try:
                curr_limit = int(limit_node.expression.this)
                # If user asked for all matching records (e.g. all 8 banks), an arbitrary limit of 10 or 5 is a mismatch
                if curr_limit in (5, 10) and not any(w in prompt.lower() for w in ["top 5", "top 10", "5 highest", "10 highest"]):
                    return False, "ARBITRARY_LIMIT", f"Query arbitrarily truncated result with LIMIT {curr_limit} when user requested all records."
            except Exception:
                pass

        return True, None, None

    @staticmethod
    def get_corrected_or_fallback_sql(
        prompt: str,
        intent: Intent,
        role: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Produces a semantically guaranteed SQL query using the IntentService generator
        when LLM generation is unavailable or fails semantic validation.
        """
        resolver = IntentService.get_instance()
        generated = resolver.generate_sql(intent, role)
        if reason:
            generated["explanation"] = f"{generated.get('explanation', '')} (Semantically verified fallback applied: {reason})"
        return generated
