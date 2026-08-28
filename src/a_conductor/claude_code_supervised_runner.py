"""Claude Code runner adapter over canonical supervised native execution.

Resolves opaque provider references only at the execution boundary, maps the
fixed Claude invocation to ``NativeCommandSpec``, and delegates to an injected
native runner.  No subprocess, retry, lifecycle, store, or dedup logic lives
here.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol

from .claude_code_harness import ClaudeCodeInvocation, ClaudeCodeRunnerResult
from .native_adapters import NativeCommandRunner
from .native_execution import (
    NativeCommandResult,
    NativeCommandSpec,
    NativeExecutionError,
    NativeExecutionScope,
)
from .supervised_command_runner import SupervisedCommandRunner


_ALLOWED_BINDINGS = {
    "ANTHROPIC_BASE_URL": False,
    "ANTHROPIC_AUTH_TOKEN": True,
}


class EnvironmentReferenceResolver(Protocol):
    def resolve(self, reference: str) -> str: ...


def _failure(code: str) -> ClaudeCodeRunnerResult:
    return ClaudeCodeRunnerResult(
        exit_code=None,
        stdout="",
        stderr=code,
        timed_out=False,
    )


def _redact(text: str, secrets: tuple[str, ...]) -> str:
    result = text
    for secret in secrets:
        if secret:
            result = result.replace(secret, "[REDACTED]")
    return result


def claude_runtime_profile_ref(endpoint_ref: str, credential_ref: str) -> str:
    refs: list[str] = []
    for value in (endpoint_ref, credential_ref):
        if (
            not isinstance(value, str)
            or not value.strip()
            or "\x00" in value
            or "\r" in value
            or "\n" in value
        ):
            raise ValueError("provider reference is invalid")
        refs.append(value.strip())
    digest = hashlib.sha256("\x00".join(refs).encode("utf-8")).hexdigest()
    return f"runtime:claude-code:{digest[:32]}"


class SupervisedClaudeCodeRunner:
    """Map one validated Claude invocation onto an identity-bound native runner."""

    def __init__(
        self,
        *,
        project_root: Path | str,
        native_runner: NativeCommandRunner,
        reference_resolver: EnvironmentReferenceResolver,
        expected_source_refs: tuple[tuple[str, str], ...] | None = None,
    ) -> None:
        root = Path(project_root).expanduser().resolve(strict=False)
        if not root.is_dir():
            raise ValueError("project_root must be an existing directory")
        if not callable(getattr(native_runner, "run", None)):
            raise ValueError("native_runner must provide run")
        if not callable(getattr(reference_resolver, "resolve", None)):
            raise ValueError("reference_resolver must provide resolve")
        expected: dict[str, str] | None = None
        if expected_source_refs is not None:
            if not isinstance(expected_source_refs, tuple):
                raise ValueError("expected_source_refs must be a tuple")
            expected = {}
            for item in expected_source_refs:
                if not isinstance(item, tuple) or len(item) != 2:
                    raise ValueError("expected source ref must be a key/ref tuple")
                key, reference = item
                if key not in _ALLOWED_BINDINGS or key in expected:
                    raise ValueError("expected source ref key is invalid")
                if (
                    not isinstance(reference, str)
                    or not reference.strip()
                    or "\x00" in reference
                ):
                    raise ValueError("expected source ref is invalid")
                expected[key] = reference.strip()
            if set(expected) != set(_ALLOWED_BINDINGS):
                raise ValueError("expected source refs are incomplete")
        self._project_root = root
        self._native_runner = native_runner
        self._resolver = reference_resolver
        self._expected_source_refs = expected

    def _resolve_environment(
        self, invocation: ClaudeCodeInvocation
    ) -> tuple[tuple[tuple[str, str], ...], tuple[str, ...]] | None:
        bindings = invocation.environment_bindings
        if not isinstance(bindings, tuple):
            return None
        validated: list[tuple[str, str, bool]] = []
        seen: set[str] = set()
        for binding in bindings:
            key = getattr(binding, "key", None)
            source_ref = getattr(binding, "source_ref", None)
            secret = getattr(binding, "secret", None)
            if key not in _ALLOWED_BINDINGS or key in seen:
                return None
            if secret is not _ALLOWED_BINDINGS[key]:
                return None
            if not isinstance(source_ref, str) or not source_ref.strip() or "\x00" in source_ref:
                return None
            source_ref = source_ref.strip()
            if (
                self._expected_source_refs is not None
                and self._expected_source_refs[key] != source_ref
            ):
                return None
            seen.add(key)
            validated.append((key, source_ref, secret))
        if seen != set(_ALLOWED_BINDINGS):
            return None

        resolved: list[tuple[str, str]] = []
        secrets: list[str] = []
        for key, source_ref, secret in validated:
            try:
                value = self._resolver.resolve(source_ref)
            except Exception:
                raise NativeExecutionError("REFERENCE_RESOLUTION_FAILED")
            if not isinstance(value, str) or not value or "\x00" in value:
                raise NativeExecutionError("REFERENCE_VALUE_INVALID")
            resolved.append((key, value))
            if secret:
                secrets.append(value)
        return tuple(resolved), tuple(secrets)

    def run(self, invocation: ClaudeCodeInvocation) -> ClaudeCodeRunnerResult:
        if not isinstance(invocation, ClaudeCodeInvocation):
            return _failure("CLAUDE_INVOCATION_INVALID")
        try:
            cwd = Path(invocation.cwd).expanduser().resolve(strict=False)
        except OSError:
            return _failure("CLAUDE_CWD_INVALID")
        if cwd != self._project_root:
            return _failure("CLAUDE_CWD_MISMATCH")

        try:
            resolved = self._resolve_environment(invocation)
        except NativeExecutionError as exc:
            return _failure(exc.code)
        if resolved is None:
            return _failure("CLAUDE_ENV_POLICY_DENIED")
        environment_overrides, secrets = resolved
        spec = NativeCommandSpec(
            argv=invocation.argv,
            cwd=".",
            timeout_seconds=invocation.timeout_seconds,
            environment_overrides=environment_overrides,
            mutation_intent=False,
        )
        try:
            raw = self._native_runner.run(spec)
        except NativeExecutionError as exc:
            return _failure(f"SUPERVISED_NATIVE_ERROR:{exc.code}")
        except Exception:
            return _failure("SUPERVISED_NATIVE_ERROR")
        if not isinstance(raw, NativeCommandResult):
            return _failure("SUPERVISED_NATIVE_RESULT_INVALID")
        return ClaudeCodeRunnerResult(
            exit_code=raw.exit_code,
            stdout=_redact(raw.stdout, secrets),
            stderr=_redact(raw.stderr, secrets),
            timed_out=raw.timed_out,
        )


def build_supervised_claude_code_runner(
    *,
    project_root: Path | str,
    execution_store: object,
    supervised: object,
    reference_resolver: EnvironmentReferenceResolver,
    job_id: str,
    work_order_ref: str,
    project_id: str,
    worker_id: str,
    branch: str,
    head_before: str,
    endpoint_ref: str,
    credential_ref: str,
    claude_executable: str = "claude",
    poll_interval_seconds: float = 0.05,
) -> SupervisedClaudeCodeRunner:
    """Assemble the Claude boundary over the canonical supervised runner."""
    scope = NativeExecutionScope(
        root=project_root,
        mutation_allowed=False,
        allowed_executables=(claude_executable,),
        allowed_environment_overrides=tuple(_ALLOWED_BINDINGS),
        max_timeout_seconds=14_400,
        max_output_bytes=8_388_608,
    )
    native = SupervisedCommandRunner(
        scope=scope,
        execution_store=execution_store,
        supervised=supervised,
        job_id=job_id,
        work_order_ref=work_order_ref,
        project_id=project_id,
        worker_id=worker_id,
        backend_id="supervised-claude-code",
        branch=branch,
        head_before=head_before,
        runtime_profile_ref=claude_runtime_profile_ref(endpoint_ref, credential_ref),
        poll_interval_seconds=poll_interval_seconds,
    )
    return SupervisedClaudeCodeRunner(
        project_root=project_root,
        native_runner=native,
        reference_resolver=reference_resolver,
        expected_source_refs=(
            ("ANTHROPIC_BASE_URL", endpoint_ref),
            ("ANTHROPIC_AUTH_TOKEN", credential_ref),
        ),
    )
