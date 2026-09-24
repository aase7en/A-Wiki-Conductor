"""WO-P1-537 — elastic borrowed-lane policy contract tests."""

import importlib
from pathlib import Path

import pytest

from a_conductor.elastic_wip_policy import (
    ACTIVE_MUTATION_LIMIT,
    BORROWED_LANE_LIMIT,
    MUTABLE_CLAIM_LIMIT,
    REVIEW_LANE_LIMIT,
    ElasticWipFacts,
    GateState,
    classify_elastic_wip,
)


def _facts(**overrides):
    defaults = dict(
        base_active=1,
        base_waiting_ci=1,
        base_waiting_external=1,
        ready_independent_candidates=2,
        scope_gate=GateState.READY,
        claim_gate=GateState.READY,
        runtime_gate=GateState.READY,
    )
    defaults.update(overrides)
    return ElasticWipFacts(**defaults)


def test_policy_constants_freeze_three_plus_two_plus_review() -> None:
    assert ACTIVE_MUTATION_LIMIT == 3
    assert BORROWED_LANE_LIMIT == 2
    assert MUTABLE_CLAIM_LIMIT == 5
    assert REVIEW_LANE_LIMIT == 1


def test_two_waiting_base_lanes_can_borrow_two_without_exceeding_compute() -> None:
    verdict = classify_elastic_wip(_facts())
    assert verdict.base_claimed == 3
    assert verdict.borrowable_waits == 2
    assert verdict.new_borrow_target == 2
    assert verdict.active_mutation_total == 1
    assert verdict.active_mutation_after_refill == 3
    assert verdict.claimed_mutable_after_refill == 5
    assert verdict.contraction_required is False


def test_one_wait_allows_only_one_borrow() -> None:
    verdict = classify_elastic_wip(
        _facts(base_active=2, base_waiting_external=0, ready_independent_candidates=5)
    )
    assert verdict.new_borrow_target == 1
    assert verdict.active_mutation_after_refill == 3


def test_no_ready_work_never_manufactures_borrowed_work() -> None:
    verdict = classify_elastic_wip(_facts(ready_independent_candidates=0))
    assert verdict.new_borrow_target == 0
    assert "NO_INDEPENDENT_READY_WORK" in verdict.blockers


@pytest.mark.parametrize("gate_name", ("scope_gate", "claim_gate", "runtime_gate"))
@pytest.mark.parametrize("gate", (GateState.BLOCKED, GateState.UNKNOWN))
def test_borrowing_fails_closed_on_nonready_gate(gate_name: str, gate: GateState) -> None:
    verdict = classify_elastic_wip(_facts(**{gate_name: gate}))
    assert verdict.new_borrow_target == 0
    assert verdict.borrowed_resume_target == 0
    assert any(gate_name.upper() in blocker for blocker in verdict.blockers)


def test_returning_base_lane_forces_borrowed_checkpoint_and_park() -> None:
    verdict = classify_elastic_wip(
        _facts(
            base_active=2,
            base_waiting_ci=0,
            base_waiting_external=0,
            base_returning_ready=1,
            borrowed_active=1,
            ready_independent_candidates=3,
        )
    )
    assert verdict.contraction_required is True
    assert verdict.borrowed_to_park == 1
    assert verdict.new_borrow_target == 0
    assert verdict.active_mutation_after_contraction == 3


def test_parked_borrowed_lane_is_claimed_but_not_active_and_resumes_first() -> None:
    verdict = classify_elastic_wip(
        _facts(
            borrowed_parked=1,
            ready_independent_candidates=2,
        )
    )
    assert verdict.borrowed_claimed == 1
    assert verdict.borrowed_resume_target == 1
    assert verdict.new_borrow_target == 1
    assert verdict.claimed_mutable_after_refill == 5
    assert verdict.active_mutation_after_refill == 3


def test_review_lane_is_separate_from_mutation_compute_budget() -> None:
    verdict = classify_elastic_wip(_facts(review_claimed=1))
    assert verdict.review_claimed == 1
    assert verdict.new_borrow_target == 2


@pytest.mark.parametrize(
    "wait_field",
    ("base_waiting_approval", "base_waiting_jev", "base_waiting_glm"),
)
def test_explicit_orchestrator_waits_can_create_borrow_capacity(wait_field: str) -> None:
    verdict = classify_elastic_wip(
        _facts(
            base_active=2,
            base_waiting_ci=0,
            base_waiting_external=0,
            ready_independent_candidates=1,
            **{wait_field: 1},
        )
    )
    assert verdict.borrowable_waits == 1
    assert verdict.new_borrow_target == 1
    assert verdict.active_mutation_after_refill == 3


def test_waiting_glm_with_active_mutation_child_does_not_free_slot() -> None:
    verdict = classify_elastic_wip(
        _facts(
            base_active=2,
            base_waiting_ci=0,
            base_waiting_external=0,
            base_waiting_glm=1,
            glm_wait_active_mutation_children=1,
            ready_independent_candidates=5,
        )
    )
    assert verdict.borrowable_waits == 0
    assert verdict.active_mutation_total == 3
    assert verdict.new_borrow_target == 0


def test_glm_wait_child_count_cannot_exceed_glm_wait_lanes() -> None:
    with pytest.raises(ValueError):
        classify_elastic_wip(
            _facts(
                base_active=2,
                base_waiting_ci=0,
                base_waiting_external=0,
                base_waiting_glm=0,
                glm_wait_active_mutation_children=1,
            )
        )


@pytest.mark.parametrize(
    "kwargs",
    (
        {"base_active": 4, "base_waiting_ci": 0, "base_waiting_external": 0},
        {"borrowed_active": 3},
        {"review_claimed": 2},
    ),
)
def test_overcommit_fails_closed(kwargs) -> None:
    with pytest.raises(ValueError):
        classify_elastic_wip(_facts(**kwargs))


def test_classifier_is_deterministic() -> None:
    facts = _facts(borrowed_parked=1)
    assert classify_elastic_wip(facts) == classify_elastic_wip(facts)


def test_policy_module_is_pure_projection_only() -> None:
    module = importlib.import_module("a_conductor.elastic_wip_policy")
    source = Path(module.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "subprocess",
        "sqlite3",
        "requests",
        "urllib",
        "socket",
        "threading",
        "Popen",
        "os.system",
    ):
        assert forbidden not in source
