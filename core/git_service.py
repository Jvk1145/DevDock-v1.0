"""Git status for project folders: branch, number of changed files, last commit.

git runs without a shell, with a timeout, in a thread pool. Missing git, a folder that is
not a repository, or a timeout all produce ``None`` instead of an exception.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Callable

from core import timeutil
from core.models import GitInfo

log = logging.getLogger(__name__)

CREATE_NO_WINDOW = 0x08000000


class GitService:
    def __init__(self, git_exe: str | None = None, timeout: float = 3, ttl: float = 60,
                 max_workers: int = 4, clock: Callable[[], float] = time.monotonic,
                 which: Callable[[str], str | None] = shutil.which):
        self.git = git_exe if git_exe is not None else which("git")
        self.timeout = timeout
        self.ttl = ttl
        self.clock = clock
        self._cache: dict[str, tuple[float, GitInfo | None]] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="git")

    @property
    def available(self) -> bool:
        return bool(self.git)

    # ------------------------------------------------------------------ cache
    def cached(self, folder: str) -> tuple[bool, GitInfo | None]:
        """(is_fresh, info). Never touches disk, safe for the UI thread."""
        key = os.path.normcase(os.path.normpath(folder or ""))
        with self._lock:
            entry = self._cache.get(key)
        if entry and self.clock() - entry[0] < self.ttl:
            return True, entry[1]
        return False, None

    def invalidate(self, folder: str | None = None) -> None:
        with self._lock:
            if folder is None:
                self._cache.clear()
            else:
                self._cache.pop(os.path.normcase(os.path.normpath(folder)), None)

    # ------------------------------------------------------------------ git calls
    def _git(self, folder: str, *args: str) -> str | None:
        env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0", LC_ALL="C")
        try:
            result = subprocess.run([self.git, "-C", folder, *args], capture_output=True, text=True,
                                    encoding="utf-8", errors="replace", timeout=self.timeout,
                                    stdin=subprocess.DEVNULL, env=env, creationflags=CREATE_NO_WINDOW)
        except subprocess.TimeoutExpired:
            log.info("git %s timed out in %s", args[0], folder)
            return None
        except OSError:
            log.warning("git could not be started", exc_info=True)
            return None
        return result.stdout if result.returncode == 0 else None

    def get_info(self, folder: str) -> GitInfo | None:
        """Blocking. Call from a worker thread (see ``submit``)."""
        fresh, info = self.cached(folder)
        if fresh:
            return info
        info = self._read(folder)
        with self._lock:
            self._cache[os.path.normcase(os.path.normpath(folder or ""))] = (self.clock(), info)
        return info

    def _read(self, folder: str) -> GitInfo | None:
        if not self.git or not folder or not os.path.isdir(folder):
            return None
        status = self._git(folder, "status", "--porcelain=v2", "--branch", "--untracked-files=normal")
        if status is None:
            return None
        branch, changes = "", 0
        for line in status.splitlines():
            if line.startswith("# branch.head "):
                branch = line[len("# branch.head "):].strip()
            elif line and not line.startswith("#"):
                changes += 1
        if branch == "(detached)":
            branch = "detached"
        last_at, message = None, ""
        log_out = self._git(folder, "log", "-1", "--format=%ct%x1f%s")
        if log_out and "\x1f" in log_out:
            stamp, message = log_out.strip().split("\x1f", 1)
            try:
                last_at = datetime.fromtimestamp(int(stamp), tz=timezone.utc).strftime(timeutil.FORMAT)
            except ValueError:
                last_at = None
        return GitInfo(branch=branch or "unknown", changes=changes, last_commit_at=last_at,
                       last_commit_message=message.strip())

    def submit(self, folder: str) -> Future:
        return self._executor.submit(self.get_info, folder)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
