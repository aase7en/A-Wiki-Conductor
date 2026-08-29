"""GE-11 read-only graph operator projection.

The operator surface consumes existing graph/job durability. It never creates,
migrates, transitions, checkpoints, dispatches, retries, or infers a current run.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from ..domain import RecoveryClassification, TaskState
from ..job_state import JobRuntimeState
from ..job_store import JobStoreError
from .dispatch import GraphDispatchKey
from .domain import DependencyType, TaskEdge, TaskGraph, TaskNodeStatus
from .graph import TaskGraphBuilder
from .lifecycle_bridge import project_graph_node_states
from .store import _json_to_node


class GraphOperatorViewError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class GraphOperatorNode:
    node_id: str
    objective: str
    status: TaskNodeStatus
    worker_id: str | None = None

@dataclass(frozen=True, slots=True)
class GraphOperatorEdge:
    from_id: str
    to_id: str
    dependency_type: DependencyType


@dataclass(frozen=True, slots=True)
class GraphOperatorEvent:
    node_id: str
    sequence_no: int
    event_type: str
    recorded_at: str
    from_state: str | None = None
    to_state: str | None = None
    worker_id: str | None = None
    evidence_ref: str | None = None


@dataclass(frozen=True, slots=True)
class GraphOperatorSnapshot:
    graph_id: str
    graph_run_id: str | None
    runtime_evidence: bool
    nodes: tuple[GraphOperatorNode, ...]
    edges: tuple[GraphOperatorEdge, ...]
    events: tuple[GraphOperatorEvent, ...]


def _safe_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or any(c in value for c in "\x00\r\n"):
        raise ValueError(f"{field} is invalid")
    return value.strip()

def _connect_read_only(database_path: str | Path) -> sqlite3.Connection:
    path = Path(database_path).expanduser().resolve(strict=False)
    if not path.is_file():
        raise GraphOperatorViewError("GRAPH_DATABASE_NOT_FOUND")
    try:
        connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        return connection
    except sqlite3.Error as exc:
        raise GraphOperatorViewError("GRAPH_DATABASE_READ_FAILED") from exc


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def list_operator_graph_ids(database_path: str | Path) -> tuple[str, ...]:
    path = Path(database_path).expanduser().resolve(strict=False)
    if not path.is_file():
        return ()
    with _connect_read_only(path) as connection:
        if not _table_exists(connection, "graph_nodes"):
            return ()
        rows = connection.execute(
            "SELECT DISTINCT graph_id FROM graph_nodes ORDER BY graph_id"
        ).fetchall()
        return tuple(str(row["graph_id"]) for row in rows)

def _load_graph(connection: sqlite3.Connection, graph_id: str) -> TaskGraph:
    if not _table_exists(connection, "graph_nodes") or not _table_exists(
        connection, "graph_edges"
    ):
        raise GraphOperatorViewError("GRAPH_SCHEMA_UNAVAILABLE")
    node_rows = connection.execute(
        "SELECT data FROM graph_nodes WHERE graph_id = ? ORDER BY node_id",
        (graph_id,),
    ).fetchall()
    if not node_rows:
        raise GraphOperatorViewError("GRAPH_NOT_FOUND")
    builder = TaskGraphBuilder()
    try:
        for row in node_rows:
            builder.add_node(_json_to_node(str(row["data"])))
        edge_rows = connection.execute(
            "SELECT from_id, to_id, dep_type FROM graph_edges "
            "WHERE graph_id = ? ORDER BY from_id, to_id, dep_type",
            (graph_id,),
        ).fetchall()
        for row in edge_rows:
            builder.add_edge(
                TaskEdge(
                    str(row["from_id"]),
                    str(row["to_id"]),
                    DependencyType(str(row["dep_type"])),
                )
            )
        return builder.build()
    except (ValueError, TypeError) as exc:
        raise GraphOperatorViewError("GRAPH_DATA_INVALID") from exc

class _ReadOnlyJobReader:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.cache: dict[str, JobRuntimeState] = {}

    def get_job(self, job_id: str) -> JobRuntimeState:
        row = self.connection.execute(
            "SELECT job_id, work_order_ref, project_id, state, worker_id, "
            "attempt_count, max_attempts, recovery_classification, version "
            "FROM job_records WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            raise JobStoreError("JOB_NOT_FOUND")
        recovery = row["recovery_classification"]
        try:
            job = JobRuntimeState(
                job_id=str(row["job_id"]),
                work_order_ref=str(row["work_order_ref"]),
                project_id=str(row["project_id"]),
                state=TaskState(str(row["state"])),
                worker_id=(str(row["worker_id"]) if row["worker_id"] is not None else None),
                attempt_count=int(row["attempt_count"]),
                max_attempts=int(row["max_attempts"]),
                recovery_classification=(
                    RecoveryClassification(str(recovery)) if recovery is not None else None
                ),
                version=int(row["version"]),
            )
        except (TypeError, ValueError) as exc:
            raise JobStoreError("JOB_STORE_READ_FAILED") from exc
        self.cache[job_id] = job
        return job

def _read_events(
    connection: sqlite3.Connection,
    job_to_node: dict[str, str],
    event_limit: int,
) -> tuple[GraphOperatorEvent, ...]:
    if not job_to_node or not _table_exists(connection, "job_events"):
        return ()
    found: list[GraphOperatorEvent] = []
    job_ids = tuple(job_to_node)
    for start in range(0, len(job_ids), 200):
        chunk = job_ids[start : start + 200]
        marks = ",".join("?" for _ in chunk)
        rows = connection.execute(
            "SELECT job_id, sequence_no, event_type, from_state, to_state, "
            "worker_id, evidence_ref, recorded_at FROM job_events "
            f"WHERE job_id IN ({marks}) "
            "ORDER BY recorded_at DESC, sequence_no DESC LIMIT ?",
            (*chunk, event_limit),
        ).fetchall()
        for row in rows:
            found.append(
                GraphOperatorEvent(
                    node_id=job_to_node[str(row["job_id"])],
                    sequence_no=int(row["sequence_no"]),
                    event_type=str(row["event_type"]),
                    recorded_at=str(row["recorded_at"]),
                    from_state=(str(row["from_state"]) if row["from_state"] else None),
                    to_state=(str(row["to_state"]) if row["to_state"] else None),
                    worker_id=(str(row["worker_id"]) if row["worker_id"] else None),
                    evidence_ref=(str(row["evidence_ref"]) if row["evidence_ref"] else None),
                )
            )
    found.sort(
        key=lambda event: (event.recorded_at, event.sequence_no, event.node_id),
        reverse=True,
    )
    return tuple(found[:event_limit])


def read_graph_operator_snapshot(
    database_path: str | Path,
    graph_id: str,
    graph_run_id: str | None = None,
    *,
    event_limit: int = 20,
) -> GraphOperatorSnapshot:
    graph_id = _safe_text(graph_id, "graph_id")
    if graph_run_id is not None:
        graph_run_id = _safe_text(graph_run_id, "graph_run_id")
    if (
        not isinstance(event_limit, int)
        or isinstance(event_limit, bool)
        or not 1 <= event_limit <= 100
    ):
        raise ValueError("event_limit must be between 1 and 100")

    with _connect_read_only(database_path) as connection:
        graph = _load_graph(connection, graph_id)
        if graph_run_id is None:
            nodes = tuple(
                GraphOperatorNode(node.id, node.objective, node.status)
                for node in graph.nodes()
            )
            events: tuple[GraphOperatorEvent, ...] = ()
            runtime_evidence = False
        else:
            if not _table_exists(connection, "job_records"):
                raise GraphOperatorViewError("JOB_SCHEMA_UNAVAILABLE")
            jobs = _ReadOnlyJobReader(connection)
            states = project_graph_node_states(graph, graph_id, graph_run_id, jobs)
            nodes = tuple(
                GraphOperatorNode(
                    node.id,
                    node.objective,
                    states[node.id],
                    jobs.cache.get(GraphDispatchKey(graph_id, graph_run_id, node.id).job_id).worker_id
                    if GraphDispatchKey(graph_id, graph_run_id, node.id).job_id in jobs.cache
                    else None,
                )
                for node in graph.nodes()
            )
            job_to_node = {
                GraphDispatchKey(graph_id, graph_run_id, node.id).job_id: node.id
                for node in graph.nodes()
            }
            events = _read_events(connection, job_to_node, event_limit)
            runtime_evidence = bool(jobs.cache) or bool(events)

        edges = tuple(
            GraphOperatorEdge(edge.from_id, edge.to_id, edge.dep_type)
            for edge in graph.edges()
        )
        return GraphOperatorSnapshot(
            graph_id=graph_id,
            graph_run_id=graph_run_id,
            runtime_evidence=runtime_evidence,
            nodes=nodes,
            edges=edges,
            events=events,
        )
