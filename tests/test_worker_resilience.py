"""WO-P1-156 evidence/regression over the EXISTING recovery authority.

These tests add NO new recovery policy. They prove, hermetically (temp
SQLite + controllable local /readyz + a fake only at the process-launch
seam), that the production observation/recovery path already on main —
DesktopControlService.instance_states_cancellable -> instance_health_state
-> reconcile_instance_recovery -> ConnectorRecoveryCoordinator ->
SQLiteSerenaConfigStore -> LocalInstanceOrchestrator — detects unexpected
connector loss, recovers exactly once with durable state, never
double-restarts on replay, and migrates a legacy schema in place without
touching pre-existing data.
"""

from __future__ import annotations

import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from a_conductor.connector_recovery import ConnectorRecoveryState
from a_conductor.desktop_control import DesktopControlService
from a_conductor.local_instances import (
    InstanceHealthState,
    InstanceOrchestrationOutcome,
    InstanceResultCode,
    LocalInstance,
)
from a_conductor.serena_config_store import SQLiteSerenaConfigStore

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


class HealthServer:
    """Controllable stand-in for the instance's /readyz listener. Binds one
    fixed port for its whole life so launcher restarts are observable at the
    same address the production HTTP probe uses."""

    def __init__(self) -> None:
        probe = ThreadingHTTPServer(("127.0.0.1", 0), _ReadyHandler)
        self._port = probe.server_address[1]
        probe.server_close()
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


class LaunchingOrchestrator:
    """Fake exactly at the process-launch seam: starting the instance brings
    its /readyz listener back up (mirrors the connector's durable spec
    binding the health port); stopping tears it down. Counts every start."""

    def __init__(self, health: HealthServer) -> None:
        self._health = health
        self.start_calls: list[str] = []

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
        self._health.stop()
        return InstanceOrchestrationOutcome(
            "stop", InstanceResultCode.STOPPED, exit_code=0
        )


def _service(tmp_path: Path, health: HealthServer, store: SQLiteSerenaConfigStore):
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
    )
    svc.instances = lambda: (target,)
    store.set_instance_autostart(NAME, True)
    return svc, store, orchestrator


def _refresh(svc):
    return svc.instance_states_cancellable(cancel_check=lambda: False)


def _tables(db_path: Path) -> set[str]:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    names = {
        row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    con.close()
    return names


# ---------------- A. hermetic synthetic legacy-DB migration proof ----------------

def test_hermetic_legacy_db_migration_preserves_preexisting_data(tmp_path):
    """Synthetic legacy fixture (NOT a live DB): SQLiteSerenaConfigStore
    initialization adds instance_recovery in place, preserving unrelated
    tables and sentinel rows, and leaves the DB integrity-clean."""
    db_path = tmp_path / "legacy-synthetic.sqlite"
    con = sqlite3.connect(str(db_path))
    con.execute("CREATE TABLE workers (worker_id TEXT PRIMARY KEY, state TEXT)")
    con.execute("CREATE TABLE unrelated_notes (id INTEGER PRIMARY KEY, body TEXT)")
    con.execute("INSERT INTO workers VALUES ('a-worker-01', 'STOPPED')")
    con.execute("INSERT INTO workers VALUES ('a-worker-02', 'STOPPED')")
    con.execute("INSERT INTO unrelated_notes VALUES (7, 'sentinel-payload')")
    con.commit()
    con.close()

    tables_before = _tables(db_path)
    assert "instance_recovery" not in tables_before  # synthetic legacy state
    assert "workers" in tables_before

    SQLiteSerenaConfigStore(db_path).initialize()

    tables_after = _tables(db_path)
    assert "instance_recovery" in tables_after
    assert tables_before <= tables_after               # nothing dropped

    con = sqlite3.connect(str(db_path))
    rows = {
        t: con.execute(f"SELECT * FROM [{t}]").fetchall()
        for t in ("workers", "unrelated_notes")
    }
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.close()
    assert rows["workers"] == [("a-worker-01", "STOPPED"), ("a-worker-02", "STOPPED")]
    assert rows["unrelated_notes"] == [(7, "sentinel-payload")]
    assert integrity == "ok"


# ---------------- B. existing production refresh path proof ----------------

def test_production_refresh_recovers_exactly_once_with_durable_state(tmp_path):
    """Real DesktopControlService refresh loop over a temp SQLite store:
    unexpected STOPPED -> existing authority starts exactly once -> durable
    restart_count=1 -> stable refreshes never duplicate -> service/store
    recreated from the same file replay nothing -> a new genuine STOPPED
    recovers exactly once more."""
    store = SQLiteSerenaConfigStore(tmp_path / "evidence.sqlite")
    store.initialize()
    health = HealthServer()
    svc, store, orchestrator = _service(tmp_path, health, store)

    assert _refresh(svc)[0][1] is InstanceHealthState.READY
    assert orchestrator.start_calls == []

    health.stop()                                        # unexpected connector loss
    states = _refresh(svc)
    assert states[0][1] is InstanceHealthState.READY     # recovered in-path
    assert orchestrator.start_calls == [NAME]            # exactly one start
    record = store.get_connector_recovery(NAME)
    assert record.state is ConnectorRecoveryState.READY
    assert record.restart_count == 1                     # durable evidence

    for _ in range(3):                                   # stable refreshes
        _refresh(svc)
    assert orchestrator.start_calls == [NAME]
    assert store.get_connector_recovery(NAME).restart_count == 1

    # Conductor restart: fresh service/store over the SAME temp SQLite file
    store2 = SQLiteSerenaConfigStore(tmp_path / "evidence.sqlite")
    health2 = HealthServer()
    svc2, store2, orchestrator2 = _service(tmp_path, health2, store2)
    _refresh(svc2)
    assert orchestrator2.start_calls == []               # no replay duplicate
    assert store2.get_connector_recovery(NAME).restart_count == 1

    health2.stop()                                       # new genuine failure
    _refresh(svc2)
    assert orchestrator2.start_calls == [NAME]
    assert store2.get_connector_recovery(NAME).restart_count == 2


def test_manual_stop_suppresses_automatic_recovery(tmp_path):
    """Operator STOP is durable manual intent: the existing authority never
    auto-restarts a manually stopped connector, across service recreation."""
    store = SQLiteSerenaConfigStore(tmp_path / "manual.sqlite")
    store.initialize()
    health = HealthServer()
    svc, store, orchestrator = _service(tmp_path, health, store)
    _refresh(svc)

    result = svc.instance_action(NAME, "stop")           # production manual stop
    assert result.result_code is InstanceResultCode.STOPPED

    for _ in range(3):
        _refresh(svc)
    assert orchestrator.start_calls == []                # zero auto restarts
    record = store.get_connector_recovery(NAME)
    assert record.recovery_suppressed is True            # durable manual intent

    store2 = SQLiteSerenaConfigStore(tmp_path / "manual.sqlite")
    health2 = HealthServer()
    svc2, store2, orchestrator2 = _service(tmp_path, health2, store2)
    _refresh(svc2)
    assert orchestrator2.start_calls == []               # survives restart
