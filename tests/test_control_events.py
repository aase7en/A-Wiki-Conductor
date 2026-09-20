from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pytest

from a_conductor.control_events import (
    ControlEvent,
    ControlEventLogError,
    SQLiteControlEventLog,
)
from a_conductor.control_hook_adapter import (
    ControlHookContext,
    normalize_control_event,
)

_CANONICAL_UTC_Z = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,9})?Z"
)


def test_append_returns_opaque_event_and_round_trips(tmp_path: Path) -> None:
    log = SQLiteControlEventLog(
        tmp_path / "control.sqlite",
        event_id_factory=lambda: "event-001",
    )

    event = log.append("START", "a-worker-01", "project-1")

    persisted = _persisted_recorded_at(log.database_path, "event-001")
    assert event == ControlEvent(
        event_id="event-001",
        event_type="START",
        worker_id="a-worker-01",
        project_id="project-1",
        recorded_at=persisted,
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


def _persisted_recorded_at(database_path: Path, event_id: str) -> str:
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT recorded_at FROM control_events WHERE event_id = ?",
            (event_id,),
        ).fetchone()
    assert row is not None
    return row[0]


def test_append_exposes_exact_persisted_recorded_at(tmp_path: Path) -> None:
    log = SQLiteControlEventLog(
        tmp_path / "control.sqlite",
        event_id_factory=lambda: "event-001",
    )

    event = log.append("START", "a-worker-01", "project-1")

    assert event.recorded_at is not None
    assert event.recorded_at == _persisted_recorded_at(log.database_path, "event-001")


def test_get_and_list_preserve_exact_persisted_recorded_at(tmp_path: Path) -> None:
    log = SQLiteControlEventLog(
        tmp_path / "control.sqlite",
        event_id_factory=lambda: "event-001",
    )

    appended = log.append("START", "a-worker-01", "project-1")
    persisted = _persisted_recorded_at(log.database_path, "event-001")

    fetched = log.get("event-001")
    listed = log.list_recent(limit=10)

    assert fetched is not None
    assert fetched.recorded_at == persisted
    assert [item.recorded_at for item in listed] == [persisted]
    assert appended.recorded_at == fetched.recorded_at == listed[0].recorded_at
    for value in (appended.recorded_at, fetched.recorded_at, listed[0].recorded_at):
        assert value.encode("utf-8") == persisted.encode("utf-8")


def test_direct_four_positional_construction_keeps_recorded_at_none() -> None:
    event = ControlEvent("event-001", "START", "a-worker-01", "project-1")

    assert event.recorded_at is None


def test_schema_has_no_payload_secret_or_command_columns(tmp_path: Path) -> None:
    log = SQLiteControlEventLog(tmp_path / "control.sqlite")
    log.initialize()
    with sqlite3.connect(log.database_path) as connection:
        info = {
            row[1]: row
            for row in connection.execute("PRAGMA table_info(control_events)")
        }
    columns = list(info)
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
    assert info["recorded_at"][2] == "TEXT"
    assert info["recorded_at"][3] == 1


def test_new_appended_recorded_at_is_canonical_utc_z(tmp_path: Path) -> None:
    log = SQLiteControlEventLog(
        tmp_path / "control.sqlite",
        event_id_factory=lambda: "event-001",
    )

    event = log.append("START", "a-worker-01", "project-1")

    persisted = _persisted_recorded_at(log.database_path, "event-001")
    assert persisted == event.recorded_at
    assert persisted.endswith("Z")
    assert not persisted.endswith("+00:00")
    assert _CANONICAL_UTC_Z.fullmatch(persisted) is not None


def test_new_append_get_and_list_expose_identical_persisted_z_bytes(
    tmp_path: Path,
) -> None:
    log = SQLiteControlEventLog(
        tmp_path / "control.sqlite",
        event_id_factory=lambda: "event-001",
    )

    appended = log.append("START", "a-worker-01", "project-1")
    persisted = _persisted_recorded_at(log.database_path, "event-001")
    fetched = log.get("event-001")
    listed = log.list_recent(limit=10)

    assert fetched is not None
    assert appended.recorded_at is not None
    assert (
        appended.recorded_at
        == fetched.recorded_at
        == listed[0].recorded_at
        == persisted
    )
    for value in (appended.recorded_at, fetched.recorded_at, listed[0].recorded_at):
        assert value.encode("utf-8") == persisted.encode("utf-8")
    assert _CANONICAL_UTC_Z.fullmatch(persisted) is not None


def test_legacy_plus_utc_offset_row_remains_readable_byte_for_byte(
    tmp_path: Path,
) -> None:
    legacy = "2026-09-20T01:02:03.000004+00:00"
    log = SQLiteControlEventLog(
        tmp_path / "control.sqlite",
        event_id_factory=lambda: "event-001",
    )
    log.initialize()
    with sqlite3.connect(log.database_path) as connection:
        connection.execute(
            "INSERT INTO control_events("
            "event_id, event_type, worker_id, project_id, recorded_at"
            ") VALUES(?, ?, ?, ?, ?)",
            ("legacy-000", "START", "a-worker-01", "project-1", legacy),
        )
        connection.commit()

    fetched = log.get("legacy-000")
    listed = log.list_recent(limit=10)

    assert fetched is not None
    assert fetched.recorded_at == legacy
    assert fetched.recorded_at.encode("utf-8") == legacy.encode("utf-8")
    assert [item.recorded_at for item in listed] == [legacy]


def test_persisted_z_timestamp_is_accepted_by_existing_hook_normalizer(
    tmp_path: Path,
) -> None:
    log = SQLiteControlEventLog(
        tmp_path / "control.sqlite",
        event_id_factory=lambda: "event-0123456789abcdef0123456789abcdef",
    )

    event = log.append("START", "a-worker-01", "project-1")

    envelope = normalize_control_event(
        event,
        ControlHookContext(
            occurred_at=event.recorded_at,
            source_version="1.0.0",
            device_id="device-01",
            host_os="windows",
        ),
    )
    assert envelope["occurred_at"] == event.recorded_at
