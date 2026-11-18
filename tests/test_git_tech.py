import json
import shutil
import subprocess

import pytest

from core import tech_detector
from core.git_service import GitService

GIT = shutil.which("git")
needs_git = pytest.mark.skipif(GIT is None, reason="git is not installed")


def git(cwd, *args):
    subprocess.run([GIT, *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / "repo with space"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.email", "test@example.com")
    git(path, "config", "user.name", "Test")
    git(path, "config", "commit.gpgsign", "false")
    (path / "a.txt").write_text("a", encoding="utf-8")
    git(path, "add", "a.txt")
    git(path, "commit", "-q", "-m", "first commit")
    return path


@needs_git
def test_git_info(repo):
    service = GitService()
    info = service.get_info(str(repo))
    assert info.branch == "main" and info.changes == 0
    assert info.last_commit_message == "first commit" and info.last_commit_at
    (repo / "b.txt").write_text("b", encoding="utf-8")
    (repo / "a.txt").write_text("changed", encoding="utf-8")
    service.invalidate()
    assert service.get_info(str(repo)).changes == 2


@needs_git
def test_git_cache_ttl(repo):
    now = [0.0]
    service = GitService(ttl=60, clock=lambda: now[0])
    assert service.cached(str(repo)) == (False, None)
    first = service.get_info(str(repo))
    (repo / "new.txt").write_text("x", encoding="utf-8")
    assert service.get_info(str(repo)) == first        # served from cache
    now[0] = 61
    assert service.get_info(str(repo)).changes == 1    # expired -> refreshed


@needs_git
def test_not_a_repo_and_missing_folder(tmp_path):
    service = GitService()
    assert service.get_info(str(tmp_path)) is None
    assert service.get_info(str(tmp_path / "missing")) is None


@needs_git
def test_empty_repo_has_no_commit(tmp_path):
    git(tmp_path, "init", "-q", "-b", "dev")
    info = GitService().get_info(str(tmp_path))
    assert info.branch == "dev" and info.last_commit_at is None


@needs_git
def test_submit_runs_in_thread_pool(repo):
    service = GitService()
    assert service.submit(str(repo)).result(timeout=10).branch == "main"
    service.shutdown()


def test_git_missing(tmp_path):
    service = GitService(which=lambda _n: None)
    assert not service.available
    assert service.get_info(str(tmp_path)) is None


def write(folder, name, content=""):
    path = folder / name
    path.write_text(content, encoding="utf-8")


@pytest.mark.parametrize("files,expected", [
    ({"requirements.txt": "numpy\npandas"}, "Python"),
    ({"requirements.txt": "Flask==3.0"}, "Flask"),
    ({"requirements.txt": "streamlit"}, "Streamlit"),
    ({"pyproject.toml": "[project]\ndependencies=['fastapi']"}, "FastAPI"),
    ({"manage.py": "", "requirements.txt": "django"}, "Django"),
    ({"package.json": json.dumps({"dependencies": {"react": "18"}})}, "React"),
    ({"package.json": json.dumps({"dependencies": {"next": "14", "react": "18"}})}, "Next.js"),
    ({"package.json": json.dumps({"devDependencies": {"vue": "3"}})}, "Vue"),
    ({"package.json": "{}"}, "Node.js"),
    ({"package.json": "{broken"}, "Node.js"),
    ({"pom.xml": ""}, "Java"),
    ({"build.gradle": ""}, "Java"),
    ({"App.csproj": ""}, "C#"),
    ({"CMakeLists.txt": ""}, "C++"),
    ({"pubspec.yaml": ""}, "Flutter"),
    ({"Sales.pbix": ""}, "Power BI"),
    ({"analysis.ipynb": "{}"}, "Jupyter"),
    ({"analysis.ipynb": "{}", "helpers.py": ""}, "Python"),
    ({"notes.txt": ""}, None),
])
def test_detect(tmp_path, files, expected):
    for name, content in files.items():
        write(tmp_path, name, content)
    assert tech_detector.detect(tmp_path) == expected


def test_detect_missing_folder(tmp_path):
    assert tech_detector.detect(tmp_path / "nope") is None


def test_scan_parent(tmp_path):
    (tmp_path / "api").mkdir()
    write(tmp_path / "api", "requirements.txt", "fastapi")
    (tmp_path / "web").mkdir()
    write(tmp_path / "web", "package.json", "{}")
    (tmp_path / "repo-only" / ".git").mkdir(parents=True)
    (tmp_path / "photos").mkdir()
    (tmp_path / "node_modules").mkdir()
    write(tmp_path / "node_modules", "package.json", "{}")
    (tmp_path / ".hidden").mkdir()
    from core.project_service import folder_key
    found = tech_detector.scan_parent(tmp_path, registered={folder_key(str(tmp_path / "web"))})
    assert [(c.name, c.technology, c.already_added) for c in found] == [
        ("api", "FastAPI", False), ("repo-only", "Other", False), ("web", "Node.js", True)]
