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

from .zcode_protocol import ZCODE_MAX_RESPONSE_BYTES

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
