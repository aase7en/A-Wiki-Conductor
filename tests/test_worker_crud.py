"""WO-P1-060 PR-A: worker slot add / rename / delete through the service."""

from __future__ import annotations

from pathlib import Path

import pytest

from a_conductor.control_center import ControlCenterError, ControlCenterService
from a_conductor.domain import WorkerState
from a_conductor.persistence import SQLiteRegistryStore
from a_conductor.registry import (
    ControlPlaneRegistry,
    RegistryNotFoundError,
    WorkerBusyError,
)


def open_service(tmp_path: Path) -> ControlCenterService:
    return ControlCenterService.open(SQLiteRegistryStore(tmp_path / "control-center.sqlite"))


# --- registry primitives -------------------------------------------------


def test_registry_unregister_worker_rejects_assigned_and_missing() -> None:
    registry = ControlPlaneRegistry.with_default_workers(size=1)
    registry.register_project  # noqa: B018 - documented below
    registry.unregister_worker("a-worker-01")  # free + STOPPED -> ok
    with pytest.raises(RegistryNotFoundError):
        registry.unregister_worker("a-worker-01")


def test_registry_rename_worker_display_name() -> None:
    registry = ControlPlaneRegistry.with_default_workers(size=1)
    updated = registry.rename_worker("a-worker-01", "Sunday-works 1")
    assert updated.display_name == "Sunday-works 1"
    assert registry.get_worker("a-worker-01").display_name == "Sunday-works 1"
    with pytest.raises(RegistryNotFoundError):
        registry.rename_worker("missing", "x")


# --- service: add --------------------------------------------------------


def test_add_worker_auto_ids_after_existing_max(tmp_path: Path) -> None:
    service = open_service(tmp_path)
    worker = service.add_worker()
    assert worker.worker_id == "a-worker-04"
    assert worker.display_name == "A-Worker 4"

    again = service.add_worker(display_name="Sub-agent A")
    assert again.worker_id == "a-worker-05"
    assert again.display_name == "Sub-agent A"

    ids = [w.worker_id for w in service.snapshot().workers]
    assert ids == ["a-worker-01", "a-worker-02", "a-worker-03", "a-worker-04", "a-worker-05"]


def test_add_worker_persists_across_reopen(tmp_path: Path) -> None:
    service = open_service(tmp_path)
    service.add_worker()
    reopened = open_service(tmp_path)
    assert len(reopened.snapshot().workers) == 4


def test_add_worker_skips_gaps_in_numbering(tmp_path: Path) -> None:
    service = open_service(tmp_path)
    service.delete_worker("a-worker-02")
    added = service.add_worker()
    assert added.worker_id == "a-worker-04"  # max(1,3)+1, no reuse


# --- service: rename -----------------------------------------------------


def test_rename_worker_display_name_round_trip(tmp_path: Path) -> None:
    service = open_service(tmp_path)
    updated = service.rename_worker("a-worker-01", "Main Chat")
    assert updated.display_name == "Main Chat"
    reopened = open_service(tmp_path)
    assert reopened.snapshot().workers[0].display_name == "Main Chat"


def test_rename_worker_rejects_blank_and_missing(tmp_path: Path) -> None:
    service = open_service(tmp_path)
    with pytest.raises(ControlCenterError):
        service.rename_worker("a-worker-01", "   ")
    with pytest.raises(ControlCenterError):
        service.rename_worker("missing", "x")


# --- service: delete -----------------------------------------------------


def test_delete_worker_persists_across_reopen(tmp_path: Path) -> None:
    service = open_service(tmp_path)
    removed = service.delete_worker("a-worker-03")
    assert removed.worker_id == "a-worker-03"
    ids = [w.worker_id for w in service.snapshot().workers]
    assert "a-worker-03" not in ids
    reopened = open_service(tmp_path)
    assert [w.worker_id for w in reopened.snapshot().workers] == [
        "a-worker-01",
        "a-worker-02",
    ]


def test_delete_worker_rejects_assigned(tmp_path: Path) -> None:
    service = open_service(tmp_path)
    project = service.register_project(tmp_path)
    service.assign_project("a-worker-01", project.project_id)
    with pytest.raises(ControlCenterError) as excinfo:
        service.delete_worker("a-worker-01")
    assert "WORKER" in str(excinfo.value)


def test_delete_worker_rejects_running(tmp_path: Path) -> None:
    service = open_service(tmp_path)
    service.set_worker_state("a-worker-01", WorkerState.BUSY)
    with pytest.raises(ControlCenterError):
        service.delete_worker("a-worker-01")


def test_delete_worker_missing_raises(tmp_path: Path) -> None:
    service = open_service(tmp_path)
    with pytest.raises(ControlCenterError):
        service.delete_worker("missing")


# --- facade --------------------------------------------------------------


def test_facade_delegates_worker_crud(tmp_path: Path) -> None:
    from a_conductor.desktop_control import DesktopControlService

    service = DesktopControlService.open(tmp_path / "control-center.sqlite")

    added = service.add_worker(display_name="Sub-agent")
    assert added.worker_id == "a-worker-04"

    renamed = service.rename_worker("a-worker-04", "Sub-agent 2")
    assert renamed.display_name == "Sub-agent 2"

    removed = service.delete_worker("a-worker-04")
    assert removed.worker_id == "a-worker-04"
    assert len(service.snapshot().workers) == 3


# --- UI ------------------------------------------------------------------


@pytest.fixture
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


def make_app(root, tmp_path: Path):
    from a_conductor.desktop_control import DesktopControlService
    from a_conductor.desktop_ui import AConductorDesktopApp

    service = DesktopControlService.open(tmp_path / "ui.sqlite")
    return AConductorDesktopApp(root, service=service)


def select_first_worker(app) -> str:
    children = app.worker_tree.get_children()
    app.worker_tree.selection_clear()
    app.worker_tree.selection_set(children[0])
    return app.selected_worker_id()


def test_worker_toolbar_has_crud_buttons(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    assert app.add_worker_button is not None
    assert app.rename_worker_button is not None
    assert app.delete_worker_button is not None


def test_add_worker_slot_through_ui(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    app.add_worker_slot("Sub-agent A")
    ids = [w.worker_id for w in app.service.snapshot().workers]
    assert "a-worker-04" in ids


def test_rename_selected_worker_through_ui(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)
    worker_id = select_first_worker(app)
    app.rename_selected_worker("Main Chat")
    row = next(
        w for w in app.service.snapshot().workers if w.worker_id == worker_id
    )
    assert row.display_name == "Main Chat"


def test_delete_selected_worker_with_confirm(root, tmp_path: Path, monkeypatch) -> None:
    app = make_app(root, tmp_path)
    children = app.worker_tree.get_children()
    app.worker_tree.selection_clear()
    app.worker_tree.selection_set(children[2])
    monkeypatch.setattr(app, "_confirm", lambda message: True)
    app.delete_selected_worker()
    ids = [w.worker_id for w in app.service.snapshot().workers]
    assert "a-worker-03" not in ids


def test_delete_selected_worker_declined_keeps_worker(
    root, tmp_path: Path, monkeypatch
) -> None:
    app = make_app(root, tmp_path)
    select_first_worker(app)
    monkeypatch.setattr(app, "_confirm", lambda message: False)
    app.delete_selected_worker()
    assert len(app.service.snapshot().workers) == 3


def test_delete_without_selection_shows_error(root, tmp_path: Path, monkeypatch) -> None:
    app = make_app(root, tmp_path)
    codes: list[str] = []
    monkeypatch.setattr(app, "_handle_error", lambda code: codes.append(code))
    app.delete_selected_worker()
    assert codes == ["SELECT_WORKER"]
