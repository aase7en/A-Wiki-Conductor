"""SQLite persistence for the Phase 1 Project/A-Worker registry.

This is deliberately narrower than the future durable task broker. It stores
only registry metadata, worker state, and assignment records and reconstructs
state through ``ControlPlaneRegistry`` validation on load.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .domain import Assignment, Project, Worker, WorkerState
from .registry import ControlPlaneRegistry, RegistryError, RegistrySnapshot


SCHEMA_VERSION = "1"


class PersistenceError(RuntimeError):
    pass


class SQLiteRegistryStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.database_path)
        except (OSError, sqlite3.Error) as exc:
            raise PersistenceError("unable to open registry database") from exc

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
                    CREATE TABLE IF NOT EXISTS metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS projects (
                        project_id TEXT PRIMARY KEY,
                        display_name TEXT NOT NULL,
                        root_path TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS workers (
                        worker_id TEXT PRIMARY KEY,
                        display_name TEXT NOT NULL,
                        runtime_id TEXT,
                        assignment_id TEXT,
                        state TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS assignments (
                        assignment_id TEXT PRIMARY KEY,
                        worker_id TEXT NOT NULL,
                        project_id TEXT NOT NULL,
                        runtime_id TEXT,
                        mutation_allowed INTEGER NOT NULL CHECK (mutation_allowed IN (0, 1)),
                        worktree_key TEXT NOT NULL,
                        FOREIGN KEY (worker_id) REFERENCES workers(worker_id),
                        FOREIGN KEY (project_id) REFERENCES projects(project_id)
                    );
                    """
                )
                row = connection.execute(
                    "SELECT value FROM metadata WHERE key = 'schema_version'"
                ).fetchone()
                if row is None:
                    connection.execute(
                        "INSERT INTO metadata(key, value) VALUES('schema_version', ?)",
                        (SCHEMA_VERSION,),
                    )
                elif row["value"] != SCHEMA_VERSION:
                    raise PersistenceError(
                        f"unsupported schema_version: {row['value']}"
                    )
                connection.commit()
            except PersistenceError:
                connection.rollback()
                raise
            except sqlite3.Error as exc:
                connection.rollback()
                raise PersistenceError("unable to initialize registry database") from exc

    def save(self, snapshot: RegistrySnapshot) -> None:
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute("DELETE FROM assignments")
                connection.execute("DELETE FROM workers")
                connection.execute("DELETE FROM projects")

                connection.executemany(
                    "INSERT INTO projects(project_id, display_name, root_path) "
                    "VALUES(?, ?, ?)",
                    [
                        (item.project_id, item.display_name, item.root_path)
                        for item in snapshot.projects
                    ],
                )
                connection.executemany(
                    "INSERT INTO workers(worker_id, display_name, runtime_id, assignment_id, state) "
                    "VALUES(?, ?, ?, ?, ?)",
                    [
                        (
                            item.worker_id,
                            item.display_name,
                            item.runtime_id,
                            item.assignment_id,
                            item.state.value,
                        )
                        for item in snapshot.workers
                    ],
                )
                connection.executemany(
                    "INSERT INTO assignments(assignment_id, worker_id, project_id, runtime_id, mutation_allowed, worktree_key) "
                    "VALUES(?, ?, ?, ?, ?, ?)",
                    [
                        (
                            record.assignment.assignment_id,
                            record.assignment.worker_id,
                            record.assignment.project_id,
                            record.assignment.runtime_id,
                            int(record.mutation_allowed),
                            record.worktree_key,
                        )
                        for record in snapshot.assignments
                    ],
                )
                connection.commit()
            except (sqlite3.Error, ValueError, TypeError) as exc:
                connection.rollback()
                raise PersistenceError("unable to save registry snapshot") from exc

    def load(self) -> ControlPlaneRegistry:
        self.initialize()
        with self._connect() as connection:
            try:
                projects = connection.execute(
                    "SELECT project_id, display_name, root_path FROM projects ORDER BY project_id"
                ).fetchall()
                workers = connection.execute(
                    "SELECT worker_id, display_name, runtime_id, assignment_id, state "
                    "FROM workers ORDER BY worker_id"
                ).fetchall()
                assignments = connection.execute(
                    "SELECT assignment_id, worker_id, project_id, runtime_id, "
                    "mutation_allowed, worktree_key FROM assignments ORDER BY assignment_id"
                ).fetchall()
            except sqlite3.Error as exc:
                raise PersistenceError("unable to read registry database") from exc

        registry = ControlPlaneRegistry()
        expected_assignment_refs: dict[str, str | None] = {}

        try:
            for row in projects:
                registry.register_project(
                    Project(
                        project_id=row["project_id"],
                        display_name=row["display_name"],
                        root_path=row["root_path"],
                    )
                )

            for row in workers:
                try:
                    state = WorkerState(row["state"])
                except (TypeError, ValueError) as exc:
                    raise PersistenceError(
                        f"invalid worker state for {row['worker_id']}: {row['state']}"
                    ) from exc
                expected_assignment_refs[row["worker_id"]] = row["assignment_id"]
                registry.register_worker(
                    Worker(
                        worker_id=row["worker_id"],
                        display_name=row["display_name"],
                        runtime_id=row["runtime_id"],
                        assignment_id=None,
                        state=state,
                    )
                )

            for row in assignments:
                mutation_raw = row["mutation_allowed"]
                if mutation_raw not in (0, 1):
                    raise PersistenceError(
                        f"invalid mutation_allowed for {row['assignment_id']}"
                    )
                assignment = Assignment(
                    assignment_id=row["assignment_id"],
                    worker_id=row["worker_id"],
                    project_id=row["project_id"],
                    runtime_id=row["runtime_id"],
                )
                registry.assign(
                    assignment,
                    mutation_allowed=bool(mutation_raw),
                )

            for worker_id, expected_assignment_id in expected_assignment_refs.items():
                actual_assignment_id = registry.get_worker(worker_id).assignment_id
                if actual_assignment_id != expected_assignment_id:
                    raise PersistenceError(
                        "assignment reference mismatch for "
                        f"worker_id={worker_id}: expected={expected_assignment_id!r}, "
                        f"actual={actual_assignment_id!r}"
                    )
        except PersistenceError:
            raise
        except (RegistryError, ValueError, TypeError) as exc:
            raise PersistenceError("invalid persisted registry data") from exc

        return registry
