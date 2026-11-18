"""Badge (coloured status pill) and Chip (toggleable filter pill)."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ui import theme


class Badge(ctk.CTkLabel):
    def __init__(self, master, text: str = "", token: str = "muted", **kwargs):
        super().__init__(master, text=text, height=22, corner_radius=6, padx=8, font=theme.font("caption", "bold"),
                         **kwargs)
        self.set(text, token)

    def set(self, text: str, token: str) -> None:
        self.configure(text=text, fg_color=theme.soft(token, 0.2), text_color=theme.c(token))


class Chip(ctk.CTkButton):
    def __init__(self, master, text: str, command: Callable[[], None] | None = None, selected: bool = False,
                 **kwargs):
        super().__init__(master, text=text, command=command, height=30, width=0, corner_radius=15, border_width=1,
                         font=theme.font("body"), **kwargs)
        self.set_selected(selected)

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        if selected:
            self.configure(fg_color=theme.soft("accent", 0.22, "bg"), hover_color=theme.soft("accent", 0.3, "bg"),
                           border_color=theme.c("accent"), text_color=theme.c("accent"))
        else:
            self.configure(fg_color="transparent", hover_color=theme.c("subtle"), border_color=theme.c("border"),
                           text_color=theme.c("muted"))
