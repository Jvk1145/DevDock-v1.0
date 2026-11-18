"""User settings stored in the database (settings + ide_paths tables)."""
from __future__ import annotations

import json
import logging
from typing import Any

from core.database import Database
from core.validators import STATUSES, normalize_path

log = logging.getLogger(__name__)

THEMES = ("dark", "light", "system")
VIEW_MODES = ("grid", "list")
SORTS = ("recent", "name", "newest")

DEFAULTS: dict[str, Any] = {
    "theme": "dark",
    "accent": "Indigo",
    "default_ide": None,          # IDE key or None (= ask)
    "default_status": "Active",
    "window_geometry": None,      # "WxH+X+Y" in logical pixels
    "window_maximized": False,
    "sidebar_collapsed": False,
    "view_mode": "grid",
    "sort": "recent",
}


class SettingsService:
    def __init__(self, db: Database):
        self.db = db

    # ------------------------------------------------------------------ generic
    def get(self, key: str, default: Any = None) -> Any:
        fallback = DEFAULTS.get(key, default)
        row = self.db.query_one("SELECT value FROM settings WHERE key=?", (key,))
        if row is None:
            return fallback
        try:
            return json.loads(row["value"])
        except (TypeError, ValueError):
            log.warning("Ignoring unreadable setting %r", key)
            return fallback

    def set(self, key: str, value: Any) -> None:
        self.db.execute("INSERT INTO settings(key, value) VALUES(?, ?) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (key, json.dumps(value)))

    def set_many(self, values: dict[str, Any]) -> None:
        with self.db.transaction() as conn:
            for key, value in values.items():
                conn.execute("INSERT INTO settings(key, value) VALUES(?, ?) "
                             "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                             (key, json.dumps(value)))

    # ------------------------------------------------------------------ typed accessors
    @property
    def theme(self) -> str:
        value = self.get("theme")
        return value if value in THEMES else "dark"

    @theme.setter
    def theme(self, value: str) -> None:
        if value not in THEMES:
            raise ValueError(f"Unknown theme {value!r}")
        self.set("theme", value)

    @property
    def accent(self) -> str:
        return str(self.get("accent") or "Indigo")

    @accent.setter
    def accent(self, value: str) -> None:
        self.set("accent", value)

    @property
    def default_ide(self) -> str | None:
        return self.get("default_ide") or None

    @default_ide.setter
    def default_ide(self, key: str | None) -> None:
        self.set("default_ide", key or None)

    @property
    def default_status(self) -> str:
        value = self.get("default_status")
        return value if value in STATUSES else "Active"

    @default_status.setter
    def default_status(self, value: str) -> None:
        if value not in STATUSES:
            raise ValueError(f"Unknown status {value!r}")
        self.set("default_status", value)

    @property
    def view_mode(self) -> str:
        value = self.get("view_mode")
        return value if value in VIEW_MODES else "grid"

    @view_mode.setter
    def view_mode(self, value: str) -> None:
        self.set("view_mode", value if value in VIEW_MODES else "grid")

    @property
    def sort(self) -> str:
        value = self.get("sort")
        return value if value in SORTS else "recent"

    @sort.setter
    def sort(self, value: str) -> None:
        self.set("sort", value if value in SORTS else "recent")

    # ------------------------------------------------------------------ IDE paths
    def ide_paths(self) -> dict[str, str]:
        return {row["ide_key"]: row["exe_path"] for row in self.db.query("SELECT ide_key, exe_path FROM ide_paths")}

    def set_ide_path(self, ide_key: str, exe_path: str | None) -> None:
        path = normalize_path(exe_path)
        if path:
            self.db.execute("INSERT INTO ide_paths(ide_key, exe_path) VALUES(?, ?) "
                            "ON CONFLICT(ide_key) DO UPDATE SET exe_path=excluded.exe_path", (ide_key, path))
        else:
            self.db.execute("DELETE FROM ide_paths WHERE ide_key=?", (ide_key,))
