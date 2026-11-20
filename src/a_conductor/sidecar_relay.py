"""WO-P1-570 / Issue #570 — Phase 1 A-Relay carrier (dumb carrier).

Stdlib-only durable carrier for the Phase 0 contract
``docs/contracts/a-sidecar-relay-v1.md``. It stores and projects typed
receipt/evidence events as append-only strict UTF-8 LF JSONL and
nothing else: no scheduler, task store, claim/lease system, retry
owner, review path, merge or completion authority. An A-Relay event is
a receipt, never a command; replaying the log can only re-derive
observations. Canonical task/claim/Git/execution truth stays with the
existing A-Conductor authorities.

Event families (closed allowlist, exactly the 11 Phase 0 families):

    SIDECAR_HELP_REQUEST, SIDECAR_CHECKPOINT, SIDECAR_RESULT_RECEIPT,
    CODEX_STEER_REQUEST, GLM_DISPATCH_REQUEST, GLM_RESULT_RECEIPT,
    JEV_ADVISORY_REQUEST, JEV_ADVISORY_RECEIPT, GPT_WORK_LIMITED,
    CONTEXT_PRESSURE_HIGH, HUMAN_GATE_REQUIRED

Binding model (deterministic projection of contract §4):

- every family requires EVENT_ID, EVENT_TYPE, SOURCE_SURFACE,
  SOURCE_THREAD_ID, SOURCE_TURN_ID, CREATED_AT;
- PRIORITY is optional and defaults to HIGH for
  HUMAN_GATE_REQUIRED / CONTEXT_PRESSURE_HIGH and NORMAL otherwise;
- the two observability families (GPT_WORK_LIMITED,
  CONTEXT_PRESSURE_HIGH) never require task/claim/repo/worktree/head
  binding;
- every other family is mutation-relevant and requires the exact
  binding tuple TASK_ID + CLAIM_ID + REPO + WORKTREE + HEAD_SHA;
  ``when applicable`` binding fields are omitted (never blank-filled)
  when they do not bind;
- SIDECAR_RESULT_RECEIPT and GLM_RESULT_RECEIPT additionally require
  at least one durable EVIDENCE_REFS pointer (pointer presence only —
  pointers are never dereferenced and never become authority).

Envelope safety: closed key set, no control/format/surrogate/private
characters in any text value, no PEM blocks or credential-token
markers, no URL-form evidence refs (share URLs are forbidden by the
contract; refs are repo-relative paths, issue/comment refs, or run
pointers). Failures are code-only and never echo field values.

Log semantics:

- append-only: existing lines are never rewritten or deleted;
- one envelope per LF-terminated line, strict UTF-8, compact JSON,
  sorted keys (byte-deterministic encoding);
- max encoded line size is 65536 bytes including the trailing LF;
- a torn final line (present but not LF-terminated) is skipped
  deterministically on read and flagged; appending after a torn tail
  fails typed RELAY_IO_ERROR without touching the file so the torn
  fragment can never concatenate onto a new event;
- a malformed complete line anywhere is corruption and fails closed
  with RELAY_ENVELOPE_INVALID (only the torn-tail shape is tolerated);
- delivery is at-least-once: readers deduplicate on EVENT_ID (first
  occurrence wins); appending a byte-identical envelope is an
  idempotent no-op while a conflicting re-use of an EVENT_ID fails
  with RELAY_EVENT_DUPLICATE;
- ordering is per-producer:
  (SOURCE_SURFACE, SOURCE_THREAD_ID, CREATED_AT, EVENT_ID);
- cross-platform WORKTREE/path values are opaque producer-observed
  evidence: they are validated as bounded safe text only, never
  resolved, normalized, or compared against the local device.

Typed failures: RELAY_ENVELOPE_INVALID, RELAY_EVIDENCE_MISSING,
RELAY_EVENT_TOO_LARGE, RELAY_EVENT_DUPLICATE, RELAY_IO_ERROR.

CLI (module-local, ``python -m a_conductor.sidecar_relay``):

    validate <log.jsonl>
    emit <log.jsonl> <envelope-json>
    tail <log.jsonl> [count]

Exit codes: 0 ok, 64 usage, 2 RELAY_ENVELOPE_INVALID,
3 RELAY_EVIDENCE_MISSING, 4 RELAY_EVENT_TOO_LARGE,
5 RELAY_EVENT_DUPLICATE, 6 RELAY_IO_ERROR.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

EVENT_FAMILIES = frozenset(
    {
        "SIDECAR_HELP_REQUEST",
        "SIDECAR_CHECKPOINT",
        "SIDECAR_RESULT_RECEIPT",
        "CODEX_STEER_REQUEST",
        "GLM_DISPATCH_REQUEST",
        "GLM_RESULT_RECEIPT",
        "JEV_ADVISORY_REQUEST",
        "JEV_ADVISORY_RECEIPT",
        "GPT_WORK_LIMITED",
        "CONTEXT_PRESSURE_HIGH",
        "HUMAN_GATE_REQUIRED",
    }
)
SOURCE_SURFACES = frozenset(
    {"chatgpt-sidecar", "codex", "glm", "jev", "gpt", "human"}
)
PRIORITIES = frozenset({"LOW", "NORMAL", "HIGH"})
DEFAULT_HIGH_PRIORITY_FAMILIES = frozenset(
    {"HUMAN_GATE_REQUIRED", "CONTEXT_PRESSURE_HIGH"}
)
MUTATION_RELEVANT_FAMILIES = frozenset(
    EVENT_FAMILIES - {"GPT_WORK_LIMITED", "CONTEXT_PRESSURE_HIGH"}
)
RESULT_RECEIPT_FAMILIES = frozenset(
    {"SIDECAR_RESULT_RECEIPT", "GLM_RESULT_RECEIPT"}
)
BINDING_KEYS = ("TASK_ID", "CLAIM_ID", "REPO", "WORKTREE", "HEAD_SHA")
_ENVELOPE_KEYS = frozenset(
    {
        "EVENT_ID",
        "EVENT_TYPE",
        "SOURCE_SURFACE",
        "SOURCE_THREAD_ID",
        "SOURCE_TURN_ID",
        "TASK_ID",
        "CLAIM_ID",
        "REPO",
        "WORKTREE",
        "HEAD_SHA",
        "REQUESTED_CAPABILITY",
        "PRIORITY",
        "EVIDENCE_REFS",
        "CREATED_AT",
        "DEVICE_CONTEXT",
    }
)

MAX_EVENT_BYTES = 65536
MAX_EVIDENCE_REFS = 16

_SAFE_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
_REPO_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._-]{0,100}/[A-Za-z0-9][A-Za-z0-9._-]{0,100}"
)
_HEAD_SHA_RE = re.compile(r"[0-9a-f]{40}")
_CAPABILITY_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
_EVENT_ID_PREFIX = "evt-"
_MAX_EVENT_ID_LEN = 4 + max(len(surface) for surface in SOURCE_SURFACES) + 1 + 128
_MAX_TASK_OR_CLAIM_LEN = 128
_MAX_THREAD_OR_TURN_LEN = 256
_MAX_WORKTREE_LEN = 1024
_MAX_DEVICE_CONTEXT_LEN = 256
_MAX_EVIDENCE_REF_LEN = 4096
_MAX_CREATED_AT_LEN = 64
_SURFACES_BY_LENGTH = sorted(SOURCE_SURFACES, key=len, reverse=True)

_UNSAFE_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Co"})
_PEM_MARKER = "-----begin"
_SECRET_TOKEN_RES = (
    re.compile(r"ghp_[A-Za-z0-9]{16,}"),
    re.compile(r"gho_[A-Za-z0-9]{16,}"),
    re.compile(r"ghu_[A-Za-z0-9]{16,}"),
    re.compile(r"ghs_[A-Za-z0-9]{16,}"),
    re.compile(r"ghr_[A-Za-z0-9]{16,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{16,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"xox[abprs]-[A-Za-z0-9-]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
)

CLI_EXIT_OK = 0
CLI_EXIT_USAGE = 64
_EXIT_BY_CODE = {
    "RELAY_ENVELOPE_INVALID": 2,
    "RELAY_EVIDENCE_MISSING": 3,
    "RELAY_EVENT_TOO_LARGE": 4,
    "RELAY_EVENT_DUPLICATE": 5,
    "RELAY_IO_ERROR": 6,
}
_USAGE = (
    "usage: python -m a_conductor.sidecar_relay "
    "validate <log.jsonl> | emit <log.jsonl> <envelope-json> | "
    "tail <log.jsonl> [count]"
)


class RelayCarrierError(RuntimeError):
    """Stable code-only carrier failure; never echoes field values."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _check_safe_text(value: str) -> None:
    for character in value:
        if unicodedata.category(character) in _UNSAFE_CATEGORIES:
            raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
    if _PEM_MARKER in value.lower():
        raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
    for pattern in _SECRET_TOKEN_RES:
        if pattern.search(value) is not None:
            raise RelayCarrierError("RELAY_ENVELOPE_INVALID")


def _require_text(value: object, max_len: int) -> str:
    if not isinstance(value, str):
        raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
    if not value or len(value) > max_len or value != value.strip():
        raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
    _check_safe_text(value)
    return value


def _require_token(value: object, max_len: int) -> str:
    text = _require_text(value, max_len)
    if _SAFE_TOKEN_RE.fullmatch(text) is None or text in (".", ".."):
        raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
    return text


def mint_event_id(source_surface: str) -> str:
    """Mint a collision-resistant ``evt-<surface>-<id>`` producer id."""
    if source_surface not in SOURCE_SURFACES:
        raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
    return f"{_EVENT_ID_PREFIX}{source_surface}-{uuid.uuid4().hex}"


def _validate_event_id(value: object, source_surface: str) -> str:
    event_id = _require_text(value, _MAX_EVENT_ID_LEN)
    if not event_id.startswith(_EVENT_ID_PREFIX):
        raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
    rest = event_id[len(_EVENT_ID_PREFIX) :]
    tail: str | None = None
    for surface in _SURFACES_BY_LENGTH:
        prefix = f"{surface}-"
        if rest.startswith(prefix):
            tail = rest[len(prefix) :]
            if surface != source_surface:
                raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
            break
    if tail is None or _SAFE_TOKEN_RE.fullmatch(tail) is None or len(tail) > 128:
        raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
    return event_id


def _validate_created_at(value: object) -> str:
    created_at = _require_text(value, _MAX_CREATED_AT_LEN)
    if " " in created_at:
        raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
    try:
        parsed = datetime.fromisoformat(created_at)
    except ValueError:
        raise RelayCarrierError("RELAY_ENVELOPE_INVALID") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
    return created_at


@dataclass(frozen=True, slots=True)
class RelayEnvelope:
    """One immutable A-Relay event (receipt/evidence only, never a command)."""

    event_id: str
    event_type: str
    source_surface: str
    source_thread_id: str
    source_turn_id: str
    priority: str
    evidence_refs: tuple[str, ...]
    created_at: str
    task_id: str | None = None
    claim_id: str | None = None
    repo: str | None = None
    worktree: str | None = None
    head_sha: str | None = None
    requested_capability: str | None = None
    device_context: str | None = None

    def to_mapping(self) -> dict:
        mapping: dict = {
            "EVENT_ID": self.event_id,
            "EVENT_TYPE": self.event_type,
            "SOURCE_SURFACE": self.source_surface,
            "SOURCE_THREAD_ID": self.source_thread_id,
            "SOURCE_TURN_ID": self.source_turn_id,
            "PRIORITY": self.priority,
            "EVIDENCE_REFS": list(self.evidence_refs),
            "CREATED_AT": self.created_at,
        }
        for key, value in (
            ("TASK_ID", self.task_id),
            ("CLAIM_ID", self.claim_id),
            ("REPO", self.repo),
            ("WORKTREE", self.worktree),
            ("HEAD_SHA", self.head_sha),
            ("REQUESTED_CAPABILITY", self.requested_capability),
            ("DEVICE_CONTEXT", self.device_context),
        ):
            if value is not None:
                mapping[key] = value
        return mapping

    def to_json(self) -> str:
        return json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )


def _validate_evidence_refs(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
    if len(value) > MAX_EVIDENCE_REFS:
        raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
    refs: list[str] = []
    for item in value:
        ref = _require_text(item, _MAX_EVIDENCE_REF_LEN)
        if "://" in ref:
            raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
        refs.append(ref)
    if len(set(refs)) != len(refs):
        raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
    return tuple(refs)


def envelope_from_mapping(payload: object) -> RelayEnvelope:
    """Strictly validate and build one relay envelope.

    Raises :class:`RelayCarrierError` with RELAY_ENVELOPE_INVALID for
    any shape, allowlist, grammar, or binding violation and
    RELAY_EVIDENCE_MISSING when a result-receipt family carries no
    durable evidence pointer. Never echoes field values.
    """
    if not isinstance(payload, dict):
        raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
    unknown_keys = set(payload) - _ENVELOPE_KEYS
    if unknown_keys:
        raise RelayCarrierError("RELAY_ENVELOPE_INVALID")

    event_type = payload.get("EVENT_TYPE")
    if not isinstance(event_type, str) or event_type not in EVENT_FAMILIES:
        raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
    source_surface = payload.get("SOURCE_SURFACE")
    if (
        not isinstance(source_surface, str)
        or source_surface not in SOURCE_SURFACES
    ):
        raise RelayCarrierError("RELAY_ENVELOPE_INVALID")

    event_id = _validate_event_id(payload.get("EVENT_ID"), source_surface)
    source_thread_id = _require_text(
        payload.get("SOURCE_THREAD_ID"), _MAX_THREAD_OR_TURN_LEN
    )
    source_turn_id = _require_text(
        payload.get("SOURCE_TURN_ID"), _MAX_THREAD_OR_TURN_LEN
    )
    created_at = _validate_created_at(payload.get("CREATED_AT"))

    priority_value = payload.get("PRIORITY")
    if priority_value is None:
        priority = (
            "HIGH"
            if event_type in DEFAULT_HIGH_PRIORITY_FAMILIES
            else "NORMAL"
        )
    elif isinstance(priority_value, str) and priority_value in PRIORITIES:
        priority = priority_value
    else:
        raise RelayCarrierError("RELAY_ENVELOPE_INVALID")

    task_id = claim_id = repo = worktree = head_sha = None
    if event_type in MUTATION_RELEVANT_FAMILIES:
        for key in BINDING_KEYS:
            if payload.get(key) is None:
                raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
    if payload.get("TASK_ID") is not None:
        task_id = _require_token(payload.get("TASK_ID"), _MAX_TASK_OR_CLAIM_LEN)
    if payload.get("CLAIM_ID") is not None:
        claim_id = _require_token(
            payload.get("CLAIM_ID"), _MAX_TASK_OR_CLAIM_LEN
        )
    if payload.get("REPO") is not None:
        repo = _require_text(payload.get("REPO"), 256)
        if _REPO_RE.fullmatch(repo) is None:
            raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
    if payload.get("WORKTREE") is not None:
        worktree = _require_text(payload.get("WORKTREE"), _MAX_WORKTREE_LEN)
    if payload.get("HEAD_SHA") is not None:
        head_sha = _require_text(payload.get("HEAD_SHA"), 40)
        if _HEAD_SHA_RE.fullmatch(head_sha) is None:
            raise RelayCarrierError("RELAY_ENVELOPE_INVALID")

    requested_capability = None
    if payload.get("REQUESTED_CAPABILITY") is not None:
        requested_capability = _require_text(
            payload.get("REQUESTED_CAPABILITY"), 64
        )
        if _CAPABILITY_RE.fullmatch(requested_capability) is None:
            raise RelayCarrierError("RELAY_ENVELOPE_INVALID")

    device_context = None
    if payload.get("DEVICE_CONTEXT") is not None:
        device_context = _require_text(
            payload.get("DEVICE_CONTEXT"), _MAX_DEVICE_CONTEXT_LEN
        )

    evidence_refs = _validate_evidence_refs(payload.get("EVIDENCE_REFS"))
    if event_type in RESULT_RECEIPT_FAMILIES and not evidence_refs:
        raise RelayCarrierError("RELAY_EVIDENCE_MISSING")

    return RelayEnvelope(
        event_id=event_id,
        event_type=event_type,
        source_surface=source_surface,
        source_thread_id=source_thread_id,
        source_turn_id=source_turn_id,
        priority=priority,
        evidence_refs=evidence_refs,
        created_at=created_at,
        task_id=task_id,
        claim_id=claim_id,
        repo=repo,
        worktree=worktree,
        head_sha=head_sha,
        requested_capability=requested_capability,
        device_context=device_context,
    )


def envelope_from_json_line(line: object) -> RelayEnvelope:
    """Validate one JSON-text envelope line into a relay envelope."""
    if not isinstance(line, str):
        raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
    try:
        payload = json.loads(line)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise RelayCarrierError("RELAY_ENVELOPE_INVALID") from None
    return envelope_from_mapping(payload)


@dataclass(frozen=True, slots=True)
class RelayLogRead:
    """Read projection of one relay log (deduplicated, file order)."""

    events: tuple[RelayEnvelope, ...]
    torn_tail_skipped: bool


def read_events(log_path: object) -> RelayLogRead:
    """Read, validate, and deduplicate one relay JSONL log.

    Duplicates on EVENT_ID collapse to the first occurrence. A torn
    final line (not LF-terminated) is skipped deterministically and
    flagged; a malformed complete line fails closed as corruption.
    """
    path = Path(log_path)
    try:
        raw = path.read_bytes()
    except OSError:
        raise RelayCarrierError("RELAY_IO_ERROR") from None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise RelayCarrierError("RELAY_IO_ERROR") from None

    torn_tail_skipped = False
    if text and not text.endswith("\n"):
        torn_tail_skipped = True
        cut = text.rfind("\n")
        text = "" if cut < 0 else text[: cut + 1]

    events: list[RelayEnvelope] = []
    seen: set[str] = set()
    for line in text.split("\n")[:-1]:
        if "\r" in line:
            raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
        envelope = envelope_from_json_line(line)
        if envelope.event_id not in seen:
            seen.add(envelope.event_id)
            events.append(envelope)
    return RelayLogRead(events=tuple(events), torn_tail_skipped=torn_tail_skipped)


def order_events(
    events: Iterable[RelayEnvelope],
) -> tuple[RelayEnvelope, ...]:
    """Deterministic per-producer order of relay envelopes.

    Sort key: (SOURCE_SURFACE, SOURCE_THREAD_ID, CREATED_AT, EVENT_ID)
    per contract §5; out-of-order arrival is tolerated.
    """
    return tuple(
        sorted(
            events,
            key=lambda envelope: (
                envelope.source_surface,
                envelope.source_thread_id,
                datetime.fromisoformat(envelope.created_at),
                envelope.event_id,
            ),
        )
    )


def append_event(log_path: object, envelope: RelayEnvelope) -> None:
    """Append one validated envelope to an append-only JSONL log.

    Existing lines are never rewritten or deleted. A byte-identical
    re-delivery of an already-stored EVENT_ID is an idempotent no-op;
    a conflicting re-use of an EVENT_ID fails with
    RELAY_EVENT_DUPLICATE. Appending after a torn final line fails
    typed so a torn fragment can never concatenate onto a new event.
    """
    checked = envelope_from_mapping(envelope.to_mapping())
    payload = checked.to_json()
    data = payload.encode("utf-8")
    if len(data) + 1 > MAX_EVENT_BYTES:
        raise RelayCarrierError("RELAY_EVENT_TOO_LARGE")

    path = Path(log_path)
    try:
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_bytes() if path.exists() else b""
    except OSError:
        raise RelayCarrierError("RELAY_IO_ERROR") from None

    if existing:
        if not existing.endswith(b"\n"):
            raise RelayCarrierError("RELAY_IO_ERROR")
        for raw_line in existing.split(b"\n")[:-1]:
            if b"\r" in raw_line:
                raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
            try:
                line_text = raw_line.decode("utf-8")
                line_payload = json.loads(line_text)
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise RelayCarrierError("RELAY_ENVELOPE_INVALID") from None
            if not isinstance(line_payload, dict):
                raise RelayCarrierError("RELAY_ENVELOPE_INVALID")
            if line_text == payload:
                return
            if line_payload.get("EVENT_ID") == checked.event_id:
                raise RelayCarrierError("RELAY_EVENT_DUPLICATE")

    try:
        with path.open("ab") as handle:
            handle.write(data + b"\n")
    except OSError:
        raise RelayCarrierError("RELAY_IO_ERROR") from None


def _cli_validate(log_path: str) -> int:
    result = read_events(log_path)
    torn = " torn_tail=1" if result.torn_tail_skipped else ""
    print(f"OK events={len(result.events)}{torn}")
    return CLI_EXIT_OK


def _cli_emit(log_path: str, envelope_json: str) -> int:
    envelope = envelope_from_json_line(envelope_json)
    append_event(log_path, envelope)
    print(envelope.event_id)
    return CLI_EXIT_OK


def _cli_tail(log_path: str, count_text: str) -> int:
    try:
        count = int(count_text)
    except ValueError:
        print(_USAGE, file=sys.stderr)
        return CLI_EXIT_USAGE
    if count < 1 or count > 1000:
        print(_USAGE, file=sys.stderr)
        return CLI_EXIT_USAGE
    result = read_events(log_path)
    for envelope in result.events[-count:]:
        print(envelope.to_json())
    return CLI_EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """Module-local CLI entry (validate / emit / tail) with typed exits."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        command, rest = args[0], args[1:]
        try:
            if command == "validate" and len(rest) == 1:
                return _cli_validate(rest[0])
            if command == "emit" and len(rest) == 2:
                return _cli_emit(rest[0], rest[1])
            if command == "tail" and len(rest) in (1, 2):
                return _cli_tail(rest[0], rest[1] if len(rest) == 2 else "10")
        except RelayCarrierError as error:
            print(error.code, file=sys.stderr)
            return _EXIT_BY_CODE.get(error.code, 2)
    print(_USAGE, file=sys.stderr)
    return CLI_EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
