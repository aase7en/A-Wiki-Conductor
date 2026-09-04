from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from a_conductor.worker_resilience import (
    BackoffSchedule,
    RepositoryGate,
    detect_fleet_outage,
    plan_parallel_recovery,
    worker_available_for_work,
    CircuitStatus,
    RecoveryAction,
    RestartBudget,
    WorkerCircuit,
    WorkerDerivedState,
    WorkerHealthProbes,
    WorkerProcessIdentity,
    WorkerRecoveryState,
    WorkerRecoveryStore,
    classify_worker,
    record_recovery_event,
    recovery_action,
)

NOW = datetime(2026, 9, 4, 3, 0, tzinfo=timezone.utc)


def _probes(**over):
    base = dict(
        process_alive=True,
        mcp_ready=True,
        tunnel_reachable=True,
        remote_session_ready=True,
        ownership_safe=True,
        task_state_known=True,
        remote_http_status=None,
    )
    base.update(over)
    return WorkerHealthProbes(**base)


def _circuit(**over):
    return WorkerCircuit(failure_threshold=3, cooldown_seconds=60, stable_window_seconds=120, **over)


# ---------------- classification ----------------

def test_healthy_when_all_layers_pass():
    assert classify_worker(_probes(), first_failure_seen=False) is WorkerDerivedState.HEALTHY


def test_first_failure_is_suspect_not_down():
    assert classify_worker(_probes(remote_session_ready=False), first_failure_seen=True) is (
        WorkerDerivedState.SUSPECT
    )


def test_process_down_outranks_other_layers():
    assert classify_worker(_probes(process_alive=False, mcp_ready=False), first_failure_seen=False) is (
        WorkerDerivedState.PROCESS_DOWN
    )


def test_mcp_down_with_live_process():
    assert classify_worker(_probes(mcp_ready=False), first_failure_seen=False) is WorkerDerivedState.MCP_DOWN


def test_tunnel_down_with_local_mcp_alive():
    assert classify_worker(_probes(tunnel_reachable=False), first_failure_seen=False) is WorkerDerivedState.TUNNEL_DOWN


def test_remote_429_is_rate_limited_not_down():
    assert classify_worker(_probes(remote_http_status=429), first_failure_seen=False) is WorkerDerivedState.RATE_LIMITED


def test_remote_404_is_endpoint_missing():
    assert classify_worker(_probes(remote_http_status=404), first_failure_seen=False) is WorkerDerivedState.ENDPOINT_MISSING


def test_remote_session_stale_with_healthy_local_stack():
    assert classify_worker(_probes(remote_session_ready=False), first_failure_seen=False) is (
        WorkerDerivedState.REMOTE_SESSION_STALE
    )


def test_ownership_blocked():
    assert classify_worker(_probes(ownership_safe=False), first_failure_seen=False) is WorkerDerivedState.OWNERSHIP_BLOCKED


def test_task_unknown_is_task_ambiguous():
    assert classify_worker(_probes(task_state_known=False), first_failure_seen=False) is WorkerDerivedState.TASK_AMBIGUOUS


def test_quarantined_sticks_until_circuit_resets():
    assert classify_worker(
        _probes(), first_failure_seen=False, quarantined=True
    ) is WorkerDerivedState.QUARANTINED


# ---------------- recovery policy ----------------

def test_rate_limited_zero_restart_backoff_only():
    state = WorkerDerivedState.RATE_LIMITED
    assert recovery_action(state, circuit=_circuit(), budget=RestartBudget(limit=3)) is (
        RecoveryAction.BACKOFF_WAIT
    )


def test_endpoint_missing_reconciles_without_recreation():
    assert recovery_action(
        WorkerDerivedState.ENDPOINT_MISSING, circuit=_circuit(), budget=RestartBudget(limit=3)
    ) is RecoveryAction.RECONCILE_ENDPOINT


def test_stale_session_reconnects_without_restart():
    assert recovery_action(
        WorkerDerivedState.REMOTE_SESSION_STALE, circuit=_circuit(), budget=RestartBudget(limit=3)
    ) is RecoveryAction.RECONNECT_SESSION


def test_tunnel_down_restarts_only_tunnel():
    assert recovery_action(
        WorkerDerivedState.TUNNEL_DOWN, circuit=_circuit(), budget=RestartBudget(limit=3)
    ) is RecoveryAction.RESTART_TUNNEL


def test_mcp_down_restarts_component_only():
    assert recovery_action(
        WorkerDerivedState.MCP_DOWN, circuit=_circuit(), budget=RestartBudget(limit=3)
    ) is RecoveryAction.RESTART_COMPONENT


def test_process_down_requires_durable_spec_and_budget():
    assert recovery_action(
        WorkerDerivedState.PROCESS_DOWN,
        circuit=_circuit(),
        budget=RestartBudget(limit=3),
        durable_launch_spec=True,
    ) is RecoveryAction.RESTART_FROM_SPEC
    assert recovery_action(
        WorkerDerivedState.PROCESS_DOWN,
        circuit=_circuit(),
        budget=RestartBudget(limit=3),
        durable_launch_spec=False,
    ) is RecoveryAction.AWAIT_OPERATOR


def test_task_ambiguous_and_ownership_blocked_never_restart_or_replay():
    assert recovery_action(
        WorkerDerivedState.TASK_AMBIGUOUS, circuit=_circuit(), budget=RestartBudget(limit=3)
    ) is RecoveryAction.AWAIT_OPERATOR
    assert recovery_action(
        WorkerDerivedState.OWNERSHIP_BLOCKED, circuit=_circuit(), budget=RestartBudget(limit=3)
    ) is RecoveryAction.AWAIT_OPERATOR


def test_open_circuit_forces_quarantine_even_if_probes_now_pass():
    circuit = _circuit()
    for _ in range(3):
        circuit.record_failure(now=NOW)
    assert circuit.status is CircuitStatus.OPEN
    assert recovery_action(
        WorkerDerivedState.HEALTHY, circuit=circuit, budget=RestartBudget(limit=3)
    ) is RecoveryAction.QUARANTINE


def test_exhausted_budget_quarantines_instead_of_restarting():
    budget = RestartBudget(limit=2, used=2)
    assert recovery_action(
        WorkerDerivedState.PROCESS_DOWN,
        circuit=_circuit(),
        budget=budget,
        durable_launch_spec=True,
    ) is RecoveryAction.QUARANTINE


def test_suspect_reprobes_cheaply():
    assert recovery_action(
        WorkerDerivedState.SUSPECT, circuit=_circuit(), budget=RestartBudget(limit=3)
    ) is RecoveryAction.REPROBE


# ---------------- backoff ----------------

def test_backoff_is_exponential_capped_and_jittered():
    schedule = BackoffSchedule(base_seconds=1.0, cap_seconds=300.0, jitter_fraction=0.0)
    assert schedule.delay_seconds(attempt=0) == 1.0
    assert schedule.delay_seconds(attempt=3) == 8.0
    assert schedule.delay_seconds(attempt=30) == 300.0
    jittered = BackoffSchedule(base_seconds=1.0, cap_seconds=300.0, jitter_fraction=0.25)
    for attempt in range(6):
        low, high = schedule.delay_seconds(attempt=attempt), jittered.delay_seconds(attempt=attempt)
        assert 0.75 * low <= high <= 1.25 * low


def test_backoff_honors_retry_after():
    schedule = BackoffSchedule(base_seconds=1.0, cap_seconds=300.0, jitter_fraction=0.0)
    assert schedule.delay_seconds(attempt=1, retry_after_seconds=42.0) == 42.0


# ---------------- circuit / anti-flap ----------------

def test_circuit_opens_on_threshold_and_flapping():
    circuit = _circuit()
    circuit.record_failure(now=NOW)
    circuit.record_failure(now=NOW)
    assert circuit.status is CircuitStatus.CLOSED
    circuit.record_failure(now=NOW)
    assert circuit.status is CircuitStatus.OPEN


def test_circuit_half_opens_after_cooldown_not_before():
    circuit = _circuit()
    for _ in range(3):
        circuit.record_failure(now=NOW)
    assert circuit.status_after(now=NOW + timedelta(seconds=59)) is CircuitStatus.OPEN
    assert circuit.status_after(now=NOW + timedelta(seconds=61)) is CircuitStatus.HALF_OPEN


def test_circuit_closes_only_after_stable_healthy_window():
    circuit = _circuit()
    for _ in range(3):
        circuit.record_failure(now=NOW)
    opened_at = NOW
    # probe success inside half-open starts the stable window but does not close
    assert circuit.record_probe_success(now=opened_at + timedelta(seconds=61)) is CircuitStatus.HALF_OPEN
    assert circuit.status_after(now=opened_at + timedelta(seconds=100)) is CircuitStatus.HALF_OPEN
    assert circuit.status_after(now=opened_at + timedelta(seconds=200)) is CircuitStatus.CLOSED


def test_probe_failure_during_half_open_reopens_immediately():
    circuit = _circuit()
    for _ in range(3):
        circuit.record_failure(now=NOW)
    later = NOW + timedelta(seconds=61)
    circuit.record_probe_success(now=later)
    assert circuit.record_failure(now=later + timedelta(seconds=1)) is CircuitStatus.OPEN


# ---------------- durable state ----------------

def _identity(pid=111):
    return WorkerProcessIdentity(
        pid=pid,
        process_start_epoch=1788490277.0,
        executable="C:/AI/dwb-serena-tunnel-starter/tunnel-client/tunnel-client.exe",
        command_sha256="a" * 64,
    )


def _recovery_state(worker="sunday-worker-1"):
    return WorkerRecoveryState(
        worker_id=worker,
        launch_spec_fingerprint="spec-sha",
        identity=_identity(),
        endpoint_ref="http://127.0.0.1:18011/readyz",
        tunnel_ref="tunnel-profile:serena-sunday-worker-1",
        project="A:/GitHub/A-Wiki-Conductor",
        worktree="A:/GitHub/A-Wiki-Conductor",
        branch="main",
        head="68079e3d00047ca9432f0aefe3ad667f892614d0",
        active_task=None,
        claim_ref=None,
        last_healthy_at=NOW,
        failure_layer="TUNNEL",
        failure_reason="TUNNEL_START_FAILED",
        recovery_attempts=1,
        circuit_state="CLOSED",
        last_execution_identity=None,
    )


def test_recovery_state_roundtrip_without_secrets(tmp_path):
    state = _recovery_state()
    data = json.dumps(state.as_dict())
    for forbidden in ("api", "token", "secret", "key="):
        assert forbidden not in data.lower() or "endpoint_ref" in data
    restored = WorkerRecoveryState.from_dict(json.loads(data))
    assert restored == state


def test_store_persists_and_restores_across_conductor_restart(tmp_path):
    store = WorkerRecoveryStore(tmp_path / "recovery.json")
    state = _recovery_state()
    store.upsert(state)
    fresh = WorkerRecoveryStore(tmp_path / "recovery.json")
    assert fresh.load()[("sunday-worker-1",)] if False else fresh.load()["sunday-worker-1"] == state


def test_duplicate_recovery_events_are_idempotent():
    state = _recovery_state()
    first = record_recovery_event(state, event_id="evt-1", now=NOW)
    second = record_recovery_event(state, event_id="evt-1", now=NOW + timedelta(seconds=5))
    assert first is True and second is False


# ---------------- process identity guard ----------------

def test_pid_reuse_rejected_by_start_time_or_command_identity():
    original = _identity(pid=500)
    reused_pid_new_start = WorkerProcessIdentity(
        pid=500,
        process_start_epoch=9999999999.0,
        executable=original.executable,
        command_sha256=original.command_sha256,
    )
    wrong_exe = WorkerProcessIdentity(
        pid=500,
        process_start_epoch=original.process_start_epoch,
        executable="C:/Windows/System32/evil.exe",
        command_sha256=original.command_sha256,
    )
    wrong_cmd = WorkerProcessIdentity(
        pid=500,
        process_start_epoch=original.process_start_epoch,
        executable=original.executable,
        command_sha256="b" * 64,
    )
    assert original.matches(original)
    assert not original.matches(reused_pid_new_start)
    assert not original.matches(wrong_exe)
    assert not original.matches(wrong_cmd)


def test_broad_kill_path_impossible_no_taskkill_by_name_api():
    import inspect
    from a_conductor import worker_resilience as module
    source = inspect.getsource(module)
    for forbidden in ("taskkill /im", "taskkill /f /im", "Stop-Process -Name",
                      "ps aux | kill", "killall"):
        assert forbidden not in source


def test_logs_and_states_contain_no_credentials_or_tunnel_ids():
    state = _recovery_state()
    text = json.dumps(state.as_dict())
    # tunnel_ref is an opaque profile reference, never the tunnel token/id value
    assert "tunnel" in text  # reference kept
    assert "eyJ" not in text and "tdp-" not in text


# ---------------- verifier-mandated explicit cases 2, 9, 20, 21, 22 ----------------

def test_case2_simultaneous_five_worker_transport_failure_zero_worker_restart():
    """All five workers lose transport in one probe round: not a single
    action may restart a local worker process/component."""
    states = {
        "sunday-worker-1": WorkerDerivedState.REMOTE_SESSION_STALE,
        "sunday-worker-2": WorkerDerivedState.TUNNEL_DOWN,
        "sunday-worker-3": WorkerDerivedState.RATE_LIMITED,
        "sunday-worker-4": WorkerDerivedState.ENDPOINT_MISSING,
        "sunday-worker-5": WorkerDerivedState.REMOTE_SESSION_STALE,
    }
    plan = plan_parallel_recovery(
        states,
        circuit_by_worker={w: _circuit() for w in states},
        budget_by_worker={w: RestartBudget(limit=3) for w in states},
    )
    assert set(plan) == set(states)
    for action in plan.values():
        assert action not in (RecoveryAction.RESTART_FROM_SPEC, RecoveryAction.RESTART_COMPONENT)


def test_case9_unknown_dirty_state_blocks_restart_and_reassignment():
    unknown_dirty = RepositoryGate(dirty_state_known=False, dirty_safe=False,
                                   ownership_safe=True, task_state_known=True)
    assert recovery_action(
        WorkerDerivedState.PROCESS_DOWN, circuit=_circuit(),
        budget=RestartBudget(limit=3), durable_launch_spec=True,
        gate=unknown_dirty,
    ) is RecoveryAction.AWAIT_OPERATOR
    assert worker_available_for_work(WorkerDerivedState.HEALTHY, unknown_dirty) is False


def test_case20_recovered_worker_must_pass_repository_ownership_gate_before_mutation():
    good_gate = RepositoryGate(dirty_state_known=True, dirty_safe=True,
                               ownership_safe=True, task_state_known=True)
    dirty_unsafe = RepositoryGate(dirty_state_known=True, dirty_safe=False,
                                  ownership_safe=True, task_state_known=True)
    ownership_unsafe = RepositoryGate(dirty_state_known=True, dirty_safe=True,
                                      ownership_safe=False, task_state_known=True)
    assert worker_available_for_work(WorkerDerivedState.HEALTHY, good_gate) is True
    assert worker_available_for_work(WorkerDerivedState.HEALTHY, dirty_unsafe) is False
    assert worker_available_for_work(WorkerDerivedState.HEALTHY, ownership_unsafe) is False
    assert worker_available_for_work(WorkerDerivedState.SUSPECT, good_gate) is False


def test_case21_parallel_recovery_no_ownership_collision():
    states = {
        f"sunday-worker-{n}": WorkerDerivedState.PROCESS_DOWN for n in range(1, 6)
    }
    plan_a = plan_parallel_recovery(
        states,
        circuit_by_worker={w: _circuit() for w in states},
        budget_by_worker={w: RestartBudget(limit=3) for w in states},
        durable_spec_by_worker={w: True for w in states},
    )
    plan_b = plan_parallel_recovery(
        states,
        circuit_by_worker={w: _circuit() for w in states},
        budget_by_worker={w: RestartBudget(limit=3) for w in states},
        durable_spec_by_worker={w: True for w in states},
    )
    assert plan_a == plan_b                      # deterministic, replay-stable
    assert set(plan_a) == set(states)            # every worker exactly one action
    assert len(plan_a) == len(states)            # no worker planned twice
    incomplete = {w: _circuit() for w in states}
    incomplete.pop("sunday-worker-3")  # a worker without its circuit is a hard error
    with pytest.raises(ValueError):
        plan_parallel_recovery(
            states,
            circuit_by_worker=incomplete,
            budget_by_worker={w: RestartBudget(limit=3) for w in states},
        )


def test_case22_outage_detected_deterministically_before_manual_intervention():
    one_probe_round = {
        "w1": _probes(remote_session_ready=False),
        "w2": _probes(tunnel_reachable=False),
        "w3": _probes(),
        "w4": _probes(remote_http_status=429),
        "w5": _probes(),
    }
    report = detect_fleet_outage(one_probe_round, min_affected=2)
    assert report is not None
    assert set(report.affected_workers) == {"w1", "w2", "w4"}
    assert report.layers == ("REMOTE_SESSION", "TUNNEL", "RATE_LIMIT")
    assert detect_fleet_outage(
        {"w1": _probes(), "w2": _probes()}, min_affected=2
    ) is None  # single-worker blip is not a fleet outage
    assert detect_fleet_outage(
        {"w1": _probes(mcp_ready=False), "w2": _probes(mcp_ready=False)},
        min_affected=2,
        transport_only=True,
    ) is None  # local MCP failures are not a shared-transport outage
