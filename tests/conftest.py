import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import Database  # noqa: E402
from core.project_service import ProjectService  # noqa: E402
from core.settings_service import SettingsService  # noqa: E402

# Exact layouts written by DevDock 1.x
LEGACY_SCHEMA_WITH_LINKS = """
CREATE TABLE projects(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name TEXT NOT NULL,
    description TEXT,
    technology TEXT,
    status TEXT,
    folder_path TEXT,
    github_url TEXT,
    live_demo TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE ide_settings(ide_name TEXT PRIMARY KEY, exe_path TEXT NOT NULL);
"""

LEGACY_SCHEMA_PLAIN = """
CREATE TABLE projects(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name TEXT NOT NULL,
    description TEXT,
    technology TEXT,
    status TEXT,
    folder_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE ide_settings(ide_name TEXT PRIMARY KEY, exe_path TEXT NOT NULL);
"""


@pytest.fixture
def make_legacy_db(tmp_path):
    def _make(with_links: bool, name: str = "legacy.db") -> Path:
        path = tmp_path / name
        conn = sqlite3.connect(path)
        if with_links:
            conn.executescript(LEGACY_SCHEMA_WITH_LINKS)
            conn.executemany(
                "INSERT INTO projects(id, project_name, description, technology, status, folder_path, "
                "github_url, live_demo, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                [(1, "test5", "test5", "Python", "Active", "F:/test", "tesdt5", "test55", "2026-07-12 06:06:36"),
                 (2, "test5", "dup", "Python", "Active", "F:/test", None, None, "2026-07-12 06:14:14"),
                 (4, "Retail dashboard", "", "Python", "Active", "F:/Retail_Sales_Analytics",
                  "https://github.com/example/retail", "", "2026-07-12 09:16:42"),
                 (5, "Ünïcode proj", None, None, None, None, None, None, None)])
        else:
            conn.executescript(LEGACY_SCHEMA_PLAIN)
            conn.execute("INSERT INTO projects(id, project_name, description, technology, status, folder_path, "
                         "created_at) VALUES(1,'devdock','building','Python','completed','F:/DevDock',"
                         "'2026-07-12 16:59:05')")
        conn.executemany("INSERT INTO ide_settings VALUES(?,?)",
                         [("PyCharm", r"C:\Program Files\JetBrains\PyCharm 2026.1.3\bin\pycharm64.exe"),
                          ("VS Code", r"C:\Users\me\AppData\Local\Programs\Microsoft VS Code\Code.exe")])
        conn.commit()
        conn.close()
        return path
    return _make


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "data" / "devdock.db", backup_dir=tmp_path / "data" / "backups").open()
    database.migrate()
    yield database
    database.close()


@pytest.fixture
def projects(db):
    return ProjectService(db)


@pytest.fixture
def settings(db):
    return SettingsService(db)


@pytest.fixture
def folder(tmp_path):
    def _make(name: str) -> str:
        path = tmp_path / "work" / name
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
    return _make
