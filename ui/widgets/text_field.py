"""Entry with a working placeholder and a change callback.

CTkEntry disables its placeholder whenever a ``textvariable`` is attached, so this widget
never uses one. Changes are reported from key, paste and cut events instead.
"""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ui import theme


class TextField(ctk.CTkEntry):
    def __init__(self, master, placeholder: str = "", on_change: Callable[[str], None] | None = None,
                 width: int = 200, height: int = theme.CONTROL_HEIGHT, **kwargs):
        kwargs.setdefault("font", theme.font("body"))
        super().__init__(master, placeholder_text=placeholder or None, width=width, height=height, **kwargs)
        self.on_change = on_change
        self._last = ""
        for sequence in ("<KeyRelease>", "<<Paste>>", "<<Cut>>", "<<Clear>>"):
            self._entry.bind(sequence, self._schedule_check, add="+")

    @property
    def value(self) -> str:
        return self.get()

    def set_value(self, text: str, notify: bool = False) -> None:
        text = text or ""
        if text == self.get():
            return
        self.delete(0, "end")
        if text:
            self.insert(0, text)
        else:
            self._restore_placeholder()
        self._last = text
        if notify and self.on_change:
            self.on_change(text)

    def _restore_placeholder(self) -> None:
        """CTkEntry starts with _is_focused=True, so delete() never brings the placeholder back
        until the entry has been focused once. Use the real focus state instead."""
        try:
            has_focus = self.focus_get() is self._entry
        except (KeyError, Exception):
            has_focus = False
        if not has_focus:
            self._is_focused = False
            self._activate_placeholder()

    def _schedule_check(self, _event=None) -> None:
        self.after_idle(self._check)

    def _check(self) -> None:
        try:
            current = self.get()
        except Exception:
            return
        if current != self._last:
            self._last = current
            if self.on_change:
                self.on_change(current)
