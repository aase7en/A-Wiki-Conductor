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
from .provider_execution_authority import ProviderExecutionRequirement


_ALLOWED_BINDINGS = {
    "ANTHROPIC_BASE_URL": False,
    "ANTHROPIC_AUTH_TOKEN": True,
}


class EnvironmentReferenceResolver(Protocol):
    def resolve(self, reference: str) -> str: ...


class ProviderExecutionAuthorityGuard(Protocol):
    def check(self) -> str | None: ...


def _failure(code: str) -> ClaudeCodeRunnerResult:
    return ClaudeCodeRunnerResult(
        exit_code=None,
        stdout="",
        stderr=code,
        timed_out=False,
        error_code=code,
    )


def _redact(text: str, secrets: tuple[str, ...]) -> str:
    result = text
    for secret in secrets:
        if secret:
            result = result.replace(secret, "[REDACTED]")
    return result


def claude_runtime_profile_ref(
    endpoint_ref: str,
    credential_ref: str,
    *,
    provider_id: str | None = None,
    configuration_generation: int | None = None,
    requirement_sha256: str | None = None,
) -> str:
    values: list[str] = []
    for value in (endpoint_ref, credential_ref):
        if not isinstance(value, str) or not value.strip() or any(ch in value for ch in "\x00\r\n"):
            raise ValueError("provider reference is invalid")
        values.append(value.strip())
    authority = (provider_id, configuration_generation, requirement_sha256)
    if any(value is not None for value in authority):
        if not all(value is not None for value in authority):
            raise ValueError("provider runtime authority is incomplete")
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError("provider_id is invalid")
        if isinstance(configuration_generation, bool) or not isinstance(configuration_generation, int) or configuration_generation < 1:
            raise ValueError("configuration_generation is invalid")
        if not isinstance(requirement_sha256, str) or len(requirement_sha256) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in requirement_sha256):
            raise ValueError("requirement_sha256 is invalid")
        values.extend((provider_id.strip(), str(configuration_generation), requirement_sha256.casefold()))
    digest = hashlib.sha256("\x00".join(values).encode("utf-8")).hexdigest()
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
        expected_base_url: str | None = None,
        authority_guard: ProviderExecutionAuthorityGuard | None = None,
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
        if authority_guard is not None and not callable(getattr(authority_guard, "check", None)):
            raise ValueError("authority_guard must provide check")
        self._project_root = root
        self._native_runner = native_runner
        self._resolver = reference_resolver
        if expected_base_url is not None and (not isinstance(expected_base_url, str) or not expected_base_url.strip() or "\x00" in expected_base_url):
            raise ValueError("expected_base_url is invalid")
        self._expected_source_refs = expected
        self._expected_base_url = None if expected_base_url is None else expected_base_url.strip()
        self._authority_guard = authority_guard

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
            if key == "ANTHROPIC_BASE_URL" and self._expected_base_url is not None and value != self._expected_base_url:
                raise NativeExecutionError("PROVIDER_ENDPOINT_VALUE_DRIFT")
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

        if self._authority_guard is not None:
            try:
                reason = self._authority_guard.check()
            except Exception:
                return _failure("PROVIDER_AUTHORITY_CHECK_FAILED")
            if reason is not None:
                if not isinstance(reason, str) or not reason or len(reason) > 128 or not all(
                    ch.isalnum() or ch in "._:-" for ch in reason
                ):
                    return _failure("PROVIDER_AUTHORITY_DENIED")
                return _failure(reason)

        try:
            resolved = self._resolve_environment(invocation)
        except NativeExecutionError as exc:
            return _failure(exc.code)
        if resolved is None:
            return _failure("CLAUDE_ENV_POLICY_DENIED")
        environment_overrides, secrets = resolved

        if self._authority_guard is not None:
            try:
                reason = self._authority_guard.check()
            except Exception:
                return _failure("PROVIDER_AUTHORITY_CHECK_FAILED")
            if reason is not None:
                if not isinstance(reason, str) or not reason or len(reason) > 128 or not all(
                    ch.isalnum() or ch in "._:-" for ch in reason
                ):
                    return _failure("PROVIDER_AUTHORITY_DENIED")
                return _failure(reason)

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
    endpoint_url: str | None = None,
    provider_requirement: ProviderExecutionRequirement | None = None,
    claude_executable: str = "claude",
    poll_interval_seconds: float = 0.05,
    authority_guard: ProviderExecutionAuthorityGuard | None = None,
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
        runtime_profile_ref=claude_runtime_profile_ref(
            endpoint_ref, credential_ref,
            provider_id=None if provider_requirement is None else provider_requirement.provider_id,
            configuration_generation=None if provider_requirement is None else provider_requirement.expected_configuration_generation,
            requirement_sha256=None if provider_requirement is None else provider_requirement.requirement_sha256,
        ),
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
        expected_base_url=endpoint_url,
        authority_guard=authority_guard,
    )
