"""Append-only SQLite journal for lifecycle transaction checkpoints.

The journal is a concrete durable checkpoint sink for ``LifecycleExecutor``.
It is intentionally narrower than the future task broker and can coexist in
the same SQLite database as the Phase 1 Project/A-Worker registry tables.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .lifecycle import LifecycleAction, LifecycleStep
from .lifecycle_executor import LifecycleCheckpoint


JOURNAL_SCHEMA_VERSION = "1"


class LifecycleJournalError(RuntimeError):
    pass


class LifecycleCheckpointConflictError(LifecycleJournalError):
    pass


class LifecycleSequenceError(LifecycleJournalError):
    pass


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value


def _validate_checkpoint(checkpoint: LifecycleCheckpoint) -> None:
    _require_text(checkpoint.transaction_id, "transaction_id")
    if (
        not isinstance(checkpoint.sequence_no, int)
        or isinstance(checkpoint.sequence_no, bool)
        or checkpoint.sequence_no < 1
    ):
        raise ValueError("sequence_no must be >= 1")
    if not isinstance(checkpoint.action, LifecycleAction):
        raise ValueError("action must be a LifecycleAction")
    if not isinstance(checkpoint.step, LifecycleStep):
        raise ValueError("step must be a LifecycleStep")
    if checkpoint.evidence_ref is not None:
        _require_text(checkpoint.evidence_ref, "evidence_ref")


class SQLiteLifecycleJournal:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.database_path)
        except (OSError, sqlite3.Error) as exc:
            raise LifecycleJournalError("unable to open lifecycle journal database") from exc

        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 5000")
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connect() as connection:
            try:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS lifecycle_journal_meta (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS lifecycle_checkpoints (
                        transaction_id TEXT NOT NULL CHECK (trim(transaction_id) <> ''),
                        sequence_no INTEGER NOT NULL CHECK (sequence_no >= 1),
                        action TEXT NOT NULL,
                        step TEXT NOT NULL,
                        evidence_ref TEXT,
                        recorded_at TEXT NOT NULL DEFAULT (
                            strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                        ),
                        PRIMARY KEY (transaction_id, sequence_no)
                    );
                    """
                )
                row = connection.execute(
                    "SELECT value FROM lifecycle_journal_meta "
                    "WHERE key = 'schema_version'"
                ).fetchone()
                if row is None:
                    connection.execute(
                        "INSERT INTO lifecycle_journal_meta(key, value) "
                        "VALUES('schema_version', ?)",
                        (JOURNAL_SCHEMA_VERSION,),
                    )
                elif row["value"] != JOURNAL_SCHEMA_VERSION:
                    raise LifecycleJournalError(
                        f"unsupported schema_version: {row['value']}"
                    )
                connection.commit()
            except LifecycleJournalError:
                connection.rollback()
                raise
            except sqlite3.Error as exc:
                connection.rollback()
                raise LifecycleJournalError(
                    "unable to initialize lifecycle journal"
                ) from exc

    def record(self, checkpoint: LifecycleCheckpoint) -> None:
        _validate_checkpoint(checkpoint)
        self.initialize()

        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    "SELECT action, step, evidence_ref "
                    "FROM lifecycle_checkpoints "
                    "WHERE transaction_id = ? AND sequence_no = ?",
                    (checkpoint.transaction_id, checkpoint.sequence_no),
                ).fetchone()

                expected_payload = (
                    checkpoint.action.value,
                    checkpoint.step.value,
                    checkpoint.evidence_ref,
                )
                if existing is not None:
                    persisted_payload = (
                        existing["action"],
                        existing["step"],
                        existing["evidence_ref"],
                    )
                    if persisted_payload == expected_payload:
                        connection.commit()
                        return
                    raise LifecycleCheckpointConflictError(
                        "checkpoint conflict for "
                        f"transaction_id={checkpoint.transaction_id!r}, "
                        f"sequence_no={checkpoint.sequence_no}"
                    )

                row = connection.execute(
                    "SELECT MAX(sequence_no) AS max_sequence "
                    "FROM lifecycle_checkpoints WHERE transaction_id = ?",
                    (checkpoint.transaction_id,),
                ).fetchone()
                max_sequence = row["max_sequence"] if row is not None else None
                expected_sequence = 1 if max_sequence is None else int(max_sequence) + 1
                if checkpoint.sequence_no != expected_sequence:
                    raise LifecycleSequenceError(
                        f"expected sequence_no={expected_sequence} for "
                        f"transaction_id={checkpoint.transaction_id!r}; "
                        f"received {checkpoint.sequence_no}"
                    )

                connection.execute(
                    "INSERT INTO lifecycle_checkpoints(" 
                    "transaction_id, sequence_no, action, step, evidence_ref" 
                    ") VALUES(?, ?, ?, ?, ?)",
                    (
                        checkpoint.transaction_id,
                        checkpoint.sequence_no,
                        checkpoint.action.value,
                        checkpoint.step.value,
                        checkpoint.evidence_ref,
                    ),
                )
                connection.commit()
            except (LifecycleCheckpointConflictError, LifecycleSequenceError):
                connection.rollback()
                raise
            except sqlite3.Error as exc:
                connection.rollback()
                raise LifecycleJournalError(
                    "unable to record lifecycle checkpoint"
                ) from exc

    def load(self, transaction_id: str) -> tuple[LifecycleCheckpoint, ...]:
        _require_text(transaction_id, "transaction_id")
        self.initialize()

        with self._connect() as connection:
            try:
                rows = connection.execute(
                    "SELECT transaction_id, sequence_no, action, step, evidence_ref "
                    "FROM lifecycle_checkpoints WHERE transaction_id = ? "
                    "ORDER BY sequence_no",
                    (transaction_id,),
                ).fetchall()
            except sqlite3.Error as exc:
                raise LifecycleJournalError(
                    "unable to load lifecycle checkpoints"
                ) from exc

        checkpoints: list[LifecycleCheckpoint] = []
        expected_sequence = 1
        try:
            for row in rows:
                sequence_no = row["sequence_no"]
                if sequence_no != expected_sequence:
                    raise LifecycleJournalError(
                        "invalid persisted checkpoint sequence"
                    )
                checkpoints.append(
                    LifecycleCheckpoint(
                        transaction_id=row["transaction_id"],
                        sequence_no=sequence_no,
                        action=LifecycleAction(row["action"]),
                        step=LifecycleStep(row["step"]),
                        evidence_ref=row["evidence_ref"],
                    )
                )
                expected_sequence += 1
        except (TypeError, ValueError) as exc:
            raise LifecycleJournalError("invalid persisted checkpoint") from exc

        return tuple(checkpoints)
