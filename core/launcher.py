"""Open projects: IDE, Explorer, terminal, browser, start command.

Commands are always argument lists (never shell=True). GUI programs start detached so
DevDock stays responsive and does not keep child processes alive.
"""
from __future__ import annotations

import base64
import logging
import os
import shutil
import subprocess
import webbrowser
from dataclasses import dataclass, field
from typing import Callable, Mapping

from core.errors import LaunchError
from core.ide_detector import ide_name
from core.models import ASK_EVERY_TIME, IDE, Project
from core.validators import is_valid_url

log = logging.getLogger(__name__)

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NEW_CONSOLE = 0x00000010
GUI_FLAGS = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP


@dataclass(frozen=True)
class Command:
    args: list[str]
    cwd: str | None = None
    creationflags: int = GUI_FLAGS
    description: str = field(default="", compare=False)


# ---------------------------------------------------------------------- pure builders
def ide_command(ide: IDE, folder: str) -> Command:
    folder = os.path.normpath(folder)
    if ide.key == "notepadpp":
        args = [ide.path, "-openFoldersAsWorkspace", folder]
    else:
        args = [ide.path, folder]
    return Command(args, cwd=folder, description=f"{ide.name}: {folder}")


def ide_test_command(ide: IDE) -> Command:
    return Command([ide.path], cwd=os.path.dirname(ide.path) or None, description=f"Test {ide.name}")


def explorer_command(folder: str, env: Mapping[str, str] = os.environ) -> Command:
    windir = env.get("SystemRoot") or env.get("WINDIR") or r"C:\Windows"
    return Command([os.path.join(windir, "explorer.exe"), os.path.normpath(folder)],
                   description=f"Explorer: {folder}")


def _powershell(which: Callable[[str], str | None], env: Mapping[str, str]) -> str:
    found = which("powershell.exe") or which("powershell")
    if found:
        return found
    windir = env.get("SystemRoot") or r"C:\Windows"
    return os.path.join(windir, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")


def encode_powershell(script: str) -> str:
    """-EncodedCommand payload: base64 of UTF-16LE. Avoids every quoting problem."""
    return base64.b64encode(script.encode("utf-16-le")).decode("ascii")


def terminal_command(folder: str, which: Callable[[str], str | None] = shutil.which,
                     env: Mapping[str, str] = os.environ) -> Command:
    folder = os.path.normpath(folder)
    wt = which("wt.exe") or which("wt")
    if wt:
        return Command([wt, "-d", folder], cwd=folder, creationflags=GUI_FLAGS,
                       description=f"Windows Terminal: {folder}")
    return Command([_powershell(which, env), "-NoExit", "-NoLogo"], cwd=folder,
                   creationflags=CREATE_NEW_CONSOLE, description=f"PowerShell: {folder}")


def run_command(folder: str, start_command: str, which: Callable[[str], str | None] = shutil.which,
                env: Mapping[str, str] = os.environ) -> Command:
    """Run the project's start command in a new terminal window that stays open."""
    folder = os.path.normpath(folder)
    command = start_command.strip()
    shown = command.replace("'", "''")
    script = f"$Host.UI.RawUI.WindowTitle = 'DevDock: {shown}'; Write-Host '> {shown}' -ForegroundColor Cyan; {command}"
    ps_args = [_powershell(which, env), "-NoExit", "-NoLogo", "-EncodedCommand", encode_powershell(script)]
    wt = which("wt.exe") or which("wt")
    if wt:
        return Command([wt, "-d", folder, *ps_args], cwd=folder, creationflags=GUI_FLAGS,
                       description=f"Run '{command}' in {folder}")
    return Command(ps_args, cwd=folder, creationflags=CREATE_NEW_CONSOLE, description=f"Run '{command}' in {folder}")


def resolve_ide(project: Project, ides: Mapping[str, IDE], default_key: str | None) -> IDE | None:
    """Pick the IDE for a project. None means: ask the user.

    Order: project's preferred IDE -> default IDE from settings -> ask.
    A preferred IDE that is no longer installed raises LaunchError(kind=ide_missing).
    """
    preferred = project.preferred_ide
    if preferred == ASK_EVERY_TIME:
        return None
    if preferred:
        if preferred in ides:
            return ides[preferred]
        raise LaunchError(f"{ide_name(preferred) or preferred} was not found on this PC.",
                          kind=LaunchError.IDE_MISSING, ide_key=preferred)
    if default_key and default_key in ides:
        return ides[default_key]
    return None


# ---------------------------------------------------------------------- side effects
class Launcher:
    def __init__(self, popen: Callable[..., object] = subprocess.Popen,
                 which: Callable[[str], str | None] = shutil.which,
                 open_browser: Callable[[str], bool] = webbrowser.open,
                 env: Mapping[str, str] | None = None):
        self.popen = popen
        self.which = which
        self.open_browser = open_browser
        self.env = os.environ if env is None else env

    def _spawn(self, command: Command) -> None:
        log.info("Launching %s -> %s", command.description, command.args)
        try:
            self.popen(command.args, cwd=command.cwd, creationflags=command.creationflags,
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       close_fds=True)
        except FileNotFoundError as exc:
            log.warning("Launch failed (not found): %s", exc)
            raise LaunchError("The program could not be found.", LaunchError.IDE_MISSING, str(exc),
                              path=command.args[0]) from exc
        except OSError as exc:
            log.warning("Launch failed: %s", exc)
            raise LaunchError("Windows could not start the program.", LaunchError.FAILED, str(exc)) from exc

    @staticmethod
    def check_folder(folder: str) -> str:
        folder = os.path.normpath(folder) if folder else ""
        if not folder or not os.path.isdir(folder):
            raise LaunchError("The project folder no longer exists. It may have been moved or renamed.",
                              LaunchError.FOLDER_MISSING, path=folder)
        return folder

    @staticmethod
    def check_ide(ide: IDE) -> None:
        if not ide.path or not os.path.isfile(ide.path):
            raise LaunchError(f"{ide.name} was not found at {ide.path}.", LaunchError.IDE_MISSING,
                              ide_key=ide.key, path=ide.path)

    def open_in_ide(self, folder: str, ide: IDE) -> None:
        folder = self.check_folder(folder)
        self.check_ide(ide)
        self._spawn(ide_command(ide, folder))

    def test_ide(self, ide: IDE) -> None:
        self.check_ide(ide)
        self._spawn(ide_test_command(ide))

    def open_folder(self, folder: str) -> None:
        self._spawn(explorer_command(self.check_folder(folder), self.env))

    def open_terminal(self, folder: str) -> None:
        self._spawn(terminal_command(self.check_folder(folder), self.which, self.env))

    def run_start_command(self, folder: str, start_command: str) -> None:
        if not (start_command or "").strip():
            raise LaunchError("This project has no start command. Edit the project to add one.")
        self._spawn(run_command(self.check_folder(folder), start_command, self.which, self.env))

    def open_url(self, url: str) -> None:
        url = (url or "").strip()
        if not is_valid_url(url):
            raise LaunchError("This link is not a valid web address. Edit the project to fix it.")
        log.info("Opening URL %s", url)
        try:
            opened = self.open_browser(url)
        except Exception as exc:  # webbrowser can raise many platform errors
            raise LaunchError("Your web browser could not be opened.", detail=str(exc)) from exc
        if opened is False:
            raise LaunchError("Your web browser could not be opened.")
