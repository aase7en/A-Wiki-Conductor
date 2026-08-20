from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from a_conductor.domain import RecoveryClassification, TaskState
from a_conductor.job_state import JobStateError
from a_conductor.job_store import (
    JobEventType,
    JobStoreError,
    SQLiteJobStore,
)


class EventIds:
    def __init__(self) -> None:
        self.value = 0

    def __call__(self) -> str:
        self.value += 1
        return f"event-{self.value:03d}"


def open_store(tmp_path: Path):
    ids = EventIds()
    store = SQLiteJobStore(tmp_path / "control.sqlite", event_id_factory=ids)
    return store, ids


def create_ready_job(store: SQLiteJobStore, *, max_attempts: int = 3):
    job = store.create_job(
        job_id="job-1",
        work_order_ref="docs/work-orders/WO-1.md",
        project_id="project-1",
        max_attempts=max_attempts,
    )
    return store.transition("job-1", TaskState.READY, expected_version=job.version)


def test_create_job_persists_minimal_runtime_state_and_created_event(tmp_path: Path) -> None:
    store, _ = open_store(tmp_path)

    job = store.create_job(
        job_id="job-1",
        work_order_ref="docs/work-orders/WO-1.md",
        project_id="project-1",
        max_attempts=4,
    )

    assert job.state is TaskState.NEW
    assert job.version == 1
    assert job.attempt_count == 0
    assert store.get_job("job-1") == job
    events = store.list_events("job-1")
    assert len(events) == 1
    assert events[0].event_type is JobEventType.CREATED
    assert events[0].sequence_no == 1
    assert events[0].from_state is None
    assert events[0].to_state is TaskState.NEW
    assert events[0].evidence_ref is None


def test_duplicate_job_id_is_refused(tmp_path: Path) -> None:
    store, _ = open_store(tmp_path)
    store.create_job(job_id="job-1", work_order_ref="wo", project_id="p")

    with pytest.raises(JobStoreError) as exc_info:
        store.create_job(job_id="job-1", work_order_ref="wo-2", project_id="p")
    assert exc_info.value.code == "JOB_ALREADY_EXISTS"


def test_transition_uses_expected_version_and_appends_event_atomically(tmp_path: Path) -> None:
    store, _ = open_store(tmp_path)
    ready = create_ready_job(store)

    claimed = store.transition(
        "job-1",
        TaskState.CLAIMED,
        expected_version=ready.version,
        worker_id="a-worker-01",
        evidence_ref="evidence-claim",
    )

    assert claimed.state is TaskState.CLAIMED
    assert claimed.worker_id == "a-worker-01"
    assert claimed.version == ready.version + 1
    events = store.list_events("job-1")
    assert [event.sequence_no for event in events] == [1, 2, 3]
    assert events[-1].event_type is JobEventType.TRANSITION
    assert events[-1].from_state is TaskState.READY
    assert events[-1].to_state is TaskState.CLAIMED
    assert events[-1].worker_id == "a-worker-01"
    assert events[-1].evidence_ref == "evidence-claim"


def test_stale_writer_gets_version_conflict_without_extra_event(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite"
    first = SQLiteJobStore(database, event_id_factory=EventIds())
    first.create_job(job_id="job-1", work_order_ref="wo", project_id="p")
    stale = first.get_job("job-1")

    second = SQLiteJobStore(database, event_id_factory=lambda: "other-event")
    second.transition("job-1", TaskState.READY, expected_version=stale.version)

    with pytest.raises(JobStoreError) as exc_info:
        first.transition("job-1", TaskState.READY, expected_version=stale.version)
    assert exc_info.value.code == "JOB_VERSION_CONFLICT"
    assert len(first.list_events("job-1")) == 2


def test_transition_policy_is_reused_by_store(tmp_path: Path) -> None:
    store, _ = open_store(tmp_path)
    ready = create_ready_job(store)

    with pytest.raises(JobStateError) as exc_info:
        store.transition("job-1", TaskState.COMPLETE, expected_version=ready.version)
    assert exc_info.value.code == "JOB_TRANSITION_INVALID"
    assert store.get_job("job-1") == ready


def test_entering_executing_persists_attempt_budget(tmp_path: Path) -> None:
    store, _ = open_store(tmp_path)
    ready = create_ready_job(store, max_attempts=1)
    claimed = store.transition(
        "job-1", TaskState.CLAIMED, expected_version=ready.version, worker_id="a-worker-01"
    )
    gating = store.transition("job-1", TaskState.GATING, expected_version=claimed.version)
    executing = store.transition("job-1", TaskState.EXECUTING, expected_version=gating.version)
    assert executing.attempt_count == 1

    verifying = store.transition("job-1", TaskState.VERIFYING, expected_version=executing.version)
    changes = store.transition(
        "job-1", TaskState.CHANGES_REQUIRED, expected_version=verifying.version
    )
    repairing = store.transition("job-1", TaskState.REPAIRING, expected_version=changes.version)
    verifying_again = store.transition(
        "job-1", TaskState.VERIFYING, expected_version=repairing.version
    )
    changes_again = store.transition(
        "job-1", TaskState.CHANGES_REQUIRED, expected_version=verifying_again.version
    )
    repairing_again = store.transition(
        "job-1", TaskState.REPAIRING, expected_version=changes_again.version
    )
    # Repair flow does not create a new EXECUTING attempt by itself.
    assert repairing_again.attempt_count == 1


def test_recovery_classification_round_trips_and_resume_clears_it(tmp_path: Path) -> None:
    store, _ = open_store(tmp_path)
    ready = create_ready_job(store)
    claimed = store.transition(
        "job-1", TaskState.CLAIMED, expected_version=ready.version, worker_id="a-worker-01"
    )
    gating = store.transition("job-1", TaskState.GATING, expected_version=claimed.version)
    recovering = store.transition(
        "job-1",
        TaskState.RECOVERY_NEEDED,
        expected_version=gating.version,
        recovery_classification=RecoveryClassification.PARTIAL_MUTATION,
    )

    reopened = SQLiteJobStore(tmp_path / "control.sqlite")
    loaded = reopened.get_job("job-1")
    assert loaded.recovery_classification is RecoveryClassification.PARTIAL_MUTATION

    resumed = reopened.transition(
        "job-1", TaskState.GATING, expected_version=loaded.version
    )
    assert resumed.recovery_classification is None
    assert resumed.worker_id == "a-worker-01"


def test_checkpoint_is_append_only_versioned_and_metadata_only(tmp_path: Path) -> None:
    store, _ = open_store(tmp_path)
    ready = create_ready_job(store)

    checkpointed = store.checkpoint(
        "job-1",
        checkpoint_ref="checkpoint:tests-green",
        expected_version=ready.version,
        evidence_ref="evidence:test-run-1",
    )

    assert checkpointed.state is TaskState.READY
    assert checkpointed.version == ready.version + 1
    event = store.list_events("job-1")[-1]
    assert event.event_type is JobEventType.CHECKPOINT
    assert event.checkpoint_ref == "checkpoint:tests-green"
    assert event.evidence_ref == "evidence:test-run-1"
    assert event.from_state is TaskState.READY
    assert event.to_state is TaskState.READY


def test_terminal_job_cannot_checkpoint_or_transition(tmp_path: Path) -> None:
    store, _ = open_store(tmp_path)
    ready = create_ready_job(store)
    claimed = store.transition(
        "job-1", TaskState.CLAIMED, expected_version=ready.version, worker_id="a-worker-01"
    )
    gating = store.transition("job-1", TaskState.GATING, expected_version=claimed.version)
    executing = store.transition("job-1", TaskState.EXECUTING, expected_version=gating.version)
    verifying = store.transition("job-1", TaskState.VERIFYING, expected_version=executing.version)
    complete = store.transition("job-1", TaskState.COMPLETE, expected_version=verifying.version)

    with pytest.raises(JobStateError) as exc_info:
        store.transition("job-1", TaskState.READY, expected_version=complete.version)
    assert exc_info.value.code == "JOB_TERMINAL"

    with pytest.raises(JobStateError) as exc_info:
        store.checkpoint("job-1", checkpoint_ref="late", expected_version=complete.version)
    assert exc_info.value.code == "JOB_TERMINAL"


def test_reopen_preserves_jobs_events_and_versions(tmp_path: Path) -> None:
    store, _ = open_store(tmp_path)
    ready = create_ready_job(store)
    checkpointed = store.checkpoint(
        "job-1", checkpoint_ref="cp-1", expected_version=ready.version
    )

    reopened = SQLiteJobStore(tmp_path / "control.sqlite")
    assert reopened.get_job("job-1") == checkpointed
    assert [event.event_type for event in reopened.list_events("job-1")] == [
        JobEventType.CREATED,
        JobEventType.TRANSITION,
        JobEventType.CHECKPOINT,
    ]


def test_missing_job_and_invalid_expected_version_are_code_only(tmp_path: Path) -> None:
    store, _ = open_store(tmp_path)
    with pytest.raises(JobStoreError) as exc_info:
        store.get_job("missing")
    assert exc_info.value.code == "JOB_NOT_FOUND"

    store.create_job(job_id="job-1", work_order_ref="wo", project_id="p")
    with pytest.raises(ValueError):
        store.transition("job-1", TaskState.READY, expected_version=0)


def test_schema_contains_no_prompt_transcript_command_or_output_payload_columns(tmp_path: Path) -> None:
    store, _ = open_store(tmp_path)
    store.initialize()

    connection = sqlite3.connect(tmp_path / "control.sqlite")
    try:
        job_columns = {row[1] for row in connection.execute("PRAGMA table_info(job_records)")}
        event_columns = {row[1] for row in connection.execute("PRAGMA table_info(job_events)")}
    finally:
        connection.close()

    forbidden = {
        "prompt",
        "payload",
        "transcript",
        "command",
        "stdout",
        "stderr",
        "response",
        "message",
        "content",
        "secret",
        "token",
    }
    assert forbidden.isdisjoint(job_columns)
    assert forbidden.isdisjoint(event_columns)
    assert "work_order_ref" in job_columns
    assert "evidence_ref" in event_columns


def test_event_sequence_is_strictly_append_only_per_job(tmp_path: Path) -> None:
    store, _ = open_store(tmp_path)
    ready = create_ready_job(store)
    claimed = store.transition(
        "job-1", TaskState.CLAIMED, expected_version=ready.version, worker_id="a-worker-01"
    )
    checkpointed = store.checkpoint(
        "job-1", checkpoint_ref="cp", expected_version=claimed.version
    )
    store.transition("job-1", TaskState.GATING, expected_version=checkpointed.version)

    events = store.list_events("job-1")
    assert [event.sequence_no for event in events] == list(range(1, len(events) + 1))
    assert len({event.event_id for event in events}) == len(events)
