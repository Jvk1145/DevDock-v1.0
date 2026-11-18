r"""Application constants, version and filesystem locations.

All user data lives in %APPDATA%\DevDock (database, logs, backups, lock files).
Set the DEVDOCK_HOME environment variable to use a different data folder
(used by tests and for portable installs).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "DevDock"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "A developer project launcher: keep every project one click away from the right IDE."
APP_USER_MODEL_ID = "DevDock.ProjectLauncher"
GITHUB_REPO_URL = "https://github.com/Jvk1145/DevDock"


def _default_app_dir() -> Path:
    override = os.environ.get("DEVDOCK_HOME")
    if override:
        return Path(override).expanduser().resolve()
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / APP_NAME


def _resource_dir() -> Path:
    """Folder that holds bundled read-only resources (assets)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


# ---------------------------------------------------------------- paths
APP_DIR: Path = _default_app_dir()
DB_PATH: Path = APP_DIR / "devdock.db"
LOG_DIR: Path = APP_DIR / "logs"
LOG_FILE: Path = LOG_DIR / "devdock.log"
BACKUP_DIR: Path = APP_DIR / "backups"
INSTANCE_FILE: Path = APP_DIR / "instance.json"

RESOURCE_DIR: Path = _resource_dir()
ASSETS_DIR: Path = RESOURCE_DIR / "assets"
ICONS_DIR: Path = ASSETS_DIR / "icons"
APP_ICON: Path = ASSETS_DIR / "app.ico"

# Where DevDock 1.x kept its database (relative to the working directory or exe).
PROGRAM_DIR: Path = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


def legacy_db_candidates() -> list[Path]:
    """Database files written by DevDock 1.x, which used a relative 'devdock.db'."""
    seen: list[Path] = []
    for folder in (Path.cwd(), PROGRAM_DIR, PROGRAM_DIR / "dist"):
        candidate = (folder / "devdock.db").resolve()
        if candidate.is_file() and candidate not in seen and candidate != DB_PATH.resolve():
            seen.append(candidate)
    return seen


def ensure_dirs() -> None:
    for folder in (APP_DIR, LOG_DIR, BACKUP_DIR):
        folder.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------- window
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 800
MIN_WIDTH = 1000
MIN_HEIGHT = 650

# ---------------------------------------------------------------- behaviour
STATUSES = ("Active", "Completed", "On Hold")
DEFAULT_STATUS = "Active"
BACKUPS_TO_KEEP = 7
GIT_TIMEOUT_SECONDS = 3
GIT_CACHE_SECONDS = 60
SEARCH_DEBOUNCE_MS = 200
TOAST_MS = 3000
RECENT_LIMIT = 6
LOG_MAX_BYTES = 1_000_000
LOG_BACKUP_COUNT = 5
