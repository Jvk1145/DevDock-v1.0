"""Hover tooltips for icon-only buttons."""
from __future__ import annotations

import tkinter as tk
from typing import Callable

from ui import theme


class Tooltip:
    DELAY_MS = 450

    def __init__(self, widget, text: str, enabled: Callable[[], bool] | None = None):
        self.widget = widget
        self.text = text
        self.enabled = enabled
        self._after: str | None = None
        self._tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")
        widget.bind("<Destroy>", self._hide, add="+")

    def set_text(self, text: str) -> None:
        self.text = text

    def _schedule(self, _event=None) -> None:
        self._cancel()
        if self.text and (self.enabled is None or self.enabled()):
            self._after = self.widget.after(self.DELAY_MS, self._show)

    def _cancel(self) -> None:
        if self._after:
            try:
                self.widget.after_cancel(self._after)
            except (tk.TclError, ValueError):
                pass
            self._after = None

    def _show(self) -> None:
        self._after = None
        try:
            if not self.widget.winfo_exists():
                return
            x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        except tk.TclError:
            return
        tip = tk.Toplevel(self.widget)
        tip.wm_overrideredirect(True)
        tip.attributes("-topmost", True)
        label = tk.Label(tip, text=self.text, bg=theme.current("surface"), fg=theme.current("text"),
                         font=theme.font("caption"), padx=8, pady=4, relief="solid", borderwidth=1,
                         highlightthickness=0)
        label.pack()
        tip.update_idletasks()
        tip.wm_geometry(f"+{x - tip.winfo_reqwidth() // 2}+{y}")
        self._tip = tip

    def _hide(self, _event=None) -> None:
        self._cancel()
        if self._tip is not None:
            try:
                self._tip.destroy()
            except tk.TclError:
                pass
            self._tip = None
