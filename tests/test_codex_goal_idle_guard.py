from __future__ import annotations

import ast
import builtins
import pathlib

import pytest

from a_conductor.codex_goal_idle_guard import (
    DelegatedExecutionCensus,
    FingerprintState,
    GlmDisposition,
    GlmDispositionState,
    GlmQuotaState,
    GoalGuardAction,
    GoalIdleGuardSnapshot,
    PendingSteerState,
    SafeReadyState,
    classify_goal_idle,
)

MODULE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "a_conductor"
    / "codex_goal_idle_guard.py"
)
ALLOWED_IMPORT_ROOTS = {"__future__", "dataclasses", "enum"}
FORBIDDEN_CALL_NAMES = {"open", "eval", "exec", "__import__", "input"}


class _ThreadID(str):
    pass


def census(**overrides) -> DelegatedExecutionCensus:
    values = {
        "starting": 0,
        "running": 0,
        "waiting": 0,
        "stalled": 0,
        "terminal_unharvested": 0,
        "interrupted": 0,
        "terminal": 0,
        "unknown": 0,
    }
    values.update(overrides)
    return DelegatedExecutionCensus(**values)


def snapshot(**overrides) -> GoalIdleGuardSnapshot:
    values = {
        "execution_census": census(),
        "actionable_queue_count": 0,
        "fingerprint_state": FingerprintState.UNCHANGED,
        "safe_ready_state": SafeReadyState.NOT_ESTABLISHED,
        "watchdog_thread_id": "watchdog-thread-synthetic-a",
        "goal_thread_id": "goal-thread-synthetic-b",
        "pending_steer_state": PendingSteerState.NONE,
        "eligible_r2r3_task": False,
        "human_instruction_pending": False,
        "glm_disposition": GlmDisposition(
            state=GlmDispositionState.NONE, reason=None
        ),
        "glm_quota_state": GlmQuotaState.CONFIRMED_AVAILABLE,
    }
    values.update(overrides)
    return GoalIdleGuardSnapshot(**values)


def test_human_instruction_pending_requires_resume_over_idle() -> None:
    verdict = classify_goal_idle(snapshot(human_instruction_pending=True))
    assert verdict.action is GoalGuardAction.RESUME_REQUIRED
    assert verdict.action is not GoalGuardAction.IDLE_PAUSE_REQUIRED
    assert verdict.pause_forbidden is True
    assert verdict.reason_codes == ("HUMAN_INSTRUCTION_PENDING",)


def test_human_instruction_pending_false_keeps_idle_pause() -> None:
    verdict = classify_goal_idle(snapshot(human_instruction_pending=False))
    assert verdict.action is GoalGuardAction.IDLE_PAUSE_REQUIRED
    assert verdict.reason_codes == ("IDLE_ALL_ACTIONLESS", "FINGERPRINT_UNCHANGED")


def test_human_instruction_pending_resumes_despite_unknown_fingerprint() -> None:
    verdict = classify_goal_idle(
        snapshot(
            fingerprint_state=FingerprintState.UNKNOWN,
            human_instruction_pending=True,
        )
    )
    assert verdict.action is GoalGuardAction.RESUME_REQUIRED
    assert verdict.action is not GoalGuardAction.IDLE_PAUSE_REQUIRED
    assert verdict.reason_codes == ("HUMAN_INSTRUCTION_PENDING",)


def test_human_instruction_pending_defaults_to_false() -> None:
    item = GoalIdleGuardSnapshot(
        execution_census=census(),
        actionable_queue_count=0,
        fingerprint_state=FingerprintState.UNCHANGED,
        safe_ready_state=SafeReadyState.NOT_ESTABLISHED,
        watchdog_thread_id="watchdog-thread-synthetic-a",
        goal_thread_id="goal-thread-synthetic-b",
        pending_steer_state=PendingSteerState.NONE,
        eligible_r2r3_task=False,
        glm_disposition=GlmDisposition(
            state=GlmDispositionState.NONE, reason=None
        ),
        glm_quota_state=GlmQuotaState.CONFIRMED_AVAILABLE,
    )
    assert item.human_instruction_pending is False
    assert classify_goal_idle(item).action is GoalGuardAction.IDLE_PAUSE_REQUIRED


def test_human_instruction_combines_with_resume_reasons_in_stable_order() -> None:
    verdict = classify_goal_idle(
        snapshot(
            fingerprint_state=FingerprintState.MATERIAL_DELTA,
            safe_ready_state=SafeReadyState.GENUINE,
            human_instruction_pending=True,
        )
    )
    assert verdict.action is GoalGuardAction.RESUME_REQUIRED
    assert verdict.pause_forbidden is True
    assert verdict.reason_codes == (
        "MATERIAL_DELTA_PRESENT",
        "SAFE_READY_GENUINE",
        "HUMAN_INSTRUCTION_PENDING",
    )


def test_human_instruction_does_not_override_higher_priority_gates() -> None:
    topology = classify_goal_idle(
        snapshot(
            goal_thread_id="watchdog-thread-synthetic-a",
            human_instruction_pending=True,
        )
    )
    assert topology.action is GoalGuardAction.CONFIG_TOPOLOGY_ERROR
    harvest = classify_goal_idle(
        snapshot(
            execution_census=census(terminal_unharvested=1),
            human_instruction_pending=True,
        )
    )
    assert harvest.action is GoalGuardAction.HARVEST_REQUIRED
    dispatch = classify_goal_idle(
        snapshot(eligible_r2r3_task=True, human_instruction_pending=True)
    )
    assert dispatch.action is GoalGuardAction.REAL_GLM_DISPATCH_REQUIRED
    stale = classify_goal_idle(
        snapshot(
            pending_steer_state=PendingSteerState.EQUIVALENT_PENDING_STALE,
            human_instruction_pending=True,
        )
    )
    assert stale.action is GoalGuardAction.STALE_QUEUE_STEER
    active = classify_goal_idle(
        snapshot(
            execution_census=census(running=1),
            human_instruction_pending=True,
        )
    )
    assert active.action is GoalGuardAction.ACTIVE_CONTINUE
    queued = classify_goal_idle(
        snapshot(actionable_queue_count=1, human_instruction_pending=True)
    )
    assert queued.action is GoalGuardAction.ACTIVE_CONTINUE


def test_all_idle_census_requires_idle_pause() -> None:
    verdict = classify_goal_idle(snapshot())
    assert verdict.action is GoalGuardAction.IDLE_PAUSE_REQUIRED
    assert verdict.pause_forbidden is False
    assert verdict.reason_codes == ("IDLE_ALL_ACTIONLESS", "FINGERPRINT_UNCHANGED")


def test_terminal_unharvested_requires_harvest_and_forbids_pause() -> None:
    verdict = classify_goal_idle(
        snapshot(execution_census=census(terminal_unharvested=1))
    )
    assert verdict.action is GoalGuardAction.HARVEST_REQUIRED
    assert verdict.pause_forbidden is True
    assert verdict.reason_codes == ("TERMINAL_UNHARVESTED_PRESENT",)


def test_harvest_outranks_active_continue() -> None:
    verdict = classify_goal_idle(
        snapshot(
            execution_census=census(terminal_unharvested=2, running=1),
            actionable_queue_count=3,
        )
    )
    assert verdict.action is GoalGuardAction.HARVEST_REQUIRED
    assert verdict.action is not GoalGuardAction.IDLE_PAUSE_REQUIRED


def test_material_delta_requires_resume() -> None:
    verdict = classify_goal_idle(
        snapshot(fingerprint_state=FingerprintState.MATERIAL_DELTA)
    )
    assert verdict.action is GoalGuardAction.RESUME_REQUIRED
    assert verdict.reason_codes == ("MATERIAL_DELTA_PRESENT",)
    assert verdict.pause_forbidden is True


def test_genuine_safe_ready_requires_resume() -> None:
    verdict = classify_goal_idle(
        snapshot(safe_ready_state=SafeReadyState.GENUINE)
    )
    assert verdict.action is GoalGuardAction.RESUME_REQUIRED
    assert verdict.reason_codes == ("SAFE_READY_GENUINE",)


def test_material_delta_and_safe_ready_yield_both_reasons() -> None:
    verdict = classify_goal_idle(
        snapshot(
            fingerprint_state=FingerprintState.MATERIAL_DELTA,
            safe_ready_state=SafeReadyState.GENUINE,
        )
    )
    assert verdict.action is GoalGuardAction.RESUME_REQUIRED
    assert verdict.reason_codes == ("MATERIAL_DELTA_PRESENT", "SAFE_READY_GENUINE")


def test_eligible_r2r3_without_disposition_confirmed_quota_dispatches() -> None:
    verdict = classify_goal_idle(snapshot(eligible_r2r3_task=True))
    assert verdict.action is GoalGuardAction.REAL_GLM_DISPATCH_REQUIRED
    assert verdict.reason_codes == ("ELIGIBLE_R2R3_WITHOUT_DISPOSITION",)
    assert verdict.pause_forbidden is True


def test_unchanged_fingerprint_idle_never_resumes_or_repeats_sweep() -> None:
    verdict = classify_goal_idle(snapshot())
    assert verdict.action is not GoalGuardAction.RESUME_REQUIRED
    assert verdict.action is GoalGuardAction.IDLE_PAUSE_REQUIRED


def test_equivalent_pending_fresh_steer_is_suppressed_not_stale() -> None:
    verdict = classify_goal_idle(
        snapshot(pending_steer_state=PendingSteerState.EQUIVALENT_PENDING_FRESH)
    )
    assert verdict.action is GoalGuardAction.STEER_DUPLICATE_SUPPRESSED
    assert verdict.action is not GoalGuardAction.STALE_QUEUE_STEER
    assert verdict.reason_codes == (
        "EQUIVALENT_STEER_PENDING_WITHIN_CADENCE_BOUND",
    )
    assert verdict.pause_forbidden is True


def test_equivalent_pending_stale_steer_requires_steer() -> None:
    verdict = classify_goal_idle(
        snapshot(pending_steer_state=PendingSteerState.EQUIVALENT_PENDING_STALE)
    )
    assert verdict.action is GoalGuardAction.STALE_QUEUE_STEER
    assert verdict.reason_codes == ("PENDING_STEER_EXCEEDS_CADENCE_BOUND",)


def test_watchdog_thread_collision_is_config_topology_error() -> None:
    verdict = classify_goal_idle(
        snapshot(goal_thread_id="watchdog-thread-synthetic-a")
    )
    assert verdict.action is GoalGuardAction.CONFIG_TOPOLOGY_ERROR
    assert verdict.pause_forbidden is True
    assert verdict.reason_codes == ("WATCHDOG_THREAD_EQUALS_GOAL_THREAD",)


def test_topology_error_outranks_harvest() -> None:
    verdict = classify_goal_idle(
        snapshot(
            goal_thread_id="watchdog-thread-synthetic-a",
            execution_census=census(terminal_unharvested=1),
        )
    )
    assert verdict.action is GoalGuardAction.CONFIG_TOPOLOGY_ERROR
    assert verdict.action is not GoalGuardAction.HARVEST_REQUIRED


def test_module_imports_are_pure() -> None:
    tree = ast.parse(
        MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH)
    )
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(
                alias.name.split(".")[0] for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            imported_roots.add((node.module or "").split(".")[0])
    assert imported_roots <= ALLOWED_IMPORT_ROOTS


def test_module_has_no_io_or_dynamic_execution_calls() -> None:
    tree = ast.parse(
        MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH)
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in FORBIDDEN_CALL_NAMES


def test_classify_runs_with_open_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _refused(*args: object, **kwargs: object) -> None:
        raise AssertionError("codex_goal_idle_guard must not open files")

    monkeypatch.setattr(builtins, "open", _refused)
    verdict = classify_goal_idle(snapshot())
    assert verdict.action is GoalGuardAction.IDLE_PAUSE_REQUIRED


@pytest.mark.parametrize(
    ("quota_state", "expected_reason"),
    [
        (GlmQuotaState.AMBIGUOUS, "BLOCKED:QUOTA_AMBIGUOUS"),
        (GlmQuotaState.CACHED, "BLOCKED:QUOTA_CACHED"),
        (GlmQuotaState.UNAVAILABLE, "BLOCKED:QUOTA_UNAVAILABLE"),
    ],
)
def test_non_confirmed_quota_never_admits_glm_dispatch(
    quota_state: GlmQuotaState, expected_reason: str
) -> None:
    verdict = classify_goal_idle(
        snapshot(eligible_r2r3_task=True, glm_quota_state=quota_state)
    )
    assert verdict.action is GoalGuardAction.BLOCKED
    assert verdict.action is not GoalGuardAction.REAL_GLM_DISPATCH_REQUIRED
    assert verdict.reason_codes == (
        "ELIGIBLE_R2R3_WITHOUT_DISPOSITION",
        expected_reason,
    )


def test_preserved_blocked_disposition_reason_is_verbatim() -> None:
    verdict = classify_goal_idle(
        snapshot(
            eligible_r2r3_task=True,
            glm_disposition=GlmDisposition(
                state=GlmDispositionState.BLOCKED,
                reason="EXTERNAL_DEPENDENCY",
            ),
        )
    )
    assert verdict.action is GoalGuardAction.BLOCKED
    assert verdict.reason_codes == (
        "TASK_ROUTE_DISPOSITION",
        "BLOCKED:EXTERNAL_DEPENDENCY",
    )


def test_preserved_not_beneficial_disposition_reason_is_verbatim() -> None:
    verdict = classify_goal_idle(
        snapshot(
            eligible_r2r3_task=True,
            glm_disposition=GlmDisposition(
                state=GlmDispositionState.NOT_BENEFICIAL,
                reason="SUPERVISOR_SWEEP_NO_DELTA",
            ),
        )
    )
    assert verdict.action is GoalGuardAction.NOT_BENEFICIAL
    assert verdict.reason_codes == (
        "TASK_ROUTE_DISPOSITION",
        "NOT_BENEFICIAL:SUPERVISOR_SWEEP_NO_DELTA",
    )


@pytest.mark.parametrize(
    ("field", "expected_reason"),
    [
        ("starting", "EXECUTIONS_STARTING"),
        ("running", "EXECUTIONS_RUNNING"),
        ("waiting", "EXECUTIONS_WAITING"),
        ("stalled", "EXECUTIONS_STALLED"),
        ("interrupted", "EXECUTIONS_INTERRUPTED"),
        ("unknown", "EXECUTIONS_UNKNOWN"),
    ],
)
def test_live_execution_classes_active_continue_never_pause(
    field: str, expected_reason: str
) -> None:
    verdict = classify_goal_idle(
        snapshot(execution_census=census(**{field: 1}))
    )
    assert verdict.action is GoalGuardAction.ACTIVE_CONTINUE
    assert verdict.action is not GoalGuardAction.IDLE_PAUSE_REQUIRED
    assert verdict.pause_forbidden is True
    assert verdict.reason_codes == (expected_reason,)


def test_actionable_queue_requires_active_continue() -> None:
    verdict = classify_goal_idle(snapshot(actionable_queue_count=2))
    assert verdict.action is GoalGuardAction.ACTIVE_CONTINUE
    assert verdict.reason_codes == ("ACTIONABLE_QUEUE_NON_EMPTY",)


def test_unknown_fingerprint_never_resumes_when_idle() -> None:
    verdict = classify_goal_idle(
        snapshot(fingerprint_state=FingerprintState.UNKNOWN)
    )
    assert verdict.action is not GoalGuardAction.RESUME_REQUIRED
    assert verdict.action is GoalGuardAction.IDLE_PAUSE_REQUIRED
    assert verdict.reason_codes == ("IDLE_ALL_ACTIONLESS", "FINGERPRINT_UNKNOWN")


def test_unknown_fingerprint_with_genuine_safe_ready_still_resumes() -> None:
    verdict = classify_goal_idle(
        snapshot(
            fingerprint_state=FingerprintState.UNKNOWN,
            safe_ready_state=SafeReadyState.GENUINE,
        )
    )
    assert verdict.action is GoalGuardAction.RESUME_REQUIRED
    assert verdict.reason_codes == ("SAFE_READY_GENUINE",)


def test_harvest_outranks_glm_dispatch_requirement() -> None:
    verdict = classify_goal_idle(
        snapshot(
            eligible_r2r3_task=True,
            execution_census=census(terminal_unharvested=1),
        )
    )
    assert verdict.action is GoalGuardAction.HARVEST_REQUIRED


def test_glm_dispatch_requirement_outranks_stale_steer() -> None:
    verdict = classify_goal_idle(
        snapshot(
            eligible_r2r3_task=True,
            pending_steer_state=PendingSteerState.EQUIVALENT_PENDING_STALE,
        )
    )
    assert verdict.action is GoalGuardAction.REAL_GLM_DISPATCH_REQUIRED


def test_stale_steer_outranks_active_continue() -> None:
    verdict = classify_goal_idle(
        snapshot(
            pending_steer_state=PendingSteerState.EQUIVALENT_PENDING_STALE,
            execution_census=census(running=1),
        )
    )
    assert verdict.action is GoalGuardAction.STALE_QUEUE_STEER


def test_active_work_outranks_resume() -> None:
    verdict = classify_goal_idle(
        snapshot(
            execution_census=census(waiting=1),
            fingerprint_state=FingerprintState.MATERIAL_DELTA,
        )
    )
    assert verdict.action is GoalGuardAction.ACTIVE_CONTINUE


def test_resume_outranks_preserved_disposition() -> None:
    verdict = classify_goal_idle(
        snapshot(
            eligible_r2r3_task=True,
            fingerprint_state=FingerprintState.MATERIAL_DELTA,
            glm_disposition=GlmDisposition(
                state=GlmDispositionState.BLOCKED,
                reason="EXTERNAL_DEPENDENCY",
            ),
        )
    )
    assert verdict.action is GoalGuardAction.RESUME_REQUIRED


def test_preserved_disposition_outranks_duplicate_steer_suppression() -> None:
    verdict = classify_goal_idle(
        snapshot(
            eligible_r2r3_task=True,
            pending_steer_state=PendingSteerState.EQUIVALENT_PENDING_FRESH,
            glm_disposition=GlmDisposition(
                state=GlmDispositionState.NOT_BENEFICIAL,
                reason="SUPERVISOR_SWEEP_NO_DELTA",
            ),
        )
    )
    assert verdict.action is GoalGuardAction.NOT_BENEFICIAL


@pytest.mark.parametrize("payload", ["snapshot", None, {}, 1])
def test_classify_rejects_non_snapshot(payload: object) -> None:
    with pytest.raises(ValueError):
        classify_goal_idle(payload)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"terminal_unharvested": -1},
        {"running": True},
        {"starting": "1"},
        {"unknown": 1.5},
        {"waiting": -3},
    ],
)
def test_invalid_census_counts_are_rejected(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        census(**kwargs)


def test_empty_thread_ids_are_rejected() -> None:
    with pytest.raises(ValueError):
        snapshot(watchdog_thread_id="")
    with pytest.raises(ValueError):
        snapshot(goal_thread_id="")


def test_subclassed_thread_ids_are_rejected() -> None:
    with pytest.raises(ValueError):
        snapshot(watchdog_thread_id=_ThreadID("watchdog-thread-synthetic-a"))
    with pytest.raises(ValueError):
        snapshot(goal_thread_id=_ThreadID("goal-thread-synthetic-b"))


@pytest.mark.parametrize(
    "state",
    [GlmDispositionState.BLOCKED, GlmDispositionState.NOT_BENEFICIAL],
)
def test_disposition_reason_required_for_negative_states(
    state: GlmDispositionState,
) -> None:
    with pytest.raises(ValueError):
        GlmDisposition(state=state, reason=None)
    with pytest.raises(ValueError):
        GlmDisposition(state=state, reason="")
    with pytest.raises(ValueError):
        GlmDisposition(state=state, reason=_ThreadID("EXTERNAL_DEPENDENCY"))


@pytest.mark.parametrize(
    "state", [GlmDispositionState.NONE, GlmDispositionState.ACTIVE]
)
def test_disposition_reason_forbidden_otherwise(
    state: GlmDispositionState,
) -> None:
    with pytest.raises(ValueError):
        GlmDisposition(state=state, reason="because")
    with pytest.raises(ValueError):
        GlmDisposition(state="BLOCKED", reason=None)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"execution_census": {"running": 1}},
        {"actionable_queue_count": -1},
        {"actionable_queue_count": True},
        {"fingerprint_state": "UNCHANGED"},
        {"safe_ready_state": "GENUINE"},
        {"pending_steer_state": "NONE"},
        {"eligible_r2r3_task": 1},
        {"eligible_r2r3_task": "yes"},
        {"human_instruction_pending": 1},
        {"human_instruction_pending": "yes"},
        {"human_instruction_pending": None},
        {"glm_disposition": ("NONE", None)},
        {"glm_quota_state": "CONFIRMED_AVAILABLE"},
    ],
)
def test_invalid_snapshot_inputs_are_rejected(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        snapshot(**kwargs)


def test_same_snapshot_is_idempotent() -> None:
    item = snapshot(
        execution_census=census(running=1, waiting=2),
        actionable_queue_count=1,
        pending_steer_state=PendingSteerState.EQUIVALENT_PENDING_FRESH,
    )
    assert classify_goal_idle(item) == classify_goal_idle(item)


def test_multi_reason_codes_are_in_canonical_order() -> None:
    verdict = classify_goal_idle(
        snapshot(
            execution_census=census(stalled=1, waiting=1),
            actionable_queue_count=1,
        )
    )
    assert verdict.action is GoalGuardAction.ACTIVE_CONTINUE
    assert verdict.reason_codes == (
        "EXECUTIONS_WAITING",
        "EXECUTIONS_STALLED",
        "ACTIONABLE_QUEUE_NON_EMPTY",
    )
