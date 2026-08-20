from __future__ import annotations

from pathlib import Path

from a_conductor.control_center import ControlCenterService
from a_conductor.desktop_control import DesktopControlService
from a_conductor.lifecycle import LifecycleAction
from a_conductor.lifecycle_executor import LifecycleExecutionResult, LifecycleExecutionState
from a_conductor.persistence import SQLiteRegistryStore


class FakeCoordinator:
    def __init__(self) -> None:
        self.calls: list[tuple[str, LifecycleAction]] = []

    def execute(self, worker_id: str, action: LifecycleAction) -> LifecycleExecutionResult:
        self.calls.append((worker_id, action))
        return LifecycleExecutionResult(
            state=LifecycleExecutionState.NOOP,
            action=action,
            reason_code="TEST_NOOP",
            transaction_id="tx-test",
        )


def test_facade_delegates_lifecycle_actions(tmp_path: Path) -> None:
    control = ControlCenterService.open(SQLiteRegistryStore(tmp_path / "control.sqlite"))
    coordinator = FakeCoordinator()
    service = DesktopControlService(control_center=control, lifecycle=coordinator)

    assert service.start_worker("a-worker-01").action is LifecycleAction.START
    assert service.stop_worker("a-worker-01").action is LifecycleAction.STOP
    assert service.restart_worker("a-worker-01").action is LifecycleAction.RESTART
    assert coordinator.calls == [
        ("a-worker-01", LifecycleAction.START),
        ("a-worker-01", LifecycleAction.STOP),
        ("a-worker-01", LifecycleAction.RESTART),
    ]


def test_facade_delegates_control_center_snapshot_and_project_actions(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    control = ControlCenterService.open(SQLiteRegistryStore(database))
    service = DesktopControlService(control_center=control, lifecycle=FakeCoordinator())
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    project = service.register_project(project_dir, display_name="Project")
    assignment = service.assign_project("a-worker-01", project.project_id)

    assert assignment.worker_id == "a-worker-01"
    assert service.snapshot() == control.snapshot()
    assert service.release_worker("a-worker-01").assignment_id is None


def test_open_uses_same_control_center_instance_for_coordinator_builder(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    captured = {}
    coordinator = FakeCoordinator()

    def builder(path, *, service):
        captured["path"] = Path(path)
        captured["service"] = service
        return coordinator

    desktop = DesktopControlService.open(database, coordinator_builder=builder)

    assert captured["path"] == database
    assert captured["service"] is desktop.control_center
    assert desktop.lifecycle is coordinator
    assert len(desktop.snapshot().workers) == 3
