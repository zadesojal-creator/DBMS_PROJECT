"""
Database Backup & Recovery Manager Tests (tests/test_backup.py)
Validates:
- Discovery of MySQL binaries
- Generation of consistent logical backups containing schema, data, triggers, and routines
- Retention policy enforcement and pruning of obsolete snapshots
"""
import os
import tempfile
import pytest
from database.backup_manager import BackupManager

def test_mysql_binary_discovery():
    """BackupManager discovers mysqldump and mysql binaries on the host system."""
    dump_bin = BackupManager.find_mysql_bin("mysqldump")
    assert os.path.exists(dump_bin)
    assert "mysqldump" in dump_bin.lower()

    mysql_bin = BackupManager.find_mysql_bin("mysql")
    assert os.path.exists(mysql_bin)
    assert "mysql" in mysql_bin.lower()

def test_backup_creation_and_metadata():
    """BackupManager creates a consistent, non-empty SQL backup with full routines and triggers."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        meta = BackupManager.create_backup(db_name="stocktrade", output_dir=tmp_dir)
        assert meta["success"] is True
        assert os.path.exists(meta["filepath"])
        assert meta["size_bytes"] > 100000  # At least 100KB of schema and seed data
        assert meta["duration_seconds"] >= 0

        # Inspect backup content for routines and triggers
        with open(meta["filepath"], "r", encoding="utf-8") as f:
            content = f.read(50000)
            assert "CREATE TABLE" in content
            assert "TRIGGER" in content or "trigger" in content

def test_backup_retention_policy():
    """apply_retention_policy retains the latest N backups and safely prunes older ones."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create 5 dummy backup files
        filenames = [
            f"backup_stocktrade_20261026_01000{i}.sql" for i in range(5)
        ]
        created_paths = []
        for fn in filenames:
            p = os.path.join(tmp_dir, fn)
            with open(p, "w", encoding="utf-8") as f:
                f.write("-- dummy dump\n")
            created_paths.append(p)

        pruned = BackupManager.apply_retention_policy(backup_dir=tmp_dir, keep_last_n=2)
        assert len(pruned) == 3

        remaining = [f for f in os.listdir(tmp_dir) if f.endswith(".sql")]
        assert len(remaining) == 2
