"""Friendly placeholder shown when a list is empty."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ui import icons, theme
from ui.widgets import controls


class EmptyState(ctk.CTkFrame):
    def __init__(self, master, icon: str, title: str, text: str,
                 button_text: str | None = None, command: Callable[[], None] | None = None,
                 secondary_text: str | None = None, secondary_command: Callable[[], None] | None = None,
                 tips: list[str] | None = None):
        super().__init__(master, fg_color="transparent")
        controls.icon_circle(self, icon, "accent", 84, 36, base="bg", amount=0.16).pack(pady=(theme.XXL, theme.LG))
        controls.label(self, title, "title", "bold", anchor="center", justify="center").pack()
        controls.label(self, text, "body", color="muted", wraplength=460, anchor="center",
                       justify="center").pack(pady=(theme.SM, theme.LG))
        if button_text or secondary_text:
            row = controls.transparent(self)
            row.pack()
            if button_text:
                controls.button(row, button_text, command, "primary", icon="plus").pack(side="left", padx=theme.XS)
            if secondary_text:
                controls.button(row, secondary_text, secondary_command, "secondary",
                                icon="import").pack(side="left", padx=theme.XS)
        if tips:
            box = controls.card(self)
            box.pack(pady=(theme.XL, 0), ipadx=theme.SM)
            controls.label(box, "Quick tips", "body", "bold").pack(anchor="w", padx=theme.LG, pady=(theme.MD, theme.XS))
            for tip in tips:
                controls.label(box, f"•  {tip}", "body", color="muted", wraplength=480).pack(
                    anchor="w", padx=theme.LG, pady=1)
            ctk.CTkFrame(box, height=theme.MD, fg_color="transparent").pack()
