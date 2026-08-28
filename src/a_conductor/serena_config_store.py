"""Durable non-secret Serena runtime configuration metadata.

This store deliberately persists opaque reference IDs and local reference file
paths only. It never opens reference files and has no columns for token/API/
credential values.
"""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .connector_recovery import ConnectorRecoveryRecord, ConnectorRecoveryState
from .serena_runtime import (
    ProjectIdentityPolicy,
    SerenaProjectBinding,
    SerenaWorkerConfig,
)
from .worker_serena_settings import LanguageBackend, WorkerSerenaSettings


_SCHEMA_VERSION = "1"


class SerenaConfigStoreError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class LocalReferencePath:
    reference_id: str
    file_path: str
    allowed_root: str

    def __post_init__(self) -> None:
        for name in ("reference_id", "file_path", "allowed_root"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be blank")


def _absolute(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise SerenaConfigStoreError("CONFIG_INVALID")
    try:
        return path.resolve(strict=False)
    except OSError as exc:
        raise SerenaConfigStoreError("CONFIG_INVALID") from exc


def _under(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _validate_worker_config(config: SerenaWorkerConfig) -> None:
    root = _absolute(config.instance_root)
    for value in (config.serena_home, config.run_dir, config.log_dir):
        if not _under(_absolute(value), root):
            raise SerenaConfigStoreError("CONFIG_INVALID")
    _absolute(config.runtime_executable_ref)
    _absolute(config.profile_template_ref)
    if not 1 <= config.health_port <= 65535:
        raise SerenaConfigStoreError("CONFIG_INVALID")


def _validate_binding(binding: SerenaProjectBinding) -> None:
    _absolute(binding.worktree_path)


def _validate_reference(reference: LocalReferencePath) -> None:
    root = _absolute(reference.allowed_root)
    path = _absolute(reference.file_path)
    if not _under(path, root):
        raise SerenaConfigStoreError("CONFIG_INVALID")


class SQLiteSerenaConfigStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.database_path)
        except (OSError, sqlite3.Error) as exc:
            raise SerenaConfigStoreError("CONFIG_STORE_UNAVAILABLE") from exc
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
                    CREATE TABLE IF NOT EXISTS serena_config_meta (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS serena_worker_configs (
                        worker_id TEXT PRIMARY KEY,
                        runtime_id TEXT NOT NULL,
                        instance_root TEXT NOT NULL UNIQUE,
                        serena_home TEXT NOT NULL,
                        health_host TEXT NOT NULL,
                        health_port INTEGER NOT NULL CHECK (health_port BETWEEN 1 AND 65535),
                        tunnel_binding_ref TEXT,
                        credential_ref TEXT,
                        runtime_executable_ref TEXT NOT NULL,
                        profile_template_ref TEXT NOT NULL,
                        run_dir TEXT NOT NULL,
                        log_dir TEXT NOT NULL,
                        startup_timeout_seconds INTEGER NOT NULL CHECK (startup_timeout_seconds >= 1),
                        stop_timeout_seconds INTEGER NOT NULL CHECK (stop_timeout_seconds >= 1),
                        UNIQUE (health_host, health_port)
                    );

                    CREATE TABLE IF NOT EXISTS serena_project_bindings (
                        project_id TEXT PRIMARY KEY,
                        worktree_path TEXT NOT NULL,
                        identity_policy TEXT NOT NULL,
                        expected_branch TEXT,
                        expected_head TEXT,
                        mutation_allowed INTEGER NOT NULL CHECK (mutation_allowed IN (0, 1))
                    );

                    CREATE TABLE IF NOT EXISTS serena_local_references (
                        reference_id TEXT PRIMARY KEY,
                        file_path TEXT NOT NULL,
                        allowed_root TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS serena_worker_settings (
                        worker_id TEXT PRIMARY KEY,
                        language_backend TEXT NOT NULL,
                        excluded_tools TEXT NOT NULL,
                        included_optional_tools TEXT NOT NULL,
                        fixed_tools TEXT NOT NULL,
                        base_modes TEXT NOT NULL,
                        tool_timeout INTEGER NOT NULL CHECK (tool_timeout BETWEEN 1 AND 86400)
                    );

                    CREATE TABLE IF NOT EXISTS instance_flags (
                        instance_name TEXT PRIMARY KEY,
                        autostart INTEGER NOT NULL CHECK (autostart IN (0, 1))
                    );

                    CREATE TABLE IF NOT EXISTS instance_recovery (
                        instance_name TEXT PRIMARY KEY,
                        state TEXT NOT NULL,
                        recovery_suppressed INTEGER NOT NULL CHECK (recovery_suppressed IN (0, 1)),
                        failure_count INTEGER NOT NULL CHECK (failure_count >= 0),
                        failure_window_started_at REAL,
                        restart_count INTEGER NOT NULL CHECK (restart_count >= 0),
                        last_exit_reason TEXT,
                        last_exit_at REAL,
                        next_retry_at REAL,
                        updated_at REAL NOT NULL CHECK (updated_at >= 0)
                    );

                    CREATE TABLE IF NOT EXISTS instance_display_names (
                        instance_name TEXT PRIMARY KEY,
                        display_name TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS app_preferences (
                        key TEXT PRIMARY KEY,
                        value INTEGER NOT NULL CHECK (value IN (0, 1))
                    );
                    """
                )
                row = connection.execute(
                    "SELECT value FROM serena_config_meta WHERE key = 'schema_version'"
                ).fetchone()
                if row is None:
                    connection.execute(
                        "INSERT INTO serena_config_meta(key, value) VALUES('schema_version', ?)",
                        (_SCHEMA_VERSION,),
                    )
                elif row["value"] != _SCHEMA_VERSION:
                    raise SerenaConfigStoreError("CONFIG_SCHEMA_UNSUPPORTED")
                self._migrate_settings_columns(connection)
                connection.commit()
            except SerenaConfigStoreError:
                connection.rollback()
                raise
            except sqlite3.Error as exc:
                connection.rollback()
                raise SerenaConfigStoreError("CONFIG_STORE_INITIALIZE_FAILED") from exc

    def save_worker_config(self, config: SerenaWorkerConfig) -> None:
        _validate_worker_config(config)
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO serena_worker_configs(
                        worker_id, runtime_id, instance_root, serena_home,
                        health_host, health_port, tunnel_binding_ref, credential_ref,
                        runtime_executable_ref, profile_template_ref, run_dir, log_dir,
                        startup_timeout_seconds, stop_timeout_seconds
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(worker_id) DO UPDATE SET
                        runtime_id=excluded.runtime_id,
                        instance_root=excluded.instance_root,
                        serena_home=excluded.serena_home,
                        health_host=excluded.health_host,
                        health_port=excluded.health_port,
                        tunnel_binding_ref=excluded.tunnel_binding_ref,
                        credential_ref=excluded.credential_ref,
                        runtime_executable_ref=excluded.runtime_executable_ref,
                        profile_template_ref=excluded.profile_template_ref,
                        run_dir=excluded.run_dir,
                        log_dir=excluded.log_dir,
                        startup_timeout_seconds=excluded.startup_timeout_seconds,
                        stop_timeout_seconds=excluded.stop_timeout_seconds
                    """,
                    (
                        config.worker_id,
                        config.runtime_id,
                        str(_absolute(config.instance_root)),
                        str(_absolute(config.serena_home)),
                        config.health_host,
                        config.health_port,
                        config.tunnel_binding_ref,
                        config.credential_ref,
                        str(_absolute(config.runtime_executable_ref)),
                        str(_absolute(config.profile_template_ref)),
                        str(_absolute(config.run_dir)),
                        str(_absolute(config.log_dir)),
                        config.startup_timeout_seconds,
                        config.stop_timeout_seconds,
                    ),
                )
                connection.commit()
            except sqlite3.IntegrityError as exc:
                connection.rollback()
                raise SerenaConfigStoreError("CONFIG_CONFLICT") from exc
            except sqlite3.Error as exc:
                connection.rollback()
                raise SerenaConfigStoreError("CONFIG_STORE_WRITE_FAILED") from exc

    def _worker_from_row(self, row: sqlite3.Row) -> SerenaWorkerConfig:
        try:
            config = SerenaWorkerConfig(
                worker_id=row["worker_id"],
                runtime_id=row["runtime_id"],
                instance_root=row["instance_root"],
                serena_home=row["serena_home"],
                health_host=row["health_host"],
                health_port=row["health_port"],
                tunnel_binding_ref=row["tunnel_binding_ref"],
                credential_ref=row["credential_ref"],
                runtime_executable_ref=row["runtime_executable_ref"],
                profile_template_ref=row["profile_template_ref"],
                run_dir=row["run_dir"],
                log_dir=row["log_dir"],
                startup_timeout_seconds=row["startup_timeout_seconds"],
                stop_timeout_seconds=row["stop_timeout_seconds"],
            )
            _validate_worker_config(config)
            return config
        except (ValueError, TypeError, SerenaConfigStoreError) as exc:
            raise SerenaConfigStoreError("CONFIG_INVALID") from exc

    def get_worker_config(self, worker_id: str) -> SerenaWorkerConfig | None:
        self.initialize()
        with self._connect() as connection:
            try:
                row = connection.execute(
                    "SELECT * FROM serena_worker_configs WHERE worker_id = ?",
                    (worker_id,),
                ).fetchone()
            except sqlite3.Error as exc:
                raise SerenaConfigStoreError("CONFIG_STORE_READ_FAILED") from exc
        return None if row is None else self._worker_from_row(row)

    def list_worker_configs(self) -> tuple[SerenaWorkerConfig, ...]:
        self.initialize()
        with self._connect() as connection:
            try:
                rows = connection.execute(
                    "SELECT * FROM serena_worker_configs ORDER BY worker_id"
                ).fetchall()
            except sqlite3.Error as exc:
                raise SerenaConfigStoreError("CONFIG_STORE_READ_FAILED") from exc
        return tuple(self._worker_from_row(row) for row in rows)

    def save_project_binding(self, binding: SerenaProjectBinding) -> None:
        _validate_binding(binding)
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO serena_project_bindings(
                        project_id, worktree_path, identity_policy,
                        expected_branch, expected_head, mutation_allowed
                    ) VALUES(?, ?, ?, ?, ?, ?)
                    ON CONFLICT(project_id) DO UPDATE SET
                        worktree_path=excluded.worktree_path,
                        identity_policy=excluded.identity_policy,
                        expected_branch=excluded.expected_branch,
                        expected_head=excluded.expected_head,
                        mutation_allowed=excluded.mutation_allowed
                    """,
                    (
                        binding.project_id,
                        str(_absolute(binding.worktree_path)),
                        binding.identity_policy.value,
                        binding.expected_branch,
                        binding.expected_head,
                        int(binding.mutation_allowed),
                    ),
                )
                connection.commit()
            except sqlite3.Error as exc:
                connection.rollback()
                raise SerenaConfigStoreError("CONFIG_STORE_WRITE_FAILED") from exc

    def _binding_from_row(self, row: sqlite3.Row) -> SerenaProjectBinding:
        try:
            policy = ProjectIdentityPolicy(row["identity_policy"])
            mutation = row["mutation_allowed"]
            if mutation not in (0, 1):
                raise ValueError("invalid mutation flag")
            result = SerenaProjectBinding(
                project_id=row["project_id"],
                worktree_path=row["worktree_path"],
                identity_policy=policy,
                expected_branch=row["expected_branch"],
                expected_head=row["expected_head"],
                mutation_allowed=bool(mutation),
            )
            _validate_binding(result)
            return result
        except (ValueError, TypeError, SerenaConfigStoreError) as exc:
            raise SerenaConfigStoreError("CONFIG_INVALID") from exc

    def get_project_binding(self, project_id: str) -> SerenaProjectBinding | None:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM serena_project_bindings WHERE project_id = ?",
                (project_id,),
            ).fetchone()
        return None if row is None else self._binding_from_row(row)

    def list_project_bindings(self) -> tuple[SerenaProjectBinding, ...]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM serena_project_bindings ORDER BY project_id"
            ).fetchall()
        return tuple(self._binding_from_row(row) for row in rows)

    def save_local_reference(self, reference: LocalReferencePath) -> None:
        _validate_reference(reference)
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO serena_local_references(reference_id, file_path, allowed_root)
                    VALUES(?, ?, ?)
                    ON CONFLICT(reference_id) DO UPDATE SET
                        file_path=excluded.file_path,
                        allowed_root=excluded.allowed_root
                    """,
                    (
                        reference.reference_id,
                        str(_absolute(reference.file_path)),
                        str(_absolute(reference.allowed_root)),
                    ),
                )
                connection.commit()
            except sqlite3.Error as exc:
                connection.rollback()
                raise SerenaConfigStoreError("CONFIG_STORE_WRITE_FAILED") from exc

    def _reference_from_row(self, row: sqlite3.Row) -> LocalReferencePath:
        try:
            reference = LocalReferencePath(
                reference_id=row["reference_id"],
                file_path=row["file_path"],
                allowed_root=row["allowed_root"],
            )
            _validate_reference(reference)
            return reference
        except (ValueError, TypeError, SerenaConfigStoreError) as exc:
            raise SerenaConfigStoreError("CONFIG_INVALID") from exc

    def get_local_reference(self, reference_id: str) -> LocalReferencePath | None:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT reference_id, file_path, allowed_root FROM serena_local_references WHERE reference_id = ?",
                (reference_id,),
            ).fetchone()
        return None if row is None else self._reference_from_row(row)

    def list_local_references(self) -> tuple[LocalReferencePath, ...]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT reference_id, file_path, allowed_root FROM serena_local_references ORDER BY reference_id"
            ).fetchall()
        return tuple(self._reference_from_row(row) for row in rows)

    @staticmethod
    def _migrate_settings_columns(connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(serena_worker_settings)"
            ).fetchall()
        }
        if "project_path" not in columns:
            connection.execute(
                "ALTER TABLE serena_worker_settings ADD COLUMN project_path TEXT"
            )
        if "enabled_languages" not in columns:
            connection.execute(
                "ALTER TABLE serena_worker_settings ADD COLUMN enabled_languages TEXT"
            )
        if "brain_folders" not in columns:
            connection.execute(
                "ALTER TABLE serena_worker_settings ADD COLUMN brain_folders TEXT"
            )
        if "brain_entry_files" not in columns:
            connection.execute(
                "ALTER TABLE serena_worker_settings ADD COLUMN brain_entry_files TEXT"
            )

    def save_worker_settings(self, settings: WorkerSerenaSettings) -> None:
        if not isinstance(settings, WorkerSerenaSettings):
            raise SerenaConfigStoreError("SETTINGS_INVALID")
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO serena_worker_settings(
                        worker_id, language_backend, excluded_tools,
                        included_optional_tools, fixed_tools, base_modes, tool_timeout,
                        project_path, enabled_languages, brain_folders, brain_entry_files
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(worker_id) DO UPDATE SET
                        language_backend=excluded.language_backend,
                        excluded_tools=excluded.excluded_tools,
                        included_optional_tools=excluded.included_optional_tools,
                        fixed_tools=excluded.fixed_tools,
                        base_modes=excluded.base_modes,
                        tool_timeout=excluded.tool_timeout,
                        project_path=excluded.project_path,
                        enabled_languages=excluded.enabled_languages,
                        brain_folders=excluded.brain_folders,
                        brain_entry_files=excluded.brain_entry_files
                    """,
                    (
                        settings.worker_id,
                        settings.language_backend.value,
                        json.dumps(list(settings.excluded_tools)),
                        json.dumps(list(settings.included_optional_tools)),
                        json.dumps(list(settings.fixed_tools)),
                        json.dumps(list(settings.base_modes)),
                        settings.tool_timeout,
                        settings.project_path,
                        json.dumps(list(settings.enabled_languages)),
                        json.dumps(list(settings.brain_folders)) if settings.brain_folders else None,
                        json.dumps(list(settings.brain_entry_files)) if settings.brain_entry_files else None,
                    ),
                )
                connection.commit()
            except sqlite3.Error as exc:
                connection.rollback()
                raise SerenaConfigStoreError("SETTINGS_STORE_WRITE_FAILED") from exc

    def get_worker_settings(self, worker_id: str) -> WorkerSerenaSettings | None:
        if not isinstance(worker_id, str) or not worker_id.strip():
            raise SerenaConfigStoreError("SETTINGS_WORKER_ID_INVALID")
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT worker_id, language_backend, excluded_tools,
                       included_optional_tools, fixed_tools, base_modes, tool_timeout,
                       project_path, enabled_languages, brain_folders, brain_entry_files
                FROM serena_worker_settings WHERE worker_id = ?
                """,
                (worker_id,),
            ).fetchone()
        if row is None:
            return None
        try:
            return WorkerSerenaSettings(
                worker_id=row["worker_id"],
                language_backend=LanguageBackend(row["language_backend"]),
                excluded_tools=tuple(json.loads(row["excluded_tools"])),
                included_optional_tools=tuple(json.loads(row["included_optional_tools"])),
                fixed_tools=tuple(json.loads(row["fixed_tools"])),
                base_modes=tuple(json.loads(row["base_modes"])),
                tool_timeout=int(row["tool_timeout"]),
                project_path=row["project_path"],
                enabled_languages=tuple(json.loads(row["enabled_languages"] or "[]")),
                brain_folders=tuple(json.loads(row["brain_folders"] or "[]")),
                brain_entry_files=tuple(json.loads(row["brain_entry_files"] or "[]")),
            )
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise SerenaConfigStoreError("SETTINGS_ROW_CORRUPT") from exc

    def save_connector_recovery(
        self, record: ConnectorRecoveryRecord
    ) -> ConnectorRecoveryRecord:
        if not isinstance(record, ConnectorRecoveryRecord):
            raise SerenaConfigStoreError("RECOVERY_RECORD_INVALID")
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO instance_recovery(
                        instance_name, state, recovery_suppressed, failure_count,
                        failure_window_started_at, restart_count, last_exit_reason,
                        last_exit_at, next_retry_at, updated_at
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(instance_name) DO UPDATE SET
                        state=excluded.state,
                        recovery_suppressed=excluded.recovery_suppressed,
                        failure_count=excluded.failure_count,
                        failure_window_started_at=excluded.failure_window_started_at,
                        restart_count=excluded.restart_count,
                        last_exit_reason=excluded.last_exit_reason,
                        last_exit_at=excluded.last_exit_at,
                        next_retry_at=excluded.next_retry_at,
                        updated_at=excluded.updated_at
                    """,
                    (
                        record.instance_name, record.state.value,
                        int(record.recovery_suppressed), record.failure_count,
                        record.failure_window_started_at, record.restart_count,
                        record.last_exit_reason, record.last_exit_at,
                        record.next_retry_at, record.updated_at,
                    ),
                )
                connection.commit()
            except sqlite3.Error as exc:
                connection.rollback()
                raise SerenaConfigStoreError("RECOVERY_STORE_WRITE_FAILED") from exc
        return record

    def get_connector_recovery(
        self, instance_name: str
    ) -> ConnectorRecoveryRecord | None:
        if not isinstance(instance_name, str) or not instance_name.strip():
            raise SerenaConfigStoreError("INSTANCE_NAME_INVALID")
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM instance_recovery WHERE instance_name = ?",
                (instance_name.strip(),),
            ).fetchone()
        if row is None:
            return None
        try:
            return ConnectorRecoveryRecord(
                instance_name=row["instance_name"],
                state=ConnectorRecoveryState(row["state"]),
                recovery_suppressed=bool(row["recovery_suppressed"]),
                failure_count=row["failure_count"],
                failure_window_started_at=row["failure_window_started_at"],
                restart_count=row["restart_count"],
                last_exit_reason=row["last_exit_reason"],
                last_exit_at=row["last_exit_at"],
                next_retry_at=row["next_retry_at"],
                updated_at=row["updated_at"],
            )
        except (ValueError, TypeError) as exc:
            raise SerenaConfigStoreError("RECOVERY_RECORD_INVALID") from exc

    def clear_connector_recovery(self, instance_name: str) -> None:
        if not isinstance(instance_name, str) or not instance_name.strip():
            raise SerenaConfigStoreError("INSTANCE_NAME_INVALID")
        self.initialize()
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM instance_recovery WHERE instance_name = ?",
                (instance_name.strip(),),
            )
            connection.commit()

    def set_instance_autostart(self, instance_name: str, enabled: bool) -> None:
        if not isinstance(instance_name, str) or not instance_name.strip():
            raise SerenaConfigStoreError("INSTANCE_NAME_INVALID")
        if not isinstance(enabled, bool):
            raise SerenaConfigStoreError("AUTOSTART_FLAG_INVALID")
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO instance_flags(instance_name, autostart)
                    VALUES(?, ?)
                    ON CONFLICT(instance_name) DO UPDATE SET
                        autostart=excluded.autostart
                    """,
                    (instance_name.strip(), 1 if enabled else 0),
                )
                connection.commit()
            except sqlite3.Error as exc:
                connection.rollback()
                raise SerenaConfigStoreError("INSTANCE_FLAG_WRITE_FAILED") from exc

    def get_instance_autostart(self, instance_name: str) -> bool:
        if not isinstance(instance_name, str) or not instance_name.strip():
            raise SerenaConfigStoreError("INSTANCE_NAME_INVALID")
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT autostart FROM instance_flags WHERE instance_name = ?",
                (instance_name.strip(),),
            ).fetchone()
        return bool(row["autostart"]) if row is not None else False

    def list_instance_autostart(self) -> tuple[str, ...]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT instance_name FROM instance_flags WHERE autostart = 1 ORDER BY instance_name"
            ).fetchall()
        return tuple(row["instance_name"] for row in rows)

    def clear_instance_flags(self, instance_name: str) -> None:
        if not isinstance(instance_name, str) or not instance_name.strip():
            raise SerenaConfigStoreError("INSTANCE_NAME_INVALID")
        self.initialize()
        with self._connect() as connection:
            cleaned = instance_name.strip()
            connection.execute(
                "DELETE FROM instance_flags WHERE instance_name = ?",
                (cleaned,),
            )
            connection.execute(
                "DELETE FROM instance_recovery WHERE instance_name = ?",
                (cleaned,),
            )
            connection.commit()

    def get_instance_display_name(self, instance_name: str) -> str | None:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT display_name FROM instance_display_names WHERE instance_name = ?",
                (instance_name,),
            ).fetchone()
        return row["display_name"] if row is not None else None

    def set_instance_display_name(self, instance_name: str, display_name: str) -> str:
        if not isinstance(instance_name, str) or not instance_name.strip():
            raise SerenaConfigStoreError("INSTANCE_NAME_INVALID")
        if not isinstance(display_name, str) or not display_name.strip():
            raise SerenaConfigStoreError("INSTANCE_DISPLAY_NAME_INVALID")
        cleaned = display_name.strip()
        self.initialize()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO instance_display_names(instance_name, display_name)
                VALUES(?, ?)
                ON CONFLICT(instance_name) DO UPDATE SET
                    display_name=excluded.display_name
                """,
                (instance_name.strip(), cleaned),
            )
            connection.commit()
        return cleaned

    def clear_instance_display_name(self, instance_name: str) -> None:
        self.initialize()
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM instance_display_names WHERE instance_name = ?",
                (instance_name,),
            )
            connection.commit()

    def instance_display_names(self) -> dict[str, str]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT instance_name, display_name FROM instance_display_names"
            ).fetchall()
        return {row["instance_name"]: row["display_name"] for row in rows}

    _PREF_KEY_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")

    def set_preference(self, key: str, value: bool) -> None:
        if not isinstance(key, str) or self._PREF_KEY_RE.fullmatch(key) is None or "\x00" in key:
            raise SerenaConfigStoreError("PREFERENCE_KEY_INVALID")
        if not isinstance(value, bool):
            raise SerenaConfigStoreError("PREFERENCE_VALUE_INVALID")
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO app_preferences(key, value)
                    VALUES(?, ?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value
                    """,
                    (key.strip(), 1 if value else 0),
                )
                connection.commit()
            except sqlite3.Error as exc:
                connection.rollback()
                raise SerenaConfigStoreError("PREFERENCE_WRITE_FAILED") from exc

    def get_preference(self, key: str) -> bool | None:
        if not isinstance(key, str) or self._PREF_KEY_RE.fullmatch(key) is None or "\x00" in key:
            raise SerenaConfigStoreError("PREFERENCE_KEY_INVALID")
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM app_preferences WHERE key = ?",
                (key.strip(),),
            ).fetchone()
        return None if row is None else bool(row["value"])
