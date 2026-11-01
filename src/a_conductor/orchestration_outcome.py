"""Bounded outcome publication over existing authority, HookBus and derived STM.

Readers are application-owned, fresh observation ports, not payload assertions.
No task state, control event, receipt, execution or retry is created here. The
application serializes this single-owner observer just as it does HookBus/STM.
"""
from __future__ import annotations

import json
from contextvars import ContextVar
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Protocol

from .control_events import ControlEvent
from .control_hook_adapter import ControlHookContext, normalize_control_event
from .hook_bus import HookBus, HookBusError, HookIngressContext
from .hook_stm import HookStm, StmPartition
from .orchestration import (
    OrchestrationError, OrchestrationOutcome, decode_outcome, encode_outcome, encode_signal,
)
from .orchestration_dispatcher import DispatchResult
from .orchestration_guards import GuardResult


class OutcomePublicationError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class OutcomePublisherPort(Protocol):
    def __call__(self, result: DispatchResult) -> OrchestrationOutcome: ...


def compose_outcome(result, *, signal=None) -> OrchestrationOutcome:
    """Map bounded results without inventing IDs or retaining guard metadata."""
    try:
        if type(result) is DispatchResult:
            if (len(result.execution_ids) > 1 or len(result.submission_ids) > 1
                    or (result.execution_ids and result.submission_ids)):
                raise OrchestrationError("SIGNAL_VALUE_INVALID")
            value = OrchestrationOutcome(result.signal_id, result.kind, result.decision,
                result.reason_code, result.evidence_refs,
                submission_ref=next(iter(result.submission_ids), None),
                execution_ref=next(iter(result.execution_ids), None),
                observability_degraded=result.observability_degraded)
        elif type(result) is GuardResult:
            encode_signal(signal)
            if type(result.admitted) is not bool:
                raise OrchestrationError("SIGNAL_VALUE_INVALID")
            decision = ("OBSERVED_ONLY" if result.reason == "OBSERVED_ONLY" else
                "RECONCILIATION_REQUIRED" if result.reason == "RECONCILIATION_REQUIRED" else
                "NO_ACTION" if result.admitted else "DENIED")
            value = OrchestrationOutcome(signal.signal_id, signal.kind, decision,
                result.reason, ())
        else:
            raise OrchestrationError("SIGNAL_VALUE_INVALID")
        return decode_outcome(encode_outcome(value))
    except (OrchestrationError, TypeError, ValueError, AttributeError):
        raise OutcomePublicationError("ORCH_OUTCOME_INVALID") from None


@dataclass(frozen=True, slots=True)
class ObservationSnapshot:
    """Fresh bound read of existing events; no new audit owner or event mapping.

    The reader must attest the exact owning job IDs and partition, resolve
    authority_ref from canonical checkpoints/events, and return only real
    ControlEvents for that worker/project. observed_at is its read time, not
    a producer event time. This DTO itself is not provenance authentication.
    """
    partition: StmPartition
    authority_ref: str
    execution_ids: tuple[str, ...]
    observed_at: datetime
    events: tuple[ControlEvent, ...]


@dataclass(frozen=True, slots=True)
class PublicationResult:
    outcome: OrchestrationOutcome
    reason_code: str
    guidance: str


class OutcomePublisher:
    """Observation-only callback for the explicitly registered runtime root.

    No subscriptions or bus dispatch callbacks are registered. Fresh authority
    is read even when STM is fresh; a cache hit cannot authorize or skip work.
    The bus remains owned/drained by its existing application consumer.
    """
    def __init__(self, *, partition, worker_id, snapshot_reader, bus, stm,
                 ingress, source_version, host_os, clock):
        if (type(partition) is not StmPartition or not isinstance(bus, HookBus)
                or not isinstance(stm, HookStm) or type(ingress) is not HookIngressContext
                or ingress.source != "a-conductor" or ingress.device_id != partition.device_id
                or not callable(snapshot_reader) or not callable(clock)
                or type(worker_id) is not str or not worker_id):
            raise ValueError("ORCH_OBSERVER_BINDING_INVALID")
        self._partition, self._worker = partition, worker_id
        self._reader, self._bus, self._stm = snapshot_reader, bus, stm
        self._ingress, self._clock = ingress, clock
        self._version, self._os = source_version, host_os
        self._publishing = ContextVar("orch_outcome_publishing", default=False)

    def __call__(self, result: DispatchResult) -> OrchestrationOutcome:
        return self.publish(result).outcome

    def publish(self, result: DispatchResult) -> PublicationResult:
        if self._publishing.get():
            raise OutcomePublicationError("ORCH_PUBLISH_REENTRANT_REFUSED")
        token = self._publishing.set(True)
        try:
            outcome = compose_outcome(result)
            snapshot = None
            pointer_validated = False
            try:
                if result.task_ref != self._partition.task_ref:
                    raise ValueError
                snapshot = self._reader(self._partition, result)
                now = self._clock()  # Check freshness after the bounded authority read.
                if (type(snapshot) is not ObservationSnapshot
                        or snapshot.partition != self._partition
                        or type(snapshot.execution_ids) is not tuple
                        or snapshot.execution_ids != result.execution_ids
                        or type(snapshot.observed_at) is not datetime
                        or snapshot.observed_at.tzinfo is None
                        or type(now) is not datetime or now.tzinfo is None
                        or not 0 <= (now - snapshot.observed_at).total_seconds() <= 30
                        or type(snapshot.events) is not tuple or len(snapshot.events) > 16):
                    raise ValueError
                # Validate every event/context before the first bus effect. Use
                # only closed context fields, never caller summary/metadata.
                records = []
                event_ids = set()
                for event in snapshot.events:
                    if (type(event) is not ControlEvent or event.project_id != self._partition.project_ref
                            or event.worker_id != self._worker or event.event_id in event_ids):
                        raise ValueError
                    event_ids.add(event.event_id)
                    envelope = normalize_control_event(event, ControlHookContext(
                        occurred_at=event.recorded_at, source_version=self._version,
                        device_id=self._partition.device_id, host_os=self._os,
                        task_id=self._partition.task_id, work_order=self._partition.work_order,
                        lane_id=self._partition.lane_id, evidence_refs=(snapshot.authority_ref,)))
                    wire = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
                    records.append((envelope, wire))
                if not records:
                    raise ValueError
                for _, wire in records:
                    admission = self._bus.accept(wire, self._ingress)
                    if admission.status not in ("ACCEPTED", "DUPLICATE"):
                        raise ValueError
                    pointer_validated = True
                    if admission.degraded:
                        raise ValueError
                if not 0 <= (self._clock() - snapshot.observed_at).total_seconds() <= 30:
                    raise ValueError
                view = self._stm.rebuild(self._partition,
                    tuple((envelope, len(wire)) for envelope, wire in records),
                    (snapshot.authority_ref,))
                if view.state != "FRESH" or view.rebuild_required:
                    raise ValueError
                return PublicationResult(outcome, "ORCH_OBSERVATION_AVAILABLE", "ORCH_OBSERVATION_AVAILABLE")
            except Exception as exc:
                # Rebuild only a bounded authority pointer on observer loss. Do
                # not retain partial projections, use cached events or replay
                # execution to repair telemetry. Never trust an invalid snapshot.
                # Backpressure occurs after HookBus validates schema/security;
                # arbitrary reader/normalization/ingress errors do not qualify.
                if isinstance(exc, HookBusError):
                    pointer_validated = exc.code == "HOOK_BACKPRESSURE"
                if pointer_validated and type(snapshot) is ObservationSnapshot:
                    try:
                        if (snapshot.partition == self._partition
                                and snapshot.execution_ids == result.execution_ids
                                and type(snapshot.observed_at) is datetime
                                and snapshot.observed_at.tzinfo is not None
                                and 0 <= (self._clock() - snapshot.observed_at).total_seconds() <= 30):
                            self._stm.rebuild(self._partition, (), (snapshot.authority_ref,))
                    except Exception:
                        pass
                return PublicationResult(replace(outcome, observability_degraded=True),
                    "ORCH_OBSERVATION_UNAVAILABLE", "ORCH_OBSERVATION_UNAVAILABLE")
        finally:
            self._publishing.reset(token)
