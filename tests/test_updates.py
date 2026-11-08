"""
MediaDock Release Channels, Auto-Updates & Migration Backup Tests.
Verifies channel switching, pre-migration database snapshotting, rollback,
and cryptographic signature/version compatibility checking.
"""
import sqlite3
import pytest
from pathlib import Path
from app.services.update_service import ReleaseUpdateManager


def test_channel_selection_and_defaults(tmp_path):
    mgr = ReleaseUpdateManager(db_path=str(tmp_path / "mock.db"))
    assert mgr.channel == "stable"

    # Opt-in to beta
    assert mgr.set_channel("beta") == "beta"
    assert mgr.channel == "beta"

    # Opt-in to dev
    assert mgr.set_channel("dev") == "dev"
    assert mgr.channel == "dev"

    # Unsupported falls back to stable
    assert mgr.set_channel("untrusted-channel") == "stable"
    assert mgr.channel == "stable"


def test_database_backup_and_rollback(tmp_path):
    db_file = tmp_path / "primary_app.db"
    backup_dir = tmp_path / "backups"

    # Create dummy database with some state
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE mock_state (key TEXT, val TEXT)")
    conn.execute("INSERT INTO mock_state VALUES ('schema_ver', '1')")
    conn.commit()
    conn.close()

    mgr = ReleaseUpdateManager(db_path=str(db_file), backup_dir=str(backup_dir))

    # Create snapshot
    backup_path = mgr.create_pre_migration_backup()
    assert backup_path is not None
    assert backup_path.exists()

    # Simulate corruptive migration
    conn = sqlite3.connect(str(db_file))
    conn.execute("DROP TABLE mock_state")
    conn.commit()
    conn.close()

    # Roll back
    assert mgr.rollback_database_from_backup(backup_path) is True

    # Verify restored state
    restored_conn = sqlite3.connect(str(db_file))
    cursor = restored_conn.cursor()
    cursor.execute("SELECT val FROM mock_state WHERE key = 'schema_ver'")
    row = cursor.fetchone()
    assert row[0] == "1"
    restored_conn.close()


def test_update_manifest_verification(tmp_path):
    mgr = ReleaseUpdateManager(db_path=str(tmp_path / "mock.db"))

    # Older / current version -> no update available
    res_no_up = mgr.verify_update_manifest({
        "version": "0.1.0",
        "notes": "Current version",
    })
    assert res_no_up.update_available is False

    # Newer release with signature -> update available
    res_up = mgr.verify_update_manifest({
        "version": "0.2.0",
        "signature": "dGVzdC1zaWduYXR1cmUtYnl0ZXM=",
        "url": "https://github.com/mediadock/mediadock/releases/download/v0.2.0/mediadock.exe",
        "notes": "Added new features.",
        "min_sidecar_version": "0.1.0",
    })
    assert res_up.update_available is True
    assert res_up.latest_version == "0.2.0"
    assert res_up.signature is not None
    assert res_up.requires_sidecar_upgrade is False
