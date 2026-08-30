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


@dataclass(frozen=True, slots=True)
class ProviderAdmissionResult:
    kind: ProviderAdmissionKind
    reason_code: str
    admission: ProviderAdmissionRecord | None = None


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
                        UNIQUE(provider_id, execution_id),
                        FOREIGN KEY(provider_id) REFERENCES provider_configurations(provider_id)
                    );
                    CREATE INDEX IF NOT EXISTS idx_provider_admissions_active
                    ON provider_admissions(provider_id, status, expires_at);
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
    ) -> ProviderAdmissionResult:
        """Acquire capacity atomically; callers must supply reasonably synchronized UTC clocks.

        Clock skew can conservatively retain capacity longer, but must never be used to
        justify over-admission or replay. Expiry is reconciled from validated UTC values.
        """
        provider_id = self._require_admission_text(provider_id, "provider_id")
        execution_id = self._require_admission_text(execution_id, "execution_id")
        batch_id = self._require_admission_text(batch_id, "batch_id")
        if isinstance(expected_max_concurrency, bool) or not isinstance(expected_max_concurrency, int) or not 1 <= expected_max_concurrency <= 64:
            raise ValueError("expected_max_concurrency must be between 1 and 64")
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or ttl_seconds < 1:
            raise ValueError("ttl_seconds must be >= 1")
        now = self._require_admission_time(now, "now")
        expires_at = now + timedelta(seconds=ttl_seconds)
        now_text = self._format_time(now)
        expires_text = self._format_time(expires_at)
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                profile = connection.execute(
                    "SELECT max_concurrency, enabled FROM provider_configurations WHERE provider_id = ?",
                    (provider_id,),
                ).fetchone()
                if profile is None:
                    raise ProviderConfigStoreError("PROVIDER_ADMISSION_PROVIDER_NOT_FOUND")
                if int(profile["max_concurrency"]) != expected_max_concurrency:
                    raise ProviderConfigStoreError("PROVIDER_ADMISSION_PROFILE_DRIFT")
                if not bool(profile["enabled"]):
                    raise ProviderConfigStoreError("PROVIDER_ADMISSION_PROVIDER_DISABLED")
                active_rows = connection.execute(
                    "SELECT * FROM provider_admissions WHERE provider_id=? AND status='ACTIVE'",
                    (provider_id,),
                ).fetchall()
                active_records = tuple(self._admission_from_row(row) for row in active_rows)
                expired_ids = tuple(
                    record.admission_id for record in active_records if record.expires_at <= now
                )
                if expired_ids:
                    connection.executemany(
                        "UPDATE provider_admissions SET status='EXPIRED', reconciled_at=? "
                        "WHERE admission_id=? AND status='ACTIVE'",
                        ((now_text, admission_id) for admission_id in expired_ids),
                    )
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
                    kind = ProviderAdmissionKind.EXISTING if record.status == "ACTIVE" else ProviderAdmissionKind.RECOVERY_REQUIRED
                    reason = "PROVIDER_ADMISSION_ALREADY_ACTIVE" if record.status == "ACTIVE" else "PROVIDER_ADMISSION_TERMINAL_RECONCILE"
                    return ProviderAdmissionResult(kind, reason, record)
                active = sum(record.expires_at > now for record in active_records)
                if active >= expected_max_concurrency:
                    connection.commit()
                    return ProviderAdmissionResult(
                        ProviderAdmissionKind.CAPACITY_WAIT,
                        "PROVIDER_CAPACITY_EXHAUSTED",
                    )
                admission_id = self._next_admission_id()
                connection.execute(
                    "INSERT INTO provider_admissions(admission_id, provider_id, execution_id, batch_id, acquired_at, expires_at, status) "
                    "VALUES(?, ?, ?, ?, ?, ?, 'ACTIVE')",
                    (admission_id, provider_id, execution_id, batch_id, now_text, expires_text),
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
                if record.status != "ACTIVE":
                    raise ProviderConfigStoreError("PROVIDER_ADMISSION_NOT_ACTIVE")
                connection.execute(
                    "UPDATE provider_admissions SET status='RELEASED', released_at=?, reconciled_at=? WHERE admission_id=? AND status='ACTIVE'",
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
