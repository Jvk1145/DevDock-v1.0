"""Guess a project's technology from the files in its folder (top level only, fast)."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Iterable

from core.models import FolderCandidate

log = logging.getLogger(__name__)

TECHNOLOGIES = (
    "Python", "Django", "Flask", "FastAPI", "Streamlit", "Jupyter", "Machine Learning",
    "Node.js", "React", "Next.js", "Vue", "Java", "C#", "C++", "Flutter", "Power BI", "Other",
)

_SKIP_DIRS = {"node_modules", "venv", ".venv", "env", "__pycache__", "dist", "build", "$recycle.bin",
              "system volume information"}


def _read(path: Path, limit: int = 256_000) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            return handle.read(limit).lower()
    except OSError:
        return ""


def _python_framework(folder: Path, names: set[str]) -> str:
    if "manage.py" in names:
        return "Django"
    text = ""
    for file in ("requirements.txt", "pyproject.toml", "pipfile", "setup.py", "setup.cfg"):
        if file in names:
            text += _read(folder / _actual(folder, file)) + "\n"
    for package, label in (("streamlit", "Streamlit"), ("fastapi", "FastAPI"), ("flask", "Flask"),
                           ("django", "Django")):
        if package in text:
            return label
    return "Python"


def _node_framework(folder: Path, names: set[str]) -> str:
    try:
        data = json.loads(_read(folder / _actual(folder, "package.json")) or "{}")
    except ValueError:
        data = {}
    deps: dict = {}
    for section in ("dependencies", "devDependencies", "peerDependencies"):
        value = data.get(section.lower()) or data.get(section) or {}
        if isinstance(value, dict):
            deps.update(value)
    if "next" in deps:
        return "Next.js"
    if "react" in deps:
        return "React"
    if "vue" in deps or "nuxt" in deps:
        return "Vue"
    return "Node.js"


def _actual(folder: Path, lower_name: str) -> str:
    """Return the real file name for a lower-cased name (file systems keep case)."""
    try:
        for entry in os.scandir(folder):
            if entry.name.lower() == lower_name:
                return entry.name
    except OSError:
        pass
    return lower_name


def detect(folder: str | Path) -> str | None:
    """Return a technology label from TECHNOLOGIES, or None if nothing recognisable."""
    folder = Path(folder)
    try:
        entries = list(os.scandir(folder))
    except OSError:
        return None
    files = {e.name.lower() for e in entries if e.is_file()}
    suffixes = {os.path.splitext(name)[1] for name in files}

    if "pubspec.yaml" in files:
        return "Flutter"
    if files & {"requirements.txt", "pyproject.toml", "pipfile", "setup.py", "manage.py"}:
        return _python_framework(folder, files)
    if "package.json" in files:
        return _node_framework(folder, files)
    if files & {"pom.xml", "build.gradle", "build.gradle.kts"}:
        return "Java"
    if suffixes & {".csproj", ".sln"}:
        return "C#"
    if "cmakelists.txt" in files:
        return "C++"
    if ".pbix" in suffixes:
        return "Power BI"
    if ".ipynb" in suffixes:
        code_suffixes = {".py", ".js", ".ts", ".java", ".cs", ".cpp"}
        return "Jupyter" if not (suffixes & code_suffixes) else "Python"
    if ".py" in suffixes:
        return "Python"
    return None


def looks_like_project(folder: str | Path) -> tuple[bool, str]:
    tech = detect(folder)
    if tech:
        return True, tech
    has_git = os.path.isdir(os.path.join(folder, ".git"))
    return has_git, "Other" if has_git else ""


def scan_parent(parent: str | Path, registered: Iterable[str] = ()) -> list[FolderCandidate]:
    """List sub-folders of ``parent`` that look like projects. Touches disk: worker thread only."""
    from core.project_service import folder_key

    known = set(registered)
    candidates: list[FolderCandidate] = []
    try:
        entries = sorted(os.scandir(parent), key=lambda e: e.name.lower())
    except OSError as exc:
        log.warning("Could not scan %s: %s", parent, exc)
        return []
    for entry in entries:
        try:
            if not entry.is_dir() or entry.name.startswith((".", "__")) or entry.name.lower() in _SKIP_DIRS:
                continue
        except OSError:
            continue
        ok, tech = looks_like_project(entry.path)
        if ok:
            path = os.path.normpath(entry.path)
            candidates.append(FolderCandidate(path, entry.name, tech, folder_key(path) in known))
    return candidates
