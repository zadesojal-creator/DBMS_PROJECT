"""
Database Migrations Runner (database/migrations_v2.py)
Applies schema enhancements, Order_Events table, check constraints,
immutability triggers, and covering indexes to stocktrade and stocktrade_test.
"""
import sys
from pathlib import Path
import pymysql

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from database.init_db import get_root_connection, execute_sql_file, DB_NAME, TEST_DB_NAME

def run_migrations_on_db(db_name: str):
    print(f"\n==========================================")
    print(f"[*] Running DBMS Migrations on '{db_name}'...")
    print(f"==========================================")
    conn = get_root_connection(db_name)

    with conn.cursor() as cur:
        # 1. Create Order_Events table if not exists
        print("[*] Creating Order_Events table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Order_Events (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                order_id BIGINT NOT NULL,
                from_status ENUM('NEW', 'PENDING', 'EXECUTED', 'REJECTED', 'FAILED', 'CANCELLED') NULL,
                to_status ENUM('PENDING', 'EXECUTED', 'REJECTED', 'FAILED', 'CANCELLED') NOT NULL,
                reason VARCHAR(255) NULL,
                event_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_oe_order FOREIGN KEY (order_id) REFERENCES Orders(id) ON DELETE RESTRICT,
                INDEX idx_oe_order_time (order_id, event_timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        # 2. Add domain check constraints safely (ignore if exists)
        constraints = [
            ("Transactions", "chk_trans_qty", "CHECK (quantity > 0)"),
            ("Transactions", "chk_trans_price", "CHECK (execution_price > 0.0000)"),
            ("Transactions", "chk_trans_gross", "CHECK (gross_amount >= 0.00)"),
            ("Transactions", "chk_trans_brokerage", "CHECK (brokerage_fee >= 0.00)"),
            ("Commission_Rules", "chk_comm_rule_rate", "CHECK (rate >= 0.00000 AND rate <= 1.00000)"),
            ("Commission_Rules", "chk_comm_rule_min_fee", "CHECK (min_fee >= 0.00)"),
            ("Commissions", "chk_comm_amount", "CHECK (commission_amount >= 0.00)"),
            ("Commissions", "chk_comm_base", "CHECK (base_brokerage >= 0.00)"),
            ("Price_Alerts", "chk_alert_target_price", "CHECK (target_price > 0.0000)")
        ]

        for tbl, c_name, c_def in constraints:
            try:
                cur.execute(f"ALTER TABLE {tbl} ADD CONSTRAINT {c_name} {c_def};")
                print(f"  [+] Added constraint {c_name} on {tbl}")
            except pymysql.err.OperationalError as ex:
                if ex.args[0] in (3822, 1061):  # Duplicate constraint name or key
                    print(f"  [i] Constraint {c_name} already present on {tbl}")
                else:
                    print(f"  [!] Warning on {c_name}: {ex}")

    # 3. Apply triggers and procedures
    execute_sql_file(conn, BASE_DIR / "database" / "triggers.sql")
    execute_sql_file(conn, BASE_DIR / "database" / "procedures.sql")
    execute_sql_file(conn, BASE_DIR / "database" / "indexes.sql")

    conn.close()
    print(f"[✓] Migrations on '{db_name}' completed successfully.")

if __name__ == "__main__":
    run_migrations_on_db(DB_NAME)
    run_migrations_on_db(TEST_DB_NAME)
