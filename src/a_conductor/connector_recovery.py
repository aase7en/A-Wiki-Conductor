"""Durable, bounded connector auto-recovery decisions.

This module owns no process launcher, scheduler, timer, or database. It consumes
observed connector health and delegates any restart to the existing connector
lifecycle seam. Persistence and clocks are injected for deterministic recovery.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Callable, Protocol, Sequence

from .local_instances import (
    InstanceHealthState,
    InstanceOrchestrationOutcome,
    InstanceResultCode,
)


class ConnectorRecoveryState(str, Enum):
    READY = "READY"
    STOPPED = "STOPPED"
    RECOVERING = "RECOVERING"
    DEGRADED = "DEGRADED"


class RecoveryHistoryEventKind(str, Enum):
    SUPPRESSED = "SUPPRESSED"
    MANUAL_START = "MANUAL_START"
    READY_OBSERVED = "READY_OBSERVED"
    UNKNOWN_OBSERVED = "UNKNOWN_OBSERVED"
    OUTAGE_OBSERVED = "OUTAGE_OBSERVED"
    RECOVERY_STARTED = "RECOVERY_STARTED"
    RECOVERY_READY = "RECOVERY_READY"
    RECOVERY_FAILED = "RECOVERY_FAILED"
    RECOVERY_CANCELLED = "RECOVERY_CANCELLED"


def _name(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ValueError("instance_name is invalid")
    return value.strip()


def _reason(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValueError("reason_code is invalid")
    if any(char in value for char in ("\x00", "\r", "\n")):
        raise ValueError("reason_code is invalid")
    return value.strip()


@dataclass(frozen=True, slots=True)
class ConnectorRecoveryRecord:
    instance_name: str
    state: ConnectorRecoveryState
    recovery_suppressed: bool = False
    failure_count: int = 0
    failure_window_started_at: float | None = None
    restart_count: int = 0
    last_exit_reason: str | None = None
    last_exit_at: float | None = None
    next_retry_at: float | None = None
    updated_at: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "instance_name", _name(self.instance_name))
        if not isinstance(self.state, ConnectorRecoveryState):
            object.__setattr__(self, "state", ConnectorRecoveryState(self.state))
        if not isinstance(self.recovery_suppressed, bool):
            raise ValueError("recovery_suppressed is invalid")
        for field_name in ("failure_count", "restart_count"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} is invalid")
        for field_name in (
            "failure_window_started_at", "last_exit_at", "next_retry_at", "updated_at"
        ):
            value = getattr(self, field_name)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0
            ):
                raise ValueError(f"{field_name} is invalid")
        object.__setattr__(self, "last_exit_reason", _reason(self.last_exit_reason))


class ConnectorRecoveryStore(Protocol):
    def get_connector_recovery(self, instance_name: str) -> ConnectorRecoveryRecord | None: ...
    def save_connector_recovery(self, record: ConnectorRecoveryRecord) -> ConnectorRecoveryRecord: ...
    def clear_connector_recovery(self, instance_name: str) -> None: ...


class ConnectorRecoveryHistoryWriter(Protocol):
    """Optional store seam: persist history events atomically with the snapshot.

    Stores that implement this method let the coordinator record lifecycle
    evidence in the same durable write as the recovery snapshot. Stores without
    it keep working exactly as before; no history is fabricated for them.
    """

    def save_connector_recovery_history(
        self,
        record: ConnectorRecoveryRecord,
        events: Sequence[ConnectorRecoveryHistoryEvent],
    ) -> ConnectorRecoveryRecord: ...


@dataclass(frozen=True, slots=True)
class ConnectorRecoveryHistoryEvent:
    instance_name: str
    kind: RecoveryHistoryEventKind
    from_state: ConnectorRecoveryState
    to_state: ConnectorRecoveryState
    observed_at: float
    reason_code: str | None = None
    restart_count: int = 0
    sequence: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "instance_name", _name(self.instance_name))
        if not isinstance(self.kind, RecoveryHistoryEventKind):
            object.__setattr__(self, "kind", RecoveryHistoryEventKind(self.kind))
        for field_name in ("from_state", "to_state"):
            value = getattr(self, field_name)
            if not isinstance(value, ConnectorRecoveryState):
                object.__setattr__(self, field_name, ConnectorRecoveryState(value))
        value = self.observed_at
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValueError("observed_at is invalid")
        object.__setattr__(self, "reason_code", _reason(self.reason_code))
        for field_name in ("restart_count", "sequence"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} is invalid")


class ConnectorRecoveryCoordinator:
    def __init__(
        self,
        *,
        store: ConnectorRecoveryStore,
        autostart_check: Callable[[str], bool],
        start_instance: Callable[..., InstanceOrchestrationOutcome],
        clock_fn: Callable[[], float],
        backoff_seconds: Sequence[float] = (5.0, 15.0, 30.0),
        failure_limit: int = 3,
        failure_window_seconds: float = 300.0,
    ) -> None:
        for method in ("get_connector_recovery", "save_connector_recovery"):
            if not callable(getattr(store, method, None)):
                raise ValueError(f"store must provide {method}")
        if not callable(autostart_check) or not callable(start_instance) or not callable(clock_fn):
            raise ValueError("recovery callbacks must be callable")
        history_writer = getattr(store, "save_connector_recovery_history", None)
        if history_writer is not None and not callable(history_writer):
            raise ValueError("save_connector_recovery_history must be callable")
        backoff = tuple(float(value) for value in backoff_seconds)
        if not backoff or any(value <= 0 for value in backoff):
            raise ValueError("backoff_seconds is invalid")
        if not isinstance(failure_limit, int) or isinstance(failure_limit, bool) or failure_limit < 1:
            raise ValueError("failure_limit is invalid")
        if failure_window_seconds <= 0:
            raise ValueError("failure_window_seconds is invalid")
        self._store = store
        self._history_writer = history_writer
        self._autostart_check = autostart_check
        self._start_instance = start_instance
        self._clock = clock_fn
        self._backoff = backoff
        self._failure_limit = failure_limit
        self._failure_window = float(failure_window_seconds)

    def _now(self) -> float:
        value = self._clock()
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValueError("clock returned invalid value")
        return float(value)

    def _current(self, instance_name: str, now: float) -> ConnectorRecoveryRecord:
        name = _name(instance_name)
        record = self._store.get_connector_recovery(name)
        if record is None:
            return ConnectorRecoveryRecord(
                instance_name=name,
                state=ConnectorRecoveryState.STOPPED,
                updated_at=now,
            )
        if not isinstance(record, ConnectorRecoveryRecord):
            raise ValueError("recovery store returned invalid record")
        return record

    def _save(
        self,
        record: ConnectorRecoveryRecord,
        events: Sequence[ConnectorRecoveryHistoryEvent] = (),
    ) -> ConnectorRecoveryRecord:
        if events and self._history_writer is not None:
            saved = self._history_writer(record, events)
        else:
            saved = self._store.save_connector_recovery(record)
        if not isinstance(saved, ConnectorRecoveryRecord):
            raise ValueError("recovery store returned invalid saved record")
        return saved

    def _event(
        self,
        *,
        current: ConnectorRecoveryRecord,
        record: ConnectorRecoveryRecord,
        kind: RecoveryHistoryEventKind,
        observed_at: float,
        reason_code: str | None = None,
    ) -> ConnectorRecoveryHistoryEvent:
        return ConnectorRecoveryHistoryEvent(
            instance_name=record.instance_name,
            kind=kind,
            from_state=current.state,
            to_state=record.state,
            observed_at=observed_at,
            reason_code=reason_code,
            restart_count=record.restart_count,
        )

    def suppress(self, instance_name: str) -> ConnectorRecoveryRecord:
        now = self._now()
        current = self._current(instance_name, now)
        record = replace(
            current,
            state=ConnectorRecoveryState.STOPPED,
            recovery_suppressed=True,
            next_retry_at=None,
            updated_at=now,
        )
        return self._save(
            record,
            events=(
                self._event(
                    current=current,
                    record=record,
                    kind=RecoveryHistoryEventKind.SUPPRESSED,
                    observed_at=now,
                ),
            ),
        )

    def manual_start(self, instance_name: str) -> ConnectorRecoveryRecord:
        now = self._now()
        current = self._current(instance_name, now)
        record = replace(
            current,
            state=ConnectorRecoveryState.STOPPED,
            recovery_suppressed=False,
            failure_count=0,
            failure_window_started_at=None,
            next_retry_at=None,
            updated_at=now,
        )
        return self._save(
            record,
            events=(
                self._event(
                    current=current,
                    record=record,
                    kind=RecoveryHistoryEventKind.MANUAL_START,
                    observed_at=now,
                ),
            ),
        )

    def _ready(self, current: ConnectorRecoveryRecord, now: float) -> ConnectorRecoveryRecord:
        if (
            current.state is ConnectorRecoveryState.READY
            and current.failure_count == 0
            and current.failure_window_started_at is None
            and current.next_retry_at is None
        ):
            return current
        record = replace(
            current,
            state=ConnectorRecoveryState.READY,
            failure_count=0,
            failure_window_started_at=None,
            next_retry_at=None,
            updated_at=now,
        )
        return self._save(
            record,
            events=(
                self._event(
                    current=current,
                    record=record,
                    kind=RecoveryHistoryEventKind.READY_OBSERVED,
                    observed_at=now,
                ),
            ),
        )

    def _failed_attempt(
        self,
        current: ConnectorRecoveryRecord,
        now: float,
        reason_code: str,
    ) -> ConnectorRecoveryRecord:
        window_start = current.failure_window_started_at
        if window_start is None or now - window_start > self._failure_window:
            window_start = now
            failures = 1
        else:
            failures = current.failure_count + 1
        if failures >= self._failure_limit:
            state = ConnectorRecoveryState.DEGRADED
            next_retry = None
        else:
            state = ConnectorRecoveryState.RECOVERING
            delay = self._backoff[min(failures - 1, len(self._backoff) - 1)]
            next_retry = now + delay
        record = replace(
            current,
            state=state,
            failure_count=failures,
            failure_window_started_at=window_start,
            last_exit_reason=_reason(reason_code),
            last_exit_at=now,
            next_retry_at=next_retry,
            updated_at=now,
        )
        return self._save(
            record,
            events=(
                self._event(
                    current=current,
                    record=record,
                    kind=RecoveryHistoryEventKind.RECOVERY_FAILED,
                    observed_at=now,
                    reason_code=reason_code,
                ),
            ),
        )

    def observe(
        self,
        instance_name: str,
        health: InstanceHealthState,
        *,
        reason_code: str = "UNEXPECTED_STOPPED",
        cancel_check: Callable[[], bool] | None = None,
    ) -> ConnectorRecoveryRecord:
        if not isinstance(health, InstanceHealthState):
            health = InstanceHealthState(health)
        now = self._now()
        current = self._current(instance_name, now)
        cancelled = cancel_check or (lambda: False)
        if cancelled():
            return current
        if health is InstanceHealthState.READY:
            return self._ready(current, now)
        if health is InstanceHealthState.UNKNOWN:
            if self._store.get_connector_recovery(current.instance_name) is None:
                return self._save(
                    current,
                    events=(
                        self._event(
                            current=current,
                            record=current,
                            kind=RecoveryHistoryEventKind.UNKNOWN_OBSERVED,
                            observed_at=now,
                        ),
                    ),
                )
            return current
        if current.recovery_suppressed:
            if (
                current.state is ConnectorRecoveryState.STOPPED
                and current.next_retry_at is None
            ):
                return current
            record = replace(
                current,
                state=ConnectorRecoveryState.STOPPED,
                next_retry_at=None,
                updated_at=now,
            )
            return self._save(
                record,
                events=(
                    self._event(
                        current=current,
                        record=record,
                        kind=RecoveryHistoryEventKind.OUTAGE_OBSERVED,
                        observed_at=now,
                        reason_code=reason_code,
                    ),
                ),
            )
        if not self._autostart_check(current.instance_name):
            normalized_reason = _reason(reason_code)
            if (
                current.state is ConnectorRecoveryState.STOPPED
                and current.next_retry_at is None
                and current.last_exit_reason == normalized_reason
            ):
                return current
            record = replace(
                current,
                state=ConnectorRecoveryState.STOPPED,
                next_retry_at=None,
                last_exit_reason=normalized_reason,
                last_exit_at=now,
                updated_at=now,
            )
            return self._save(
                record,
                events=(
                    self._event(
                        current=current,
                        record=record,
                        kind=RecoveryHistoryEventKind.OUTAGE_OBSERVED,
                        observed_at=now,
                        reason_code=normalized_reason,
                    ),
                ),
            )
        if current.state is ConnectorRecoveryState.DEGRADED:
            return current
        if current.next_retry_at is not None and now < current.next_retry_at:
            return current
        if cancelled():
            return current

        recovering_record = replace(
            current,
            state=ConnectorRecoveryState.RECOVERING,
            last_exit_reason=_reason(reason_code),
            last_exit_at=now,
            next_retry_at=None,
            updated_at=now,
        )
        recovering = self._save(
            recovering_record,
            events=(
                self._event(
                    current=current,
                    record=recovering_record,
                    kind=RecoveryHistoryEventKind.RECOVERY_STARTED,
                    observed_at=now,
                    reason_code=reason_code,
                ),
            ),
        )
        try:
            if cancel_check is None:
                outcome = self._start_instance(recovering.instance_name)
            else:
                outcome = self._start_instance(
                    recovering.instance_name, cancel_check=cancel_check
                )
        except Exception:
            return self._failed_attempt(recovering, now, "RECOVERY_START_EXCEPTION")
        if not isinstance(outcome, InstanceOrchestrationOutcome):
            return self._failed_attempt(recovering, now, "RECOVERY_RESULT_INVALID")
        if outcome.result_code is InstanceResultCode.START_CANCELLED:
            cancelled_record = replace(
                recovering,
                state=ConnectorRecoveryState.STOPPED,
                next_retry_at=None,
                updated_at=now,
            )
            return self._save(
                cancelled_record,
                events=(
                    self._event(
                        current=recovering,
                        record=cancelled_record,
                        kind=RecoveryHistoryEventKind.RECOVERY_CANCELLED,
                        observed_at=now,
                    ),
                ),
            )
        if outcome.result_code in {
            InstanceResultCode.RUNNING,
            InstanceResultCode.ALREADY_RUNNING,
        }:
            finished = self._now()
            ready_record = replace(
                recovering,
                state=ConnectorRecoveryState.READY,
                failure_count=0,
                failure_window_started_at=None,
                restart_count=recovering.restart_count + 1,
                next_retry_at=None,
                updated_at=finished,
            )
            return self._save(
                ready_record,
                events=(
                    self._event(
                        current=recovering,
                        record=ready_record,
                        kind=RecoveryHistoryEventKind.RECOVERY_READY,
                        observed_at=finished,
                    ),
                ),
            )
        return self._failed_attempt(recovering, now, outcome.result_code.value)
