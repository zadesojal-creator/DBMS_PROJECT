"""
SQL AST Validator (services/sql_validator.py)
Uses sqlglot (MySQL dialect) to enforce strict AST allowlists, query complexity boundaries,
and mandatory tenant isolation scoping.
"""
from typing import Tuple, List, Set, Optional
import sqlglot
from sqlglot import exp

ROLE_ALLOWED_TABLES = {
    "INVESTOR": {"v_investor_portfolio", "v_investor_transactions", "v_market_latest"},
    "BROKER": {"v_broker_client_transactions", "v_broker_commissions", "v_broker_client_summary", "v_market_latest"},
    "ADMIN": {"v_admin_trade_facts", "v_admin_user_audit", "v_admin_audit_logs", "v_market_latest", "stocks", "commission_rules"}
}

ROLE_TENANT_MAP = {
    "v_investor_portfolio": "user_id",
    "v_investor_transactions": "user_id",
    "v_broker_client_transactions": "broker_id",
    "v_broker_commissions": "broker_id",
    "v_broker_client_summary": "broker_id"
}

ALL_PROTECTED_TABLES = {t.lower() for tables in ROLE_ALLOWED_TABLES.values() for t in tables} | {t.lower() for t in ROLE_TENANT_MAP.keys()}

ALLOWED_FUNCTIONS = {
    "count", "sum", "avg", "min", "max", "round", "coalesce", "nullif",
    "date", "time", "hour", "minute", "year", "month", "day", "date_format", "concat", "lower", "upper",
    "if", "case", "now", "current_date", "current_timestamp", "from_unixtime",
    "unix_timestamp", "substring_index", "group_concat", "rank", "dense_rank", "row_number"
}

FORBIDDEN_KEYWORDS = {
    "sleep", "benchmark", "load_file", "into", "outfile", "dumpfile",
    "information_schema", "mysql", "performance_schema", "sys"
}

class SQLValidator:
    @staticmethod
    def validate_sql(raw_sql: str, role: str) -> Tuple[bool, Optional[str], Optional[str], List[str]]:
        """
        Validates SQL query against AST allowlist and enforces tenant isolation.
        Returns (is_valid, sanitized_sql, error_message, tables_used).
        """
        if not raw_sql or not raw_sql.strip():
            return False, None, "Empty SQL query provided", []

        sql_clean = raw_sql.strip().rstrip(";")

        # Quick check for dangerous keywords/comments hiding tokens
        lower_sql = sql_clean.lower()
        for forbidden in FORBIDDEN_KEYWORDS:
            if forbidden in lower_sql:
                return False, None, f"Forbidden keyword detected: {forbidden}", []

        # Parse AST with sqlglot (MySQL dialect)
        try:
            expressions = sqlglot.parse(sql_clean, read="mysql")
        except Exception as e:
            return False, None, f"SQL Syntax Error: {str(e)}", []

        if len(expressions) != 1:
            return False, None, "Multi-statement queries or stacked queries are prohibited", []

        ast = expressions[0]
        if ast is None:
            return False, None, "Unable to parse SQL statement", []

        # Enforce Root is SELECT or UNION
        if not isinstance(ast, (exp.Select, exp.Union)):
            return False, None, f"Only SELECT read queries are permitted. Got statement type: {type(ast).__name__}", []

        # Check for mutation expressions anywhere in AST
        for node in ast.walk():
            if isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Alter, exp.Create)):
                return False, None, "Database mutation operations are strictly prohibited", []
            
            # Check functions
            if isinstance(node, (exp.Anonymous, exp.Func)):
                if isinstance(node, (exp.Binary, exp.Connector, exp.Predicate, exp.Unary)):
                    continue
                if isinstance(node, exp.Anonymous):
                    func_name = node.name.lower()
                else:
                    func_name = node.sql_name().lower() if hasattr(node, "sql_name") else str(type(node).__name__).lower()
                if func_name and func_name not in ALLOWED_FUNCTIONS:
                    return False, None, f"Function '{func_name}' is not in the approved safety allowlist", []

        # Check and validate CTEs
        cte_names = set()
        with_node = ast.find(exp.With)
        if with_node:
            ctes = with_node.expressions
            if len(ctes) > 2:
                return False, None, "Too many CTEs; maximum 2 CTEs permitted", []
            for cte in ctes:
                cname = cte.alias.lower()
                cte_names.add(cname)
                if cname in ALL_PROTECTED_TABLES:
                    return False, None, f"CTE alias '{cname}' collides with protected view name", []

        # Check joins for Cartesian products and complexity
        joins = list(ast.find_all(exp.Join))
        if len(joins) > 2:
            return False, None, "Excessive joins; maximum 2 joins permitted", []
        for j in joins:
            if j.kind and j.kind.upper() == "CROSS":
                return False, None, "Unconstrained CROSS JOIN is prohibited", []
            if not j.args.get("on") and not j.args.get("using"):
                return False, None, "Join without ON or USING condition is prohibited", []

        # Check offset
        offset_node = ast.find(exp.Offset)
        if offset_node:
            try:
                offset_val = int(offset_node.expression.this)
                if offset_val > 1000:
                    return False, None, f"Excessive query OFFSET ({offset_val}); maximum allowed is 1000", []
            except Exception:
                return False, None, "Invalid query OFFSET specification", []

        # Extract and validate referenced tables/views
        tables_used = []
        allowed_tables = ROLE_ALLOWED_TABLES.get(role.upper(), set())
        table_nodes = list(ast.find_all(exp.Table))

        for table_node in table_nodes:
            t_name = table_node.name.lower()
            if t_name in cte_names:
                continue
            tables_used.append(t_name)
            if t_name not in allowed_tables:
                return False, None, f"Unauthorized table or view '{t_name}' for role '{role}'", []

        if not tables_used:
            return False, None, "Query must select from at least one authorized view", []

        # Enforce Tenant Isolation via Scoped Derived Tables
        # For INVESTOR and BROKER, wrap every private tenant view reference into a scoped subquery
        if role.upper() in ("INVESTOR", "BROKER"):
            for table_node in table_nodes:
                t_name = table_node.name.lower()
                if t_name in cte_names:
                    continue
                if t_name in ROLE_TENANT_MAP:
                    tenant_col = ROLE_TENANT_MAP[t_name]
                    alias = table_node.alias or t_name
                    scoped_subquery_sql = f"(SELECT * FROM {t_name} WHERE {tenant_col} = :auth_user_id) AS {alias}"
                    scoped_subquery = sqlglot.parse_one(scoped_subquery_sql, read="mysql")
                    table_node.replace(scoped_subquery)

        # Inject or clamp LIMIT (default max 500)
        limit_node = ast.find(exp.Limit)
        if limit_node:
            try:
                curr_limit = int(limit_node.expression.this)
                if curr_limit > 500:
                    limit_node.set("expression", exp.Literal.number(500))
            except Exception:
                limit_node.set("expression", exp.Literal.number(500))
        else:
            ast = ast.limit(500)

        sanitized_sql = ast.sql(dialect="mysql") + ";"

        # Re-validate final transformed AST to guarantee integrity
        try:
            recheck = sqlglot.parse(sanitized_sql.rstrip(";"), read="mysql")
            if len(recheck) != 1 or not isinstance(recheck[0], (exp.Select, exp.Union)):
                return False, None, "Transformed query failed final AST safety re-validation", []
        except Exception as ex:
            return False, None, f"Transformed query syntax error: {str(ex)}", []

        return True, sanitized_sql, None, tables_used
