from datetime import datetime, timedelta, timezone

import pytest

from core import timeutil
from core.models import Project
from core.validators import (is_valid_url, normalize_path, parse_tags, validate_folder, validate_name,
                             validate_project, validate_url)


@pytest.mark.parametrize("url,ok", [
    ("https://github.com/user/repo", True), ("http://localhost:8501", True),
    ("github.com/user", False), ("ftp://x.com", False), ("https://", False), ("https://a b.com", False),
])
def test_urls(url, ok):
    assert is_valid_url(url) is ok
    assert (validate_url(url) is None) is ok


def test_empty_url_is_allowed():
    assert validate_url("") is None


def test_tags():
    assert parse_tags(" a, B ,b,, c  d ") == ["a", "B", "c d"]
    assert parse_tags(None) == []


def test_name_rules():
    assert validate_name("  ") is not None
    assert validate_name("x" * 81) is not None
    assert validate_name("Taken", lambda n: True) == "A project with this name already exists."
    assert validate_name("Fine", lambda n: False) is None


def test_folder_rules(tmp_path):
    assert validate_folder("") is not None
    assert validate_folder("relative\\path") is not None
    assert validate_folder(str(tmp_path / "missing")) == "This folder does not exist."
    assert validate_folder(str(tmp_path / "missing"), must_exist=False) is None
    assert validate_folder(f'"{tmp_path}"') is None


def test_normalize_path():
    assert normalize_path("  C:/a/b/../c  ") == "C:\\a\\c"
    assert normalize_path(None) == ""


def test_validate_project(tmp_path):
    good = Project(name="X", folder_path=str(tmp_path))
    assert validate_project(good) == {}
    bad = Project(name="X", folder_path=str(tmp_path), status="Weird", start_command="a\nb",
                  tags=[f"t{i}" for i in range(11)])
    assert set(validate_project(bad)) == {"status", "start_command", "tags"}


def test_settings_roundtrip(settings):
    assert settings.theme == "dark" and settings.accent == "Indigo" and settings.default_ide is None
    settings.theme = "light"
    settings.accent = "Emerald"
    settings.default_ide = "vscode"
    settings.default_status = "On Hold"
    settings.set("window_geometry", "1200x700+10+20")
    settings.set_many({"view_mode": "list", "sort": "name"})
    assert (settings.theme, settings.accent, settings.default_ide, settings.default_status) == \
        ("light", "Emerald", "vscode", "On Hold")
    assert settings.get("window_geometry") == "1200x700+10+20"
    assert settings.view_mode == "list" and settings.sort == "name"
    with pytest.raises(ValueError):
        settings.theme = "neon"


def test_settings_bad_values_fall_back(settings):
    settings.db.execute("INSERT INTO settings(key, value) VALUES('theme', '{broken')")
    assert settings.theme == "dark"


def test_ide_paths(settings):
    settings.set_ide_path("vscode", "C:/Tools/Code.exe")
    assert settings.ide_paths() == {"vscode": "C:\\Tools\\Code.exe"}
    settings.set_ide_path("vscode", "")
    assert settings.ide_paths() == {}


def test_humanize():
    now = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)

    def ago(**kw):
        return timeutil.humanize((now - timedelta(**kw)).strftime(timeutil.FORMAT), now)

    assert ago(seconds=5) == "just now"
    assert ago(minutes=5) == "5 min ago"
    assert ago(hours=1) == "1 hour ago"
    assert ago(hours=2) == "2 hours ago"
    assert ago(days=1) == "yesterday"
    assert ago(days=3) == "3 days ago"
    assert ago(days=200) == "Jun 24, 2025"
    assert timeutil.humanize(None) == "" and timeutil.humanize("garbage") == ""
