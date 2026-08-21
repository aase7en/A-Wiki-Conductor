from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from a_conductor.domain import Project
from a_conductor.persistence import SQLiteRegistryStore
from a_conductor.serena_config_store import (
    LocalReferencePath,
    SerenaConfigStoreError,
    SQLiteSerenaConfigStore,
)
from a_conductor.serena_runtime import (
    ProjectIdentityPolicy,
    SerenaProjectBinding,
    SerenaWorkerConfig,
)


def worker(tmp_path: Path, worker_id: str = "a-worker-01", port: int = 18011) -> SerenaWorkerConfig:
    root = (tmp_path / worker_id).resolve()
    external = (tmp_path / "bin").resolve()
    return SerenaWorkerConfig(
        worker_id=worker_id,
        runtime_id=f"runtime-{worker_id}",
        instance_root=str(root),
        serena_home=str(root / "serena-home"),
        health_host="127.0.0.1",
        health_port=port,
        tunnel_binding_ref=f"tunnel-ref-{worker_id}",
        credential_ref=f"credential-ref-{worker_id}",
        runtime_executable_ref=str(external / "tunnel-client.exe"),
        profile_template_ref=str(root / "profiles" / "runtime.yaml.template"),
        run_dir=str(root / "run"),
        log_dir=str(root / "logs"),
        startup_timeout_seconds=9,
        stop_timeout_seconds=7,
    )


def binding(tmp_path: Path, project_id: str = "project-one") -> SerenaProjectBinding:
    return SerenaProjectBinding(
        project_id=project_id,
        worktree_path=str((tmp_path / project_id).resolve()),
        identity_policy=ProjectIdentityPolicy.AUTHORIZED_SUCCESSOR,
        expected_branch="main",
        expected_head="abc123",
        mutation_allowed=False,
    )


def store(tmp_path: Path) -> SQLiteSerenaConfigStore:
    return SQLiteSerenaConfigStore(tmp_path / "control-center.sqlite")


def test_worker_config_round_trip(tmp_path: Path) -> None:
    db = store(tmp_path)
    expected = worker(tmp_path)

    db.save_worker_config(expected)

    assert db.get_worker_config(expected.worker_id) == expected
    assert db.list_worker_configs() == (expected,)


def test_worker_config_update_replaces_same_worker_id(tmp_path: Path) -> None:
    db = store(tmp_path)
    original = worker(tmp_path)
    updated = SerenaWorkerConfig(
        **{
            **{name: getattr(original, name) for name in original.__dataclass_fields__},
            "startup_timeout_seconds": 12,
        }
    )
    db.save_worker_config(original)
    db.save_worker_config(updated)
    assert db.get_worker_config(original.worker_id) == updated


def test_project_binding_round_trip(tmp_path: Path) -> None:
    db = store(tmp_path)
    expected = binding(tmp_path)
    db.save_project_binding(expected)
    assert db.get_project_binding(expected.project_id) == expected
    assert db.list_project_bindings() == (expected,)


def test_reference_mapping_round_trip_without_reading_target_file(tmp_path: Path) -> None:
    db = store(tmp_path)
    root = (tmp_path / "refs").resolve()
    missing_file = root / "not-created-tunnel-id.txt"
    expected = LocalReferencePath(
        reference_id="tunnel-ref-a-worker-01",
        file_path=str(missing_file),
        allowed_root=str(root),
    )

    db.save_local_reference(expected)

    assert not missing_file.exists()
    assert db.get_local_reference(expected.reference_id) == expected
    assert db.list_local_references() == (expected,)


def test_store_coexists_with_registry_tables_in_same_sqlite_file(tmp_path: Path) -> None:
    database = tmp_path / "shared.sqlite"
    registry_store = SQLiteRegistryStore(database)
    registry = registry_store.load()
    registry.register_project(Project("p1", "Project", str(tmp_path / "p1")))
    registry_store.save(registry.snapshot())

    config_store = SQLiteSerenaConfigStore(database)
    config_store.save_worker_config(worker(tmp_path))

    assert registry_store.load().get_project("p1").display_name == "Project"
    assert config_store.get_worker_config("a-worker-01") == worker(tmp_path)


def test_instance_root_must_be_unique_across_workers(tmp_path: Path) -> None:
    db = store(tmp_path)
    first = worker(tmp_path, "a-worker-01", 18011)
    second_data = {name: getattr(worker(tmp_path, "a-worker-02", 18012), name) for name in first.__dataclass_fields__}
    shared_root = Path(first.instance_root)
    second_data["instance_root"] = first.instance_root
    second_data["serena_home"] = str(shared_root / "serena-home-2")
    second_data["run_dir"] = str(shared_root / "run-2")
    second_data["log_dir"] = str(shared_root / "logs-2")
    second = SerenaWorkerConfig(**second_data)
    db.save_worker_config(first)

    with pytest.raises(SerenaConfigStoreError) as exc_info:
        db.save_worker_config(second)
    assert exc_info.value.code == "CONFIG_CONFLICT"


def test_health_host_port_pair_must_be_unique(tmp_path: Path) -> None:
    db = store(tmp_path)
    first = worker(tmp_path, "a-worker-01", 18011)
    second = worker(tmp_path, "a-worker-02", 18011)
    db.save_worker_config(first)
    with pytest.raises(SerenaConfigStoreError) as exc_info:
        db.save_worker_config(second)
    assert exc_info.value.code == "CONFIG_CONFLICT"


def test_get_missing_records_returns_none(tmp_path: Path) -> None:
    db = store(tmp_path)
    assert db.get_worker_config("missing") is None
    assert db.get_project_binding("missing") is None
    assert db.get_local_reference("missing") is None


def test_corrupt_identity_policy_fails_closed(tmp_path: Path) -> None:
    db = store(tmp_path)
    expected = binding(tmp_path)
    db.save_project_binding(expected)
    with sqlite3.connect(db.database_path) as connection:
        connection.execute(
            "UPDATE serena_project_bindings SET identity_policy = 'BAD_POLICY' WHERE project_id = ?",
            (expected.project_id,),
        )
        connection.commit()

    with pytest.raises(SerenaConfigStoreError) as exc_info:
        db.get_project_binding(expected.project_id)
    assert exc_info.value.code == "CONFIG_INVALID"


def test_relative_operational_paths_are_rejected(tmp_path: Path) -> None:
    db = store(tmp_path)
    expected = worker(tmp_path)
    data = {name: getattr(expected, name) for name in expected.__dataclass_fields__}
    data["instance_root"] = "relative-worker-root"
    bad = SerenaWorkerConfig(**data)
    with pytest.raises(SerenaConfigStoreError) as exc_info:
        db.save_worker_config(bad)
    assert exc_info.value.code == "CONFIG_INVALID"


def test_reference_allowed_root_must_contain_file_path(tmp_path: Path) -> None:
    db = store(tmp_path)
    bad = LocalReferencePath(
        reference_id="ref",
        file_path=str((tmp_path / "outside" / "id.txt").resolve()),
        allowed_root=str((tmp_path / "allowed").resolve()),
    )
    with pytest.raises(SerenaConfigStoreError) as exc_info:
        db.save_local_reference(bad)
    assert exc_info.value.code == "CONFIG_INVALID"


def test_schema_has_no_secret_or_token_value_columns(tmp_path: Path) -> None:
    db = store(tmp_path)
    db.initialize()
    with sqlite3.connect(db.database_path) as connection:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'serena_%'"
            )
        ]
        columns = {
            table: [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
            for table in tables
        }

    assert "serena_local_references" in columns
    assert columns["serena_local_references"] == [
        "reference_id",
        "file_path",
        "allowed_root",
    ]
    flattened = {name for values in columns.values() for name in values}
    assert "secret_value" not in flattened
    assert "token_value" not in flattened
    assert "file_contents" not in flattened


def test_app_preferences_round_trip_and_default(tmp_path):
    from a_conductor.serena_config_store import SQLiteSerenaConfigStore

    store = SQLiteSerenaConfigStore(tmp_path / "pref.sqlite")
    store.initialize()

    assert store.get_preference("supervised") is None
    store.set_preference("supervised", True)
    assert store.get_preference("supervised") is True
    store.set_preference("supervised", False)
    assert store.get_preference("supervised") is False
    store.set_preference("theme_note", True)
    assert store.get_preference("theme_note") is True
    assert store.get_preference("missing") is None

    reopened = SQLiteSerenaConfigStore(tmp_path / "pref.sqlite")
    reopened.initialize()
    assert reopened.get_preference("supervised") is False


def test_app_preferences_reject_invalid(tmp_path):
    from a_conductor.serena_config_store import (
        SerenaConfigStoreError,
        SQLiteSerenaConfigStore,
    )

    store = SQLiteSerenaConfigStore(tmp_path / "pref2.sqlite")
    store.initialize()
    for bad in ("", "   ", "key with spaces"):
        try:
            store.set_preference(bad, True)
        except SerenaConfigStoreError as exc:
            assert "PREFERENCE_KEY_INVALID" in str(exc)
        else:
            raise AssertionError(f"invalid key accepted: {bad!r}")
    try:
        store.set_preference("ok", "not-a-bool")
    except SerenaConfigStoreError as exc:
        assert "PREFERENCE_VALUE_INVALID" in str(exc)
    else:
        raise AssertionError("non-bool value accepted")
