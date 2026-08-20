from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path

import pytest

from a_conductor.control_center import (
    ControlCenterSnapshot,
    WorkerScreenRow,
)
from a_conductor.desktop_app import default_database_path, run_smoke
from a_conductor.desktop_ui import AConductorDesktopApp, DesktopTheme
from a_conductor.domain import Project, WorkerState


class FakeService:
    def __init__(self, snapshot: ControlCenterSnapshot) -> None:
        self.current = snapshot
        self.assign_calls: list[tuple[str, str]] = []
        self.release_calls: list[str] = []
        self.register_calls: list[tuple[Path, str | None]] = []

    def snapshot(self) -> ControlCenterSnapshot:
        return self.current

    def assign_project(self, worker_id: str, project_id: str, *, mutation_allowed: bool = True):
        self.assign_calls.append((worker_id, project_id))
        return object()

    def release_worker(self, worker_id: str):
        self.release_calls.append(worker_id)
        return object()

    def register_project(self, root_path, *, display_name=None, project_id=None):
        self.register_calls.append((Path(root_path), display_name))
        return object()


def sample_snapshot() -> ControlCenterSnapshot:
    project = Project("project-1", "A-Wiki", r"A:\GitHub\A-Wiki")
    workers = (
        WorkerScreenRow(
            "a-worker-01",
            "A-Worker 1",
            WorkerState.READY,
            "runtime-01",
            "assignment-1",
            project.project_id,
            project.display_name,
            project.root_path,
            True,
        ),
        WorkerScreenRow(
            "a-worker-02",
            "A-Worker 2",
            WorkerState.STOPPED,
            "runtime-02",
            None,
            None,
            None,
            None,
            None,
        ),
        WorkerScreenRow(
            "a-worker-03",
            "A-Worker 3",
            WorkerState.STOPPED,
            "runtime-03",
            None,
            None,
            None,
            None,
            None,
        ),
    )
    return ControlCenterSnapshot(projects=(project,), workers=workers, online=True)


@pytest.fixture
def root():
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


def test_default_theme_is_dark_compact_and_semantic() -> None:
    theme = DesktopTheme()
    assert theme.background.startswith("#")
    assert theme.panel.startswith("#")
    assert theme.ready != theme.error != theme.warning
    assert theme.monospace_font
    assert theme.base_font_size <= 12


def test_default_database_path_uses_localappdata_when_available(tmp_path: Path) -> None:
    path = default_database_path({"LOCALAPPDATA": str(tmp_path)})
    assert path == tmp_path / "A-Conductor" / "control-center.sqlite"


def test_default_database_path_falls_back_to_home(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    path = default_database_path({})
    assert path == tmp_path / ".a-conductor" / "control-center.sqlite"


def test_app_renders_projects_workers_and_disabled_lifecycle_controls(root) -> None:
    service = FakeService(sample_snapshot())
    app = AConductorDesktopApp(root, service=service)
    root.update_idletasks()

    assert root.title() == "A-Conductor"
    assert app.project_list.size() == 1
    assert len(app.worker_tree.get_children()) == 3
    assert app.start_button.instate(["disabled"])
    assert app.stop_button.instate(["disabled"])
    assert app.restart_button.instate(["disabled"])
    assert "ONLINE" in app.connection_label.cget("text")


def test_refresh_projects_worker_assignment_and_state(root) -> None:
    app = AConductorDesktopApp(root, service=FakeService(sample_snapshot()))
    app.refresh()
    rows = app.worker_tree.get_children()
    values = app.worker_tree.item(rows[0], "values")
    assert "READY" in values
    assert "A-Wiki" in values
    assert "a-worker-01" in values


def test_assign_selected_delegates_to_service(root) -> None:
    service = FakeService(sample_snapshot())
    app = AConductorDesktopApp(root, service=service)
    app.project_list.selection_set(0)
    worker_item = app.worker_tree.get_children()[1]
    app.worker_tree.selection_set(worker_item)
    app.worker_tree.focus(worker_item)

    app.assign_selected()

    assert service.assign_calls == [("a-worker-02", "project-1")]
    assert "Assign" in app.activity_text.get("1.0", "end")


def test_release_selected_delegates_to_service(root) -> None:
    service = FakeService(sample_snapshot())
    app = AConductorDesktopApp(root, service=service)
    worker_item = app.worker_tree.get_children()[0]
    app.worker_tree.selection_set(worker_item)
    app.worker_tree.focus(worker_item)

    app.release_selected()

    assert service.release_calls == ["a-worker-01"]


def test_add_project_uses_injected_directory_picker(root, tmp_path: Path) -> None:
    project = tmp_path / "new-project"
    project.mkdir()
    service = FakeService(sample_snapshot())
    app = AConductorDesktopApp(
        root,
        service=service,
        directory_picker=lambda: str(project),
    )

    app.add_project()

    assert service.register_calls == [(project, None)]


def test_ctrl_k_command_palette_opens_and_can_close(root) -> None:
    app = AConductorDesktopApp(root, service=FakeService(sample_snapshot()))
    palette = app.open_command_palette()
    root.update_idletasks()
    assert isinstance(palette, tk.Toplevel)
    assert palette.winfo_exists() == 1
    palette.destroy()


def test_smoke_constructs_real_service_ui_without_mainloop(tmp_path: Path) -> None:
    try:
        code, summary = run_smoke(tmp_path / "control-center.sqlite")
    except tk.TclError as exc:
        pytest.skip(f"Tk display unavailable: {exc}")
    assert code == 0
    assert summary == "A-CONDUCTOR_SMOKE_OK projects=0 workers=3"
