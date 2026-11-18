"""Typed data models."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any, ClassVar

# Stored in projects.preferred_ide: always show the IDE chooser for this project.
ASK_EVERY_TIME = "__ask__"


@dataclass
class Project:
    name: str
    folder_path: str
    id: int | None = None
    description: str = ""
    technology: str = ""
    status: str = "Active"
    preferred_ide: str | None = None   # IDE key, ASK_EVERY_TIME, or None (= use default IDE)
    github_url: str = ""
    live_demo: str = ""
    start_command: str = ""
    tags: list[str] = field(default_factory=list)
    favorite: bool = False
    created_at: str | None = None
    updated_at: str | None = None
    last_opened: str | None = None

    EXPORT_FIELDS: ClassVar[tuple[str, ...]] = (
        "name", "folder_path", "description", "technology", "status", "preferred_ide",
        "github_url", "live_demo", "start_command", "tags", "favorite", "created_at", "last_opened")

    @classmethod
    def from_row(cls, row: sqlite3.Row, tags: list[str] | None = None) -> "Project":
        return cls(
            id=row["id"],
            name=row["name"] or "",
            folder_path=row["folder_path"] or "",
            description=row["description"] or "",
            technology=row["technology"] or "",
            status=row["status"] or "Active",
            preferred_ide=row["preferred_ide"] or None,
            github_url=row["github_url"] or "",
            live_demo=row["live_demo"] or "",
            start_command=row["start_command"] or "",
            tags=list(tags or []),
            favorite=bool(row["favorite"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_opened=row["last_opened"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.EXPORT_FIELDS}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Project":
        def text(key: str) -> str:
            value = data.get(key)
            return "" if value is None else str(value).strip()

        tags = data.get("tags") or []
        if isinstance(tags, str):
            tags = tags.split(",")
        if not isinstance(tags, (list, tuple)):
            tags = []
        return cls(
            name=text("name"),
            folder_path=text("folder_path"),
            description=text("description"),
            technology=text("technology"),
            status=text("status") or "Active",
            preferred_ide=text("preferred_ide") or None,
            github_url=text("github_url"),
            live_demo=text("live_demo"),
            start_command=text("start_command"),
            tags=[str(t).strip() for t in tags if str(t).strip()],
            favorite=bool(data.get("favorite")),
            created_at=text("created_at") or None,
            last_opened=text("last_opened") or None,
        )


@dataclass(frozen=True)
class IDE:
    """An IDE that was found on this machine."""
    key: str
    name: str
    path: str
    source: str  # custom | local | program_files | toolbox | path | vswhere

    SOURCE_LABELS: ClassVar[dict[str, str]] = {
        "custom": "Custom path",
        "local": "User install",
        "program_files": "Program Files",
        "toolbox": "JetBrains Toolbox",
        "path": "PATH",
        "vswhere": "Visual Studio Installer",
    }

    @property
    def source_label(self) -> str:
        return self.SOURCE_LABELS.get(self.source, self.source)


@dataclass(frozen=True)
class GitInfo:
    branch: str
    changes: int
    last_commit_at: str | None = None   # UTC timestamp string
    last_commit_message: str = ""


@dataclass(frozen=True)
class FolderCandidate:
    """A sub-folder found by the import scanner."""
    path: str
    name: str
    technology: str
    already_added: bool = False


@dataclass
class ImportResult:
    added: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
