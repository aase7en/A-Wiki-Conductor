from __future__ import annotations

import hashlib
import json

import pytest
from datetime import datetime, timezone
from pathlib import Path

from a_conductor.claude_code_harness import (
    ClaudeCodeHarnessAdapter,
    ClaudeCodeRunnerResult,
    HarnessDispatch,
    MutationIntent,
    TaskPacketFile,
)
from a_conductor.claude_code_job_backend import (
    ClaudeCodeJobBackend,
    ClaudeCodeOperationDefinition,
    ClaudeCodeProviderState,
    StaticClaudeCodeProviderResolver,
)
from a_conductor.domain import RecoveryClassification, TaskState
from a_conductor.job_execution import DurableJobExecutionCoordinator, JobExecutionContext
from a_conductor.job_store import SQLiteJobStore
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

NOW = datetime(2026, 8, 28, 9, 45, tzinfo=timezone.utc)


def profile() -> ProviderConfiguration:
    return ProviderConfiguration(
        provider_id="provider-glm-shared",
        display_name="GLM Shared",
        provider_type="cloud-proxy",
        protocol_family=ProtocolFamily.ANTHROPIC_MESSAGES,
        endpoint_ref="provider-config:glm-shared/base-url",
        credential_ref="secret-ref:provider/glm-shared/main",
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


class FakeRunner:
    def __init__(self, result: ClaudeCodeRunnerResult) -> None:
        self.result = result
        self.calls = []

    def run(self, invocation):
        self.calls.append(invocation)
        return self.result


def runner_result(*, exit_code=0, payload=None, stderr="", timed_out=False):
    if payload is None:
        payload = {"type": "result", "is_error": False, "result": "done"}
    return ClaudeCodeRunnerResult(
        exit_code=exit_code,
        stdout=json.dumps(payload),
        stderr=stderr,
        timed_out=timed_out,
    )


def packet(worktree: Path, ref: str) -> TaskPacketFile:
    path = worktree / ".a-conductor" / "task-packets" / "node.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# bounded read-only task\n", encoding="utf-8")
    return TaskPacketFile(
        task_contract_ref=ref,
        path=str(path),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def operation(worktree: Path, *, job_id="job-claude", worker_id="a-worker-01", operation_ref="op:claude-node"):
    ref = "docs/work-orders/WO-node.md"
    dispatch = HarnessDispatch(
        execution_id=job_id,
        task_contract_ref=ref,
        project_id="project-1",
        worktree_path=str(worktree),
        expected_branch="feat/node",
        expected_head="a" * 40,
        provider_id="provider-glm-shared",
        model_id="glm-5.3",
        harness_strategy=HarnessStrategy.CLAUDE_CODE_CLI,
        mutation_intent=MutationIntent.READ_ONLY,
        timeout_seconds=60,
        max_output_bytes=4096,
        effort_level="MAX",
    )
    return ClaudeCodeOperationDefinition(
        operation_ref=operation_ref,
        dispatch=dispatch,
        packet=packet(worktree, ref),
        worker_id=worker_id,
    )


def backend(worktree: Path, runner: FakeRunner, *, state=None):
    p = profile()
    state = state or ClaudeCodeProviderState(
        profile=p,
        endpoint=ProviderEndpointConfig(p.endpoint_ref, "https://api.example.test/v1"),
        observation=observation(),
    )
    return ClaudeCodeJobBackend(
        operations=(operation(worktree),),
        adapter=ClaudeCodeHarnessAdapter(runner=runner),
        provider_resolver=StaticClaudeCodeProviderResolver({p.provider_id: state}),
        clock=lambda: NOW,
    )


def gating_store(tmp_path: Path):
    store = SQLiteJobStore(tmp_path / "control.sqlite")
    created = store.create_job(
        job_id="job-claude",
        work_order_ref="docs/work-orders/WO-node.md",
        project_id="project-1",
    )
    ready = store.transition("job-claude", TaskState.READY, expected_version=created.version)
    claimed = store.transition(
        "job-claude",
        TaskState.CLAIMED,
        expected_version=ready.version,
        worker_id="a-worker-01",
    )
    gating = store.transition(
        "job-claude",
        TaskState.GATING,
        expected_version=claimed.version,
        worker_id="a-worker-01",
    )
    return store, gating


def execute(tmp_path: Path, job_backend: ClaudeCodeJobBackend):
    store, gating = gating_store(tmp_path)
    outcome = DurableJobExecutionCoordinator(store=store, backend=job_backend).execute(
        "job-claude",
        expected_version=gating.version,
        worker_id="a-worker-01",
        operation_ref="op:claude-node",
    )
    return store, outcome


def test_success_runs_through_existing_coordinator_and_persists_only_evidence_digest(tmp_path: Path) -> None:
    runner = FakeRunner(runner_result(payload={"type": "result", "is_error": False, "result": "private-output"}))
    store, outcome = execute(tmp_path, backend(tmp_path, runner))

    assert outcome.success is True
    assert outcome.job.state is TaskState.VERIFYING
    assert outcome.evidence_ref is not None
    assert outcome.evidence_ref.startswith("claude-harness-evidence:")
    assert len(runner.calls) == 1
    database = (tmp_path / "control.sqlite").read_bytes()
    assert b"private-output" not in database
    assert outcome.evidence_ref.encode() in database


def test_timeout_is_typed_unknown_recovery_not_success(tmp_path: Path) -> None:
    runner = FakeRunner(runner_result(timed_out=True))
    _, outcome = execute(tmp_path, backend(tmp_path, runner))

    assert outcome.success is False
    assert outcome.job.state is TaskState.RECOVERY_NEEDED
    assert outcome.job.recovery_classification is RecoveryClassification.UNKNOWN
    assert outcome.error_code == "EXECUTION_STATE_UNKNOWN"
    assert len(runner.calls) == 1


def test_rate_limited_provider_fails_before_runner_with_typed_reason(tmp_path: Path) -> None:
    runner = FakeRunner(runner_result())
    p = profile()
    state = ClaudeCodeProviderState(
        profile=p,
        endpoint=ProviderEndpointConfig(p.endpoint_ref, "https://api.example.test/v1"),
        observation=observation(ProviderHealth.RATE_LIMITED),
    )
    _, outcome = execute(tmp_path, backend(tmp_path, runner, state=state))

    assert outcome.success is False
    assert outcome.job.state is TaskState.RECOVERY_NEEDED
    assert outcome.job.recovery_classification is RecoveryClassification.NO_MUTATION
    assert outcome.error_code == "RATE_LIMITED"
    assert runner.calls == []


def test_harness_reported_failure_is_typed_no_mutation(tmp_path: Path) -> None:
    runner = FakeRunner(
        runner_result(payload={"type": "result", "is_error": True, "result": "denied"})
    )
    _, outcome = execute(tmp_path, backend(tmp_path, runner))

    assert outcome.success is False
    assert outcome.job.recovery_classification is RecoveryClassification.NO_MUTATION
    assert outcome.error_code == "HARNESS_FAILED"


def test_backend_identity_mismatch_fails_closed_before_runner(tmp_path: Path) -> None:
    runner = FakeRunner(runner_result())
    job_backend = backend(tmp_path, runner)
    with pytest.raises(ValueError, match="CLAUDE_JOB_IDENTITY_MISMATCH"):
        job_backend.execute(
            "op:claude-node",
            JobExecutionContext(
                job_id="job-claude",
                work_order_ref="docs/work-orders/WO-node.md",
                project_id="project-1",
                worker_id="a-worker-02",
                attempt_no=1,
                max_attempts=3,
            ),
        )
    assert runner.calls == []


def test_raw_model_output_and_stderr_are_not_persisted(tmp_path: Path) -> None:
    runner = FakeRunner(
        runner_result(
            payload={"type": "result", "is_error": False, "result": "TOP-SECRET-MODEL-TEXT"},
            stderr="PRIVATE-STDERR",
        )
    )
    store, outcome = execute(tmp_path, backend(tmp_path, runner))
    database = (tmp_path / "control.sqlite").read_bytes()
    assert outcome.success is True
    assert b"TOP-SECRET-MODEL-TEXT" not in database
    assert b"PRIVATE-STDERR" not in database
    assert outcome.evidence_ref.encode() in database


def test_evidence_digest_is_bound_to_durable_execution_identity(tmp_path: Path) -> None:
    runner = FakeRunner(runner_result(payload={"type": "result", "is_error": False, "result": "same"}))
    p = profile()
    state = ClaudeCodeProviderState(
        profile=p,
        endpoint=ProviderEndpointConfig(p.endpoint_ref, "https://api.example.test/v1"),
        observation=observation(),
    )
    one_root, two_root = tmp_path / "one", tmp_path / "two"
    one_root.mkdir(); two_root.mkdir()
    job_backend = ClaudeCodeJobBackend(
        operations=(
            operation(one_root, job_id="job-one", operation_ref="op:one"),
            operation(two_root, job_id="job-two", operation_ref="op:two"),
        ),
        adapter=ClaudeCodeHarnessAdapter(runner=runner),
        provider_resolver=StaticClaudeCodeProviderResolver({p.provider_id: state}),
        clock=lambda: NOW,
    )
    one = job_backend.execute(
        "op:one",
        JobExecutionContext(
            job_id="job-one",
            work_order_ref="docs/work-orders/WO-node.md",
            project_id="project-1",
            worker_id="a-worker-01",
            attempt_no=1,
            max_attempts=3,
        ),
    )
    two = job_backend.execute(
        "op:two",
        JobExecutionContext(
            job_id="job-two",
            work_order_ref="docs/work-orders/WO-node.md",
            project_id="project-1",
            worker_id="a-worker-01",
            attempt_no=1,
            max_attempts=3,
        ),
    )
    assert one.success is True and two.success is True
    assert one.evidence_ref != two.evidence_ref
