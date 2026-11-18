"""Project CRUD, search, filtering, sorting, favourites, tags and JSON import/export."""
from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Iterable

from core import timeutil
from core.database import Database
from core.errors import ImportExportError, NotFoundError, ValidationError
from core.models import FolderCandidate, ImportResult, Project
from core.validators import STATUSES, normalize_path, parse_tags, validate_project

log = logging.getLogger(__name__)

EXPORT_FORMAT = "devdock-projects"
EXPORT_VERSION = 1

_SORT_SQL = {
    "recent": "CASE WHEN p.last_opened IS NULL THEN 1 ELSE 0 END, p.last_opened DESC, p.created_at DESC, p.id DESC",
    "name": "p.name COLLATE NOCASE ASC, p.id ASC",
    "newest": "p.created_at DESC, p.id DESC",
}


def _like(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def folder_key(path: str) -> str:
    """Comparable form of a folder path (case-insensitive on Windows)."""
    return os.path.normcase(normalize_path(path)).rstrip("\\/")


class ProjectService:
    def __init__(self, db: Database):
        self.db = db

    # ------------------------------------------------------------------ reading
    def _tags_for(self, ids: Iterable[int]) -> dict[int, list[str]]:
        ids = list(ids)
        if not ids:
            return {}
        result: dict[int, list[str]] = {i: [] for i in ids}
        placeholders = ",".join("?" * len(ids))
        rows = self.db.query(
            f"SELECT pt.project_id, t.name FROM project_tags pt JOIN tags t ON t.id = pt.tag_id "
            f"WHERE pt.project_id IN ({placeholders}) ORDER BY t.name COLLATE NOCASE", ids)
        for row in rows:
            result[row["project_id"]].append(row["name"])
        return result

    def _hydrate(self, rows: list[sqlite3.Row]) -> list[Project]:
        tags = self._tags_for(row["id"] for row in rows)
        return [Project.from_row(row, tags.get(row["id"], [])) for row in rows]

    def list_projects(self, search: str = "", status: str | None = None, technology: str | None = None,
                      tag: str | None = None, sort: str = "recent", favorites_only: bool = False,
                      limit: int | None = None) -> list[Project]:
        where: list[str] = []
        params: list[object] = []
        text = (search or "").strip()
        if text:
            like = _like(text)
            where.append(
                "(p.name LIKE ? ESCAPE '\\' OR p.description LIKE ? ESCAPE '\\' OR p.technology LIKE ? ESCAPE '\\' "
                "OR p.status LIKE ? ESCAPE '\\' OR p.folder_path LIKE ? ESCAPE '\\' OR EXISTS ("
                "SELECT 1 FROM project_tags pt JOIN tags t ON t.id = pt.tag_id "
                "WHERE pt.project_id = p.id AND t.name LIKE ? ESCAPE '\\'))")
            params += [like] * 6
        if status:
            where.append("p.status = ?")
            params.append(status)
        if technology:
            where.append("p.technology = ? COLLATE NOCASE")
            params.append(technology)
        if tag:
            where.append("EXISTS (SELECT 1 FROM project_tags pt JOIN tags t ON t.id = pt.tag_id "
                         "WHERE pt.project_id = p.id AND t.name = ? COLLATE NOCASE)")
            params.append(tag)
        if favorites_only:
            where.append("p.favorite = 1")
        sql = "SELECT p.* FROM projects p"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY " + _SORT_SQL.get(sort, _SORT_SQL["recent"])
        if limit:
            sql += " LIMIT ?"
            params.append(int(limit))
        return self._hydrate(self.db.query(sql, params))

    def get(self, project_id: int) -> Project:
        row = self.db.query_one("SELECT * FROM projects WHERE id=?", (project_id,))
        if row is None:
            raise NotFoundError("That project no longer exists.")
        return self._hydrate([row])[0]

    def ids(self) -> set[int]:
        return {row["id"] for row in self.db.query("SELECT id FROM projects")}

    def count(self) -> int:
        row = self.db.query_one("SELECT COUNT(*) AS n FROM projects")
        return int(row["n"]) if row else 0

    def recent(self, limit: int = 6) -> list[Project]:
        rows = self.db.query("SELECT * FROM projects WHERE last_opened IS NOT NULL "
                             "ORDER BY last_opened DESC, id DESC LIMIT ?", (limit,))
        return self._hydrate(rows)

    def pinned(self) -> list[Project]:
        return self.list_projects(favorites_only=True, sort="name")

    def technologies(self) -> list[str]:
        rows = self.db.query("SELECT DISTINCT technology FROM projects WHERE technology <> '' "
                             "ORDER BY technology COLLATE NOCASE")
        return [row["technology"] for row in rows]

    def all_tags(self) -> list[str]:
        rows = self.db.query("SELECT t.name FROM tags t WHERE EXISTS "
                             "(SELECT 1 FROM project_tags pt WHERE pt.tag_id = t.id) ORDER BY t.name COLLATE NOCASE")
        return [row["name"] for row in rows]

    def name_taken(self, name: str, exclude_id: int | None = None) -> bool:
        row = self.db.query_one("SELECT id FROM projects WHERE name = ? COLLATE NOCASE AND id IS NOT ?",
                                ((name or "").strip(), exclude_id))
        return row is not None

    def registered_folders(self) -> set[str]:
        return {folder_key(row["folder_path"]) for row in self.db.query("SELECT folder_path FROM projects")}

    def unique_name(self, base: str) -> str:
        base = (base or "").strip() or "Untitled project"
        candidate, n = base, 2
        while self.name_taken(candidate):
            candidate = f"{base} ({n})"
            n += 1
        return candidate

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def find_missing(projects: Iterable[Project]) -> set[int]:
        """IDs of projects whose folder is gone. Touches the disk: call from a worker thread."""
        return {p.id for p in projects if p.id is not None and not os.path.isdir(p.folder_path)}

    @staticmethod
    def stats(projects: list[Project], missing_ids: set[int] | None = None) -> dict[str, int]:
        missing_ids = missing_ids or set()
        counts = {"total": len(projects), "missing": sum(1 for p in projects if p.id in missing_ids)}
        for status in STATUSES:
            counts[status] = sum(1 for p in projects if p.status == status)
        return counts

    @staticmethod
    def _clean(project: Project) -> Project:
        return replace(
            project,
            name=" ".join((project.name or "").split()),
            folder_path=normalize_path(project.folder_path),
            description=(project.description or "").strip(),
            technology=(project.technology or "").strip(),
            status=project.status if project.status in STATUSES else "Active",
            github_url=(project.github_url or "").strip(),
            live_demo=(project.live_demo or "").strip(),
            start_command=(project.start_command or "").strip(),
            tags=parse_tags(project.tags),
            preferred_ide=project.preferred_ide or None,
        )

    # Fields a lenient (legacy) import may carry over unchanged; the edit form flags them later.
    _LENIENT_FIELDS = ("folder_path", "github_url", "live_demo", "tags")

    def _validate(self, project: Project, require_existing_folder: bool, lenient: bool = False) -> None:
        errors = validate_project(project, lambda n: self.name_taken(n, project.id), require_existing_folder)
        if lenient:
            errors = {k: v for k, v in errors.items() if k not in self._LENIENT_FIELDS}
        if errors:
            raise ValidationError(errors)

    @staticmethod
    def _save_tags(conn: sqlite3.Connection, project_id: int, tags: list[str]) -> None:
        conn.execute("DELETE FROM project_tags WHERE project_id=?", (project_id,))
        for tag in tags:
            conn.execute("INSERT OR IGNORE INTO tags(name) VALUES(?)", (tag,))
            tag_id = conn.execute("SELECT id FROM tags WHERE name=? COLLATE NOCASE", (tag,)).fetchone()[0]
            conn.execute("INSERT OR IGNORE INTO project_tags(project_id, tag_id) VALUES(?,?)", (project_id, tag_id))
        conn.execute("DELETE FROM tags WHERE id NOT IN (SELECT tag_id FROM project_tags)")

    def _insert(self, conn: sqlite3.Connection, project: Project) -> int:
        now = timeutil.now_str()
        cursor = conn.execute("""
            INSERT INTO projects(name, description, technology, status, folder_path, preferred_ide,
                                 github_url, live_demo, start_command, favorite, created_at, updated_at,
                                 last_opened)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            project.name, project.description, project.technology, project.status, project.folder_path,
            project.preferred_ide, project.github_url, project.live_demo, project.start_command,
            int(project.favorite), project.created_at or now, now, project.last_opened))
        project_id = int(cursor.lastrowid)
        self._save_tags(conn, project_id, project.tags)
        return project_id

    # ------------------------------------------------------------------ writing
    def create(self, project: Project, require_existing_folder: bool = True, lenient: bool = False) -> Project:
        project = self._clean(replace(project, id=None))
        self._validate(project, require_existing_folder, lenient)
        with self.db.transaction() as conn:
            project_id = self._insert(conn, project)
        log.info("Created project %r (id=%s)", project.name, project_id)
        return self.get(project_id)

    def update(self, project: Project, require_existing_folder: bool = True) -> Project:
        if project.id is None:
            raise NotFoundError("That project has not been saved yet.")
        self.get(project.id)
        project = self._clean(project)
        self._validate(project, require_existing_folder)
        with self.db.transaction() as conn:
            conn.execute("""
                UPDATE projects SET name=?, description=?, technology=?, status=?, folder_path=?,
                       preferred_ide=?, github_url=?, live_demo=?, start_command=?, favorite=?, updated_at=?
                WHERE id=?""", (
                project.name, project.description, project.technology, project.status, project.folder_path,
                project.preferred_ide, project.github_url, project.live_demo, project.start_command,
                int(project.favorite), timeutil.now_str(), project.id))
            self._save_tags(conn, project.id, project.tags)
        log.info("Updated project %r (id=%s)", project.name, project.id)
        return self.get(project.id)

    def delete(self, project_id: int) -> None:
        with self.db.transaction() as conn:
            cursor = conn.execute("DELETE FROM projects WHERE id=?", (project_id,))
            if cursor.rowcount == 0:
                raise NotFoundError("That project no longer exists.")
            conn.execute("DELETE FROM tags WHERE id NOT IN (SELECT tag_id FROM project_tags)")
        log.info("Deleted project id=%s", project_id)

    def _set_column(self, project_id: int, column: str, value: object) -> None:
        cursor = self.db.execute(f"UPDATE projects SET {column}=?, updated_at=? WHERE id=?",
                                 (value, timeutil.now_str(), project_id))
        if cursor.rowcount == 0:
            raise NotFoundError("That project no longer exists.")

    def set_favorite(self, project_id: int, favorite: bool) -> None:
        self._set_column(project_id, "favorite", int(bool(favorite)))

    def toggle_favorite(self, project_id: int) -> bool:
        new_value = not self.get(project_id).favorite
        self.set_favorite(project_id, new_value)
        return new_value

    def set_preferred_ide(self, project_id: int, ide_key: str | None) -> None:
        self._set_column(project_id, "preferred_ide", ide_key or None)

    def mark_opened(self, project_id: int) -> None:
        cursor = self.db.execute("UPDATE projects SET last_opened=? WHERE id=?", (timeutil.now_str(), project_id))
        if cursor.rowcount == 0:
            raise NotFoundError("That project no longer exists.")

    def relocate(self, project_id: int, new_folder: str) -> Project:
        folder = normalize_path(new_folder)
        if not os.path.isdir(folder):
            raise ValidationError({"folder_path": "This folder does not exist."})
        self._set_column(project_id, "folder_path", folder)
        log.info("Relocated project id=%s to %s", project_id, folder)
        return self.get(project_id)

    def add_many(self, candidates: Iterable[FolderCandidate], status: str = "Active") -> ImportResult:
        """Add folders picked on the Import page. Already registered folders are skipped."""
        result = ImportResult()
        registered = self.registered_folders()
        for candidate in candidates:
            key = folder_key(candidate.path)
            if key in registered:
                result.skipped += 1
                continue
            try:
                self.create(Project(name=self.unique_name(candidate.name), folder_path=candidate.path,
                                    technology=candidate.technology, status=status))
                registered.add(key)
                result.added += 1
            except ValidationError as exc:
                result.errors.append(f"{candidate.name}: {exc.user_message}")
        return result

    # ------------------------------------------------------------------ JSON
    def export_json(self, path: Path | str) -> int:
        projects = self.list_projects(sort="name")
        payload = {
            "format": EXPORT_FORMAT,
            "version": EXPORT_VERSION,
            "exported_at": timeutil.now_str(),
            "projects": [p.to_dict() for p in projects],
        }
        target = Path(path)
        temp = target.with_name(target.name + ".tmp")
        try:
            temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            temp.replace(target)
        except OSError as exc:
            raise ImportExportError("The export file could not be written.", str(exc)) from exc
        log.info("Exported %d projects to %s", len(projects), target)
        return len(projects)

    @staticmethod
    def read_export(path: Path | str) -> list[dict]:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        except OSError as exc:
            raise ImportExportError("The file could not be read.", str(exc)) from exc
        except ValueError as exc:
            raise ImportExportError("This file is not valid JSON.", str(exc)) from exc
        if isinstance(data, dict):
            if data.get("format") not in (None, EXPORT_FORMAT):
                raise ImportExportError("This JSON file was not exported by DevDock.")
            items = data.get("projects")
        else:
            items = data
        if not isinstance(items, list):
            raise ImportExportError("The file does not contain a list of projects.")
        return items

    def import_projects(self, items: list, on_duplicate: str = "skip", lenient: bool = False) -> ImportResult:
        """on_duplicate: 'skip' keeps existing projects; 'rename' imports copies as 'Name (2)'.

        lenient=True (DevDock 1.x data) keeps rows with an empty folder or a malformed URL
        instead of rejecting them, so an upgrade never drops data.
        """
        result = ImportResult()
        existing = {(p.name.lower(), folder_key(p.folder_path)) for p in self.list_projects()}
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                result.errors.append(f"Entry {index}: not a project object")
                continue
            project = Project.from_dict(item)
            if not project.name or (not project.folder_path and not lenient):
                result.errors.append(f"Entry {index}: name and folder_path are required")
                continue
            if (project.name.lower(), folder_key(project.folder_path)) in existing:
                result.skipped += 1
                continue
            if self.name_taken(project.name):
                if on_duplicate != "rename":
                    result.skipped += 1
                    continue
                project.name = self.unique_name(project.name)
            try:
                self.create(project, require_existing_folder=False, lenient=lenient)
                existing.add((project.name.lower(), folder_key(project.folder_path)))
                result.added += 1
            except ValidationError as exc:
                result.errors.append(f"{project.name}: {exc.user_message}")
        log.info("Import finished: %s added, %s skipped, %s errors", result.added, result.skipped, len(result.errors))
        return result

    def import_json(self, path: Path | str, on_duplicate: str = "skip") -> ImportResult:
        return self.import_projects(self.read_export(path), on_duplicate)

    # ------------------------------------------------------------------ DevDock 1.x
    def merge_legacy_database(self, legacy_path: Path | str) -> ImportResult:
        """Copy projects and IDE paths from a DevDock 1.x database into this one.

        The legacy file is never modified: it is copied to a temp folder and migrated there.
        """
        result = ImportResult()
        with tempfile.TemporaryDirectory(prefix="devdock-legacy-") as tmp:
            copy = Path(tmp) / "legacy.db"
            shutil.copy2(legacy_path, copy)
            legacy = Database(copy, backup_dir=Path(tmp) / "backups").open()
            try:
                legacy.migrate()
                projects = ProjectService(legacy).list_projects(sort="newest")
                ide_rows = legacy.query("SELECT ide_key, exe_path FROM ide_paths")
            finally:
                legacy.close()
        items = [p.to_dict() for p in reversed(projects)]
        result = self.import_projects(items, on_duplicate="rename", lenient=True)
        with self.db.transaction() as conn:
            for row in ide_rows:
                conn.execute("INSERT OR IGNORE INTO ide_paths(ide_key, exe_path) VALUES(?,?)",
                             (row["ide_key"], row["exe_path"]))
        log.info("Merged legacy database %s: %s added, %s skipped", legacy_path, result.added, result.skipped)
        return result
