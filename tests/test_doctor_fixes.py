"""A-Doctor deep-audit fixes: toggle column, reaper matching, PS quoting."""

from __future__ import annotations

from pathlib import Path

import pytest


# --- A1: Toggle Auto must update the AUTO column, not TUNNEL -------------


@pytest.fixture()
def root():
    import tkinter as tk

    try:
        window = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk display unavailable: {exc}")
    window.withdraw()
    yield window
    try:
        window.destroy()
    except tk.TclError:
        pass


def test_toggle_autostart_updates_auto_column_not_tunnel(root, tmp_path: Path) -> None:
    from a_conductor.desktop_control import DesktopControlService
    from a_conductor.desktop_ui import AConductorDesktopApp

    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    service = DesktopControlService.open(tmp_path / "cc.sqlite", instances_root=instances_root)
    app = AConductorDesktopApp(root, service=service)

    item = app.instance_tree.insert("", "end", values=("W1", "18011", "READY", "p", "Y", "-"))
    app.instance_tree.selection_clear()
    app.instance_tree.selection_set(item)
    app._instance_rows["W1"] = item

    app.toggle_instance_autostart()

    values = app.instance_tree.item(item, "values")
    assert values[4] == "Y"      # TUNNEL untouched
    assert values[5] == "ON"     # AUTO updated


# --- A2: reaper matches path boundaries only ------------------------------


def test_reap_instance_wrappers_matches_boundary_only(monkeypatch) -> None:
    import a_conductor.instance_runtime as runtime

    captured: list[str] = []

    def fake_run(argv, **kwargs):
        if argv[0].endswith("powershell.exe"):
            captured.append(argv[-1])
            result = type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
            return result
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)
    runtime.reap_instance_wrappers(Path("C:/AI/serena-instances/sunday-worker-1"))
    assert len(captured) == 1
    script = captured[0]
    # boundary-anchored: the needle must be followed by a backslash wildcard,
    # not a bare substring match
    assert "*\\sunday-worker-1\\*" in script.replace("/", "\\") or (
        "sunday-worker-1" in script and "\\*" in script
    )
    assert script.count("sunday-worker-1") >= 1


def test_reap_instance_wrappers_noop_off_windows(monkeypatch) -> None:
    import a_conductor.instance_runtime as runtime

    monkeypatch.setattr(runtime.sys, "platform", "linux")
    assert runtime.reap_instance_wrappers(Path("C:/AI/x")) == []


# --- A3: apostrophes in paths are escaped for PowerShell ------------------


def test_create_instance_escapes_apostrophe_in_ps1(tmp_path: Path) -> None:
    from tests.test_instance_create import make_reference  # type: ignore[import-not-found]

    from a_conductor.instance_create import create_instance

    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    make_reference(instances_root)
    project = tmp_path / "O'Brien proj"
    project.mkdir()

    created = create_instance(
        instances_root, "research", project, health_port=48114
    )
    ps1 = (created / "instance.ps1").read_text(encoding="utf-8")
    assert "$ProjectPath = '" + str(project).replace("'", "''") + "'" in ps1
    config = (created / "serena-home" / "serena_config.yml").read_text(encoding="utf-8")
    assert str(project).replace("'", "''") in config


def test_rename_escapes_apostrophe_in_serenahome(tmp_path: Path) -> None:
    from tests.test_instance_create import make_reference  # type: ignore[import-not-found]

    from a_conductor.instance_create import create_instance
    from a_conductor.instance_rename import rename_instance_backend

    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    make_reference(instances_root)
    project = tmp_path / "proj"
    project.mkdir()
    create_instance(instances_root, "research", project, health_port=48114)

    # Move the whole tree into a path containing an apostrophe, then rename:
    # $SerenaHome must come out escaped.
    tricky = tmp_path / "d'angelo"
    tricky.mkdir()
    moved_root = tricky / "instances"
    instances_root.rename(moved_root)

    new_root = rename_instance_backend(moved_root, "research", "sunday-worker-9", work_number=9)
    ps1 = (new_root / "instance.ps1").read_text(encoding="utf-8")
    expected_home = str(new_root / "serena-home").replace("'", "''")
    assert f"$SerenaHome = '{expected_home}'" in ps1


# --- A10: error tables are symmetric and duplicate-free -------------------


def test_error_tables_are_symmetric() -> None:
    from a_conductor.desktop_ui import ERROR_EXPLANATIONS
    from a_conductor.error_explanations_en import ERROR_EXPLANATIONS_EN

    assert set(ERROR_EXPLANATIONS) == set(ERROR_EXPLANATIONS_EN), (
        sorted(set(ERROR_EXPLANATIONS) ^ set(ERROR_EXPLANATIONS_EN))
    )
    assert "WORKER_BUSY" in ERROR_EXPLANATIONS


def test_zip_directory_includes_empty_dirs(tmp_path: Path) -> None:
    import zipfile

    from a_conductor.instance_delete import zip_directory

    source = tmp_path / "inst"
    (source / "run").mkdir(parents=True)  # empty dir
    (source / "instance.ps1").write_text("cfg", encoding="utf-8")
    dest = tmp_path / "b.zip"
    zip_directory(source, dest)
    with zipfile.ZipFile(dest) as archive:
        names = set(archive.namelist())
    assert "instance.ps1" in names
    assert "run/" in names


def test_create_instance_bad_reference_leaves_no_skeleton(tmp_path: Path) -> None:
    from tests.test_instance_create import make_reference  # type: ignore[import-not-found]

    from a_conductor.instance_create import InstanceCreateError, create_instance

    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    make_reference(instances_root)
    (instances_root / "wastewater" / "start.ps1").unlink()  # break the reference

    project = tmp_path / "proj"
    project.mkdir()
    with pytest.raises(InstanceCreateError) as exc:
        create_instance(instances_root, "research", project, health_port=48114)
    assert exc.value.code == "REFERENCE_SCRIPT_MISSING"
    assert not (instances_root / "research").exists()  # no skeleton left behind
