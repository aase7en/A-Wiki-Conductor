from __future__ import annotations

import pytest

from a_conductor.connector_recovery import (
    ConnectorRecoveryCoordinator,
    ConnectorRecoveryRecord,
    ConnectorRecoveryState,
)
from a_conductor.local_instances import (
    InstanceHealthState,
    InstanceOrchestrationOutcome,
    InstanceResultCode,
)
from a_conductor.worker_resilience import (
    REASON_CODES,
    CoordinatorDisposition,
    DispositionHealth,
    RepositoryGate,
    WorkerDerivedState,
    WorkerHealthProbes,
    WorkerProcessIdentity,
    ObservationDeduper,
    classify_worker,
    coordinator_disposition,
    detect_fleet_outage,
    plan_parallel_recovery,
    worker_available_for_work,
)


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


# ---------------- classification (unchanged policy) ----------------

def test_healthy_when_all_layers_pass():
    assert classify_worker(_probes(), first_failure_seen=False) is WorkerDerivedState.HEALTHY


def test_first_failure_is_suspect():
    assert classify_worker(
        _probes(remote_session_ready=False), first_failure_seen=True
    ) is WorkerDerivedState.SUSPECT


def test_layer_states_classify_independently():
    cases = [
        (dict(process_alive=False), WorkerDerivedState.PROCESS_DOWN),
        (dict(mcp_ready=False), WorkerDerivedState.MCP_DOWN),
        (dict(tunnel_reachable=False), WorkerDerivedState.TUNNEL_DOWN),
        (dict(remote_session_ready=False), WorkerDerivedState.REMOTE_SESSION_STALE),
        (dict(remote_http_status=429), WorkerDerivedState.RATE_LIMITED),
        (dict(remote_http_status=404), WorkerDerivedState.ENDPOINT_MISSING),
        (dict(ownership_safe=False), WorkerDerivedState.OWNERSHIP_BLOCKED),
        (dict(task_state_known=False), WorkerDerivedState.TASK_AMBIGUOUS),
    ]
    for over, expected in cases:
        assert classify_worker(_probes(**over), first_failure_seen=False) is expected
    assert classify_worker(_probes(), first_failure_seen=False, quarantined=True) is (
        WorkerDerivedState.QUARANTINED
    )


# ---------------- authority bridge dispositions ----------------

def test_transport_and_process_deaths_report_unexpected_stopped_with_restart():
    for state in (
        WorkerDerivedState.PROCESS_DOWN,
        WorkerDerivedState.MCP_DOWN,
        WorkerDerivedState.TUNNEL_DOWN,
    ):
        d = coordinator_disposition(state)
        assert d.health is DispositionHealth.UNEXPECTED_STOPPED
        assert d.restart_permitted is True
        assert d.suppress_recovery is False


def test_429_404_stale_suspect_never_restart_local_worker():
    for state in (
        WorkerDerivedState.RATE_LIMITED,
        WorkerDerivedState.ENDPOINT_MISSING,
        WorkerDerivedState.REMOTE_SESSION_STALE,
        WorkerDerivedState.SUSPECT,
    ):
        d = coordinator_disposition(state)
        assert d.health is DispositionHealth.READY
        assert d.restart_permitted is False


def test_ownership_ambiguity_and_quarantine_suppress_recovery():
    for state in (
        WorkerDerivedState.OWNERSHIP_BLOCKED,
        WorkerDerivedState.TASK_AMBIGUOUS,
        WorkerDerivedState.QUARANTINED,
    ):
        d = coordinator_disposition(state)
        assert d.restart_permitted is False
        assert d.suppress_recovery is True


def test_reason_codes_form_closed_set_no_raw_text_persists():
    for state in WorkerDerivedState:
        assert coordinator_disposition(state).reason_code in REASON_CODES
    with pytest.raises(ValueError):
        CoordinatorDisposition(
            DispositionHealth.READY, "Authorization: Bearer raw-secret-value", False
        )


# ---------------- coordinator integration (single authority) ----------------

class MemoryRecoveryStore:
    def __init__(self):
        self.records: dict[str, ConnectorRecoveryRecord] = {}
        self.writes = 0

    def get_connector_recovery(self, instance_name):
        return self.records.get(instance_name)

    def save_connector_recovery(self, record):
        self.records[record.instance_name] = record
        self.writes += 1
        return record

    def clear_connector_recovery(self, instance_name):
        self.records.pop(instance_name, None)


def _outcome(code):
    return InstanceOrchestrationOutcome(action="start", result_code=code, process_launched=True)


def _coordinator(store, starts, *, autostart=True, code=InstanceResultCode.RUNNING):
    return ConnectorRecoveryCoordinator(
        store=store,
        autostart_check=lambda name: autostart,
        start_instance=lambda name, **kw: (starts.append(name), _outcome(code))[1],
        clock_fn=lambda: 1000.0,
    )


_DEDUPER = ObservationDeduper()


def _observe(coordinator, state, name="Sunday-Worker-1"):
    if not _DEDUPER.should_report(name, state):
        return coordinator.observe(
            name, InstanceHealthState.UNKNOWN, reason_code="DUPLICATE_SUPPRESSED"
        )
    disposition = coordinator_disposition(state)
    health = (
        InstanceHealthState.READY
        if disposition.health is DispositionHealth.READY
        else InstanceHealthState.STOPPED
    )
    if disposition.suppress_recovery:
        coordinator.suppress(name)
    return coordinator.observe(name, health, reason_code=disposition.reason_code)


def test_unexpected_stopped_recovers_exactly_once():
    global _DEDUPER
    _DEDUPER = ObservationDeduper()
    store = MemoryRecoveryStore()
    starts: list[str] = []
    record = _observe(_coordinator(store, starts), WorkerDerivedState.PROCESS_DOWN)
    assert record.state is ConnectorRecoveryState.READY
    assert starts == ["Sunday-Worker-1"]


def test_manual_stop_suppresses_all_automatic_recovery():
    global _DEDUPER
    _DEDUPER = ObservationDeduper()
    store = MemoryRecoveryStore()
    starts: list[str] = []
    coordinator = _coordinator(store, starts)
    coordinator.suppress("Sunday-Worker-1")
    for _ in range(5):
        record = _observe(coordinator, WorkerDerivedState.PROCESS_DOWN)
    assert record.state is ConnectorRecoveryState.STOPPED
    assert record.recovery_suppressed is True
    assert starts == []


def test_duplicate_health_observation_no_duplicate_restart():
    global _DEDUPER
    _DEDUPER = ObservationDeduper()
    store = MemoryRecoveryStore()
    starts: list[str] = []
    coordinator = _coordinator(store, starts)
    _observe(coordinator, WorkerDerivedState.PROCESS_DOWN)
    record = None
    for _ in range(4):
        record = _observe(coordinator, WorkerDerivedState.PROCESS_DOWN)  # same epoch
    assert len(starts) == 1  # duplicates never re-restart
    assert record.state is ConnectorRecoveryState.READY
    # a genuine re-death goes through an intervening healthy observation
    _observe(coordinator, WorkerDerivedState.HEALTHY)
    record = _observe(coordinator, WorkerDerivedState.PROCESS_DOWN)
    assert len(starts) == 2  # transition reported: exactly one new restart
    assert record.state is ConnectorRecoveryState.READY


def test_rate_limited_disposition_observes_ready_zero_restarts():
    global _DEDUPER
    _DEDUPER = ObservationDeduper()
    store = MemoryRecoveryStore()
    starts: list[str] = []
    record = _observe(_coordinator(store, starts), WorkerDerivedState.RATE_LIMITED)
    assert record.state is ConnectorRecoveryState.READY
    assert starts == []


def test_authority_backoff_binds_recovery_failure_between_attempts():
    store = MemoryRecoveryStore()
    starts: list[str] = []
    coordinator = _coordinator(store, starts, code=InstanceResultCode.LAUNCH_FAILED)
    disposition = coordinator_disposition(WorkerDerivedState.TUNNEL_DOWN)
    first = coordinator.observe(
        "Sunday-Worker-1", InstanceHealthState.STOPPED, reason_code=disposition.reason_code
    )
    assert first.state is ConnectorRecoveryState.RECOVERING
    assert first.next_retry_at is not None
    coordinator.observe(
        "Sunday-Worker-1", InstanceHealthState.STOPPED, reason_code=disposition.reason_code
    )
    assert len(starts) == 1


def test_manual_start_rearms_recovery_after_suppression():
    global _DEDUPER
    _DEDUPER = ObservationDeduper()
    store = MemoryRecoveryStore()
    starts: list[str] = []
    coordinator = _coordinator(store, starts)
    coordinator.suppress("Sunday-Worker-1")
    coordinator.manual_start("Sunday-Worker-1")
    record = _observe(coordinator, WorkerDerivedState.PROCESS_DOWN)
    assert record.state is ConnectorRecoveryState.READY
    assert starts == ["Sunday-Worker-1"]


def test_ownership_hold_suppresses_before_any_observation_restart():
    global _DEDUPER
    _DEDUPER = ObservationDeduper()
    store = MemoryRecoveryStore()
    starts: list[str] = []
    record = _observe(_coordinator(store, starts), WorkerDerivedState.OWNERSHIP_BLOCKED)
    assert record.recovery_suppressed is True
    assert starts == []


def test_conductor_restart_restores_recovery_state_from_store():
    global _DEDUPER
    _DEDUPER = ObservationDeduper()
    store = MemoryRecoveryStore()
    starts: list[str] = []
    _observe(_coordinator(store, starts), WorkerDerivedState.PROCESS_DOWN)
    coordinator_b = ConnectorRecoveryCoordinator(
        store=store,
        autostart_check=lambda name: True,
        start_instance=lambda name, **kw: (
            starts.append(name),
            _outcome(InstanceResultCode.RUNNING),
        )[1],
        clock_fn=lambda: 1000.0,
    )
    record = _observe(coordinator_b, WorkerDerivedState.PROCESS_DOWN)
    assert record.state is ConnectorRecoveryState.READY
    assert starts == ["Sunday-Worker-1"]


# ---------------- availability gate ----------------

def _gate(**over):
    base = dict(dirty_state_known=True, dirty_safe=True, ownership_safe=True, task_state_known=True)
    base.update(over)
    return RepositoryGate(**base)


def test_recovered_worker_available_only_through_full_gate():
    assert worker_available_for_work(WorkerDerivedState.HEALTHY, _gate()) is True
    for over in (
        dict(dirty_state_known=False),
        dict(dirty_safe=False),
        dict(ownership_safe=False),
        dict(task_state_known=False),
    ):
        assert worker_available_for_work(WorkerDerivedState.HEALTHY, _gate(**over)) is False
    assert worker_available_for_work(WorkerDerivedState.SUSPECT, _gate()) is False
    assert worker_available_for_work(WorkerDerivedState.PROCESS_DOWN, _gate()) is False


# ---------------- parallel planning ----------------

def test_parallel_recovery_dispositions_deterministic_and_per_worker():
    states = {
        "w1": WorkerDerivedState.PROCESS_DOWN,
        "w2": WorkerDerivedState.RATE_LIMITED,
        "w3": WorkerDerivedState.OWNERSHIP_BLOCKED,
        "w4": WorkerDerivedState.TUNNEL_DOWN,
        "w5": WorkerDerivedState.HEALTHY,
    }
    plan_a = plan_parallel_recovery(states)
    plan_b = plan_parallel_recovery(states)
    assert plan_a == plan_b
    assert set(plan_a) == set(states)
    assert plan_a["w1"].restart_permitted and plan_a["w4"].restart_permitted
    assert not plan_a["w2"].restart_permitted
    assert plan_a["w3"].suppress_recovery
    assert not plan_a["w5"].restart_permitted


def test_unsafe_ownership_suppresses_never_restarts():
    unsafe_states = {
        "w-a": WorkerDerivedState.OWNERSHIP_BLOCKED,
        "w-b": WorkerDerivedState.PROCESS_DOWN,
    }
    plan = plan_parallel_recovery(unsafe_states)
    assert plan["w-a"].suppress_recovery is True
    assert not plan["w-a"].restart_permitted
    assert plan["w-b"].restart_permitted is True
    with pytest.raises(ValueError):
        plan_parallel_recovery({})


# ---------------- fleet correlation ----------------

def test_post_amplification_outage_requires_transport_evidence():
    all_down = {f"w{n}": _probes(process_alive=False) for n in range(1, 6)}
    evidenced = detect_fleet_outage(
        all_down, min_affected=2,
        recent_failures_by_worker={w: ("TUNNEL_START_FAILED",) for w in all_down},
    )
    assert evidenced is not None
    assert evidenced.layers == ("TRANSPORT_AMPLIFIED",)
    assert detect_fleet_outage(all_down, min_affected=2) is None
    assert detect_fleet_outage(
        all_down, min_affected=2,
        recent_failures_by_worker={w: ("WORKER_CRASH",) for w in all_down},
    ) is None


def test_direct_transport_states_detected_without_evidence():
    probes = {
        "w1": _probes(remote_session_ready=False),
        "w2": _probes(tunnel_reachable=False),
        "w3": _probes(),
    }
    report = detect_fleet_outage(probes, min_affected=2)
    assert report is not None
    assert set(report.affected_workers) == {"w1", "w2"}
    assert report.layers == ("REMOTE_SESSION", "TUNNEL")


def test_transport_only_mode_excludes_rate_limit_and_endpoint():
    probes = {
        "w1": _probes(remote_http_status=429),
        "w2": _probes(remote_http_status=404),
    }
    assert detect_fleet_outage(probes, min_affected=2, transport_only=True) is None
    assert detect_fleet_outage(probes, min_affected=2) is not None


# ---------------- process identity ----------------

def _identity(pid=500, start=1788490277.0, exe="C:/AI/tunnel/tunnel-client.exe", cmd="a" * 64):
    return WorkerProcessIdentity(pid=pid, process_start_epoch=start, executable=exe, command_sha256=cmd)


def test_pid_reuse_rejected_by_identity_tuple():
    original = _identity()
    assert original.matches(_identity())
    assert not original.matches(_identity(start=9999999999.0))
    assert not original.matches(_identity(exe="C:/Windows/evil.exe"))
    assert not original.matches(_identity(cmd="b" * 64))
    assert not original.matches(_identity(pid=501))


def test_identity_validates_inputs():
    with pytest.raises(ValueError):
        _identity(pid=0)
    with pytest.raises(ValueError):
        _identity(start=0)
    with pytest.raises(ValueError):
        _identity(exe=" ")
    with pytest.raises(ValueError):
        _identity(cmd="not-a-sha")


def test_no_broad_kill_surface_exists_in_policy_module():
    import inspect
    from a_conductor import worker_resilience as module
    source = inspect.getsource(module)
    for forbidden in ("taskkill /im", "Stop-Process -Name", "killall", "ps aux"):
        assert forbidden not in source
