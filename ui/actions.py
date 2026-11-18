"""Project actions shared by the Dashboard and Projects pages (launch, open, edit, delete...).

Talks to core services only and turns every LaunchError into a friendly modal with a fix.
"""
from __future__ import annotations

import logging
import os
from tkinter import filedialog
from typing import TYPE_CHECKING

from core.errors import DevDockError, LaunchError, NotFoundError
from core.ide_detector import definition, ide_name
from core.launcher import resolve_ide
from core.models import IDE, Project
from ui.widgets.dialogs import IDEChooserDialog, MessageDialog, confirm

if TYPE_CHECKING:
    from ui.main_window import MainWindow

log = logging.getLogger(__name__)


class ProjectActions:
    def __init__(self, window: "MainWindow"):
        self.window = window
        self.ctx = window.ctx

    def _toast(self, message: str, kind: str = "success") -> None:
        self.window.toasts.show(message, kind)

    def _fresh(self, project: Project) -> Project | None:
        try:
            return self.ctx.projects.get(project.id)
        except NotFoundError:
            self._toast("That project no longer exists.", "error")
            self.window.notify_data_changed()
            return None

    # ------------------------------------------------------------------ launch
    def launch(self, project: Project) -> None:
        project = self._fresh(project)
        if project is None:
            return
        if project.id in self.ctx.missing_ids or not project.folder_path:
            self.handle_error(project, LaunchError("The project folder no longer exists.",
                                                   LaunchError.FOLDER_MISSING, path=project.folder_path))
            return
        self.window.ensure_ides(lambda ides: self._launch_with(project, ides))

    def _launch_with(self, project: Project, ides: dict[str, IDE]) -> None:
        try:
            ide = resolve_ide(project, ides, self.ctx.settings.default_ide)
        except LaunchError as exc:
            self.handle_error(project, exc)
            return
        if ide is None:
            ide = self.choose_ide(project, ides)
            if ide is None:
                return
        self._open(project, ide)

    def choose_ide(self, project: Project, ides: dict[str, IDE]) -> IDE | None:
        if not ides:
            choice = MessageDialog(
                self.window, "No IDE found",
                "DevDock could not find a supported IDE. Add the path to your IDE in Settings.",
                "warning", (("Open Settings", "settings", "primary"), ("Close", None, "secondary"))).show()
            if choice == "settings":
                self.window.navigate("settings")
            return None
        result = IDEChooserDialog(self.window, ides, project.name, self.ctx.settings.default_ide).show()
        if not result:
            return None
        key, remember = result
        if remember:
            self.ctx.projects.set_preferred_ide(project.id, key)
            self.window.notify_data_changed()
        return ides[key]

    def _open(self, project: Project, ide: IDE) -> None:
        try:
            self.ctx.launcher.open_in_ide(project.folder_path, ide)
        except LaunchError as exc:
            self.handle_error(project, exc)
            return
        self.ctx.projects.mark_opened(project.id)
        self._toast(f"Opening {project.name} in {ide.name}")
        self.window.notify_data_changed()

    # ------------------------------------------------------------------ error handling
    def handle_error(self, project: Project, exc: LaunchError) -> None:
        log.info("Launch problem for %r: %s (%s)", project.name, exc.user_message, exc.kind)
        if exc.kind == LaunchError.FOLDER_MISSING:
            choice = MessageDialog(
                self.window, "Folder not found",
                f"“{project.name}” points to a folder that no longer exists:\n{project.folder_path or '(no folder)'}",
                "warning", (("Locate folder", "locate", "primary"), ("Cancel", None, "secondary"))).show()
            if choice == "locate":
                self.relocate(project)
        elif exc.kind == LaunchError.IDE_MISSING:
            name = ide_name(exc.ide_key) if exc.ide_key else "The IDE"
            choice = MessageDialog(
                self.window, f"{name} not found",
                f"{exc.user_message}\nPoint DevDock to its .exe file, or pick another IDE.",
                "warning", (("Fix IDE path", "fix", "primary"), ("Choose another IDE", "choose", "secondary"),
                            ("Cancel", None, "ghost"))).show()
            if choice == "fix":
                self.fix_ide_path(project, exc.ide_key)
            elif choice == "choose":
                self.ctx.projects.set_preferred_ide(project.id, None)
                self.window.ensure_ides(lambda ides: self._choose_then_open(project, ides))
        else:
            MessageDialog(self.window, "Could not open", exc.user_message, "error",
                          detail=exc.detail if exc.detail != exc.user_message else None).show()

    def _choose_then_open(self, project: Project, ides: dict[str, IDE]) -> None:
        fresh = self._fresh(project)
        if fresh is None:
            return
        ide = self.choose_ide(fresh, ides)
        if ide:
            self._open(fresh, ide)

    def fix_ide_path(self, project: Project | None, ide_key: str | None) -> None:
        if not ide_key:
            self.window.navigate("settings")
            return
        d = definition(ide_key)
        title = f"Locate {d.name if d else ide_key}"
        exe = d.exe if d else "*.exe"
        path = filedialog.askopenfilename(parent=self.window, title=title,
                                          filetypes=[(f"{d.name if d else 'IDE'} ({exe})", exe),
                                                     ("Programs", "*.exe")])
        if not path:
            return
        self.ctx.settings.set_ide_path(ide_key, path)
        self._toast(f"Saved path for {d.name if d else ide_key}")

        def retry(ides: dict[str, IDE]) -> None:
            self.window.notify_settings_changed()
            if project is not None:
                fresh = self._fresh(project)
                if fresh is not None:
                    self._launch_with(fresh, ides)

        self.window.ensure_ides(retry, refresh=True)

    # ------------------------------------------------------------------ other actions
    def _guard(self, project: Project, action) -> None:
        try:
            action()
        except LaunchError as exc:
            self.handle_error(project, exc)

    def open_folder(self, project: Project) -> None:
        self._guard(project, lambda: self.ctx.launcher.open_folder(project.folder_path))

    def open_terminal(self, project: Project) -> None:
        self._guard(project, lambda: self.ctx.launcher.open_terminal(project.folder_path))

    def open_github(self, project: Project) -> None:
        self._guard(project, lambda: self.ctx.launcher.open_url(project.github_url))

    def run(self, project: Project) -> None:
        def go() -> None:
            self.ctx.launcher.run_start_command(project.folder_path, project.start_command)
            self._toast(f"Running “{project.start_command}”", "info")
        self._guard(project, go)

    def edit(self, project: Project) -> None:
        self.window.navigate("form", project_id=project.id)

    def delete(self, project: Project) -> bool:
        if not confirm(self.window, f"Delete “{project.name}”?",
                       "The project is removed from DevDock. Your files on disk are not touched.", "Delete project"):
            return False
        try:
            self.ctx.projects.delete(project.id)
        except DevDockError as exc:
            self._toast(exc.user_message, "error")
            return False
        self.ctx.git.invalidate(project.folder_path)
        self.ctx.missing_ids.discard(project.id)
        self._toast(f"Deleted {project.name}")
        self.window.notify_data_changed()
        return True

    def toggle_favorite(self, project: Project) -> None:
        try:
            pinned = self.ctx.projects.toggle_favorite(project.id)
        except DevDockError as exc:
            self._toast(exc.user_message, "error")
            return
        self._toast(f"Pinned {project.name}" if pinned else f"Unpinned {project.name}", "info")
        self.window.notify_data_changed()

    def relocate(self, project: Project) -> None:
        start = project.folder_path
        while start and not os.path.isdir(start):
            parent = os.path.dirname(start)
            start = "" if parent == start else parent
        folder = filedialog.askdirectory(parent=self.window, title=f"Locate the folder for {project.name}",
                                         initialdir=start or os.path.expanduser("~"), mustexist=True)
        if not folder:
            return
        try:
            self.ctx.projects.relocate(project.id, folder)
        except DevDockError as exc:
            self._toast(exc.user_message, "error")
            return
        self.ctx.missing_ids.discard(project.id)
        self.ctx.git.invalidate()
        self._toast(f"Updated folder for {project.name}")
        self.window.notify_data_changed()
        self.window.refresh_missing()
