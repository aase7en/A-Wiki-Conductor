import sqlite3
from pathlib import Path

import pytest

from a_conductor.domain import Project, Worker
from a_conductor.lifecycle import LifecycleAction, LifecycleStep
from a_conductor.lifecycle_executor import LifecycleCheckpoint
from a_conductor.lifecycle_journal import (
    LifecycleCheckpointConflictError,
    LifecycleJournalError,
    LifecycleSequenceError,
    SQLiteLifecycleJournal,
)
from a_conductor.persistence import SQLiteRegistryStore
from a_conductor.registry import ControlPlaneRegistry


def checkpoint(
    transaction_id: str = "txn-001",
    sequence_no: int = 1,
    *,
    action: LifecycleAction = LifecycleAction.START,
    step: LifecycleStep = LifecycleStep.VERIFY_ASSIGNMENT,
    evidence_ref: str | None = "EVID-001",
) -> LifecycleCheckpoint:
    return LifecycleCheckpoint(
        transaction_id=transaction_id,
        sequence_no=sequence_no,
        action=action,
        step=step,
        evidence_ref=evidence_ref,
    )


def test_initialize_creates_parent_and_component_schema_version(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "state" / "conductor.sqlite"
    journal = SQLiteLifecycleJournal(db_path)

    journal.initialize()

    assert db_path.is_file()
    with sqlite3.connect(db_path) as connection:
        version = connection.execute(
            "SELECT value FROM lifecycle_journal_meta WHERE key = 'schema_version'"
        ).fetchone()[0]
    assert version == "1"


def test_record_and_load_round_trip_in_sequence_order(tmp_path: Path) -> None:
    journal = SQLiteLifecycleJournal(tmp_path / "conductor.sqlite")
    first = checkpoint()
    second = checkpoint(
        sequence_no=2,
        step=LifecycleStep.RENDER_PROFILE,
        evidence_ref="EVID-002",
    )

    journal.record(first)
    journal.record(second)

    assert journal.load("txn-001") == (first, second)


def test_exact_duplicate_checkpoint_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "conductor.sqlite"
    journal = SQLiteLifecycleJournal(db_path)
    item = checkpoint()

    journal.record(item)
    journal.record(item)

    assert journal.load("txn-001") == (item,)
    with sqlite3.connect(db_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM lifecycle_checkpoints WHERE transaction_id = ?",
            ("txn-001",),
        ).fetchone()[0]
    assert count == 1


@pytest.mark.parametrize(
    "conflicting",
    [
        checkpoint(step=LifecycleStep.PREFLIGHT),
        checkpoint(action=LifecycleAction.STOP),
        checkpoint(evidence_ref="DIFFERENT-EVIDENCE"),
    ],
)
def test_same_transaction_sequence_with_different_payload_is_rejected(
    tmp_path: Path,
    conflicting: LifecycleCheckpoint,
) -> None:
    journal = SQLiteLifecycleJournal(tmp_path / "conductor.sqlite")
    original = checkpoint()
    journal.record(original)

    with pytest.raises(LifecycleCheckpointConflictError, match="checkpoint conflict"):
        journal.record(conflicting)

    assert journal.load("txn-001") == (original,)


def test_sequence_gap_is_rejected(tmp_path: Path) -> None:
    journal = SQLiteLifecycleJournal(tmp_path / "conductor.sqlite")

    with pytest.raises(LifecycleSequenceError, match="expected sequence_no=1"):
        journal.record(checkpoint(sequence_no=2))

    assert journal.load("txn-001") == ()


def test_sequence_must_continue_contiguously(tmp_path: Path) -> None:
    journal = SQLiteLifecycleJournal(tmp_path / "conductor.sqlite")
    journal.record(checkpoint(sequence_no=1))

    with pytest.raises(LifecycleSequenceError, match="expected sequence_no=2"):
        journal.record(checkpoint(sequence_no=3, step=LifecycleStep.PREFLIGHT))

    assert [item.sequence_no for item in journal.load("txn-001")] == [1]


def test_transactions_have_independent_sequence_spaces(tmp_path: Path) -> None:
    journal = SQLiteLifecycleJournal(tmp_path / "conductor.sqlite")
    a = checkpoint(transaction_id="txn-a", sequence_no=1)
    b = checkpoint(transaction_id="txn-b", sequence_no=1)

    journal.record(a)
    journal.record(b)

    assert journal.load("txn-a") == (a,)
    assert journal.load("txn-b") == (b,)


@pytest.mark.parametrize("transaction_id", ["", " ", "\t"])
def test_blank_transaction_id_is_rejected_before_write(
    tmp_path: Path,
    transaction_id: str,
) -> None:
    journal = SQLiteLifecycleJournal(tmp_path / "conductor.sqlite")

    with pytest.raises(ValueError, match="transaction_id must not be blank"):
        journal.record(checkpoint(transaction_id=transaction_id))


def test_non_positive_sequence_is_rejected_before_write(tmp_path: Path) -> None:
    journal = SQLiteLifecycleJournal(tmp_path / "conductor.sqlite")

    with pytest.raises(ValueError, match="sequence_no must be >= 1"):
        journal.record(checkpoint(sequence_no=0))


def test_blank_evidence_ref_is_rejected_when_present(tmp_path: Path) -> None:
    journal = SQLiteLifecycleJournal(tmp_path / "conductor.sqlite")

    with pytest.raises(ValueError, match="evidence_ref must not be blank"):
        journal.record(checkpoint(evidence_ref=" "))


def test_unsupported_component_schema_version_fails_explicitly(tmp_path: Path) -> None:
    db_path = tmp_path / "conductor.sqlite"
    journal = SQLiteLifecycleJournal(db_path)
    journal.initialize()

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE lifecycle_journal_meta SET value = '999' WHERE key = 'schema_version'"
        )
        connection.commit()

    with pytest.raises(LifecycleJournalError, match="unsupported schema_version"):
        journal.load("txn-001")


def test_corrupt_persisted_action_fails_explicitly(tmp_path: Path) -> None:
    db_path = tmp_path / "conductor.sqlite"
    journal = SQLiteLifecycleJournal(db_path)
    journal.record(checkpoint())

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE lifecycle_checkpoints SET action = 'NOT_AN_ACTION' "
            "WHERE transaction_id = 'txn-001' AND sequence_no = 1"
        )
        connection.commit()

    with pytest.raises(LifecycleJournalError, match="invalid persisted checkpoint"):
        journal.load("txn-001")


def test_corrupt_persisted_step_fails_explicitly(tmp_path: Path) -> None:
    db_path = tmp_path / "conductor.sqlite"
    journal = SQLiteLifecycleJournal(db_path)
    journal.record(checkpoint())

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE lifecycle_checkpoints SET step = 'NOT_A_STEP' "
            "WHERE transaction_id = 'txn-001' AND sequence_no = 1"
        )
        connection.commit()

    with pytest.raises(LifecycleJournalError, match="invalid persisted checkpoint"):
        journal.load("txn-001")


def test_journal_coexists_with_registry_tables_in_same_database(tmp_path: Path) -> None:
    db_path = tmp_path / "conductor.sqlite"
    registry_store = SQLiteRegistryStore(db_path)
    registry = ControlPlaneRegistry()
    registry.register_project(
        Project(project_id="project-a", display_name="Project A", root_path=r"A:\Repo-A")
    )
    registry.register_worker(
        Worker(worker_id="a-worker-01", display_name="A-Worker 1")
    )
    registry_store.save(registry.snapshot())

    journal = SQLiteLifecycleJournal(db_path)
    journal.record(checkpoint())

    loaded_registry = registry_store.load().snapshot()
    assert [item.project_id for item in loaded_registry.projects] == ["project-a"]
    assert [item.worker_id for item in loaded_registry.workers] == ["a-worker-01"]
    assert journal.load("txn-001") == (checkpoint(),)


def test_journal_does_not_create_task_broker_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "conductor.sqlite"
    journal = SQLiteLifecycleJournal(db_path)
    journal.initialize()

    with sqlite3.connect(db_path) as connection:
        names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert "lifecycle_journal_meta" in names
    assert "lifecycle_checkpoints" in names
    assert "tasks" not in names
    assert "leases" not in names
    assert "evidence" not in names
