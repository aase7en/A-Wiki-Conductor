"""GE-2 / WO-P1-461 — durable SQLite persistence for TaskGraph.

GraphStore owns graph-definition persistence plus the bounded ZRA-3A Child-A
run-preparation authority.  It deliberately does not own project resolution,
provider selection, runtime activation, dispatch, retry, NEXT_READY, or job /
execution / lease lifecycle authority.

Schema v2 preserves every v1 table/column and adds replay-safe graph-run
preparation identity plus immutable per-node binding records.  Writable
initialization is fail-closed and transactional; read-only opens never perform
DDL or migration.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .domain import DependencyType, TaskEdge, TaskGraph, TaskNode, TaskNodeStatus


_SCHEMA_VERSION = 2
_GRAPH_DEFINITION_DOMAIN = b"graph-definition-v1\0"
_PREPARATION_DOMAIN = b"graph-run-preparation-v1\0"
_RUN_ID_PREFIX = "graph-run-v1:"
_MAX_IDENTITY_TEXT = 512
_MAX_REF_TEXT = 1024
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:")

_CORE_TABLES = {
    "graph_meta",
    "graph_nodes",
    "graph_edges",
    "graph_runs",
    "node_events",
}
_BINDING_TABLE = "graph_run_bindings"

# PRAGMA table_info signatures:
# (name, declared_type, notnull, normalized_default, pk_ordinal)
_V1_TABLE_SHAPES: dict[str, tuple[tuple[Any, ...], ...]] = {
    "graph_meta": (
        ("key", "TEXT", 0, None, 1),
        ("value", "TEXT", 1, None, 0),
    ),
    "graph_nodes": (
        ("graph_id", "TEXT", 1, None, 1),
        ("node_id", "TEXT", 1, None, 2),
        ("data", "TEXT", 1, None, 0),
    ),
    "graph_edges": (
        ("graph_id", "TEXT", 1, None, 1),
        ("from_id", "TEXT", 1, None, 2),
        ("to_id", "TEXT", 1, None, 3),
        ("dep_type", "TEXT", 1, None, 4),
    ),
    "graph_runs": (
        ("run_id", "TEXT", 0, None, 1),
        ("graph_id", "TEXT", 1, None, 0),
        ("status", "TEXT", 1, "'pending'", 0),
        ("created_at", "TEXT", 1, "datetime('now')", 0),
        ("completed_at", "TEXT", 0, None, 0),
    ),
    "node_events": (
        ("event_id", "INTEGER", 0, None, 1),
        ("graph_id", "TEXT", 1, None, 0),
        ("node_id", "TEXT", 1, None, 0),
        ("event_type", "TEXT", 1, None, 0),
        ("payload", "TEXT", 0, None, 0),
        ("ts", "TEXT", 1, "datetime('now')", 0),
    ),
}

_V2_RUN_SHAPE = _V1_TABLE_SHAPES["graph_runs"] + (
    ("project_id", "TEXT", 0, None, 0),
    ("graph_definition_sha256", "TEXT", 0, None, 0),
    ("preparation_ref", "TEXT", 0, None, 0),
    ("preparation_sha256", "TEXT", 0, None, 0),
)

_V2_BINDING_SHAPE: tuple[tuple[Any, ...], ...] = (
    ("run_id", "TEXT", 1, None, 1),
    ("node_id", "TEXT", 1, None, 2),
    ("runtime_kind", "TEXT", 1, None, 0),
    ("task_contract_ref", "TEXT", 1, None, 0),
    ("task_contract_sha256", "TEXT", 1, None, 0),
    ("task_packet_ref", "TEXT", 1, None, 0),
    ("task_packet_sha256", "TEXT", 1, None, 0),
    ("provider_id", "TEXT", 1, None, 0),
    ("model_id", "TEXT", 1, None, 0),
    ("effort_level", "TEXT", 1, None, 0),
    ("bound_at", "TEXT", 1, None, 0),
)

_V2_BINDING_SQL = """
CREATE TABLE graph_run_bindings (
    run_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    runtime_kind TEXT NOT NULL
        CHECK (runtime_kind = 'serena'),
    task_contract_ref TEXT NOT NULL
        CHECK (trim(task_contract_ref) <> ''),
    task_contract_sha256 TEXT NOT NULL
        CHECK (
            length(task_contract_sha256) = 64
            AND task_contract_sha256 = lower(task_contract_sha256)
        ),
    task_packet_ref TEXT NOT NULL
        CHECK (trim(task_packet_ref) <> ''),
    task_packet_sha256 TEXT NOT NULL
        CHECK (
            length(task_packet_sha256) = 64
            AND task_packet_sha256 = lower(task_packet_sha256)
        ),
    provider_id TEXT NOT NULL CHECK (trim(provider_id) <> ''),
    model_id TEXT NOT NULL CHECK (trim(model_id) <> ''),
    effort_level TEXT NOT NULL CHECK (trim(effort_level) <> ''),
    bound_at TEXT NOT NULL CHECK (trim(bound_at) <> ''),
    PRIMARY KEY (run_id, node_id),
    FOREIGN KEY (run_id)
        REFERENCES graph_runs(run_id)
        ON DELETE RESTRICT
)
"""

_PREPARATION_INDEX_SQL = """
CREATE UNIQUE INDEX idx_graph_runs_preparation_ref
    ON graph_runs(preparation_ref)
    WHERE preparation_ref IS NOT NULL
"""


def _normalize_schema_sql(value: Any) -> str:
    return " ".join(str(value).split()).strip()


def _normalize_default(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower()


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
    for key in (
        "expected_outputs",
        "read_set",
        "write_set",
        "worker_requirement",
        "artifacts",
    ):
        d[key] = tuple(d.get(key, ()))
    if "status" in d:
        d["status"] = TaskNodeStatus(d["status"])
    return TaskNode(**d)


def _canonical_node(node: TaskNode) -> dict[str, Any]:
    raw = asdict(node)
    canonical: dict[str, Any] = {}
    for key, value in raw.items():
        if isinstance(value, TaskNodeStatus):
            canonical[key] = value.value
        elif isinstance(value, DependencyType):
            canonical[key] = value.value
        elif isinstance(value, tuple):
            canonical[key] = list(value)
        else:
            canonical[key] = value
    # dataclasses.asdict currently leaves str-enum instances intact.  Normalize
    # explicitly so the digest contract is independent of json's Enum handling.
    status = node.status
    canonical["status"] = status.value if isinstance(status, TaskNodeStatus) else status
    return canonical


def _canonical_graph_object(graph: TaskGraph) -> dict[str, Any]:
    nodes = [_canonical_node(node) for node in sorted(graph.nodes(), key=lambda n: n.id)]
    edges = [
        {
            "from_id": edge.from_id,
            "to_id": edge.to_id,
            "dep_type": edge.dep_type.value,
        }
        for edge in sorted(
            graph.edges(),
            key=lambda edge: (edge.from_id, edge.to_id, edge.dep_type.value),
        )
    ]
    return {"nodes": nodes, "edges": edges}


def canonical_graph_definition_sha256(graph: TaskGraph) -> str:
    """Return the accepted graph-definition-v1 canonical SHA-256 digest."""
    payload = json.dumps(
        _canonical_graph_object(graph),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8", errors="strict")
    return hashlib.sha256(_GRAPH_DEFINITION_DOMAIN + payload).hexdigest()


class GraphStoreError(RuntimeError):
    """Stable typed GraphStore/run-preparation failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class GraphStoreReadOnlyError(GraphStoreError):
    def __init__(self, code: str = "GRAPH_STORE_READ_ONLY") -> None:
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class GraphRunBindingSpec:
    """Caller-supplied immutable run-binding intent.

    Validation belongs to GraphStore.prepare_run so constructing an object never
    becomes route/runtime authority by itself.
    """

    node_id: str
    runtime_kind: str
    task_contract_ref: str
    task_contract_sha256: str
    task_packet_ref: str
    task_packet_sha256: str
    provider_id: str
    model_id: str
    effort_level: str


@dataclass(frozen=True, slots=True)
class GraphRunRecord:
    run_id: str
    graph_id: str
    status: str
    created_at: str
    completed_at: str | None
    project_id: str | None
    graph_definition_sha256: str | None
    preparation_ref: str | None
    preparation_sha256: str | None


@dataclass(frozen=True, slots=True)
class GraphRunBindingRecord:
    run_id: str
    node_id: str
    runtime_kind: str
    task_contract_ref: str
    task_contract_sha256: str
    task_packet_ref: str
    task_packet_sha256: str
    provider_id: str
    model_id: str
    effort_level: str
    bound_at: str


def _require_text(
    value: Any,
    *,
    code: str,
    max_length: int = _MAX_IDENTITY_TEXT,
) -> str:
    if not isinstance(value, str):
        raise GraphStoreError(code)
    if (
        not value
        or value != value.strip()
        or len(value) > max_length
        or any(char in value for char in ("\x00", "\r", "\n"))
    ):
        raise GraphStoreError(code)
    return value


def _require_sha256(value: Any, *, code: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise GraphStoreError(code)
    return value


def _require_project_relative_ref(value: Any, *, code: str) -> str:
    ref = _require_text(value, code=code, max_length=_MAX_REF_TEXT)
    if (
        ref.startswith("/")
        or "\\" in ref
        or _WINDOWS_ABSOLUTE_RE.match(ref) is not None
    ):
        raise GraphStoreError(code)
    parts = ref.split("/")
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise GraphStoreError(code)
    if "/".join(parts) != ref:
        raise GraphStoreError(code)
    return ref


def _validated_binding_spec(binding: Any) -> GraphRunBindingSpec:
    if not isinstance(binding, GraphRunBindingSpec):
        raise GraphStoreError("GRAPH_RUN_BINDING_INVALID")
    node_id = _require_text(binding.node_id, code="GRAPH_RUN_BINDING_INVALID")
    runtime_kind = _require_text(
        binding.runtime_kind, code="GRAPH_RUN_BINDING_INVALID"
    )
    if runtime_kind != "serena":
        raise GraphStoreError("RUNTIME_KIND_AUTHORITY_UNAVAILABLE")
    return GraphRunBindingSpec(
        node_id=node_id,
        runtime_kind=runtime_kind,
        task_contract_ref=_require_project_relative_ref(
            binding.task_contract_ref, code="GRAPH_RUN_BINDING_INVALID"
        ),
        task_contract_sha256=_require_sha256(
            binding.task_contract_sha256, code="GRAPH_RUN_BINDING_INVALID"
        ),
        task_packet_ref=_require_project_relative_ref(
            binding.task_packet_ref, code="GRAPH_RUN_BINDING_INVALID"
        ),
        task_packet_sha256=_require_sha256(
            binding.task_packet_sha256, code="GRAPH_RUN_BINDING_INVALID"
        ),
        provider_id=_require_text(
            binding.provider_id, code="GRAPH_RUN_BINDING_INVALID"
        ),
        model_id=_require_text(binding.model_id, code="GRAPH_RUN_BINDING_INVALID"),
        effort_level=_require_text(
            binding.effort_level, code="GRAPH_RUN_BINDING_INVALID"
        ),
    )


def _binding_intent(binding: GraphRunBindingSpec) -> dict[str, str]:
    return {
        "node_id": binding.node_id,
        "runtime_kind": binding.runtime_kind,
        "task_contract_ref": binding.task_contract_ref,
        "task_contract_sha256": binding.task_contract_sha256,
        "task_packet_ref": binding.task_packet_ref,
        "task_packet_sha256": binding.task_packet_sha256,
        "provider_id": binding.provider_id,
        "model_id": binding.model_id,
        "effort_level": binding.effort_level,
    }


def _binding_record_intent(binding: GraphRunBindingRecord) -> dict[str, str]:
    return {
        "node_id": binding.node_id,
        "runtime_kind": binding.runtime_kind,
        "task_contract_ref": binding.task_contract_ref,
        "task_contract_sha256": binding.task_contract_sha256,
        "task_packet_ref": binding.task_packet_ref,
        "task_packet_sha256": binding.task_packet_sha256,
        "provider_id": binding.provider_id,
        "model_id": binding.model_id,
        "effort_level": binding.effort_level,
    }


def _preparation_sha256(
    *,
    graph_id: str,
    project_id: str,
    graph_definition_sha256: str,
    bindings: Iterable[GraphRunBindingSpec],
) -> str:
    payload = {
        "graph_id": graph_id,
        "project_id": project_id,
        "graph_definition_sha256": graph_definition_sha256,
        "bindings": [
            _binding_intent(binding)
            for binding in sorted(bindings, key=lambda item: item.node_id)
        ],
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8", errors="strict")
    return hashlib.sha256(_PREPARATION_DOMAIN + encoded).hexdigest()


def _sqlite_is_busy(exc: sqlite3.Error) -> bool:
    message = str(exc).lower()
    return "locked" in message or "busy" in message


class GraphStore:
    """Durable graph definition and Child-A run-preparation persistence."""

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

    @staticmethod
    def _table_names(connection: sqlite3.Connection) -> set[str]:
        return {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

    @staticmethod
    def _table_shape(
        connection: sqlite3.Connection, table: str
    ) -> tuple[tuple[Any, ...], ...]:
        rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
        return tuple(
            (
                row[1],
                str(row[2]).upper(),
                int(row[3]),
                _normalize_default(row[4]),
                int(row[5]),
            )
            for row in rows
        )

    @staticmethod
    def _schema_version(connection: sqlite3.Connection) -> str | None:
        row = connection.execute(
            "SELECT value FROM graph_meta WHERE key='schema_version'"
        ).fetchone()
        if row is None:
            return None
        value = row[0]
        if not isinstance(value, str):
            raise GraphStoreError("GRAPH_STORE_SCHEMA_SHAPE_INVALID")
        return value

    @staticmethod
    def _required_index_is_present(
        connection: sqlite3.Connection,
        *,
        table: str,
        index_name: str,
        columns: tuple[str, ...],
        unique: bool,
        partial: bool,
    ) -> bool:
        for row in connection.execute(f"PRAGMA index_list({table})").fetchall():
            # seq, name, unique, origin, partial
            if row[1] != index_name:
                continue
            if bool(row[2]) is not unique or bool(row[4]) is not partial:
                return False
            actual = tuple(
                item[2]
                for item in connection.execute(
                    f"PRAGMA index_info({index_name})"
                ).fetchall()
            )
            return actual == columns
        return False

    @classmethod
    def _v1_shape_is_canonical(cls, connection: sqlite3.Connection) -> bool:
        names = cls._table_names(connection)
        if not _CORE_TABLES.issubset(names) or _BINDING_TABLE in names:
            return False
        for table, expected in _V1_TABLE_SHAPES.items():
            if cls._table_shape(connection, table) != expected:
                return False
        return cls._required_index_is_present(
            connection,
            table="node_events",
            index_name="idx_node_events_graph_node",
            columns=("graph_id", "node_id"),
            unique=False,
            partial=False,
        )

    @classmethod
    def _v2_shape_is_canonical(cls, connection: sqlite3.Connection) -> bool:
        names = cls._table_names(connection)
        if not _CORE_TABLES.issubset(names) or _BINDING_TABLE not in names:
            return False
        for table, expected in _V1_TABLE_SHAPES.items():
            if table == "graph_runs":
                continue
            if cls._table_shape(connection, table) != expected:
                return False
        if cls._table_shape(connection, "graph_runs") != _V2_RUN_SHAPE:
            return False
        if cls._table_shape(connection, _BINDING_TABLE) != _V2_BINDING_SHAPE:
            return False
        binding_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (_BINDING_TABLE,),
        ).fetchone()
        if (
            binding_sql is None
            or not isinstance(binding_sql[0], str)
            or _normalize_schema_sql(binding_sql[0])
            != _normalize_schema_sql(_V2_BINDING_SQL)
        ):
            return False
        if not cls._required_index_is_present(
            connection,
            table="node_events",
            index_name="idx_node_events_graph_node",
            columns=("graph_id", "node_id"),
            unique=False,
            partial=False,
        ):
            return False
        if not cls._required_index_is_present(
            connection,
            table="graph_runs",
            index_name="idx_graph_runs_preparation_ref",
            columns=("preparation_ref",),
            unique=True,
            partial=True,
        ):
            return False
        index_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name=?",
            ("idx_graph_runs_preparation_ref",),
        ).fetchone()
        if (
            index_sql is None
            or not isinstance(index_sql[0], str)
            or _normalize_schema_sql(index_sql[0])
            != _normalize_schema_sql(_PREPARATION_INDEX_SQL)
        ):
            return False
        foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(graph_run_bindings)"
        ).fetchall()
        if len(foreign_keys) != 1:
            return False
        fk = foreign_keys[0]
        # id, seq, table, from, to, on_update, on_delete, match
        if not (
            fk[2] == "graph_runs"
            and fk[3] == "run_id"
            and fk[4] == "run_id"
            and str(fk[5]).upper() == "NO ACTION"
            and str(fk[6]).upper() == "RESTRICT"
        ):
            return False
        pragma_fk = connection.execute("PRAGMA foreign_keys").fetchone()
        return pragma_fk is not None and int(pragma_fk[0]) == 1

    @classmethod
    def _schema_state(cls, connection: sqlite3.Connection) -> str:
        names = cls._table_names(connection)
        participating = names.intersection(_CORE_TABLES | {_BINDING_TABLE})
        if not participating:
            return "FRESH"
        if not _CORE_TABLES.issubset(names):
            raise GraphStoreError("GRAPH_STORE_SCHEMA_SHAPE_INVALID")

        version = cls._schema_version(connection)
        if version not in (None, "1", "2"):
            raise GraphStoreError("GRAPH_STORE_SCHEMA_VERSION_UNSUPPORTED")

        if version in (None, "1") and cls._v1_shape_is_canonical(connection):
            return "V1"
        if version == "2" and cls._v2_shape_is_canonical(connection):
            return "V2"
        if version is None and cls._v2_shape_is_canonical(connection):
            return "V2_UNSTAMPED"
        raise GraphStoreError("GRAPH_STORE_SCHEMA_SHAPE_INVALID")

    @staticmethod
    def _create_v2_schema(connection: sqlite3.Connection) -> None:
        statements = (
            """
            CREATE TABLE graph_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE graph_nodes (
                graph_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                data TEXT NOT NULL,
                PRIMARY KEY (graph_id, node_id)
            )
            """,
            """
            CREATE TABLE graph_edges (
                graph_id TEXT NOT NULL,
                from_id TEXT NOT NULL,
                to_id TEXT NOT NULL,
                dep_type TEXT NOT NULL,
                PRIMARY KEY (graph_id, from_id, to_id, dep_type)
            )
            """,
            """
            CREATE TABLE graph_runs (
                run_id TEXT PRIMARY KEY,
                graph_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                completed_at TEXT,
                project_id TEXT,
                graph_definition_sha256 TEXT,
                preparation_ref TEXT,
                preparation_sha256 TEXT
            )
            """,
            """
            CREATE TABLE node_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                graph_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT,
                ts TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """,
            """
            CREATE TABLE graph_run_bindings (
                run_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                runtime_kind TEXT NOT NULL
                    CHECK (runtime_kind = 'serena'),
                task_contract_ref TEXT NOT NULL
                    CHECK (trim(task_contract_ref) <> ''),
                task_contract_sha256 TEXT NOT NULL
                    CHECK (
                        length(task_contract_sha256) = 64
                        AND task_contract_sha256 = lower(task_contract_sha256)
                    ),
                task_packet_ref TEXT NOT NULL
                    CHECK (trim(task_packet_ref) <> ''),
                task_packet_sha256 TEXT NOT NULL
                    CHECK (
                        length(task_packet_sha256) = 64
                        AND task_packet_sha256 = lower(task_packet_sha256)
                    ),
                provider_id TEXT NOT NULL CHECK (trim(provider_id) <> ''),
                model_id TEXT NOT NULL CHECK (trim(model_id) <> ''),
                effort_level TEXT NOT NULL CHECK (trim(effort_level) <> ''),
                bound_at TEXT NOT NULL CHECK (trim(bound_at) <> ''),
                PRIMARY KEY (run_id, node_id),
                FOREIGN KEY (run_id)
                    REFERENCES graph_runs(run_id)
                    ON DELETE RESTRICT
            )
            """,
            """
            CREATE INDEX idx_node_events_graph_node
                ON node_events(graph_id, node_id)
            """,
            """
            CREATE UNIQUE INDEX idx_graph_runs_preparation_ref
                ON graph_runs(preparation_ref)
                WHERE preparation_ref IS NOT NULL
            """,
        )
        for statement in statements:
            connection.execute(statement)

    @staticmethod
    def _migrate_v1_to_v2(connection: sqlite3.Connection) -> None:
        for statement in (
            "ALTER TABLE graph_runs ADD COLUMN project_id TEXT",
            "ALTER TABLE graph_runs ADD COLUMN graph_definition_sha256 TEXT",
            "ALTER TABLE graph_runs ADD COLUMN preparation_ref TEXT",
            "ALTER TABLE graph_runs ADD COLUMN preparation_sha256 TEXT",
            """
            CREATE TABLE graph_run_bindings (
                run_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                runtime_kind TEXT NOT NULL
                    CHECK (runtime_kind = 'serena'),
                task_contract_ref TEXT NOT NULL
                    CHECK (trim(task_contract_ref) <> ''),
                task_contract_sha256 TEXT NOT NULL
                    CHECK (
                        length(task_contract_sha256) = 64
                        AND task_contract_sha256 = lower(task_contract_sha256)
                    ),
                task_packet_ref TEXT NOT NULL
                    CHECK (trim(task_packet_ref) <> ''),
                task_packet_sha256 TEXT NOT NULL
                    CHECK (
                        length(task_packet_sha256) = 64
                        AND task_packet_sha256 = lower(task_packet_sha256)
                    ),
                provider_id TEXT NOT NULL CHECK (trim(provider_id) <> ''),
                model_id TEXT NOT NULL CHECK (trim(model_id) <> ''),
                effort_level TEXT NOT NULL CHECK (trim(effort_level) <> ''),
                bound_at TEXT NOT NULL CHECK (trim(bound_at) <> ''),
                PRIMARY KEY (run_id, node_id),
                FOREIGN KEY (run_id)
                    REFERENCES graph_runs(run_id)
                    ON DELETE RESTRICT
            )
            """,
            """
            CREATE UNIQUE INDEX idx_graph_runs_preparation_ref
                ON graph_runs(preparation_ref)
                WHERE preparation_ref IS NOT NULL
            """,
        ):
            connection.execute(statement)

    @classmethod
    def _stamp_v2(cls, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            INSERT INTO graph_meta(key, value)
            VALUES('schema_version', '2')
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """
        )
        if cls._schema_version(connection) != "2":
            raise GraphStoreError("GRAPH_STORE_SCHEMA_VERSION_UNSUPPORTED")

    def _init_schema(self) -> None:
        with self._connect() as connection:
            try:
                # Classify writable schema only after acquiring the SQLite
                # writer lock.  A concurrent initializer may be between v1
                # DDL steps and the v2 version stamp; inspecting that transient
                # shape before BEGIN IMMEDIATE can falsely classify a valid
                # in-flight migration as corrupt.
                connection.execute("BEGIN IMMEDIATE")
                state = self._schema_state(connection)
                if state == "V2":
                    connection.rollback()
                    return
                if state == "FRESH":
                    self._create_v2_schema(connection)
                elif state == "V1":
                    self._migrate_v1_to_v2(connection)
                elif state != "V2_UNSTAMPED":
                    raise GraphStoreError("GRAPH_STORE_SCHEMA_SHAPE_INVALID")

                # Validate the physical v2 shape before publishing schema v2.
                if not self._v2_shape_is_canonical(connection):
                    raise GraphStoreError("GRAPH_STORE_SCHEMA_SHAPE_INVALID")
                self._stamp_v2(connection)
                if self._schema_state(connection) != "V2":
                    raise GraphStoreError("GRAPH_STORE_SCHEMA_SHAPE_INVALID")
                connection.commit()
            except GraphStoreError:
                connection.rollback()
                raise
            except sqlite3.Error as exc:
                connection.rollback()
                if _sqlite_is_busy(exc):
                    raise GraphStoreError("GRAPH_STORE_SCHEMA_BUSY") from exc
                raise GraphStoreError("GRAPH_STORE_INIT_FAILED") from exc

    @staticmethod
    def _load_graph_from_connection(
        connection: sqlite3.Connection, graph_id: str
    ) -> TaskGraph:
        from .graph import TaskGraphBuilder

        builder = TaskGraphBuilder()
        rows = connection.execute(
            "SELECT data FROM graph_nodes WHERE graph_id = ? ORDER BY node_id",
            (graph_id,),
        ).fetchall()
        try:
            for (data,) in rows:
                builder.add_node(_json_to_node(data))
            edges = connection.execute(
                "SELECT from_id, to_id, dep_type FROM graph_edges "
                "WHERE graph_id = ? ORDER BY from_id, to_id, dep_type",
                (graph_id,),
            ).fetchall()
            for from_id, to_id, dep_type in edges:
                builder.add_edge(TaskEdge(from_id, to_id, DependencyType(dep_type)))
            return builder.build()
        except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise GraphStoreError("GRAPH_DEFINITION_INVALID") from exc

    @classmethod
    def _decode_v2_run_row(cls, row: tuple[Any, ...]) -> GraphRunRecord:
        try:
            (
                run_id,
                graph_id,
                status,
                created_at,
                completed_at,
                project_id,
                graph_definition_sha256,
                preparation_ref,
                preparation_sha256,
            ) = row
            run_id = _require_text(run_id, code="GRAPH_RUN_RECORD_INVALID")
            graph_id = _require_text(graph_id, code="GRAPH_RUN_RECORD_INVALID")
            status = _require_text(status, code="GRAPH_RUN_RECORD_INVALID")
            created_at = _require_text(
                created_at, code="GRAPH_RUN_RECORD_INVALID"
            )
            if completed_at is not None:
                completed_at = _require_text(
                    completed_at, code="GRAPH_RUN_RECORD_INVALID"
                )

            values = (
                project_id,
                graph_definition_sha256,
                preparation_ref,
                preparation_sha256,
            )
            all_null = all(value is None for value in values)
            all_present = all(value is not None for value in values)
            if not (all_null or all_present):
                raise GraphStoreError("GRAPH_RUN_RECORD_INVALID")
            if all_present:
                project_id = _require_text(
                    project_id, code="GRAPH_RUN_RECORD_INVALID"
                )
                graph_definition_sha256 = _require_sha256(
                    graph_definition_sha256, code="GRAPH_RUN_RECORD_INVALID"
                )
                preparation_ref = _require_text(
                    preparation_ref, code="GRAPH_RUN_RECORD_INVALID"
                )
                preparation_sha256 = _require_sha256(
                    preparation_sha256, code="GRAPH_RUN_RECORD_INVALID"
                )
            return GraphRunRecord(
                run_id=run_id,
                graph_id=graph_id,
                status=status,
                created_at=created_at,
                completed_at=completed_at,
                project_id=project_id,
                graph_definition_sha256=graph_definition_sha256,
                preparation_ref=preparation_ref,
                preparation_sha256=preparation_sha256,
            )
        except GraphStoreError:
            raise
        except Exception as exc:
            raise GraphStoreError("GRAPH_RUN_RECORD_INVALID") from exc

    @classmethod
    def _decode_binding_row(
        cls, row: tuple[Any, ...]
    ) -> GraphRunBindingRecord:
        try:
            (
                run_id,
                node_id,
                runtime_kind,
                task_contract_ref,
                task_contract_sha256,
                task_packet_ref,
                task_packet_sha256,
                provider_id,
                model_id,
                effort_level,
                bound_at,
            ) = row
            run_id = _require_text(
                run_id, code="GRAPH_RUN_BINDING_RECORD_INVALID"
            )
            node_id = _require_text(
                node_id, code="GRAPH_RUN_BINDING_RECORD_INVALID"
            )
            runtime_kind = _require_text(
                runtime_kind, code="GRAPH_RUN_BINDING_RECORD_INVALID"
            )
            if runtime_kind != "serena":
                raise GraphStoreError("GRAPH_RUN_BINDING_RECORD_INVALID")
            return GraphRunBindingRecord(
                run_id=run_id,
                node_id=node_id,
                runtime_kind=runtime_kind,
                task_contract_ref=_require_project_relative_ref(
                    task_contract_ref, code="GRAPH_RUN_BINDING_RECORD_INVALID"
                ),
                task_contract_sha256=_require_sha256(
                    task_contract_sha256, code="GRAPH_RUN_BINDING_RECORD_INVALID"
                ),
                task_packet_ref=_require_project_relative_ref(
                    task_packet_ref, code="GRAPH_RUN_BINDING_RECORD_INVALID"
                ),
                task_packet_sha256=_require_sha256(
                    task_packet_sha256, code="GRAPH_RUN_BINDING_RECORD_INVALID"
                ),
                provider_id=_require_text(
                    provider_id, code="GRAPH_RUN_BINDING_RECORD_INVALID"
                ),
                model_id=_require_text(
                    model_id, code="GRAPH_RUN_BINDING_RECORD_INVALID"
                ),
                effort_level=_require_text(
                    effort_level, code="GRAPH_RUN_BINDING_RECORD_INVALID"
                ),
                bound_at=_require_text(
                    bound_at, code="GRAPH_RUN_BINDING_RECORD_INVALID"
                ),
            )
        except GraphStoreError:
            raise
        except Exception as exc:
            raise GraphStoreError("GRAPH_RUN_BINDING_RECORD_INVALID") from exc

    @classmethod
    def _read_v2_run_by_id(
        cls, connection: sqlite3.Connection, run_id: str
    ) -> GraphRunRecord | None:
        row = connection.execute(
            """
            SELECT run_id, graph_id, status, created_at, completed_at,
                   project_id, graph_definition_sha256,
                   preparation_ref, preparation_sha256
            FROM graph_runs WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()
        return None if row is None else cls._decode_v2_run_row(row)

    @classmethod
    def _read_v2_run_by_preparation_ref(
        cls, connection: sqlite3.Connection, preparation_ref: str
    ) -> GraphRunRecord | None:
        row = connection.execute(
            """
            SELECT run_id, graph_id, status, created_at, completed_at,
                   project_id, graph_definition_sha256,
                   preparation_ref, preparation_sha256
            FROM graph_runs WHERE preparation_ref = ?
            """,
            (preparation_ref,),
        ).fetchone()
        return None if row is None else cls._decode_v2_run_row(row)

    @classmethod
    def _read_binding_records(
        cls, connection: sqlite3.Connection, run_id: str
    ) -> tuple[GraphRunBindingRecord, ...]:
        rows = connection.execute(
            """
            SELECT run_id, node_id, runtime_kind,
                   task_contract_ref, task_contract_sha256,
                   task_packet_ref, task_packet_sha256,
                   provider_id, model_id, effort_level, bound_at
            FROM graph_run_bindings
            WHERE run_id = ?
            ORDER BY node_id
            """,
            (run_id,),
        ).fetchall()
        return tuple(cls._decode_binding_row(row) for row in rows)

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
        with self._connect() as conn:
            return self._load_graph_from_connection(conn, graph_id)

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

    def load_graph_run(self, run_id: str) -> GraphRunRecord:
        run_id = _require_text(run_id, code="GRAPH_RUN_RECORD_INVALID")
        with self._connect() as connection:
            state = self._schema_state(connection)
            if state == "V1":
                row = connection.execute(
                    """
                    SELECT run_id, graph_id, status, created_at, completed_at
                    FROM graph_runs WHERE run_id = ?
                    """,
                    (run_id,),
                ).fetchone()
                if row is None:
                    raise GraphStoreError("GRAPH_RUN_NOT_FOUND")
                legacy = tuple(row) + (None, None, None, None)
                return self._decode_v2_run_row(legacy)
            if state not in ("V2", "V2_UNSTAMPED"):
                raise GraphStoreError("GRAPH_STORE_SCHEMA_SHAPE_INVALID")
            record = self._read_v2_run_by_id(connection, run_id)
            if record is None:
                raise GraphStoreError("GRAPH_RUN_NOT_FOUND")
            return record

    def load_graph_run_bindings(
        self, run_id: str
    ) -> tuple[GraphRunBindingRecord, ...]:
        run_id = _require_text(
            run_id, code="GRAPH_RUN_BINDING_RECORD_INVALID"
        )
        with self._connect() as connection:
            state = self._schema_state(connection)
            if state == "V1":
                raise GraphStoreError("GRAPH_RUN_BINDING_AUTHORITY_UNAVAILABLE")
            if state not in ("V2", "V2_UNSTAMPED"):
                raise GraphStoreError("GRAPH_STORE_SCHEMA_SHAPE_INVALID")
            return self._read_binding_records(connection, run_id)

    def prepare_run(
        self,
        *,
        graph_id: str,
        project_id: str,
        preparation_ref: str,
        bindings: Iterable[GraphRunBindingSpec],
    ) -> GraphRunRecord:
        """Atomically persist or replay one immutable graph-run preparation."""
        self._require_writable()
        graph_id = _require_text(
            graph_id, code="GRAPH_RUN_PREPARATION_INVALID"
        )
        project_id = _require_text(
            project_id, code="GRAPH_RUN_PREPARATION_INVALID"
        )
        if (
            not isinstance(preparation_ref, str)
            or not preparation_ref.strip()
        ):
            raise GraphStoreError("GRAPH_RUN_PREPARATION_REF_REQUIRED")
        preparation_ref = _require_text(
            preparation_ref, code="GRAPH_RUN_PREPARATION_REF_REQUIRED"
        )

        try:
            raw_bindings = tuple(bindings)
        except TypeError as exc:
            raise GraphStoreError("GRAPH_RUN_BINDING_INVALID") from exc
        validated = tuple(_validated_binding_spec(binding) for binding in raw_bindings)
        node_ids = [binding.node_id for binding in validated]
        if len(node_ids) != len(set(node_ids)):
            raise GraphStoreError("GRAPH_RUN_BINDING_INVALID")
        validated = tuple(sorted(validated, key=lambda item: item.node_id))

        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                if self._schema_state(connection) != "V2":
                    raise GraphStoreError("GRAPH_STORE_SCHEMA_SHAPE_INVALID")

                graph = self._load_graph_from_connection(connection, graph_id)
                if not graph.nodes():
                    raise GraphStoreError("GRAPH_DEFINITION_UNAVAILABLE")
                graph_digest = canonical_graph_definition_sha256(graph)
                graph_node_ids = set(graph.node_ids())

                for binding in validated:
                    if binding.node_id not in graph_node_ids:
                        raise GraphStoreError("GRAPH_RUN_BINDING_NODE_INVALID")
                    node = graph.node(binding.node_id)
                    if node.worker_requirement:
                        raise GraphStoreError(
                            "RUNTIME_CAPABILITY_AUTHORITY_UNAVAILABLE"
                        )

                preparation_digest = _preparation_sha256(
                    graph_id=graph_id,
                    project_id=project_id,
                    graph_definition_sha256=graph_digest,
                    bindings=validated,
                )

                raw_existing = connection.execute(
                    """
                    SELECT run_id, graph_id, status, created_at, completed_at,
                           project_id, graph_definition_sha256,
                           preparation_ref, preparation_sha256
                    FROM graph_runs WHERE preparation_ref = ?
                    """,
                    (preparation_ref,),
                ).fetchone()
                if raw_existing is not None:
                    raw_digest = raw_existing[8]
                    if not isinstance(raw_digest, str) or _SHA256_RE.fullmatch(
                        raw_digest
                    ) is None:
                        raise GraphStoreError(
                            "GRAPH_RUN_PREPARATION_RECOVERY_REQUIRED"
                        )
                    if raw_digest != preparation_digest:
                        raise GraphStoreError(
                            "GRAPH_RUN_PREPARATION_IDENTITY_MISMATCH"
                        )
                    try:
                        existing = self._decode_v2_run_row(raw_existing)
                        durable_bindings = self._read_binding_records(
                            connection, existing.run_id
                        )
                    except GraphStoreError as exc:
                        raise GraphStoreError(
                            "GRAPH_RUN_PREPARATION_RECOVERY_REQUIRED"
                        ) from exc

                    expected_run = (
                        existing.graph_id == graph_id
                        and existing.project_id == project_id
                        and existing.graph_definition_sha256 == graph_digest
                        and existing.preparation_ref == preparation_ref
                        and existing.preparation_sha256 == preparation_digest
                    )
                    expected_bindings = tuple(
                        _binding_intent(binding) for binding in validated
                    )
                    observed_bindings = tuple(
                        _binding_record_intent(binding)
                        for binding in durable_bindings
                    )
                    if not expected_run or observed_bindings != expected_bindings:
                        raise GraphStoreError(
                            "GRAPH_RUN_PREPARATION_RECOVERY_REQUIRED"
                        )
                    connection.commit()
                    return existing

                run_id = f"{_RUN_ID_PREFIX}{uuid.uuid4().hex}"
                connection.execute(
                    """
                    INSERT INTO graph_runs(
                        run_id, graph_id, project_id,
                        graph_definition_sha256,
                        preparation_ref, preparation_sha256
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        graph_id,
                        project_id,
                        graph_digest,
                        preparation_ref,
                        preparation_digest,
                    ),
                )
                for binding in validated:
                    connection.execute(
                        """
                        INSERT INTO graph_run_bindings(
                            run_id, node_id, runtime_kind,
                            task_contract_ref, task_contract_sha256,
                            task_packet_ref, task_packet_sha256,
                            provider_id, model_id, effort_level, bound_at
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                        )
                        """,
                        (
                            run_id,
                            binding.node_id,
                            binding.runtime_kind,
                            binding.task_contract_ref,
                            binding.task_contract_sha256,
                            binding.task_packet_ref,
                            binding.task_packet_sha256,
                            binding.provider_id,
                            binding.model_id,
                            binding.effort_level,
                        ),
                    )

                try:
                    inserted = self._read_v2_run_by_id(connection, run_id)
                    durable_bindings = self._read_binding_records(
                        connection, run_id
                    )
                except GraphStoreError as exc:
                    raise GraphStoreError(
                        "GRAPH_RUN_PREPARATION_RECOVERY_REQUIRED"
                    ) from exc
                if inserted is None:
                    raise GraphStoreError(
                        "GRAPH_RUN_PREPARATION_RECOVERY_REQUIRED"
                    )
                expected_bindings = tuple(
                    _binding_intent(binding) for binding in validated
                )
                observed_bindings = tuple(
                    _binding_record_intent(binding)
                    for binding in durable_bindings
                )
                if not (
                    inserted.graph_id == graph_id
                    and inserted.project_id == project_id
                    and inserted.graph_definition_sha256 == graph_digest
                    and inserted.preparation_ref == preparation_ref
                    and inserted.preparation_sha256 == preparation_digest
                    and observed_bindings == expected_bindings
                ):
                    raise GraphStoreError(
                        "GRAPH_RUN_PREPARATION_RECOVERY_REQUIRED"
                    )
                connection.commit()
                return inserted
            except GraphStoreError:
                connection.rollback()
                raise
            except sqlite3.Error as exc:
                connection.rollback()
                if _sqlite_is_busy(exc):
                    raise GraphStoreError(
                        "GRAPH_RUN_PREPARATION_STORE_BUSY"
                    ) from exc
                raise GraphStoreError(
                    "GRAPH_RUN_PREPARATION_STORE_FAILED"
                ) from exc
