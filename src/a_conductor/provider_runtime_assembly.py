"""Production provider-state and supervised Claude runtime assembly.

This module wires accepted provider persistence, A-Wiki reference resolution and
Claude supervised execution. It owns no scheduler, retry loop, provider store,
secret vault, lease system or lifecycle authority.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Mapping, Sequence

from .awiki_environment_resolver import (
    AWikiDriveEnvironmentSource,
    AWikiEnvironmentReferenceResolver,
    resolve_awiki_drive_root,
)
from .claude_code_job_assembly import build_supervised_claude_job_backend
from .claude_code_job_backend import (
    ClaudeCodeJobBackend,
    ClaudeCodeOperationDefinition,
    ClaudeCodeProviderState,
)
from .provider_config_store import ProviderConfigStoreError, SQLiteProviderConfigStore
from .parallel_ready_execution import ParallelReadyExecutor, ParallelReadyRunner
from .worker_lease import WorkerLeaseBroker
from .provider_configuration import ProviderHealth, ProviderObservation, observe_provider
from .zai_quota_probe import ZaiQuotaProbe, ZaiQuotaTransport, supports_zai_quota_endpoint


class SQLiteClaudeCodeProviderResolver:
    """Resolve one provider runtime state from the existing control database."""

    def __init__(self, store: SQLiteProviderConfigStore) -> None:
        if not isinstance(store, SQLiteProviderConfigStore):
            raise ValueError("store must be SQLiteProviderConfigStore")
        self._store = store
    def resolve(self, provider_id: str) -> ClaudeCodeProviderState | None:
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError("provider_id must not be blank")
        try:
            profile = self._store.get_provider(provider_id.strip())
            if profile is None:
                return None
            endpoint = self._store.get_endpoint(profile.endpoint_ref)
            if endpoint is None or endpoint.endpoint_ref != profile.endpoint_ref:
                return None
            observation = self._store.get_observation(profile.provider_id)
        except (ProviderConfigStoreError, TypeError, ValueError):
            return None
        if observation is not None and observation.provider_id != profile.provider_id:
            return None
        return ClaudeCodeProviderState(
            profile=profile,
            endpoint=endpoint,
            observation=observation,
        )


def build_sqlite_supervised_claude_job_backend(
    *,
    database_path: str | Path,
    operations: Sequence[ClaudeCodeOperationDefinition],
    execution_store: object,
    supervised: object,
    clock: Callable[[], object],
    drive_root: str | Path | None = None,
    awiki_repo_root: str | Path | None = None,
    home: str | Path | None = None,
    environment: Mapping[str, str] | None = None,
    repo_env_name: str | None = None,
    claude_executable: str = "claude",
    poll_interval_seconds: float = 0.05,
) -> ClaudeCodeJobBackend:
    """Build the accepted Claude backend from one existing control database."""
    store = SQLiteProviderConfigStore(database_path)
    store.initialize()
    resolved_drive = (
        Path(drive_root).expanduser().resolve(strict=False)
        if drive_root is not None
        else resolve_awiki_drive_root(
            environment=environment,
            awiki_repo_root=awiki_repo_root,
            home=home,
        )
    )
    secret_source = AWikiDriveEnvironmentSource(
        resolved_drive,
        repo_env_name=repo_env_name,
    )
    reference_resolver = AWikiEnvironmentReferenceResolver(
        endpoint_reader=store,
        secret_source=secret_source,
    )
    provider_resolver = SQLiteClaudeCodeProviderResolver(store)
    return build_supervised_claude_job_backend(
        operations=operations,
        execution_store=execution_store,
        supervised=supervised,
        reference_resolver=reference_resolver,
        provider_resolver=provider_resolver,
        clock=clock,
        claude_executable=claude_executable,
        poll_interval_seconds=poll_interval_seconds,
    )

def refresh_zai_provider_observation(
    *,
    database_path: str | Path,
    provider_id: str,
    clock: Callable[[], object],
    transport: ZaiQuotaTransport | None = None,
    drive_root: str | Path | None = None,
    awiki_repo_root: str | Path | None = None,
    home: str | Path | None = None,
    environment: Mapping[str, str] | None = None,
    repo_env_name: str | None = None,
) -> ProviderObservation | None:
    """Refresh one explicit Z.ai provider observation without guessing routes."""
    if not isinstance(provider_id, str) or not provider_id.strip():
        raise ValueError("provider_id must not be blank")
    if not callable(clock):
        raise ValueError("clock must be callable")
    store = SQLiteProviderConfigStore(database_path)
    store.initialize()
    profile = store.get_provider(provider_id.strip())
    if profile is None:
        return None
    endpoint = store.get_endpoint(profile.endpoint_ref)
    if endpoint is None:
        return None
    if not supports_zai_quota_endpoint(endpoint):
        observation = ProviderObservation(
            provider_id=profile.provider_id,
            health=ProviderHealth.UNAVAILABLE,
            observed_at=clock(),
            provenance="zai-quota-monitor:unsupported-route",
        )
        store.save_observation(observation)
        return observation
    resolved_drive = (
        Path(drive_root).expanduser().resolve(strict=False)
        if drive_root is not None
        else resolve_awiki_drive_root(
            environment=environment,
            awiki_repo_root=awiki_repo_root,
            home=home,
        )
    )
    secret_source = AWikiDriveEnvironmentSource(
        resolved_drive,
        repo_env_name=repo_env_name,
    )
    reference_resolver = AWikiEnvironmentReferenceResolver(
        endpoint_reader=store,
        secret_source=secret_source,
    )
    probe = ZaiQuotaProbe(
        resolve_credential=reference_resolver.resolve,
        transport=transport,
        clock=clock,
    )
    observed_at = clock()
    observation = observe_provider(
        profile,
        endpoint,
        probe,
        observed_at=observed_at,
        provenance="zai-quota-monitor:v1",
    )
    store.save_observation(observation)
    return observation

def build_sqlite_parallel_ready_executor(
    *,
    database_path: str | Path,
    broker: WorkerLeaseBroker,
    runner: ParallelReadyRunner,
    clock: Callable[[], object],
) -> ParallelReadyExecutor:
    """Build AHA-6 execution with the shared SQLite provider admission authority."""
    store = SQLiteProviderConfigStore(database_path)
    store.initialize()
    return ParallelReadyExecutor(
        broker=broker,
        runner=runner,
        clock=clock,
        provider_admission_store=store,
    )
