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
            transaction_id=f"tx-{action.value.lower()}",
            state=LifecycleExecutionState.NOOP,
            reason_code="TEST_NOOP",
        )


def test_facade_delegates_lifecycle_actions(tmp_path: Path) -> None:
    control = ControlCenterService.open(SQLiteRegistryStore(tmp_path / "control.sqlite"))
    coordinator = FakeCoordinator()
    service = DesktopControlService(control_center=control, lifecycle=coordinator)

    assert service.start_worker("a-worker-01").state is LifecycleExecutionState.NOOP
    assert service.stop_worker("a-worker-01").state is LifecycleExecutionState.NOOP
    assert service.restart_worker("a-worker-01").state is LifecycleExecutionState.NOOP
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


def _worker_config_for(root, worker_id="a-worker-01"):
    from a_conductor.serena_runtime import SerenaWorkerConfig

    return SerenaWorkerConfig(
        worker_id=worker_id,
        runtime_id="runtime-1",
        instance_root=str(root / "instance"),
        serena_home=str(root / "instance" / "serena-home"),
        health_host="127.0.0.1",
        health_port=18201,
        tunnel_binding_ref=None,
        credential_ref=None,
        runtime_executable_ref=str(root / "engine.exe"),
        profile_template_ref=str(root / "profile.yaml"),
        run_dir=str(root / "instance" / "run"),
        log_dir=str(root / "instance" / "logs"),
    )


class _FakeControlCenter:
    def __init__(self, project_root=None):
        self._project_root = project_root

    def snapshot(self):
        from a_conductor.control_center import ControlCenterSnapshot, WorkerScreenRow
        from a_conductor.domain import WorkerState

        return ControlCenterSnapshot(
            projects=(),
            workers=(
                WorkerScreenRow(
                    worker_id="a-worker-01",
                    display_name="A-Worker 1",
                    state=WorkerState.STOPPED,
                    runtime_id="runtime-1",
                    assignment_id="assignment-1" if self._project_root else None,
                    project_id="project-1" if self._project_root else None,
                    project_display_name="P" if self._project_root else None,
                    project_root_path=self._project_root,
                    mutation_allowed=True,
                ),
            ),
            online=True,
        )


class _FakeLifecycle:
    def __init__(self):
        self.calls = []

    def execute(self, worker_id, action):
        self.calls.append((worker_id, action.value))
        return object()


def test_apply_worker_settings_to_home_applied(tmp_path):
    from a_conductor.serena_config_store import SQLiteSerenaConfigStore
    from a_conductor.worker_serena_settings import WorkerSerenaSettings

    config_store = SQLiteSerenaConfigStore(tmp_path / "control.sqlite")
    config_store.save_worker_config(_worker_config_for(tmp_path))
    config_store.save_worker_settings(
        WorkerSerenaSettings(
            worker_id="a-worker-01",
            tool_timeout=777,
            project_path=r"A:\GitHub\demo",
            brain_folders=(r"A:\GitHub\A-Wiki",),
        )
    )
    service = DesktopControlService(
        control_center=_FakeControlCenter(),
        lifecycle=_FakeLifecycle(),
        settings_store=config_store,
    )

    result = service.apply_worker_settings_to_home("a-worker-01")

    written = tmp_path / "instance" / "serena-home" / "serena_config.yml"
    assert result == "APPLIED"
    text = written.read_text(encoding="utf-8")
    assert "tool_timeout: 777" in text
    assert "A:\GitHub\demo" in text
    assert "[A-CONDUCTOR SECOND BRAIN]" in text


def test_apply_worker_settings_project_fallback_from_assignment(tmp_path):
    from a_conductor.serena_config_store import SQLiteSerenaConfigStore
    from a_conductor.worker_serena_settings import WorkerSerenaSettings

    config_store = SQLiteSerenaConfigStore(tmp_path / "control.sqlite")
    config_store.save_worker_config(_worker_config_for(tmp_path))
    config_store.save_worker_settings(
        WorkerSerenaSettings(worker_id="a-worker-01")
    )
    service = DesktopControlService(
        control_center=_FakeControlCenter(project_root=r"A:\GitHub\assigned"),
        lifecycle=_FakeLifecycle(),
        settings_store=config_store,
    )

    result = service.apply_worker_settings_to_home("a-worker-01")

    assert result == "APPLIED"
    text = (tmp_path / "instance" / "serena-home" / "serena_config.yml").read_text(encoding="utf-8")
    assert r"A:\GitHub\assigned" in text


def test_apply_worker_settings_skip_codes(tmp_path):
    from a_conductor.serena_config_store import SQLiteSerenaConfigStore
    from a_conductor.worker_serena_settings import WorkerSerenaSettings

    empty_store = SQLiteSerenaConfigStore(tmp_path / "empty.sqlite")
    service = DesktopControlService(
        control_center=_FakeControlCenter(),
        lifecycle=_FakeLifecycle(),
        settings_store=empty_store,
    )
    from a_conductor.worker_serena_settings import WorkerSerenaSettings as _W

    empty_store.save_worker_settings(_W(worker_id="a-worker-01"))
    assert service.apply_worker_settings_to_home("a-worker-01") == "SKIPPED_NOT_CONFIGURED"

    config_store = SQLiteSerenaConfigStore(tmp_path / "cfg.sqlite")
    config_store.save_worker_config(_worker_config_for(tmp_path / "c"))
    service2 = DesktopControlService(
        control_center=_FakeControlCenter(),
        lifecycle=_FakeLifecycle(),
        settings_store=config_store,
    )
    assert service2.apply_worker_settings_to_home("a-worker-01") == "SKIPPED_NO_SETTINGS"

    config_store.save_worker_settings(WorkerSerenaSettings(worker_id="a-worker-01"))

    # A rogue config that escapes its instance root cannot even be persisted by
    # the store (its own validation rejects it), so prove the facade guard with
    # a stub store that hands out an unsafe config directly.
    from dataclasses import replace as _replace

    rogue_config = _replace(
        _worker_config_for(tmp_path / "c"), serena_home=str(tmp_path / "elsewhere")
    )

    class _RogueStore:
        def get_worker_settings(self, worker_id):
            return WorkerSerenaSettings(worker_id=worker_id)

        def get_worker_config(self, worker_id):
            return rogue_config

    service3 = DesktopControlService(
        control_center=_FakeControlCenter(),
        lifecycle=_FakeLifecycle(),
        settings_store=_RogueStore(),
    )
    assert service3.apply_worker_settings_to_home("a-worker-01") == "SKIPPED_TARGET_UNSAFE"


def test_start_worker_applies_settings_before_lifecycle(tmp_path):
    from a_conductor.serena_config_store import SQLiteSerenaConfigStore
    from a_conductor.worker_serena_settings import WorkerSerenaSettings

    config_store = SQLiteSerenaConfigStore(tmp_path / "control.sqlite")
    config_store.save_worker_config(_worker_config_for(tmp_path))
    config_store.save_worker_settings(
        WorkerSerenaSettings(worker_id="a-worker-01", tool_timeout=555)
    )
    lifecycle = _FakeLifecycle()
    service = DesktopControlService(
        control_center=_FakeControlCenter(),
        lifecycle=lifecycle,
        settings_store=config_store,
    )

    service.start_worker("a-worker-01")

    assert lifecycle.calls == [("a-worker-01", "START")]
    text = (tmp_path / "instance" / "serena-home" / "serena_config.yml").read_text(encoding="utf-8")
    assert "tool_timeout: 555" in text


def test_open_job_control_honors_supervised_preference(tmp_path, monkeypatch):
    from a_conductor.serena_config_store import SQLiteSerenaConfigStore
    from a_conductor.native_operations import NativeOperationDefinition, NativeOperationKind

    config_store = SQLiteSerenaConfigStore(tmp_path / "jc.sqlite")
    service = DesktopControlService(
        control_center=_FakeControlCenter(),
        lifecycle=_FakeLifecycle(),
        settings_store=config_store,
    )
    operations = (
        NativeOperationDefinition(
            operation_ref="op:pytest",
            kind=NativeOperationKind.PYTEST,
            paths=("tests",),
            timeout_seconds=60,
        ),
    )

    captured = {}
    import a_conductor.desktop_control as dc

    class _RecordingJobControl:
        def __init__(self, *, supervised, **kwargs):
            captured["supervised"] = supervised

        @classmethod
        def open(cls, *args, **kwargs):
            return cls(**kwargs)

    import a_conductor.job_control as jc

    monkeypatch.setattr(jc, "DurableJobControlService", _RecordingJobControl)

    jobs = service.open_job_control(tmp_path / "jc.sqlite", operations)
    assert isinstance(jobs, _RecordingJobControl)
    assert captured["supervised"] is True  # default ON per user decision

    config_store.set_preference("supervised", False)
    service.open_job_control(tmp_path / "jc.sqlite", operations)
    assert captured["supervised"] is False


def test_open_job_control_requires_settings_store(tmp_path):
    from a_conductor.serena_config_store import SerenaConfigStoreError

    service = DesktopControlService(
        control_center=_FakeControlCenter(),
        lifecycle=_FakeLifecycle(),
    )
    try:
        service.open_job_control(tmp_path / "x.sqlite", ())
    except SerenaConfigStoreError as exc:
        assert "SETTINGS_STORE_NOT_AVAILABLE" in str(exc)
    else:
        raise AssertionError("missing store accepted")
