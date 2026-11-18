"""Navigation sidebar: logo, nav items with icons, collapse toggle, version."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

import config
from ui import icons, theme
from ui.widgets import controls
from ui.widgets.tooltip import Tooltip


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, items: list[tuple[str, str, str, str]], on_navigate: Callable[[str], None],
                 on_toggle: Callable[[bool], None], collapsed: bool = False):
        """items: (key, label, icon, shortcut)."""
        super().__init__(master, width=theme.SIDEBAR_WIDTH, corner_radius=0, fg_color=theme.c("surface"))
        self.grid_propagate(False)
        self.on_navigate = on_navigate
        self.on_toggle = on_toggle
        self.collapsed = collapsed
        self.active: str | None = None
        self.items = items
        self.buttons: dict[str, ctk.CTkButton] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(len(items) + 1, weight=1)
        ctk.CTkFrame(self, width=1, corner_radius=0, fg_color=theme.c("border")).grid(
            row=0, column=1, rowspan=len(items) + 4, sticky="ns")

        header = controls.transparent(self)
        header.grid(row=0, column=0, sticky="ew", padx=theme.LG, pady=(theme.XL, theme.XL))
        self.logo = ctk.CTkLabel(header, text="", image=icons.logo(34), width=34)
        self.logo.pack(side="left")
        self.title_label = controls.label(header, config.APP_NAME, "title", "bold")
        self.title_label.pack(side="left", padx=(theme.MD, 0))

        for row, (key, text, icon, shortcut) in enumerate(items, start=1):
            btn = ctk.CTkButton(self, text=text, height=40, corner_radius=theme.RADIUS_INPUT, anchor="w",
                                font=theme.font("body"), compound="left", fg_color="transparent",
                                hover_color=theme.c("subtle"), text_color=theme.c("muted"),
                                image=icons.get(icon, 18, "muted"), command=lambda k=key: self.on_navigate(k))
            btn.grid(row=row, column=0, sticky="ew", padx=theme.MD, pady=2)
            Tooltip(btn, f"{text}   {shortcut}" if shortcut else text, enabled=lambda: self.collapsed)
            self.buttons[key] = btn

        footer = controls.transparent(self)
        footer.grid(row=len(items) + 2, column=0, sticky="ew", padx=theme.MD, pady=(theme.SM, theme.LG))
        self.toggle_btn = ctk.CTkButton(footer, text="Collapse", height=34, anchor="w", corner_radius=theme.RADIUS_INPUT,
                                        fg_color="transparent", hover_color=theme.c("subtle"),
                                        text_color=theme.c("muted"), font=theme.font("caption"), compound="left",
                                        image=icons.get("chevron_left", 14, "muted"), command=self.toggle)
        self.toggle_btn.pack(fill="x")
        Tooltip(self.toggle_btn, "Expand sidebar", enabled=lambda: self.collapsed)
        self.version_label = controls.label(footer, f"Version {config.APP_VERSION}", "caption", color="muted")
        self.version_label.pack(fill="x", padx=theme.MD, pady=(theme.XS, 0))
        self._apply_collapsed()

    def toggle(self) -> None:
        self.collapsed = not self.collapsed
        self._apply_collapsed()
        self.on_toggle(self.collapsed)

    def _apply_collapsed(self) -> None:
        collapsed = self.collapsed
        self.configure(width=theme.SIDEBAR_COLLAPSED_WIDTH if collapsed else theme.SIDEBAR_WIDTH)
        if collapsed:
            self.title_label.pack_forget()
        else:
            self.title_label.pack(side="left", padx=(theme.MD, 0))
        for key, text, _icon, _shortcut in self.items:
            self.buttons[key].configure(text="" if collapsed else text, anchor="center" if collapsed else "w")
        self.toggle_btn.configure(text="" if collapsed else "Collapse", anchor="center" if collapsed else "w",
                                  image=icons.get("chevron_right" if collapsed else "chevron_left", 14, "muted"))
        major = config.APP_VERSION.split(".")[0]
        self.version_label.configure(text=f"v{major}" if collapsed else f"Version {config.APP_VERSION}",
                                     anchor="center" if collapsed else "w")
        self.version_label.pack_configure(padx=0 if collapsed else theme.MD)

    def set_active(self, key: str) -> None:
        self.active = key
        for k, _text, icon, _shortcut in self.items:
            on = k == key
            self.buttons[k].configure(
                fg_color=theme.c("accent") if on else "transparent",
                hover_color=theme.c("accent_hover") if on else theme.c("subtle"),
                text_color=theme.c("on_accent") if on else theme.c("muted"),
                font=theme.font("body", "bold" if on else "normal"),
                image=icons.get(icon, 18, "on_accent" if on else "muted"))
