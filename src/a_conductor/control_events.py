"""Append-only, payload-free lifecycle/control event references."""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator


class ControlEventLogError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class ControlEvent:
    event_id: str
    event_type: str
    worker_id: str
    project_id: str


def _require_text(value: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or "\x00" in value
        or "\r" in value
        or "\n" in value
    ):
        raise ControlEventLogError("EVENT_INVALID")
    return value.strip()


def _default_event_id() -> str:
    return f"event-{uuid.uuid4().hex}"


class SQLiteControlEventLog:
    def __init__(
        self,
        database_path: str | Path,
        *,
        event_id_factory: Callable[[], str] = _default_event_id,
    ) -> None:
        self.database_path = Path(database_path)
        self._event_id_factory = event_id_factory

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.database_path)
        except (OSError, sqlite3.Error) as exc:
            raise ControlEventLogError("EVENT_STORE_UNAVAILABLE") from exc
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout = 5000")
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS control_events (
                        event_id TEXT PRIMARY KEY,
                        event_type TEXT NOT NULL,
                        worker_id TEXT NOT NULL,
                        project_id TEXT NOT NULL,
                        recorded_at TEXT NOT NULL
                    )
                    """
                )
                connection.commit()
            except sqlite3.Error as exc:
                connection.rollback()
                raise ControlEventLogError("EVENT_STORE_INITIALIZE_FAILED") from exc

    def append(self, event_type: str, worker_id: str, project_id: str) -> ControlEvent:
        event_type = _require_text(event_type)
        worker_id = _require_text(worker_id)
        project_id = _require_text(project_id)
        try:
            event_id = _require_text(self._event_id_factory())
        except ControlEventLogError:
            raise
        except Exception as exc:
            raise ControlEventLogError("EVENT_ID_INVALID") from exc
        recorded_at = datetime.now(timezone.utc).isoformat()
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute(
                    "INSERT INTO control_events(event_id, event_type, worker_id, project_id, recorded_at) VALUES(?, ?, ?, ?, ?)",
                    (event_id, event_type, worker_id, project_id, recorded_at),
                )
                connection.commit()
            except sqlite3.IntegrityError as exc:
                connection.rollback()
                raise ControlEventLogError("EVENT_ID_CONFLICT") from exc
            except sqlite3.Error as exc:
                connection.rollback()
                raise ControlEventLogError("EVENT_STORE_WRITE_FAILED") from exc
        return ControlEvent(event_id, event_type, worker_id, project_id)

    @staticmethod
    def _from_row(row: sqlite3.Row) -> ControlEvent:
        return ControlEvent(
            event_id=row["event_id"],
            event_type=row["event_type"],
            worker_id=row["worker_id"],
            project_id=row["project_id"],
        )

    def get(self, event_id: str) -> ControlEvent | None:
        event_id = _require_text(event_id)
        self.initialize()
        with self._connect() as connection:
            try:
                row = connection.execute(
                    "SELECT event_id, event_type, worker_id, project_id FROM control_events WHERE event_id = ?",
                    (event_id,),
                ).fetchone()
            except sqlite3.Error as exc:
                raise ControlEventLogError("EVENT_STORE_READ_FAILED") from exc
        return None if row is None else self._from_row(row)

    def list_recent(self, *, limit: int = 100) -> tuple[ControlEvent, ...]:
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1 or limit > 1000:
            raise ControlEventLogError("EVENT_LIMIT_INVALID")
        self.initialize()
        with self._connect() as connection:
            try:
                rows = connection.execute(
                    "SELECT event_id, event_type, worker_id, project_id FROM control_events ORDER BY recorded_at DESC, rowid DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            except sqlite3.Error as exc:
                raise ControlEventLogError("EVENT_STORE_READ_FAILED") from exc
        return tuple(self._from_row(row) for row in rows)
