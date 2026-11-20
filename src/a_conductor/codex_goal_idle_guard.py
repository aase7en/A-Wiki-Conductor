"""Pure Codex Goal idle-guard projection for A-Sunday Conductor (WO-P1-576).

This module is a deterministic, decision-only classifier over caller-verified
facts.  It never invokes Codex Goal APIs, performs no I/O of any kind, reads
no clock, and holds no process, network, or mutation authority.  Facts that
depend on time (steer age vs cadence bound) or on external probes (GLM quota
freshness) must arrive pre-classified by the caller; ambiguous evidence stays
ambiguous and is never converted into admission.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class GoalGuardAction(str, Enum):
    CONFIG_TOPOLOGY_ERROR = "CONFIG_TOPOLOGY_ERROR"
    HARVEST_REQUIRED = "HARVEST_REQUIRED"
    REAL_GLM_DISPATCH_REQUIRED = "REAL_GLM_DISPATCH_REQUIRED"
    STALE_QUEUE_STEER = "STALE_QUEUE_STEER"
    ACTIVE_CONTINUE = "ACTIVE_CONTINUE"
    RESUME_REQUIRED = "RESUME_REQUIRED"
    BLOCKED = "BLOCKED"
    NOT_BENEFICIAL = "NOT_BENEFICIAL"
    STEER_DUPLICATE_SUPPRESSED = "STEER_DUPLICATE_SUPPRESSED"
    IDLE_PAUSE_REQUIRED = "IDLE_PAUSE_REQUIRED"


class FingerprintState(str, Enum):
    UNCHANGED = "UNCHANGED"
    MATERIAL_DELTA = "MATERIAL_DELTA"
    UNKNOWN = "UNKNOWN"


class SafeReadyState(str, Enum):
    GENUINE = "GENUINE"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"


class PendingSteerState(str, Enum):
    NONE = "NONE"
    EQUIVALENT_PENDING_FRESH = "EQUIVALENT_PENDING_FRESH"
    EQUIVALENT_PENDING_STALE = "EQUIVALENT_PENDING_STALE"


class GlmDispositionState(str, Enum):
    NONE = "NONE"
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    NOT_BENEFICIAL = "NOT_BENEFICIAL"


class GlmQuotaState(str, Enum):
    CONFIRMED_AVAILABLE = "CONFIRMED_AVAILABLE"
    AMBIGUOUS = "AMBIGUOUS"
    CACHED = "CACHED"
    UNAVAILABLE = "UNAVAILABLE"


_REASON_ORDER: tuple[str, ...] = (
    "WATCHDOG_THREAD_EQUALS_GOAL_THREAD",
    "TERMINAL_UNHARVESTED_PRESENT",
    "ELIGIBLE_R2R3_WITHOUT_DISPOSITION",
    "BLOCKED:QUOTA_AMBIGUOUS",
    "BLOCKED:QUOTA_CACHED",
    "BLOCKED:QUOTA_UNAVAILABLE",
    "PENDING_STEER_EXCEEDS_CADENCE_BOUND",
    "EXECUTIONS_STARTING",
    "EXECUTIONS_RUNNING",
    "EXECUTIONS_WAITING",
    "EXECUTIONS_STALLED",
    "EXECUTIONS_INTERRUPTED",
    "EXECUTIONS_UNKNOWN",
    "ACTIONABLE_QUEUE_NON_EMPTY",
    "MATERIAL_DELTA_PRESENT",
    "SAFE_READY_GENUINE",
    "HUMAN_INSTRUCTION_PENDING",
    "TASK_ROUTE_DISPOSITION",
    "EQUIVALENT_STEER_PENDING_WITHIN_CADENCE_BOUND",
    "IDLE_ALL_ACTIONLESS",
    "FINGERPRINT_UNCHANGED",
    "FINGERPRINT_UNKNOWN",
)

_QUOTA_BLOCK_REASONS = {
    GlmQuotaState.AMBIGUOUS: "BLOCKED:QUOTA_AMBIGUOUS",
    GlmQuotaState.CACHED: "BLOCKED:QUOTA_CACHED",
    GlmQuotaState.UNAVAILABLE: "BLOCKED:QUOTA_UNAVAILABLE",
}

_CENSUS_COUNT_FIELDS = (
    "starting",
    "running",
    "waiting",
    "stalled",
    "terminal_unharvested",
    "interrupted",
    "terminal",
    "unknown",
)


def _require_count(name: str, value: int) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative int")


@dataclass(frozen=True, slots=True)
class DelegatedExecutionCensus:
    starting: int
    running: int
    waiting: int
    stalled: int
    terminal_unharvested: int
    interrupted: int
    terminal: int
    unknown: int

    def __post_init__(self) -> None:
        for name in _CENSUS_COUNT_FIELDS:
            _require_count(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class GlmDisposition:
    state: GlmDispositionState
    reason: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.state, GlmDispositionState):
            raise ValueError("state must be a GlmDispositionState")
        requires_reason = self.state in (
            GlmDispositionState.BLOCKED,
            GlmDispositionState.NOT_BENEFICIAL,
        )
        if requires_reason:
            if type(self.reason) is not str or not self.reason:
                raise ValueError(
                    "reason must be a non-empty plain str for"
                    " BLOCKED/NOT_BENEFICIAL dispositions"
                )
        elif self.reason is not None:
            raise ValueError(
                "reason is only allowed for BLOCKED/NOT_BENEFICIAL dispositions"
            )


@dataclass(frozen=True, slots=True)
class GoalIdleGuardSnapshot:
    execution_census: DelegatedExecutionCensus
    actionable_queue_count: int
    fingerprint_state: FingerprintState
    safe_ready_state: SafeReadyState
    watchdog_thread_id: str
    goal_thread_id: str
    pending_steer_state: PendingSteerState
    eligible_r2r3_task: bool
    glm_disposition: GlmDisposition
    glm_quota_state: GlmQuotaState
    human_instruction_pending: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.execution_census, DelegatedExecutionCensus):
            raise ValueError(
                "execution_census must be a DelegatedExecutionCensus"
            )
        _require_count("actionable_queue_count", self.actionable_queue_count)
        if not isinstance(self.fingerprint_state, FingerprintState):
            raise ValueError("fingerprint_state must be a FingerprintState")
        if not isinstance(self.safe_ready_state, SafeReadyState):
            raise ValueError("safe_ready_state must be a SafeReadyState")
        if (
            type(self.watchdog_thread_id) is not str
            or not self.watchdog_thread_id
        ):
            raise ValueError(
                "watchdog_thread_id must be a non-empty plain str"
            )
        if type(self.goal_thread_id) is not str or not self.goal_thread_id:
            raise ValueError("goal_thread_id must be a non-empty plain str")
        if not isinstance(self.pending_steer_state, PendingSteerState):
            raise ValueError("pending_steer_state must be a PendingSteerState")
        if type(self.eligible_r2r3_task) is not bool:
            raise ValueError("eligible_r2r3_task must be bool")
        if type(self.human_instruction_pending) is not bool:
            raise ValueError("human_instruction_pending must be bool")
        if not isinstance(self.glm_disposition, GlmDisposition):
            raise ValueError("glm_disposition must be a GlmDisposition")
        if not isinstance(self.glm_quota_state, GlmQuotaState):
            raise ValueError("glm_quota_state must be a GlmQuotaState")


@dataclass(frozen=True, slots=True)
class GoalIdleGuardVerdict:
    action: GoalGuardAction
    reason_codes: tuple[str, ...]

    @property
    def pause_forbidden(self) -> bool:
        return self.action is not GoalGuardAction.IDLE_PAUSE_REQUIRED


def _ordered_reasons(present: set[str]) -> tuple[str, ...]:
    ordered = [reason for reason in _REASON_ORDER if reason in present]
    ordered.extend(sorted(code for code in present if code not in _REASON_ORDER))
    return tuple(ordered)


def classify_goal_idle(
    snapshot: GoalIdleGuardSnapshot,
) -> GoalIdleGuardVerdict:
    """Return the single deterministic Goal idle-guard action for a snapshot."""

    if not isinstance(snapshot, GoalIdleGuardSnapshot):
        raise ValueError("snapshot must be a GoalIdleGuardSnapshot")

    census = snapshot.execution_census
    disposition = snapshot.glm_disposition

    if snapshot.watchdog_thread_id == snapshot.goal_thread_id:
        return GoalIdleGuardVerdict(
            action=GoalGuardAction.CONFIG_TOPOLOGY_ERROR,
            reason_codes=_ordered_reasons({"WATCHDOG_THREAD_EQUALS_GOAL_THREAD"}),
        )

    if census.terminal_unharvested > 0:
        return GoalIdleGuardVerdict(
            action=GoalGuardAction.HARVEST_REQUIRED,
            reason_codes=_ordered_reasons({"TERMINAL_UNHARVESTED_PRESENT"}),
        )

    if (
        snapshot.eligible_r2r3_task
        and disposition.state is GlmDispositionState.NONE
    ):
        if snapshot.glm_quota_state is GlmQuotaState.CONFIRMED_AVAILABLE:
            return GoalIdleGuardVerdict(
                action=GoalGuardAction.REAL_GLM_DISPATCH_REQUIRED,
                reason_codes=_ordered_reasons(
                    {"ELIGIBLE_R2R3_WITHOUT_DISPOSITION"}
                ),
            )
        return GoalIdleGuardVerdict(
            action=GoalGuardAction.BLOCKED,
            reason_codes=_ordered_reasons(
                {
                    "ELIGIBLE_R2R3_WITHOUT_DISPOSITION",
                    _QUOTA_BLOCK_REASONS[snapshot.glm_quota_state],
                }
            ),
        )

    if snapshot.pending_steer_state is PendingSteerState.EQUIVALENT_PENDING_STALE:
        return GoalIdleGuardVerdict(
            action=GoalGuardAction.STALE_QUEUE_STEER,
            reason_codes=_ordered_reasons(
                {"PENDING_STEER_EXCEEDS_CADENCE_BOUND"}
            ),
        )

    active_reasons: set[str] = set()
    if census.starting > 0:
        active_reasons.add("EXECUTIONS_STARTING")
    if census.running > 0:
        active_reasons.add("EXECUTIONS_RUNNING")
    if census.waiting > 0:
        active_reasons.add("EXECUTIONS_WAITING")
    if census.stalled > 0:
        active_reasons.add("EXECUTIONS_STALLED")
    if census.interrupted > 0:
        active_reasons.add("EXECUTIONS_INTERRUPTED")
    if census.unknown > 0:
        active_reasons.add("EXECUTIONS_UNKNOWN")
    if snapshot.actionable_queue_count > 0:
        active_reasons.add("ACTIONABLE_QUEUE_NON_EMPTY")
    if active_reasons:
        return GoalIdleGuardVerdict(
            action=GoalGuardAction.ACTIVE_CONTINUE,
            reason_codes=_ordered_reasons(active_reasons),
        )

    resume_reasons: set[str] = set()
    if snapshot.fingerprint_state is FingerprintState.MATERIAL_DELTA:
        resume_reasons.add("MATERIAL_DELTA_PRESENT")
    if snapshot.safe_ready_state is SafeReadyState.GENUINE:
        resume_reasons.add("SAFE_READY_GENUINE")
    if snapshot.human_instruction_pending:
        resume_reasons.add("HUMAN_INSTRUCTION_PENDING")
    if resume_reasons:
        return GoalIdleGuardVerdict(
            action=GoalGuardAction.RESUME_REQUIRED,
            reason_codes=_ordered_reasons(resume_reasons),
        )

    if disposition.state is GlmDispositionState.BLOCKED:
        return GoalIdleGuardVerdict(
            action=GoalGuardAction.BLOCKED,
            reason_codes=_ordered_reasons(
                {
                    "TASK_ROUTE_DISPOSITION",
                    f"BLOCKED:{disposition.reason}",
                }
            ),
        )
    if disposition.state is GlmDispositionState.NOT_BENEFICIAL:
        return GoalIdleGuardVerdict(
            action=GoalGuardAction.NOT_BENEFICIAL,
            reason_codes=_ordered_reasons(
                {
                    "TASK_ROUTE_DISPOSITION",
                    f"NOT_BENEFICIAL:{disposition.reason}",
                }
            ),
        )

    if (
        snapshot.pending_steer_state
        is PendingSteerState.EQUIVALENT_PENDING_FRESH
    ):
        return GoalIdleGuardVerdict(
            action=GoalGuardAction.STEER_DUPLICATE_SUPPRESSED,
            reason_codes=_ordered_reasons(
                {"EQUIVALENT_STEER_PENDING_WITHIN_CADENCE_BOUND"}
            ),
        )

    idle_reasons = {"IDLE_ALL_ACTIONLESS"}
    if snapshot.fingerprint_state is FingerprintState.UNCHANGED:
        idle_reasons.add("FINGERPRINT_UNCHANGED")
    else:
        idle_reasons.add("FINGERPRINT_UNKNOWN")
    return GoalIdleGuardVerdict(
        action=GoalGuardAction.IDLE_PAUSE_REQUIRED,
        reason_codes=_ordered_reasons(idle_reasons),
    )
