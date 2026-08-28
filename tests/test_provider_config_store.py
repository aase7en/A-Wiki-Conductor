from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from a_conductor.provider_config_store import SQLiteProviderConfigStore
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
        ):
            columns.extend(row[1].lower() for row in connection.execute(f"PRAGMA table_info({table})"))
    forbidden = ("api_key", "token_value", "password", "secret_value", "authorization")
    assert not [name for name in columns if any(item in name for item in forbidden)]
