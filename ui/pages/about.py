"""About page: version, description, keyboard shortcuts, data locations."""
from __future__ import annotations

import platform

import customtkinter as ctk

import config
from core.errors import LaunchError
from ui import icons, theme
from ui.pages.base import Page
from ui.widgets import controls
from ui.widgets.dialogs import info

SHORTCUTS = [
    ("Ctrl+N", "New project"),
    ("Ctrl+F", "Search projects"),
    ("Ctrl+1 … Ctrl+6", "Dashboard, Projects, Add, Import, Settings, About"),
    ("Ctrl+S", "Save the project form"),
    ("Enter", "Open the selected project"),
    ("Delete", "Delete the selected project (asks first)"),
    ("Arrow keys", "Move the selection on the Projects page"),
    ("Double-click", "Open a project card"),
    ("F5", "Refresh folders and git status"),
    ("Esc", "Close a dialog, cancel the form, clear search"),
]


class AboutPage(Page):
    key = "about"
    title = "About"
    subtitle = f"{config.APP_NAME} {config.APP_VERSION}"

    def __init__(self, master, window):
        super().__init__(master, window)
        scroll = controls.scroll_frame(self)
        scroll.pack(fill="both", expand=True, padx=theme.LG - theme.XS)
        body = controls.transparent(scroll)
        body.pack(fill="both", expand=True, padx=theme.SM, pady=(theme.LG, theme.XL))

        hero = controls.card(body)
        hero.pack(fill="x", pady=(0, theme.LG))
        inner = controls.transparent(hero)
        inner.pack(fill="x", padx=theme.XL, pady=theme.XL)
        ctk.CTkLabel(inner, text="", image=icons.logo(72)).pack(side="left", padx=(0, theme.XL))
        text = controls.transparent(inner)
        text.pack(side="left", fill="x", expand=True)
        controls.label(text, config.APP_NAME, "header", "bold").pack(anchor="w")
        controls.label(text, f"Version {config.APP_VERSION}", "body", color="accent").pack(anchor="w")
        controls.label(text, config.APP_DESCRIPTION, "body", color="muted", wraplength=640).pack(anchor="w",
                                                                                               pady=(theme.SM, 0))
        controls.label(text, f"Python {platform.python_version()} · CustomTkinter {ctk.__version__} · "
                             f"{platform.system()} {platform.release()}", "caption", color="muted").pack(
            anchor="w", pady=(theme.SM, 0))
        controls.button(inner, "View on GitHub", self._open_repo, "secondary", icon="external").pack(
            side="right", anchor="n")

        box, keys = controls.section(body, "Keyboard shortcuts", "Work without the mouse.", "keyboard")
        box.pack(fill="x", pady=(0, theme.LG))
        keys.grid_columnconfigure(1, weight=1)
        for row, (combo, action) in enumerate(SHORTCUTS):
            ctk.CTkLabel(keys, text=combo, font=theme.font("caption", "bold"), fg_color=theme.c("subtle"),
                         corner_radius=6, padx=8, height=24, text_color=theme.c("text")).grid(
                row=row, column=0, sticky="w", pady=3, padx=(0, theme.LG))
            controls.label(keys, action, "body", color="muted").grid(row=row, column=1, sticky="w")

        box, data = controls.section(body, "Your data", "Everything stays on this PC.", "database")
        box.pack(fill="x")
        data.grid_columnconfigure(1, weight=1)
        for row, (label, path, folder) in enumerate((
                ("Data folder", config.APP_DIR, config.APP_DIR),
                ("Database", config.DB_PATH, config.APP_DIR),
                ("Backups", config.BACKUP_DIR, config.BACKUP_DIR),
                ("Log file", config.LOG_FILE, config.LOG_DIR))):
            controls.label(data, label, "body", "bold", width=120).grid(row=row, column=0, sticky="w", pady=4)
            controls.label(data, str(path), "body", color="muted").grid(row=row, column=1, sticky="w")
            controls.button(data, "Open", lambda f=folder: self._open(str(f)), "ghost", icon="folder",
                            height=28).grid(row=row, column=2, sticky="e")

    def _open_repo(self) -> None:
        try:
            self.ctx.launcher.open_url(config.GITHUB_REPO_URL)
        except LaunchError as exc:
            info(self.window, "Could not open the link", exc.user_message, "error")

    def _open(self, folder: str) -> None:
        try:
            self.ctx.launcher.open_folder(folder)
        except LaunchError as exc:
            info(self.window, "Could not open the folder", exc.user_message, "error")
