from __future__ import annotations

from pathlib import Path

import pytest

from a_conductor.domain import RecoveryClassification, TaskState
from a_conductor.job_execution import DurableJobExecutionCoordinator, JobExecutionContext
from a_conductor.job_store import SQLiteJobStore
from a_conductor.native_execution import NativeCommandResult
from a_conductor.native_operations import (
    AllowlistedNativeJobBackend,
    NativeOperationDefinition,
    NativeOperationError,
    NativeOperationKind,
    NativeOperationRegistry,
    StaticWorkerNativeAdapterResolver,
    WorkerNativeAdapters,
)


def command_result(
    *,
    exit_code: int | None = 0,
    timed_out: bool = False,
    stdout: str = "",
    stderr: str = "",
    stdout_sha256: str = "a" * 64,
    stderr_sha256: str = "b" * 64,
) -> NativeCommandResult:
    return NativeCommandResult(
        executable="tool.exe",
        argument_count=3,
        exit_code=exit_code,
        timed_out=timed_out,
        stdout=stdout,
        stderr=stderr,
        stdout_sha256=stdout_sha256,
        stderr_sha256=stderr_sha256,
        stdout_truncated=False,
        stderr_truncated=False,
    )


class FakeGitAdapter:
    def __init__(self, result: NativeCommandResult | None = None) -> None:
        self.result = result or command_result()
        self.calls: list[tuple] = []

    def status_short(self, *, timeout_seconds: int = 10):
        self.calls.append(("status", timeout_seconds))
        return self.result

    def working_diff(self, paths=(), *, timeout_seconds: int = 15):
        self.calls.append(("working_diff", tuple(paths), timeout_seconds))
        return self.result

    def cached_diff(self, paths=(), *, timeout_seconds: int = 15):
        self.calls.append(("cached_diff", tuple(paths), timeout_seconds))
        return self.result


class FakeVerificationAdapter:
    def __init__(self, result: NativeCommandResult | None = None) -> None:
        self.result = result or command_result()
        self.calls: list[tuple] = []

    def pytest(self, paths=("tests",), *, timeout_seconds: int = 120):
        self.calls.append(("pytest", tuple(paths), timeout_seconds))
        return self.result

    def compileall(self, paths=("src",), *, timeout_seconds: int = 120):
        self.calls.append(("compileall", tuple(paths), timeout_seconds))
        return self.result


def execution_context(worker_id: str = "a-worker-01") -> JobExecutionContext:
    return JobExecutionContext(
        job_id="job-native",
        work_order_ref="docs/work-orders/WO-native.md",
        project_id="project-native",
        worker_id=worker_id,
        attempt_no=1,
        max_attempts=3,
    )


def resolver_for(
    *,
    git_result: NativeCommandResult | None = None,
    verify_result: NativeCommandResult | None = None,
):
    git = FakeGitAdapter(git_result)
    verify = FakeVerificationAdapter(verify_result)
    resolver = StaticWorkerNativeAdapterResolver(
        {
            "a-worker-01": WorkerNativeAdapters(
                git=git,
                verification=verify,
            )
        }
    )
    return resolver, git, verify


def test_definition_has_no_generic_command_or_executable_surface() -> None:
    definition = NativeOperationDefinition(
        operation_ref="op:pytest-unit",
        kind=NativeOperationKind.PYTEST,
        paths=("tests/test_unit.py",),
        timeout_seconds=60,
    )
    assert definition.paths == ("tests/test_unit.py",)
    for forbidden in ("argv", "command", "shell", "executable", "environment"):
        assert not hasattr(definition, forbidden)


def test_definition_rejects_raw_command_ref_absolute_parent_paths_and_broad_verify() -> None:
    with pytest.raises(ValueError):
        NativeOperationDefinition(
            operation_ref="python -m pytest",
            kind=NativeOperationKind.PYTEST,
            paths=("tests",),
        )
    with pytest.raises(ValueError):
        NativeOperationDefinition(
            operation_ref="op:absolute",
            kind=NativeOperationKind.PYTEST,
            paths=(str(Path.cwd().resolve()),),
        )
    with pytest.raises(ValueError):
        NativeOperationDefinition(
            operation_ref="op:escape",
            kind=NativeOperationKind.COMPILEALL,
            paths=("../src",),
        )
    with pytest.raises(ValueError):
        NativeOperationDefinition(
            operation_ref="op:broad",
            kind=NativeOperationKind.PYTEST,
            paths=(),
        )


def test_registry_rejects_duplicate_and_unregistered_refs() -> None:
    definition = NativeOperationDefinition(
        operation_ref="op:status",
        kind=NativeOperationKind.GIT_STATUS,
    )
    with pytest.raises(NativeOperationError) as exc_info:
        NativeOperationRegistry((definition, definition))
    assert exc_info.value.code == "OPERATION_REF_DUPLICATE"

    registry = NativeOperationRegistry((definition,))
    with pytest.raises(NativeOperationError) as exc_info:
        registry.resolve("op:missing")
    assert exc_info.value.code == "OPERATION_NOT_REGISTERED"


def test_worker_resolver_has_no_fallback() -> None:
    resolver, _, _ = resolver_for()
    with pytest.raises(NativeOperationError) as exc_info:
        resolver.resolve("a-worker-02")
    assert exc_info.value.code == "WORKER_NATIVE_ADAPTERS_NOT_REGISTERED"


@pytest.mark.parametrize(
    ("definition", "expected_call"),
    [
        (
            NativeOperationDefinition(
                operation_ref="op:status",
                kind=NativeOperationKind.GIT_STATUS,
                timeout_seconds=7,
            ),
            ("git", ("status", 7)),
        ),
        (
            NativeOperationDefinition(
                operation_ref="op:diff",
                kind=NativeOperationKind.GIT_WORKING_DIFF,
                paths=("src/a.py",),
                timeout_seconds=8,
            ),
            ("git", ("working_diff", ("src/a.py",), 8)),
        ),
        (
            NativeOperationDefinition(
                operation_ref="op:cached",
                kind=NativeOperationKind.GIT_CACHED_DIFF,
                paths=("src/a.py",),
                timeout_seconds=9,
            ),
            ("git", ("cached_diff", ("src/a.py",), 9)),
        ),
        (
            NativeOperationDefinition(
                operation_ref="op:pytest",
                kind=NativeOperationKind.PYTEST,
                paths=("tests/test_a.py",),
                timeout_seconds=10,
            ),
            ("verify", ("pytest", ("tests/test_a.py",), 10)),
        ),
        (
            NativeOperationDefinition(
                operation_ref="op:compile",
                kind=NativeOperationKind.COMPILEALL,
                paths=("src",),
                timeout_seconds=11,
            ),
            ("verify", ("compileall", ("src",), 11)),
        ),
    ],
)
def test_backend_dispatches_only_fixed_adapter_methods(definition, expected_call) -> None:
    resolver, git, verify = resolver_for()
    backend = AllowlistedNativeJobBackend(
        registry=NativeOperationRegistry((definition,)),
        resolver=resolver,
    )

    result = backend.execute(definition.operation_ref, execution_context())

    assert result.success is True
    target, call = expected_call
    if target == "git":
        assert git.calls == [call]
        assert verify.calls == []
    else:
        assert verify.calls == [call]
        assert git.calls == []


def test_evidence_ref_is_digest_only_and_does_not_embed_output() -> None:
    secret = "sensitive-output-that-must-not-persist"
    native = command_result(
        stdout=secret,
        stderr="another-sensitive-value",
        stdout_sha256="1" * 64,
        stderr_sha256="2" * 64,
    )
    resolver, _, _ = resolver_for(git_result=native)
    definition = NativeOperationDefinition(
        operation_ref="op:status",
        kind=NativeOperationKind.GIT_STATUS,
    )
    backend = AllowlistedNativeJobBackend(
        registry=NativeOperationRegistry((definition,)),
        resolver=resolver,
    )

    result = backend.execute("op:status", execution_context())

    assert result.success is True
    assert result.evidence_ref is not None
    assert result.evidence_ref.startswith("native-evidence:")
    assert secret not in result.evidence_ref
    assert "another-sensitive-value" not in result.evidence_ref
    assert len(result.evidence_ref.split(":")[-1]) == 64


def test_git_failure_is_no_mutation_recovery() -> None:
    resolver, _, _ = resolver_for(git_result=command_result(exit_code=1, stderr="git failed"))
    definition = NativeOperationDefinition(
        operation_ref="op:diff",
        kind=NativeOperationKind.GIT_WORKING_DIFF,
    )
    backend = AllowlistedNativeJobBackend(
        registry=NativeOperationRegistry((definition,)), resolver=resolver
    )

    result = backend.execute("op:diff", execution_context())

    assert result.success is False
    assert result.recovery_classification is RecoveryClassification.NO_MUTATION
    assert result.evidence_ref is not None


@pytest.mark.parametrize("timed_out,exit_code", [(False, 2), (True, None)])
def test_verification_failure_or_timeout_is_unknown_recovery(timed_out, exit_code) -> None:
    resolver, _, _ = resolver_for(
        verify_result=command_result(exit_code=exit_code, timed_out=timed_out)
    )
    definition = NativeOperationDefinition(
        operation_ref="op:pytest",
        kind=NativeOperationKind.PYTEST,
        paths=("tests",),
    )
    backend = AllowlistedNativeJobBackend(
        registry=NativeOperationRegistry((definition,)), resolver=resolver
    )

    result = backend.execute("op:pytest", execution_context())

    assert result.success is False
    assert result.recovery_classification is RecoveryClassification.UNKNOWN


def prepare_gating(store: SQLiteJobStore):
    job = store.create_job(job_id="job-1", work_order_ref="wo", project_id="p")
    ready = store.transition("job-1", TaskState.READY, expected_version=job.version)
    claimed = store.transition(
        "job-1", TaskState.CLAIMED, expected_version=ready.version, worker_id="a-worker-01"
    )
    return store.transition("job-1", TaskState.GATING, expected_version=claimed.version)


def test_end_to_end_durable_execution_persists_digest_not_raw_output(tmp_path: Path) -> None:
    secret = "RAW-TEST-OUTPUT-MUST-STAY-EPHEMERAL"
    verify_result = command_result(
        stdout=secret,
        stderr="",
        stdout_sha256="3" * 64,
        stderr_sha256="4" * 64,
    )
    resolver, _, _ = resolver_for(verify_result=verify_result)
    definition = NativeOperationDefinition(
        operation_ref="op:pytest-targeted",
        kind=NativeOperationKind.PYTEST,
        paths=("tests/test_job_execution.py",),
    )
    backend = AllowlistedNativeJobBackend(
        registry=NativeOperationRegistry((definition,)), resolver=resolver
    )
    store = SQLiteJobStore(tmp_path / "control.sqlite")
    gating = prepare_gating(store)
    coordinator = DurableJobExecutionCoordinator(store=store, backend=backend)

    outcome = coordinator.execute(
        "job-1",
        expected_version=gating.version,
        worker_id="a-worker-01",
        operation_ref="op:pytest-targeted",
    )

    assert outcome.success is True
    assert outcome.job.state is TaskState.VERIFYING
    assert outcome.evidence_ref is not None
    assert outcome.evidence_ref.startswith("native-evidence:")
    assert secret not in outcome.evidence_ref
    assert secret.encode() not in (tmp_path / "control.sqlite").read_bytes()


def test_backend_exposes_no_generic_run_shell_or_git_mutation_surface() -> None:
    resolver, _, _ = resolver_for()
    backend = AllowlistedNativeJobBackend(
        registry=NativeOperationRegistry(
            (
                NativeOperationDefinition(
                    operation_ref="op:status", kind=NativeOperationKind.GIT_STATUS
                ),
            )
        ),
        resolver=resolver,
    )
    for forbidden in (
        "run",
        "shell",
        "argv",
        "execute_command",
        "git_add",
        "git_commit",
        "git_reset",
        "delete",
        "write",
        "schedule",
        "route_model",
    ):
        assert not hasattr(backend, forbidden)
