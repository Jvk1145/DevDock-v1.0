"""Services and shared state handed to the UI."""
from __future__ import annotations

from dataclasses import dataclass, field

from core.database import Database
from core.git_service import GitService
from core.ide_detector import IDEDetector
from core.launcher import Launcher
from core.project_service import ProjectService
from core.settings_service import SettingsService


@dataclass
class AppContext:
    db: Database
    projects: ProjectService
    settings: SettingsService
    ide_detector: IDEDetector
    launcher: Launcher
    git: GitService
    missing_ids: set[int] = field(default_factory=set)
    legacy_imported: int = 0

    @classmethod
    def create(cls, db: Database) -> "AppContext":
        return cls(db=db, projects=ProjectService(db), settings=SettingsService(db), ide_detector=IDEDetector(),
                   launcher=Launcher(), git=GitService())
