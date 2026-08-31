"""SQLite persistence for non-secret provider configuration and observations.

The store shares the existing control SQLite file by path. It never resolves
credential references and has no columns for raw credential values.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, Iterator

from .provider_configuration import (
    ProviderConfiguration,
    ProviderEndpointConfig,
    ProviderObservation,
)


class ProviderConfigStoreError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ProviderAdmissionKind(str, Enum):
    ADMITTED = "ADMITTED"
    CAPACITY_WAIT = "CAPACITY_WAIT"
    EXISTING = "EXISTING"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


@dataclass(frozen=True, slots=True)
class ProviderAdmissionRecord:
    admission_id: str
    provider_id: str
    execution_id: str
    batch_id: str
    acquired_at: datetime
    expires_at: datetime
    status: str
    released_at: datetime | None = None
    reconciled_at: datetime | None = None
    configuration_generation: int | None = None


@dataclass(frozen=True, slots=True)
class ProviderAdmissionResult:
    kind: ProviderAdmissionKind
    reason_code: str
    admission: ProviderAdmissionRecord | None = None


@dataclass(frozen=True, slots=True)
class ProviderConfigurationSnapshot:
    """One consistent provider read: profile, endpoint, generation, observation."""

    profile: ProviderConfiguration
    endpoint: ProviderEndpointConfig | None
    generation: int | None
    observation: ProviderObservation | None


class SQLiteProviderConfigStore:
    def __init__(self, database_path: str | Path, *, admission_id_factory: Callable[[], str] | None = None) -> None:
        self.database_path = Path(database_path)
        self._admission_id_factory = admission_id_factory or (lambda: f'provider-admission-{uuid.uuid4().hex}')

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
                        enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
                        generation INTEGER
                    );

                    CREATE TABLE IF NOT EXISTS provider_endpoints (
                        endpoint_ref TEXT PRIMARY KEY,
                        base_url TEXT NOT NULL,
                        generation INTEGER
                    );

                    CREATE TABLE IF NOT EXISTS provider_observations (
                        provider_id TEXT PRIMARY KEY,
                        schema_version TEXT NOT NULL,
                        health TEXT NOT NULL,
                        observed_at TEXT NOT NULL,
                        provenance TEXT NOT NULL,
                        latency_ms INTEGER,
                        quota_json TEXT,
                        configuration_generation INTEGER
                    );

                    CREATE TABLE IF NOT EXISTS provider_admissions (
                        admission_id TEXT PRIMARY KEY,
                        provider_id TEXT NOT NULL,
                        execution_id TEXT NOT NULL,
                        batch_id TEXT NOT NULL,
                        acquired_at TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'RELEASED', 'EXPIRED')),
                        released_at TEXT,
                        reconciled_at TEXT,
                        configuration_generation INTEGER,
                        UNIQUE(provider_id, execution_id),
                        FOREIGN KEY(provider_id) REFERENCES provider_configurations(provider_id)
                    );
                    CREATE INDEX IF NOT EXISTS idx_provider_admissions_active
                    ON provider_admissions(provider_id, status, expires_at);
                    """
                )
                # Conservative in-place migration for installed databases created
                # before generations existed: existing rows become generation 1;
                # legacy observations/admissions keep NULL (unknown) generations.
                for table in (
                    "provider_configurations",
                    "provider_endpoints",
                    "provider_observations",
                    "provider_admissions",
                ):
                    columns = {
                        row["name"]
                        for row in connection.execute(f"PRAGMA table_info({table})")
                    }
                    column = "configuration_generation" if table in (
                        "provider_observations", "provider_admissions",
                    ) else "generation"
                    if column not in columns:
                        connection.execute(
                            f"ALTER TABLE {table} ADD COLUMN {column} INTEGER"
                        )
                connection.execute(
                    "UPDATE provider_configurations SET generation=1 "
                    "WHERE generation IS NULL OR generation < 1"
                )
                connection.execute(
                    "UPDATE provider_endpoints SET generation=1 "
                    "WHERE generation IS NULL OR generation < 1"
                )
                connection.commit()
            except sqlite3.Error as exc:
                connection.rollback()
                raise ProviderConfigStoreError("CONFIG_STORE_INITIALIZE_FAILED") from exc

    @staticmethod
    def _validated_expected_generation(value: int | None) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError("expected generation must be a positive integer or None")
        return value

    def save_endpoint(
        self,
        endpoint: ProviderEndpointConfig,
        *,
        expected_generation: int | None = None,
    ) -> int:
        """Insert or CAS-update one endpoint; returns the stored generation.

        A successful endpoint update atomically increments the generation of
        every provider profile referencing the endpoint, so provider
        generation always reflects the exact effective profile+endpoint
        configuration. Wall-clock time is never generation authority.
        """
        if not isinstance(endpoint, ProviderEndpointConfig):
            raise ValueError("endpoint must be ProviderEndpointConfig")
        expected = self._validated_expected_generation(expected_generation)
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT generation FROM provider_endpoints WHERE endpoint_ref = ?",
                    (endpoint.endpoint_ref,),
                ).fetchone()
                if row is None:
                    connection.execute(
                        "INSERT INTO provider_endpoints(endpoint_ref, base_url, generation) "
                        "VALUES(?, ?, 1)",
                        (endpoint.endpoint_ref, endpoint.base_url),
                    )
                    connection.commit()
                    return 1
                current = row["generation"]
                if current is None or int(current) < 1:
                    connection.rollback()
                    raise ProviderConfigStoreError("PROVIDER_GENERATION_INVALID")
                if expected is None:
                    connection.rollback()
                    raise ProviderConfigStoreError("PROVIDER_GENERATION_EXPECTED")
                if int(expected) != int(current):
                    connection.rollback()
                    raise ProviderConfigStoreError("PROVIDER_GENERATION_STALE")
                connection.execute(
                    "UPDATE provider_endpoints SET base_url=?, generation=generation+1 "
                    "WHERE endpoint_ref=? AND generation=?",
                    (endpoint.base_url, endpoint.endpoint_ref, int(current)),
                )
                connection.execute(
                    "UPDATE provider_configurations SET generation=generation+1 "
                    "WHERE endpoint_ref=?",
                    (endpoint.endpoint_ref,),
                )
                updated = connection.execute(
                    "SELECT generation FROM provider_endpoints WHERE endpoint_ref = ?",
                    (endpoint.endpoint_ref,),
                ).fetchone()
                connection.commit()
                return int(updated["generation"])
            except ProviderConfigStoreError:
                connection.rollback()
                raise
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

    def save_provider(
        self,
        profile: ProviderConfiguration,
        *,
        expected_generation: int | None = None,
    ) -> int:
        """Insert or CAS-update one provider profile; returns the stored generation.

        Insert establishes generation 1. Updating an existing row requires the
        caller's expected generation to equal the stored generation; stale or
        missing expectations fail typed instead of silently overwriting a
        newer configuration.
        """
        if not isinstance(profile, ProviderConfiguration):
            raise ValueError("profile must be ProviderConfiguration")
        expected = self._validated_expected_generation(expected_generation)
        self.initialize()
        payload = profile.as_dict()
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT generation FROM provider_configurations WHERE provider_id = ?",
                    (profile.provider_id,),
                ).fetchone()
                if row is None:
                    connection.execute(
                        """
                        INSERT INTO provider_configurations(
                            provider_id, schema_version, display_name, provider_type,
                            protocol_family, endpoint_ref, credential_ref, trust_class,
                            egress_boundary, harness_strategies_json, max_concurrency,
                            models_json, enabled, generation
                        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
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
                    return 1
                current = row["generation"]
                if current is None or int(current) < 1:
                    connection.rollback()
                    raise ProviderConfigStoreError("PROVIDER_GENERATION_INVALID")
                if expected is None:
                    connection.rollback()
                    raise ProviderConfigStoreError("PROVIDER_GENERATION_EXPECTED")
                if int(expected) != int(current):
                    connection.rollback()
                    raise ProviderConfigStoreError("PROVIDER_GENERATION_STALE")
                connection.execute(
                    """
                    UPDATE provider_configurations SET
                        schema_version=?, display_name=?, provider_type=?,
                        protocol_family=?, endpoint_ref=?, credential_ref=?, trust_class=?,
                        egress_boundary=?, harness_strategies_json=?, max_concurrency=?,
                        models_json=?, enabled=?, generation=generation+1
                    WHERE provider_id=? AND generation=?
                    """,
                    (
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
                        profile.provider_id,
                        int(current),
                    ),
                )
                updated = connection.execute(
                    "SELECT generation FROM provider_configurations WHERE provider_id = ?",
                    (profile.provider_id,),
                ).fetchone()
                connection.commit()
                return int(updated["generation"])
            except ProviderConfigStoreError:
                connection.rollback()
                raise
            except sqlite3.Error as exc:
                connection.rollback()
                raise ProviderConfigStoreError("CONFIG_STORE_WRITE_FAILED") from exc

    @staticmethod
    def _profile_from_row(row: sqlite3.Row) -> ProviderConfiguration:
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

    @staticmethod
    def _observation_from_row(row: sqlite3.Row) -> ProviderObservation:
        quota = None if row["quota_json"] is None else json.loads(row["quota_json"])
        generation = row["configuration_generation"]
        return ProviderObservation(
            provider_id=row["provider_id"],
            health=row["health"],
            observed_at=row["observed_at"],
            provenance=row["provenance"],
            latency_ms=row["latency_ms"],
            quota=quota,
            schema_version=row["schema_version"],
            configuration_generation=None if generation is None else int(generation),
        )

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
        return self._profile_from_row(row)

    def save_observation(self, observation: ProviderObservation) -> None:
        """Persist one observation bound to its exact configuration generation.

        The observation must carry a positive generation that matches the
        provider's current generation inside the same write transaction, so a
        probe that started before a configuration edit can never publish its
        result as current-valid evidence for the newer configuration.
        """
        if not isinstance(observation, ProviderObservation):
            raise ValueError("observation must be ProviderObservation")
        if observation.configuration_generation is None:
            raise ValueError("observation.configuration_generation must be positive")
        self.initialize()
        payload = observation.as_dict()
        quota_json = (
            None
            if payload["quota"] is None
            else json.dumps(payload["quota"], separators=(",", ":"))
        )
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                provider = connection.execute(
                    "SELECT generation FROM provider_configurations WHERE provider_id = ?",
                    (observation.provider_id,),
                ).fetchone()
                if provider is None:
                    connection.rollback()
                    raise ProviderConfigStoreError("PROVIDER_OBSERVATION_PROVIDER_NOT_FOUND")
                current = provider["generation"]
                if current is None or int(current) < 1:
                    connection.rollback()
                    raise ProviderConfigStoreError("PROVIDER_GENERATION_INVALID")
                if int(observation.configuration_generation) != int(current):
                    connection.rollback()
                    raise ProviderConfigStoreError("PROVIDER_OBSERVATION_GENERATION_STALE")
                connection.execute(
                    """
                    INSERT INTO provider_observations(
                        provider_id, schema_version, health, observed_at,
                        provenance, latency_ms, quota_json, configuration_generation
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(provider_id) DO UPDATE SET
                        schema_version=excluded.schema_version,
                        health=excluded.health,
                        observed_at=excluded.observed_at,
                        provenance=excluded.provenance,
                        latency_ms=excluded.latency_ms,
                        quota_json=excluded.quota_json,
                        configuration_generation=excluded.configuration_generation
                    """,
                    (
                        observation.provider_id,
                        observation.schema_version,
                        observation.health.value,
                        payload["observed_at"],
                        observation.provenance,
                        observation.latency_ms,
                        quota_json,
                        int(observation.configuration_generation),
                    ),
                )
                connection.commit()
            except ProviderConfigStoreError:
                connection.rollback()
                raise
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
        generation = row["configuration_generation"]
        return ProviderObservation(
            provider_id=row["provider_id"],
            health=row["health"],
            observed_at=row["observed_at"],
            provenance=row["provenance"],
            latency_ms=row["latency_ms"],
            quota=quota,
            schema_version=row["schema_version"],
            configuration_generation=None if generation is None else int(generation),
        )

    def load_provider_snapshot(self, provider_id: str) -> "ProviderConfigurationSnapshot | None":
        """Read profile, endpoint, current generation and latest observation together.

        One typed store snapshot under one read transaction; callers must not
        reconstruct authoritative snapshots from separate reads.
        """
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError("provider_id must not be blank")
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute("BEGIN")
                profile_row = connection.execute(
                    "SELECT * FROM provider_configurations WHERE provider_id = ?",
                    (provider_id.strip(),),
                ).fetchone()
                endpoint_row = None
                observation_row = None
                generation: int | None = None
                profile = None
                if profile_row is not None:
                    raw_generation = profile_row["generation"]
                    generation = None if raw_generation is None else int(raw_generation)
                    endpoint_row = connection.execute(
                        "SELECT * FROM provider_endpoints WHERE endpoint_ref = ?",
                        (profile_row["endpoint_ref"],),
                    ).fetchone()
                    observation_row = connection.execute(
                        "SELECT * FROM provider_observations WHERE provider_id = ?",
                        (profile_row["provider_id"],),
                    ).fetchone()
                    profile = self._profile_from_row(profile_row)
                connection.commit()
            except sqlite3.Error as exc:
                connection.rollback()
                raise ProviderConfigStoreError("CONFIG_STORE_READ_FAILED") from exc
        if profile is None:
            return None
        endpoint = (
            None
            if endpoint_row is None
            else ProviderEndpointConfig(
                endpoint_row["endpoint_ref"], endpoint_row["base_url"]
            )
        )
        observation = None if observation_row is None else self._observation_from_row(
            observation_row
        )
        return ProviderConfigurationSnapshot(
            profile=profile,
            endpoint=endpoint,
            generation=generation,
            observation=observation,
        )

    @staticmethod
    def _require_admission_text(value: str, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must not be blank")
        return value

    @staticmethod
    def _require_admission_time(value: datetime, field_name: str) -> datetime:
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field_name} must be timezone-aware datetime")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _format_time(value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _parse_time(value: str | None) -> datetime | None:
        if value is None:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (AttributeError, TypeError, ValueError) as exc:
            raise ProviderConfigStoreError("PROVIDER_ADMISSION_RECORD_INVALID") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ProviderConfigStoreError("PROVIDER_ADMISSION_RECORD_INVALID")
        return parsed.astimezone(timezone.utc)

    @classmethod
    def _admission_from_row(cls, row: sqlite3.Row) -> ProviderAdmissionRecord:
        acquired_at = cls._parse_time(row["acquired_at"])
        expires_at = cls._parse_time(row["expires_at"])
        if acquired_at is None or expires_at is None:
            raise ProviderConfigStoreError("PROVIDER_ADMISSION_RECORD_INVALID")
        return ProviderAdmissionRecord(
            admission_id=row["admission_id"],
            provider_id=row["provider_id"],
            execution_id=row["execution_id"],
            batch_id=row["batch_id"],
            acquired_at=acquired_at,
            expires_at=expires_at,
            status=row["status"],
            released_at=cls._parse_time(row["released_at"]),
            reconciled_at=cls._parse_time(row["reconciled_at"]),
            configuration_generation=(
                None
                if row["configuration_generation"] is None
                else int(row["configuration_generation"])
            ),
        )

    def _next_admission_id(self) -> str:
        try:
            value = self._admission_id_factory()
        except Exception as exc:
            raise ProviderConfigStoreError("PROVIDER_ADMISSION_ID_FAILED") from exc
        return self._require_admission_text(value, "admission_id")

    def acquire_admission(
        self,
        *,
        provider_id: str,
        execution_id: str,
        batch_id: str,
        expected_max_concurrency: int,
        now: datetime,
        ttl_seconds: int,
        expected_configuration_generation: int | None = None,
    ) -> ProviderAdmissionResult:
        """Acquire capacity atomically; callers must supply reasonably synchronized UTC clocks.

        Clock skew can conservatively retain capacity longer, but must never be used to
        justify over-admission or replay. Expiry is reconciled from validated UTC values.
        ``expected_configuration_generation`` (optional for current callers) is
        validated against the provider's current generation inside this same
        transaction before capacity is granted; a stale expectation fails
        closed without consuming or releasing unrelated capacity. A prior
        admission whose persisted generation is unknown or mismatched is typed
        recovery, never EXISTING/ADMITTED.
        """
        provider_id = self._require_admission_text(provider_id, "provider_id")
        execution_id = self._require_admission_text(execution_id, "execution_id")
        batch_id = self._require_admission_text(batch_id, "batch_id")
        if isinstance(expected_max_concurrency, bool) or not isinstance(expected_max_concurrency, int) or not 1 <= expected_max_concurrency <= 64:
            raise ValueError("expected_max_concurrency must be between 1 and 64")
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or ttl_seconds < 1:
            raise ValueError("ttl_seconds must be >= 1")
        expected_generation = self._validated_expected_generation(
            expected_configuration_generation
        )
        now = self._require_admission_time(now, "now")
        expires_at = now + timedelta(seconds=ttl_seconds)
        now_text = self._format_time(now)
        expires_text = self._format_time(expires_at)
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                profile = connection.execute(
                    "SELECT max_concurrency, enabled, generation FROM provider_configurations WHERE provider_id = ?",
                    (provider_id,),
                ).fetchone()
                if profile is None:
                    raise ProviderConfigStoreError("PROVIDER_ADMISSION_PROVIDER_NOT_FOUND")
                if int(profile["max_concurrency"]) != expected_max_concurrency:
                    raise ProviderConfigStoreError("PROVIDER_ADMISSION_PROFILE_DRIFT")
                if not bool(profile["enabled"]):
                    raise ProviderConfigStoreError("PROVIDER_ADMISSION_PROVIDER_DISABLED")
                current_generation = profile["generation"]
                if current_generation is None or int(current_generation) < 1:
                    raise ProviderConfigStoreError("PROVIDER_GENERATION_INVALID")
                if (
                    expected_generation is not None
                    and int(expected_generation) != int(current_generation)
                ):
                    raise ProviderConfigStoreError("PROVIDER_ADMISSION_GENERATION_STALE")
                active_rows = connection.execute(
                    "SELECT * FROM provider_admissions WHERE provider_id=? AND status IN ('ACTIVE','EXPIRED')",
                    (provider_id,),
                ).fetchall()
                active_records = tuple(self._admission_from_row(row) for row in active_rows)
                prior = connection.execute(
                    "SELECT * FROM provider_admissions WHERE provider_id=? AND execution_id=?",
                    (provider_id, execution_id),
                ).fetchone()
                if prior is not None:
                    record = self._admission_from_row(prior)
                    if record.batch_id != batch_id:
                        connection.commit()
                        return ProviderAdmissionResult(
                            ProviderAdmissionKind.RECOVERY_REQUIRED,
                            "PROVIDER_ADMISSION_BATCH_DRIFT",
                            record,
                        )
                    connection.commit()
                    if (
                        record.configuration_generation is None
                        and expected_generation is not None
                    ):
                        return ProviderAdmissionResult(
                            ProviderAdmissionKind.RECOVERY_REQUIRED,
                            "PROVIDER_ADMISSION_GENERATION_RECONCILE",
                            record,
                        )
                    if (
                        expected_generation is not None
                        and record.configuration_generation != expected_generation
                    ):
                        return ProviderAdmissionResult(
                            ProviderAdmissionKind.RECOVERY_REQUIRED,
                            "PROVIDER_ADMISSION_GENERATION_RECONCILE",
                            record,
                        )
                    if record.status == "EXPIRED" or (record.status == "ACTIVE" and record.expires_at <= now):
                        return ProviderAdmissionResult(
                            ProviderAdmissionKind.RECOVERY_REQUIRED,
                            "PROVIDER_ADMISSION_EXPIRED_RECONCILE",
                            record,
                        )
                    kind = ProviderAdmissionKind.EXISTING if record.status == "ACTIVE" else ProviderAdmissionKind.RECOVERY_REQUIRED
                    reason = "PROVIDER_ADMISSION_ALREADY_ACTIVE" if record.status == "ACTIVE" else "PROVIDER_ADMISSION_TERMINAL_RECONCILE"
                    return ProviderAdmissionResult(kind, reason, record)
                active = len(active_records)
                if active >= expected_max_concurrency:
                    stale = next((record for record in active_records if record.status == "EXPIRED" or record.expires_at <= now), None)
                    connection.commit()
                    if stale is not None:
                        return ProviderAdmissionResult(
                            ProviderAdmissionKind.RECOVERY_REQUIRED,
                            "PROVIDER_ADMISSION_EXPIRED_RECONCILE",
                            stale,
                        )
                    return ProviderAdmissionResult(
                        ProviderAdmissionKind.CAPACITY_WAIT,
                        "PROVIDER_CAPACITY_EXHAUSTED",
                    )
                admission_id = self._next_admission_id()
                connection.execute(
                    "INSERT INTO provider_admissions(admission_id, provider_id, execution_id, batch_id, acquired_at, expires_at, status, configuration_generation) "
                    "VALUES(?, ?, ?, ?, ?, ?, 'ACTIVE', ?)",
                    (admission_id, provider_id, execution_id, batch_id, now_text, expires_text, expected_generation),
                )
                row = connection.execute(
                    "SELECT * FROM provider_admissions WHERE admission_id=?",
                    (admission_id,),
                ).fetchone()
                connection.commit()
                return ProviderAdmissionResult(
                    ProviderAdmissionKind.ADMITTED,
                    "PROVIDER_ADMITTED",
                    self._admission_from_row(row),
                )
            except ProviderConfigStoreError:
                connection.rollback()
                raise
            except sqlite3.IntegrityError as exc:
                connection.rollback()
                raise ProviderConfigStoreError("PROVIDER_ADMISSION_CONFLICT") from exc
            except sqlite3.Error as exc:
                connection.rollback()
                raise ProviderConfigStoreError("CONFIG_STORE_WRITE_FAILED") from exc

    def get_admission(self, admission_id: str) -> ProviderAdmissionRecord | None:
        admission_id = self._require_admission_text(admission_id, "admission_id")
        self.initialize()
        with self._connect() as connection:
            try:
                row = connection.execute(
                    "SELECT * FROM provider_admissions WHERE admission_id=?",
                    (admission_id,),
                ).fetchone()
            except sqlite3.Error as exc:
                raise ProviderConfigStoreError("CONFIG_STORE_READ_FAILED") from exc
        return None if row is None else self._admission_from_row(row)

    def release_admission(
        self,
        admission_id: str,
        *,
        provider_id: str,
        execution_id: str,
        batch_id: str,
        now: datetime,
    ) -> ProviderAdmissionRecord:
        admission_id = self._require_admission_text(admission_id, "admission_id")
        provider_id = self._require_admission_text(provider_id, "provider_id")
        execution_id = self._require_admission_text(execution_id, "execution_id")
        batch_id = self._require_admission_text(batch_id, "batch_id")
        now = self._require_admission_time(now, "now")
        now_text = self._format_time(now)
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT * FROM provider_admissions WHERE admission_id=?",
                    (admission_id,),
                ).fetchone()
                if row is None:
                    raise ProviderConfigStoreError("PROVIDER_ADMISSION_NOT_FOUND")
                record = self._admission_from_row(row)
                if (record.provider_id, record.execution_id, record.batch_id) != (provider_id, execution_id, batch_id):
                    raise ProviderConfigStoreError("PROVIDER_ADMISSION_IDENTITY_MISMATCH")
                if record.status not in {"ACTIVE", "EXPIRED"}:
                    raise ProviderConfigStoreError("PROVIDER_ADMISSION_NOT_ACTIVE")
                connection.execute(
                    "UPDATE provider_admissions SET status='RELEASED', released_at=?, reconciled_at=? WHERE admission_id=? AND status IN ('ACTIVE','EXPIRED')",
                    (now_text, now_text, admission_id),
                )
                updated = connection.execute(
                    "SELECT * FROM provider_admissions WHERE admission_id=?",
                    (admission_id,),
                ).fetchone()
                connection.commit()
                return self._admission_from_row(updated)
            except ProviderConfigStoreError:
                connection.rollback()
                raise
            except sqlite3.Error as exc:
                connection.rollback()
                raise ProviderConfigStoreError("CONFIG_STORE_WRITE_FAILED") from exc
