from __future__ import annotations

from pathlib import Path

import a_conductor.desktop_ui as desktop_ui
from a_conductor.desktop_control import DesktopControlService
from a_conductor.desktop_ui import AConductorDesktopApp, graph_monitor_lines
from a_conductor.graph.dispatch import GraphDispatchKey
from a_conductor.graph.domain import TaskEdge, TaskNode, TaskNodeStatus
from a_conductor.graph.graph import build_graph
from a_conductor.graph.operator_view import read_graph_operator_snapshot
from a_conductor.graph.store import GraphStore
from a_conductor.serena_config_store import SQLiteSerenaConfigStore
from a_conductor.job_store import SQLiteJobStore


class NullControl:
    def snapshot(self):
        raise AssertionError("snapshot not expected")


class NullLifecycle:
    def execute(self, worker_id, action):
        raise AssertionError("lifecycle not expected")


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


def _graph():
    return build_graph(
        [TaskNode(id="a", objective="prepare"), TaskNode(id="b", objective="finish")],
        [TaskEdge("a", "b")],
    )


def _service(tmp_path: Path) -> DesktopControlService:
    database = tmp_path / "control.sqlite"
    settings = SQLiteSerenaConfigStore(database)
    settings.initialize()
    SQLiteJobStore(database).initialize()
    GraphStore(database).save_graph(_graph(), "graph-1")
    return DesktopControlService(
        control_center=NullControl(),
        lifecycle=NullLifecycle(),
        settings_store=settings,
        instances_root=tmp_path,
    )


def _bare_app(service) -> AConductorDesktopApp:
    app = object.__new__(AConductorDesktopApp)
    app.service = service
    app.root = object()
    app.monitor_text = FakeText()
    app._monitor_mode = "connector"
    app._graph_monitor_graph_id = None
    app._graph_monitor_run_id = None
    return app

def test_desktop_control_exposes_read_only_graph_operator_snapshot(tmp_path: Path) -> None:
    service = _service(tmp_path)

    assert service.operator_graph_ids() == ("graph-1",)
    snapshot = service.operator_graph_snapshot("graph-1")

    assert snapshot.graph_id == "graph-1"
    assert snapshot.runtime_evidence is False


def test_graph_monitor_lines_label_planning_only_as_no_run_evidence(tmp_path: Path) -> None:
    service = _service(tmp_path)
    snapshot = read_graph_operator_snapshot(
        service.settings_store.database_path,
        "graph-1",
    )

    lines = graph_monitor_lines(snapshot)
    text = "\n".join(lines)

    assert "MONITOR · GRAPH" in text
    assert "GRAPH graph-1" in text
    assert "RUNTIME: NO RUN EVIDENCE" in text
    assert "TODO 2" in text
    assert "a -> b" in text
    assert "timeline: -" in text

def test_graph_monitor_lines_label_explicit_run_evidence(tmp_path: Path) -> None:
    service = _service(tmp_path)
    database = service.settings_store.database_path
    key = GraphDispatchKey("graph-1", "run-1", "a")
    SQLiteJobStore(database).create_job(
        job_id=key.job_id, work_order_ref="wo:ge11", project_id="project-1"
    )
    snapshot = read_graph_operator_snapshot(database, "graph-1", "run-1")

    text = "\n".join(graph_monitor_lines(snapshot))

    assert "RUN run-1" in text
    assert "RUNTIME: DURABLE RUN EVIDENCE" in text
    assert "TODO 2" in text


def test_graph_monitor_lines_show_unproven_requested_run_without_claiming_evidence(tmp_path: Path) -> None:
    service = _service(tmp_path)
    snapshot = read_graph_operator_snapshot(
        service.settings_store.database_path, "graph-1", "run-unknown"
    )

    text = "\n".join(graph_monitor_lines(snapshot))

    assert "RUN run-unknown" in text
    assert "RUNTIME: NO RUN EVIDENCE" in text
    assert "DURABLE RUN EVIDENCE" not in text


def test_open_graph_monitor_uses_explicit_context_without_latest_inference(
    tmp_path: Path, monkeypatch
) -> None:
    app = _bare_app(_service(tmp_path))
    responses = iter(["graph-1", ""])
    monkeypatch.setattr(
        desktop_ui.simpledialog,
        "askstring",
        lambda *_args, **_kwargs: next(responses),
    )
    refreshed: list[bool] = []
    app._refresh_monitor_async = lambda: refreshed.append(True)

    app.open_graph_monitor()

    assert app._monitor_mode == "graph"
    assert app._graph_monitor_graph_id == "graph-1"
    assert app._graph_monitor_run_id is None
    assert refreshed == [True]

def test_render_graph_monitor_writes_copyable_text(tmp_path: Path) -> None:
    app = _bare_app(_service(tmp_path))
    snapshot = app.service.operator_graph_snapshot("graph-1")

    app._render_graph_monitor(snapshot)

    assert "MONITOR · GRAPH" in app.monitor_text.text
    assert "RUNTIME: NO RUN EVIDENCE" in app.monitor_text.text


def test_show_connector_monitor_restores_existing_monitor_mode(tmp_path: Path) -> None:
    app = _bare_app(_service(tmp_path))
    app._monitor_mode = "graph"
    app._graph_monitor_graph_id = "graph-1"
    app._graph_monitor_run_id = "run-1"
    refreshed: list[bool] = []
    app._refresh_monitor_async = lambda: refreshed.append(True)

    app.show_connector_monitor()

    assert app._monitor_mode == "connector"
    assert refreshed == [True]


def test_completed_graph_future_cannot_render_after_switch_to_connector(tmp_path: Path) -> None:
    from concurrent.futures import Future

    app = _bare_app(_service(tmp_path))
    snapshot = app.service.operator_graph_snapshot("graph-1")
    future = Future()
    future.set_result((snapshot, None))
    app._closing = False
    app._monitor_mode = "connector"
    app._monitor_future = future
    app._monitor_refresh_pending = True
    app._monitor_poll_after_id = None
    app._graph_monitor_graph_id = "graph-1"
    app._graph_monitor_run_id = None
    rendered: list[object] = []
    scheduled: list[tuple] = []
    app._render_graph_monitor = lambda *args: rendered.append(args)
    app._cancel_after = lambda _callback_id: None
    app._schedule_after = lambda delay, callback, *args: scheduled.append(
        (delay, callback, args)
    ) or "scheduled"

    app._poll_graph_monitor(future, "graph-1", None)

    assert rendered == []
    assert len(scheduled) == 1
    assert scheduled[0][0] == 0
    assert scheduled[0][1].__name__ == "_refresh_monitor_async"


# --- WO134: graph evidence exact-link reuse (RED-first) ---


def test_wo134_graph_evidence_links_exact_match_only(tmp_path) -> None:
    from a_conductor.desktop_ui import provider_graph_evidence_links
    from a_conductor.graph.operator_view import read_graph_operator_snapshot

    service = _service(tmp_path)
    database = service.settings_store.database_path
    expected_a = GraphDispatchKey("graph-1", "run-1", "a").job_id
    SQLiteJobStore(database).create_job(
        job_id=expected_a, work_order_ref="wo:wo134-graph", project_id="project-1"
    )
    snapshot = read_graph_operator_snapshot(database, "graph-1", "run-1")
    assert snapshot.runtime_evidence is True

    links = provider_graph_evidence_links(snapshot, "graph-1", "run-1")
    expected_b = GraphDispatchKey("graph-1", "run-1", "b").job_id
    assert links == {expected_a: "a", expected_b: "b"}

    # near-miss run id derives different job ids -> no false link
    wrong = GraphDispatchKey("graph-1", "run-2", "a").job_id
    assert wrong not in links

    # missing explicit context never links
    assert provider_graph_evidence_links(snapshot, "graph-1", None) == {}
    assert provider_graph_evidence_links(snapshot, None, "run-1") == {}
    assert provider_graph_evidence_links(None, "graph-1", "run-1") == {}


def test_wo134_graph_evidence_requires_durable_runtime_evidence(tmp_path) -> None:
    from a_conductor.desktop_ui import provider_graph_evidence_links
    from a_conductor.graph.operator_view import read_graph_operator_snapshot

    service = _service(tmp_path)
    snapshot = read_graph_operator_snapshot(
        service.settings_store.database_path, "graph-1", "run-without-durable-jobs"
    )
    assert snapshot.runtime_evidence is False
    assert provider_graph_evidence_links(
        snapshot, "graph-1", "run-without-durable-jobs"
    ) == {}
