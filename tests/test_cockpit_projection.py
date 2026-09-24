"""WO-P1-424 COCKPIT-1 — focused projection / facade / UI-boundary tests.

RED-first matrix from the work order:
1. provenance mismatch cannot render RUNNING or COMPLETED_VERIFIED;
2. bounded re-pin drift returns STALE/typed blocker, never a mixed snapshot;
3. unavailable Hook/WTL/review/remote/process evidence stays explicit
   UNKNOWN/EVIDENCE_INCOMPLETE;
4. PID without exact process provenance is not authoritative running identity;
5. transport-exited/ambiguous result maps to OUTCOME_UNKNOWN or
   STALLED_RECONCILE, never success;
6. missing verify/review/merge/post-main proof cannot become complete;
7. exact accepted evidence renders COMPLETED_VERIFIED;
8. identical inputs yield deterministic snapshot/fingerprint/render data;
9. cockpit adds no command authority and no new timer;
10. real DesktopControlService read-only smoke returns a coherent snapshot
    without durable writes.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from a_conductor.desktop_control import DesktopControlService
from a_conductor.desktop_ui import cockpit_monitor_lines
from a_conductor.execution_record import (
    ExecutionProcessState,
    TransportState,
    new_execution_record,
)
from a_conductor.execution_store import SQLiteExecutionStore
from a_conductor.registry import windows_worktree_key
from a_conductor.serena_config_store import SQLiteSerenaConfigStore
from a_conductor.worker_lease import (
    LeaseMutationIntent,
    SQLiteWorkerLeaseStore,
    WorkerLeaseCandidate,
    WorkerLeaseRequest,
)

from a_conductor.cockpit_projection import (
    CockpitActivityObservation,
    CockpitExecutionObservation,
    CockpitFingerprintError,
    CockpitGateEvidence,
    CockpitGateStatus,
    CockpitGitObservation,
    CockpitLaneIdentity,
    CockpitLaneInputs,
    CockpitLeaseObservation,
    CockpitObservations,
    CockpitOriginDisplay,
    CockpitOriginObservation,
    CockpitProjectionError,
    CockpitState,
    build_control_center_lane_inputs,
    build_observed_lane_inputs,
    cockpit_fingerprint,
    project_cockpit_lane,
    project_cockpit_snapshot,
)

GENERATED_AT = "2026-09-20T10:00:00.000000Z"


def _identity(**overrides) -> CockpitLaneIdentity:
    base = dict(
        work_order_ref="WO-P1-424",
        task_ref="COCKPIT-1",
        topology="CONTROL_PLANE_ONLY",
        lane="WO-P1-424-COCKPIT1-RUNTIME-COCKPIT-001",
        executor="a-worker-01",
        provider=None,
        harness=None,
        authority_repo="aase7en/A-Wiki",
        execution_repo="aase7en/A-Wiki-Conductor",
        worktree="A:/GitHub/_worktrees/A-Wiki-Conductor-wo424-cockpit1",
        branch="feat/wo-p1-424-cockpit1-runtime-cockpit",
        expected_head="5f4f9bd3b44a5314dbd85a92872c82533efa7509",
        execution_id=None,
        lease_id=None,
    )
    base.update(overrides)
    return CockpitLaneIdentity(**base)


def _execution(**overrides) -> CockpitExecutionObservation:
    base = dict(
        available=True,
        provenance="DURABLE_EXECUTION_RECORD",
        reason=None,
        execution_id="exec-0001",
        job_id="job-0001",
        worker_id="a-worker-01",
        backend_id="backend-zcode",
        repo_root="A:/GitHub/_worktrees/A-Wiki-Conductor-wo424-cockpit1",
        branch="feat/wo-p1-424-cockpit1-runtime-cockpit",
        head_before="5f4f9bd3b44a5314dbd85a92872c82533efa7509",
        transport_state="CONNECTED",
        execution_state="RUNNING",
        pid=None,
        exit_code=None,
        started_at="2026-09-20T09:00:00.000000Z",
        finished_at=None,
        updated_at="2026-09-20T09:30:00.000000Z",
    )
    base.update(overrides)
    return CockpitExecutionObservation(**base)


def _activity(**overrides) -> CockpitActivityObservation:
    base = dict(
        available=True,
        provenance="DURABLE_MONITOR_RECORD",
        reason=None,
        work_order_ref="WO-P1-424",
        task_ref="COCKPIT-1",
        lane_ref="WO-P1-424-COCKPIT1-RUNTIME-COCKPIT-001",
        execution_id="exec-0001",
        state="WAITING_CI",
        capacity_class="BASE_MUTABLE",
        observed_at="2026-09-20T09:40:00.000000Z",
        next_recheck_at="2026-09-20T09:48:42.000000Z",
        countdown_seconds=522,
    )
    base.update(overrides)
    return CockpitActivityObservation(**base)


def _lease(**overrides) -> CockpitLeaseObservation:
    base = dict(
        available=True,
        provenance="WORKER_LEASE_STORE",
        reason=None,
        lease_id="lease-0001",
        worktree_key="A:/GitHub/_worktrees/A-Wiki-Conductor-wo424-cockpit1",
        branch="feat/wo-p1-424-cockpit1-runtime-cockpit",
        expected_head="5f4f9bd3b44a5314dbd85a92872c82533efa7509",
        health="ACTIVE",
        acquired_at="2026-09-20T08:00:00.000000Z",
        heartbeat_at="2026-09-20T09:00:00.000000Z",
        expires_at=None,
    )
    base.update(overrides)
    return CockpitLeaseObservation(**base)


def _git(**overrides) -> CockpitGitObservation:
    base = dict(
        available=True,
        provenance="LOCAL_GIT_OBSERVATION",
        reason=None,
        branch="feat/wo-p1-424-cockpit1-runtime-cockpit",
        head="5f4f9bd3b44a5314dbd85a92872c82533efa7509",
        dirty_state="CLEAN",
    )
    base.update(overrides)
    return CockpitGitObservation(**base)


def _gates(**overrides) -> CockpitGateEvidence:
    base = dict(
        verification=CockpitGateStatus.UNKNOWN,
        review=CockpitGateStatus.NOT_REQUIRED,
        merge=CockpitGateStatus.UNKNOWN,
        post_main=CockpitGateStatus.UNKNOWN,
        ci=CockpitGateStatus.UNKNOWN,
        provenance="OPERATOR_DECLARED",
    )
    base.update(overrides)
    return CockpitGateEvidence(**base)


def _inputs(
    identity=None,
    execution=None,
    lease=None,
    git=None,
    gates=None,
    origin=None,
    activity=None,
) -> CockpitLaneInputs:
    return CockpitLaneInputs(
        identity=identity or _identity(),
        execution=execution if execution is not None else CockpitExecutionObservation.unavailable(
            reason="PORT_UNAVAILABLE"
        ),
        lease=lease if lease is not None else CockpitLeaseObservation.unavailable(
            reason="PORT_UNAVAILABLE"
        ),
        git=git if git is not None else CockpitGitObservation.unavailable(
            reason="PORT_UNAVAILABLE"
        ),
        gates=gates if gates is not None else _gates(),
        origin=origin if origin is not None else CockpitOriginObservation.unavailable(
            reason="PORT_UNAVAILABLE"
        ),
        activity=(
            activity
            if activity is not None
            else CockpitActivityObservation.unavailable(reason="PORT_UNAVAILABLE")
        ),
    )


def _unavailable_execution() -> CockpitExecutionObservation:
    return CockpitExecutionObservation.unavailable(reason="PORT_UNAVAILABLE")


# ---------------------------------------------------------------- Model 1


def test_provenance_mismatch_cannot_render_running_or_completed() -> None:
    identity = _identity()
    # execution record pinned to a foreign worktree/head
    foreign = _execution(
        repo_root="A:/GitHub/_worktrees/somewhere-else",
        head_before="0000000000000000000000000000000000000000",
    )

    lane = project_cockpit_lane(_inputs(identity=identity, execution=foreign))

    assert lane.state is not CockpitState.RUNNING
    assert lane.state is not CockpitState.COMPLETED_VERIFIED
    assert "EVIDENCE_INCOMPLETE" in lane.state_markers
    assert lane.blocker_code == "EXECUTION_PROVENANCE_MISMATCH"

    # same for a positively-verified completion observed on a foreign identity
    completed_foreign = foreign
    object.__setattr__(
        completed_foreign, "execution_state", "SUCCEEDED"
    )
    object.__setattr__(completed_foreign, "finished_at", GENERATED_AT)
    gates = _gates(
        verification=CockpitGateStatus.PROVEN,
        review=CockpitGateStatus.NOT_REQUIRED,
        merge=CockpitGateStatus.PROVEN,
        post_main=CockpitGateStatus.PROVEN,
        ci=CockpitGateStatus.PROVEN,
    )
    lane = project_cockpit_lane(
        _inputs(identity=identity, execution=completed_foreign, gates=gates)
    )
    assert lane.state is not CockpitState.COMPLETED_VERIFIED
    assert lane.blocker_code == "EXECUTION_PROVENANCE_MISMATCH"


def test_lease_provenance_mismatch_never_running() -> None:
    identity = _identity()
    foreign_lease = _lease(
        worktree_key="A:/GitHub/_worktrees/somewhere-else",
        expected_head="1111111111111111111111111111111111111111",
    )

    lane = project_cockpit_lane(
        _inputs(identity=identity, execution=_execution(), lease=foreign_lease)
    )

    assert lane.state is not CockpitState.RUNNING
    assert lane.blocker_code == "LEASE_PROVENANCE_MISMATCH"


# ---------------------------------------------------------------- Model 2


def test_repin_drift_renders_stale_never_mixed_snapshot() -> None:
    first = CockpitObservations(
        lanes=(_inputs(execution=_execution()),),
        generated_at=GENERATED_AT,
    )
    drifted = CockpitObservations(
        lanes=(
            _inputs(
                execution=_execution(
                    execution_state="PROCESS_EXITED_UNKNOWN_RESULT",
                    transport_state="LOST",
                )
            ),
        ),
        generated_at=GENERATED_AT,
    )

    snapshot = project_cockpit_snapshot(first, recheck=drifted)

    assert snapshot.stale is True
    assert snapshot.stale_reason == "SOURCE_DRIFT_DETECTED"
    lane = snapshot.lanes[0]
    assert lane.state is CockpitState.UNKNOWN
    assert "STALE" in lane.state_markers
    assert "EVIDENCE_INCOMPLETE" in lane.state_markers
    # no field mixes an observation from either pin
    assert lane.execution_id is None
    assert lane.last_activity is None


def test_repin_identical_observations_are_not_stale() -> None:
    first = CockpitObservations(
        lanes=(_inputs(execution=_execution()),), generated_at=GENERATED_AT
    )

    snapshot = project_cockpit_snapshot(first, recheck=replace(first))

    assert snapshot.stale is False
    assert snapshot.lanes[0].state is CockpitState.RUNNING


# ---------------------------------------------------------------- Model 3


def test_unavailable_evidence_stays_unknown_evidence_incomplete() -> None:
    lane = project_cockpit_lane(_inputs())

    assert lane.state is CockpitState.UNKNOWN
    assert "UNKNOWN" in lane.state_markers
    assert "EVIDENCE_INCOMPLETE" in lane.state_markers
    assert lane.blocker_code == "EXECUTION_EVIDENCE_UNAVAILABLE"
    # Hook/WTL authorities are not accepted: fields stay UNKNOWN by contract
    assert lane.hook_state == "UNKNOWN"
    assert lane.wtl_state == "UNKNOWN"
    assert "Hook read-back authority not accepted" in lane.hook_reason
    assert "WTL read-back authority not accepted" in lane.wtl_reason


def test_missing_review_evidence_is_not_success() -> None:
    gates = _gates(
        verification=CockpitGateStatus.PROVEN,
        review=CockpitGateStatus.UNKNOWN,
        merge=CockpitGateStatus.PROVEN,
        post_main=CockpitGateStatus.PROVEN,
    )
    lane = project_cockpit_lane(
        _inputs(
            execution=_execution(
                execution_state="SUCCEEDED",
                finished_at=GENERATED_AT,
                exit_code=0,
            ),
            gates=gates,
        )
    )

    assert lane.state is not CockpitState.COMPLETED_VERIFIED
    assert lane.state is CockpitState.TERMINAL_UNHARVESTED
    assert "MISSING_REVIEW_PROOF" in (lane.blocker_code or "")


# ---------------------------------------------------------------- Model 4


def test_pid_without_exact_provenance_is_not_authoritative() -> None:
    # an unproven pid observation (operator-declared only) cannot make RUNNING
    execution = _execution(
        pid=4242,
        provenance="OPERATOR_DECLARED",
    )
    lane = project_cockpit_lane(_inputs(execution=execution))

    assert lane.process_identity.pid == 4242
    assert lane.process_identity.authoritative is False
    assert lane.process_identity.provenance == "OPERATOR_DECLARED"
    # unproven provenance also fails the identity gate -> never RUNNING
    assert lane.state is not CockpitState.RUNNING

    # a durable-record pid on a matched identity is authoritative
    proven = project_cockpit_lane(_inputs(execution=_execution(pid=4242)))
    assert proven.process_identity.authoritative is True
    assert proven.process_identity.provenance == "DURABLE_EXECUTION_RECORD"


def test_pid_existence_alone_does_not_create_running_state() -> None:
    # execution finished with exit 0 but a stray pid is recorded
    lane = project_cockpit_lane(
        _inputs(
            execution=_execution(
                execution_state="PROCESS_EXITED_UNKNOWN_RESULT",
                transport_state="LOST",
                pid=4242,
            )
        )
    )

    assert lane.state is CockpitState.OUTCOME_UNKNOWN


# ---------------------------------------------------------------- Model 5


def test_transport_exited_or_ambiguous_maps_to_outcome_unknown() -> None:
    lane = project_cockpit_lane(
        _inputs(
            execution=_execution(
                execution_state="PROCESS_EXITED_UNKNOWN_RESULT",
                transport_state="LOST",
            )
        )
    )
    assert lane.state is CockpitState.OUTCOME_UNKNOWN
    assert "RECOVER_POINTER_PROCESS_RESULT_GIT_BEFORE_REDISPATCH" == lane.replay_safety


def test_transport_lost_while_running_maps_to_stalled_reconcile() -> None:
    lane = project_cockpit_lane(
        _inputs(execution=_execution(transport_state="LOST"))
    )
    assert lane.state is CockpitState.STALLED_RECONCILE
    assert lane.blocker_code == "TRANSPORT_LOST"
    # never label retry safe merely because transport disconnected
    assert "REDISPATCH" not in lane.next_safe_action or "RECOVER" in lane.next_safe_action


def test_degraded_transport_still_running_with_marker() -> None:
    lane = project_cockpit_lane(
        _inputs(execution=_execution(transport_state="DEGRADED"))
    )
    assert lane.state is CockpitState.RUNNING
    assert "DEGRADED_OBSERVABILITY" in lane.state_markers


# ---------------------------------------------------------------- Model 6


@pytest.mark.parametrize(
    "gates_overrides",
    [
        {"verification": CockpitGateStatus.UNKNOWN},
        {"review": CockpitGateStatus.UNKNOWN},
        {"review": CockpitGateStatus.REFUTED},
        {"merge": CockpitGateStatus.UNKNOWN},
        {"post_main": CockpitGateStatus.UNKNOWN},
        {"verification": CockpitGateStatus.REFUTED},
    ],
)
def test_missing_gate_proof_cannot_become_complete(gates_overrides) -> None:
    gates = _gates(
        verification=CockpitGateStatus.PROVEN,
        review=CockpitGateStatus.NOT_REQUIRED,
        merge=CockpitGateStatus.PROVEN,
        post_main=CockpitGateStatus.PROVEN,
        ci=CockpitGateStatus.PROVEN,
    )
    gates = replace(gates, **gates_overrides)
    lane = project_cockpit_lane(
        _inputs(
            execution=_execution(
                execution_state="SUCCEEDED",
                exit_code=0,
                finished_at=GENERATED_AT,
            ),
            gates=gates,
        )
    )
    assert lane.state is not CockpitState.COMPLETED_VERIFIED


# ---------------------------------------------------------------- Model 7


def test_accepted_evidence_renders_completed_verified() -> None:
    gates = _gates(
        verification=CockpitGateStatus.PROVEN,
        review=CockpitGateStatus.PROVEN,
        merge=CockpitGateStatus.PROVEN,
        post_main=CockpitGateStatus.PROVEN,
        ci=CockpitGateStatus.PROVEN,
        provenance="DURABLE_GATE_RECORD",
    )
    lane = project_cockpit_lane(
        _inputs(
            execution=_execution(
                execution_state="SUCCEEDED",
                exit_code=0,
                finished_at=GENERATED_AT,
            ),
            gates=gates,
        )
    )

    assert lane.state is CockpitState.COMPLETED_VERIFIED
    assert lane.blocker_code is None


def test_operator_declared_gates_never_reach_completed_verified() -> None:
    # P2 regression: operator-declared/untrusted gate evidence must never
    # produce COMPLETED_VERIFIED even when every gate is PROVEN.
    gates = _gates(
        verification=CockpitGateStatus.PROVEN,
        review=CockpitGateStatus.PROVEN,
        merge=CockpitGateStatus.PROVEN,
        post_main=CockpitGateStatus.PROVEN,
        ci=CockpitGateStatus.PROVEN,
        provenance="OPERATOR_DECLARED",
    )
    lane = project_cockpit_lane(
        _inputs(
            execution=_execution(
                execution_state="SUCCEEDED",
                exit_code=0,
                finished_at=GENERATED_AT,
            ),
            gates=gates,
        )
    )

    assert lane.state is CockpitState.TERMINAL_UNHARVESTED
    assert lane.state is not CockpitState.COMPLETED_VERIFIED
    assert lane.blocker_code == "GATE_PROVENANCE_NOT_AUTHORITATIVE"


def test_gate_evidence_rejects_unknown_provenance_tag() -> None:
    with pytest.raises(CockpitProjectionError):
        CockpitGateEvidence(provenance="SOME_RANDOM_TRUST_TAG")


def test_lifecycle_vocabulary_mapping() -> None:
    # dispatched-not-yet-running waits externally
    lane = project_cockpit_lane(
        _inputs(execution=_execution(execution_state="QUEUED"))
    )
    assert lane.state is CockpitState.WAITING_EXTERNAL

    # record positively absent + active matched lease => scope pending
    lane = project_cockpit_lane(
        _inputs(
            execution=CockpitExecutionObservation.unavailable(
                reason="RECORD_NOT_FOUND"
            ),
            lease=_lease(),
        )
    )
    assert lane.state is CockpitState.PENDING_SCOPE

    # record positively absent without a lease => not dispatched
    lane = project_cockpit_lane(
        _inputs(
            execution=CockpitExecutionObservation.unavailable(
                reason="RECORD_NOT_FOUND"
            )
        )
    )
    assert lane.state is CockpitState.NOT_DISPATCHED

    # verified failure
    lane = project_cockpit_lane(
        _inputs(
            execution=_execution(
                execution_state="FAILED", exit_code=1, finished_at=GENERATED_AT
            )
        )
    )
    assert lane.state is CockpitState.FAILED_VERIFIED

    # failure without exit proof stays unknown
    lane = project_cockpit_lane(
        _inputs(execution=_execution(execution_state="FAILED"))
    )
    assert lane.state is CockpitState.OUTCOME_UNKNOWN

    # recovery/verification required => reconcile
    lane = project_cockpit_lane(
        _inputs(execution=_execution(execution_state="RECOVERY_REQUIRED"))
    )
    assert lane.state is CockpitState.STALLED_RECONCILE


# --------------------------------------------------------- WO-P1-537 waits


def test_durable_wait_activity_distinguishes_ci_from_running_and_renders_countdown() -> None:
    lane = project_cockpit_lane(
        _inputs(execution=_execution(), activity=_activity()), generated_at=GENERATED_AT
    )
    assert lane.state is CockpitState.WAITING_CI
    assert lane.capacity_class == "BASE_MUTABLE"
    assert lane.countdown_seconds == 0
    assert lane.next_recheck_at == "2026-09-20T09:48:42.000000Z"
    assert lane.last_activity == "2026-09-20T09:40:00.000000Z"

    snapshot = project_cockpit_snapshot(
        CockpitObservations(
            lanes=(_inputs(execution=_execution(), activity=_activity()),),
            generated_at=GENERATED_AT,
        )
    )
    text = "\n".join(cockpit_monitor_lines(snapshot))
    assert "state: WAITING_CI" in text
    assert "countdown: 00:00" in text
    assert "recheck: 2026-09-20T09:48:42.000000Z" in text


def test_activity_countdown_is_recomputed_at_snapshot_time() -> None:
    lane = project_cockpit_lane(
        _inputs(
            execution=_execution(),
            activity=_activity(
                observed_at="2026-09-20T09:55:00.000000Z",
                next_recheck_at="2026-09-20T10:10:00.000000Z",
                countdown_seconds=900,
            ),
        ),
        generated_at=GENERATED_AT,
    )

    assert lane.countdown_seconds == 600

    without_absolute_time = project_cockpit_lane(
        _inputs(
            execution=_execution(),
            activity=_activity(
                observed_at="2026-09-20T09:55:00.000000Z",
                next_recheck_at=None,
                countdown_seconds=900,
            ),
        ),
        generated_at=GENERATED_AT,
    )
    assert without_absolute_time.countdown_seconds == 600


def test_cooldown_is_not_generic_running() -> None:
    lane = project_cockpit_lane(
        _inputs(
            execution=_execution(),
            activity=_activity(
                state="COOLDOWN",
                reason="UPSTREAM_PROVIDER_THROTTLED",
                countdown_seconds=660,
            ),
        ),
        generated_at=GENERATED_AT,
    )
    assert lane.state is CockpitState.COOLDOWN
    assert lane.wait_reason == "UPSTREAM_PROVIDER_THROTTLED"
    assert lane.state is not CockpitState.RUNNING


@pytest.mark.parametrize(
    "state,expected_action",
    (
        ("WAITING_APPROVAL", "AWAIT_APPROVAL_THEN_REPROJECT"),
        ("WAITING_GLM", "AWAIT_GLM_CHILD_THEN_RECONCILE"),
        ("WAITING_JEV", "AWAIT_JEV_ADVISORY_THEN_REPROJECT"),
    ),
)
def test_explicit_wait_states_render_as_waits_not_running(
    state: str, expected_action: str
) -> None:
    lane = project_cockpit_lane(
        _inputs(
            execution=_execution(),
            activity=_activity(state=state, reason=f"{state}_REASON"),
        ),
        generated_at=GENERATED_AT,
    )
    assert lane.state.value == state
    assert lane.state is not CockpitState.RUNNING
    assert lane.next_safe_action == expected_action


def test_borrowed_active_and_parked_capacity_are_distinct() -> None:
    active = project_cockpit_lane(
        _inputs(
            execution=_execution(),
            activity=_activity(
                state="BORROWED_ACTIVE",
                capacity_class="BORROWED_MUTABLE",
                countdown_seconds=None,
                next_recheck_at=None,
            ),
        ),
        generated_at=GENERATED_AT,
    )
    assert active.state is CockpitState.BORROWED_ACTIVE

    parked = project_cockpit_lane(
        _inputs(
            activity=_activity(
                state="PARKED_CAPACITY",
                capacity_class="BORROWED_MUTABLE",
                reason="BASE_LANE_RESUME_CAPACITY",
                countdown_seconds=None,
                next_recheck_at=None,
            )
        ),
        generated_at=GENERATED_AT,
    )
    assert parked.state is CockpitState.PARKED_CAPACITY
    assert parked.replay_safety == "PARKED_CLAIM_NEVER_DUPLICATE"


def test_activity_identity_mismatch_cannot_override_execution() -> None:
    lane = project_cockpit_lane(
        _inputs(execution=_execution(), activity=_activity(work_order_ref="WO-FOREIGN")),
        generated_at=GENERATED_AT,
    )
    assert lane.state is CockpitState.RUNNING
    assert lane.blocker_code is None
    assert lane.wait_reason is None


def test_activity_without_projection_time_fails_closed() -> None:
    lane = project_cockpit_lane(
        _inputs(execution=_execution(), activity=_activity())
    )
    assert lane.state is CockpitState.RUNNING
    assert lane.wait_reason is None
    assert lane.next_recheck_at is None
    assert lane.countdown_seconds is None
    assert lane.capacity_class is None


@pytest.mark.parametrize(
    "execution_state,transport_state,expected",
    (
        ("FAILED", "CONNECTED", CockpitState.FAILED_VERIFIED),
        ("SUCCEEDED", "CONNECTED", CockpitState.TERMINAL_UNHARVESTED),
        ("RECOVERY_REQUIRED", "CONNECTED", CockpitState.STALLED_RECONCILE),
        ("PROCESS_EXITED_UNKNOWN_RESULT", "CONNECTED", CockpitState.OUTCOME_UNKNOWN),
        ("RUNNING", "LOST", CockpitState.STALLED_RECONCILE),
        ("RUNNING", "DEGRADED", CockpitState.RUNNING),
    ),
)
def test_activity_never_overrides_exact_execution_lifecycle(
    execution_state, transport_state, expected
) -> None:
    terminal = _execution(
        execution_state=execution_state,
        transport_state=transport_state,
        exit_code=(1 if execution_state == "FAILED" else 0)
        if execution_state in {"FAILED", "SUCCEEDED"}
        else None,
        finished_at="2026-09-20T09:59:00.000000Z"
        if execution_state in {"FAILED", "SUCCEEDED"}
        else None,
    )
    lane = project_cockpit_lane(
        _inputs(
            execution=terminal,
            activity=_activity(
                state="BORROWED_ACTIVE",
                capacity_class="BORROWED_MUTABLE",
                reason="DO_NOT_LEAK_THIS",
            ),
        ),
        generated_at=GENERATED_AT,
    )
    assert lane.state is expected
    assert lane.wait_reason is None
    assert lane.next_recheck_at is None
    assert lane.countdown_seconds is None
    assert lane.capacity_class is None


@pytest.mark.parametrize(
    "overrides",
    (
        {"execution_id": None},
        {"execution_id": "stale-execution"},
        {"observed_at": "2026-09-20T10:00:01Z"},
        {"observed_at": "not-a-timestamp"},
        {"observed_at": "2026-09-20T09:00:00Z"},
    ),
)
def test_rejected_activity_cannot_leak_details_or_override_execution(overrides) -> None:
    activity = _activity(
        reason="DO_NOT_LEAK_THIS",
        **overrides,
    )
    lane = project_cockpit_lane(
        _inputs(execution=_execution(), activity=activity), generated_at=GENERATED_AT
    )
    assert lane.state is CockpitState.RUNNING
    assert lane.wait_reason is None
    assert lane.next_recheck_at is None
    assert lane.countdown_seconds is None
    assert lane.capacity_class is None


@pytest.mark.parametrize(
    "kwargs",
    (
        {"provenance": "OPERATOR_DECLARED"},
        {"state": "SOMETHING_ELSE"},
        {"reason": "free form reason"},
        {"countdown_seconds": -1},
    ),
)
def test_activity_observation_rejects_untrusted_or_invalid_fields(kwargs) -> None:
    with pytest.raises(CockpitProjectionError):
        _activity(**kwargs)


def test_running_activity_cannot_claim_borrowed_mutable_capacity() -> None:
    with pytest.raises(CockpitProjectionError, match="ACTIVITY_RUNNING_BORROWED_CLASS_INVALID"):
        _activity(state="RUNNING", capacity_class="BORROWED_MUTABLE")


def test_monitor_capacity_line_shows_base_borrowed_parked_review_and_waits() -> None:
    base_run = _inputs(
        execution=_execution(),
        activity=_activity(
            state="RUNNING", capacity_class="BASE_MUTABLE",
            countdown_seconds=None, next_recheck_at=None,
        ),
    )
    borrowed = _inputs(
        identity=_identity(lane="borrowed", work_order_ref="WO-B", task_ref="B"),
        execution=_execution(),
        activity=_activity(
            work_order_ref="WO-B", task_ref="B", lane_ref="borrowed",
            state="BORROWED_ACTIVE", capacity_class="BORROWED_MUTABLE",
            countdown_seconds=None, next_recheck_at=None,
        ),
    )
    parked = _inputs(
        identity=_identity(lane="parked", work_order_ref="WO-P", task_ref="P"),
        activity=_activity(
            work_order_ref="WO-P", task_ref="P", lane_ref="parked",
            execution_id=None, state="PARKED_CAPACITY",
            capacity_class="BORROWED_MUTABLE",
            countdown_seconds=None, next_recheck_at=None,
        ),
    )
    review = _inputs(
        identity=_identity(lane="review", work_order_ref="WO-R", task_ref="R"),
        execution=_execution(),
        activity=_activity(
            work_order_ref="WO-R", task_ref="R", lane_ref="review",
            state="RUNNING", capacity_class="INDEPENDENT_REVIEW",
            countdown_seconds=None, next_recheck_at=None,
        ),
    )
    waiting = _inputs(
        identity=_identity(lane="wait", work_order_ref="WO-W", task_ref="W"),
        execution=_execution(),
        activity=_activity(
            work_order_ref="WO-W", task_ref="W", lane_ref="wait",
            state="WAITING_EXTERNAL", capacity_class="BASE_MUTABLE",
        ),
    )
    snap = project_cockpit_snapshot(
        CockpitObservations(
            lanes=(base_run, borrowed, parked, review, waiting),
            generated_at=GENERATED_AT,
        )
    )
    text = "\n".join(cockpit_monitor_lines(snap))
    assert (
        "capacity observed: base-active=1/3 borrowed-active=1/2 "
        "parked=1 review=1/1 waits=1"
    ) in text


def test_monitor_capacity_counts_waiting_glm_active_child_and_marks_ambiguity() -> None:
    active_child = _inputs(
        execution=_execution(),
        activity=_activity(
            state="WAITING_GLM",
            active_mutation_child=True,
            reason="GLM_CHILD_ACTIVE",
        ),
    )
    unknown_child = _inputs(
        identity=_identity(lane="unknown-child"),
        execution=_execution(),
        activity=_activity(
            lane_ref="unknown-child",
            state="WAITING_GLM",
            active_mutation_child=None,
            reason="GLM_CHILD_STATUS_UNKNOWN",
        ),
    )
    snapshot = project_cockpit_snapshot(
        CockpitObservations(
            lanes=(active_child, unknown_child), generated_at=GENERATED_AT
        )
    )
    text = "\n".join(cockpit_monitor_lines(snapshot))
    assert "base-active=1/3 (+1 unknown-active)" in text


def test_monitor_capacity_reports_lanes_without_capacity_evidence() -> None:
    classified = _inputs(
        execution=_execution(),
        activity=_activity(
            state="RUNNING",
            capacity_class="BASE_MUTABLE",
            countdown_seconds=None,
            next_recheck_at=None,
        ),
    )
    unclassified = _inputs(
        identity=_identity(lane="unclassified"), execution=_execution()
    )
    snapshot = project_cockpit_snapshot(
        CockpitObservations(
            lanes=(classified, unclassified), generated_at=GENERATED_AT
        )
    )

    text = "\n".join(cockpit_monitor_lines(snapshot))

    assert "base-active=1/3" in text
    assert "unclassified=1" in text


# ---------------------------------------------------------------- Model 8


def test_identical_inputs_deterministic_snapshot_and_fingerprint() -> None:
    first = CockpitObservations(
        lanes=(
            _inputs(execution=_execution()),
            _inputs(identity=_identity(lane="other-lane", work_order_ref="WO-2")),
        ),
        generated_at=GENERATED_AT,
    )
    second = replace(first)

    snap_a = project_cockpit_snapshot(first)
    snap_b = project_cockpit_snapshot(second)

    assert snap_a == snap_b
    assert cockpit_fingerprint(snap_a) == cockpit_fingerprint(snap_b)
    assert cockpit_monitor_lines(snap_a) == cockpit_monitor_lines(snap_b)
    assert len(cockpit_fingerprint(snap_a)) == 64


def test_fingerprint_rejects_foreign_object() -> None:
    with pytest.raises(CockpitFingerprintError):
        cockpit_fingerprint(object())


def test_projection_rejects_invalid_inputs() -> None:
    with pytest.raises(CockpitProjectionError):
        CockpitLaneIdentity(work_order_ref="", task_ref=None)
    with pytest.raises(CockpitProjectionError):
        _execution(transport_state="SOMETHING_WEIRD")
    with pytest.raises(CockpitProjectionError):
        _execution(execution_state="ALSO_WEIRD")
    with pytest.raises(CockpitProjectionError):
        _execution(available=True, provenance="OPERATOR_DECLARED")
    with pytest.raises(CockpitProjectionError):
        CockpitGateEvidence(provenance="MYSTERY_AUTHORITY")


def test_durable_execution_vocabulary_maps_without_inventing_lifecycle() -> None:
    # every accepted SQLiteExecutionStore state projects to an existing
    # operator vocabulary entry, fail-closed
    cases = (
        ("STARTING", "CONNECTED", CockpitState.WAITING_EXTERNAL),
        ("PROCESS_STILL_RUNNING", "CONNECTED", CockpitState.RUNNING),
        ("VERIFICATION_REQUIRED", "CONNECTED", CockpitState.TERMINAL_UNHARVESTED),
        ("PARTIAL", "CONNECTED", CockpitState.OUTCOME_UNKNOWN),
        ("CANCELLED", "CONNECTED", CockpitState.TERMINAL_UNHARVESTED),
        ("PROCESS_EXITED_UNKNOWN_RESULT", "LOST", CockpitState.OUTCOME_UNKNOWN),
    )
    for execution_state, transport_state, expected in cases:
        lane = project_cockpit_lane(
            _inputs(
                execution=_execution(
                    execution_state=execution_state,
                    transport_state=transport_state,
                )
            )
        )
        assert lane.state is expected, execution_state

    # transport UNAVAILABLE while the durable record says the process runs:
    # still RUNNING, explicitly degraded observability
    lane = project_cockpit_lane(
        _inputs(
            execution=_execution(
                execution_state="PROCESS_STILL_RUNNING",
                transport_state="UNAVAILABLE",
            )
        )
    )
    assert lane.state is CockpitState.RUNNING
    assert "DEGRADED_OBSERVABILITY" in lane.state_markers
    assert lane.state is not CockpitState.COMPLETED_VERIFIED


# ---------------------------------------------------------------- Model 9


def test_no_cockpit_command_authority_or_new_timer() -> None:
    # the projection module defines no command/mutation surface at all
    import a_conductor.cockpit_projection as module

    public = {
        name
        for name in dir(module)
        if not name.startswith("_")
    }
    forbidden_words = ("retry", "dispatch", "cancel", "restart", "merge", "cleanup", "reassign")
    for name in public:
        assert not any(word in name.lower() for word in forbidden_words), name

    # facade exposes exactly one read-only cockpit seam
    facade_methods = [
        name
        for name in dir(DesktopControlService)
        if "cockpit" in name.lower()
    ]
    assert facade_methods == ["cockpit_projection"]

    # UI gains a monitor mode, not a second timer: the cockpit refresh reuses
    # the single existing _monitor_tick cadence
    import inspect

    import a_conductor.desktop_ui as ui

    source = inspect.getsource(ui.AConductorDesktopApp._refresh_cockpit_monitor_async)
    assert "after(" not in source
    tick = inspect.getsource(ui.AConductorDesktopApp._monitor_tick)
    assert tick.count("_schedule_after") == 1


def test_render_lines_are_copyable_and_truthful() -> None:
    snapshot = project_cockpit_snapshot(
        CockpitObservations(
            lanes=(_inputs(execution=_execution(pid=4242)),),
            generated_at=GENERATED_AT,
        )
    )
    text = "\n".join(cockpit_monitor_lines(snapshot))

    assert "MONITOR · COCKPIT" in text
    assert "WO-P1-424" in text
    assert "RUNNING" in text
    assert "PID 4242" in text
    # UNKNOWN hook/wtl truth is explicit on screen
    assert "HOOK: UNKNOWN" in text
    assert "WTL: UNKNOWN" in text


def test_render_lines_stale_snapshot() -> None:
    first = CockpitObservations(
        lanes=(_inputs(execution=_execution()),), generated_at=GENERATED_AT
    )
    drifted = CockpitObservations(
        lanes=(
            _inputs(execution=_execution(pid=999)),
        ),
        generated_at=GENERATED_AT,
    )
    snapshot = project_cockpit_snapshot(first, recheck=drifted)

    text = "\n".join(cockpit_monitor_lines(snapshot))

    assert "STALE" in text
    assert "SOURCE_DRIFT_DETECTED" in text


# ---------------------------------------------------------------- Model 10


class NullControl:
    def snapshot(self):
        raise AssertionError("snapshot not expected here")


class NullLifecycle:
    def execute(self, worker_id, action):
        raise AssertionError("lifecycle not expected")


def _real_service(tmp_path: Path) -> DesktopControlService:
    database = tmp_path / "control.sqlite"
    settings = SQLiteSerenaConfigStore(database)
    settings.initialize()
    return DesktopControlService(
        control_center=NullControl(),
        lifecycle=NullLifecycle(),
        settings_store=settings,
        instances_root=tmp_path,
    )


class CountingControl:
    def __init__(self) -> None:
        self.snapshot_obj = object.__new__(__import__(
            "a_conductor.control_center", fromlist=["ControlCenterSnapshot"]
        ).ControlCenterSnapshot)
        object.__setattr__(self.snapshot_obj, "projects", ())
        object.__setattr__(self.snapshot_obj, "workers", ())
        object.__setattr__(self.snapshot_obj, "online", True)
        self.calls = 0

    def snapshot(self):
        self.calls += 1
        return self.snapshot_obj


def _service_with_control(tmp_path: Path, control) -> DesktopControlService:
    database = tmp_path / "control.sqlite"
    settings = SQLiteSerenaConfigStore(database)
    settings.initialize()
    return DesktopControlService(
        control_center=control,
        lifecycle=NullLifecycle(),
        settings_store=settings,
        instances_root=tmp_path,
    )


def test_real_service_smoke_coherent_snapshot_without_durable_writes(
    tmp_path: Path,
) -> None:
    control = CountingControl()
    service = _service_with_control(tmp_path, control)
    database = service.settings_store.database_path

    def _db_fingerprint() -> tuple:
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        try:
            rows = connection.execute(
                "SELECT name FROM sqlite_master ORDER BY name"
            ).fetchall()
            page_count = connection.execute("PRAGMA page_count").fetchone()[0]
            change_counter = connection.execute(
                "PRAGMA header_format"
            ).fetchone() if False else None
            return tuple(rows), page_count
        finally:
            connection.close()

    before = _db_fingerprint()

    snapshot = service.cockpit_projection(generated_at=GENERATED_AT)

    after = _db_fingerprint()

    assert snapshot.stale is False
    assert snapshot.degraded_observability == ("ACTIVITY_READER_UNAVAILABLE",)
    assert snapshot.lanes == ()
    assert control.calls == 2  # bounded first pin + recheck pin
    assert before == after


def test_facade_composes_control_center_lanes_with_unknown_truths(
    tmp_path: Path,
) -> None:
    from a_conductor.control_center import ControlCenterSnapshot, WorkerScreenRow
    from a_conductor.domain import WorkerState

    row = WorkerScreenRow(
        worker_id="a-worker-01",
        display_name="SunDay Worker 1",
        state=WorkerState.BUSY,
        runtime_id="serena",
        assignment_id="assignment-1",
        project_id="project-1",
        project_display_name="A-Wiki-Conductor",
        project_root_path="A:/GitHub/A-Wiki-Conductor",
        mutation_allowed=True,
    )

    class StaticControl:
        def snapshot(self):
            return ControlCenterSnapshot(projects=(), workers=(row,))

    service = _service_with_control(tmp_path, StaticControl())

    snapshot = service.cockpit_projection(generated_at=GENERATED_AT)

    assert len(snapshot.lanes) == 1
    lane = snapshot.lanes[0]
    assert lane.identity.lane == "a-worker-01"
    assert lane.identity.provenance == "CONTROL_CENTER_SNAPSHOT"
    # fields without an accepted desktop authority stay UNKNOWN
    assert lane.state is CockpitState.UNKNOWN
    assert lane.blocker_code == "EXECUTION_EVIDENCE_UNAVAILABLE"
    assert lane.hook_state == "UNKNOWN"
    assert lane.wtl_state == "UNKNOWN"
    text = "\n".join(cockpit_monitor_lines(snapshot))
    assert "a-worker-01" in text


def test_build_control_center_lane_inputs_maps_workers_only() -> None:
    from a_conductor.control_center import ControlCenterSnapshot, WorkerScreenRow
    from a_conductor.domain import WorkerState

    row = WorkerScreenRow(
        worker_id="a-worker-02",
        display_name="Worker 2",
        state=WorkerState.READY,
        runtime_id=None,
        assignment_id=None,
        project_id=None,
        project_display_name=None,
        project_root_path=None,
        mutation_allowed=None,
    )
    snapshot = ControlCenterSnapshot(projects=(), workers=(row,))

    inputs = build_control_center_lane_inputs(snapshot)

    assert len(inputs) == 1
    assert inputs[0].identity.lane == "a-worker-02"
    assert inputs[0].identity.executor == "Worker 2"
    assert inputs[0].identity.provenance == "CONTROL_CENTER_SNAPSHOT"
    assert inputs[0].execution.available is False
    assert inputs[0].execution.reason == "PORT_UNAVAILABLE"


# ------------------------------------- bound durable authority (R2 repair P1)


_WORKER_ID = "a-worker-01"
_LEASE_WORKER_ID = "a-worker-02"
_REPO_ROOT = "A:/GitHub/_worktrees/A-Wiki-Conductor-wo424-run"
_BRANCH = "feat/wo-p1-424-cockpit1-runtime-cockpit"
_HEAD = "5f4f9bd3b44a5314dbd85a92872c82533efa7509"
_FIXED_NOW = datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc)
_LEASE_EXPIRES = "2026-09-20T10:05:00.000000Z"


def _authority_row(worker_id: str, project_root: str | None):
    from a_conductor.control_center import WorkerScreenRow
    from a_conductor.domain import WorkerState

    return WorkerScreenRow(
        worker_id=worker_id,
        display_name=f"SunDay Worker {worker_id[-1]}",
        state=WorkerState.BUSY,
        runtime_id="serena",
        assignment_id="assignment-1",
        project_id="project-1",
        project_display_name="A-Wiki-Conductor",
        project_root_path=project_root,
        mutation_allowed=True,
    )


class StaticRowsControl:
    def __init__(self, rows) -> None:
        self._rows = tuple(rows)
        self.calls = 0

    def snapshot(self):
        self.calls += 1
        from a_conductor.control_center import ControlCenterSnapshot

        return ControlCenterSnapshot(projects=(), workers=self._rows)


class DriftingRowsControl:
    def __init__(self, first_rows, recheck_rows) -> None:
        self._first = tuple(first_rows)
        self._recheck = tuple(recheck_rows)
        self.calls = 0

    def snapshot(self):
        self.calls += 1
        from a_conductor.control_center import ControlCenterSnapshot

        rows = self._first if self.calls == 1 else self._recheck
        return ControlCenterSnapshot(projects=(), workers=rows)


def _bound_service(
    tmp_path: Path,
    rows,
    authority_db,
    *,
    control=None,
    clock=None,
) -> DesktopControlService:
    database = tmp_path / "control.sqlite"
    settings = SQLiteSerenaConfigStore(database)
    settings.initialize()
    return DesktopControlService(
        control_center=control or StaticRowsControl(rows),
        lifecycle=NullLifecycle(),
        settings_store=settings,
        instances_root=tmp_path,
        cockpit_authority_database=authority_db,
        clock=clock or (lambda: _FIXED_NOW),
    )


def _create_execution(
    store: SQLiteExecutionStore,
    execution_id: str,
    execution_state: ExecutionProcessState,
    *,
    pid: int | None = None,
    exit_code: int | None = None,
    finished_at: str | None = None,
    worker_id: str = _WORKER_ID,
):
    record = new_execution_record(
        execution_id=execution_id,
        job_id=f"job-{execution_id}",
        work_order_ref="WO-P1-424",
        project_id="project-1",
        worker_id=worker_id,
        backend_id="backend-zcode",
        agent_ref=None,
        repo_root=_REPO_ROOT,
        branch=_BRANCH,
        head_before=_HEAD,
        operation_ref=f"operation-{execution_id}",
        command_fingerprint="a" * 64,
        command_summary="cockpit repair verification",
        runtime_profile_ref=None,
        run_dir_ref=None,
        stdout_ref=None,
        stderr_ref=None,
        result_ref=None,
        report_ref=None,
        transport_state=TransportState.CONNECTED,
    )
    record = store.create(record)
    if pid is not None:
        record = store.set_process_metadata(
            execution_id,
            pid=pid,
            started_at="2026-09-20T09:00:00.000000Z",
            expected_version=record.version,
        )
    if exit_code is not None:
        record = store.set_result_metadata(
            execution_id,
            exit_code=exit_code,
            finished_at=finished_at,
            expected_version=record.version,
        )
    if execution_state is not ExecutionProcessState.QUEUED:
        record = store.set_execution_state(
            execution_id, execution_state, expected_version=record.version
        )
    return record


def _prepare_authority(
    tmp_path: Path, name: str = "authority.sqlite"
) -> tuple[Path, SQLiteExecutionStore, SQLiteWorkerLeaseStore]:
    authority = tmp_path / name
    execution_store = SQLiteExecutionStore(authority)
    execution_store.initialize()
    lease_store = SQLiteWorkerLeaseStore(authority)
    lease_store.initialize()
    return authority, execution_store, lease_store


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_real_facade_projects_running_from_bound_durable_authority(
    tmp_path: Path,
) -> None:
    authority, execution_store, _lease_store = _prepare_authority(tmp_path)
    _create_execution(execution_store, "exec-running", ExecutionProcessState.RUNNING, pid=4242)
    service = _bound_service(tmp_path, [_authority_row(_WORKER_ID, _REPO_ROOT)], authority)

    snapshot = service.cockpit_projection(generated_at=GENERATED_AT)

    assert snapshot.stale is False
    assert snapshot.degraded_observability == ("ACTIVITY_READER_UNAVAILABLE",)
    assert len(snapshot.lanes) == 1
    lane = snapshot.lanes[0]
    assert lane.state is CockpitState.RUNNING
    assert lane.identity.provenance == "DURABLE_EXECUTION_RECORD"
    assert lane.identity.work_order_ref == "WO-P1-424"
    assert lane.identity.task_ref == "job-exec-running"
    assert lane.identity.worktree == windows_worktree_key(_REPO_ROOT)
    assert lane.identity.expected_head == _HEAD
    assert lane.process_identity.pid == 4242
    assert lane.process_identity.authoritative is True
    assert lane.process_identity.provenance == "DURABLE_EXECUTION_RECORD"
    assert lane.identity.executor == "SunDay Worker 1"
    assert lane.state is not CockpitState.COMPLETED_VERIFIED


def test_bound_facade_reads_activity_on_both_durable_pins(tmp_path: Path) -> None:
    authority, execution_store, _lease_store = _prepare_authority(tmp_path)
    _create_execution(execution_store, "exec-running", ExecutionProcessState.RUNNING, pid=4242)
    service = _bound_service(tmp_path, [_authority_row(_WORKER_ID, _REPO_ROOT)], authority)
    calls = []

    def reader():
        calls.append(len(calls) + 1)
        return (
            CockpitActivityObservation(
                available=True,
                provenance="DURABLE_MONITOR_RECORD",
                work_order_ref="WO-P1-424",
                task_ref="job-exec-running",
                lane_ref="a-worker-01:exec-running",
                execution_id="exec-running",
                state="WAITING_CI",
                capacity_class="BASE_MUTABLE",
                observed_at="2026-09-20T09:50:00Z",
                reason="CI_PENDING",
            ),
        )

    service._cockpit_activity_reader = reader
    snapshot = service.cockpit_projection(generated_at=GENERATED_AT)
    assert calls == [1, 2]
    assert snapshot.lanes[0].state is CockpitState.WAITING_CI


def test_real_facade_projects_terminal_unharvested_from_bound_authority(
    tmp_path: Path,
) -> None:
    authority, execution_store, _lease_store = _prepare_authority(tmp_path)
    _create_execution(
        execution_store,
        "exec-succeeded",
        ExecutionProcessState.SUCCEEDED,
        exit_code=0,
        finished_at=GENERATED_AT,
    )
    service = _bound_service(tmp_path, [_authority_row(_WORKER_ID, _REPO_ROOT)], authority)

    snapshot = service.cockpit_projection(generated_at=GENERATED_AT)

    lane = snapshot.lanes[0]
    assert lane.state is CockpitState.TERMINAL_UNHARVESTED
    assert lane.state is not CockpitState.COMPLETED_VERIFIED
    assert lane.blocker_code == "MISSING_VERIFICATION_PROOF"


def test_real_facade_projects_outcome_unknown_from_bound_authority(
    tmp_path: Path,
) -> None:
    authority, execution_store, _lease_store = _prepare_authority(tmp_path)
    _create_execution(
        execution_store,
        "exec-exited-unknown",
        ExecutionProcessState.PROCESS_EXITED_UNKNOWN_RESULT,
        pid=4242,
    )
    service = _bound_service(tmp_path, [_authority_row(_WORKER_ID, _REPO_ROOT)], authority)

    snapshot = service.cockpit_projection(generated_at=GENERATED_AT)

    lane = snapshot.lanes[0]
    assert lane.state is CockpitState.OUTCOME_UNKNOWN
    assert lane.blocker_code == "PROCESS_EXITED_UNKNOWN_RESULT"
    assert lane.replay_safety == "RECOVER_POINTER_PROCESS_RESULT_GIT_BEFORE_REDISPATCH"


def test_real_facade_projects_pending_scope_from_active_lease(
    tmp_path: Path,
) -> None:
    authority, _execution_store, lease_store = _prepare_authority(tmp_path)
    request = WorkerLeaseRequest(
        session_id="session-0001",
        task_id="WO-P1-424-COCKPIT1-R2-REPAIR-001",
        project_id="project-1",
        ordered_worker_ids=(_LEASE_WORKER_ID,),
        required_capabilities=(),
        required_runtime_id=None,
        worktree=_REPO_ROOT,
        branch=_BRANCH,
        expected_head=_HEAD,
        mutation_intent=LeaseMutationIntent.READ_ONLY,
    )
    candidate = WorkerLeaseCandidate(
        worker_id=_LEASE_WORKER_ID,
        state="READY",
        reserved=False,
        active_task=False,
        capabilities=(),
        runtime_id=None,
        project_id="project-1",
        worktree=_REPO_ROOT,
        branch=_BRANCH,
        head=_HEAD,
        health_fresh=True,
        ownership_known=True,
        dirty_state="CLEAN",
        mutation_authorized=False,
    )
    lease = lease_store.try_acquire(
        request,
        candidate,
        lease_id="lease-0001",
        acquired_at=_FIXED_NOW,
        expires_at=_LEASE_EXPIRES,
    )
    assert lease is not None
    service = _bound_service(
        tmp_path, [_authority_row(_LEASE_WORKER_ID, _REPO_ROOT)], authority
    )

    snapshot = service.cockpit_projection(generated_at=GENERATED_AT)

    lane = snapshot.lanes[0]
    assert lane.state is CockpitState.PENDING_SCOPE
    assert lane.identity.provenance == "CONTROL_CENTER_SNAPSHOT"
    assert lane.identity.lease_id == "lease-0001"
    assert lane.replay_safety == "NO_EXECUTION_IN_FLIGHT"


def test_real_facade_without_bound_authority_stays_fail_closed_unknown(
    tmp_path: Path,
) -> None:
    authority = tmp_path / "authority.sqlite"
    execution_store = SQLiteExecutionStore(authority)
    _create_execution(execution_store, "exec-running", ExecutionProcessState.RUNNING, pid=4242)
    service = _bound_service(tmp_path, [_authority_row(_WORKER_ID, _REPO_ROOT)], None)

    snapshot = service.cockpit_projection(generated_at=GENERATED_AT)

    assert snapshot.stale is False
    assert snapshot.degraded_observability == ("ACTIVITY_READER_UNAVAILABLE",)
    lane = snapshot.lanes[0]
    assert lane.state is CockpitState.UNKNOWN
    assert lane.blocker_code == "EXECUTION_EVIDENCE_UNAVAILABLE"
    assert lane.execution_id is None
    assert lane.process_identity.pid is None


def test_bound_authority_reads_never_write_the_authority_db(
    tmp_path: Path,
) -> None:
    authority, execution_store, lease_store = _prepare_authority(tmp_path)
    _create_execution(execution_store, "exec-running", ExecutionProcessState.RUNNING, pid=4242)
    before = _file_digest(authority)
    service = _bound_service(tmp_path, [_authority_row(_WORKER_ID, _REPO_ROOT)], authority)
    sidecars_before = sorted(p.name for p in tmp_path.iterdir())

    for _ in range(3):
        snapshot = service.cockpit_projection(generated_at=GENERATED_AT)
        assert snapshot.stale is False

    assert _file_digest(authority) == before
    assert sorted(p.name for p in tmp_path.iterdir()) == sidecars_before
    connection = sqlite3.connect(f"file:{authority}?mode=ro", uri=True)
    try:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()
    finally:
        connection.close()
    assert [row[0] for row in tables] == [
        "execution_events",
        "execution_receipts",
        "execution_records",
        "execution_store_meta",
        "worker_leases",
        "worker_provisioning_reservations",
    ]


def test_bound_authority_without_tables_fails_closed_and_creates_nothing(
    tmp_path: Path,
) -> None:
    empty = tmp_path / "empty.sqlite"
    connection = sqlite3.connect(empty)
    connection.close()
    before = _file_digest(empty)
    service = _bound_service(tmp_path, [_authority_row(_WORKER_ID, _REPO_ROOT)], empty)

    snapshot = service.cockpit_projection(generated_at=GENERATED_AT)

    lane = snapshot.lanes[0]
    assert lane.state is CockpitState.UNKNOWN
    assert lane.blocker_code == "EXECUTION_EVIDENCE_UNAVAILABLE"
    assert "EXECUTION_AUTHORITY_READ_FAILED" in snapshot.degraded_observability
    assert "LEASE_AUTHORITY_READ_FAILED" in snapshot.degraded_observability
    connection = sqlite3.connect(f"file:{empty}?mode=ro", uri=True)
    try:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    finally:
        connection.close()
    assert tables == []
    assert _file_digest(empty) == before


def test_bound_authority_snapshot_goes_stale_on_control_center_drift(
    tmp_path: Path,
) -> None:
    authority, execution_store, _lease_store = _prepare_authority(tmp_path)
    _create_execution(execution_store, "exec-running", ExecutionProcessState.RUNNING, pid=4242)
    control = DriftingRowsControl(
        [_authority_row(_WORKER_ID, _REPO_ROOT)],
        [_authority_row(_WORKER_ID, _REPO_ROOT), _authority_row("a-worker-09", None)],
    )
    service = _bound_service(
        tmp_path, (), authority, control=control
    )

    snapshot = service.cockpit_projection(generated_at=GENERATED_AT)

    assert snapshot.stale is True
    assert snapshot.stale_reason == "SOURCE_DRIFT_DETECTED"
    for lane in snapshot.lanes:
        assert lane.state is CockpitState.UNKNOWN
        assert "STALE" in lane.state_markers
        assert lane.execution_id is None


def test_build_observed_lane_inputs_truthful_absence_semantics() -> None:
    from a_conductor.control_center import ControlCenterSnapshot

    snapshot = ControlCenterSnapshot(
        projects=(), workers=(_authority_row(_WORKER_ID, _REPO_ROOT),)
    )
    durable = CockpitExecutionObservation(
        available=True,
        provenance="DURABLE_EXECUTION_RECORD",
        execution_id="exec-0001",
        job_id="job-0001",
        work_order_ref="WO-P1-424",
        worker_id=_WORKER_ID,
        backend_id="backend-zcode",
        repo_root=windows_worktree_key(_REPO_ROOT),
        branch=_BRANCH,
        head_before=_HEAD,
        transport_state="CONNECTED",
        execution_state="RUNNING",
    )

    lanes = build_observed_lane_inputs(
        snapshot,
        (durable,),
        (),
        execution_authority_readable=True,
        lease_authority_readable=True,
    )

    assert len(lanes) == 1
    assert lanes[0].identity.provenance == "DURABLE_EXECUTION_RECORD"
    assert lanes[0].execution.available is True
    assert lanes[0].lease.reason == "RECORD_NOT_FOUND"
    assert lanes[0].identity.worktree == windows_worktree_key(_REPO_ROOT)

    unreadable = build_observed_lane_inputs(
        snapshot,
        (),
        (),
        execution_authority_readable=False,
        lease_authority_readable=False,
    )

    assert len(unreadable) == 1
    assert unreadable[0].identity.provenance == "CONTROL_CENTER_SNAPSHOT"
    assert unreadable[0].execution.reason == "PORT_UNAVAILABLE"
    assert unreadable[0].lease.reason == "PORT_UNAVAILABLE"


@pytest.mark.parametrize("include_worker", (False, True))
def test_parked_activity_composes_without_an_execution_record(include_worker) -> None:
    from a_conductor.control_center import ControlCenterSnapshot

    activity = _activity(
        work_order_ref="WO-P1-537",
        task_ref="PARKED-TASK",
        lane_ref=_WORKER_ID,
        execution_id=None,
        state="PARKED_CAPACITY",
        capacity_class="BORROWED_MUTABLE",
        reason="BASE_LANE_RESUME_CAPACITY",
        countdown_seconds=None,
        next_recheck_at=None,
    )
    snapshot = ControlCenterSnapshot(
        projects=(),
        workers=(_authority_row(_WORKER_ID, _REPO_ROOT),) if include_worker else (),
    )

    lanes = build_observed_lane_inputs(
        snapshot,
        (),
        (),
        execution_authority_readable=True,
        lease_authority_readable=True,
        activities=(activity,),
    )

    assert len(lanes) == 1
    assert lanes[0].identity.work_order_ref == "WO-P1-537"
    assert lanes[0].identity.task_ref == "PARKED-TASK"
    assert (
        project_cockpit_lane(lanes[0], generated_at=GENERATED_AT).state
        is CockpitState.PARKED_CAPACITY
    )

    control_center_lanes = build_control_center_lane_inputs(snapshot, (activity,))
    assert len(control_center_lanes) == 1
    assert (
        project_cockpit_lane(
            control_center_lanes[0], generated_at=GENERATED_AT
        ).state
        is CockpitState.PARKED_CAPACITY
    )


def test_worker_wait_activity_keeps_exact_identity_when_composed() -> None:
    from a_conductor.control_center import ControlCenterSnapshot

    activity = _activity(
        work_order_ref="WO-P1-537",
        task_ref="WAITING-CI-TASK",
        lane_ref=_WORKER_ID,
        state="WAITING_CI",
        capacity_class="BASE_MUTABLE",
        execution_id=None,
    )
    snapshot = ControlCenterSnapshot(
        projects=(), workers=(_authority_row(_WORKER_ID, _REPO_ROOT),)
    )
    for lane_inputs in (
        build_control_center_lane_inputs(snapshot, (activity,))[0],
        build_observed_lane_inputs(
            snapshot, (), (), execution_authority_readable=True,
            lease_authority_readable=True, activities=(activity,),
        )[0],
    ):
        assert lane_inputs.identity.work_order_ref == "WO-P1-537"
        assert lane_inputs.identity.task_ref == "WAITING-CI-TASK"
        projected = project_cockpit_lane(lane_inputs, generated_at=GENERATED_AT)
        assert projected.state is CockpitState.WAITING_CI


@pytest.mark.parametrize("builder", ("control", "observed"))
def test_duplicate_activity_lane_refs_are_preserved_and_marked(builder) -> None:
    from a_conductor.control_center import ControlCenterSnapshot

    snapshot = ControlCenterSnapshot(
        projects=(), workers=(_authority_row(_WORKER_ID, _REPO_ROOT),)
    )
    activities = (
        _activity(work_order_ref="WO-A", task_ref="TASK-A", lane_ref=_WORKER_ID,
                  execution_id=None, state="PARKED_CAPACITY",
                  capacity_class="BORROWED_MUTABLE"),
        _activity(work_order_ref="WO-B", task_ref="TASK-B", lane_ref=_WORKER_ID,
                  execution_id=None, state="PARKED_CAPACITY",
                  capacity_class="BORROWED_MUTABLE"),
    )
    if builder == "control":
        lanes = build_control_center_lane_inputs(snapshot, activities)
    else:
        lanes = build_observed_lane_inputs(
            snapshot, (), (), execution_authority_readable=True,
            lease_authority_readable=True, activities=activities,
        )
    assert len(lanes) == 2
    assert {lane.identity.task_ref for lane in lanes} == {"TASK-A", "TASK-B"}
    projected = [project_cockpit_lane(lane, generated_at=GENERATED_AT) for lane in lanes]
    assert all(lane.blocker_code == "ACTIVITY_LANE_COLLISION" for lane in projected)
    assert all("ACTIVITY_LANE_COLLISION" in lane.state_markers for lane in projected)
    snapshot_projection = project_cockpit_snapshot(
        CockpitObservations(lanes=tuple(lanes), generated_at=GENERATED_AT)
    )
    assert "ACTIVITY_LANE_COLLISION" in "\n".join(
        cockpit_monitor_lines(snapshot_projection)
    )
    assert "collisions=2" in "\n".join(
        cockpit_monitor_lines(snapshot_projection)
    )


@pytest.mark.parametrize(
    "lane_ref_kind",
    ("compound", "bare_execution", "bare_execution_worker"),
)
def test_parked_activity_already_joined_to_execution_is_not_double_counted(
    lane_ref_kind,
) -> None:
    from a_conductor.control_center import ControlCenterSnapshot

    if lane_ref_kind == "compound":
        worker_id = _WORKER_ID
        lane_ref = f"{worker_id}:exec-0001"
        snapshot = ControlCenterSnapshot(
            projects=(), workers=(_authority_row(worker_id, _REPO_ROOT),)
        )
        execution = _execution()
    elif lane_ref_kind == "bare_execution_worker":
        worker_id = _WORKER_ID
        lane_ref = "exec-0001"
        snapshot = ControlCenterSnapshot(
            projects=(), workers=(_authority_row(worker_id, _REPO_ROOT),)
        )
        execution = _execution()
    else:
        worker_id = None
        lane_ref = "exec-0001"
        snapshot = ControlCenterSnapshot(projects=(), workers=())
        execution = _execution(worker_id=None)
    activity = _activity(
        work_order_ref="WO-P1-537",
        task_ref="PARKED-TASK",
        lane_ref=lane_ref,
        execution_id=(
            "exec-0001"
            if lane_ref_kind in {"bare_execution", "bare_execution_worker"}
            else None
        ),
        state="PARKED_CAPACITY",
        capacity_class="BORROWED_MUTABLE",
    )

    lanes = build_observed_lane_inputs(
        snapshot,
        (execution,),
        (),
        execution_authority_readable=True,
        lease_authority_readable=True,
        activities=(activity,),
    )

    assert len(lanes) == 1
    assert lanes[0].activity is activity
    projected = project_cockpit_lane(lanes[0], generated_at=GENERATED_AT)
    assert projected.state is CockpitState.RUNNING


def test_unmatched_mixed_activity_collision_preserves_every_claim_identity() -> None:
    from a_conductor.control_center import ControlCenterSnapshot

    activities = (
        _activity(work_order_ref="WO-A", task_ref="PARKED-TASK", lane_ref="shared-lane",
                  execution_id=None, state="PARKED_CAPACITY",
                  capacity_class="BORROWED_MUTABLE"),
        _activity(work_order_ref="WO-B", task_ref="WAITING-TASK", lane_ref="shared-lane",
                  execution_id=None, state="WAITING_CI", capacity_class="BASE_MUTABLE"),
    )
    lanes = build_observed_lane_inputs(
        ControlCenterSnapshot(projects=(), workers=()),
        (), (), execution_authority_readable=True,
        lease_authority_readable=True, activities=activities,
    )
    assert len(lanes) == 2
    assert {lane.identity.task_ref for lane in lanes} == {
        "PARKED-TASK", "WAITING-TASK"
    }
    assert all(
        project_cockpit_lane(lane, generated_at=GENERATED_AT).blocker_code
        == "ACTIVITY_LANE_COLLISION"
        for lane in lanes
    )


def test_collision_count_is_visible_without_capacity_classes() -> None:
    from a_conductor.control_center import ControlCenterSnapshot

    activities = (
        _activity(work_order_ref="WO-A", task_ref="WAIT-A", lane_ref="shared-lane",
                  execution_id=None, state="WAITING_CI", capacity_class=None),
        _activity(work_order_ref="WO-B", task_ref="WAIT-B", lane_ref="shared-lane",
                  execution_id=None, state="WAITING_CI", capacity_class=None),
    )
    lanes = build_observed_lane_inputs(
        ControlCenterSnapshot(projects=(), workers=()),
        (), (), execution_authority_readable=True,
        lease_authority_readable=True, activities=activities,
    )
    snapshot_projection = project_cockpit_snapshot(
        CockpitObservations(lanes=lanes, generated_at=GENERATED_AT)
    )
    rendered = "\n".join(cockpit_monitor_lines(snapshot_projection))
    assert "no classified lanes" in rendered
    assert "collisions=2" in rendered


# ---------------------------------------------------------------- UI boundary


class FakeText:
    def __init__(self) -> None:
        self.text = ""

    def winfo_exists(self):
        return True

    def configure(self, **_kwargs):
        pass

    def delete(self, *_args):
        self.text = ""

    def insert(self, _index, text):
        self.text = text

    def yview_moveto(self, _fraction):
        pass


def _bare_app(service) -> "object":
    import a_conductor.desktop_ui as desktop_ui

    app = object.__new__(desktop_ui.AConductorDesktopApp)
    app.service = service
    app.root = object()
    app.monitor_text = FakeText()
    app._monitor_mode = "connector"
    app._graph_monitor_graph_id = None
    app._graph_monitor_run_id = None
    return app


def test_show_cockpit_monitor_switches_mode_and_refreshes(tmp_path: Path) -> None:
    app = _bare_app(_real_service(tmp_path))
    refreshed: list[bool] = []
    app._refresh_monitor_async = lambda: refreshed.append(True)

    app.show_cockpit_monitor()

    assert app._monitor_mode == "cockpit"
    assert refreshed == [True]


def test_update_cockpit_monitor_now_renders_without_deadlock(tmp_path: Path) -> None:
    app = _bare_app(_real_service(tmp_path))
    app._closing = False

    app._update_cockpit_monitor_now()

    assert "MONITOR · COCKPIT" in app.monitor_text.text


def test_cockpit_future_cannot_render_after_mode_switch(tmp_path: Path) -> None:
    from concurrent.futures import Future

    app = _bare_app(_real_service(tmp_path))
    snapshot = app.service.cockpit_projection()
    future = Future()
    future.set_result((snapshot, None))
    app._closing = False
    app._monitor_mode = "connector"
    app._monitor_future = future
    app._monitor_refresh_pending = True
    app._monitor_poll_after_id = None
    rendered: list[object] = []
    scheduled: list[tuple] = []
    app._render_cockpit_monitor = lambda *args: rendered.append(args)
    app._cancel_after = lambda _callback_id: None
    app._schedule_after = lambda delay, callback, *args: scheduled.append(
        (delay, callback, args)
    ) or "scheduled"

    app._poll_cockpit_monitor(future)

    assert rendered == []
    assert len(scheduled) == 1
    assert scheduled[0][0] == 0
    assert scheduled[0][1].__name__ == "_refresh_monitor_async"


def test_cockpit_monitor_unavailable_service_renders_error(tmp_path: Path) -> None:
    app = _bare_app(NullControl())
    app._closing = False

    app._update_cockpit_monitor_now()

    assert "COCKPIT_UNAVAILABLE" in app.monitor_text.text


# --------------------------------------------------- WO-P1-493 MSP-3 origin


_ORIGIN_REF = "origin-chat-v1:kv1:" + "1f" + "0" * 62
_ORIGIN_REF_ALT = "origin-chat-v1:kv2:" + "2e" + "0" * 62


def _origin(**overrides) -> CockpitOriginObservation:
    base = dict(
        available=True,
        provenance="CONTROL_HOOK_EVENT",
        reason=None,
        origin_ref=_ORIGIN_REF,
        origin_surface="a-conductor",
        observed_at="2026-09-22T08:00:00.000000Z",
        execution_id="exec-0001",
    )
    base.update(overrides)
    return CockpitOriginObservation(**base)


def test_origin_present_or_absent_leaves_authority_truth_equivalent() -> None:
    without = project_cockpit_lane(_inputs(execution=_execution()))
    with_origin = project_cockpit_lane(
        _inputs(execution=_execution(), origin=_origin())
    )

    assert without.state is with_origin.state is CockpitState.RUNNING
    assert without.state_markers == with_origin.state_markers
    assert without.blocker_code == with_origin.blocker_code
    assert without.replay_safety == with_origin.replay_safety
    assert without.next_safe_action == with_origin.next_safe_action
    assert without.gates == with_origin.gates
    assert without.process_identity == with_origin.process_identity
    assert without.execution_id == with_origin.execution_id
    assert without.job_id == with_origin.job_id
    assert without.transport_state == with_origin.transport_state
    assert without.hook_state == with_origin.hook_state
    assert without.wtl_state == with_origin.wtl_state

    # only the read-model display context differs
    assert without.origin_display != with_origin.origin_display
    assert with_origin.origin_display == CockpitOriginDisplay(
        status="RECORDED",
        origin_ref=_ORIGIN_REF,
        origin_surface="a-conductor",
        key_version="kv1",
        reason=None,
    )
    assert without.origin_display.status == "UNAVAILABLE"


def test_missing_pre_msp1_origin_renders_typed_absence_never_inferred() -> None:
    not_recorded = project_cockpit_lane(
        _inputs(
            execution=_execution(),
            origin=CockpitOriginObservation.unavailable("RECORD_NOT_FOUND"),
        )
    )
    assert not_recorded.origin_display.status == "NOT_RECORDED"
    assert not_recorded.origin_display.origin_ref is None
    assert not_recorded.origin_display.origin_surface is None

    port_unavailable = project_cockpit_lane(_inputs(execution=_execution()))
    assert port_unavailable.origin_display.status == "UNAVAILABLE"
    assert port_unavailable.origin_display.reason == "PORT_UNAVAILABLE"

    # absence is never upgraded from identity aliases or worker rows
    assert not_recorded.state is port_unavailable.state is CockpitState.RUNNING


def test_unsupported_origin_provenance_renders_typed_unknown_display_only() -> None:
    origin = _origin(provenance="OPERATOR_DECLARED", origin_ref="raw-session-XYZ")

    # unsupported provenance never carries origin payload inside the model
    assert origin.origin_ref is None
    assert origin.origin_surface is None

    lane = project_cockpit_lane(_inputs(execution=_execution(), origin=origin))
    assert lane.origin_display.status == "UNKNOWN"
    assert lane.origin_display.reason == "ORIGIN_PROVENANCE_UNSUPPORTED"
    assert lane.origin_display.origin_ref is None
    assert lane.origin_display.origin_surface is None
    # degraded display only: lane truth unchanged
    assert lane.state is CockpitState.RUNNING
    assert lane.blocker_code is None


def test_secret_shaped_or_raw_origin_refs_are_rejected() -> None:
    for bad_ref in (
        "sess_abc123",
        "origin-chat-v1:kv1:not-hex-at-all",
        "origin-chat-v1:kv1:" + "f" * 63,
        "user@host/session",
        "sk-ant-api03-secret",
        "",
    ):
        with pytest.raises(CockpitProjectionError):
            _origin(origin_ref=bad_ref)
    with pytest.raises(CockpitProjectionError):
        _origin(origin_surface="some-unknown-surface")
    with pytest.raises(CockpitProjectionError):
        _origin(provenance=None)


def test_origin_never_rescues_terminal_unharvested_or_unknown_runtime() -> None:
    terminal = project_cockpit_lane(
        _inputs(
            execution=_execution(execution_state="VERIFICATION_REQUIRED"),
            origin=_origin(),
        )
    )
    assert terminal.state is CockpitState.TERMINAL_UNHARVESTED
    assert terminal.blocker_code == "VERIFICATION_PROOF_REQUIRED"
    assert terminal.replay_safety == "RECONCILE_BEFORE_ANY_REDISPATCH"

    unknown_runtime = project_cockpit_lane(
        _inputs(
            execution=_execution(
                execution_state="PROCESS_STILL_RUNNING", transport_state="UNAVAILABLE"
            ),
            origin=_origin(),
        )
    )
    assert unknown_runtime.state is CockpitState.RUNNING
    assert "DEGRADED_OBSERVABILITY" in unknown_runtime.state_markers


def test_multiple_origin_refs_keep_one_lane_and_one_owner() -> None:
    from a_conductor.control_center import ControlCenterSnapshot

    snapshot = ControlCenterSnapshot(
        projects=(), workers=(_authority_row(_WORKER_ID, _REPO_ROOT),)
    )
    durable = CockpitExecutionObservation(
        available=True,
        provenance="DURABLE_EXECUTION_RECORD",
        execution_id="exec-0001",
        job_id="job-0001",
        work_order_ref="WO-P1-493",
        worker_id=_WORKER_ID,
        backend_id="backend-zcode",
        repo_root=windows_worktree_key(_REPO_ROOT),
        branch=_BRANCH,
        head_before=_HEAD,
        transport_state="CONNECTED",
        execution_state="RUNNING",
    )
    earliest = _origin(observed_at="2026-09-22T08:00:00.000000Z")
    latest = _origin(
        origin_ref=_ORIGIN_REF_ALT, observed_at="2026-09-22T09:00:00.000000Z"
    )

    baseline = build_observed_lane_inputs(
        snapshot,
        (durable,),
        (),
        execution_authority_readable=True,
        lease_authority_readable=True,
    )
    multi = build_observed_lane_inputs(
        snapshot,
        (durable,),
        (),
        execution_authority_readable=True,
        lease_authority_readable=True,
        origins=(latest, earliest),
    )
    reordered = build_observed_lane_inputs(
        snapshot,
        (durable,),
        (),
        execution_authority_readable=True,
        lease_authority_readable=True,
        origins=(earliest, latest),
    )

    assert len(baseline) == len(multi) == 1
    assert multi[0].identity == baseline[0].identity
    assert multi[0].execution == baseline[0].execution
    assert multi[0].lease == baseline[0].lease
    assert multi[0].gates == baseline[0].gates
    # deterministic: earliest observed origin wins regardless of tuple order
    assert multi[0].origin == reordered[0].origin == earliest
    # and origin absence baseline still renders typed unavailable display
    baseline_lane = project_cockpit_lane(baseline[0])
    multi_lane = project_cockpit_lane(multi[0])
    assert baseline_lane.state is multi_lane.state is CockpitState.RUNNING
    assert baseline_lane.origin_display.status == "UNAVAILABLE"
    assert multi_lane.origin_display.origin_ref == _ORIGIN_REF


def test_fresh_projection_reconstructs_equivalent_origin_display() -> None:
    lanes = (_inputs(execution=_execution(), origin=_origin()),)
    snap_a = project_cockpit_snapshot(
        CockpitObservations(lanes=lanes, generated_at=GENERATED_AT)
    )
    snap_b = project_cockpit_snapshot(
        CockpitObservations(lanes=lanes, generated_at=GENERATED_AT),
        recheck=CockpitObservations(lanes=lanes, generated_at=GENERATED_AT),
    )
    assert snap_b.stale is False
    assert snap_a.lanes[0].origin_display == snap_b.lanes[0].origin_display
    assert (
        cockpit_fingerprint(snap_a)
        == cockpit_fingerprint(project_cockpit_snapshot(
            CockpitObservations(lanes=lanes, generated_at=GENERATED_AT)
        ))
    )


def test_origin_drift_between_pins_renders_stale_not_mixed() -> None:
    first = CockpitObservations(
        lanes=(_inputs(execution=_execution(), origin=_origin()),),
        generated_at=GENERATED_AT,
    )
    drifted = CockpitObservations(
        lanes=(
            _inputs(
                execution=_execution(),
                origin=_origin(
                    origin_ref=_ORIGIN_REF_ALT,
                    observed_at="2026-09-22T09:00:00.000000Z",
                ),
            ),
        ),
        generated_at=GENERATED_AT,
    )
    snapshot = project_cockpit_snapshot(first, recheck=drifted)

    assert snapshot.stale is True
    lane = snapshot.lanes[0]
    assert lane.origin_display.status == "UNKNOWN"
    assert lane.origin_display.reason == "SOURCE_DRIFT_DETECTED"
    assert lane.origin_display.origin_ref is None


def test_origin_display_renders_in_monitor_lines() -> None:
    recorded = project_cockpit_snapshot(
        CockpitObservations(
            lanes=(_inputs(execution=_execution(), origin=_origin()),),
            generated_at=GENERATED_AT,
        )
    )
    text = "\n".join(cockpit_monitor_lines(recorded))
    assert "ORIGIN: RECORDED" in text
    assert _ORIGIN_REF in text
    assert "surface: a-conductor" in text
    assert "key version: kv1" in text

    absent = project_cockpit_snapshot(
        CockpitObservations(
            lanes=(
                _inputs(
                    execution=_execution(),
                    origin=CockpitOriginObservation.unavailable("RECORD_NOT_FOUND"),
                ),
            ),
            generated_at=GENERATED_AT,
        )
    )
    absent_text = "\n".join(cockpit_monitor_lines(absent))
    assert "ORIGIN: NOT_RECORDED" in absent_text
    assert _ORIGIN_REF not in absent_text
