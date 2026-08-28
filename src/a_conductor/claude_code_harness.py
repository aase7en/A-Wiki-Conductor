"""Bounded Claude Code harness adapter for AHA-3.

Builds one fixed read-only, non-interactive invocation and delegates execution
to an injected runner. This module performs no subprocess/network I/O and owns
no scheduler, retry, credential resolution, or task-completion authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol

from .provider_configuration import (
    HarnessStrategy,
    ProviderConfiguration,
    ProviderEndpointConfig,
    ProviderObservation,
    is_provider_ready,
)

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
_HEAD_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_EFFORT_LEVELS = frozenset({"LOW", "HIGH", "MAX", "DEFAULT"})
_READ_ONLY_TOOLS = "Read,Glob,Grep"
_FIXED_PROMPT = "Execute the authorized task packet. Return concise structured evidence only."


def _require_text(value: str, field: str, *, max_length: int) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ValueError(f"{field} must be a non-blank string")
    if len(value) > max_length:
        raise ValueError(f"{field} is too long")
    return value


class MutationIntent(str, Enum):
    READ_ONLY = "READ_ONLY"
    PROJECT_MUTATION = "PROJECT_MUTATION"


class HarnessExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    OUTPUT_LIMIT = "OUTPUT_LIMIT"
    OUTPUT_INVALID = "OUTPUT_INVALID"


class ClaudeCodeHarnessError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class HarnessDispatch:
    execution_id: str
    task_contract_ref: str
    project_id: str
    worktree_path: str
    expected_branch: str | None
    expected_head: str
    provider_id: str
    model_id: str
    harness_strategy: HarnessStrategy
    mutation_intent: MutationIntent
    timeout_seconds: int
    max_output_bytes: int
    effort_level: str | None = None
    evidence_destination_ref: str | None = None
    schema_version: str = "1.0.0"

    def __post_init__(self) -> None:
        if not _ID_RE.fullmatch(self.execution_id):
            raise ValueError("execution_id is invalid")
        _require_text(self.task_contract_ref, "task_contract_ref", max_length=512)
        _require_text(self.project_id, "project_id", max_length=128)
        _require_text(self.worktree_path, "worktree_path", max_length=1024)
        if self.expected_branch is not None:
            _require_text(self.expected_branch, "expected_branch", max_length=256)
        if not _HEAD_RE.fullmatch(self.expected_head):
            raise ValueError("expected_head is invalid")
        _require_text(self.provider_id, "provider_id", max_length=128)
        _require_text(self.model_id, "model_id", max_length=128)
        if not isinstance(self.harness_strategy, HarnessStrategy):
            try:
                object.__setattr__(self, "harness_strategy", HarnessStrategy(self.harness_strategy))
            except (TypeError, ValueError) as exc:
                raise ValueError("harness_strategy is invalid") from exc
        if not isinstance(self.mutation_intent, MutationIntent):
            try:
                object.__setattr__(self, "mutation_intent", MutationIntent(self.mutation_intent))
            except (TypeError, ValueError) as exc:
                raise ValueError("mutation_intent is invalid") from exc
        if self.effort_level is not None and self.effort_level not in _EFFORT_LEVELS:
            raise ValueError("effort_level is invalid")
        if isinstance(self.timeout_seconds, bool) or not 1 <= self.timeout_seconds <= 14400:
            raise ValueError("timeout_seconds is invalid")
        if isinstance(self.max_output_bytes, bool) or not 1 <= self.max_output_bytes <= 8_388_608:
            raise ValueError("max_output_bytes is invalid")
        if self.evidence_destination_ref is not None:
            _require_text(self.evidence_destination_ref, "evidence_destination_ref", max_length=512)
        if self.schema_version != "1.0.0":
            raise ValueError("schema_version is unsupported")

    def as_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "schema_version": self.schema_version,
            "execution_id": self.execution_id,
            "task_contract_ref": self.task_contract_ref,
            "project_id": self.project_id,
            "worktree_path": self.worktree_path,
            "expected_branch": self.expected_branch,
            "expected_head": self.expected_head,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "harness_strategy": self.harness_strategy.value,
            "mutation_intent": self.mutation_intent.value,
            "timeout_seconds": self.timeout_seconds,
            "max_output_bytes": self.max_output_bytes,
        }
        if self.effort_level is not None:
            data["effort_level"] = self.effort_level
        if self.evidence_destination_ref is not None:
            data["evidence_destination_ref"] = self.evidence_destination_ref
        return data


@dataclass(frozen=True, slots=True)
class TaskPacketFile:
    task_contract_ref: str
    path: str
    sha256: str

    def __post_init__(self) -> None:
        _require_text(self.task_contract_ref, "task_contract_ref", max_length=512)
        _require_text(self.path, "path", max_length=2048)
        if not _SHA256_RE.fullmatch(self.sha256):
            raise ValueError("sha256 is invalid")


@dataclass(frozen=True, slots=True)
class EnvironmentBinding:
    key: str
    source_ref: str
    secret: bool


@dataclass(frozen=True, slots=True)
class ClaudeCodeInvocation:
    argv: tuple[str, ...]
    cwd: str
    timeout_seconds: int
    max_output_bytes: int
    environment_bindings: tuple[EnvironmentBinding, ...]


@dataclass(frozen=True, slots=True)
class ClaudeCodeRunnerResult:
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool


class ClaudeCodeRunner(Protocol):
    def run(self, invocation: ClaudeCodeInvocation) -> ClaudeCodeRunnerResult: ...


@dataclass(frozen=True, slots=True)
class ClaudeCodeHarnessResult:
    status: HarnessExecutionStatus
    payload: dict[str, object] | None
    stderr: str
    exit_code: int | None


def _redact_text(text: str, values: tuple[str, ...]) -> str:
    result = text
    for value in values:
        if isinstance(value, str) and value:
            result = result.replace(value, "[REDACTED]")
    return result


def _redact_json(value, values: tuple[str, ...]):
    if isinstance(value, str):
        return _redact_text(value, values)
    if isinstance(value, list):
        return [_redact_json(item, values) for item in value]
    if isinstance(value, dict):
        return {
            _redact_text(key, values) if isinstance(key, str) else key: _redact_json(item, values)
            for key, item in value.items()
        }
    return value


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


class ClaudeCodeHarnessAdapter:
    def __init__(self, *, runner: ClaudeCodeRunner, max_task_packet_bytes: int = 262_144) -> None:
        if not callable(getattr(runner, "run", None)):
            raise ValueError("runner must provide run")
        if (
            isinstance(max_task_packet_bytes, bool)
            or not isinstance(max_task_packet_bytes, int)
            or max_task_packet_bytes < 1
        ):
            raise ValueError("max_task_packet_bytes must be positive")
        self._runner = runner
        self._max_task_packet_bytes = max_task_packet_bytes

    def _validate_dispatch(
        self,
        dispatch: HarnessDispatch,
        profile: ProviderConfiguration,
        endpoint: ProviderEndpointConfig,
        observation: ProviderObservation | None,
        *,
        now,
    ) -> None:
        if dispatch.harness_strategy is not HarnessStrategy.CLAUDE_CODE_CLI:
            raise ClaudeCodeHarnessError("HARNESS_STRATEGY_UNSUPPORTED")
        if dispatch.mutation_intent is not MutationIntent.READ_ONLY:
            raise ClaudeCodeHarnessError("HARNESS_MUTATION_NOT_READY")
        if dispatch.provider_id != profile.provider_id:
            raise ClaudeCodeHarnessError("PROVIDER_ID_MISMATCH")
        if HarnessStrategy.CLAUDE_CODE_CLI not in profile.harness_strategies:
            raise ClaudeCodeHarnessError("HARNESS_NOT_CONFIGURED")
        if endpoint.endpoint_ref != profile.endpoint_ref:
            raise ClaudeCodeHarnessError("ENDPOINT_REF_MISMATCH")
        model = next((item for item in profile.models if item.model_id == dispatch.model_id), None)
        if model is None:
            raise ClaudeCodeHarnessError("MODEL_NOT_CONFIGURED")
        if dispatch.effort_level is not None and dispatch.effort_level not in model.supported_effort_levels:
            raise ClaudeCodeHarnessError("EFFORT_NOT_SUPPORTED")
        if not is_provider_ready(profile, observation, now=now):
            raise ClaudeCodeHarnessError("PROVIDER_NOT_READY")

    def _verified_packet(self, dispatch: HarnessDispatch, packet: TaskPacketFile) -> Path:
        if packet.task_contract_ref != dispatch.task_contract_ref:
            raise ClaudeCodeHarnessError("TASK_PACKET_REF_MISMATCH")
        root = Path(dispatch.worktree_path).expanduser().resolve(strict=False)
        path = Path(packet.path).expanduser().resolve(strict=False)
        if not _is_within(path, root):
            raise ClaudeCodeHarnessError("TASK_PACKET_OUTSIDE_WORKTREE")
        if not path.is_file():
            raise ClaudeCodeHarnessError("TASK_PACKET_MISSING")
        raw = path.read_bytes()
        if len(raw) > self._max_task_packet_bytes:
            raise ClaudeCodeHarnessError("TASK_PACKET_TOO_LARGE")
        if hashlib.sha256(raw).hexdigest().casefold() != packet.sha256.casefold():
            raise ClaudeCodeHarnessError("TASK_PACKET_HASH_MISMATCH")
        return path

    def _build_invocation(
        self,
        dispatch: HarnessDispatch,
        profile: ProviderConfiguration,
        packet_path: Path,
    ) -> ClaudeCodeInvocation:
        argv = [
            "claude",
            "--print",
            _FIXED_PROMPT,
            "--output-format",
            "json",
            "--no-session-persistence",
            "--safe-mode",
            "--permission-mode",
            "plan",
            "--tools",
            _READ_ONLY_TOOLS,
            "--system-prompt-file",
            str(packet_path),
            "--model",
            dispatch.model_id,
        ]
        if dispatch.effort_level not in (None, "DEFAULT"):
            argv.extend(("--effort", dispatch.effort_level.lower()))
        bindings = (
            EnvironmentBinding("ANTHROPIC_BASE_URL", profile.endpoint_ref, False),
            EnvironmentBinding("ANTHROPIC_AUTH_TOKEN", profile.credential_ref, True),
        )
        return ClaudeCodeInvocation(
            argv=tuple(argv),
            cwd=str(Path(dispatch.worktree_path).expanduser().resolve(strict=False)),
            timeout_seconds=dispatch.timeout_seconds,
            max_output_bytes=dispatch.max_output_bytes,
            environment_bindings=bindings,
        )

    def execute(
        self,
        dispatch: HarnessDispatch,
        profile: ProviderConfiguration,
        endpoint: ProviderEndpointConfig,
        observation: ProviderObservation | None,
        packet: TaskPacketFile,
        *,
        now,
        redaction_values: tuple[str, ...] = (),
    ) -> ClaudeCodeHarnessResult:
        if not isinstance(dispatch, HarnessDispatch):
            raise ValueError("dispatch must be HarnessDispatch")
        if not isinstance(profile, ProviderConfiguration):
            raise ValueError("profile must be ProviderConfiguration")
        if not isinstance(endpoint, ProviderEndpointConfig):
            raise ValueError("endpoint must be ProviderEndpointConfig")
        if observation is not None and not isinstance(observation, ProviderObservation):
            raise ValueError("observation must be ProviderObservation or None")
        if not isinstance(packet, TaskPacketFile):
            raise ValueError("packet must be TaskPacketFile")
        redactions = tuple(value for value in redaction_values if isinstance(value, str) and value)
        self._validate_dispatch(dispatch, profile, endpoint, observation, now=now)
        packet_path = self._verified_packet(dispatch, packet)
        invocation = self._build_invocation(dispatch, profile, packet_path)
        raw = self._runner.run(invocation)
        if not isinstance(raw, ClaudeCodeRunnerResult):
            raise ClaudeCodeHarnessError("RUNNER_RESULT_INVALID")
        if raw.timed_out:
            return ClaudeCodeHarnessResult(
                HarnessExecutionStatus.TIMEOUT, None, "", raw.exit_code
            )
        output_size = len(raw.stdout.encode("utf-8")) + len(raw.stderr.encode("utf-8"))
        if output_size > dispatch.max_output_bytes:
            return ClaudeCodeHarnessResult(
                HarnessExecutionStatus.OUTPUT_LIMIT, None, "", raw.exit_code
            )
        stderr = _redact_text(raw.stderr, redactions)
        if raw.exit_code != 0:
            return ClaudeCodeHarnessResult(
                HarnessExecutionStatus.FAILED, None, stderr, raw.exit_code
            )
        try:
            decoded = json.loads(raw.stdout)
        except (TypeError, json.JSONDecodeError):
            return ClaudeCodeHarnessResult(
                HarnessExecutionStatus.OUTPUT_INVALID, None, stderr, raw.exit_code
            )
        if not isinstance(decoded, dict):
            return ClaudeCodeHarnessResult(
                HarnessExecutionStatus.OUTPUT_INVALID, None, stderr, raw.exit_code
            )
        payload = _redact_json(decoded, redactions)
        status = (
            HarnessExecutionStatus.FAILED
            if bool(payload.get("is_error"))
            else HarnessExecutionStatus.SUCCESS
        )
        return ClaudeCodeHarnessResult(status, payload, stderr, raw.exit_code)
