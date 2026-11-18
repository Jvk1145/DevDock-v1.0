"""Generate assets/app.ico (multi-size), assets/logo.png and assets/icons/*.png with Pillow.

Usage:  python scripts/make_icon.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ui import icon_art  # noqa: E402

ICO_SIZES = [(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (128, 128), (256, 256)]


def main() -> int:
    assets = ROOT / "assets"
    icons = assets / "icons"
    icons.mkdir(parents=True, exist_ok=True)
    for name in icon_art.names():
        icon_art.white_png(name).save(icons / f"{name}.png")
    logo = icon_art.logo(256)
    logo.save(assets / "logo.png")
    logo.save(assets / "app.ico", sizes=ICO_SIZES)
    print(f"Wrote {len(icon_art.names())} icons to {icons}")
    print(f"Wrote {assets / 'app.ico'} ({len(ICO_SIZES)} sizes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
