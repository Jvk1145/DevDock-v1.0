"""Form validation rules shared by the UI (inline messages) and services (hard checks)."""
from __future__ import annotations

import os
from typing import Callable
from urllib.parse import urlparse

from core.models import Project

STATUSES = ("Active", "Completed", "On Hold")

MAX_NAME = 80
MAX_DESCRIPTION = 2000
MAX_TECHNOLOGY = 40
MAX_COMMAND = 500
MAX_URL = 500
MAX_TAGS = 10
MAX_TAG_LENGTH = 30


def normalize_path(path: str | None) -> str:
    """Expand ~ and %VARS%, normalize separators. Returns '' for empty input."""
    text = (path or "").strip().strip('"').strip()
    if not text:
        return ""
    return os.path.normpath(os.path.expandvars(os.path.expanduser(text)))


def parse_tags(text: str | list[str] | None) -> list[str]:
    """Split comma separated tags, trim, drop empties and case-insensitive duplicates."""
    if text is None:
        return []
    parts = text if isinstance(text, list) else str(text).split(",")
    seen: set[str] = set()
    tags: list[str] = []
    for part in parts:
        tag = " ".join(str(part).split())
        if tag and tag.lower() not in seen:
            seen.add(tag.lower())
            tags.append(tag)
    return tags


def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False
    host = parsed.hostname or ""
    return (parsed.scheme in ("http", "https") and bool(host)
            and ("." in host or host == "localhost") and " " not in url.strip())


def validate_name(name: str, name_taken: Callable[[str], bool] | None = None) -> str | None:
    name = (name or "").strip()
    if not name:
        return "Project name is required."
    if len(name) > MAX_NAME:
        return f"Keep the name under {MAX_NAME} characters."
    if name_taken and name_taken(name):
        return "A project with this name already exists."
    return None


def validate_folder(folder: str, must_exist: bool = True) -> str | None:
    folder = normalize_path(folder)
    if not folder:
        return "Choose the project folder."
    if not os.path.isabs(folder):
        return "Use a full folder path, for example C:\\Projects\\MyApp."
    if must_exist and not os.path.isdir(folder):
        return "This folder does not exist."
    return None


def validate_url(url: str) -> str | None:
    url = (url or "").strip()
    if not url:
        return None
    if len(url) > MAX_URL:
        return "This URL is too long."
    if not is_valid_url(url):
        return "Enter a full URL starting with https://"
    return None


def validate_tags(tags: list[str]) -> str | None:
    if len(tags) > MAX_TAGS:
        return f"Use at most {MAX_TAGS} tags."
    for tag in tags:
        if len(tag) > MAX_TAG_LENGTH:
            return f"Tags must be under {MAX_TAG_LENGTH} characters."
    return None


def validate_project(project: Project, name_taken: Callable[[str], bool] | None = None,
                     require_existing_folder: bool = True) -> dict[str, str]:
    """Return {field: message}. An empty dict means the project is valid."""
    errors: dict[str, str] = {}

    def check(field: str, message: str | None) -> None:
        if message:
            errors[field] = message

    check("name", validate_name(project.name, name_taken))
    check("folder_path", validate_folder(project.folder_path, require_existing_folder))
    check("github_url", validate_url(project.github_url))
    check("live_demo", validate_url(project.live_demo))
    check("tags", validate_tags(project.tags))
    if len(project.description or "") > MAX_DESCRIPTION:
        errors["description"] = f"Keep the description under {MAX_DESCRIPTION} characters."
    if len(project.technology or "") > MAX_TECHNOLOGY:
        errors["technology"] = f"Keep the technology under {MAX_TECHNOLOGY} characters."
    if project.status not in STATUSES:
        errors["status"] = "Choose Active, Completed or On Hold."
    if len(project.start_command or "") > MAX_COMMAND:
        errors["start_command"] = "The start command is too long."
    elif "\n" in (project.start_command or ""):
        errors["start_command"] = "The start command must be a single line."
    return errors
