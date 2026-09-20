"""WO-P1-424 COCKPIT-1 — immutable read-only Runtime Cockpit projection.

Pure DTO/composer layer: it converts injected observations (already gathered
from accepted read authorities by callers) into one immutable lane projection
and snapshot with explicit field provenance and UNKNOWN / STALE /
EVIDENCE_INCOMPLETE semantics. The module never reads files, spawns
processes, keeps mutable state, schedules work, or issues commands. Hook and
WTL read-back authorities are not accepted in this candidate, so their
fields stay UNKNOWN by contract.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum


class CockpitProjectionError(ValueError):
    """Invalid cockpit observation inputs; projection fails closed."""


class CockpitFingerprintError(TypeError):
    """Fingerprint requested for an object that is not a cockpit snapshot."""


class CockpitState(Enum):
    NOT_DISPATCHED = "NOT_DISPATCHED"
    PENDING_SCOPE = "PENDING_SCOPE"
    RUNNING = "RUNNING"
    WAITING_EXTERNAL = "WAITING_EXTERNAL"
    STALLED_RECONCILE = "STALLED_RECONCILE"
    TERMINAL_UNHARVESTED = "TERMINAL_UNHARVESTED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    FAILED_VERIFIED = "FAILED_VERIFIED"
    COMPLETED_VERIFIED = "COMPLETED_VERIFIED"
    UNKNOWN = "UNKNOWN"


class CockpitGateStatus(Enum):
    UNKNOWN = "UNKNOWN"
    NOT_REQUIRED = "NOT_REQUIRED"
    PROVEN = "PROVEN"
    REFUTED = "REFUTED"


_TRANSPORT_STATES = ("CONNECTED", "DEGRADED", "LOST")
_EXECUTION_STATES = (
    "QUEUED",
    "RUNNING",
    "SUCCEEDED",
    "FAILED",
    "PROCESS_EXITED_UNKNOWN_RESULT",
    "RECOVERY_REQUIRED",
)
_EXECUTION_PROVENANCES = ("DURABLE_EXECUTION_RECORD", "OPERATOR_DECLARED")
_ACCEPTED_EXECUTION_PROVENANCE = "DURABLE_EXECUTION_RECORD"
_PORT_UNAVAILABLE = "PORT_UNAVAILABLE"
_RECORD_NOT_FOUND = "RECORD_NOT_FOUND"
_ACTIVE_LEASE = "ACTIVE"
_NOT_DECLARED = "NOT_DECLARED"

_HOOK_UNACCEPTED_REASON = (
    "Hook read-back authority not accepted (WO-P1-424); field stays UNKNOWN."
)
_WTL_UNACCEPTED_REASON = (
    "WTL read-back authority not accepted (WO-P1-424); field stays UNKNOWN."
)

_REPLAY_ACTIVE = "ACTIVE_EXECUTION_NEVER_DUPLICATE"
_REPLAY_RECOVER = "RECOVER_POINTER_PROCESS_RESULT_GIT_BEFORE_REDISPATCH"
_REPLAY_RECONCILE = "RECONCILE_BEFORE_ANY_REDISPATCH"
_REPLAY_SETTLED = "SETTLED_NO_REPLAY"
_REPLAY_NO_FLIGHT = "NO_EXECUTION_IN_FLIGHT"


@dataclass(frozen=True)
class CockpitLaneIdentity:
    """Declared lane context (who the projection is about), with provenance."""

    work_order_ref: str
    task_ref: str
    topology: str | None = None
    lane: str | None = None
    executor: str | None = None
    provider: str | None = None
    harness: str | None = None
    authority_repo: str | None = None
    execution_repo: str | None = None
    worktree: str | None = None
    branch: str | None = None
    expected_head: str | None = None
    execution_id: str | None = None
    lease_id: str | None = None
    provenance: str = "WORK_ORDER_DECLARED"

    def __post_init__(self) -> None:
        for label, value in (
            ("WORK_ORDER_REF", self.work_order_ref),
            ("TASK_REF", self.task_ref),
        ):
            if not isinstance(value, str) or not value.strip():
                raise CockpitProjectionError(f"LANE_IDENTITY_{label}_REQUIRED")


@dataclass(frozen=True)
class CockpitExecutionObservation:
    available: bool = False
    provenance: str | None = None
    reason: str | None = None
    execution_id: str | None = None
    job_id: str | None = None
    worker_id: str | None = None
    backend_id: str | None = None
    repo_root: str | None = None
    branch: str | None = None
    head_before: str | None = None
    transport_state: str | None = None
    execution_state: str | None = None
    pid: int | None = None
    exit_code: int | None = None
    started_at: str | None = None
    finished_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def unavailable(cls, reason: str) -> "CockpitExecutionObservation":
        return cls(available=False, reason=reason)

    def __post_init__(self) -> None:
        if self.transport_state is not None and self.transport_state not in _TRANSPORT_STATES:
            raise CockpitProjectionError("EXECUTION_TRANSPORT_STATE_UNSUPPORTED")
        if self.execution_state is not None and self.execution_state not in _EXECUTION_STATES:
            raise CockpitProjectionError("EXECUTION_STATE_UNSUPPORTED")
        if not self.available:
            return
        if self.provenance not in _EXECUTION_PROVENANCES:
            raise CockpitProjectionError("EXECUTION_PROVENANCE_UNSUPPORTED")
        if self.provenance == "OPERATOR_DECLARED" and self.pid is None:
            raise CockpitProjectionError("EXECUTION_OPERATOR_DECLARATION_REQUIRES_PID")
        if self.execution_state is None:
            raise CockpitProjectionError("EXECUTION_STATE_REQUIRED")
        if self.transport_state is None:
            raise CockpitProjectionError("EXECUTION_TRANSPORT_STATE_REQUIRED")


@dataclass(frozen=True)
class CockpitLeaseObservation:
    available: bool = False
    provenance: str | None = None
    reason: str | None = None
    lease_id: str | None = None
    worktree_key: str | None = None
    branch: str | None = None
    expected_head: str | None = None
    health: str | None = None
    acquired_at: str | None = None
    heartbeat_at: str | None = None
    expires_at: str | None = None

    @classmethod
    def unavailable(cls, reason: str) -> "CockpitLeaseObservation":
        return cls(available=False, reason=reason)

    def __post_init__(self) -> None:
        if self.available and not (
            isinstance(self.provenance, str) and self.provenance.strip()
        ):
            raise CockpitProjectionError("LEASE_PROVENANCE_REQUIRED")


@dataclass(frozen=True)
class CockpitGitObservation:
    available: bool = False
    provenance: str | None = None
    reason: str | None = None
    branch: str | None = None
    head: str | None = None
    dirty_state: str | None = None

    @classmethod
    def unavailable(cls, reason: str) -> "CockpitGitObservation":
        return cls(available=False, reason=reason)

    def __post_init__(self) -> None:
        if self.available and not (
            isinstance(self.provenance, str) and self.provenance.strip()
        ):
            raise CockpitProjectionError("GIT_PROVENANCE_REQUIRED")


@dataclass(frozen=True)
class CockpitGateEvidence:
    verification: CockpitGateStatus = CockpitGateStatus.UNKNOWN
    review: CockpitGateStatus = CockpitGateStatus.NOT_REQUIRED
    merge: CockpitGateStatus = CockpitGateStatus.UNKNOWN
    post_main: CockpitGateStatus = CockpitGateStatus.UNKNOWN
    ci: CockpitGateStatus = CockpitGateStatus.UNKNOWN
    provenance: str = "OPERATOR_DECLARED"


@dataclass(frozen=True)
class CockpitProcessIdentity:
    """Observed process identity; authoritative only with exact provenance."""

    pid: int | None = None
    authoritative: bool = False
    provenance: str | None = None


@dataclass(frozen=True)
class CockpitLaneInputs:
    identity: CockpitLaneIdentity
    execution: CockpitExecutionObservation = field(
        default_factory=lambda: CockpitExecutionObservation.unavailable(_PORT_UNAVAILABLE)
    )
    lease: CockpitLeaseObservation = field(
        default_factory=lambda: CockpitLeaseObservation.unavailable(_PORT_UNAVAILABLE)
    )
    git: CockpitGitObservation = field(
        default_factory=lambda: CockpitGitObservation.unavailable(_PORT_UNAVAILABLE)
    )
    gates: CockpitGateEvidence = field(default_factory=CockpitGateEvidence)


@dataclass(frozen=True)
class CockpitObservations:
    """One bounded pin of every lane observation, with a generation stamp."""

    lanes: tuple[CockpitLaneInputs, ...] = ()
    generated_at: str = ""


@dataclass(frozen=True)
class CockpitLaneProjection:
    identity: CockpitLaneIdentity
    state: CockpitState
    state_markers: tuple[str, ...]
    blocker_code: str | None
    execution_id: str | None = None
    job_id: str | None = None
    process_identity: CockpitProcessIdentity = field(default_factory=CockpitProcessIdentity)
    transport_state: str | None = None
    last_activity: str | None = None
    last_meaningful_progress: str | None = None
    replay_safety: str = "RECOVER_EVIDENCE_BEFORE_ANY_REDISPATCH"
    next_safe_action: str = "RECOVER_READ_AUTHORITIES_THEN_REPROJECT"
    hook_state: str = "UNKNOWN"
    hook_reason: str = _HOOK_UNACCEPTED_REASON
    wtl_state: str = "UNKNOWN"
    wtl_reason: str = _WTL_UNACCEPTED_REASON
    gates: CockpitGateEvidence = field(default_factory=CockpitGateEvidence)


@dataclass(frozen=True)
class CockpitSnapshot:
    lanes: tuple[CockpitLaneProjection, ...]
    generated_at: str
    stale: bool = False
    stale_reason: str | None = None
    degraded_observability: tuple[str, ...] = ()


def _anchor_mismatch(observed: str | None, declared: str | None) -> bool:
    return observed is not None and declared is not None and observed != declared


def _execution_matches(
    identity: CockpitLaneIdentity, execution: CockpitExecutionObservation
) -> bool:
    return not (
        _anchor_mismatch(execution.repo_root, identity.worktree)
        or _anchor_mismatch(execution.branch, identity.branch)
        or _anchor_mismatch(execution.head_before, identity.expected_head)
    )


def _lease_matches(
    identity: CockpitLaneIdentity, lease: CockpitLeaseObservation
) -> bool:
    return not (
        _anchor_mismatch(lease.worktree_key, identity.worktree)
        or _anchor_mismatch(lease.branch, identity.branch)
        or _anchor_mismatch(lease.expected_head, identity.expected_head)
    )


def _process_identity(
    identity: CockpitLaneIdentity, execution: CockpitExecutionObservation
) -> CockpitProcessIdentity:
    authoritative = bool(
        execution.available
        and execution.pid is not None
        and execution.provenance == _ACCEPTED_EXECUTION_PROVENANCE
        and _execution_matches(identity, execution)
    )
    return CockpitProcessIdentity(
        pid=execution.pid if execution.available else None,
        authoritative=authoritative,
        provenance=execution.provenance if execution.available else None,
    )


def _evaluate_gates(gates: CockpitGateEvidence) -> tuple[bool, str | None]:
    for status, missing_code, refuted_code in (
        (gates.verification, "MISSING_VERIFICATION_PROOF", "VERIFICATION_REFUTED"),
        (gates.review, "MISSING_REVIEW_PROOF", "REVIEW_REFUTED"),
        (gates.merge, "MISSING_MERGE_PROOF", "MERGE_REFUTED"),
        (gates.post_main, "MISSING_POST_MAIN_PROOF", "POST_MAIN_REFUTED"),
        (gates.ci, "MISSING_CI_PROOF", "CI_REFUTED"),
    ):
        if status is CockpitGateStatus.REFUTED:
            return False, refuted_code
        if status is CockpitGateStatus.NOT_REQUIRED:
            continue
        if status is not CockpitGateStatus.PROVEN:
            return False, missing_code
    return True, None


def project_cockpit_lane(inputs: CockpitLaneInputs) -> CockpitLaneProjection:
    """Project one lane fail-closed; never infers truth from absence."""
    identity = inputs.identity
    execution = inputs.execution
    lease = inputs.lease
    evidence_incomplete = not lease.available or not inputs.git.available
    base_markers = ("EVIDENCE_INCOMPLETE",) if evidence_incomplete else ()
    common = dict(
        identity=identity,
        execution_id=execution.execution_id if execution.available else None,
        job_id=execution.job_id if execution.available else None,
        process_identity=_process_identity(identity, execution),
        transport_state=execution.transport_state if execution.available else None,
        last_activity=(
            (execution.updated_at or execution.started_at) if execution.available else None
        ),
        last_meaningful_progress=execution.updated_at if execution.available else None,
        gates=inputs.gates,
    )

    if execution.available and execution.provenance != _ACCEPTED_EXECUTION_PROVENANCE:
        return CockpitLaneProjection(
            state=CockpitState.UNKNOWN,
            state_markers=("UNKNOWN", "EVIDENCE_INCOMPLETE"),
            blocker_code="EXECUTION_PROVENANCE_NOT_AUTHORITATIVE",
            next_safe_action="RECONCILE_EXECUTION_PROVENANCE_THEN_REPROJECT",
            **common,
        )

    if execution.available and not _execution_matches(identity, execution):
        return CockpitLaneProjection(
            state=CockpitState.UNKNOWN,
            state_markers=("UNKNOWN", "EVIDENCE_INCOMPLETE"),
            blocker_code="EXECUTION_PROVENANCE_MISMATCH",
            next_safe_action="RECONCILE_EXECUTION_IDENTITY_BEFORE_TRUST",
            **common,
        )

    if lease.available and not _lease_matches(identity, lease):
        return CockpitLaneProjection(
            state=CockpitState.UNKNOWN,
            state_markers=("UNKNOWN", "EVIDENCE_INCOMPLETE"),
            blocker_code="LEASE_PROVENANCE_MISMATCH",
            next_safe_action="RECONCILE_LEASE_IDENTITY_BEFORE_TRUST",
            **common,
        )

    if not execution.available:
        if execution.reason == _RECORD_NOT_FOUND:
            if (
                lease.available
                and lease.health == _ACTIVE_LEASE
                and _lease_matches(identity, lease)
            ):
                return CockpitLaneProjection(
                    state=CockpitState.PENDING_SCOPE,
                    state_markers=base_markers,
                    blocker_code=None,
                    replay_safety=_REPLAY_NO_FLIGHT,
                    next_safe_action="DECLARE_MUTABLE_SCOPE_THEN_DISPATCH_UNDER_EXISTING_AUTHORITY",
                    **common,
                )
            return CockpitLaneProjection(
                state=CockpitState.NOT_DISPATCHED,
                state_markers=base_markers,
                blocker_code=None,
                replay_safety=_REPLAY_NO_FLIGHT,
                next_safe_action="DISPATCH_UNDER_EXISTING_AUTHORITY_WHEN_READY",
                **common,
            )
        return CockpitLaneProjection(
            state=CockpitState.UNKNOWN,
            state_markers=("UNKNOWN", "EVIDENCE_INCOMPLETE"),
            blocker_code="EXECUTION_EVIDENCE_UNAVAILABLE",
            **common,
        )

    execution_state = execution.execution_state
    transport_state = execution.transport_state

    if execution_state == "PROCESS_EXITED_UNKNOWN_RESULT":
        return CockpitLaneProjection(
            state=CockpitState.OUTCOME_UNKNOWN,
            state_markers=base_markers,
            blocker_code="PROCESS_EXITED_UNKNOWN_RESULT",
            replay_safety=_REPLAY_RECOVER,
            next_safe_action="RECOVER_POINTER_PROCESS_RESULT_GIT_BEFORE_REDISPATCH",
            **common,
        )

    if execution_state == "RECOVERY_REQUIRED":
        return CockpitLaneProjection(
            state=CockpitState.STALLED_RECONCILE,
            state_markers=base_markers,
            blocker_code="EXECUTION_RECOVERY_REQUIRED",
            replay_safety=_REPLAY_RECONCILE,
            next_safe_action="RECONCILE_EXECUTION_THROUGH_EXISTING_RECOVERY_AUTHORITY",
            **common,
        )

    if execution_state == "QUEUED":
        return CockpitLaneProjection(
            state=CockpitState.WAITING_EXTERNAL,
            state_markers=base_markers,
            blocker_code=None,
            replay_safety=_REPLAY_ACTIVE,
            next_safe_action="AWAIT_EXTERNAL_EXECUTION_PROGRESS",
            **common,
        )

    if execution_state == "RUNNING":
        if transport_state == "LOST":
            return CockpitLaneProjection(
                state=CockpitState.STALLED_RECONCILE,
                state_markers=base_markers,
                blocker_code="TRANSPORT_LOST",
                replay_safety=_REPLAY_RECONCILE,
                next_safe_action="RECOVER_TRANSPORT_STATE_THEN_RECONCILE",
                **common,
            )
        markers = base_markers + (
            ("DEGRADED_OBSERVABILITY",) if transport_state == "DEGRADED" else ()
        )
        return CockpitLaneProjection(
            state=CockpitState.RUNNING,
            state_markers=markers,
            blocker_code=None,
            replay_safety=_REPLAY_ACTIVE,
            next_safe_action="AWAIT_NEXT_OBSERVATION",
            **common,
        )

    if execution_state == "SUCCEEDED":
        if execution.exit_code != 0 or execution.finished_at is None:
            return CockpitLaneProjection(
                state=CockpitState.OUTCOME_UNKNOWN,
                state_markers=base_markers,
                blocker_code="SUCCESS_WITHOUT_TERMINAL_PROOF",
                replay_safety=_REPLAY_RECOVER,
                next_safe_action="RECOVER_RESULT_EVIDENCE_BEFORE_TRUST",
                **common,
            )
        complete, gate_blocker = _evaluate_gates(inputs.gates)
        if complete:
            return CockpitLaneProjection(
                state=CockpitState.COMPLETED_VERIFIED,
                state_markers=base_markers,
                blocker_code=None,
                replay_safety=_REPLAY_SETTLED,
                next_safe_action="RECORD_DURABLE_CHECKPOINT",
                **common,
            )
        return CockpitLaneProjection(
            state=CockpitState.TERMINAL_UNHARVESTED,
            state_markers=base_markers,
            blocker_code=gate_blocker,
            replay_safety=_REPLAY_RECONCILE,
            next_safe_action="COMPLETE_MISSING_GATE_PROOFS",
            **common,
        )

    if execution_state == "FAILED":
        if execution.exit_code is None or execution.finished_at is None:
            return CockpitLaneProjection(
                state=CockpitState.OUTCOME_UNKNOWN,
                state_markers=base_markers,
                blocker_code="FAILURE_WITHOUT_TERMINAL_PROOF",
                replay_safety=_REPLAY_RECOVER,
                next_safe_action="RECOVER_RESULT_EVIDENCE_BEFORE_TRUST",
                **common,
            )
        return CockpitLaneProjection(
            state=CockpitState.FAILED_VERIFIED,
            state_markers=base_markers,
            blocker_code=None,
            replay_safety=_REPLAY_SETTLED,
            next_safe_action="REVIEW_FAILURE_EVIDENCE_UNDER_EXISTING_AUTHORITY",
            **common,
        )

    return CockpitLaneProjection(
        state=CockpitState.UNKNOWN,
        state_markers=("UNKNOWN", "EVIDENCE_INCOMPLETE"),
        blocker_code="EXECUTION_STATE_UNSUPPORTED",
        **common,
    )


def _stale_lane(inputs: CockpitLaneInputs) -> CockpitLaneProjection:
    return CockpitLaneProjection(
        identity=inputs.identity,
        state=CockpitState.UNKNOWN,
        state_markers=("STALE", "UNKNOWN", "EVIDENCE_INCOMPLETE"),
        blocker_code="SOURCE_DRIFT_DETECTED",
        execution_id=None,
        job_id=None,
        process_identity=CockpitProcessIdentity(),
        transport_state=None,
        last_activity=None,
        last_meaningful_progress=None,
        replay_safety="REPIN_SOURCES_BEFORE_TRUST",
        next_safe_action="REPIN_BOTH_SOURCES_THEN_REPROJECT",
        gates=inputs.gates,
    )


def project_cockpit_snapshot(
    observations: CockpitObservations,
    *,
    recheck: CockpitObservations | None = None,
) -> CockpitSnapshot:
    """Project one internally consistent snapshot.

    A bounded re-pin whose observations drifted from the first pin renders
    the whole snapshot STALE instead of mixing observations from different
    identities.
    """
    if recheck is not None and recheck.lanes != observations.lanes:
        return CockpitSnapshot(
            lanes=tuple(_stale_lane(inputs) for inputs in observations.lanes),
            generated_at=observations.generated_at,
            stale=True,
            stale_reason="SOURCE_DRIFT_DETECTED",
            degraded_observability=(),
        )
    lanes = tuple(project_cockpit_lane(inputs) for inputs in observations.lanes)
    degraded = tuple(
        f"{lane.identity.lane}:DEGRADED_OBSERVABILITY"
        for lane in lanes
        if "DEGRADED_OBSERVABILITY" in lane.state_markers
    )
    return CockpitSnapshot(
        lanes=lanes,
        generated_at=observations.generated_at,
        stale=False,
        stale_reason=None,
        degraded_observability=degraded,
    )


def build_control_center_lane_inputs(snapshot) -> tuple[CockpitLaneInputs, ...]:
    """Wrap ControlCenterSnapshot workers as lane inputs with UNKNOWN truth.

    The desktop control-center authority observes worker/assignment rows
    only; execution, lease, git, and gate evidence has no accepted desktop
    read-back yet and stays explicitly unavailable.
    """
    workers = tuple(getattr(snapshot, "workers", None) or ())
    return tuple(
        CockpitLaneInputs(
            identity=CockpitLaneIdentity(
                work_order_ref=_NOT_DECLARED,
                task_ref=_NOT_DECLARED,
                topology=None,
                lane=row.worker_id,
                executor=row.worker_id,
                provider=None,
                harness=getattr(row, "runtime_id", None),
                authority_repo=None,
                execution_repo=None,
                worktree=getattr(row, "project_root_path", None),
                branch=None,
                expected_head=None,
                execution_id=None,
                lease_id=None,
                provenance="CONTROL_CENTER_SNAPSHOT",
            ),
            execution=CockpitExecutionObservation.unavailable(_PORT_UNAVAILABLE),
            lease=CockpitLeaseObservation.unavailable(_PORT_UNAVAILABLE),
            git=CockpitGitObservation.unavailable(_PORT_UNAVAILABLE),
            gates=CockpitGateEvidence(),
        )
        for row in workers
    )


def cockpit_fingerprint(snapshot: CockpitSnapshot) -> str:
    """Deterministic SHA-256 fingerprint of one rendered snapshot."""
    if not isinstance(snapshot, CockpitSnapshot):
        raise CockpitFingerprintError("FINGERPRINT_REQUIRES_COCKPIT_SNAPSHOT")

    def _encode(value):
        if isinstance(value, Enum):
            return value.value
        return str(value)

    payload = json.dumps(
        asdict(snapshot), sort_keys=True, separators=(",", ":"), default=_encode
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
