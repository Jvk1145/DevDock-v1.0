import json
import os

import pytest

from core.errors import ImportExportError, NotFoundError, ValidationError
from core.models import ASK_EVERY_TIME, FolderCandidate, Project


def make(projects, folder, name, **kw):
    return projects.create(Project(name=name, folder_path=folder(name), **kw))


def test_create_and_get(projects, folder):
    p = make(projects, folder, "Alpha", technology="Python", tags=["ml", " ML ", "web"],
             github_url="https://github.com/a/b", start_command="python app.py")
    got = projects.get(p.id)
    assert got.name == "Alpha"
    assert got.tags == ["ml", "web"]
    assert got.folder_path == os.path.normpath(got.folder_path)
    assert got.created_at and got.updated_at and got.last_opened is None


def test_validation_errors(projects, tmp_path):
    with pytest.raises(ValidationError) as exc:
        projects.create(Project(name="", folder_path=str(tmp_path / "missing"), github_url="nope"))
    assert set(exc.value.errors) == {"name", "folder_path", "github_url"}


def test_unique_name_case_insensitive(projects, folder):
    make(projects, folder, "Alpha")
    with pytest.raises(ValidationError) as exc:
        projects.create(Project(name="alpha", folder_path=folder("other")))
    assert "name" in exc.value.errors
    assert projects.unique_name("ALPHA") == "ALPHA (2)"


def test_update(projects, folder):
    p = make(projects, folder, "Alpha", tags=["a"])
    p.description = "new"
    p.tags = ["b"]
    p.preferred_ide = "vscode"
    updated = projects.update(p)
    assert updated.description == "new" and updated.tags == ["b"] and updated.preferred_ide == "vscode"
    assert projects.all_tags() == ["b"]   # orphan tag "a" cleaned up


def test_update_can_keep_own_name(projects, folder):
    p = make(projects, folder, "Alpha")
    p.status = "Completed"
    assert projects.update(p).status == "Completed"


def test_delete(projects, folder):
    p = make(projects, folder, "Alpha")
    projects.delete(p.id)
    with pytest.raises(NotFoundError):
        projects.get(p.id)
    with pytest.raises(NotFoundError):
        projects.delete(p.id)


def test_search_filter_sort(projects, folder):
    a = make(projects, folder, "Alpha", technology="Python", status="Active", tags=["ml"])
    b = make(projects, folder, "beta", technology="React", status="Completed", description="web shop")
    c = make(projects, folder, "Gamma 100%", technology="Python", status="On Hold", tags=["web"])
    assert {p.name for p in projects.list_projects(search="web")} == {b.name, c.name}
    assert [p.name for p in projects.list_projects(search="100%")] == ["Gamma 100%"]
    assert [p.name for p in projects.list_projects(search="ph_")] == []   # '_' is literal, not a wildcard
    assert [p.name for p in projects.list_projects(status="Completed")] == ["beta"]
    assert {p.name for p in projects.list_projects(technology="python")} == {"Alpha", "Gamma 100%"}
    assert [p.name for p in projects.list_projects(tag="ML")] == ["Alpha"]
    assert [p.name for p in projects.list_projects(sort="name")] == ["Alpha", "beta", "Gamma 100%"]
    assert [p.name for p in projects.list_projects(sort="newest")][0] == "Gamma 100%"
    projects.mark_opened(a.id)
    assert projects.list_projects(sort="recent")[0].name == "Alpha"
    assert projects.technologies() == ["Python", "React"]


def test_favorites_and_recent(projects, folder):
    a = make(projects, folder, "Alpha")
    b = make(projects, folder, "Beta")
    assert projects.toggle_favorite(a.id) is True
    assert [p.name for p in projects.pinned()] == ["Alpha"]
    assert projects.toggle_favorite(a.id) is False
    assert projects.pinned() == []
    assert projects.recent() == []
    projects.mark_opened(b.id)
    assert [p.name for p in projects.recent()] == ["Beta"]


def test_preferred_ide_and_relocate(projects, folder, tmp_path):
    p = make(projects, folder, "Alpha")
    projects.set_preferred_ide(p.id, ASK_EVERY_TIME)
    assert projects.get(p.id).preferred_ide == ASK_EVERY_TIME
    new_place = folder("moved here")
    assert projects.relocate(p.id, new_place).folder_path == os.path.normpath(new_place)
    with pytest.raises(ValidationError):
        projects.relocate(p.id, str(tmp_path / "nowhere"))


def test_find_missing_and_stats(projects, folder):
    a = make(projects, folder, "Alpha", status="Completed")
    b = make(projects, folder, "Beta")
    os.rmdir(b.folder_path)
    all_projects = projects.list_projects()
    missing = projects.find_missing(all_projects)
    assert missing == {b.id}
    stats = projects.stats(all_projects, missing)
    assert stats == {"total": 2, "missing": 1, "Active": 1, "Completed": 1, "On Hold": 0}
    assert a.id not in missing


def test_add_many_skips_registered(projects, folder):
    existing = make(projects, folder, "Alpha")
    result = projects.add_many([
        FolderCandidate(existing.folder_path, "Alpha", "Python"),
        FolderCandidate(folder("new one"), "Alpha", "React"),
    ])
    assert result.added == 1 and result.skipped == 1
    assert {p.name for p in projects.list_projects()} == {"Alpha", "Alpha (2)"}


def test_export_import_roundtrip(projects, folder, tmp_path):
    make(projects, folder, "Alpha", tags=["x"], favorite=True, technology="Python")
    make(projects, folder, "Beta")
    out = tmp_path / "export.json"
    assert projects.export_json(out) == 2
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["format"] == "devdock-projects" and len(data["projects"]) == 2

    for p in projects.list_projects():
        projects.delete(p.id)
    result = projects.import_json(out)
    assert result.added == 2
    alpha = [p for p in projects.list_projects() if p.name == "Alpha"][0]
    assert alpha.tags == ["x"] and alpha.favorite and alpha.technology == "Python"


def test_import_duplicates(projects, folder, tmp_path):
    a = make(projects, folder, "Alpha")
    items = [
        {"name": "Alpha", "folder_path": a.folder_path},                    # exact duplicate
        {"name": "Alpha", "folder_path": "D:\\elsewhere"},                  # same name, other folder
        {"name": "Remote", "folder_path": "D:\\not\\on\\this\\pc"},          # missing folder is allowed
        {"name": "", "folder_path": "x"},
        "garbage",
    ]
    skip = projects.import_projects(items, on_duplicate="skip")
    assert (skip.added, skip.skipped, len(skip.errors)) == (1, 2, 2)
    rename = projects.import_projects(items, on_duplicate="rename")
    assert rename.added == 1
    assert "Alpha (2)" in {p.name for p in projects.list_projects()}


@pytest.mark.parametrize("content", ["{not json", '{"format": "other", "projects": []}', '{"projects": 5}'])
def test_import_rejects_bad_files(projects, tmp_path, content):
    path = tmp_path / "bad.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ImportExportError):
        projects.import_json(path)


def test_import_accepts_bare_list_with_bom(projects, tmp_path):
    path = tmp_path / "list.json"
    path.write_text(json.dumps([{"name": "Solo", "folder_path": "C:\\x"}]), encoding="utf-8-sig")
    assert projects.import_json(path).added == 1
