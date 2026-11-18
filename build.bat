@echo off
rem Build DevDock: run the tests, regenerate icons, then create dist\DevDock\DevDock.exe.
rem If Inno Setup (iscc.exe) is on PATH, the installer is built as well.
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)

echo [1/4] Installing requirements...
"%PY%" -m pip install --disable-pip-version-check -q -r requirements.txt || goto :error

echo [2/4] Running tests...
"%PY%" -m pytest -q || goto :error

echo [3/4] Generating icons...
"%PY%" scripts\make_icon.py || goto :error

echo [4/4] Building with PyInstaller...
"%PY%" -m PyInstaller --noconfirm --clean DevDock.spec || goto :error

echo.
echo Build complete: dist\DevDock\DevDock.exe

where iscc >nul 2>nul
if %errorlevel%==0 (
    echo Building installer with Inno Setup...
    iscc installer.iss || goto :error
    echo Installer: installer_output\DevDock_Setup.exe
) else (
    echo Inno Setup not found on PATH - skipping the installer. Install it from https://jrsoftware.org/isinfo.php
)
exit /b 0

:error
echo.
echo Build failed.
exit /b 1
