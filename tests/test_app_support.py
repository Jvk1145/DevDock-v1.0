import importlib
import json
import os
import sys
import threading
import uuid

import pytest

from core.single_instance import SingleInstance


def test_single_instance_activation(tmp_path):
    name = f"DevDockTest-{uuid.uuid4().hex}"
    info_file = tmp_path / "instance.json"
    first = SingleInstance(name, info_file)
    assert first.acquire() is True
    activated = threading.Event()
    first.listen(activated.set)
    data = json.loads(info_file.read_text(encoding="utf-8"))
    assert data["pid"] == os.getpid() and data["port"] > 0 and len(data["token"]) == 32

    second = SingleInstance(name, info_file)
    assert second.acquire() is False            # already running
    assert second.notify_existing() is True
    assert activated.wait(5)

    first.release()
    assert not info_file.exists()
    third = SingleInstance(name, info_file)
    assert third.acquire() is True               # free again after release
    third.release()


def test_wrong_token_is_ignored(tmp_path):
    name = f"DevDockTest-{uuid.uuid4().hex}"
    info_file = tmp_path / "instance.json"
    owner = SingleInstance(name, info_file)
    owner.acquire()
    activated = threading.Event()
    owner.listen(activated.set)
    data = json.loads(info_file.read_text(encoding="utf-8"))
    info_file.write_text(json.dumps({**data, "token": "0" * 32}), encoding="utf-8")
    assert SingleInstance(name, info_file).notify_existing() is True
    assert not activated.wait(1.5)
    owner.release()


def test_notify_without_running_instance(tmp_path):
    assert SingleInstance("nobody", tmp_path / "missing.json").notify_existing() is False


def test_data_folder_override(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVDOCK_HOME", str(tmp_path / "Dev Dock ü"))
    import config
    reloaded = importlib.reload(config)
    try:
        assert reloaded.APP_DIR == (tmp_path / "Dev Dock ü").resolve()
        assert reloaded.DB_PATH.parent == reloaded.APP_DIR
        assert reloaded.LOG_FILE.parent == reloaded.LOG_DIR
        reloaded.ensure_dirs()
        assert reloaded.BACKUP_DIR.is_dir() and reloaded.LOG_DIR.is_dir()
    finally:
        monkeypatch.delenv("DEVDOCK_HOME")
        importlib.reload(config)


def test_default_data_folder_is_appdata(monkeypatch, tmp_path):
    monkeypatch.delenv("DEVDOCK_HOME", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    import config
    reloaded = importlib.reload(config)
    try:
        assert reloaded.APP_DIR == tmp_path / "Roaming" / "DevDock"
    finally:
        importlib.reload(config)


def test_icon_art_and_make_icon(tmp_path, monkeypatch):
    from ui import icon_art
    assert {"folder", "terminal", "git", "run", "edit", "delete", "star", "settings"} <= set(icon_art.names())
    mask = icon_art.mask("folder")
    assert mask.size == (64, 64) and mask.getextrema()[1] == 255
    logo = icon_art.logo(64)
    assert logo.mode == "RGBA" and logo.size == (64, 64)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_virtual_screen_helper():
    from ui.main_window import _virtual_screen

    class Fake:
        def winfo_screenwidth(self):
            return 1920

        def winfo_screenheight(self):
            return 1080

    x, y, w, h = _virtual_screen(Fake())
    assert w > 0 and h > 0
