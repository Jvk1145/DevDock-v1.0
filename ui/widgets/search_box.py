"""Search field with icon, clear button and debounced change callback."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

import config
from ui import icons, theme
from ui.widgets.icon_button import IconButton
from ui.widgets.text_field import TextField


class SearchBox(ctk.CTkFrame):
    def __init__(self, master, on_change: Callable[[str], None], placeholder: str = "Search projects  (Ctrl+F)",
                 width: int = 320, debounce_ms: int = config.SEARCH_DEBOUNCE_MS):
        super().__init__(master, width=width, height=theme.CONTROL_HEIGHT, fg_color=theme.c("input"),
                         border_width=1, border_color=theme.c("border"), corner_radius=theme.RADIUS_INPUT)
        self.pack_propagate(False)
        self.on_change = on_change
        self.debounce_ms = debounce_ms
        self._after: str | None = None

        ctk.CTkLabel(self, text="", image=icons.get("search", 15, "muted"), width=20).pack(side="left", padx=(10, 2))
        self.clear_btn = IconButton(self, "close", self.clear, "Clear search", size=24, icon_size=12)
        self.entry = TextField(self, placeholder, self._changed, border_width=0, fg_color=theme.c("input"),
                               height=theme.CONTROL_HEIGHT - 4)
        self.entry.pack(side="left", fill="both", expand=True, pady=2)
        self.entry.bind("<Escape>", lambda _e: self.clear())
        self.entry.bind("<FocusIn>", lambda _e: self.configure(border_color=theme.c("accent")))
        self.entry.bind("<FocusOut>", lambda _e: self.configure(border_color=theme.c("border")))

    def get(self) -> str:
        return self.entry.value

    def focus(self) -> None:
        self.entry.focus_set()
        self.entry.select_range(0, "end")

    def set_text(self, text: str, notify: bool = False) -> None:
        self.entry.set_value(text)
        self._toggle_clear()
        if notify:
            self._changed(text)

    def clear(self) -> None:
        if self.entry.value:
            self.entry.set_value("", notify=True)
        self._toggle_clear()
        self.entry.focus_set()

    def _toggle_clear(self) -> None:
        if self.entry.value:
            self.clear_btn.pack(side="right", padx=(0, 6), before=self.entry)
        else:
            self.clear_btn.pack_forget()

    def _changed(self, _text: str) -> None:
        self._toggle_clear()
        if self._after:
            self.after_cancel(self._after)
        self._after = self.after(self.debounce_ms, self._fire)

    def _fire(self) -> None:
        self._after = None
        self.on_change(self.entry.value.strip())
