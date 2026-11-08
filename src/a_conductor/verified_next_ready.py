"""WO-P1-738 — Verified NEXT READY selection (verify-then-select).

One READ-ONLY seam for one explicit graph ID + one explicit graph-run ID +
one completed parent node: select at most ONE direct-successor node ID for a
future continuation. The selection is advisory only and is NOT dispatch
authorization.

Reuse-before-build: this module owns NO selection authority of its own. It
composes ONLY the two verified ZRA-3 seams —

- ``observe_next_ready_facts`` (``next_ready_continuation.py:378``): the
  existing read-only durable job observation interface (one ``get_job``
  reader port, injected, fixture-ownable);
- ``plan_next_ready_continuation`` (``next_ready_continuation.py:256``): the
  existing PURE planner whose priority/topological/node-ID ordering is
  preserved verbatim in every selection and every ordered output.

plus one injected authoritative completion-verification port
(:class:`ParentCompletionVerifier`). This module NEVER manufactures an
acceptance verdict: an ACCEPTED verdict must come from the port and must bind
to the exact graph/run/node/job identity and the durably observed parent
version; anything else fails closed as a typed blocker.

Output is EXACTLY one of:
1. one selected direct-successor ID (:attr:`VerifiedNextReadyOutcomeKind.SELECTED`);
2. an existing no-op / reconciliation planner outcome
   (:attr:`VerifiedNextReadyOutcomeKind.NOOP` /
   :attr:`VerifiedNextReadyOutcomeKind.RECONCILE`);
3. a typed blocker (:attr:`VerifiedNextReadyOutcomeKind.BLOCKED` with an
   exact reason code below).

``select_verified_next_ready`` never raises: every failure mode — including
unexpected port exceptions — is contained into a typed blocker (boundary
containment mirroring the accepted WO-736 pattern). Partial, conflicting, or
malformed reads are NEVER interpreted as "no successor".

Typed reason-code contract (asserted by ``tests/test_verified_next_ready.py``):

Input / port validity:
- ``VERIFIED_NEXT_READY_INPUT_INVALID`` — malformed caller input
- ``VERIFIED_NEXT_READY_JOBS_PORT_INVALID`` — jobs reader lacks get_job
- ``VERIFIED_NEXT_READY_VERIFIER_PORT_INVALID`` — verifier lacks the
  verification method
- ``VERIFIED_NEXT_READY_JOBS_PORT_INSPECTION_FAILED`` — inspecting the
  jobs port's ``get_job`` attribute raised (contained; detail carries the
  exception type name only)
- ``VERIFIED_NEXT_READY_VERIFIER_PORT_INSPECTION_FAILED`` — inspecting
  the verifier port's method attribute raised (contained; type name only)

Completion verdict:
- ``COMPLETION_VERDICT_MISSING`` — verifier returned None
- ``COMPLETION_VERDICT_INVALID`` — the returned verdict object exists but
  its typed fields cannot be safely inspected at the consumer boundary
  (uninitialized slots or attribute access raising; contained; detail
  carries the exception type name only). Distinct from
  ``COMPLETION_VERDICT_MALFORMED`` (fully inspectable object whose field
  values violate the verdict contract).
- ``COMPLETION_VERDICT_MALFORMED`` — verifier returned a non-verdict shape
  or a verdict with malformed typed fields
- ``COMPLETION_VERDICT_REJECTED`` — verifier authoritatively rejected the
  completion
- ``COMPLETION_VERDICT_EVIDENCE_MISSING`` — ACCEPTED without completion
  evidence
- ``COMPLETION_VERIFIER_FAILED`` — verifier raised; contained, detail
  carries the exception type name only
- ``COMPLETION_BINDING_GRAPH_MISMATCH`` — verdict bound to another graph
- ``COMPLETION_BINDING_RUN_MISMATCH`` — verdict bound to another run
- ``COMPLETION_BINDING_NODE_MISMATCH`` — verdict bound to another node
- ``COMPLETION_BINDING_JOB_MISMATCH`` — verdict bound to another job
- ``COMPLETION_VERSION_MISMATCH`` — verdict version is stale/conflicting
  against the durably observed parent version
- ``COMPLETION_STATE_CONFLICT`` — ACCEPTED verdict against a durable parent
  state that is not COMPLETE (conflicting evidence; never a silent no-op)

Ingress normalization (fail closed at ONE guarded boundary before any
validation/comparison/formatting/selection): caller input fields and every
port-returned verdict field are each extracted EXACTLY ONCE at the guarded
ingress and the extracted values are normalized there; the verdict object is
never touched again downstream (no repeated field reads). Strings are
accepted only when ``type(v) is str`` and integers only when
``type(v) is int`` (bool and subclasses rejected BEFORE any range check, so
hostile comparators are never invoked); the enum kind is accepted only by
identity against the explicitly allowed trusted members (no equality, no
coercion, no isinstance trust). BOTH sides of every binding AND the
rejected-verdict reason_code are normalized at this boundary; invalid input
or extraction failure is a contained fail-closed typed result. A verdict-side
binding value that is not an exact plain ``str`` is a binding mismatch by
definition (its comparators are never invoked), so a ``str`` subclass whose
``==``/``!=`` raises or lies can never detonate raw or launder a selection,
and a caller-side non-plain id is ``VERIFIED_NEXT_READY_INPUT_INVALID``
before any comparison. Downstream uses only normalized plain values; the
plain binding comparison itself is additionally wrapped in bounded
containment (typed blocker on any residual failure).

Observation containment (existing observe vocabulary passed through
unchanged; no second vocabulary):
- ``PARENT_JOB_NOT_FOUND`` / ``PARENT_JOB_INVALID`` /
  ``PARENT_JOB_IDENTITY_MISMATCH`` / ``GRAPH_JOB_INVALID`` /
  ``GRAPH_JOB_IDENTITY_MISMATCH`` — from ``observe_next_ready_facts``
- ``OBSERVATION_READ_FAILED`` — store fault or unexpected exception during
  observation
- ``OBSERVATION_INPUT_INVALID`` — malformed values reaching observation
- ``OBSERVATION_INCONSISTENT`` — repeated parent-job reads inside one
  observation boundary disagree on durable identity (job_id/state/
  version), or the observed identity does not match the parent identity
  used for the verdict cross-check. The reused seam reads the parent job
  more than once (facts projection + graph-state projection); a
  boundary-level read monitor proves that the parent identity seen by the
  verdict check equals the identity of the final projected observation.
  Conflicting reads fail closed here BEFORE the verdict cross-check and
  can never select.

Planner containment (existing planner vocabulary passed through unchanged):
- ``PARENT_NODE_UNKNOWN`` / ``GRAPH_CYCLE`` /
  ``PARENT_COMPLETION_EVIDENCE_MISSING`` / ``WORKTREE_DIRTY`` /
  ``HEAD_DRIFT`` / ``LEASE_CONFLICT`` / ``PROVIDER_ADMISSION_STALE``
- ``PLANNER_FAILED`` — unexpected planner exception; contained

Because the ACCEPTED verdict is cross-checked against durable state, the
planner's ``NOOP_PARENT_NOT_COMPLETE`` outcome is unreachable through this
seam (the stricter ``COMPLETION_STATE_CONFLICT`` blocker fires first); the
planner boundary itself is unchanged.

Prohibitions (WO-P1-738 §3): no loop, no continuation-loop reconstruction,
no dispatch-request construction, no execution, no claim mutation, no
network/credentials/live runtime, no new store/scheduler/authority. This
seam must not weaken, bypass, or shadow any existing ORCH-1 boundary.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .domain import TaskState
from .graph.dispatch import GraphDispatchKey
from .graph.domain import TaskGraph
from .job_store import JobStoreError
from .next_ready_continuation import (
    ContinuationGuards,
    NextReadyContinuationError,
    NextReadyDecision,
    NextReadyPlan,
    ParentCompletion,
    observe_next_ready_facts,
    plan_next_ready_continuation,
)

_IDENTITY_RE = re.compile(r"^[A-Za-z0-9._:/-]{1,256}$")

_MAX_DETAIL_CHARS = 256
_MAX_REASON_CHARS = 96


class ParentCompletionVerdictKind(str, Enum):
    """Verdict vocabulary owned by the completion-verification authority."""

    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class ParentCompletionVerdict:
    """Accepted/rejected completion verdict bound to one parent job.

    Produced only by the injected verification port. Every binding field is
    revalidated by the consumer (this module) before the verdict can select.
    """

    kind: ParentCompletionVerdictKind
    reason_code: str
    graph_id: str
    graph_run_id: str
    node_id: str
    job_id: str
    job_version: int
    completion_evidence_ref: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ParentCompletionVerdictKind):
            raise ValueError("kind must be a ParentCompletionVerdictKind")
        if not isinstance(self.reason_code, str) or not self.reason_code.strip():
            raise ValueError("reason_code must be non-empty str")
        for field in ("graph_id", "graph_run_id", "node_id", "job_id"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be non-empty str")
        if (
            not isinstance(self.job_version, int)
            or isinstance(self.job_version, bool)
            or self.job_version < 1
        ):
            raise ValueError("job_version must be a positive int")
        if self.completion_evidence_ref is not None and not isinstance(
            self.completion_evidence_ref, str
        ):
            raise ValueError("completion_evidence_ref must be str or None")


class ParentCompletionVerifier(Protocol):
    """Authoritative completion-verification port (fixture-ownable).

    The implementation derives its verdict from its own durable completion
    evidence; this seam only consumes the returned verdict after binding
    revalidation.
    """

    def verify_parent_completion(
        self,
        *,
        graph_id: str,
        graph_run_id: str,
        node_id: str,
        job_id: str,
    ) -> ParentCompletionVerdict: ...


class VerifiedNextReadyOutcomeKind(str, Enum):
    """Exactly-one-of output vocabulary for the verify-then-select seam."""

    SELECTED = "SELECTED"
    NOOP = "NOOP"
    RECONCILE = "RECONCILE"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class VerifiedNextReadyOutcome:
    """One verify-then-select outcome (advisory, never dispatch authority).

    ``candidate_node_ids`` / ``represented_node_ids`` /
    ``recovery_node_ids`` carry the planner's ordered outputs verbatim;
    this module never reorders.
    """

    kind: VerifiedNextReadyOutcomeKind
    selected_node_id: str | None = None
    blocker_code: str | None = None
    planner_decision: NextReadyDecision | None = None
    detail: str = ""
    candidate_node_ids: tuple[str, ...] = ()
    represented_node_ids: tuple[str, ...] = ()
    recovery_node_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.kind, VerifiedNextReadyOutcomeKind):
            raise ValueError("kind must be a VerifiedNextReadyOutcomeKind")
        if not isinstance(self.detail, str):
            raise ValueError("detail must be str")
        object.__setattr__(self, "detail", self.detail[:_MAX_DETAIL_CHARS])
        for name in (
            "candidate_node_ids",
            "represented_node_ids",
            "recovery_node_ids",
        ):
            values = getattr(self, name)
            if not isinstance(values, tuple):
                raise ValueError(f"{name} must be a tuple")
            object.__setattr__(self, name, values)
        if self.planner_decision is not None and not isinstance(
            self.planner_decision, NextReadyDecision
        ):
            raise ValueError("planner_decision must be NextReadyDecision or None")
        if self.kind is VerifiedNextReadyOutcomeKind.SELECTED:
            if not isinstance(self.selected_node_id, str) or self.blocker_code is not None:
                raise ValueError("SELECTED requires selected_node_id, no blocker")
        elif self.kind is VerifiedNextReadyOutcomeKind.BLOCKED:
            if not isinstance(self.blocker_code, str) or not self.blocker_code:
                raise ValueError("BLOCKED requires blocker_code")
            if self.selected_node_id is not None:
                raise ValueError("BLOCKED never selects")
        else:
            if self.selected_node_id is not None or self.blocker_code is not None:
                raise ValueError("NOOP/RECONCILE never select or block")


class ContinuationJobReader(Protocol):
    """Existing read-only job observation interface (single get_job)."""

    def get_job(self, job_id: str): ...


class _ParentReadMonitor:
    """Read-recording delegation port for one observation boundary.

    Wraps the injected jobs reader passed to ``observe_next_ready_facts``
    and records the durable identity (job_id/state/version) of every read
    of the parent job made inside that boundary. The reused seam reads the
    parent job more than once (facts projection + graph-state projection);
    the recorded identities let the consumer prove that the parent identity
    seen by the verdict cross-check equals the identity of the final
    projected observation. Delegation is verbatim: no read is added,
    dropped, retried, or reordered, and exceptions propagate unchanged into
    the existing observation containment.
    """

    def __init__(self, reader: ContinuationJobReader, parent_job_id: str) -> None:
        self._reader = reader
        self._parent_job_id = parent_job_id
        self.parent_reads: list[tuple[object, object, object]] = []

    def get_job(self, job_id: str):
        job = self._reader.get_job(job_id)
        if job_id == self._parent_job_id:
            try:
                self.parent_reads.append(
                    (
                        getattr(job, "job_id", None),
                        getattr(job, "state", None),
                        getattr(job, "version", None),
                    )
                )
            except Exception:
                # identity extraction must never turn into a selection path
                self.parent_reads.append((None, None, None))
        return job


def _parent_observation_consistent(
    reads: list[tuple[object, object, object]],
    parent: ParentCompletion,
) -> bool:
    """True iff repeated parent observations agree with each other AND with
    the parent identity used for the verdict cross-check (fail closed on
    any doubt, including unhashable or missing identity evidence)."""
    try:
        if len(reads) > 1 and len(set(reads)) != 1:
            return False
        identity = (parent.job_id, parent.state, parent.version)
        return identity in reads
    except Exception:
        return False


def _bounded(text: str, limit: int) -> str:
    cleaned = text.replace("\x00", "").replace("\r", " ").replace("\n", " ")
    return cleaned[:limit]


def _blocked(code: str, detail: str = "") -> VerifiedNextReadyOutcome:
    return VerifiedNextReadyOutcome(
        kind=VerifiedNextReadyOutcomeKind.BLOCKED,
        blocker_code=code,
        detail=_bounded(detail, _MAX_DETAIL_CHARS),
    )


def _plan_outcome(plan: NextReadyPlan) -> VerifiedNextReadyOutcome:
    if plan.decision is NextReadyDecision.DISPATCH_ONE:
        kind = VerifiedNextReadyOutcomeKind.SELECTED
    elif plan.decision is NextReadyDecision.RECONCILE_RECOVERY:
        kind = VerifiedNextReadyOutcomeKind.RECONCILE
    else:
        kind = VerifiedNextReadyOutcomeKind.NOOP
    return VerifiedNextReadyOutcome(
        kind=kind,
        selected_node_id=plan.selected_node_id,
        planner_decision=plan.decision,
        detail=plan.detail,
        candidate_node_ids=plan.candidate_node_ids,
        represented_node_ids=plan.represented_node_ids,
        recovery_node_ids=plan.recovery_node_ids,
    )


def _verify_binding(
    *,
    verdict_graph_id: str,
    verdict_graph_run_id: str,
    verdict_node_id: str,
    verdict_job_id: str,
    verdict_evidence_ref: str | None,
    graph_id: str,
    graph_run_id: str,
    parent_node_id: str,
    expected_job_id: str,
) -> VerifiedNextReadyOutcome | None:
    """Plain-value binding cross-check on NORMALIZED plain values (fail
    closed).

    BOTH sides are pre-normalized at the guarded ingress boundary: a
    verdict-side binding value that is not an exact plain ``str`` never
    reaches this function (it is fail-closed as a binding mismatch at the
    ingress, comparators never invoked), so only exact plain ``str``
    values are compared here. The comparison block is additionally wrapped
    in bounded containment as defense in depth.
    """
    try:
        if verdict_graph_id != graph_id:
            return _blocked("COMPLETION_BINDING_GRAPH_MISMATCH")
        if verdict_graph_run_id != graph_run_id:
            return _blocked("COMPLETION_BINDING_RUN_MISMATCH")
        if verdict_node_id != parent_node_id:
            return _blocked("COMPLETION_BINDING_NODE_MISMATCH")
        if verdict_job_id != expected_job_id:
            return _blocked("COMPLETION_BINDING_JOB_MISMATCH")
    except Exception as exc:  # bounded containment: type name only
        return _blocked(
            "COMPLETION_VERDICT_INVALID",
            f"COMPLETION_VERDICT_INVALID:{type(exc).__name__}",
        )
    if verdict_evidence_ref is None:
        return _blocked("COMPLETION_VERDICT_EVIDENCE_MISSING")
    return None


def select_verified_next_ready(
    *,
    jobs: ContinuationJobReader,
    completion_verifier: ParentCompletionVerifier,
    graph: TaskGraph,
    graph_id: str,
    graph_run_id: str,
    parent_node_id: str,
    guards: ContinuationGuards,
) -> VerifiedNextReadyOutcome:
    """Verify the parent completion, then select at most one successor.

    Read-only and total: never raises, never mutates, never dispatches.
    Identical inputs against identical durable truth re-derive an identical
    outcome (restart/re-read stability).
    """
    # ---- guarded ingress boundary (BEFORE any validation/comparison/
    # formatting/selection): normalize the caller input fields exactly
    # once. Strings are accepted only when type(value) is str — a caller
    # id str subclass (e.g. one whose reflected __ne__ lies or detonates)
    # is fail-closed here without ever invoking its operators or the
    # identity grammar, so it can never launder a binding mismatch.
    for field_name, value in (
        ("graph_id", graph_id),
        ("graph_run_id", graph_run_id),
        ("parent_node_id", parent_node_id),
    ):
        if type(value) is not str or not _IDENTITY_RE.fullmatch(value):
            return _blocked(
                "VERIFIED_NEXT_READY_INPUT_INVALID", f"{field_name} is invalid"
            )

    # ---- input / port validation (fail closed, contained) ----
    # attribute inspection itself is inside containment: a port whose
    # __getattribute__ raises must never escape raw (getattr's default only
    # suppresses AttributeError)
    try:
        jobs_get_job = getattr(jobs, "get_job", None)
    except Exception as exc:  # bounded containment: type name only
        return _blocked(
            "VERIFIED_NEXT_READY_JOBS_PORT_INSPECTION_FAILED",
            f"VERIFIED_NEXT_READY_JOBS_PORT_INSPECTION_FAILED:{type(exc).__name__}",
        )
    if not callable(jobs_get_job):
        return _blocked("VERIFIED_NEXT_READY_JOBS_PORT_INVALID")
    try:
        verifier_method = getattr(
            completion_verifier, "verify_parent_completion", None
        )
    except Exception as exc:  # bounded containment: type name only
        return _blocked(
            "VERIFIED_NEXT_READY_VERIFIER_PORT_INSPECTION_FAILED",
            f"VERIFIED_NEXT_READY_VERIFIER_PORT_INSPECTION_FAILED:{type(exc).__name__}",
        )
    if not callable(verifier_method):
        return _blocked("VERIFIED_NEXT_READY_VERIFIER_PORT_INVALID")
    if not isinstance(graph, TaskGraph):
        return _blocked("VERIFIED_NEXT_READY_INPUT_INVALID", "graph must be TaskGraph")
    if not isinstance(guards, ContinuationGuards):
        return _blocked("VERIFIED_NEXT_READY_INPUT_INVALID", "guards must be ContinuationGuards")

    try:
        expected_job_id = GraphDispatchKey(
            graph_id, graph_run_id, parent_node_id
        ).job_id
    except (TypeError, ValueError):
        return _blocked("VERIFIED_NEXT_READY_INPUT_INVALID", "dispatch key invalid")

    # ---- authoritative completion verdict (never manufactured here) ----
    try:
        verdict = completion_verifier.verify_parent_completion(
            graph_id=graph_id,
            graph_run_id=graph_run_id,
            node_id=parent_node_id,
            job_id=expected_job_id,
        )
    except NextReadyContinuationError as exc:
        return _blocked(exc.code)
    except Exception as exc:  # bounded containment: type name only
        return _blocked(
            "COMPLETION_VERIFIER_FAILED", f"COMPLETION_VERIFIER_FAILED:{type(exc).__name__}"
        )

    # ---- guarded ingress boundary: extract each verdict field exactly
    # once ----
    # the port-returned object is read exactly once per field below and
    # NEVER touched again; validation, comparison, and formatting run only
    # on the extracted normalized plain values, so no shapeshifter verdict
    # can present one value to validation and a different one to the
    # pipeline (the validated-then-reread TOCTOU is structurally closed)
    if verdict is None:
        return _blocked("COMPLETION_VERDICT_MISSING")
    if not isinstance(verdict, ParentCompletionVerdict):
        return _blocked("COMPLETION_VERDICT_MALFORMED")
    try:
        verdict_kind = verdict.kind
        verdict_reason_code = verdict.reason_code
        verdict_graph_id = verdict.graph_id
        verdict_graph_run_id = verdict.graph_run_id
        verdict_node_id = verdict.node_id
        verdict_job_id = verdict.job_id
        verdict_version = verdict.job_version
        verdict_evidence_ref = verdict.completion_evidence_ref
    except Exception as exc:  # bounded containment: type name only
        return _blocked(
            "COMPLETION_VERDICT_INVALID",
            f"COMPLETION_VERDICT_INVALID:{type(exc).__name__}",
        )

    # ---- normalize the extracted values (no further verdict reads) ----
    # enum kind: identity against the explicitly allowed trusted members
    # only (no isinstance trust, no equality comparison, no coercion)
    if (
        verdict_kind is not ParentCompletionVerdictKind.ACCEPTED
        and verdict_kind is not ParentCompletionVerdictKind.REJECTED
    ):
        return _blocked("COMPLETION_VERDICT_MALFORMED")
    # rejected-verdict reason_code: exact plain str, normalized here BEFORE
    # the rejected-branch formatting can invoke any method on it
    if type(verdict_reason_code) is not str or not verdict_reason_code.strip():
        return _blocked("COMPLETION_VERDICT_MALFORMED")
    # version: exact plain int (bool and int subclasses rejected) BEFORE
    # any range check/comparison, so hostile comparators are never invoked
    if type(verdict_version) is not int:
        return _blocked("COMPLETION_VERDICT_MALFORMED")
    if verdict_version < 1:
        return _blocked("COMPLETION_VERDICT_MALFORMED")
    if verdict_evidence_ref is not None and type(verdict_evidence_ref) is not str:
        return _blocked("COMPLETION_VERDICT_MALFORMED")
    # verdict-side binding values: a non-plain value is a binding mismatch
    # by definition — fail closed WITHOUT invoking its comparators,
    # preserving the exact per-field mismatch codes
    if type(verdict_graph_id) is not str:
        return _blocked("COMPLETION_BINDING_GRAPH_MISMATCH")
    if type(verdict_graph_run_id) is not str:
        return _blocked("COMPLETION_BINDING_RUN_MISMATCH")
    if type(verdict_node_id) is not str:
        return _blocked("COMPLETION_BINDING_NODE_MISMATCH")
    if type(verdict_job_id) is not str:
        return _blocked("COMPLETION_BINDING_JOB_MISMATCH")
    for field_name, value in (
        ("reason_code", verdict_reason_code),
        ("graph_id", verdict_graph_id),
        ("graph_run_id", verdict_graph_run_id),
        ("node_id", verdict_node_id),
        ("job_id", verdict_job_id),
    ):
        if not value.strip():
            return _blocked(
                "COMPLETION_VERDICT_MALFORMED", f"{field_name} is empty"
            )

    if verdict_kind is ParentCompletionVerdictKind.REJECTED:
        return _blocked(
            "COMPLETION_VERDICT_REJECTED",
            f"COMPLETION_VERDICT_REJECTED:{_bounded(verdict_reason_code, _MAX_REASON_CHARS)}",
        )

    binding = _verify_binding(
        verdict_graph_id=verdict_graph_id,
        verdict_graph_run_id=verdict_graph_run_id,
        verdict_node_id=verdict_node_id,
        verdict_job_id=verdict_job_id,
        verdict_evidence_ref=verdict_evidence_ref,
        graph_id=graph_id,
        graph_run_id=graph_run_id,
        parent_node_id=parent_node_id,
        expected_job_id=expected_job_id,
    )
    if binding is not None:
        return binding

    # ---- read-only observation through the verified seam (REUSE) ----
    # the parent-read monitor proves one consistent parent identity across
    # the whole observation boundary (facts projection + graph-state
    # projection); delegation is verbatim and exceptions flow unchanged
    # into the containment below
    monitor = _ParentReadMonitor(jobs, expected_job_id)
    try:
        facts = observe_next_ready_facts(
            jobs=monitor,
            graph=graph,
            graph_id=graph_id,
            graph_run_id=graph_run_id,
            parent_node_id=parent_node_id,
            guards=guards,
            completion_ref=verdict_evidence_ref,
        )
    except NextReadyContinuationError as exc:
        return _blocked(exc.code)
    except JobStoreError as exc:
        return _blocked(
            "OBSERVATION_READ_FAILED", f"OBSERVATION_READ_FAILED:{_bounded(exc.code, 64)}"
        )
    except ValueError as exc:
        return _blocked(
            "OBSERVATION_INPUT_INVALID", f"OBSERVATION_INPUT_INVALID:{type(exc).__name__}"
        )
    except Exception as exc:  # bounded containment: type name only
        return _blocked(
            "OBSERVATION_READ_FAILED", f"OBSERVATION_READ_FAILED:{type(exc).__name__}"
        )

    # ---- repeated parent observations must agree within the boundary ----
    # the parent identity seen by the verdict cross-check must equal the
    # parent identity of the final projected observation; conflicting
    # COMPLETE snapshots across reads can therefore never select
    if not _parent_observation_consistent(monitor.parent_reads, facts.parent):
        return _blocked(
            "OBSERVATION_INCONSISTENT",
            "OBSERVATION_INCONSISTENT:PARENT_JOB_READS_CONFLICT",
        )

    # ---- cross-check the accepted verdict against durable truth ----
    if verdict_version != facts.parent.version:
        return _blocked("COMPLETION_VERSION_MISMATCH")
    if facts.parent.state is not TaskState.COMPLETE:
        return _blocked(
            "COMPLETION_STATE_CONFLICT",
            "accepted completion verdict conflicts with durable parent state",
        )

    # ---- pure planner decision through the verified seam (REUSE) ----
    try:
        plan = plan_next_ready_continuation(facts)
    except NextReadyContinuationError as exc:
        return _blocked(exc.code)
    except Exception as exc:  # defensive containment: type name only
        return _blocked(
            "PLANNER_FAILED", f"PLANNER_FAILED:{type(exc).__name__}"
        )

    return _plan_outcome(plan)
