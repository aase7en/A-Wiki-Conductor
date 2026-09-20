"""WO-P1-419 GOT-1b-B — production merge/post-main evidence provider (RED-first).

Real existing authorities (SQLiteJobStore CHECKPOINT journal,
SQLiteWorkerLeaseStore, classify_continuity, completed_closeout_checkpoint_refs,
CloseoutEvidenceBundle/GoalCloseout planner) plus bounded injected observation
ports (merge / post-main / local Git / accepted review) drive the READ-ONLY
ProductionCloseoutEvidenceProvider: one evidence() call yields one internally
consistent re-pinned bundle; missing, stale, contradictory, malformed or
drifting facts fail closed and never coerce into success. The provider
performs zero writes of its own.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import a_conductor
from a_conductor.continuity_guard import (
    ContinuityClassification,
    ContinuitySnapshot,
    LeaseFact,
)
from a_conductor.domain import TaskState
from a_conductor.goal_closeout import (
    CloseoutDecision,
    CloseoutStage,
    FoldEvidence,
    FoldRequirement,
    LeaseEvidence,
    closeout_checkpoint_ref,
    plan_goal_closeout,
)
from a_conductor.goal_closeout_assembly import (
    CloseoutEvidenceBundle,
    assemble_goal_closeout_facade,
    completed_closeout_checkpoint_refs,
)
from a_conductor.job_store import SQLiteJobStore
from a_conductor.worker_lease import (
    LeaseMutationIntent,
    SQLiteWorkerLeaseStore,
    WorkerLeaseCandidate,
    WorkerLeaseRequest,
)

from a_conductor.production_closeout_observation import (
    PRODUCTION_REPOSITORY,
    PRODUCTION_WORKFLOW_ID,
    PRODUCTION_WORKFLOW_NAME,
    AcceptedReviewObservation,
    BoundedGitHubObservationAdapter,
    LocalGitObservation,
    MergeObservation,
    PostMainRunObservation,
    ProductionCloseoutEvidenceProvider,
    ProductionCloseoutObservationError,
    StrictLocalGitObserver,
)

REPO = "aase7en/A-Wiki-Conductor"
PR_NUMBER = 417
WORKFLOW_ID = 338737025
WORKFLOW_NAME = "CI"
CANDIDATE = "0f1e2d3c4b5a697887766554433221100f1e2d3c4b5a6978877665544332211f"
MERGE_COMMIT = "1111222233334444555566667777888811112222333344445555666677778888"
OTHER_SHA = "9999888877776666555544443333222211110000999988887777666655554444"
RUN_ID = "35494699488"
TASK = "task-419"
ATTEMPT = "attempt-0001"
SESSION = "session-419"
JOB = "job-419-1"
LEASE = "lease-419-1"
WORKER = "a-worker-01"
BRANCH = "feat/wo-p1-419-example"
T0 = "2026-09-18T00:00:00.000000Z"
NOW = "2026-09-18T00:05:00.000000Z"

assert PRODUCTION_REPOSITORY == REPO
assert PRODUCTION_WORKFLOW_ID == WORKFLOW_ID
assert PRODUCTION_WORKFLOW_NAME == WORKFLOW_NAME

VERIFY_REF = closeout_checkpoint_ref(
    CloseoutStage.VERIFY_CHECKPOINT, task_id=TASK, candidate_sha=CANDIDATE, attempt_id=ATTEMPT
)
FOLD_REF = closeout_checkpoint_ref(
    CloseoutStage.FOLD,
    task_id=TASK,
    candidate_sha=CANDIDATE,
    merge_key=MERGE_COMMIT,
    fold_key="required",
)
RELEASE_REF = closeout_checkpoint_ref(
    CloseoutStage.RELEASE_LEASE, task_id=TASK, candidate_sha=CANDIDATE, lease_id=LEASE
)


class ProductionError(ProductionCloseoutObservationError):
    pass


# ── fakes (injected observation ports only; stores are real) ────────────


class FakeGitObserver:
    def __init__(self, head=CANDIDATE, branch=BRANCH, dirty="CLEAN", ancestry=True,
                 script=None):
        self._base = LocalGitObservation(branch=branch, head=head, dirty_state=dirty)
        self._script = script or []
        self.ancestry_calls = []
        self._ancestry = ancestry
        self.observe_calls = 0

    def observe(self) -> LocalGitObservation:
        self.observe_calls += 1
        if self._script:
            return self._script.pop(0)
        return self._base

    def candidate_is_ancestor(self, candidate_sha: str, merge_commit_sha: str):
        self.ancestry_calls.append((candidate_sha, merge_commit_sha))
        return self._ancestry


class FakeMergePort:
    def __init__(self, observation=None, on_call=None):
        self.observation = observation or green_merge()
        self.on_call = on_call
        self.calls = 0

    def observe_merge(self) -> MergeObservation:
        self.calls += 1
        if self.on_call is not None:
            self.on_call()
        return self.observation


class FakePostMainPort:
    def __init__(self, observation=None):
        self.observation = observation or green_run()
        self.calls = []

    def observe_post_main_run(self, merge_commit_sha: str) -> PostMainRunObservation:
        self.calls.append(merge_commit_sha)
        return self.observation


class FakeReviewPort:
    def __init__(self, observation):
        self.observation = observation
        self.calls = 0

    def observe_review(self):
        self.calls += 1
        return self.observation


def green_merge(**over) -> MergeObservation:
    base = dict(
        observed=True,
        repository=REPO,
        pr_number=PR_NUMBER,
        merged=True,
        merge_commit_sha=MERGE_COMMIT,
        pr_head_sha=CANDIDATE,
    )
    base.update(over)
    return MergeObservation(**base)


def green_run(**over) -> PostMainRunObservation:
    base = dict(
        observed=True,
        repository=REPO,
        workflow_id=WORKFLOW_ID,
        workflow_name=WORKFLOW_NAME,
        run_id=RUN_ID,
        run_head_sha=MERGE_COMMIT,
        status="completed",
        conclusion="SUCCESS",
    )
    base.update(over)
    return PostMainRunObservation(**base)


def accepted_review(head=CANDIDATE) -> AcceptedReviewObservation:
    return AcceptedReviewObservation(reviewed_head=head, disposition="ACCEPTED")


# ── durable-store seeding (existing authorities only) ───────────────────


def make_job_store(tmp_path) -> SQLiteJobStore:
    return SQLiteJobStore(tmp_path / "jobs.sqlite")


def make_lease_store(tmp_path) -> SQLiteWorkerLeaseStore:
    return SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")


def drive_to_review_pending(store, *, job_id=JOB) -> None:
    store.create_job(job_id=job_id, work_order_ref="WO-P1-419", project_id="project-419")
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
    job = store.get_job(job_id)
    store.checkpoint(job_id, checkpoint_ref=VERIFY_REF, expected_version=job.version)
    job = store.get_job(job_id)
    store.transition(job_id, TaskState.REVIEW_PENDING, expected_version=job.version)


def add_ref(store, ref, *, job_id=JOB) -> None:
    job = store.get_job(job_id)
    store.checkpoint(job_id, checkpoint_ref=ref, expected_version=job.version)


def make_lease(lease_store, root, *, lease_id=LEASE, session_id=SESSION, task_id=TASK):
    request = WorkerLeaseRequest(
        session_id=session_id,
        task_id=task_id,
        project_id="project-419",
        ordered_worker_ids=(WORKER,),
        required_capabilities=("code",),
        required_runtime_id=None,
        worktree=str(root),
        branch=BRANCH,
        expected_head=CANDIDATE,
        mutation_intent=LeaseMutationIntent.MUTATION,
        allowed_scope=("CURRENT-WORK.md", "handoff.md", "COLLAB.md"),
        forbidden_scope=("secrets/**",),
        mutable_scope=("CURRENT-WORK.md", "handoff.md", "COLLAB.md"),
        lease_ttl_seconds=900,
    )
    candidate = WorkerLeaseCandidate(
        worker_id=WORKER,
        state="READY",
        reserved=False,
        active_task=False,
        capabilities=("code",),
        runtime_id=None,
        project_id="project-419",
        worktree=str(root),
        branch=BRANCH,
        head=CANDIDATE,
        health_fresh=True,
        ownership_known=True,
        dirty_state="CLEAN",
        mutation_authorized=True,
    )
    result = lease_store.try_acquire_result(request, candidate, lease_id=lease_id, acquired_at=T0)
    assert result.created
    return lease_id


def build(
    tmp_path,
    *,
    refs=(VERIFY_REF, FOLD_REF, RELEASE_REF),
    lease="released",
    git=None,
    merge=None,
    post_main=None,
    review="accepted",
    foreign_lease=False,
):
    store = make_job_store(tmp_path)
    lease_store = make_lease_store(tmp_path)
    root = tmp_path / "repo"
    root.mkdir(parents=True, exist_ok=True)
    drive_to_review_pending(store)
    for ref in refs:
        add_ref(store, ref)
    lease_id = None
    if lease in ("released", "active"):
        lease_id = LEASE
        make_lease(lease_store, root, lease_id=LEASE)
        if lease == "released":
            lease_store.release(LEASE, session_id=SESSION, task_id=TASK, released_at=NOW)
    if foreign_lease:
        make_lease(
            lease_store, root, lease_id="lease-foreign",
            session_id="session-other", task_id="task-other",
        )
    review_port = None
    if review == "accepted":
        review_port = FakeReviewPort(accepted_review())
    elif review == "missing":
        review_port = FakeReviewPort(None)
    elif review is not None:
        review_port = FakeReviewPort(review)
    provider = ProductionCloseoutEvidenceProvider(
        job_store=store,
        lease_store=lease_store,
        git_observer=git or FakeGitObserver(),
        merge_port=merge or FakeMergePort(),
        post_main_port=post_main or FakePostMainPort(),
        review_port=review_port,
        review_required=True,
        repository=REPO,
        pr_number=PR_NUMBER,
        workflow_id=WORKFLOW_ID,
        workflow_name=WORKFLOW_NAME,
        job_id=JOB,
        task_id=TASK,
        attempt_id=ATTEMPT,
        session_id=SESSION,
        lease_id=lease_id,
        candidate_sha=CANDIDATE,
        branch=BRANCH,
        worktree=str(root),
        clock=lambda: NOW,
    )
    return store, lease_store, root, provider


def plan_from_bundle(bundle, *, refs, lease=None, version=10):
    """Consume the bundle exactly the way the production facade does."""
    verification = bundle.verification
    if verification.ok and VERIFY_REF in refs and verification.checkpoint_version is None:
        verification = type(verification)(
            task_id=verification.task_id,
            attempt_id=verification.attempt_id,
            ok=verification.ok,
            checkpoint_ref=verification.checkpoint_ref,
            mutation_version=verification.mutation_version,
            checkpoint_version=version,
        )
    fold_ref = (
        closeout_checkpoint_ref(
            CloseoutStage.FOLD,
            task_id=TASK,
            candidate_sha=CANDIDATE,
            merge_key=bundle.merge.merge_commit or "nomerge",
            fold_key="required",
        )
        if bundle.merge.required
        else None
    )
    fold_done = fold_ref is not None and fold_ref in refs
    from a_conductor.goal_closeout import GoalCloseoutFacts

    facts = GoalCloseoutFacts(
        job_id=JOB,
        task_id=TASK,
        attempt_id=ATTEMPT,
        state=TaskState.REVIEW_PENDING,
        version=version,
        verification=verification,
        blocking_findings=tuple(bundle.blocking_findings),
        continuity=bundle.continuity,
        current_candidate_sha=CANDIDATE,
        review=bundle.review,
        merge=bundle.merge,
        fold=FoldEvidence(
            requirement=bundle.fold_requirement,
            not_required_reason=bundle.fold_not_required_reason,
            completed=True if fold_done else None,
            bound_task_id=TASK if fold_done else None,
            bound_merge_commit=bundle.merge.merge_commit if fold_done else None,
        ),
        lease=lease or LeaseEvidence(lease_id=None, state=None, owner_ok=True),
        ownership=bundle.ownership,
        completed_closeout_refs=frozenset(refs),
    )
    return plan_goal_closeout(facts)


FULL_REFS = frozenset({VERIFY_REF, FOLD_REF, RELEASE_REF})


# ── A: exact fully-bound observation composes a consumable bundle ───────


def test_a_full_bound_observation_composes_exact_bundle(tmp_path):
    store, lease_store, root, provider = build(tmp_path)
    bundle = provider.evidence()
    assert isinstance(bundle, CloseoutEvidenceBundle)
    assert bundle.verification.ok is True
    assert bundle.verification.task_id == TASK
    assert bundle.verification.attempt_id == ATTEMPT
    assert bundle.verification.checkpoint_ref == VERIFY_REF
    assert bundle.continuity is ContinuityClassification.FRESH
    assert bundle.review.required is True
    assert bundle.review.passed is True
    assert bundle.review.reviewed_sha == CANDIDATE
    assert bundle.merge.required is True
    assert bundle.merge.merged is True
    assert bundle.merge.merge_commit == MERGE_COMMIT
    assert bundle.merge.accepted_candidate_sha == CANDIDATE
    assert bundle.merge.accepted_candidate_ancestor is True
    assert bundle.merge.post_main_required is True
    assert bundle.merge.post_main_run_id == RUN_ID
    assert bundle.merge.post_main_success is True
    assert bundle.merge.post_main_merge_commit == MERGE_COMMIT
    assert bundle.fold_requirement is FoldRequirement.REQUIRED
    assert bundle.fold_not_required_reason is None
    assert bundle.ownership.known is True
    assert bundle.ownership.conflicting is False
    assert bundle.ownership.transition_in_progress is False
    assert bundle.blocking_findings == ()
    plan = plan_from_bundle(bundle, refs=FULL_REFS)
    assert plan.decision is CloseoutDecision.COMPLETE_ALLOWED


# ── B: PR head != candidate -> typed fail closed, no bundle ─────────────


def test_b_pr_head_mismatch_fails_closed_typed(tmp_path):
    store, lease_store, root, provider = build(
        tmp_path, merge=FakeMergePort(green_merge(pr_head_sha=OTHER_SHA))
    )
    events_before = len(store.list_events(JOB))
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        provider.evidence()
    assert excinfo.value.code == "MERGE_CANDIDATE_MISMATCH"
    assert len(store.list_events(JOB)) == events_before


def test_b_pr_head_missing_rejected_at_dto_boundary(tmp_path):
    # an observed merge observation without a PR head can never exist:
    # the DTO itself rejects it before the provider composes anything
    with pytest.raises(ValueError):
        green_merge(pr_head_sha=None)


# ── C: merge unknown / not merged -> no fabricated merge success ────────


def test_c_merge_unknown_blocks_without_success(tmp_path):
    store, lease_store, root, provider = build(
        tmp_path,
        refs=(VERIFY_REF,),
        merge=FakeMergePort(green_merge(observed=True, merged=None, merge_commit_sha=None)),
    )
    bundle = provider.evidence()
    assert bundle.merge.merged is None
    plan = plan_from_bundle(bundle, refs={VERIFY_REF})
    assert plan.decision is CloseoutDecision.BLOCK
    assert plan.findings[0].code == "MERGE_NOT_MERGED"


def test_c_merge_not_merged_blocks(tmp_path):
    store, lease_store, root, provider = build(
        tmp_path,
        refs=(VERIFY_REF,),
        merge=FakeMergePort(green_merge(merged=False, merge_commit_sha=None)),
    )
    bundle = provider.evidence()
    assert bundle.merge.merged is False
    plan = plan_from_bundle(bundle, refs={VERIFY_REF})
    assert plan.decision is CloseoutDecision.BLOCK
    assert plan.findings[0].code == "MERGE_NOT_MERGED"


def test_c_merge_unobserved_blocks(tmp_path):
    store, lease_store, root, provider = build(
        tmp_path,
        refs=(VERIFY_REF,),
        merge=FakeMergePort(
            MergeObservation(
                observed=False, repository=REPO, pr_number=PR_NUMBER,
                merged=None, merge_commit_sha=None, pr_head_sha=None,
            )
        ),
    )
    bundle = provider.evidence()
    assert bundle.merge.merged is None
    assert bundle.merge.post_main_success is None
    # remote head is unobserved too: fail closed as recovery, never success
    plan = plan_from_bundle(bundle, refs={VERIFY_REF})
    assert plan.decision is CloseoutDecision.RECOVERY_REQUIRED


# ── D: candidate ancestry false/unknown -> fail closed ──────────────────


def test_d_ancestry_false_blocks(tmp_path):
    store, lease_store, root, provider = build(tmp_path, git=FakeGitObserver(ancestry=False))
    bundle = provider.evidence()
    assert bundle.merge.accepted_candidate_ancestor is False
    plan = plan_from_bundle(bundle, refs=FULL_REFS)
    assert plan.decision is CloseoutDecision.BLOCK
    assert plan.findings[0].code == "MERGE_ANCESTRY_MISMATCH"


def test_d_ancestry_unknown_blocks(tmp_path):
    store, lease_store, root, provider = build(tmp_path, git=FakeGitObserver(ancestry=None))
    bundle = provider.evidence()
    assert bundle.merge.accepted_candidate_ancestor is None
    plan = plan_from_bundle(bundle, refs=FULL_REFS)
    assert plan.findings[0].code == "MERGE_ANCESTRY_MISMATCH"


# ── E: post-main missing / pending / failed -> never success ────────────


def test_e_post_main_missing_blocks(tmp_path):
    store, lease_store, root, provider = build(
        tmp_path,
        post_main=FakePostMainPort(
            PostMainRunObservation(
                observed=False, repository=None, workflow_id=WORKFLOW_ID,
                workflow_name=None, run_id=None, run_head_sha=None,
                status=None, conclusion=None,
            )
        ),
    )
    bundle = provider.evidence()
    assert bundle.merge.post_main_run_id is None
    assert bundle.merge.post_main_success is None
    plan = plan_from_bundle(bundle, refs=FULL_REFS)
    assert plan.decision is CloseoutDecision.BLOCK
    assert plan.findings[0].code == "POST_MAIN_MISSING"


def test_e_post_main_pending_blocks(tmp_path):
    store, lease_store, root, provider = build(
        tmp_path,
        post_main=FakePostMainPort(green_run(status="in_progress", conclusion=None)),
    )
    bundle = provider.evidence()
    assert bundle.merge.post_main_run_id == RUN_ID
    assert bundle.merge.post_main_success is None
    plan = plan_from_bundle(bundle, refs=FULL_REFS)
    assert plan.findings[0].code == "POST_MAIN_PENDING"


def test_e_post_main_failed_blocks(tmp_path):
    store, lease_store, root, provider = build(
        tmp_path,
        post_main=FakePostMainPort(green_run(conclusion="FAILURE")),
    )
    bundle = provider.evidence()
    assert bundle.merge.post_main_success is False
    plan = plan_from_bundle(bundle, refs=FULL_REFS)
    assert plan.findings[0].code == "POST_MAIN_FAILED"


# ── F: post-main run head != merge commit -> typed fail closed ──────────


def test_f_post_main_head_mismatch_raises_typed(tmp_path):
    store, lease_store, root, provider = build(
        tmp_path, post_main=FakePostMainPort(green_run(run_head_sha=OTHER_SHA))
    )
    events_before = len(store.list_events(JOB))
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        provider.evidence()
    assert excinfo.value.code == "POST_MAIN_IDENTITY_MISMATCH"
    assert len(store.list_events(JOB)) == events_before


# ── G: repo / workflow identity mismatch -> fail closed ─────────────────


def test_g_merge_repo_mismatch_raises(tmp_path):
    store, lease_store, root, provider = build(
        tmp_path, merge=FakeMergePort(green_merge(repository="octocat/other-repo"))
    )
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        provider.evidence()
    assert excinfo.value.code == "MERGE_REPO_MISMATCH"


def test_g_merge_pr_number_mismatch_raises(tmp_path):
    store, lease_store, root, provider = build(
        tmp_path, merge=FakeMergePort(green_merge(pr_number=PR_NUMBER + 1))
    )
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        provider.evidence()
    assert excinfo.value.code == "MERGE_PR_MISMATCH"


def test_g_post_main_repo_mismatch_raises(tmp_path):
    store, lease_store, root, provider = build(
        tmp_path, post_main=FakePostMainPort(green_run(repository="octocat/other-repo"))
    )
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        provider.evidence()
    assert excinfo.value.code == "POST_MAIN_REPO_MISMATCH"


def test_g_post_main_workflow_id_mismatch_raises(tmp_path):
    store, lease_store, root, provider = build(
        tmp_path, post_main=FakePostMainPort(green_run(workflow_id=WORKFLOW_ID + 1))
    )
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        provider.evidence()
    assert excinfo.value.code == "POST_MAIN_WORKFLOW_IDENTITY_MISMATCH"


def test_g_post_main_workflow_name_mismatch_raises(tmp_path):
    store, lease_store, root, provider = build(
        tmp_path, post_main=FakePostMainPort(green_run(workflow_name="Other CI"))
    )
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        provider.evidence()
    assert excinfo.value.code == "POST_MAIN_WORKFLOW_IDENTITY_MISMATCH"


# ── H: checkpoint journal drift inside one evidence() ───────────────────


def test_h_journal_drift_during_observation_raises(tmp_path):
    store, lease_store, root, provider_holder = {}, {}, {}, {}

    def mutate_journal():
        add_ref(store["s"], "closeout:drift:mid-observation")

    store["s"], lease_store["s"], root["r"], provider_holder["p"] = build(
        tmp_path, merge=FakeMergePort(on_call=mutate_journal)
    )
    events_before = len(store["s"].list_events(JOB))
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        provider_holder["p"].evidence()
    assert excinfo.value.code == "CHECKPOINT_JOURNAL_DRIFT"
    # the mid-observation write itself is the only change; provider added none
    assert len(store["s"].list_events(JOB)) == events_before + 1


# ── I: local Git head/branch drift inside one evidence() ────────────────


def test_i_local_head_drift_during_observation_raises(tmp_path):
    git = FakeGitObserver(
        script=[
            LocalGitObservation(branch=BRANCH, head=CANDIDATE, dirty_state="CLEAN"),
            LocalGitObservation(branch=BRANCH, head=OTHER_SHA, dirty_state="CLEAN"),
        ]
    )
    store, lease_store, root, provider = build(tmp_path, git=git)
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        provider.evidence()
    assert excinfo.value.code == "LOCAL_GIT_DRIFT"


def test_i_local_branch_drift_during_observation_raises(tmp_path):
    git = FakeGitObserver(
        script=[
            LocalGitObservation(branch=BRANCH, head=CANDIDATE, dirty_state="CLEAN"),
            LocalGitObservation(branch="feat/other", head=CANDIDATE, dirty_state="CLEAN"),
        ]
    )
    store, lease_store, root, provider = build(tmp_path, git=git)
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        provider.evidence()
    assert excinfo.value.code == "LOCAL_GIT_DRIFT"


def test_i_wrong_branch_identity_fails_closed(tmp_path):
    store, lease_store, root, provider = build(tmp_path, git=FakeGitObserver(branch="feat/other"))
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        provider.evidence()
    assert excinfo.value.code == "LOCAL_BRANCH_MISMATCH"


def test_i_local_head_not_expected_classifies_head_drift(tmp_path):
    store, lease_store, root, provider = build(tmp_path, git=FakeGitObserver(head=OTHER_SHA))
    bundle = provider.evidence()
    assert bundle.continuity is ContinuityClassification.HEAD_DRIFT
    plan = plan_from_bundle(bundle, refs=FULL_REFS)
    assert plan.decision is CloseoutDecision.BLOCK
    assert plan.findings[0].code.startswith("CONTINUITY_")


# ── J: accepted review missing / non-ACCEPTED / stale head ──────────────


def test_j_review_missing_blocks_not_performed(tmp_path):
    store, lease_store, root, provider = build(tmp_path, review="missing")
    bundle = provider.evidence()
    assert bundle.review.passed is None
    plan = plan_from_bundle(bundle, refs=FULL_REFS)
    assert plan.decision is CloseoutDecision.BLOCK
    assert plan.findings[0].code == "REVIEW_NOT_PERFORMED"


def test_j_review_rejected_blocks_changes_required(tmp_path):
    store, lease_store, root, provider = build(
        tmp_path, review=AcceptedReviewObservation(reviewed_head=CANDIDATE, disposition="REJECTED")
    )
    bundle = provider.evidence()
    assert bundle.review.passed is False
    plan = plan_from_bundle(bundle, refs=FULL_REFS)
    assert plan.findings[0].code == "REVIEW_CHANGES_REQUIRED"


def test_j_review_stale_head_blocks(tmp_path):
    store, lease_store, root, provider = build(
        tmp_path, review=accepted_review(head=OTHER_SHA)
    )
    bundle = provider.evidence()
    assert bundle.review.passed is True
    assert bundle.review.reviewed_sha == OTHER_SHA
    plan = plan_from_bundle(bundle, refs=FULL_REFS)
    assert plan.findings[0].code == "STALE_REVIEW_SHA"


def test_j_review_port_failure_raises_typed(tmp_path):
    class ExplodingReviewPort:
        def observe_review(self):
            raise RuntimeError("boom")

    store, lease_store, root, provider = build(tmp_path, review="accepted")
    provider._review_port = ExplodingReviewPort()
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        provider.evidence()
    assert excinfo.value.code == "REVIEW_OBSERVATION_FAILED"


# ── K: fold completion derives only from the journal fold ref ───────────


def test_k_fold_complete_only_from_checkpoint_ref(tmp_path):
    store, lease_store, root, provider = build(tmp_path, refs=(VERIFY_REF, RELEASE_REF))
    bundle = provider.evidence()
    assert bundle.continuity is ContinuityClassification.MERGED_NOT_FOLDED
    plan = plan_from_bundle(bundle, refs={VERIFY_REF, RELEASE_REF})
    assert plan.decision is CloseoutDecision.FOLD_REQUIRED


def test_k_fold_ref_present_satisfies_fold_axis(tmp_path):
    store, lease_store, root, provider = build(tmp_path)  # FULL_REFS
    bundle = provider.evidence()
    assert bundle.continuity is ContinuityClassification.FRESH


def test_k_provider_writes_no_fold_record(tmp_path):
    store, lease_store, root, provider = build(tmp_path, refs=(VERIFY_REF,))
    events_before = tuple(store.list_events(JOB))
    provider.evidence()
    assert tuple(store.list_events(JOB)) == events_before


# ── L: canonical lease semantics stay accurate ──────────────────────────


def test_l_own_active_lease_blocks_release_axis(tmp_path):
    store, lease_store, root, provider = build(tmp_path, lease="active")
    bundle = provider.evidence()
    assert bundle.continuity is ContinuityClassification.MERGED_NOT_FOLDED
    plan = plan_from_bundle(
        bundle,
        refs={VERIFY_REF, FOLD_REF},
        lease=LeaseEvidence(lease_id=LEASE, state="ACTIVE", owner_ok=True),
    )
    assert plan.decision is CloseoutDecision.RELEASE_REQUIRED


def test_l_foreign_active_lease_conflict(tmp_path):
    store, lease_store, root, provider = build(tmp_path, foreign_lease=True)
    bundle = provider.evidence()
    assert bundle.continuity is ContinuityClassification.CLAIM_CONFLICT
    assert bundle.ownership.conflicting is True
    plan = plan_from_bundle(bundle, refs=FULL_REFS)
    assert plan.decision is CloseoutDecision.BLOCK


def test_l_missing_lease_ownership_unknown(tmp_path):
    store, lease_store, root, provider = build(tmp_path, lease="released")
    provider._lease_id = "lease-gone"  # canonical authority no longer knows it
    bundle = provider.evidence()
    assert bundle.ownership.known is False
    assert bundle.continuity is ContinuityClassification.UNKNOWN
    plan = plan_from_bundle(bundle, refs=FULL_REFS)
    assert plan.decision is CloseoutDecision.BLOCK
    assert plan.findings[0].code == "OWNERSHIP_UNKNOWN"


def test_l_no_lease_vacuously_released(tmp_path):
    store, lease_store, root, provider = build(tmp_path, lease="none", refs=(VERIFY_REF, FOLD_REF))
    bundle = provider.evidence()
    assert bundle.continuity is ContinuityClassification.FRESH
    plan = plan_from_bundle(
        bundle, refs={VERIFY_REF, FOLD_REF},
        lease=LeaseEvidence(lease_id=None, state=None, owner_ok=True),
    )
    assert plan.decision is CloseoutDecision.COMPLETE_ALLOWED


# ── M: malformed / oversized GitHub payloads -> bounded typed failure ───


def pr_payload(**over):
    base = {
        "merged": True,
        "merge_commit_sha": MERGE_COMMIT,
        "head": {"sha": CANDIDATE},
        "base": {"repo": {"full_name": REPO}},
    }
    base.update(over)
    return base


def runs_payload(runs, workflow_id=WORKFLOW_ID, **over):
    base = {"total_count": len(runs), "workflow_id": workflow_id, "runs": runs}
    base.update(over)
    return base


def run_entry(run_id=RUN_ID, head=MERGE_COMMIT, status="completed", conclusion="SUCCESS",
              workflow_id=WORKFLOW_ID, name=WORKFLOW_NAME, repo=REPO):
    return {
        "id": int(run_id),
        "head_sha": head,
        "status": status,
        "conclusion": conclusion,
        "workflow_id": workflow_id,
        "name": name,
        "repository": {"full_name": repo},
    }


def make_adapter(fetch, **over):
    base = dict(
        repository=REPO,
        pr_number=PR_NUMBER,
        workflow_id=WORKFLOW_ID,
        workflow_name=WORKFLOW_NAME,
        fetcher=fetch,
    )
    base.update(over)
    return BoundedGitHubObservationAdapter(**base)


def test_m_adapter_merge_oversized_payload(tmp_path):
    adapter = make_adapter(lambda url: "x" * (262144 + 1))
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        adapter.observe_merge()
    assert excinfo.value.code == "MERGE_PAYLOAD_TOO_LARGE"


def test_m_adapter_merge_malformed_json(tmp_path):
    adapter = make_adapter(lambda url: "{not json")
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        adapter.observe_merge()
    assert excinfo.value.code == "MERGE_PAYLOAD_INVALID"


def test_m_adapter_merge_duplicate_keys_rejected(tmp_path):
    raw = json.dumps(pr_payload())[:-1] + ', "merged": false}'
    adapter = make_adapter(lambda url: raw)
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        adapter.observe_merge()
    assert excinfo.value.code == "MERGE_PAYLOAD_INVALID"


def test_m_adapter_merge_repo_identity_mismatch(tmp_path):
    adapter = make_adapter(lambda url: json.dumps(pr_payload(base={"repo": {"full_name": "a/b"}})))
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        adapter.observe_merge()
    assert excinfo.value.code == "MERGE_REPO_MISMATCH"


def test_m_adapter_merge_bad_sha_rejected(tmp_path):
    adapter = make_adapter(lambda url: json.dumps(pr_payload(head={"sha": "nothex"})))
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        adapter.observe_merge()
    assert excinfo.value.code == "MERGE_IDENTITY_INVALID"


def test_m_adapter_merge_success(tmp_path):
    adapter = make_adapter(lambda url: json.dumps(pr_payload(merged=False, merge_commit_sha=None)))
    obs = adapter.observe_merge()
    assert obs.observed is True
    assert obs.repository == REPO
    assert obs.pr_number == PR_NUMBER
    assert obs.merged is False
    assert obs.merge_commit_sha is None
    assert obs.pr_head_sha == CANDIDATE


def test_m_adapter_runs_oversized(tmp_path):
    adapter = make_adapter(lambda url: "x" * (524288 + 1))
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        adapter.observe_post_main_run(MERGE_COMMIT)
    assert excinfo.value.code == "POST_MAIN_PAYLOAD_TOO_LARGE"


def test_m_adapter_runs_malformed(tmp_path):
    adapter = make_adapter(lambda url: "[]")
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        adapter.observe_post_main_run(MERGE_COMMIT)
    assert excinfo.value.code == "POST_MAIN_PAYLOAD_INVALID"


def test_m_adapter_runs_workflow_identity_mismatch(tmp_path):
    adapter = make_adapter(
        lambda url: json.dumps(runs_payload([run_entry()], workflow_id=WORKFLOW_ID + 1))
    )
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        adapter.observe_post_main_run(MERGE_COMMIT)
    assert excinfo.value.code == "POST_MAIN_WORKFLOW_IDENTITY_MISMATCH"


def test_m_adapter_runs_run_name_mismatch(tmp_path):
    adapter = make_adapter(
        lambda url: json.dumps(runs_payload([run_entry(name="Other")]))
    )
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        adapter.observe_post_main_run(MERGE_COMMIT)
    assert excinfo.value.code == "POST_MAIN_WORKFLOW_IDENTITY_MISMATCH"


def test_m_adapter_runs_malformed_head_sha(tmp_path):
    adapter = make_adapter(
        lambda url: json.dumps(runs_payload([run_entry(head="nothex")]))
    )
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        adapter.observe_post_main_run(MERGE_COMMIT)
    assert excinfo.value.code == "POST_MAIN_PAYLOAD_INVALID"


def test_m_adapter_runs_no_matching_head_observed_false(tmp_path):
    adapter = make_adapter(
        lambda url: json.dumps(runs_payload([run_entry(head=OTHER_SHA)]))
    )
    obs = adapter.observe_post_main_run(MERGE_COMMIT)
    assert obs.observed is False
    assert obs.run_id is None


def test_m_adapter_runs_newest_matching_head_wins(tmp_path):
    payload = runs_payload(
        [
            run_entry(run_id="111", head=MERGE_COMMIT, conclusion="SUCCESS"),
            run_entry(run_id="222", head=MERGE_COMMIT, conclusion="FAILURE"),
        ]
    )
    adapter = make_adapter(lambda url: json.dumps(payload))
    obs = adapter.observe_post_main_run(MERGE_COMMIT)
    assert obs.observed is True
    assert obs.run_id == "111"
    assert obs.conclusion == "SUCCESS"


# ── N: repeated identical observations deterministic, zero writes ───────


def test_n_repeated_observations_deterministic_and_write_nothing(tmp_path):
    store, lease_store, root, provider = build(tmp_path)
    git = provider._git_observer
    events_before = tuple(store.list_events(JOB))
    leases_before = lease_store.list_active()
    first = provider.evidence()
    second = provider.evidence()
    assert first == second
    assert tuple(store.list_events(JOB)) == events_before
    assert lease_store.list_active() == leases_before
    assert git.observe_calls == 4  # two pinned reads per evidence() call


# ── O: transport/fetcher exception -> typed failure, no partial bundle ──


def test_o_merge_transport_exception_typed(tmp_path):
    def explode(url):
        raise OSError("network down")

    adapter = make_adapter(explode)
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        adapter.observe_merge()
    assert excinfo.value.code == "MERGE_FETCH_FAILED"


def test_o_post_main_transport_exception_typed(tmp_path):
    def explode(url):
        raise TimeoutError("timeout")

    adapter = make_adapter(explode)
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        adapter.observe_post_main_run(MERGE_COMMIT)
    assert excinfo.value.code == "POST_MAIN_FETCH_FAILED"


def test_o_merge_port_exception_wraps_typed(tmp_path):
    class ExplodingPort:
        def observe_merge(self):
            raise RuntimeError("transport gone")

    store, lease_store, root, provider = build(tmp_path, merge=ExplodingPort())
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        provider.evidence()
    assert excinfo.value.code == "MERGE_OBSERVATION_FAILED"


def test_o_post_main_port_exception_wraps_typed(tmp_path):
    class ExplodingPort:
        def observe_post_main_run(self, merge_commit_sha):
            raise RuntimeError("transport gone")

    store, lease_store, root, provider = build(tmp_path, post_main=ExplodingPort())
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        provider.evidence()
    assert excinfo.value.code == "POST_MAIN_OBSERVATION_FAILED"


# ── P: pure planner/classifier modules keep zero network/egress ─────────


def test_p_no_network_in_planner_modules():
    source_dir = Path(a_conductor.__file__).parent
    for name in ("goal_closeout.py", "goal_closeout_assembly.py", "continuity_guard.py"):
        text = (source_dir / name).read_text(encoding="utf-8")
        for token in ("urlopen", "urllib", "socket", "requests", "http.client"):
            assert token not in text, f"{name} must not touch {token}"


def test_p_strict_git_observer_argv_read_only(monkeypatch, tmp_path):
    captured = []

    def fake_run(argv, **kwargs):
        captured.append(list(argv))
        arg = argv[-1] if argv[-1] != "HEAD" else ""
        if "rev-parse" in argv:
            if "--abbrev-ref" in argv:
                return subprocess.CompletedProcess(argv, 0, stdout=BRANCH, stderr="")
            return subprocess.CompletedProcess(argv, 0, stdout=CANDIDATE, stderr="")
        if "status" in argv:
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        if "cat-file" in argv:
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        if "merge-base" in argv:
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="")

    monkeypatch.setattr(
        "a_conductor.production_closeout_observation.subprocess.run", fake_run
    )
    observer = StrictLocalGitObserver(worktree=tmp_path)
    obs = observer.observe()
    assert obs.branch == BRANCH
    assert obs.head == CANDIDATE
    assert obs.dirty_state == "CLEAN"
    assert observer.candidate_is_ancestor(CANDIDATE, MERGE_COMMIT) is True
    assert captured, "observer must exercise the read-only argv surface"
    joined = [" ".join(argv) for argv in captured]
    for line in joined:
        for forbidden in (
            " push", " fetch", " checkout", " reset", " clean", " stash",
            " commit", " rebase", " pull", " clone", " gc", " worktree",
            " apply", " am", " cherry-pick",
        ):
            assert forbidden not in line, f"non-read-only git argv: {line}"


def test_p_strict_git_observer_rejects_malformed_sha(monkeypatch, tmp_path):
    called = []
    monkeypatch.setattr(
        "a_conductor.production_closeout_observation.subprocess.run",
        lambda argv, **kwargs: called.append(list(argv)) or subprocess.CompletedProcess(argv, 0, stdout="", stderr=""),
    )
    observer = StrictLocalGitObserver(worktree=tmp_path)
    assert observer.candidate_is_ancestor("nothex", MERGE_COMMIT) is None
    assert observer.candidate_is_ancestor(CANDIDATE, "also-bad") is None
    assert called == []


# ── DTO validation (matrix 13) ──────────────────────────────────────────


def test_dto_merge_observation_rejects_malformed():
    with pytest.raises(ValueError):
        MergeObservation(observed=True, repository="bad repo", pr_number=1,
                         merged=True, merge_commit_sha=MERGE_COMMIT, pr_head_sha=CANDIDATE)
    with pytest.raises(ValueError):
        MergeObservation(observed=True, repository=REPO, pr_number=0,
                         merged=True, merge_commit_sha=MERGE_COMMIT, pr_head_sha=CANDIDATE)
    with pytest.raises(ValueError):
        MergeObservation(observed=True, repository=REPO, pr_number=1,
                         merged=True, merge_commit_sha="zzz", pr_head_sha=CANDIDATE)
    with pytest.raises(ValueError):
        MergeObservation(observed=True, repository=REPO, pr_number=1,
                         merged=True, merge_commit_sha=MERGE_COMMIT, pr_head_sha=None)


def test_dto_post_main_observation_rejects_malformed():
    with pytest.raises(ValueError):
        PostMainRunObservation(observed=True, repository=REPO, workflow_id=0,
                               workflow_name=WORKFLOW_NAME, run_id=RUN_ID,
                               run_head_sha=MERGE_COMMIT, status="completed",
                               conclusion="SUCCESS")
    with pytest.raises(ValueError):
        PostMainRunObservation(observed=True, repository=REPO, workflow_id=WORKFLOW_ID,
                               workflow_name=WORKFLOW_NAME, run_id=RUN_ID,
                               run_head_sha="nope", status="completed",
                               conclusion="SUCCESS")
    with pytest.raises(ValueError):
        PostMainRunObservation(observed=True, repository=REPO, workflow_id=WORKFLOW_ID,
                               workflow_name=WORKFLOW_NAME, run_id=None,
                               run_head_sha=MERGE_COMMIT, status="completed",
                               conclusion="SUCCESS")
    with pytest.raises(ValueError):
        PostMainRunObservation(observed=True, repository=REPO, workflow_id=WORKFLOW_ID,
                               workflow_name=WORKFLOW_NAME, run_id=RUN_ID,
                               run_head_sha=MERGE_COMMIT, status="Completed!",
                               conclusion="SUCCESS")


def test_dto_accepted_review_rejects_malformed():
    with pytest.raises(ValueError):
        AcceptedReviewObservation(reviewed_head="nope", disposition="ACCEPTED")
    with pytest.raises(ValueError):
        AcceptedReviewObservation(reviewed_head=CANDIDATE, disposition="MAYBE")


def test_dto_local_git_rejects_malformed():
    with pytest.raises(ValueError):
        LocalGitObservation(branch=BRANCH, head=CANDIDATE, dirty_state="WET")
    with pytest.raises(ValueError):
        LocalGitObservation(branch="", head=CANDIDATE, dirty_state="CLEAN")


# ── provider configuration binding ──────────────────────────────────────


def test_provider_rejects_invalid_configuration(tmp_path):
    store, lease_store, root, provider = build(tmp_path)
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        ProductionCloseoutEvidenceProvider(
            job_store=store,
            lease_store=lease_store,
            git_observer=FakeGitObserver(),
            merge_port=FakeMergePort(),
            post_main_port=FakePostMainPort(),
            review_port=None,
            review_required=True,
            repository="bad repo",
            pr_number=PR_NUMBER,
            workflow_id=WORKFLOW_ID,
            workflow_name=WORKFLOW_NAME,
            job_id=JOB,
            task_id=TASK,
            attempt_id=ATTEMPT,
            session_id=SESSION,
            lease_id=LEASE,
            candidate_sha=CANDIDATE,
            branch=BRANCH,
            worktree=str(root),
            clock=lambda: NOW,
        )
    assert excinfo.value.code == "PROVIDER_CONFIG_INVALID"


def test_provider_review_required_without_port_invalid(tmp_path):
    store, lease_store, root, _ = build(tmp_path)
    with pytest.raises(ProductionCloseoutObservationError) as excinfo:
        ProductionCloseoutEvidenceProvider(
            job_store=store,
            lease_store=lease_store,
            git_observer=FakeGitObserver(),
            merge_port=FakeMergePort(),
            post_main_port=FakePostMainPort(),
            review_port=None,
            review_required=True,
            repository=REPO,
            pr_number=PR_NUMBER,
            workflow_id=WORKFLOW_ID,
            workflow_name=WORKFLOW_NAME,
            job_id=JOB,
            task_id=TASK,
            attempt_id=ATTEMPT,
            session_id=SESSION,
            lease_id=LEASE,
            candidate_sha=CANDIDATE,
            branch=BRANCH,
            worktree=str(root),
            clock=lambda: NOW,
        )
    assert excinfo.value.code == "PROVIDER_CONFIG_INVALID"


# ── E2E: provider composed through the real production facade ───────────


CW_ANCHOR = "<!-- HISTORICAL EVIDENCE — superseded by WO162 (2026-09-07).            -->"


def production_shaped_fixtures():
    cw = (
        "# A-Sunday Conductor — Current Work\n"
        "\n"
        "Last updated: 2026-09-18 (WO-P1-419 GOT-1b-B production evidence)\n"
        "\n"
        "- WO-P1-419 is the active closeout evidence lane.\n"
        "\n"
        + CW_ANCHOR + "\n"
        "<!-- Nothing below this separator is a current instruction.              -->\n"
        "\n"
        "## historical section\n"
        "old historical body\n"
    )
    ho = (
        "# HANDOFF — A-Sunday Conductor\n"
        "\n"
        "Last updated: 2026-09-18 — WO-P1-419\n"
        "\n"
        "- WO-P1-419 evidence provider lane active.\n"
        "\n"
        + CW_ANCHOR + "\n"
        "\n"
        "## historical handoff\n"
        "old handoff history\n"
    )
    co_wo166_row = (
        "| `WO-P1-166` P0-B Continuity Guard activation | GPT1 architecture/activation | "
        "FOLD_CANDIDATE / CONDITIONAL_RELEASE 2026-09-08 (self-closing) | Docs-only activation. |"
    )
    co = (
        "# A-Wiki Conductor — Agent Collaboration\n"
        "\n"
        "## In-progress claims\n"
        "\n"
        "| Chunk/WO | Agent | Claimed | Scope (files) |\n"
        "|---|---|---|---|\n"
        + co_wo166_row + "\n"
        "\n"
        "## Released claims history\n"
        "human history text\n"
    )
    return {"CURRENT-WORK.md": cw, "handoff.md": ho, "COLLAB.md": co}


def test_e2e_production_provider_drives_facade_fold_release_complete(tmp_path):
    from a_conductor.agent_change_packets import AgentChangeApplier
    from a_conductor.continuity_projection import CANONICAL_TARGETS
    from a_conductor.native_execution import NativeExecutionScope, NativeFileSystem

    store = make_job_store(tmp_path)
    lease_store = make_lease_store(tmp_path)
    root = tmp_path / "repo"
    root.mkdir(parents=True, exist_ok=True)
    fixtures = production_shaped_fixtures()
    for name in CANONICAL_TARGETS:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(fixtures[name], encoding="utf-8", newline="\n")
    drive_to_review_pending(store)
    make_lease(lease_store, root)

    class FoldTimeFreshProvider:
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

    provider = ProductionCloseoutEvidenceProvider(
        job_store=store,
        lease_store=lease_store,
        git_observer=FakeGitObserver(),
        merge_port=FakeMergePort(),
        post_main_port=FakePostMainPort(),
        review_port=FakeReviewPort(accepted_review()),
        review_required=True,
        repository=REPO,
        pr_number=PR_NUMBER,
        workflow_id=WORKFLOW_ID,
        workflow_name=WORKFLOW_NAME,
        job_id=JOB,
        task_id=TASK,
        attempt_id=ATTEMPT,
        session_id=SESSION,
        lease_id=LEASE,
        candidate_sha=CANDIDATE,
        branch=BRANCH,
        worktree=str(root),
        clock=lambda: NOW,
    )
    facade = assemble_goal_closeout_facade(
        job_store=store,
        lease_store=lease_store,
        applier=AgentChangeApplier(
            filesystem=NativeFileSystem(NativeExecutionScope(root=root, mutation_allowed=True)),
            lease_store=lease_store,
            continuity_provider=FoldTimeFreshProvider(),
            clock=lambda: NOW,
        ),
        evidence_provider=provider,
        job_id=JOB,
        task_id=TASK,
        attempt_id=ATTEMPT,
        session_id=SESSION,
        lease_id=LEASE,
        candidate_sha=CANDIDATE,
        branch=BRANCH,
        actual_head=CANDIDATE,
        clock=lambda: NOW,
    )

    r1 = facade.next_stage(JOB)
    assert r1.decision == "FOLD_REQUIRED"
    r2 = facade.next_stage(JOB)
    assert r2.decision == "RELEASE_REQUIRED"
    r3 = facade.next_stage(JOB)
    assert r3.decision == "COMPLETE_ALLOWED"
    assert store.get_job(JOB).state is TaskState.COMPLETE
    for name in CANONICAL_TARGETS:
        text = (root / name).read_text(encoding="utf-8")
        assert "<!-- BEGIN-MACHINE-PROJECTION -->" in text
    refs = completed_closeout_checkpoint_refs(store, JOB)
    assert FOLD_REF in refs
    assert RELEASE_REF in refs
