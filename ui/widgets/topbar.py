"""Top bar: page title + subtitle, global search, New Project button."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ui import theme
from ui.widgets import controls
from ui.widgets.search_box import SearchBox


class TopBar(ctk.CTkFrame):
    def __init__(self, master, on_search: Callable[[str], None], on_new: Callable[[], None]):
        super().__init__(master, height=theme.TOPBAR_HEIGHT, corner_radius=0, fg_color=theme.c("bg"))
        self.pack_propagate(False)
        inner = controls.transparent(self)
        inner.pack(fill="both", expand=True, padx=theme.XL)

        titles = controls.transparent(inner)
        titles.pack(side="left", fill="y", pady=theme.MD)
        self.title_label = controls.label(titles, "", "title", "bold")
        self.title_label.pack(anchor="w")
        self.subtitle_label = controls.label(titles, "", "caption", color="muted")
        self.subtitle_label.pack(anchor="w")

        self.new_button = controls.button(inner, "New Project", on_new, "primary", icon="plus")
        self.new_button.pack(side="right")
        self.search = SearchBox(inner, on_search)
        self.search.pack(side="right", padx=(0, theme.MD))
        controls.divider(self).pack(side="bottom", fill="x")

    def set_title(self, title: str, subtitle: str = "") -> None:
        self.title_label.configure(text=title)
        self.subtitle_label.configure(text=subtitle)
