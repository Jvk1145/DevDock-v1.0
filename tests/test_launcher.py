import base64
import os

import pytest

from core import launcher
from core.errors import LaunchError
from core.launcher import Launcher
from core.models import ASK_EVERY_TIME, IDE, Project


class FakePopen:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    def __call__(self, args, **kwargs):
        if self.error:
            raise self.error
        self.calls.append((args, kwargs))


def exe(tmp_path, name="Code.exe"):
    path = tmp_path / "bin" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"MZ")
    return str(path)


def proj_dir(tmp_path, name="My Project ü"):
    path = tmp_path / name
    path.mkdir(exist_ok=True)
    return str(path)


def test_ide_command_is_argument_list(tmp_path):
    ide = IDE("vscode", "VS Code", r"C:\Apps\Code.exe", "local")
    cmd = launcher.ide_command(ide, r"C:\My Projects\app/")
    assert cmd.args == [r"C:\Apps\Code.exe", r"C:\My Projects\app"]
    assert cmd.creationflags & launcher.DETACHED_PROCESS


def test_notepadpp_opens_folder_as_workspace():
    cmd = launcher.ide_command(IDE("notepadpp", "Notepad++", r"C:\npp\notepad++.exe", "path"), r"C:\x")
    assert cmd.args == [r"C:\npp\notepad++.exe", "-openFoldersAsWorkspace", r"C:\x"]


def test_terminal_prefers_windows_terminal():
    cmd = launcher.terminal_command(r"C:\a b", which=lambda n: r"C:\wt.exe" if n.startswith("wt") else None)
    assert cmd.args == [r"C:\wt.exe", "-d", r"C:\a b"]


def test_terminal_falls_back_to_powershell():
    ps = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
    cmd = launcher.terminal_command(r"C:\a b", which=lambda n: ps if n.startswith("powershell") else None)
    assert cmd.args[0] == ps and cmd.cwd == r"C:\a b"
    assert cmd.creationflags == launcher.CREATE_NEW_CONSOLE


def test_run_command_encodes_script():
    cmd = launcher.run_command(r"C:\proj", "streamlit run app.py; echo 'hi'", which=lambda n: None,
                               env={"SystemRoot": r"C:\Windows"})
    assert "-EncodedCommand" in cmd.args
    payload = cmd.args[cmd.args.index("-EncodedCommand") + 1]
    script = base64.b64decode(payload).decode("utf-16-le")
    assert script.endswith("streamlit run app.py; echo 'hi'")
    assert cmd.cwd == r"C:\proj"


def test_run_command_inside_windows_terminal():
    cmd = launcher.run_command(r"C:\proj", "npm start", which=lambda n: r"C:\wt.exe" if n.startswith("wt") else None)
    assert cmd.args[:3] == [r"C:\wt.exe", "-d", r"C:\proj"]
    assert ";" not in " ".join(cmd.args)     # wt treats ';' as a separator


def test_resolve_ide_order():
    vscode = IDE("vscode", "VS Code", "c", "local")
    pycharm = IDE("pycharm", "PyCharm", "p", "local")
    ides = {"vscode": vscode, "pycharm": pycharm}
    p = Project(name="x", folder_path="y")
    assert launcher.resolve_ide(p, ides, None) is None                  # ask
    assert launcher.resolve_ide(p, ides, "pycharm") is pycharm          # default
    p.preferred_ide = "vscode"
    assert launcher.resolve_ide(p, ides, "pycharm") is vscode           # preferred wins
    p.preferred_ide = ASK_EVERY_TIME
    assert launcher.resolve_ide(p, ides, "pycharm") is None
    p.preferred_ide = "cursor"
    with pytest.raises(LaunchError) as exc:
        launcher.resolve_ide(p, ides, "pycharm")
    assert exc.value.kind == LaunchError.IDE_MISSING and exc.value.ide_key == "cursor"


def test_open_in_ide_validates_folder_and_exe(tmp_path):
    popen = FakePopen()
    lx = Launcher(popen=popen)
    ide = IDE("vscode", "VS Code", exe(tmp_path), "local")
    with pytest.raises(LaunchError) as exc:
        lx.open_in_ide(str(tmp_path / "missing"), ide)
    assert exc.value.kind == LaunchError.FOLDER_MISSING
    with pytest.raises(LaunchError) as exc:
        lx.open_in_ide(proj_dir(tmp_path), IDE("vscode", "VS Code", str(tmp_path / "nope.exe"), "custom"))
    assert exc.value.kind == LaunchError.IDE_MISSING
    assert popen.calls == []
    folder = proj_dir(tmp_path)
    lx.open_in_ide(folder, ide)
    args, kwargs = popen.calls[0]
    assert args == [ide.path, folder]
    assert "shell" not in kwargs and kwargs["cwd"] == folder


def test_os_errors_become_friendly(tmp_path):
    lx = Launcher(popen=FakePopen(error=PermissionError("Access is denied")))
    with pytest.raises(LaunchError) as exc:
        lx.open_in_ide(proj_dir(tmp_path), IDE("vscode", "VS Code", exe(tmp_path), "local"))
    assert exc.value.user_message == "Windows could not start the program."
    assert "Access is denied" in exc.value.detail


def test_folder_terminal_run(tmp_path):
    popen = FakePopen()
    lx = Launcher(popen=popen, which=lambda n: None, env={"SystemRoot": r"C:\Windows"})
    folder = proj_dir(tmp_path)
    lx.open_folder(folder)
    lx.open_terminal(folder)
    lx.run_start_command(folder, "python app.py")
    assert popen.calls[0][0] == [os.path.join(r"C:\Windows", "explorer.exe"), folder]
    assert popen.calls[1][1]["cwd"] == folder
    with pytest.raises(LaunchError):
        lx.run_start_command(folder, "   ")


def test_open_url():
    opened = []
    lx = Launcher(open_browser=lambda u: opened.append(u) or True)
    lx.open_url("https://github.com/a/b")
    assert opened == ["https://github.com/a/b"]
    with pytest.raises(LaunchError):
        lx.open_url("tesdt5")
