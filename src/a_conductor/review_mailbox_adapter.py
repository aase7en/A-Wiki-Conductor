"""Thin bridge from agent-mailbox review results to A-Wiki Review Bridge CLI.

This module owns no review lifecycle. It validates mailbox/result identity,
minimizes the payload, and invokes the accepted A-Wiki conductor CLI through
the existing bounded native command runner.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .agent_change_packets import AgentMailboxAssignment
from .native_execution import (
    NativeCommandResult,
    NativeCommandSpec,
    NativeExecutionError,
    NativeExecutionScope,
    NativeSubprocessRunner,
)

MAX_REVIEW_RESULT_BYTES = 64_000


class ReviewMailboxAdapterError(RuntimeError):
    """Code-only adapter failure safe for higher-level logging."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class _CommandRunner(Protocol):
    def run(self, spec: NativeCommandSpec) -> NativeCommandResult: ...


@dataclass(frozen=True, slots=True)
class ReviewMailboxResult:
    task_id: str
    provider_id: str
    model_id: str
    reviewed_head: str
    task_sha256: str
    _awiki_payload_json: str

    @property
    def awiki_payload(self) -> dict[str, object]:
        payload = json.loads(self._awiki_payload_json)
        assert isinstance(payload, dict)
        return payload


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(64 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ReviewMailboxAdapterError("TASK_PACKET_UNAVAILABLE") from exc
    return digest.hexdigest()


def _require_assignment(assignment: AgentMailboxAssignment) -> AgentMailboxAssignment:
    if not isinstance(assignment, AgentMailboxAssignment):
        raise ReviewMailboxAdapterError("MAILBOX_ASSIGNMENT_INVALID")
    return assignment


def _verify_task_packet(assignment: AgentMailboxAssignment) -> None:
    if _sha256_file(Path(assignment.task_ref)) != assignment.task_sha256:
        raise ReviewMailboxAdapterError("TASK_PACKET_HASH_MISMATCH")


def _result_bytes(path: Path) -> bytes:
    try:
        if not path.is_file():
            raise ReviewMailboxAdapterError("REVIEW_RESULT_UNAVAILABLE")
        if path.stat().st_size > MAX_REVIEW_RESULT_BYTES:
            raise ReviewMailboxAdapterError("REVIEW_RESULT_TOO_LARGE")
        raw = path.read_bytes()
    except ReviewMailboxAdapterError:
        raise
    except OSError as exc:
        raise ReviewMailboxAdapterError("REVIEW_RESULT_UNAVAILABLE") from exc
    if len(raw) > MAX_REVIEW_RESULT_BYTES:
        raise ReviewMailboxAdapterError("REVIEW_RESULT_TOO_LARGE")
    return raw


class ReviewMailboxResultReader:
    """Validate exact mailbox identity without interpreting review lifecycle."""
    def read(self, assignment: AgentMailboxAssignment) -> ReviewMailboxResult:
        assignment = _require_assignment(assignment)
        if not re.fullmatch(r"[0-9a-f]{7,40}", assignment.base_head):
            raise ReviewMailboxAdapterError("REVIEW_HEAD_INVALID_FOR_AWIKI")
        _verify_task_packet(assignment)
        raw = _result_bytes(Path(assignment.result_ref))
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ReviewMailboxAdapterError("REVIEW_RESULT_INVALID") from exc
        if not isinstance(decoded, dict):
            raise ReviewMailboxAdapterError("REVIEW_RESULT_INVALID")

        checks = (
            ("task_id", assignment.task_id, "REVIEW_TASK_MISMATCH"),
            ("provider_id", assignment.provider_id, "REVIEW_PROVIDER_MISMATCH"),
            ("model_id", assignment.model_id, "REVIEW_MODEL_MISMATCH"),
            ("reviewed_head", assignment.base_head, "REVIEW_HEAD_MISMATCH"),
            ("task_sha256", assignment.task_sha256, "REVIEW_TASK_HASH_MISMATCH"),
        )
        for field, expected, code in checks:
            if decoded.get(field) != expected:
                raise ReviewMailboxAdapterError(code)

        payload = {
            "task_id": assignment.task_id,
            "reviewed_head": assignment.base_head,
            "task_sha256": assignment.task_sha256,
            "model": assignment.model_id,
            "verdict": decoded.get("verdict"),
            "findings": decoded.get("findings", []),
        }
        return ReviewMailboxResult(
            task_id=assignment.task_id,
            provider_id=assignment.provider_id,
            model_id=assignment.model_id,
            reviewed_head=assignment.base_head,
            task_sha256=assignment.task_sha256,
            _awiki_payload_json=json.dumps(
                payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
            ),
        )


def _verify_result_binding(
    assignment: AgentMailboxAssignment,
    result: ReviewMailboxResult,
) -> None:
    checks = (
        (result.task_id, assignment.task_id, "REVIEW_TASK_MISMATCH"),
        (result.provider_id, assignment.provider_id, "REVIEW_PROVIDER_MISMATCH"),
        (result.model_id, assignment.model_id, "REVIEW_MODEL_MISMATCH"),
        (result.reviewed_head, assignment.base_head, "REVIEW_HEAD_MISMATCH"),
        (result.task_sha256, assignment.task_sha256, "REVIEW_TASK_HASH_MISMATCH"),
    )
    for actual, expected, code in checks:
        if actual != expected:
            raise ReviewMailboxAdapterError(code)


class ReviewResultForwarder:
    """Forward a validated result to the accepted A-Wiki review-ingest CLI."""

    def __init__(
        self,
        *,
        runner: _CommandRunner,
        python_executable: str,
        timeout_seconds: int = 30,
    ) -> None:
        if not callable(getattr(runner, "run", None)):
            raise ReviewMailboxAdapterError("COMMAND_RUNNER_INVALID")
        if (
            not isinstance(python_executable, str)
            or not python_executable.strip()
            or "\x00" in python_executable
        ):
            raise ReviewMailboxAdapterError("PYTHON_EXECUTABLE_INVALID")
        if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool) or timeout_seconds < 1:
            raise ReviewMailboxAdapterError("FORWARD_TIMEOUT_INVALID")
        self._runner = runner
        self._python_executable = python_executable
        self._timeout_seconds = timeout_seconds

    def forward(
        self,
        assignment: AgentMailboxAssignment,
        result: ReviewMailboxResult,
    ) -> dict[str, object]:
        assignment = _require_assignment(assignment)
        if not isinstance(result, ReviewMailboxResult):
            raise ReviewMailboxAdapterError("REVIEW_RESULT_OBJECT_INVALID")
        _verify_result_binding(assignment, result)
        _verify_task_packet(assignment)

        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                prefix="a-conductor-review-",
                suffix=".json",
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                json.dump(
                    result.awiki_payload,
                    handle,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                handle.flush()
                os.fsync(handle.fileno())

            spec = NativeCommandSpec(
                argv=(
                    self._python_executable,
                    "-m",
                    "conductor",
                    "review",
                    "ingest",
                    "--task",
                    assignment.task_id,
                    "--file",
                    str(temp_path),
                    "--json",
                ),
                cwd=".",
                timeout_seconds=self._timeout_seconds,
                mutation_intent=True,
            )
            try:
                command = self._runner.run(spec)
            except NativeExecutionError as exc:
                raise ReviewMailboxAdapterError("AWIKI_REVIEW_FORWARD_FAILED") from exc
            except Exception as exc:
                raise ReviewMailboxAdapterError("AWIKI_REVIEW_FORWARD_FAILED") from exc
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass

        if not isinstance(command, NativeCommandResult):
            raise ReviewMailboxAdapterError("AWIKI_REVIEW_RESPONSE_INVALID")
        if command.timed_out:
            raise ReviewMailboxAdapterError("AWIKI_REVIEW_FORWARD_TIMEOUT")
        if command.stdout_truncated or command.stderr_truncated:
            raise ReviewMailboxAdapterError("AWIKI_REVIEW_FORWARD_TRUNCATED")
        if command.exit_code != 0:
            raise ReviewMailboxAdapterError("AWIKI_REVIEW_FORWARD_FAILED")
        try:
            response = json.loads(command.stdout)
        except json.JSONDecodeError as exc:
            raise ReviewMailboxAdapterError("AWIKI_REVIEW_RESPONSE_INVALID") from exc
        if not isinstance(response, dict):
            raise ReviewMailboxAdapterError("AWIKI_REVIEW_RESPONSE_INVALID")
        if response.get("ok") is not True:
            raise ReviewMailboxAdapterError("AWIKI_REVIEW_REJECTED")
        if response.get("task_id") != assignment.task_id:
            raise ReviewMailboxAdapterError("AWIKI_REVIEW_TASK_MISMATCH")
        return response


def build_review_result_forwarder(
    *,
    awiki_root: Path | str,
    python_executable: str,
    timeout_seconds: int = 30,
) -> ReviewResultForwarder:
    """Build the production adapter with one pinned A-Wiki/Python command scope."""
    if (
        not isinstance(timeout_seconds, int)
        or isinstance(timeout_seconds, bool)
        or timeout_seconds < 1
    ):
        raise ReviewMailboxAdapterError("FORWARD_TIMEOUT_INVALID")
    if (
        not isinstance(python_executable, str)
        or not python_executable.strip()
        or "\x00" in python_executable
    ):
        raise ReviewMailboxAdapterError("PYTHON_EXECUTABLE_INVALID")
    try:
        scope = NativeExecutionScope(
            root=awiki_root,
            mutation_allowed=True,
            allowed_executables=(Path(python_executable).name,),
            max_timeout_seconds=timeout_seconds,
            max_output_bytes=MAX_REVIEW_RESULT_BYTES,
        )
    except NativeExecutionError as exc:
        raise ReviewMailboxAdapterError("AWIKI_ROOT_INVALID") from exc
    return ReviewResultForwarder(
        runner=NativeSubprocessRunner(scope),
        python_executable=python_executable,
        timeout_seconds=timeout_seconds,
    )
