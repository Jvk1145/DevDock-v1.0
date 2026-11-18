"""Animated inline loading indicator."""
from __future__ import annotations

import customtkinter as ctk

from ui import theme

FRAMES = ("◐", "◓", "◑", "◒")


class Spinner(ctk.CTkLabel):
    def __init__(self, master, text: str = "Loading…", kind: str = "caption", **kwargs):
        super().__init__(master, text="", font=theme.font(kind), text_color=theme.c("muted"), anchor="w", **kwargs)
        self._text = text
        self._index = 0
        self._after: str | None = None

    def start(self) -> "Spinner":
        if self._after is None:
            self._tick()
        return self

    def stop(self) -> None:
        if self._after is not None:
            try:
                self.after_cancel(self._after)
            except Exception:
                pass
            self._after = None

    def _tick(self) -> None:
        try:
            if not self.winfo_exists():
                return
            self.configure(text=f"{FRAMES[self._index % len(FRAMES)]}  {self._text}")
        except Exception:
            return
        self._index += 1
        self._after = self.after(120, self._tick)

    def destroy(self) -> None:
        self.stop()
        super().destroy()
