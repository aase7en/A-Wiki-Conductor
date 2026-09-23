"""WO-P1-498 / 498A — lease-bound PRE_DISPATCH GUARD (RED-first matrix).

Deterministic proofs that the consequential FRESH supervised launch is
revalidated at launch time against the SAME configured lease authority:
ACTIVE health + exact authority-bearing binding (worker/session/task/
project/worktree/branch/HEAD/intent/scope) or the launch fails closed
BEFORE author-attempt mint, execution-id/record creation, or backend
launch. ATTACH_RUNNING / REUSE_COMPLETED remain dedupe-owned and never
invoke the fresh-launch guard. Guard output is untrusted: exceptions and
malformed results collapse to stable typed codes. Fingerprints and dedupe
semantics are untouched. No new store/scheduler/lease authority exists.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from a_conductor.execution_store import SQLiteExecutionStore
from a_conductor.pre_dispatch_guard import (
    PreDispatchGuardDecision,
    PreDispatchGuardDecisionKind,
    WorkerLeasePreDispatchGuard,
)
from a_conductor.supervised_run_coordinator import SupervisedRunCoordinator
from a_conductor.worker_lease import (
    LeaseHealth,
    LeaseHealthKind,
    LeaseMutationIntent,
    WorkerLease,
)

from tests.test_supervised_run_coordinator import (
    ARGV,
    ScriptedSupervised,
    _identity,
)

_REASON_RE = re.compile(r"[A-Z0-9_]{3,64}")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _lease(**overrides) -> WorkerLease:
    fields = dict(
        lease_id="lease-498a-0001",
        worker_id="a-worker-01",
        session_id="sess-498a",
        task_id="WO-P1-498-GUARD498A",
        project_id="zcode",
        runtime_id=None,
        worktree_key=r"a:\repo\wt-498a",
        branch="docs/wo-p1-498-guard-shaping",
        expected_head="3" * 40,
        required_capabilities=("code",),
        allowed_scope=("src/a_conductor", "src/a_conductor/*"),
        forbidden_scope=("secrets", "secrets/*"),
        mutable_scope=("src/a_conductor/*",),
        mutation_intent=LeaseMutationIntent.MUTATION,
        acquired_at=_now().isoformat(),
        heartbeat_at=_now().isoformat(),
        lease_ttl_seconds=600,
        expires_at=(_now() + timedelta(minutes=10)).isoformat(),
    )
    fields.update(overrides)
    return WorkerLease(**fields)


_REQUESTED = ("src/a_conductor/zcode_runner.py",)


class FakeHealthReader:
    """Deterministic injected lease-health authority (records every read)."""

    def __init__(self, health=None, error: Exception | None = None):
        self.health = health
        self.error = error
        self.calls: list[str] = []

    def inspect_health(self, lease_id: str, *, now: object) -> LeaseHealth:
        self.calls.append(lease_id)
        if self.error is not None:
            raise self.error
        if callable(self.health):
            return self.health(lease_id, now=now)
        return self.health


def _guard(
    baseline: WorkerLease | None = None,
    reader: FakeHealthReader | None = None,
    requested: tuple[str, ...] = _REQUESTED,
) -> tuple[WorkerLeasePreDispatchGuard, FakeHealthReader]:
    baseline = baseline or _lease()
    reader = reader or FakeHealthReader(
        LeaseHealth(LeaseHealthKind.ACTIVE, baseline)
    )
    guard = WorkerLeasePreDispatchGuard(
        health_reader=reader,
        baseline_lease=baseline,
        requested_mutable_scope=requested,
    )
    return guard, reader


# ---------------- guard unit matrix ----------------


def test_exact_active_lease_passes():
    guard, reader = _guard()
    decision = guard.check()
    assert isinstance(decision, PreDispatchGuardDecision)
    assert decision.kind is PreDispatchGuardDecisionKind.ALLOW
    assert reader.calls == ["lease-498a-0001"]


def test_non_active_health_kinds_deny_with_stable_reasons():
    for kind, reason in (
        (LeaseHealthKind.STALE, "LEASE_STALE"),
        (LeaseHealthKind.QUARANTINED, "LEASE_QUARANTINED"),
        (LeaseHealthKind.RELEASED, "LEASE_RELEASED"),
        (LeaseHealthKind.EXPIRY_UNKNOWN, "LEASE_EXPIRY_UNKNOWN"),
    ):
        baseline = _lease()
        observed = LeaseHealth(kind, baseline)
        guard, _ = _guard(baseline, FakeHealthReader(observed))
        decision = guard.check()
        assert decision.kind is PreDispatchGuardDecisionKind.DENY, kind
        assert decision.reason_code == reason, kind


def test_health_reader_exception_denies_unavailable():
    guard, _ = _guard(reader=FakeHealthReader(error=RuntimeError("store down")))
    decision = guard.check()
    assert decision.kind is PreDispatchGuardDecisionKind.DENY
    assert decision.reason_code == "LEASE_HEALTH_UNAVAILABLE"


def test_malformed_health_denies_invalid():
    for junk in (None, "ACTIVE", object(), 42):
        baseline = _lease()
        guard, _ = _guard(baseline, FakeHealthReader(junk))
        decision = guard.check()
        assert decision.kind is PreDispatchGuardDecisionKind.DENY, junk
        assert decision.reason_code == "LEASE_HEALTH_INVALID", junk


def test_authority_identity_drift_denies():
    drift = {
        "LEASE_WORKER_MISMATCH": {"worker_id": "a-worker-99"},
        "LEASE_SESSION_MISMATCH": {"session_id": "sess-other"},
        "LEASE_TASK_MISMATCH": {"task_id": "WO-P1-999-OTHER"},
        "LEASE_PROJECT_MISMATCH": {"project_id": "other-project"},
        "LEASE_WORKTREE_MISMATCH": {"worktree_key": r"a:\repo\other-wt"},
        "LEASE_BRANCH_MISMATCH": {"branch": "other/branch"},
        "LEASE_HEAD_MISMATCH": {"expected_head": "f" * 40},
    }
    for reason, overrides in drift.items():
        baseline = _lease()
        observed = _lease(**overrides)
        guard, _ = _guard(baseline, FakeHealthReader(LeaseHealth(LeaseHealthKind.ACTIVE, observed)))
        decision = guard.check()
        assert decision.kind is PreDispatchGuardDecisionKind.DENY, reason
        assert decision.reason_code == reason, reason


def test_mutation_intent_drift_denies():
    baseline = _lease()
    observed = _lease(mutation_intent=LeaseMutationIntent.READ_ONLY)
    guard, _ = _guard(baseline, FakeHealthReader(LeaseHealth(LeaseHealthKind.ACTIVE, observed)))
    decision = guard.check()
    assert decision.kind is PreDispatchGuardDecisionKind.DENY
    assert decision.reason_code == "LEASE_INTENT_MISMATCH"


def test_baseline_scope_drift_denies():
    drift = {
        "LEASE_ALLOWED_SCOPE_MISMATCH": {"allowed_scope": ("src/a_conductor", "src/a_conductor/*", "docs/*")},
        "LEASE_FORBIDDEN_SCOPE_MISMATCH": {"forbidden_scope": ("secrets",)},
        "LEASE_MUTABLE_SCOPE_MISMATCH": {"mutable_scope": ("src/a_conductor/*", "tests/*")},
    }
    for reason, overrides in drift.items():
        baseline = _lease()
        observed = _lease(**overrides)
        guard, _ = _guard(baseline, FakeHealthReader(LeaseHealth(LeaseHealthKind.ACTIVE, observed)))
        decision = guard.check()
        assert decision.kind is PreDispatchGuardDecisionKind.DENY, reason
        assert decision.reason_code == reason, reason


def test_requested_scope_drift_denies():
    # The observed lease stays IDENTICAL to the accepted baseline; only the
    # declared requested mutable scope drifts past what assembly validated.
    baseline = _lease()
    cases = (
        # requested outside the lease allowed scope entirely
        (("docs/README.md",), "REQUESTED_SCOPE_NOT_AUTHORIZED"),
        # requested inside allowed but outside the mutable write set
        (("src/a_conductor",), "REQUESTED_SCOPE_OUTSIDE_MUTABLE"),
    )
    for requested, reason in cases:
        guard, _ = _guard(
            baseline,
            FakeHealthReader(LeaseHealth(LeaseHealthKind.ACTIVE, baseline)),
            requested=requested,
        )
        decision = guard.check()
        assert decision.kind is PreDispatchGuardDecisionKind.DENY, reason
        assert decision.reason_code == reason, reason

    # requested within allowed+mutable but overlapping the forbidden scope
    overlap_baseline = _lease(
        allowed_scope=("src", "src/*"),
        forbidden_scope=("src/never/*",),
        mutable_scope=("src/*",),
    )
    guard, _ = _guard(
        overlap_baseline,
        FakeHealthReader(LeaseHealth(LeaseHealthKind.ACTIVE, overlap_baseline)),
        requested=("src/never/file.py",),
    )
    decision = guard.check()
    assert decision.kind is PreDispatchGuardDecisionKind.DENY
    assert decision.reason_code == "REQUESTED_SCOPE_FORBIDDEN"


def test_heartbeat_only_advancement_remains_allowed():
    baseline = _lease(heartbeat_at=_now().isoformat(), expires_at=(_now() + timedelta(seconds=60)).isoformat())
    observed = _lease(
        heartbeat_at=(_now() + timedelta(seconds=30)).isoformat(),
        expires_at=(_now() + timedelta(minutes=10)).isoformat(),
    )
    guard, _ = _guard(baseline, FakeHealthReader(LeaseHealth(LeaseHealthKind.ACTIVE, observed)))
    decision = guard.check()
    assert decision.kind is PreDispatchGuardDecisionKind.ALLOW


def test_every_reason_code_is_bounded_and_safe():
    baseline = _lease()
    reasons: set[str] = set()
    for kind in (
        LeaseHealthKind.STALE,
        LeaseHealthKind.QUARANTINED,
        LeaseHealthKind.RELEASED,
        LeaseHealthKind.EXPIRY_UNKNOWN,
    ):
        guard, _ = _guard(baseline, FakeHealthReader(LeaseHealth(kind, baseline)))
        reasons.add(guard.check().reason_code)
    guard, _ = _guard(baseline, FakeHealthReader(error=RuntimeError("x")))
    reasons.add(guard.check().reason_code)
    guard, _ = _guard(baseline, FakeHealthReader("junk"))
    reasons.add(guard.check().reason_code)
    for reason in reasons:
        assert _REASON_RE.fullmatch(reason), reason


def test_constructor_fails_closed_on_invalid_authorities():
    baseline = _lease()
    with pytest.raises(ValueError):
        WorkerLeasePreDispatchGuard(
            health_reader=object(),  # no inspect_health
            baseline_lease=baseline,
            requested_mutable_scope=_REQUESTED,
        )
    with pytest.raises(ValueError):
        WorkerLeasePreDispatchGuard(
            health_reader=FakeHealthReader(),
            baseline_lease=object(),  # not a WorkerLease
            requested_mutable_scope=_REQUESTED,
        )


def test_guard_module_derives_no_own_store_or_lease_path():
    """The health reader is injected from the SAME configured lease
    authority; the guard never opens its own SQLite path or store."""
    source = (Path(__file__).parent.parent / "src" / "a_conductor" / "pre_dispatch_guard.py").read_text(
        encoding="utf-8"
    )
    assert "sqlite3" not in source
    assert "SQLiteWorkerLeaseStore(" not in source
    assert "try_acquire" not in source
    assert "def release" not in source


# ---------------- coordinator integration matrix ----------------


class CountingGuard:
    """Injected guard double; records calls and replays a scripted decision."""

    _DEFAULT = object()

    def __init__(self, decision=_DEFAULT, error: Exception | None = None):
        self.calls = 0
        self.decision = (
            PreDispatchGuardDecision(PreDispatchGuardDecisionKind.ALLOW, "PRE_DISPATCH_ALLOWED")
            if decision is CountingGuard._DEFAULT
            else decision
        )
        self.error = error

    def check(self) -> PreDispatchGuardDecision:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.decision


def _harness(tmp_path: Path, *, guard=None, required: bool = False):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    supervised = ScriptedSupervised(repo, store)
    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=supervised,
        identity=_identity(repo),
        pre_dispatch_guard=guard,
        pre_dispatch_guard_required=required,
        poll_interval_seconds=0.01,
    )
    return repo, store, supervised, coordinator


def test_fresh_required_guard_allow_launches_exactly_once(tmp_path):
    guard = CountingGuard()
    _, store, supervised, coordinator = _harness(tmp_path, guard=guard, required=True)
    outcome = coordinator.run_with_outcome(ARGV, timeout_seconds=30)
    assert outcome.kind.value == "FRESH"
    assert outcome.native.exit_code == 0
    assert guard.calls == 1
    assert supervised.launch_calls == 1
    records = store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV))
    assert len(records) == 1  # exactly one record


def test_required_guard_missing_fails_closed_before_persistence_or_launch(tmp_path):
    _, store, supervised, coordinator = _harness(tmp_path, guard=None, required=True)
    outcome = coordinator.run_with_outcome(ARGV, timeout_seconds=30)
    assert outcome.kind.value == "FAILED"
    assert outcome.execution_id is None
    assert outcome.native.stderr == "SUPERVISED_PRE_DISPATCH_GUARD_REQUIRED"
    assert supervised.launch_calls == 0
    assert store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV)) == ()


def test_guard_exception_fails_closed_typed_unavailable(tmp_path):
    guard = CountingGuard(error=RuntimeError("lease authority exploded"))
    _, store, supervised, coordinator = _harness(tmp_path, guard=guard, required=True)
    outcome = coordinator.run_with_outcome(ARGV, timeout_seconds=30)
    assert outcome.kind.value == "FAILED"
    assert outcome.native.stderr == "SUPERVISED_PRE_DISPATCH_GUARD_UNAVAILABLE"
    assert supervised.launch_calls == 0
    assert store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV)) == ()


def test_malformed_guard_result_fails_closed_typed_invalid(tmp_path):
    for junk in (None, "ALLOW", {"kind": "ALLOW"}, object()):
        guard = CountingGuard(decision=junk)
        _, store, supervised, coordinator = _harness(tmp_path, guard=guard, required=True)
        outcome = coordinator.run_with_outcome(ARGV, timeout_seconds=30)
        assert outcome.kind.value == "FAILED", junk
        assert outcome.native.stderr == "SUPERVISED_PRE_DISPATCH_GUARD_INVALID", junk
        assert supervised.launch_calls == 0, junk
        assert store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV)) == (), junk


def test_typed_deny_blocks_record_and_launch(tmp_path):
    guard = CountingGuard(
        decision=PreDispatchGuardDecision(PreDispatchGuardDecisionKind.DENY, "LEASE_STALE")
    )
    _, store, supervised, coordinator = _harness(tmp_path, guard=guard, required=True)
    outcome = coordinator.run_with_outcome(ARGV, timeout_seconds=30)
    assert outcome.kind.value == "FAILED"
    assert outcome.native.stderr == "SUPERVISED_PRE_DISPATCH_GUARD_DENIED:LEASE_STALE"
    assert supervised.launch_calls == 0
    assert store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV)) == ()


def test_attach_running_does_not_invoke_fresh_launch_guard(tmp_path):
    from a_conductor.execution_record import ExecutionProcessState
    from a_conductor.supervised_execution import SupervisedInspection, SupervisedInspectionState

    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")

    class RunningThenResult(ScriptedSupervised):
        def launch(self, plan):
            outcome = super().launch(plan)
            with self._lock:
                record = self.records[outcome.record.execution_id]
                stored = store.set_execution_state(
                    record.execution_id,
                    ExecutionProcessState.RUNNING,
                    expected_version=record.version,
                )
                self.records[record.execution_id] = stored
            return outcome

        def inspect(self, execution_id):
            return SupervisedInspection(
                execution_id=execution_id,
                state=SupervisedInspectionState.RESULT_AVAILABLE,
                supervisor_pid=None,
                result_available=True,
                recovery_required=False,
            )

    supervised = RunningThenResult(repo, store)
    guard = CountingGuard()
    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=supervised,
        identity=_identity(repo),
        pre_dispatch_guard=guard,
        pre_dispatch_guard_required=True,
        poll_interval_seconds=0.01,
    )
    first = coordinator.run_with_outcome(ARGV, timeout_seconds=30)
    assert first.kind.value == "FRESH"
    launches = supervised.launch_calls
    assert guard.calls == 1

    second = coordinator.run_with_outcome(ARGV, timeout_seconds=30)
    assert second.kind.value == "ATTACH_RUNNING"
    assert second.execution_id == first.execution_id
    assert supervised.launch_calls == launches  # reused, no new launch
    assert guard.calls == 1  # ATTACH_RUNNING never invoked the fresh guard


def test_reuse_completed_does_not_invoke_fresh_launch_guard(tmp_path):
    guard = CountingGuard()
    _, store, supervised, coordinator = _harness(tmp_path, guard=guard, required=True)
    first = coordinator.run_with_outcome(ARGV, timeout_seconds=30)
    assert first.kind.value == "FRESH"
    launches = supervised.launch_calls

    second = coordinator.run_with_outcome(ARGV, timeout_seconds=30)
    assert second.kind.value == "REUSE_COMPLETED"
    assert second.execution_id == first.execution_id
    assert supervised.launch_calls == launches
    assert guard.calls == 1  # REUSE_COMPLETED never invoked the fresh guard


def test_blocked_unknown_never_reaches_guard(tmp_path):
    from a_conductor.execution_deduplication import (
        DuplicateExecutionAssessment,
        DuplicateExecutionDecision,
    )

    _, _, supervised, coordinator = _harness(tmp_path, guard=CountingGuard(), required=True)
    fingerprint = coordinator.fingerprint_for_argv(ARGV)

    class BlockedDedup:
        def assess(self, _spec):
            return DuplicateExecutionAssessment(
                decision=DuplicateExecutionDecision.BLOCKED_UNKNOWN,
                fingerprint=fingerprint,
                record=None,
                reason_code="AMBIGUOUS_HISTORY",
            )

    coordinator._guard = BlockedDedup()
    guard = coordinator._pre_dispatch_guard
    outcome = coordinator.run_with_outcome(ARGV, timeout_seconds=30)
    assert outcome.kind.value == "BLOCKED_UNKNOWN"
    assert guard.calls == 0


def test_guard_ordering_after_dedupe_before_mint_persist_launch(tmp_path, monkeypatch):
    """The guard runs after DuplicateExecutionGuard.assess and before the
    author-attempt mint, durable record persistence, or backend launch."""
    import a_conductor.supervised_run_coordinator as coord_module
    from a_conductor.supervised_run_coordinator import SupervisedRunIdentity
    from a_conductor.zero_relay_author_provenance import classify_author_provenance

    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    events: list[str] = []

    real_assess = coord_module.DuplicateExecutionGuard.assess

    class LoggingDedup(coord_module.DuplicateExecutionGuard):
        def assess(self, spec):
            events.append("assess")
            return real_assess(self, spec)

    class LoggingLaunch(ScriptedSupervised):
        def launch(self, plan):
            events.append("launch")
            return super().launch(plan)

    class LoggingGuard:
        def check(self):
            events.append("guard")
            return PreDispatchGuardDecision(PreDispatchGuardDecisionKind.ALLOW, "PRE_DISPATCH_ALLOWED")

    supervised = LoggingLaunch(repo, store)
    coordinator = SupervisedRunCoordinator(
        execution_store=store,
        supervised=supervised,
        identity=SupervisedRunIdentity(
            repo_root=str(repo),
            author_provenance=classify_author_provenance(
                task_contract_ref="docs/work-orders/WO-P1-158-zero-relay-zcode.md",
                packet_sha256="c" * 64,
            ),
            job_id="job-001",
            work_order_ref="docs/work-orders/WO-P1-158-zero-relay-zcode.md",
            project_id="project-1",
            worker_id="a-worker-01",
            backend_id="supervised-native",
            branch="main",
            head_before="b" * 40,
            runtime_profile_ref="runtime:test",
        ),
        pre_dispatch_guard=LoggingGuard(),
        pre_dispatch_guard_required=True,
        poll_interval_seconds=0.01,
    )
    coordinator._guard = LoggingDedup(store=store)

    real_mint = coord_module.mint_author_attempt_id

    def logging_mint():
        events.append("mint")
        return real_mint()

    monkeypatch.setattr(coord_module, "mint_author_attempt_id", logging_mint)

    outcome = coordinator.run_with_outcome(ARGV, timeout_seconds=30)
    assert outcome.native.exit_code == 0
    # exact ordering: dedupe assessment FIRST, guard SECOND, then mint, then
    # launch (record persistence happens inside the backend launch seam)
    assert events == ["assess", "guard", "mint", "launch"]


def test_fingerprint_bytes_identical_with_and_without_guard(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    plain = SupervisedRunCoordinator(
        execution_store=store,
        supervised=ScriptedSupervised(repo, store),
        identity=_identity(repo),
        poll_interval_seconds=0.01,
    )
    guarded = SupervisedRunCoordinator(
        execution_store=store,
        supervised=ScriptedSupervised(repo, store),
        identity=_identity(repo),
        pre_dispatch_guard=CountingGuard(),
        pre_dispatch_guard_required=True,
        poll_interval_seconds=0.01,
    )
    assert plain.fingerprint_for_argv(ARGV) == guarded.fingerprint_for_argv(ARGV)
    assert plain.fingerprint_spec(ARGV) == guarded.fingerprint_spec(ARGV)


def test_optional_route_without_guard_preserves_historical_behavior(tmp_path):
    _, store, supervised, coordinator = _harness(tmp_path, guard=None, required=False)
    outcome = coordinator.run_with_outcome(ARGV, timeout_seconds=30)
    assert outcome.kind.value == "FRESH"
    assert outcome.native.exit_code == 0
    assert supervised.launch_calls == 1
    assert len(store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV))) == 1


def test_coordinator_rejects_non_callable_guard(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    with pytest.raises(ValueError):
        SupervisedRunCoordinator(
            execution_store=SQLiteExecutionStore(tmp_path / "control.sqlite"),
            supervised=ScriptedSupervised(repo, SQLiteExecutionStore(tmp_path / "control.sqlite")),
            identity=_identity(repo),
            pre_dispatch_guard=object(),  # no check()
        )


def test_worker_lease_backed_guard_satisfies_coordinator_contract(tmp_path):
    """The WorkerLease-backed implementation plugs into the coordinator and
    allows an exact ACTIVE lease end to end (record + launch exactly once)."""
    baseline = _lease()
    reader = FakeHealthReader(LeaseHealth(LeaseHealthKind.ACTIVE, baseline))
    guard = WorkerLeasePreDispatchGuard(
        health_reader=reader,
        baseline_lease=baseline,
        requested_mutable_scope=_REQUESTED,
    )
    _, store, supervised, coordinator = _harness(tmp_path, guard=guard, required=True)
    outcome = coordinator.run_with_outcome(ARGV, timeout_seconds=30)
    assert outcome.kind.value == "FRESH"
    assert outcome.native.exit_code == 0
    assert supervised.launch_calls == 1
    assert len(store.find_by_fingerprint(coordinator.fingerprint_for_argv(ARGV))) == 1

    # launch-time release denies a subsequent FRESH dispatch before effects
    released = _lease(released_at=_now().isoformat())
    reader2 = FakeHealthReader(LeaseHealth(LeaseHealthKind.RELEASED, released))
    denied = WorkerLeasePreDispatchGuard(
        health_reader=reader2,
        baseline_lease=baseline,
        requested_mutable_scope=_REQUESTED,
    )
    repo2 = tmp_path / "repo2"
    repo2.mkdir(parents=True, exist_ok=True)
    store2 = SQLiteExecutionStore(tmp_path / "control2.sqlite")
    supervised2 = ScriptedSupervised(repo2, store2)
    coordinator2 = SupervisedRunCoordinator(
        execution_store=store2,
        supervised=supervised2,
        identity=_identity(repo2),
        pre_dispatch_guard=denied,
        pre_dispatch_guard_required=True,
        poll_interval_seconds=0.01,
    )
    outcome2 = coordinator2.run_with_outcome(ARGV, timeout_seconds=30)
    assert outcome2.kind.value == "FAILED"
    assert outcome2.native.stderr == "SUPERVISED_PRE_DISPATCH_GUARD_DENIED:LEASE_RELEASED"
    assert supervised2.launch_calls == 0
    assert store2.find_by_fingerprint(coordinator2.fingerprint_for_argv(ARGV)) == ()
