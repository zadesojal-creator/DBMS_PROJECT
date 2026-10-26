"""
Database Backup & Recovery Manager (database/backup_manager.py)
Implements enterprise-grade MySQL backup, restore, validation, and retention policies:
- Full consistent logical snapshot using mysqldump with --routines, --triggers, --events, --single-transaction
- Cross-database recovery into isolated recovery environments (e.g. stocktrade_test)
- Complete post-restore structural and row-count verification (tables, views, procedures, triggers)
- Automated rolling retention policy
"""
import os
import sys
import subprocess
import glob
from datetime import datetime
from typing import Dict, Any, List, Optional

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import text
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

class BackupManager:
    DEFAULT_BACKUP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "backups"))

    @staticmethod
    def find_mysql_bin(tool_name: str = "mysqldump") -> str:
        """Locates the MySQL utility binary (mysqldump / mysql)."""
        exe_name = f"{tool_name}.exe" if sys.platform == "win32" else tool_name
        
        # 1. Check PATH
        import shutil
        found = shutil.which(tool_name) or shutil.which(exe_name)
        if found:
            return found

        # 2. Known Windows paths
        candidate_dirs = [
            r"C:\Program Files\MySQL\MySQL Server 8.0\bin",
            r"C:\Program Files\MySQL\MySQL Server 8.4\bin",
            r"C:\Program Files (x86)\MySQL\MySQL Server 8.0\bin",
        ]
        for cdir in candidate_dirs:
            full_path = os.path.join(cdir, exe_name)
            if os.path.exists(full_path):
                return full_path

        raise FileNotFoundError(f"Could not locate MySQL utility binary: {tool_name}")

    @classmethod
    def create_backup(
        cls, 
        db_name: Optional[str] = None, 
        output_dir: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes consistent, non-blocking logical backup of MySQL database.
        Includes all schema DDL, table data, stored routines, triggers, and views.
        """
        db_name = db_name or os.getenv("DB_NAME", "stocktrade")
        output_dir = output_dir or cls.DEFAULT_BACKUP_DIR
        host = host or os.getenv("DB_HOST", "localhost")
        port = port or os.getenv("DB_PORT", "3306")
        user = user or os.getenv("DB_ROOT_USER", "root")
        password = password or os.getenv("DB_ROOT_PASSWORD", "root")

        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{db_name}_{timestamp}.sql"
        backup_filepath = os.path.join(output_dir, backup_filename)

        mysqldump_bin = cls.find_mysql_bin("mysqldump")

        cmd = [
            mysqldump_bin,
            f"--host={host}",
            f"--port={port}",
            f"--user={user}",
            f"--password={password}",
            "--routines",
            "--triggers",
            "--events",
            "--single-transaction",
            "--quick",
            "--set-gtid-purged=OFF",
            "--default-character-set=utf8mb4",
            db_name
        ]

        start_time = datetime.now()
        with open(backup_filepath, "w", encoding="utf-8") as out_file:
            result = subprocess.run(
                cmd,
                stdout=out_file,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )

        duration = (datetime.now() - start_time).total_seconds()

        if result.returncode != 0:
            if os.path.exists(backup_filepath):
                os.remove(backup_filepath)
            raise RuntimeError(f"mysqldump failed (code {result.returncode}): {result.stderr}")

        file_size_bytes = os.path.getsize(backup_filepath)

        return {
            "success": True,
            "database": db_name,
            "filepath": backup_filepath,
            "filename": backup_filename,
            "size_bytes": file_size_bytes,
            "size_kb": round(file_size_bytes / 1024, 2),
            "duration_seconds": round(duration, 3),
            "timestamp": timestamp
        }

    @classmethod
    def restore_backup(
        cls, 
        backup_filepath: str, 
        target_db: str,
        host: Optional[str] = None,
        port: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Restores a SQL backup dump into a specified target database.
        """
        if not os.path.exists(backup_filepath):
            raise FileNotFoundError(f"Backup file not found: {backup_filepath}")

        host = host or os.getenv("DB_HOST", "localhost")
        port = port or os.getenv("DB_PORT", "3306")
        user = user or os.getenv("DB_ROOT_USER", "root")
        password = password or os.getenv("DB_ROOT_PASSWORD", "root")

        mysql_bin = cls.find_mysql_bin("mysql")

        start_time = datetime.now()
        with open(backup_filepath, "r", encoding="utf-8") as in_file:
            result = subprocess.run(
                [
                    mysql_bin,
                    f"--host={host}",
                    f"--port={port}",
                    f"--user={user}",
                    f"--password={password}",
                    target_db
                ],
                stdin=in_file,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                check=False
            )

        duration = (datetime.now() - start_time).total_seconds()

        if result.returncode != 0:
            raise RuntimeError(f"mysql restore failed (code {result.returncode}): {result.stderr}")

        return {
            "success": True,
            "target_database": target_db,
            "restored_from": backup_filepath,
            "duration_seconds": round(duration, 3)
        }

    @classmethod
    def verify_restoration(
        cls, 
        source_db: str, 
        target_db: str,
        conn = None
    ) -> Dict[str, Any]:
        """
        Rigorously validates that target_db structurally and numerically matches source_db:
        - Table counts and individual table row counts
        - Stored views count and names
        - Stored procedures count and names
        - Triggers count and names
        """
        from config import Config
        from models.db import init_db_engines, get_engine
        
        init_db_engines(Config())
        engine = get_engine()

        def _get_db_meta(db_name: str, connection):
            # Tables and row counts
            tables_q = text("""
                SELECT TABLE_NAME, TABLE_TYPE 
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = :schema
            """)
            table_rows = connection.execute(tables_q, {"schema": db_name}).mappings().all()
            base_tables = [r["TABLE_NAME"] for r in table_rows if r["TABLE_TYPE"] == "BASE TABLE"]
            views = [r["TABLE_NAME"] for r in table_rows if r["TABLE_TYPE"] == "VIEW"]

            # Exact row counts for base tables
            row_counts = {}
            for t in sorted(base_tables):
                cnt = connection.execute(text(f"SELECT COUNT(*) FROM `{db_name}`.`{t}`")).scalar()
                row_counts[t] = cnt

            # Stored Procedures
            procs_q = text("""
                SELECT ROUTINE_NAME 
                FROM information_schema.ROUTINES 
                WHERE ROUTINE_SCHEMA = :schema AND ROUTINE_TYPE = 'PROCEDURE'
            """)
            procs = [r[0] for r in connection.execute(procs_q, {"schema": db_name}).fetchall()]

            # Triggers
            trgs_q = text("""
                SELECT TRIGGER_NAME 
                FROM information_schema.TRIGGERS 
                WHERE TRIGGER_SCHEMA = :schema
            """)
            triggers = [r[0] for r in connection.execute(trgs_q, {"schema": db_name}).fetchall()]

            # Table Constraints (CHECK, FOREIGN KEY, UNIQUE, PRIMARY KEY)
            constraints_q = text("""
                SELECT TABLE_NAME, CONSTRAINT_NAME, CONSTRAINT_TYPE 
                FROM information_schema.TABLE_CONSTRAINTS 
                WHERE TABLE_SCHEMA = :schema
                ORDER BY TABLE_NAME, CONSTRAINT_NAME
            """)
            constraints = [
                f"{r['TABLE_NAME']}.{r['CONSTRAINT_NAME']}:{r['CONSTRAINT_TYPE']}"
                for r in connection.execute(constraints_q, {"schema": db_name}).mappings().all()
            ]

            # Indexes
            indexes_q = text("""
                SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, COLUMN_NAME, SEQ_IN_INDEX
                FROM information_schema.STATISTICS 
                WHERE TABLE_SCHEMA = :schema
                ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX
            """)
            indexes = [
                f"{r['TABLE_NAME']}.{r['INDEX_NAME']}.{r['COLUMN_NAME']}({r['SEQ_IN_INDEX']})"
                for r in connection.execute(indexes_q, {"schema": db_name}).mappings().all()
            ]

            # Events
            events_q = text("""
                SELECT EVENT_NAME 
                FROM information_schema.EVENTS 
                WHERE EVENT_SCHEMA = :schema
                ORDER BY EVENT_NAME
            """)
            events = [r[0] for r in connection.execute(events_q, {"schema": db_name}).fetchall()]

            return {
                "base_tables": sorted(base_tables),
                "row_counts": row_counts,
                "views": sorted(views),
                "procedures": sorted(procs),
                "triggers": sorted(triggers),
                "constraints": sorted(constraints),
                "indexes": sorted(indexes),
                "events": sorted(events)
            }

        with engine.connect() as db_conn:
            src_meta = _get_db_meta(source_db, db_conn)
            tgt_meta = _get_db_meta(target_db, db_conn)

        mismatches = []

        if src_meta["base_tables"] != tgt_meta["base_tables"]:
            mismatches.append(f"Base table sets differ: Source={src_meta['base_tables']} vs Target={tgt_meta['base_tables']}")

        for tbl, src_cnt in src_meta["row_counts"].items():
            tgt_cnt = tgt_meta["row_counts"].get(tbl)
            if src_cnt != tgt_cnt:
                mismatches.append(f"Row count mismatch on table '{tbl}': Source={src_cnt} vs Target={tgt_cnt}")

        if src_meta["views"] != tgt_meta["views"]:
            mismatches.append(f"View sets differ: Source={src_meta['views']} vs Target={tgt_meta['views']}")

        if src_meta["procedures"] != tgt_meta["procedures"]:
            mismatches.append(f"Stored procedure sets differ: Source={src_meta['procedures']} vs Target={tgt_meta['procedures']}")

        if src_meta["triggers"] != tgt_meta["triggers"]:
            mismatches.append(f"Trigger sets differ: Source={src_meta['triggers']} vs Target={tgt_meta['triggers']}")

        if src_meta["constraints"] != tgt_meta["constraints"]:
            diff_c = set(src_meta["constraints"]) ^ set(tgt_meta["constraints"])
            mismatches.append(f"Constraints differ ({len(diff_c)} discrepancies): {list(diff_c)[:5]}")

        if src_meta["indexes"] != tgt_meta["indexes"]:
            diff_i = set(src_meta["indexes"]) ^ set(tgt_meta["indexes"])
            mismatches.append(f"Indexes differ ({len(diff_i)} discrepancies): {list(diff_i)[:5]}")

        # Post-restore Stored Procedure Execution Check in Target DB
        procedure_test_success = False
        try:
            with engine.connect() as db_conn:
                raw_c = db_conn.connection
                with raw_c.cursor() as cur:
                    cur.execute("SET NAMES utf8mb4")
                    cur.execute(f"USE `{target_db}`")
                    cur.callproc("sp_reconcile_financial_integrity")
                    cur.fetchall()
                    procedure_test_success = True
        except Exception as proc_e:
            mismatches.append(f"Target DB stored procedure validation failed: {str(proc_e)}")

        is_verified = (len(mismatches) == 0 and procedure_test_success)

        return {
            "verified": is_verified,
            "source_database": source_db,
            "target_database": target_db,
            "table_count": len(src_meta["base_tables"]),
            "view_count": len(src_meta["views"]),
            "procedure_count": len(src_meta["procedures"]),
            "trigger_count": len(src_meta["triggers"]),
            "constraint_count": len(src_meta["constraints"]),
            "index_count": len(src_meta["indexes"]),
            "row_counts": src_meta["row_counts"],
            "procedure_executed_successfully": procedure_test_success,
            "mismatches": mismatches
        }

    @classmethod
    def apply_retention_policy(cls, backup_dir: Optional[str] = None, keep_last_n: int = 5) -> List[str]:
        """
        Retains the latest keep_last_n backups and removes older backup artifacts.
        Returns the list of pruned filepaths.
        """
        backup_dir = backup_dir or cls.DEFAULT_BACKUP_DIR
        pattern = os.path.join(backup_dir, "backup_*.sql")
        files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)

        pruned = []
        if len(files) > keep_last_n:
            for old_file in files[keep_last_n:]:
                try:
                    os.remove(old_file)
                    pruned.append(old_file)
                except OSError:
                    pass
        return pruned

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="StockTrade MySQL Backup & Recovery Manager")
    parser.add_argument("--action", choices=["backup", "restore", "verify", "drill"], default="backup")
    parser.add_argument("--source-db", default="stocktrade")
    parser.add_argument("--target-db", default="stocktrade_test")
    parser.add_argument("--file", help="Path to SQL dump file for restore")
    parser.add_argument("--keep", type=int, default=5, help="Number of backups to retain")
    args = parser.parse_args()

    if args.action == "backup":
        print(f"Creating backup for {args.source_db}...")
        meta = BackupManager.create_backup(args.source_db)
        print(f"Backup created successfully: {meta['filepath']} ({meta['size_kb']} KB in {meta['duration_seconds']}s)")
        pruned = BackupManager.apply_retention_policy(keep_last_n=args.keep)
        if pruned:
            print(f"Retention policy pruned {len(pruned)} old backup(s).")

    elif args.action == "restore":
        if not args.file:
            print("Error: --file argument is required for restore.")
            sys.exit(1)
        print(f"Restoring {args.file} into {args.target_db}...")
        res = BackupManager.restore_backup(args.file, args.target_db)
        print(f"Restored successfully in {res['duration_seconds']}s.")

    elif args.action == "verify":
        print(f"Verifying integrity between {args.source_db} and {args.target_db}...")
        res = BackupManager.verify_restoration(args.source_db, args.target_db)
        if res["verified"]:
            print(f"VERIFIED! Tables: {res['table_count']}, Views: {res['view_count']}, Procedures: {res['procedure_count']}, Triggers: {res['trigger_count']}")
        else:
            print(f"VERIFICATION FAILED: {res['mismatches']}")
            sys.exit(1)

    elif args.action == "drill":
        print(f"--- EXECUTING COMPLETE DISASTER RECOVERY DRILL ---")
        print(f"1. Dumping {args.source_db}...")
        b_meta = BackupManager.create_backup(args.source_db)
        print(f"   Created {b_meta['filepath']} ({b_meta['size_kb']} KB)")

        print(f"2. Restoring into sandbox database {args.target_db}...")
        r_meta = BackupManager.restore_backup(b_meta['filepath'], args.target_db)
        print(f"   Restored in {r_meta['duration_seconds']}s")

        print(f"3. Validating structural & numerical parity...")
        v_meta = BackupManager.verify_restoration(args.source_db, args.target_db)
        if v_meta["verified"]:
            print(f"   SUCCESS: 100% parity verified across all {v_meta['table_count']} tables, {v_meta['view_count']} views, {v_meta['procedure_count']} procedures, and {v_meta['trigger_count']} triggers!")
        else:
            print(f"   FAILED PARITY: {v_meta['mismatches']}")
            sys.exit(1)
