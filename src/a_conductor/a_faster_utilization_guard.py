"""WO-P1-517 — pure deterministic A-Faster utilization classifier.

This module is a POLICY-ONLY, pure-function classifier over structured
utilization facts. It computes the machine-checkable utilization verdicts
``FANOUT_TARGET``, ``UNUSED_SAFE_CAPACITY``, ``A_FASTER_UNDERUTILIZED`` and
``AUTO_REFILL_REQUIRED`` plus typed blockers for the A-Faster acceleration
profile (see ``.agents/skills/a-faster/SKILL.md``).

Authority boundary (binding):

- It creates no scheduler, task store, claim/lease, provider, dispatch,
  retry, review, merge, or completion authority — it is a projection over
  facts supplied by the existing authorities.
- It launches nothing and never burns or probes quota itself; quota
  evidence arrives through the existing refresh-before-each-material-
  dispatch flow as structured admission evidence only.
- This classifier remains projection-only and launches nothing. WO-P1-549's
  separate executable auto-refill bridge may consume its accepted verdict and
  delegate a bounded scheduler-owned batch through the existing
  ``ParallelReadyExecutor``. The exact material route remains
  ``POLICY_ONLY`` unless the accepted WO-P1-498 ``PRE_DISPATCH`` guard is
  proven on that action path; only such a route may claim ``GUARD_ENFORCED``.
  This module does not import, call, or modify the #498 guard surface.

WO-P1-517 bootstrap lessons preserved here:

1. admission is consumed from structured evidence only — serialized
   command text is never quota evidence, and a structured
   ``SECRET_SOURCE_UNAVAILABLE`` probe result means admission is
   unavailable regardless of any command-text side channel;
2. delegated sessions require an explicit ``--dir`` bound to the claimed
   worktree plus in-session repo/worktree/branch/HEAD proof before any
   mutation;
3. delegated Kilo runs with a per-run ``share=disabled`` override unless
   sharing is separately authorized.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

DEFAULT_MUTABLE_LANES = 3
DEFAULT_REVIEW_LANES = 1

# Echoed on every verdict: preconditions any AUTO_REFILL dispatch must
# already satisfy through the existing A-Faster delegation rules. They are
# evidence requirements, never launch authority.
DELEGATION_LAUNCH_PRECONDITIONS: tuple[str, ...] = (
    "STRUCTURED_ADMISSION_EVIDENCE_ONLY",
    "EXPLICIT_DIR_BOUND_TO_CLAIMED_WORKTREE",
    "IN_SESSION_REPO_WORKTREE_BRANCH_HEAD_PROOF",
    "KILO_SHARE_DISABLED_PER_RUN_UNLESS_SEPARATELY_AUTHORIZED",
)

BLOCKER_A_FASTER_NOT_ACTIVE = "A_FASTER_NOT_ACTIVE"
BLOCKER_ACTIVATION_EXPLANATION_ONLY = "A_FASTER_EXPLANATION_ONLY_NOT_TASKING"
BLOCKER_NO_INDEPENDENT_READY_WORK = "NO_INDEPENDENT_READY_WORK"
BLOCKER_QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
BLOCKER_QUOTA_UNKNOWN = "QUOTA_UNKNOWN"
BLOCKER_SECRET_SOURCE_UNAVAILABLE = "SECRET_SOURCE_UNAVAILABLE"
BLOCKER_GLM_ROUTE_BLOCKED = "GLM_ROUTE_BLOCKED"
BLOCKER_SOL_DIRECT_LONG_LABOR_WHILE_GLM_CAPACITY_IDLE = (
    "SOL_DIRECT_LONG_LABOR_WHILE_GLM_CAPACITY_IDLE"
)


class AFasterActivation(Enum):
    """A-Faster activation receipt states (tasking-vs-explanation boundary).

    ``ACTIVE`` (receipt code ``A_FASTER_ACTIVE``) means a canonical
    invocation clause plus the normal A-FastTask binding/authority gates
    produced a proven tasking receipt for the session. ``EXPLANATION_ONLY``
    means A-Faster was described, explained, or quoted — including the
    roadmap shorthand inside documentation or review prose — which is
    never an activation receipt, never triggers utilization enforcement,
    and never grants WIP, claim, or mutation authority.
    """

    ACTIVE = "A_FASTER_ACTIVE"
    EXPLANATION_ONLY = "A_FASTER_EXPLANATION_ONLY"
    NOT_INVOKED = "A_FASTER_NOT_INVOKED"


class QuotaAdmission(Enum):
    """Structured GLM quota admission evidence.

    ``SECRET_SOURCE_UNAVAILABLE`` is a typed probe failure: admission is
    unavailable and must fail closed. It can never be upgraded by
    command-text resemblance (bootstrap lesson 1).
    """

    QUOTA_AVAILABLE = "QUOTA_AVAILABLE"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    QUOTA_UNKNOWN = "QUOTA_UNKNOWN"
    SECRET_SOURCE_UNAVAILABLE = "SECRET_SOURCE_UNAVAILABLE"


def parse_quota_admission(value: str) -> QuotaAdmission:
    """Parse quota admission from an exact structured label only.

    Anything else — including serialized command text that merely contains
    quota-looking words — raises ``ValueError``. This is the deterministic
    refusal of the attempt-0001 defect where admission was inferred by
    matching serialized command text after the real probe returned
    ``SECRET_SOURCE_UNAVAILABLE``.
    """
    if not isinstance(value, str):
        raise ValueError("QUOTA_EVIDENCE_NOT_STRUCTURED: expected string label")
    try:
        return QuotaAdmission(value)
    except ValueError:
        raise ValueError(
            "QUOTA_EVIDENCE_NOT_STRUCTURED: serialized or unknown admission "
            f"text is never quota evidence: {value!r}"
        ) from None


@dataclass(frozen=True)
class UtilizationFacts:
    """Structured, already-verified utilization facts (no I/O, pure input).

    Counts are lane/candidate counts reconstructed by the caller from
    durable evidence (census + lane occupancy matrix). This dataclass
    never derives or invents facts and never verifies claims.
    """

    activation: AFasterActivation
    occupied_mutable_lanes: int = 0
    occupied_review_lanes: int = 0
    ready_mutable_candidates: int = 0
    ready_review_candidates: int = 0
    glm_quota_admission: QuotaAdmission = QuotaAdmission.QUOTA_UNKNOWN
    glm_route_ready: bool = False
    sol_direct_long_labor_active: bool = False
    sol_direct_labor_glm_eligible: bool = False
    mutable_lanes_budget: int = DEFAULT_MUTABLE_LANES
    review_lanes_budget: int = DEFAULT_REVIEW_LANES

    def _validate_count(self, name: str, value: int) -> None:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"UTILIZATION_FACTS_INVALID: {name} must be an int")
        if value < 0:
            raise ValueError(f"UTILIZATION_FACTS_INVALID: {name} must be >= 0")

    def __post_init__(self) -> None:
        self._validate_count("occupied_mutable_lanes", self.occupied_mutable_lanes)
        self._validate_count("occupied_review_lanes", self.occupied_review_lanes)
        self._validate_count(
            "ready_mutable_candidates", self.ready_mutable_candidates
        )
        self._validate_count(
            "ready_review_candidates", self.ready_review_candidates
        )
        self._validate_count("mutable_lanes_budget", self.mutable_lanes_budget)
        self._validate_count("review_lanes_budget", self.review_lanes_budget)
        if self.mutable_lanes_budget < 1:
            raise ValueError(
                "UTILIZATION_FACTS_INVALID: mutable_lanes_budget must be >= 1"
            )
        if self.review_lanes_budget < 1:
            raise ValueError(
                "UTILIZATION_FACTS_INVALID: review_lanes_budget must be >= 1"
            )
        if self.occupied_mutable_lanes > self.mutable_lanes_budget:
            raise ValueError(
                "WIP_OVERCOMMIT_MUTABLE: occupancy exceeds the global WIP "
                "budget; reconcile through existing authorities before "
                "classification"
            )
        if self.occupied_review_lanes > self.review_lanes_budget:
            raise ValueError(
                "WIP_OVERCOMMIT_REVIEW: occupancy exceeds the global WIP "
                "budget; reconcile through existing authorities before "
                "classification"
            )


@dataclass(frozen=True)
class UtilizationVerdict:
    """Deterministic utilization verdict.

    Field names double as the stable WO-P1-517 output codes:

    - ``fanout_target`` — ``FANOUT_TARGET``: admitted lanes AUTO-FILL may
      dispatch now (budget- and candidate-bounded, quota/route admitted);
    - ``unused_safe_capacity`` — ``UNUSED_SAFE_CAPACITY``: idle slots
      inside the global WIP budget that independent READY work could
      occupy (objective capacity evidence, activation-independent);
    - ``a_faster_underutilized`` — ``A_FASTER_UNDERUTILIZED``: A-Faster is
      active and safe READY capacity is idle;
    - ``auto_refill_required`` — ``AUTO_REFILL_REQUIRED``: the refill
      obligation is due now (active, fillable capacity, no dispatch gate).

    ``blockers`` are typed explanations for idle capacity and dispatch
    gates. A verdict is a projection, never dispatch permission: it grants
    no authority and executes nothing.
    """

    activation: str
    fanout_target_mutable: int
    fanout_target_review: int
    unused_safe_capacity: int
    a_faster_underutilized: bool
    auto_refill_required: bool
    blockers: tuple[str, ...]
    delegation_launch_preconditions: tuple[str, ...] = field(
        default_factory=lambda: DELEGATION_LAUNCH_PRECONDITIONS
    )

    @property
    def fanout_target(self) -> int:
        """FANOUT_TARGET total across mutable and review lanes."""
        return self.fanout_target_mutable + self.fanout_target_review


def classify_utilization(facts: UtilizationFacts) -> UtilizationVerdict:
    """Classify A-Faster utilization deterministically (pure function)."""
    blockers: list[str] = []

    active = facts.activation is AFasterActivation.ACTIVE
    if facts.activation is AFasterActivation.NOT_INVOKED:
        blockers.append(BLOCKER_A_FASTER_NOT_ACTIVE)
    elif facts.activation is AFasterActivation.EXPLANATION_ONLY:
        blockers.append(BLOCKER_ACTIVATION_EXPLANATION_ONLY)

    free_mutable = facts.mutable_lanes_budget - facts.occupied_mutable_lanes
    free_review = facts.review_lanes_budget - facts.occupied_review_lanes

    # No manufactured work: only real independent READY candidates can
    # occupy idle capacity.
    fillable_mutable = min(free_mutable, facts.ready_mutable_candidates)
    fillable_review = min(free_review, facts.ready_review_candidates)
    unused_safe_capacity = fillable_mutable + fillable_review

    # Typed explanation for idle capacity that has no matching work.
    if free_mutable > facts.ready_mutable_candidates or free_review > (
        facts.ready_review_candidates
    ):
        blockers.append(BLOCKER_NO_INDEPENDENT_READY_WORK)

    # Dispatch gates apply to every fillable lane (all delegated inference
    # lanes need admission + a ready route), and only an A_FASTER_ACTIVE
    # receipt can produce a dispatch obligation at all: an explanation-only
    # session never yields fanout.
    quota = facts.glm_quota_admission
    dispatch_admitted = (
        active
        and quota is QuotaAdmission.QUOTA_AVAILABLE
        and facts.glm_route_ready
    )
    if active and unused_safe_capacity > 0:
        if quota is QuotaAdmission.QUOTA_EXHAUSTED:
            blockers.append(BLOCKER_QUOTA_EXHAUSTED)
        elif quota is QuotaAdmission.QUOTA_UNKNOWN:
            blockers.append(BLOCKER_QUOTA_UNKNOWN)
        elif quota is QuotaAdmission.SECRET_SOURCE_UNAVAILABLE:
            blockers.append(BLOCKER_SECRET_SOURCE_UNAVAILABLE)
        if not facts.glm_route_ready:
            blockers.append(BLOCKER_GLM_ROUTE_BLOCKED)

    fanout_mutable = fillable_mutable if dispatch_admitted else 0
    fanout_review = fillable_review if dispatch_admitted else 0

    # GLM-first preserved: Sol directly executes eligible long labor only
    # as the fallback when eligible GLM routes are blocked. Eligible GLM
    # capacity idle while Sol performs such labor is a typed blocker.
    if (
        facts.sol_direct_long_labor_active
        and facts.sol_direct_labor_glm_eligible
        and quota is QuotaAdmission.QUOTA_AVAILABLE
        and facts.glm_route_ready
    ):
        blockers.append(BLOCKER_SOL_DIRECT_LONG_LABOR_WHILE_GLM_CAPACITY_IDLE)

    underutilized = active and unused_safe_capacity > 0
    auto_refill_required = active and (fanout_mutable + fanout_review) > 0

    return UtilizationVerdict(
        activation=facts.activation.value,
        fanout_target_mutable=fanout_mutable,
        fanout_target_review=fanout_review,
        unused_safe_capacity=unused_safe_capacity,
        a_faster_underutilized=underutilized,
        auto_refill_required=auto_refill_required,
        blockers=tuple(blockers),
    )
