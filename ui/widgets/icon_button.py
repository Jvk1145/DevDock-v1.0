"""Square icon-only button with tooltip and optional active (toggled) state."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ui import icons, theme
from ui.widgets.tooltip import Tooltip


class IconButton(ctk.CTkButton):
    def __init__(self, master, icon: str, command: Callable | None = None, tooltip: str = "",
                 size: int = 32, icon_size: int = 16, color: str = "muted", danger: bool = False, **kwargs):
        self._icon = icon
        self._icon_size = icon_size
        self._color = "danger" if danger else color
        self._danger = danger
        self._active = False
        super().__init__(master, text="", width=size, height=size, corner_radius=theme.RADIUS_INPUT,
                         fg_color="transparent", hover_color=theme.soft("danger", 0.2) if danger else theme.c("subtle"),
                         image=icons.get(icon, icon_size, self._color), command=command, **kwargs)
        self.tooltip = Tooltip(self, tooltip) if tooltip else None

    def set_icon(self, icon: str, color: str | None = None) -> None:
        self._icon = icon
        if color:
            self._color = color
        self.configure(image=icons.get(icon, self._icon_size, "accent" if self._active else self._color))

    def set_active(self, active: bool) -> None:
        self._active = active
        self.configure(fg_color=theme.soft("accent", 0.22) if active else "transparent",
                       image=icons.get(self._icon, self._icon_size, "accent" if active else self._color))

    def set_tooltip(self, text: str) -> None:
        if self.tooltip:
            self.tooltip.set_text(text)
        else:
            self.tooltip = Tooltip(self, text)
