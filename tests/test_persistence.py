import sqlite3
from pathlib import Path

import pytest

from a_conductor.domain import Assignment, Project, Worker, WorkerState
from a_conductor.persistence import PersistenceError, SQLiteRegistryStore
from a_conductor.registry import ControlPlaneRegistry


def populated_registry() -> ControlPlaneRegistry:
    registry = ControlPlaneRegistry()
    registry.register_project(
        Project(
            project_id="project-a",
            display_name="Project A",
            root_path=r"A:\Repo-A",
        )
    )
    registry.register_worker(
        Worker(
            worker_id="a-worker-01",
            display_name="A-Worker 1",
            runtime_id="runtime-01",
        )
    )
    registry.assign(
        Assignment(
            assignment_id="assign-01",
            worker_id="a-worker-01",
            project_id="project-a",
            runtime_id="runtime-01",
        ),
        mutation_allowed=True,
    )
    registry.set_worker_state("a-worker-01", WorkerState.READY)
    return registry


def test_initialize_creates_schema_version_and_parent_directory(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "state" / "registry.sqlite"
    store = SQLiteRegistryStore(db_path)

    store.initialize()

    assert db_path.is_file()
    with sqlite3.connect(db_path) as connection:
        version = connection.execute(
            "SELECT value FROM metadata WHERE key = 'schema_version'"
        ).fetchone()[0]
        assert version == "1"
        foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
        # Foreign keys are connection-scoped; the store enables them on its own connections.
        assert foreign_keys in {0, 1}


def test_empty_database_loads_empty_registry(tmp_path: Path) -> None:
    store = SQLiteRegistryStore(tmp_path / "registry.sqlite")

    registry = store.load()

    snapshot = registry.snapshot()
    assert snapshot.projects == ()
    assert snapshot.workers == ()
    assert snapshot.assignments == ()


def test_registry_round_trip_preserves_project_worker_assignment_and_state(
    tmp_path: Path,
) -> None:
    store = SQLiteRegistryStore(tmp_path / "registry.sqlite")
    original = populated_registry()

    store.save(original.snapshot())
    loaded = store.load()
    snapshot = loaded.snapshot()

    assert [(item.project_id, item.root_path) for item in snapshot.projects] == [
        ("project-a", r"A:\Repo-A")
    ]
    assert [
        (item.worker_id, item.runtime_id, item.assignment_id, item.state)
        for item in snapshot.workers
    ] == [
        ("a-worker-01", "runtime-01", "assign-01", WorkerState.READY)
    ]
    assert len(snapshot.assignments) == 1
    record = snapshot.assignments[0]
    assert record.assignment_id == "assign-01"
    assert record.project_id == "project-a"
    assert record.worker_id == "a-worker-01"
    assert record.mutation_allowed is True


def test_default_three_worker_pool_round_trips(tmp_path: Path) -> None:
    store = SQLiteRegistryStore(tmp_path / "registry.sqlite")
    registry = ControlPlaneRegistry.with_default_workers(size=3)

    store.save(registry.snapshot())
    loaded = store.load().snapshot()

    assert [(item.worker_id, item.display_name) for item in loaded.workers] == [
        ("a-worker-01", "A-Worker 1"),
        ("a-worker-02", "A-Worker 2"),
        ("a-worker-03", "A-Worker 3"),
    ]


def test_second_save_replaces_previous_registry_snapshot_atomically(tmp_path: Path) -> None:
    store = SQLiteRegistryStore(tmp_path / "registry.sqlite")
    first = populated_registry()
    store.save(first.snapshot())

    second = ControlPlaneRegistry.with_default_workers(size=1)
    second.register_project(
        Project(
            project_id="project-b",
            display_name="Project B",
            root_path=r"A:\Repo-B",
        )
    )
    store.save(second.snapshot())

    loaded = store.load().snapshot()
    assert [item.project_id for item in loaded.projects] == ["project-b"]
    assert [item.worker_id for item in loaded.workers] == ["a-worker-01"]
    assert loaded.assignments == ()


def test_corrupt_worker_state_fails_explicitly(tmp_path: Path) -> None:
    db_path = tmp_path / "registry.sqlite"
    store = SQLiteRegistryStore(db_path)
    store.save(populated_registry().snapshot())

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE workers SET state = 'NOT_A_REAL_STATE' WHERE worker_id = 'a-worker-01'"
        )
        connection.commit()

    with pytest.raises(PersistenceError, match="invalid worker state"):
        store.load()


def test_unsupported_schema_version_fails_explicitly(tmp_path: Path) -> None:
    db_path = tmp_path / "registry.sqlite"
    store = SQLiteRegistryStore(db_path)
    store.initialize()

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE metadata SET value = '999' WHERE key = 'schema_version'"
        )
        connection.commit()

    with pytest.raises(PersistenceError, match="unsupported schema_version"):
        store.load()


def test_inconsistent_persisted_worker_assignment_reference_is_detected(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "registry.sqlite"
    store = SQLiteRegistryStore(db_path)
    store.save(populated_registry().snapshot())

    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            "UPDATE workers SET assignment_id = 'ghost-assignment' WHERE worker_id = 'a-worker-01'"
        )
        connection.commit()

    with pytest.raises(PersistenceError, match="assignment reference mismatch"):
        store.load()


def test_store_does_not_create_task_broker_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "registry.sqlite"
    store = SQLiteRegistryStore(db_path)
    store.initialize()

    with sqlite3.connect(db_path) as connection:
        names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert {"metadata", "projects", "workers", "assignments"}.issubset(names)
    assert "tasks" not in names
    assert "leases" not in names
    assert "evidence" not in names
