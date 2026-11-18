"""Theme-aware CTkImage icons (light and dark variants), cached."""
from __future__ import annotations

import logging

import customtkinter as ctk
from PIL import Image

import config
from ui import icon_art, theme

log = logging.getLogger(__name__)

_masks: dict[str, Image.Image] = {}
_images: dict[tuple, ctk.CTkImage] = {}


def _mask(name: str) -> Image.Image:
    if name not in _masks:
        path = config.ICONS_DIR / f"{name}.png"
        try:
            if path.is_file():
                with Image.open(path) as img:
                    _masks[name] = img.convert("RGBA").getchannel("A")
            else:
                _masks[name] = icon_art.mask(name)
        except OSError:
            log.warning("Icon %s could not be loaded, drawing it instead", name)
            _masks[name] = icon_art.mask(name)
    return _masks[name]


def _tint(mask: Image.Image, color: str) -> Image.Image:
    img = Image.new("RGBA", mask.size, color)
    img.putalpha(mask)
    return img


def get(name: str, size: int = 18, color: str | tuple[str, str] = "text") -> ctk.CTkImage:
    """``color`` is a theme token ('muted', 'accent', ...) or an explicit (light, dark) tuple."""
    light, dark = theme.c(color) if isinstance(color, str) else color
    key = (name, size, light, dark)
    if key not in _images:
        mask = _mask(name)
        _images[key] = ctk.CTkImage(light_image=_tint(mask, light), dark_image=_tint(mask, dark), size=(size, size))
    return _images[key]


def logo(size: int = 32) -> ctk.CTkImage:
    key = ("__logo__", size, theme.accent_name())
    if key not in _images:
        base, hover = theme.ACCENTS[theme.accent_name()]
        img = icon_art.logo(size * 3, base, theme.mix(hover, "#8B5CF6", 0.5))
        _images[key] = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    return _images[key]


def clear_cache() -> None:
    _images.clear()
