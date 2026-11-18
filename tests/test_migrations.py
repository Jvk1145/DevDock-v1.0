import os
import sqlite3

from core import migrations
from core.database import Database
from core.project_service import ProjectService
from core.settings_service import SettingsService


def _open(path, tmp_path):
    return Database(path, backup_dir=tmp_path / "backups").open()


def test_empty_database_reaches_latest(tmp_path):
    db = _open(tmp_path / "new.db", tmp_path)
    applied = db.migrate()
    assert applied == [m.version for m in migrations.MIGRATIONS]
    assert db.schema_version() == migrations.LATEST_VERSION
    cols = migrations.columns(db.conn, "projects")
    assert {"name", "preferred_ide", "favorite", "start_command", "last_opened", "updated_at"} <= cols
    for table in ("settings", "ide_paths", "tags", "project_tags", "schema_version"):
        assert migrations.table_exists(db.conn, table)
    assert not migrations.table_exists(db.conn, "ide_settings")
    # A brand-new database has nothing to protect, so no backup is made.
    assert db.list_backups() == []
    db.close()


def test_migrate_is_idempotent(tmp_path):
    db = _open(tmp_path / "new.db", tmp_path)
    db.migrate()
    assert db.migrate() == []
    db.close()


def test_legacy_schema_with_links(tmp_path, make_legacy_db):
    path = make_legacy_db(with_links=True)
    db = _open(path, tmp_path)
    db.migrate()
    rows = ProjectService(db).list_projects(sort="name")
    by_id = {p.id: p for p in rows}
    assert len(rows) == 4
    assert by_id[1].name == "test5"
    assert by_id[2].name == "test5 (2)"            # duplicate renamed, not dropped
    assert by_id[1].github_url == "tesdt5"         # odd legacy values kept as-is
    assert by_id[1].live_demo == "test55"
    assert by_id[1].folder_path == os.path.normpath("F:/test")
    assert by_id[1].created_at == "2026-07-12 06:06:36"
    assert by_id[4].github_url == "https://github.com/example/retail"
    assert by_id[5].name == "Ünïcode proj"
    assert by_id[5].status == "Active" and by_id[5].description == ""
    assert all(p.preferred_ide is None for p in rows)
    paths = SettingsService(db).ide_paths()
    assert paths["pycharm"].endswith("pycharm64.exe")
    assert paths["vscode"].endswith("Code.exe")
    # Backup was taken before upgrading.
    assert [b.reason for b in db.list_backups()] == [f"pre-v{migrations.LATEST_VERSION}"]
    db.close()


def test_legacy_schema_without_links(tmp_path, make_legacy_db):
    path = make_legacy_db(with_links=False)
    db = _open(path, tmp_path)
    db.migrate()
    project = ProjectService(db).get(1)
    assert project.name == "devdock"
    assert project.status == "Completed"           # 'completed' normalized
    assert project.github_url == ""
    assert db.schema_version() == migrations.LATEST_VERSION
    db.close()


def test_new_ids_continue_after_legacy_ids(tmp_path, make_legacy_db, folder):
    db = _open(make_legacy_db(with_links=True), tmp_path)
    db.migrate()
    from core.models import Project
    created = ProjectService(db).create(Project(name="fresh", folder_path=folder("fresh")))
    assert created.id > 5
    db.close()


def test_failed_migration_rolls_back(tmp_path, monkeypatch):
    db = _open(tmp_path / "x.db", tmp_path)

    def boom(conn):
        conn.execute("CREATE TABLE half_done(x)")
        raise sqlite3.OperationalError("simulated")

    broken = migrations.MIGRATIONS[:1] + (migrations.Migration(2, "broken", boom),)
    monkeypatch.setattr(migrations, "MIGRATIONS", broken)
    import pytest
    from core.errors import DatabaseError
    with pytest.raises(DatabaseError):
        db.migrate()
    assert db.schema_version() == 1
    assert not migrations.table_exists(db.conn, "half_done")
    db.close()


def test_merge_legacy_database(projects, make_legacy_db, tmp_path):
    with_links = make_legacy_db(with_links=True, name="a.db")
    plain = make_legacy_db(with_links=False, name="b.db")
    first = projects.merge_legacy_database(with_links)
    second = projects.merge_legacy_database(plain)
    assert first.added == 4 and second.added == 1
    again = projects.merge_legacy_database(with_links)
    assert again.added == 0 and again.skipped == 4
    names = {p.name for p in projects.list_projects()}
    assert {"test5", "test5 (2)", "Retail dashboard", "devdock"} <= names
    # Source files are untouched
    conn = sqlite3.connect(with_links)
    assert conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 4
    assert migrations.table_exists(conn, "ide_settings")
    conn.close()
