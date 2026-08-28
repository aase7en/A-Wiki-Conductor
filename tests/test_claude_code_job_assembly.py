from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from a_conductor.claude_code_harness import (
    HarnessDispatch,
    MutationIntent,
    TaskPacketFile,
)
from a_conductor.claude_code_job_assembly import build_supervised_claude_job_backend
from a_conductor.claude_code_job_backend import (
    ClaudeCodeOperationDefinition,
    ClaudeCodeProviderState,
    StaticClaudeCodeProviderResolver,
)
from a_conductor.domain import RecoveryClassification
from a_conductor.execution_record import ExecutionProcessState
from a_conductor.execution_store import SQLiteExecutionStore
from a_conductor.job_execution import JobExecutionContext
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
)
from a_conductor.supervised_child import SupervisedChildResult
from a_conductor.supervised_execution import (
    SupervisedCollectOutcome,
    SupervisedInspection,
    SupervisedInspectionState,
    SupervisedLaunchOutcome,
)

NOW = datetime(2026, 8, 28, 14, 0, tzinfo=timezone.utc)


def profile() -> ProviderConfiguration:
    return ProviderConfiguration(
        provider_id="provider-glm-shared",
        display_name="GLM Shared",
        provider_type="cloud-proxy",
        protocol_family=ProtocolFamily.ANTHROPIC_MESSAGES,
        endpoint_ref="provider-config:glm/base-url",
        credential_ref="secret-ref:provider/glm/main",
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


def observation(health: ProviderHealth = ProviderHealth.AVAILABLE) -> ProviderObservation:
    return ProviderObservation(
        provider_id="provider-glm-shared",
        health=health,
        observed_at=NOW,
        provenance="fake:test",
    )


def provider_state(*, health: ProviderHealth = ProviderHealth.AVAILABLE) -> ClaudeCodeProviderState:
    configured = profile()
    return ClaudeCodeProviderState(
        profile=configured,
        endpoint=ProviderEndpointConfig(configured.endpoint_ref, "https://provider.example/v1"),
        observation=observation(health),
    )

def packet(root: Path, ref: str, name: str) -> TaskPacketFile:
    path = root / ".a-conductor" / "task-packets" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# bounded read-only task\n", encoding="utf-8")
    return TaskPacketFile(
        task_contract_ref=ref,
        path=str(path),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def operation(
    root: Path,
    *,
    job_id: str = "job-one",
    operation_ref: str = "op:one",
    work_order_ref: str = "docs/work-orders/WO-one.md",
    worker_id: str = "a-worker-01",
    branch: str | None = "feat/one",
    head: str = "a" * 40,
) -> ClaudeCodeOperationDefinition:
    dispatch = HarnessDispatch(
        execution_id=job_id,
        task_contract_ref=work_order_ref,
        project_id="project-1",
        worktree_path=str(root),
        expected_branch=branch,
        expected_head=head,
        provider_id="provider-glm-shared",
        model_id="glm-5.3",
        harness_strategy=HarnessStrategy.CLAUDE_CODE_CLI,
        mutation_intent=MutationIntent.READ_ONLY,
        timeout_seconds=30,
        max_output_bytes=4096,
        effort_level="MAX",
    )
    return ClaudeCodeOperationDefinition(
        operation_ref=operation_ref,
        dispatch=dispatch,
        packet=packet(root, work_order_ref, operation_ref.replace(":", "-")),
        worker_id=worker_id,
    )


def context(
    definition: ClaudeCodeOperationDefinition,
    *,
    attempt_no: int = 1,
) -> JobExecutionContext:
    return JobExecutionContext(
        job_id=definition.dispatch.execution_id,
        work_order_ref=definition.dispatch.task_contract_ref,
        project_id=definition.dispatch.project_id,
        worker_id=definition.worker_id,
        attempt_no=attempt_no,
        max_attempts=3,
    )

class CountingResolver:
    def __init__(self, values: dict[str, str]) -> None:
        self.values = values
        self.calls: list[str] = []

    def resolve(self, reference: str) -> str:
        self.calls.append(reference)
        return self.values[reference]


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

def build_backend(
    tmp_path: Path,
    definitions: tuple[ClaudeCodeOperationDefinition, ...],
    *,
    states: dict[str, ClaudeCodeProviderState] | None = None,
    resolver: CountingResolver | None = None,
    supervised=None,
):
    state = provider_state()
    resolver = resolver or CountingResolver(
        {
            state.profile.endpoint_ref: state.endpoint.base_url,
            state.profile.credential_ref: "super-secret-token",
        }
    )
    supervised = supervised or CapturingRecoverySupervised()
    backend = build_supervised_claude_job_backend(
        operations=definitions,
        execution_store=SQLiteExecutionStore(tmp_path / "execution.sqlite"),
        supervised=supervised,
        reference_resolver=resolver,
        provider_resolver=StaticClaudeCodeProviderResolver(
            states if states is not None else {state.profile.provider_id: state}
        ),
        clock=lambda: NOW,
        claude_executable="claude",
        poll_interval_seconds=0.001,
    )
    return backend, resolver, supervised

def test_provider_unavailable_does_not_resolve_or_launch(tmp_path: Path) -> None:
    definition = operation(tmp_path)
    configured = profile()
    resolver = CountingResolver(
        {
            configured.endpoint_ref: "https://provider.example/v1",
            configured.credential_ref: "must-not-read",
        }
    )
    backend, resolver, supervised = build_backend(
        tmp_path,
        (definition,),
        states={},
        resolver=resolver,
    )

    result = backend.execute(definition.operation_ref, context(definition))

    assert result.success is False
    assert result.error_code == "PROVIDER_UNAVAILABLE"
    assert result.recovery_classification is RecoveryClassification.NO_MUTATION
    assert resolver.calls == []
    assert supervised.plans == []

def test_rate_limited_provider_does_not_resolve_or_launch(tmp_path: Path) -> None:
    definition = operation(tmp_path)
    state = provider_state(health=ProviderHealth.RATE_LIMITED)
    resolver = CountingResolver(
        {
            state.profile.endpoint_ref: state.endpoint.base_url,
            state.profile.credential_ref: "must-not-read",
        }
    )
    backend, resolver, supervised = build_backend(
        tmp_path,
        (definition,),
        states={state.profile.provider_id: state},
        resolver=resolver,
    )

    result = backend.execute(definition.operation_ref, context(definition))

    assert result.success is False
    assert result.error_code == "RATE_LIMITED"
    assert result.recovery_classification is RecoveryClassification.NO_MUTATION
    assert resolver.calls == []
    assert supervised.plans == []

def test_missing_branch_fails_closed_before_reference_resolution_or_launch(tmp_path: Path) -> None:
    definition = operation(tmp_path, branch=None)
    state = provider_state()
    resolver = CountingResolver(
        {
            state.profile.endpoint_ref: state.endpoint.base_url,
            state.profile.credential_ref: "must-not-read",
        }
    )
    backend, resolver, supervised = build_backend(
        tmp_path,
        (definition,),
        resolver=resolver,
    )

    result = backend.execute(definition.operation_ref, context(definition))

    assert result.success is False
    assert result.error_code == "POLICY_DENIED"
    assert result.recovery_classification is RecoveryClassification.NO_MUTATION
    assert resolver.calls == []
    assert supervised.plans == []

def test_each_durable_job_builds_exact_identity_bound_supervised_plan(tmp_path: Path) -> None:
    one_root = tmp_path / "one"
    two_root = tmp_path / "two"
    one_root.mkdir()
    two_root.mkdir()
    one = operation(
        one_root,
        job_id="job-one",
        operation_ref="op:one",
        work_order_ref="docs/work-orders/WO-one.md",
        worker_id="a-worker-01",
        branch="feat/one",
        head="a" * 40,
    )
    two = operation(
        two_root,
        job_id="job-two",
        operation_ref="op:two",
        work_order_ref="docs/work-orders/WO-two.md",
        worker_id="a-worker-02",
        branch="feat/two",
        head="b" * 40,
    )
    secret = "super-secret-token"
    state = provider_state()
    resolver = CountingResolver(
        {
            state.profile.endpoint_ref: state.endpoint.base_url,
            state.profile.credential_ref: secret,
        }
    )
    supervised = CapturingRecoverySupervised()
    backend, _, _ = build_backend(
        tmp_path,
        (one, two),
        resolver=resolver,
        supervised=supervised,
    )

    first = backend.execute(one.operation_ref, context(one))
    second = backend.execute(two.operation_ref, context(two))

    assert first.success is False and second.success is False
    assert first.error_code == "HARNESS_FAILED"
    assert second.error_code == "HARNESS_FAILED"
    assert len(supervised.plans) == 2
    first_plan, second_plan = supervised.plans
    assert first_plan.record.job_id == "job-one"
    assert first_plan.record.work_order_ref == "docs/work-orders/WO-one.md"
    assert first_plan.record.project_id == "project-1"
    assert first_plan.record.worker_id == "a-worker-01"
    assert first_plan.record.branch == "feat/one"
    assert first_plan.record.head_before == "a" * 40
    assert second_plan.record.job_id == "job-two"
    assert second_plan.record.work_order_ref == "docs/work-orders/WO-two.md"
    assert second_plan.record.worker_id == "a-worker-02"
    assert second_plan.record.branch == "feat/two"
    assert second_plan.record.head_before == "b" * 40
    assert first_plan.record.command_fingerprint != second_plan.record.command_fingerprint
    for plan in supervised.plans:
        assert secret not in plan.record.command_fingerprint
        assert secret not in plan.record.command_summary
        assert secret not in plan.record.runtime_profile_ref
        assert secret not in repr(plan)

class StoringRecoverySupervised:
    def __init__(self, store: SQLiteExecutionStore) -> None:
        self.store = store
        self.launch_count = 0
        self.records = []

    def launch(self, plan):
        self.launch_count += 1
        self.records.append(plan.record)
        created = self.store.create(plan.record)
        recovered = self.store.set_execution_state(
            created.execution_id,
            ExecutionProcessState.RECOVERY_REQUIRED,
            expected_version=created.version,
            evidence_ref="test:unknown",
        )
        return SupervisedLaunchOutcome(
            record=recovered,
            supervisor_pid=1234,
            child_pid=None,
            recovery_required=True,
            error_code="TEST_UNKNOWN",
        )

    def inspect(self, execution_id):
        raise AssertionError("inspect must not run")

    def collect(self, execution_id, *, expected_version):
        raise AssertionError("collect must not run")

def test_recovery_unknown_never_blind_relaunches_same_fingerprint(tmp_path: Path) -> None:
    definition = operation(tmp_path)
    state = provider_state()
    secret = "super-secret-token"
    resolver = CountingResolver(
        {
            state.profile.endpoint_ref: state.endpoint.base_url,
            state.profile.credential_ref: secret,
        }
    )
    execution_store = SQLiteExecutionStore(tmp_path / "execution.sqlite")
    supervised = StoringRecoverySupervised(execution_store)
    backend = build_supervised_claude_job_backend(
        operations=(definition,),
        execution_store=execution_store,
        supervised=supervised,
        reference_resolver=resolver,
        provider_resolver=StaticClaudeCodeProviderResolver({state.profile.provider_id: state}),
        clock=lambda: NOW,
        claude_executable="claude",
        poll_interval_seconds=0.001,
    )

    first = backend.execute(definition.operation_ref, context(definition))
    second = backend.execute(definition.operation_ref, context(definition))

    assert first.success is False
    assert second.success is False
    assert supervised.launch_count == 1
    fingerprint = supervised.records[0].command_fingerprint
    records = execution_store.find_by_fingerprint(fingerprint)
    assert len(records) == 1
    assert records[0].execution_state is ExecutionProcessState.RECOVERY_REQUIRED
    assert secret not in records[0].command_fingerprint
    assert secret not in records[0].command_summary

class SuccessfulSupervised:
    def __init__(self, store: SQLiteExecutionStore) -> None:
        self.store = store
        self.plans = []

    def launch(self, plan):
        self.plans.append(plan)
        created = self.store.create(plan.record)
        run_dir = Path(plan.runtime_root) / created.run_dir_ref
        run_dir.mkdir(parents=True, exist_ok=True)
        (Path(plan.runtime_root) / created.stdout_ref).write_text(
            json.dumps({"type": "result", "is_error": False, "result": "done"}),
            encoding="utf-8",
        )
        (Path(plan.runtime_root) / created.stderr_ref).write_text("", encoding="utf-8")
        return SupervisedLaunchOutcome(
            record=created,
            supervisor_pid=1234,
            child_pid=5678,
            recovery_required=False,
        )

    def inspect(self, execution_id):
        return SupervisedInspection(
            execution_id=execution_id,
            state=SupervisedInspectionState.RESULT_AVAILABLE,
            supervisor_pid=1234,
            result_available=True,
            recovery_required=False,
        )

    def collect(self, execution_id, *, expected_version):
        record = self.store.get(execution_id)
        assert record.version == expected_version
        result = SupervisedChildResult(
            schema_version=1,
            execution_id=execution_id,
            child_pid=5678,
            exit_code=0,
            started_at="2026-08-28T14:00:00Z",
            finished_at="2026-08-28T14:00:01Z",
        )
        return SupervisedCollectOutcome(
            record=record,
            result=result,
            recovery_required=False,
        )

def test_successful_supervised_chain_returns_digest_only(tmp_path: Path) -> None:
    definition = operation(tmp_path)
    state = provider_state()
    secret = "super-secret-token"
    resolver = CountingResolver({
        state.profile.endpoint_ref: state.endpoint.base_url,
        state.profile.credential_ref: secret,
    })
    execution_store = SQLiteExecutionStore(tmp_path / "execution.sqlite")
    supervised = SuccessfulSupervised(execution_store)
    backend = build_supervised_claude_job_backend(
        operations=(definition,),
        execution_store=execution_store,
        supervised=supervised,
        reference_resolver=resolver,
        provider_resolver=StaticClaudeCodeProviderResolver({state.profile.provider_id: state}),
        clock=lambda: NOW,
        claude_executable="claude",
        poll_interval_seconds=0.001,
    )

    result = backend.execute(definition.operation_ref, context(definition))

    assert result.success is True
    assert result.evidence_ref is not None
    assert result.evidence_ref.startswith("claude-harness-evidence:")
    assert secret not in result.evidence_ref
    assert resolver.calls == [state.profile.endpoint_ref, state.profile.credential_ref]
    assert len(supervised.plans) == 1

def test_successful_assembly_reaches_verifying_via_durable_coordinator(tmp_path: Path) -> None:
    from a_conductor.domain import TaskState
    from a_conductor.job_execution import DurableJobExecutionCoordinator
    from a_conductor.job_store import SQLiteJobStore

    definition = operation(tmp_path)
    state = provider_state()
    resolver = CountingResolver({
        state.profile.endpoint_ref: state.endpoint.base_url,
        state.profile.credential_ref: "super-secret-token",
    })
    execution_store = SQLiteExecutionStore(tmp_path / "execution.sqlite")
    supervised = SuccessfulSupervised(execution_store)
    backend = build_supervised_claude_job_backend(
        operations=(definition,), execution_store=execution_store,
        supervised=supervised, reference_resolver=resolver,
        provider_resolver=StaticClaudeCodeProviderResolver({state.profile.provider_id: state}),
        clock=lambda: NOW, claude_executable="claude", poll_interval_seconds=0.001,
    )

    store = SQLiteJobStore(tmp_path / "control.sqlite")
    created = store.create_job(job_id="job-one", work_order_ref="docs/work-orders/WO-one.md", project_id="project-1")
    ready = store.transition("job-one", TaskState.READY, expected_version=created.version)
    claimed = store.transition("job-one", TaskState.CLAIMED, expected_version=ready.version, worker_id="a-worker-01")
    gated = store.transition("job-one", TaskState.GATING, expected_version=claimed.version, worker_id="a-worker-01")
    outcome = DurableJobExecutionCoordinator(store=store, backend=backend).execute(
        "job-one", expected_version=gated.version, worker_id="a-worker-01", operation_ref="op:one"
    )
    assert outcome.success is True
    assert outcome.job.state is TaskState.VERIFYING
    assert len(supervised.plans) == 1
