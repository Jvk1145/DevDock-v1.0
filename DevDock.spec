# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for DevDock: windowed, one-folder build, app icon, no UPX.
# Build with:  python -m PyInstaller --noconfirm --clean DevDock.spec
# Output:      dist\DevDock\DevDock.exe

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("customtkinter")
datas += [("assets", "assets")]

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=["darkdetect"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "_pytest", "tests", "PyInstaller"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DevDock",
    icon="assets/app.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX-packed executables are often flagged by antivirus software
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="DevDock",
)
