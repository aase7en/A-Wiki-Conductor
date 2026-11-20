from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Barrier, Thread

import pytest

from a_conductor import worker_lease as worker_lease_module
from a_conductor.dex_identity import canonical_root_digest, canonicalize_existing_root
from a_conductor.graph.analyze import write_sets_overlap as analyze_write_sets_overlap
from a_conductor.worker_lease import (
    HotspotFenceKind,
    LeaseMutationIntent,
    SQLiteWorkerLeaseStore,
    WorkerLeaseBroker,
    WorkerLeaseCandidate,
    WorkerLeaseError,
    WorkerLeaseRequest,
    default_hotspot_resolver,
)

NOW = datetime(2026, 9, 23, 0, 0, tzinfo=timezone.utc)
PLATFORM_TAG = "win32" if os.name == "nt" else "posix"


def candidate(worker_id: str, *, worktree: str = r"A:\Repo") -> WorkerLeaseCandidate:
    return WorkerLeaseCandidate(
        worker_id=worker_id, state="READY", reserved=False, active_task=False,
        capabilities=("shell",), runtime_id=None, project_id="project-1",
        worktree=worktree, branch="feat/test", head="a" * 40, health_fresh=True,
        ownership_known=True, dirty_state="CLEAN", mutation_authorized=True,
    )


def mutation_request(
    *,
    session: str,
    task: str,
    worktree: str = r"A:\Repo",
    mutable: tuple[str, ...] = ("src/a.py",),
    project: str = "project-1",
    worker: str = "a-worker-01",
    allowed: tuple[str, ...] = ("src/**", "tests/**"),
) -> WorkerLeaseRequest:
    return WorkerLeaseRequest(
        session_id=session, task_id=task, project_id=project,
        ordered_worker_ids=(worker,), required_capabilities=("shell",),
        required_runtime_id=None, worktree=worktree, branch="feat/test",
        expected_head="a" * 40, mutation_intent=LeaseMutationIntent.MUTATION,
        allowed_scope=allowed, forbidden_scope=("secrets/**",), mutable_scope=mutable,
    )


def read_only_request(
    *,
    session: str,
    task: str,
    worktree: str = r"A:\Repo",
    project: str = "project-1",
    worker: str = "a-worker-01",
) -> WorkerLeaseRequest:
    return WorkerLeaseRequest(
        session_id=session, task_id=task, project_id=project,
        ordered_worker_ids=(worker,), required_capabilities=("shell",),
        required_runtime_id=None, worktree=worktree, branch="feat/test",
        expected_head="a" * 40, mutation_intent=LeaseMutationIntent.READ_ONLY,
        allowed_scope=("src/a.py",), forbidden_scope=("secrets/**",),
    )


def mapped_store(database: Path, mapping: dict[str, str]) -> SQLiteWorkerLeaseStore:
    return SQLiteWorkerLeaseStore(database, hotspot_resolver=lambda worktree: mapping[worktree])


LEGACY_SCHEMA = """
CREATE TABLE IF NOT EXISTS worker_leases (
    lease_id TEXT PRIMARY KEY, worker_id TEXT NOT NULL, session_id TEXT NOT NULL,
    task_id TEXT NOT NULL, project_id TEXT NOT NULL, runtime_id TEXT,
    worktree_key TEXT NOT NULL, branch TEXT NOT NULL, expected_head TEXT NOT NULL,
    required_capabilities_json TEXT NOT NULL, allowed_scope_json TEXT NOT NULL,
    forbidden_scope_json TEXT NOT NULL, mutable_scope_json TEXT NOT NULL,
    mutation_intent TEXT NOT NULL, acquired_at TEXT NOT NULL, expires_at TEXT, released_at TEXT
);
"""


def seed_legacy_row(
    database: Path,
    *,
    lease_id: str = "legacy-1",
    session: str = "legacy-session",
    task: str = "legacy-task",
    worktree_key: str = "a:\\legacy",
    intent: str = "MUTATION",
    released: str | None = None,
) -> None:
    connection = sqlite3.connect(database)
    connection.executescript(LEGACY_SCHEMA)
    connection.execute(
        "INSERT INTO worker_leases VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            lease_id, "a-worker-09", session, task, "project-1", "runtime-1",
            worktree_key, "feat/test", "a" * 40, '["shell"]', '["src/**"]',
            '["secrets/**"]', '["src/legacy.py"]', intent,
            "2026-09-23T00:00:00.000000Z", "2026-09-23T00:01:00.000000Z", released,
        ),
    )
    connection.commit()
    connection.close()


def make_git_worktree_family(root: Path) -> tuple[Path, Path]:
    main = root / "main"
    (main / ".git").mkdir(parents=True)
    admin = main / ".git" / "worktrees" / "wt1"
    admin.mkdir(parents=True)
    (admin / "commondir").write_text("../../", encoding="utf-8")
    worktree = root / "wt"
    worktree.mkdir()
    (worktree / ".git").write_text(f"gitdir: {admin}", encoding="utf-8")
    return main, worktree


def expected_hotspot_for(path: Path) -> str:
    return canonical_root_digest(
        canonicalize_existing_root(path), platform_tag=PLATFORM_TAG
    )


def test_independent_connections_racing_same_hotspot_produce_one_winner(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    first = mapped_store(database, {r"A:\Repo": "hot-a"})
    second = mapped_store(database, {r"A:\Repo": "hot-a"})
    barrier = Barrier(2)

    def acquire(store: SQLiteWorkerLeaseStore, session: str, task: str, worker: str, lease_id: str):
        barrier.wait()
        try:
            return store.try_acquire(
                mutation_request(session=session, task=task, worker=worker),
                candidate(worker),
                lease_id=lease_id,
                acquired_at=NOW,
            )
        except WorkerLeaseError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        left = pool.submit(acquire, first, "s1", "t1", "a-worker-01", "lease-1")
        right = pool.submit(acquire, second, "s2", "t2", "a-worker-02", "lease-2")
        results = (left.result(), right.result())

    leases = [item for item in results if not isinstance(item, str) and item is not None]
    errors = [item for item in results if isinstance(item, str)]
    assert len(leases) == 1
    assert errors == ["MUTABLE_SCOPE_OVERLAP"]
    assert leases[0].hotspot_key == "hot-a"
    assert len(first.list_active()) == 1


def test_distinct_worktree_paths_same_hotspot_one_winner(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    store = mapped_store(database, {r"A:\WT1": "hot-a", r"A:\WT2": "hot-a"})
    first = store.try_acquire(
        mutation_request(session="s1", task="t1", worktree=r"A:\WT1", worker="a-worker-01"),
        candidate("a-worker-01", worktree=r"A:\WT1"),
        lease_id="lease-1", acquired_at=NOW,
    )
    assert first is not None
    assert first.hotspot_key == "hot-a"
    with pytest.raises(WorkerLeaseError, match="MUTABLE_SCOPE_OVERLAP"):
        store.try_acquire(
            mutation_request(session="s2", task="t2", worktree=r"A:\WT2", worker="a-worker-02"),
            candidate("a-worker-02", worktree=r"A:\WT2"),
            lease_id="lease-2", acquired_at=NOW,
        )
    assert len(store.list_active()) == 1


def test_different_hotspots_overlapping_relative_scope_proceed_independently(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    store = mapped_store(database, {r"A:\WT1": "hot-a", r"A:\WT2": "hot-b"})
    first = store.try_acquire(
        mutation_request(session="s1", task="t1", worktree=r"A:\WT1", worker="a-worker-01"),
        candidate("a-worker-01", worktree=r"A:\WT1"),
        lease_id="lease-1", acquired_at=NOW,
    )
    second = store.try_acquire(
        mutation_request(session="s2", task="t2", worktree=r"A:\WT2", worker="a-worker-02"),
        candidate("a-worker-02", worktree=r"A:\WT2"),
        lease_id="lease-2", acquired_at=NOW,
    )
    assert first is not None and second is not None
    assert first.hotspot_key == "hot-a"
    assert second.hotspot_key == "hot-b"
    assert len(store.list_active()) == 2


def test_same_hotspot_disjoint_scopes_proceed_independently(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    store = mapped_store(database, {r"A:\Repo": "hot-a"})
    first = store.try_acquire(
        mutation_request(session="s1", task="t1", mutable=("src/a.py",), worker="a-worker-01"),
        candidate("a-worker-01"), lease_id="lease-1", acquired_at=NOW,
    )
    second = store.try_acquire(
        mutation_request(session="s2", task="t2", mutable=("tests/b.py",), worker="a-worker-02"),
        candidate("a-worker-02"), lease_id="lease-2", acquired_at=NOW,
    )
    assert first is not None and second is not None
    assert len(store.list_active()) == 2
    status = store.hotspot_fence_status()
    assert status.kind is HotspotFenceKind.LOCAL_FENCE_ENFORCED
    assert status.active_mutation_leases == 2
    assert status.active_mutation_leases_missing_hotspot == 0


def test_active_legacy_null_hotspot_mutation_row_blocks_new_mutation(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    worktree = tmp_path / "new-worktree"
    worktree.mkdir()
    seed_legacy_row(database)
    store = SQLiteWorkerLeaseStore(database)

    with pytest.raises(WorkerLeaseError, match="HOTSPOT_RECONCILIATION_REQUIRED"):
        store.try_acquire(
            mutation_request(
                session="s2",
                task="t2",
                worktree=str(worktree),
                mutable=("docs/x.md",),
                allowed=("docs/**", "src/**", "tests/**"),
                worker="a-worker-01",
            ),
            candidate("a-worker-01", worktree=str(worktree)),
            lease_id="lease-new", acquired_at=NOW,
        )
    assert len(store.list_active()) == 1

    status = store.hotspot_fence_status()
    assert status.kind is HotspotFenceKind.LOCAL_FENCE_RECONCILIATION_REQUIRED
    assert status.active_mutation_leases == 1
    assert status.active_mutation_leases_missing_hotspot == 1


def test_legacy_row_owner_retry_still_reuses_its_own_lease(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    worktree = tmp_path / "legacy-worktree"
    worktree.mkdir()
    seed_legacy_row(
        database,
        worktree_key=worker_lease_module.windows_worktree_key(str(worktree)),
    )
    store = SQLiteWorkerLeaseStore(database)
    retry = WorkerLeaseRequest(
        session_id="legacy-session", task_id="legacy-task", project_id="project-1",
        ordered_worker_ids=("a-worker-09",), required_capabilities=("shell",),
        required_runtime_id=None, worktree=str(worktree), branch="feat/test",
        expected_head="a" * 40, mutation_intent=LeaseMutationIntent.MUTATION,
        allowed_scope=("src/**",), forbidden_scope=("secrets/**",),
        mutable_scope=("src/legacy.py",), lease_ttl_seconds=60,
    )
    result = store.try_acquire_result(
        retry, candidate("a-worker-09", worktree=str(worktree)),
        lease_id="lease-retry", acquired_at=NOW,
    )
    assert result.created is False
    assert result.lease is not None and result.lease.lease_id == "legacy-1"
    assert result.lease.hotspot_key is None
    assert len(store.list_active()) == 1


def test_released_legacy_row_no_longer_blocks_new_mutation(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    worktree = tmp_path / "new-worktree"
    worktree.mkdir()
    seed_legacy_row(database)
    store = SQLiteWorkerLeaseStore(database)
    store.release(
        "legacy-1", session_id="legacy-session", task_id="legacy-task",
        released_at="2026-09-23T00:00:30.000000Z",
    )
    lease = store.try_acquire(
        mutation_request(
            session="s2", task="t2", worker="a-worker-01", worktree=str(worktree)
        ),
        candidate("a-worker-01", worktree=str(worktree)),
        lease_id="lease-new", acquired_at=NOW,
    )
    assert lease is not None
    assert lease.hotspot_key is not None
    assert store.hotspot_fence_status().kind is HotspotFenceKind.LOCAL_FENCE_ENFORCED


def test_additive_migration_preserves_legacy_rows(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    seed_legacy_row(database, lease_id="legacy-active", released=None)
    seed_legacy_row(database, lease_id="legacy-done", session="done", task="done", released="2026-09-23T00:00:10.000000Z")
    store = SQLiteWorkerLeaseStore(database)

    connection = sqlite3.connect(database)
    columns = [row[1] for row in connection.execute("PRAGMA table_info(worker_leases)")]
    connection.close()
    assert columns.count("hotspot_key") == 1

    active = store.list_active()
    assert len(active) == 1
    assert active[0].lease_id == "legacy-active"
    assert active[0].hotspot_key is None
    assert active[0].lease_ttl_seconds == 60
    assert active[0].heartbeat_at == active[0].acquired_at


def test_concurrent_initialize_on_fresh_database_is_deterministic(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    barrier = Barrier(6)
    errors: list[BaseException] = []

    def open_store() -> None:
        barrier.wait()
        try:
            SQLiteWorkerLeaseStore(database)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [Thread(target=open_store) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []

    connection = sqlite3.connect(database)
    columns = [row[1] for row in connection.execute("PRAGMA table_info(worker_leases)")]
    connection.close()
    assert columns.count("hotspot_key") == 1


def test_concurrent_initialize_on_legacy_database_is_deterministic(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    seed_legacy_row(database)
    barrier = Barrier(6)
    errors: list[BaseException] = []

    def open_store() -> None:
        barrier.wait()
        try:
            SQLiteWorkerLeaseStore(database)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [Thread(target=open_store) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []

    store = SQLiteWorkerLeaseStore(database)
    assert len(store.list_active()) == 1
    assert store.list_active()[0].lease_id == "legacy-1"


def test_same_owner_retry_with_hotspot_drift_fails_closed(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    current = {"value": "hot-a"}
    store = SQLiteWorkerLeaseStore(database, hotspot_resolver=lambda worktree: current["value"])
    request = mutation_request(session="s1", task="t1")
    lease = store.try_acquire(request, candidate("a-worker-01"), lease_id="lease-1", acquired_at=NOW)
    assert lease is not None

    current["value"] = "hot-b"
    with pytest.raises(WorkerLeaseError, match="LEASE_REQUEST_CONFLICT"):
        store.try_acquire(request, candidate("a-worker-01"), lease_id="lease-2", acquired_at=NOW)
    assert len(store.list_active()) == 1

    broker = WorkerLeaseBroker(store=store, lease_id_factory=lambda: "lease-3", clock=lambda: NOW)
    with pytest.raises(WorkerLeaseError, match="LEASE_REQUEST_CONFLICT"):
        broker.acquire(request, (candidate("a-worker-01"),))
    assert len(store.list_active()) == 1


@pytest.mark.parametrize(
    "resolver",
    [
        lambda worktree: (_ for _ in ()).throw(RuntimeError("resolver boom")),
        lambda worktree: "",
        lambda worktree: 123,  # type: ignore[return-value]
    ],
)
def test_resolver_failure_or_invalid_output_fails_closed(tmp_path: Path, resolver) -> None:
    database = tmp_path / "leases.sqlite"
    store = SQLiteWorkerLeaseStore(database, hotspot_resolver=resolver)
    with pytest.raises(WorkerLeaseError, match="HOTSPOT_IDENTITY_FAILED"):
        store.try_acquire(
            mutation_request(session="s1", task="t1"), candidate("a-worker-01"),
            lease_id="lease-1", acquired_at=NOW,
        )
    assert store.list_active() == ()


def test_default_resolver_missing_worktree_raises_identity_failure(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    store = SQLiteWorkerLeaseStore(database)
    with pytest.raises(WorkerLeaseError, match="HOTSPOT_IDENTITY_FAILED"):
        store.resolve_mutation_hotspot("")


def test_store_identity_is_stable_and_observable_across_instances(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    other = tmp_path / "other" / "leases.sqlite"
    first = SQLiteWorkerLeaseStore(database)
    second = SQLiteWorkerLeaseStore(database)
    assert first.store_identity == second.store_identity
    assert len(first.store_identity) == 64

    variant = database.parent / ".." / database.parent.name / database.name
    third = SQLiteWorkerLeaseStore(variant)
    assert third.store_identity == first.store_identity

    assert SQLiteWorkerLeaseStore(other).store_identity != first.store_identity


def test_default_resolver_converges_worktrees_sharing_git_common_dir(tmp_path: Path) -> None:
    main, worktree = make_git_worktree_family(tmp_path)
    database = tmp_path / "leases.sqlite"
    store = SQLiteWorkerLeaseStore(database)

    main_hotspot = store.resolve_mutation_hotspot(str(main))
    worktree_hotspot = store.resolve_mutation_hotspot(str(worktree))
    assert main_hotspot == worktree_hotspot
    assert main_hotspot == expected_hotspot_for(main / ".git")

    first = store.try_acquire(
        mutation_request(session="s1", task="t1", worktree=str(main), worker="a-worker-01"),
        candidate("a-worker-01", worktree=str(main)),
        lease_id="lease-1", acquired_at=NOW,
    )
    assert first is not None
    with pytest.raises(WorkerLeaseError, match="MUTABLE_SCOPE_OVERLAP"):
        store.try_acquire(
            mutation_request(session="s2", task="t2", worktree=str(worktree), worker="a-worker-02"),
            candidate("a-worker-02", worktree=str(worktree)),
            lease_id="lease-2", acquired_at=NOW,
        )
    assert len(store.list_active()) == 1


def test_default_resolver_converges_separator_and_case_aliases(tmp_path: Path) -> None:
    main, _ = make_git_worktree_family(tmp_path)
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    base = str(main)
    variants = [base, base + os.sep + "." + os.sep]
    if sys.platform == "win32":
        variants.append(base.swapcase())
    hotspots = {store.resolve_mutation_hotspot(variant) for variant in variants}
    assert len(hotspots) == 1


def test_default_resolver_missing_worktree_fails_closed(tmp_path: Path) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    for spelling in (r"A:\Repo", r"a:/repo/.", "A:\\Repo\\.\\"):
        with pytest.raises(WorkerLeaseError, match="HOTSPOT_IDENTITY_FAILED"):
            store.resolve_mutation_hotspot(spelling)


def test_default_resolver_probe_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    worktree = tmp_path / "blocked"
    worktree.mkdir()
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    original_exists = Path.exists

    def failing_exists(path: Path) -> bool:
        if path == worktree:
            raise OSError("probe denied")
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", failing_exists)
    with pytest.raises(WorkerLeaseError, match="HOTSPOT_IDENTITY_FAILED"):
        store.resolve_mutation_hotspot(str(worktree))


@pytest.mark.skipif(sys.platform != "win32", reason="junction alias requires win32")
def test_default_resolver_converges_junction_alias(tmp_path: Path) -> None:
    import _winapi

    main, _ = make_git_worktree_family(tmp_path)
    link = tmp_path / "main-link"
    _winapi.CreateJunction(str(main), str(link))
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    assert store.resolve_mutation_hotspot(str(main)) == store.resolve_mutation_hotspot(str(link))


def test_hotspot_fence_reuses_write_sets_overlap_seam(tmp_path: Path) -> None:
    assert worker_lease_module.write_sets_overlap is analyze_write_sets_overlap

    database = tmp_path / "leases.sqlite"
    store = mapped_store(database, {r"A:\Repo": "hot-a"})
    assert store.try_acquire(
        mutation_request(session="s1", task="t1", mutable=("src/**",), worker="a-worker-01"),
        candidate("a-worker-01"), lease_id="lease-1", acquired_at=NOW,
    ) is not None
    with pytest.raises(WorkerLeaseError, match="MUTABLE_SCOPE_OVERLAP"):
        store.try_acquire(
            mutation_request(session="s2", task="t2", mutable=("src/a.py",), worker="a-worker-02"),
            candidate("a-worker-02"), lease_id="lease-2", acquired_at=NOW,
        )
    disjoint = store.try_acquire(
        mutation_request(session="s3", task="t3", mutable=("tests/b.py",), worker="a-worker-03"),
        candidate("a-worker-03"), lease_id="lease-3", acquired_at=NOW,
    )
    assert disjoint is not None


def test_provenance_differences_do_not_affect_hotspot_ownership(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    store = mapped_store(database, {r"A:\Repo": "hot-a"})
    first = store.try_acquire(
        mutation_request(session="chat-alpha", task="issue-1", project="project-1", worker="a-worker-01"),
        candidate("a-worker-01"), lease_id="lease-1", acquired_at=NOW,
    )
    assert first is not None
    with pytest.raises(WorkerLeaseError, match="MUTABLE_SCOPE_OVERLAP"):
        store.try_acquire(
            mutation_request(session="chat-beta", task="issue-2", project="project-2", worker="a-worker-02"),
            candidate("a-worker-02"), lease_id="lease-2", acquired_at=NOW,
        )
    assert len(store.list_active()) == 1


def test_db_restart_preserves_active_hotspot_fence(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    store = mapped_store(database, {r"A:\Repo": "hot-a"})
    assert store.try_acquire(
        mutation_request(session="s1", task="t1", worker="a-worker-01"),
        candidate("a-worker-01"), lease_id="lease-1", acquired_at=NOW,
    ) is not None
    del store

    reopened = mapped_store(database, {r"A:\Repo": "hot-a"})
    with pytest.raises(WorkerLeaseError, match="MUTABLE_SCOPE_OVERLAP"):
        reopened.try_acquire(
            mutation_request(session="s2", task="t2", worker="a-worker-02"),
            candidate("a-worker-02"), lease_id="lease-2", acquired_at=NOW,
        )
    assert len(reopened.list_active()) == 1


def test_released_lease_permits_later_valid_acquisition(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    store = mapped_store(database, {r"A:\Repo": "hot-a"})
    first = store.try_acquire(
        mutation_request(session="s1", task="t1", worker="a-worker-01"),
        candidate("a-worker-01"), lease_id="lease-1", acquired_at=NOW,
    )
    assert first is not None
    store.release("lease-1", session_id="s1", task_id="t1", released_at="2026-09-23T00:00:10.000000Z")

    second = store.try_acquire(
        mutation_request(session="s2", task="t2", worker="a-worker-02"),
        candidate("a-worker-02"), lease_id="lease-2", acquired_at=NOW,
    )
    assert second is not None
    assert second.hotspot_key == "hot-a"
    assert len(store.list_active()) == 1


def test_read_only_leases_are_not_mutation_hotspot_authority(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    store = mapped_store(database, {r"A:\Repo": "hot-a"})
    reader = store.try_acquire(
        read_only_request(session="s1", task="t1", worker="a-worker-01"),
        candidate("a-worker-01"), lease_id="lease-ro", acquired_at=NOW,
    )
    assert reader is not None
    assert reader.hotspot_key is None

    writer = store.try_acquire(
        mutation_request(session="s2", task="t2", worker="a-worker-02"),
        candidate("a-worker-02"), lease_id="lease-mut", acquired_at=NOW,
    )
    assert writer is not None
    status = store.hotspot_fence_status()
    assert status.kind is HotspotFenceKind.LOCAL_FENCE_ENFORCED
    assert status.active_mutation_leases == 1
    assert status.active_mutation_leases_missing_hotspot == 0


def test_read_only_admission_preserved_during_legacy_null_mutation_row(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    seed_legacy_row(database)
    store = SQLiteWorkerLeaseStore(database)
    reader = store.try_acquire(
        read_only_request(session="s2", task="t2", worker="a-worker-01"),
        candidate("a-worker-01"), lease_id="lease-ro", acquired_at=NOW,
    )
    assert reader is not None
    assert store.hotspot_fence_status().kind is HotspotFenceKind.LOCAL_FENCE_RECONCILIATION_REQUIRED


def test_broker_mutation_drift_and_resolver_failure_fail_closed(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    state = {"value": "hot-a"}
    store = SQLiteWorkerLeaseStore(database, hotspot_resolver=lambda worktree: state["value"])
    broker = WorkerLeaseBroker(store=store, lease_id_factory=lambda: "lease-1", clock=lambda: NOW)
    request = mutation_request(session="s1", task="t1")
    assert broker.acquire(request, (candidate("a-worker-01"),)).lease is not None

    state["value"] = "hot-b"
    with pytest.raises(WorkerLeaseError, match="LEASE_REQUEST_CONFLICT"):
        broker.acquire(request, (candidate("a-worker-01"),))

    def explode(worktree: str) -> str:
        raise RuntimeError("resolver boom")

    store2 = SQLiteWorkerLeaseStore(tmp_path / "other.sqlite", hotspot_resolver=explode)
    broker2 = WorkerLeaseBroker(store=store2, lease_id_factory=lambda: "lease-2", clock=lambda: NOW)
    with pytest.raises(WorkerLeaseError, match="HOTSPOT_IDENTITY_FAILED"):
        broker2.acquire(mutation_request(session="s1", task="t1"), (candidate("a-worker-01"),))
    assert store2.list_active() == ()


def test_default_resolver_is_deterministic_for_stable_worktree(tmp_path: Path) -> None:
    main, _ = make_git_worktree_family(tmp_path)
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    assert store.resolve_mutation_hotspot(str(main)) == store.resolve_mutation_hotspot(str(main))
    assert default_hotspot_resolver(str(main)) == store.resolve_mutation_hotspot(str(main))


RACE_CHILD = """
import json, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
(db, worktree, session, task, worker, ready, go) = sys.argv[2:9]
from a_conductor.worker_lease import (
    LeaseMutationIntent, SQLiteWorkerLeaseStore, WorkerLeaseCandidate,
    WorkerLeaseError, WorkerLeaseRequest,
)
Path(ready).write_text("READY", encoding="utf-8")
deadline = time.monotonic() + 60.0
while not Path(go).exists():
    if time.monotonic() > deadline:
        raise SystemExit("go timeout")
    time.sleep(0.005)
request = WorkerLeaseRequest(
    session_id=session, task_id=task, project_id="project-1",
    ordered_worker_ids=(worker,), required_capabilities=("shell",),
    required_runtime_id=None, worktree=worktree, branch="feat/test",
    expected_head="a" * 40, mutation_intent=LeaseMutationIntent.MUTATION,
    allowed_scope=("src/**",), forbidden_scope=("secrets/**",),
    mutable_scope=("src/a.py",),
)
worker_candidate = WorkerLeaseCandidate(
    worker_id=worker, state="READY", reserved=False, active_task=False,
    capabilities=("shell",), runtime_id=None, project_id="project-1",
    worktree=worktree, branch="feat/test", head="a" * 40, health_fresh=True,
    ownership_known=True, dirty_state="CLEAN", mutation_authorized=True,
)
store = SQLiteWorkerLeaseStore(db)
try:
    lease = store.try_acquire(
        request, worker_candidate, lease_id="lease-child",
        acquired_at="2026-09-23T00:00:00.000000Z",
    )
except WorkerLeaseError as exc:
    print(json.dumps({"error": exc.code}))
else:
    print(json.dumps({"lease_id": lease.lease_id if lease else None}))
"""


def wait_for_file(path: Path, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while not path.exists():
        assert time.monotonic() < deadline, f"timed out waiting for {path}"
        time.sleep(0.01)


def test_two_process_same_hotspot_race_has_exactly_one_winner(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    ready = tmp_path / "child-ready.txt"
    go = tmp_path / "go.txt"
    main, linked = make_git_worktree_family(tmp_path)
    source_root = Path(__file__).resolve().parents[1] / "src"
    process = subprocess.Popen(
        [
            sys.executable, "-c", RACE_CHILD, str(source_root), str(database),
            str(linked), "child-session", "child-task", "a-worker-02",
            str(ready), str(go),
        ],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        wait_for_file(ready)
        go.write_text("GO", encoding="utf-8")
        store = SQLiteWorkerLeaseStore(database)
        parent_error: str | None = None
        parent_created = False
        try:
            lease = store.try_acquire(
                mutation_request(
                    session="parent-session",
                    task="parent-task",
                    worker="a-worker-01",
                    worktree=str(main),
                ),
                candidate("a-worker-01", worktree=str(main)),
                lease_id="lease-parent",
                acquired_at=NOW,
            )
            parent_created = lease is not None
        except WorkerLeaseError as exc:
            parent_error = exc.code
        out, err = process.communicate(timeout=90)
    finally:
        if process.poll() is None:  # pragma: no cover - cleanup only
            process.kill()
    assert process.returncode == 0, err
    payload = json.loads(out.strip().splitlines()[-1])
    child_created = payload.get("lease_id") is not None
    assert int(parent_created) + int(child_created) == 1
    loser_codes = [code for code in (parent_error, payload.get("error")) if code]
    assert loser_codes == ["MUTABLE_SCOPE_OVERLAP"]
    active = SQLiteWorkerLeaseStore(database).list_active()
    assert len(active) == 1
    assert active[0].hotspot_key == default_hotspot_resolver(str(main))
    assert default_hotspot_resolver(str(main)) == default_hotspot_resolver(str(linked))


CONTENTION_CHILD = """
import sqlite3, sys, time
from pathlib import Path
db, marker = sys.argv[1:3]
con = sqlite3.connect(db)
con.execute("PRAGMA busy_timeout = 10000")
con.execute("BEGIN IMMEDIATE")
Path(marker).write_text("HELD", encoding="utf-8")
time.sleep(0.5)
con.commit()
con.close()
"""


def test_subprocess_db_contention_yields_typed_outcome(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    marker = tmp_path / "child-held.txt"
    worktree = tmp_path / "physical-worktree"
    worktree.mkdir()
    store = SQLiteWorkerLeaseStore(database)
    process = subprocess.Popen(
        [sys.executable, "-c", CONTENTION_CHILD, str(database), str(marker)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        wait_for_file(marker)
        lease = store.try_acquire(
            mutation_request(
                session="s1", task="t1", worker="a-worker-01", worktree=str(worktree)
            ),
            candidate("a-worker-01", worktree=str(worktree)),
            lease_id="lease-1", acquired_at=NOW,
        )
        out, err = process.communicate(timeout=60)
    finally:
        if process.poll() is None:  # pragma: no cover - cleanup only
            process.kill()
    assert process.returncode == 0, err
    assert lease is not None
    assert lease.hotspot_key == default_hotspot_resolver(str(worktree))
    assert len(store.list_active()) == 1
