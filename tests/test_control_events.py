from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from a_conductor.control_events import (
    ControlEvent,
    ControlEventLogError,
    SQLiteControlEventLog,
)


def test_append_returns_opaque_event_and_round_trips(tmp_path: Path) -> None:
    log = SQLiteControlEventLog(
        tmp_path / "control.sqlite",
        event_id_factory=lambda: "event-001",
    )

    event = log.append("START", "a-worker-01", "project-1")

    assert event == ControlEvent(
        event_id="event-001",
        event_type="START",
        worker_id="a-worker-01",
        project_id="project-1",
    )
    assert log.get("event-001") == event
    assert log.list_recent(limit=10) == (event,)


def test_event_ids_are_append_only_and_conflict_fails(tmp_path: Path) -> None:
    log = SQLiteControlEventLog(
        tmp_path / "control.sqlite",
        event_id_factory=lambda: "same-id",
    )
    log.append("START", "a-worker-01", "project-1")
    with pytest.raises(ControlEventLogError) as exc_info:
        log.append("STOP", "a-worker-01", "project-1")
    assert exc_info.value.code == "EVENT_ID_CONFLICT"


def test_invalid_text_is_rejected_before_database_write(tmp_path: Path) -> None:
    log = SQLiteControlEventLog(tmp_path / "control.sqlite")
    with pytest.raises(ControlEventLogError) as exc_info:
        log.append("", "a-worker-01", "project-1")
    assert exc_info.value.code == "EVENT_INVALID"


def test_schema_has_no_payload_secret_or_command_columns(tmp_path: Path) -> None:
    log = SQLiteControlEventLog(tmp_path / "control.sqlite")
    log.initialize()
    with sqlite3.connect(log.database_path) as connection:
        columns = [
            row[1]
            for row in connection.execute("PRAGMA table_info(control_events)")
        ]
    assert columns == [
        "event_id",
        "event_type",
        "worker_id",
        "project_id",
        "recorded_at",
    ]
    assert all(
        forbidden not in columns
        for forbidden in ("payload", "secret", "token", "command", "stderr", "stdout")
    )
