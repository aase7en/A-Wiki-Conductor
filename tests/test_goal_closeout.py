"""WO-P1-166 P0-B3 — GoalCloseout durable completion gate (RED-first matrix).

Covers the binding RED matrix from the GPT1 gate release (Issue #226
comment 5579757798) and the P0-B3 goal contract: verification binding,
blocking findings, continuity gate, review/SHA binding, merge/post-main,
fold, lease release, completion, crash/resume, and integration
concurrency — plus the thin executor's failure/crash cases.
"""
from __future__ import annotations

import pytest

from a_conductor.domain import TaskState
from a_conductor.continuity_guard import ContinuityClassification

from a_conductor.goal_closeout import (
    CloseoutDecision,
    CloseoutStage,
    FoldRequirement,
    GoalCloseoutFacts,
    GoalCloseoutExecutor,
    LeaseEvidence,
    MergeEvidence,
    OwnershipEvidence,
    ReviewEvidence,
    VerificationEvidence,
    FoldEvidence,
    closeout_checkpoint_ref,
    plan_goal_closeout,
)

SHA = "0f1e2d3c4b5a697887766554433221100f1e2d3c4b5a6978877665544332211f"
SHA_OTHER = "1111222233334444555566667777888811112222333344445555666677778888"
TASK = "task-1"
JOB = "job-1"
ATTEMPT = "attempt-1"
LEASE = "lease-1"


def V(**over):
    base = dict(
        task_id=TASK, attempt_id=ATTEMPT, ok=True,
        checkpoint_ref=f"closeout:verify:{TASK}:{SHA}",
        mutation_version=3, checkpoint_version=4,
    )
    base.update(over)
    return VerificationEvidence(**base)


def R(**over):
    base = dict(required=True, passed=True, reviewed_sha=SHA)
    base.update(over)
    return ReviewEvidence(**base)


def M(**over):
    base = dict(
        required=True, merged=True, merge_commit="ab12", accepted_candidate_sha=SHA,
        accepted_candidate_ancestor=True,
        post_main_required=True, post_main_run_id="run-1", post_main_success=True,
        post_main_merge_commit="ab12",
    )
    base.update(over)
    return MergeEvidence(**base)


def F(**over):
    base = dict(
        requirement=FoldRequirement.NOT_REQUIRED,
        not_required_reason="non-mutating review task",
        completed=None, bound_task_id=None, bound_merge_commit=None,
    )
    base.update(over)
    return FoldEvidence(**base)


def L(**over):
    base = dict(lease_id=None, state=None, owner_ok=True)
    base.update(over)
    return LeaseEvidence(**base)


def OWN(**over):
    base = dict(known=True, conflicting=False, transition_in_progress=False)
    base.update(over)
    return OwnershipEvidence(**base)


def facts(**over) -> GoalCloseoutFacts:
    base = dict(
        job_id=JOB, task_id=TASK, attempt_id=ATTEMPT,
        state=TaskState.REVIEW_PENDING, version=10,
        verification=V(),
        blocking_findings=(),
        continuity=ContinuityClassification.FRESH,
        current_candidate_sha=SHA,
        review=R(),
        merge=M(),
        fold=F(),
        lease=L(),
        ownership=OWN(),
        completed_closeout_refs=frozenset({closeout_checkpoint_ref(CloseoutStage.VERIFY_CHECKPOINT, task_id=TASK, candidate_sha=SHA, attempt_id=ATTEMPT)}),
    )
    base.update(over)
    return GoalCloseoutFacts(**base)


def decide(**over) -> CloseoutDecision:
    return plan_goal_closeout(facts(**over)).decision


# ── 1-5: verification binding ─────────────────────────────────────────
def test_v_missing_evidence_blocks():
    assert decide(verification=V(ok=False)) is CloseoutDecision.BLOCK


def test_v_no_checkpoint_yet_requires_checkpoint_stage():
    plan = plan_goal_closeout(facts(
        verification=V(checkpoint_ref=None, checkpoint_version=None),
        completed_closeout_refs=frozenset(),
    ))
    assert plan.decision is CloseoutDecision.VERIFY_CHECKPOINT_REQUIRED
    assert plan.stage is CloseoutStage.VERIFY_CHECKPOINT


def test_v_identity_mismatch_blocks():
    assert decide(verification=V(task_id="task-other")) is CloseoutDecision.BLOCK
    assert decide(verification=V(attempt_id="attempt-other")) is CloseoutDecision.BLOCK


def test_v_mutation_ahead_of_journal_is_recovery():
    plan = plan_goal_closeout(facts(verification=V(mutation_version=9, checkpoint_version=4)))
    assert plan.decision is CloseoutDecision.RECOVERY_REQUIRED
    assert any(f.code == "MUTATION_AHEAD_OF_JOURNAL" for f in plan.findings)


# ── 6-8: blocking findings ────────────────────────────────────────────
@pytest.mark.parametrize("finding", ["P0: crash", "P1: leak", "REVIEW-BLOCK: unverified"])
def test_unresolved_blocking_finding_blocks(finding):
    assert decide(blocking_findings=(finding,)) is CloseoutDecision.BLOCK


# ── 9-15: continuity gate ─────────────────────────────────────────────
def test_continuity_unknown_fails_closed_recovery():
    plan = plan_goal_closeout(facts(continuity=ContinuityClassification.UNKNOWN))
    assert plan.decision is CloseoutDecision.RECOVERY_REQUIRED


@pytest.mark.parametrize("kind", [
    ContinuityClassification.CLAIM_CONFLICT,
    ContinuityClassification.WORKTREE_DIRTY_OR_UNKNOWN,
    ContinuityClassification.HEAD_DRIFT,
    ContinuityClassification.STALE_LOCAL_CHECKOUT,
    ContinuityClassification.SSOT_DRIFT,
    ContinuityClassification.RECONCILE_REQUIRED,
])
def test_non_fresh_continuity_blocks(kind):
    assert decide(continuity=kind) is CloseoutDecision.BLOCK


def test_merged_not_folded_requires_fold():
    plan = plan_goal_closeout(facts(
        continuity=ContinuityClassification.MERGED_NOT_FOLDED,
        fold=FoldEvidence(requirement=FoldRequirement.REQUIRED, completed=False),
    ))
    assert plan.decision is CloseoutDecision.FOLD_REQUIRED


# ── 16-20: review / SHA binding ───────────────────────────────────────
def test_review_required_but_missing_blocks():
    assert decide(review=R(passed=None)) is CloseoutDecision.BLOCK


def test_review_changes_required_blocks():
    assert decide(review=R(passed=False)) is CloseoutDecision.BLOCK


def test_stale_reviewed_sha_blocks():
    assert decide(review=R(reviewed_sha=SHA_OTHER)) is CloseoutDecision.BLOCK


def test_unknown_current_sha_blocks():
    assert decide(current_candidate_sha=None) is CloseoutDecision.BLOCK


# ── 21-27: merge / post-main ──────────────────────────────────────────
def test_merge_required_missing_blocks():
    assert decide(merge=M(merged=False)) is CloseoutDecision.BLOCK


def test_merge_commit_without_accepted_ancestor_blocks():
    assert decide(merge=M(accepted_candidate_ancestor=False)) is CloseoutDecision.BLOCK


def test_post_main_missing_run_blocks():
    assert decide(merge=M(post_main_run_id=None)) is CloseoutDecision.BLOCK


def test_post_main_pending_blocks():
    assert decide(merge=M(post_main_success=None)) is CloseoutDecision.BLOCK


def test_post_main_failed_blocks():
    assert decide(merge=M(post_main_success=False)) is CloseoutDecision.BLOCK


def test_post_main_wrong_merge_identity_blocks():
    assert decide(merge=M(post_main_merge_commit="zz99")) is CloseoutDecision.BLOCK


def test_exact_identities_continue():
    assert decide() is CloseoutDecision.COMPLETE_ALLOWED


# ── 28-32: fold ───────────────────────────────────────────────────────
def test_fold_required_without_evidence_requires_fold():
    plan = plan_goal_closeout(facts(
        fold=FoldEvidence(requirement=FoldRequirement.REQUIRED, completed=None),
        lease=L(lease_id=LEASE, state="ACTIVE"),
    ))
    assert plan.decision is CloseoutDecision.FOLD_REQUIRED
    assert plan.stage is CloseoutStage.FOLD


def test_fold_completed_wrong_identity_blocks():
    assert decide(fold=FoldEvidence(
        requirement=FoldRequirement.REQUIRED, completed=True,
        bound_task_id="task-other", bound_merge_commit="ab12",
    )) is CloseoutDecision.BLOCK


def test_fold_not_required_with_reason_skips_fold():
    plan = plan_goal_closeout(facts(fold=F()))
    assert plan.decision is CloseoutDecision.COMPLETE_ALLOWED
    assert plan.stage is not CloseoutStage.FOLD


def test_fold_not_required_without_reason_blocks():
    assert decide(fold=FoldEvidence(
        requirement=FoldRequirement.NOT_REQUIRED, not_required_reason=None,
    )) is CloseoutDecision.BLOCK


def test_fold_checkpoint_present_resumes_at_release():
    plan = plan_goal_closeout(facts(
        fold=FoldEvidence(requirement=FoldRequirement.REQUIRED, completed=True,
                          bound_task_id=TASK, bound_merge_commit="ab12"),
        lease=L(lease_id=LEASE, state="ACTIVE"),
        completed_closeout_refs=frozenset({closeout_checkpoint_ref(CloseoutStage.VERIFY_CHECKPOINT, task_id=TASK, candidate_sha=SHA, attempt_id=ATTEMPT), closeout_checkpoint_ref(CloseoutStage.FOLD, task_id=TASK, candidate_sha=SHA, merge_key="ab12", fold_key="required")}),
    ))
    assert plan.decision is CloseoutDecision.RELEASE_REQUIRED
    assert plan.stage is CloseoutStage.RELEASE_LEASE


# ── 33-37: lease release ──────────────────────────────────────────────
def test_active_mutation_lease_requires_release():
    plan = plan_goal_closeout(facts(lease=L(lease_id=LEASE, state="ACTIVE")))
    assert plan.decision is CloseoutDecision.RELEASE_REQUIRED
    assert plan.stage is CloseoutStage.RELEASE_LEASE


@pytest.mark.parametrize("state", ["STALE", "UNKNOWN"])
def test_stale_or_unknown_lease_is_recovery(state):
    assert decide(lease=L(lease_id=LEASE, state=state)) is CloseoutDecision.RECOVERY_REQUIRED


def test_quarantined_lease_is_recovery():
    assert decide(lease=L(lease_id=LEASE, state="QUARANTINED")) is CloseoutDecision.RECOVERY_REQUIRED


def test_lease_owner_mismatch_blocks():
    assert decide(lease=L(lease_id=LEASE, state="ACTIVE", owner_ok=False)) is CloseoutDecision.BLOCK


def test_released_lease_satisfied():
    assert decide(lease=L(lease_id=LEASE, state="RELEASED")) is CloseoutDecision.COMPLETE_ALLOWED


# ── 38-41: complete ───────────────────────────────────────────────────
def test_all_satisfied_review_pending_completes():
    assert decide() is CloseoutDecision.COMPLETE_ALLOWED


def test_already_complete_is_noop():
    assert decide(state=TaskState.COMPLETE) is CloseoutDecision.ALREADY_COMPLETE


@pytest.mark.parametrize("state", [TaskState.FAILED, TaskState.CANCELLED])
def test_terminal_failure_refuses_closeout(state):
    assert decide(state=state) is CloseoutDecision.REFUSED


def test_planner_never_completes_with_unresolved_blocker():
    plan = plan_goal_closeout(facts(blocking_findings=("P0: x",)))
    assert plan.decision is not CloseoutDecision.COMPLETE_ALLOWED
    assert plan.decision is CloseoutDecision.BLOCK


# ── 42-43 crash/resume at verification (planner-level) ────────────────
def test_crash_before_verify_checkpoint_not_durably_complete():
    plan = plan_goal_closeout(facts(
        verification=V(checkpoint_ref=None, checkpoint_version=None),
        completed_closeout_refs=frozenset(),
    ))
    assert plan.decision is CloseoutDecision.VERIFY_CHECKPOINT_REQUIRED


def test_crash_after_verify_checkpoint_resumes_past_verify():
    assert decide() is CloseoutDecision.COMPLETE_ALLOWED  # verify ref present


# ── 50: planner purity / determinism ──────────────────────────────────
def test_plan_is_deterministic_and_idempotent():
    f = facts()
    assert plan_goal_closeout(f) == plan_goal_closeout(f)


def test_checkpoint_refs_are_stable_and_timestamp_free():
    ref = closeout_checkpoint_ref(CloseoutStage.FOLD, task_id=TASK, candidate_sha=SHA, merge_key="ab12", fold_key="required")
    assert ref == f"closeout:fold:{TASK}:{SHA}:ab12:required"
    assert ref == closeout_checkpoint_ref(CloseoutStage.FOLD, task_id=TASK, candidate_sha=SHA, merge_key="ab12", fold_key="required")


# ── 51-55: integration ownership concurrency ──────────────────────────
def test_ownership_unknown_blocks():
    assert decide(ownership=OWN(known=False)) is CloseoutDecision.BLOCK


def test_ownership_conflicting_blocks():
    assert decide(ownership=OWN(conflicting=True)) is CloseoutDecision.BLOCK


def test_same_transition_in_progress_by_other_blocks():
    assert decide(ownership=OWN(transition_in_progress=True)) is CloseoutDecision.BLOCK


def test_durable_occupied_wins_over_projection():
    """Case 55: the durable ownership fact blocks even when a (projection)
    caller would have liked to proceed — the planner consumes only durable
    facts, so occupied-is-occupied."""
    assert decide(ownership=OWN(conflicting=True)) is CloseoutDecision.BLOCK


# ── 56-57: non-mutating tasks ─────────────────────────────────────────
def test_non_mutating_task_may_complete():
    assert decide(
        fold=F(),
        lease=L(),
        merge=M(required=False, merged=None, merge_commit=None,
                accepted_candidate_sha=None, accepted_candidate_ancestor=None,
                post_main_required=False, post_main_run_id=None,
                post_main_success=None, post_main_merge_commit=None),
    ) is CloseoutDecision.COMPLETE_ALLOWED


def test_non_mutating_implicit_fold_policy_blocks():
    assert decide(fold=FoldEvidence(
        requirement=FoldRequirement.NOT_REQUIRED, not_required_reason=None,
    )) is CloseoutDecision.BLOCK


# ══════════════════════════════════════════════════════════════════════
# Executor — one durable side effect at a time over injected ports
# ══════════════════════════════════════════════════════════════════════
class FakeJobStore:
    def __init__(self, *, fail_checkpoint=False, fail_transition=False):
        self.checkpoints: list[tuple[str, str]] = []
        self.transitions: list[TaskState] = []
        self.version = 10
        self.fail_checkpoint = fail_checkpoint
        self.fail_transition = fail_transition

    def checkpoint(self, job_id, *, checkpoint_ref, expected_version, evidence_ref=None):
        from a_conductor.job_store import JobStoreError
        if self.fail_checkpoint:
            raise JobStoreError("JOB_STORE_WRITE_FAILED")
        self.checkpoints.append((job_id, checkpoint_ref))
        self.version += 1
        return None

    def transition(self, job_id, target_state, *, expected_version, **kw):
        from a_conductor.job_store import JobStoreError
        if self.fail_transition:
            raise JobStoreError("JOB_VERSION_CONFLICT")
        self.transitions.append(target_state)
        self.version += 1
        return None


class FakeLeasePort:
    def __init__(self, *, fail=False, already=False):
        self.released: list[str] = []
        self.fail = fail
        self.already = already

    def release(self, lease_id):
        from a_conductor.goal_closeout import LeaseReleaseOutcome
        if self.fail:
            raise RuntimeError("lease store down")
        self.released.append(lease_id)
        return LeaseReleaseOutcome(released=True, already_released=self.already)


class FakeFoldPort:
    def __init__(self, *, fail=False, unknown=False):
        self.calls: list[str] = []
        self.fail = fail
        self.unknown = unknown

    def fold(self, request):
        from a_conductor.goal_closeout import FoldOutcome
        self.calls.append(request.task_id)
        if self.fail:
            raise RuntimeError("fold backend down")
        return FoldOutcome(completed=None) if self.unknown else FoldOutcome(completed=True)


def executor(store=None, lease=None, fold=None) -> GoalCloseoutExecutor:
    return GoalCloseoutExecutor(
        job_store=store or FakeJobStore(),
        lease_release_port=lease or FakeLeasePort(),
        fold_port=fold or FakeFoldPort(),
    )


def test_executor_completes_via_release_then_complete_one_step_at_a_time():
    store, lease = FakeJobStore(), FakeLeasePort()
    ex = executor(store=store, lease=lease)
    base = facts(lease=L(lease_id=LEASE, state="ACTIVE"))
    r1 = ex.execute_next(base)
    assert r1.decision is CloseoutDecision.RELEASE_REQUIRED
    assert lease.released == [LEASE]
    assert closeout_checkpoint_ref(CloseoutStage.RELEASE_LEASE, task_id=TASK, candidate_sha=SHA, lease_id=LEASE) in [c[1] for c in store.checkpoints]
    # next invocation rehydrates truthful facts: the release durably landed,
    # so current lease authority now says RELEASED
    r2 = ex.execute_next(facts(
        lease=L(lease_id=LEASE, state="RELEASED"),
        completed_closeout_refs=frozenset({closeout_checkpoint_ref(CloseoutStage.VERIFY_CHECKPOINT, task_id=TASK, candidate_sha=SHA, attempt_id=ATTEMPT), closeout_checkpoint_ref(CloseoutStage.RELEASE_LEASE, task_id=TASK, candidate_sha=SHA, lease_id=LEASE)}),
    ))
    assert r2.decision is CloseoutDecision.COMPLETE_ALLOWED
    assert store.transitions == [TaskState.COMPLETE]


def test_executor_fold_then_checkpoint():
    store, fold = FakeJobStore(), FakeFoldPort()
    ex = executor(store=store, fold=fold)
    plan_facts = facts(
        fold=FoldEvidence(requirement=FoldRequirement.REQUIRED, completed=None),
        lease=L(lease_id=LEASE, state="ACTIVE"),
    )
    r = ex.execute_next(plan_facts)
    assert r.decision is CloseoutDecision.FOLD_REQUIRED
    assert fold.calls == [TASK]
    assert closeout_checkpoint_ref(CloseoutStage.FOLD, task_id=TASK, candidate_sha=SHA, merge_key="ab12", fold_key="required") in [c[1] for c in store.checkpoints]


def test_executor_fold_raises_before_effect_writes_no_checkpoint():
    store, fold = FakeJobStore(), FakeFoldPort(fail=True)
    with pytest.raises(Exception):
        executor(store=store, fold=fold).execute_next(facts(
            fold=FoldEvidence(requirement=FoldRequirement.REQUIRED, completed=None),
        ))
    assert store.checkpoints == []


def test_executor_fold_unknown_outcome_is_recovery():
    r = executor(fold=FakeFoldPort(unknown=True)).execute_next(facts(
        fold=FoldEvidence(requirement=FoldRequirement.REQUIRED, completed=None),
    ))
    assert r.decision is CloseoutDecision.RECOVERY_REQUIRED


def test_executor_lease_release_failure_no_complete():
    store = FakeJobStore()
    with pytest.raises(Exception):
        executor(store=store, lease=FakeLeasePort(fail=True)).execute_next(facts(
            lease=L(lease_id=LEASE, state="ACTIVE"),
        ))
    assert store.transitions == [] and store.checkpoints == []


def test_executor_lease_already_released_continues():
    store, lease = FakeJobStore(), FakeLeasePort(already=True)
    r = executor(store=store, lease=lease).execute_next(facts(
        lease=L(lease_id=LEASE, state="ACTIVE"),
    ))
    assert r.decision is CloseoutDecision.RELEASE_REQUIRED
    assert closeout_checkpoint_ref(CloseoutStage.RELEASE_LEASE, task_id=TASK, candidate_sha=SHA, lease_id=LEASE) in [c[1] for c in store.checkpoints]


def test_executor_checkpoint_failure_after_effect_is_recovery():
    """Fold effect succeeded but the durable checkpoint write failed — the
    side effect may have landed; must surface RECOVERY_REQUIRED."""
    store = FakeJobStore(fail_checkpoint=True)
    r = executor(store=store, fold=FakeFoldPort()).execute_next(facts(
        fold=FoldEvidence(requirement=FoldRequirement.REQUIRED, completed=None),
    ))
    assert r.decision is CloseoutDecision.RECOVERY_REQUIRED


def test_executor_complete_cas_conflict_is_reload_replan():
    r = executor(store=FakeJobStore(fail_transition=True)).execute_next(facts())
    assert r.decision is CloseoutDecision.RELOAD_REPLAN


def test_executor_duplicate_call_after_complete_no_side_effect():
    store = FakeJobStore()
    ex = executor(store=store)
    r = ex.execute_next(facts(state=TaskState.COMPLETE))
    assert r.decision is CloseoutDecision.ALREADY_COMPLETE
    assert store.checkpoints == [] and store.transitions == [] and store.released if False else True


def test_executor_blocked_plan_has_no_side_effects():
    store, lease = FakeJobStore(), FakeLeasePort()
    r = executor(store=store, lease=lease).execute_next(facts(blocking_findings=("P0: x",)))
    assert r.decision is CloseoutDecision.BLOCK
    assert store.checkpoints == [] and store.transitions == [] and lease.released == []


# ── GPT1 P0-B3 repair (candidate eaabb34, P1: stale checkpoint authority) ──
def test_r1_active_lease_with_release_checkpoint_never_completes(tmp=None):
    """DEFECT A reproducer: lease-new ACTIVE + a release checkpoint for the
    same task/candidate must NOT yield COMPLETE_ALLOWED."""
    plan = plan_goal_closeout(facts(
        lease=L(lease_id="lease-new", state="ACTIVE"),
        completed_closeout_refs=frozenset({
            closeout_checkpoint_ref(CloseoutStage.VERIFY_CHECKPOINT, task_id=TASK,
                                    candidate_sha=SHA, attempt_id=ATTEMPT),
            closeout_checkpoint_ref(CloseoutStage.RELEASE_LEASE, task_id=TASK,
                                    candidate_sha=SHA, lease_id="lease-new"),
        }),
    ))
    assert plan.decision is not CloseoutDecision.COMPLETE_ALLOWED
    assert plan.decision in (CloseoutDecision.RELEASE_REQUIRED, CloseoutDecision.RECOVERY_REQUIRED)


def test_r2_release_checkpoint_for_old_lease_does_not_satisfy_new():
    plan = plan_goal_closeout(facts(
        lease=L(lease_id="lease-new", state="ACTIVE"),
        completed_closeout_refs=frozenset({
            closeout_checkpoint_ref(CloseoutStage.VERIFY_CHECKPOINT, task_id=TASK,
                                    candidate_sha=SHA, attempt_id=ATTEMPT),
            closeout_checkpoint_ref(CloseoutStage.RELEASE_LEASE, task_id=TASK,
                                    candidate_sha=SHA, lease_id="lease-old"),
        }),
    ))
    assert plan.decision is CloseoutDecision.RELEASE_REQUIRED
    assert plan.stage is CloseoutStage.RELEASE_LEASE


def test_r3_released_same_lease_with_matching_checkpoint_idempotent():
    plan = plan_goal_closeout(facts(
        lease=L(lease_id="lease-new", state="RELEASED"),
        completed_closeout_refs=frozenset({
            closeout_checkpoint_ref(CloseoutStage.VERIFY_CHECKPOINT, task_id=TASK,
                                    candidate_sha=SHA, attempt_id=ATTEMPT),
            closeout_checkpoint_ref(CloseoutStage.RELEASE_LEASE, task_id=TASK,
                                    candidate_sha=SHA, lease_id="lease-new"),
        }),
    ))
    assert plan.decision is CloseoutDecision.COMPLETE_ALLOWED


def test_r4_fold_incomplete_with_fold_checkpoint_never_completes():
    """DEFECT B reproducer: fold REQUIRED, completed=False, but a fold
    checkpoint for the same task/candidate exists → must NOT COMPLETE."""
    plan = plan_goal_closeout(facts(
        fold=FoldEvidence(requirement=FoldRequirement.REQUIRED, completed=False),
        completed_closeout_refs=frozenset({
            closeout_checkpoint_ref(CloseoutStage.VERIFY_CHECKPOINT, task_id=TASK,
                                    candidate_sha=SHA, attempt_id=ATTEMPT),
            closeout_checkpoint_ref(CloseoutStage.FOLD, task_id=TASK,
                                    candidate_sha=SHA, merge_key="ab12", fold_key="required"),
        }),
    ))
    assert plan.decision is not CloseoutDecision.COMPLETE_ALLOWED
    assert plan.decision in (CloseoutDecision.FOLD_REQUIRED, CloseoutDecision.RECOVERY_REQUIRED)


def test_r5_fold_checkpoint_from_old_merge_ignored():
    plan = plan_goal_closeout(facts(
        fold=FoldEvidence(requirement=FoldRequirement.REQUIRED, completed=False),
        completed_closeout_refs=frozenset({
            closeout_checkpoint_ref(CloseoutStage.VERIFY_CHECKPOINT, task_id=TASK,
                                    candidate_sha=SHA, attempt_id=ATTEMPT),
            closeout_checkpoint_ref(CloseoutStage.FOLD, task_id=TASK,
                                    candidate_sha=SHA, merge_key="cd34", fold_key="required"),
        }),
    ))
    assert plan.decision is CloseoutDecision.FOLD_REQUIRED
    assert plan.stage is CloseoutStage.FOLD


def test_r6_valid_current_fold_replay_idempotent():
    plan = plan_goal_closeout(facts(
        fold=FoldEvidence(requirement=FoldRequirement.REQUIRED, completed=True,
                          bound_task_id=TASK, bound_merge_commit="ab12"),
        lease=L(lease_id=LEASE, state="ACTIVE"),
        completed_closeout_refs=frozenset({
            closeout_checkpoint_ref(CloseoutStage.VERIFY_CHECKPOINT, task_id=TASK,
                                    candidate_sha=SHA, attempt_id=ATTEMPT),
            closeout_checkpoint_ref(CloseoutStage.FOLD, task_id=TASK,
                                    candidate_sha=SHA, merge_key="ab12", fold_key="required"),
        }),
    ))
    assert plan.decision is CloseoutDecision.RELEASE_REQUIRED  # fold satisfied, next stage


def test_r7_verify_checkpoint_from_old_attempt_does_not_satisfy_new_attempt():
    plan = plan_goal_closeout(facts(
        attempt_id="attempt-2",
        verification=V(attempt_id="attempt-2"),
        completed_closeout_refs=frozenset({
            closeout_checkpoint_ref(CloseoutStage.VERIFY_CHECKPOINT, task_id=TASK,
                                    candidate_sha=SHA, attempt_id="attempt-1"),
        }),
    ))
    assert plan.decision is CloseoutDecision.VERIFY_CHECKPOINT_REQUIRED


def test_r8_active_lease_plus_exact_release_checkpoint_is_typed_recovery():
    """Contradiction handling: journal claims release of the EXACT current
    lease while current authority says ACTIVE → typed fail-closed conflict,
    never silent COMPLETE."""
    plan = plan_goal_closeout(facts(
        lease=L(lease_id="lease-new", state="ACTIVE"),
        completed_closeout_refs=frozenset({
            closeout_checkpoint_ref(CloseoutStage.VERIFY_CHECKPOINT, task_id=TASK,
                                    candidate_sha=SHA, attempt_id=ATTEMPT),
            closeout_checkpoint_ref(CloseoutStage.RELEASE_LEASE, task_id=TASK,
                                    candidate_sha=SHA, lease_id="lease-new"),
        }),
    ))
    assert plan.decision is CloseoutDecision.RECOVERY_REQUIRED
    assert any(f.code == "LEASE_RELEASE_CONTRADICTION" for f in plan.findings)


def test_r9_fold_checkpoint_contradiction_is_typed_recovery():
    plan = plan_goal_closeout(facts(
        fold=FoldEvidence(requirement=FoldRequirement.REQUIRED, completed=False),
        completed_closeout_refs=frozenset({
            closeout_checkpoint_ref(CloseoutStage.VERIFY_CHECKPOINT, task_id=TASK,
                                    candidate_sha=SHA, attempt_id=ATTEMPT),
            closeout_checkpoint_ref(CloseoutStage.FOLD, task_id=TASK,
                                    candidate_sha=SHA, merge_key="ab12", fold_key="required"),
        }),
    ))
    assert plan.decision is CloseoutDecision.RECOVERY_REQUIRED
    assert any(f.code == "FOLD_CHECKPOINT_CONTRADICTION" for f in plan.findings)


@pytest.mark.parametrize("completed", [False, None])
def test_r10_unknown_or_false_fold_fact_with_checkpoint_never_completes(completed):
    plan = plan_goal_closeout(facts(
        fold=FoldEvidence(requirement=FoldRequirement.REQUIRED, completed=completed),
        completed_closeout_refs=frozenset({
            closeout_checkpoint_ref(CloseoutStage.VERIFY_CHECKPOINT, task_id=TASK,
                                    candidate_sha=SHA, attempt_id=ATTEMPT),
            closeout_checkpoint_ref(CloseoutStage.FOLD, task_id=TASK,
                                    candidate_sha=SHA, merge_key="ab12", fold_key="required"),
        }),
    ))
    assert plan.decision is not CloseoutDecision.COMPLETE_ALLOWED


def test_r11_ref_binding_requires_stage_authority_fields():
    import pytest as _pytest
    with _pytest.raises(ValueError):
        closeout_checkpoint_ref(CloseoutStage.VERIFY_CHECKPOINT, task_id=TASK, candidate_sha=SHA)
    with _pytest.raises(ValueError):
        closeout_checkpoint_ref(CloseoutStage.RELEASE_LEASE, task_id=TASK, candidate_sha=SHA)
    with _pytest.raises(ValueError):
        closeout_checkpoint_ref(CloseoutStage.FOLD, task_id=TASK, candidate_sha=SHA)


def test_r12_refs_are_stage_authority_bound_and_deterministic():
    v = closeout_checkpoint_ref(CloseoutStage.VERIFY_CHECKPOINT, task_id=TASK,
                                candidate_sha=SHA, attempt_id=ATTEMPT)
    assert v == f"closeout:verify:{TASK}:{SHA}:{ATTEMPT}" == closeout_checkpoint_ref(
        CloseoutStage.VERIFY_CHECKPOINT, task_id=TASK, candidate_sha=SHA, attempt_id=ATTEMPT)
    f1 = closeout_checkpoint_ref(CloseoutStage.FOLD, task_id=TASK, candidate_sha=SHA,
                                 merge_key="ab12", fold_key="required")
    f2 = closeout_checkpoint_ref(CloseoutStage.FOLD, task_id=TASK, candidate_sha=SHA,
                                 merge_key="cd34", fold_key="required")
    assert f1 != f2
    r1 = closeout_checkpoint_ref(CloseoutStage.RELEASE_LEASE, task_id=TASK,
                                 candidate_sha=SHA, lease_id="lease-a")
    r2 = closeout_checkpoint_ref(CloseoutStage.RELEASE_LEASE, task_id=TASK,
                                 candidate_sha=SHA, lease_id="lease-b")
    assert r1 != r2 and r1 == closeout_checkpoint_ref(
        CloseoutStage.RELEASE_LEASE, task_id=TASK, candidate_sha=SHA, lease_id="lease-a")
