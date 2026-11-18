import subprocess
from pathlib import Path

from core import ide_detector
from core.ide_detector import IDEDetector


def touch(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"MZ")
    return str(path)


def make_env(tmp_path: Path) -> dict:
    env = {
        "LOCALAPPDATA": str(tmp_path / "me" / "AppData" / "Local"),
        "ProgramFiles": str(tmp_path / "Program Files"),
        "ProgramFiles(x86)": str(tmp_path / "Program Files (x86)"),
    }
    for value in env.values():
        Path(value).mkdir(parents=True, exist_ok=True)
    return env


def no_which(_name):
    return None


def test_nothing_installed(tmp_path):
    assert IDEDetector(env=make_env(tmp_path), which=no_which).detect() == {}


def test_current_user_install_only(tmp_path):
    env = make_env(tmp_path)
    # Another user's VS Code must never be picked up.
    touch(tmp_path / "other" / "AppData" / "Local" / "Programs" / "Microsoft VS Code" / "Code.exe")
    assert "vscode" not in IDEDetector(env=env, which=no_which).detect()
    mine = touch(Path(env["LOCALAPPDATA"]) / "Programs" / "Microsoft VS Code" / "Code.exe")
    found = IDEDetector(env=env, which=no_which).detect()
    assert found["vscode"].path == mine and found["vscode"].source == "local"


def test_lookup_order_custom_local_program_files(tmp_path):
    env = make_env(tmp_path)
    pf = touch(Path(env["ProgramFiles"]) / "Microsoft VS Code" / "Code.exe")
    assert IDEDetector(env=env, which=no_which).detect()["vscode"].source == "program_files"
    local = touch(Path(env["LOCALAPPDATA"]) / "Programs" / "Microsoft VS Code" / "Code.exe")
    assert IDEDetector(env=env, which=no_which).detect()["vscode"].path == local
    custom = touch(tmp_path / "portable" / "Code.exe")
    result = IDEDetector(env=env, which=no_which).detect({"vscode": custom})["vscode"]
    assert (result.path, result.source) == (custom, "custom")
    # A custom path that no longer exists falls back to detection
    result = IDEDetector(env=env, which=no_which).detect({"vscode": str(tmp_path / "gone.exe")})["vscode"]
    assert result.path == local
    assert pf


def test_jetbrains_newest_version_and_editions(tmp_path):
    env = make_env(tmp_path)
    jb = Path(env["ProgramFiles"]) / "JetBrains"
    touch(jb / "PyCharm 2024.3" / "bin" / "pycharm64.exe")
    newest = touch(jb / "PyCharm 2026.1.3" / "bin" / "pycharm64.exe")
    ce = touch(jb / "PyCharm Community Edition 2024.1" / "bin" / "pycharm64.exe")
    found = IDEDetector(env=env, which=no_which).detect()
    assert found["pycharm"].path == newest
    assert found["pycharm_ce"].path == ce


def test_jetbrains_toolbox(tmp_path):
    env = make_env(tmp_path)
    toolbox = Path(env["LOCALAPPDATA"]) / "JetBrains" / "Toolbox" / "apps"
    idea = touch(toolbox / "IDEA-U" / "ch-0" / "241.1" / "bin" / "idea64.exe")
    studio = touch(toolbox / "AndroidStudio" / "ch-0" / "233.1" / "bin" / "studio64.exe")
    found = IDEDetector(env=env, which=no_which).detect()
    assert found["intellij"].path == idea and found["intellij"].source == "toolbox"
    assert found["android_studio"].path == studio


def test_path_lookup_and_shim_resolution(tmp_path):
    env = make_env(tmp_path)
    real = touch(tmp_path / "tools" / "VSCode" / "Code.exe")
    shim = touch(tmp_path / "tools" / "VSCode" / "bin" / "code.cmd")
    subl = touch(tmp_path / "tools" / "Sublime" / "subl.exe")
    sublime_real = touch(tmp_path / "tools" / "Sublime" / "sublime_text.exe")

    def which(name):
        return {"code": shim, "subl": sublime_real}.get(name)

    found = IDEDetector(env=env, which=which).detect()
    assert found["vscode"].path == real and found["vscode"].source == "path"
    assert found["sublime"].path == sublime_real
    assert subl


def test_shim_that_points_elsewhere(tmp_path):
    env = make_env(tmp_path)
    real = touch(tmp_path / "Apps" / "IntelliJ IDEA" / "bin" / "idea64.exe")
    shim = tmp_path / "Toolbox" / "scripts" / "idea.cmd"
    shim.parent.mkdir(parents=True)
    shim.write_text(f'@echo off\nstart "" "{real}" %*\n', encoding="utf-8")
    found = IDEDetector(env=env, which=lambda n: str(shim) if n == "idea64" else None).detect()
    assert found["intellij"].path == real


def test_visual_studio_via_vswhere(tmp_path):
    env = make_env(tmp_path)
    vswhere = touch(Path(env["ProgramFiles(x86)"]) / "Microsoft Visual Studio" / "Installer" / "vswhere.exe")
    devenv = touch(tmp_path / "VS" / "Common7" / "IDE" / "devenv.exe")
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout=devenv + "\n", stderr="")

    found = IDEDetector(env=env, which=no_which, run=fake_run).detect()
    assert found["visual_studio"].path == devenv and found["visual_studio"].source == "vswhere"
    assert calls[0][0] == vswhere and "-latest" in calls[0]


def test_visual_studio_program_files(tmp_path):
    env = make_env(tmp_path)
    devenv = touch(Path(env["ProgramFiles"]) / "Microsoft Visual Studio" / "2022" / "Community" / "Common7" /
                   "IDE" / "devenv.exe")
    assert IDEDetector(env=env, which=no_which).detect()["visual_studio"].path == devenv


def test_cache_and_refresh(tmp_path):
    env = make_env(tmp_path)
    detector = IDEDetector(env=env, which=no_which)
    assert detector.detect() == {} and detector.cached == {}
    touch(Path(env["ProgramFiles"]) / "Notepad++" / "notepad++.exe")
    assert detector.detect() == {}                       # cached
    assert "notepadpp" in detector.detect(refresh=True)  # "Detect again"


def test_ide_name_lookup():
    assert ide_detector.ide_name("android_studio") == "Android Studio"
    assert ide_detector.ide_name("unknown_thing") == "unknown_thing"
    assert {d.key for d in ide_detector.DEFINITIONS} >= {
        "vscode", "cursor", "pycharm", "pycharm_ce", "intellij", "android_studio", "visual_studio",
        "sublime", "notepadpp"}
