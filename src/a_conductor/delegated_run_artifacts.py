"""WO-P1-480 (MSP-0 of WO-P1-475 / Issue #480) — collision-proof
delegated-run artifact identity.

Pure, deterministic, filesystem-light helper that binds the accepted
A-Faster delegated-run identity grammar to physical attempt-directory
names under ``runs/<WO>/<lane>/``:

- ``DELEGATED_RUN_ID`` grammar (``references/durable-lanes.md``):
  ``run:<TASK_ID>:<role>:<ordinal>:a<attempt>:<random-id>`` where
  ``<random-id>`` is either the historical 8-lowercase-hex form or
  the current 12-lowercase-hex form observed in durable dispatch evidence.
  Parsed from the right so the load-bearing uniqueness
  component (the random id) is anchored first.
- New physical attempt directory name (frozen by this work order):
  ``attempt-<NNNN>-<random-id>`` where ``NNNN`` is the run's attempt
  number zero-padded to 4 digits (human-readable, NOT uniqueness
  authority) and ``<random-id>`` is exactly the run id's random
  suffix. The existing random run suffix is reused as the physical
  uniqueness component — no second durable identity namespace.
- Legacy ``attempt-NNNN`` directories remain readable/recoverable via
  their ``pointer.md`` ``delegated_run_id`` field and are never
  rewritten in place (this module performs no writes at all).
- Enumeration over mixed legacy/new directories is deterministic
  (sorted by attempt, legacy first, then suffix).
- Recovery maps each suffixed canonical directory back to exactly one
  immutable delegated run identity by requiring name/pointer suffix
  and ordinal agreement; any mismatch fails closed.
- Other non-canonical lowercase-hex suffix shapes are enumerated for
  census visibility but bind to runs via
  pointer only, still requiring ordinal agreement.
- Recovery-only legacy compatibility (P1 repair): structurally
  non-canonical pointer values with the two proven pre-grammar alias
  shapes — missing ordinal segment, or a non-decimal token in the
  ordinal position — are accepted ONLY when recovering an existing
  attempt directory from pointer.md / execution-pointer.json
  evidence. The entire original string is preserved as the immutable
  recovery identity; only the trailing ``a<attempt>`` and 8/12-hex
  random suffix are extracted for physical directory agreement.
  Legacy aliases never gain minting or physical path generation
  authority (``attempt_dir_name()`` stays strictly canonical), never
  get rewritten, and never become canonical.

``DELEGATED_RUN_ID`` remains observation/recovery identity only. This
module grants no task, claim, lease, retry, review, merge, or
acceptance authority and adds no database, registry, session lock,
scheduler, task store, or browser authority.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

_RUN_PREFIX = "run:"
_RANDOM_ID_RE = re.compile(r"(?:[0-9a-f]{8}|[0-9a-f]{12})")
_TASK_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
_ROLE_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
_DIGITS_RE = re.compile(r"[0-9]+")
_ATTEMPT_SEGMENT_RE = re.compile(r"a[0-9]+")
_LEGACY_NAME_RE = re.compile(r"attempt-([0-9]+)")
_SUFFIXED_NAME_RE = re.compile(r"attempt-([0-9]+)-([0-9a-f]{8,64})")
_POINTER_RUN_ID_LINE_RE = re.compile(
    r"[ \t]{0,3}(?:[-*][ \t]+)?[`*]{0,2}delegated_run_id[`*]{0,2}"
    r"[ \t]*:[ \t]*([^ \t\r\n]+)[ \t]*$"
)
POINTER_FILENAME = "pointer.md"
EXECUTION_POINTER_FILENAME = "execution-pointer.json"
_MAX_RUN_ID_LEN = 512
_MAX_TASK_ID_LEN = 128
_MAX_ROLE_LEN = 64
_MAX_COUNTER = 999999


class DelegatedRunArtifactError(RuntimeError):
    """Stable code-only artifact-identity failure; never echoes input text."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class DelegatedRunIdentity:
    """One parsed delegated run identity (observation/recovery only)."""

    task_id: str
    role: str
    ordinal: int
    attempt: int
    random_id: str

    @property
    def run_id(self) -> str:
        return (
            f"{_RUN_PREFIX}{self.task_id}:{self.role}:"
            f"{self.ordinal}:a{self.attempt}:{self.random_id}"
        )

    @property
    def suffix(self) -> str:
        return self.random_id


def _counter(text: str, segment: str) -> int:
    if not _DIGITS_RE.fullmatch(text):
        raise DelegatedRunArtifactError("RUN_ID_INVALID")
    if len(text) > 1 and text.startswith("0"):
        raise DelegatedRunArtifactError("RUN_ID_INVALID")
    value = int(text)
    if value < 1 or value > _MAX_COUNTER:
        raise DelegatedRunArtifactError("RUN_ID_INVALID")
    return value


def parse_delegated_run_id(run_id: object) -> DelegatedRunIdentity:
    """Parse a DELEGATED_RUN_ID from the right; anything else fails closed.

    The grammar is exactly ``run:<TASK_ID>:<role>:<ordinal>:a<attempt>:<random-id>``.
    Task ids may not contain ``:``; the four rightmost segments are
    anchored first so the random-id uniqueness component can never be
    spoofed by left-side content. Separators, traversal tokens,
    whitespace damage, non-hex or wrong-length random ids, leading-zero
    counters, and zero counters are all rejected.
    """
    if not isinstance(run_id, str):
        raise DelegatedRunArtifactError("RUN_ID_INVALID")
    if not run_id or len(run_id) > _MAX_RUN_ID_LEN:
        raise DelegatedRunArtifactError("RUN_ID_INVALID")
    if run_id != run_id.strip() or not run_id.startswith(_RUN_PREFIX):
        raise DelegatedRunArtifactError("RUN_ID_INVALID")
    if "\x00" in run_id or "\r" in run_id or "\n" in run_id:
        raise DelegatedRunArtifactError("RUN_ID_INVALID")
    parts = run_id[len(_RUN_PREFIX) :].rsplit(":", 4)
    if len(parts) != 5 or not all(parts):
        raise DelegatedRunArtifactError("RUN_ID_INVALID")
    task_id, role, ordinal_text, attempt_segment, random_id = parts
    if (
        not _TASK_ID_RE.fullmatch(task_id)
        or len(task_id) > _MAX_TASK_ID_LEN
        or task_id in (".", "..")
    ):
        raise DelegatedRunArtifactError("RUN_ID_INVALID")
    if not _ROLE_RE.fullmatch(role) or len(role) > _MAX_ROLE_LEN:
        raise DelegatedRunArtifactError("RUN_ID_INVALID")
    if not _ATTEMPT_SEGMENT_RE.fullmatch(attempt_segment):
        raise DelegatedRunArtifactError("RUN_ID_INVALID")
    if not _RANDOM_ID_RE.fullmatch(random_id):
        raise DelegatedRunArtifactError("RUN_ID_INVALID")
    ordinal = _counter(ordinal_text, "ordinal")
    attempt = _counter(attempt_segment[1:], "attempt")
    return DelegatedRunIdentity(
        task_id=task_id,
        role=role,
        ordinal=ordinal,
        attempt=attempt,
        random_id=random_id,
    )


@dataclass(frozen=True, slots=True)
class LegacyPointerRunIdentity:
    """Recovery-only identity for one proven pre-grammar pointer alias.

    Carries the entire original ``delegated_run_id`` string verbatim
    as the immutable observation/recovery identity, plus only the
    trailing ``a<attempt>`` and 8/12-hex random suffix extracted to
    prove physical directory agreement. No task/role/ordinal binding
    is inferred for the alias, the pointer is never rewritten, and
    this type is never accepted by :func:`parse_delegated_run_id` or
    :func:`attempt_dir_name` (minting and physical path generation
    stay strictly canonical).
    """

    run_id: str
    attempt: int
    random_id: str

    @property
    def suffix(self) -> str:
        return self.random_id


#: Identity recovered from pointer evidence: canonical run identity,
#: or a recovery-only legacy alias identity (P1 repair seam).
RecoveredRunIdentity = DelegatedRunIdentity | LegacyPointerRunIdentity


def _parse_legacy_pointer_run_id(run_id: str) -> LegacyPointerRunIdentity:
    """Recovery-only compatibility seam for proven legacy aliases.

    Accepts exactly the two pre-grammar alias shapes observed in real
    durable pointer evidence (WO-P1-480 P1 repair), and nothing else:

    - ``run:<TASK_ID>:<role>:a<attempt>:<random-id>`` — ordinal
      segment absent (e.g. ``run:WO-P1-478:r3-review:a1:2933deb345c2``);
    - ``run:<TASK_ID>:<role>:<middle>:a<attempt>:<random-id>`` — a
      stable safe non-decimal token sits in the ordinal position
      (e.g. ``run:WO-P1-475:flash-architecture:acfa39d:a1:16b32a2f6ea9``).

    Reached only after the canonical parser rejected the exact same
    string, only from :func:`read_pointer_run_id` (pointer-evidence
    recovery of an existing attempt directory). The whole original
    string is preserved verbatim; only the trailing ``a<attempt>``
    and 8/12-hex random suffix are extracted. Missing attempt or
    suffix segments are never inferred; unobserved shapes, decimal
    tokens in the ordinal position, blank/control/separator/traversal
    payloads, and oversized segments all fail closed with the same
    stable code-only ``RUN_ID_INVALID`` error as the canonical parser
    (no input echo).
    """
    if not run_id or len(run_id) > _MAX_RUN_ID_LEN:
        raise DelegatedRunArtifactError("RUN_ID_INVALID")
    if run_id != run_id.strip() or not run_id.startswith(_RUN_PREFIX):
        raise DelegatedRunArtifactError("RUN_ID_INVALID")
    if "\x00" in run_id or "\r" in run_id or "\n" in run_id:
        raise DelegatedRunArtifactError("RUN_ID_INVALID")
    parts = run_id[len(_RUN_PREFIX) :].split(":")
    if len(parts) == 4:
        task_id, role, attempt_segment, random_id = parts
    elif len(parts) == 5:
        task_id, role, middle, attempt_segment, random_id = parts
        if (
            not _ROLE_RE.fullmatch(middle)
            or len(middle) > _MAX_ROLE_LEN
            or _DIGITS_RE.fullmatch(middle) is not None
        ):
            raise DelegatedRunArtifactError("RUN_ID_INVALID")
    else:
        raise DelegatedRunArtifactError("RUN_ID_INVALID")
    if (
        not _TASK_ID_RE.fullmatch(task_id)
        or len(task_id) > _MAX_TASK_ID_LEN
        or task_id in (".", "..")
    ):
        raise DelegatedRunArtifactError("RUN_ID_INVALID")
    if not _ROLE_RE.fullmatch(role) or len(role) > _MAX_ROLE_LEN:
        raise DelegatedRunArtifactError("RUN_ID_INVALID")
    if not _ATTEMPT_SEGMENT_RE.fullmatch(attempt_segment):
        raise DelegatedRunArtifactError("RUN_ID_INVALID")
    if not _RANDOM_ID_RE.fullmatch(random_id):
        raise DelegatedRunArtifactError("RUN_ID_INVALID")
    attempt = _counter(attempt_segment[1:], "attempt")
    return LegacyPointerRunIdentity(
        run_id=run_id, attempt=attempt, random_id=random_id
    )


def attempt_dir_name(run_id: object) -> str:
    """Deterministic physical name for one delegated run attempt.

    One delegated run maps to exactly one immutable directory name:
    ``attempt-<NNNN>-<random-id>`` with ``NNNN`` zero-padded to 4 digits
    (extending naturally beyond 9999). The ordinal is human-readable
    bookkeeping only; uniqueness authority is the run's random id.
    """
    identity = parse_delegated_run_id(run_id)
    return f"attempt-{identity.attempt:04d}-{identity.random_id}"


def attempt_dir_path(lane_dir: object, run_id: object) -> Path:
    """Deterministic physical attempt path inside one lane directory."""
    return Path(lane_dir) / attempt_dir_name(run_id)


@dataclass(frozen=True, slots=True)
class AttemptDirName:
    """One recognized attempt-directory name (legacy or suffixed)."""

    attempt: int
    suffix: str | None
    canonical: bool

    @property
    def form(self) -> str:
        return "legacy" if self.suffix is None else "suffixed"

    @property
    def dir_name(self) -> str:
        if self.suffix is None:
            return f"attempt-{self.attempt:04d}"
        return f"attempt-{self.attempt:04d}-{self.suffix}"


def _canonical_ordinal(digits: str) -> int | None:
    if len(digits) > 6:
        return None
    value = int(digits)
    if value < 1 or value > _MAX_COUNTER or f"{value:04d}" != digits:
        return None
    return value


def parse_attempt_dir_name(name: object) -> AttemptDirName:
    """Recognize legacy ``attempt-NNNN`` and suffixed attempt names.

    The ordinal must be the canonical zero-padded-to-4 form (so
    ``attempt-12`` and ``attempt-00012`` can never alias ordinal 12).
    A suffixed name carries a lowercase-hex suffix of 8..64 chars;
    exactly 8-hex (historical) or 12-hex (current durable dispatch form)
    suffixes are ``canonical`` and eligible for name/run binding. Anything else is
    rejected fail-closed.
    """
    if not isinstance(name, str):
        raise DelegatedRunArtifactError("ATTEMPT_DIR_NAME_INVALID")
    suffixed = _SUFFIXED_NAME_RE.fullmatch(name)
    if suffixed is not None:
        attempt = _canonical_ordinal(suffixed.group(1))
        if attempt is None:
            raise DelegatedRunArtifactError("ATTEMPT_DIR_NAME_INVALID")
        suffix = suffixed.group(2)
        return AttemptDirName(
            attempt=attempt, suffix=suffix, canonical=len(suffix) in (8, 12)
        )
    legacy = _LEGACY_NAME_RE.fullmatch(name)
    if legacy is not None:
        attempt = _canonical_ordinal(legacy.group(1))
        if attempt is None:
            raise DelegatedRunArtifactError("ATTEMPT_DIR_NAME_INVALID")
        return AttemptDirName(attempt=attempt, suffix=None, canonical=False)
    raise DelegatedRunArtifactError("ATTEMPT_DIR_NAME_INVALID")


@dataclass(frozen=True, slots=True)
class AttemptDirRecord:
    """One enumerated attempt directory inside a lane."""

    path: Path
    dir_name: str
    attempt: int
    form: str
    suffix: str | None
    canonical: bool


def enumerate_attempt_dirs(lane_dir: object) -> tuple[AttemptDirRecord, ...]:
    """Deterministically enumerate mixed legacy/new attempt directories.

    Non-attempt entries (files, unrelated directories, malformed names)
    are ignored, never guessed into identity. Ordering is fixed:
    ascending attempt ordinal, legacy before suffixed at the same
    ordinal, then ascending suffix. A missing or unreadable lane
    directory yields an empty census rather than authority claims.
    """
    try:
        entries = sorted(Path(lane_dir).iterdir(), key=lambda p: p.name)
    except OSError:
        return ()
    records: list[AttemptDirRecord] = []
    for entry in entries:
        try:
            if not entry.is_dir():
                continue
            parsed = parse_attempt_dir_name(entry.name)
        except (OSError, DelegatedRunArtifactError):
            continue
        records.append(
            AttemptDirRecord(
                path=entry,
                dir_name=parsed.dir_name,
                attempt=parsed.attempt,
                form=parsed.form,
                suffix=parsed.suffix,
                canonical=parsed.canonical,
            )
        )
    records.sort(
        key=lambda r: (r.attempt, 0 if r.form == "legacy" else 1, r.suffix or "")
    )
    return tuple(records)


def read_pointer_run_id(attempt_dir: object) -> RecoveredRunIdentity:
    """Recover one delegated run id from accepted pointer evidence.

    Historical/canonical A-Faster evidence uses ``pointer.md``; current
    hardened delegated runners also persist ``execution-pointer.json``.
    Either source may recover a run. When both exist they must agree on
    the exact full ``delegated_run_id`` string. Canonical pointer ids
    still use the canonical parser; a value the canonical parser
    rejects is offered to the recovery-only legacy alias seam (P1
    repair) exactly once, verbatim. Unreadable, malformed, missing, or
    conflicting evidence fails closed with stable code-only errors.
    """
    directory = Path(attempt_dir)
    values: list[str] = []
    saw_pointer = False

    markdown = directory / POINTER_FILENAME
    if markdown.exists():
        saw_pointer = True
        try:
            text = markdown.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            raise DelegatedRunArtifactError("POINTER_READ_FAILED") from None
        for line in text.splitlines():
            match = _POINTER_RUN_ID_LINE_RE.match(line)
            if match is not None:
                values.append(match.group(1))

    execution = directory / EXECUTION_POINTER_FILENAME
    if execution.exists():
        saw_pointer = True
        try:
            payload = json.loads(execution.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise DelegatedRunArtifactError("POINTER_READ_FAILED") from None
        if not isinstance(payload, dict):
            raise DelegatedRunArtifactError("POINTER_READ_FAILED")
        value = payload.get("delegated_run_id")
        if value is not None:
            if not isinstance(value, str):
                raise DelegatedRunArtifactError("POINTER_RUN_ID_MISSING")
            values.append(value)

    if not saw_pointer:
        raise DelegatedRunArtifactError("POINTER_READ_FAILED")
    if not values:
        raise DelegatedRunArtifactError("POINTER_RUN_ID_MISSING")
    if len(set(values)) > 1:
        raise DelegatedRunArtifactError("POINTER_RUN_ID_AMBIGUOUS")
    value = values[0]
    try:
        return parse_delegated_run_id(value)
    except DelegatedRunArtifactError:
        return _parse_legacy_pointer_run_id(value)


def recover_attempt_run(attempt_dir: object) -> RecoveredRunIdentity:
    """Map one attempt directory back to exactly one delegated run.

    Binding rules (fail closed on any mismatch):

    - the pointer's run id must parse canonically or as a recovery-only
      legacy alias, and its attempt number must equal the directory's
      ordinal — for legacy directories the pointer is the only binding,
      and it is never rewritten;
    - a canonical suffixed directory must additionally carry exactly
      the run's accepted 8- or 12-hex random id as its directory suffix, so one
      physical path proves one immutable delegated run;
    - a legacy recovery alias on a suffixed directory must still prove
      exact attempt number plus exact physical suffix agreement via its
      trailing random id (a non-8/12-hex suffixed directory can never
      satisfy an 8/12-hex alias suffix, so it fails closed rather than
      binding pointer-only);
    - a non-canonical suffixed directory with a canonical pointer id
      (pre-grammar suffix shapes) binds pointer-only with ordinal
      agreement, staying visible for census/reconciliation instead of
      silently disappearing.
    """
    parsed = parse_attempt_dir_name(Path(attempt_dir).name)
    identity = read_pointer_run_id(attempt_dir)
    if parsed.attempt != identity.attempt:
        raise DelegatedRunArtifactError("ATTEMPT_DIR_NAME_RUN_MISMATCH")
    if isinstance(identity, LegacyPointerRunIdentity):
        if parsed.suffix is not None and parsed.suffix != identity.random_id:
            raise DelegatedRunArtifactError("ATTEMPT_DIR_NAME_RUN_MISMATCH")
    elif parsed.canonical and parsed.suffix != identity.random_id:
        raise DelegatedRunArtifactError("ATTEMPT_DIR_NAME_RUN_MISMATCH")
    return identity
