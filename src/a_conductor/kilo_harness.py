"""Bounded Kilo CLI task-packet transport adapter.

This module owns only harness invocation shape, task-packet integrity checks, and
bounded result decoding. It performs no subprocess/network I/O and owns no
scheduler, claim, provider-admission, retry, review, or completion authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .claude_code_harness import HarnessDispatch, HarnessExecutionStatus, TaskPacketFile
from .provider_configuration import HarnessStrategy


_FIXED_PROMPT = (
    "Execute the attached authorized task packet. "
    "Return concise structured evidence only."
)
_KILO_COMPONENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_KILO_SHARE_URL_RE = re.compile(r"https://app\.kilo\.ai/s/[A-Za-z0-9._~-]+")
_EFFORT_VARIANTS = {
    "LOW": "low",
    "HIGH": "high",
    "MAX": "max",
}


class KiloHarnessError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class KiloInvocation:
    argv: tuple[str, ...]
    cwd: str
    timeout_seconds: int
    max_output_bytes: int


@dataclass(frozen=True, slots=True)
class KiloRunnerResult:
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    error_code: str | None = None


class KiloRunner(Protocol):
    def run(self, invocation: KiloInvocation) -> KiloRunnerResult: ...


@dataclass(frozen=True, slots=True)
class KiloHarnessResult:
    status: HarnessExecutionStatus
    events: tuple[dict[str, object], ...] | None
    stderr: str
    exit_code: int | None
    error_code: str | None = None


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _redact_text(text: str, values: tuple[str, ...]) -> str:
    redacted = _KILO_SHARE_URL_RE.sub("[REDACTED_KILO_SHARE_URL]", text)
    for value in values:
        if value:
            redacted = redacted.replace(value, "[REDACTED]")
    return redacted


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


class KiloHarnessAdapter:
    def __init__(
        self,
        *,
        runner: KiloRunner,
        executable: str = "kilo",
        max_task_packet_bytes: int = 262_144,
    ) -> None:
        if not callable(getattr(runner, "run", None)):
            raise ValueError("runner must provide run")
        if not isinstance(executable, str) or not executable.strip() or "\x00" in executable:
            raise ValueError("executable must be a non-blank string")
        if (
            isinstance(max_task_packet_bytes, bool)
            or not isinstance(max_task_packet_bytes, int)
            or max_task_packet_bytes < 1
        ):
            raise ValueError("max_task_packet_bytes must be positive")
        self._runner = runner
        self._executable = executable
        self._max_task_packet_bytes = max_task_packet_bytes

    @staticmethod
    def _validate_dispatch(dispatch: HarnessDispatch) -> None:
        if dispatch.harness_strategy is not HarnessStrategy.LOCAL_CLI:
            raise KiloHarnessError("KILO_HARNESS_STRATEGY_UNSUPPORTED")
        if _KILO_COMPONENT_RE.fullmatch(dispatch.provider_id) is None:
            raise KiloHarnessError("KILO_PROVIDER_ID_INVALID")
        if _KILO_COMPONENT_RE.fullmatch(dispatch.model_id) is None:
            raise KiloHarnessError("KILO_MODEL_ID_INVALID")

    def _verified_packet(self, dispatch: HarnessDispatch, packet: TaskPacketFile) -> Path:
        if packet.task_contract_ref != dispatch.task_contract_ref:
            raise KiloHarnessError("TASK_PACKET_REF_MISMATCH")
        try:
            root = Path(dispatch.worktree_path).expanduser().resolve(strict=True)
        except OSError as exc:
            raise KiloHarnessError("KILO_WORKTREE_UNREADABLE") from exc
        if not root.is_dir():
            raise KiloHarnessError("KILO_WORKTREE_UNREADABLE")

        named = Path(packet.path).expanduser()
        if not named.is_absolute():
            named = root / named
        try:
            before = named.lstat()
        except OSError as exc:
            raise KiloHarnessError("TASK_PACKET_UNREADABLE") from exc
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise KiloHarnessError("TASK_PACKET_NOT_REGULAR")
        if before.st_size > self._max_task_packet_bytes:
            raise KiloHarnessError("TASK_PACKET_TOO_LARGE")
        try:
            resolved = named.resolve(strict=True)
        except OSError as exc:
            raise KiloHarnessError("TASK_PACKET_UNREADABLE") from exc
        if not _is_within(resolved, root):
            raise KiloHarnessError("TASK_PACKET_OUTSIDE_WORKTREE")

        identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        try:
            with named.open("rb") as handle:
                opened = os.fstat(handle.fileno())
                if (
                    opened.st_dev,
                    opened.st_ino,
                    opened.st_size,
                    opened.st_mtime_ns,
                ) != identity:
                    raise KiloHarnessError("TASK_PACKET_TOCTOU")
                raw = handle.read(self._max_task_packet_bytes + 1)
                final_handle = os.fstat(handle.fileno())
            after = named.lstat()
        except KiloHarnessError:
            raise
        except OSError as exc:
            raise KiloHarnessError("TASK_PACKET_UNREADABLE") from exc

        if len(raw) > self._max_task_packet_bytes:
            raise KiloHarnessError("TASK_PACKET_TOO_LARGE")
        if (
            final_handle.st_dev,
            final_handle.st_ino,
            final_handle.st_size,
            final_handle.st_mtime_ns,
        ) != identity:
            raise KiloHarnessError("TASK_PACKET_TOCTOU")
        if (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ) != identity:
            raise KiloHarnessError("TASK_PACKET_TOCTOU")
        digest = hashlib.sha256(raw).hexdigest()
        if digest.casefold() != packet.sha256.casefold():
            raise KiloHarnessError("TASK_PACKET_HASH_MISMATCH")
        return resolved

    def _build_invocation(self, dispatch: HarnessDispatch, packet_path: Path) -> KiloInvocation:
        model = f"{dispatch.provider_id}/{dispatch.model_id}"
        argv = [
            self._executable,
            "run",
            _FIXED_PROMPT,
            "--file",
            str(packet_path),
            "--pure",
            "--agent",
            "code",
            "--model",
            model,
            "--format",
            "json",
            "--dir",
            str(Path(dispatch.worktree_path).expanduser().resolve(strict=True)),
        ]
        if dispatch.effort_level not in (None, "DEFAULT"):
            variant = _EFFORT_VARIANTS.get(dispatch.effort_level)
            if variant is None:
                raise KiloHarnessError("KILO_EFFORT_UNSUPPORTED")
            argv.extend(("--variant", variant))
        return KiloInvocation(
            argv=tuple(argv),
            cwd=str(Path(dispatch.worktree_path).expanduser().resolve(strict=True)),
            timeout_seconds=dispatch.timeout_seconds,
            max_output_bytes=dispatch.max_output_bytes,
        )

    @staticmethod
    def _decode_events(stdout: str, redactions: tuple[str, ...]) -> tuple[dict[str, object], ...]:
        events: list[dict[str, object]] = []
        for line in stdout.splitlines():
            if not line.strip():
                continue
            try:
                decoded = json.loads(line)
            except (TypeError, json.JSONDecodeError) as exc:
                raise KiloHarnessError("KILO_OUTPUT_INVALID") from exc
            if not isinstance(decoded, dict):
                raise KiloHarnessError("KILO_OUTPUT_INVALID")
            events.append(_redact_json(decoded, redactions))
        if not events:
            raise KiloHarnessError("KILO_OUTPUT_INVALID")
        return tuple(events)

    def execute(
        self,
        dispatch: HarnessDispatch,
        packet: TaskPacketFile,
        *,
        redaction_values: tuple[str, ...] = (),
    ) -> KiloHarnessResult:
        if not isinstance(dispatch, HarnessDispatch):
            raise ValueError("dispatch must be HarnessDispatch")
        if not isinstance(packet, TaskPacketFile):
            raise ValueError("packet must be TaskPacketFile")
        redactions = tuple(value for value in redaction_values if isinstance(value, str) and value)
        self._validate_dispatch(dispatch)
        packet_path = self._verified_packet(dispatch, packet)
        invocation = self._build_invocation(dispatch, packet_path)
        raw = self._runner.run(invocation)
        if not isinstance(raw, KiloRunnerResult):
            raise KiloHarnessError("RUNNER_RESULT_INVALID")

        stderr = _redact_text(raw.stderr, redactions)
        if raw.timed_out:
            return KiloHarnessResult(
                HarnessExecutionStatus.TIMEOUT,
                None,
                stderr,
                raw.exit_code,
                raw.error_code,
            )

        output_size = len(raw.stdout.encode("utf-8")) + len(raw.stderr.encode("utf-8"))
        if output_size > dispatch.max_output_bytes:
            return KiloHarnessResult(
                HarnessExecutionStatus.OUTPUT_LIMIT,
                None,
                "",
                raw.exit_code,
                raw.error_code,
            )
        if raw.exit_code != 0:
            return KiloHarnessResult(
                HarnessExecutionStatus.FAILED,
                None,
                stderr,
                raw.exit_code,
                raw.error_code,
            )

        try:
            events = self._decode_events(raw.stdout, redactions)
        except KiloHarnessError:
            return KiloHarnessResult(
                HarnessExecutionStatus.OUTPUT_INVALID,
                None,
                stderr,
                raw.exit_code,
                raw.error_code,
            )
        if any(event.get("type") == "error" for event in events):
            return KiloHarnessResult(
                HarnessExecutionStatus.FAILED,
                events,
                stderr,
                raw.exit_code,
                raw.error_code,
            )
        if not any(event.get("type") == "text" for event in events):
            return KiloHarnessResult(
                HarnessExecutionStatus.OUTPUT_INVALID,
                events,
                stderr,
                raw.exit_code,
                raw.error_code,
            )
        return KiloHarnessResult(
            HarnessExecutionStatus.SUCCESS,
            events,
            stderr,
            raw.exit_code,
            raw.error_code,
        )
