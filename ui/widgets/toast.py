"""Toast notifications in the bottom-right corner of the main window (auto-hide after 3 s)."""
from __future__ import annotations

import logging

import customtkinter as ctk

import config
from ui import icons, theme
from ui.widgets import controls
from ui.widgets.icon_button import IconButton

log = logging.getLogger(__name__)

_KINDS = {"success": ("check", "success"), "error": ("error", "danger"), "warning": ("warning", "warning"),
          "info": ("about", "info")}
MAX_TOASTS = 4
MARGIN = 24
GAP = 10


class ToastManager:
    def __init__(self, window):
        self.window = window
        self._toasts: list[ctk.CTkFrame] = []

    def show(self, message: str, kind: str = "success", duration: int = config.TOAST_MS) -> None:
        icon, token = _KINDS.get(kind, _KINDS["info"])
        toast = ctk.CTkFrame(self.window, fg_color=theme.c("surface"), border_width=1, border_color=theme.c("border"),
                             corner_radius=10)
        ctk.CTkFrame(toast, width=4, height=20, corner_radius=2, fg_color=theme.c(token)).pack(
            side="left", fill="y", padx=(6, 0), pady=8)
        ctk.CTkLabel(toast, text="", image=icons.get(icon, 18, token), width=24).pack(side="left", padx=(10, 8), pady=12)
        controls.label(toast, message, "body", wraplength=320).pack(side="left", pady=12)
        IconButton(toast, "close", lambda t=toast: self.dismiss(t), "Dismiss", size=26, icon_size=11).pack(
            side="left", padx=(12, 8))
        self._toasts.append(toast)
        while len(self._toasts) > MAX_TOASTS:
            self.dismiss(self._toasts[0])
        self._restack()
        toast.after(duration if kind != "error" else duration * 2, lambda t=toast: self.dismiss(t))
        log.debug("Toast (%s): %s", kind, message)

    def dismiss(self, toast: ctk.CTkFrame) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
            try:
                toast.destroy()
            except Exception:
                pass
            self._restack()

    def _restack(self) -> None:
        offset = MARGIN
        for toast in reversed(self._toasts):
            try:
                toast.update_idletasks()
                scale = ctk.ScalingTracker.get_widget_scaling(toast)
                toast.place(relx=1.0, rely=1.0, x=-MARGIN, y=-offset, anchor="se")
                toast.lift()
                offset += toast.winfo_reqheight() / scale + GAP
            except Exception:
                continue

    def lift_all(self) -> None:
        for toast in self._toasts:
            try:
                toast.lift()
            except Exception:
                pass
