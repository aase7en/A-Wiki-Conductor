"""WO-P1-409 GOT-1a — production GoalCloseout composition wiring (RED-first).

Real existing stores (SQLiteJobStore, SQLiteWorkerLeaseStore,
NativeFileSystem, AgentChangeApplier, ContinuityProjectionFoldAdapter,
GoalCloseoutExecutor) plus an injected deterministic continuity provider
drive the bounded DurableJobControlService closeout entry end-to-end:
D1 VERIFYING->REVIEW_PENDING promotion, fold, canonical lease release,
and COMPLETE. All filesystem work happens in tmp_path.
"""
from __future__ import annotations

import pytest

from a_conductor.agent_change_packets import AgentChangeApplier
from a_conductor.continuity_guard import (
    ContinuityClassification,
    ContinuitySnapshot,
    MergeFoldFact,
)
from a_conductor.continuity_projection import (
    CANONICAL_TARGETS,
    ProjectionFacts,
    ProjectionLeaseFact,
    render_projection_target,
)
from a_conductor.domain import TaskState
from a_conductor.goal_closeout import (
    CloseoutStage,
    FoldRequirement,
    MergeEvidence,
    OwnershipEvidence,
    ReviewEvidence,
    VerificationEvidence,
    closeout_checkpoint_ref,
)
from a_conductor.job_control import DurableJobControlService, JobControlError
from a_conductor.job_execution import DurableJobExecutionCoordinator
from a_conductor.job_store import SQLiteJobStore
from a_conductor.native_execution import NativeExecutionScope, NativeFileSystem
from a_conductor.worker_lease import (
    LeaseHealthKind,
    LeaseMutationIntent,
    SQLiteWorkerLeaseStore,
    WorkerLeaseCandidate,
    WorkerLeaseRequest,
)

from a_conductor.goal_closeout_assembly import (
    CloseoutEvidenceBundle,
    GoalCloseoutAssemblyError,
    StaticCloseoutEvidenceProvider,
    assemble_goal_closeout_facade,
    completed_closeout_checkpoint_refs,
)

HEAD = "0f1e2d3c4b5a697887766554433221100f1e2d3c4b5a6978877665544332211f"
HEAD_OTHER = "1111222233334444555566667777888811112222333344445555666677778888"
BRANCH = "feat/wo-p1-409-example"
TASK = "task-409"
ATTEMPT = "attempt-1"
SESSION = "session-409"
JOB = "job-409-1"
LEASE = "lease-409-1"
WORKER = "a-worker-01"
T0 = "2026-09-08T00:00:00.000000Z"
NOW = "2026-09-08T00:05:00.000000Z"

VERIFY_REF = closeout_checkpoint_ref(
    CloseoutStage.VERIFY_CHECKPOINT, task_id=TASK, candidate_sha=HEAD, attempt_id=ATTEMPT
)
FOLD_REF = closeout_checkpoint_ref(
    CloseoutStage.FOLD, task_id=TASK, candidate_sha=HEAD, merge_key="nomerge", fold_key="required"
)
RELEASE_REF = closeout_checkpoint_ref(
    CloseoutStage.RELEASE_LEASE, task_id=TASK, candidate_sha=HEAD, lease_id=LEASE
)

CW_ANCHOR = "<!-- HISTORICAL EVIDENCE — superseded by WO162 (2026-09-07).            -->"
CW_FIXTURE = (
    "# A-Sunday Conductor — Current Work\n"
    "\n"
    "Last updated: 2026-09-08 (GPT1 — WO166 P0-B Continuity Guard activation)\n"
    "\n"
    "- **P0-B Continuity Guard is the current dependency frontier.**\n"
    "\n"
    + CW_ANCHOR + "\n"
    "<!-- Nothing below this separator is a current instruction.              -->\n"
    "\n"
    "## Post-PR208 merge actual-state override - 2026-09-05\n"
    "old historical body\n"
)
HO_ANCHOR = "<!-- HISTORICAL EVIDENCE — superseded by WO162 (2026-09-07).            -->"
HO_FIXTURE = (
    "# HANDOFF — A-Sunday Conductor\n"
    "\n"
    "Last updated: 2026-09-08 — GPT1 WO166 P0-B activation\n"
    "\n"
    "- WO165/ZRA-2 is queued successor only.\n"
    "\n"
    + HO_ANCHOR + "\n"
    "\n"
    "## WO158 / PR221 r5 handoff override - 2026-09-06\n"
    "old handoff history\n"
)
CO_WO166_ROW = (
    "| `WO-P1-166` P0-B Continuity Guard activation | GPT1 architecture/activation | "
    "FOLD_CANDIDATE / CONDITIONAL_RELEASE 2026-09-08 (self-closing) | Docs-only activation. |"
)
CO_FIXTURE = (
    "# A-Wiki Conductor — Agent Collaboration\n"
    "\n"
    "## In-progress claims\n"
    "\n"
    "| Chunk/WO | Agent | Claimed | Scope (files) |\n"
    "|---|---|---|---|\n"
    + CO_WO166_ROW + "\n"
    "\n"
    "## Released claims history\n"
    "human history text\n"
)
FIXTURES = {
    "CURRENT-WORK.md": CW_FIXTURE,
    "handoff.md": HO_FIXTURE,
    "COLLAB.md": CO_FIXTURE,
}


class FreshProvider:
    def continuity_snapshot(self, request) -> ContinuitySnapshot:
        return ContinuitySnapshot(
            worktree=request.worktree,
            branch=request.branch,
            session_id=request.session_id,
            task_id=request.task_id,
            expected_head=request.expected_head,
            local_head=request.actual_head,
            remote_head=request.actual_head,
            dirty_state="CLEAN",
            ownership_known=True,
            mutable_scope=request.mutable_scope,
        )


class MergedNotFoldedProvider(FreshProvider):
    def continuity_snapshot(self, request) -> ContinuitySnapshot:
        snapshot = super().continuity_snapshot(request)
        return ContinuitySnapshot(
            worktree=snapshot.worktree,
            branch=snapshot.branch,
            session_id=snapshot.session_id,
            task_id=snapshot.task_id,
            expected_head=snapshot.expected_head,
            local_head=snapshot.local_head,
            remote_head=snapshot.remote_head,
            dirty_state=snapshot.dirty_state,
            ownership_known=snapshot.ownership_known,
            mutable_scope=snapshot.mutable_scope,
            merge_fold=MergeFoldFact(
                merge_commit="abc1234", fold_complete=False, release_complete=True
            ),
        )


class CountingApplier:
    def __init__(self, inner):
        self.inner = inner
        self.apply_calls = 0

    @property
    def _filesystem(self):
        return self.inner._filesystem

    def apply(self, packet, lease_id, **kwargs):
        self.apply_calls += 1
        return self.inner.apply(packet, lease_id, **kwargs)


class FailingApplier:
    def __init__(self, inner, fail_on: int):
        self.inner = inner
        self.fail_on = fail_on
        self.seen = 0

    @property
    def _filesystem(self):
        return self.inner._filesystem

    def apply(self, packet, lease_id, **kwargs):
        from a_conductor.agent_change_packets import AgentChangeError

        self.seen += 1
        if self.seen == self.fail_on:
            raise AgentChangeError("CHANGE_APPLY_FAILED")
        return self.inner.apply(packet, lease_id, **kwargs)


class StaticBackend:
    def execute(self, operation_ref, context):
        raise AssertionError("closeout must not execute job operations")


def seed(root, fixtures=FIXTURES):
    for name, text in fixtures.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")


def make_job_store(tmp_path) -> SQLiteJobStore:
    return SQLiteJobStore(tmp_path / "jobs.sqlite")


def make_lease_store(tmp_path) -> SQLiteWorkerLeaseStore:
    return SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")


def drive_to_verifying(store, *, job_id=JOB) -> None:
    store.create_job(job_id=job_id, work_order_ref="WO-P1-409", project_id="project-409")
    version = 1
    for target, kwargs in (
        (TaskState.READY, {}),
        (TaskState.CLAIMED, {"worker_id": WORKER}),
        (TaskState.GATING, {}),
        (TaskState.EXECUTING, {}),
        (TaskState.VERIFYING, {}),
    ):
        store.transition(job_id, target, expected_version=version, **kwargs)
        version += 1


def drive_to_review_pending(store, *, job_id=JOB) -> None:
    drive_to_verifying(store, job_id=job_id)
    job = store.get_job(job_id)
    store.checkpoint(job_id, checkpoint_ref=VERIFY_REF, expected_version=job.version)
    job = store.get_job(job_id)
    store.transition(job_id, TaskState.REVIEW_PENDING, expected_version=job.version)


def make_lease(lease_store, root, *, lease_id=LEASE, session_id=SESSION, task_id=TASK):
    request = WorkerLeaseRequest(
        session_id=session_id,
        task_id=task_id,
        project_id="project-409",
        ordered_worker_ids=(WORKER,),
        required_capabilities=("code",),
        required_runtime_id=None,
        worktree=str(root),
        branch=BRANCH,
        expected_head=HEAD,
        mutation_intent=LeaseMutationIntent.MUTATION,
        allowed_scope=CANONICAL_TARGETS,
        forbidden_scope=("secrets/**",),
        mutable_scope=CANONICAL_TARGETS,
        lease_ttl_seconds=900,
    )
    candidate = WorkerLeaseCandidate(
        worker_id=WORKER,
        state="READY",
        reserved=False,
        active_task=False,
        capabilities=("code",),
        runtime_id=None,
        project_id="project-409",
        worktree=str(root),
        branch=BRANCH,
        head=HEAD,
        health_fresh=True,
        ownership_known=True,
        dirty_state="CLEAN",
        mutation_authorized=True,
    )
    result = lease_store.try_acquire_result(
        request, candidate, lease_id=lease_id, acquired_at=T0
    )
    assert result.created
    return lease_id


def V(**over) -> VerificationEvidence:
    base = dict(
        task_id=TASK,
        attempt_id=ATTEMPT,
        ok=True,
        checkpoint_ref=None,
        mutation_version=None,
        checkpoint_version=None,
    )
    base.update(over)
    return VerificationEvidence(**base)


def bundle(**over) -> CloseoutEvidenceBundle:
    base = dict(
        verification=V(),
        continuity=ContinuityClassification.FRESH,
        review=ReviewEvidence(required=False, passed=None, reviewed_sha=None),
        merge=MergeEvidence(
            required=False,
            merged=None,
            merge_commit=None,
            accepted_candidate_sha=None,
            accepted_candidate_ancestor=None,
            post_main_required=False,
            post_main_run_id=None,
            post_main_success=None,
            post_main_merge_commit=None,
        ),
        fold_requirement=FoldRequirement.REQUIRED,
        fold_not_required_reason=None,
        ownership=OwnershipEvidence(True, False, False),
        blocking_findings=(),
    )
    base.update(over)
    return CloseoutEvidenceBundle(**base)


def make_facade(
    tmp_path,
    *,
    root,
    store,
    lease_store,
    evidence=None,
    provider=None,
    applier_wrapper=None,
    lease_id=LEASE,
    job_id=JOB,
):
    real_applier = AgentChangeApplier(
        filesystem=NativeFileSystem(NativeExecutionScope(root=root, mutation_allowed=True)),
        lease_store=lease_store,
        continuity_provider=provider or FreshProvider(),
        clock=lambda: NOW,
    )
    applier = applier_wrapper(real_applier) if applier_wrapper else real_applier
    return assemble_goal_closeout_facade(
        job_store=store,
        lease_store=lease_store,
        applier=applier,
        evidence_provider=StaticCloseoutEvidenceProvider(evidence or bundle()),
        job_id=job_id,
        task_id=TASK,
        attempt_id=ATTEMPT,
        session_id=SESSION,
        lease_id=lease_id,
        candidate_sha=HEAD,
        branch=BRANCH,
        actual_head=HEAD,
        clock=lambda: NOW,
    )


def make_service(store, facade) -> DurableJobControlService:
    return DurableJobControlService(
        store=store,
        coordinator=DurableJobExecutionCoordinator(store=store, backend=StaticBackend()),
        closeout=facade,
    )


def build_harness(tmp_path, *, job_state, evidence=None, evidence_provider=None, provider=None, applier_wrapper=None, lease_id=LEASE):
    store = make_job_store(tmp_path)
    lease_store = make_lease_store(tmp_path)
    root = tmp_path / "repo"
    root.mkdir(parents=True, exist_ok=True)
    seed(root)
    if job_state is TaskState.VERIFYING:
        drive_to_verifying(store)
    else:
        drive_to_review_pending(store)
    if lease_id is not None:
        make_lease(lease_store, root, lease_id=lease_id)
    counting = CountingApplier(
        AgentChangeApplier(
            filesystem=NativeFileSystem(NativeExecutionScope(root=root, mutation_allowed=True)),
            lease_store=lease_store,
            continuity_provider=provider or FreshProvider(),
            clock=lambda: NOW,
        )
    )
    applier = applier_wrapper(counting) if applier_wrapper else counting
    facade = assemble_goal_closeout_facade(
        job_store=store,
        lease_store=lease_store,
        applier=applier,
        evidence_provider=evidence_provider
        or StaticCloseoutEvidenceProvider(evidence or bundle()),
        job_id=JOB,
        task_id=TASK,
        attempt_id=ATTEMPT,
        session_id=SESSION,
        lease_id=lease_id,
        candidate_sha=HEAD,
        branch=BRANCH,
        actual_head=HEAD,
        clock=lambda: NOW,
    )
    return store, lease_store, root, make_service(store, facade), counting


def harness(tmp_path, **kwargs):
    return build_harness(tmp_path, job_state=TaskState.VERIFYING, **kwargs)


def review_pending_harness(tmp_path, **kwargs):
    return build_harness(tmp_path, job_state=TaskState.REVIEW_PENDING, **kwargs)


def refs(store, job_id=JOB):
    return completed_closeout_checkpoint_refs(store, job_id)


def target_bytes(root):
    return {name: (root / name).read_bytes() for name in CANONICAL_TARGETS}


# ── end-to-end happy path through the service entry ────────────────────
def test_end_to_end_promote_fold_release_complete(tmp_path):
    store, lease_store, root, service, counting = harness(tmp_path)

    r1 = service.closeout_next_stage(JOB)
    assert r1.decision == "VERIFY_CHECKPOINT_REQUIRED"
    assert r1.stage == "VERIFY_CHECKPOINT"
    assert VERIFY_REF in refs(store)
    assert store.get_job(JOB).state is TaskState.VERIFYING
    assert counting.apply_calls == 0

    r2 = service.closeout_next_stage(JOB)
    assert r2.decision == "PROMOTED_TO_REVIEW_PENDING"
    assert store.get_job(JOB).state is TaskState.REVIEW_PENDING

    r3 = service.closeout_next_stage(JOB)
    assert r3.decision == "FOLD_REQUIRED"
    assert r3.stage == "FOLD"
    assert FOLD_REF in refs(store)
    assert counting.apply_calls == len(CANONICAL_TARGETS)
    for name in CANONICAL_TARGETS:
        text = (root / name).read_text(encoding="utf-8")
        assert "<!-- BEGIN-MACHINE-PROJECTION -->" in text
        assert HEAD in text
    assert lease_store.inspect_health(LEASE, now=NOW).kind is LeaseHealthKind.ACTIVE

    r4 = service.closeout_next_stage(JOB)
    assert r4.decision == "RELEASE_REQUIRED"
    assert r4.stage == "RELEASE_LEASE"
    assert RELEASE_REF in refs(store)
    assert lease_store.inspect_health(LEASE, now=NOW).kind is LeaseHealthKind.RELEASED

    r5 = service.closeout_next_stage(JOB)
    assert r5.decision == "COMPLETE_ALLOWED"
    job = store.get_job(JOB)
    assert job.state is TaskState.COMPLETE
    assert job.worker_id is None

    r6 = service.closeout_next_stage(JOB)
    assert r6.decision == "ALREADY_COMPLETE"


# ── D1: promotion gate ─────────────────────────────────────────────────
def test_d1_missing_verify_evidence_fails_closed_no_promotion(tmp_path):
    store, _, root, service, counting = harness(
        tmp_path, evidence=bundle(verification=V(ok=False))
    )
    result = service.closeout_next_stage(JOB)
    assert result.decision == "BLOCK"
    assert result.detail == "VERIFY_EVIDENCE_MISSING"
    assert result.stage == "VERIFYING_PROMOTION"
    assert store.get_job(JOB).state is TaskState.VERIFYING
    assert refs(store) == frozenset()
    assert counting.apply_calls == 0
    for name in CANONICAL_TARGETS:
        assert (root / name).read_text(encoding="utf-8") == FIXTURES[name]


def test_d1_identity_mismatch_fails_closed_no_promotion(tmp_path):
    store, _, _, service, counting = harness(
        tmp_path, evidence=bundle(verification=V(task_id="task-other"))
    )
    result = service.closeout_next_stage(JOB)
    assert result.decision == "BLOCK"
    assert result.detail == "VERIFY_IDENTITY_MISMATCH"
    assert store.get_job(JOB).state is TaskState.VERIFYING
    assert refs(store) == frozenset()
    assert counting.apply_calls == 0


def test_d1_attempt_mismatch_fails_closed_no_promotion(tmp_path):
    store, _, _, service, counting = harness(
        tmp_path, evidence=bundle(verification=V(attempt_id="attempt-other"))
    )
    result = service.closeout_next_stage(JOB)
    assert result.decision == "BLOCK"
    assert result.detail == "VERIFY_IDENTITY_MISMATCH"
    assert store.get_job(JOB).state is TaskState.VERIFYING
    assert refs(store) == frozenset()
    assert counting.apply_calls == 0


def test_d1_no_promotion_until_durable_verify_checkpoint_exists(tmp_path):
    store, _, _, service, _ = harness(tmp_path, evidence=bundle(verification=V()))
    r1 = service.closeout_next_stage(JOB)
    assert r1.decision == "VERIFY_CHECKPOINT_REQUIRED"
    assert store.get_job(JOB).state is TaskState.VERIFYING
    r2 = service.closeout_next_stage(JOB)
    assert r2.decision == "PROMOTED_TO_REVIEW_PENDING"
    assert store.get_job(JOB).state is TaskState.REVIEW_PENDING


def test_d1_evidence_claimed_checkpoint_still_requires_journal(tmp_path):
    store, _, _, service, _ = harness(
        tmp_path, evidence=bundle(verification=V(checkpoint_version=4))
    )
    result = service.closeout_next_stage(JOB)
    assert result.decision == "VERIFY_CHECKPOINT_REQUIRED"
    assert store.get_job(JOB).state is TaskState.VERIFYING
    assert VERIFY_REF in refs(store)


def test_d1_old_attempt_checkpoint_does_not_satisfy_current_attempt(tmp_path):
    store, _, _, service, _ = harness(tmp_path)
    old_ref = closeout_checkpoint_ref(
        CloseoutStage.VERIFY_CHECKPOINT,
        task_id=TASK,
        candidate_sha=HEAD,
        attempt_id="attempt-2",
    )
    store.checkpoint(JOB, checkpoint_ref=old_ref, expected_version=6)
    r1 = service.closeout_next_stage(JOB)
    assert r1.decision == "VERIFY_CHECKPOINT_REQUIRED"
    assert store.get_job(JOB).state is TaskState.VERIFYING
    assert VERIFY_REF in refs(store)
    r2 = service.closeout_next_stage(JOB)
    assert r2.decision == "PROMOTED_TO_REVIEW_PENDING"


def test_d1_journal_checkpoint_but_contradicted_evidence_fails_closed(tmp_path):
    store, _, _, service, _ = harness(tmp_path, evidence=bundle(verification=V(ok=False)))
    store.checkpoint(JOB, checkpoint_ref=VERIFY_REF, expected_version=6)
    result = service.closeout_next_stage(JOB)
    assert result.decision == "BLOCK"
    assert store.get_job(JOB).state is TaskState.VERIFYING


def test_d1_mutation_ahead_of_journal_is_recovery(tmp_path):
    store, _, root, service, counting = harness(
        tmp_path,
        evidence=bundle(verification=V(mutation_version=9, checkpoint_version=4)),
    )
    result = service.closeout_next_stage(JOB)
    assert result.decision == "RECOVERY_REQUIRED"
    assert result.detail == "MUTATION_AHEAD_OF_JOURNAL"
    assert store.get_job(JOB).state is TaskState.VERIFYING
    assert refs(store) == frozenset()
    assert counting.apply_calls == 0
    for name in CANONICAL_TARGETS:
        assert (root / name).read_text(encoding="utf-8") == FIXTURES[name]


# ── state-graph respect ────────────────────────────────────────────────
def test_executing_job_is_typed_invalid_no_shortcut(tmp_path):
    store = make_job_store(tmp_path)
    lease_store = make_lease_store(tmp_path)
    root = tmp_path / "repo"
    root.mkdir()
    seed(root)
    store.create_job(job_id=JOB, work_order_ref="WO-P1-409", project_id="project-409")
    store.transition(JOB, TaskState.READY, expected_version=1)
    store.transition(JOB, TaskState.CLAIMED, expected_version=2, worker_id=WORKER)
    store.transition(JOB, TaskState.GATING, expected_version=3)
    store.transition(JOB, TaskState.EXECUTING, expected_version=4)
    make_lease(lease_store, root)
    facade = make_facade(
        tmp_path, root=root, store=store, lease_store=lease_store, lease_id=LEASE
    )
    service = make_service(store, facade)
    result = service.closeout_next_stage(JOB)
    assert result.decision == "CLOSEOUT_STATE_INVALID"
    assert store.get_job(JOB).state is TaskState.EXECUTING


def test_complete_job_is_already_complete_noop(tmp_path):
    store, _, _, service, _ = harness(tmp_path)
    job = store.get_job(JOB)
    store.checkpoint(JOB, checkpoint_ref=VERIFY_REF, expected_version=job.version)
    job = store.get_job(JOB)
    store.transition(JOB, TaskState.REVIEW_PENDING, expected_version=job.version)
    job = store.get_job(JOB)
    store.transition(JOB, TaskState.COMPLETE, expected_version=job.version)
    result = service.closeout_next_stage(JOB)
    assert result.decision == "ALREADY_COMPLETE"


# ── fail-closed continuity / merge / review gates after promotion ──────
def test_unknown_continuity_fails_closed_zero_writes(tmp_path):
    store, _, root, service, counting = review_pending_harness(
        tmp_path, evidence=bundle(continuity=ContinuityClassification.UNKNOWN)
    )
    before = target_bytes(root)
    result = service.closeout_next_stage(JOB)
    assert result.decision == "RECOVERY_REQUIRED"
    assert result.detail == "CONTINUITY_UNKNOWN"
    assert store.get_job(JOB).state is TaskState.REVIEW_PENDING
    assert counting.apply_calls == 0
    assert target_bytes(root) == before


def test_merge_required_unknown_never_completes(tmp_path):
    store, _, root, service, counting = review_pending_harness(
        tmp_path,
        evidence=bundle(
            merge=MergeEvidence(
                required=True,
                merged=None,
                merge_commit=None,
                accepted_candidate_sha=None,
                accepted_candidate_ancestor=None,
                post_main_required=False,
                post_main_run_id=None,
                post_main_success=None,
                post_main_merge_commit=None,
            )
        ),
    )
    before = target_bytes(root)
    result = service.closeout_next_stage(JOB)
    assert result.decision == "BLOCK"
    assert result.detail == "MERGE_NOT_MERGED"
    assert store.get_job(JOB).state is TaskState.REVIEW_PENDING
    assert counting.apply_calls == 0
    assert target_bytes(root) == before


def test_post_main_unknown_pending_blocks(tmp_path):
    store, _, _, service, _ = review_pending_harness(
        tmp_path,
        evidence=bundle(
            merge=MergeEvidence(
                required=True,
                merged=True,
                merge_commit="abc1234",
                accepted_candidate_sha=HEAD,
                accepted_candidate_ancestor=True,
                post_main_required=True,
                post_main_run_id="run-409",
                post_main_success=None,
                post_main_merge_commit="abc1234",
            )
        ),
    )
    result = service.closeout_next_stage(JOB)
    assert result.decision == "BLOCK"
    assert result.detail == "POST_MAIN_PENDING"
    assert store.get_job(JOB).state is not TaskState.COMPLETE


def test_stale_review_sha_blocks_completion(tmp_path):
    store, _, _, service, _ = review_pending_harness(
        tmp_path,
        evidence=bundle(
            review=ReviewEvidence(required=True, passed=True, reviewed_sha=HEAD_OTHER)
        ),
    )
    result = service.closeout_next_stage(JOB)
    assert result.decision == "BLOCK"
    assert result.detail == "STALE_REVIEW_SHA"
    assert store.get_job(JOB).state is TaskState.REVIEW_PENDING


# ── MERGED_NOT_FOLDED stays structurally blocked (Issue #410 owns it) ──
def test_merged_not_folded_structurally_blocked_zero_writes(tmp_path):
    store, lease_store, root, service, counting = review_pending_harness(
        tmp_path,
        evidence=bundle(continuity=ContinuityClassification.MERGED_NOT_FOLDED),
        provider=MergedNotFoldedProvider(),
    )
    before = target_bytes(root)
    result = service.closeout_next_stage(JOB)
    assert result.decision == "RECOVERY_REQUIRED"
    assert result.detail in ("FOLD_NOT_COMPLETED", "FOLD_OUTCOME_UNKNOWN")
    assert store.get_job(JOB).state is TaskState.REVIEW_PENDING
    assert counting.apply_calls >= 1
    assert target_bytes(root) == before
    assert FOLD_REF not in refs(store)
    assert lease_store.inspect_health(LEASE, now=NOW).kind is LeaseHealthKind.ACTIVE


# ── fold checkpoint only after confirmed fold; canonical release ───────
def test_fold_failure_writes_no_fold_checkpoint(tmp_path):
    store, _, _, service, _ = review_pending_harness(
        tmp_path, applier_wrapper=lambda counting: FailingApplier(counting, fail_on=2)
    )
    result = service.closeout_next_stage(JOB)
    assert result.decision == "RECOVERY_REQUIRED"
    assert FOLD_REF not in refs(store)
    assert store.get_job(JOB).state is TaskState.REVIEW_PENDING


def test_release_crash_before_checkpoint_fails_closed(tmp_path):
    store, lease_store, _, service, _ = review_pending_harness(
        tmp_path,
        evidence=bundle(
            fold_requirement=FoldRequirement.NOT_REQUIRED,
            fold_not_required_reason="non-mutating review task",
        ),
    )
    lease_store.release(LEASE, session_id=SESSION, task_id=TASK, released_at=NOW)
    result = service.closeout_next_stage(JOB)
    assert result.decision == "RECOVERY_REQUIRED"
    assert result.detail == "LEASE_RELEASE_CHECKPOINT_MISSING"
    assert store.get_job(JOB).state is TaskState.REVIEW_PENDING


# ── idempotent republish: zero unnecessary writes ──────────────────────
def test_stage_after_completed_fold_does_not_rewrite_targets(tmp_path):
    store, lease_store, root, service, _ = review_pending_harness(tmp_path)
    first = service.closeout_next_stage(JOB)
    assert first.decision == "FOLD_REQUIRED"
    counting = CountingApplier(
        AgentChangeApplier(
            filesystem=NativeFileSystem(NativeExecutionScope(root=root, mutation_allowed=True)),
            lease_store=lease_store,
            continuity_provider=FreshProvider(),
            clock=lambda: NOW,
        )
    )
    next_service = make_service(
        store,
        assemble_goal_closeout_facade(
            job_store=store,
            lease_store=lease_store,
            applier=counting,
            evidence_provider=StaticCloseoutEvidenceProvider(bundle()),
            job_id=JOB,
            task_id=TASK,
            attempt_id=ATTEMPT,
            session_id=SESSION,
            lease_id=LEASE,
            candidate_sha=HEAD,
            branch=BRANCH,
            actual_head=HEAD,
            clock=lambda: NOW,
        ),
    )
    before = target_bytes(root)
    result = next_service.closeout_next_stage(JOB)
    assert result.decision == "RELEASE_REQUIRED"
    assert counting.apply_calls == 0
    assert target_bytes(root) == before


def test_fold_idempotent_republish_zero_apply_calls(tmp_path):
    store, lease_store, root, _, _ = review_pending_harness(tmp_path)
    expected_facts = ProjectionFacts(
        task_id=TASK,
        candidate_sha=HEAD,
        branch=BRANCH,
        head=HEAD,
        merge_commit=None,
        post_main_status="NOT_REQUIRED",
        closeout_status="FOLD_PENDING",
        leases=(ProjectionLeaseFact(LEASE, SESSION, TASK, "ACTIVE", True),),
        ownership_known=True,
        writer_session=SESSION,
    )
    for name in CANONICAL_TARGETS:
        rendered = render_projection_target(name, expected_facts, prior_text=FIXTURES[name])
        (root / name).write_text(rendered, encoding="utf-8", newline="\n")
    before = target_bytes(root)
    counting = CountingApplier(
        AgentChangeApplier(
            filesystem=NativeFileSystem(NativeExecutionScope(root=root, mutation_allowed=True)),
            lease_store=lease_store,
            continuity_provider=FreshProvider(),
            clock=lambda: NOW,
        )
    )
    service = make_service(
        store,
        assemble_goal_closeout_facade(
            job_store=store,
            lease_store=lease_store,
            applier=counting,
            evidence_provider=StaticCloseoutEvidenceProvider(bundle()),
            job_id=JOB,
            task_id=TASK,
            attempt_id=ATTEMPT,
            session_id=SESSION,
            lease_id=LEASE,
            candidate_sha=HEAD,
            branch=BRANCH,
            actual_head=HEAD,
            clock=lambda: NOW,
        ),
    )
    result = service.closeout_next_stage(JOB)
    assert result.decision == "FOLD_REQUIRED"
    assert counting.apply_calls == 0
    assert target_bytes(root) == before
    assert FOLD_REF in refs(store)


# ── non-mutating lane completes without lease or fold ──────────────────
def test_non_mutating_review_pending_completes_without_lease(tmp_path):
    store, _, _, service, _ = review_pending_harness(
        tmp_path,
        lease_id=None,
        evidence=bundle(
            fold_requirement=FoldRequirement.NOT_REQUIRED,
            fold_not_required_reason="non-mutating review task",
        ),
    )
    result = service.closeout_next_stage(JOB)
    assert result.decision == "COMPLETE_ALLOWED"
    assert store.get_job(JOB).state is TaskState.COMPLETE


# ── facade binding and service configuration guards ────────────────────
def test_facade_rejects_foreign_job_id(tmp_path):
    store, lease_store, root, _, _ = harness(tmp_path)
    facade = make_facade(
        tmp_path, root=root, store=store, lease_store=lease_store, job_id="job-other"
    )
    with pytest.raises(GoalCloseoutAssemblyError) as exc:
        facade.next_stage(JOB)
    assert exc.value.code == "CLOSEOUT_JOB_MISMATCH"


def test_service_without_closeout_composition_is_typed(tmp_path):
    store = make_job_store(tmp_path)
    service = DurableJobControlService(
        store=store,
        coordinator=DurableJobExecutionCoordinator(store=store, backend=StaticBackend()),
    )
    with pytest.raises(JobControlError) as exc:
        service.closeout_next_stage(JOB)
    assert exc.value.code == "CLOSEOUT_NOT_CONFIGURED"


def test_assembly_module_creates_no_second_authority():
    import inspect
    from a_conductor import goal_closeout_assembly as module

    source = inspect.getsource(module)
    for banned in (
        "CREATE TABLE",
        "sqlite3.connect",
        "subprocess",
        "threading",
        "asyncio",
        "requests",
        "time.time",
        "datetime.now",
    ):
        assert banned not in source, banned


# ── attempt-0002 P1-1: production open() composition path (RED-first) ──
class NoNativeResolver:
    def resolve(self, *args, **kwargs):
        raise AssertionError("closeout composition must not resolve native adapters")


def open_composed_service(tmp_path, *, evidence_provider=None):
    from a_conductor.goal_closeout_assembly import (
        GoalCloseoutCompositionConfig,
        StaticCloseoutEvidenceProvider,
    )

    lease_store = make_lease_store(tmp_path)
    root = tmp_path / "repo"
    root.mkdir(parents=True, exist_ok=True)
    seed(root)
    make_lease(lease_store, root)
    config = GoalCloseoutCompositionConfig(
        evidence_provider=evidence_provider
        or StaticCloseoutEvidenceProvider(bundle()),
        applier=AgentChangeApplier(
            filesystem=NativeFileSystem(
                NativeExecutionScope(root=root, mutation_allowed=True)
            ),
            lease_store=lease_store,
            continuity_provider=FreshProvider(),
            clock=lambda: NOW,
        ),
        lease_store=lease_store,
        job_id=JOB,
        task_id=TASK,
        attempt_id=ATTEMPT,
        session_id=SESSION,
        lease_id=LEASE,
        candidate_sha=HEAD,
        branch=BRANCH,
        actual_head=HEAD,
        clock=lambda: NOW,
    )
    return DurableJobControlService.open(
        tmp_path / "jobs.sqlite",
        operations=(),
        native_resolver=NoNativeResolver(),
        closeout_composition=config,
    )


def test_open_composes_closeout_using_same_store_end_to_end(tmp_path):
    seed_store = make_job_store(tmp_path)
    drive_to_verifying(seed_store)
    service = open_composed_service(tmp_path)
    assert service.get_job(JOB).state is TaskState.VERIFYING
    assert service._closeout is not None
    assert service._closeout._job_store is service._store

    r1 = service.closeout_next_stage(JOB)
    assert r1.decision == "VERIFY_CHECKPOINT_REQUIRED"
    r2 = service.closeout_next_stage(JOB)
    assert r2.decision == "PROMOTED_TO_REVIEW_PENDING"
    r3 = service.closeout_next_stage(JOB)
    assert r3.decision == "FOLD_REQUIRED"
    r4 = service.closeout_next_stage(JOB)
    assert r4.decision == "RELEASE_REQUIRED"
    r5 = service.closeout_next_stage(JOB)
    assert r5.decision == "COMPLETE_ALLOWED"
    assert seed_store.get_job(JOB).state is TaskState.COMPLETE


def test_open_without_closeout_composition_still_plain_service(tmp_path):
    service = DurableJobControlService.open(
        tmp_path / "jobs.sqlite",
        operations=(),
        native_resolver=NoNativeResolver(),
    )
    service.create_job(job_id=JOB, work_order_ref="WO-P1-409", project_id="project-409")
    assert service.get_job(JOB).job_id == JOB
    with pytest.raises(JobControlError) as exc:
        service.closeout_next_stage(JOB)
    assert exc.value.code == "CLOSEOUT_NOT_CONFIGURED"


# ── attempt-0002 P1-2: per-stage trusted evidence refresh (RED-first) ──
class SequenceEvidenceProvider:
    def __init__(self, bundles):
        self._bundles = list(bundles)
        self.calls = 0

    def evidence(self):
        index = min(self.calls, len(self._bundles) - 1)
        self.calls += 1
        return self._bundles[index]


class CountingEvidenceProvider:
    def __init__(self, inner):
        self.inner = inner
        self.calls = 0

    def evidence(self):
        self.calls += 1
        return self.inner.evidence()


class InvalidEvidenceProvider:
    def evidence(self):
        return object()


def provider_service(tmp_path, *, evidence_provider):
    from a_conductor.goal_closeout_assembly import assemble_goal_closeout_facade

    store = make_job_store(tmp_path)
    lease_store = make_lease_store(tmp_path)
    root = tmp_path / "repo"
    root.mkdir(parents=True, exist_ok=True)
    seed(root)
    drive_to_review_pending(store)
    make_lease(lease_store, root)
    counting = CountingApplier(
        AgentChangeApplier(
            filesystem=NativeFileSystem(
                NativeExecutionScope(root=root, mutation_allowed=True)
            ),
            lease_store=lease_store,
            continuity_provider=FreshProvider(),
            clock=lambda: NOW,
        )
    )
    facade = assemble_goal_closeout_facade(
        job_store=store,
        lease_store=lease_store,
        applier=counting,
        evidence_provider=evidence_provider,
        job_id=JOB,
        task_id=TASK,
        attempt_id=ATTEMPT,
        session_id=SESSION,
        lease_id=LEASE,
        candidate_sha=HEAD,
        branch=BRANCH,
        actual_head=HEAD,
        clock=lambda: NOW,
    )
    return store, lease_store, root, make_service(store, facade), counting


def test_changed_trusted_evidence_between_stages_is_not_ignored(tmp_path):
    provider = SequenceEvidenceProvider(
        [
            bundle(),
            bundle(blocking_findings=("integrator-blocking-finding",)),
        ]
    )
    store, lease_store, _, service, _ = provider_service(
        tmp_path, evidence_provider=provider
    )
    r1 = service.closeout_next_stage(JOB)
    assert r1.decision == "FOLD_REQUIRED"
    assert provider.calls == 1
    r2 = service.closeout_next_stage(JOB)
    assert r2.decision == "BLOCK"
    assert r2.detail == "BLOCKING_FINDINGS"
    assert store.get_job(JOB).state is TaskState.REVIEW_PENDING
    assert lease_store.inspect_health(LEASE, now=NOW).kind is LeaseHealthKind.ACTIVE


def test_evidence_refreshed_exactly_once_per_stage(tmp_path):
    provider = CountingEvidenceProvider(SequenceEvidenceProvider([bundle()]))
    store, _, _, service, counting = provider_service(tmp_path, evidence_provider=provider)
    r1 = service.closeout_next_stage(JOB)
    assert r1.decision == "FOLD_REQUIRED"
    assert counting.apply_calls == len(CANONICAL_TARGETS)
    assert provider.calls == 1
    r2 = service.closeout_next_stage(JOB)
    assert r2.decision == "RELEASE_REQUIRED"
    assert provider.calls == 2


def test_invalid_bundle_from_provider_fails_typed_zero_writes(tmp_path):
    store, _, root, service, counting = provider_service(
        tmp_path, evidence_provider=InvalidEvidenceProvider()
    )
    before = target_bytes(root)
    with pytest.raises(GoalCloseoutAssemblyError) as exc:
        service.closeout_next_stage(JOB)
    assert exc.value.code == "EVIDENCE_BUNDLE_INVALID"
    assert store.get_job(JOB).state is TaskState.REVIEW_PENDING
    assert counting.apply_calls == 0
    assert target_bytes(root) == before


def test_one_immutable_snapshot_bound_through_single_stage(tmp_path):
    def merged(commit):
        return MergeEvidence(
            required=True,
            merged=True,
            merge_commit=commit,
            accepted_candidate_sha=HEAD,
            accepted_candidate_ancestor=True,
            post_main_required=False,
            post_main_run_id=None,
            post_main_success=None,
            post_main_merge_commit=None,
        )

    fold_ref_a = closeout_checkpoint_ref(
        CloseoutStage.FOLD,
        task_id=TASK,
        candidate_sha=HEAD,
        merge_key="aaaaaaa",
        fold_key="required",
    )
    fold_ref_b = closeout_checkpoint_ref(
        CloseoutStage.FOLD,
        task_id=TASK,
        candidate_sha=HEAD,
        merge_key="bbbbbbb",
        fold_key="required",
    )
    provider = SequenceEvidenceProvider(
        [bundle(merge=merged("aaaaaaa")), bundle(merge=merged("bbbbbbb"))]
    )
    store, _, root, service, counting = provider_service(
        tmp_path, evidence_provider=provider
    )
    r1 = service.closeout_next_stage(JOB)
    assert r1.decision == "FOLD_REQUIRED"
    assert fold_ref_a in refs(store)
    assert fold_ref_b not in refs(store)
    assert "merge-commit: aaaaaaa" in (root / "CURRENT-WORK.md").read_text(
        encoding="utf-8"
    )
    r2 = service.closeout_next_stage(JOB)
    assert r2.decision == "FOLD_REQUIRED"
    assert fold_ref_b in refs(store)
    assert "merge-commit: bbbbbbb" in (root / "CURRENT-WORK.md").read_text(
        encoding="utf-8"
    )
    assert provider.calls == 2
