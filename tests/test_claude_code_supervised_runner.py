from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import os
import sys
import time
from pathlib import Path

import pytest

from a_conductor.claude_code_harness import (
    ClaudeCodeInvocation,
    EnvironmentBinding,
)
from a_conductor.claude_code_supervised_runner import (
    SupervisedClaudeCodeRunner,
    build_supervised_claude_code_runner,
    claude_runtime_profile_ref,
)
from a_conductor.native_execution import NativeCommandResult


class RecordingNativeRunner:
    def __init__(self, result: NativeCommandResult) -> None:
        self.result = result
        self.specs = []

    def run(self, spec):
        self.specs.append(spec)
        return self.result


class MappingResolver:
    def __init__(self, values: dict[str, str]) -> None:
        self.values = values
        self.calls: list[str] = []

    def resolve(self, reference: str) -> str:
        self.calls.append(reference)
        return self.values[reference]


def native_result(*, stdout: str = "{}", stderr: str = "", exit_code: int | None = 0, timed_out: bool = False):
    out = stdout.encode()
    err = stderr.encode()
    return NativeCommandResult(
        executable="claude.exe",
        argument_count=3,
        exit_code=exit_code,
        timed_out=timed_out,
        stdout=stdout,
        stderr=stderr,
        stdout_sha256=hashlib.sha256(out).hexdigest(),
        stderr_sha256=hashlib.sha256(err).hexdigest(),
        stdout_truncated=False,
        stderr_truncated=False,
    )


def invocation(root: Path, *, bindings=None) -> ClaudeCodeInvocation:
    return ClaudeCodeInvocation(
        argv=("claude.exe", "--print", "bounded-task"),
        cwd=str(root.resolve()),
        timeout_seconds=30,
        max_output_bytes=64 * 1024,
        environment_bindings=bindings or (
            EnvironmentBinding("ANTHROPIC_BASE_URL", "endpoint:glm", False),
            EnvironmentBinding("ANTHROPIC_AUTH_TOKEN", "secret-ref:glm/token", True),
        ),
    )


def test_resolves_refs_at_boundary_and_redacts_returned_streams(tmp_path: Path) -> None:
    secret = "super-secret-token"
    native = RecordingNativeRunner(
        native_result(stdout=f'{{"result":"{secret}"}}', stderr=f"warning {secret}")
    )
    resolver = MappingResolver({
        "endpoint:glm": "https://provider.example/v1",
        "secret-ref:glm/token": secret,
    })
    runner = SupervisedClaudeCodeRunner(
        project_root=tmp_path,
        native_runner=native,
        reference_resolver=resolver,
    )

    result = runner.run(invocation(tmp_path))

    assert result.exit_code == 0
    assert secret not in result.stdout
    assert secret not in result.stderr
    assert "[REDACTED]" in result.stdout
    assert len(native.specs) == 1
    spec = native.specs[0]
    assert spec.argv == ("claude.exe", "--print", "bounded-task")
    assert spec.cwd == "."
    assert secret not in "\x00".join(spec.argv)
    assert spec.environment_overrides == (
        ("ANTHROPIC_BASE_URL", "https://provider.example/v1"),
        ("ANTHROPIC_AUTH_TOKEN", secret),
    )
    assert resolver.calls == ["endpoint:glm", "secret-ref:glm/token"]


@pytest.mark.skipif(os.name != "nt", reason="Windows supervised integration")
def test_real_provider_output_is_redacted_before_durable_persistence(tmp_path: Path) -> None:
    from a_conductor.execution_store import SQLiteExecutionStore
    from a_conductor.owned_process import WindowsOwnedProcessController
    from a_conductor.supervised_execution import SupervisedExecutionService
    from a_conductor.windows_io import LoopbackReadyzHttpProbe, StrictPowerShellInspectionRunner
    from a_conductor.windows_observer import WindowsRuntimeObserver

    repo = tmp_path / "repo"
    repo.mkdir()
    runtime_python = getattr(sys, "_base_executable", sys.executable)
    python_name = Path(runtime_python).name
    secret = "wo119-synthetic-provider-auth-only-91ddf051"
    resolver = MappingResolver({
        "endpoint:glm": "https://provider.invalid/v1",
        "secret-ref:glm/token": secret,
    })
    store = SQLiteExecutionStore(tmp_path / "executions.sqlite")
    observer = WindowsRuntimeObserver(
        runner=StrictPowerShellInspectionRunner(),
        http_probe=LoopbackReadyzHttpProbe(),
    )
    supervised = SupervisedExecutionService(
        store=store,
        controller=WindowsOwnedProcessController(observer=observer),
        observer=observer,
        allowed_target_executables=(python_name,),
        python_executable=runtime_python,
        startup_poll_attempts=100,
        startup_poll_delay_seconds=0.02,
    )
    runner = build_supervised_claude_code_runner(
        project_root=repo,
        execution_store=store,
        supervised=supervised,
        reference_resolver=resolver,
        job_id="job-wo119-output-persistence-test",
        work_order_ref="docs/work-orders/WO-P1-119-provider-output-persistence-safety.md",
        project_id="wo119-isolated-test",
        worker_id="wo119-test-worker",
        branch="test/wo119",
        head_before="a" * 40,
        endpoint_ref="endpoint:glm",
        credential_ref="secret-ref:glm/token",
        claude_executable=python_name,
        poll_interval_seconds=0.02,
    )
    # The fake credential travels only through the approved environment binding.
    # Real child output goes through the canonical detached supervisor and files.
    child_code = (
        "import os; token=os.environ['ANTHROPIC_AUTH_TOKEN'].encode('utf-8'); "
        "os.write(1,b'out-before\\n'+token+b'\\nout-after\\n'); "
        "os.write(2,b'err-before\\n'+token+b'\\nerr-after\\n')"
    )
    base = invocation(repo)
    request = ClaudeCodeInvocation(
        argv=(runtime_python, "-c", child_code),
        cwd=base.cwd,
        timeout_seconds=30,
        max_output_bytes=base.max_output_bytes,
        environment_bindings=base.environment_bindings,
    )
    assert secret not in "\x00".join(request.argv)

    result = runner.run(request)

    assert result.exit_code == 0, result.stderr
    assert result.timed_out is False
    assert result.stdout == "out-before\n[REDACTED]\nout-after\n"
    assert result.stderr == "err-before\n[REDACTED]\nerr-after\n"
    artifact_paths = sorted((repo / "runs").glob("exec-*/*.log"))
    assert len(artifact_paths) == 2
    assert len({path.parent for path in artifact_paths}) == 1
    assert {path.name for path in artifact_paths} == {"stdout.log", "stderr.log"}
    persisted = {path.name: path.read_bytes() for path in artifact_paths}
    assert b"out-before\n" in persisted["stdout.log"]
    assert b"out-after\n" in persisted["stdout.log"]
    assert b"err-before\n" in persisted["stderr.log"]
    assert b"err-after\n" in persisted["stderr.log"]
    leaked = {name: secret.encode("utf-8") in raw for name, raw in persisted.items()}
    assert not any(leaked.values()), f"Fake credential persisted in durable streams: {leaked}"


@pytest.mark.skipif(os.name != "nt", reason="Windows supervised integration")
def test_live_provider_logs_are_sanitized_before_persistence(tmp_path: Path) -> None:
    from a_conductor.execution_store import SQLiteExecutionStore
    from a_conductor.owned_process import WindowsOwnedProcessController
    from a_conductor.supervised_execution import SupervisedExecutionService
    from a_conductor.windows_io import LoopbackReadyzHttpProbe, StrictPowerShellInspectionRunner
    from a_conductor.windows_observer import WindowsRuntimeObserver

    repo = tmp_path / "repo"
    repo.mkdir()
    runtime_python = getattr(sys, "_base_executable", sys.executable)
    python_name = Path(runtime_python).name
    marker_value = "wo119-sensitive-marker-8b461"
    resolver = MappingResolver({"endpoint:glm": "https://provider.invalid/v1", "secret-ref:glm/token": marker_value})

    store = SQLiteExecutionStore(tmp_path / "executions.sqlite")
    observer = WindowsRuntimeObserver(
        runner=StrictPowerShellInspectionRunner(), http_probe=LoopbackReadyzHttpProbe()
    )
    supervised = SupervisedExecutionService(
        store=store, controller=WindowsOwnedProcessController(observer=observer), observer=observer,
        allowed_target_executables=(python_name,), python_executable=runtime_python,
        startup_poll_attempts=100, startup_poll_delay_seconds=0.02,
    )
    runner = build_supervised_claude_code_runner(
        project_root=repo, execution_store=store, supervised=supervised,
        reference_resolver=resolver, job_id="job-wo119-live-test",
        work_order_ref="docs/work-orders/WO-P1-119-provider-output-persistence-safety.md",
        project_id="wo119-live-test", worker_id="wo119-live-worker",
        branch="test/wo119-live", head_before="b" * 40,
        endpoint_ref="endpoint:glm", credential_ref="secret-ref:glm/token",
        claude_executable=python_name, poll_interval_seconds=0.02,
    )

    ready_flag = repo / "child-ready.flag"
    child_code = (
        "import os,pathlib,time; v=os.environ['ANTHROPIC_AUTH_TOKEN'].encode('utf-8'); "
        "os.write(1,b'live-before\\n'+v+b'\\n'); os.write(2,b'live-err\\n'+v+b'\\n'); "
        f"pathlib.Path({str(ready_flag)!r}).write_text('ready',encoding='utf-8'); "
        "time.sleep(1.5); os.write(1,b'live-after\\n')"
    )
    base = invocation(repo)
    request = ClaudeCodeInvocation(
        argv=(runtime_python, "-c", child_code), cwd=base.cwd, timeout_seconds=30,
        max_output_bytes=base.max_output_bytes, environment_bindings=base.environment_bindings,
    )
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(runner.run, request)
        deadline = time.monotonic() + 8
        while not ready_flag.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert ready_flag.exists()
        assert not future.done()

        log_paths = sorted((repo / "runs").glob("exec-*/*.log"))
        while len(log_paths) < 2 and time.monotonic() < deadline:
            time.sleep(0.02)
            log_paths = sorted((repo / "runs").glob("exec-*/*.log"))
        assert len(log_paths) == 2
        live_bytes = b""
        while b"[REDACTED]" not in live_bytes and time.monotonic() < deadline:
            live_bytes = b"".join(path.read_bytes() for path in log_paths)
            assert marker_value.encode("utf-8") not in live_bytes
            if b"[REDACTED]" not in live_bytes:
                time.sleep(0.02)
        assert b"[REDACTED]" in live_bytes
        assert not future.done()
        result = future.result(timeout=8)
    assert result.exit_code == 0
    assert marker_value not in result.stdout
    assert marker_value not in result.stderr


@pytest.mark.skipif(os.name != "nt", reason="Windows supervised integration")
def test_timeout_and_reattach_keep_durable_provider_output_sanitized(tmp_path: Path) -> None:
    from a_conductor.execution_store import SQLiteExecutionStore
    from a_conductor.owned_process import WindowsOwnedProcessController
    from a_conductor.supervised_execution import SupervisedExecutionService
    from a_conductor.windows_io import LoopbackReadyzHttpProbe, StrictPowerShellInspectionRunner
    from a_conductor.windows_observer import WindowsRuntimeObserver

    repo = tmp_path / "repo"
    repo.mkdir()
    runtime_python = getattr(sys, "_base_executable", sys.executable)
    python_name = Path(runtime_python).name
    marker_value = "wo119-timeout-marker-31ac7"
    resolver = MappingResolver({"endpoint:glm": "https://provider.invalid/v1", "secret-ref:glm/token": marker_value})

    store = SQLiteExecutionStore(tmp_path / "executions.sqlite")
    observer = WindowsRuntimeObserver(
        runner=StrictPowerShellInspectionRunner(), http_probe=LoopbackReadyzHttpProbe()
    )
    supervised = SupervisedExecutionService(
        store=store, controller=WindowsOwnedProcessController(observer=observer), observer=observer,
        allowed_target_executables=(python_name,), python_executable=runtime_python,
        startup_poll_attempts=100, startup_poll_delay_seconds=0.02,
    )
    runner = build_supervised_claude_code_runner(
        project_root=repo, execution_store=store, supervised=supervised,
        reference_resolver=resolver, job_id="job-wo119-timeout-test",
        work_order_ref="docs/work-orders/WO-P1-119-provider-output-persistence-safety.md",
        project_id="wo119-timeout-test", worker_id="wo119-timeout-worker",
        branch="test/wo119-timeout", head_before="c" * 40,
        endpoint_ref="endpoint:glm", credential_ref="secret-ref:glm/token",
        claude_executable=python_name, poll_interval_seconds=0.02,
    )

    release = repo / "release-child"
    child_code = (
        "import os,time,pathlib; v=os.environ['ANTHROPIC_AUTH_TOKEN'].encode('utf-8'); "
        "os.write(1,b'timeout-before\\n'+v+b'\\n'); os.write(2,b'timeout-err\\n'+v+b'\\n'); "
        f"p=pathlib.Path({str(release)!r}); "
        "[time.sleep(0.05) for _ in iter(p.exists, True)]; os.write(1,b'timeout-after\\n')"
    )
    base = invocation(repo)
    first_request = ClaudeCodeInvocation(
        argv=(runtime_python, "-c", child_code), cwd=base.cwd, timeout_seconds=1,
        max_output_bytes=base.max_output_bytes, environment_bindings=base.environment_bindings,
    )
    first = runner.run(first_request)
    assert first.timed_out is True
    assert first.exit_code is None
    live_paths = sorted((repo / "runs").glob("exec-*/*.log"))
    assert len(live_paths) == 2
    deadline = time.monotonic() + 8
    durable = b""
    while b"[REDACTED]" not in durable and time.monotonic() < deadline:
        durable = b"".join(path.read_bytes() for path in live_paths)
        assert marker_value.encode("utf-8") not in durable
        if b"[REDACTED]" not in durable:
            time.sleep(0.02)
    assert b"[REDACTED]" in durable

    release.write_text("release", encoding="utf-8")
    second_request = ClaudeCodeInvocation(
        argv=first_request.argv, cwd=first_request.cwd, timeout_seconds=30,
        max_output_bytes=first_request.max_output_bytes,
        environment_bindings=first_request.environment_bindings,
    )
    second = runner.run(second_request)
    assert second.timed_out is False
    assert second.exit_code == 0
    assert marker_value not in second.stdout
    assert marker_value not in second.stderr
    final_bytes = b"".join(path.read_bytes() for path in live_paths)
    assert marker_value.encode("utf-8") not in final_bytes
    assert b"timeout-after\n" in final_bytes


def test_rejects_unknown_binding_before_native_execution(tmp_path: Path) -> None:
    native = RecordingNativeRunner(native_result())
    resolver = MappingResolver({"secret-ref:other": "value"})
    runner = SupervisedClaudeCodeRunner(
        project_root=tmp_path,
        native_runner=native,
        reference_resolver=resolver,
    )
    bad = invocation(
        tmp_path,
        bindings=(EnvironmentBinding("OPENAI_API_KEY", "secret-ref:other", True),),
    )

    result = runner.run(bad)

    assert result.exit_code is None
    assert result.timed_out is False
    assert result.stdout == ""
    assert result.stderr == "CLAUDE_ENV_POLICY_DENIED"
    assert native.specs == []
    assert resolver.calls == []


def test_incomplete_binding_set_is_denied_before_resolving_secret(tmp_path: Path) -> None:
    native = RecordingNativeRunner(native_result())
    resolver = MappingResolver({"secret-ref:glm/token": "must-not-read"})
    runner = SupervisedClaudeCodeRunner(
        project_root=tmp_path,
        native_runner=native,
        reference_resolver=resolver,
    )
    secret_only = invocation(
        tmp_path,
        bindings=(
            EnvironmentBinding("ANTHROPIC_AUTH_TOKEN", "secret-ref:glm/token", True),
        ),
    )

    result = runner.run(secret_only)

    assert result.stderr == "CLAUDE_ENV_POLICY_DENIED"
    assert resolver.calls == []
    assert native.specs == []


def test_cwd_mismatch_fails_before_reference_resolution(tmp_path: Path) -> None:
    other = tmp_path / "other"
    other.mkdir()
    native = RecordingNativeRunner(native_result())
    resolver = MappingResolver({})
    runner = SupervisedClaudeCodeRunner(
        project_root=tmp_path,
        native_runner=native,
        reference_resolver=resolver,
    )
    result = runner.run(invocation(other))

    assert result.stderr == "CLAUDE_CWD_MISMATCH"
    assert resolver.calls == []
    assert native.specs == []


def test_reference_failure_is_code_only_and_never_launches(tmp_path: Path) -> None:
    native = RecordingNativeRunner(native_result())

    class FailingResolver:
        def resolve(self, reference: str) -> str:
            raise RuntimeError("sensitive resolver detail")

    runner = SupervisedClaudeCodeRunner(
        project_root=tmp_path,
        native_runner=native,
        reference_resolver=FailingResolver(),
    )

    result = runner.run(invocation(tmp_path))

    assert result.stderr == "REFERENCE_RESOLUTION_FAILED"
    assert "sensitive" not in result.stderr
    assert native.specs == []


def test_native_failure_is_code_only(tmp_path: Path) -> None:
    from a_conductor.native_execution import NativeExecutionError

    class FailingNative:
        def run(self, spec):
            raise NativeExecutionError("SUPERVISED_DUPLICATE_BLOCKED")
    resolver = MappingResolver({
        "endpoint:glm": "https://provider.example/v1",
        "secret-ref:glm/token": "secret-token-value",
    })
    runner = SupervisedClaudeCodeRunner(
        project_root=tmp_path,
        native_runner=FailingNative(),
        reference_resolver=resolver,
    )

    result = runner.run(invocation(tmp_path))

    assert result.exit_code is None
    assert result.stderr == "SUPERVISED_NATIVE_ERROR:SUPERVISED_DUPLICATE_BLOCKED"


def test_timeout_mapping_preserves_unknown_execution_signal(tmp_path: Path) -> None:
    native = RecordingNativeRunner(
        native_result(stdout="partial", exit_code=None, timed_out=True)
    )
    resolver = MappingResolver({
        "endpoint:glm": "https://provider.example/v1",
        "secret-ref:glm/token": "secret-token-value",
    })
    runner = SupervisedClaudeCodeRunner(
        project_root=tmp_path,
        native_runner=native,
        reference_resolver=resolver,
    )

    result = runner.run(invocation(tmp_path))

    assert result.timed_out is True
    assert result.exit_code is None
    assert result.stdout == "partial"


def test_harness_adapter_executes_through_supervised_mapping(tmp_path: Path) -> None:
    import json
    from datetime import datetime, timezone

    from a_conductor.claude_code_harness import (
        ClaudeCodeHarnessAdapter,
        HarnessDispatch,
        HarnessExecutionStatus,
        MutationIntent,
        TaskPacketFile,
    )
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
    )

    secret = "super-secret-token"
    profile = ProviderConfiguration(
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
        models=(ProviderModelConfiguration(
            model_id="glm-5.3",
            display_name="GLM-5.3",
            actor_capabilities=(ActorCapabilityEvidence("documentation", "DECLARED", "test"),),
            supported_effort_levels=("MAX",),
        ),),
        enabled=True,
    )
    endpoint = ProviderEndpointConfig(profile.endpoint_ref, "https://provider.example/v1")
    now = datetime(2026, 8, 28, 10, 0, tzinfo=timezone.utc)
    observation = ProviderObservation(
        provider_id=profile.provider_id,
        health=ProviderHealth.AVAILABLE,
        observed_at=now,
        provenance="test",
    )
    packet_path = tmp_path / "task.md"
    packet_path.write_text("# bounded\n", encoding="utf-8")
    packet = TaskPacketFile(
        task_contract_ref="work-order:WO-P1-098",
        path=str(packet_path),
        sha256=hashlib.sha256(packet_path.read_bytes()).hexdigest(),
    )
    dispatch = HarnessDispatch(
        execution_id="job-wo098-test",
        task_contract_ref="work-order:WO-P1-098",
        project_id="a-wiki-conductor",
        worktree_path=str(tmp_path),
        expected_branch="feat/wo-p1-098-aha4-supervised-claude-runner",
        expected_head="a" * 40,
        provider_id=profile.provider_id,
        model_id="glm-5.3",
        harness_strategy=HarnessStrategy.CLAUDE_CODE_CLI,
        mutation_intent=MutationIntent.READ_ONLY,
        timeout_seconds=30,
        max_output_bytes=4096,
        effort_level="MAX",
    )
    native = RecordingNativeRunner(
        native_result(stdout=json.dumps({"is_error": False, "result": secret}))
    )
    resolver = MappingResolver({
        profile.endpoint_ref: endpoint.base_url,
        profile.credential_ref: secret,
    })
    supervised_runner = SupervisedClaudeCodeRunner(
        project_root=tmp_path,
        native_runner=native,
        reference_resolver=resolver,
    )
    result = ClaudeCodeHarnessAdapter(runner=supervised_runner).execute(
        dispatch,
        profile,
        endpoint,
        observation,
        packet,
        now=now,
    )

    assert result.status is HarnessExecutionStatus.SUCCESS
    assert result.payload is not None
    assert result.payload["result"] == "[REDACTED]"
    assert secret not in repr(result)
    assert len(native.specs) == 1
    spec = native.specs[0]
    assert spec.argv[0] == "claude"
    assert "--dangerously-skip-permissions" not in spec.argv
    assert spec.environment_overrides == (
        ("ANTHROPIC_BASE_URL", endpoint.base_url),
        ("ANTHROPIC_AUTH_TOKEN", secret),
    )


class SequenceAuthorityGuard:
    def __init__(self, reasons):
        self.reasons = list(reasons)
        self.calls = 0

    def check(self):
        self.calls += 1
        return self.reasons.pop(0) if self.reasons else None


def test_provider_authority_denial_precedes_reference_resolution(tmp_path: Path) -> None:
    native = RecordingNativeRunner(native_result())
    resolver = MappingResolver({
        "endpoint:glm": "https://provider.example/v1",
        "secret-ref:glm/token": "must-not-read",
    })
    guard = SequenceAuthorityGuard(["PROVIDER_CONFIGURATION_STALE"])
    runner = SupervisedClaudeCodeRunner(
        project_root=tmp_path,
        native_runner=native,
        reference_resolver=resolver,
        authority_guard=guard,
    )

    result = runner.run(invocation(tmp_path))

    assert result.stderr == "PROVIDER_CONFIGURATION_STALE"
    assert guard.calls == 1
    assert resolver.calls == []
    assert native.specs == []


def test_provider_authority_revalidates_after_secret_resolution_before_native_launch(tmp_path: Path) -> None:
    native = RecordingNativeRunner(native_result())
    resolver = MappingResolver({
        "endpoint:glm": "https://provider.example/v1",
        "secret-ref:glm/token": "resolved-secret",
    })
    guard = SequenceAuthorityGuard([None, "PROVIDER_CONFIGURATION_STALE"])
    runner = SupervisedClaudeCodeRunner(
        project_root=tmp_path,
        native_runner=native,
        reference_resolver=resolver,
        authority_guard=guard,
    )

    result = runner.run(invocation(tmp_path))

    assert result.stderr == "PROVIDER_CONFIGURATION_STALE"
    assert guard.calls == 2
    assert resolver.calls == ["endpoint:glm", "secret-ref:glm/token"]
    assert native.specs == []


def test_runtime_profile_ref_uses_only_opaque_reference_identity() -> None:
    first = claude_runtime_profile_ref(
        "provider-config:glm/base-url",
        "secret-ref:provider/glm/main",
    )
    second = claude_runtime_profile_ref(
        "provider-config:glm/base-url",
        "secret-ref:provider/glm/main",
    )
    changed = claude_runtime_profile_ref(
        "provider-config:glm/base-url",
        "secret-ref:provider/glm/rotated",
    )

    assert first == second
    assert first != changed
    assert "secret-ref" not in first
    assert first.startswith("runtime:claude-code:")


def test_runtime_profile_ref_separates_provider_generation_and_requirement_identity() -> None:
    endpoint = "provider-config:glm/base-url"
    credential = "secret-ref:provider/glm/main"
    base = claude_runtime_profile_ref(
        endpoint, credential, provider_id="provider-glm",
        configuration_generation=1, requirement_sha256="1" * 64,
    )
    generation2 = claude_runtime_profile_ref(
        endpoint, credential, provider_id="provider-glm",
        configuration_generation=2, requirement_sha256="1" * 64,
    )
    security_changed = claude_runtime_profile_ref(
        endpoint, credential, provider_id="provider-glm",
        configuration_generation=1, requirement_sha256="2" * 64,
    )
    assert len({base, generation2, security_changed}) == 3
    assert all(value.startswith("runtime:claude-code:") for value in (base, generation2, security_changed))
    assert all("provider-glm" not in value and "secret-ref" not in value for value in (base, generation2, security_changed))


def test_builder_binds_supervised_record_to_durable_and_opaque_identity(tmp_path: Path) -> None:
    from a_conductor.execution_store import SQLiteExecutionStore
    from a_conductor.supervised_execution import SupervisedLaunchOutcome

    class CapturingSupervised:
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
            raise AssertionError("inspect must not run")

        def collect(self, execution_id, *, expected_version):
            raise AssertionError("collect must not run")

    endpoint_ref = "provider-config:glm/base-url"
    credential_ref = "secret-ref:provider/glm/main"
    secret = "super-secret-token"
    resolver = MappingResolver({
        endpoint_ref: "https://provider.example/v1",
        credential_ref: secret,
    })
    supervised = CapturingSupervised()
    runner = build_supervised_claude_code_runner(
        project_root=tmp_path,
        execution_store=SQLiteExecutionStore(tmp_path / "exec.sqlite"),
        supervised=supervised,
        reference_resolver=resolver,
        job_id="job-wo098",
        work_order_ref="docs/work-orders/WO-P1-098-aha4-supervised-claude-runner.md",
        project_id="a-wiki-conductor",
        worker_id="a-worker-01",
        branch="feat/wo-p1-098-aha4-supervised-claude-runner",
        head_before="a" * 40,
        endpoint_ref=endpoint_ref,
        credential_ref=credential_ref,
        claude_executable="claude.exe",
    )
    result = runner.run(
        invocation(
            tmp_path,
            bindings=(
                EnvironmentBinding("ANTHROPIC_BASE_URL", endpoint_ref, False),
                EnvironmentBinding("ANTHROPIC_AUTH_TOKEN", credential_ref, True),
            ),
        )
    )

    assert result.stderr == "SUPERVISED_LAUNCH_FAILED:TEST_STOP"
    assert len(supervised.plans) == 1
    plan = supervised.plans[0]
    record = plan.record
    assert record.job_id == "job-wo098"
    assert record.work_order_ref.endswith("WO-P1-098-aha4-supervised-claude-runner.md")
    assert record.project_id == "a-wiki-conductor"
    assert record.worker_id == "a-worker-01"
    assert record.backend_id == "supervised-claude-code"
    assert record.runtime_profile_ref == claude_runtime_profile_ref(endpoint_ref, credential_ref)
    assert secret not in record.runtime_profile_ref
    assert secret not in record.command_fingerprint
    assert secret not in record.command_summary
    assert secret not in repr(plan)


def test_builder_rejects_reference_drift_before_resolver_or_launch(tmp_path: Path) -> None:
    from a_conductor.execution_store import SQLiteExecutionStore

    class NoLaunch:
        def launch(self, plan):
            raise AssertionError("launch must not run")
        def inspect(self, execution_id):
            raise AssertionError("inspect must not run")
        def collect(self, execution_id, *, expected_version):
            raise AssertionError("collect must not run")

    endpoint_ref = "provider-config:glm/base-url"
    credential_ref = "secret-ref:provider/glm/main"
    resolver = MappingResolver({
        endpoint_ref: "https://provider.example/v1",
        credential_ref: "expected-token",
        "secret-ref:provider/glm/other": "other-token",
    })
    runner = build_supervised_claude_code_runner(
        project_root=tmp_path,
        execution_store=SQLiteExecutionStore(tmp_path / "exec.sqlite"),
        supervised=NoLaunch(),
        reference_resolver=resolver,
        job_id="job-wo098",
        work_order_ref="docs/work-orders/WO-P1-098-aha4-supervised-claude-runner.md",
        project_id="a-wiki-conductor",
        worker_id="a-worker-01",
        branch="main",
        head_before="a" * 40,
        endpoint_ref=endpoint_ref,
        credential_ref=credential_ref,
        claude_executable="claude.exe",
    )
    drift = invocation(
        tmp_path,
        bindings=(
            EnvironmentBinding("ANTHROPIC_BASE_URL", endpoint_ref, False),
            EnvironmentBinding(
                "ANTHROPIC_AUTH_TOKEN",
                "secret-ref:provider/glm/other",
                True,
            ),
        ),
    )

    result = runner.run(drift)

    assert result.stderr == "CLAUDE_ENV_POLICY_DENIED"
    assert resolver.calls == []
