"""Main window: sidebar + top bar + page container, page router, shortcuts, window state."""
from __future__ import annotations

import logging
import re
import sys
import tkinter as tk
from typing import Callable

import customtkinter as ctk

import config
from core.ide_detector import ide_name
from core.models import ASK_EVERY_TIME, IDE, Project
from core.project_service import ProjectService
from ui import icons, theme
from ui.actions import ProjectActions
from ui.async_runner import TaskRunner
from ui.context import AppContext
from ui.pages.about import AboutPage
from ui.pages.base import Page
from ui.pages.dashboard import DashboardPage
from ui.pages.import_projects import ImportPage
from ui.pages.project_form import ProjectFormPage
from ui.pages.projects import ProjectsPage
from ui.pages.settings import SettingsPage
from ui.widgets import Sidebar, ToastManager, TopBar

log = logging.getLogger(__name__)

# key, label, icon, shortcut, page class
PAGES: list[tuple[str, str, str, str, type[Page]]] = [
    ("dashboard", "Dashboard", "dashboard", "Ctrl+1", DashboardPage),
    ("projects", "Projects", "projects", "Ctrl+2", ProjectsPage),
    ("form", "Add Project", "add", "Ctrl+3", ProjectFormPage),
    ("import", "Import", "import", "Ctrl+4", ImportPage),
    ("settings", "Settings", "settings", "Ctrl+5", SettingsPage),
    ("about", "About", "about", "Ctrl+6", AboutPage),
]
_PAGE_CLASSES = {key: cls for key, _l, _i, _s, cls in PAGES}
_GEOMETRY_RE = re.compile(r"^(\d+)x(\d+)\+(-?\d+)\+(-?\d+)$")


def _virtual_screen(window: tk.Misc) -> tuple[int, int, int, int]:
    """(x, y, width, height) of the whole desktop across monitors, in physical pixels."""
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            return (user32.GetSystemMetrics(76), user32.GetSystemMetrics(77),
                    user32.GetSystemMetrics(78), user32.GetSystemMetrics(79))
        except (OSError, AttributeError):
            pass
    return 0, 0, window.winfo_screenwidth(), window.winfo_screenheight()


class MainWindow(ctk.CTk):
    def __init__(self, ctx: AppContext):
        theme.set_accent(ctx.settings.accent)
        theme.apply_mode(ctx.settings.theme)
        theme.apply_ctk_theme()
        super().__init__(fg_color=theme.c("bg"))
        # Do not withdraw() here: CustomTkinter skips its own deiconify in mainloop() if the
        # window was withdrawn before it existed, which would leave DevDock invisible.
        self.ctx = ctx
        self.title(config.APP_NAME)
        if config.APP_ICON.is_file():
            try:
                self.iconbitmap(default=str(config.APP_ICON))
            except tk.TclError:
                log.warning("Window icon could not be set")
        self.runner = TaskRunner(self)
        self.toasts = ToastManager(self)
        self.actions = ProjectActions(self)
        self.pages: dict[str, Page] = {}
        self.current: Page | None = None
        self.current_key = ""
        self.previous_key = "dashboard"
        self._normal_geometry: str | None = None
        self._default_ide = ctx.settings.default_ide

        self._build_chrome()
        self._restore_geometry()
        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<Configure>", self._on_configure, add="+")
        self.navigate("dashboard")
        self.after(150, self._startup_tasks)

    # ------------------------------------------------------------------ layout
    def _build_chrome(self) -> None:
        nav = [(key, label, icon, shortcut) for key, label, icon, shortcut, _cls in PAGES]
        self.sidebar = Sidebar(self, nav, self._on_nav_click, self._on_sidebar_toggle,
                               collapsed=bool(self.ctx.settings.get("sidebar_collapsed")))
        self.sidebar.pack(side="left", fill="y")
        self.main = ctk.CTkFrame(self, fg_color=theme.c("bg"), corner_radius=0)
        self.main.pack(side="left", fill="both", expand=True)
        self.topbar = TopBar(self.main, self.on_global_search, lambda: self.navigate("form"))
        self.topbar.pack(fill="x")
        self.container = ctk.CTkFrame(self.main, fg_color=theme.c("bg"), corner_radius=0)
        self.container.pack(fill="both", expand=True)

    def rebuild(self) -> None:
        """Recreate every widget (used after the accent colour changes)."""
        key = self.current_key or "dashboard"
        theme.set_accent(self.ctx.settings.accent)
        theme.apply_ctk_theme()
        icons.clear_cache()
        for page in self.pages.values():
            page.destroy()
        self.pages.clear()
        self.current = None
        self.sidebar.destroy()
        self.main.destroy()
        self.configure(fg_color=theme.c("bg"))
        self._build_chrome()
        self.navigate(key)

    # ------------------------------------------------------------------ routing
    def _on_nav_click(self, key: str) -> None:
        self.navigate(key)

    def _on_sidebar_toggle(self, collapsed: bool) -> None:
        self.ctx.settings.set("sidebar_collapsed", collapsed)

    def page(self, key: str) -> Page:
        if key not in self.pages:
            self.pages[key] = _PAGE_CLASSES[key](self.container, self)
        return self.pages[key]

    def navigate(self, key: str, **kwargs) -> None:
        if key not in _PAGE_CLASSES:
            key = "dashboard"
        page = self.page(key)
        if self.current is not None and self.current is not page:
            self.current.on_hide()
            self.current.pack_forget()
            self.previous_key = self.current_key
        self.current, self.current_key = page, key
        page.pack(fill="both", expand=True)
        page.on_show(**kwargs)
        self.sidebar.set_active(page.nav_key or key)
        self.update_title()
        self.toasts.lift_all()

    def back(self) -> None:
        target = self.previous_key if self.previous_key and self.previous_key != self.current_key else "projects"
        self.navigate(target)

    def update_title(self) -> None:
        if self.current is not None:
            self.topbar.set_title(self.current.title, self.current.subtitle)
            self.title(f"{self.current.title} · {config.APP_NAME}" if self.current.title else config.APP_NAME)

    def on_global_search(self, text: str) -> None:
        if self.current_key == "projects":
            self.current.on_search(text)
        elif text:
            self.navigate("projects", search=text)

    # ------------------------------------------------------------------ shared state
    def notify_data_changed(self) -> None:
        """Projects changed: mark every page stale and refresh the visible one."""
        for page in self.pages.values():
            page.dirty = True
        if self.current is not None:
            self.current.on_data_changed()

    def notify_settings_changed(self) -> None:
        self._default_ide = self.ctx.settings.default_ide
        self.notify_data_changed()

    def refresh_missing(self, then: Callable[[], None] | None = None) -> None:
        """Check every project folder in a worker thread; update badges when done."""
        projects = self.ctx.projects.list_projects()

        def done(missing: set[int]) -> None:
            changed = missing != self.ctx.missing_ids
            self.ctx.missing_ids = missing
            if changed:
                self.notify_data_changed()
            if then:
                then()

        self.runner.submit(ProjectService.find_missing, projects, on_success=done)

    def ensure_ides(self, callback: Callable[[dict[str, IDE]], None] | None = None, refresh: bool = False) -> None:
        """Detect IDEs in a worker thread (cached), then call ``callback`` on the UI thread."""
        paths = self.ctx.settings.ide_paths()

        def done(ides: dict[str, IDE]) -> None:
            if callback:
                callback(ides)

        self.runner.submit(self.ctx.ide_detector.detect, paths, refresh, on_success=done)

    def ide_label_for(self, project: Project) -> str:
        key = project.preferred_ide
        if key == ASK_EVERY_TIME:
            return "Open…"
        key = key or self._default_ide
        return f"Open in {ide_name(key)}" if key else "Open"

    def _startup_tasks(self) -> None:
        self.ensure_ides()
        self.refresh_missing()
        if self.ctx.legacy_imported:
            self.toasts.show(f"Imported {self.ctx.legacy_imported} project(s) from your previous DevDock data", "info")

    # ------------------------------------------------------------------ keyboard
    def _typing(self) -> bool:
        try:
            widget = self.focus_get()
        except (KeyError, tk.TclError):
            return False
        return widget is not None and widget.winfo_class() in ("Entry", "Text", "TEntry", "Spinbox")

    def _bind_shortcuts(self) -> None:
        def bind(sequences: tuple[str, ...], fn: Callable[[], object], when_typing: bool = True) -> None:
            def handler(_event):
                if not when_typing and self._typing():
                    return None
                fn()
                return "break"
            for seq in sequences:
                self.bind(seq, handler)

        bind(("<Control-n>", "<Control-N>"), lambda: self.navigate("form"))
        bind(("<Control-f>", "<Control-F>"), lambda: self.topbar.search.focus())
        for index, (key, *_rest) in enumerate(PAGES, start=1):
            bind((f"<Control-Key-{index}>",), lambda k=key: self.navigate(k))
        bind(("<Control-s>", "<Control-S>"), lambda: self._page_key("save"))
        bind(("<F5>",), self.refresh_all)
        self.bind("<Escape>", lambda _e: "break" if self._page_key("escape") else None)
        for seq, action in (("<Return>", "enter"), ("<KP_Enter>", "enter"), ("<Delete>", "delete"),
                            ("<Up>", "up"), ("<Down>", "down"), ("<Left>", "left"), ("<Right>", "right")):
            self.bind(seq, lambda _e, a=action: None if self._typing() else ("break" if self._page_key(a) else None))

    def _page_key(self, action: str) -> bool:
        return bool(self.current and self.current.handle_key(action))

    def refresh_all(self) -> None:
        self.ctx.git.invalidate()
        self.refresh_missing()
        self.notify_data_changed()
        self.toasts.show("Refreshed", "info")

    # ------------------------------------------------------------------ window state
    def _restore_geometry(self) -> None:
        scale = ctk.ScalingTracker.get_window_scaling(self) or 1.0
        screen_w = self.winfo_screenwidth() / scale
        screen_h = self.winfo_screenheight() / scale
        min_w = int(min(config.MIN_WIDTH, screen_w * 0.95))
        min_h = int(min(config.MIN_HEIGHT, screen_h * 0.9))
        self.minsize(min_w, min_h)
        width, height, x, y = config.DEFAULT_WIDTH, config.DEFAULT_HEIGHT, None, None
        match = _GEOMETRY_RE.match(str(self.ctx.settings.get("window_geometry") or ""))
        if match:
            width, height, x, y = (int(v) for v in match.groups())
        width = int(max(min_w, min(width, screen_w * 0.95)))
        height = int(max(min_h, min(height, screen_h * 0.9)))
        vx, vy, vw, vh = _virtual_screen(self)
        pw, ph = int(width * scale), int(height * scale)
        visible = x is not None and (x + pw > vx + 120 and x < vx + vw - 120 and y >= vy - 10 and y < vy + vh - 80)
        if not visible:
            x = (self.winfo_screenwidth() - pw) // 2
            y = max(0, (self.winfo_screenheight() - ph) // 2 - 20)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self._normal_geometry = f"{width}x{height}+{x}+{y}"
        if self.ctx.settings.get("window_maximized"):
            self.after(30, lambda: self.state("zoomed"))

    def _on_configure(self, event) -> None:
        if event.widget is self and self.state() == "normal":
            geometry = self.geometry()
            if _GEOMETRY_RE.match(geometry):
                self._normal_geometry = geometry

    def save_window_state(self) -> None:
        try:
            self.ctx.settings.set_many({"window_geometry": self._normal_geometry,
                                        "window_maximized": self.state() == "zoomed"})
        except Exception:
            log.exception("Could not save the window state")

    def bring_to_front(self) -> None:
        try:
            if self.state() in ("iconic", "withdrawn"):
                self.deiconify()
            self.lift()
            self.attributes("-topmost", True)
            self.after(200, lambda: self.attributes("-topmost", False))
            self.focus_force()
        except tk.TclError:
            log.exception("Could not bring the window to the front")

    def on_close(self) -> None:
        self.save_window_state()
        self.runner.shutdown()
        self.ctx.git.shutdown()
        self.destroy()
