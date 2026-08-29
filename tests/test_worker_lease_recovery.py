from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier

import pytest

from a_conductor.domain import RecoveryClassification
from a_conductor.worker_lease import (
    LeaseHealthKind,
    LeaseMutationIntent,
    LeaseOutcomeKind,
    LeaseReconciliationKind,
    SQLiteWorkerLeaseStore,
    WorkerLeaseBroker,
    WorkerLeaseCandidate,
    WorkerLeaseError,
    WorkerLeaseRecoveryObservation,
    WorkerLeaseRequest,
)

NOW = datetime(2026, 8, 29, 14, 0, tzinfo=timezone.utc)


def request(*, session: str = "session-1", task: str = "task-1", ttl: int = 60) -> WorkerLeaseRequest:
    return WorkerLeaseRequest(
        session_id=session,
        task_id=task,
        project_id="project-1",
        ordered_worker_ids=("a-worker-01", "a-worker-02"),
        required_capabilities=("shell",),
        required_runtime_id="runtime-1",
        worktree=r"A:\Repo",
        branch="feat/test",
        expected_head="a" * 40,
        mutation_intent=LeaseMutationIntent.MUTATION,
        allowed_scope=("src/**",),
        forbidden_scope=("secrets/**",),
        mutable_scope=("src/a.py",),
        lease_ttl_seconds=ttl,
    )


def candidate(worker_id: str = "a-worker-01") -> WorkerLeaseCandidate:
    return WorkerLeaseCandidate(
        worker_id=worker_id,
        state="READY",
        reserved=False,
        active_task=False,
        capabilities=("shell",),
        runtime_id="runtime-1",
        project_id="project-1",
        worktree=r"A:\Repo",
        branch="feat/test",
        head="a" * 40,
        health_fresh=True,
        ownership_known=True,
        dirty_state="CLEAN",
        mutation_authorized=True,
    )


def observation(
    *,
    at: datetime,
    classification: RecoveryClassification = RecoveryClassification.NO_MUTATION,
    runtime_running: bool | None = False,
    dirty_state: str = "CLEAN",
    ownership_known: bool = True,
    worktree: str = r"A:\Repo",
    branch: str = "feat/test",
    head: str = "a" * 40,
    evidence: str = "recovery:e1",
) -> WorkerLeaseRecoveryObservation:
    return WorkerLeaseRecoveryObservation(
        worker_id="a-worker-01",
        worktree=worktree,
        branch=branch,
        head=head,
        dirty_state=dirty_state,
        ownership_known=ownership_known,
        runtime_running=runtime_running,
        recovery_classification=classification,
        evidence_ref=evidence,
        observed_at=at,
    )


def open_broker(tmp_path: Path, *, now: datetime = NOW):
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    broker = WorkerLeaseBroker(
        store=store,
        lease_id_factory=lambda: "lease-1",
        clock=lambda: now,
    )
    return broker, store


def test_broker_creates_bounded_lease_and_heartbeat_extends_exact_owner(tmp_path: Path) -> None:
    broker, store = open_broker(tmp_path)
    outcome = broker.acquire(request(ttl=60), (candidate(),))
    assert outcome.kind is LeaseOutcomeKind.LEASED
    lease = outcome.lease
    assert lease is not None
    assert lease.heartbeat_at == "2026-08-29T14:00:00.000000Z"
    assert lease.expires_at == "2026-08-29T14:01:00.000000Z"

    renewed = store.heartbeat(
        lease.lease_id,
        session_id=lease.session_id,
        task_id=lease.task_id,
        heartbeat_at=NOW + timedelta(seconds=30),
    )
    assert renewed.heartbeat_at == "2026-08-29T14:00:30.000000Z"
    assert renewed.expires_at == "2026-08-29T14:01:30.000000Z"


def test_heartbeat_wrong_owner_and_older_timestamp_fail_closed(tmp_path: Path) -> None:
    broker, store = open_broker(tmp_path)
    lease = broker.acquire(request(), (candidate(),)).lease
    assert lease is not None
    with pytest.raises(WorkerLeaseError, match="LEASE_OWNER_MISMATCH"):
        store.heartbeat(lease.lease_id, session_id="other", task_id=lease.task_id, heartbeat_at=NOW)
    with pytest.raises(WorkerLeaseError, match="LEASE_HEARTBEAT_STALE"):
        store.heartbeat(
            lease.lease_id,
            session_id=lease.session_id,
            task_id=lease.task_id,
            heartbeat_at=NOW - timedelta(seconds=1),
        )


def test_expired_lease_cannot_be_revived_by_late_heartbeat(tmp_path: Path) -> None:
    broker, store = open_broker(tmp_path)
    lease = broker.acquire(request(ttl=10), (candidate(),)).lease
    assert lease is not None
    with pytest.raises(WorkerLeaseError, match="LEASE_HEARTBEAT_EXPIRED"):
        store.heartbeat(
            lease.lease_id,
            session_id=lease.session_id,
            task_id=lease.task_id,
            heartbeat_at=NOW + timedelta(seconds=11),
        )
    assert store.inspect_health(lease.lease_id, now=NOW + timedelta(seconds=11)).kind is LeaseHealthKind.STALE


def test_same_owner_retry_on_stale_lease_requires_recovery_not_fallback(tmp_path: Path) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    first = WorkerLeaseBroker(store=store, lease_id_factory=lambda: "lease-1", clock=lambda: NOW)
    stale = first.acquire(request(ttl=10), (candidate(), candidate("a-worker-02"))).lease
    assert stale is not None
    later = WorkerLeaseBroker(
        store=store,
        lease_id_factory=lambda: "lease-2",
        clock=lambda: NOW + timedelta(seconds=11),
    )
    outcome = later.acquire(request(ttl=10), (candidate(), candidate("a-worker-02")))
    assert outcome.kind is LeaseOutcomeKind.RECOVERY_REQUIRED
    assert outcome.lease is not None and outcome.lease.lease_id == stale.lease_id
    assert len(store.list_active()) == 1


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"runtime_running": True}, "RUNTIME_STILL_RUNNING"),
        ({"runtime_running": None}, "RUNTIME_STATE_UNKNOWN"),
        ({"dirty_state": "DIRTY"}, "WORKTREE_DIRTY"),
        ({"dirty_state": "UNKNOWN"}, "WORKTREE_DIRTY_UNKNOWN"),
        ({"ownership_known": False}, "OWNERSHIP_UNKNOWN"),
        ({"branch": "other"}, "BRANCH_MISMATCH"),
        ({"worktree": r"A:\Other"}, "WORKTREE_MISMATCH"),
        ({"head": "b" * 40}, "HEAD_MISMATCH"),
        ({"classification": RecoveryClassification.UNKNOWN}, "RECOVERY_UNKNOWN"),
        ({"classification": RecoveryClassification.PARTIAL_MUTATION}, "PARTIAL_MUTATION"),
        ({"classification": RecoveryClassification.UNEXPECTED_DRIFT}, "UNEXPECTED_DRIFT"),
    ],
)
def test_stale_ambiguous_observation_quarantines_and_preserves_lease(
    tmp_path: Path, changes: dict[str, object], reason: str
) -> None:
    broker, store = open_broker(tmp_path)
    lease = broker.acquire(request(ttl=5), (candidate(),)).lease
    assert lease is not None
    values = dict(at=NOW + timedelta(seconds=6))
    values.update(changes)
    result = store.reconcile_stale(
        lease.lease_id,
        session_id=lease.session_id,
        task_id=lease.task_id,
        observation=observation(**values),
    )
    assert result.kind is LeaseReconciliationKind.QUARANTINED
    assert result.reason_code == reason
    assert result.lease.released_at is None
    assert result.lease.quarantine_code == reason
    assert store.inspect_health(lease.lease_id, now=NOW + timedelta(seconds=6)).kind is LeaseHealthKind.QUARANTINED


def test_no_mutation_reconciliation_releases_stale_lease_for_reuse(tmp_path: Path) -> None:
    broker, store = open_broker(tmp_path)
    lease = broker.acquire(request(ttl=5), (candidate(),)).lease
    assert lease is not None
    result = store.reconcile_stale(
        lease.lease_id,
        session_id=lease.session_id,
        task_id=lease.task_id,
        observation=observation(at=NOW + timedelta(seconds=6)),
    )
    assert result.kind is LeaseReconciliationKind.RELEASED
    assert result.lease.released_at == "2026-08-29T14:00:06.000000Z"
    assert store.list_active() == ()


def test_complete_verified_can_release_clean_stopped_lease_with_new_head(tmp_path: Path) -> None:
    broker, store = open_broker(tmp_path)
    lease = broker.acquire(request(ttl=5), (candidate(),)).lease
    assert lease is not None
    result = store.reconcile_stale(
        lease.lease_id,
        session_id=lease.session_id,
        task_id=lease.task_id,
        observation=observation(
            at=NOW + timedelta(seconds=6),
            classification=RecoveryClassification.COMPLETE_VERIFIED,
            head="b" * 40,
        ),
    )
    assert result.kind is LeaseReconciliationKind.RELEASED


def test_quarantined_lease_cannot_be_heartbeat_revived(tmp_path: Path) -> None:
    broker, store = open_broker(tmp_path)
    lease = broker.acquire(request(ttl=5), (candidate(),)).lease
    assert lease is not None
    store.reconcile_stale(
        lease.lease_id,
        session_id=lease.session_id,
        task_id=lease.task_id,
        observation=observation(at=NOW + timedelta(seconds=6), dirty_state="UNKNOWN"),
    )
    with pytest.raises(WorkerLeaseError, match="LEASE_QUARANTINED"):
        store.heartbeat(
            lease.lease_id,
            session_id=lease.session_id,
            task_id=lease.task_id,
            heartbeat_at=NOW + timedelta(seconds=7),
        )


def test_reconcile_race_cannot_release_lease_renewed_before_stale_observation(tmp_path: Path) -> None:
    broker, store = open_broker(tmp_path)
    lease = broker.acquire(request(ttl=10), (candidate(),)).lease
    assert lease is not None
    store.heartbeat(
        lease.lease_id,
        session_id=lease.session_id,
        task_id=lease.task_id,
        heartbeat_at=NOW + timedelta(seconds=9),
    )
    with pytest.raises(WorkerLeaseError, match="LEASE_NOT_STALE"):
        store.reconcile_stale(
            lease.lease_id,
            session_id=lease.session_id,
            task_id=lease.task_id,
            observation=observation(at=NOW + timedelta(seconds=11)),
        )
    assert store.list_active()[0].released_at is None


def test_heartbeat_and_reconcile_race_never_yields_live_released_lease(tmp_path: Path) -> None:
    broker, store = open_broker(tmp_path)
    lease = broker.acquire(request(ttl=5), (candidate(),)).lease
    assert lease is not None
    barrier = Barrier(2)

    def heartbeat():
        barrier.wait()
        try:
            return store.heartbeat(
                lease.lease_id,
                session_id=lease.session_id,
                task_id=lease.task_id,
                heartbeat_at=NOW + timedelta(seconds=6),
            )
        except WorkerLeaseError as exc:
            return exc.code

    def reconcile():
        barrier.wait()
        try:
            return store.reconcile_stale(
                lease.lease_id,
                session_id=lease.session_id,
                task_id=lease.task_id,
                observation=observation(at=NOW + timedelta(seconds=6)),
            )
        except WorkerLeaseError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(heartbeat)
        b = pool.submit(reconcile)
        results = (a.result(), b.result())

    active = store.list_active()
    assert not (active and active[0].released_at is not None)
    assert any(
        value in {"LEASE_HEARTBEAT_EXPIRED", "LEASE_RELEASED", "LEASE_NOT_STALE"}
        or getattr(value, "kind", None) is LeaseReconciliationKind.RELEASED
        for value in results
    )


def test_legacy_aha4a_database_is_migrated_without_dropping_active_lease(tmp_path: Path) -> None:
    import sqlite3

    db = tmp_path / "legacy.sqlite"
    con = sqlite3.connect(db)
    con.executescript(
        """
        CREATE TABLE worker_leases (
            lease_id TEXT PRIMARY KEY, worker_id TEXT NOT NULL, session_id TEXT NOT NULL,
            task_id TEXT NOT NULL, project_id TEXT NOT NULL, runtime_id TEXT,
            worktree_key TEXT NOT NULL, branch TEXT NOT NULL, expected_head TEXT NOT NULL,
            required_capabilities_json TEXT NOT NULL, allowed_scope_json TEXT NOT NULL,
            forbidden_scope_json TEXT NOT NULL, mutable_scope_json TEXT NOT NULL,
            mutation_intent TEXT NOT NULL, acquired_at TEXT NOT NULL, expires_at TEXT, released_at TEXT
        );
        INSERT INTO worker_leases VALUES(
            'legacy-1','a-worker-01','session-1','task-1','project-1','runtime-1',
            'a:\repo','feat/test','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','["shell"]',
            '["src/**"]','["secrets/**"]','["src/a.py"]','MUTATION',
            '2026-08-29T14:00:00.000000Z','2026-08-29T14:01:00.000000Z',NULL
        );
        """
    )
    con.commit(); con.close()

    store = SQLiteWorkerLeaseStore(db)
    lease = store.list_active()[0]
    assert lease.lease_id == "legacy-1"
    assert lease.heartbeat_at == lease.acquired_at
    assert lease.lease_ttl_seconds == 60


def test_released_lease_rejects_heartbeat(tmp_path: Path) -> None:
    broker, store = open_broker(tmp_path)
    lease = broker.acquire(request(), (candidate(),)).lease
    assert lease is not None
    store.release(
        lease.lease_id,
        session_id=lease.session_id,
        task_id=lease.task_id,
        released_at=NOW + timedelta(seconds=1),
    )
    with pytest.raises(WorkerLeaseError, match="LEASE_RELEASED"):
        store.heartbeat(
            lease.lease_id,
            session_id=lease.session_id,
            task_id=lease.task_id,
            heartbeat_at=NOW + timedelta(seconds=2),
        )


def test_reconcile_wrong_owner_fails_closed(tmp_path: Path) -> None:
    broker, store = open_broker(tmp_path)
    lease = broker.acquire(request(ttl=5), (candidate(),)).lease
    assert lease is not None
    with pytest.raises(WorkerLeaseError, match="LEASE_OWNER_MISMATCH"):
        store.reconcile_stale(
            lease.lease_id,
            session_id="other",
            task_id=lease.task_id,
            observation=observation(at=NOW + timedelta(seconds=6)),
        )
    assert store.list_active()[0].lease_id == lease.lease_id


def test_retry_with_ttl_contract_drift_fails_closed(tmp_path: Path) -> None:
    broker, store = open_broker(tmp_path)
    assert broker.acquire(request(ttl=30), (candidate(),)).lease is not None
    with pytest.raises(WorkerLeaseError, match="LEASE_REQUEST_CONFLICT"):
        broker.acquire(request(ttl=60), (candidate(),))
    assert len(store.list_active()) == 1


def test_other_task_cannot_steal_stale_worker_and_falls_back(tmp_path: Path) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    first = WorkerLeaseBroker(store=store, lease_id_factory=lambda: "lease-1", clock=lambda: NOW)
    assert first.acquire(request(ttl=5), (candidate(),)).lease is not None
    later = WorkerLeaseBroker(
        store=store,
        lease_id_factory=lambda: "lease-2",
        clock=lambda: NOW + timedelta(seconds=6),
    )
    other = replace(
        request(session="session-2", task="task-2", ttl=5),
        allowed_scope=("tests/**",),
        mutable_scope=("tests/b.py",),
    )
    outcome = later.acquire(other, (candidate(), candidate("a-worker-02")))
    assert outcome.kind is LeaseOutcomeKind.LEASED
    assert outcome.lease is not None and outcome.lease.worker_id == "a-worker-02"
    assert len(store.list_active()) == 2


def test_quarantine_persists_across_store_reload(tmp_path: Path) -> None:
    db = tmp_path / "leases.sqlite"
    broker = WorkerLeaseBroker(
        store=SQLiteWorkerLeaseStore(db), lease_id_factory=lambda: "lease-1", clock=lambda: NOW
    )
    lease = broker.acquire(request(ttl=5), (candidate(),)).lease
    assert lease is not None
    SQLiteWorkerLeaseStore(db).reconcile_stale(
        lease.lease_id,
        session_id=lease.session_id,
        task_id=lease.task_id,
        observation=observation(at=NOW + timedelta(seconds=6), dirty_state="UNKNOWN"),
    )
    reloaded = SQLiteWorkerLeaseStore(db).list_active()[0]
    assert reloaded.quarantine_code == "WORKTREE_DIRTY_UNKNOWN"
    assert reloaded.recovery_evidence_ref == "recovery:e1"


def test_quarantine_can_release_after_newer_safe_reconciliation(tmp_path: Path) -> None:
    broker, store = open_broker(tmp_path)
    lease = broker.acquire(request(ttl=5), (candidate(),)).lease
    assert lease is not None
    first = store.reconcile_stale(
        lease.lease_id,
        session_id=lease.session_id,
        task_id=lease.task_id,
        observation=observation(at=NOW + timedelta(seconds=6), dirty_state="UNKNOWN", evidence="recovery:q"),
    )
    assert first.kind is LeaseReconciliationKind.QUARANTINED
    second = store.reconcile_stale(
        lease.lease_id,
        session_id=lease.session_id,
        task_id=lease.task_id,
        observation=observation(at=NOW + timedelta(seconds=7), evidence="recovery:safe"),
    )
    assert second.kind is LeaseReconciliationKind.RELEASED
    assert second.lease.recovery_evidence_ref == "recovery:safe"


def test_reconciliation_observation_older_than_latest_heartbeat_is_rejected(tmp_path: Path) -> None:
    broker, store = open_broker(tmp_path)
    lease = broker.acquire(request(ttl=10), (candidate(),)).lease
    assert lease is not None
    store.heartbeat(
        lease.lease_id,
        session_id=lease.session_id,
        task_id=lease.task_id,
        heartbeat_at=NOW + timedelta(seconds=8),
    )
    with pytest.raises(WorkerLeaseError, match="LEASE_OBSERVATION_STALE"):
        store.reconcile_stale(
            lease.lease_id,
            session_id=lease.session_id,
            task_id=lease.task_id,
            observation=observation(at=NOW + timedelta(seconds=6)),
        )


def test_old_safe_observation_cannot_release_newer_quarantine(tmp_path: Path) -> None:
    broker, store = open_broker(tmp_path)
    lease = broker.acquire(request(ttl=5), (candidate(),)).lease
    assert lease is not None
    store.reconcile_stale(
        lease.lease_id,
        session_id=lease.session_id,
        task_id=lease.task_id,
        observation=observation(at=NOW + timedelta(seconds=8), dirty_state="UNKNOWN", evidence="recovery:new"),
    )
    with pytest.raises(WorkerLeaseError, match="LEASE_OBSERVATION_STALE"):
        store.reconcile_stale(
            lease.lease_id,
            session_id=lease.session_id,
            task_id=lease.task_id,
            observation=observation(at=NOW + timedelta(seconds=7), evidence="recovery:old-safe"),
        )
    assert store.list_active()[0].quarantine_code == "WORKTREE_DIRTY_UNKNOWN"


def test_direct_release_of_expired_lease_requires_reconciliation(tmp_path: Path) -> None:
    broker, store = open_broker(tmp_path)
    lease = broker.acquire(request(ttl=5), (candidate(),)).lease
    assert lease is not None
    with pytest.raises(WorkerLeaseError, match="LEASE_RECOVERY_REQUIRED"):
        store.release(
            lease.lease_id,
            session_id=lease.session_id,
            task_id=lease.task_id,
            released_at=NOW + timedelta(seconds=6),
        )
    assert store.list_active()[0].lease_id == lease.lease_id


def test_direct_release_of_quarantined_lease_requires_reconciliation(tmp_path: Path) -> None:
    broker, store = open_broker(tmp_path)
    lease = broker.acquire(request(ttl=5), (candidate(),)).lease
    assert lease is not None
    store.reconcile_stale(
        lease.lease_id,
        session_id=lease.session_id,
        task_id=lease.task_id,
        observation=observation(at=NOW + timedelta(seconds=6), dirty_state="UNKNOWN"),
    )
    with pytest.raises(WorkerLeaseError, match="LEASE_RECOVERY_REQUIRED"):
        store.release(
            lease.lease_id,
            session_id=lease.session_id,
            task_id=lease.task_id,
            released_at=NOW + timedelta(seconds=7),
        )


def test_release_timestamp_older_than_latest_heartbeat_fails_closed(tmp_path: Path) -> None:
    broker, store = open_broker(tmp_path)
    lease = broker.acquire(request(ttl=30), (candidate(),)).lease
    assert lease is not None
    store.heartbeat(
        lease.lease_id,
        session_id=lease.session_id,
        task_id=lease.task_id,
        heartbeat_at=NOW + timedelta(seconds=10),
    )
    with pytest.raises(WorkerLeaseError, match="LEASE_RELEASE_STALE"):
        store.release(
            lease.lease_id,
            session_id=lease.session_id,
            task_id=lease.task_id,
            released_at=NOW + timedelta(seconds=9),
        )
