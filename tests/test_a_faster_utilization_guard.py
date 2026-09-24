"""WO-P1-517 — pure deterministic A-Faster utilization classifier tests.

Pins the utilization-enforcement contract of
``src/a_conductor/a_faster_utilization_guard.py``:

- ``FANOUT_TARGET`` / ``UNUSED_SAFE_CAPACITY`` /
  ``A_FASTER_UNDERUTILIZED`` / ``AUTO_REFILL_REQUIRED`` semantics;
- the ``A_FASTER_ACTIVE`` receipt tasking-vs-explanation boundary;
- typed blockers, including
  ``SOL_DIRECT_LONG_LABOR_WHILE_GLM_CAPACITY_IDLE`` when eligible GLM
  capacity is idle while Sol performs GLM-eligible direct long labor;
- no manufactured work and no quota burning (the classifier is pure,
  launches nothing, probes nothing);
- the three WO-P1-517 bootstrap lessons as delegation launch
  preconditions and the structured-admission-evidence rule.

The classifier is a projection only: it must never become a scheduler,
task store, claim/lease, provider, dispatch, review, merge, or completion
authority.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from a_conductor.a_faster_utilization_guard import (
    AFasterActivation,
    BLOCKER_ACTIVATION_EXPLANATION_ONLY,
    BLOCKER_A_FASTER_NOT_ACTIVE,
    BLOCKER_GLM_ROUTE_BLOCKED,
    BLOCKER_NO_INDEPENDENT_READY_WORK,
    BLOCKER_QUOTA_EXHAUSTED,
    BLOCKER_QUOTA_UNKNOWN,
    BLOCKER_SECRET_SOURCE_UNAVAILABLE,
    BLOCKER_SOL_DIRECT_LONG_LABOR_WHILE_GLM_CAPACITY_IDLE,
    DELEGATION_LAUNCH_PRECONDITIONS,
    DEFAULT_MUTABLE_LANES,
    DEFAULT_REVIEW_LANES,
    QuotaAdmission,
    UtilizationFacts,
    classify_utilization,
    parse_quota_admission,
)

MODULE_PATH = Path(importlib.util.find_spec("a_conductor.a_faster_utilization_guard").origin)


def _admitted_facts(**overrides) -> UtilizationFacts:
    """Facts with an active receipt and admitted GLM capacity."""
    defaults = dict(
        activation=AFasterActivation.ACTIVE,
        occupied_mutable_lanes=1,
        occupied_review_lanes=0,
        ready_mutable_candidates=1,
        ready_review_candidates=1,
        glm_quota_admission=QuotaAdmission.QUOTA_AVAILABLE,
        glm_route_ready=True,
    )
    defaults.update(overrides)
    return UtilizationFacts(**defaults)


# --- activation receipt: tasking vs explanation -------------------------


def test_activation_receipt_enum_uses_stable_codes() -> None:
    assert AFasterActivation.ACTIVE.value == "A_FASTER_ACTIVE"
    assert AFasterActivation.EXPLANATION_ONLY.value == "A_FASTER_EXPLANATION_ONLY"
    assert AFasterActivation.NOT_INVOKED.value == "A_FASTER_NOT_INVOKED"


def test_active_idle_capacity_with_ready_work_requires_auto_refill() -> None:
    verdict = classify_utilization(_admitted_facts(ready_mutable_candidates=5))
    # 3 - 1 = 2 free mutable slots (5 candidates), review slot free with 1
    # candidate: fanout = 2 mutable + 1 review, all fillable capacity counted.
    assert verdict.fanout_target_mutable == 2
    assert verdict.fanout_target_review == 1
    assert verdict.fanout_target == 3
    assert verdict.unused_safe_capacity == 3
    assert verdict.a_faster_underutilized is True
    assert verdict.auto_refill_required is True
    assert BLOCKER_NO_INDEPENDENT_READY_WORK not in verdict.blockers


def test_explanation_only_never_activates_enforcement() -> None:
    verdict = classify_utilization(
        _admitted_facts(
            activation=AFasterActivation.EXPLANATION_ONLY,
            occupied_mutable_lanes=0,
            ready_mutable_candidates=5,
        )
    )
    # Explaining/describing A-Faster is not tasking: capacity is objectively
    # idle and fillable, but no utilization obligation may be derived.
    assert verdict.fanout_target == 0
    assert verdict.auto_refill_required is False
    assert verdict.a_faster_underutilized is False
    assert BLOCKER_ACTIVATION_EXPLANATION_ONLY in verdict.blockers
    assert verdict.activation == "A_FASTER_EXPLANATION_ONLY"


def test_not_invoked_blocks_with_typed_blocker() -> None:
    verdict = classify_utilization(
        _admitted_facts(activation=AFasterActivation.NOT_INVOKED)
    )
    assert verdict.fanout_target == 0
    assert verdict.auto_refill_required is False
    assert BLOCKER_A_FASTER_NOT_ACTIVE in verdict.blockers


# --- FANOUT_TARGET / budget bounds --------------------------------------


def test_fanout_never_exceeds_budget_or_candidates() -> None:
    verdict = classify_utilization(
        _admitted_facts(
            occupied_mutable_lanes=0,
            occupied_review_lanes=0,
            ready_mutable_candidates=10,
            ready_review_candidates=10,
        )
    )
    assert DEFAULT_MUTABLE_LANES == 3
    assert DEFAULT_REVIEW_LANES == 1
    assert verdict.fanout_target_mutable == 3
    assert verdict.fanout_target_review == 1
    assert verdict.fanout_target == 4
    assert verdict.unused_safe_capacity == 4


def test_review_lane_is_capped_by_its_own_budget() -> None:
    verdict = classify_utilization(
        _admitted_facts(occupied_review_lanes=0, ready_review_candidates=2)
    )
    assert verdict.fanout_target_review == 1


def test_partial_idle_without_matching_work_reports_typed_blocker() -> None:
    verdict = classify_utilization(
        _admitted_facts(
            occupied_mutable_lanes=2,
            ready_mutable_candidates=0,
            ready_review_candidates=1,
        )
    )
    # One mutable slot idles with no matching work (typed explanation, not
    # a dispatch obligation); the review slot still refills.
    assert verdict.fanout_target_mutable == 0
    assert verdict.fanout_target_review == 1
    assert verdict.fanout_target == 1
    assert verdict.unused_safe_capacity == 1
    assert verdict.a_faster_underutilized is True
    assert BLOCKER_NO_INDEPENDENT_READY_WORK in verdict.blockers


# --- no manufactured work / no quota burning -----------------------------


def test_no_ready_work_means_no_refill_and_no_manufactured_work() -> None:
    verdict = classify_utilization(
        _admitted_facts(ready_mutable_candidates=0, ready_review_candidates=0)
    )
    assert verdict.fanout_target == 0
    assert verdict.unused_safe_capacity == 0
    assert verdict.a_faster_underutilized is False
    assert verdict.auto_refill_required is False
    assert BLOCKER_NO_INDEPENDENT_READY_WORK in verdict.blockers


def test_module_is_pure_and_burns_no_quota() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "subprocess",
        "urllib",
        "requests",
        "socket",
        "os.system",
        "Popen",
        "open(",
        "Path(",
        "sqlite3",
        "threading",
    ):
        assert forbidden not in source, (
            f"utilization guard must stay pure; forbidden token {forbidden!r}"
        )


# --- quota admission: structured evidence only ---------------------------


def test_quota_exhausted_keeps_underutilized_with_typed_blocker() -> None:
    verdict = classify_utilization(
        _admitted_facts(glm_quota_admission=QuotaAdmission.QUOTA_EXHAUSTED)
    )
    # Capacity is idle and fillable (underutilized) but a typed blocker
    # explains why refill is not admitted now.
    assert verdict.fanout_target == 0
    assert verdict.unused_safe_capacity == 2
    assert verdict.a_faster_underutilized is True
    assert verdict.auto_refill_required is False
    assert BLOCKER_QUOTA_EXHAUSTED in verdict.blockers


@pytest.mark.parametrize(
    "admission,blocker",
    [
        (QuotaAdmission.QUOTA_UNKNOWN, BLOCKER_QUOTA_UNKNOWN),
        (
            QuotaAdmission.SECRET_SOURCE_UNAVAILABLE,
            BLOCKER_SECRET_SOURCE_UNAVAILABLE,
        ),
    ],
)
def test_unavailable_quota_evidence_fails_closed(
    admission: QuotaAdmission, blocker: str
) -> None:
    verdict = classify_utilization(_admitted_facts(glm_quota_admission=admission))
    assert verdict.fanout_target == 0
    assert verdict.auto_refill_required is False
    assert verdict.a_faster_underutilized is True
    assert blocker in verdict.blockers


def test_parse_quota_admission_accepts_exact_structured_labels() -> None:
    assert (
        parse_quota_admission("QUOTA_AVAILABLE") is QuotaAdmission.QUOTA_AVAILABLE
    )
    assert (
        parse_quota_admission("QUOTA_EXHAUSTED") is QuotaAdmission.QUOTA_EXHAUSTED
    )


def test_parse_quota_admission_rejects_serialized_command_text() -> None:
    # Bootstrap lesson 1: attempt-0001 inferred admission by matching
    # serialized command text after the real probe returned
    # SECRET_SOURCE_UNAVAILABLE. Serialized command text must never be
    # admission evidence.
    serialized = (
        "kilo --dir /wt --model cointh-glm/glm-5.3 --effort max "
        "&& echo QUOTA_AVAILABLE remaining_5h=12345"
    )
    with pytest.raises(ValueError):
        parse_quota_admission(serialized)
    with pytest.raises(ValueError):
        parse_quota_admission("quota_available")  # not an exact label
    with pytest.raises(ValueError):
        parse_quota_admission("")


# --- GLM route gate -------------------------------------------------------


def test_glm_route_blocked_blocks_fanout_with_typed_blocker() -> None:
    verdict = classify_utilization(_admitted_facts(glm_route_ready=False))
    assert verdict.fanout_target == 0
    assert verdict.a_faster_underutilized is True
    assert verdict.auto_refill_required is False
    assert BLOCKER_GLM_ROUTE_BLOCKED in verdict.blockers


# --- Sol direct long labor vs idle GLM capacity ---------------------------


def test_sol_direct_long_labor_flagged_when_glm_capacity_idle() -> None:
    verdict = classify_utilization(
        _admitted_facts(
            occupied_mutable_lanes=DEFAULT_MUTABLE_LANES,
            occupied_review_lanes=DEFAULT_REVIEW_LANES,
            ready_mutable_candidates=0,
            ready_review_candidates=0,
            sol_direct_long_labor_active=True,
            sol_direct_labor_glm_eligible=True,
        )
    )
    # Even with WIP full, Sol doing GLM-eligible long labor while eligible
    # GLM capacity is idle (quota available + route ready) is a typed
    # blocker: Sol direct execution is the fallback, not the default.
    assert verdict.a_faster_underutilized is False
    assert (
        BLOCKER_SOL_DIRECT_LONG_LABOR_WHILE_GLM_CAPACITY_IDLE in verdict.blockers
    )


def test_sol_direct_labor_not_flagged_when_glm_blocked() -> None:
    verdict = classify_utilization(
        _admitted_facts(
            glm_quota_admission=QuotaAdmission.QUOTA_EXHAUSTED,
            sol_direct_long_labor_active=True,
            sol_direct_labor_glm_eligible=True,
        )
    )
    assert (
        BLOCKER_SOL_DIRECT_LONG_LABOR_WHILE_GLM_CAPACITY_IDLE
        not in verdict.blockers
    )


def test_sol_direct_labor_not_flagged_when_not_glm_eligible() -> None:
    verdict = classify_utilization(
        _admitted_facts(
            sol_direct_long_labor_active=True,
            sol_direct_labor_glm_eligible=False,
        )
    )
    assert (
        BLOCKER_SOL_DIRECT_LONG_LABOR_WHILE_GLM_CAPACITY_IDLE
        not in verdict.blockers
    )


# --- delegation launch preconditions (bootstrap lessons) ------------------


def test_delegation_launch_preconditions_pin_bootstrap_lessons() -> None:
    assert "STRUCTURED_ADMISSION_EVIDENCE_ONLY" in DELEGATION_LAUNCH_PRECONDITIONS
    assert "EXPLICIT_DIR_BOUND_TO_CLAIMED_WORKTREE" in DELEGATION_LAUNCH_PRECONDITIONS
    assert (
        "IN_SESSION_REPO_WORKTREE_BRANCH_HEAD_PROOF"
        in DELEGATION_LAUNCH_PRECONDITIONS
    )
    assert (
        "KILO_SHARE_DISABLED_PER_RUN_UNLESS_SEPARATELY_AUTHORIZED"
        in DELEGATION_LAUNCH_PRECONDITIONS
    )
    verdict = classify_utilization(_admitted_facts())
    assert verdict.delegation_launch_preconditions == DELEGATION_LAUNCH_PRECONDITIONS


# --- fail-closed validation -----------------------------------------------


def test_negative_counts_fail_closed() -> None:
    with pytest.raises(ValueError):
        UtilizationFacts(activation=AFasterActivation.ACTIVE,
                         occupied_mutable_lanes=-1)
    with pytest.raises(ValueError):
        UtilizationFacts(activation=AFasterActivation.ACTIVE,
                         ready_review_candidates=-1)


def test_wip_overcommit_fails_closed() -> None:
    with pytest.raises(ValueError):
        UtilizationFacts(
            activation=AFasterActivation.ACTIVE,
            occupied_mutable_lanes=DEFAULT_MUTABLE_LANES + 1,
        )
    with pytest.raises(ValueError):
        UtilizationFacts(
            activation=AFasterActivation.ACTIVE,
            occupied_review_lanes=DEFAULT_REVIEW_LANES + 1,
        )


def test_invalid_budgets_fail_closed() -> None:
    with pytest.raises(ValueError):
        UtilizationFacts(activation=AFasterActivation.ACTIVE,
                         mutable_lanes_budget=0)
    with pytest.raises(ValueError):
        UtilizationFacts(activation=AFasterActivation.ACTIVE,
                         review_lanes_budget=-1)


# --- determinism -----------------------------------------------------------

def test_classification_is_deterministic() -> None:
    facts = _admitted_facts(ready_mutable_candidates=3)
    assert classify_utilization(facts) == classify_utilization(facts)
