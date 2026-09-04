from __future__ import annotations

import json
import threading
from dataclasses import fields
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from a_conductor.connector_recovery import ConnectorRecoveryState
from a_conductor.desktop_control import DesktopControlService
from a_conductor.local_instances import (
    InstanceHealthState,
    InstanceOrchestrationOutcome,
    InstanceResultCode,
    LocalInstance,
)
from a_conductor.serena_config_store import SQLiteSerenaConfigStore
from a_conductor.worker_resilience import recovery_hold_active

NAME = "Sunday-Worker-1"


class NullControl:
    def snapshot(self):
        raise AssertionError("snapshot not expected")


class NullLifecycle:
    def execute(self, worker_id, action):
        raise AssertionError("worker lifecycle not expected")


class _ReadyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"ready"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def _reserve_port() -> int:
    probe = ThreadingHTTPServer(("127.0.0.1", 0), _ReadyHandler)
    port = probe.server_address[1]
    probe.server_close()
    return port


class HealthServer:
    """Deterministic stand-in for the instance's real /readyz listener.
    Binds one fixed port for its whole life so restarts (the launcher
    bringing the listener back) are observable at the same address."""

    def __init__(self) -> None:
        self._port = _reserve_port()
        self._server: ThreadingHTTPServer | None = None
        self._lock = threading.Lock()
        self.start()

    def start(self) -> None:
        with self._lock:
            if self._server is not None:
                return
            self._server = ThreadingHTTPServer(("127.0.0.1", self._port), _ReadyHandler)
            threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def stop(self) -> None:
        with self._lock:
            if self._server is None:
                return
            server, self._server = self._server, None
        server.shutdown()
        server.server_close()

    @property
    def address(self) -> str:
        return f"127.0.0.1:{self._port}"

    @property
    def up(self) -> bool:
        return self._server is not None


class LaunchingOrchestrator:
    """Fake exactly at the process-launch seam: starting the instance brings
    its real /readyz listener up (mirrors tunnel-client binding the port);
    stopping tears it down. Counts every start."""

    def __init__(self, health: HealthServer) -> None:
        self._health = health
        self.start_calls: list[str] = []
        self.stop_calls: list[str] = []

    def start(self, target, *, cancel_check=None):
        if cancel_check is not None and cancel_check():
            return InstanceOrchestrationOutcome(
                "start", InstanceResultCode.START_CANCELLED, process_launched=False
            )
        self.start_calls.append(target.name)
        self._health.start()
        return InstanceOrchestrationOutcome(
            "start", InstanceResultCode.RUNNING, process_launched=True
        )

    def stop(self, target, *, force=False):
        self.stop_calls.append(target.name)
        self._health.stop()
        return InstanceOrchestrationOutcome(
            "stop", InstanceResultCode.STOPPED, exit_code=0
        )


def _service(tmp_path: Path, health: HealthServer, *, hold_provider=None):
    store = SQLiteSerenaConfigStore(tmp_path / "control.sqlite")
    target = LocalInstance(
        name=NAME,
        project_path=str(tmp_path / "project"),
        health_address=health.address,
        instance_root=tmp_path / NAME,
        tunnel_configured=True,
        tunnel_suffix="abcd",
    )
    orchestrator = LaunchingOrchestrator(health)
    svc = DesktopControlService(
        control_center=NullControl(),
        lifecycle=NullLifecycle(),
        settings_store=store,
        instances_root=tmp_path,
        instance_orchestrator=orchestrator,
        recovery_hold_provider=hold_provider,
    )
    svc.instances = lambda: (target,)
    store.set_instance_autostart(NAME, True)
    return svc, store, orchestrator


def _refresh(svc):
    return svc.instance_states_cancellable(cancel_check=lambda: False)


# ---------------- pure hold semantics ----------------

def test_hold_policy_flags_and_validation():
    assert recovery_hold_active() is False
    assert recovery_hold_active(ownership_unsafe=True) is True
    assert recovery_hold_active(task_state_unknown=True) is True
    assert recovery_hold_active(quarantined=True) is True
    with pytest.raises(ValueError):
        recovery_hold_active(ownership_unsafe=1)


# ---------------- production path: exactly-once recovery ----------------

def test_production_path_recovers_exactly_once_and_persists_to_sqlite(tmp_path):
    health = HealthServer()
    svc, store, orchestrator = _service(tmp_path, health)
    states = _refresh(svc)
    assert states[0][1] is InstanceHealthState.READY
    assert orchestrator.start_calls == []

    health.stop()  # the real failure: instance gone
    states = _refresh(svc)
    assert states[0][1] is InstanceHealthState.READY  # recovered in-path
    assert orchestrator.start_calls == [NAME]         # exactly one start
    record = store.get_connector_recovery(NAME)
    assert record.state is ConnectorRecoveryState.READY
    assert record.restart_count == 1                  # durable SQLite evidence
    assert record.recovery_suppressed is False

    for _ in range(3):  # stable observation: no duplicate restart
        _refresh(svc)
    assert orchestrator.start_calls == [NAME]
    assert store.get_connector_recovery(NAME).restart_count == 1


def test_service_recreated_from_same_sqlite_no_replay(tmp_path):
    health = HealthServer()
    svc, store, orchestrator = _service(tmp_path, health)
    _refresh(svc)
    health.stop()
    _refresh(svc)  # one recovery (launcher brought the listener back)
    for _ in range(3):
        _refresh(svc)
    assert orchestrator.start_calls == [NAME]

    # Conductor restart: fresh service + store over the SAME SQLite file
    svc2, store2, orchestrator2 = _service(tmp_path, health)
    for _ in range(3):
        _refresh(svc2)
    assert orchestrator2.start_calls == []            # no replay duplicate
    assert store2.get_connector_recovery(NAME).restart_count == 1

    # a NEW real failure after restart still recovers exactly once
    health.stop()
    _refresh(svc2)
    assert orchestrator2.start_calls == [NAME]
    assert store2.get_connector_recovery(NAME).restart_count == 2


def test_manual_stop_suppresses_recovery_across_recreate(tmp_path):
    health = HealthServer()
    svc, store, orchestrator = _service(tmp_path, health)
    _refresh(svc)
    result = svc.instance_action(NAME, "stop")  # production manual stop
    assert result.result_code is InstanceResultCode.STOPPED
    assert health.up is False

    for _ in range(3):
        _refresh(svc)
    assert orchestrator.start_calls == []             # zero auto restarts
    record = store.get_connector_recovery(NAME)
    assert record.recovery_suppressed is True         # durable manual-stop intent

    svc2, store2, orchestrator2 = _service(tmp_path, health)
    _refresh(svc2)
    assert orchestrator2.start_calls == []            # suppression survives restart


# ---------------- transient hold: never manual stop ----------------

@pytest.mark.parametrize("hold_flags", [
    {"ownership_unsafe": True},
    {"task_state_unknown": True},
])
def test_transient_hold_zero_recovery_no_suppression_then_recovers(tmp_path, hold_flags):
    health = HealthServer()
    provider_state = {"flags": hold_flags}
    svc, store, orchestrator = _service(
        tmp_path, health, hold_provider=lambda name: provider_state["flags"]
    )
    _refresh(svc)
    health.stop()
    for _ in range(3):
        _refresh(svc)
    assert orchestrator.start_calls == []             # hold: zero recovery
    record = store.get_connector_recovery(NAME)
    assert record is None or record.recovery_suppressed is False  # never manual stop

    provider_state["flags"] = {}                      # hold clears
    _refresh(svc)                                     # same real failure still down
    assert orchestrator.start_calls == [NAME]         # recovers exactly once
    record = store.get_connector_recovery(NAME)
    assert record.restart_count == 1
    assert record.recovery_suppressed is False        # no manual start needed


def test_hold_provider_failure_fails_closed(tmp_path):
    health = HealthServer()

    def broken_provider(name):
        raise RuntimeError("ownership source unavailable")

    svc, store, orchestrator = _service(tmp_path, health, hold_provider=broken_provider)
    _refresh(svc)
    health.stop()
    _refresh(svc)
    assert orchestrator.start_calls == []             # unknown hold state: fail closed


# ---------------- external control surface guarantee ----------------

def test_ready_worker_never_restarted_regardless_of_flags(tmp_path):
    health = HealthServer()
    svc, store, orchestrator = _service(
        tmp_path,
        health,
        hold_provider=lambda name: {"ownership_unsafe": True, "task_state_unknown": True},
    )
    for _ in range(3):
        states = _refresh(svc)                        # healthy local runtime
        assert states[0][1] is InstanceHealthState.READY
    assert orchestrator.start_calls == []             # READY never restarts
    record = store.get_connector_recovery(NAME)
    assert record is None or record.recovery_suppressed is False


# ---------------- durable payload carries reason codes only ----------------

def test_durable_records_carry_bounded_reason_codes_only(tmp_path):
    health = HealthServer()
    svc, store, orchestrator = _service(tmp_path, health)
    _refresh(svc)
    health.stop()
    _refresh(svc)
    record = store.get_connector_recovery(NAME)
    allowed = {"UNEXPECTED_STOPPED", "RECOVERY_START_EXCEPTION", "RECOVERY_RESULT_INVALID"}
    allowed |= {code.value for code in InstanceResultCode}
    assert record.last_exit_reason in allowed
    payload = json.dumps({f.name: getattr(record, f.name) for f in fields(record)})
    assert "stderr" not in payload
    assert "Authorization" not in payload
    assert "Bearer" not in payload
