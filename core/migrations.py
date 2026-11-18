"""Ordered, versioned schema migrations.

The current version is stored in the ``schema_version`` table. A database without that table
is version 0. Both DevDock 1.x layouts are version 0:

  * projects(id, project_name, description, technology, status, folder_path, created_at)
  * the same plus github_url and live_demo

Every step is written so that it upgrades either layout without losing rows.
"""
from __future__ import annotations

import logging
import os
import re
import sqlite3
from dataclasses import dataclass
from typing import Callable

from core import timeutil

log = logging.getLogger(__name__)

KNOWN_STATUSES = ("Active", "Completed", "On Hold")

# IDE names used by DevDock 1.x in the ide_settings table -> IDE keys used now.
LEGACY_IDE_NAMES = {
    "vs code": "vscode",
    "visual studio code": "vscode",
    "cursor": "cursor",
    "pycharm": "pycharm",
    "pycharm community": "pycharm_ce",
    "intellij idea": "intellij",
    "android studio": "android_studio",
    "visual studio": "visual_studio",
    "sublime text": "sublime",
    "notepad++": "notepadpp",
}


@dataclass(frozen=True)
class Migration:
    version: int
    description: str
    apply: Callable[[sqlite3.Connection], None]


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return row is not None


def columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def current_version(conn: sqlite3.Connection) -> int:
    if not table_exists(conn, "schema_version"):
        return 0
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return int(row[0] or 0)


def ensure_version_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version(
            version     INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at  TEXT NOT NULL
        )""")


# --------------------------------------------------------------------------- v1
def _v1_baseline(conn: sqlite3.Connection) -> None:
    """Bring any 1.x database (or an empty one) to the same 1.x layout."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            description TEXT,
            technology TEXT,
            status TEXT,
            folder_path TEXT,
            github_url TEXT,
            live_demo TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    existing = columns(conn, "projects")
    for name, ddl in (("description", "TEXT"), ("technology", "TEXT"), ("status", "TEXT"),
                      ("folder_path", "TEXT"), ("github_url", "TEXT"), ("live_demo", "TEXT"),
                      ("created_at", "TIMESTAMP")):
        if name not in existing:
            conn.execute(f"ALTER TABLE projects ADD COLUMN {name} {ddl}")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ide_settings(
            ide_name TEXT PRIMARY KEY,
            exe_path TEXT NOT NULL
        )""")


# --------------------------------------------------------------------------- v2
def _unique_name(name: str, used: set[str]) -> str:
    candidate, n = name, 2
    while candidate.lower() in used:
        candidate = f"{name} ({n})"
        n += 1
    used.add(candidate.lower())
    return candidate


def _normalize_status(value: str | None) -> str:
    text = (value or "").strip().lower().replace("_", " ")
    for status in KNOWN_STATUSES:
        if status.lower() == text:
            return status
    return "Active"


def _v2_projects_table(conn: sqlite3.Connection) -> None:
    """Rebuild projects with named columns, preferred IDE, favourites and timestamps."""
    conn.execute("""
        CREATE TABLE projects_v2(
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL UNIQUE COLLATE NOCASE,
            description   TEXT    NOT NULL DEFAULT '',
            technology    TEXT    NOT NULL DEFAULT '',
            status        TEXT    NOT NULL DEFAULT 'Active',
            folder_path   TEXT    NOT NULL DEFAULT '',
            preferred_ide TEXT,
            github_url    TEXT    NOT NULL DEFAULT '',
            live_demo     TEXT    NOT NULL DEFAULT '',
            start_command TEXT    NOT NULL DEFAULT '',
            favorite      INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT    NOT NULL,
            updated_at    TEXT    NOT NULL,
            last_opened   TEXT
        )""")
    used: set[str] = set()
    now = timeutil.now_str()
    cursor = conn.execute("SELECT * FROM projects ORDER BY id")
    names = [d[0] for d in cursor.description]
    rows = [dict(zip(names, tuple(r))) for r in cursor.fetchall()]
    renamed = 0
    for data in rows:
        original = (data.get("project_name") or "").strip() or "Untitled project"
        name = _unique_name(original, used)
        renamed += name != original
        folder = (data.get("folder_path") or "").strip()
        if folder:
            folder = os.path.normpath(folder)
        created = str(data.get("created_at") or now)
        conn.execute("""
            INSERT INTO projects_v2(id, name, description, technology, status, folder_path,
                                    github_url, live_demo, created_at, updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)""", (
            data["id"], name, (data.get("description") or "").strip(),
            (data.get("technology") or "").strip(), _normalize_status(data.get("status")),
            folder, (data.get("github_url") or "").strip(), (data.get("live_demo") or "").strip(),
            created, created))
    conn.execute("DROP TABLE projects")
    conn.execute("ALTER TABLE projects_v2 RENAME TO projects")
    log.info("Migrated %d project(s); renamed %d duplicate name(s)", len(rows), renamed)


# --------------------------------------------------------------------------- v3
def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "ide"


def _v3_settings_ides_tags(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings(
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ide_paths(
            ide_key  TEXT PRIMARY KEY,
            exe_path TEXT NOT NULL
        )""")
    if table_exists(conn, "ide_settings"):
        for ide_name, exe_path in conn.execute("SELECT ide_name, exe_path FROM ide_settings").fetchall():
            if not exe_path:
                continue
            key = LEGACY_IDE_NAMES.get((ide_name or "").strip().lower(), _slug(ide_name or ""))
            conn.execute("INSERT OR REPLACE INTO ide_paths(ide_key, exe_path) VALUES(?,?)",
                         (key, os.path.normpath(exe_path)))
        conn.execute("DROP TABLE ide_settings")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tags(
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_tags(
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            tag_id     INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            PRIMARY KEY(project_id, tag_id)
        )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_last_opened ON projects(last_opened)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_tags_tag ON project_tags(tag_id)")


MIGRATIONS: tuple[Migration, ...] = (
    Migration(1, "Baseline: normalize DevDock 1.x layouts", _v1_baseline),
    Migration(2, "Projects table with preferred IDE, favorites, start command, timestamps", _v2_projects_table),
    Migration(3, "Settings, IDE paths, tags and indexes", _v3_settings_ides_tags),
)

LATEST_VERSION = MIGRATIONS[-1].version


def pending(conn: sqlite3.Connection) -> list[Migration]:
    version = current_version(conn)
    return [m for m in MIGRATIONS if m.version > version]
