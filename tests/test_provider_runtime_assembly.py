from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from a_conductor.claude_code_harness import HarnessDispatch, MutationIntent, TaskPacketFile
from a_conductor.claude_code_job_backend import ClaudeCodeOperationDefinition
from a_conductor.domain import RecoveryClassification
from a_conductor.execution_store import SQLiteExecutionStore
from a_conductor.job_execution import JobExecutionContext
from a_conductor.provider_config_store import SQLiteProviderConfigStore
from a_conductor.provider_execution_authority import ProviderExecutionRequirement
from a_conductor.provider_policy import (
    ProviderPolicyTaskSecurity,
    TaskNetworkPolicy,
    TaskPrivacyClass,
)
from a_conductor.provider_configuration import (
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
from a_conductor.provider_runtime_assembly import (
    SQLiteClaudeCodeProviderResolver,
    build_sqlite_supervised_claude_job_backend,
    refresh_zai_provider_observation,
)
from a_conductor.supervised_execution import SupervisedLaunchOutcome

NOW = datetime(2026, 8, 30, 5, 0, tzinfo=timezone.utc)

def profile() -> ProviderConfiguration:
    return ProviderConfiguration(
        provider_id="provider-glm-shared",
        display_name="GLM Shared",
        provider_type="cloud-proxy",
        protocol_family=ProtocolFamily.ANTHROPIC_MESSAGES,
        endpoint_ref="provider-config:glm/base-url",
        credential_ref="secret-ref:awiki-env/ANTHROPIC_API_KEY",
        trust_class=ProviderTrustClass.TRUSTED_THIRD_PARTY,
        egress_boundary=EgressBoundary.EXTERNAL_THIRD_PARTY,
        harness_strategies=(HarnessStrategy.CLAUDE_CODE_CLI,),
        max_concurrency=1,
        models=(
            ProviderModelConfiguration(
                model_id="glm-5.3",
                display_name="GLM-5.3",
                supported_effort_levels=("MAX",),
            ),
        ),
        enabled=True,
    )


def observation() -> ProviderObservation:
    return ProviderObservation(
        provider_id="provider-glm-shared",
        health=ProviderHealth.AVAILABLE,
        observed_at=NOW,
        provenance="fake:quota",
        quota=QuotaSnapshot("5h", limit=100, used=10, remaining=90, reset_at=NOW, reset_in_seconds=3600),
        configuration_generation=1,
    )

def seeded_store(db: Path, *, include_endpoint: bool = True) -> SQLiteProviderConfigStore:
    store = SQLiteProviderConfigStore(db)
    configured = profile()
    if include_endpoint:
        store.save_endpoint(
            ProviderEndpointConfig(configured.endpoint_ref, "https://provider.example/v1")
        )
    store.save_provider(configured)
    store.save_observation(observation())
    return store


def test_sqlite_provider_resolver_reads_same_control_database(tmp_path: Path) -> None:
    db = tmp_path / "control.sqlite"
    store = seeded_store(db)
    state = SQLiteClaudeCodeProviderResolver(store).resolve("provider-glm-shared")

    assert state is not None
    assert state.profile == profile()
    assert state.endpoint.base_url == "https://provider.example/v1"
    assert state.observation == observation()
    assert state.observation.quota is not None
    assert state.observation.quota.remaining == 90


def test_sqlite_provider_resolver_fails_closed_for_missing_profile_or_endpoint(tmp_path: Path) -> None:
    db = tmp_path / "control.sqlite"
    store = SQLiteProviderConfigStore(db)
    resolver = SQLiteClaudeCodeProviderResolver(store)
    assert resolver.resolve("provider-glm-shared") is None

    seeded_store(db, include_endpoint=False)
    assert resolver.resolve("provider-glm-shared") is None

def operation(
    root: Path,
    *,
    provider_security: ProviderPolicyTaskSecurity | None = None,
    expected_generation: int | None = None,
    provider_database_path: Path | None = None,
) -> ClaudeCodeOperationDefinition:
    if provider_security is None:
        provider_security = ProviderPolicyTaskSecurity(
            privacy_class=TaskPrivacyClass.INTERNAL,
            network_policy=TaskNetworkPolicy.ALLOWLISTED,
            network_allowlist=("provider.example",),
            secret_access=False,
        )
    if expected_generation is None:
        expected_generation = 1
    work_order = "docs/work-orders/WO-P1-114-auto-provider-runtime-assembly.md"
    authority_path = root / work_order
    authority_path.parent.mkdir(parents=True, exist_ok=True)
    authority_payload = {
        "schema_version": "1.0.0", "task_id": "task-provider-runtime",
        "goal": "bounded provider runtime test", "risk_class": "HIGH",
        "authority": {"requested_by": "test", "mutation_allowed": False, "human_approval_required": False},
        "target": {"project_id": "project-1", "identity_policy": "EXACT"},
        "scope": {"allowed_files": [], "forbidden_files": [], "allowed_commands": [], "forbidden_commands": []},
        "acceptance": {"criteria": ["typed result"], "verify_commands": [], "review_required": True},
        "security": {
            "privacy_class": provider_security.privacy_class.value,
            "network_policy": provider_security.network_policy.value,
            "network_allowlist": list(provider_security.network_allowlist),
            "secret_access": provider_security.secret_access,
        },
        "budget": {"max_elapsed_seconds": 300},
        "retry_policy": {"max_attempts": 1, "max_identical_failures": 1, "on_lease_expiry": "RECOVERY_REQUIRED"},
        "escalation": {"conditions": ["SECURITY_BOUNDARY_CHANGE"]},
        "required_evidence": ["TEST_RESULT"],
    }
    authority_path.write_text(json.dumps(authority_payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    db_path = provider_database_path or (root / "control.sqlite")
    requirement = ProviderExecutionRequirement.from_task_contract_file(
        project_root=root, provider_id="provider-glm-shared", provider_authority_path=db_path,
        expected_configuration_generation=expected_generation, task_contract_ref=work_order,
        base_operation_ref="op:provider-runtime",
    )
    packet_path = root / ".a-conductor" / "task-packets" / "provider-runtime.md"
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text("# bounded provider runtime test\n", encoding="utf-8")
    packet = TaskPacketFile(
        task_contract_ref=work_order,
        path=str(packet_path),
        sha256=hashlib.sha256(packet_path.read_bytes()).hexdigest(),
    )
    dispatch = HarnessDispatch(
        execution_id="job-provider-runtime",
        task_contract_ref=work_order,
        project_id="project-1",
        worktree_path=str(root),
        expected_branch="feat/wo-p1-114-auto-provider-dispatch",
        expected_head="a" * 40,
        provider_id="provider-glm-shared",
        model_id="glm-5.3",
        harness_strategy=HarnessStrategy.CLAUDE_CODE_CLI,
        mutation_intent=MutationIntent.READ_ONLY,
        timeout_seconds=30,
        max_output_bytes=4096,
        effort_level="MAX",
    )
    return ClaudeCodeOperationDefinition(
        operation_ref=requirement.operation_ref,
        dispatch=dispatch,
        packet=packet,
        worker_id="a-worker-01",
        provider_security=provider_security,
        expected_configuration_generation=expected_generation,
        provider_requirement=requirement,
    )

class CapturingRecoverySupervised:
    def __init__(self) -> None:
        self.plans = []

    def launch(self, plan):
        self.plans.append(plan)
        return SupervisedLaunchOutcome(
            record=plan.record,
            supervisor_pid=None,
            child_pid=None,
            recovery_required=True,
            error_code="TEST_STOP",
        )

    def inspect(self, execution_id):
        raise AssertionError("inspect must not run after launch recovery")

    def collect(self, execution_id, *, expected_version):
        raise AssertionError("collect must not run after launch recovery")


def context(definition: ClaudeCodeOperationDefinition) -> JobExecutionContext:
    return JobExecutionContext(
        job_id=definition.dispatch.execution_id,
        work_order_ref=definition.dispatch.task_contract_ref,
        project_id=definition.dispatch.project_id,
        worker_id=definition.worker_id,
        attempt_no=1,
        max_attempts=3,
    )

def test_wo118b_production_builder_rejects_requirement_bound_to_different_provider_database(tmp_path: Path) -> None:
    db = tmp_path / "canonical.sqlite"
    other_db = tmp_path / "other.sqlite"
    seeded_store(db)
    seeded_store(other_db)
    definition = operation(tmp_path / "worktree-db-mismatch", provider_database_path=other_db)
    drive = tmp_path / "A-Wiki-Data"
    drive.mkdir()
    with pytest.raises(ValueError, match="PROVIDER_AUTHORITY_STORE_MISMATCH"):
        build_sqlite_supervised_claude_job_backend(
            database_path=db, operations=(definition,),
            execution_store=SQLiteExecutionStore(tmp_path / "execution-db-mismatch.sqlite"),
            supervised=CapturingRecoverySupervised(), drive_root=drive, clock=lambda: NOW,
            claude_executable="claude", poll_interval_seconds=0.001,
        )


def test_wo118b_production_builder_rejects_legacy_operation_without_durable_requirement(tmp_path: Path) -> None:
    db = tmp_path / "legacy.sqlite"
    seeded_store(db)
    definition = operation(tmp_path / "worktree-legacy", provider_database_path=db)
    legacy = ClaudeCodeOperationDefinition(
        operation_ref="op:legacy-provider-runtime", dispatch=definition.dispatch,
        packet=definition.packet, worker_id=definition.worker_id,
        provider_security=definition.provider_security, expected_configuration_generation=1,
    )
    drive = tmp_path / "A-Wiki-Data"
    drive.mkdir()
    with pytest.raises(ValueError, match="PROVIDER_EXECUTION_REQUIREMENT_REQUIRED"):
        build_sqlite_supervised_claude_job_backend(
            database_path=db, operations=(legacy,),
            execution_store=SQLiteExecutionStore(tmp_path / "execution-legacy.sqlite"),
            supervised=CapturingRecoverySupervised(), drive_root=drive, clock=lambda: NOW,
            claude_executable="claude", poll_interval_seconds=0.001,
        )


def test_production_builder_resolves_db_endpoint_and_drive_secret_at_supervised_boundary(tmp_path: Path) -> None:
    db = tmp_path / "control.sqlite"
    seeded_store(db)
    drive = tmp_path / "A-Wiki-Data"
    (drive / "secrets").mkdir(parents=True)
    (drive / "secrets" / "global.env").write_text(
        "ANTHROPIC_API_KEY=top-secret-value\n", encoding="utf-8"
    )
    definition = operation(tmp_path / "worktree", provider_database_path=db)
    supervised = CapturingRecoverySupervised()
    backend = build_sqlite_supervised_claude_job_backend(
        database_path=db,
        operations=(definition,),
        execution_store=SQLiteExecutionStore(tmp_path / "execution.sqlite"),
        supervised=supervised,
        drive_root=drive,
        clock=lambda: NOW,
        claude_executable="claude",
        poll_interval_seconds=0.001,
    )

    result = backend.execute(definition.operation_ref, context(definition))

    assert result.success is False
    assert result.error_code == "HARNESS_FAILED"
    assert result.recovery_classification is RecoveryClassification.NO_MUTATION
    assert len(supervised.plans) == 1
    assert supervised.plans[0].environment_overrides == (
        ("ANTHROPIC_BASE_URL", "https://provider.example/v1"),
        ("ANTHROPIC_AUTH_TOKEN", "top-secret-value"),
    )
    assert "top-secret-value" not in (result.evidence_ref or "")


def _wo118b_security(*, secret: bool = False) -> ProviderPolicyTaskSecurity:
    return ProviderPolicyTaskSecurity(
        privacy_class=TaskPrivacyClass.SECRET if secret else TaskPrivacyClass.INTERNAL,
        network_policy=TaskNetworkPolicy.ALLOWLISTED,
        network_allowlist=("provider.example",),
        secret_access=secret,
    )


def test_wo118b_production_policy_denial_precedes_drive_secret_resolution(tmp_path: Path) -> None:
    db = tmp_path / "policy-denied.sqlite"
    seeded_store(db)
    drive = tmp_path / "A-Wiki-Data"
    drive.mkdir()
    definition = operation(
        tmp_path / "worktree-policy",
        provider_security=_wo118b_security(secret=True),
        provider_database_path=db,
        expected_generation=1,
    )
    supervised = CapturingRecoverySupervised()
    backend = build_sqlite_supervised_claude_job_backend(
        database_path=db,
        operations=(definition,),
        execution_store=SQLiteExecutionStore(tmp_path / "execution-policy.sqlite"),
        supervised=supervised,
        drive_root=drive,
        clock=lambda: NOW,
        claude_executable="claude",
        poll_interval_seconds=0.001,
    )

    result = backend.execute(definition.operation_ref, context(definition))

    assert result.success is False
    assert result.error_code == "SECRET_TASK_EXTERNAL_DENIED"
    assert result.recovery_classification is RecoveryClassification.NO_MUTATION
    assert supervised.plans == []


def test_wo118b_generation_drift_during_secret_resolution_blocks_launch(
    tmp_path: Path, monkeypatch
) -> None:
    from a_conductor.awiki_environment_resolver import AWikiEnvironmentReferenceResolver

    db = tmp_path / "secret-drift.sqlite"
    store = seeded_store(db)
    drive = tmp_path / "A-Wiki-Data"
    (drive / "secrets").mkdir(parents=True)
    (drive / "secrets" / "global.env").write_text(
        "ANTHROPIC_API_KEY=top-secret-value\n", encoding="utf-8"
    )
    definition = operation(
        tmp_path / "worktree-drift",
        provider_security=_wo118b_security(),
        provider_database_path=db,
        expected_generation=1,
    )
    supervised = CapturingRecoverySupervised()
    original_resolve = AWikiEnvironmentReferenceResolver.resolve
    bumped = {"done": False}

    def drifting_resolve(self, reference: str):
        value = original_resolve(self, reference)
        if reference == profile().credential_ref and not bumped["done"]:
            snapshot = store.load_provider_snapshot(profile().provider_id)
            assert snapshot is not None and snapshot.generation == 1
            store.save_provider(
                ProviderConfiguration(**{
                    **snapshot.profile.as_dict(),
                    "display_name": "Changed during credential resolution",
                }),
                expected_generation=1,
            )
            bumped["done"] = True
        return value

    monkeypatch.setattr(AWikiEnvironmentReferenceResolver, "resolve", drifting_resolve)
    backend = build_sqlite_supervised_claude_job_backend(
        database_path=db,
        operations=(definition,),
        execution_store=SQLiteExecutionStore(tmp_path / "execution-drift.sqlite"),
        supervised=supervised,
        drive_root=drive,
        clock=lambda: NOW,
        claude_executable="claude",
        poll_interval_seconds=0.001,
    )

    result = backend.execute(definition.operation_ref, context(definition))

    assert bumped["done"] is True
    assert result.success is False
    assert result.error_code == "PROVIDER_CONFIGURATION_STALE"
    assert result.recovery_classification is RecoveryClassification.NO_MUTATION
    assert supervised.plans == []


def test_production_builder_does_not_touch_secret_source_when_provider_missing(tmp_path: Path) -> None:
    db = tmp_path / "empty-control.sqlite"
    drive = tmp_path / "A-Wiki-Data"
    drive.mkdir()
    definition = operation(tmp_path / "worktree", provider_database_path=db)
    supervised = CapturingRecoverySupervised()
    backend = build_sqlite_supervised_claude_job_backend(
        database_path=db,
        operations=(definition,),
        execution_store=SQLiteExecutionStore(tmp_path / "execution.sqlite"),
        supervised=supervised,
        drive_root=drive,
        clock=lambda: NOW,
        claude_executable="claude",
        poll_interval_seconds=0.001,
    )

    result = backend.execute(definition.operation_ref, context(definition))

    assert result.success is False
    assert result.error_code == "PROVIDER_UNAVAILABLE"
    assert result.recovery_classification is RecoveryClassification.NO_MUTATION
    assert supervised.plans == []

def test_stale_provider_fails_before_secret_resolution_or_launch(tmp_path: Path) -> None:
    db = tmp_path / "stale-control.sqlite"
    store = seeded_store(db)
    stale = ProviderObservation(
        provider_id="provider-glm-shared",
        health=ProviderHealth.AVAILABLE,
        observed_at=datetime(2026, 8, 30, 4, 0, tzinfo=timezone.utc),
        provenance="fake:stale",
        quota=observation().quota,
        configuration_generation=1,
    )
    store.save_observation(stale)
    drive = tmp_path / "A-Wiki-Data"
    drive.mkdir()
    definition = operation(tmp_path / "worktree", provider_database_path=db)
    supervised = CapturingRecoverySupervised()
    backend = build_sqlite_supervised_claude_job_backend(
        database_path=db, operations=(definition,),
        execution_store=SQLiteExecutionStore(tmp_path / "execution.sqlite"),
        supervised=supervised, drive_root=drive, clock=lambda: NOW,
        claude_executable="claude", poll_interval_seconds=0.001,
    )

    result = backend.execute(definition.operation_ref, context(definition))
    assert result.error_code == "PROVIDER_UNAVAILABLE"
    assert supervised.plans == []


def test_missing_endpoint_fails_before_secret_resolution_or_launch(tmp_path: Path) -> None:
    db = tmp_path / "missing-endpoint.sqlite"
    seeded_store(db, include_endpoint=False)
    drive = tmp_path / "A-Wiki-Data"
    drive.mkdir()
    definition = operation(tmp_path / "worktree", provider_database_path=db)
    supervised = CapturingRecoverySupervised()
    backend = build_sqlite_supervised_claude_job_backend(
        database_path=db, operations=(definition,),
        execution_store=SQLiteExecutionStore(tmp_path / "execution.sqlite"),
        supervised=supervised, drive_root=drive, clock=lambda: NOW,
        claude_executable="claude", poll_interval_seconds=0.001,
    )

    result = backend.execute(definition.operation_ref, context(definition))
    assert result.error_code == "PROVIDER_UNAVAILABLE"
    assert result.recovery_classification is RecoveryClassification.NO_MUTATION
    assert supervised.plans == []


def test_corrupt_provider_row_fails_closed_as_unusable_state(tmp_path: Path) -> None:
    import sqlite3

    db = tmp_path / "corrupt-provider.sqlite"
    store = seeded_store(db)
    with sqlite3.connect(db) as connection:
        connection.execute(
            "UPDATE provider_configurations SET protocol_family = ? WHERE provider_id = ?",
            ("NOT_A_PROTOCOL", "provider-glm-shared"),
        )
        connection.commit()

    resolver = SQLiteClaudeCodeProviderResolver(store)
    assert resolver.resolve("provider-glm-shared") is None


def test_production_builder_bootstraps_provider_schema_without_touching_existing_data(tmp_path: Path) -> None:
    import sqlite3

    db = tmp_path / "installed-control.sqlite"
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE existing_state(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO existing_state(key, value) VALUES('keep', 'unchanged')")
        connection.commit()
    drive = tmp_path / "A-Wiki-Data"
    drive.mkdir()
    definition = operation(tmp_path / "worktree-bootstrap", provider_database_path=db)
    supervised = CapturingRecoverySupervised()

    build_sqlite_supervised_claude_job_backend(
        database_path=db,
        operations=(definition,),
        execution_store=SQLiteExecutionStore(tmp_path / "execution-bootstrap.sqlite"),
        supervised=supervised,
        drive_root=drive,
        clock=lambda: NOW,
    )
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT value FROM existing_state WHERE key='keep'").fetchone()[0] == "unchanged"
        names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"provider_configurations", "provider_endpoints", "provider_observations", "provider_admissions"} <= names
    assert supervised.plans == []


class FakeQuotaTransport:
    def __init__(self, status: int, payload: object) -> None:
        self.status = status
        self.payload = payload
        self.calls = []

    def get_json(self, url: str, *, authorization: str, timeout_seconds: float):
        self.calls.append((url, authorization, timeout_seconds))
        return self.status, self.payload


def test_refresh_zai_provider_observation_uses_drive_secret_and_persists_quota(tmp_path: Path) -> None:
    db = tmp_path / "quota-control.sqlite"
    store = SQLiteProviderConfigStore(db)
    configured = profile()
    store.save_provider(configured)
    store.save_endpoint(ProviderEndpointConfig(configured.endpoint_ref, "https://api.z.ai/api/anthropic"))
    drive = tmp_path / "A-Wiki-Data"
    (drive / "secrets").mkdir(parents=True)
    (drive / "secrets" / "global.env").write_text("ANTHROPIC_API_KEY=quota-secret\n", encoding="utf-8")
    transport = FakeQuotaTransport(200, {"data": {"limits": [{
        "type": "TOKENS_LIMIT", "usage": 100, "currentValue": 40,
        "remaining": 60, "nextResetTime": 1788084000000,
    }]}})
    observed = refresh_zai_provider_observation(
        database_path=db,
        provider_id=configured.provider_id,
        drive_root=drive,
        clock=lambda: NOW,
        transport=transport,
    )

    assert observed is not None
    assert observed.health is ProviderHealth.AVAILABLE
    assert observed.quota is not None
    assert observed.quota.window_type == "5h"
    assert observed.quota.remaining == 60
    assert store.get_observation(configured.provider_id) == observed
    assert transport.calls[0][1] == "quota-secret"
    assert "quota-secret" not in observed.provenance


def test_refresh_zai_provider_observation_rejects_non_zai_route_without_secret_read(tmp_path: Path) -> None:
    db = tmp_path / "quota-non-zai.sqlite"
    store = SQLiteProviderConfigStore(db)
    configured = profile()
    store.save_provider(configured)
    store.save_endpoint(ProviderEndpointConfig(configured.endpoint_ref, "https://proxy.example/v1"))
    transport = FakeQuotaTransport(200, {})

    observed = refresh_zai_provider_observation(
        database_path=db,
        provider_id=configured.provider_id,
        clock=lambda: NOW,
        transport=transport,
        environment={},
        home=tmp_path / "missing-home",
    )
    assert observed is not None
    assert observed.health is ProviderHealth.UNAVAILABLE
    assert observed.quota is None
    assert transport.calls == []
    assert store.get_observation(configured.provider_id) == observed


def test_resolver_treats_generation_mismatched_and_legacy_observations_as_unavailable(
    tmp_path: Path,
) -> None:
    db = tmp_path / "control.sqlite"
    store = seeded_store(db)
    resolver = SQLiteClaudeCodeProviderResolver(store)

    fresh = resolver.resolve("provider-glm-shared")
    assert fresh is not None and fresh.observation is not None

    store.save_provider(
        ProviderConfiguration(**{**profile().as_dict(), "display_name": "Edited"}),
        expected_generation=1,
    )
    mismatched = resolver.resolve("provider-glm-shared")
    assert mismatched is not None
    assert mismatched.observation is None, (
        "generation-1 observation must be unavailable for generation-2 configuration"
    )

    import sqlite3 as _sqlite3

    legacy_sql = "UPDATE provider_observations SET configuration_generation=NULL WHERE provider_id=?"
    with _sqlite3.connect(db) as connection:
        connection.execute(legacy_sql, ("provider-glm-shared",))
        connection.commit()
    legacy = resolver.resolve("provider-glm-shared")
    assert legacy is not None and legacy.observation is None


def test_refresh_observation_is_bound_to_captured_generation(tmp_path: Path) -> None:
    db = tmp_path / "quota-stale.sqlite"
    store = SQLiteProviderConfigStore(db)
    configured = profile()
    store.save_endpoint(
        ProviderEndpointConfig(configured.endpoint_ref, "https://api.z.ai/api/anthropic")
    )
    store.save_provider(configured)
    drive = tmp_path / "A-Wiki-Data"
    (drive / "secrets").mkdir(parents=True)
    (drive / "secrets" / "global.env").write_text(
        "ANTHROPIC_API_KEY=quota-secret\n", encoding="utf-8"
    )
    store.save_observation(observation())

    class BumpingTransport:
        """Z.ai-shaped transport that lands a config edit mid-probe."""

        def get_json(self, url, *, authorization, timeout_seconds):
            store.save_provider(
                ProviderConfiguration(
                    **{**configured.as_dict(), "display_name": "Edited"}
                ),
                expected_generation=1,
            )
            return 200, {
                "data": {
                    "limits": [{
                        "type": "TOKENS_LIMIT", "usage": 100, "currentValue": 40,
                        "remaining": 60, "nextResetTime": 1788084000000,
                    }]
                }
            }

    from a_conductor.provider_config_store import ProviderConfigStoreError
    import pytest as _pytest

    with _pytest.raises(ProviderConfigStoreError) as stale_save:
        refresh_zai_provider_observation(
            database_path=db,
            provider_id=configured.provider_id,
            drive_root=drive,
            clock=lambda: NOW,
            transport=BumpingTransport(),
        )
    assert stale_save.value.code == "PROVIDER_OBSERVATION_GENERATION_STALE"

    import sqlite3 as _sqlite3

    select_sql = (
        "SELECT configuration_generation FROM provider_observations "
        "WHERE provider_id=?"
    )
    with _sqlite3.connect(db) as connection:
        saved = connection.execute(select_sql, (configured.provider_id,)).fetchone()[0]
    assert saved == 1, "stale in-flight probe must never publish generation-2 evidence"


def test_resolver_fails_closed_on_corrupt_endpoint_generation(tmp_path: Path) -> None:
    import sqlite3

    db = tmp_path / "corrupt-endpoint-generation.sqlite"
    store = seeded_store(db)
    with sqlite3.connect(db) as connection:
        connection.execute(
            "UPDATE provider_endpoints SET base_url=?, generation=0 WHERE endpoint_ref=?",
            ("https://new-route.example/v1", profile().endpoint_ref),
        )
        connection.commit()

    assert SQLiteClaudeCodeProviderResolver(store).resolve("provider-glm-shared") is None
