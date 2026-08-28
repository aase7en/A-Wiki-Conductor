from __future__ import annotations

from pathlib import Path

from a_conductor.connector_recovery import ConnectorRecoveryRecord, ConnectorRecoveryState
from a_conductor.desktop_control import DesktopControlService
from a_conductor.local_instances import (
    InstanceHealthState,
    InstanceOrchestrationOutcome,
    InstanceResultCode,
    LocalInstance,
)
from a_conductor.serena_config_store import SQLiteSerenaConfigStore


class NullControl:
    def snapshot(self):
        raise AssertionError("snapshot not expected")


class NullLifecycle:
    def execute(self, worker_id, action):
        raise AssertionError("worker lifecycle not expected")


def instance(root: Path) -> LocalInstance:
    return LocalInstance(
        name="Sunday-Worker-1",
        project_path=str(root / "project"),
        health_address="127.0.0.1:18901",
        instance_root=root / "Sunday-Worker-1",
        tunnel_configured=True,
        tunnel_suffix="abcd",
    )
class RecordingOrchestrator:
    def __init__(self, store: SQLiteSerenaConfigStore) -> None:
        self.store = store
        self.start_calls: list[str] = []
        self.stop_calls: list[str] = []
        self.start_seen = None
        self.stop_seen = None

    def start(self, target, *, cancel_check=None):
        self.start_calls.append(target.name)
        self.start_seen = self.store.get_connector_recovery(target.name)
        return InstanceOrchestrationOutcome("start", InstanceResultCode.RUNNING, process_launched=True)

    def stop(self, target, *, force=False):
        self.stop_calls.append(target.name)
        self.stop_seen = self.store.get_connector_recovery(target.name)
        return InstanceOrchestrationOutcome("stop", InstanceResultCode.STOPPED, exit_code=0)


def service(tmp_path: Path):
    store = SQLiteSerenaConfigStore(tmp_path / "control.sqlite")
    target = instance(tmp_path)
    orchestrator = RecordingOrchestrator(store)
    svc = DesktopControlService(
        control_center=NullControl(),
        lifecycle=NullLifecycle(),
        settings_store=store,
        instances_root=tmp_path,
        instance_orchestrator=orchestrator,
    )
    svc.instances = lambda: (target,)
    return svc, store, orchestrator
def test_explicit_stop_persists_suppression_before_stop_call(tmp_path: Path) -> None:
    svc, store, orchestrator = service(tmp_path)
    store.set_instance_autostart("Sunday-Worker-1", True)

    result = svc.instance_action("Sunday-Worker-1", "stop")

    assert result.result_code is InstanceResultCode.STOPPED
    assert orchestrator.stop_seen is not None
    assert orchestrator.stop_seen.recovery_suppressed is True
    assert orchestrator.stop_seen.state is ConnectorRecoveryState.STOPPED


def test_manual_start_clears_degraded_budget_before_start_call(tmp_path: Path) -> None:
    svc, store, orchestrator = service(tmp_path)
    store.save_connector_recovery(
        ConnectorRecoveryRecord(
            instance_name="Sunday-Worker-1",
            state=ConnectorRecoveryState.DEGRADED,
            recovery_suppressed=True,
            failure_count=3,
            failure_window_started_at=10.0,
            updated_at=20.0,
        )
    )

    result = svc.instance_action("Sunday-Worker-1", "start")

    assert result.result_code is InstanceResultCode.RUNNING
    assert orchestrator.start_seen is not None
    assert orchestrator.start_seen.recovery_suppressed is False
    assert orchestrator.start_seen.failure_count == 0
def test_reconcile_stopped_autostart_uses_existing_orchestrator_start(tmp_path: Path) -> None:
    svc, store, orchestrator = service(tmp_path)
    store.set_instance_autostart("Sunday-Worker-1", True)

    record = svc.reconcile_instance_recovery(
        "Sunday-Worker-1", InstanceHealthState.STOPPED
    )

    assert record.state is ConnectorRecoveryState.READY
    assert record.restart_count == 1
    assert orchestrator.start_calls == ["Sunday-Worker-1"]


def test_explicit_stop_then_reconcile_never_restarts(tmp_path: Path) -> None:
    svc, store, orchestrator = service(tmp_path)
    store.set_instance_autostart("Sunday-Worker-1", True)
    svc.instance_action("Sunday-Worker-1", "stop")

    record = svc.reconcile_instance_recovery(
        "Sunday-Worker-1", InstanceHealthState.STOPPED
    )

    assert record.state is ConnectorRecoveryState.STOPPED
    assert record.recovery_suppressed is True
    assert orchestrator.start_calls == []


def test_manual_stop_serializes_with_inflight_auto_recovery(tmp_path: Path) -> None:
    import threading
    import time

    svc, store, orchestrator = service(tmp_path)
    store.set_instance_autostart("Sunday-Worker-1", True)
    entered = threading.Event()
    release = threading.Event()
    original_start = orchestrator.start

    def blocking_start(target, *, cancel_check=None):
        entered.set()
        assert release.wait(2.0)
        return original_start(target, cancel_check=cancel_check)

    orchestrator.start = blocking_start
    recovery = threading.Thread(
        target=lambda: svc.reconcile_instance_recovery(
            "Sunday-Worker-1", InstanceHealthState.STOPPED
        )
    )
    recovery.start()
    assert entered.wait(1.0)
    stopped = threading.Event()

    def manual_stop():
        svc.instance_action("Sunday-Worker-1", "stop")
        stopped.set()

    stop_thread = threading.Thread(target=manual_stop)
    stop_thread.start()
    time.sleep(0.05)
    assert orchestrator.stop_calls == []
    assert not stopped.is_set()

    release.set()
    recovery.join(2.0)
    stop_thread.join(2.0)

    assert not recovery.is_alive()
    assert not stop_thread.is_alive()
    assert orchestrator.stop_calls == ["Sunday-Worker-1"]
    record = store.get_connector_recovery("Sunday-Worker-1")
    assert record is not None
    assert record.recovery_suppressed is True
    assert record.state is ConnectorRecoveryState.STOPPED
