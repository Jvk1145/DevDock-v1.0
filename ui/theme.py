"""Design tokens: colours, fonts, spacing and radius for the dark and light themes.

Colours are returned as (light, dark) tuples, which CustomTkinter switches automatically
when the appearance mode changes. Widgets must use these tokens, never raw hex values.
"""
from __future__ import annotations

import customtkinter as ctk

# ---------------------------------------------------------------- palettes
DARK = {
    "bg": "#0B0F17",
    "surface": "#111827",
    "card": "#161E2E",
    "card_hover": "#1C2638",
    "border": "#243047",
    "input": "#0F1623",
    "subtle": "#1A2436",
    "text": "#E5E7EB",
    "muted": "#94A3B8",
    "success": "#22C55E",
    "info": "#3B82F6",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "danger_hover": "#F87171",
    "on_accent": "#FFFFFF",
}

LIGHT = {
    "bg": "#F3F5FA",
    "surface": "#FFFFFF",
    "card": "#FFFFFF",
    "card_hover": "#F5F7FC",
    "border": "#E2E8F0",
    "input": "#F8FAFC",
    "subtle": "#EEF2F7",
    "text": "#0F172A",
    "muted": "#64748B",
    "success": "#16A34A",
    "info": "#2563EB",
    "warning": "#D97706",
    "danger": "#DC2626",
    "danger_hover": "#EF4444",
    "on_accent": "#FFFFFF",
}

ACCENTS: dict[str, tuple[str, str]] = {   # name -> (base, hover)
    "Indigo": ("#6366F1", "#818CF8"),
    "Blue": ("#3B82F6", "#60A5FA"),
    "Violet": ("#8B5CF6", "#A78BFA"),
    "Emerald": ("#10B981", "#34D399"),
    "Rose": ("#F43F5E", "#FB7185"),
    "Amber": ("#F59E0B", "#FBBF24"),
    "Cyan": ("#06B6D4", "#22D3EE"),
}
DEFAULT_ACCENT = "Indigo"

STATUS_TOKENS = {"Active": "success", "Completed": "info", "On Hold": "warning", "Missing": "danger"}

# ---------------------------------------------------------------- typography & layout
FONT_FAMILY = "Segoe UI"
FONT_SIZES = {"caption": 12, "body": 13, "subtitle": 15, "title": 20, "header": 28}

XS, SM, MD, LG, XL, XXL = 4, 8, 12, 16, 24, 32
RADIUS_CARD = 12
RADIUS_INPUT = 8
SIDEBAR_WIDTH = 240
SIDEBAR_COLLAPSED_WIDTH = 72
TOPBAR_HEIGHT = 72
CONTROL_HEIGHT = 36

_accent = DEFAULT_ACCENT


def font(kind: str = "body", weight: str = "normal") -> tuple:
    return (FONT_FAMILY, FONT_SIZES.get(kind, 13), weight)


# ---------------------------------------------------------------- colour helpers
def set_accent(name: str) -> None:
    global _accent
    _accent = name if name in ACCENTS else DEFAULT_ACCENT


def accent_name() -> str:
    return _accent


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def mix(top: str, bottom: str, amount: float) -> str:
    """Blend ``amount`` of ``top`` over ``bottom`` (0 = bottom, 1 = top)."""
    a, b = _hex_to_rgb(top), _hex_to_rgb(bottom)
    return "#" + "".join(f"{round(x * amount + y * (1 - amount)):02X}" for x, y in zip(a, b))


def _raw(token: str, palette: dict[str, str]) -> str:
    if token == "accent":
        return ACCENTS[_accent][0]
    if token == "accent_hover":
        return ACCENTS[_accent][1]
    return palette[token]


def c(token: str) -> tuple[str, str]:
    """(light, dark) colour for a token."""
    return _raw(token, LIGHT), _raw(token, DARK)


def soft(token: str, amount: float = 0.16, base: str = "card") -> tuple[str, str]:
    """A tinted background: ``token`` colour washed over ``base`` (for badges and chips)."""
    return (mix(_raw(token, LIGHT), _raw(base, LIGHT), amount),
            mix(_raw(token, DARK), _raw(base, DARK), amount))


def status_token(status: str) -> str:
    return STATUS_TOKENS.get(status, "muted")


def current(token: str) -> str:
    """The single hex value for the active appearance mode (for non-CTk widgets)."""
    light, dark = c(token)
    return dark if ctk.get_appearance_mode() == "Dark" else light


# ---------------------------------------------------------------- CustomTkinter integration
def apply_mode(mode: str) -> None:
    ctk.set_appearance_mode({"dark": "Dark", "light": "Light", "system": "System"}.get(mode, "Dark"))


def apply_ctk_theme() -> None:
    """Load the base theme and override every widget default with DevDock tokens.

    Must run before widgets are created (and again before a rebuild after the accent changes).
    """
    ctk.set_default_color_theme("blue")
    t = ctk.ThemeManager.theme
    bg, surface, card, border = c("bg"), c("surface"), c("card"), c("border")
    text, muted, field, subtle = c("text"), c("muted"), c("input"), c("subtle")
    accent, accent_hover, white = c("accent"), c("accent_hover"), c("on_accent")
    seg_selected = (soft("accent", 0.28, "subtle")[0], accent[1])

    t["CTk"]["fg_color"] = bg
    t["CTkToplevel"]["fg_color"] = surface
    t["CTkFrame"].update(corner_radius=RADIUS_CARD, border_width=0, fg_color=card,
                         top_fg_color=c("card_hover"), border_color=border)
    t["CTkButton"].update(corner_radius=RADIUS_INPUT, border_width=0, fg_color=accent, hover_color=accent_hover,
                          border_color=border, text_color=white,
                          text_color_disabled=(mix(LIGHT["on_accent"], _raw("accent", LIGHT), 0.6),
                                               mix(DARK["muted"], DARK["card"], 0.8)))
    t["CTkLabel"].update(fg_color="transparent", text_color=text)
    t["CTkEntry"].update(corner_radius=RADIUS_INPUT, border_width=1, fg_color=field, border_color=border,
                         text_color=text, placeholder_text_color=muted)
    t["CTkCheckBox"].update(corner_radius=6, border_width=2, fg_color=accent, hover_color=accent_hover,
                            border_color=muted, checkmark_color=white, text_color=text, text_color_disabled=muted)
    t["CTkSwitch"].update(progress_color=accent, fg_color=border, button_color=white,
                          button_hover_color=white, text_color=text)
    t["CTkRadioButton"].update(fg_color=accent, hover_color=accent_hover, border_color=muted, text_color=text)
    t["CTkProgressBar"].update(fg_color=border, progress_color=accent)
    t["CTkSlider"].update(fg_color=border, progress_color=accent, button_color=accent, button_hover_color=accent_hover)
    t["CTkOptionMenu"].update(corner_radius=RADIUS_INPUT, fg_color=field, button_color=field,
                              button_hover_color=c("card_hover"), text_color=text, text_color_disabled=muted)
    t["CTkComboBox"].update(corner_radius=RADIUS_INPUT, border_width=1, fg_color=field, border_color=border,
                            button_color=border, button_hover_color=muted, text_color=text,
                            text_color_disabled=muted)
    t["CTkScrollbar"].update(fg_color="transparent", button_color=border, button_hover_color=muted)
    t["CTkSegmentedButton"].update(corner_radius=RADIUS_INPUT, border_width=2, fg_color=subtle,
                                   selected_color=seg_selected, selected_hover_color=seg_selected,
                                   unselected_color=subtle, unselected_hover_color=c("card_hover"),
                                   text_color=text, text_color_disabled=muted)
    t["CTkTextbox"].update(corner_radius=RADIUS_INPUT, border_width=1, fg_color=field, border_color=border,
                           text_color=text, scrollbar_button_color=border, scrollbar_button_hover_color=muted)
    t["CTkScrollableFrame"].update(label_fg_color=surface)
    t["DropdownMenu"].update(fg_color=surface, hover_color=c("card_hover"), text_color=text)
    t["CTkFont"].update(family=FONT_FAMILY, size=FONT_SIZES["body"], weight="normal")
