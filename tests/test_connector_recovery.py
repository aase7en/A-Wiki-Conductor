from __future__ import annotations

from dataclasses import replace

from a_conductor.connector_recovery import (
    ConnectorRecoveryCoordinator,
    ConnectorRecoveryRecord,
    ConnectorRecoveryState,
    RecoveryHistoryEventKind,
)
from a_conductor.local_instances import (
    InstanceHealthState,
    InstanceOrchestrationOutcome,
    InstanceResultCode,
)


class MemoryStore:
    def __init__(self) -> None:
        self.records: dict[str, ConnectorRecoveryRecord] = {}
        self.save_calls = 0
        self.history: list = []

    def get_connector_recovery(self, instance_name: str):
        return self.records.get(instance_name)

    def save_connector_recovery(self, record: ConnectorRecoveryRecord):
        self.save_calls += 1
        self.records[record.instance_name] = record
        return record

    def save_connector_recovery_history(self, record: ConnectorRecoveryRecord, events):
        self.save_calls += 1
        self.records[record.instance_name] = record
        self.history.extend(events)
        return record

    def clear_connector_recovery(self, instance_name: str) -> None:
        self.records.pop(instance_name, None)


class BareStore:
    def __init__(self) -> None:
        self.records: dict[str, ConnectorRecoveryRecord] = {}

    def get_connector_recovery(self, instance_name: str):
        return self.records.get(instance_name)

    def save_connector_recovery(self, record: ConnectorRecoveryRecord):
        self.records[record.instance_name] = record
        return record

    def clear_connector_recovery(self, instance_name: str) -> None:
        self.records.pop(instance_name, None)


class Clock:
    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now
def build(*, outcomes=(), autostart=True, clock=None):
    store = MemoryStore()
    calls: list[str] = []
    queue = list(outcomes)
    active_clock = clock or Clock()

    def start(name: str, *, cancel_check=None):
        if cancel_check is not None and cancel_check():
            return InstanceOrchestrationOutcome("start", InstanceResultCode.START_CANCELLED)
        calls.append(name)
        if queue:
            return queue.pop(0)
        return InstanceOrchestrationOutcome("start", InstanceResultCode.RUNNING)

    coordinator = ConnectorRecoveryCoordinator(
        store=store,
        autostart_check=lambda name: autostart,
        start_instance=start,
        clock_fn=active_clock,
        backoff_seconds=(5.0, 15.0, 30.0),
        failure_limit=3,
        failure_window_seconds=300.0,
    )
    return coordinator, store, calls, active_clock


def failed(code=InstanceResultCode.STARTED_NOT_READY):
    return InstanceOrchestrationOutcome("start", code, process_launched=True)


def test_ready_connector_never_launches_recovery() -> None:
    recovery, store, calls, _ = build()
    result = recovery.observe("Sunday-Worker-1", InstanceHealthState.READY)
    assert result.state is ConnectorRecoveryState.READY
    assert result.restart_count == 0
    assert calls == []
    assert store.records["Sunday-Worker-1"] == result
def test_unknown_health_fails_closed_without_launch() -> None:
    recovery, store, calls, _ = build()
    result = recovery.observe("Sunday-Worker-1", InstanceHealthState.UNKNOWN)
    assert result.state is ConnectorRecoveryState.STOPPED
    assert calls == []
    assert store.records["Sunday-Worker-1"] == result


def test_unexpected_stopped_autostart_attempts_one_recovery() -> None:
    recovery, _, calls, _ = build()
    result = recovery.observe(
        "Sunday-Worker-1",
        InstanceHealthState.STOPPED,
        reason_code="UNEXPECTED_EXIT",
    )
    assert calls == ["Sunday-Worker-1"]
    assert result.state is ConnectorRecoveryState.READY
    assert result.restart_count == 1
    assert result.failure_count == 0


def test_explicit_stop_suppresses_recovery_before_observation() -> None:
    recovery, store, calls, clock = build()
    stopped = recovery.suppress("Sunday-Worker-1")
    saves = store.save_calls
    clock.now += 15.0
    assert stopped.recovery_suppressed is True
    result = recovery.observe("Sunday-Worker-1", InstanceHealthState.STOPPED)
    assert result == stopped
    assert result.state is ConnectorRecoveryState.STOPPED
    assert result.recovery_suppressed is True
    assert result.last_exit_reason is None
    assert result.last_exit_at is None
    assert store.save_calls == saves
    assert calls == []
def test_manual_start_clears_suppression_and_failure_budget() -> None:
    recovery, store, _, _ = build()
    store.save_connector_recovery(
        ConnectorRecoveryRecord(
            instance_name="Sunday-Worker-1",
            state=ConnectorRecoveryState.DEGRADED,
            recovery_suppressed=True,
            failure_count=3,
            failure_window_started_at=900.0,
            restart_count=4,
            last_exit_reason="STARTED_NOT_READY",
            last_exit_at=990.0,
            next_retry_at=None,
            updated_at=990.0,
        )
    )
    result = recovery.manual_start("Sunday-Worker-1")
    assert result.state is ConnectorRecoveryState.STOPPED
    assert result.recovery_suppressed is False
    assert result.failure_count == 0
    assert result.failure_window_started_at is None
    assert result.restart_count == 4


def test_failed_recovery_uses_backoff_and_does_not_relaunch_early() -> None:
    recovery, _, calls, clock = build(outcomes=(failed(), failed()))
    first = recovery.observe("Sunday-Worker-1", InstanceHealthState.STOPPED)
    assert first.state is ConnectorRecoveryState.RECOVERING
    assert first.failure_count == 1
    assert first.next_retry_at == 1005.0
    assert calls == ["Sunday-Worker-1"]
    again = recovery.observe("Sunday-Worker-1", InstanceHealthState.STOPPED)
    assert again == first
    assert calls == ["Sunday-Worker-1"]
    clock.now = 1005.0
    second = recovery.observe("Sunday-Worker-1", InstanceHealthState.STOPPED)
    assert second.failure_count == 2
    assert second.next_retry_at == 1020.0
    assert calls == ["Sunday-Worker-1", "Sunday-Worker-1"]
def test_third_failure_inside_window_degrades_and_stops_launching() -> None:
    recovery, _, calls, clock = build(outcomes=(failed(), failed(), failed(), failed()))
    one = recovery.observe("Sunday-Worker-1", InstanceHealthState.STOPPED)
    clock.now = one.next_retry_at
    two = recovery.observe("Sunday-Worker-1", InstanceHealthState.STOPPED)
    clock.now = two.next_retry_at
    three = recovery.observe("Sunday-Worker-1", InstanceHealthState.STOPPED)
    assert three.state is ConnectorRecoveryState.DEGRADED
    assert three.failure_count == 3
    assert three.next_retry_at is None
    assert len(calls) == 3
    clock.now += 120.0
    same = recovery.observe("Sunday-Worker-1", InstanceHealthState.STOPPED)
    assert same.state is ConnectorRecoveryState.DEGRADED
    assert len(calls) == 3


def test_non_autostart_connector_stays_stopped() -> None:
    recovery, _, calls, _ = build(autostart=False)
    result = recovery.observe("Sunday-Worker-1", InstanceHealthState.STOPPED)
    assert result.state is ConnectorRecoveryState.STOPPED
    assert calls == []


def test_repeated_ready_observation_is_idempotent() -> None:
    recovery, store, calls, clock = build()
    first = recovery.observe("Sunday-Worker-1", InstanceHealthState.READY)
    saves = store.save_calls
    clock.now += 15.0
    second = recovery.observe("Sunday-Worker-1", InstanceHealthState.READY)
    assert second == first
    assert store.save_calls == saves
    assert calls == []


def test_repeated_suppressed_stopped_does_not_move_last_exit_timestamp() -> None:
    recovery, store, calls, clock = build()
    recovery.suppress("Sunday-Worker-1")
    first = recovery.observe("Sunday-Worker-1", InstanceHealthState.STOPPED)
    saves = store.save_calls
    clock.now += 15.0
    second = recovery.observe("Sunday-Worker-1", InstanceHealthState.STOPPED)
    assert second == first
    assert second.last_exit_at == first.last_exit_at
    assert store.save_calls == saves
    assert calls == []


def test_late_cancellation_reaches_start_boundary_without_failure_budget() -> None:
    checks = iter((False, True))
    recovery, _, calls, _ = build()
    result = recovery.observe(
        "Sunday-Worker-1",
        InstanceHealthState.STOPPED,
        cancel_check=lambda: next(checks),
    )
    assert result.state is ConnectorRecoveryState.STOPPED
    assert result.failure_count == 0
    assert calls == []


def test_store_without_history_support_still_recovers() -> None:
    store = BareStore()
    calls: list[str] = []

    def start(name: str, *, cancel_check=None):
        calls.append(name)
        return InstanceOrchestrationOutcome("start", InstanceResultCode.RUNNING)

    recovery = ConnectorRecoveryCoordinator(
        store=store,
        autostart_check=lambda name: True,
        start_instance=start,
        clock_fn=Clock(1000.0),
    )
    result = recovery.observe("Sunday-Worker-1", InstanceHealthState.STOPPED)
    assert result.state is ConnectorRecoveryState.READY
    assert result.restart_count == 1
    assert calls == ["Sunday-Worker-1"]


def test_stable_ready_refresh_appends_zero_history_events() -> None:
    recovery, store, _, clock = build()
    recovery.observe("Sunday-Worker-1", InstanceHealthState.READY)
    assert [event.kind for event in store.history] == [
        RecoveryHistoryEventKind.READY_OBSERVED
    ]
    events_after_first = len(store.history)
    clock.now += 15.0
    recovery.observe("Sunday-Worker-1", InstanceHealthState.READY)
    assert len(store.history) == events_after_first


def test_unexpected_stopped_recovery_ready_uses_fresh_post_start_time() -> None:
    store = MemoryStore()
    clock = Clock(2000.0)

    def start(name: str, *, cancel_check=None):
        clock.now += 30.0
        return InstanceOrchestrationOutcome("start", InstanceResultCode.RUNNING)

    recovery = ConnectorRecoveryCoordinator(
        store=store,
        autostart_check=lambda name: True,
        start_instance=start,
        clock_fn=clock,
    )
    result = recovery.observe(
        "Sunday-Worker-1",
        InstanceHealthState.STOPPED,
        reason_code="UNEXPECTED_EXIT",
    )
    assert result.state is ConnectorRecoveryState.READY
    assert result.restart_count == 1
    assert result.updated_at == 2030.0

    assert [event.kind for event in store.history] == [
        RecoveryHistoryEventKind.RECOVERY_STARTED,
        RecoveryHistoryEventKind.RECOVERY_READY,
    ]
    started, ready = store.history
    assert started.observed_at == 2000.0
    assert started.from_state is ConnectorRecoveryState.STOPPED
    assert started.to_state is ConnectorRecoveryState.RECOVERING
    assert started.reason_code == "UNEXPECTED_EXIT"
    assert ready.observed_at == 2030.0
    assert ready.observed_at > started.observed_at
    assert ready.from_state is ConnectorRecoveryState.RECOVERING
    assert ready.to_state is ConnectorRecoveryState.READY
    assert ready.restart_count == 1


def test_failed_attempts_and_degrade_are_reconstructable_from_history() -> None:
    recovery, store, _, clock = build(outcomes=(failed(), failed(), failed()))
    one = recovery.observe("Sunday-Worker-1", InstanceHealthState.STOPPED)
    clock.now = one.next_retry_at
    two = recovery.observe("Sunday-Worker-1", InstanceHealthState.STOPPED)
    clock.now = two.next_retry_at
    three = recovery.observe("Sunday-Worker-1", InstanceHealthState.STOPPED)
    assert three.state is ConnectorRecoveryState.DEGRADED

    assert [event.kind for event in store.history] == [
        RecoveryHistoryEventKind.RECOVERY_STARTED,
        RecoveryHistoryEventKind.RECOVERY_FAILED,
        RecoveryHistoryEventKind.RECOVERY_STARTED,
        RecoveryHistoryEventKind.RECOVERY_FAILED,
        RecoveryHistoryEventKind.RECOVERY_STARTED,
        RecoveryHistoryEventKind.RECOVERY_FAILED,
    ]
    degrade_event = store.history[-1]
    assert degrade_event.from_state is ConnectorRecoveryState.RECOVERING
    assert degrade_event.to_state is ConnectorRecoveryState.DEGRADED
    assert degrade_event.reason_code == "STARTED_NOT_READY"


def test_manual_suppress_and_manual_start_history_is_distinguishable() -> None:
    recovery, store, _, _ = build()
    recovery.suppress("Sunday-Worker-1")
    suppressed = store.history[-1]
    assert suppressed.kind is RecoveryHistoryEventKind.SUPPRESSED
    assert suppressed.from_state is ConnectorRecoveryState.STOPPED
    assert suppressed.to_state is ConnectorRecoveryState.STOPPED

    recovery.manual_start("Sunday-Worker-1")
    manual = store.history[-1]
    assert manual.kind is RecoveryHistoryEventKind.MANUAL_START
    assert manual.from_state is ConnectorRecoveryState.STOPPED
    assert manual.to_state is ConnectorRecoveryState.STOPPED
    assert manual.restart_count == 0


def test_manual_start_after_degrade_preserves_restart_count_in_history() -> None:
    recovery, store, _, _ = build()
    store.save_connector_recovery(
        ConnectorRecoveryRecord(
            instance_name="Sunday-Worker-1",
            state=ConnectorRecoveryState.DEGRADED,
            recovery_suppressed=True,
            failure_count=3,
            failure_window_started_at=900.0,
            restart_count=4,
            last_exit_reason="STARTED_NOT_READY",
            last_exit_at=990.0,
            next_retry_at=None,
            updated_at=990.0,
        )
    )
    result = recovery.manual_start("Sunday-Worker-1")
    assert result.restart_count == 4
    assert store.history[-1].kind is RecoveryHistoryEventKind.MANUAL_START
    assert store.history[-1].restart_count == 4


def test_non_autostart_stop_and_cancel_are_evidenced() -> None:
    stopped = build(autostart=False)
    recovery, store, _, _ = stopped
    recovery.observe("Sunday-Worker-1", InstanceHealthState.STOPPED)
    outage = store.history[-1]
    assert outage.kind is RecoveryHistoryEventKind.OUTAGE_OBSERVED
    assert outage.to_state is ConnectorRecoveryState.STOPPED
    assert outage.reason_code == "UNEXPECTED_STOPPED"

    checks = iter((False, False, True))
    recovery2, store2, _, _ = build()
    recovery2.observe(
        "Sunday-Worker-1",
        InstanceHealthState.STOPPED,
        cancel_check=lambda: next(checks),
    )
    cancelled = store2.history[-1]
    assert cancelled.kind is RecoveryHistoryEventKind.RECOVERY_CANCELLED
    assert cancelled.from_state is ConnectorRecoveryState.RECOVERING
    assert cancelled.to_state is ConnectorRecoveryState.STOPPED
