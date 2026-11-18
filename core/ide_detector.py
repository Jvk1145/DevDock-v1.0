"""Find installed IDEs for the current Windows user.

Lookup order for every IDE (first hit wins):
  1. user-configured path (Settings)
  2. %LOCALAPPDATA%\\Programs\\...      (current user only, never other profiles)
  3. Program Files / Program Files (x86)
  4. JetBrains Toolbox (%LOCALAPPDATA%\\JetBrains\\Toolbox\\apps\\...)
  5. PATH via shutil.which (code, cursor, idea64, pycharm64, studio64, subl, devenv, ...)
  6. Visual Studio via vswhere.exe
"""
from __future__ import annotations

import glob
import logging
import os
import re
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from core.models import IDE

log = logging.getLogger(__name__)

CREATE_NO_WINDOW = 0x08000000


@dataclass(frozen=True)
class IDEDefinition:
    key: str
    name: str
    exe: str                                  # real executable file name
    local: tuple[str, ...] = ()               # globs under %LOCALAPPDATA%\Programs
    program_files: tuple[str, ...] = ()       # globs under each Program Files folder
    toolbox: tuple[str, ...] = ()             # globs under %LOCALAPPDATA%\JetBrains\Toolbox
    commands: tuple[str, ...] = ()            # names looked up on PATH
    vswhere: bool = False
    require: tuple[str, ...] = ()             # path must contain one of these (lower-case)
    exclude: tuple[str, ...] = ()             # path must not contain any of these (lower-case)


DEFINITIONS: tuple[IDEDefinition, ...] = (
    IDEDefinition("vscode", "VS Code", "Code.exe",
                  local=("Microsoft VS Code/Code.exe",),
                  program_files=("Microsoft VS Code/Code.exe",),
                  commands=("code",)),
    IDEDefinition("cursor", "Cursor", "Cursor.exe",
                  local=("cursor/Cursor.exe",),
                  program_files=("Cursor/Cursor.exe",),
                  commands=("cursor",)),
    IDEDefinition("pycharm", "PyCharm", "pycharm64.exe",
                  local=("PyCharm*/bin/pycharm64.exe",),
                  program_files=("JetBrains/PyCharm*/bin/pycharm64.exe",),
                  toolbox=("apps/PyCharm-P/**/bin/pycharm64.exe", "apps/pycharm/**/bin/pycharm64.exe"),
                  commands=("pycharm64", "pycharm"),
                  exclude=("community", "pycharm-c")),
    IDEDefinition("pycharm_ce", "PyCharm Community", "pycharm64.exe",
                  local=("PyCharm Community*/bin/pycharm64.exe",),
                  program_files=("JetBrains/PyCharm Community*/bin/pycharm64.exe",),
                  toolbox=("apps/PyCharm-C/**/bin/pycharm64.exe",),
                  require=("community", "pycharm-c")),
    IDEDefinition("intellij", "IntelliJ IDEA", "idea64.exe",
                  local=("IntelliJ IDEA*/bin/idea64.exe",),
                  program_files=("JetBrains/IntelliJ IDEA*/bin/idea64.exe",),
                  toolbox=("apps/IDEA-U/**/bin/idea64.exe", "apps/IDEA-C/**/bin/idea64.exe",
                           "apps/intellij-idea*/**/bin/idea64.exe"),
                  commands=("idea64", "idea")),
    IDEDefinition("android_studio", "Android Studio", "studio64.exe",
                  local=("Android Studio/bin/studio64.exe",),
                  program_files=("Android/Android Studio/bin/studio64.exe",),
                  toolbox=("apps/AndroidStudio/**/bin/studio64.exe",),
                  commands=("studio64",)),
    IDEDefinition("visual_studio", "Visual Studio", "devenv.exe",
                  program_files=("Microsoft Visual Studio/*/*/Common7/IDE/devenv.exe",),
                  commands=("devenv",),
                  vswhere=True),
    IDEDefinition("sublime", "Sublime Text", "sublime_text.exe",
                  local=("Sublime Text/sublime_text.exe",),
                  program_files=("Sublime Text/sublime_text.exe", "Sublime Text 4/sublime_text.exe",
                                 "Sublime Text 3/sublime_text.exe"),
                  commands=("subl", "sublime_text")),
    IDEDefinition("notepadpp", "Notepad++", "notepad++.exe",
                  program_files=("Notepad++/notepad++.exe",),
                  commands=("notepad++",)),
)

_BY_KEY = {d.key: d for d in DEFINITIONS}


def definition(key: str) -> IDEDefinition | None:
    return _BY_KEY.get(key)


def ide_name(key: str | None) -> str:
    d = _BY_KEY.get(key or "")
    return d.name if d else (key or "")


def _natural_key(path: str) -> list:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path)]


def _is_file(path: str) -> bool:
    return os.path.isfile(path)


class IDEDetector:
    def __init__(self, env: Mapping[str, str] | None = None,
                 which: Callable[[str], str | None] = shutil.which,
                 run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
                 definitions: tuple[IDEDefinition, ...] = DEFINITIONS):
        self.env = os.environ if env is None else env
        self.which = which
        self.run = run
        self.definitions = definitions
        self._cache: dict[str, IDE] | None = None
        self._cache_key: frozenset | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ public
    @property
    def cached(self) -> dict[str, IDE] | None:
        return self._cache

    def invalidate(self) -> None:
        with self._lock:
            self._cache = None

    def detect(self, custom_paths: Mapping[str, str] | None = None, refresh: bool = False) -> dict[str, IDE]:
        """Return {ide_key: IDE} for every IDE found. Results are cached until refresh=True
        or the custom paths change."""
        custom_paths = dict(custom_paths or {})
        key = frozenset(custom_paths.items())
        with self._lock:
            if not refresh and self._cache is not None and self._cache_key == key:
                return dict(self._cache)
            found: dict[str, IDE] = {}
            for d in self.definitions:
                try:
                    ide = self._detect_one(d, custom_paths.get(d.key))
                except OSError:
                    log.exception("Detection failed for %s", d.name)
                    ide = None
                if ide:
                    found[d.key] = ide
            self._cache, self._cache_key = found, key
            log.info("Detected IDEs: %s", {k: v.path for k, v in found.items()})
            return dict(found)

    # ------------------------------------------------------------------ lookup steps
    def _accept(self, d: IDEDefinition, path: str) -> bool:
        lower = path.lower()
        if d.require and not any(r in lower for r in d.require):
            return False
        if any(x in lower for x in d.exclude):
            return False
        return _is_file(path)

    def _glob_first(self, d: IDEDefinition, base: str | None, patterns: tuple[str, ...]) -> str | None:
        if not base or not os.path.isdir(base):
            return None
        for pattern in patterns:
            matches = glob.glob(os.path.join(base, os.path.normpath(pattern)), recursive=True)
            matches = [os.path.normpath(m) for m in matches if self._accept(d, m)]
            if matches:
                return sorted(matches, key=_natural_key, reverse=True)[0]   # newest version first
        return None

    def _program_files_dirs(self) -> list[str]:
        dirs: list[str] = []
        for var in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
            value = self.env.get(var)
            if value and os.path.normcase(value) not in {os.path.normcase(x) for x in dirs}:
                dirs.append(value)
        return dirs

    def _from_path(self, d: IDEDefinition) -> str | None:
        for command in d.commands:
            try:
                found = self.which(command)
            except OSError:
                found = None
            if not found:
                continue
            found = os.path.normpath(found)
            if found.lower().endswith((".cmd", ".bat")):
                found = self._exe_from_shim(found, d.exe)
                if not found:
                    continue
            if self._accept(d, found):
                return found
        return None

    def _exe_from_shim(self, shim: str, exe: str) -> str | None:
        """PATH entries like ...\\VS Code\\bin\\code.cmd point at the real exe a few folders up."""
        folder = Path(shim).parent
        for _ in range(4):
            for candidate in (folder / exe,):
                if candidate.is_file():
                    return str(candidate)
            folder = folder.parent
        try:
            text = Path(shim).read_text(encoding="utf-8", errors="ignore")[:65536]
        except OSError:
            return None
        match = re.search(r'"?([A-Za-z]:\\[^"\r\n]*?' + re.escape(exe) + r')"?', text, re.IGNORECASE)
        if match and _is_file(match.group(1)):
            return os.path.normpath(match.group(1))
        return None

    def _from_vswhere(self) -> str | None:
        base = self.env.get("ProgramFiles(x86)") or self.env.get("ProgramFiles")
        if not base:
            return None
        vswhere = os.path.join(base, "Microsoft Visual Studio", "Installer", "vswhere.exe")
        if not _is_file(vswhere):
            return None
        try:
            result = self.run([vswhere, "-latest", "-products", "*", "-property", "productPath", "-utf8"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=5, creationflags=CREATE_NO_WINDOW)
        except (OSError, subprocess.SubprocessError):
            log.warning("vswhere failed", exc_info=True)
            return None
        for line in (result.stdout or "").splitlines():
            line = line.strip()
            if line.lower().endswith("devenv.exe") and _is_file(line):
                return os.path.normpath(line)
        return None

    def _detect_one(self, d: IDEDefinition, custom: str | None) -> IDE | None:
        if custom:
            path = os.path.normpath(custom)
            if _is_file(path):
                return IDE(d.key, d.name, path, "custom")
            log.warning("Configured path for %s does not exist: %s", d.name, path)
        local_app_data = self.env.get("LOCALAPPDATA")
        programs = os.path.join(local_app_data, "Programs") if local_app_data else None
        steps: list[tuple[str, Callable[[], str | None]]] = [
            ("local", lambda: self._glob_first(d, programs, d.local)),
            ("program_files", lambda: next(filter(None, (self._glob_first(d, base, d.program_files)
                                                          for base in self._program_files_dirs())), None)),
            ("toolbox", lambda: self._glob_first(
                d, os.path.join(local_app_data, "JetBrains", "Toolbox") if local_app_data else None, d.toolbox)),
            ("path", lambda: self._from_path(d)),
        ]
        if d.vswhere:
            steps.append(("vswhere", self._from_vswhere))
        for source, step in steps:
            path = step()
            if path:
                return IDE(d.key, d.name, path, source)
        return None
