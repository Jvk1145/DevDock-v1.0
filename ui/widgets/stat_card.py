"""Dashboard statistic tile. Clicking it can jump to a filtered list."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ui import icons, theme
from ui.widgets import controls


class StatCard(ctk.CTkFrame):
    def __init__(self, master, title: str, value: int | str, icon: str, token: str = "accent",
                 command: Callable[[], None] | None = None):
        super().__init__(master, fg_color=theme.c("card"), corner_radius=theme.RADIUS_CARD, border_width=1,
                         border_color=theme.c("border"), height=104)
        self.grid_propagate(False)
        self.grid_columnconfigure(1, weight=1)
        self.command = command
        ctk.CTkLabel(self, text="", image=icons.get(icon, 18, token), width=36, height=36, corner_radius=10,
                     fg_color=theme.soft(token, 0.18)).grid(row=0, column=0, rowspan=2, padx=(theme.LG, theme.MD),
                                                            pady=theme.LG, sticky="w")
        self.value_label = controls.label(self, str(value), "header", "bold")
        self.value_label.grid(row=0, column=1, sticky="sw", pady=(theme.MD, 0))
        controls.label(self, title, "caption", color="muted").grid(row=1, column=1, sticky="nw", pady=(0, theme.MD))
        if command:
            self.configure(cursor="hand2")
            self._bind_all(self)

    def _bind_all(self, widget) -> None:
        widget.bind("<Button-1>", lambda _e: self.command and self.command(), add="+")
        widget.bind("<Enter>", lambda _e: self.configure(border_color=theme.c("accent")), add="+")
        widget.bind("<Leave>", lambda _e: self.configure(border_color=theme.c("border")), add="+")
        for child in widget.winfo_children():
            self._bind_all(child)

    def set_value(self, value: int | str) -> None:
        self.value_label.configure(text=str(value))
