"""Small factories that create consistently styled CustomTkinter controls from theme tokens."""
from __future__ import annotations

from typing import Callable, Sequence

import customtkinter as ctk

from ui import icons, theme

_BUTTON_VARIANTS = {
    #            fg            hover            text        icon         border
    "primary": ("accent", "accent_hover", "on_accent", "on_accent", None),
    "secondary": ("subtle", "card_hover", "text", "text", "border"),
    "ghost": (None, "subtle", "text", "muted", None),
    "danger": ("danger", "danger_hover", "on_accent", "on_accent", None),
    "danger_ghost": (None, "subtle", "danger", "danger", None),
}


def label(master, text: str = "", kind: str = "body", weight: str = "normal", color: str = "text",
          **kwargs) -> ctk.CTkLabel:
    kwargs.setdefault("anchor", "w")
    kwargs.setdefault("justify", "left")
    return ctk.CTkLabel(master, text=text, font=theme.font(kind, weight), text_color=theme.c(color), **kwargs)


def button(master, text: str, command: Callable | None = None, variant: str = "primary",
           icon: str | None = None, width: int = 0, height: int = theme.CONTROL_HEIGHT, **kwargs) -> ctk.CTkButton:
    fg, hover, text_token, icon_token, border = _BUTTON_VARIANTS[variant]
    options = dict(
        text=text, command=command, height=height, width=width or (0 if text else height),
        corner_radius=theme.RADIUS_INPUT, font=theme.font("body", "bold" if variant in ("primary", "danger") else "normal"),
        fg_color=theme.c(fg) if fg else "transparent", hover_color=theme.c(hover), text_color=theme.c(text_token),
        border_width=1 if border else 0, border_color=theme.c(border) if border else None,
    )
    if icon:
        options.update(image=icons.get(icon, 16, icon_token), compound="left")
    options.update(kwargs)
    if options.get("border_color") is None:
        options.pop("border_color")
    return ctk.CTkButton(master, **options)


def restyle_button(btn: ctk.CTkButton, variant: str, icon: str | None = None) -> None:
    fg, hover, text_token, icon_token, border = _BUTTON_VARIANTS[variant]
    btn.configure(fg_color=theme.c(fg) if fg else "transparent", hover_color=theme.c(hover),
                  text_color=theme.c(text_token), border_width=1 if border else 0)
    if border:
        btn.configure(border_color=theme.c(border))
    if icon:
        btn.configure(image=icons.get(icon, 16, icon_token))


def entry(master, placeholder: str = "", width: int = 200, **kwargs) -> ctk.CTkEntry:
    return ctk.CTkEntry(master, placeholder_text=placeholder, width=width, height=theme.CONTROL_HEIGHT,
                        font=theme.font("body"), **kwargs)


def option_menu(master, values: Sequence[str], command: Callable[[str], None] | None = None,
                width: int = 180, **kwargs) -> ctk.CTkOptionMenu:
    return ctk.CTkOptionMenu(master, values=list(values) or [""], command=command, width=width,
                             height=theme.CONTROL_HEIGHT, dynamic_resizing=False, font=theme.font("body"),
                             dropdown_font=theme.font("body"), **kwargs)


def combo(master, values: Sequence[str], width: int = 200, **kwargs) -> ctk.CTkComboBox:
    return ctk.CTkComboBox(master, values=list(values), width=width, height=theme.CONTROL_HEIGHT,
                           font=theme.font("body"), dropdown_font=theme.font("body"), **kwargs)


def card(master, **kwargs) -> ctk.CTkFrame:
    kwargs.setdefault("fg_color", theme.c("card"))
    kwargs.setdefault("corner_radius", theme.RADIUS_CARD)
    kwargs.setdefault("border_width", 1)
    kwargs.setdefault("border_color", theme.c("border"))
    return ctk.CTkFrame(master, **kwargs)


def transparent(master, **kwargs) -> ctk.CTkFrame:
    return ctk.CTkFrame(master, fg_color="transparent", corner_radius=0, **kwargs)


def scroll_frame(master, **kwargs) -> ctk.CTkScrollableFrame:
    kwargs.setdefault("fg_color", "transparent")
    kwargs.setdefault("corner_radius", 0)
    return ctk.CTkScrollableFrame(master, scrollbar_button_color=theme.c("border"),
                                  scrollbar_button_hover_color=theme.c("muted"), **kwargs)


def divider(master, **kwargs) -> ctk.CTkFrame:
    return ctk.CTkFrame(master, height=1, corner_radius=0, fg_color=theme.c("border"), **kwargs)


def section(master, title: str, subtitle: str = "", icon: str | None = None) -> tuple[ctk.CTkFrame, ctk.CTkFrame]:
    """A titled card. Returns (card, body) — put content in body."""
    box = card(master)
    header = transparent(box)
    header.pack(fill="x", padx=theme.XL, pady=(theme.LG, theme.SM))
    if icon:
        ctk.CTkLabel(header, text="", image=icons.get(icon, 18, "accent"), width=22).pack(side="left", padx=(0, theme.SM))
    text_col = transparent(header)
    text_col.pack(side="left", fill="x", expand=True)
    label(text_col, title, "subtitle", "bold").pack(anchor="w")
    if subtitle:
        label(text_col, subtitle, "caption", color="muted").pack(anchor="w")
    body = transparent(box)
    body.pack(fill="both", expand=True, padx=theme.XL, pady=(theme.XS, theme.LG))
    box.header = header  # type: ignore[attr-defined]
    return box, body


def icon_circle(master, icon: str, token: str = "accent", size: int = 44, icon_size: int = 22,
                base: str = "card", amount: float = 0.18) -> ctk.CTkFrame:
    """A perfect circle with a tinted background and a centred icon."""
    circle = ctk.CTkFrame(master, width=size, height=size, corner_radius=size // 2,
                          fg_color=theme.soft(token, amount, base))
    circle.pack_propagate(False)
    ctk.CTkLabel(circle, text="", image=icons.get(icon, icon_size, token), width=icon_size,
                 height=icon_size).place(relx=0.5, rely=0.5, anchor="center")
    return circle


def field_label(master, text: str, required: bool = False) -> ctk.CTkLabel:
    return label(master, text + ("  *" if required else ""), "caption", "bold", color="muted")


def error_label(master) -> ctk.CTkLabel:
    return label(master, "", "caption", color="danger", height=18)


def hint_label(master, text: str = "") -> ctk.CTkLabel:
    return label(master, text, "caption", color="muted", height=18)
