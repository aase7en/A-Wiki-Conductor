"""WO-P1-537 — pure elastic WIP / borrowed-lane policy projection.

This module grants no task, claim, lease, dispatch, scheduler, retry, review,
merge, or completion authority.  It classifies already-reconciled facts only.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


ACTIVE_MUTATION_LIMIT = 3
BORROWED_LANE_LIMIT = 2
MUTABLE_CLAIM_LIMIT = ACTIVE_MUTATION_LIMIT + BORROWED_LANE_LIMIT
REVIEW_LANE_LIMIT = 1


class GateState(Enum):
    READY = "READY"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ElasticWipFacts:
    """Structured occupancy facts reconstructed from existing authorities."""

    base_active: int = 0
    base_waiting_ci: int = 0
    base_waiting_approval: int = 0
    base_waiting_glm: int = 0
    base_waiting_jev: int = 0
    base_waiting_external: int = 0
    base_cooldown: int = 0
    glm_wait_active_mutation_children: int = 0
    glm_wait_unknown_mutation_children: int = 0
    base_returning_ready: int = 0
    base_blocked: int = 0
    base_human_required: int = 0
    borrowed_active: int = 0
    borrowed_parked: int = 0
    review_claimed: int = 0
    ready_independent_candidates: int = 0
    scope_gate: GateState = GateState.UNKNOWN
    claim_gate: GateState = GateState.UNKNOWN
    runtime_gate: GateState = GateState.UNKNOWN

    def __post_init__(self) -> None:
        names = (
            "base_active",
            "base_waiting_ci",
            "base_waiting_approval",
            "base_waiting_glm",
            "base_waiting_jev",
            "base_waiting_external",
            "base_cooldown",
            "glm_wait_active_mutation_children",
            "glm_wait_unknown_mutation_children",
            "base_returning_ready",
            "base_blocked",
            "base_human_required",
            "borrowed_active",
            "borrowed_parked",
            "review_claimed",
            "ready_independent_candidates",
        )
        for name in names:
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"ELASTIC_WIP_FACTS_INVALID: {name} must be >= 0")
        if (
            self.glm_wait_active_mutation_children
            + self.glm_wait_unknown_mutation_children
            > self.base_waiting_glm
        ):
            raise ValueError(
                "ELASTIC_WIP_FACTS_INVALID: GLM child evidence exceeds WAITING_GLM lanes"
            )

    @property
    def base_claimed(self) -> int:
        return (
            self.base_active
            + self.base_waiting_ci
            + self.base_waiting_approval
            + self.base_waiting_glm
            + self.base_waiting_jev
            + self.base_waiting_external
            + self.base_cooldown
            + self.base_returning_ready
            + self.base_blocked
            + self.base_human_required
        )

    @property
    def borrowed_claimed(self) -> int:
        return self.borrowed_active + self.borrowed_parked

    @property
    def borrowable_waits(self) -> int:
        passive_glm_waits = (
            self.base_waiting_glm
            - self.glm_wait_active_mutation_children
            - self.glm_wait_unknown_mutation_children
        )
        return (
            self.base_waiting_ci
            + self.base_waiting_approval
            + passive_glm_waits
            + self.base_waiting_jev
            + self.base_waiting_external
            + self.base_cooldown
        )

    @property
    def active_base_mutations(self) -> int:
        return self.base_active + self.glm_wait_active_mutation_children


@dataclass(frozen=True)
class ElasticWipVerdict:
    base_claimed: int
    borrowed_claimed: int
    review_claimed: int
    borrowable_waits: int
    active_mutation_total: int
    claimed_mutable_total: int
    borrowed_to_park: int
    borrowed_resume_target: int
    new_borrow_target: int
    active_mutation_after_contraction: int
    active_mutation_after_refill: int
    claimed_mutable_after_refill: int
    contraction_required: bool
    blockers: tuple[str, ...]


def _gate_blockers(facts: ElasticWipFacts) -> tuple[str, ...]:
    blockers: list[str] = []
    for field_name in ("scope_gate", "claim_gate", "runtime_gate"):
        gate = getattr(facts, field_name)
        if not isinstance(gate, GateState):
            raise ValueError(f"ELASTIC_WIP_FACTS_INVALID: {field_name} unsupported")
        if gate is not GateState.READY:
            blockers.append(f"{field_name.upper()}_{gate.value}")
    return tuple(blockers)


def _validate_occupancy(facts: ElasticWipFacts) -> None:
    if facts.base_claimed > ACTIVE_MUTATION_LIMIT:
        raise ValueError("WIP_OVERCOMMIT_BASE: base claims exceed 3")
    if facts.borrowed_claimed > BORROWED_LANE_LIMIT:
        raise ValueError("WIP_OVERCOMMIT_BORROWED: borrowed claims exceed 2")
    if facts.base_claimed + facts.borrowed_claimed > MUTABLE_CLAIM_LIMIT:
        raise ValueError("WIP_OVERCOMMIT_MUTABLE_CLAIMS: claims exceed 5")
    if facts.review_claimed > REVIEW_LANE_LIMIT:
        raise ValueError("WIP_OVERCOMMIT_REVIEW: review claims exceed 1")
    if facts.active_base_mutations + facts.borrowed_active > ACTIVE_MUTATION_LIMIT:
        raise ValueError("WIP_OVERCOMMIT_ACTIVE: active mutation exceeds 3")


def classify_elastic_wip(facts: ElasticWipFacts) -> ElasticWipVerdict:
    """Classify borrow/refill/contraction obligations without performing them."""

    _validate_occupancy(facts)
    gate_blockers = _gate_blockers(facts)

    projected_with_returns = (
        facts.active_base_mutations
        + facts.base_returning_ready
        + facts.borrowed_active
    )
    borrowed_to_park = max(
        0,
        projected_with_returns - ACTIVE_MUTATION_LIMIT,
        facts.borrowed_active - facts.borrowable_waits,
    )
    if borrowed_to_park > facts.borrowed_active:
        raise ValueError("WIP_CONTRACTION_IMPOSSIBLE: insufficient borrowed active lanes")

    borrowed_active_after_park = facts.borrowed_active - borrowed_to_park
    active_after_contraction = (
        facts.active_base_mutations
        + facts.base_returning_ready
        + borrowed_active_after_park
    )
    headroom = ACTIVE_MUTATION_LIMIT - active_after_contraction

    # Borrowed work may consume only capacity created by the three explicit
    # passive wait classes. BLOCKED/HUMAN_REQUIRED never create borrow capacity.
    borrowed_wait_headroom = max(
        0, facts.borrowable_waits - borrowed_active_after_park
    )
    admitted_headroom = min(headroom, borrowed_wait_headroom)

    resume_target = 0
    new_target = 0
    blockers = list(gate_blockers)
    if facts.glm_wait_unknown_mutation_children:
        blockers.append("WAITING_GLM_CHILD_STATUS_UNKNOWN")
    if not gate_blockers and admitted_headroom > 0:
        # Existing parked claims resume before creating another claim.
        resume_target = min(facts.borrowed_parked, admitted_headroom)
        remaining = admitted_headroom - resume_target
        free_borrow_claims = BORROWED_LANE_LIMIT - facts.borrowed_claimed
        new_target = min(
            remaining,
            free_borrow_claims,
            facts.ready_independent_candidates,
        )
        if remaining > 0 and free_borrow_claims > 0 and facts.ready_independent_candidates == 0:
            blockers.append("NO_INDEPENDENT_READY_WORK")
    elif admitted_headroom > 0 and facts.ready_independent_candidates == 0:
        blockers.append("NO_INDEPENDENT_READY_WORK")

    active_after_refill = active_after_contraction + resume_target + new_target
    claimed_after_refill = (
        facts.base_claimed + facts.borrowed_claimed + new_target
    )
    if active_after_refill > ACTIVE_MUTATION_LIMIT:
        raise AssertionError("elastic WIP classifier exceeded active mutation limit")
    if claimed_after_refill > MUTABLE_CLAIM_LIMIT:
        raise AssertionError("elastic WIP classifier exceeded mutable claim limit")

    return ElasticWipVerdict(
        base_claimed=facts.base_claimed,
        borrowed_claimed=facts.borrowed_claimed,
        review_claimed=facts.review_claimed,
        borrowable_waits=facts.borrowable_waits,
        active_mutation_total=facts.active_base_mutations + facts.borrowed_active,
        claimed_mutable_total=facts.base_claimed + facts.borrowed_claimed,
        borrowed_to_park=borrowed_to_park,
        borrowed_resume_target=resume_target,
        new_borrow_target=new_target,
        active_mutation_after_contraction=active_after_contraction,
        active_mutation_after_refill=active_after_refill,
        claimed_mutable_after_refill=claimed_after_refill,
        contraction_required=borrowed_to_park > 0,
        blockers=tuple(blockers),
    )
