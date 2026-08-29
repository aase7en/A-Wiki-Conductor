"""GE-2 — durable SQLite persistence for TaskGraph (ADR GE-0002).

Tables: graph_nodes, graph_edges, graph_runs, node_events.
The store round-trips GE-1a/1b domain objects exactly; no scheduler
or dispatch semantics here (D5 gate). Uses the same per-call connection
pattern as the existing SQLite stores.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .domain import DependencyType, TaskEdge, TaskGraph, TaskNode, TaskNodeStatus

_SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS graph_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS graph_nodes (
    graph_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (graph_id, node_id)
);
CREATE TABLE IF NOT EXISTS graph_edges (
    graph_id TEXT NOT NULL,
    from_id TEXT NOT NULL,
    to_id TEXT NOT NULL,
    dep_type TEXT NOT NULL,
    PRIMARY KEY (graph_id, from_id, to_id, dep_type)
);
CREATE TABLE IF NOT EXISTS graph_runs (
    run_id TEXT PRIMARY KEY,
    graph_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);
CREATE TABLE IF NOT EXISTS node_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    graph_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload TEXT,
    ts TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_node_events_graph_node
    ON node_events(graph_id, node_id);
"""


def _dataclass_to_json(obj: Any) -> str:
    d = asdict(obj)
    for key, val in d.items():
        if isinstance(val, TaskNodeStatus):
            d[key] = val.value
        elif isinstance(val, DependencyType):
            d[key] = val.value
        elif isinstance(val, tuple):
            d[key] = list(val)
    return json.dumps(d, ensure_ascii=False)


def _json_to_node(json_str: str) -> TaskNode:
    d = json.loads(json_str)
    for key in ("expected_outputs", "read_set", "write_set",
                "worker_requirement", "artifacts"):
        d[key] = tuple(d.get(key, ()))
    if "status" in d:
        d["status"] = TaskNodeStatus(d["status"])
    return TaskNode(**d)


class GraphStoreReadOnlyError(RuntimeError):
    def __init__(self, code: str = "GRAPH_STORE_READ_ONLY") -> None:
        self.code = code
        super().__init__(code)


class GraphStore:
    """Durable persistence for TaskGraph instances in SQLite."""

    def __init__(self, db_path: Path | str, *, read_only: bool = False) -> None:
        self._db_path = Path(db_path)
        self._read_only = bool(read_only)
        if self._read_only:
            return
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @classmethod
    def open_read_only(cls, db_path: Path | str) -> "GraphStore":
        path = Path(db_path).expanduser().resolve(strict=False)
        if not path.is_file():
            raise FileNotFoundError(path)
        return cls(path, read_only=True)

    def _connect(self) -> sqlite3.Connection:
        if self._read_only:
            path = self._db_path.expanduser().resolve(strict=False)
            conn = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
            conn.execute("PRAGMA query_only=ON")
        else:
            conn = sqlite3.connect(str(self._db_path))
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _require_writable(self) -> None:
        if self._read_only:
            raise GraphStoreReadOnlyError()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.execute(
                "INSERT OR REPLACE INTO graph_meta (key, value) VALUES (?, ?)",
                ("schema_version", str(_SCHEMA_VERSION)),
            )

    def save_graph(self, graph: TaskGraph, graph_id: str) -> None:
        self._require_writable()
        with self._connect() as conn:
            conn.execute("DELETE FROM graph_nodes WHERE graph_id = ?", (graph_id,))
            conn.execute("DELETE FROM graph_edges WHERE graph_id = ?", (graph_id,))
            for node in graph.nodes():
                conn.execute(
                    "INSERT INTO graph_nodes (graph_id, node_id, data) VALUES (?, ?, ?)",
                    (graph_id, node.id, _dataclass_to_json(node)),
                )
            for edge in graph.edges():
                conn.execute(
                    "INSERT INTO graph_edges VALUES (?, ?, ?, ?)",
                    (graph_id, edge.from_id, edge.to_id, edge.dep_type.value),
                )

    def load_graph(self, graph_id: str) -> TaskGraph:
        from .graph import TaskGraphBuilder

        builder = TaskGraphBuilder()
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT data FROM graph_nodes WHERE graph_id = ? ORDER BY node_id",
                (graph_id,),
            ).fetchall()
            for (data,) in rows:
                builder.add_node(_json_to_node(data))
            edges = conn.execute(
                "SELECT from_id, to_id, dep_type FROM graph_edges "
                "WHERE graph_id = ? ORDER BY from_id, to_id, dep_type",
                (graph_id,),
            ).fetchall()
            for from_id, to_id, dep_type in edges:
                builder.add_edge(TaskEdge(from_id, to_id, DependencyType(dep_type)))
        return builder.build()

    def list_graph_ids(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT graph_id FROM graph_nodes ORDER BY graph_id"
            ).fetchall()
        return [r[0] for r in rows]

    def delete_graph(self, graph_id: str) -> None:
        self._require_writable()
        with self._connect() as conn:
            conn.execute("DELETE FROM graph_nodes WHERE graph_id = ?", (graph_id,))
            conn.execute("DELETE FROM graph_edges WHERE graph_id = ?", (graph_id,))

    def record_node_event(
        self, graph_id: str, node_id: str, event_type: str, payload: str = ""
    ) -> int:
        self._require_writable()
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO node_events (graph_id, node_id, event_type, payload) "
                "VALUES (?, ?, ?, ?)",
                (graph_id, node_id, event_type, payload),
            )
            return cursor.lastrowid or 0

    def node_events(self, graph_id: str, node_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT event_id, event_type, payload, ts FROM node_events "
                "WHERE graph_id = ? AND node_id = ? ORDER BY event_id",
                (graph_id, node_id),
            ).fetchall()
        return [
            {"event_id": r[0], "event_type": r[1], "payload": r[2], "ts": r[3]}
            for r in rows
        ]
