"""WO-P1-461 — RED-first GraphStore v2 run-authority contract.

These tests intentionally pin only Child-A persistence authority. They do not
exercise ControlCenter/project resolution, live provider policy, activation,
dispatch, NEXT_READY, or any runtime/job/execution/lease authority.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import a_conductor.graph.store as store_module
from a_conductor.graph.domain import DependencyType, TaskEdge, TaskNode
from a_conductor.graph.graph import build_graph


V1_SCHEMA = """
CREATE TABLE graph_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE graph_nodes (
    graph_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (graph_id, node_id)
);
CREATE TABLE graph_edges (
    graph_id TEXT NOT NULL,
    from_id TEXT NOT NULL,
    to_id TEXT NOT NULL,
    dep_type TEXT NOT NULL,
    PRIMARY KEY (graph_id, from_id, to_id, dep_type)
);
CREATE TABLE graph_runs (
    run_id TEXT PRIMARY KEY,
    graph_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);
CREATE TABLE node_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    graph_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload TEXT,
    ts TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_node_events_graph_node
    ON node_events(graph_id, node_id);
"""


def _api():
    error = getattr(store_module, "GraphStoreError", None)
    binding = getattr(store_module, "GraphRunBindingSpec", None)
    run_record = getattr(store_module, "GraphRunRecord", None)
    binding_record = getattr(store_module, "GraphRunBindingRecord", None)
    digest = getattr(store_module, "canonical_graph_definition_sha256", None)
    assert error is not None, "Child A must expose typed GraphStoreError"
    assert binding is not None, "Child A must expose GraphRunBindingSpec"
    assert run_record is not None, "Child A must expose GraphRunRecord"
    assert binding_record is not None, "Child A must expose GraphRunBindingRecord"
    assert callable(digest), "Child A must expose graph-definition digest helper"
    return error, binding, run_record, binding_record, digest


def _node(node_id: str, *, objective: str | None = None) -> TaskNode:
    return TaskNode(
        id=node_id,
        objective=objective or f"objective {node_id}",
        expected_outputs=("out.md",),
        read_set=("src/**",),
        write_set=("docs/out.md",),
        worker_requirement=(),
        model_requirement=None,
        priority=5,
        timeout_seconds=600,
        retry_policy_ref="default",
        artifacts=("artifact.json",),
    )


def _graph(order: tuple[str, ...] = ("a", "b")):
    nodes = {node_id: _node(node_id) for node_id in order}
    edge = TaskEdge("a", "b", DependencyType.DATA)
    return build_graph([nodes[node_id] for node_id in order], [edge])


def _create_v1_database(path: Path, *, version: str = "1") -> None:
    with sqlite3.connect(path) as conn:
        conn.executescript(V1_SCHEMA)
        conn.execute(
            "INSERT INTO graph_meta(key, value) VALUES('schema_version', ?)",
            (version,),
        )


def _seed_v1_graph(path: Path, graph_id: str = "g1") -> None:
    node_json = store_module._dataclass_to_json(_node("a"))
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT INTO graph_nodes(graph_id, node_id, data) VALUES (?, ?, ?)",
            (graph_id, "a", node_json),
        )
        conn.execute(
            "INSERT INTO graph_runs(run_id, graph_id, status) VALUES (?, ?, ?)",
            ("legacy-run", graph_id, "pending"),
        )


def _columns(path: Path, table: str) -> tuple[tuple, ...]:
    with sqlite3.connect(path) as conn:
        return tuple(conn.execute(f"PRAGMA table_info({table})").fetchall())


def _version(path: Path) -> str | None:
    with sqlite3.connect(path) as conn:
        row = conn.execute(
            "SELECT value FROM graph_meta WHERE key='schema_version'"
        ).fetchone()
    return None if row is None else row[0]


def _binding(node_id: str = "a", *, provider_id: str = "cointh-glm"):
    _, binding_type, _, _, _ = _api()
    return binding_type(
        node_id=node_id,
        runtime_kind="serena",
        task_contract_ref=f"contracts/{node_id}.json",
        task_contract_sha256="a" * 64,
        task_packet_ref=f"packets/{node_id}.json",
        task_packet_sha256="b" * 64,
        provider_id=provider_id,
        model_id="glm-5.3",
        effort_level="max",
    )


def _prepare(
    store,
    *,
    ref: str = "prep-001",
    bindings=None,
    graph_id: str = "g1",
    project_id: str = "project-1",
):
    if bindings is None:
        bindings = (_binding(),)
    return store.prepare_run(
        graph_id=graph_id,
        project_id=project_id,
        preparation_ref=ref,
        bindings=tuple(bindings),
    )


def _assert_code(exc: BaseException, code: str) -> None:
    assert getattr(exc, "code", None) == code


def test_child_a_typed_api_surface_exists() -> None:
    _api()


def test_unsupported_schema_version_is_typed_and_unchanged(tmp_path: Path) -> None:
    error, *_ = _api()
    db = tmp_path / "graphs.sqlite"
    _create_v1_database(db, version="99")
    before = _columns(db, "graph_runs")

    with pytest.raises(error) as exc:
        store_module.GraphStore(db)

    _assert_code(exc.value, "GRAPH_STORE_SCHEMA_VERSION_UNSUPPORTED")
    assert _version(db) == "99"
    assert _columns(db, "graph_runs") == before


def test_wrong_shaped_v1_is_typed_and_unchanged(tmp_path: Path) -> None:
    error, *_ = _api()
    db = tmp_path / "graphs.sqlite"
    _create_v1_database(db)
    with sqlite3.connect(db) as conn:
        conn.execute("ALTER TABLE graph_runs ADD COLUMN project_id INTEGER")
    before = _columns(db, "graph_runs")

    with pytest.raises(error) as exc:
        store_module.GraphStore(db)

    _assert_code(exc.value, "GRAPH_STORE_SCHEMA_SHAPE_INVALID")
    assert _version(db) == "1"
    assert _columns(db, "graph_runs") == before


def test_partial_v2_is_not_stamped_or_repaired(tmp_path: Path) -> None:
    error, *_ = _api()
    db = tmp_path / "graphs.sqlite"
    _create_v1_database(db, version="2")
    with sqlite3.connect(db) as conn:
        conn.execute("ALTER TABLE graph_runs ADD COLUMN project_id TEXT")
    before = _columns(db, "graph_runs")

    with pytest.raises(error) as exc:
        store_module.GraphStore(db)

    _assert_code(exc.value, "GRAPH_STORE_SCHEMA_SHAPE_INVALID")
    assert _version(db) == "2"
    assert _columns(db, "graph_runs") == before
    with sqlite3.connect(db) as conn:
        assert conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='graph_run_bindings'"
        ).fetchone() is None


def test_exact_v1_migrates_to_v2_preserving_legacy_rows(tmp_path: Path) -> None:
    _api()
    db = tmp_path / "graphs.sqlite"
    _create_v1_database(db)
    _seed_v1_graph(db)

    store_module.GraphStore(db)

    assert _version(db) == "2"
    columns = {row[1] for row in _columns(db, "graph_runs")}
    assert {
        "project_id",
        "graph_definition_sha256",
        "preparation_ref",
        "preparation_sha256",
    } <= columns
    with sqlite3.connect(db) as conn:
        legacy = conn.execute(
            "SELECT run_id, graph_id, status, project_id, preparation_ref "
            "FROM graph_runs WHERE run_id='legacy-run'"
        ).fetchone()
        assert legacy == ("legacy-run", "g1", "pending", None, None)
        assert conn.execute(
            "SELECT COUNT(*) FROM graph_run_bindings"
        ).fetchone()[0] == 0
        assert conn.execute(
            "SELECT data FROM graph_nodes WHERE graph_id='g1' AND node_id='a'"
        ).fetchone() is not None


def test_concurrent_initializers_converge_on_exact_v2(tmp_path: Path) -> None:
    _api()
    db = tmp_path / "graphs.sqlite"
    _create_v1_database(db)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(store_module.GraphStore, db) for _ in range(8)]
        stores = [future.result(timeout=15) for future in futures]

    assert len(stores) == 8
    assert _version(db) == "2"
    with sqlite3.connect(db) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM graph_meta WHERE key='schema_version'"
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='graph_run_bindings'"
        ).fetchone() == (1,)


def test_read_only_v1_reads_graph_without_migration_and_binding_lookup_fails(
    tmp_path: Path,
) -> None:
    error, *_ = _api()
    db = tmp_path / "graphs.sqlite"
    _create_v1_database(db)
    _seed_v1_graph(db)
    before = db.stat().st_mtime_ns

    readonly = store_module.GraphStore.open_read_only(db)

    assert readonly.load_graph("g1").node_ids() == ("a",)
    with pytest.raises(error) as exc:
        readonly.load_graph_run_bindings("legacy-run")
    _assert_code(exc.value, "GRAPH_RUN_BINDING_AUTHORITY_UNAVAILABLE")
    assert _version(db) == "1"
    assert db.stat().st_mtime_ns == before


def test_graph_digest_is_order_independent_and_semantic(tmp_path: Path) -> None:
    *_, digest = _api()
    first = _graph(("a", "b"))
    second = _graph(("b", "a"))
    changed = build_graph(
        [_node("a"), _node("b", objective="changed")],
        [TaskEdge("a", "b", DependencyType.DATA)],
    )

    assert digest(first) == digest(second)
    assert len(digest(first)) == 64
    assert digest(first) != digest(changed)


def test_graph_digest_uses_deterministic_unicode_utf8() -> None:
    *_, digest = _api()
    graph = build_graph(
        [_node("ก", objective="ทดสอบ 🌱")],
        [],
    )

    first = digest(graph)
    second = digest(graph)

    assert first == second
    assert len(first) == 64
    bytes.fromhex(first)


def test_missing_or_empty_graph_fails_before_run_minting(tmp_path: Path) -> None:
    error, *_ = _api()
    db = tmp_path / "graphs.sqlite"
    store = store_module.GraphStore(db)

    with pytest.raises(error) as exc:
        _prepare(store, graph_id="missing")
    _assert_code(exc.value, "GRAPH_DEFINITION_UNAVAILABLE")

    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM graph_runs").fetchone()[0] == 0


def test_first_prepare_and_lost_response_replay_return_same_run(tmp_path: Path) -> None:
    _api()
    db = tmp_path / "graphs.sqlite"
    store = store_module.GraphStore(db)
    store.save_graph(_graph(), "g1")

    first = _prepare(store)
    second = _prepare(store)

    assert first.run_id == second.run_id
    assert first.run_id.startswith("graph-run-v1:")
    assert first.preparation_ref == "prep-001"
    assert first.preparation_sha256 == second.preparation_sha256
    rows = store.load_graph_run_bindings(first.run_id)
    assert tuple(row.node_id for row in rows) == ("a",)
    assert rows[0].provider_id == "cointh-glm"


def test_missing_or_blank_preparation_ref_fails_without_insert(tmp_path: Path) -> None:
    error, *_ = _api()
    db = tmp_path / "graphs.sqlite"
    store = store_module.GraphStore(db)
    store.save_graph(_graph(), "g1")

    for ref in ("", "   "):
        with pytest.raises(error) as exc:
            _prepare(store, ref=ref)
        _assert_code(exc.value, "GRAPH_RUN_PREPARATION_REF_REQUIRED")

    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM graph_runs").fetchone()[0] == 0


def test_same_ref_different_intent_is_identity_mismatch(tmp_path: Path) -> None:
    error, *_ = _api()
    db = tmp_path / "graphs.sqlite"
    store = store_module.GraphStore(db)
    store.save_graph(_graph(), "g1")
    _prepare(store)

    with pytest.raises(error) as exc:
        _prepare(store, bindings=(_binding(provider_id="other-provider"),))

    _assert_code(exc.value, "GRAPH_RUN_PREPARATION_IDENTITY_MISMATCH")
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM graph_runs").fetchone()[0] == 1


def test_new_preparation_ref_intentionally_mints_new_run(tmp_path: Path) -> None:
    _api()
    db = tmp_path / "graphs.sqlite"
    store = store_module.GraphStore(db)
    store.save_graph(_graph(), "g1")

    first = _prepare(store, ref="prep-001")
    second = _prepare(store, ref="prep-002")

    assert first.run_id != second.run_id


def test_unknown_binding_node_fails_before_any_run_insert(tmp_path: Path) -> None:
    error, *_ = _api()
    db = tmp_path / "graphs.sqlite"
    store = store_module.GraphStore(db)
    store.save_graph(_graph(), "g1")

    with pytest.raises(error) as exc:
        _prepare(store, bindings=(_binding("missing"),))

    _assert_code(exc.value, "GRAPH_RUN_BINDING_NODE_INVALID")
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM graph_runs").fetchone()[0] == 0


def test_non_serena_runtime_kind_fails_before_insert(tmp_path: Path) -> None:
    error, binding_type, *_ = _api()
    db = tmp_path / "graphs.sqlite"
    store = store_module.GraphStore(db)
    store.save_graph(_graph(), "g1")
    invalid = binding_type(
        node_id="a",
        runtime_kind="other",
        task_contract_ref="contracts/a.json",
        task_contract_sha256="a" * 64,
        task_packet_ref="packets/a.json",
        task_packet_sha256="b" * 64,
        provider_id="cointh-glm",
        model_id="glm-5.3",
        effort_level="max",
    )

    with pytest.raises(error) as exc:
        _prepare(store, bindings=(invalid,))

    _assert_code(exc.value, "RUNTIME_KIND_AUTHORITY_UNAVAILABLE")


def test_precommit_binding_failure_rolls_back_run_and_bindings(tmp_path: Path) -> None:
    error, *_ = _api()
    db = tmp_path / "graphs.sqlite"
    store = store_module.GraphStore(db)
    store.save_graph(_graph(), "g1")
    with sqlite3.connect(db) as conn:
        conn.executescript(
            """
            CREATE TRIGGER abort_binding_insert
            BEFORE INSERT ON graph_run_bindings
            BEGIN
              SELECT RAISE(ABORT, 'injected binding failure');
            END;
            """
        )

    with pytest.raises(error):
        _prepare(store)

    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM graph_runs").fetchone()[0] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM graph_run_bindings"
        ).fetchone()[0] == 0


def test_concurrent_identical_prepare_converges_on_one_run(tmp_path: Path) -> None:
    _api()
    db = tmp_path / "graphs.sqlite"
    store = store_module.GraphStore(db)
    store.save_graph(_graph(), "g1")
    barrier = threading.Barrier(6)

    def prepare_once():
        local = store_module.GraphStore(db)
        barrier.wait(timeout=5)
        return _prepare(local).run_id

    with ThreadPoolExecutor(max_workers=6) as pool:
        ids = list(pool.map(lambda _: prepare_once(), range(6)))

    assert len(set(ids)) == 1
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM graph_runs").fetchone()[0] == 1


def test_concurrent_conflicting_prepare_has_one_winner_and_one_mismatch(
    tmp_path: Path,
) -> None:
    error, *_ = _api()
    db = tmp_path / "graphs.sqlite"
    store = store_module.GraphStore(db)
    store.save_graph(_graph(), "g1")
    barrier = threading.Barrier(2)

    def prepare_with(provider_id: str):
        local = store_module.GraphStore(db)
        barrier.wait(timeout=5)
        try:
            return ("ok", _prepare(local, bindings=(_binding(provider_id=provider_id),)))
        except error as exc:
            return ("error", exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(prepare_with, ("p1", "p2")))

    assert sorted(kind for kind, _ in outcomes) == ["error", "ok"]
    failure = next(value for kind, value in outcomes if kind == "error")
    _assert_code(failure, "GRAPH_RUN_PREPARATION_IDENTITY_MISMATCH")


def test_replay_detects_missing_durable_binding_as_recovery_required(
    tmp_path: Path,
) -> None:
    error, *_ = _api()
    db = tmp_path / "graphs.sqlite"
    store = store_module.GraphStore(db)
    store.save_graph(_graph(), "g1")
    first = _prepare(store)
    with sqlite3.connect(db) as conn:
        conn.execute(
            "DELETE FROM graph_run_bindings WHERE run_id=? AND node_id='a'",
            (first.run_id,),
        )

    with pytest.raises(error) as exc:
        _prepare(store)

    _assert_code(exc.value, "GRAPH_RUN_PREPARATION_RECOVERY_REQUIRED")


def test_replay_detects_extra_durable_binding_as_recovery_required(
    tmp_path: Path,
) -> None:
    error, *_ = _api()
    db = tmp_path / "graphs.sqlite"
    store = store_module.GraphStore(db)
    store.save_graph(_graph(), "g1")
    first = _prepare(store)
    with sqlite3.connect(db) as conn:
        conn.execute(
            """
            INSERT INTO graph_run_bindings(
                run_id, node_id, runtime_kind,
                task_contract_ref, task_contract_sha256,
                task_packet_ref, task_packet_sha256,
                provider_id, model_id, effort_level, bound_at
            ) VALUES (?, 'b', 'serena', 'contracts/b.json', ?, 'packets/b.json', ?,
                      'cointh-glm', 'glm-5.3', 'max', '2026-09-21T00:00:00Z')
            """,
            (first.run_id, "c" * 64, "d" * 64),
        )

    with pytest.raises(error) as exc:
        _prepare(store)

    _assert_code(exc.value, "GRAPH_RUN_PREPARATION_RECOVERY_REQUIRED")


def test_no_public_rebind_or_mint_api_and_prepared_row_stays_inert(
    tmp_path: Path,
) -> None:
    _api()
    db = tmp_path / "graphs.sqlite"
    store = store_module.GraphStore(db)
    store.save_graph(_graph(), "g1")
    prepared = _prepare(store)

    assert not hasattr(store, "mint_run")
    assert not hasattr(store, "rebind_graph_run")
    assert not hasattr(store, "update_graph_run_binding")
    loaded = store.load_graph_run(prepared.run_id)
    assert loaded.run_id == prepared.run_id
    with sqlite3.connect(db) as conn:
        status = conn.execute(
            "SELECT status FROM graph_runs WHERE run_id=?", (prepared.run_id,)
        ).fetchone()[0]
    assert status == "pending"


def test_write_lock_contention_is_typed_and_has_no_internal_retry_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    error, *_ = _api()
    db = tmp_path / "graphs.sqlite"
    store = store_module.GraphStore(db)
    store.save_graph(_graph(), "g1")

    real_connect = store_module.sqlite3.connect

    def zero_timeout_connect(*args, **kwargs):
        kwargs.setdefault("timeout", 0)
        return real_connect(*args, **kwargs)

    locker = real_connect(db)
    locker.execute("BEGIN IMMEDIATE")
    monkeypatch.setattr(store_module.sqlite3, "connect", zero_timeout_connect)
    started = time.monotonic()
    try:
        with pytest.raises(error) as exc:
            _prepare(store)
    finally:
        locker.rollback()
        locker.close()

    assert time.monotonic() - started < 1.0
    _assert_code(exc.value, "GRAPH_RUN_PREPARATION_STORE_BUSY")
