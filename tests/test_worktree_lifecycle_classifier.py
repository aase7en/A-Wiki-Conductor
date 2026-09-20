"""RED-first matrix + invariants for the WTL-1 pure lifecycle classifier."""

from __future__ import annotations

from dataclasses import replace

import pytest

from a_conductor.execution_record import ExecutionProcessState
from a_conductor.runtime_safety import ProcessObservation
from a_conductor.worktree_lifecycle import (
    WTL_CLASSIFIER_VERSION,
    WtlExecutionFact,
    WtlLifecycleState,
    WtlLeaseFact,
    WtlMergeFoldFact,
    WtlProcessFact,
    WtlReason,
    WtlReviewFreezeFact,
    WtlRemoteEvidence,
    WtlWorktreeFacts,
    classify_worktree_lifecycle,
    wtl_input_fingerprint,
)

HEAD_A = "0123456789abcdef0123456789abcdef01234567"
HEAD_B = "fedcba9876543210fedcba9876543210fedcba98"
WORKTREE = r"A:\repo\wt-a"
BRANCH = "feat/example"
OBSERVED_AT = "2026-09-20T06:00:00.000000Z"


def lease(state: str = "RELEASED", lease_id: str = "lease-1") -> WtlLeaseFact:
    return WtlLeaseFact(
        lease_id=lease_id,
        authority="worker_lease",
        owner_ref="session-1/task-1",
        state=state,
        worktree_key=WORKTREE,
    )


def owned_process(pid: int = 4242) -> WtlProcessFact:
    return WtlProcessFact(
        pid=pid,
        observation=ProcessObservation(
            pid_metadata_present=True,
            pid=pid,
            process_exists=True,
            executable_matches=True,
            profile_matches=True,
        ),
    )


def facts(**overrides) -> WtlWorktreeFacts:
    defaults: dict = {
        "worktree_path": WORKTREE,
        "worktree_key": WORKTREE,
        "repo_root": r"A:\repo",
        "branch": BRANCH,
        "detached": False,
        "head": HEAD_A,
        "head_recheck": HEAD_A,
        "protected_root": False,
        "tracked_dirty": False,
        "untracked_paths": (),
        "leases": (lease(),),
        "durable_executions": (),
        "process_observations": (),
        "review_freezes": (),
        "merge_fold": WtlMergeFoldFact(
            merged_into_canonical=True,
            fold_complete=True,
            release_complete=True,
            merge_commit=HEAD_B,
        ),
        "remote": WtlRemoteEvidence(
            open_pr=False,
            remote_branch_present=False,
            unmerged_commits=False,
        ),
        "durable_task_refs": ("task-1",),
        "observed_at": OBSERVED_AT,
        "input_fingerprint": "",
    }
    defaults.update(overrides)
    bundle = WtlWorktreeFacts(**defaults)
    return replace(bundle, input_fingerprint=wtl_input_fingerprint(bundle))


def classify(**overrides) -> object:
    return classify_worktree_lifecycle(facts(**overrides))


def reason_codes(verdict) -> tuple[str, ...]:
    return tuple(reason.code for reason in verdict.reasons)


# ---------------------------------------------------------------------------
# Matrix case 9: fully proven safe -> RELEASED_SAFE_TO_ARCHIVE
# ---------------------------------------------------------------------------


def test_matrix_9_fully_proven_safe_is_released_and_eligible() -> None:
    verdict = classify()
    assert verdict.state is WtlLifecycleState.RELEASED_SAFE_TO_ARCHIVE
    assert verdict.cleanup_eligible is True
    assert verdict.cleanup_eligible == (verdict.state is WtlLifecycleState.RELEASED_SAFE_TO_ARCHIVE)
    assert "RELEASE_PROVEN" in reason_codes(verdict)
    assert verdict.classified_head == HEAD_A
    assert verdict.worktree_key == r"a:\repo\wt-a"
    assert verdict.classifier_version == WTL_CLASSIFIER_VERSION
    assert verdict.classified_at == OBSERVED_AT
    assert verdict.input_fingerprint == wtl_input_fingerprint(facts())


# ---------------------------------------------------------------------------
# Matrix case 1: canonical dirty protected root -> DIRTY_PROTECTED
# ---------------------------------------------------------------------------


def test_matrix_1_canonical_dirty_root_is_dirty_protected_with_root_reason_first() -> None:
    verdict = classify(protected_root=True, tracked_dirty=True)
    assert verdict.state is WtlLifecycleState.DIRTY_PROTECTED
    assert verdict.cleanup_eligible is False
    codes = reason_codes(verdict)
    assert "PROTECTED_ROOT" in codes
    assert "TRACKED_DIRTY" in codes
    assert codes.index("PROTECTED_ROOT") < codes.index("TRACKED_DIRTY")


def test_clean_canonical_root_still_protected_and_never_eligible() -> None:
    verdict = classify(protected_root=True)
    assert verdict.state is WtlLifecycleState.DIRTY_PROTECTED
    assert verdict.cleanup_eligible is False
    assert "PROTECTED_ROOT" in reason_codes(verdict)


def test_unknown_protected_root_fact_fails_closed() -> None:
    verdict = classify(protected_root=None)
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "PROTECTED_ROOT_UNKNOWN" in reason_codes(verdict)


# ---------------------------------------------------------------------------
# Matrix case 2: tracked dirty -> DIRTY_PROTECTED
# ---------------------------------------------------------------------------


def test_matrix_2_tracked_dirty_is_dirty_protected() -> None:
    verdict = classify(tracked_dirty=True)
    assert verdict.state is WtlLifecycleState.DIRTY_PROTECTED
    assert verdict.cleanup_eligible is False
    assert "TRACKED_DIRTY" in reason_codes(verdict)


def test_dirty_state_unknown_fails_closed() -> None:
    verdict = classify(tracked_dirty=None)
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "DIRTY_STATE_UNKNOWN" in reason_codes(verdict)


# ---------------------------------------------------------------------------
# Matrix case 3: untracked bytes including .serena -> DIRTY_PROTECTED
# ---------------------------------------------------------------------------


def test_matrix_3_untracked_serena_bytes_are_dirty_protected() -> None:
    verdict = classify(untracked_paths=(".serena",))
    assert verdict.state is WtlLifecycleState.DIRTY_PROTECTED
    assert "UNTRACKED_BYTES_PRESENT" in reason_codes(verdict)


def test_untracked_state_unknown_fails_closed() -> None:
    verdict = classify(untracked_paths=None)
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "UNTRACKED_STATE_UNKNOWN" in reason_codes(verdict)


def test_untracked_observed_absent_stays_released() -> None:
    verdict = classify(untracked_paths=())
    assert verdict.state is WtlLifecycleState.RELEASED_SAFE_TO_ARCHIVE
    assert verdict.cleanup_eligible is True


# ---------------------------------------------------------------------------
# Matrix case 4: active lease -> ACTIVE_OWNED
# ---------------------------------------------------------------------------


def test_matrix_4_active_lease_is_active_owned() -> None:
    verdict = classify(leases=(lease(state="ACTIVE"),))
    assert verdict.state is WtlLifecycleState.ACTIVE_OWNED
    assert verdict.cleanup_eligible is False
    assert "ACTIVE_LEASE_OWNED" in reason_codes(verdict)


# ---------------------------------------------------------------------------
# Matrix case 5: conflicting leases -> CLAIM_CONFLICT
# ---------------------------------------------------------------------------


def test_matrix_5_conflicting_leases_are_claim_conflict() -> None:
    verdict = classify(
        leases=(
            lease(state="ACTIVE", lease_id="lease-a"),
            lease(state="ACTIVE", lease_id="lease-b"),
        )
    )
    assert verdict.state is WtlLifecycleState.CLAIM_CONFLICT
    assert verdict.cleanup_eligible is False
    assert "LEASE_OWNER_CONFLICT" in reason_codes(verdict)


def test_claim_conflict_outranks_active_owned() -> None:
    verdict = classify(
        leases=(
            lease(state="ACTIVE", lease_id="lease-a"),
            lease(state="QUARANTINED", lease_id="lease-b"),
        )
    )
    assert verdict.state is WtlLifecycleState.CLAIM_CONFLICT


def test_stale_lease_residue_fails_closed() -> None:
    verdict = classify(leases=(lease(state="STALE"),))
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "LEASE_RECONCILIATION_REQUIRED" in reason_codes(verdict)


def test_unknown_lease_state_fails_closed() -> None:
    verdict = classify(leases=(lease(state="UNKNOWN"),))
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "LEASE_STATE_UNKNOWN" in reason_codes(verdict)


def test_lease_evidence_unknown_fails_closed() -> None:
    verdict = classify(leases=None)
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "LEASE_EVIDENCE_UNKNOWN" in reason_codes(verdict)


def test_foreign_worktree_lease_binding_is_conflict_evidence() -> None:
    foreign = WtlLeaseFact(
        lease_id="lease-foreign",
        authority="worker_lease",
        owner_ref="session-2/task-2",
        state="ACTIVE",
        worktree_key=r"A:\repo\wt-b",
    )
    verdict = classify(leases=(lease(), foreign))
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "LEASE_BINDING_CONFLICT" in reason_codes(verdict)


# ---------------------------------------------------------------------------
# Matrix case 6: exact live process/execution -> PROCESS_OR_EXECUTION_ACTIVE
# ---------------------------------------------------------------------------


def test_matrix_6_exact_live_process_is_process_active() -> None:
    verdict = classify(process_observations=(owned_process(),))
    assert verdict.state is WtlLifecycleState.PROCESS_OR_EXECUTION_ACTIVE
    assert verdict.cleanup_eligible is False
    assert "LIVE_EXACT_PROCESS" in reason_codes(verdict)


def test_live_durable_execution_is_process_active() -> None:
    verdict = classify(
        durable_executions=(
            WtlExecutionFact("exec-1", ExecutionProcessState.RUNNING),
        )
    )
    assert verdict.state is WtlLifecycleState.PROCESS_OR_EXECUTION_ACTIVE
    assert "LIVE_DURABLE_EXECUTION" in reason_codes(verdict)


@pytest.mark.parametrize(
    "state",
    [
        ExecutionProcessState.QUEUED,
        ExecutionProcessState.STARTING,
        ExecutionProcessState.RUNNING,
        ExecutionProcessState.PROCESS_STILL_RUNNING,
    ],
)
def test_live_execution_states_protect(state: ExecutionProcessState) -> None:
    verdict = classify(durable_executions=(WtlExecutionFact("exec-1", state),))
    assert verdict.state is WtlLifecycleState.PROCESS_OR_EXECUTION_ACTIVE


@pytest.mark.parametrize(
    "state",
    [
        ExecutionProcessState.PROCESS_EXITED_UNKNOWN_RESULT,
        ExecutionProcessState.RECOVERY_REQUIRED,
        ExecutionProcessState.VERIFICATION_REQUIRED,
    ],
)
def test_unresolved_execution_outcome_fails_closed(state: ExecutionProcessState) -> None:
    verdict = classify(durable_executions=(WtlExecutionFact("exec-1", state),))
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "EXECUTION_OUTCOME_UNRESOLVED" in reason_codes(verdict)


@pytest.mark.parametrize(
    "state",
    [
        ExecutionProcessState.SUCCEEDED,
        ExecutionProcessState.FAILED,
        ExecutionProcessState.PARTIAL,
        ExecutionProcessState.CANCELLED,
    ],
)
def test_terminal_execution_states_do_not_protect(state: ExecutionProcessState) -> None:
    verdict = classify(durable_executions=(WtlExecutionFact("exec-1", state),))
    assert verdict.state is WtlLifecycleState.RELEASED_SAFE_TO_ARCHIVE


def test_execution_evidence_unknown_fails_closed() -> None:
    verdict = classify(durable_executions=None)
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "EXECUTION_EVIDENCE_UNKNOWN" in reason_codes(verdict)


def test_process_evidence_unknown_fails_closed() -> None:
    verdict = classify(process_observations=None)
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "PROCESS_EVIDENCE_UNKNOWN" in reason_codes(verdict)


# ---------------------------------------------------------------------------
# Matrix case 7: stale/unverified PID -> EVIDENCE_INCOMPLETE
# ---------------------------------------------------------------------------


def test_matrix_7_stale_pid_is_evidence_incomplete() -> None:
    stale = WtlProcessFact(
        pid=4242,
        observation=ProcessObservation(
            pid_metadata_present=True,
            pid=4242,
            process_exists=False,
            executable_matches=None,
            profile_matches=None,
        ),
    )
    verdict = classify(process_observations=(stale,))
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "PROCESS_IDENTITY_STALE" in reason_codes(verdict)


def test_pid_existence_alone_is_never_process_active() -> None:
    unverified = WtlProcessFact(
        pid=4242,
        observation=ProcessObservation(
            pid_metadata_present=True,
            pid=4242,
            process_exists=True,
            executable_matches=None,
            profile_matches=None,
        ),
    )
    verdict = classify(process_observations=(unverified,))
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "PROCESS_IDENTITY_UNKNOWN" in reason_codes(verdict)


def test_identity_mismatched_pid_is_evidence_incomplete() -> None:
    mismatch = WtlProcessFact(
        pid=4242,
        observation=ProcessObservation(
            pid_metadata_present=True,
            pid=4242,
            process_exists=True,
            executable_matches=False,
            profile_matches=True,
        ),
    )
    verdict = classify(process_observations=(mismatch,))
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "PROCESS_IDENTITY_MISMATCH" in reason_codes(verdict)


# ---------------------------------------------------------------------------
# Matrix case 8: merged but fold/release incomplete -> MERGED_NOT_FOLDED
# ---------------------------------------------------------------------------


def test_matrix_8_merged_but_fold_incomplete_is_merged_not_folded() -> None:
    verdict = classify(
        merge_fold=WtlMergeFoldFact(
            merged_into_canonical=True,
            fold_complete=False,
            release_complete=True,
            merge_commit=HEAD_B,
        )
    )
    assert verdict.state is WtlLifecycleState.MERGED_NOT_FOLDED
    assert verdict.cleanup_eligible is False
    assert "MERGED_FOLD_INCOMPLETE" in reason_codes(verdict)


def test_merged_but_release_incomplete_is_merged_not_folded() -> None:
    verdict = classify(
        merge_fold=WtlMergeFoldFact(
            merged_into_canonical=True,
            fold_complete=True,
            release_complete=False,
            merge_commit=HEAD_B,
        )
    )
    assert verdict.state is WtlLifecycleState.MERGED_NOT_FOLDED
    assert "MERGED_RELEASE_INCOMPLETE" in reason_codes(verdict)


# ---------------------------------------------------------------------------
# Matrix case 10: open PR / remote branch / unmerged -> REMOTE_UNMERGED
# ---------------------------------------------------------------------------


def test_matrix_10_open_pr_is_remote_unmerged() -> None:
    verdict = classify(remote=WtlRemoteEvidence(True, False, False))
    assert verdict.state is WtlLifecycleState.REMOTE_UNMERGED
    assert verdict.cleanup_eligible is False
    assert "OPEN_PR_PRESENT" in reason_codes(verdict)


def test_remote_branch_present_is_remote_unmerged() -> None:
    verdict = classify(remote=WtlRemoteEvidence(False, True, False))
    assert verdict.state is WtlLifecycleState.REMOTE_UNMERGED
    assert "REMOTE_BRANCH_PRESENT" in reason_codes(verdict)


def test_unmerged_commits_are_remote_unmerged() -> None:
    verdict = classify(remote=WtlRemoteEvidence(False, False, True))
    assert verdict.state is WtlLifecycleState.REMOTE_UNMERGED
    assert "UNMERGED_COMMITS_PRESENT" in reason_codes(verdict)


def test_observed_unmerged_ancestry_is_remote_unmerged() -> None:
    verdict = classify(
        merge_fold=WtlMergeFoldFact(
            merged_into_canonical=False,
            fold_complete=None,
            release_complete=None,
            merge_commit=None,
        )
    )
    assert verdict.state is WtlLifecycleState.REMOTE_UNMERGED
    assert "UNMERGED_COMMITS_PRESENT" in reason_codes(verdict)


def test_partial_remote_status_fails_closed() -> None:
    verdict = classify(remote=WtlRemoteEvidence(None, False, False))
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "OPEN_PR_STATUS_UNKNOWN" in reason_codes(verdict)


# ---------------------------------------------------------------------------
# Matrix case 11: detached exact review freeze -> REVIEW_FROZEN
# ---------------------------------------------------------------------------


def test_matrix_11_detached_exact_review_freeze_is_review_frozen() -> None:
    verdict = classify(
        branch=None,
        detached=True,
        review_freezes=(
            WtlReviewFreezeFact(
                review_ref="review-1",
                frozen_head=HEAD_A,
                worktree_key=WORKTREE,
            ),
        ),
    )
    assert verdict.state is WtlLifecycleState.REVIEW_FROZEN
    assert verdict.cleanup_eligible is False
    assert "REVIEW_FREEZE_EXACT" in reason_codes(verdict)


def test_review_freeze_for_other_head_is_conflict_evidence() -> None:
    verdict = classify(
        review_freezes=(
            WtlReviewFreezeFact(
                review_ref="review-1",
                frozen_head=HEAD_B,
                worktree_key=WORKTREE,
            ),
        )
    )
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "REVIEW_FREEZE_HEAD_CONFLICT" in reason_codes(verdict)


def test_review_freeze_bound_to_other_worktree_is_conflict_evidence() -> None:
    verdict = classify(
        review_freezes=(
            WtlReviewFreezeFact(
                review_ref="review-1",
                frozen_head=HEAD_A,
                worktree_key=r"A:\repo\wt-b",
            ),
        )
    )
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "REVIEW_FREEZE_BINDING_CONFLICT" in reason_codes(verdict)


# WO-P1-417 repair: UNKNOWN review-freeze evidence must fail closed. An
# unavailable/raising review-freeze collector yields review_freezes=None,
# which is unknown evidence — never observed absence — and must never let an
# otherwise fully proven release become RELEASED_SAFE_TO_ARCHIVE.


def test_review_evidence_unknown_fails_closed_not_released() -> None:
    verdict = classify(review_freezes=None)
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert verdict.cleanup_eligible is False
    codes = reason_codes(verdict)
    assert "REVIEW_EVIDENCE_UNKNOWN" in codes
    assert "RELEASE_PROVEN" not in codes


def test_unknown_review_freezes_distinguishable_from_observed_absent() -> None:
    unknown = classify(review_freezes=None)
    absent = classify(review_freezes=())
    assert unknown.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "REVIEW_EVIDENCE_UNKNOWN" in reason_codes(unknown)
    assert absent.state is WtlLifecycleState.RELEASED_SAFE_TO_ARCHIVE
    assert absent.cleanup_eligible is True


def test_review_evidence_unknown_keeps_incompleteness_rank_below_protective() -> None:
    verdict = classify(review_freezes=None, tracked_dirty=True)
    assert verdict.state is WtlLifecycleState.DIRTY_PROTECTED
    codes = reason_codes(verdict)
    assert "TRACKED_DIRTY" in codes
    assert "REVIEW_EVIDENCE_UNKNOWN" in codes
    assert codes.index("TRACKED_DIRTY") < codes.index("REVIEW_EVIDENCE_UNKNOWN")


# ---------------------------------------------------------------------------
# Matrix case 12: required fold/merge/remote evidence missing -> EVIDENCE_INCOMPLETE
# ---------------------------------------------------------------------------


def test_matrix_12_missing_merge_evidence_is_evidence_incomplete() -> None:
    verdict = classify(merge_fold=None)
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert verdict.cleanup_eligible is False
    assert "MERGE_EVIDENCE_MISSING" in reason_codes(verdict)


def test_missing_remote_evidence_is_evidence_incomplete() -> None:
    verdict = classify(remote=None)
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "REMOTE_EVIDENCE_MISSING" in reason_codes(verdict)


def test_unavailable_remote_port_is_never_safe() -> None:
    verdict = classify(remote=None, merge_fold=None)
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "REMOTE_EVIDENCE_MISSING" in reason_codes(verdict)


def test_unknown_merge_status_fails_closed() -> None:
    verdict = classify(
        merge_fold=WtlMergeFoldFact(
            merged_into_canonical=None,
            fold_complete=None,
            release_complete=None,
        )
    )
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "MERGE_STATUS_UNKNOWN" in reason_codes(verdict)


def test_merged_with_unknown_fold_status_fails_closed() -> None:
    verdict = classify(
        merge_fold=WtlMergeFoldFact(
            merged_into_canonical=True,
            fold_complete=None,
            release_complete=True,
            merge_commit=HEAD_B,
        )
    )
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "FOLD_STATUS_UNKNOWN" in reason_codes(verdict)


def test_merged_with_unknown_release_status_fails_closed() -> None:
    verdict = classify(
        merge_fold=WtlMergeFoldFact(
            merged_into_canonical=True,
            fold_complete=True,
            release_complete=None,
            merge_commit=HEAD_B,
        )
    )
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "RELEASE_STATUS_UNKNOWN" in reason_codes(verdict)


# ---------------------------------------------------------------------------
# Matrix case 13: no durable facts -> UNOWNED_UNKNOWN
# ---------------------------------------------------------------------------


def test_matrix_13_zero_durable_facts_is_unowned_unknown() -> None:
    verdict = classify(
        leases=(),
        merge_fold=None,
        remote=None,
        durable_task_refs=(),
    )
    assert verdict.state is WtlLifecycleState.UNOWNED_UNKNOWN
    assert verdict.cleanup_eligible is False
    assert "NO_DURABLE_LINKAGE" in reason_codes(verdict)


def test_zero_linkage_with_remote_port_unavailable_still_unowned() -> None:
    verdict = classify(leases=(), merge_fold=None, remote=None)
    assert verdict.state is WtlLifecycleState.UNOWNED_UNKNOWN


# ---------------------------------------------------------------------------
# Matrix case 14: HEAD changed since observation -> EVIDENCE_INCOMPLETE
# ---------------------------------------------------------------------------


def test_matrix_14_head_drift_is_evidence_incomplete() -> None:
    verdict = classify(head_recheck=HEAD_B)
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert verdict.cleanup_eligible is False
    assert "HEAD_DRIFT" in reason_codes(verdict)


def test_head_recheck_unknown_fails_closed() -> None:
    verdict = classify(head_recheck=None)
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "HEAD_RECHECK_UNKNOWN" in reason_codes(verdict)


def test_head_unknown_fails_closed() -> None:
    verdict = classify(head=None, head_recheck=None)
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "HEAD_UNKNOWN" in reason_codes(verdict)


# ---------------------------------------------------------------------------
# Matrix case 15: dirty + merged -> DIRTY_PROTECTED
# ---------------------------------------------------------------------------


def test_matrix_15_dirty_plus_merged_is_dirty_protected() -> None:
    verdict = classify(
        tracked_dirty=True,
        merge_fold=WtlMergeFoldFact(
            merged_into_canonical=True,
            fold_complete=False,
            release_complete=False,
            merge_commit=HEAD_B,
        ),
    )
    assert verdict.state is WtlLifecycleState.DIRTY_PROTECTED
    codes = reason_codes(verdict)
    assert "TRACKED_DIRTY" in codes
    assert "MERGED_FOLD_INCOMPLETE" in codes
    assert codes.index("TRACKED_DIRTY") < codes.index("MERGED_FOLD_INCOMPLETE")


# ---------------------------------------------------------------------------
# Matrix case 16: live process + released lease -> PROCESS_OR_EXECUTION_ACTIVE
# ---------------------------------------------------------------------------


def test_matrix_16_live_process_with_released_lease_is_process_active() -> None:
    verdict = classify(
        leases=(lease(state="RELEASED"),),
        process_observations=(owned_process(),),
    )
    assert verdict.state is WtlLifecycleState.PROCESS_OR_EXECUTION_ACTIVE
    assert verdict.cleanup_eligible is False
    assert reason_codes(verdict)[0] == "LIVE_EXACT_PROCESS"


# ---------------------------------------------------------------------------
# Core invariants
# ---------------------------------------------------------------------------


def test_invariant_cleanup_eligible_only_for_released_state() -> None:
    verdict = classify()
    assert verdict.cleanup_eligible is True
    for overrides in (
        {"tracked_dirty": True},
        {"leases": (lease(state="ACTIVE"),)},
        {"process_observations": (owned_process(),)},
        {"protected_root": True},
        {"head_recheck": HEAD_B},
    ):
        protective = classify(**overrides)
        assert protective.state is not WtlLifecycleState.RELEASED_SAFE_TO_ARCHIVE
        assert protective.cleanup_eligible is False


def test_invariant_fingerprint_mismatch_fails_closed() -> None:
    stamped = facts()
    tampered = replace(stamped, tracked_dirty=True)
    verdict = classify_worktree_lifecycle(tampered)
    assert verdict.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "INPUT_FINGERPRINT_MISMATCH" in reason_codes(verdict)


def test_invariant_fingerprint_is_deterministic_and_input_sensitive() -> None:
    first = facts()
    second = facts()
    assert wtl_input_fingerprint(first) == wtl_input_fingerprint(second)
    changed = facts(tracked_dirty=True)
    assert wtl_input_fingerprint(first) != wtl_input_fingerprint(changed)


def test_invariant_classification_is_pure_and_repeatable() -> None:
    bundle = facts()
    first = classify_worktree_lifecycle(bundle)
    second = classify_worktree_lifecycle(bundle)
    assert first == second


def test_invariant_protective_evidence_outranks_permissive_evidence() -> None:
    verdict = classify(
        protected_root=True,
        process_observations=(owned_process(),),
        leases=(lease(state="ACTIVE"),),
    )
    assert verdict.state in (
        WtlLifecycleState.DIRTY_PROTECTED,
        WtlLifecycleState.PROCESS_OR_EXECUTION_ACTIVE,
    )
    assert reason_codes(verdict)[0] == "PROTECTED_ROOT"


def test_invariant_live_process_outranks_dirty() -> None:
    verdict = classify(tracked_dirty=True, process_observations=(owned_process(),))
    assert verdict.state is WtlLifecycleState.PROCESS_OR_EXECUTION_ACTIVE


def test_invariant_evidence_refs_are_ordered_and_deduplicated() -> None:
    verdict = classify(
        durable_executions=(WtlExecutionFact("exec-1", ExecutionProcessState.SUCCEEDED),),
        durable_task_refs=("task-1", "task-2"),
    )
    assert verdict.evidence_refs == tuple(sorted(verdict.evidence_refs))
    assert len(set(verdict.evidence_refs)) == len(verdict.evidence_refs)
    assert "lease-1" in verdict.evidence_refs
    assert "exec-1" in verdict.evidence_refs
    assert "task-2" in verdict.evidence_refs
    assert HEAD_B in verdict.evidence_refs


def test_classification_rejects_cleanup_flag_inconsistency() -> None:
    from a_conductor.worktree_lifecycle import WtlClassification

    with pytest.raises(ValueError):
        WtlClassification(
            worktree_key=WORKTREE,
            classified_head=HEAD_A,
            state=WtlLifecycleState.DIRTY_PROTECTED,
            cleanup_eligible=True,
            reasons=(WtlReason("TRACKED_DIRTY"),),
            evidence_refs=(),
            classifier_version=WTL_CLASSIFIER_VERSION,
            classified_at=OBSERVED_AT,
            input_fingerprint="0" * 64,
        )


# ---------------------------------------------------------------------------
# DTO validation / unknown-vs-absent semantics
# ---------------------------------------------------------------------------


def test_facts_normalize_worktree_key_via_windows_seam() -> None:
    bundle = facts()
    assert bundle.worktree_key == r"a:\repo\wt-a"


def test_facts_reject_blank_worktree() -> None:
    with pytest.raises(ValueError):
        facts(worktree_path="   ", worktree_key="   ")


def test_facts_reject_invalid_head_shape() -> None:
    with pytest.raises(ValueError):
        facts(head="not-a-head")


def test_facts_reject_duplicate_lease_ids() -> None:
    with pytest.raises(ValueError):
        facts(leases=(lease(lease_id="dup"), lease(lease_id="dup")))


def test_facts_reject_invalid_lease_state() -> None:
    with pytest.raises(ValueError):
        lease(state="SOMETHING_ELSE")


def test_facts_reject_multiline_detail_text() -> None:
    with pytest.raises(ValueError):
        facts(observed_at="2026-09-20T06:00:00\nZ")


def test_reason_rejects_unknown_code() -> None:
    with pytest.raises(ValueError):
        WtlReason("NOT_A_REASON_CODE")


def test_classify_rejects_non_facts_input() -> None:
    with pytest.raises(ValueError):
        classify_worktree_lifecycle({"worktree": WORKTREE})  # type: ignore[arg-type]


def test_unknown_leases_distinguishable_from_observed_absent() -> None:
    unknown = classify(leases=None)
    absent = classify(leases=())
    assert unknown.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert "LEASE_EVIDENCE_UNKNOWN" in reason_codes(unknown)
    assert absent.state is WtlLifecycleState.RELEASED_SAFE_TO_ARCHIVE


def test_unknown_remote_distinguishable_from_observed_clear() -> None:
    unknown = classify(remote=None)
    clear = classify(remote=WtlRemoteEvidence(False, False, False))
    assert unknown.state is WtlLifecycleState.EVIDENCE_INCOMPLETE
    assert clear.state is WtlLifecycleState.RELEASED_SAFE_TO_ARCHIVE
