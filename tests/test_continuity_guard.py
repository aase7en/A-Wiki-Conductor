from __future__ import annotations

import pytest

from a_conductor.continuity_guard import (
    ContinuityClassification,
    ContinuityFinding,
    ContinuitySnapshot,
    ContinuityVerdict,
    JobFact,
    LeaseFact,
    MergeFoldFact,
    ProjectionClaim,
    ReconciliationAction,
    REASON_CODES,
    classify_continuity,
)
from a_conductor.domain import RecoveryClassification, TaskState

HEAD_A = "0123456789abcdef0123456789abcdef01234567"
HEAD_B = "fedcba9876543210fedcba9876543210fedcba98"
WORKTREE = r"A:\repo\wt-a"
BRANCH = "feat/example"
SESSION = "session-1"
TASK = "task-1"
SCOPE = ("src/a_conductor/*", "tests/*")


def own_lease(state: str = "ACTIVE") -> LeaseFact:
    return LeaseFact(
        lease_id="lease-own",
        session_id=SESSION,
        task_id=TASK,
        worktree_key=WORKTREE,
        branch=BRANCH,
        mutable_scope=SCOPE,
        state=state,
    )


def foreign_lease(
    *,
    lease_id: str = "lease-foreign",
    state: str = "ACTIVE",
    worktree_key: str = WORKTREE,
    mutable_scope: tuple[str, ...] = SCOPE,
) -> LeaseFact:
    return LeaseFact(
        lease_id=lease_id,
        session_id="session-other",
        task_id="task-other",
        worktree_key=worktree_key,
        branch="feat/other",
        mutable_scope=mutable_scope,
        state=state,
    )


def snapshot(**overrides) -> ContinuitySnapshot:
    defaults: dict = {
        "worktree": WORKTREE,
        "branch": BRANCH,
        "session_id": SESSION,
        "task_id": TASK,
        "expected_head": HEAD_A,
        "local_head": HEAD_A,
        "remote_head": HEAD_A,
        "dirty_state": "CLEAN",
        "ownership_known": True,
        "mutable_scope": SCOPE,
        "leases": (),
        "job": None,
        "merge_fold": None,
        "projections": (),
    }
    defaults.update(overrides)
    return ContinuitySnapshot(**defaults)


# ---------------------------------------------------------------------------
# Matrix case 1: complete compatible clean snapshot -> FRESH / safe
# ---------------------------------------------------------------------------


def test_fresh_snapshot_classifies_fresh_and_safe() -> None:
    verdict = classify_continuity(snapshot())
    assert verdict.classification is ContinuityClassification.FRESH
    assert verdict.safe_to_mutate is True
    assert verdict.findings == ()
    assert verdict.reconciliation_actions == ()


def test_fresh_with_own_active_lease_and_consistent_projection() -> None:
    verdict = classify_continuity(
        snapshot(
            leases=(own_lease(),),
            job=JobFact(job_id="job-1", state=TaskState.EXECUTING),
            merge_fold=MergeFoldFact(
                merge_commit=HEAD_B, fold_complete=True, release_complete=True
            ),
            projections=(
                ProjectionClaim(
                    source="CURRENT-WORK.md",
                    asserted_head=HEAD_A,
                    asserted_branch=BRANCH,
                    asserted_active_lease_ids=("lease-own",),
                ),
            ),
        )
    )
    assert verdict.classification is ContinuityClassification.FRESH
    assert verdict.safe_to_mutate is True


# ---------------------------------------------------------------------------
# Matrix cases 2 + 3: missing critical factual fields -> UNKNOWN / unsafe
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "missing_field",
    ["expected_head", "local_head", "remote_head"],
)
def test_missing_critical_head_fails_closed_as_unknown(missing_field: str) -> None:
    verdict = classify_continuity(snapshot(**{missing_field: None}))
    assert verdict.classification is ContinuityClassification.UNKNOWN
    assert verdict.safe_to_mutate is False
    assert ReconciliationAction.RECOVER_MISSING_FACTS in verdict.reconciliation_actions


def test_missing_job_state_fails_closed_as_unknown() -> None:
    verdict = classify_continuity(
        snapshot(job=JobFact(job_id="job-1", state=None))
    )
    assert verdict.classification is ContinuityClassification.UNKNOWN
    assert verdict.safe_to_mutate is False


# ---------------------------------------------------------------------------
# Matrix cases 4 + 5: head mismatch family
# ---------------------------------------------------------------------------


def test_local_head_differs_from_expected_is_head_drift() -> None:
    verdict = classify_continuity(
        snapshot(expected_head=HEAD_A, local_head=HEAD_B, remote_head=HEAD_B)
    )
    assert verdict.classification is ContinuityClassification.HEAD_DRIFT
    assert verdict.safe_to_mutate is False
    assert verdict.findings[0].reason_code == "LOCAL_HEAD_NOT_EXPECTED"
    assert ReconciliationAction.REALIGN_TO_EXPECTED_HEAD in verdict.reconciliation_actions


def test_local_checkout_behind_remote_is_stale_local_checkout() -> None:
    verdict = classify_continuity(
        snapshot(expected_head=HEAD_A, local_head=HEAD_A, remote_head=HEAD_B)
    )
    assert verdict.classification is ContinuityClassification.STALE_LOCAL_CHECKOUT
    assert verdict.safe_to_mutate is False
    assert verdict.findings[0].reason_code == "LOCAL_HEAD_NOT_REMOTE"
    assert (
        ReconciliationAction.UPDATE_FROM_AUTHORITATIVE_REMOTE
        in verdict.reconciliation_actions
    )


def test_all_three_heads_differ_reports_both_head_findings_deterministically() -> None:
    verdict = classify_continuity(
        snapshot(expected_head=HEAD_A, local_head=HEAD_B, remote_head="ab" * 20)
    )
    kinds = tuple(finding.kind for finding in verdict.findings)
    assert kinds == (
        ContinuityClassification.HEAD_DRIFT,
        ContinuityClassification.STALE_LOCAL_CHECKOUT,
    )
    assert verdict.classification is ContinuityClassification.HEAD_DRIFT


# ---------------------------------------------------------------------------
# Matrix cases 6 + 7 (+ 16): worktree dirty / unknown family
# ---------------------------------------------------------------------------


def test_dirty_worktree_blocks_mutation() -> None:
    verdict = classify_continuity(snapshot(dirty_state="DIRTY"))
    assert verdict.classification is ContinuityClassification.WORKTREE_DIRTY_OR_UNKNOWN
    assert verdict.safe_to_mutate is False
    assert verdict.findings[0].reason_code == "WORKTREE_DIRTY"
    assert (
        ReconciliationAction.RECONCILE_WORKTREE_STATE in verdict.reconciliation_actions
    )


def test_unknown_dirty_state_blocks_mutation() -> None:
    verdict = classify_continuity(snapshot(dirty_state="UNKNOWN"))
    assert verdict.classification is ContinuityClassification.WORKTREE_DIRTY_OR_UNKNOWN
    assert verdict.findings[0].reason_code == "DIRTY_STATE_UNKNOWN"


def test_missing_dirty_state_never_degrades_to_clean() -> None:
    verdict = classify_continuity(snapshot(dirty_state=None))
    assert verdict.classification is ContinuityClassification.WORKTREE_DIRTY_OR_UNKNOWN
    assert verdict.safe_to_mutate is False
    assert verdict.findings[0].reason_code == "DIRTY_STATE_UNKNOWN"


def test_unknown_ownership_blocks_even_when_dirty_state_is_clean() -> None:
    verdict = classify_continuity(snapshot(dirty_state="CLEAN", ownership_known=False))
    assert verdict.classification is ContinuityClassification.WORKTREE_DIRTY_OR_UNKNOWN
    assert verdict.findings[0].reason_code == "OWNERSHIP_UNKNOWN"


# ---------------------------------------------------------------------------
# Matrix cases 8 + 9: claim conflicts
# ---------------------------------------------------------------------------


def test_foreign_active_lease_on_same_worktree_is_claim_conflict() -> None:
    verdict = classify_continuity(snapshot(leases=(foreign_lease(),)))
    assert verdict.classification is ContinuityClassification.CLAIM_CONFLICT
    assert verdict.safe_to_mutate is False
    assert verdict.findings[0].reason_code == "LEASE_OWNER_CONFLICT"
    assert "lease-foreign" in verdict.findings[0].detail
    assert (
        ReconciliationAction.RESOLVE_CLAIM_CONFLICT in verdict.reconciliation_actions
    )


def test_foreign_active_lease_with_overlapping_scope_is_claim_conflict() -> None:
    verdict = classify_continuity(
        snapshot(
            leases=(
                foreign_lease(worktree_key=r"A:\repo\wt-b", mutable_scope=SCOPE),
            )
        )
    )
    assert verdict.classification is ContinuityClassification.CLAIM_CONFLICT
    assert verdict.findings[0].reason_code == "MUTABLE_SCOPE_OVERLAP"


def test_own_active_lease_is_not_a_conflict() -> None:
    verdict = classify_continuity(snapshot(leases=(own_lease(),)))
    assert verdict.classification is ContinuityClassification.FRESH
    assert verdict.safe_to_mutate is True


def test_released_foreign_lease_does_not_conflict() -> None:
    verdict = classify_continuity(snapshot(leases=(foreign_lease(state="RELEASED"),)))
    assert verdict.classification is ContinuityClassification.FRESH


def test_foreign_active_lease_elsewhere_without_overlap_does_not_conflict() -> None:
    verdict = classify_continuity(
        snapshot(
            leases=(
                foreign_lease(
                    worktree_key=r"A:\repo\wt-b",
                    mutable_scope=("docs/other/*",),
                ),
            )
        )
    )
    assert verdict.classification is ContinuityClassification.FRESH


def test_stale_fencing_lease_requires_reconciliation() -> None:
    verdict = classify_continuity(snapshot(leases=(foreign_lease(state="STALE"),)))
    assert verdict.classification is ContinuityClassification.RECONCILE_REQUIRED
    assert verdict.safe_to_mutate is False
    assert verdict.findings[0].reason_code == "LEASE_RECONCILIATION_REQUIRED"
    assert (
        ReconciliationAction.RUN_DETERMINISTIC_RECONCILIATION
        in verdict.reconciliation_actions
    )


def test_quarantined_fencing_lease_requires_reconciliation() -> None:
    verdict = classify_continuity(
        snapshot(leases=(foreign_lease(state="QUARANTINED"),))
    )
    assert verdict.classification is ContinuityClassification.RECONCILE_REQUIRED


def test_own_stale_lease_requires_reconciliation() -> None:
    verdict = classify_continuity(snapshot(leases=(own_lease(state="STALE"),)))
    assert verdict.classification is ContinuityClassification.RECONCILE_REQUIRED


def test_unknown_state_fencing_lease_fails_closed_as_unknown() -> None:
    verdict = classify_continuity(snapshot(leases=(foreign_lease(state="UNKNOWN"),)))
    assert verdict.classification is ContinuityClassification.UNKNOWN
    assert verdict.safe_to_mutate is False
    assert verdict.findings[0].reason_code == "LEASE_STATE_UNKNOWN"


def test_terminal_job_is_claim_conflict() -> None:
    verdict = classify_continuity(
        snapshot(job=JobFact(job_id="job-1", state=TaskState.COMPLETE))
    )
    assert verdict.classification is ContinuityClassification.CLAIM_CONFLICT
    assert verdict.findings[0].reason_code == "JOB_TERMINAL"


# ---------------------------------------------------------------------------
# Matrix case 10: SSOT drift
# ---------------------------------------------------------------------------


def test_projection_head_contradiction_is_ssot_drift() -> None:
    verdict = classify_continuity(
        snapshot(
            projections=(
                ProjectionClaim(source="handoff.md", asserted_head=HEAD_B),
            )
        )
    )
    assert verdict.classification is ContinuityClassification.SSOT_DRIFT
    assert verdict.safe_to_mutate is False
    assert (
        verdict.findings[0].reason_code == "PROJECTION_HEAD_CONTRADICTS_FACTS"
    )
    assert ReconciliationAction.REFRESH_PROJECTION in verdict.reconciliation_actions


def test_projection_branch_contradiction_is_ssot_drift() -> None:
    verdict = classify_continuity(
        snapshot(
            projections=(
                ProjectionClaim(source="handoff.md", asserted_branch="feat/other"),
            )
        )
    )
    assert verdict.classification is ContinuityClassification.SSOT_DRIFT
    assert verdict.findings[0].reason_code == "PROJECTION_BRANCH_CONTRADICTS_FACTS"


def test_projection_active_claims_matching_facts_stay_fresh() -> None:
    verdict = classify_continuity(
        snapshot(
            leases=(own_lease(), foreign_lease(state="RELEASED")),
            projections=(
                ProjectionClaim(
                    source="COLLAB.md", asserted_active_lease_ids=("lease-own",)
                ),
            ),
        )
    )
    # Facts show only lease-own active and the projection asserts exactly that.
    assert verdict.classification is ContinuityClassification.FRESH


def test_projection_missing_active_claim_is_ssot_drift() -> None:
    verdict = classify_continuity(
        snapshot(
            leases=(own_lease(),),
            projections=(
                ProjectionClaim(source="COLLAB.md", asserted_active_lease_ids=()),
            ),
        )
    )
    assert verdict.classification is ContinuityClassification.SSOT_DRIFT
    assert verdict.findings[0].reason_code == "PROJECTION_CLAIMS_CONTRADICTS_FACTS"


def test_projection_claiming_inactive_lease_is_ssot_drift() -> None:
    verdict = classify_continuity(
        snapshot(
            projections=(
                ProjectionClaim(
                    source="CURRENT-WORK.md", asserted_active_lease_ids=("lease-x",)
                ),
            ),
        )
    )
    assert verdict.classification is ContinuityClassification.SSOT_DRIFT
    assert verdict.findings[0].reason_code == "PROJECTION_CLAIMS_CONTRADICTS_FACTS"


# ---------------------------------------------------------------------------
# Matrix case 11 (+ 16): merged but not folded
# ---------------------------------------------------------------------------


def test_merge_with_incomplete_fold_is_merged_not_folded() -> None:
    verdict = classify_continuity(
        snapshot(
            merge_fold=MergeFoldFact(
                merge_commit=HEAD_B, fold_complete=False, release_complete=True
            )
        )
    )
    assert verdict.classification is ContinuityClassification.MERGED_NOT_FOLDED
    assert verdict.safe_to_mutate is False
    assert verdict.findings[0].reason_code == "FOLD_NOT_COMPLETE"
    assert ReconciliationAction.COMPLETE_MERGE_FOLD in verdict.reconciliation_actions


def test_merge_with_unknown_fold_status_never_degrades_to_folded() -> None:
    verdict = classify_continuity(
        snapshot(
            merge_fold=MergeFoldFact(
                merge_commit=HEAD_B, fold_complete=None, release_complete=True
            )
        )
    )
    assert verdict.classification is ContinuityClassification.MERGED_NOT_FOLDED
    assert verdict.findings[0].reason_code == "FOLD_STATUS_UNKNOWN"


def test_merge_with_incomplete_release_is_merged_not_folded() -> None:
    verdict = classify_continuity(
        snapshot(
            merge_fold=MergeFoldFact(
                merge_commit=HEAD_B, fold_complete=True, release_complete=False
            )
        )
    )
    assert verdict.classification is ContinuityClassification.MERGED_NOT_FOLDED
    assert verdict.findings[0].reason_code == "RELEASE_NOT_COMPLETE"


def test_merge_with_unknown_release_status_never_degrades_to_released() -> None:
    verdict = classify_continuity(
        snapshot(
            merge_fold=MergeFoldFact(
                merge_commit=HEAD_B, fold_complete=True, release_complete=None
            )
        )
    )
    assert verdict.classification is ContinuityClassification.MERGED_NOT_FOLDED
    assert verdict.findings[0].reason_code == "RELEASE_STATUS_UNKNOWN"


def test_fully_folded_merge_introduces_no_finding() -> None:
    verdict = classify_continuity(
        snapshot(
            merge_fold=MergeFoldFact(
                merge_commit=HEAD_B, fold_complete=True, release_complete=True
            )
        )
    )
    assert verdict.classification is ContinuityClassification.FRESH


# ---------------------------------------------------------------------------
# Matrix case 12: deterministic reconciliation required before mutation
# ---------------------------------------------------------------------------


def test_recovery_needed_job_requires_reconciliation() -> None:
    verdict = classify_continuity(
        snapshot(
            job=JobFact(
                job_id="job-1",
                state=TaskState.RECOVERY_NEEDED,
                recovery_classification=RecoveryClassification.UNKNOWN,
            )
        )
    )
    assert verdict.classification is ContinuityClassification.RECONCILE_REQUIRED
    assert verdict.safe_to_mutate is False
    assert verdict.findings[0].reason_code == "RECOVERY_TRANSITION_REQUIRED"


# ---------------------------------------------------------------------------
# Matrix cases 13-15: ordering, determinism, idempotence
# ---------------------------------------------------------------------------


def test_multiple_defects_return_stable_ordered_findings_and_primary() -> None:
    verdict = classify_continuity(
        snapshot(
            expected_head=HEAD_A,
            local_head=HEAD_B,
            remote_head=HEAD_B,
            dirty_state="DIRTY",
            projections=(ProjectionClaim(source="handoff.md", asserted_head=HEAD_A),),
        )
    )
    kinds = tuple(finding.kind for finding in verdict.findings)
    assert kinds == (
        ContinuityClassification.HEAD_DRIFT,
        ContinuityClassification.WORKTREE_DIRTY_OR_UNKNOWN,
        ContinuityClassification.SSOT_DRIFT,
    )
    assert verdict.classification is ContinuityClassification.HEAD_DRIFT
    assert verdict.safe_to_mutate is False
    assert verdict.reconciliation_actions == (
        ReconciliationAction.REALIGN_TO_EXPECTED_HEAD,
        ReconciliationAction.RECONCILE_WORKTREE_STATE,
        ReconciliationAction.REFRESH_PROJECTION,
    )


def test_unknown_outranks_other_simultaneous_defects() -> None:
    verdict = classify_continuity(snapshot(local_head=None, dirty_state="DIRTY"))
    assert verdict.classification is ContinuityClassification.UNKNOWN
    kinds = tuple(finding.kind for finding in verdict.findings)
    assert kinds == (
        ContinuityClassification.UNKNOWN,
        ContinuityClassification.WORKTREE_DIRTY_OR_UNKNOWN,
    )


def test_input_ordering_does_not_change_semantic_result() -> None:
    leases = (
        foreign_lease(lease_id="lease-b"),
        own_lease(),
        foreign_lease(lease_id="lease-a", state="STALE", worktree_key=r"A:\repo\wt-c"),
    )
    projections = (
        ProjectionClaim(source="a-handoff.md", asserted_head=HEAD_B),
        ProjectionClaim(source="b-collab.md", asserted_branch="feat/other"),
    )
    forward = classify_continuity(
        snapshot(leases=leases, projections=projections)
    )
    reversed_input = classify_continuity(
        snapshot(leases=tuple(reversed(leases)), projections=tuple(reversed(projections)))
    )
    assert forward == reversed_input
    assert forward.classification is ContinuityClassification.CLAIM_CONFLICT


def test_repeated_evaluation_is_idempotent() -> None:
    subject = snapshot(
        leases=(foreign_lease(),),
        projections=(ProjectionClaim(source="handoff.md", asserted_head=HEAD_B),),
    )
    first = classify_continuity(subject)
    second = classify_continuity(subject)
    third = classify_continuity(
        snapshot(
            leases=(foreign_lease(),),
            projections=(ProjectionClaim(source="handoff.md", asserted_head=HEAD_B),),
        )
    )
    assert first == second == third


def test_every_non_fresh_classification_denies_mutation() -> None:
    representatives: dict[ContinuityClassification, ContinuitySnapshot] = {
        ContinuityClassification.UNKNOWN: snapshot(local_head=None),
        ContinuityClassification.CLAIM_CONFLICT: snapshot(
            leases=(foreign_lease(),)
        ),
        ContinuityClassification.HEAD_DRIFT: snapshot(local_head=HEAD_B),
        ContinuityClassification.STALE_LOCAL_CHECKOUT: snapshot(remote_head=HEAD_B),
        ContinuityClassification.WORKTREE_DIRTY_OR_UNKNOWN: snapshot(
            dirty_state="DIRTY"
        ),
        ContinuityClassification.MERGED_NOT_FOLDED: snapshot(
            merge_fold=MergeFoldFact(merge_commit=HEAD_B)
        ),
        ContinuityClassification.RECONCILE_REQUIRED: snapshot(
            leases=(foreign_lease(state="STALE"),)
        ),
        ContinuityClassification.SSOT_DRIFT: snapshot(
            projections=(ProjectionClaim(source="handoff.md", asserted_head=HEAD_B),)
        ),
    }
    for expected_classification, subject in representatives.items():
        verdict = classify_continuity(subject)
        assert verdict.classification is expected_classification, expected_classification
        assert verdict.safe_to_mutate is False, expected_classification
        assert verdict.reconciliation_actions, expected_classification


def test_reason_codes_come_from_bounded_vocabulary() -> None:
    representatives = (
        snapshot(local_head=None, dirty_state="DIRTY", leases=(foreign_lease(),)),
        snapshot(
            local_head=HEAD_B,
            remote_head="ab" * 20,
            leases=(foreign_lease(state="STALE"),),
            job=JobFact(job_id="job-1", state=None),
            merge_fold=MergeFoldFact(merge_commit=HEAD_B),
            projections=(ProjectionClaim(source="handoff.md", asserted_head=HEAD_A)),
        ),
    )
    for subject in representatives:
        for finding in classify_continuity(subject).findings:
            assert finding.reason_code in REASON_CODES
            assert isinstance(finding, ContinuityFinding)


# ---------------------------------------------------------------------------
# Adversarial: malformed construction fails at the boundary
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        {"worktree": "  "},
        {"branch": ""},
        {"session_id": "not-a-session\n"},
        {"task_id": None},
        {"expected_head": "zzz"},
        {"local_head": "0123"},
        {"remote_head": "g" * 40},
        {"dirty_state": "SOMETIMES"},
        {"ownership_known": "yes"},
        {"mutable_scope": ("ok/*", "ok/*")},
        {"mutable_scope": ("",)},
        {"leases": (foreign_lease(state="PAUSED"),)},
        {"leases": (foreign_lease(lease_id=" "),)},
        {"job": JobFact(job_id=" ", state=TaskState.READY)},
        {"job": JobFact(job_id="job-1", state="EXECUTING")},
        {"merge_fold": MergeFoldFact(merge_commit="nothex")},
        {"merge_fold": MergeFoldFact(merge_commit=HEAD_B, fold_complete="yes")},
        {"projections": (ProjectionClaim(source=""),)},
        {"projections": (ProjectionClaim(source="s", asserted_head="xyz"),)},
        {"projections": (ProjectionClaim(source="s", asserted_active_lease_ids=("",)),)},
    ],
)
def test_malformed_snapshot_inputs_are_rejected(overrides: dict) -> None:
    with pytest.raises(ValueError):
        snapshot(**overrides)


def test_classify_rejects_non_snapshot_input() -> None:
    with pytest.raises(ValueError):
        classify_continuity("not-a-snapshot")  # type: ignore[arg-type]


def test_verdict_is_frozen_and_hashable_value_object() -> None:
    verdict = classify_continuity(snapshot())
    assert isinstance(verdict, ContinuityVerdict)
    with pytest.raises(Exception):
        verdict.safe_to_mutate = False  # type: ignore[misc]
