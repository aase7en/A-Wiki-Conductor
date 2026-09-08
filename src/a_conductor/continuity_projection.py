"""WO-P1-166 P0-B4 — single-writer continuity projections.

REUSE / WRAP only (no second scheduler, job store, work-order system,
claim store, lease store, checkpoint DB, retry engine, lifecycle state
machine, review authority, or projection authority):

1. a PURE deterministic projection renderer — immutable identity-bound
   ``ProjectionFacts`` render byte-stable machine-owned sentinel sections;
   Markdown is NEVER parsed back for authority;
2. a thin ``ContinuityProjectionFoldAdapter`` satisfying the existing
   ``CloseoutFoldPort`` protocol — it publishes projections ONLY through
   the existing ``AgentChangeApplier`` mutation authority (lease-gated,
   all-or-nothing per-file preflight, content ``expected_sha256``
   preconditions), one target packet at a time, then read-back verifies
   EVERY intended target before ``completed=True``.

The adapter writes files one-by-one (AgentChangeApplier is atomic per
file, not per bundle). A crash/failure after the first target can leave
a mixed old/new projection — acceptable ONLY because the adapter then
returns ``completed=None`` (ambiguous, never optimistic), re-observation
stays fail-closed under ContinuityGuard's SSOT_DRIFT/recovery rules,
and there is NO internal blind retry. The durable fold checkpoint after
effect success remains owned by GoalCloseout's executor.

Deterministic UTF-8 / LF-only output; no wall-clock, no environment
reads, no threading, no network, no database inside this module.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Callable, Iterable, Mapping, Protocol

from .agent_change_packets import (
    AgentChangeApplier,
    AgentChangeError,
    AgentFileChange,
    AgentResultPacket,
)
from .goal_closeout import FoldOutcome, FoldRequest

CANONICAL_TARGETS: tuple[str, ...] = (
    "CURRENT-WORK.md", "handoff.md", "COLLAB.md",
)
_TARGET_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_BEGIN_SENTINEL = "<!-- BEGIN-MACHINE-PROJECTION -->"
_END_SENTINEL = "<!-- END-MACHINE-PROJECTION -->"
_SENTINEL_PAIR_RE = re.compile(
    re.escape(_BEGIN_SENTINEL) + r"(.*?)" + re.escape(_END_SENTINEL),
    re.DOTALL,
)

_HISTORICAL_ANCHOR_RE = re.compile(r"^<!-- HISTORICAL EVIDENCE[^\n]*$", re.MULTILINE)
_COLLAB_HEADING_RE = re.compile(r"^## In-progress claims$", re.MULTILINE)
_WO166_ROW_RE = re.compile(r"^\| `WO-P1-166`.*$", re.MULTILINE)
_LEASE_STATES = frozenset({"ACTIVE", "RELEASED", "QUARANTINED", "STALE", "UNKNOWN"})
_CLOSEOUT_STATUSES = frozenset({"FOLD_PENDING", "FOLD_REQUIRED", "COMPLETE", "RECOVERY_REQUIRED", "BLOCKED"})
_POST_MAIN_STATUSES = frozenset({"NOT_REQUIRED", "PENDING", "SUCCESS", "FAILED", "UNKNOWN"})
_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")


class ProjectionError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _text(value: str, field: str, *, max_length: int = 512) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value or len(value) > max_length:
        raise ValueError(f"{field} is invalid")
    return value.strip()


def _optional_sha(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise ValueError(f"{field} is invalid")
    return value.casefold()


@dataclass(frozen=True, slots=True)
class ProjectionLeaseFact:
    """Display-only lease fact — never a lease authority (the store is)."""

    lease_id: str
    session_id: str
    task_id: str
    state: str
    owner_ok: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "lease_id", _text(self.lease_id, "lease_id", max_length=128))
        object.__setattr__(self, "session_id", _text(self.session_id, "session_id", max_length=128))
        object.__setattr__(self, "task_id", _text(self.task_id, "task_id", max_length=256))
        state = _text(self.state, "state", max_length=32).upper()
        if state not in _LEASE_STATES:
            raise ValueError("state is invalid")
        object.__setattr__(self, "state", state)
        if not isinstance(self.owner_ok, bool):
            raise ValueError("owner_ok must be bool")


@dataclass(frozen=True, slots=True)
class ProjectionFacts:
    """Immutable, identity-bound facts sufficient to render the current
    projection state. Minimal by design — NOT an authority database."""

    task_id: str
    candidate_sha: str
    branch: str
    head: str | None
    merge_commit: str | None
    post_main_status: str
    closeout_status: str
    leases: tuple[ProjectionLeaseFact, ...]
    ownership_known: bool
    writer_session: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_id", _text(self.task_id, "task_id", max_length=256))
        object.__setattr__(self, "candidate_sha", _optional_sha(self.candidate_sha, "candidate_sha") or "")
        object.__setattr__(self, "branch", _text(self.branch, "branch", max_length=256))
        object.__setattr__(self, "head", _optional_sha(self.head, "head"))
        object.__setattr__(self, "merge_commit", _optional_sha(self.merge_commit, "merge_commit"))
        status = _text(self.post_main_status, "post_main_status", max_length=32).upper()
        if status not in _POST_MAIN_STATUSES:
            raise ValueError("post_main_status is invalid")
        object.__setattr__(self, "post_main_status", status)
        closeout = _text(self.closeout_status, "closeout_status", max_length=32).upper()
        if closeout not in _CLOSEOUT_STATUSES:
            raise ValueError("closeout_status is invalid")
        object.__setattr__(self, "closeout_status", closeout)
        leases = tuple(self.leases)
        if any(not isinstance(item, ProjectionLeaseFact) for item in leases):
            raise ValueError("leases must be ProjectionLeaseFact instances")
        if len({item.lease_id for item in leases}) != len(leases):
            raise ValueError("lease_id must be unique")
        object.__setattr__(self, "leases", leases)
        if not isinstance(self.ownership_known, bool):
            raise ValueError("ownership_known must be bool")
        object.__setattr__(self, "writer_session", _text(self.writer_session, "writer_session", max_length=128))


def _render_machine_block(facts: ProjectionFacts) -> str:
    """Deterministic machine-owned block: same facts => identical bytes.
    Explicit UNKNOWN for missing facts; canonical (sorted) lease order."""
    active = sorted(
        item.lease_id for item in facts.leases
        if item.state == "ACTIVE" and item.owner_ok
    )
    released = sorted(
        item.lease_id for item in facts.leases if item.state == "RELEASED"
    )
    lines = [
        f"task: {facts.task_id}",
        f"candidate: {facts.candidate_sha or 'UNKNOWN'}",
        f"branch: {facts.branch}",
        f"head: {facts.head or 'UNKNOWN'}",
        f"merge-commit: {facts.merge_commit or 'UNKNOWN'}",
        f"post-main: {facts.post_main_status}",
        f"closeout: {facts.closeout_status}",
        f"active-leases: {','.join(active) if active else 'NONE'}",
        f"ownership: {'KNOWN' if facts.ownership_known else 'UNKNOWN'}",
        f"writer-session: {facts.writer_session}",
    ]
    if released:
        lines.append(f"released-leases: {','.join(released)}")
    return "\n".join(lines)


def _adopt_front_matter(prior_text: str, machine: str) -> str:
    """FIRST-ADOPTION for CURRENT-WORK.md / handoff.md production shape:
    exactly one HISTORICAL EVIDENCE anchor comment; title line preserved
    byte-for-byte; the current-authoritative region between the title and
    the anchor is adopted into the machine sentinel; the anchor line and
    EVERY byte after it are preserved byte-for-byte."""
    anchors = list(_HISTORICAL_ANCHOR_RE.finditer(prior_text))
    if len(anchors) != 1:
        raise ValueError("PROJECTION_ADOPTION_ANCHOR_INVALID")
    if not prior_text.startswith("# ") or prior_text.find("\n") < 0:
        raise ValueError("PROJECTION_ADOPTION_TITLE_INVALID")
    title = prior_text[: prior_text.find("\n") + 1]
    return title + machine + "\n\n" + prior_text[anchors[0].start():]


def _adopt_collab_row(prior_text: str, machine: str) -> str:
    """FIRST-ADOPTION for COLLAB.md production shape: exactly one
    In-progress claims heading and exactly one WO-P1-166 row; ONLY that
    row line is adopted into the machine sentinel; every other byte
    (headers, other rows, human text) is preserved byte-for-byte."""
    headings = list(_COLLAB_HEADING_RE.finditer(prior_text))
    if len(headings) != 1:
        raise ValueError("PROJECTION_ADOPTION_ANCHOR_INVALID")
    rows = list(_WO166_ROW_RE.finditer(prior_text))
    if len(rows) != 1 or rows[0].start() < headings[0].start():
        raise ValueError("PROJECTION_ADOPTION_ROW_INVALID")
    return prior_text[: rows[0].start()] + machine + prior_text[rows[0].end():]


def _render_document(
    title: str,
    facts: ProjectionFacts,
    prior_text: str | None,
    adopter: "Callable[[str, str], str] | None" = None,
) -> str:
    block = _render_machine_block(facts)
    machine = f"{_BEGIN_SENTINEL}\n{block}\n{_END_SENTINEL}"
    if prior_text is None:
        return f"# {title}\n\n{machine}\n"
    begin_count = prior_text.count(_BEGIN_SENTINEL)
    end_count = prior_text.count(_END_SENTINEL)
    if begin_count == 0 and end_count == 0:
        if adopter is None:
            raise ValueError("PROJECTION_SENTINEL_INVALID")
        return adopter(prior_text, machine)
    if (
        begin_count != 1
        or end_count != 1
        or len(_SENTINEL_PAIR_RE.findall(prior_text)) != 1
    ):
        # malformed/missing/duplicate sentinels: fail closed, never clobber
        raise ValueError("PROJECTION_SENTINEL_INVALID")
    return _SENTINEL_PAIR_RE.sub(lambda _m: machine, prior_text, count=1)


def render_current_work(facts: ProjectionFacts, *, prior_text: str | None = None) -> str:
    return _render_document("CURRENT-WORK", facts, prior_text, _adopt_front_matter)


def render_handoff(facts: ProjectionFacts, *, prior_text: str | None = None) -> str:
    return _render_document("HANDOFF", facts, prior_text, _adopt_front_matter)


def render_collab(facts: ProjectionFacts, *, prior_text: str | None = None) -> str:
    return _render_document("COLLAB", facts, prior_text, _adopt_collab_row)


_RENDERERS: Mapping[str, Callable[..., str]] = {
    "CURRENT-WORK.md": render_current_work,
    "handoff.md": render_handoff,
    "COLLAB.md": render_collab,
}


def render_projection_target(name: str, facts: ProjectionFacts, *, prior_text: str | None = None) -> str:
    """Render one canonical target. Unsupported names, subdirectories, and
    path traversal are refused before any rendering."""
    if not isinstance(name, str) or name not in _RENDERERS or not _TARGET_NAME_RE.fullmatch(name):
        raise ValueError("PROJECTION_TARGET_UNSUPPORTED")
    return _RENDERERS[name](facts, prior_text=prior_text)


# ---------------- thin fold adapter over AgentChangeApplier ----------------

class _PriorTextLoader(Protocol):
    def __call__(self, name: str) -> str | None: ...


class _ReadBack(Protocol):
    def __call__(self, name: str) -> str | None: ...


class _FileBytes(Protocol):
    def read_text(self, relative_path: str) -> object: ...


class ContinuityProjectionFoldAdapter:
    """CloseoutFoldPort implementation publishing projections through the
    existing AgentChangeApplier mutation authority ONLY.

    All intended render/packet construction happens BEFORE the first
    write; each target is applied as its own lease-gated packet with a
    content precondition; EVERY intended target is read back and verified
    before ``completed=True``; any failure/ambiguity yields
    ``completed=None`` (or ``False`` when nothing was attempted), never
    optimistic success and never an internal blind retry."""

    def __init__(
        self,
        *,
        applier: AgentChangeApplier,
        lease_id: str,
        session_id: str,
        task_id: str,
        actual_head: str,
        facts_factory: Callable[[], ProjectionFacts],
        targets: Iterable[str] = CANONICAL_TARGETS,
        prior_text_loader: _PriorTextLoader | None = None,
        read_back: _ReadBack | None = None,
    ) -> None:
        for method in ("apply",):
            if not callable(getattr(applier, method, None)):
                raise ValueError("applier must provide apply")
        self._applier = applier
        self._lease_id = _text(lease_id, "lease_id", max_length=128)
        self._session_id = _text(session_id, "session_id", max_length=128)
        self._task_id = _text(task_id, "task_id", max_length=256)
        self._actual_head = _optional_sha(actual_head, "actual_head") or ""
        if not callable(facts_factory):
            raise ValueError("facts_factory must be callable")
        self._facts_factory = facts_factory
        names = tuple(targets)
        if not names or any(name not in _RENDERERS for name in names):
            raise ValueError("PROJECTION_TARGET_UNSUPPORTED")
        self._targets = names
        self._prior_text_loader = prior_text_loader or self._default_prior_text
        self._read_back = read_back or self._default_read_back

    # -- default IO through the applier's own confined filesystem -------

    def _filesystem(self) -> _FileBytes:
        fs = getattr(self._applier, "_filesystem", None)
        if fs is None or not callable(getattr(fs, "read_text", None)):
            raise ProjectionError("PROJECTION_FILESYSTEM_UNAVAILABLE")
        return fs

    def _default_prior_text(self, name: str) -> str | None:
        from a_conductor.native_execution import NativeExecutionError

        try:
            result = self._filesystem().read_text(name)
        except NativeExecutionError as exc:
            if getattr(exc, "code", "") == "PATH_NOT_FOUND":
                return None
            raise ProjectionError("PROJECTION_READ_FAILED") from exc
        return getattr(result, "content", None)

    def _default_read_back(self, name: str) -> str | None:
        return self._default_prior_text(name)

    # -- CloseoutFoldPort ------------------------------------------------

    def fold(self, request: FoldRequest) -> FoldOutcome:
        # 1. render EVERYTHING before the first write. Renderer/facts
        #    failures PROPAGATE (matching the B3 executor fold-port
        #    contract: a raising fold port => no fold checkpoint, zero
        #    partial writes).
        facts = self._facts_factory()
        if not isinstance(facts, ProjectionFacts):
            raise ProjectionError("PROJECTION_FACTS_INVALID")
        if facts.task_id != self._task_id:
            raise ProjectionError("PROJECTION_TASK_MISMATCH")
        if request.task_id != self._task_id:
            raise ProjectionError("PROJECTION_TASK_MISMATCH")
        # P1-A: the fold request must bind the EXACT current projection
        # candidate identity. UNKNOWN/absent/unprovable candidate facts
        # fail closed; mismatch NEVER publishes and never completes.
        if (
            not facts.candidate_sha
            or not isinstance(request.candidate_sha, str)
            or request.candidate_sha.casefold() != facts.candidate_sha
        ):
            raise ProjectionError("PROJECTION_CANDIDATE_MISMATCH")
        rendered: dict[str, str] = {}
        for name in self._targets:
            prior = self._prior_text_loader(name)
            rendered[name] = render_projection_target(name, facts, prior_text=prior)

        # 2. skip targets whose current bytes already equal the render
        #    (idempotent republish => zero unnecessary writes)
        pending: list[tuple[str, str, str | None]] = []
        for name in self._targets:
            current = self._prior_text_loader(name)
            if current is not None and current == rendered[name]:
                continue
            expected = sha256((current or "").encode("utf-8")).hexdigest() if current is not None else None
            pending.append((name, rendered[name], expected))

        # 3. publish through the mutation authority, one packet per target
        wrote_any = False
        for name, content, expected in pending:
            change = AgentFileChange(name, content, expected)
            packet = AgentResultPacket(
                task_id=self._task_id,
                provider_id="conductor-projection",
                model_id="deterministic",
                status="CHANGES_PROPOSED",
                base_head=self._actual_head or ("0" * 40),
                changes=(change,),
                evidence_refs=("projection-fold",),
            )
            try:
                self._applier.apply(
                    packet, self._lease_id,
                    session_id=self._session_id,
                    task_id=self._task_id,
                    actual_head=self._actual_head or ("0" * 40),
                )
            except AgentChangeError:
                # preflight conflict / ownership / drift: no NEW write in
                # this packet. Earlier targets may already have landed =>
                # ambiguous, never optimistic.
                return FoldOutcome(completed=None if wrote_any else False)
            except Exception:
                return FoldOutcome(completed=None if wrote_any else False)
            wrote_any = True

        # 4. read back and verify EVERY intended target before success
        for name in self._targets:
            after = self._read_back(name)
            if after is None or after != rendered[name]:
                return FoldOutcome(completed=None)
        return FoldOutcome(completed=True)
