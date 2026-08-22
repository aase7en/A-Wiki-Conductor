"""WO-P1-060 PR-C: connector display-name alias + guarded delete with zip backup."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from tests.test_instance_create import make_reference  # type: ignore[import-not-found]

from a_conductor.desktop_control import DesktopControlService
from a_conductor.instance_create import create_instance
from a_conductor.instance_delete import InstanceManageError, zip_directory
from a_conductor.local_instances import discover_local_instances
from a_conductor.serena_config_store import SQLiteSerenaConfigStore


# --- store ---------------------------------------------------------------


def test_display_name_round_trip_and_clear(tmp_path: Path) -> None:
    store = SQLiteSerenaConfigStore(tmp_path / "store.sqlite")
    assert store.get_instance_display_name("Serena-Research") is None
    store.set_instance_display_name("Serena-Research", "งานวิจัย")
    assert store.get_instance_display_name("Serena-Research") == "งานวิจัย"
    store.set_instance_display_name("Serena-Research", "Research chat")
    assert store.get_instance_display_name("Serena-Research") == "Research chat"
    store.clear_instance_display_name("Serena-Research")
    assert store.get_instance_display_name("Serena-Research") is None


def test_clear_instance_flags_removes_autostart(tmp_path: Path) -> None:
    store = SQLiteSerenaConfigStore(tmp_path / "store.sqlite")
    store.set_instance_autostart("Serena-Research", True)
    assert "Serena-Research" in store.list_instance_autostart()
    store.clear_instance_flags("Serena-Research")
    assert "Serena-Research" not in store.list_instance_autostart()


# --- zip helper ----------------------------------------------------------


def test_zip_directory_captures_tree(tmp_path: Path) -> None:
    source = tmp_path / "instance"
    (source / "profiles").mkdir(parents=True)
    (source / "profiles" / "serena-x.yaml.template").write_text("data", encoding="utf-8")
    (source / "instance.ps1").write_text("cfg", encoding="utf-8")
    dest = tmp_path / "backup.zip"

    zip_directory(source, dest)

    with zipfile.ZipFile(dest) as archive:
        names = set(archive.namelist())
    assert "instance.ps1" in names
    assert "profiles/serena-x.yaml.template" in names


# --- facade --------------------------------------------------------------


@pytest.fixture()
def service(tmp_path: Path) -> DesktopControlService:
    instances_root = tmp_path / "instances"
    instances_root.mkdir()
    make_reference(instances_root)
    project = tmp_path / "proj"
    project.mkdir()
    svc = DesktopControlService.open(
        tmp_path / "cc.sqlite", instances_root=instances_root
    )
    svc.create_instance("Research", str(project))
    return svc


def test_rename_instance_stores_alias(service: DesktopControlService) -> None:
    service.rename_instance("Serena-Research", "งานวิจัย")
    aliases = service.instance_aliases()
    assert aliases.get("Serena-Research") == "งานวิจัย"
    # real instance identity unchanged
    names = {instance.name for instance in service.instances()}
    assert "Serena-Research" in names


def test_rename_instance_rejects_blank(service: DesktopControlService) -> None:
    with pytest.raises(Exception):
        service.rename_instance("Serena-Research", "   ")


def test_delete_instance_zips_and_removes(service: DesktopControlService, tmp_path: Path) -> None:
    service.set_instance_autostart("Serena-Research", True)
    backup_dir = tmp_path / "backups"

    removed_zip = service.delete_instance(
        "Serena-Research", backup_dir=backup_dir
    )

    assert removed_zip.is_file()
    assert removed_zip.suffix == ".zip"
    names = {instance.name for instance in service.instances()}
    assert "Serena-Research" not in names
    # instance folder gone from disk
    remaining = {instance.name for instance in discover_local_instances(service.instances_root)}
    assert "Serena-Research" not in remaining
    # flags cleaned
    assert "Serena-Research" not in service.autostart_instance_names()
    assert service.instance_aliases().get("Serena-Research") is None


def test_delete_instance_unknown_name(service: DesktopControlService, tmp_path: Path) -> None:
    with pytest.raises(InstanceManageError) as exc:
        service.delete_instance("Serena-Missing", backup_dir=tmp_path / "b")
    assert exc.value.code == "INSTANCE_NOT_FOUND"


def test_delete_instance_stop_failure_blocks_delete(
    service: DesktopControlService, tmp_path: Path, monkeypatch
) -> None:
    from a_conductor.local_instances import InstanceHealthState
    import a_conductor.local_instances as local_instances

    monkeypatch.setattr(
        local_instances, "instance_health_state", lambda _i: InstanceHealthState.READY
    )

    def refuse(_name, _action):
        raise RuntimeError("stop failed")

    monkeypatch.setattr(service, "instance_action", refuse)
    with pytest.raises(InstanceManageError) as exc:
        service.delete_instance("Serena-Research", backup_dir=tmp_path / "b")
    assert exc.value.code == "INSTANCE_STOP_REQUIRED"
    names = {instance.name for instance in service.instances()}
    assert "Serena-Research" in names  # untouched


# --- UI ------------------------------------------------------------------


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


class ImmediateExecutor:
    def submit(self, fn, *args, **kwargs):
        class _Future:
            def done(self) -> bool:
                return True

            def result(self):
                return fn(*args, **kwargs)

        return _Future()


def make_app(root, service: DesktopControlService):
    from a_conductor.desktop_ui import AConductorDesktopApp

    app = AConductorDesktopApp(
        root, service=service, background_executor=ImmediateExecutor()
    )
    app.refresh_instances()
    root.update()  # let the async instance-tree population run
    return app


def test_instance_bar_has_rename_and_delete_buttons(root, service) -> None:
    app = make_app(root, service)
    assert app.rename_instance_button is not None
    assert app.delete_instance_button is not None


def test_rename_selected_instance_flow(root, service) -> None:
    app = make_app(root, service)
    item = app._instance_rows["Serena-Research"]
    app.instance_tree.selection_clear()
    app.instance_tree.selection_set(item)
    app.rename_selected_instance("งานวิจัย")
    assert service.instance_aliases().get("Serena-Research") == "งานวิจัย"


def test_delete_selected_instance_flow(root, service, tmp_path, monkeypatch) -> None:
    app = make_app(root, service)
    monkeypatch.setattr(app, "_confirm", lambda message: True)
    item = app._instance_rows["Serena-Research"]
    app.instance_tree.selection_clear()
    app.instance_tree.selection_set(item)
    app.delete_selected_instance(backup_dir=tmp_path / "backups")
    names = {instance.name for instance in service.instances()}
    assert "Serena-Research" not in names
