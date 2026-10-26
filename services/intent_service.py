"""
Intent Resolver & Schema Grounding Service (services/intent_service.py)
Extracts structured intent from user requests, resolves domain entities against
the actual database schema and catalog, and generates intent-preserving SQL.
"""
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Set
from sqlalchemy import text
from models.db import get_db_connection

@dataclass
class Intent:
    raw_prompt: str
    role: str
    domain: str  # 'MARKET_EQUITIES', 'INVESTOR_PORTFOLIO', 'INVESTOR_TRANSACTIONS', 'BROKER_CLIENTS', 'BROKER_TRANSACTIONS', 'BROKER_COMMISSIONS', 'ADMIN_USERS', 'ADMIN_AUDIT', 'ADMIN_PLATFORM_TRADES', 'ADMIN_COMMISSION_RULES', 'UNKNOWN', 'UNSUPPORTED'
    target_view: str
    operation: str  # 'LIST', 'COUNT', 'SUM', 'AVG', 'RANK', 'SUMMARY', 'COMPARE'
    entity_type: Optional[str] = None  # 'SECTOR', 'STOCK', 'USER', 'TRANSACTION', 'COMMISSION', 'POLICY'
    sector: Optional[str] = None  # Exact canonical database sector name (e.g. 'Banking', 'Chemicals', 'Logistics')
    symbol: Optional[str] = None  # e.g. 'TCS', 'HDFCBANK', 'DELHIVERY'
    company_name_query: Optional[str] = None
    time_filter: Optional[str] = None  # e.g. 'till_930', 'today', 'this_month'
    failed_login_only: bool = False
    lockout_only: bool = False
    scope: str = 'ALL'  # 'ALL' or 'TOP_N'
    limit: Optional[int] = None
    order_by_col: Optional[str] = None
    order_direction: str = 'ASC'
    is_supported: bool = True
    is_ambiguous: bool = False
    clarification_message: Optional[str] = None
    explanation: str = ""
    tables_used: List[str] = field(default_factory=list)


class IntentService:
    _instance: Optional['IntentService'] = None
    _sectors_cache: Set[str] = set()
    _symbols_cache: Dict[str, str] = {}  # symbol -> company_name
    _initialized: bool = False

    # Canonical Sector Synonym Mapping
    SECTOR_SYNONYMS = {
        "Banking": ["bank", "banks", "banking", "lender", "lenders", "financial institutions"],
        "Chemicals": ["chemical", "chemicals", "specialty chemicals", "chem", "chems"],
        "Logistics": ["delivery", "courier", "logistics", "freight", "transport", "transportation", "shipping", "supply chain"],
        "Information Technology": ["it", "tech", "technology", "software", "computer", "computers", "infotech", "tech companies", "it sector"],
        "Healthcare & Pharma": ["pharma", "pharmaceutical", "pharmaceuticals", "drug", "drugs", "medicine", "medicines", "healthcare", "health", "hospital", "hospitals"],
        "Automotive": ["auto", "automobile", "automobiles", "automotive", "car", "cars", "motor", "motors", "vehicle", "vehicles"],
        "Energy & Power": ["energy", "power", "oil", "gas", "petroleum", "electricity", "refinery", "utilities"],
        "Consumer Goods & FMCG": ["fmcg", "consumer goods", "packaged goods", "household"],
        "Metals & Mining": ["metal", "metals", "mining", "steel", "iron", "aluminum", "minerals"],
        "Telecom & Media": ["telecom", "telecoms", "telecommunication", "media", "broadcast", "broadcasting", "cinema", "entertainment"],
        "Retail & Consumer Services": ["retail", "consumer services", "shopping", "ecommerce", "e-commerce"],
        "Real Estate": ["real estate", "realty", "property", "builders", "housing", "developers"],
        "Defense & Aerospace": ["defense", "defence", "aerospace", "military"],
        "Cement & Building Materials": ["cement", "building materials", "construction materials"],
        "Consumer Electricals": ["electrical", "electricals", "cables", "wires"],
        "Financial Services": ["financial services", "finance", "nbfc", "insurance", "amc"],
        "Infrastructure & Construction": ["infrastructure", "construction", "infra"],
        "Capital Goods": ["capital goods", "heavy machinery", "engineering equipment"]
    }

    # Out of domain keywords
    OUT_OF_DOMAIN_KEYWORDS = [
        "weather", "climate", "temperature", "cricket", "football", "sports", "capital of",
        "prime minister", "president", "recipe", "cooking", "movie review", "translate",
        "poem", "song", "joke", "riddle", "horoscope", "astrology"
    ]

    def __init__(self):
        self._load_catalog()

    @classmethod
    def get_instance(cls) -> 'IntentService':
        if cls._instance is None:
            cls._instance = IntentService()
        return cls._instance

    def _load_catalog(self) -> None:
        """Loads live distinct sectors and stock tickers from MySQL database."""
        try:
            with get_db_connection() as conn:
                sectors = conn.execute(text("SELECT DISTINCT sector FROM Stocks WHERE sector IS NOT NULL;")).scalars().all()
                self._sectors_cache = set(sectors)

                stocks = conn.execute(text("SELECT symbol, company_name FROM Stocks;")).mappings().all()
                self._symbols_cache = {s["symbol"].upper(): s["company_name"] for s in stocks}
                self._initialized = True
        except Exception:
            # Fallback to standard canonical catalog if DB cold start
            self._sectors_cache = set(self.SECTOR_SYNONYMS.keys())
            self._initialized = True

    def resolve_sector(self, text_input: str) -> Optional[str]:
        """Resolves informal wording or sector synonyms to canonical database sector name."""
        lower = f" {text_input.lower()} "
        # 1. Exact match against database sectors
        for sec in self._sectors_cache:
            pattern = rf"\b{re.escape(sec.lower())}\b"
            if re.search(pattern, lower):
                return sec

        # 2. Check synonyms
        for canonical, syns in self.SECTOR_SYNONYMS.items():
            for syn in syns:
                pattern = rf"\b{re.escape(syn.lower())}\b"
                if re.search(pattern, lower):
                    return canonical

        # 3. Check for explicit sector mention syntax: "in the <word> sector" or "<word> sector"
        sec_match = re.search(r'\b(?:in(?:\s+the)?\s+)?([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+sector\b', text_input, re.IGNORECASE)
        if sec_match:
            candidate = sec_match.group(1).strip().title()
            if candidate.lower() not in ("each", "all", "every", "this", "that"):
                return candidate

        return None

    def resolve_symbol(self, text_input: str) -> Tuple[Optional[str], Optional[str]]:
        """Resolves explicit ticker symbol or company name."""
        tokens = re.findall(r'[A-Za-z0-9&\-]+', text_input)
        for t in tokens:
            t_upper = t.upper()
            if t_upper in self._symbols_cache:
                return t_upper, self._symbols_cache[t_upper]

        # Check partial company name match
        lower_prompt = text_input.lower()
        for sym, name in self._symbols_cache.items():
            # Check company base name (e.g. "reliance" -> "Reliance Industries Ltd")
            base_name = name.split()[0].lower()
            if len(base_name) >= 4 and f" {base_name} " in f" {lower_prompt} ":
                return sym, name

        return None, None

    def resolve_intent(self, prompt: str, role: str) -> Intent:
        """
        Parses user prompt into a structured, schema-grounded Intent.
        Preserves constraints, target domain, sector filters, scope, and time criteria.
        """
        p = prompt.strip()
        p_lower = p.lower()
        r = role.upper()

        # Check for out-of-domain requests
        for ood in self.OUT_OF_DOMAIN_KEYWORDS:
            if ood in p_lower:
                return Intent(
                    raw_prompt=p,
                    role=r,
                    domain="UNSUPPORTED",
                    target_view="",
                    operation="LIST",
                    is_supported=False,
                    explanation="The requested subject is outside the financial trading platform database scope.",
                    clarification_message=f"The StockTrade database manages virtual stock trading, market prices, investor portfolios, broker commissions, and security audit logs, but does not contain information about '{ood}'."
                )

        # 1. Detect Sector / Symbol / Company
        resolved_sector = self.resolve_sector(p_lower)
        resolved_symbol, resolved_company = self.resolve_symbol(p)

        # 2. Detect Operation
        op = "LIST"
        if any(w in p_lower for w in ["how many", "count of", "number of", "count "]):
            op = "COUNT"
        elif any(w in p_lower for w in ["total turnover", "total volume", "total brokerage", "total fees", "sum of", "total amount"]):
            op = "SUM"
        elif any(w in p_lower for w in ["average", "avg price", "avg return", "mean "]):
            op = "AVG"
        elif any(w in p_lower for w in ["top", "highest", "most", "lowest", "least", "best", "worst", "leading", "gainers", "losers", "gained the most"]):
            op = "RANK"
        elif any(w in p_lower for w in ["breakdown", "grouped by", "per sector", "by sector", "by role"]):
            op = "COMPARE"

        # 3. Detect Scope & Limit
        scope = "ALL"
        limit_val = 500  # Default system safety cap for ALL
        top_match = re.search(r'\btop\s+(\d+)\b|\b(\d+)\s+(highest|lowest|most|best|worst|gainers|losers)\b', p_lower)
        if top_match:
            scope = "TOP_N"
            limit_val = int(top_match.group(1) or top_match.group(2))
        elif any(w in p_lower for w in ["top gainer", "best performing", "top loser", "highest price"]):
            if "top" in p_lower and not any(w in p_lower for w in ["all", "list all", "every"]):
                # Single top entity
                scope = "TOP_N"
                limit_val = 1
        elif any(w in p_lower for w in ["all", "every", "list", "show me all", "show all"]):
            scope = "ALL"
            limit_val = 500

        # 4. Detect Time Filters
        time_filter = None
        # E.g. "till 9:30", "before 9:30", "at 9:30", "till 9.30", "until 9:30"
        time_match = re.search(r'\b(?:till|before|until|up to|at)\s+(\d{1,2})[:\.](\d{2})\b', p_lower)
        if time_match:
            hh = int(time_match.group(1))
            mm = int(time_match.group(2))
            time_filter = f"{hh:02d}:{mm:02d}:00"
        elif "today" in p_lower:
            time_filter = "today"
        elif "this month" in p_lower:
            time_filter = "this_month"

        # 5. Detect Sorting & Direction
        order_col = None
        order_dir = "ASC"
        if any(w in p_lower for w in ["gainers", "highest return", "gained the most", "top return"]):
            order_col = "day_change_pct"
            order_dir = "DESC"
        elif any(w in p_lower for w in ["losers", "worst return", "lost the most", "down the most"]):
            order_col = "day_change_pct"
            order_dir = "ASC"
        elif any(w in p_lower for w in ["volume", "most traded", "highest volume", "most active"]):
            order_col = "volume"
            order_dir = "DESC"
        elif any(w in p_lower for w in ["highest price", "most expensive", "top price"]):
            order_col = "current_price"
            order_dir = "DESC"
        elif any(w in p_lower for w in ["lowest price", "cheapest"]):
            order_col = "current_price"
            order_dir = "ASC"
        elif any(w in p_lower for w in ["most failed", "highest failed"]):
            order_col = "failed_login_attempts"
            order_dir = "DESC"
        elif any(w in p_lower for w in ["recent", "latest", "newest"]):
            order_col = "created_at"
            order_dir = "DESC"

        # 6. Domain & Target View Resolution
        # -------------------------------------------------------------
        # Security & User Audit Domain
        has_login_kw = any(w in p_lower for w in ["login", "log in", "logged in", "logins", "sign in", "signed in", "password", "attempts", "auth"])
        has_fail_kw = any(w in p_lower for w in ["fail", "failed", "failure", "unsuccessful", "wrong", "rejected", "invalid", "bad"])
        has_lock_kw = any(w in p_lower for w in ["lock", "locked", "lockout", "lockouts", "brute force"])
        has_audit_kw = any(w in p_lower for w in ["audit log", "audit logs", "security event", "security events", "security log"])
        is_security_query = (has_login_kw and (has_fail_kw or has_lock_kw)) or has_lock_kw or has_audit_kw

        if is_security_query:
            if r != "ADMIN":
                return Intent(
                    raw_prompt=p,
                    role=r,
                    domain="ADMIN_AUDIT",
                    target_view="",
                    operation=op,
                    is_supported=False,
                    explanation="Access restricted. User login and security audit records require Administrator role.",
                    clarification_message="Security audit records and system lockout tables are restricted to System Administrators."
                )

            # If user asks for audit events, logs, or specifies a time filter (e.g. "till 9:30", "today")
            has_explicit_audit_log = bool(re.search(r'\b(logs?|events?|audit|history|actions?)\b', p_lower))
            has_explicit_user_account = any(w in p_lower for w in ["which accounts", "which users", "who has", "user accounts", "users who", "accounts with", "accounts currently"])

            if time_filter or (has_explicit_audit_log and not has_explicit_user_account):
                return Intent(
                    raw_prompt=p,
                    role=r,
                    domain="ADMIN_AUDIT",
                    target_view="v_admin_audit_logs",
                    operation=op,
                    time_filter=time_filter,
                    failed_login_only=True,
                    scope=scope,
                    limit=limit_val,
                    order_by_col=order_col or "created_at",
                    order_direction="DESC",
                    explanation=f"Retrieves security audit logs of failed login attempts{' before ' + time_filter if time_filter else ''}.",
                    tables_used=["v_admin_audit_logs"]
                )
            else:
                return Intent(
                    raw_prompt=p,
                    role=r,
                    domain="ADMIN_USERS",
                    target_view="v_admin_user_audit",
                    operation=op,
                    failed_login_only=True,
                    scope=scope,
                    limit=limit_val,
                    order_by_col=order_col or "failed_login_attempts",
                    order_direction="DESC",
                    explanation="Lists user accounts with recorded failed login attempts or active security lockouts.",
                    tables_used=["v_admin_user_audit"]
                )

        # -------------------------------------------------------------
        # User Accounts Roster Domain (Admin)
        is_user_roster_query = any(w in p_lower for w in [
            "user accounts", "registered users", "list users", "all accounts", "users by role", "user roster"
        ])
        if is_user_roster_query:
            if r != "ADMIN":
                return Intent(
                    raw_prompt=p, role=r, domain="ADMIN_USERS", target_view="", operation=op, is_supported=False,
                    explanation="User directory access requires Administrator privileges.",
                    clarification_message="System-wide user accounts are only visible to System Administrators."
                )
            return Intent(
                raw_prompt=p, role=r, domain="ADMIN_USERS", target_view="v_admin_user_audit",
                operation=op, scope=scope, limit=limit_val,
                order_by_col=order_col or "role", order_direction="ASC",
                explanation="Lists registered platform user accounts across system roles.",
                tables_used=["v_admin_user_audit"]
            )

        # -------------------------------------------------------------
        # Platform Turnover / Volume Domain (Admin)
        is_platform_trade_query = any(w in p_lower for w in [
            "platform volume", "total platform trades", "platform turnover", "collected fees",
            "total brokerage collected", "all trades across", "system volume"
        ])
        if is_platform_trade_query:
            if r != "ADMIN":
                return Intent(
                    raw_prompt=p, role=r, domain="ADMIN_PLATFORM_TRADES", target_view="", operation=op, is_supported=False,
                    explanation="Platform-wide trade facts are restricted to Administrator.",
                    clarification_message="System-wide trading turnover is only accessible to Administrators."
                )
            return Intent(
                raw_prompt=p, role=r, domain="ADMIN_PLATFORM_TRADES", target_view="v_admin_trade_facts",
                operation=op, scope=scope, limit=limit_val,
                explanation="Aggregates platform-wide trade count, principal turnover, and collected brokerage fees.",
                tables_used=["v_admin_trade_facts"]
            )

        # -------------------------------------------------------------
        # Commission Rules & Brokerage Policy (Admin)
        if any(w in p_lower for w in ["commission rules", "brokerage policy", "commission rates", "brokerage rate"]):
            if r != "ADMIN":
                return Intent(
                    raw_prompt=p, role=r, domain="ADMIN_COMMISSION_RULES", target_view="", operation=op, is_supported=False,
                    explanation="Commission policy administration requires Administrator role.",
                    clarification_message="Configured brokerage and commission policy rules are managed by Administrators."
                )
            return Intent(
                raw_prompt=p, role=r, domain="ADMIN_COMMISSION_RULES", target_view="Commission_Rules",
                operation=op, scope=scope, limit=limit_val,
                order_by_col="is_active", order_direction="DESC",
                explanation="Lists active and historical commission rules and fee structures.",
                tables_used=["Commission_Rules"]
            )

        # -------------------------------------------------------------
        # Investor-Specific Domain (Holdings & Transactions)
        has_trans_kw = any(w in p_lower for w in ["transaction", "transactions", "trade", "trades", "order", "orders", "brokerage", "fee", "fees", "executed"])
        has_holding_kw = any(w in p_lower for w in ["holding", "holdings", "portfolio", "own", "shares i have", "shares i own", "position", "positions", "unrealized", "pnl", "profit", "return"])

        is_my_transactions = False
        is_my_holdings = False

        if r == "INVESTOR":
            if has_trans_kw and not has_holding_kw:
                is_my_transactions = True
            elif has_holding_kw and not has_trans_kw:
                is_my_holdings = True
            elif "transaction" in p_lower or "trade" in p_lower or "brokerage" in p_lower:
                is_my_transactions = True
            elif "portfolio" in p_lower or "holding" in p_lower or "pnl" in p_lower:
                is_my_holdings = True

        if is_my_holdings:
            return Intent(
                raw_prompt=p, role=r, domain="INVESTOR_PORTFOLIO", target_view="v_investor_portfolio",
                operation=op, sector=resolved_sector, symbol=resolved_symbol,
                scope=scope, limit=limit_val,
                order_by_col=order_col or "market_value", order_direction="DESC",
                explanation="Lists your open portfolio holdings with live market values and returns.",
                tables_used=["v_investor_portfolio"]
            )

        if is_my_transactions:
            return Intent(
                raw_prompt=p, role=r, domain="INVESTOR_TRANSACTIONS", target_view="v_investor_transactions",
                operation=op, sector=resolved_sector, symbol=resolved_symbol,
                scope=scope, limit=limit_val,
                order_by_col=order_col or "executed_at", order_direction="DESC",
                explanation="Lists your executed trade transactions with execution prices and brokerage fees.",
                tables_used=["v_investor_transactions"]
            )

        # -------------------------------------------------------------
        # Broker-Specific Domain (Clients & Commissions)
        has_client_kw = any(w in p_lower for w in ["client", "clients", "investor", "investors"])
        has_comm_kw = any(w in p_lower for w in ["commission", "commissions", "earned", "payout", "payouts"])
        has_client_trades_kw = any(w in p_lower for w in ["client transaction", "client transactions", "trades by my clients", "client trades"])

        is_broker_clients = False
        is_broker_commissions = False
        is_broker_transactions = False

        if r == "BROKER":
            if has_comm_kw:
                is_broker_commissions = True
            elif has_client_trades_kw:
                is_broker_transactions = True
            elif has_client_kw:
                is_broker_clients = True

        if is_broker_clients:
            return Intent(
                raw_prompt=p, role=r, domain="BROKER_CLIENTS", target_view="v_broker_client_summary",
                operation=op, scope=scope, limit=limit_val,
                order_by_col=order_col or "total_commission_generated", order_direction="DESC",
                explanation="Lists active investor clients assigned to your brokerage with balances and turnover.",
                tables_used=["v_broker_client_summary"]
            )

        if is_broker_commissions:
            return Intent(
                raw_prompt=p, role=r, domain="BROKER_COMMISSIONS", target_view="v_broker_commissions",
                operation=op, scope=scope, limit=limit_val,
                order_by_col=order_col or "created_at", order_direction="DESC",
                explanation="Breakdown of platform commission payouts earned from client trade transactions.",
                tables_used=["v_broker_commissions"]
            )

        if is_broker_transactions:
            return Intent(
                raw_prompt=p, role=r, domain="BROKER_TRANSACTIONS", target_view="v_broker_client_transactions",
                operation=op, scope=scope, limit=limit_val,
                order_by_col=order_col or "executed_at", order_direction="DESC",
                explanation="Executed trade transactions across your assigned investor clients.",
                tables_used=["v_broker_client_transactions"]
            )

        # -------------------------------------------------------------
        # Public Market Equities Domain (Available to all roles)
        # Handles sector listings, stock quotes, gainers, losers, market volume
        return Intent(
            raw_prompt=p,
            role=r,
            domain="MARKET_EQUITIES",
            target_view="v_market_latest",
            operation=op,
            sector=resolved_sector,
            symbol=resolved_symbol,
            company_name_query=resolved_company,
            scope=scope,
            limit=limit_val,
            order_by_col=order_col or ("company_name" if resolved_sector else "volume"),
            order_direction=order_dir if order_col else ("ASC" if resolved_sector else "DESC"),
            explanation=f"Queries real-time market quotes and volume{f' for the {resolved_sector} sector' if resolved_sector else (f' for {resolved_symbol}' if resolved_symbol else '')}.",
            tables_used=["v_market_latest"]
        )

    def generate_sql(self, intent: Intent, role: str) -> Dict[str, Any]:
        """
        Generates schema-precise, parameterized SQL directly from the structured Intent.
        Preserves user constraints, sector filters, scope, ordering, and tenancy.
        """
        if not intent.is_supported:
            return {
                "sql": "SELECT 'Unsupported request' AS status, 'Request cannot be mapped to the available database schema.' AS explanation LIMIT 0;",
                "tables": [],
                "explanation": intent.explanation or "Request is outside the supported database domain."
            }

        view = intent.target_view
        where_clauses = []
        order_clause = ""
        limit_clause = f"LIMIT {intent.limit or 500}"

        # 1. Market Equities Domain
        if intent.domain == "MARKET_EQUITIES":
            cols = "symbol, company_name, sector, current_price, previous_close, day_change_pct, volume"
            if intent.operation == "COUNT" and not intent.sector:
                # Group by sector count
                sql = "SELECT sector, COUNT(*) AS stock_count, ROUND(AVG(current_price), 2) AS avg_price FROM v_market_latest GROUP BY sector ORDER BY stock_count DESC LIMIT 500;"
                return {
                    "sql": sql,
                    "tables": ["v_market_latest"],
                    "explanation": "Calculates the number of listed companies and average share price per sector."
                }

            if intent.sector:
                # Support delivery keyword matching Logistics sector as well
                if intent.sector == "Logistics" and "delivery" in intent.raw_prompt.lower():
                    where_clauses.append("(sector = 'Logistics' OR company_name LIKE '%Delivery%' OR symbol = 'DELHIVERY')")
                else:
                    where_clauses.append(f"sector = '{intent.sector}'")
            elif intent.symbol:
                where_clauses.append(f"symbol = '{intent.symbol}'")
            elif intent.company_name_query:
                where_clauses.append(f"company_name LIKE '%{intent.company_name_query.split()[0]}%'")

            if intent.order_by_col:
                order_clause = f"ORDER BY {intent.order_by_col} {intent.order_direction}"
            elif intent.sector:
                order_clause = "ORDER BY company_name ASC"
            else:
                order_clause = "ORDER BY volume DESC"

            where_str = f"WHERE {' AND '.join(where_clauses)} " if where_clauses else ""
            sql = f"SELECT {cols} FROM v_market_latest {where_str}{order_clause} {limit_clause};"
            expl = intent.explanation or (f"Lists companies in {intent.sector} sector with live market data." if intent.sector else "Queries live market quotes and volumes.")
            return {"sql": sql, "tables": ["v_market_latest"], "explanation": expl}

        # 2. Security Audit Domain (v_admin_audit_logs)
        elif intent.domain == "ADMIN_AUDIT":
            cols = "log_id, username, role, action, ip_address, created_at"
            if intent.failed_login_only:
                where_clauses.append("action IN ('LOGIN_FAILED', 'LOGIN_LOCKED', 'SECURITY_LOCKOUT')")

            if intent.time_filter:
                if intent.time_filter == "today":
                    where_clauses.append("DATE(created_at) = CURRENT_DATE")
                elif intent.time_filter == "this_month":
                    where_clauses.append("YEAR(created_at) = YEAR(CURRENT_DATE) AND MONTH(created_at) = MONTH(CURRENT_DATE)")
                else:
                    # Precise time bound (e.g. 09:30:00)
                    where_clauses.append(f"TIME(created_at) <= '{intent.time_filter}'")

            where_str = f"WHERE {' AND '.join(where_clauses)} " if where_clauses else ""
            sql = f"SELECT {cols} FROM v_admin_audit_logs {where_str}ORDER BY created_at DESC {limit_clause};"
            expl = intent.explanation or "Retrieves security audit logs of failed login attempts."
            return {"sql": sql, "tables": ["v_admin_audit_logs"], "explanation": expl}

        # 3. User Accounts Domain (v_admin_user_audit)
        elif intent.domain == "ADMIN_USERS":
            cols = "user_id, username, email, full_name, role, status, failed_login_attempts, locked_until, last_login_at"
            if intent.failed_login_only:
                where_clauses.append("(failed_login_attempts > 0 OR locked_until IS NOT NULL)")

            order_col = intent.order_by_col or ("failed_login_attempts" if intent.failed_login_only else "role, username")
            where_str = f"WHERE {' AND '.join(where_clauses)} " if where_clauses else ""
            sql = f"SELECT {cols} FROM v_admin_user_audit {where_str}ORDER BY {order_col} {intent.order_direction} {limit_clause};"
            expl = intent.explanation or "Lists registered user accounts and their authentication status."
            return {"sql": sql, "tables": ["v_admin_user_audit"], "explanation": expl}

        # 4. Investor Portfolio Domain
        elif intent.domain == "INVESTOR_PORTFOLIO":
            where_clauses.append("user_id = @current_user_id")
            if intent.sector:
                where_clauses.append(f"sector = '{intent.sector}'")
            if intent.symbol:
                where_clauses.append(f"symbol = '{intent.symbol}'")

            if intent.operation == "SUM" or any(w in intent.raw_prompt.lower() for w in ["total profit", "total unrealized", "total pnl"]):
                sql = "SELECT COALESCE(SUM(unrealized_pnl), 0.00) AS total_unrealized_pnl, COALESCE(SUM(market_value), 0.00) AS total_market_value FROM v_investor_portfolio WHERE user_id = @current_user_id LIMIT 500;"
                return {"sql": sql, "tables": ["v_investor_portfolio"], "explanation": "Calculates total open unrealized profit/loss across all current holdings."}

            cols = "symbol, company_name, sector, quantity, avg_cost, cost_basis, current_price, market_value, unrealized_pnl, return_pct"
            order_col = intent.order_by_col or "market_value"
            sql = f"SELECT {cols} FROM v_investor_portfolio WHERE {' AND '.join(where_clauses)} ORDER BY {order_col} {intent.order_direction} {limit_clause};"
            expl = intent.explanation or "Lists your current active portfolio positions ordered by value."
            return {"sql": sql, "tables": ["v_investor_portfolio"], "explanation": expl}

        # 5. Investor Transactions Domain
        elif intent.domain == "INVESTOR_TRANSACTIONS":
            where_clauses.append("user_id = @current_user_id")
            if intent.sector:
                where_clauses.append(f"sector = '{intent.sector}'")
            if intent.symbol:
                where_clauses.append(f"symbol = '{intent.symbol}'")

            if intent.operation == "SUM" or "brokerage" in intent.raw_prompt.lower() or "fee" in intent.raw_prompt.lower():
                sql = "SELECT COUNT(*) AS total_trades, COALESCE(SUM(brokerage_fee), 0.00) AS total_brokerage_paid, COALESCE(SUM(gross_amount), 0.00) AS total_traded_volume FROM v_investor_transactions WHERE user_id = @current_user_id LIMIT 500;"
                return {"sql": sql, "tables": ["v_investor_transactions"], "explanation": "Calculates cumulative brokerage fees paid across executed trades."}

            cols = "transaction_id, symbol, company_name, sector, side, quantity, execution_price, gross_amount, brokerage_fee, net_amount, executed_at"
            order_col = intent.order_by_col or "executed_at"
            sql = f"SELECT {cols} FROM v_investor_transactions WHERE {' AND '.join(where_clauses)} ORDER BY {order_col} {intent.order_direction} {limit_clause};"
            expl = intent.explanation or "Lists your executed trade transactions chronologically."
            return {"sql": sql, "tables": ["v_investor_transactions"], "explanation": expl}

        # 6. Broker Clients Domain
        elif intent.domain == "BROKER_CLIENTS":
            cols = "investor_id, investor_name, investor_email, investor_status, virtual_balance, total_trades, total_volume, total_commission_generated"
            order_col = intent.order_by_col or "total_commission_generated"
            sql = f"SELECT {cols} FROM v_broker_client_summary WHERE broker_id = @current_user_id ORDER BY {order_col} {intent.order_direction} {limit_clause};"
            expl = intent.explanation or "Lists active investor clients assigned to your brokerage."
            return {"sql": sql, "tables": ["v_broker_client_summary"], "explanation": expl}

        # 7. Broker Commissions Domain
        elif intent.domain == "BROKER_COMMISSIONS":
            if intent.operation == "SUM" or "total" in intent.raw_prompt.lower():
                sql = "SELECT COUNT(*) AS total_commission_events, COALESCE(SUM(commission_amount), 0.00) AS total_commission_earned FROM v_broker_commissions WHERE broker_id = @current_user_id LIMIT 500;"
                return {"sql": sql, "tables": ["v_broker_commissions"], "explanation": "Calculates cumulative broker commission earned from client trades."}

            cols = "commission_id, transaction_id, investor_name, symbol, side, quantity, base_brokerage, rate_applied, commission_amount, created_at"
            order_col = intent.order_by_col or "created_at"
            sql = f"SELECT {cols} FROM v_broker_commissions WHERE broker_id = @current_user_id ORDER BY {order_col} {intent.order_direction} {limit_clause};"
            expl = intent.explanation or "Lists individual commission records generated by client trades."
            return {"sql": sql, "tables": ["v_broker_commissions"], "explanation": expl}

        # 7b. Broker Client Transactions Domain
        elif intent.domain == "BROKER_TRANSACTIONS":
            cols = "transaction_id, investor_id, investor_name, symbol, side, quantity, execution_price, gross_amount, brokerage_fee, broker_commission_earned, executed_at"
            order_col = intent.order_by_col or "executed_at"
            sql = f"SELECT {cols} FROM v_broker_client_transactions WHERE broker_id = @current_user_id ORDER BY {order_col} {intent.order_direction} {limit_clause};"
            expl = intent.explanation or "Lists executed trade transactions across your assigned clients."
            return {"sql": sql, "tables": ["v_broker_client_transactions"], "explanation": expl}

        # 8. Platform Trade Facts (Admin)
        elif intent.domain == "ADMIN_PLATFORM_TRADES":
            if intent.operation in ("SUM", "COUNT") or "total" in intent.raw_prompt.lower():
                sql = "SELECT COUNT(*) AS total_trades, COALESCE(SUM(gross_amount), 0.00) AS total_platform_volume, COALESCE(SUM(brokerage_fee), 0.00) AS total_brokerage_collected FROM v_admin_trade_facts LIMIT 500;"
                return {"sql": sql, "tables": ["v_admin_trade_facts"], "explanation": "Calculates platform-wide trade count, principal turnover, and collected brokerage fees."}

            cols = "transaction_id, executed_at, side, quantity, execution_price, gross_amount, brokerage_fee, investor_name, symbol, sector"
            sql = f"SELECT {cols} FROM v_admin_trade_facts ORDER BY executed_at DESC {limit_clause};"
            expl = intent.explanation or "Lists executed trades across the entire trading platform."
            return {"sql": sql, "tables": ["v_admin_trade_facts"], "explanation": expl}

        # 9. Commission Rules (Admin)
        elif intent.domain == "ADMIN_COMMISSION_RULES":
            sql = "SELECT id, rule_type, rate, min_fee, effective_from, is_active FROM Commission_Rules ORDER BY is_active DESC, effective_from DESC LIMIT 50;"
            return {"sql": sql, "tables": ["Commission_Rules"], "explanation": "Lists active and historical commission rules and fee structures."}

        # Default Fallback (Safe query on v_market_latest)
        sql = f"SELECT symbol, company_name, sector, current_price, volume FROM v_market_latest ORDER BY volume DESC {limit_clause};"
        return {"sql": sql, "tables": ["v_market_latest"], "explanation": "Queries market overview equities."}
