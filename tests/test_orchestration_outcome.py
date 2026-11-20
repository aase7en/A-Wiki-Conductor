"""ORCH-1/6: fixture-owned authority/effects, no live runtime activation."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from test_orchestration_dispatcher import CONTEXT, lane, signal
from a_conductor.control_events import ControlEvent
from a_conductor.hook_bus import HookBus, HookIngressContext
from a_conductor.hook_stm import HookStm, StmError, StmPartition
from a_conductor.orchestration import decode_outcome, encode_outcome
from a_conductor.orchestration_dispatcher import DispatchResult
from a_conductor.orchestration_guards import GuardResult
from a_conductor.orchestration_outcome import (
    ObservationSnapshot, OutcomePublisher, OutcomePublicationError, compose_outcome,
)


NOW = datetime(2026, 11, 1, tzinfo=timezone.utc)
PARTITION = StmPartition("a-sunday-conductor", "windows-fixture", "task-review", lane_id="review")


def result():
    return DispatchResult("signal:review", "ENQUEUE", "task-review",
        "DISPATCH_OBSERVED", "ORCH_DISPATCH_OBSERVED", ("job:1",),
        ("evidence:canonical-ready",), ("job:1",))


@pytest.fixture
def observation():
    state = SimpleNamespace(tick=0, now=NOW)
    state.bus = HookBus(clock=lambda: state.tick)
    state.stm = HookStm(clock=lambda: state.tick, ttl_seconds=300)
    event = ControlEvent("event-" + "1" * 32, "START", "worker-review",
        PARTITION.project_ref, "2026-11-01T00:00:00Z")
    state.snapshot = ObservationSnapshot(PARTITION, "authority:checkpoint", ("job:1",), NOW, (event,))
    state.reader = Mock(side_effect=lambda *_: state.snapshot)
    state.make = lambda **kw: OutcomePublisher(partition=PARTITION,
        worker_id="worker-review", snapshot_reader=state.reader,
        bus=state.bus, stm=state.stm,
        ingress=HookIngressContext("a-conductor", PARTITION.device_id, "session:1"),
        source_version="1.0.0", host_os="windows", clock=lambda: state.now, **kw)
    return state


def test_composition_uses_accepted_codec_and_is_immutable():
    value = compose_outcome(result())
    assert decode_outcome(encode_outcome(value)) == value
    assert value.execution_ref == "job:1"
    assert value.evidence_refs == result().evidence_refs
    with pytest.raises(FrozenInstanceError):
        value.decision = "NO_ACTION"


def test_guard_mapping_does_not_mint_execution_ids():
    value = compose_outcome(GuardResult(False, "AUTHORITY_DENIED", {}), signal=signal())
    assert value.decision == "DENIED" and value.reason_code == "AUTHORITY_DENIED"
    assert value.execution_ref is None and value.evidence_refs == ()


@pytest.mark.parametrize("field,value", [
    ("execution_ids", ("one", "two")), ("submission_ids", ("submission:1",)),
    ("kind", "invalid"), ("signal_id", "x" * 129),
])
def test_composition_never_truncates_or_chooses_ambiguous_identity(field, value):
    with pytest.raises(OutcomePublicationError, match="ORCH_OUTCOME_INVALID"):
        compose_outcome(replace(result(), **{field: value}))


def test_existing_mapping_accepts_before_derived_stm_and_is_closed(observation, monkeypatch):
    order = []
    accept, rebuild = observation.bus.accept, observation.stm.rebuild
    monkeypatch.setattr(observation.bus, "accept", lambda *a: (order.append("bus"), accept(*a))[1])
    monkeypatch.setattr(observation.stm, "rebuild", lambda *a: (order.append("stm"), rebuild(*a))[1])
    published = observation.make().publish(result())
    assert order == ["bus", "stm"]
    assert not published.outcome.observability_degraded
    assert published.guidance == "ORCH_OBSERVATION_AVAILABLE"
    records = observation.stm.read(PARTITION).records
    envelope = records[0][0]
    assert envelope["hook_class"] == "OBSERVE"
    assert envelope["event_type"] == "control.start.after"
    assert not {"command_request", "guard", "payload", "outcome", "prompt"} & envelope.keys()
    assert envelope["evidence_refs"] == ["authority:checkpoint"]
    assert len(published.guidance.encode("utf-8")) <= 512


@pytest.mark.parametrize("event_type", ["START", "STOP", "RESTART", "RELEASE"])
def test_supported_control_mapping_is_not_an_outcome_event(observation, event_type):
    observation.snapshot = replace(observation.snapshot,
        events=(replace(observation.snapshot.events[0], event_type=event_type),))
    published = observation.make().publish(result())
    assert not published.outcome.observability_degraded
    assert observation.stm.read(PARTITION).records[0][0]["event_type"] == "control." + event_type.lower() + ".after"


@pytest.mark.parametrize("events", [(), (ControlEvent("event-" + "2" * 32,
    "ORCH_OUTCOME", "worker-review", PARTITION.project_ref, "2026-11-01T00:00:00Z"),)])
def test_missing_or_unsupported_mapping_publishes_nothing(observation, events):
    observation.snapshot = replace(observation.snapshot, events=events)
    published = observation.make().publish(result())
    assert published.outcome.observability_degraded
    assert published.guidance == "ORCH_OBSERVATION_UNAVAILABLE"
    assert observation.bus.queued_count == 0
    assert observation.stm.read(PARTITION).records == ()


@pytest.mark.parametrize("initial", ["missing", "stale", "overflow"])
def test_missing_stale_overflow_stm_rebuilds_only_from_fresh_authority(observation, initial):
    if initial != "missing":
        observation.stm.rebuild(PARTITION, (({"summary": "old cache, not authority"}, 1),), ())
    if initial == "stale":
        observation.tick = 301
    if initial == "overflow":
        observation.stm._rebuild_item_limit = 1
        with pytest.raises(StmError):
            observation.stm.rebuild(PARTITION, (({}, 1), ({}, 1)), ())
        observation.stm._rebuild_item_limit = 2048
    publisher = observation.make()
    published = publisher.publish(result())
    assert not published.outcome.observability_degraded
    observation.reader.assert_called_once_with(PARTITION, result())
    assert observation.stm.read(PARTITION).state == "FRESH"
    assert "old cache" not in str(observation.stm.read(PARTITION).records)
    publisher.publish(result())
    assert observation.reader.call_count == 2  # A fresh cache is never authority either.


@pytest.mark.parametrize("failure", ["bus", "stm"])
def test_overflow_is_typed_unavailable_with_authority_reference_rebuild(observation, failure):
    if failure == "bus":
        observation.bus = HookBus(clock=lambda: observation.tick, max_events=0)
    else:
        observation.stm = HookStm(clock=lambda: observation.tick, records_per_partition=1)
    published = observation.make().publish(result())
    assert published.outcome.observability_degraded
    assert published.guidance == "ORCH_OBSERVATION_UNAVAILABLE"
    assert published.reason_code == "ORCH_OBSERVATION_UNAVAILABLE"
    assert observation.stm.read(PARTITION).state == "FRESH"
    assert observation.stm.read(PARTITION).records == ()
    assert observation.stm.record_count == 1


def test_latched_bus_degradation_rebuilds_reference_without_trusting_old_cache(observation):
    publisher = observation.make()
    assert not publisher.publish(result()).outcome.observability_degraded
    # Backpressure is a sticky bus health fact, even after its owner drains.
    observation.bus._limits = (*observation.bus._limits[:4], 0, *observation.bus._limits[5:])
    observation.snapshot = replace(observation.snapshot, events=(replace(
        observation.snapshot.events[0], event_id="event-" + "3" * 32),))
    publisher.publish(result())
    observation.bus.drain()
    observation.bus._limits = (*observation.bus._limits[:4], 4096, *observation.bus._limits[5:])
    observation.stm.rebuild(PARTITION, (({"summary": "old projection"}, 1),), ())
    assert publisher.publish(result()).outcome.observability_degraded
    assert observation.stm.read(PARTITION).records == ()
    assert observation.stm.record_count == 1


@pytest.mark.parametrize("age", [31, -1])
def test_ttl_expiry_or_future_authority_cannot_refresh_stm(observation, age):
    observation.snapshot = replace(observation.snapshot, observed_at=NOW - timedelta(seconds=age))
    published = observation.make().publish(result())
    assert published.outcome.observability_degraded
    assert observation.stm.read(PARTITION).state == "UNKNOWN"
    assert observation.bus.queued_count == 0


def test_reader_time_is_checked_after_read_not_before(observation):
    def slow(*_):
        observation.now += timedelta(seconds=31)
        return observation.snapshot
    observation.reader.side_effect = slow
    assert observation.make().publish(result()).outcome.observability_degraded
    assert observation.bus.queued_count == 0


@pytest.mark.parametrize("mismatch", ["partition", "execution", "project", "worker", "count", "duplicate"])
def test_authority_binding_and_bounds_before_bus(observation, mismatch):
    snap = observation.snapshot
    if mismatch == "partition":
        snap = replace(snap, partition=replace(PARTITION, task_id="foreign"))
    elif mismatch == "execution":
        snap = replace(snap, execution_ids=("foreign",))
    elif mismatch == "project":
        snap = replace(snap, events=(replace(snap.events[0], project_id="foreign"),))
    elif mismatch == "worker":
        snap = replace(snap, events=(replace(snap.events[0], worker_id="foreign"),))
    elif mismatch == "count":
        snap = replace(snap, events=snap.events * 17)
    else:
        snap = replace(snap, events=snap.events * 2)
    observation.snapshot = snap
    assert observation.make().publish(result()).outcome.observability_degraded
    assert observation.bus.queued_count == 0
    assert observation.stm.read(PARTITION).state == "UNKNOWN"


def test_sensitive_authority_pointer_never_enters_bus_or_stm(observation):
    observation.snapshot = replace(observation.snapshot,
        authority_ref="ghp_FAKE0000000000000000000000000000000")
    assert observation.make().publish(result()).outcome.observability_degraded
    assert observation.bus.queued_count == 0
    assert observation.stm.record_count == 0


def test_raw_error_not_exposed_and_reentrancy_is_typed(observation):
    publisher = observation.make()
    nested = []
    def read(*_):
        with pytest.raises(OutcomePublicationError, match="ORCH_PUBLISH_REENTRANT_REFUSED") as exc:
            publisher.publish(result())
        nested.append(exc.value.code)
        raise RuntimeError("private provider prompt or credential")
    observation.reader.side_effect = read
    published = publisher.publish(result())
    assert nested == ["ORCH_PUBLISH_REENTRANT_REFUSED"]
    assert published.outcome == replace(compose_outcome(result()), observability_degraded=True)
    assert "private" not in str(published)


@pytest.mark.parametrize("when", ["before", "after"])
def test_registered_root_audit_failure_before_after_effect_retains_ids(lane, observation, when):
    lane.after_audit = when == "after"
    if when == "before":
        lane.jobs.checkpoint = Mock(side_effect=RuntimeError("private audit failure"))
    root = lane.make_root(outcome_publisher=observation.make())
    value = root.handle(signal(), admitted=CONTEXT)
    assert value.decision == "RECONCILIATION_REQUIRED"
    assert value.execution_ids == (lane.task.dispatch_request.key.job_id,)
    assert lane.calls == (1 if when == "after" else 0)
    if when == "after":
        root.handle(signal(), admitted=CONTEXT)
        assert lane.calls == 1


def test_registered_publisher_failure_degrades_only_never_relaunches(lane, observation):
    observation.reader.side_effect = RuntimeError("private failure")
    root = lane.make_root(outcome_publisher=observation.make())
    value = root.handle(signal(), admitted=CONTEXT)
    assert value.decision == "DISPATCH_OBSERVED"
    assert value.reason_code == "ORCH_DISPATCH_OBSERVED"
    assert value.observability_degraded
    root.handle(signal(), admitted=CONTEXT)
    assert lane.calls == 1


def test_runtime_composition_has_no_ambient_read_and_rejects_two_publishers(lane, observation):
    publisher = observation.make()
    root = lane.make_root(outcome_publisher=publisher)
    assert callable(root.handle)
    observation.reader.assert_not_called()
    assert lane.calls == 0
    with pytest.raises(ValueError, match="ORCH_PUBLISHER_AMBIGUOUS"):
        lane.make_root(outcome_publisher=publisher, publisher=lambda _: None)


def test_observation_callback_cannot_recursively_dispatch(lane, observation):
    nested = []
    def read(*_):
        nested.append(root.handle(signal(), admitted=CONTEXT))
        raise RuntimeError("observation unavailable")
    observation.reader.side_effect = read
    root = lane.make_root(outcome_publisher=observation.make())
    value = root.handle(signal(), admitted=CONTEXT)
    assert value.decision == "DISPATCH_OBSERVED"
    assert nested[0].reason_code == "ORCH_REENTRANT_DENIED"
    assert lane.calls == 1


def test_registered_root_reads_canonical_checkpoint_and_existing_control_event(lane, observation):
    from a_conductor.control_events import SQLiteControlEventLog
    log = SQLiteControlEventLog(lane.jobs.database_path)
    event = log.append("START", "worker-review", PARTITION.project_ref)
    log.append = Mock(side_effect=AssertionError("publisher must not manufacture an event"))
    observation.now = datetime.now(timezone.utc)

    def read(partition, current):
        job_id, = current.execution_ids
        job = lane.jobs.get_job(job_id)
        assert job.project_id == partition.project_ref
        assert current.task_ref == partition.task_id
        checkpoints = lane.jobs.list_events(job_id)
        checkpoint = next(e for e in checkpoints if e.checkpoint_ref == "orch-worker-post:" + job_id)
        return ObservationSnapshot(partition, checkpoint.event_id, (job_id,),
            observation.now, (log.get(event.event_id),))

    observation.reader.side_effect = read
    value = lane.make_root(outcome_publisher=observation.make()).handle(signal(), admitted=CONTEXT)
    assert value.decision == "DISPATCH_OBSERVED" and not value.observability_degraded
    records = observation.stm.read(PARTITION).records
    assert records[0][0]["event_id"] == "hk-" + event.event_id.removeprefix("event-")
    assert records[0][0]["evidence_refs"][0].startswith("job-event-")
    assert log.list_recent() == (event,)
    log.append.assert_not_called()
    assert lane.calls == 1


def test_stop_receipt_schema_and_context_budgets_unchanged():
    import runpy
    from pathlib import Path
    hook = runpy.run_path(str(Path(__file__).resolve().parents[1] / ".codex/hooks/a_sunday_lifecycle.py"))
    assert hook["_MAX_STDIN_BYTES"] == 262144
    assert hook["_MAX_RECEIPT_BYTES"] == 65536
    assert hook["_REQUIRED_RECEIPT_FIELDS"] == {
        "schema_version", "receipt_type", "run_id", "thread_id", "parent_exec_ref",
        "model", "effort", "contract_ref", "receipt_ref", "authority_repo_ref",
        "worktree_ref", "capability_evidence_version", "generation", "generated_at",
        "status", "reason", "stop_gate", "outstanding_exec_refs", "next_safe_action_ref",
    }
    assert hook["_ACTIONABLE_CONTINUE_REASONS"] == {"NEXT_READY", "CHILD_RESULT_READY", "TURN_BUDGET_BOUNDARY"}
    for key in ("_BASE_CONTEXT", "_DISPATCH_CONTEXT", "_POST_EXEC_CONTEXT"):
        assert len(hook[key].encode("utf-8")) <= 4096
