"""SQLite connection management: WAL, foreign keys, transactions, migrations, backups.

The connection runs in autocommit mode (isolation_level=None). Every write goes through
``transaction()``, which issues an explicit BEGIN IMMEDIATE ... COMMIT or rolls back on error.
"""
from __future__ import annotations

import logging
import re
import shutil
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Sequence

from core import migrations, timeutil
from core.errors import DatabaseCorruptError, DatabaseError

log = logging.getLogger(__name__)

_BACKUP_RE = re.compile(r"^devdock-(\d{8})-(\d{6})(?:-\d+)?-([a-z0-9-]+)\.db$")


@dataclass(frozen=True)
class BackupInfo:
    path: Path
    created: datetime   # local time
    reason: str
    size: int

    @property
    def label(self) -> str:
        return f"{self.created:%Y-%m-%d %H:%M:%S}  ·  {self.reason}  ·  {self.size / 1024:.0f} KB"


class Database:
    def __init__(self, path: Path | str, backup_dir: Path | str | None = None, keep_backups: int = 7):
        self.path = Path(path)
        self.backup_dir = Path(backup_dir) if backup_dir else self.path.parent / "backups"
        self.keep_backups = keep_backups
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.RLock()
        self.created_new = False

    # ------------------------------------------------------------------ connection
    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise DatabaseError("The database is not open.")
        return self._conn

    def open(self) -> "Database":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.created_new = not self.path.exists() or self.path.stat().st_size == 0
        try:
            conn = sqlite3.connect(str(self.path), isolation_level=None, timeout=5,
                                   check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
        except sqlite3.DatabaseError as exc:
            raise DatabaseCorruptError(
                "DevDock's database file could not be opened. It may be damaged.", str(exc)) from exc
        self._conn = conn
        return self

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                finally:
                    self._conn = None

    # ------------------------------------------------------------------ health
    def integrity_ok(self) -> bool:
        try:
            row = self.conn.execute("PRAGMA integrity_check").fetchone()
            return row is not None and str(row[0]).lower() == "ok"
        except sqlite3.DatabaseError:
            return False

    def check_integrity(self) -> None:
        if not self.integrity_ok():
            raise DatabaseCorruptError("DevDock's database failed its integrity check. It may be damaged.")

    # ------------------------------------------------------------------ queries
    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            conn = self.conn
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            else:
                conn.execute("COMMIT")

    def query(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self.conn.execute(sql, tuple(params)).fetchall()

    def query_one(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
        with self._lock:
            return self.conn.execute(sql, tuple(params)).fetchone()

    def execute(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        """Run one write statement in its own transaction."""
        with self.transaction() as conn:
            return conn.execute(sql, tuple(params))

    # ------------------------------------------------------------------ migrations
    def schema_version(self) -> int:
        return migrations.current_version(self.conn)

    def _has_user_tables(self) -> bool:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()
        return bool(row and row[0])

    def migrate(self) -> list[int]:
        """Apply pending migrations. Takes a backup first if the database already holds data."""
        with self._lock:
            todo = migrations.pending(self.conn)
            if not todo:
                return []
            if self._has_user_tables():
                self.backup(f"pre-v{todo[-1].version}")
            self.conn.execute("PRAGMA foreign_keys=OFF")
            applied: list[int] = []
            try:
                for step in todo:
                    with self.transaction() as conn:
                        migrations.ensure_version_table(conn)
                        step.apply(conn)
                        conn.execute("INSERT INTO schema_version(version, description, applied_at) VALUES(?,?,?)",
                                     (step.version, step.description, timeutil.now_str()))
                    applied.append(step.version)
                    log.info("Applied migration v%d: %s", step.version, step.description)
            except sqlite3.Error as exc:
                log.exception("Migration failed")
                raise DatabaseError("DevDock could not upgrade its database. A backup was kept.", str(exc)) from exc
            finally:
                self.conn.execute("PRAGMA foreign_keys=ON")
            problems = self.conn.execute("PRAGMA foreign_key_check").fetchall()
            if problems:
                log.warning("Foreign key problems after migration: %s", [tuple(p) for p in problems])
            return applied

    # ------------------------------------------------------------------ backups
    def backup(self, reason: str = "manual") -> Path:
        reason = re.sub(r"[^a-z0-9-]+", "-", reason.lower()).strip("-") or "manual"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target = self.backup_dir / f"devdock-{stamp}-{reason}.db"
        counter = 1
        while target.exists():
            target = self.backup_dir / f"devdock-{stamp}-{counter}-{reason}.db"
            counter += 1
        with self._lock:
            dest = sqlite3.connect(str(target))
            try:
                self.conn.backup(dest)
            finally:
                dest.close()
        log.info("Backup created: %s", target)
        self.prune_backups(reason)
        return target

    def list_backups(self) -> list[BackupInfo]:
        if not self.backup_dir.is_dir():
            return []
        result: list[BackupInfo] = []
        for file in self.backup_dir.glob("devdock-*.db"):
            match = _BACKUP_RE.match(file.name)
            if not match:
                continue
            try:
                created = datetime.strptime(match.group(1) + match.group(2), "%Y%m%d%H%M%S")
                result.append(BackupInfo(file, created, match.group(3), file.stat().st_size))
            except (ValueError, OSError):
                continue
        result.sort(key=lambda b: (b.created, b.path.name), reverse=True)
        return result

    def latest_backup(self) -> BackupInfo | None:
        backups = self.list_backups()
        return backups[0] if backups else None

    def prune_backups(self, reason: str) -> None:
        same_kind = [b for b in self.list_backups() if b.reason == reason]
        for old in same_kind[self.keep_backups:]:
            try:
                old.path.unlink()
            except OSError:
                log.warning("Could not delete old backup %s", old.path)

    def daily_backup(self) -> Path | None:
        today = datetime.now().date()
        if any(b.reason == "daily" and b.created.date() == today for b in self.list_backups()):
            return None
        return self.backup("daily")

    @staticmethod
    def is_valid_backup(path: Path | str) -> bool:
        try:
            conn = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
            try:
                ok = conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                has_projects = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='projects'").fetchone()
                return bool(ok and has_projects)
            finally:
                conn.close()
        except sqlite3.Error:
            return False

    def _remove_db_files(self) -> None:
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(str(self.path) + suffix)
            if candidate.exists():
                candidate.unlink()

    def restore(self, backup_path: Path | str) -> None:
        """Replace the live database with a backup, then migrate it to the current schema."""
        backup_path = Path(backup_path)
        if not self.is_valid_backup(backup_path):
            raise DatabaseError("That backup file is not a valid DevDock database.")
        with self._lock:
            if self._conn is not None:
                try:
                    if self.integrity_ok():
                        self.backup("pre-restore")
                except (sqlite3.Error, OSError):
                    log.warning("Could not back up the current database before restoring")
                self.close()
            try:
                self._remove_db_files()
                shutil.copy2(backup_path, self.path)
            except OSError as exc:
                raise DatabaseError("The backup could not be restored.", str(exc)) from exc
            self.open()
            self.migrate()
        log.info("Restored database from %s", backup_path)

    def quarantine(self) -> Path | None:
        """Move a damaged database aside so a fresh one can be created."""
        self.close()
        if not self.path.exists():
            return None
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target = self.path.with_name(f"devdock.corrupt-{stamp}.db")
        try:
            self.path.replace(target)
            for suffix in ("-wal", "-shm"):
                extra = Path(str(self.path) + suffix)
                if extra.exists():
                    extra.unlink()
        except OSError as exc:
            raise DatabaseError("The damaged database could not be moved aside.", str(exc)) from exc
        log.warning("Damaged database moved to %s", target)
        return target
