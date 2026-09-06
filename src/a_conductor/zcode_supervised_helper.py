"""WO-P1-158 — supervised ZCode helper (specialized lifecycle executable).

The helper OWNS process lifecycle for exactly one allowlisted app-server
child and enforces the ordering guarantee: exact OS-observed child identity
is durably persisted and verified BEFORE any task protocol message is sent.

Runtime task authority reaches the helper ONLY through the accepted
non-persistent environment channel (never argv):

- ``ZCODE_TASK_PACKET_PATH``         trusted task-packet file path
- ``ZCODE_TASK_PACKET_SHA256``       expected packet SHA-256 (64 hex)
- ``ZCODE_TASK_PACKET_TRUSTED_ROOT`` confinement root for the packet path
- ``ZCODE_TASK_PACKET_MAX_BYTES``    packet size bound
- ``ZCODE_OUTPUT_BUDGET``            response budget (<= 64 KiB)
- ``ZCODE_DEADLINE_SECONDS``         bounded protocol deadline
- ``ZCODE_CREDENTIAL_DELIVERY_KEY``  env var name carrying the credential
- ``<delivery key>``                 the resolved credential value

The packet is RE-OPENED and fully re-verified (trusted-root confinement,
regular file, size, SHA-256, UTF-8) immediately before the protocol send;
cached bytes are never the final authority. The credential is forwarded to
the child ONLY through an explicitly constructed child environment — the
parent environment is never inherited and conflicting legacy credential
variables are denied by construction. Shutdown is stdin EOF + bounded
natural-exit wait: no terminate/kill ladder exists here.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from typing import Mapping

try:  # package import (normal)
    from .zcode_protocol import ZCODE_MAX_RESPONSE_BYTES
except ImportError:  # script-mode execution by the supervised supervisor
    from zcode_protocol import ZCODE_MAX_RESPONSE_BYTES  # type: ignore

try:  # package import (normal)
    from .zcode_process_truth import observe_child_process
except ImportError:  # script mode: sibling already importable from sys.path[0]
    from zcode_process_truth import observe_child_process  # type: ignore

_CHILD_IDENTITY_SCHEMA = "zcode-child-identity/1"
_ARGV_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")

# Fixed allowlisted app-server argv shape (the supervisor supplies exact
# absolute paths per deployment; this grammar rejects any prompt/task content).
ZCODE_APP_SERVER_ARGV_GRAMMAR = (
    "<zcode-exe>", "<bundle-js>", "app-server", "--stdio", "--surface", "desktop",
)

# The app-server child environment is EXPLICITLY constructed from exactly
# these entries. Conflicting legacy credential variables (an unauthorized
# token fallback) are denied: they can never enter the child environment.
_HELPER_CHILD_ENV_BASE = {"ELECTRON_RUN_AS_NODE": "1"}
_DENIED_LEGACY_CREDENTIAL_ENV_KEYS = frozenset({
    "ANTHROPIC_AUTH_TOKEN", "CLAUDE_API_KEY", "OPENAI_API_KEY", "ZCODE_API_KEY",
})

# bounded accepted deadline ceiling for the protocol turn
ZCODE_HELPER_MAX_DEADLINE_SECONDS = 3600.0
# bounded natural-exit wait after stdin EOF (no kill ladder after it)
ZCODE_HELPER_EXIT_WAIT_SECONDS = 30.0


def validate_app_server_argv(argv: tuple[str, ...], *, executable: str, bundle_js: str) -> bool:
    """True iff argv matches the fixed allowlisted app-server shape exactly.

    Prompt/task content can never appear: the grammar has exactly six tokens,
    tokens 3-6 are literals, and tokens 1-2 must equal the configured
    executable/bundle paths exactly.
    """
    if not isinstance(argv, tuple) or len(argv) != 6:
        return False
    if argv[0] != executable or argv[1] != bundle_js:
        return False
    return tuple(argv[2:]) == ("app-server", "--stdio", "--surface", "desktop")


def target_argv_sha256(argv: tuple[str, ...]) -> str:
    if not isinstance(argv, tuple) or not argv or not all(isinstance(a, str) and a for a in argv):
        raise ValueError("argv is invalid")
    return hashlib.sha256("\x00".join(argv).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ZCodeChildIdentity:
    child_pid: int
    child_created_epoch_ms: int
    executable: str
    parent_pid: int
    target_argv_sha256: str
    execution_id: str

    def __post_init__(self) -> None:
        for name in ("child_pid", "parent_pid"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} is invalid")
        if (
            isinstance(self.child_created_epoch_ms, bool)
            or not isinstance(self.child_created_epoch_ms, int)
            or self.child_created_epoch_ms < 1
        ):
            raise ValueError("child_created_epoch_ms is invalid")
        if not isinstance(self.executable, str) or not self.executable.strip():
            raise ValueError("executable is invalid")
        if not _ARGV_SHA_RE.fullmatch(self.target_argv_sha256):
            raise ValueError("target_argv_sha256 is invalid")
        if not isinstance(self.execution_id, str) or not re.fullmatch(
            r"exec-[0-9a-f]{16}", self.execution_id
        ):
            raise ValueError("execution_id is invalid")

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": _CHILD_IDENTITY_SCHEMA,
            "execution_id": self.execution_id,
            "child_pid": self.child_pid,
            "child_created_epoch_ms": self.child_created_epoch_ms,
            "executable": self.executable,
            "parent_pid": self.parent_pid,
            "target_argv_sha256": self.target_argv_sha256,
        }

    def matches(self, other: "ZCodeChildIdentity") -> bool:
        """Exact PID-reuse-proof identity: same PID AND same creation time AND
        same executable AND same argv hash. Same PID with a different creation
        time is a MISMATCH."""
        if not isinstance(other, ZCodeChildIdentity):
            return False
        return (
            self.child_pid == other.child_pid
            and self.child_created_epoch_ms == other.child_created_epoch_ms
            and self.executable.casefold() == other.executable.casefold()
            and self.target_argv_sha256 == other.target_argv_sha256
        )


def parse_child_identity_document(raw: object) -> ZCodeChildIdentity:
    """Parse + validate a child.identity.json document.

    Fails closed on: non-mapping payloads, wrong/missing schema tag, unknown
    fields (no smuggled prompt/secret keys), and malformed values.
    """
    if not isinstance(raw, Mapping):
        raise ValueError("identity document is invalid")
    if set(raw.keys()) != _ALLOWED_FIELDS:
        raise ValueError("identity document fields are invalid")
    if raw["schema"] != _CHILD_IDENTITY_SCHEMA:
        raise ValueError("identity schema is unsupported")
    return ZCodeChildIdentity(
        child_pid=raw["child_pid"],
        child_created_epoch_ms=raw["child_created_epoch_ms"],
        executable=raw["executable"],
        parent_pid=raw["parent_pid"],
        target_argv_sha256=raw["target_argv_sha256"],
        execution_id=raw["execution_id"],
    )


def serialize_child_identity_document(identity: ZCodeChildIdentity) -> str:
    """Canonical JSON serialization (sorted keys, compact separators)."""
    return json.dumps(identity.as_dict(), sort_keys=True, separators=(",", ":"))


def validate_output_budget(max_response_bytes: int) -> int:
    """Fail BEFORE spawn when a dispatch exceeds the production cap."""
    if (
        isinstance(max_response_bytes, bool)
        or not isinstance(max_response_bytes, int)
        or max_response_bytes < 1
        or max_response_bytes > ZCODE_MAX_RESPONSE_BYTES
    ):
        raise ValueError("ZCODE_OUTPUT_BUDGET_UNSUPPORTED")
    return max_response_bytes


_ALLOWED_FIELDS = frozenset({
    "schema", "execution_id", "child_pid", "child_created_epoch_ms",
    "executable", "parent_pid", "target_argv_sha256",
})


# ---------------- executable supervised CLI entrypoint ----------------

@dataclass(frozen=True, slots=True)
class _HelperRuntimeMetadata:
    """Bounded runtime task authority received via the accepted env channel."""

    packet_path: str
    packet_sha256: str
    trusted_root: str
    max_packet_bytes: int
    output_budget: int
    deadline_seconds: float
    delivery_key: str
    credential: str


class _HelperExit(Exception):
    """Typed bounded exit: code only, never argv/env/traceback material."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _load_runtime_metadata(environ: Mapping[str, str]) -> _HelperRuntimeMetadata:
    """Validate the FULL accepted metadata contract BEFORE any spawn."""

    def _required(name: str) -> str:
        value = environ.get(name, "")
        if not isinstance(value, str) or not value.strip():
            raise _HelperExit("RUNTIME_METADATA_MISSING")
        return value

    packet_path = _required("ZCODE_TASK_PACKET_PATH")
    packet_sha256 = _required("ZCODE_TASK_PACKET_SHA256").strip().casefold()
    if not _SHA256_RE.fullmatch(packet_sha256):
        raise _HelperExit("RUNTIME_METADATA_INVALID")
    trusted_root = _required("ZCODE_TASK_PACKET_TRUSTED_ROOT")
    try:
        max_packet_bytes = int(_required("ZCODE_TASK_PACKET_MAX_BYTES"))
        output_budget = int(_required("ZCODE_OUTPUT_BUDGET"))
        deadline_seconds = float(_required("ZCODE_DEADLINE_SECONDS"))
    except ValueError:
        raise _HelperExit("RUNTIME_METADATA_INVALID") from None
    if max_packet_bytes < 1 or max_packet_bytes > 262_144:
        raise _HelperExit("RUNTIME_METADATA_INVALID")
    try:
        output_budget = validate_output_budget(output_budget)
    except ValueError:
        raise _HelperExit("ZCODE_OUTPUT_BUDGET_UNSUPPORTED") from None
    if not (0 < deadline_seconds <= ZCODE_HELPER_MAX_DEADLINE_SECONDS):
        raise _HelperExit("RUNTIME_METADATA_INVALID")
    delivery_key = _required("ZCODE_CREDENTIAL_DELIVERY_KEY")
    if not _ENV_NAME_RE.fullmatch(delivery_key):
        raise _HelperExit("RUNTIME_METADATA_INVALID")
    credential = environ.get(delivery_key, "")
    if not isinstance(credential, str) or not credential:
        raise _HelperExit("RUNTIME_METADATA_CREDENTIAL_MISSING")
    return _HelperRuntimeMetadata(
        packet_path=packet_path,
        packet_sha256=packet_sha256,
        trusted_root=trusted_root,
        max_packet_bytes=max_packet_bytes,
        output_budget=output_budget,
        deadline_seconds=deadline_seconds,
        delivery_key=delivery_key,
        credential=credential,
    )


def _build_child_environment(metadata: _HelperRuntimeMetadata) -> dict[str, str]:
    """EXPLICITLY constructed child environment: base + the accepted
    credential entry only. No parent inheritance; denied legacy credential
    variables are asserted absent (fail closed if ever introduced)."""
    environment = dict(_HELPER_CHILD_ENV_BASE)
    environment[metadata.delivery_key] = metadata.credential
    for denied in _DENIED_LEGACY_CREDENTIAL_ENV_KEYS:
        if denied in environment:
            raise _HelperExit("CHILD_ENV_CONFLICT")
    return environment


def _verify_packet_bytes(metadata: _HelperRuntimeMetadata) -> str:
    """Re-open the REAL packet immediately before the protocol send.

    Verifies trusted-root confinement, regular file, size bound, SHA-256,
    and UTF-8; returns the exact verified bytes. Cached content is never
    the final authority (there is no cached copy in this helper at all).
    """
    from pathlib import Path

    root = Path(metadata.trusted_root).expanduser().resolve(strict=False)
    path = Path(metadata.packet_path).expanduser().resolve(strict=False)
    try:
        path.relative_to(root)
    except ValueError:
        raise _HelperExit("ZCODE_TASK_PACKET_OUTSIDE_TRUSTED_ROOT") from None
    if not path.is_file():
        raise _HelperExit("ZCODE_TASK_PACKET_UNREADABLE")
    try:
        raw = path.read_bytes()
    except OSError:
        raise _HelperExit("ZCODE_TASK_PACKET_UNREADABLE") from None
    if len(raw) > metadata.max_packet_bytes:
        raise _HelperExit("ZCODE_TASK_PACKET_TOO_LARGE")
    if hashlib.sha256(raw).hexdigest().casefold() != metadata.packet_sha256:
        raise _HelperExit("ZCODE_TASK_PACKET_TOCTOU") from None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        raise _HelperExit("ZCODE_TASK_PACKET_UNREADABLE") from None


def _write_atomic(path, text: str) -> None:
    from pathlib import Path

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, target)


def main(argv: "list[str] | None" = None) -> int:
    """Bounded supervised ZCode helper CLI (see module docstring)."""
    import argparse as _argparse
    import queue as _queue
    import subprocess as _subprocess
    import sys as _sys
    import threading as _threading
    from datetime import datetime as _datetime, timezone as _timezone
    from pathlib import Path as _Path

    try:
        from .zcode_protocol import ZCodeProtocolDriver, ZCodeProtocolError
    except ImportError:  # script mode: sibling already importable from sys.path[0]
        from zcode_protocol import ZCodeProtocolDriver, ZCodeProtocolError  # type: ignore

    def _fail(code: str) -> int:
        print(f"ZCODE_HELPER_EXIT code={code}", file=_sys.stderr, flush=True)
        return 1

    parser = _argparse.ArgumentParser(prog="zcode-supervised-helper", add_help=False)
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--pid-path", required=True)
    parser.add_argument("--result-path", required=True)
    parser.add_argument("--report-path", default=None)
    parser.add_argument("--cwd", default=".")
    parser.add_argument("target", nargs=_argparse.REMAINDER)
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return _fail("ARGUMENTS_INVALID")
    if not args.target or args.target[0] != "--":
        return _fail("ARGUMENTS_INVALID")
    target_argv = tuple(args.target[1:])
    if len(target_argv) != 6 or target_argv[2:] != ("app-server", "--stdio", "--surface", "desktop"):
        return _fail("TARGET_ARGV_NOT_ALLOWLISTED")

    executable = target_argv[0]
    bundle_js = target_argv[1]
    pid_path = _Path(args.pid_path)
    result_path = _Path(args.result_path)
    report_path = _Path(args.report_path) if args.report_path else None
    cwd = _Path(args.cwd)
    run_dir = result_path.parent
    identity_path = run_dir / "child.identity.json"

    child = None
    try:
        # 1. full runtime-metadata contract BEFORE any spawn
        metadata = _load_runtime_metadata(os.environ)
        child_environment = _build_child_environment(metadata)

        # 2. spawn exactly one app-server child (explicit environment only)
        try:
            child = _subprocess.Popen(
                list(target_argv),
                cwd=str(cwd),
                env=child_environment,
                stdin=_subprocess.PIPE,
                stdout=_subprocess.PIPE,
                stderr=_subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except OSError:
            return _fail("CHILD_SPAWN_FAILED")

        # 3. exact child identity from REAL OS observation (fail closed —
        #    never wall-clock approximations, never the helper's parent PID)
        observed = observe_child_process(child.pid)
        if observed is None:
            return _fail("ZCODE_CHILD_IDENTITY_UNAVAILABLE")
        helper_pid = os.getpid()
        if int(observed["parent_pid"]) != helper_pid:
            return _fail("ZCODE_CHILD_IDENTITY_UNAVAILABLE")
        identity = ZCodeChildIdentity(
            child_pid=child.pid,
            child_created_epoch_ms=int(observed["created_epoch_ms"]),
            executable=str(observed["executable"]),
            parent_pid=int(observed["parent_pid"]),
            target_argv_sha256=target_argv_sha256(target_argv),
            execution_id=args.execution_id,
        )
        # identity BEFORE protocol: atomic write -> re-parse -> exact match
        try:
            _write_atomic(identity_path, serialize_child_identity_document(identity))
            reparsed = parse_child_identity_document(
                json.loads(identity_path.read_text(encoding="utf-8"))
            )
        except (OSError, ValueError):
            return _fail("IDENTITY_WRITE_FAILED")
        if not reparsed.matches(identity):
            return _fail("IDENTITY_WRITE_FAILED")
        _write_atomic(pid_path, str(child.pid))

        # 4. bounded transport: one blocking reader thread feeding a queue so
        #    read_line(timeout_seconds) ACTUALLY respects its timeout (a raw
        #    readline() would block forever on a silent child).
        lines: "_queue.Queue[str | None]" = _queue.Queue()

        def _reader(stream, sink: "_queue.Queue[str | None]") -> None:
            try:
                for line in stream:
                    sink.put(line)
            except (OSError, ValueError):
                pass
            finally:
                sink.put(None)  # stream closed / child exited

        reader_thread = _threading.Thread(
            target=_reader, args=(child.stdout, lines), daemon=True
        )
        reader_thread.start()

        class _ChildTransport:
            def send_line(self, text):
                child.stdin.write(text + "\n")
                child.stdin.flush()

            def read_line(self, timeout_seconds):
                try:
                    line = lines.get(timeout=max(0.0, float(timeout_seconds)))
                except _queue.Empty:
                    return None
                if line is None or line == "":
                    return None
                return line.rstrip("\r\n") or None

            def alive(self):
                return child.poll() is None

            def close_stdin_and_wait(self, *, exit_wait_seconds):
                try:
                    child.stdin.close()
                except OSError:
                    pass
                try:
                    return child.wait(timeout=max(0.0, float(exit_wait_seconds)))
                except _subprocess.TimeoutExpired:
                    return None

        def _natural_shutdown() -> int | None:
            """stdin EOF -> bounded natural-exit wait. NO kill ladder."""
            code = _ChildTransport.close_stdin_and_wait(
                _ChildTransport(), exit_wait_seconds=ZCODE_HELPER_EXIT_WAIT_SECONDS
            )
            return code

        # 5. re-open + fully re-verify the REAL task packet immediately
        #    before the first protocol send; those exact bytes are the input
        prompt = _verify_packet_bytes(metadata)

        started = _datetime.now(_timezone.utc).isoformat()
        driver = ZCodeProtocolDriver(
            _ChildTransport(), max_response_bytes=metadata.output_budget
        )
        report: dict | None = None
        turn = None
        try:
            turn = driver.run_turn(
                prompt,
                workspace=str(cwd),
                deadline_seconds=metadata.deadline_seconds,
            )
        except ZCodeProtocolError as exc:
            _natural_shutdown()
            return _fail(exc.code)
        except (OSError, ValueError):
            _natural_shutdown()
            return _fail("PROTOCOL_FAILED")
        finished = _datetime.now(_timezone.utc).isoformat()

        # 6. bounded natural shutdown — known exit or RECOVERY_REQUIRED
        exit_code = _natural_shutdown()
        if not isinstance(exit_code, int):
            # protocol completed but no known terminal exit within the bound:
            # report records the pending state; result is NEVER fabricated.
            report = {
                "schema": "zcode-report/1",
                "execution_id": args.execution_id,
                "task_packet_sha256": metadata.packet_sha256,
                "response_bytes": turn.bytes_received,
                "response_sha256": hashlib.sha256(turn.response_text.encode("utf-8")).hexdigest(),
                "session_id": turn.session_id,
                "exit_state": "EXIT_PENDING",
            }
            if report_path is not None:
                _write_atomic(report_path, json.dumps(report, sort_keys=True, separators=(",", ":")))
            return _fail("EXIT_PENDING")

        # 7. canonical artifacts, strict order: report BEFORE result; the
        #    six-key result exists ONLY on the real terminal exit above.
        report = {
            "schema": "zcode-report/1",
            "execution_id": args.execution_id,
            "task_packet_sha256": metadata.packet_sha256,
            "response_bytes": turn.bytes_received,
            "response_sha256": hashlib.sha256(turn.response_text.encode("utf-8")).hexdigest(),
            "session_id": turn.session_id,
        }
        if report_path is not None:
            _write_atomic(report_path, json.dumps(report, sort_keys=True, separators=(",", ":")))
        result = {
            "schema_version": 1,
            "execution_id": args.execution_id,
            "child_pid": child.pid,
            "exit_code": exit_code,
            "started_at": started,
            "finished_at": finished,
        }
        _write_atomic(result_path, json.dumps(result, sort_keys=True, separators=(",", ":")))

        # the response text is the helper's ONLY stdout payload (bounded by
        # the protocol budget); typed codes go to stderr in every failure path
        _sys.stdout.write(turn.response_text)
        _sys.stdout.flush()
        return 0
    except _HelperExit as exc:
        if child is not None:
            # bounded best-effort natural shutdown on the failure path
            try:
                child.stdin and child.stdin.close()
                child.wait(timeout=ZCODE_HELPER_EXIT_WAIT_SECONDS)
            except (OSError, ValueError, _subprocess.TimeoutExpired):
                pass
        return _fail(exc.code)


if __name__ == "__main__":
    raise SystemExit(main())
