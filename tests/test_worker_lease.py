from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Barrier

import pytest

from a_conductor.worker_lease import (
    CandidateRejectionKind,
    LeaseMutationIntent,
    LeaseOutcomeKind,
    SQLiteWorkerLeaseStore,
    WorkerLeaseBroker,
    WorkerLeaseCandidate,
    WorkerLeaseError,
    WorkerLeaseRequest,
)

NOW = datetime(2026, 8, 28, 15, 45, tzinfo=timezone.utc)


def candidate(worker_id: str, *, worktree: str = r"A:\Repo", **changes) -> WorkerLeaseCandidate:
    values = dict(
        worker_id=worker_id, state="READY", reserved=False, active_task=False,
        capabilities=("shell", "repo"), runtime_id="runtime-1", project_id="project-1",
        worktree=worktree, branch="feat/test", head="a" * 40, health_fresh=True,
        ownership_known=True, dirty_state="CLEAN", mutation_authorized=True,
        occupied_mutable_scopes=(),
    )
    values.update(changes)
    return WorkerLeaseCandidate(**values)

def request(*, ordered=("a-worker-01",), mutation=True, rdc=False, session="session-1", task="task-1", mutable_scope=("src/a.py",)) -> WorkerLeaseRequest:
    return WorkerLeaseRequest(
        session_id=session, task_id=task, project_id="project-1",
        ordered_worker_ids=tuple(ordered), required_capabilities=("shell",),
        required_runtime_id="runtime-1", worktree=r"A:\Repo", branch="feat/test",
        expected_head="a" * 40,
        mutation_intent=(LeaseMutationIntent.MUTATION if mutation else LeaseMutationIntent.READ_ONLY),
        allowed_scope=(tuple(mutable_scope) if mutation else ("src/a.py",)), forbidden_scope=("secrets/**",),
        mutable_scope=(tuple(mutable_scope) if mutation else ()), rdc_fallback_eligible=rdc,
    )


def broker(tmp_path: Path, *, ids=None) -> tuple[WorkerLeaseBroker, SQLiteWorkerLeaseStore]:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    counter = iter(ids or (f"lease-{i}" for i in range(1, 100)))
    return WorkerLeaseBroker(store=store, lease_id_factory=lambda: next(counter), clock=lambda: NOW), store


def test_two_independent_stores_racing_one_worker_produce_one_winner(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    first = SQLiteWorkerLeaseStore(database)
    second = SQLiteWorkerLeaseStore(database)
    barrier = Barrier(2)

    def acquire(store, req, lease_id):
        barrier.wait()
        return store.try_acquire(req, candidate("a-worker-01"), lease_id=lease_id, acquired_at=NOW)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(
            lambda args: acquire(*args),
            ((first, request(session="s1", task="t1"), "lease-1"),
             (second, request(session="s2", task="t2"), "lease-2")),
        ))

    winners = [item for item in results if item is not None]
    assert len(winners) == 1
    assert winners[0].worker_id == "a-worker-01"
    assert len(first.list_active()) == 1

def test_busy_first_candidate_falls_back_to_second_in_order(tmp_path: Path) -> None:
    service, store = broker(tmp_path, ids=iter(("lease-existing", "lease-new")))
    occupied = request(session="busy", task="busy", mutable_scope=("docs/**",))
    store.try_acquire(occupied, candidate("a-worker-01"), lease_id="lease-existing", acquired_at=NOW)

    outcome = service.acquire(
        request(ordered=("a-worker-01", "a-worker-02")),
        (candidate("a-worker-01"), candidate("a-worker-02")),
    )

    assert outcome.kind is LeaseOutcomeKind.LEASED
    assert outcome.lease is not None
    assert outcome.lease.worker_id == "a-worker-02"
    assert [(item.worker_id, item.kind) for item in outcome.rejections] == [
        ("a-worker-01", CandidateRejectionKind.LEASE_BUSY)
    ]


def test_equivalent_candidates_follow_caller_order_not_worker_id_sort(tmp_path: Path) -> None:
    service, _ = broker(tmp_path)
    outcome = service.acquire(
        request(ordered=("a-worker-09", "a-worker-01")),
        (candidate("a-worker-01"), candidate("a-worker-09")),
    )
    assert outcome.lease is not None
    assert outcome.lease.worker_id == "a-worker-09"


@pytest.mark.parametrize(
    ("changes", "kind"),
    [
        ({"active_task": True}, CandidateRejectionKind.ACTIVE_TASK),
        ({"state": "BUSY"}, CandidateRejectionKind.WORKER_NOT_READY),
        ({"reserved": True}, CandidateRejectionKind.WORKER_RESERVED),
        ({"capabilities": ("repo",)}, CandidateRejectionKind.CAPABILITY_MISMATCH),
        ({"runtime_id": "runtime-2"}, CandidateRejectionKind.RUNTIME_MISMATCH),
        ({"project_id": "project-2"}, CandidateRejectionKind.PROJECT_MISMATCH),
        ({"worktree": r"A:\Other"}, CandidateRejectionKind.WORKTREE_MISMATCH),
    ],
)
def test_preflight_skips_ineligible_candidate_with_typed_reason(tmp_path: Path, changes, kind) -> None:
    service, _ = broker(tmp_path)
    outcome = service.acquire(request(), (candidate("a-worker-01", **changes),))
    assert outcome.kind is LeaseOutcomeKind.WAIT
    assert outcome.rejections[0].kind is kind

@pytest.mark.parametrize(
    ("changes", "kind"),
    [
        ({"branch": "other"}, CandidateRejectionKind.BRANCH_MISMATCH),
        ({"head": "b" * 40}, CandidateRejectionKind.HEAD_MISMATCH),
        ({"health_fresh": False}, CandidateRejectionKind.HEALTH_STALE),
        ({"ownership_known": False}, CandidateRejectionKind.OWNERSHIP_UNKNOWN),
        ({"dirty_state": "UNKNOWN"}, CandidateRejectionKind.DIRTY_UNKNOWN),
        ({"dirty_state": "DIRTY"}, CandidateRejectionKind.DIRTY_WORKTREE),
        ({"mutation_authorized": False}, CandidateRejectionKind.MUTATION_UNAUTHORIZED),
        ({"occupied_mutable_scopes": (("src/a.py",),)}, CandidateRejectionKind.MUTABLE_SCOPE_OVERLAP),
    ],
)
def test_mutating_request_fails_closed_on_identity_health_or_scope(tmp_path: Path, changes, kind) -> None:
    service, _ = broker(tmp_path)
    outcome = service.acquire(request(mutation=True), (candidate("a-worker-01", **changes),))
    assert outcome.kind is LeaseOutcomeKind.WAIT
    assert outcome.rejections[0].kind is kind


def test_known_dirty_worker_can_serve_read_only_but_unknown_dirty_cannot(tmp_path: Path) -> None:
    service, _ = broker(tmp_path)
    dirty = service.acquire(request(mutation=False), (candidate("a-worker-01", dirty_state="DIRTY"),))
    assert dirty.kind is LeaseOutcomeKind.LEASED

    other, _ = broker(tmp_path / "other")
    unknown = other.acquire(request(mutation=False), (candidate("a-worker-01", dirty_state="UNKNOWN"),))
    assert unknown.kind is LeaseOutcomeKind.WAIT
    assert unknown.rejections[0].kind is CandidateRejectionKind.DIRTY_UNKNOWN


def test_read_only_can_explicitly_fall_back_to_rdc_but_mutation_never_does(tmp_path: Path) -> None:
    readonly, _ = broker(tmp_path / "ro")
    ro = readonly.acquire(request(mutation=False, rdc=True), ())
    assert ro.kind is LeaseOutcomeKind.RDC_READ_ONLY

    mutating, _ = broker(tmp_path / "mut")
    mut = mutating.acquire(request(mutation=True, rdc=True), ())
    assert mut.kind is LeaseOutcomeKind.WAIT

def test_release_requires_exact_owner_and_is_idempotent_for_same_lease(tmp_path: Path) -> None:
    service, store = broker(tmp_path, ids=iter(("lease-1",)))
    outcome = service.acquire(request(), (candidate("a-worker-01"),))
    assert outcome.lease is not None

    with pytest.raises(WorkerLeaseError, match="LEASE_OWNER_MISMATCH"):
        store.release("lease-1", session_id="other", task_id="task-1", released_at=NOW)

    first = store.release("lease-1", session_id="session-1", task_id="task-1", released_at=NOW)
    second = store.release("lease-1", session_id="session-1", task_id="task-1", released_at=NOW)
    assert first.released is True
    assert first.already_released is False
    assert second.released is False
    assert second.already_released is True
    assert store.list_active() == ()


def test_active_lease_persists_across_store_reopen_and_keeps_identity(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    first = SQLiteWorkerLeaseStore(database)
    lease = first.try_acquire(request(), candidate("a-worker-01"), lease_id="lease-1", acquired_at=NOW)
    assert lease is not None

    second = SQLiteWorkerLeaseStore(database)
    restored = second.list_active()
    assert len(restored) == 1
    assert restored[0].lease_id == "lease-1"
    assert restored[0].session_id == "session-1"
    assert restored[0].task_id == "task-1"
    assert restored[0].project_id == "project-1"
    assert restored[0].worktree_key.endswith(r"repo")
    assert restored[0].branch == "feat/test"
    assert restored[0].expected_head == "a" * 40
    assert restored[0].allowed_scope == ("src/a.py",)
    assert restored[0].forbidden_scope == ("secrets/**",)
    assert restored[0].mutation_intent is LeaseMutationIntent.MUTATION


def test_expiry_metadata_never_causes_aha4a_to_reclaim_active_lease(tmp_path: Path) -> None:
    service, store = broker(tmp_path)
    req = request()
    store.try_acquire(req, candidate("a-worker-01"), lease_id="lease-old", acquired_at=NOW, expires_at="2026-08-28T15:00:00Z")
    owner_retry = service.acquire(req, (candidate("a-worker-01"),))
    assert owner_retry.kind is LeaseOutcomeKind.RECOVERY_REQUIRED
    assert owner_retry.lease is not None and owner_retry.lease.lease_id == "lease-old"

    other = service.acquire(
        request(session="other", task="other"),
        (candidate("a-worker-01"),),
    )
    assert other.kind is LeaseOutcomeKind.WAIT
    assert other.rejections[0].kind is CandidateRejectionKind.LEASE_BUSY
    assert store.list_active()[0].lease_id == "lease-old"


def test_two_workers_cannot_atomically_lease_overlapping_mutable_scope(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    first = SQLiteWorkerLeaseStore(database)
    second = SQLiteWorkerLeaseStore(database)
    barrier = Barrier(2)
    one = request(ordered=("a-worker-01",), session="s1", task="t1", mutable_scope=("src/**",))
    two = request(ordered=("a-worker-02",), session="s2", task="t2", mutable_scope=("src/a.py",))

    def acquire(store, req, worker_id, lease_id):
        barrier.wait()
        try:
            return store.try_acquire(req, candidate(worker_id), lease_id=lease_id, acquired_at=NOW)
        except WorkerLeaseError as exc:
            return exc.args[0]

    with ThreadPoolExecutor(max_workers=2) as pool:
        left = pool.submit(acquire, first, one, "a-worker-01", "lease-1")
        right = pool.submit(acquire, second, two, "a-worker-02", "lease-2")
        results = (left.result(), right.result())

    leases = [item for item in results if not isinstance(item, str) and item is not None]
    errors = [item for item in results if isinstance(item, str)]
    assert len(leases) == 1
    assert errors == ["MUTABLE_SCOPE_OVERLAP"]
    assert len(first.list_active()) == 1



def test_store_scope_conflict_is_typed_and_broker_does_not_bypass_it(tmp_path: Path) -> None:
    service, store = broker(tmp_path)
    active_request = request(ordered=("a-worker-09",), session="active", task="active", mutable_scope=("src/**",))
    store.try_acquire(
        active_request, candidate("a-worker-09"), lease_id="lease-active", acquired_at=NOW
    )

    outcome = service.acquire(
        request(ordered=("a-worker-01", "a-worker-02"), mutable_scope=("src/a.py",)),
        (candidate("a-worker-01"), candidate("a-worker-02")),
    )

    assert outcome.kind is LeaseOutcomeKind.WAIT
    assert [item.kind for item in outcome.rejections] == [
        CandidateRejectionKind.MUTABLE_SCOPE_OVERLAP,
        CandidateRejectionKind.MUTABLE_SCOPE_OVERLAP,
    ]
    assert len(store.list_active()) == 1


def test_non_overlapping_mutation_scopes_can_lease_different_workers(tmp_path: Path) -> None:
    service, store = broker(tmp_path)
    first = request(ordered=("a-worker-01",), session="s1", task="t1", mutable_scope=("src/a.py",))
    assert service.acquire(first, (candidate("a-worker-01"),)).kind is LeaseOutcomeKind.LEASED

    second = request(ordered=("a-worker-02",), session="s2", task="t2", mutable_scope=("tests/**",))
    outcome = service.acquire(second, (candidate("a-worker-02"),))
    assert outcome.kind is LeaseOutcomeKind.LEASED
    assert len(store.list_active()) == 2


def test_two_independent_brokers_racing_same_worker_have_one_lease_winner(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    first = WorkerLeaseBroker(
        store=SQLiteWorkerLeaseStore(database), lease_id_factory=lambda: "lease-1", clock=lambda: NOW
    )
    second = WorkerLeaseBroker(
        store=SQLiteWorkerLeaseStore(database), lease_id_factory=lambda: "lease-2", clock=lambda: NOW
    )
    barrier = Barrier(2)

    def run(service, req):
        barrier.wait()
        return service.acquire(req, (candidate("a-worker-01"),))

    with ThreadPoolExecutor(max_workers=2) as pool:
        left = pool.submit(run, first, request(session="s1", task="t1"))
        right = pool.submit(run, second, request(session="s2", task="t2"))
        outcomes = (left.result(), right.result())

    assert sum(item.kind is LeaseOutcomeKind.LEASED for item in outcomes) == 1
    assert sum(item.kind is LeaseOutcomeKind.WAIT for item in outcomes) == 1
    losing = next(item for item in outcomes if item.kind is LeaseOutcomeKind.WAIT)
    assert losing.rejections[-1].kind is CandidateRejectionKind.LEASE_BUSY


def test_missing_ordered_candidate_is_typed_and_next_candidate_can_win(tmp_path: Path) -> None:
    service, _ = broker(tmp_path)
    outcome = service.acquire(
        request(ordered=("a-worker-missing", "a-worker-02")),
        (candidate("a-worker-02"),),
    )
    assert outcome.kind is LeaseOutcomeKind.LEASED
    assert outcome.lease is not None and outcome.lease.worker_id == "a-worker-02"
    assert outcome.rejections[0].kind is CandidateRejectionKind.CANDIDATE_MISSING


def test_windows_worktree_identity_is_case_and_separator_insensitive(tmp_path: Path) -> None:
    service, _ = broker(tmp_path)
    outcome = service.acquire(request(), (candidate("a-worker-01", worktree="a:/repo/."),))
    assert outcome.kind is LeaseOutcomeKind.LEASED


def test_mutation_scope_cannot_escape_allowed_scope() -> None:
    with pytest.raises(ValueError, match="mutable_scope escapes allowed_scope"):
        WorkerLeaseRequest(
            session_id="session-1", task_id="task-1", project_id="project-1",
            ordered_worker_ids=("a-worker-01",), required_capabilities=("shell",),
            required_runtime_id="runtime-1", worktree=r"A:\Repo", branch="feat/test",
            expected_head="a" * 40, mutation_intent=LeaseMutationIntent.MUTATION,
            allowed_scope=("src/a.py",), forbidden_scope=("secrets/**",),
            mutable_scope=("src/**",),
        )


def test_literal_mutation_path_can_be_covered_by_allowed_glob() -> None:
    req = request(mutable_scope=("src/a.py",))
    widened = WorkerLeaseRequest(
        session_id=req.session_id, task_id=req.task_id, project_id=req.project_id,
        ordered_worker_ids=req.ordered_worker_ids, required_capabilities=req.required_capabilities,
        required_runtime_id=req.required_runtime_id, worktree=req.worktree, branch=req.branch,
        expected_head=req.expected_head, mutation_intent=req.mutation_intent,
        allowed_scope=("src/**",), forbidden_scope=req.forbidden_scope,
        mutable_scope=req.mutable_scope,
    )
    assert widened.mutable_scope == ("src/a.py",)


def test_retry_same_owner_task_reuses_existing_lease_without_fallback(tmp_path: Path) -> None:
    service, store = broker(tmp_path, ids=iter(("lease-1", "lease-2")))
    req = request(ordered=("a-worker-01", "a-worker-02"))
    first = service.acquire(req, (candidate("a-worker-01"), candidate("a-worker-02")))
    assert first.lease is not None and first.lease.worker_id == "a-worker-01"

    retried = service.acquire(
        req,
        (candidate("a-worker-01", active_task=True), candidate("a-worker-02")),
    )

    assert retried.kind is LeaseOutcomeKind.EXISTING
    assert retried.lease is not None and retried.lease.lease_id == first.lease.lease_id
    assert retried.lease.worker_id == "a-worker-01"
    assert len(store.list_active()) == 1


def test_same_owner_task_with_drifted_contract_fails_closed(tmp_path: Path) -> None:
    service, store = broker(tmp_path, ids=iter(("lease-1", "lease-2")))
    original = request(ordered=("a-worker-01", "a-worker-02"))
    assert service.acquire(original, (candidate("a-worker-01"), candidate("a-worker-02"))).lease
    drifted = WorkerLeaseRequest(
        session_id=original.session_id, task_id=original.task_id, project_id=original.project_id,
        ordered_worker_ids=original.ordered_worker_ids, required_capabilities=original.required_capabilities,
        required_runtime_id=original.required_runtime_id, worktree=original.worktree, branch="feat/drifted",
        expected_head=original.expected_head, mutation_intent=original.mutation_intent,
        allowed_scope=original.allowed_scope, forbidden_scope=original.forbidden_scope,
        mutable_scope=original.mutable_scope,
    )
    with pytest.raises(WorkerLeaseError, match="LEASE_REQUEST_CONFLICT"):
        service.acquire(drifted, (candidate("a-worker-01"), candidate("a-worker-02", branch="feat/drifted")))
    assert len(store.list_active()) == 1


def test_concurrent_same_owner_task_converges_on_one_lease(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    first = WorkerLeaseBroker(
        store=SQLiteWorkerLeaseStore(database), lease_id_factory=lambda: "lease-1", clock=lambda: NOW
    )
    second = WorkerLeaseBroker(
        store=SQLiteWorkerLeaseStore(database), lease_id_factory=lambda: "lease-2", clock=lambda: NOW
    )
    req = request(ordered=("a-worker-01", "a-worker-02"))
    candidates = (candidate("a-worker-01"), candidate("a-worker-02"))
    barrier = Barrier(2)

    def run(service):
        barrier.wait()
        return service.acquire(req, candidates)

    with ThreadPoolExecutor(max_workers=2) as pool:
        left = pool.submit(run, first)
        right = pool.submit(run, second)
        outcomes = (left.result(), right.result())

    assert sorted(item.kind.value for item in outcomes) == ["EXISTING", "LEASED"]
    assert outcomes[0].lease is not None and outcomes[1].lease is not None
    assert outcomes[0].lease.lease_id == outcomes[1].lease.lease_id
    assert len(SQLiteWorkerLeaseStore(database).list_active()) == 1


def test_same_owner_task_with_capability_contract_drift_fails_closed(tmp_path: Path) -> None:
    service, store = broker(tmp_path, ids=iter(("lease-1",)))
    original = request()
    assert service.acquire(original, (candidate("a-worker-01"),)).lease
    drifted = WorkerLeaseRequest(
        session_id=original.session_id, task_id=original.task_id, project_id=original.project_id,
        ordered_worker_ids=original.ordered_worker_ids,
        required_capabilities=("shell", "new-capability"),
        required_runtime_id=original.required_runtime_id, worktree=original.worktree,
        branch=original.branch, expected_head=original.expected_head,
        mutation_intent=original.mutation_intent, allowed_scope=original.allowed_scope,
        forbidden_scope=original.forbidden_scope, mutable_scope=original.mutable_scope,
    )
    with pytest.raises(WorkerLeaseError, match="LEASE_REQUEST_CONFLICT"):
        service.acquire(drifted, (candidate("a-worker-01"),))
    assert len(store.list_active()) == 1


def test_concurrent_same_owner_with_reused_proposed_id_still_marks_existing(tmp_path: Path) -> None:
    database = tmp_path / "leases.sqlite"
    first = WorkerLeaseBroker(
        store=SQLiteWorkerLeaseStore(database), lease_id_factory=lambda: "lease-same", clock=lambda: NOW
    )
    second = WorkerLeaseBroker(
        store=SQLiteWorkerLeaseStore(database), lease_id_factory=lambda: "lease-same", clock=lambda: NOW
    )
    req = request(ordered=("a-worker-01", "a-worker-02"))
    candidates = (candidate("a-worker-01"), candidate("a-worker-02"))
    barrier = Barrier(2)

    def run(service):
        barrier.wait()
        return service.acquire(req, candidates)

    with ThreadPoolExecutor(max_workers=2) as pool:
        left = pool.submit(run, first)
        right = pool.submit(run, second)
        outcomes = (left.result(), right.result())

    assert sorted(item.kind.value for item in outcomes) == ["EXISTING", "LEASED"]
    assert outcomes[0].lease is not None and outcomes[1].lease is not None
    assert outcomes[0].lease.lease_id == outcomes[1].lease.lease_id == "lease-same"
    assert len(SQLiteWorkerLeaseStore(database).list_active()) == 1
