"""Vector-style icons drawn with Pillow (no Tk dependency).

Each icon is drawn white-on-transparent on a 256 px canvas and downsampled to 64 px, giving
smooth anti-aliased masks. ``scripts/make_icon.py`` writes them to assets/icons/*.png and
builds assets/app.ico; at runtime the PNGs are loaded, or drawn here if they are missing.
"""
from __future__ import annotations

import math
from typing import Callable

from PIL import Image, ImageChops, ImageDraw

CANVAS = 256
OUT = 64
W = 18  # stroke width on the 256 canvas

Drawer = Callable[[ImageDraw.ImageDraw], None]
_REGISTRY: dict[str, Drawer] = {}


def icon(name: str) -> Callable[[Drawer], Drawer]:
    def register(fn: Drawer) -> Drawer:
        _REGISTRY[name] = fn
        return fn
    return register


def names() -> list[str]:
    return sorted(_REGISTRY)


def _poly(d: ImageDraw.ImageDraw, points, width: int = W, closed: bool = False) -> None:
    pts = list(points) + ([points[0]] if closed else [])
    d.line(pts, fill=255, width=width, joint="curve")
    r = width / 2
    for x, y in (pts[0], pts[-1]):
        d.ellipse((x - r, y - r, x + r, y + r), fill=255)


def _dot(d: ImageDraw.ImageDraw, x: float, y: float, r: float) -> None:
    d.ellipse((x - r, y - r, x + r, y + r), fill=255)


def _ring(d: ImageDraw.ImageDraw, box, width: int = W) -> None:
    d.ellipse(box, outline=255, width=width)


def _round_box(d: ImageDraw.ImageDraw, box, radius: int = 22, width: int = W, fill: bool = False) -> None:
    if fill:
        d.rounded_rectangle(box, radius=radius, fill=255)
    else:
        d.rounded_rectangle(box, radius=radius, outline=255, width=width)


# ------------------------------------------------------------------ navigation
@icon("dashboard")
def _home(d):
    _poly(d, [(36, 124), (128, 44), (220, 124)])
    _poly(d, [(64, 108), (64, 212), (192, 212), (192, 108)])
    _round_box(d, (108, 148, 148, 214), radius=8, fill=True)


@icon("projects")
def _grid4(d):
    for x, y in ((40, 40), (140, 40), (40, 140), (140, 140)):
        _round_box(d, (x, y, x + 76, y + 76), radius=16)


@icon("add")
def _plus_circle(d):
    _ring(d, (28, 28, 228, 228))
    _poly(d, [(128, 84), (128, 172)])
    _poly(d, [(84, 128), (172, 128)])


@icon("plus")
def _plus(d):
    _poly(d, [(128, 48), (128, 208)], width=W + 4)
    _poly(d, [(48, 128), (208, 128)], width=W + 4)


@icon("import")
def _download(d):
    _poly(d, [(128, 36), (128, 152)])
    _poly(d, [(80, 108), (128, 156), (176, 108)])
    _poly(d, [(40, 152), (40, 212), (216, 212), (216, 152)])


@icon("export")
def _upload(d):
    _poly(d, [(128, 56), (128, 164)])
    _poly(d, [(80, 100), (128, 52), (176, 100)])
    _poly(d, [(40, 152), (40, 212), (216, 212), (216, 152)])


@icon("settings")
def _gear(d):
    cx = cy = 128
    for i in range(8):
        a = math.radians(i * 45)
        ca, sa = math.cos(a), math.sin(a)
        half = 22
        pts = []
        for r, s in ((64, -half), (106, -half), (106, half), (64, half)):
            pts.append((cx + r * ca - s * sa, cy + r * sa + s * ca))
        d.polygon(pts, fill=255)
    d.ellipse((cx - 78, cy - 78, cx + 78, cy + 78), fill=255)
    d.ellipse((cx - 34, cy - 34, cx + 34, cy + 34), fill=0)


@icon("about")
def _info(d):
    _ring(d, (28, 28, 228, 228))
    _dot(d, 128, 82, 14)
    _poly(d, [(128, 120), (128, 180)], width=W + 2)


@icon("menu")
def _menu(d):
    for y in (72, 128, 184):
        _poly(d, [(48, y), (208, y)])


@icon("chevron_left")
def _chev_left(d):
    _poly(d, [(156, 52), (84, 128), (156, 204)], width=W + 2)


@icon("chevron_right")
def _chev_right(d):
    _poly(d, [(100, 52), (172, 128), (100, 204)], width=W + 2)


# ------------------------------------------------------------------ project actions
@icon("folder")
def _folder(d):
    _poly(d, [(36, 76), (100, 76), (122, 100), (220, 100), (220, 200), (36, 200)], closed=True)


@icon("terminal")
def _terminal(d):
    _round_box(d, (28, 44, 228, 212), radius=24)
    _poly(d, [(70, 98), (108, 128), (70, 158)])
    _poly(d, [(126, 164), (186, 164)])


@icon("git")
def _branch(d):
    _ring(d, (62, 36, 106, 80))
    _ring(d, (62, 176, 106, 220))
    _ring(d, (150, 72, 194, 116))
    _poly(d, [(84, 82), (84, 174)])
    _poly(d, [(172, 118), (172, 136), (96, 176)])


@icon("run")
def _play(d):
    d.polygon([(86, 52), (86, 204), (206, 128)], fill=255)
    _poly(d, [(86, 52), (86, 204), (206, 128)], width=14, closed=True)


@icon("edit")
def _pencil(d):
    _poly(d, [(64, 164), (166, 62), (194, 90), (92, 192)], closed=True)
    _poly(d, [(64, 164), (50, 206), (92, 192)])
    _poly(d, [(146, 82), (174, 110)], width=12)


@icon("delete")
def _trash(d):
    _poly(d, [(44, 72), (212, 72)])
    _poly(d, [(100, 70), (106, 44), (150, 44), (156, 70)], width=14)
    _poly(d, [(66, 76), (80, 212), (176, 212), (190, 76)])
    _poly(d, [(112, 108), (112, 180)], width=14)
    _poly(d, [(144, 108), (144, 180)], width=14)


def _star_points(cx=128, cy=134, outer=104, inner=44):
    pts = []
    for i in range(10):
        r = outer if i % 2 == 0 else inner
        a = math.radians(-90 + i * 36)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


@icon("star")
def _star(d):
    _poly(d, _star_points(), width=16, closed=True)


@icon("star_filled")
def _star_filled(d):
    pts = _star_points()
    d.polygon(pts, fill=255)
    _poly(d, pts, width=16, closed=True)


@icon("search")
def _search(d):
    _ring(d, (36, 36, 172, 172), width=W + 2)
    _poly(d, [(160, 160), (216, 216)], width=W + 6)


@icon("grid")
def _grid_view(d):
    _grid4(d)


@icon("list")
def _list_view(d):
    for y in (68, 128, 188):
        _round_box(d, (40, y - 16, 72, y + 16), radius=8, fill=True)
        _poly(d, [(100, y), (216, y)])


@icon("refresh")
def _refresh(d):
    box = (48, 48, 208, 208)
    start, end = 40, 320
    d.arc(box, start=start, end=end, fill=255, width=W)
    a = math.radians(end)
    ex, ey = 128 + 80 * math.cos(a), 128 + 80 * math.sin(a)
    tx, ty = -math.sin(a), math.cos(a)        # direction of travel (clockwise)
    nx, ny = math.cos(a), math.sin(a)
    tip = (ex + tx * 34, ey + ty * 34)
    d.polygon([tip, (ex + nx * 30 - tx * 6, ey + ny * 30 - ty * 6), (ex - nx * 30 - tx * 6, ey - ny * 30 - ty * 6)],
              fill=255)


@icon("close")
def _close(d):
    _poly(d, [(68, 68), (188, 188)], width=W + 2)
    _poly(d, [(188, 68), (68, 188)], width=W + 2)


@icon("check")
def _check(d):
    _poly(d, [(52, 132), (104, 184), (204, 76)], width=W + 4)


@icon("warning")
def _warning(d):
    _poly(d, [(128, 36), (228, 210), (28, 210)], closed=True)
    _poly(d, [(128, 96), (128, 146)], width=W + 2)
    _dot(d, 128, 178, 13)


@icon("error")
def _error(d):
    _ring(d, (28, 28, 228, 228))
    _poly(d, [(128, 72), (128, 140)], width=W + 2)
    _dot(d, 128, 176, 13)


@icon("external")
def _external(d):
    _poly(d, [(184, 144), (184, 212), (44, 212), (44, 72), (112, 72)])
    _poly(d, [(112, 144), (212, 44)])
    _poly(d, [(148, 44), (212, 44), (212, 108)])


@icon("clock")
def _clock(d):
    _ring(d, (28, 28, 228, 228))
    _poly(d, [(128, 74), (128, 128), (166, 152)])


@icon("database")
def _database(d):
    d.ellipse((48, 32, 208, 84), outline=255, width=W)
    _poly(d, [(48, 58), (48, 196)])
    _poly(d, [(208, 58), (208, 196)])
    d.arc((48, 102, 208, 154), start=0, end=180, fill=255, width=W)
    d.arc((48, 170, 208, 222), start=0, end=180, fill=255, width=W)


@icon("palette")
def _palette(d):
    _ring(d, (28, 28, 228, 228))
    for x, y in ((92, 88), (148, 80), (178, 128), (84, 146)):
        _dot(d, x, y, 15)


@icon("code")
def _code(d):
    _poly(d, [(92, 76), (44, 128), (92, 180)], width=W + 2)
    _poly(d, [(164, 76), (212, 128), (164, 180)], width=W + 2)


@icon("keyboard")
def _keyboard(d):
    _round_box(d, (24, 64, 232, 196), radius=22)
    for x in (64, 104, 144, 184):
        _dot(d, x, 106, 10)
    _poly(d, [(80, 152), (176, 152)])


@icon("empty")
def _empty_box(d):
    _poly(d, [(36, 104), (128, 60), (220, 104), (128, 148)], closed=True)
    _poly(d, [(36, 104), (36, 176), (128, 220), (220, 176), (220, 104)])
    _poly(d, [(128, 148), (128, 220)])


# ------------------------------------------------------------------ rendering
def mask(name: str, size: int = OUT) -> Image.Image:
    """Greyscale (L) mask of an icon: 255 where the icon is drawn."""
    drawer = _REGISTRY.get(name)
    image = Image.new("L", (CANVAS, CANVAS), 0)
    if drawer is not None:
        drawer(ImageDraw.Draw(image))
    return image.resize((size, size), Image.LANCZOS)


def white_png(name: str, size: int = OUT) -> Image.Image:
    rgba = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    rgba.putalpha(mask(name, size))
    return rgba


def logo(size: int = 256, start: str = "#6366F1", end: str = "#8B5CF6") -> Image.Image:
    """App logo: rounded square with a gradient and a white </> glyph."""
    big = 512
    vertical = Image.linear_gradient("L").resize((big, big))
    diagonal = ImageChops.add(vertical, vertical.transpose(Image.Transpose.ROTATE_90).transpose(
        Image.Transpose.FLIP_LEFT_RIGHT), scale=2)
    gradient = Image.composite(Image.new("RGBA", (big, big), end), Image.new("RGBA", (big, big), start), diagonal)
    shape = Image.new("L", (big, big), 0)
    ImageDraw.Draw(shape).rounded_rectangle((16, 16, big - 16, big - 16), radius=120, fill=255)
    out = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    out.paste(gradient, (0, 0), shape)
    glyph = Image.new("L", (big, big), 0)
    g = ImageDraw.Draw(glyph)
    w = 44
    for pts in ([(196, 168), (124, 256), (196, 344)], [(316, 168), (388, 256), (316, 344)], [(284, 140), (228, 372)]):
        g.line(pts, fill=255, width=w, joint="curve")
        for x, y in (pts[0], pts[-1]):
            g.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=255)
    white = Image.new("RGBA", (big, big), (255, 255, 255, 255))
    out.paste(white, (0, 0), glyph)
    return out.resize((size, size), Image.LANCZOS)
