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
    CockpitExecutionObservation,
    CockpitFingerprintError,
    CockpitGateEvidence,
    CockpitGateStatus,
    CockpitGitObservation,
    CockpitLaneIdentity,
    CockpitLaneInputs,
    CockpitLeaseObservation,
    CockpitObservations,
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


def _inputs(identity=None, execution=None, lease=None, git=None, gates=None) -> CockpitLaneInputs:
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
    assert snapshot.degraded_observability == ()
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
    assert snapshot.degraded_observability == ()
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
    assert snapshot.degraded_observability == ()
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
