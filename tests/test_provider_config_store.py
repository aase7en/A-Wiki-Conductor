from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

import pytest

from a_conductor.provider_config_store import (
    ProviderAdmissionKind,
    ProviderConfigStoreError,
    SQLiteProviderConfigStore,
)
from a_conductor.provider_configuration import (
    ActorCapabilityEvidence,
    EgressBoundary,
    HarnessStrategy,
    ProviderConfiguration,
    ProviderEndpointConfig,
    ProviderHealth,
    ProviderModelConfiguration,
    ProviderObservation,
    ProviderTrustClass,
    ProtocolFamily,
    QuotaSnapshot,
)
from a_conductor.serena_config_store import SQLiteSerenaConfigStore


NOW = datetime(2026, 8, 28, 1, 30, tzinfo=timezone.utc)

def make_profile() -> ProviderConfiguration:
    return ProviderConfiguration(
        provider_id="provider-test",
        display_name="Test Provider",
        provider_type="cloud-proxy",
        protocol_family=ProtocolFamily.ANTHROPIC_MESSAGES,
        endpoint_ref="provider-config:test/base-url",
        credential_ref="secret-ref:provider/test/main",
        trust_class=ProviderTrustClass.TRUSTED_THIRD_PARTY,
        egress_boundary=EgressBoundary.EXTERNAL_THIRD_PARTY,
        harness_strategies=(HarnessStrategy.CLAUDE_CODE_CLI,),
        max_concurrency=1,
        models=(ProviderModelConfiguration(model_id="model-test", display_name="Model Test", actor_capabilities=(ActorCapabilityEvidence(capability="documentation", evidence_level="DECLARED", source="test"),), supported_effort_levels=("DEFAULT",)),),
        enabled=True,
    )


def test_provider_config_round_trip_in_same_control_database(tmp_path) -> None:
    database = tmp_path / "control.sqlite"
    SQLiteSerenaConfigStore(database).initialize()
    store = SQLiteProviderConfigStore(database)
    profile = make_profile()
    endpoint = ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1")

    store.save_endpoint(endpoint)
    store.save_provider(profile)

    assert store.get_endpoint(endpoint.endpoint_ref) == endpoint
    assert store.get_provider(profile.provider_id) == profile
    with sqlite3.connect(database) as connection:
        names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "serena_worker_configs" in names
    assert "provider_configurations" in names
    assert "provider_endpoints" in names


def test_latest_observation_round_trip_is_separate_from_configuration(tmp_path) -> None:
    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    profile = make_profile()
    store.save_provider(profile)
    observation = ProviderObservation(
        provider_id=profile.provider_id,
        health=ProviderHealth.AVAILABLE,
        observed_at=NOW,
        provenance="fake:test",
        latency_ms=50,
        quota=QuotaSnapshot(
            window_type="daily",
            limit=100,
            used=40,
            remaining=60,
            reset_in_seconds=3600,
            unit="requests",
        ),
    )
    store.save_observation(observation)
    assert store.get_observation(profile.provider_id) == observation


def test_provider_store_schema_has_no_secret_value_columns(tmp_path) -> None:
    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    store.initialize()
    with sqlite3.connect(database) as connection:
        columns = []
        for table in (
            "provider_configurations",
            "provider_endpoints",
            "provider_observations",
            "provider_admissions",
        ):
            columns.extend(row[1].lower() for row in connection.execute(f"PRAGMA table_info({table})"))
    forbidden = ("api_key", "token_value", "password", "secret_value", "authorization")
    assert not [name for name in columns if any(item in name for item in forbidden)]


def _admission_store(database, ids):
    return SQLiteProviderConfigStore(database, admission_id_factory=lambda: next(ids))


def test_provider_initialize_preserves_existing_control_center_tables_and_data(tmp_path) -> None:
    database = tmp_path / "control.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE existing_state(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO existing_state(key, value) VALUES('keep', 'unchanged')")
        connection.commit()

    SQLiteProviderConfigStore(database).initialize()

    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT value FROM existing_state WHERE key='keep'").fetchone()[0] == "unchanged"
        names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"provider_configurations", "provider_endpoints", "provider_observations", "provider_admissions"} <= names


def test_atomic_provider_admission_allows_only_one_concurrent_owner(tmp_path) -> None:
    database = tmp_path / "control.sqlite"
    setup = SQLiteProviderConfigStore(database)
    setup.save_provider(make_profile())
    barrier = Barrier(2, timeout=3)

    def attempt(index: int):
        store = _admission_store(database, iter((f"admission-{index}",)))
        barrier.wait()
        return store.acquire_admission(
            provider_id="provider-test",
            execution_id=f"execution-{index}",
            batch_id=f"batch-{index}",
            expected_max_concurrency=1,
            now=NOW,
            ttl_seconds=600,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(attempt, (1, 2)))
    assert sorted(item.kind.value for item in results) == ["ADMITTED", "CAPACITY_WAIT"]
    assert sum(item.admission is not None for item in results) == 1


def test_provider_admission_release_requires_exact_identity_and_no_double_release(tmp_path) -> None:
    database = tmp_path / "control.sqlite"
    store = _admission_store(database, iter(("admission-1",)))
    store.save_provider(make_profile())
    result = store.acquire_admission(
        provider_id="provider-test",
        execution_id="execution-1",
        batch_id="batch-1",
        expected_max_concurrency=1,
        now=NOW,
        ttl_seconds=600,
    )
    assert result.kind is ProviderAdmissionKind.ADMITTED
    admission = result.admission
    assert admission is not None

    with pytest.raises(ProviderConfigStoreError) as exc:
        store.release_admission(admission.admission_id, provider_id="provider-test", execution_id="wrong", batch_id="batch-1", now=NOW)
    assert exc.value.code == "PROVIDER_ADMISSION_IDENTITY_MISMATCH"

    released = store.release_admission(
        admission.admission_id,
        provider_id="provider-test",
        execution_id="execution-1",
        batch_id="batch-1",
        now=NOW,
    )
    assert released.status == "RELEASED"

    with pytest.raises(ProviderConfigStoreError) as exc:
        store.release_admission(
            admission.admission_id,
            provider_id="provider-test",
            execution_id="execution-1",
            batch_id="batch-1",
            now=NOW,
        )
    assert exc.value.code == "PROVIDER_ADMISSION_NOT_ACTIVE"


def test_expired_admission_is_reconciled_before_new_capacity_is_granted(tmp_path) -> None:
    database = tmp_path / "control.sqlite"
    store = _admission_store(database, iter(("admission-old", "admission-new")))
    store.save_provider(make_profile())
    old = store.acquire_admission(
        provider_id="provider-test",
        execution_id="execution-old",
        batch_id="batch-old",
        expected_max_concurrency=1,
        now=NOW,
        ttl_seconds=1,
    )
    assert old.kind is ProviderAdmissionKind.ADMITTED

    new = store.acquire_admission(
        provider_id="provider-test",
        execution_id="execution-new",
        batch_id="batch-new",
        expected_max_concurrency=1,
        now=NOW + timedelta(seconds=2),
        ttl_seconds=600,
    )
    assert new.kind is ProviderAdmissionKind.ADMITTED
    assert old.admission is not None
    assert store.get_admission(old.admission.admission_id).status == "EXPIRED"


def test_corrupt_provider_admission_timestamp_fails_as_typed_store_error(tmp_path) -> None:
    database = tmp_path / "control.sqlite"
    store = _admission_store(database, iter(("admission-corrupt",)))
    store.save_provider(make_profile())
    admitted = store.acquire_admission(
        provider_id="provider-test",
        execution_id="execution-corrupt",
        batch_id="batch-corrupt",
        expected_max_concurrency=1,
        now=NOW,
        ttl_seconds=600,
    )
    assert admitted.admission is not None
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE provider_admissions SET acquired_at='not-a-time' WHERE admission_id=?",
            (admitted.admission.admission_id,),
        )
        connection.commit()

    with pytest.raises(ProviderConfigStoreError) as exc:
        store.get_admission(admitted.admission.admission_id)
    assert exc.value.code == "PROVIDER_ADMISSION_RECORD_INVALID"


def test_corrupt_active_admission_expiry_blocks_as_typed_recovery_not_capacity_wait(tmp_path) -> None:
    database = tmp_path / "control.sqlite"
    store = _admission_store(database, iter(("admission-corrupt-active", "admission-next")))
    store.save_provider(make_profile())
    admitted = store.acquire_admission(
        provider_id="provider-test", execution_id="execution-corrupt-active",
        batch_id="batch-corrupt-active", expected_max_concurrency=1,
        now=NOW, ttl_seconds=600,
    )
    assert admitted.kind is ProviderAdmissionKind.ADMITTED
    assert admitted.admission is not None
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE provider_admissions SET expires_at='not-a-time' WHERE admission_id=?",
            (admitted.admission.admission_id,),
        )
        connection.commit()

    with pytest.raises(ProviderConfigStoreError) as exc:
        store.acquire_admission(
            provider_id="provider-test", execution_id="execution-next",
            batch_id="batch-next", expected_max_concurrency=1,
            now=NOW + timedelta(seconds=1), ttl_seconds=600,
        )

    assert exc.value.code == "PROVIDER_ADMISSION_RECORD_INVALID"
