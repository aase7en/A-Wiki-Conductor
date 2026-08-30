from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from a_conductor.claude_code_harness import HarnessDispatch, MutationIntent, TaskPacketFile
from a_conductor.claude_code_job_backend import ClaudeCodeOperationDefinition
from a_conductor.domain import RecoveryClassification
from a_conductor.execution_store import SQLiteExecutionStore
from a_conductor.job_execution import JobExecutionContext
from a_conductor.provider_config_store import SQLiteProviderConfigStore
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
    )

def seeded_store(db: Path, *, include_endpoint: bool = True) -> SQLiteProviderConfigStore:
    store = SQLiteProviderConfigStore(db)
    configured = profile()
    store.save_provider(configured)
    if include_endpoint:
        store.save_endpoint(
            ProviderEndpointConfig(configured.endpoint_ref, "https://provider.example/v1")
        )
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

def operation(root: Path) -> ClaudeCodeOperationDefinition:
    work_order = "docs/work-orders/WO-P1-114-auto-provider-runtime-assembly.md"
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
        operation_ref="op:provider-runtime",
        dispatch=dispatch,
        packet=packet,
        worker_id="a-worker-01",
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

def test_production_builder_resolves_db_endpoint_and_drive_secret_at_supervised_boundary(tmp_path: Path) -> None:
    db = tmp_path / "control.sqlite"
    seeded_store(db)
    drive = tmp_path / "A-Wiki-Data"
    (drive / "secrets").mkdir(parents=True)
    (drive / "secrets" / "global.env").write_text(
        "ANTHROPIC_API_KEY=top-secret-value\n", encoding="utf-8"
    )
    definition = operation(tmp_path / "worktree")
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

def test_production_builder_does_not_touch_secret_source_when_provider_missing(tmp_path: Path) -> None:
    db = tmp_path / "empty-control.sqlite"
    drive = tmp_path / "A-Wiki-Data"
    drive.mkdir()
    definition = operation(tmp_path / "worktree")
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
    )
    store.save_observation(stale)
    drive = tmp_path / "A-Wiki-Data"
    drive.mkdir()
    definition = operation(tmp_path / "worktree")
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
    definition = operation(tmp_path / "worktree")
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
