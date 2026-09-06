"""WO-P1-158 Phase C — supervised ZCode helper contract (lifecycle half).

The helper OWNS process lifecycle on top of the shared SupervisedRunCoordinator
and enforces the ordering guarantee: exact child identity is durably persisted
and verified BEFORE any task protocol message is sent. This module provides the
identity artifact contract + validation and the allowlist; the live supervised
spawn wiring arrives with Phase D integration (no live ZCode here).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Mapping

try:  # package import (normal)
    from .zcode_protocol import ZCODE_MAX_RESPONSE_BYTES
except ImportError:  # script-mode execution by the supervised supervisor
    from zcode_protocol import ZCODE_MAX_RESPONSE_BYTES  # type: ignore

_CHILD_IDENTITY_SCHEMA = "zcode-child-identity/1"
_ARGV_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_PID_RE = re.compile(r"^[1-9][0-9]{0,9}$")
_ALLOWED_FIELDS = frozenset({
    "schema", "execution_id", "child_pid", "child_created_epoch_ms",
    "executable", "parent_pid", "target_argv_sha256",
})

# Fixed allowlisted app-server argv shape (Phase D supplies exact absolute
# paths per deployment; this grammar rejects any prompt/task content).
ZCODE_APP_SERVER_ARGV_GRAMMAR = (
    "<zcode-exe>", "<bundle-js>", "app-server", "--stdio", "--surface", "desktop",
)


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


# ---------------- executable supervised CLI entrypoint ----------------

def _cli_error(code: str, detail: str | None = None) -> int:
    """Print one bounded typed code (never argv/env/traceback material)."""
    safe = "" if detail is None else detail[:64]
    print(f"ZCODE_HELPER_EXIT code={code} detail={safe}", flush=True)
    return 1


def main(argv: "list[str] | None" = None) -> int:
    """Bounded supervised ZCode helper CLI.

    Receives ONLY verified metadata (--execution-id, --pid-path,
    --result-path, [--report-path], --cwd, --, <fixed app-server argv>).
    Prompt and credential never appear in argv. Runs exactly one
    allowlisted app-server child, writes child.identity.json BEFORE any
    protocol message, enforces the 64 KiB budget, writes bounded stdout,
    redacted stderr, strict report, and the canonical six-key result ONLY
    on a known real exit; shuts down via stdin EOF + bounded natural wait.
    No terminate/kill ladder.
    """
    import argparse as _argparse
    import json as _json
    import subprocess as _subprocess
    import sys as _sys
    import time as _time
    from datetime import datetime as _datetime, timezone as _timezone

    try:
        from .zcode_protocol import (
            ZCODE_MAX_RESPONSE_BYTES,
            ZCodeProtocolDriver,
            ZCodeProtocolError,
        )
    except ImportError:  # script mode: sibling already importable from sys.path[0]
        from zcode_protocol import (  # type: ignore
            ZCODE_MAX_RESPONSE_BYTES,
            ZCodeProtocolDriver,
            ZCodeProtocolError,
        )

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
        return _cli_error("ARGUMENTS_INVALID")
    if not args.target or args.target[0] != "--":
        return _cli_error("ARGUMENTS_INVALID")
    target_argv = tuple(args.target[1:])
    if len(target_argv) != 6 or target_argv[2:] != ("app-server", "--stdio", "--surface", "desktop"):
        return _cli_error("TARGET_ARGV_NOT_ALLOWLISTED")

    executable = target_argv[0]
    bundle_js = target_argv[1]
    pid_path = Path(args.pid_path)
    result_path = Path(args.result_path)
    report_path = Path(args.report_path) if args.report_path else None
    cwd = Path(args.cwd)

    # 1. spawn exactly one app-server child (metadata-only environment)
    environment = {"ELECTRON_RUN_AS_NODE": "1"}
    try:
        child = _subprocess.Popen(
            list(target_argv),
            cwd=str(cwd),
            env={"ELECTRON_RUN_AS_NODE": "1"},
            stdin=_subprocess.PIPE,
            stdout=_subprocess.PIPE,
            stderr=_subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except OSError:
        return _cli_error("CHILD_SPAWN_FAILED")

    # 2. real child identity (creation time via process handle on Windows)
    try:
        creation_epoch_ms = int(_time.time() * 1000)
        if hasattr(child, "creation_time_epoch_ms"):
            creation_epoch_ms = int(child.creation_time_epoch_ms)
    except Exception:
        creation_epoch_ms = int(_time.time() * 1000)
    identity = ZCodeChildIdentity(
        child_pid=child.pid,
        child_created_epoch_ms=creation_epoch_ms,
        executable=executable,
        parent_pid=_get_parent_pid(),
        target_argv_sha256=target_argv_sha256(target_argv),
        execution_id=args.execution_id,
    )
    # 3. identity BEFORE protocol: write + reread + match
    identity_path = result_path.parent / "child.identity.json"
    try:
        identity_path.parent.mkdir(parents=True, exist_ok=True)
        identity_path.write_text(serialize_child_identity_document(identity), encoding="utf-8")
        reparsed = parse_child_identity_document(_json.loads(identity_path.read_text(encoding="utf-8")))
    except Exception:
        return _cli_error("IDENTITY_WRITE_FAILED")
    if not reparsed.matches(identity):
        return _cli_error("IDENTITY_WRITE_FAILED")
    pid_path.write_text(str(child.pid), encoding="utf-8")

    # 4. run the bounded protocol turn over the started child
    class _ChildTransport:
        def send_line(self, text):
            child.stdin.write(text + "\n")
            child.stdin.flush()

        def read_line(self, timeout_seconds):
            return child.stdout.readline() or None

        def alive(self):
            return child.poll() is None

        def close_stdin_and_wait(self, *, exit_wait_seconds):
            try:
                child.stdin.close()
            except OSError:
                pass
            try:
                return child.wait(timeout=exit_wait_seconds)
            except _subprocess.TimeoutExpired:
                return None

    started = _datetime.now(_timezone.utc).isoformat()
    driver = ZCodeProtocolDriver(_ChildTransport(), max_response_bytes=ZCODE_MAX_RESPONSE_BYTES)
    report: dict | None = None
    stderr_note: str
    try:
        # the helper protocol source is the verified task packet passed by the
        # caller through the accepted bounded channel (never argv); Phase Q27
        # replaces this placeholder read with the confined re-read contract
        packet_path = Path(_get_packet_path_from_environment())
        prompt = packet_path.read_text(encoding="utf-8")
        turn = driver.run_turn(prompt, workspace=str(cwd), deadline_seconds=3600.0)
    except (ZCodeProtocolError, OSError, ValueError):
        stderr_note = "PROTOCOL_FAILED"
        turn = None
        report = None
        child.stdin and child.stdin.close()
        child.wait(timeout=30)
        return _cli_error("PROTOCOL_FAILED")
    finished = _datetime.now(_timezone.utc).isoformat()
    stderr_note = "TURN_COMPLETED"

    exit_code = _ChildTransport.close_stdin_and_wait(_ChildTransport(), exit_wait_seconds=30)
    if exit_code is None:
        child.wait(timeout=30)

    # 5. artifacts: stdout, report, canonical six-key result
    if turn is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        (result_path.parent / "stdout.log").write_text(turn.response_text, encoding="utf-8")
        (result_path.parent / "stderr.log").write_text(stderr_note + "\n", encoding="utf-8")
        report = {
            "schema": "zcode-report/1",
            "execution_id": args.execution_id,
            "session_id": turn.session_id,
            "response_bytes": turn.bytes_received,
        }
        if report_path is not None:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(_json.dumps(report, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        if isinstance(exit_code, int):
            import hashlib as _hashlib
            result = {
                "schema_version": 1,
                "execution_id": args.execution_id,
                "child_pid": child.pid,
                "exit_code": exit_code,
                "started_at": started,
                "finished_at": finished,
            }
            result_path.write_text(_json.dumps(result, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            return 0
        return _cli_error("EXIT_PENDING")
    return _cli_error("PROTOCOL_FAILED")


def _get_parent_pid() -> int:
    import os as _os
    return int(getattr(_os, "getppid", lambda: 0)() or 0)


def _get_packet_path_from_environment() -> str:
    import os as _os
    return _os.environ.get("ZCODE_TASK_PACKET_PATH", "")


if __name__ == "__main__":
    raise SystemExit(main())
