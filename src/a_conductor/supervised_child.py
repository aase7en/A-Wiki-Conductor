"""Internal detached supervisor helper for one validated target subprocess.

The helper is intentionally stdlib-only so it can be executed by absolute
script path without relying on PYTHONPATH. It never persists target argv or
environment. Credential-bearing target streams are captured in memory, redacted
before forwarding to inherited durable handles, and fully drained before the
terminal result is published.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Thread
from typing import BinaryIO, Callable, Mapping, Sequence


SUPERVISED_RESULT_SCHEMA_VERSION = 1
_MAX_RESULT_BYTES = 32 * 1024
_RESULT_KEYS = frozenset(
    {
        "schema_version",
        "execution_id",
        "child_pid",
        "exit_code",
        "started_at",
        "finished_at",
    }
)


class SupervisedChildError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _require_text(value: str, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or "\x00" in value
        or "\r" in value
        or "\n" in value
    ):
        raise ValueError(f"{field_name} must be non-blank single-line text")
    return value


def _require_pid(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError("child_pid must be >= 1")
    return value


def _require_exit_code(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("exit_code must be an integer")
    return value


def _validated_argv(values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError("target_argv must be a sequence of strings")
    argv = tuple(values)
    if not argv:
        raise ValueError("target_argv must not be empty")
    for index, item in enumerate(argv):
        if (
            not isinstance(item, str)
            or not item
            or "\x00" in item
            or "\r" in item
            or "\n" in item
        ):
            raise ValueError(f"target_argv[{index}] is invalid")
    return argv


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    handle = None
    temporary_path: Path | None = None
    try:
        handle = tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        )
        temporary_path = Path(handle.name)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        handle = None
        os.replace(temporary_path, target)
    except OSError as exc:
        raise SupervisedChildError("ATOMIC_WRITE_FAILED") from exc
    finally:
        if handle is not None:
            handle.close()
        if temporary_path is not None and temporary_path.exists():
            try:
                temporary_path.unlink()
            except OSError:
                pass


def _write_pid_atomic(path: Path, pid: int) -> None:
    _write_bytes_atomic(Path(path), f"{_require_pid(pid)}\n".encode("utf-8"))


@dataclass(frozen=True, slots=True)
class SupervisedChildResult:
    schema_version: int
    execution_id: str
    child_pid: int
    exit_code: int
    started_at: str
    finished_at: str

    def __post_init__(self) -> None:
        if self.schema_version != SUPERVISED_RESULT_SCHEMA_VERSION:
            raise ValueError("unsupported supervised result schema_version")
        _require_text(self.execution_id, "execution_id")
        _require_pid(self.child_pid)
        _require_exit_code(self.exit_code)
        _require_text(self.started_at, "started_at")
        _require_text(self.finished_at, "finished_at")

    def as_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "execution_id": self.execution_id,
            "child_pid": self.child_pid,
            "exit_code": self.exit_code,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


def _strict_object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise SupervisedChildError("RESULT_INVALID")
        result[key] = value
    return result


def _reject_constant(_: str) -> object:
    raise SupervisedChildError("RESULT_INVALID")


def read_supervised_child_result(
    path: str | Path,
    *,
    expected_execution_id: str,
) -> SupervisedChildResult:
    _require_text(expected_execution_id, "expected_execution_id")
    target = Path(path)
    try:
        raw = target.read_bytes()
    except FileNotFoundError as exc:
        raise SupervisedChildError("RESULT_NOT_AVAILABLE") from exc
    except OSError as exc:
        raise SupervisedChildError("RESULT_READ_FAILED") from exc
    if len(raw) > _MAX_RESULT_BYTES:
        raise SupervisedChildError("RESULT_INVALID")
    try:
        text = raw.decode("utf-8", errors="strict")
        payload = json.loads(
            text,
            object_pairs_hook=_strict_object_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        if isinstance(exc, SupervisedChildError):
            raise
        raise SupervisedChildError("RESULT_INVALID") from exc
    if not isinstance(payload, Mapping) or set(payload) != _RESULT_KEYS:
        raise SupervisedChildError("RESULT_INVALID")
    try:
        result = SupervisedChildResult(
            schema_version=payload["schema_version"],
            execution_id=payload["execution_id"],
            child_pid=payload["child_pid"],
            exit_code=payload["exit_code"],
            started_at=payload["started_at"],
            finished_at=payload["finished_at"],
        )
    except (TypeError, ValueError) as exc:
        raise SupervisedChildError("RESULT_INVALID") from exc
    if result.execution_id != expected_execution_id:
        raise SupervisedChildError("RESULT_EXECUTION_MISMATCH")
    return result


_REDACTED = b"[REDACTED]"
_CAPTURE_CHUNK_BYTES = 64 * 1024
_MAX_REDACTION_SECRET_BYTES = 16 * 1024
_SENSITIVE_ENVIRONMENT_KEYS = ("ANTHROPIC_AUTH_TOKEN",)


def _secret_bytes_from_environment() -> tuple[bytes, ...]:
    values: list[bytes] = []
    for key in _SENSITIVE_ENVIRONMENT_KEYS:
        value = os.environ.get(key)
        if value:
            encoded = value.encode("utf-8")
            if len(encoded) > _MAX_REDACTION_SECRET_BYTES:
                raise SupervisedChildError("REDACTION_SECRET_TOO_LARGE")
            if encoded and encoded not in values:
                values.append(encoded)
    return tuple(sorted(values, key=len, reverse=True))


class _StreamingRedactor:
    def __init__(self, secrets: tuple[bytes, ...]) -> None:
        self._secrets = tuple(secret for secret in secrets if secret)
        self._pending = bytearray()
        self._max_secret = max((len(secret) for secret in self._secrets), default=1)

    def feed(self, chunk: bytes, *, final: bool = False) -> bytes:
        self._pending.extend(chunk)
        limit = len(self._pending) if final else max(0, len(self._pending) - self._max_secret + 1)
        output = bytearray()
        index = 0
        while index < limit:
            matched = next((secret for secret in self._secrets if self._pending.startswith(secret, index)), None)
            if matched is not None:
                output.extend(_REDACTED)
                index += len(matched)
            else:
                output.append(self._pending[index])
                index += 1
        del self._pending[:index]
        return bytes(output)


def _pump_redacted(source: BinaryIO, target: BinaryIO, secrets: tuple[bytes, ...], errors: list[BaseException]) -> None:
    redactor = _StreamingRedactor(secrets)
    write_failed = False
    try:
        reader = getattr(source, "read1", None)
        if not callable(reader):
            reader = source.read
        while True:
            chunk = reader(_CAPTURE_CHUNK_BYTES)
            if not chunk:
                break
            sanitized = redactor.feed(chunk)
            if sanitized and not write_failed:
                try:
                    target.write(sanitized)
                    target.flush()
                except BaseException as exc:
                    errors.append(exc)
                    write_failed = True
        tail = redactor.feed(b"", final=True)
        if tail and not write_failed:
            target.write(tail)
            target.flush()
    except BaseException as exc:
        errors.append(exc)


def run_supervised_child(
    *,
    execution_id: str,
    pid_path: str | Path,
    result_path: str | Path,
    cwd: str | Path,
    target_argv: Sequence[str],
    popen_factory: Callable[..., object] = subprocess.Popen,
    now_factory: Callable[[], str] = _utc_now,
) -> int:
    _require_text(execution_id, "execution_id")
    argv = _validated_argv(target_argv)
    working_directory = Path(cwd).expanduser().resolve(strict=False)
    if not working_directory.is_dir():
        raise ValueError("cwd must be an existing directory")
    started_at = _require_text(now_factory(), "started_at")
    secrets = _secret_bytes_from_environment()
    popen_kwargs = {
        "cwd": str(working_directory),
        "shell": False,
        "stdin": subprocess.DEVNULL,
    }
    if secrets:
        popen_kwargs.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        child = popen_factory(list(argv), **popen_kwargs)
    except Exception as exc:
        raise SupervisedChildError("CHILD_START_FAILED") from exc
    try:
        child_pid = _require_pid(getattr(child, "pid"))
        _write_pid_atomic(Path(pid_path), child_pid)
    except (TypeError, ValueError, SupervisedChildError) as exc:
        raise SupervisedChildError("CHILD_PID_PERSIST_FAILED") from exc
    capture_errors: list[BaseException] = []
    capture_threads: list[Thread] = []
    if secrets:
        stdout_pipe = getattr(child, "stdout", None)
        stderr_pipe = getattr(child, "stderr", None)
        if stdout_pipe is None or stderr_pipe is None:
            raise SupervisedChildError("OUTPUT_CAPTURE_SETUP_FAILED")
        stdout_target = getattr(sys.stdout, "buffer", sys.stdout)
        stderr_target = getattr(sys.stderr, "buffer", sys.stderr)
        capture_threads = [
            Thread(target=_pump_redacted, args=(stdout_pipe, stdout_target, secrets, capture_errors)),
            Thread(target=_pump_redacted, args=(stderr_pipe, stderr_target, secrets, capture_errors)),
        ]
        for thread in capture_threads:
            thread.start()
    try:
        exit_code = _require_exit_code(child.wait())
    except Exception as exc:
        raise SupervisedChildError("CHILD_WAIT_FAILED") from exc
    for thread in capture_threads:
        thread.join()
    if capture_errors:
        raise SupervisedChildError("OUTPUT_CAPTURE_FAILED") from capture_errors[0]
    finished_at = _require_text(now_factory(), "finished_at")
    result = SupervisedChildResult(
        schema_version=SUPERVISED_RESULT_SCHEMA_VERSION,
        execution_id=execution_id,
        child_pid=child_pid,
        exit_code=exit_code,
        started_at=started_at,
        finished_at=finished_at,
    )
    payload = json.dumps(
        result.as_payload(),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    _write_bytes_atomic(Path(result_path), payload)
    return exit_code


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--pid-path", required=True)
    parser.add_argument("--result-path", required=True)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("target", nargs=argparse.REMAINDER)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    namespace = parser.parse_args(argv)
    target = tuple(namespace.target)
    if target and target[0] == "--":
        target = target[1:]
    try:
        return run_supervised_child(
            execution_id=namespace.execution_id,
            pid_path=namespace.pid_path,
            result_path=namespace.result_path,
            cwd=namespace.cwd,
            target_argv=target,
        )
    except (ValueError, SupervisedChildError):
        return 125


if __name__ == "__main__":
    raise SystemExit(main())
