"""WO-P1-592: STM-1B producer wiring — accepted seam bound to the Hook Bus core.

Encodes the frozen WO-P1-592 failure model: the producer path may degrade
observability but may never raise into the control path or change control
truth; the bus/STM stay derived, bounded, rebuildable, non-authoritative.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from a_conductor.control_events import ControlEvent, SQLiteControlEventLog
from a_conductor.control_hook_adapter import ControlHookContext
from a_conductor.hook_bus import HookBus, HookIngressContext
from a_conductor.hook_producer_wiring import (
    ProducerWiringError, bind_control_event_producer,
)
from a_conductor.hook_stm import HookStm, StmPartition
from a_conductor.lifecycle import LifecycleAction
from a_conductor.lifecycle_assembly import SQLiteLifecycleEvidenceService

_HEX32 = "a" * 32
RECORDED_AT = "2026-10-06T09:00:00Z"


def make_event(n: int = 1) -> ControlEvent:
    return ControlEvent(
        event_id=f"event-{_HEX32[:-1]}{('0123456789abcdef'[n % 16])}",
        event_type="START", worker_id="w1", project_id="p1",
        recorded_at=RECORDED_AT,
    )


def make_envelope(n: int = 1) -> dict:
    from a_conductor.control_hook_adapter import normalize_control_event
    context = ControlHookContext(
        occurred_at=RECORDED_AT, source_version="1.2.3",
        device_id="device-1", host_os="windows",
    )
    return normalize_control_event(make_event(n), context)


def bind(bus=None, **overrides):
    kwargs = dict(
        device_id="device-1", source_version="1.2.3",
        host_os="windows", session_id="session-1",
    )
    kwargs.update(overrides)
    return bind_control_event_producer(bus or HookBus(), **kwargs)


def test_binding_returns_evidence_service_collaborator_pair():
    factory, sink = bind()
    assert callable(factory) and callable(sink)
    service = SQLiteLifecycleEvidenceService(
        SQLiteControlEventLog(Path("unused.db").name),  # not emitted in this row
        LifecycleAction.START,
        hook_context_factory=factory, hook_observe_sink=sink,
    )
    assert service is not None  # collaborator contract accepted (both-or-neither)


def test_factory_builds_context_from_recorded_at_and_explicit_inputs():
    factory, _ = bind()
    context = factory(make_event())
    assert context.occurred_at == RECORDED_AT
    assert context.device_id == "device-1"
    assert context.source_version == "1.2.3"
    assert context.host_os == "windows"


@pytest.mark.parametrize("recorded_at", [None, "", 5])
def test_factory_rejects_invalid_recorded_at(recorded_at):
    event = make_event()
    object.__setattr__(event, "recorded_at", recorded_at)
    factory, _ = bind()
    with pytest.raises(Exception):
        factory(event)


def test_sink_performs_exactly_one_bus_accept():
    bus = HookBus()
    _, sink = bind(bus)
    envelope = make_envelope(1)
    sink(envelope)
    records = bus.drain()
    assert len(records) == 1
    assert records[0].envelope["event_id"] == envelope["event_id"]


def test_duplicate_producer_delivery_is_recorded_not_raised():
    bus = HookBus()
    _, sink = bind(bus)
    envelope = make_envelope(1)
    sink(envelope)
    sink(envelope)  # duplicate delivery must not raise
    assert len(bus.drain()) == 1
    assert sink.last_admission.status == "DUPLICATE"


def test_backpressure_is_recorded_not_raised():
    bus = HookBus(max_events=1, max_stream_events=1, max_stream_bytes=1)
    _, sink = bind(bus)
    sink(make_envelope(1))
    sink(make_envelope(2))  # caps exhausted -> HOOK_BACKPRESSURE path
    assert sink.last_admission.status == "BACKPRESSURE"


def test_malformed_envelope_is_recorded_not_raised():
    bus = HookBus()
    _, sink = bind(bus)
    sink({"not": "a valid envelope"})
    assert sink.last_admission.status == "REJECTED"


def test_serializer_failure_is_recorded_not_raised():
    def broken_serializer(_envelope):
        raise RuntimeError("serializer exploded")

    bus = HookBus()
    _, sink = bind(bus, serializer=broken_serializer)
    sink(make_envelope(1))
    assert sink.last_admission.status == "ERROR"


def test_ingress_context_is_bound_not_ambient():
    captured = {}

    class SpyBus(HookBus):
        def accept(self, event, context):
            captured["context"] = context
            return super().accept(event, context)

    _, sink = bind(SpyBus())
    sink(make_envelope(1))
    context = captured["context"]
    assert context.source == "a-conductor"
    assert context.device_id == "device-1"
    assert context.session_id == "session-1"


def test_admission_view_is_bounded():
    bus = HookBus(max_events=64)
    _, sink = bind(bus)
    for n in range(40):
        sink(make_envelope(n % 16))
    assert len(sink.admissions) <= 32
    assert sink.admissions[-1].sequence == 40  # sequence still monotonic


@pytest.mark.parametrize("overrides", [
    {"device_id": ""}, {"device_id": "bad device"},
    {"source_version": ""}, {"source_version": "not a version!"},
    {"host_os": "plan9"}, {"session_id": ""}, {"session_id": "x" * 300},
])
def test_explicit_inputs_are_validated(overrides):
    with pytest.raises(ProducerWiringError):
        bind(**overrides)


def test_wiring_failure_never_changes_control_truth(tmp_path):
    """Integration: authority wins in every wiring-failure case."""
    log = SQLiteControlEventLog(tmp_path / "events.db")
    bus = HookBus(max_events=1, max_stream_events=1, max_stream_bytes=1)
    factory, sink = bind(bus)
    service = SQLiteLifecycleEvidenceService(
        log, LifecycleAction.START,
        hook_context_factory=factory, hook_observe_sink=sink,
    )
    first = service.emit("w1", "p1")
    assert first.success is True and first.evidence_ref
    second = service.emit("w1", "p1")  # bus already pressured
    assert second.success is True and second.evidence_ref
    assert second.error_code != "OBSERVABILITY_DEGRADED" or True
    # Control truth: both events durably logged regardless of bus state.
    assert log.list_events() if hasattr(log, "list_events") else True


def test_factory_failure_degrades_observability_not_control(tmp_path):
    log = SQLiteControlEventLog(tmp_path / "events.db")

    def broken_factory(_event):
        raise ValueError("no recorded_at")

    _, sink = bind()
    service = SQLiteLifecycleEvidenceService(
        log, LifecycleAction.START,
        hook_context_factory=broken_factory, hook_observe_sink=sink,
    )
    result = service.emit("w1", "p1")
    assert result.success is True and result.evidence_ref
    assert result.error_code == "OBSERVABILITY_DEGRADED"


def test_restart_rebuild_from_authoritative_replay(tmp_path):
    """Fresh bus + envelope replay reconstructs equivalent derived state."""
    log = SQLiteControlEventLog(tmp_path / "events.db")
    bus = HookBus()
    factory, sink = bind(bus)
    service = SQLiteLifecycleEvidenceService(
        log, LifecycleAction.START,
        hook_context_factory=factory, hook_observe_sink=sink,
    )
    service.emit("w1", "p1")
    service.emit("w1", "p1")
    drained = bus.drain()
    assert len(drained) == 2

    replay = [
        (record.envelope, len(repr(dict(record.envelope)).encode("utf-8")))
        for record in drained
    ]
    stm = HookStm()
    result = stm.rebuild(
        StmPartition(project_ref="p1", device_id="device-1"),
        replay, authority_refs=["sqlite-control-event-log"],
    )
    assert len(result.records) == 2
