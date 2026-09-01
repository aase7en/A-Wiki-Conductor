from __future__ import annotations

import sqlite3
import multiprocessing
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


def _acquire_after_expiry_in_process(database, start_event, output, execution_id):
    try:
        store = SQLiteProviderConfigStore(database)
        if not start_event.wait(10):
            output.put(("error", "start-timeout", None))
            return
        result = store.acquire_admission(
            provider_id="provider-test", execution_id=execution_id,
            batch_id=f"batch-{execution_id}", expected_max_concurrency=1,
            now=NOW + timedelta(seconds=2), ttl_seconds=600,
        )
        admission_id = None if result.admission is None else result.admission.admission_id
        output.put((result.kind.value, result.reason_code, admission_id))
    except BaseException as exc:
        output.put(("error", f"{type(exc).__name__}:{exc}", None))

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
    store.save_observation(
        ProviderObservation(
            **{**observation.as_dict(), "configuration_generation": 1}
        )
    )
    persisted = store.get_observation(profile.provider_id)
    assert persisted.health == observation.health
    assert persisted.quota == observation.quota
    assert persisted.configuration_generation == 1


def test_generation_cas_prevents_stale_editors_and_blind_updates(tmp_path) -> None:
    store = SQLiteProviderConfigStore(tmp_path / "control.sqlite")
    profile = make_profile()
    assert (
        store.save_endpoint(
            ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1")
        )
        == 1
    )
    assert store.save_provider(profile) == 1

    with pytest.raises(ProviderConfigStoreError) as missing:
        store.save_provider(profile)
    assert missing.value.code == "PROVIDER_GENERATION_EXPECTED"
    with pytest.raises(ProviderConfigStoreError) as stale:
        store.save_provider(profile, expected_generation=5)
    assert stale.value.code == "PROVIDER_GENERATION_STALE"

    first = store.save_provider(
        ProviderConfiguration(**{**profile.as_dict(), "display_name": "Editor A"}),
        expected_generation=1,
    )
    assert first == 2
    with pytest.raises(ProviderConfigStoreError) as second:
        store.save_provider(
            ProviderConfiguration(**{**profile.as_dict(), "display_name": "Editor B"}),
            expected_generation=1,
        )
    assert second.value.code == "PROVIDER_GENERATION_STALE"
    assert store.get_provider(profile.provider_id).display_name == "Editor A"

    with pytest.raises(ProviderConfigStoreError) as endpoint_missing:
        store.save_endpoint(
            ProviderEndpointConfig(profile.endpoint_ref, "https://api2.example.test/v1")
        )
    assert endpoint_missing.value.code == "PROVIDER_GENERATION_EXPECTED"
    with pytest.raises(ProviderConfigStoreError) as endpoint_stale:
        store.save_endpoint(
            ProviderEndpointConfig(profile.endpoint_ref, "https://api2.example.test/v1"),
            expected_generation=99,
        )
    assert endpoint_stale.value.code == "PROVIDER_GENERATION_STALE"


def test_endpoint_update_fans_out_generation_to_referencing_providers_only(tmp_path) -> None:
    store = SQLiteProviderConfigStore(tmp_path / "control.sqlite")
    shared = make_profile()
    other = ProviderConfiguration(
        **{
            **make_profile().as_dict(),
            "provider_id": "provider-other",
            "endpoint_ref": "provider-config:other/base-url",
            "credential_ref": "secret-ref:provider/other",
        }
    )
    store.save_endpoint(
        ProviderEndpointConfig(shared.endpoint_ref, "https://api.example.test/v1")
    )
    store.save_endpoint(
        ProviderEndpointConfig(other.endpoint_ref, "https://other.example.test/v1")
    )
    store.save_provider(shared)
    store.save_provider(other)

    store.save_endpoint(
        ProviderEndpointConfig(shared.endpoint_ref, "https://api2.example.test/v1"),
        expected_generation=1,
    )

    snapshot = store.load_provider_snapshot(shared.provider_id)
    assert snapshot.generation == 2
    assert snapshot.endpoint.base_url == "https://api2.example.test/v1"
    unrelated = store.load_provider_snapshot(other.provider_id)
    assert unrelated.generation == 1


def test_stale_observation_cannot_authorize_new_configuration(tmp_path) -> None:
    from a_conductor.provider_configuration import is_provider_ready

    store = SQLiteProviderConfigStore(tmp_path / "control.sqlite")
    profile = make_profile()
    store.save_endpoint(
        ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1")
    )
    store.save_provider(profile)
    observation = ProviderObservation(
        provider_id=profile.provider_id,
        health=ProviderHealth.AVAILABLE,
        observed_at=NOW,
        provenance="fake:test",
        configuration_generation=1,
    )
    store.save_observation(observation)

    store.save_provider(
        ProviderConfiguration(
            **{**profile.as_dict(), "credential_ref": "secret-ref:provider/new"}
        ),
        expected_generation=1,
    )

    with pytest.raises(ProviderConfigStoreError) as stale_probe:
        store.save_observation(observation)
    assert stale_probe.value.code == "PROVIDER_OBSERVATION_GENERATION_STALE"

    snapshot = store.load_provider_snapshot(profile.provider_id)
    assert snapshot.generation == 2
    assert snapshot.observation.configuration_generation == 1
    assert (
        is_provider_ready(
            snapshot.profile,
            snapshot.observation,
            now=NOW + timedelta(seconds=10),
            expected_generation=snapshot.generation,
        )
        is False
    ), "an observation from generation 1 must not authorize generation 2"


def test_observation_write_requires_positive_current_generation(tmp_path) -> None:
    store = SQLiteProviderConfigStore(tmp_path / "control.sqlite")
    profile = make_profile()
    store.save_provider(profile)
    with pytest.raises(ValueError):
        store.save_observation(
            ProviderObservation(
                provider_id=profile.provider_id,
                health=ProviderHealth.AVAILABLE,
                observed_at=NOW,
                provenance="fake:test",
            )
        )
    with pytest.raises(ProviderConfigStoreError) as unknown_provider:
        store.save_observation(
            ProviderObservation(
                provider_id="provider-missing",
                health=ProviderHealth.AVAILABLE,
                observed_at=NOW,
                provenance="fake:test",
                configuration_generation=1,
            )
        )
    assert unknown_provider.value.code == "PROVIDER_OBSERVATION_PROVIDER_NOT_FOUND"


def test_legacy_rows_migrate_conservatively_on_synthetic_installed_database(tmp_path) -> None:
    database = tmp_path / "installed-copy.sqlite"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE provider_configurations (
            provider_id TEXT PRIMARY KEY, schema_version TEXT NOT NULL,
            display_name TEXT NOT NULL, provider_type TEXT NOT NULL,
            protocol_family TEXT NOT NULL, endpoint_ref TEXT NOT NULL,
            credential_ref TEXT NOT NULL, trust_class TEXT NOT NULL,
            egress_boundary TEXT NOT NULL, harness_strategies_json TEXT NOT NULL,
            max_concurrency INTEGER NOT NULL, models_json TEXT NOT NULL,
            enabled INTEGER NOT NULL
        );
        CREATE TABLE provider_endpoints (endpoint_ref TEXT PRIMARY KEY, base_url TEXT NOT NULL);
        CREATE TABLE provider_observations (
            provider_id TEXT PRIMARY KEY, schema_version TEXT NOT NULL,
            health TEXT NOT NULL, observed_at TEXT NOT NULL,
            provenance TEXT NOT NULL, latency_ms INTEGER, quota_json TEXT
        );
        CREATE TABLE unrelated_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT INTO unrelated_settings VALUES ('theme', 'sunday');
        """
    )
    profile = make_profile()
    endpoint = ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1")
    connection.execute(
        "INSERT INTO provider_configurations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            profile.provider_id, profile.schema_version, profile.display_name,
            profile.provider_type, profile.protocol_family.value, profile.endpoint_ref,
            profile.credential_ref, profile.trust_class.value, profile.egress_boundary.value,
            '["CLAUDE_CODE_CLI"]', 1,
            '[{"model_id":"model-test","display_name":"Model Test"}]', 1,
        ),
    )
    connection.execute(
        "INSERT INTO provider_endpoints VALUES(?, ?)",
        (endpoint.endpoint_ref, endpoint.base_url),
    )
    connection.execute(
        "INSERT INTO provider_observations VALUES('provider-test','1.0.0','AVAILABLE',?,?,NULL,NULL)",
        ("2026-08-28T01:30:00Z", "legacy:probe"),
    )
    connection.commit()
    connection.close()

    store = SQLiteProviderConfigStore(database)
    snapshot = store.load_provider_snapshot(profile.provider_id)

    assert snapshot.generation == 1
    assert snapshot.observation is not None
    assert snapshot.observation.configuration_generation is None, (
        "legacy observations must load as unknown generation, never upgraded"
    )
    from a_conductor.provider_configuration import is_provider_ready

    assert (
        is_provider_ready(
            snapshot.profile,
            snapshot.observation,
            now=NOW + timedelta(seconds=10),
            expected_generation=1,
        )
        is False
    )
    with sqlite3.connect(database) as check:
        assert (
            check.execute(
                "SELECT value FROM unrelated_settings WHERE key='theme'"
            ).fetchone()[0]
            == "sunday"
        )


def test_admission_expected_generation_seam(tmp_path) -> None:
    store = SQLiteProviderConfigStore(tmp_path / "control.sqlite")
    profile = make_profile()
    store.save_provider(profile)
    admitted = store.acquire_admission(
        provider_id=profile.provider_id,
        execution_id="exec-1",
        batch_id="batch-1",
        expected_max_concurrency=1,
        now=NOW,
        ttl_seconds=600,
        expected_configuration_generation=1,
    )
    assert admitted.kind.value == "ADMITTED"
    assert admitted.admission.configuration_generation == 1

    with pytest.raises(ProviderConfigStoreError) as stale:
        store.acquire_admission(
            provider_id=profile.provider_id,
            execution_id="exec-2",
            batch_id="batch-2",
            expected_max_concurrency=1,
            now=NOW,
            ttl_seconds=600,
            expected_configuration_generation=99,
        )
    assert stale.value.code == "PROVIDER_ADMISSION_GENERATION_STALE"
    with sqlite3.connect(store.database_path) as check:
        count = check.execute(
            "SELECT COUNT(*) FROM provider_admissions WHERE execution_id='exec-2'"
        ).fetchone()[0]
    assert count == 0, "stale expected generation must not consume capacity"

    prior = store.acquire_admission(
        provider_id=profile.provider_id,
        execution_id="exec-1",
        batch_id="batch-1",
        expected_max_concurrency=1,
        now=NOW + timedelta(seconds=1),
        ttl_seconds=600,
        expected_configuration_generation=1,
    )
    assert prior.kind.value == "EXISTING"

    # Simulate legacy/out-of-band generation drift that bypassed the public write fence.
    # Public save_provider/save_endpoint are now required to reject this while ACTIVE.
    with sqlite3.connect(store.database_path) as drift:
        drift.execute(
            "UPDATE provider_configurations SET generation=2 WHERE provider_id=?",
            (profile.provider_id,),
        )
        drift.commit()
    mismatched = store.acquire_admission(
        provider_id=profile.provider_id,
        execution_id="exec-1",
        batch_id="batch-1",
        expected_max_concurrency=1,
        now=NOW + timedelta(seconds=2),
        ttl_seconds=600,
        expected_configuration_generation=2,
    )
    assert mismatched.kind.value == "RECOVERY_REQUIRED"
    assert mismatched.reason_code == "PROVIDER_ADMISSION_GENERATION_RECONCILE"

    with sqlite3.connect(store.database_path) as legacy:
        legacy.execute(
            "UPDATE provider_admissions SET configuration_generation=NULL "
            "WHERE execution_id='exec-1'"
        )
        legacy.commit()
    unknown = store.acquire_admission(
        provider_id=profile.provider_id,
        execution_id="exec-1",
        batch_id="batch-1",
        expected_max_concurrency=1,
        now=NOW + timedelta(seconds=3),
        ttl_seconds=600,
        expected_configuration_generation=2,
    )
    assert unknown.kind.value == "RECOVERY_REQUIRED"
    assert unknown.reason_code == "PROVIDER_ADMISSION_GENERATION_RECONCILE"


def test_backward_compatible_admission_without_generation_still_works(tmp_path) -> None:
    store = SQLiteProviderConfigStore(tmp_path / "control.sqlite")
    profile = make_profile()
    store.save_provider(profile)
    result = store.acquire_admission(
        provider_id=profile.provider_id,
        execution_id="exec-legacy",
        batch_id="batch-legacy",
        expected_max_concurrency=1,
        now=NOW,
        ttl_seconds=600,
    )
    assert result.kind.value == "ADMITTED"
    assert result.admission.configuration_generation is None


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


def test_expired_time_alone_does_not_free_unknown_provider_capacity(tmp_path) -> None:
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
    assert old.admission is not None

    blocked = store.acquire_admission(
        provider_id="provider-test",
        execution_id="execution-new",
        batch_id="batch-new",
        expected_max_concurrency=1,
        now=NOW + timedelta(seconds=2),
        ttl_seconds=600,
    )
    assert blocked.kind is ProviderAdmissionKind.RECOVERY_REQUIRED
    assert blocked.reason_code == "PROVIDER_ADMISSION_EXPIRED_RECONCILE"
    assert blocked.admission is not None
    assert blocked.admission.admission_id == old.admission.admission_id
    assert store.get_admission(old.admission.admission_id).status == "ACTIVE"

    released = store.release_admission(
        old.admission.admission_id,
        provider_id="provider-test",
        execution_id="execution-old",
        batch_id="batch-old",
        now=NOW + timedelta(seconds=2),
    )
    assert released.status == "RELEASED"

    admitted = store.acquire_admission(
        provider_id="provider-test",
        execution_id="execution-new",
        batch_id="batch-new",
        expected_max_concurrency=1,
        now=NOW + timedelta(seconds=2),
        ttl_seconds=600,
    )
    assert admitted.kind is ProviderAdmissionKind.ADMITTED


def test_same_execution_after_ttl_requires_reconcile_instead_of_existing(tmp_path) -> None:
    database = tmp_path / "control.sqlite"
    store = _admission_store(database, iter(("admission-same",)))
    store.save_provider(make_profile())
    first = store.acquire_admission(
        provider_id="provider-test", execution_id="execution-same",
        batch_id="batch-same", expected_max_concurrency=1, now=NOW, ttl_seconds=1,
    )
    assert first.admission is not None
    replay = store.acquire_admission(
        provider_id="provider-test", execution_id="execution-same",
        batch_id="batch-same", expected_max_concurrency=1,
        now=NOW + timedelta(seconds=2), ttl_seconds=600,
    )
    assert replay.kind is ProviderAdmissionKind.RECOVERY_REQUIRED
    assert replay.reason_code == "PROVIDER_ADMISSION_EXPIRED_RECONCILE"
    assert replay.admission == first.admission


def test_legacy_expired_admission_remains_capacity_consuming_until_exact_release(tmp_path) -> None:
    database = tmp_path / "control.sqlite"
    store = _admission_store(database, iter(("admission-old", "admission-new")))
    store.save_provider(make_profile())
    old = store.acquire_admission(
        provider_id="provider-test", execution_id="execution-old",
        batch_id="batch-old", expected_max_concurrency=1, now=NOW, ttl_seconds=1,
    )
    assert old.admission is not None
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE provider_admissions SET status='EXPIRED' WHERE admission_id=?",
            (old.admission.admission_id,),
        )
        connection.commit()

    blocked = store.acquire_admission(
        provider_id="provider-test", execution_id="execution-new",
        batch_id="batch-new", expected_max_concurrency=1,
        now=NOW + timedelta(seconds=2), ttl_seconds=600,
    )
    assert blocked.kind is ProviderAdmissionKind.RECOVERY_REQUIRED
    assert blocked.admission is not None
    assert blocked.admission.admission_id == old.admission.admission_id

    released = store.release_admission(
        old.admission.admission_id, provider_id="provider-test",
        execution_id="execution-old", batch_id="batch-old",
        now=NOW + timedelta(seconds=2),
    )
    assert released.status == "RELEASED"



def test_expired_unknown_admission_blocks_spawned_processes(tmp_path) -> None:
    database = str(tmp_path / "control.sqlite")
    store = _admission_store(database, iter(("admission-old",)))
    store.save_provider(make_profile())
    old = store.acquire_admission(
        provider_id="provider-test", execution_id="execution-old",
        batch_id="batch-old", expected_max_concurrency=1, now=NOW, ttl_seconds=1,
    )
    assert old.admission is not None
    ctx = multiprocessing.get_context("spawn")
    start_event = ctx.Event()
    output = ctx.Queue()
    processes = tuple(
        ctx.Process(target=_acquire_after_expiry_in_process, args=(database, start_event, output, f"new-{i}"))
        for i in (1, 2)
    )
    for process in processes:
        process.start()
    start_event.set()
    for process in processes:
        process.join(15)
        assert process.exitcode == 0
    results = [output.get(timeout=5) for _ in processes]
    assert {item[0] for item in results} == {"RECOVERY_REQUIRED"}
    assert {item[1] for item in results} == {"PROVIDER_ADMISSION_EXPIRED_RECONCILE"}
    assert {item[2] for item in results} == {old.admission.admission_id}
    with sqlite3.connect(database) as connection:
        rows = connection.execute("SELECT admission_id, status FROM provider_admissions").fetchall()
    assert rows == [(old.admission.admission_id, "ACTIVE")]

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


def test_generation_corruption_never_rolls_back_and_reauthorizes_stale_observation(tmp_path) -> None:
    from a_conductor.provider_runtime_assembly import SQLiteClaudeCodeProviderResolver
    from a_conductor.provider_configuration import is_provider_ready

    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    profile = make_profile()
    store.save_endpoint(ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1"))
    store.save_provider(profile)
    observation = ProviderObservation(
        provider_id=profile.provider_id, health=ProviderHealth.AVAILABLE,
        observed_at=NOW, provenance="fake:old-generation", configuration_generation=1,
    )
    store.save_observation(observation)
    store.save_provider(
        ProviderConfiguration(**{**profile.as_dict(), "display_name": "Generation Two"}),
        expected_generation=1,
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE provider_configurations SET generation=0 WHERE provider_id=?",
            (profile.provider_id,),
        )
        connection.commit()

    resolved = SQLiteClaudeCodeProviderResolver(store).resolve(profile.provider_id)
    assert resolved is None or resolved.observation is None
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT generation FROM provider_configurations WHERE provider_id=?",
            (profile.provider_id,),
        ).fetchone()[0] == 0
    if resolved is not None and resolved.observation is not None:
        assert not is_provider_ready(
            resolved.profile, resolved.observation, now=NOW, expected_generation=1,
        )


def test_expected_generation_cannot_recreate_missing_provider_or_endpoint(tmp_path) -> None:
    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    profile = make_profile()
    endpoint = ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1")
    store.save_endpoint(endpoint)
    store.save_provider(profile)
    with sqlite3.connect(database) as connection:
        connection.execute("DELETE FROM provider_configurations WHERE provider_id=?", (profile.provider_id,))
        connection.execute("DELETE FROM provider_endpoints WHERE endpoint_ref=?", (profile.endpoint_ref,))
        connection.commit()

    with pytest.raises(ProviderConfigStoreError) as provider_stale:
        store.save_provider(profile, expected_generation=1)
    assert provider_stale.value.code == "PROVIDER_GENERATION_STALE"
    with pytest.raises(ProviderConfigStoreError) as endpoint_stale:
        store.save_endpoint(endpoint, expected_generation=1)
    assert endpoint_stale.value.code == "PROVIDER_GENERATION_STALE"


@pytest.mark.parametrize("corrupt", ["abc", 1.5])
def test_non_integer_generation_corruption_fails_typed_without_mutation(tmp_path, corrupt) -> None:
    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    profile = make_profile()
    store.save_provider(profile)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE provider_configurations SET generation=? WHERE provider_id=?",
            (corrupt, profile.provider_id),
        )
        connection.commit()

    with pytest.raises(ProviderConfigStoreError) as invalid:
        store.save_provider(profile, expected_generation=1)
    assert invalid.value.code == "PROVIDER_GENERATION_INVALID"
    with sqlite3.connect(database) as connection:
        persisted = connection.execute(
            "SELECT generation, typeof(generation) FROM provider_configurations WHERE provider_id=?",
            (profile.provider_id,),
        ).fetchone()
    assert persisted[0] == corrupt


def test_generation_exhaustion_fails_closed_before_sqlite_real_coercion(tmp_path) -> None:
    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    profile = make_profile()
    endpoint = ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1")
    store.save_endpoint(endpoint)
    store.save_provider(profile)
    maximum = 2**63 - 1
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE provider_configurations SET generation=? WHERE provider_id=?",
            (maximum, profile.provider_id),
        )
        connection.commit()

    with pytest.raises(ProviderConfigStoreError) as exhausted:
        store.save_provider(profile, expected_generation=maximum)
    assert exhausted.value.code == "PROVIDER_GENERATION_EXHAUSTED"
    with sqlite3.connect(database) as connection:
        value, kind = connection.execute(
            "SELECT generation, typeof(generation) FROM provider_configurations WHERE provider_id=?",
            (profile.provider_id,),
        ).fetchone()
    assert value == maximum
    assert kind == "integer"


@pytest.mark.parametrize(
    ("bad_generation", "expected_code"),
    [(0, "PROVIDER_GENERATION_INVALID"), (2**63 - 1, "PROVIDER_GENERATION_EXHAUSTED")],
)
def test_endpoint_fanout_refuses_corrupt_or_exhausted_referencing_provider_generation(
    tmp_path, bad_generation, expected_code
) -> None:
    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    profile = make_profile()
    endpoint = ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1")
    store.save_endpoint(endpoint)
    store.save_provider(profile)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE provider_configurations SET generation=? WHERE provider_id=?",
            (bad_generation, profile.provider_id),
        )
        connection.commit()

    with pytest.raises(ProviderConfigStoreError) as blocked:
        store.save_endpoint(
            ProviderEndpointConfig(profile.endpoint_ref, "https://api2.example.test/v1"),
            expected_generation=1,
        )
    assert blocked.value.code == expected_code
    assert store.get_endpoint(profile.endpoint_ref) == endpoint


def test_endpoint_insert_fans_out_generation_to_existing_referencing_provider(tmp_path) -> None:
    from a_conductor.provider_configuration import is_provider_ready

    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    profile = make_profile()
    store.save_provider(profile)
    stale_observation = ProviderObservation(
        provider_id=profile.provider_id,
        health=ProviderHealth.AVAILABLE,
        observed_at=NOW,
        provenance="fake:before-endpoint-existed",
        configuration_generation=1,
    )
    store.save_observation(stale_observation)

    assert store.save_endpoint(
        ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1")
    ) == 1

    snapshot = store.load_provider_snapshot(profile.provider_id)
    assert snapshot is not None
    assert snapshot.endpoint is not None
    assert snapshot.generation == 2
    assert snapshot.observation is not None
    assert snapshot.observation.configuration_generation == 1
    assert not is_provider_ready(
        snapshot.profile,
        snapshot.observation,
        now=NOW,
        expected_generation=snapshot.generation,
    )


@pytest.mark.parametrize(
    ("bad_generation", "expected_code"),
    [(0, "PROVIDER_GENERATION_INVALID"), (2**63 - 1, "PROVIDER_GENERATION_EXHAUSTED")],
)
def test_endpoint_insert_fanout_validates_referencing_provider_before_mutation(
    tmp_path, bad_generation, expected_code
) -> None:
    database = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(database)
    profile = make_profile()
    store.save_provider(profile)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE provider_configurations SET generation=? WHERE provider_id=?",
            (bad_generation, profile.provider_id),
        )
        connection.commit()

    with pytest.raises(ProviderConfigStoreError) as blocked:
        store.save_endpoint(
            ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1")
        )
    assert blocked.value.code == expected_code
    assert store.get_endpoint(profile.endpoint_ref) is None

def test_interrupted_legacy_generation_migration_rolls_back_and_retries(tmp_path, monkeypatch) -> None:
    database = tmp_path / "interrupted-legacy.sqlite"
    connection = sqlite3.connect(database)
    connection.executescript("""
        CREATE TABLE provider_configurations (provider_id TEXT PRIMARY KEY, schema_version TEXT NOT NULL, display_name TEXT NOT NULL, provider_type TEXT NOT NULL, protocol_family TEXT NOT NULL, endpoint_ref TEXT NOT NULL, credential_ref TEXT NOT NULL, trust_class TEXT NOT NULL, egress_boundary TEXT NOT NULL, harness_strategies_json TEXT NOT NULL, max_concurrency INTEGER NOT NULL, models_json TEXT NOT NULL, enabled INTEGER NOT NULL);
        CREATE TABLE provider_endpoints (endpoint_ref TEXT PRIMARY KEY, base_url TEXT NOT NULL);
        CREATE TABLE unrelated_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT INTO unrelated_settings VALUES ('theme', 'sunday');
    """)
    profile = make_profile()
    connection.execute("INSERT INTO provider_configurations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (profile.provider_id, profile.schema_version, profile.display_name, profile.provider_type, profile.protocol_family.value, profile.endpoint_ref, profile.credential_ref, profile.trust_class.value, profile.egress_boundary.value, '["CLAUDE_CODE_CLI"]', 1, '[{"model_id":"model-test","display_name":"Model Test"}]', 1))
    connection.execute("INSERT INTO provider_endpoints VALUES(?, ?)", (profile.endpoint_ref, "https://api.example.test/v1"))
    connection.commit(); connection.close()
    real_connect = sqlite3.connect
    denied = {"done": False}

    def faulting_connect(*args, **kwargs):
        conn = real_connect(*args, **kwargs)
        def authorizer(action, arg1, arg2, db_name, trigger):
            if not denied["done"] and action == sqlite3.SQLITE_UPDATE and arg1 == "provider_configurations" and arg2 == "generation":
                denied["done"] = True
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        conn.set_authorizer(authorizer)
        return conn
    monkeypatch.setattr(sqlite3, "connect", faulting_connect)
    store = SQLiteProviderConfigStore(database)
    with pytest.raises(ProviderConfigStoreError) as interrupted:
        store.initialize()
    assert interrupted.value.code == "CONFIG_STORE_INITIALIZE_FAILED"
    monkeypatch.setattr(sqlite3, "connect", real_connect)
    with sqlite3.connect(database) as check:
        provider_columns = {row[1] for row in check.execute("PRAGMA table_info(provider_configurations)")}
        endpoint_columns = {row[1] for row in check.execute("PRAGMA table_info(provider_endpoints)")}
    assert "generation" not in provider_columns
    assert "generation" not in endpoint_columns

    store.initialize()
    snapshot = store.load_provider_snapshot(profile.provider_id)
    assert snapshot is not None
    assert snapshot.generation == 1
    assert snapshot.endpoint is not None
    with sqlite3.connect(database) as check:
        assert check.execute("SELECT generation FROM provider_endpoints WHERE endpoint_ref=?", (profile.endpoint_ref,)).fetchone()[0] == 1
        assert check.execute("SELECT value FROM unrelated_settings WHERE key='theme'").fetchone()[0] == "sunday"


def test_generation_bound_admission_fences_provider_and_endpoint_mutation(tmp_path) -> None:
    store = SQLiteProviderConfigStore(tmp_path / "fence.sqlite")
    profile = make_profile()
    endpoint = ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1")
    store.save_endpoint(endpoint)
    store.save_provider(profile)
    admission = store.acquire_admission(
        provider_id=profile.provider_id, execution_id="exec-fence", batch_id="batch-fence",
        expected_max_concurrency=1, now=NOW, ttl_seconds=600,
        expected_configuration_generation=1,
    )
    assert admission.kind is ProviderAdmissionKind.ADMITTED
    with pytest.raises(ProviderConfigStoreError) as profile_busy:
        store.save_provider(
            ProviderConfiguration(**{**profile.as_dict(), "display_name": "must-wait"}),
            expected_generation=1,
        )
    assert profile_busy.value.code == "PROVIDER_CONFIGURATION_IN_USE"
    with pytest.raises(ProviderConfigStoreError) as endpoint_busy:
        store.save_endpoint(
            ProviderEndpointConfig(profile.endpoint_ref, "https://new.example.test/v1"),
            expected_generation=1,
        )
    assert endpoint_busy.value.code == "PROVIDER_CONFIGURATION_IN_USE"
    record = admission.admission
    assert record is not None
    store.release_admission(
        record.admission_id, provider_id=profile.provider_id, execution_id="exec-fence",
        batch_id="batch-fence", now=NOW + timedelta(seconds=1),
    )
    assert store.save_provider(
        ProviderConfiguration(**{**profile.as_dict(), "display_name": "after-release"}),
        expected_generation=1,
    ) == 2


def test_validate_admission_fence_requires_exact_active_unexpired_generation(tmp_path) -> None:
    store = SQLiteProviderConfigStore(tmp_path / "validate-fence.sqlite")
    profile = make_profile()
    store.save_endpoint(ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1"))
    store.save_provider(profile)
    acquired = store.acquire_admission(
        provider_id=profile.provider_id, execution_id="exec-validate", batch_id="batch-validate",
        expected_max_concurrency=1, now=NOW, ttl_seconds=600,
        expected_configuration_generation=1,
    )
    record = acquired.admission
    assert record is not None
    validated = store.validate_admission_fence(
        record.admission_id, provider_id=profile.provider_id, execution_id="exec-validate",
        batch_id="batch-validate", expected_configuration_generation=1, now=NOW,
    )
    assert validated == record
    with pytest.raises(ProviderConfigStoreError) as wrong_generation:
        store.validate_admission_fence(
            record.admission_id, provider_id=profile.provider_id, execution_id="exec-validate",
            batch_id="batch-validate", expected_configuration_generation=2, now=NOW,
        )
    assert wrong_generation.value.code == "PROVIDER_ADMISSION_GENERATION_STALE"
    with pytest.raises(ProviderConfigStoreError) as expired:
        store.validate_admission_fence(
            record.admission_id, provider_id=profile.provider_id, execution_id="exec-validate",
            batch_id="batch-validate", expected_configuration_generation=1,
            now=NOW + timedelta(seconds=601),
        )
    assert expired.value.code == "PROVIDER_ADMISSION_EXPIRED_RECONCILE"
