from __future__ import annotations

from pathlib import Path

import a_conductor.desktop_control as desktop_control
from a_conductor.connector_recovery import ConnectorRecoveryRecord, ConnectorRecoveryState
from a_conductor.desktop_control import DesktopControlService
from a_conductor.desktop_ui import AConductorDesktopApp
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


class RecordingOrchestrator:
    def __init__(self) -> None:
        self.start_calls: list[str] = []

    def start(self, target, *, cancel_check=None):
        if cancel_check is not None and cancel_check():
            return InstanceOrchestrationOutcome(
                "start", InstanceResultCode.START_CANCELLED, process_launched=False
            )
        self.start_calls.append(target.name)
        return InstanceOrchestrationOutcome(
            "start", InstanceResultCode.RUNNING, process_launched=True
        )

    def stop(self, target, *, force=False):
        return InstanceOrchestrationOutcome(
            "stop", InstanceResultCode.STOPPED, exit_code=0
        )


class FakeText:
    def __init__(self) -> None:
        self.text = ""

    def winfo_exists(self):
        return True

    def configure(self, **_kwargs):
        pass

    def delete(self, *_args):
        self.text = ""

    def insert(self, _index, text):
        self.text = text

    def yview_moveto(self, _fraction):
        pass


def _instance(root: Path) -> LocalInstance:
    return LocalInstance(
        name="Sunday-Worker-1",
        project_path=str(root / "project"),
        health_address="127.0.0.1:18901",
        instance_root=root / "Sunday-Worker-1",
        tunnel_configured=False,
    )


def _service(tmp_path: Path) -> tuple[DesktopControlService, SQLiteSerenaConfigStore, RecordingOrchestrator]:
    store = SQLiteSerenaConfigStore(tmp_path / "control.sqlite")
    store.set_instance_autostart("Sunday-Worker-1", True)
    orchestrator = RecordingOrchestrator()
    service = DesktopControlService(
        control_center=NullControl(),
        lifecycle=NullLifecycle(),
        settings_store=store,
        instances_root=tmp_path,
        instance_orchestrator=orchestrator,
    )
    target = _instance(tmp_path)
    service.instances = lambda: (target,)
    return service, store, orchestrator


def test_recovery_diagnostic_reads_existing_record(tmp_path: Path) -> None:
    service, store, _ = _service(tmp_path)
    record = ConnectorRecoveryRecord(
        instance_name="Sunday-Worker-1",
        state=ConnectorRecoveryState.DEGRADED,
        failure_count=3,
        restart_count=2,
        last_exit_reason="RECOVERY_START_EXCEPTION",
        last_exit_at=1_788_000_000.0,
        updated_at=1_788_000_000.0,
    )
    store.save_connector_recovery(record)

    assert service.connector_recovery_record("Sunday-Worker-1") == record


def test_successful_auto_recovery_emits_one_drainable_event(
    tmp_path: Path, monkeypatch
) -> None:
    service, _store, orchestrator = _service(tmp_path)
    monkeypatch.setattr(
        desktop_control,
        "instance_health_state",
        lambda _instance: InstanceHealthState.STOPPED,
    )

    states = service.instance_states_cancellable(cancel_check=lambda: False)

    assert states[0][1] is InstanceHealthState.READY
    assert orchestrator.start_calls == ["Sunday-Worker-1"]
    first = service.drain_connector_recovery_events()
    assert len(first) == 1
    assert first[0].instance_name == "Sunday-Worker-1"
    assert first[0].restart_count == 1
    assert service.drain_connector_recovery_events() == ()


def test_repeated_ready_observation_does_not_duplicate_recovery_event(
    tmp_path: Path, monkeypatch
) -> None:
    service, _store, orchestrator = _service(tmp_path)
    health = {"value": InstanceHealthState.STOPPED}
    monkeypatch.setattr(
        desktop_control,
        "instance_health_state",
        lambda _instance: health["value"],
    )

    service.instance_states_cancellable(cancel_check=lambda: False)
    assert len(service.drain_connector_recovery_events()) == 1
    health["value"] = InstanceHealthState.READY
    service.instance_states_cancellable(cancel_check=lambda: False)

    assert orchestrator.start_calls == ["Sunday-Worker-1"]
    assert service.drain_connector_recovery_events() == ()


def test_explicit_stop_never_emits_auto_recover_event(tmp_path: Path, monkeypatch) -> None:
    service, _store, orchestrator = _service(tmp_path)
    service.instance_action("Sunday-Worker-1", "stop")
    monkeypatch.setattr(
        desktop_control,
        "instance_health_state",
        lambda _instance: InstanceHealthState.STOPPED,
    )

    states = service.instance_states_cancellable(cancel_check=lambda: False)

    assert states[0][1] is InstanceHealthState.STOPPED
    assert orchestrator.start_calls == []
    assert service.drain_connector_recovery_events() == ()


class RenderService:
    def instance_aliases(self):
        return {}


class EventService(RenderService):
    def __init__(self, records):
        self.records = list(records)

    def drain_connector_recovery_events(self):
        records = tuple(self.records)
        self.records.clear()
        return records


def _bare_app(service) -> AConductorDesktopApp:
    app = object.__new__(AConductorDesktopApp)
    app.service = service
    app.monitor_text = FakeText()
    return app


def test_monitor_renders_recovery_diagnostics_separately_from_connection() -> None:
    app = _bare_app(RenderService())
    recovery = ConnectorRecoveryRecord(
        instance_name="Sunday-Worker-1",
        state=ConnectorRecoveryState.RECOVERING,
        failure_count=2,
        restart_count=4,
        last_exit_reason="UNEXPECTED_STOPPED",
        last_exit_at=1_788_000_000.0,
        next_retry_at=1_788_000_015.0,
        updated_at=1_788_000_000.0,
    )
    report = {
        "state": "STOPPED",
        "pid": None,
        "memory_mb": None,
        "log_file": None,
        "errors": [],
        "tail": [],
        "recovery": recovery,
    }
    app._render_monitor("Sunday-Worker-1", report)

    assert "STOPPED" in app.monitor_text.text
    assert "recovery: RECOVERING" in app.monitor_text.text
    assert "restarts 4" in app.monitor_text.text
    assert "failures 2" in app.monitor_text.text
    assert "UNEXPECTED_STOPPED" in app.monitor_text.text
    assert "next retry" in app.monitor_text.text


def test_auto_recover_activity_logs_each_drained_event_once() -> None:
    record = ConnectorRecoveryRecord(
        instance_name="Sunday-Worker-1",
        state=ConnectorRecoveryState.READY,
        restart_count=3,
        updated_at=1_788_000_000.0,
    )
    service = EventService([record])
    app = _bare_app(service)
    lines: list[str] = []
    app.log_activity = lines.append

    app._log_connector_recovery_events()
    app._log_connector_recovery_events()

    assert lines == ["AUTO-RECOVER Sunday-Worker-1 READY restart=3"]


def test_diagnostic_read_failure_cannot_replay_old_restart_event(tmp_path: Path) -> None:
    service, store, _orchestrator = _service(tmp_path)
    old = ConnectorRecoveryRecord(
        instance_name="Sunday-Worker-1",
        state=ConnectorRecoveryState.READY,
        restart_count=7,
        updated_at=1_788_000_000.0,
    )
    store.save_connector_recovery(old)
    service.connector_recovery_record = lambda _name: None

    record = service.reconcile_instance_recovery(
        "Sunday-Worker-1",
        InstanceHealthState.READY,
    )

    assert record.restart_count == 7
    assert service.drain_connector_recovery_events() == ()
