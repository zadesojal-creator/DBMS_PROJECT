"""
StockTrade Database Initializer & Migration Tool (init_db.py)
Idempotent setup for MySQL 8.0:
- Creates stocktrade & stocktrade_test databases
- Provisions least-privilege app & AI users
- Executes schema, indexes, views, triggers, stored procedures
- Seeds 100 companies, commission rules, system settings, and demo users
- Backfills 7-day historical price observations
"""
import os
import re
import sys
from pathlib import Path
import pymysql
from dotenv import load_dotenv

# Load environment configuration
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "database"))
load_dotenv(BASE_DIR / ".env")

# Ensure UTF-8 output on Windows terminal
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_ROOT_USER = os.getenv("DB_ROOT_USER", "root")
DB_ROOT_PASSWORD = os.getenv("DB_ROOT_PASSWORD", "root")
DB_NAME = os.getenv("DB_NAME", "stocktrade")
TEST_DB_NAME = os.getenv("TEST_DB_NAME", "stocktrade_test")

APP_USER = os.getenv("DB_USER", "stocktrade_app")
APP_PASSWORD = os.getenv("DB_PASSWORD", "StockTradeApp@2026!")
AI_USER = os.getenv("DB_AI_USER", "stocktrade_ai_ro")
AI_PASSWORD = os.getenv("DB_AI_PASSWORD", "StockTradeAiRo@2026!")

def get_root_connection(db=None):
    """Establish connection with root administrative privileges."""
    connect_kwargs = {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_ROOT_USER,
        "password": DB_ROOT_PASSWORD,
        "database": db,
        "charset": "utf8mb4",
        "autocommit": True,
        "cursorclass": pymysql.cursors.Cursor
    }
    if os.getenv("DB_SSL", "false").lower() in ("true", "1", "yes"):
        ssl_ca = os.getenv("DB_SSL_CA")
        connect_kwargs["ssl"] = {"ca": ssl_ca} if ssl_ca else {}
    return pymysql.connect(**connect_kwargs)

def execute_sql_file(conn, file_path: Path):
    """
    Executes a SQL file, handling DELIMITER blocks (for procedures & triggers)
    and standard semicolon-terminated statements.
    """
    print(f"[*] Executing {file_path.name}...")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split into blocks if DELIMITER is present
    delimiter_pattern = re.compile(r'DELIMITER\s+([^\w\s]+)', re.IGNORECASE)
    parts = delimiter_pattern.split(content)
    
    with conn.cursor() as cur:
        def run_stmt(stmt_str):
            try:
                cur.execute(stmt_str)
            except (pymysql.err.OperationalError, pymysql.err.ProgrammingError) as ex:
                # 1061: Duplicate key name (index already exists)
                # 1050: Table already exists
                if ex.args[0] in (1061, 1050):
                    pass
                else:
                    raise

        if len(parts) == 1:
            statements = content.split(";")
            for stmt in statements:
                stmt_clean = stmt.strip()
                if stmt_clean:
                    run_stmt(stmt_clean)
        else:
            curr_delim = ";"
            for idx, part in enumerate(parts):
                if idx % 2 == 1:
                    curr_delim = part.strip()
                else:
                    if not part.strip():
                        continue
                    statements = part.split(curr_delim)
                    for stmt in statements:
                        stmt_clean = stmt.strip()
                        stmt_clean = re.sub(r'DELIMITER\s+;?', '', stmt_clean, flags=re.IGNORECASE).strip()
                        if stmt_clean:
                            run_stmt(stmt_clean)

def setup_databases_and_users():
    """Create databases and users with baseline privileges."""
    print("[1/5] Provisioning databases and security accounts...")
    root_conn = get_root_connection()
    try:
        with root_conn.cursor() as cur:
            # 1. Create Databases
            try:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{TEST_DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            except Exception as db_err:
                print(f"    [!] Note on database creation: {db_err}")

            # 2. Provision App User & AI User
            try:
                cur.execute(f"CREATE USER IF NOT EXISTS '{APP_USER}'@'%' IDENTIFIED BY '{APP_PASSWORD}';")
                cur.execute(f"ALTER USER '{APP_USER}'@'%' IDENTIFIED BY '{APP_PASSWORD}';")
                cur.execute(f"CREATE USER IF NOT EXISTS '{APP_USER}'@'localhost' IDENTIFIED BY '{APP_PASSWORD}';")
                cur.execute(f"ALTER USER '{APP_USER}'@'localhost' IDENTIFIED BY '{APP_PASSWORD}';")
                
                # App user privileges: DML + Views + Execute procedures on both DBs
                for host in ['%', 'localhost']:
                    cur.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE, SHOW VIEW ON `{DB_NAME}`.* TO '{APP_USER}'@'{host}';")
                    cur.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE, SHOW VIEW ON `{TEST_DB_NAME}`.* TO '{APP_USER}'@'{host}';")

                # Provision AI User
                cur.execute(f"CREATE USER IF NOT EXISTS '{AI_USER}'@'%' IDENTIFIED BY '{AI_PASSWORD}';")
                cur.execute(f"ALTER USER '{AI_USER}'@'%' IDENTIFIED BY '{AI_PASSWORD}';")
                cur.execute(f"CREATE USER IF NOT EXISTS '{AI_USER}'@'localhost' IDENTIFIED BY '{AI_PASSWORD}';")
                cur.execute(f"ALTER USER '{AI_USER}'@'localhost' IDENTIFIED BY '{AI_PASSWORD}';")

                cur.execute("FLUSH PRIVILEGES;")
            except Exception as u_err:
                print(f"    [!] Note on user provisioning (managed/cloud user): {u_err}")
        print("    Databases and user accounts checked.")
    finally:
        root_conn.close()

def grant_ai_view_privileges(target_db: str):
    """Grant restricted view-only permissions to AI read-only user."""
    print(f"[*] Applying restricted view permissions to '{AI_USER}' on '{target_db}'...")
    root_conn = get_root_connection(db=target_db)
    try:
        with root_conn.cursor() as cur:
            for host in ['%', 'localhost']:
                cur.execute(f"GRANT SELECT ON `{target_db}`.v_market_latest TO '{AI_USER}'@'{host}';")
                cur.execute(f"GRANT SELECT ON `{target_db}`.v_investor_portfolio TO '{AI_USER}'@'{host}';")
                cur.execute(f"GRANT SELECT ON `{target_db}`.v_investor_transactions TO '{AI_USER}'@'{host}';")
                cur.execute(f"GRANT SELECT ON `{target_db}`.v_broker_client_transactions TO '{AI_USER}'@'{host}';")
                cur.execute(f"GRANT SELECT ON `{target_db}`.v_broker_commissions TO '{AI_USER}'@'{host}';")
                cur.execute(f"GRANT SELECT ON `{target_db}`.v_broker_client_summary TO '{AI_USER}'@'{host}';")
                cur.execute(f"GRANT SELECT ON `{target_db}`.v_admin_trade_facts TO '{AI_USER}'@'{host}';")
                cur.execute(f"GRANT SELECT ON `{target_db}`.v_admin_user_audit TO '{AI_USER}'@'{host}';")
                cur.execute(f"GRANT SELECT ON `{target_db}`.v_admin_audit_logs TO '{AI_USER}'@'{host}';")
                cur.execute(f"GRANT SELECT ON `{target_db}`.Stocks TO '{AI_USER}'@'{host}';")
                cur.execute(f"GRANT SELECT ON `{target_db}`.Commission_Rules TO '{AI_USER}'@'{host}';")
            cur.execute("FLUSH PRIVILEGES;")
    except Exception as g_err:
        print(f"    [!] Note on granting view privileges: {g_err}")
    finally:
        root_conn.close()

def run_migrations(target_db: str):
    """Runs all DDL and seed scripts on the specified database."""
    print(f"[2/5] Running migrations on '{target_db}'...")
    conn = get_root_connection(db=target_db)
    db_dir = BASE_DIR / "database"
    try:
        scripts = [
            db_dir / "schema.sql",
            db_dir / "indexes.sql",
            db_dir / "views.sql",
            db_dir / "triggers.sql",
            db_dir / "procedures.sql",
            db_dir / "seed_settings_rules.sql",
            db_dir / "seed_companies.sql",
            db_dir / "seed_demo_users.sql"
        ]
        for script in scripts:
            if script.exists():
                execute_sql_file(conn, script)
            else:
                print(f"[!] Warning: {script.name} not found.")
    finally:
        conn.close()

def run_price_backfill(target_db: str):
    """Backfills 7-day price data."""
    print(f"[3/5] Checking historical price backfill for '{target_db}'...")
    conn = get_root_connection(db=target_db)
    try:
        from database.backfill_prices import generate_seven_day_history
        generate_seven_day_history(conn, days=7)
    finally:
        conn.close()

def run_sample_trade():
    """Seeds one initial trade for Rahul Verma (buying 5 shares of TCS) to verify sp_execute_trade."""
    print("[4/5] Checking demo trade sample...")
    conn = get_root_connection(db=DB_NAME)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM Transactions WHERE user_id = 4")
            count = cur.fetchone()[0]
            if count == 0:
                print("    Executing sample trade via sp_execute_trade...")
                cur.execute("SELECT id FROM Stocks WHERE symbol = 'TCS'")
                stock_id = cur.fetchone()[0]
                cur.callproc("sp_execute_trade", (4, stock_id, 'BUY', 5, 'SEED_DEMO_TRADE_RAHUL_001', 0, 0, 0.0, '', ''))
                cur.execute("SELECT @_sp_execute_trade_5, @_sp_execute_trade_6, @_sp_execute_trade_7, @_sp_execute_trade_8, @_sp_execute_trade_9")
                res = cur.fetchone()
                print(f"    Sample trade result: Status={res[3]}, Msg={res[4]}, ExecPrice={res[2]}")
            else:
                print(f"    Sample trades already present ({count} trades).")
    finally:
        conn.close()

def print_demo_credentials():
    """Prints demo credentials formatted for presentation and testing."""
    print("\n" + "=" * 78)
    print(" STOCKTRADE — DEMO LOGIN CREDENTIALS (COLLEGE EVALUATION)")
    print("=" * 78)
    print(f"{'ROLE':<12} | {'USERNAME':<16} | {'EMAIL':<26} | {'PASSWORD':<22}")
    print("-" * 78)
    print(f"{'ADMIN':<12} | {'admin':<16} | {'admin@stocktrade.local':<26} | {'Admin@StockTrade2026':<22}")
    print(f"{'BROKER':<12} | {'broker_arun':<16} | {'arun@stocktrade.local':<26} | {'Broker@StockTrade2026':<22}")
    print(f"{'BROKER':<12} | {'broker_priya':<16} | {'priya@stocktrade.local':<26} | {'Broker@StockTrade2026':<22}")
    print(f"{'INVESTOR':<12} | {'investor_rahul':<16} | {'rahul@gmail.com':<26} | {'Investor@StockTrade2026':<22}")
    print(f"{'INVESTOR':<12} | {'investor_sneha':<16} | {'sneha@gmail.com':<26} | {'Investor@StockTrade2026':<22}")
    print(f"{'INVESTOR':<12} | {'investor_vikram':<16} | {'vikram@gmail.com':<26} | {'Investor@StockTrade2026':<22}")
    print(f"{'INVESTOR':<12} | {'investor_ananya':<16} | {'ananya@gmail.com':<26} | {'Investor@StockTrade2026':<22}")
    print(f"{'INVESTOR':<12} | {'investor_karan':<16} | {'karan@gmail.com':<26} | {'Investor@StockTrade2026':<22}")
    print(f"{'INVESTOR':<12} | {'investor_rohit':<16} | {'rohit@gmail.com':<26} | {'Investor@StockTrade2026':<22}")
    print("=" * 78)
    print("All investor accounts seeded with Rs. 1,00,000 virtual balance grant.")
    print("Data source: SIMULATED (no real capital or live market exchange prices).\n")

def main():
    print("=== Initializing StockTrade Database System ===")
    setup_databases_and_users()
    run_migrations(DB_NAME)
    grant_ai_view_privileges(DB_NAME)
    run_migrations(TEST_DB_NAME)
    grant_ai_view_privileges(TEST_DB_NAME)
    run_price_backfill(DB_NAME)
    run_price_backfill(TEST_DB_NAME)
    run_sample_trade()
    print_demo_credentials()
    print("[5/5] Database initialization completed successfully!")

if __name__ == "__main__":
    main()
