"""SQLite persistence for non-secret provider configuration and observations.

The store shares the existing control SQLite file by path. It never resolves
credential references and has no columns for raw credential values.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .provider_configuration import (
    ProviderConfiguration,
    ProviderEndpointConfig,
    ProviderObservation,
)


class ProviderConfigStoreError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class SQLiteProviderConfigStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.database_path)
        except (OSError, sqlite3.Error) as exc:
            raise ProviderConfigStoreError("CONFIG_STORE_UNAVAILABLE") from exc
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
                    CREATE TABLE IF NOT EXISTS provider_configurations (
                        provider_id TEXT PRIMARY KEY,
                        schema_version TEXT NOT NULL,
                        display_name TEXT NOT NULL,
                        provider_type TEXT NOT NULL,
                        protocol_family TEXT NOT NULL,
                        endpoint_ref TEXT NOT NULL,
                        credential_ref TEXT NOT NULL,
                        trust_class TEXT NOT NULL,
                        egress_boundary TEXT NOT NULL,
                        harness_strategies_json TEXT NOT NULL,
                        max_concurrency INTEGER NOT NULL CHECK (max_concurrency BETWEEN 1 AND 64),
                        models_json TEXT NOT NULL,
                        enabled INTEGER NOT NULL CHECK (enabled IN (0, 1))
                    );

                    CREATE TABLE IF NOT EXISTS provider_endpoints (
                        endpoint_ref TEXT PRIMARY KEY,
                        base_url TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS provider_observations (
                        provider_id TEXT PRIMARY KEY,
                        schema_version TEXT NOT NULL,
                        health TEXT NOT NULL,
                        observed_at TEXT NOT NULL,
                        provenance TEXT NOT NULL,
                        latency_ms INTEGER,
                        quota_json TEXT
                    );
                    """
                )
                connection.commit()
            except sqlite3.Error as exc:
                connection.rollback()
                raise ProviderConfigStoreError("CONFIG_STORE_INITIALIZE_FAILED") from exc

    def save_endpoint(self, endpoint: ProviderEndpointConfig) -> None:
        if not isinstance(endpoint, ProviderEndpointConfig):
            raise ValueError("endpoint must be ProviderEndpointConfig")
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO provider_endpoints(endpoint_ref, base_url)
                    VALUES(?, ?)
                    ON CONFLICT(endpoint_ref) DO UPDATE SET
                        base_url=excluded.base_url
                    """,
                    (endpoint.endpoint_ref, endpoint.base_url),
                )
                connection.commit()
            except sqlite3.Error as exc:
                connection.rollback()
                raise ProviderConfigStoreError("CONFIG_STORE_WRITE_FAILED") from exc

    def get_endpoint(self, endpoint_ref: str) -> ProviderEndpointConfig | None:
        self.initialize()
        with self._connect() as connection:
            try:
                row = connection.execute(
                    "SELECT endpoint_ref, base_url FROM provider_endpoints WHERE endpoint_ref = ?",
                    (endpoint_ref,),
                ).fetchone()
            except sqlite3.Error as exc:
                raise ProviderConfigStoreError("CONFIG_STORE_READ_FAILED") from exc
        if row is None:
            return None
        return ProviderEndpointConfig(row["endpoint_ref"], row["base_url"])

    def save_provider(self, profile: ProviderConfiguration) -> None:
        if not isinstance(profile, ProviderConfiguration):
            raise ValueError("profile must be ProviderConfiguration")
        self.initialize()
        payload = profile.as_dict()
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO provider_configurations(
                        provider_id, schema_version, display_name, provider_type,
                        protocol_family, endpoint_ref, credential_ref, trust_class,
                        egress_boundary, harness_strategies_json, max_concurrency,
                        models_json, enabled
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(provider_id) DO UPDATE SET
                        schema_version=excluded.schema_version,
                        display_name=excluded.display_name,
                        provider_type=excluded.provider_type,
                        protocol_family=excluded.protocol_family,
                        endpoint_ref=excluded.endpoint_ref,
                        credential_ref=excluded.credential_ref,
                        trust_class=excluded.trust_class,
                        egress_boundary=excluded.egress_boundary,
                        harness_strategies_json=excluded.harness_strategies_json,
                        max_concurrency=excluded.max_concurrency,
                        models_json=excluded.models_json,
                        enabled=excluded.enabled
                    """,
                    (
                        profile.provider_id,
                        profile.schema_version,
                        profile.display_name,
                        profile.provider_type,
                        profile.protocol_family.value,
                        profile.endpoint_ref,
                        profile.credential_ref,
                        profile.trust_class.value,
                        profile.egress_boundary.value,
                        json.dumps(payload["harness_strategies"], separators=(",", ":")),
                        profile.max_concurrency,
                        json.dumps(payload["models"], separators=(",", ":")),
                        int(profile.enabled),
                    ),
                )
                connection.commit()
            except sqlite3.Error as exc:
                connection.rollback()
                raise ProviderConfigStoreError("CONFIG_STORE_WRITE_FAILED") from exc

    def get_provider(self, provider_id: str) -> ProviderConfiguration | None:
        self.initialize()
        with self._connect() as connection:
            try:
                row = connection.execute(
                    "SELECT * FROM provider_configurations WHERE provider_id = ?",
                    (provider_id,),
                ).fetchone()
            except sqlite3.Error as exc:
                raise ProviderConfigStoreError("CONFIG_STORE_READ_FAILED") from exc
        if row is None:
            return None
        return ProviderConfiguration(
            provider_id=row["provider_id"],
            display_name=row["display_name"],
            provider_type=row["provider_type"],
            protocol_family=row["protocol_family"],
            endpoint_ref=row["endpoint_ref"],
            credential_ref=row["credential_ref"],
            trust_class=row["trust_class"],
            egress_boundary=row["egress_boundary"],
            harness_strategies=tuple(json.loads(row["harness_strategies_json"])),
            max_concurrency=row["max_concurrency"],
            models=tuple(json.loads(row["models_json"])),
            enabled=bool(row["enabled"]),
            schema_version=row["schema_version"],
        )

    def save_observation(self, observation: ProviderObservation) -> None:
        if not isinstance(observation, ProviderObservation):
            raise ValueError("observation must be ProviderObservation")
        self.initialize()
        payload = observation.as_dict()
        quota_json = (
            None
            if payload["quota"] is None
            else json.dumps(payload["quota"], separators=(",", ":"))
        )
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO provider_observations(
                        provider_id, schema_version, health, observed_at,
                        provenance, latency_ms, quota_json
                    ) VALUES(?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(provider_id) DO UPDATE SET
                        schema_version=excluded.schema_version,
                        health=excluded.health,
                        observed_at=excluded.observed_at,
                        provenance=excluded.provenance,
                        latency_ms=excluded.latency_ms,
                        quota_json=excluded.quota_json
                    """,
                    (
                        observation.provider_id,
                        observation.schema_version,
                        observation.health.value,
                        payload["observed_at"],
                        observation.provenance,
                        observation.latency_ms,
                        quota_json,
                    ),
                )
                connection.commit()
            except sqlite3.Error as exc:
                connection.rollback()
                raise ProviderConfigStoreError("CONFIG_STORE_WRITE_FAILED") from exc

    def get_observation(self, provider_id: str) -> ProviderObservation | None:
        self.initialize()
        with self._connect() as connection:
            try:
                row = connection.execute(
                    "SELECT * FROM provider_observations WHERE provider_id = ?",
                    (provider_id,),
                ).fetchone()
            except sqlite3.Error as exc:
                raise ProviderConfigStoreError("CONFIG_STORE_READ_FAILED") from exc
        if row is None:
            return None
        quota = None if row["quota_json"] is None else json.loads(row["quota_json"])
        return ProviderObservation(
            provider_id=row["provider_id"],
            health=row["health"],
            observed_at=row["observed_at"],
            provenance=row["provenance"],
            latency_ms=row["latency_ms"],
            quota=quota,
            schema_version=row["schema_version"],
        )
