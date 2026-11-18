"""Base class for pages shown in the main window."""
from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from ui.main_window import MainWindow


class Page(ctk.CTkFrame):
    key = ""
    title = ""
    subtitle = ""
    nav_key: str | None = None   # sidebar item to highlight (defaults to key)

    def __init__(self, master, window: "MainWindow"):
        super().__init__(master, fg_color="transparent", corner_radius=0)
        self.window = window
        self.ctx = window.ctx
        self.dirty = True

    def on_show(self, **kwargs) -> None:
        if self.dirty:
            self.refresh()

    def on_hide(self) -> None:
        """Called when another page is shown."""

    def refresh(self) -> None:
        self.dirty = False

    def on_data_changed(self) -> None:
        self.refresh()

    def on_search(self, text: str) -> None:
        """Global search text changed while this page is visible."""

    def handle_key(self, action: str) -> bool:
        """Keyboard action: enter, delete, save, escape, up, down, left, right. Return True if handled."""
        return False
