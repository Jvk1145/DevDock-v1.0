import os
import sqlite3
from datetime import datetime, timedelta

import pytest

from core.database import Database
from core.errors import DatabaseCorruptError, DatabaseError
from core.models import Project
from core.project_service import ProjectService


def test_pragmas(db):
    assert db.conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    assert db.conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert db.integrity_ok()


def test_transaction_rolls_back(db):
    with pytest.raises(RuntimeError):
        with db.transaction() as conn:
            conn.execute("INSERT INTO settings(key, value) VALUES('a', '1')")
            raise RuntimeError("stop")
    assert db.query_one("SELECT * FROM settings WHERE key='a'") is None


def test_foreign_keys_cascade(projects, folder):
    p = projects.create(Project(name="x", folder_path=folder("x"), tags=["one"]))
    projects.delete(p.id)
    assert projects.db.query("SELECT * FROM project_tags") == []


def test_backup_and_restore(projects, folder):
    db = projects.db
    projects.create(Project(name="keep", folder_path=folder("keep")))
    backup = db.backup("manual")
    projects.create(Project(name="later", folder_path=folder("later")))
    assert projects.count() == 2
    db.restore(backup)
    assert [p.name for p in projects.list_projects()] == ["keep"]
    reasons = {b.reason for b in db.list_backups()}
    assert {"manual", "pre-restore"} <= reasons


def test_restore_rejects_invalid_file(db, tmp_path):
    bogus = tmp_path / "bogus.db"
    bogus.write_bytes(b"not a database at all")
    with pytest.raises(DatabaseError):
        db.restore(bogus)
    assert db.integrity_ok()


def test_prune_keeps_last_seven(db):
    for _ in range(9):
        db.backup("manual")
    assert len([b for b in db.list_backups() if b.reason == "manual"]) == 7


def test_daily_backup_once_per_day(db):
    assert db.daily_backup() is not None
    assert db.daily_backup() is None


def test_daily_backup_after_old_one(db):
    first = db.daily_backup()
    yesterday = datetime.now() - timedelta(days=1)
    old = first.with_name(f"devdock-{yesterday:%Y%m%d-%H%M%S}-daily.db")
    first.rename(old)
    assert db.daily_backup() is not None


def test_corrupt_database_detected(tmp_path):
    path = tmp_path / "bad.db"
    path.write_bytes(b"SQLite format 3\x00" + os.urandom(4096))
    db = Database(path, backup_dir=tmp_path / "b")
    with pytest.raises(DatabaseCorruptError):
        db.open()
        db.check_integrity()
        db.migrate()


def test_quarantine_and_recover_from_backup(tmp_path, folder):
    path = tmp_path / "live.db"
    db = Database(path, backup_dir=tmp_path / "backups").open()
    db.migrate()
    ProjectService(db).create(Project(name="saved", folder_path=folder("saved")))
    db.backup("daily")
    db.close()
    path.write_bytes(b"garbage" * 100)
    moved = Database(path, backup_dir=tmp_path / "backups").quarantine()
    assert moved.exists() and not path.exists()
    fresh = Database(path, backup_dir=tmp_path / "backups").open()
    fresh.restore(fresh.latest_backup().path)
    assert [p.name for p in ProjectService(fresh).list_projects()] == ["saved"]
    fresh.close()


def test_paths_with_spaces_and_unicode(tmp_path):
    path = tmp_path / "Mes données" / "dev dock.db"
    db = Database(path, backup_dir=path.parent / "sauvegardes").open()
    db.migrate()
    assert db.backup("manual").exists()
    db.close()
    assert sqlite3.connect(path).execute("PRAGMA integrity_check").fetchone()[0] == "ok"
