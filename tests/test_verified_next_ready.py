"""WO-P1-738 — Verified NEXT READY selection (verify-then-select) RED matrix.

Covers the WO-P1-738 §2 failure model and §4 acceptance criteria against the
read-only seam ``select_verified_next_ready`` (``verified_next_ready.py``):

- happy path: accepted completion -> exactly one direct successor selected,
  planner priority/topological/node-ID ordering preserved verbatim;
- forged / unbound / rejected / missing acceptance -> typed blockers;
- cross-graph / cross-run / cross-node / cross-job / cross-version evidence
  -> exact per-field binding-mismatch codes;
- partial / conflicting / malformed observation reads -> typed blockers,
  never a silent "no successor";
- already-represented successor / uncertain prior dispatch -> explicit
  NOOP / RECONCILE outcomes, never a reselect;
- guard failure, structural ambiguity, cycle, stale evidence -> blockers;
- restart / re-read stability: identical inputs re-derive the identical
  outcome.

All stores/ports are fixture-owned fakes; no network, no live runtime, no
credentials, no mutation. The two verified ZRA-3 seams
(``observe_next_ready_facts`` + ``plan_next_ready_continuation``) are reused
in these tests only to prove ordering equivalence with the planner, not as a
second selection authority.

Typed reason-code contract pinned (mirrors the implementation module
docstring):

Input / port validity:
- ``VERIFIED_NEXT_READY_INPUT_INVALID``
- ``VERIFIED_NEXT_READY_JOBS_PORT_INVALID``
- ``VERIFIED_NEXT_READY_VERIFIER_PORT_INVALID``
- ``VERIFIED_NEXT_READY_JOBS_PORT_INSPECTION_FAILED`` (inspecting the
  jobs port's ``get_job`` attribute raised; contained, type name only)
- ``VERIFIED_NEXT_READY_VERIFIER_PORT_INSPECTION_FAILED`` (inspecting
  the verifier port's method attribute raised; contained, type name only)

Completion verdict:
- ``COMPLETION_VERDICT_MISSING``
- ``COMPLETION_VERDICT_INVALID`` (verdict object whose typed fields
  cannot be safely inspected at the consumer boundary — uninitialized
  slots or attribute access raising; contained, type name only)
- ``COMPLETION_VERDICT_MALFORMED``
- ``COMPLETION_VERDICT_REJECTED``
- ``COMPLETION_VERDICT_EVIDENCE_MISSING``
- ``COMPLETION_VERIFIER_FAILED``
- ``COMPLETION_BINDING_GRAPH_MISMATCH``
- ``COMPLETION_BINDING_RUN_MISMATCH``
- ``COMPLETION_BINDING_NODE_MISMATCH``
- ``COMPLETION_BINDING_JOB_MISMATCH``
- ``COMPLETION_VERSION_MISMATCH``
- ``COMPLETION_STATE_CONFLICT``

Observation containment:
- ``PARENT_JOB_NOT_FOUND`` / ``PARENT_JOB_INVALID`` /
  ``PARENT_JOB_IDENTITY_MISMATCH`` / ``GRAPH_JOB_INVALID`` /
  ``GRAPH_JOB_IDENTITY_MISMATCH``  (existing observe vocabulary, passed
  through unchanged)
- ``OBSERVATION_READ_FAILED`` (store fault or unexpected exception)
- ``OBSERVATION_INPUT_INVALID``
- ``OBSERVATION_INCONSISTENT`` (repeated parent-job reads inside one
  observation boundary disagree on durable identity — job_id/state/
  version — so the identity seen by the verdict cross-check cannot be
  proven equal to the projected observation; fail closed, never select)

Planner containment:
- ``PARENT_NODE_UNKNOWN`` / ``GRAPH_CYCLE`` /
  ``PARENT_COMPLETION_EVIDENCE_MISSING`` / ``WORKTREE_DIRTY`` /
  ``HEAD_DRIFT`` / ``LEASE_CONFLICT`` / ``PROVIDER_ADMISSION_STALE``
  (existing planner vocabulary, passed through unchanged)
- ``PLANNER_FAILED`` (defensive containment)

Outcome kinds: ``SELECTED`` | ``NOOP`` | ``RECONCILE`` | ``BLOCKED``.
"""
from __future__ import annotations

import pytest

from a_conductor.domain import RecoveryClassification, TaskState
from a_conductor.graph.domain import (
    DependencyType,
    TaskEdge,
    TaskGraph,
    TaskNode,
)
from a_conductor.graph.dispatch import GraphDispatchKey
from a_conductor.job_state import JobRuntimeState
from a_conductor.job_store import JobStoreError
from a_conductor.next_ready_continuation import (
    ContinuationGuards,
    NextReadyDecision,
    observe_next_ready_facts,
    plan_next_ready_continuation,
)
from a_conductor.verified_next_ready import (
    ParentCompletionVerdict,
    ParentCompletionVerdictKind,
    VerifiedNextReadyOutcomeKind,
    select_verified_next_ready,
)

GRAPH = "wo738-graph"
RUN = "wo738-run-1"
PARENT = "A"
CHILD = "B"
EVIDENCE = "closeout:complete:A:0f1e2d3c4b5a697887766554433221100f1e2d3c"
PARENT_VERSION = 7


# ---------------- fixture-owned fakes ----------------


class FakeJobs:
    """Fixture-owned read-only job observation port (get_job only)."""

    def __init__(self, jobs_by_id: dict[str, object]) -> None:
        self._jobs = dict(jobs_by_id)
        self._failures: dict[str, BaseException] = {}
        self.reads: list[str] = []

    def fail_read(self, job_id: str, exc: BaseException) -> None:
        self._failures[job_id] = exc

    def get_job(self, job_id: str):
        self.reads.append(job_id)
        if job_id in self._failures:
            raise self._failures[job_id]
        if job_id not in self._jobs:
            raise JobStoreError("JOB_NOT_FOUND")
        return self._jobs[job_id]


class FakeVerifier:
    """Fixture-owned authoritative completion-verification port."""

    def __init__(
        self,
        verdict: object | None = None,
        exc: BaseException | None = None,
    ) -> None:
        self._verdict = verdict
        self._exc = exc
        self.calls: list[dict[str, str]] = []

    def verify_parent_completion(
        self, *, graph_id: str, graph_run_id: str, node_id: str, job_id: str
    ):
        self.calls.append(
            {
                "graph_id": graph_id,
                "graph_run_id": graph_run_id,
                "node_id": node_id,
                "job_id": job_id,
            }
        )
        if self._exc is not None:
            raise self._exc
        return self._verdict


class NoopVerifier:
    """Port object without the verification method (invalid shape)."""


# ---------------- fixture builders ----------------


def _node(node_id: str, *, priority: int = 0) -> TaskNode:
    return TaskNode(
        id=node_id, objective=f"objective {node_id}", priority=priority
    )


def _chain_graph() -> TaskGraph:
    graph = TaskGraph()
    for node_id in (PARENT, CHILD):
        graph.add_node(_node(node_id))
    graph.add_edge(TaskEdge(PARENT, CHILD, DependencyType.ORDERING))
    return graph


def _fork_graph() -> TaskGraph:
    graph = TaskGraph()
    graph.add_node(_node(PARENT))
    for node_id in ("B1", "B2"):
        graph.add_node(_node(node_id))
    graph.add_node(_node("B3", priority=5))  # B3 outranks B1/B2 (priority 0)
    for child in ("B1", "B2", "B3"):
        graph.add_edge(TaskEdge(PARENT, child, DependencyType.ORDERING))
    return graph


def _cycle_graph() -> TaskGraph:
    graph = TaskGraph()
    for node_id in (PARENT, CHILD):
        graph.add_node(_node(node_id))
    graph.add_edge(TaskEdge(PARENT, CHILD, DependencyType.ORDERING))
    graph.add_edge(TaskEdge(CHILD, PARENT, DependencyType.ORDERING))
    return graph


def _guards(**over) -> ContinuationGuards:
    base = dict(
        worktree_clean=True,
        head_matches_expected=True,
        lease_available=True,
        provider_admission_fresh=True,
    )
    base.update(over)
    return ContinuationGuards(**base)


def _job(
    state: TaskState,
    node_id: str = PARENT,
    *,
    graph_id: str = GRAPH,
    run: str = RUN,
    version: int = PARENT_VERSION,
) -> JobRuntimeState:
    return JobRuntimeState(
        job_id=GraphDispatchKey(graph_id, run, node_id).job_id,
        work_order_ref="docs/work-orders/WO-P1-738-verified-next-ready.md",
        project_id="wo738-project",
        state=state,
        worker_id=None,
        attempt_count=0,
        max_attempts=3,
        recovery_classification=(
            RecoveryClassification.UNKNOWN
            if state is TaskState.RECOVERY_NEEDED
            else None
        ),
        version=version,
    )


def _verdict(
    kind: ParentCompletionVerdictKind = ParentCompletionVerdictKind.ACCEPTED,
    *,
    graph_id: str = GRAPH,
    run: str = RUN,
    node_id: str = PARENT,
    job_id: str | None = None,
    version: int = PARENT_VERSION,
    evidence: str | None = EVIDENCE,
    reason_code: str = "CLOSEOUT_ACCEPTED",
) -> ParentCompletionVerdict:
    if job_id is None:
        job_id = GraphDispatchKey(graph_id, run, node_id).job_id
    return ParentCompletionVerdict(
        kind=kind,
        reason_code=reason_code,
        graph_id=graph_id,
        graph_run_id=run,
        node_id=node_id,
        job_id=job_id,
        job_version=version,
        completion_evidence_ref=evidence,
    )


def _fixtures(
    *,
    graph: TaskGraph | None = None,
    parent_state: TaskState = TaskState.COMPLETE,
    parent_version: int = PARENT_VERSION,
    child_jobs: dict[str, TaskState | None] | None = None,
    jobs: FakeJobs | None = None,
    verifier: object | None = None,
    guards: ContinuationGuards | None = None,
):
    graph = graph if graph is not None else _chain_graph()
    if jobs is None:
        store: dict[str, object] = {
            GraphDispatchKey(GRAPH, RUN, PARENT).job_id: _job(
                parent_state, PARENT, version=parent_version
            )
        }
        child_states = child_jobs if child_jobs is not None else {CHILD: None}
        for node_id, state in child_states.items():
            if state is not None:
                store[GraphDispatchKey(GRAPH, RUN, node_id).job_id] = _job(
                    state, node_id
                )
        jobs = FakeJobs(store)
    if verifier is None:
        verifier = FakeVerifier(_verdict())
    return graph, jobs, verifier, guards or _guards()


def _select(
    *,
    graph: TaskGraph | None = None,
    parent_state: TaskState = TaskState.COMPLETE,
    parent_version: int = PARENT_VERSION,
    child_jobs: dict[str, TaskState | None] | None = None,
    jobs: FakeJobs | None = None,
    verifier: object | None = None,
    guards: ContinuationGuards | None = None,
    graph_id: str = GRAPH,
    graph_run_id: str = RUN,
    parent_node_id: str = PARENT,
):
    g, j, v, gd = _fixtures(
        graph=graph,
        parent_state=parent_state,
        parent_version=parent_version,
        child_jobs=child_jobs,
        jobs=jobs,
        verifier=verifier,
        guards=guards,
    )
    return select_verified_next_ready(
        jobs=j,
        completion_verifier=v,
        graph=g,
        graph_id=graph_id,
        graph_run_id=graph_run_id,
        parent_node_id=parent_node_id,
        guards=gd,
    )


def _planner_plan(graph: TaskGraph, child_states: dict[str, TaskState | None]):
    """Recompute the plan via the two verified seams for ordering equality."""
    from a_conductor.graph.ready import compute_ready_set
    from a_conductor.next_ready_continuation import (
        ParentCompletion,
        SuccessorObservation,
    )

    jobs = FakeJobs(
        {
            GraphDispatchKey(GRAPH, RUN, PARENT).job_id: _job(
                TaskState.COMPLETE, PARENT
            ),
            **{
                GraphDispatchKey(GRAPH, RUN, node_id).job_id: _job(state, node_id)
                for node_id, state in child_states.items()
                if state is not None
            },
        }
    )
    facts = observe_next_ready_facts(
        jobs=jobs,
        graph=graph,
        graph_id=GRAPH,
        graph_run_id=RUN,
        parent_node_id=PARENT,
        guards=_guards(),
        completion_ref=EVIDENCE,
    )
    return plan_next_ready_continuation(facts)


# ══════════════════════════════════════════════════════════════════════
# Happy path + ordering preservation
# ══════════════════════════════════════════════════════════════════════


def test_accepted_completion_selects_single_ready_successor() -> None:
    outcome = _select()
    assert outcome.kind is VerifiedNextReadyOutcomeKind.SELECTED
    assert outcome.selected_node_id == CHILD
    assert outcome.blocker_code is None
    assert outcome.planner_decision is NextReadyDecision.DISPATCH_ONE
    assert outcome.candidate_node_ids == (CHILD,)


def test_verifier_receives_derived_graph_dispatch_job_id() -> None:
    graph, jobs, verifier, guards = _fixtures()
    select_verified_next_ready(
        jobs=jobs,
        completion_verifier=verifier,
        graph=graph,
        graph_id=GRAPH,
        graph_run_id=RUN,
        parent_node_id=PARENT,
        guards=guards,
    )
    expected_job_id = GraphDispatchKey(GRAPH, RUN, PARENT).job_id
    assert verifier.calls == [
        {
            "graph_id": GRAPH,
            "graph_run_id": RUN,
            "node_id": PARENT,
            "job_id": expected_job_id,
        }
    ]


def test_fork_selection_preserves_planner_ordering() -> None:
    graph = _fork_graph()
    outcome = _select(graph=graph)
    plan = _planner_plan(graph, {"B1": None, "B2": None, "B3": None})
    assert plan.decision is NextReadyDecision.DISPATCH_ONE
    assert outcome.kind is VerifiedNextReadyOutcomeKind.SELECTED
    # exact planner ordering preserved: priority -> topo -> lexical id
    assert outcome.selected_node_id == plan.selected_node_id == "B3"
    assert outcome.candidate_node_ids == plan.candidate_node_ids
    assert outcome.represented_node_ids == plan.represented_node_ids == ()
    assert outcome.recovery_node_ids == plan.recovery_node_ids == ()
    # independent expectation: B3 has the highest priority
    assert outcome.candidate_node_ids[0] == "B3"


def test_equal_priority_fork_matches_planner_tiebreak() -> None:
    graph = TaskGraph()
    for node_id in (PARENT, "B1", "B2"):
        graph.add_node(_node(node_id))
    for child in ("B1", "B2"):
        graph.add_edge(TaskEdge(PARENT, child, DependencyType.ORDERING))
    outcome = _select(graph=graph)
    plan = _planner_plan(graph, {"B1": None, "B2": None})
    assert outcome.kind is VerifiedNextReadyOutcomeKind.SELECTED
    assert outcome.selected_node_id == plan.selected_node_id
    assert outcome.candidate_node_ids == plan.candidate_node_ids


# ══════════════════════════════════════════════════════════════════════
# §2.1 / §4 — forged, unbound, rejected, missing acceptance
# ══════════════════════════════════════════════════════════════════════


def test_forged_cross_job_verdict_blocked() -> None:
    forged = _verdict(job_id=GraphDispatchKey(GRAPH, RUN, CHILD).job_id)
    outcome = _select(verifier=FakeVerifier(forged))
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "COMPLETION_BINDING_JOB_MISMATCH"
    assert outcome.selected_node_id is None


def test_cross_graph_evidence_blocked() -> None:
    forged = _verdict(graph_id="other-graph")
    outcome = _select(verifier=FakeVerifier(forged))
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "COMPLETION_BINDING_GRAPH_MISMATCH"


def test_cross_run_evidence_blocked() -> None:
    forged = _verdict(run="wo738-run-2")
    outcome = _select(verifier=FakeVerifier(forged))
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "COMPLETION_BINDING_RUN_MISMATCH"


def test_cross_node_evidence_blocked() -> None:
    forged = _verdict(node_id=CHILD)
    outcome = _select(verifier=FakeVerifier(forged))
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "COMPLETION_BINDING_NODE_MISMATCH"


def test_cross_version_stale_evidence_blocked() -> None:
    stale = _verdict(version=PARENT_VERSION - 1)
    outcome = _select(verifier=FakeVerifier(stale))
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "COMPLETION_VERSION_MISMATCH"
    assert outcome.selected_node_id is None


def test_rejected_acceptance_blocked() -> None:
    rejected = _verdict(
        kind=ParentCompletionVerdictKind.REJECTED, reason_code="CLOSEOUT_REJECTED"
    )
    outcome = _select(verifier=FakeVerifier(rejected))
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "COMPLETION_VERDICT_REJECTED"
    assert outcome.selected_node_id is None
    assert "CLOSEOUT_REJECTED" in outcome.detail


def test_missing_acceptance_blocked() -> None:
    outcome = _select(verifier=FakeVerifier(None))
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "COMPLETION_VERDICT_MISSING"
    assert outcome.selected_node_id is None


def test_accepted_verdict_without_completion_evidence_blocked() -> None:
    no_evidence = _verdict(evidence=None)
    outcome = _select(verifier=FakeVerifier(no_evidence))
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "COMPLETION_VERDICT_EVIDENCE_MISSING"


def test_malformed_verdict_object_blocked() -> None:
    outcome = _select(verifier=FakeVerifier(object()))
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "COMPLETION_VERDICT_MALFORMED"


def test_malformed_verdict_scalar_blocked() -> None:
    outcome = _select(verifier=FakeVerifier("ACCEPTED"))
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "COMPLETION_VERDICT_MALFORMED"


def test_verifier_port_failure_contained() -> None:
    outcome = _select(
        verifier=FakeVerifier(exc=RuntimeError("secret-payload-leak"))
    )
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "COMPLETION_VERIFIER_FAILED"
    # bounded containment: type name only, never payloads
    assert "secret-payload-leak" not in outcome.detail


def test_accepted_verdict_conflicting_with_durable_state_blocked() -> None:
    # verifier accepts completion but the durable parent job is EXECUTING:
    # conflicting evidence must block, never silently no-op
    outcome = _select(parent_state=TaskState.EXECUTING)
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "COMPLETION_STATE_CONFLICT"
    assert outcome.selected_node_id is None


# ══════════════════════════════════════════════════════════════════════
# §2.3 / §4 — partial, conflicting, malformed observation reads
# ══════════════════════════════════════════════════════════════════════


def test_partial_successor_read_blocked_not_noop() -> None:
    graph, jobs, verifier, guards = _fixtures()
    jobs.fail_read(
        GraphDispatchKey(GRAPH, RUN, CHILD).job_id,
        JobStoreError("JOB_STORE_UNAVAILABLE"),
    )
    outcome = select_verified_next_ready(
        jobs=jobs,
        completion_verifier=verifier,
        graph=graph,
        graph_id=GRAPH,
        graph_run_id=RUN,
        parent_node_id=PARENT,
        guards=guards,
    )
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "OBSERVATION_READ_FAILED"
    assert outcome.planner_decision is None


def test_malformed_successor_job_blocked() -> None:
    graph = _chain_graph()
    store = {
        GraphDispatchKey(GRAPH, RUN, PARENT).job_id: _job(TaskState.COMPLETE),
        GraphDispatchKey(GRAPH, RUN, CHILD).job_id: object(),  # malformed
    }
    outcome = _select(
        graph=graph, jobs=FakeJobs(store), verifier=FakeVerifier(_verdict())
    )
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "GRAPH_JOB_INVALID"
    assert outcome.selected_node_id is None


def test_malformed_parent_job_blocked() -> None:
    store = {GraphDispatchKey(GRAPH, RUN, PARENT).job_id: "not-a-job"}
    outcome = _select(
        jobs=FakeJobs(store), verifier=FakeVerifier(_verdict())
    )
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "PARENT_JOB_INVALID"


def test_parent_job_identity_mismatch_blocked() -> None:
    rotated = _job(TaskState.COMPLETE, CHILD)  # wrong job under parent key
    store = {GraphDispatchKey(GRAPH, RUN, PARENT).job_id: rotated}
    outcome = _select(
        jobs=FakeJobs(store), verifier=FakeVerifier(_verdict())
    )
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "PARENT_JOB_IDENTITY_MISMATCH"


def test_parent_job_missing_blocked() -> None:
    outcome = _select(jobs=FakeJobs({}))
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "PARENT_JOB_NOT_FOUND"


def test_jobs_port_unexpected_exception_contained() -> None:
    graph, jobs, verifier, guards = _fixtures()
    jobs.fail_read(
        GraphDispatchKey(GRAPH, RUN, PARENT).job_id,
        RuntimeError("driver-explosion"),
    )
    outcome = select_verified_next_ready(
        jobs=jobs,
        completion_verifier=verifier,
        graph=graph,
        graph_id=GRAPH,
        graph_run_id=RUN,
        parent_node_id=PARENT,
        guards=guards,
    )
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "OBSERVATION_READ_FAILED"
    assert "driver-explosion" not in outcome.detail


def test_jobs_port_invalid_blocked() -> None:
    outcome = _select(jobs=object())
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "VERIFIED_NEXT_READY_JOBS_PORT_INVALID"


def test_verifier_port_invalid_blocked() -> None:
    outcome = _select(verifier=NoopVerifier())
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "VERIFIED_NEXT_READY_VERIFIER_PORT_INVALID"


def test_malformed_caller_inputs_blocked() -> None:
    # the seam is total: malformed scalar inputs are contained into typed
    # blockers, never raw exceptions
    for bad_kwargs in (
        {"graph_id": 123},
        {"graph_run_id": None},
        {"parent_node_id": ""},
    ):
        outcome = _select(**bad_kwargs)
        assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
        assert outcome.blocker_code == "VERIFIED_NEXT_READY_INPUT_INVALID"
    graph, jobs, verifier, guards = _fixtures()
    outcome = select_verified_next_ready(
        jobs=jobs,
        completion_verifier=verifier,
        graph="not-a-graph",
        graph_id=GRAPH,
        graph_run_id=RUN,
        parent_node_id=PARENT,
        guards=guards,
    )
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "VERIFIED_NEXT_READY_INPUT_INVALID"
    outcome = select_verified_next_ready(
        jobs=jobs,
        completion_verifier=verifier,
        graph=graph,
        graph_id=GRAPH,
        graph_run_id=RUN,
        parent_node_id=PARENT,
        guards="not-guards",
    )
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "VERIFIED_NEXT_READY_INPUT_INVALID"


# ══════════════════════════════════════════════════════════════════════
# §2.4 / §4 — already-represented successor / uncertain prior dispatch
# ══════════════════════════════════════════════════════════════════════


def test_already_represented_successor_explicit_noop() -> None:
    outcome = _select(child_jobs={CHILD: TaskState.READY})
    assert outcome.kind is VerifiedNextReadyOutcomeKind.NOOP
    assert outcome.planner_decision is NextReadyDecision.NOOP_ALL_REPRESENTED
    assert outcome.selected_node_id is None
    assert outcome.blocker_code is None
    assert outcome.represented_node_ids == (CHILD,)


def test_uncertain_prior_dispatch_explicit_reconcile() -> None:
    outcome = _select(child_jobs={CHILD: TaskState.RECOVERY_NEEDED})
    assert outcome.kind is VerifiedNextReadyOutcomeKind.RECONCILE
    assert outcome.planner_decision is NextReadyDecision.RECONCILE_RECOVERY
    assert outcome.selected_node_id is None
    assert outcome.blocker_code is None
    assert outcome.recovery_node_ids == (CHILD,)


# ══════════════════════════════════════════════════════════════════════
# §2.5 / §4 — guards, ambiguity, cycle, stale guards
# ══════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    ("guard_kwargs", "expected_code"),
    [
        ({"worktree_clean": False}, "WORKTREE_DIRTY"),
        ({"head_matches_expected": False}, "HEAD_DRIFT"),
        ({"lease_available": False}, "LEASE_CONFLICT"),
        ({"provider_admission_fresh": False}, "PROVIDER_ADMISSION_STALE"),
    ],
)
def test_guard_failures_blocked_with_exact_codes(
    guard_kwargs: dict, expected_code: str
) -> None:
    outcome = _select(guards=_guards(**guard_kwargs))
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == expected_code
    assert outcome.selected_node_id is None


def test_parent_node_unknown_structural_ambiguity_blocked() -> None:
    # durable job + verdict exist for the requested identity, but the graph
    # has no such node: the planner fails typed on structural ambiguity
    unknown_id = "Z-unknown"
    unknown_key = GraphDispatchKey(GRAPH, RUN, unknown_id)
    store = {
        unknown_key.job_id: _job(TaskState.COMPLETE, unknown_id),
    }
    verdict = _verdict(node_id=unknown_id, job_id=unknown_key.job_id)
    outcome = _select(
        jobs=FakeJobs(store),
        verifier=FakeVerifier(verdict),
        parent_node_id=unknown_id,
    )
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "PARENT_NODE_UNKNOWN"


def test_graph_cycle_blocked() -> None:
    outcome = _select(graph=_cycle_graph())
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "GRAPH_CYCLE"


# ══════════════════════════════════════════════════════════════════════
# Restart / re-read stability
# ══════════════════════════════════════════════════════════════════════


def test_restart_reread_stability_identical_outcome() -> None:
    first = _select(child_jobs={CHILD: TaskState.READY})
    second = _select(child_jobs={CHILD: TaskState.READY})
    assert first == second
    # simulated restart: fresh fixtures rebuilt from the same durable truth
    fresh_graph = _chain_graph()
    fresh_jobs = FakeJobs(
        {
            GraphDispatchKey(GRAPH, RUN, PARENT).job_id: _job(
                TaskState.COMPLETE
            ),
            GraphDispatchKey(GRAPH, RUN, CHILD).job_id: _job(
                TaskState.READY, CHILD
            ),
        }
    )
    fresh = select_verified_next_ready(
        jobs=fresh_jobs,
        completion_verifier=FakeVerifier(_verdict()),
        graph=fresh_graph,
        graph_id=GRAPH,
        graph_run_id=RUN,
        parent_node_id=PARENT,
        guards=_guards(),
    )
    assert fresh == first
    # and for a blocker: identical stale verdict keeps blocking identically
    stale_first = _select(verifier=FakeVerifier(_verdict(version=1)))
    stale_second = _select(verifier=FakeVerifier(_verdict(version=1)))
    assert stale_first == stale_second


def test_read_only_no_mutation_of_fixture_ports() -> None:
    graph, jobs, verifier, guards = _fixtures()
    select_verified_next_ready(
        jobs=jobs,
        completion_verifier=verifier,
        graph=graph,
        graph_id=GRAPH,
        graph_run_id=RUN,
        parent_node_id=PARENT,
        guards=guards,
    )
    # the only verifier interaction is the single verification read
    assert len(verifier.calls) == 1
    # the only job interaction is bounded read-only get_job calls
    expected_parent_job_id = GraphDispatchKey(GRAPH, RUN, PARENT).job_id
    expected_child_job_id = GraphDispatchKey(GRAPH, RUN, CHILD).job_id
    assert set(jobs.reads) == {expected_parent_job_id, expected_child_job_id}


# ══════════════════════════════════════════════════════════════════════
# Round-1 P1 repair RED matrix (independent review findings)
# ══════════════════════════════════════════════════════════════════════


class ConflictingParentJobs:
    """Parent identity flips between repeated reads inside one boundary.

    ``observe_next_ready_facts`` reads the parent job TWICE: once for
    ``facts.parent`` (read 1: COMPLETE v7) and again during graph-state
    projection (read 2: COMPLETE v8). Each read is individually valid, so
    only a boundary-level consistency check can detect the conflict; a
    verdict bound to v7 currently passes the version cross-check against
    read 1 while the projected observation saw v8.
    """

    def __init__(self, parent_job_id: str) -> None:
        self._parent_job_id = parent_job_id
        self.parent_read_versions: list[int] = []

    def get_job(self, job_id: str):
        if job_id == self._parent_job_id:
            version = 7 if not self.parent_read_versions else 8
            self.parent_read_versions.append(version)
            return _job(TaskState.COMPLETE, PARENT, version=version)
        raise JobStoreError("JOB_NOT_FOUND")


class RefreshingParentJobs:
    """Control: repeated parent reads with EQUAL durable identity.

    Every parent read returns a fresh but identical (COMPLETE v7) job
    object; repeated consistent observations must still select.
    """

    def __init__(self, parent_job_id: str) -> None:
        self._parent_job_id = parent_job_id

    def get_job(self, job_id: str):
        if job_id == self._parent_job_id:
            return _job(TaskState.COMPLETE, PARENT)
        raise JobStoreError("JOB_NOT_FOUND")


def test_conflicting_parent_reads_blocked_not_selected() -> None:
    # Finding 1: read 1 = COMPLETE v7 (facts.parent), read 2 = COMPLETE v8
    # (projection); the verdict binds v7 and passes the version cross-check
    # against read 1 only. Conflicting repeated parent observations must
    # fail closed with a typed blocker, never select.
    parent_job_id = GraphDispatchKey(GRAPH, RUN, PARENT).job_id
    jobs = ConflictingParentJobs(parent_job_id)
    outcome = select_verified_next_ready(
        jobs=jobs,
        completion_verifier=FakeVerifier(_verdict()),
        graph=_chain_graph(),
        graph_id=GRAPH,
        graph_run_id=RUN,
        parent_node_id=PARENT,
        guards=_guards(),
    )
    assert jobs.parent_read_versions == [7, 8]  # double-read boundary proven
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "OBSERVATION_INCONSISTENT"
    assert outcome.selected_node_id is None
    assert outcome.planner_decision is None


def test_consistent_repeated_parent_reads_still_select() -> None:
    # positive control: repeated reads with equal durable identity (fresh
    # objects) must NOT trip the inconsistency gate
    parent_job_id = GraphDispatchKey(GRAPH, RUN, PARENT).job_id
    outcome = select_verified_next_ready(
        jobs=RefreshingParentJobs(parent_job_id),
        completion_verifier=FakeVerifier(_verdict()),
        graph=_chain_graph(),
        graph_id=GRAPH,
        graph_run_id=RUN,
        parent_node_id=PARENT,
        guards=_guards(),
    )
    assert outcome.kind is VerifiedNextReadyOutcomeKind.SELECTED
    assert outcome.selected_node_id == CHILD
    assert outcome.blocker_code is None


class _ExplodingAttrPort:
    """Port whose every attribute access raises a non-AttributeError.

    ``getattr(port, "method", None)`` only suppresses AttributeError, so a
    port whose ``__getattribute__`` raises escapes raw today.
    """

    def __getattribute__(self, name: str):
        raise RuntimeError("port-attr-explosion")


class _RaisingVerdict(ParentCompletionVerdict):
    """Verdict-shaped object whose field access raises on every read."""

    def __getattribute__(self, name: str):
        raise RuntimeError("verdict-attr-explosion")


def test_uninitialized_verdict_blocked_not_raw() -> None:
    # Finding 2: isinstance passes for an uninitialized slots dataclass,
    # but verdict.kind raises AttributeError outside containment today.
    ghost = object.__new__(ParentCompletionVerdict)
    outcome = _select(verifier=FakeVerifier(ghost))
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "COMPLETION_VERDICT_INVALID"
    assert outcome.selected_node_id is None


def test_verdict_attribute_access_raising_blocked_not_raw() -> None:
    # Finding 2: verdict object whose field inspection raises; contained
    # with a stable typed code, bounded detail (type name only).
    outcome = _select(verifier=FakeVerifier(object.__new__(_RaisingVerdict)))
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "COMPLETION_VERDICT_INVALID"
    assert outcome.selected_node_id is None
    assert "verdict-attr-explosion" not in outcome.detail


def test_jobs_port_attribute_access_raising_contained() -> None:
    # Finding 2: jobs port whose get_job attribute raises on access; must
    # mirror the port-failure containment, never escape raw.
    outcome = _select(jobs=_ExplodingAttrPort())
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == (
        "VERIFIED_NEXT_READY_JOBS_PORT_INSPECTION_FAILED"
    )
    assert outcome.selected_node_id is None
    assert "port-attr-explosion" not in outcome.detail


def test_verifier_port_attribute_access_raising_contained() -> None:
    # Finding 2: verifier port whose method attribute raises on access.
    outcome = _select(verifier=_ExplodingAttrPort())
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == (
        "VERIFIED_NEXT_READY_VERIFIER_PORT_INSPECTION_FAILED"
    )
    assert outcome.selected_node_id is None
    assert "port-attr-explosion" not in outcome.detail


# ══════════════════════════════════════════════════════════════════════
# Hostile verdict objects: mutating kind, raising/lying comparators
# ══════════════════════════════════════════════════════════════════════


class TestHostileVerdictObjects:
    """RED matrix for hostile port-returned verdict objects.

    The completion verdict is attacker-influenceable data crossing the
    verification-port boundary: its ``kind`` can mutate between reads, and
    its binding fields can carry ``str`` subclasses whose comparison
    operators raise or lie. Every hostile shape must fail closed into a
    typed blocker; the seam itself must return, never raise raw.
    """

    _COMPLETION_VERDICT_BLOCKER_CODES = frozenset(
        {
            "COMPLETION_VERDICT_MISSING",
            "COMPLETION_VERDICT_INVALID",
            "COMPLETION_VERDICT_MALFORMED",
            "COMPLETION_VERDICT_REJECTED",
            "COMPLETION_VERDICT_EVIDENCE_MISSING",
        }
    )
    _EXISTING_BLOCKER_CODES = frozenset(
        {
            "VERIFIED_NEXT_READY_INPUT_INVALID",
            "VERIFIED_NEXT_READY_JOBS_PORT_INVALID",
            "VERIFIED_NEXT_READY_VERIFIER_PORT_INVALID",
            "VERIFIED_NEXT_READY_JOBS_PORT_INSPECTION_FAILED",
            "VERIFIED_NEXT_READY_VERIFIER_PORT_INSPECTION_FAILED",
            "COMPLETION_VERDICT_MISSING",
            "COMPLETION_VERDICT_INVALID",
            "COMPLETION_VERDICT_MALFORMED",
            "COMPLETION_VERDICT_REJECTED",
            "COMPLETION_VERDICT_EVIDENCE_MISSING",
            "COMPLETION_VERIFIER_FAILED",
            "COMPLETION_BINDING_GRAPH_MISMATCH",
            "COMPLETION_BINDING_RUN_MISMATCH",
            "COMPLETION_BINDING_NODE_MISMATCH",
            "COMPLETION_BINDING_JOB_MISMATCH",
            "COMPLETION_VERSION_MISMATCH",
            "COMPLETION_STATE_CONFLICT",
            "PARENT_JOB_NOT_FOUND",
            "PARENT_JOB_INVALID",
            "PARENT_JOB_IDENTITY_MISMATCH",
            "GRAPH_JOB_INVALID",
            "GRAPH_JOB_IDENTITY_MISMATCH",
            "OBSERVATION_READ_FAILED",
            "OBSERVATION_INPUT_INVALID",
            "OBSERVATION_INCONSISTENT",
            "PARENT_NODE_UNKNOWN",
            "GRAPH_CYCLE",
            "PARENT_COMPLETION_EVIDENCE_MISSING",
            "WORKTREE_DIRTY",
            "HEAD_DRIFT",
            "LEASE_CONFLICT",
            "PROVIDER_ADMISSION_STALE",
            "PLANNER_FAILED",
        }
    )

    class _KindFlippingVerdict(ParentCompletionVerdict):
        """``kind`` reads ACCEPTED on the first access, INVALID after."""

        def __init__(self, base: ParentCompletionVerdict) -> None:
            object.__setattr__(self, "_kind_reads", 0)
            for name in (
                "reason_code",
                "graph_id",
                "graph_run_id",
                "node_id",
                "job_id",
                "job_version",
                "completion_evidence_ref",
            ):
                object.__setattr__(self, name, getattr(base, name))
            ParentCompletionVerdict.kind.__set__(self, base.kind)

        @property
        def kind(self):
            reads = object.__getattribute__(self, "_kind_reads") + 1
            object.__setattr__(self, "_kind_reads", reads)
            if reads == 1:
                return ParentCompletionVerdictKind.ACCEPTED
            return "INVALID"

    def _kind_flipping_verdict(self) -> ParentCompletionVerdict:
        return self._KindFlippingVerdict(_verdict())

    class _RaisingCompareStr(str):
        """Detonating comparator: ``==``/``!=`` raise RuntimeError."""

        def __eq__(self, other: object) -> bool:
            raise RuntimeError("eq-explosion")

        def __ne__(self, other: object) -> bool:
            raise RuntimeError("ne-explosion")

    class _LyingCompareStr(str):
        """Lying comparator: ``==`` always False, ``!=`` always True."""

        def __eq__(self, other: object) -> bool:
            return False

        def __ne__(self, other: object) -> bool:
            return True

    def test_kind_shapeshifter_presenting_accepted_at_ingress_is_consumed_as_presented(
        self,
    ) -> None:
        # PINNED-EXPECTATION ADJUSTMENT (adjudicated ingress contract):
        # previously `test_verdict_kind_changes_on_second_read_blocked`
        # expected BLOCKED because the old code validated one read of
        # ``kind`` and later re-read it (validated-then-reread TOCTOU).
        # Under the final ingress the boundary extracts each verdict field
        # EXACTLY ONCE, so cross-read mutation is undetectable by contract:
        # a shapeshifter that presents the trusted ACCEPTED enum member at
        # the single ingress read is consumed exactly as a genuine ACCEPTED
        # verdict. The fail-closed direction (REJECTED presented first) is
        # pinned by
        # ``test_rejected_then_accepted_shapeshifter_kind_fails_closed``.
        flipper = self._kind_flipping_verdict()
        outcome = _select(verifier=FakeVerifier(flipper))
        assert outcome.kind is VerifiedNextReadyOutcomeKind.SELECTED
        assert outcome.selected_node_id == CHILD
        assert outcome.blocker_code is None
        # exactly-once evidence: kind was read once, at the ingress
        assert (
            object.__getattribute__(flipper, "_kind_reads") == 1
        )

    def test_raising_comparison_subclass_blocked_not_raw(self) -> None:
        # Finding 4: a binding field can carry a str subclass whose
        # comparison operators raise; the binding ``!=`` checks run outside
        # the extraction containment today, so a raw RuntimeError escapes.
        # The seam is total: it must return a typed BLOCKED outcome
        # instead, never propagate raw.
        hostile = self._RaisingCompareStr(GRAPH)
        try:
            outcome = _select(
                verifier=FakeVerifier(
                    _verdict(
                        graph_id=hostile,
                        job_id=GraphDispatchKey(GRAPH, RUN, PARENT).job_id,
                    )
                )
            )
        except RuntimeError as exc:
            pytest.fail(f"raw RuntimeError escaped the seam boundary: {exc}")
        assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
        assert outcome.blocker_code in self._EXISTING_BLOCKER_CODES
        assert outcome.selected_node_id is None

    def test_liar_eq_cannot_bypass_binding(self) -> None:
        # Finding 5: a comparator that swears every field is unequal
        # (== always False, != always True) must land in the exact identity
        # binding-mismatch blocker; lying equality semantics can never
        # launder a selection through the binding cross-check.
        liar = self._LyingCompareStr(GRAPH)
        outcome = _select(
            verifier=FakeVerifier(
                _verdict(
                    graph_id=liar,
                    job_id=GraphDispatchKey(GRAPH, RUN, PARENT).job_id,
                )
            )
        )
        assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
        assert outcome.blocker_code == "COMPLETION_BINDING_GRAPH_MISMATCH"
        assert outcome.selected_node_id is None


# ══════════════════════════════════════════════════════════════════════
# Final structural ingress repair (adjudicated ingress contract) matrix
#
# Contract under test:
# 1. ONE guarded ingress boundary BEFORE any validation/comparison/
#    formatting/selection; each required verdict field AND caller input
#    field is extracted exactly once.
# 2. Strings accepted ONLY when type(value) is str (no subclasses, no
#    coercion).
# 3. Integers ONLY when type(value) is int (bool + subclasses rejected)
#    BEFORE any range check/comparison.
# 4. Enum kind ONLY by identity against the explicitly allowed trusted
#    members (no equality comparisons, no coercion, no isinstance trust).
# 5. BOTH sides of every binding AND the rejected-verdict reason_code are
#    normalized at that boundary; invalid input or extraction failure is a
#    contained fail-closed typed result.
# 6. Downstream uses ONLY normalized plain values: no foreign methods, no
#    overridden comparisons, no implicit coercion, no repeated field reads.
# ══════════════════════════════════════════════════════════════════════


def _forged_verdict(**overrides) -> ParentCompletionVerdict:
    """Build a verdict-shaped ParentCompletionVerdict bypassing the
    constructor validation (slot writes, no __post_init__), so hostile
    field values can be placed behind the ingress boundary."""
    fields: dict[str, object] = {
        "kind": ParentCompletionVerdictKind.ACCEPTED,
        "reason_code": "CLOSEOUT_ACCEPTED",
        "graph_id": GRAPH,
        "graph_run_id": RUN,
        "node_id": PARENT,
        "job_id": GraphDispatchKey(GRAPH, RUN, PARENT).job_id,
        "job_version": PARENT_VERSION,
        "completion_evidence_ref": EVIDENCE,
    }
    fields.update(overrides)
    forged = object.__new__(ParentCompletionVerdict)
    for name, value in fields.items():
        object.__setattr__(forged, name, value)
    return forged


class _RejThenAccKindVerdict(ParentCompletionVerdict):
    """Shapeshifter kind: REJECTED on the FIRST access, ACCEPTED after.

    The old validate-then-reread boundary read ``kind`` once during
    validation (ignoring its value) and once more at extraction, so this
    verdict laundered a REJECTED presentation into an ACCEPTED selection.
    """

    def __init__(self, base: ParentCompletionVerdict) -> None:
        object.__setattr__(self, "_kind_reads", 0)
        for name in (
            "reason_code",
            "graph_id",
            "graph_run_id",
            "node_id",
            "job_id",
            "job_version",
            "completion_evidence_ref",
        ):
            object.__setattr__(self, name, getattr(base, name))
        ParentCompletionVerdict.kind.__set__(self, base.kind)

    @property
    def kind(self):
        reads = object.__getattribute__(self, "_kind_reads") + 1
        object.__setattr__(self, "_kind_reads", reads)
        if reads == 1:
            return ParentCompletionVerdictKind.REJECTED
        return ParentCompletionVerdictKind.ACCEPTED


class _LaunderingNeCallerId(str):
    """Caller-side id subclass: reflected ==/!= always claim EQUAL."""

    eq_invocations = 0
    ne_invocations = 0

    def __eq__(self, other: object) -> bool:
        type(self).eq_invocations += 1
        return False

    def __ne__(self, other: object) -> bool:
        type(self).ne_invocations += 1
        return False


class _RaisingNeCallerId(str):
    """Caller-side id subclass: reflected ==/!= detonate."""

    invocations = 0

    def __eq__(self, other: object) -> bool:
        type(self).invocations += 1
        raise RuntimeError("caller-ne-explosion")

    def __ne__(self, other: object) -> bool:
        type(self).invocations += 1
        raise RuntimeError("caller-ne-explosion")


class _ExplodingReplaceStr(str):
    """Reason-code subclass whose .replace() detonates (hostile payload)."""

    invocations = 0

    def replace(self, *args: object, **kwargs: object) -> str:
        type(self).invocations += 1
        raise RuntimeError("replace-explosion")


class _ExplodingLtInt(int):
    """Version subclass whose < comparator detonates."""

    invocations = 0

    def __lt__(self, other: object) -> bool:
        type(self).invocations += 1
        raise RuntimeError("lt-explosion")


def _counting_prop(name: str) -> property:
    """Read-counting property shadowing one verdict slot descriptor."""
    slot = ParentCompletionVerdict.__dict__[name]

    def prop(self):
        reads = dict(object.__getattribute__(self, "_reads"))
        reads[name] = reads.get(name, 0) + 1
        object.__setattr__(self, "_reads", reads)
        return slot.__get__(self)

    return property(prop)


class _CountingVerdict(ParentCompletionVerdict):
    """Fully valid verdict that records exactly how often each field is
    attribute-read by the consumer boundary."""

    def __init__(self, base: ParentCompletionVerdict) -> None:
        object.__setattr__(self, "_reads", {})
        for name in (
            "kind",
            "reason_code",
            "graph_id",
            "graph_run_id",
            "node_id",
            "job_id",
            "job_version",
            "completion_evidence_ref",
        ):
            ParentCompletionVerdict.__dict__[name].__set__(
                self, getattr(base, name)
            )

    kind = _counting_prop("kind")
    reason_code = _counting_prop("reason_code")
    graph_id = _counting_prop("graph_id")
    graph_run_id = _counting_prop("graph_run_id")
    node_id = _counting_prop("node_id")
    job_id = _counting_prop("job_id")
    job_version = _counting_prop("job_version")
    completion_evidence_ref = _counting_prop("completion_evidence_ref")


class _MidExtractionRaisingVerdict(ParentCompletionVerdict):
    """kind/reason extract fine; graph_id attribute access detonates."""

    def __init__(self, base: ParentCompletionVerdict) -> None:
        ParentCompletionVerdict.kind.__set__(self, base.kind)
        ParentCompletionVerdict.reason_code.__set__(self, base.reason_code)
        # graph_id onward deliberately left uninitialized

    @property
    def graph_id(self):
        raise RuntimeError("mid-extraction-explosion")


class TestIngressNormalization:
    """RED/GREEN matrix for the adjudicated single-ingress contract."""

    def test_rejected_then_accepted_shapeshifter_kind_fails_closed(self) -> None:
        # Reproduced defect 1 (validated-then-reread TOCTOU): a shapeshifter
        # that presents REJECTED to validation and ACCEPTED to the
        # extraction re-read currently launders a REJECTED verdict into a
        # SELECTION. Under the exactly-once ingress the single extracted
        # kind is REJECTED, so the verdict fails closed as
        # COMPLETION_VERDICT_REJECTED — never a successor.
        shapeshifter = _RejThenAccKindVerdict(_verdict())
        outcome = _select(verifier=FakeVerifier(shapeshifter))
        assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
        assert outcome.blocker_code == "COMPLETION_VERDICT_REJECTED"
        assert outcome.selected_node_id is None
        assert outcome.planner_decision is None
        # exactly-once evidence: kind was read once, at the ingress
        assert object.__getattribute__(shapeshifter, "_kind_reads") == 1

    def test_caller_reflected_ne_subclass_laundering_rejected_at_ingress(
        self,
    ) -> None:
        # Reproduced defect 2 (reflected __ne__ laundering): a caller-side
        # graph id admitted via isinstance(str) can be a str subclass whose
        # reflected __ne__ always claims EQUAL, laundering a cross-graph
        # binding mismatch into a match (and even a selection) through
        # plain != subclass. The ingress must accept strings only when
        # type(value) is str and reject this input before any comparison
        # (comparator never invoked, verifier never consulted).
        caller_graph_id = _LaunderingNeCallerId(GRAPH)
        expected_job_id = GraphDispatchKey(GRAPH, RUN, PARENT).job_id
        forged = _verdict(graph_id="other-graph", job_id=expected_job_id)
        outcome = _select(
            verifier=FakeVerifier(forged), graph_id=caller_graph_id
        )
        assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
        assert outcome.blocker_code == "VERIFIED_NEXT_READY_INPUT_INVALID"
        assert outcome.selected_node_id is None
        # fail closed BEFORE any comparison/formatting/verification
        assert _LaunderingNeCallerId.eq_invocations == 0
        assert _LaunderingNeCallerId.ne_invocations == 0

    def test_caller_raising_ne_subclass_rejected_at_ingress(self) -> None:
        # Companion to defect 2: a caller-side id subclass whose reflected
        # comparators detonate must be rejected at the ingress, never
        # invoked during any binding comparison and never converted into a
        # downstream verdict-containment code.
        caller_graph_id = _RaisingNeCallerId(GRAPH)
        outcome = _select(
            verifier=FakeVerifier(_verdict()), graph_id=caller_graph_id
        )
        assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
        assert outcome.blocker_code == "VERIFIED_NEXT_READY_INPUT_INVALID"
        assert outcome.selected_node_id is None
        assert _RaisingNeCallerId.invocations == 0
        assert "caller-ne-explosion" not in outcome.detail

    def test_hostile_reason_code_replace_never_invoked(self) -> None:
        # Reproduced defect 3 (raw RuntimeError escape): a REJECTED verdict
        # whose reason_code is a str subclass with a detonating .replace()
        # escapes the seam RAW today because the bounded reason-code
        # formatting runs outside containment on an un-normalized value.
        # The ingress must normalize the reason_code (exact plain str only)
        # BEFORE the rejected-branch formatting, fail closed typed, and
        # never invoke .replace().
        hostile_reason = _ExplodingReplaceStr("CLOSEOUT_REJECTED")
        rejected = _verdict(
            kind=ParentCompletionVerdictKind.REJECTED,
            reason_code=hostile_reason,
        )
        try:
            outcome = _select(verifier=FakeVerifier(rejected))
        except RuntimeError as exc:
            pytest.fail(f"raw RuntimeError escaped the seam boundary: {exc}")
        assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
        assert outcome.blocker_code == "COMPLETION_VERDICT_MALFORMED"
        assert outcome.selected_node_id is None
        assert outcome.planner_decision is None
        assert _ExplodingReplaceStr.invocations == 0
        assert "replace-explosion" not in outcome.detail

    def test_int_subclass_comparator_not_invoked_before_exact_int_gate(
        self,
    ) -> None:
        # Reproduced defect 1b: job_version is range-compared (< 1) during
        # validation BEFORE any exact-int gate, so an int subclass with an
        # overridden comparator has its operator invoked on un-normalized
        # attacker data and its failure lands in the wrong typed code. The
        # ingress must gate type(value) is int first, reject the subclass
        # as COMPLETION_VERDICT_MALFORMED, and never invoke __lt__.
        hostile_version = _ExplodingLtInt(PARENT_VERSION)
        forged = _forged_verdict(job_version=hostile_version)
        try:
            outcome = _select(verifier=FakeVerifier(forged))
        except RuntimeError as exc:
            pytest.fail(f"raw comparator exception escaped the seam: {exc}")
        assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
        assert outcome.blocker_code == "COMPLETION_VERDICT_MALFORMED"
        assert outcome.selected_node_id is None
        assert _ExplodingLtInt.invocations == 0
        assert "lt-explosion" not in outcome.detail

    def test_bool_job_version_fails_closed_as_malformed(self) -> None:
        # exact-int gate rejects bool (type(True) is not int) BEFORE any
        # range comparison.
        forged = _forged_verdict(job_version=True)
        outcome = _select(verifier=FakeVerifier(forged))
        assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
        assert outcome.blocker_code == "COMPLETION_VERDICT_MALFORMED"
        assert outcome.selected_node_id is None

    def test_invalid_enum_kind_plain_string_fails_closed(self) -> None:
        # enum kind is accepted ONLY by identity against the trusted
        # members: a plain "ACCEPTED" string (or any foreign object) is
        # COMPLETION_VERDICT_MALFORMED, never compared or coerced.
        forged = _forged_verdict(kind="ACCEPTED")
        outcome = _select(verifier=FakeVerifier(forged))
        assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
        assert outcome.blocker_code == "COMPLETION_VERDICT_MALFORMED"
        assert outcome.selected_node_id is None

    def test_mid_extraction_field_failure_contained(self) -> None:
        # failing field extraction mid-way through the single guarded
        # extraction is contained as COMPLETION_VERDICT_INVALID (type name
        # only), never raw.
        outcome = _select(
            verifier=FakeVerifier(
                _MidExtractionRaisingVerdict(_verdict())
            )
        )
        assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
        assert outcome.blocker_code == "COMPLETION_VERDICT_INVALID"
        assert outcome.selected_node_id is None
        assert "mid-extraction-explosion" not in outcome.detail

    def test_verdict_fields_extracted_exactly_once_at_ingress(self) -> None:
        # the whole fully-valid verdict must be attribute-read exactly once
        # per field at the ingress and never touched again downstream.
        counting = _CountingVerdict(_verdict())
        outcome = _select(verifier=FakeVerifier(counting))
        assert outcome.kind is VerifiedNextReadyOutcomeKind.SELECTED
        assert outcome.selected_node_id == CHILD
        reads = object.__getattribute__(counting, "_reads")
        assert set(reads) == {
            "kind",
            "reason_code",
            "graph_id",
            "graph_run_id",
            "node_id",
            "job_id",
            "job_version",
            "completion_evidence_ref",
        }
        assert all(count == 1 for count in reads.values()), reads


# ══════════════════════════════════════════════════════════════════════
# Observed-side ingress normalization (R4 P1 adjudicated contract)
# ══════════════════════════════════════════════════════════════════════


class _LyingNeObservedVersion(int):
    """Observed version subclass whose reflected __ne__ always claims
    EQUAL (suppresses the version cross-check)."""

    ne_invocations = 0

    def __ne__(self, other: object) -> bool:
        type(self).ne_invocations += 1
        return False


class _RaisingNeObservedVersion(int):
    """Observed version subclass whose reflected __ne__ detonates."""

    ne_invocations = 0

    def __ne__(self, other: object) -> bool:
        type(self).ne_invocations += 1
        raise RuntimeError("observed-ne-explosion")


class _LaunderingObservedJobId(str):
    """Observed job_id subclass whose comparators always claim EQUAL."""

    cmp_invocations = 0

    def __eq__(self, other: object) -> bool:
        type(self).cmp_invocations += 1
        return True

    def __ne__(self, other: object) -> bool:
        type(self).cmp_invocations += 1
        return False

    def __hash__(self) -> int:
        return str.__hash__(self)


def _forged_parent_job(**overrides) -> JobRuntimeState:
    """JobRuntimeState bypassing __post_init__ for hostile observed
    fields the durable store could never validate but could still
    project (defense for the consumer boundary, not the store)."""
    base = _job(TaskState.COMPLETE, PARENT)
    forged = object.__new__(JobRuntimeState)
    for name in (
        "job_id",
        "work_order_ref",
        "project_id",
        "state",
        "worker_id",
        "attempt_count",
        "max_attempts",
        "recovery_classification",
        "version",
    ):
        object.__setattr__(forged, name, getattr(base, name))
    for name, value in overrides.items():
        object.__setattr__(forged, name, value)
    return forged


class TestObservedSideIngressNormalization:
    """RED/GREEN matrix for the R4 observed-side exact-type ingress
    boundary (mirror of TestIngressNormalization on the observed side):
    the store-projected parent identity must be exact-plain-type gated
    EXACTLY ONCE, immediately after observation and BEFORE the
    consistency proof / version cross-check / state check / planner use,
    so no observed comparator is ever invoked on a non-plain value."""

    def test_observed_version_int_subclass_liar_ne_blocked_as_mismatch(
        self,
    ) -> None:
        # R4 reproduction: the durable store projects parent version as an
        # int subclass whose reflected __ne__ always claims EQUAL, so the
        # plain `verdict_version != facts.parent.version` cross-check
        # (verdict says 7, durable says 8) currently launders into a
        # match and SELECTS. The observed-side ingress must gate
        # type(v) is int FIRST — a non-plain observed version is a
        # COMPLETION_VERSION_MISMATCH by definition, comparator never
        # invoked, never a selection.
        expected_job_id = GraphDispatchKey(GRAPH, RUN, PARENT).job_id
        hostile_job = _job(
            TaskState.COMPLETE, PARENT, version=_LyingNeObservedVersion(8)
        )
        outcome = _select(
            jobs=FakeJobs({expected_job_id: hostile_job}),
            verifier=FakeVerifier(_verdict()),  # verdict says 7
        )
        assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
        assert outcome.blocker_code == "COMPLETION_VERSION_MISMATCH"
        assert outcome.selected_node_id is None
        assert outcome.planner_decision is None
        assert _LyingNeObservedVersion.ne_invocations == 0

    def test_observed_version_raising_ne_subclass_blocked_not_raw(
        self,
    ) -> None:
        # Companion: an observed version subclass whose __ne__ detonates
        # must be fail-closed at the observed-side ingress (comparator
        # never invoked) — never a raw RuntimeError escape from the seam
        # at the version cross-check.
        expected_job_id = GraphDispatchKey(GRAPH, RUN, PARENT).job_id
        hostile_job = _job(
            TaskState.COMPLETE, PARENT, version=_RaisingNeObservedVersion(7)
        )
        try:
            outcome = _select(
                jobs=FakeJobs({expected_job_id: hostile_job}),
                verifier=FakeVerifier(_verdict()),  # verdict says 7
            )
        except RuntimeError as exc:
            pytest.fail(f"raw comparator exception escaped the seam: {exc}")
        assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
        assert outcome.blocker_code == "COMPLETION_VERSION_MISMATCH"
        assert outcome.selected_node_id is None
        assert outcome.planner_decision is None
        assert _RaisingNeObservedVersion.ne_invocations == 0
        assert "observed-ne-explosion" not in outcome.detail

    def test_observed_bool_version_blocked_typed(self) -> None:
        # a projected parent version of True (type(v) is bool, not int)
        # can never reach a comparator: it must fail closed typed.
        expected_job_id = GraphDispatchKey(GRAPH, RUN, PARENT).job_id
        forged_job = _forged_parent_job(version=True)
        outcome = _select(
            jobs=FakeJobs({expected_job_id: forged_job}),
            verifier=FakeVerifier(_verdict()),
        )
        assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
        assert outcome.blocker_code == "OBSERVATION_INPUT_INVALID"
        assert outcome.selected_node_id is None
        assert outcome.planner_decision is None

    def test_observed_job_id_non_plain_subclass_blocked_typed(self) -> None:
        # a projected parent job_id that is a str subclass (whose
        # comparators claim EQUAL) must be fail-closed at the observed-side
        # ingress BEFORE any module-owned consistency proof / planner
        # identity comparison — never a selection. (The reused observation
        # seam's own internal identity check runs upstream of this module's
        # ingress and stays verbatim; the ingress still fails the value
        # closed before any comparator owned by THIS seam can see it.)
        expected_job_id = GraphDispatchKey(GRAPH, RUN, PARENT).job_id
        forged_job = _forged_parent_job(
            job_id=_LaunderingObservedJobId(expected_job_id)
        )
        outcome = _select(
            jobs=FakeJobs({expected_job_id: forged_job}),
            verifier=FakeVerifier(_verdict()),
        )
        assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
        assert outcome.blocker_code == "OBSERVATION_INCONSISTENT"
        assert "PARENT_JOB_IDENTITY_NOT_PLAIN" in outcome.detail
        assert outcome.selected_node_id is None
        assert outcome.planner_decision is None


# ══════════════════════════════════════════════════════════════════════
# Read-monitor capture normalization (R5 adjudicated lane, Terra (a) 0.82)
# ══════════════════════════════════════════════════════════════════════


class _LyingEqHostileVersion(int):
    """Read-2 version: int subclass representing 8 whose ``__eq__``
    always claims EQUAL (even against plain 7) and whose ``__hash__``
    equals ``hash(7)``, so a RAW captured-identity set() dedups the
    conflicting read and launders the flip into a selection."""

    eq_invocations = 0
    hash_invocations = 0

    def __eq__(self, other: object) -> bool:
        type(self).eq_invocations += 1
        return True

    def __ne__(self, other: object) -> bool:
        type(self).eq_invocations += 1
        return False

    def __hash__(self) -> int:
        type(self).hash_invocations += 1
        return hash(7)


class PlainThenHostileParentJobs:
    """Parent identity flips between repeated reads inside one boundary:
    read 1 (facts projection) = plain COMPLETE v7; read 2 (graph-state
    projection) = COMPLETE v8 as a lying int subclass. Each read is
    individually valid (JobRuntimeState, plain job_id/state), so only
    capture-time identity normalization can detect the flip without ever
    invoking the hostile comparators."""

    def __init__(self, parent_job_id: str) -> None:
        self._parent_job_id = parent_job_id
        self.parent_read_count = 0

    def get_job(self, job_id: str):
        if job_id == self._parent_job_id:
            self.parent_read_count += 1
            if self.parent_read_count == 1:
                return _job(TaskState.COMPLETE, PARENT, version=PARENT_VERSION)
            return _forged_parent_job(version=_LyingEqHostileVersion(8))
        raise JobStoreError("JOB_NOT_FOUND")


def test_read_monitor_hostile_version_capture_blocked_not_selected() -> None:
    # R5 reproduction (Terra verdict (a) 0.82): the parent read monitor
    # captures RAW identity tuples, so a read-2 version that is an int
    # subclass with __eq__ always claiming EQUAL and __hash__ == hash(7)
    # dedups inside the raw set() consistency proof: read 1 (plain 7,
    # projected into facts.parent) and read 2 (hostile 8) present as ONE
    # identity, the flip launders through the boundary, and the seam
    # SELECTS on a conflicting observation. Capture-time exact-type
    # normalization must record the non-plain read as inconsistent and
    # fail closed as OBSERVATION_INCONSISTENT:PARENT_JOB_READS_CONFLICT
    # — with the hostile __eq__/__hash__ never invoked anywhere.
    parent_job_id = GraphDispatchKey(GRAPH, RUN, PARENT).job_id
    jobs = PlainThenHostileParentJobs(parent_job_id)
    outcome = select_verified_next_ready(
        jobs=jobs,
        completion_verifier=FakeVerifier(_verdict()),  # verdict binds v7
        graph=_chain_graph(),
        graph_id=GRAPH,
        graph_run_id=RUN,
        parent_node_id=PARENT,
        guards=_guards(),
    )
    assert jobs.parent_read_count == 2  # double-read boundary proven
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "OBSERVATION_INCONSISTENT"
    assert outcome.detail == "OBSERVATION_INCONSISTENT:PARENT_JOB_READS_CONFLICT"
    assert outcome.selected_node_id is None
    assert outcome.planner_decision is None
    # no hostile comparator or hash was ever invoked inside the seam
    assert _LyingEqHostileVersion.eq_invocations == 0
    assert _LyingEqHostileVersion.hash_invocations == 0


# ══════════════════════════════════════════════════════════════════════
# Universal sanitized job snapshot at the monitor boundary (R6 joint
# lane: JEV direct 0.68 GRANT + Terra conditional 0.84 — the snapshot
# must cover EVERY returned job; no raw object reaches the reused seam)
# ══════════════════════════════════════════════════════════════════════


class _CountingHostileRead2JobId(str):
    """Read-2 parent job_id: str subclass whose comparators always claim
    EQUAL and whose hash equals the content hash, so a raw read flowing
    into the reused seam's identity comparison invokes a hostile
    comparator before the eventual blocker (R6 P1)."""

    eq_invocations = 0
    ne_invocations = 0
    hash_invocations = 0

    def __eq__(self, other: object) -> bool:
        type(self).eq_invocations += 1
        return True

    def __ne__(self, other: object) -> bool:
        type(self).ne_invocations += 1
        return False

    def __hash__(self) -> int:
        type(self).hash_invocations += 1
        return str.__hash__(self)


class PlainThenHostileJobIdParentJobs:
    """Parent identity: read 1 (facts projection) = plain COMPLETE v7;
    read 2 (graph-state projection) = same identity with job_id carried
    as the hostile str subclass. Under raw passthrough the read-2 object
    reaches the reused seam unmonitored: the seam's own `!=` invokes the
    hostile comparator and the non-plain value then launders through
    ParentCompletion into the observed-side ingress."""

    def __init__(self, parent_job_id: str) -> None:
        self._parent_job_id = parent_job_id
        self.parent_read_count = 0

    def get_job(self, job_id: str):
        if job_id == self._parent_job_id:
            self.parent_read_count += 1
            if self.parent_read_count == 1:
                return _job(TaskState.COMPLETE, PARENT, version=PARENT_VERSION)
            return _forged_parent_job(
                job_id=_CountingHostileRead2JobId(self._parent_job_id)
            )
        raise JobStoreError("JOB_NOT_FOUND")


def test_read_monitor_hostile_read2_job_id_snapshot_blocked_without_comparator() -> None:
    # R6 P1 (raw job passthrough): the monitor must never hand a raw job
    # to the reused seam. A read-2 parent job_id that is a hostile str
    # subclass must be captured as inconsistent (plain-tuple capture,
    # hostile dropped), the boundary fail-closed as
    # OBSERVATION_INCONSISTENT:PARENT_JOB_READS_CONFLICT, and the hostile
    # __eq__/__ne__/__hash__ never invoked anywhere in the pipeline.
    parent_job_id = GraphDispatchKey(GRAPH, RUN, PARENT).job_id
    jobs = PlainThenHostileJobIdParentJobs(parent_job_id)
    outcome = select_verified_next_ready(
        jobs=jobs,
        completion_verifier=FakeVerifier(_verdict()),  # verdict binds v7
        graph=_chain_graph(),
        graph_id=GRAPH,
        graph_run_id=RUN,
        parent_node_id=PARENT,
        guards=_guards(),
    )
    assert jobs.parent_read_count == 2  # double-read boundary proven
    assert outcome.kind is VerifiedNextReadyOutcomeKind.BLOCKED
    assert outcome.blocker_code == "OBSERVATION_INCONSISTENT"
    assert outcome.detail == "OBSERVATION_INCONSISTENT:PARENT_JOB_READS_CONFLICT"
    assert outcome.selected_node_id is None
    assert outcome.planner_decision is None
    # zero hostile comparator invocations anywhere (identity/counter probe)
    assert _CountingHostileRead2JobId.eq_invocations == 0
    assert _CountingHostileRead2JobId.ne_invocations == 0
    assert _CountingHostileRead2JobId.hash_invocations == 0


class _CountingHostileSuccessorJobId(str):
    """Non-parent (successor) job_id: str subclass wrapping the true key
    whose comparators always claim EQUAL and whose hash equals the
    content hash — raw passthrough lets the reused seam's successor
    identity check invoke the hostile comparator (R6: the raw job
    compared at the seam)."""

    eq_invocations = 0
    ne_invocations = 0
    hash_invocations = 0

    def __eq__(self, other: object) -> bool:
        type(self).eq_invocations += 1
        return True

    def __ne__(self, other: object) -> bool:
        type(self).ne_invocations += 1
        return False

    def __hash__(self) -> int:
        type(self).hash_invocations += 1
        return str.__hash__(self)


class _ProbeSuccessorJob(JobRuntimeState):
    """Raw-object identity probe: a JobRuntimeState subclass instance so
    the test can prove the RAW object itself never reaches the reused
    seam (its comparators are counted; any set()/==/dict-keying on the
    raw object increments them)."""

    obj_eq_invocations = 0
    obj_hash_invocations = 0

    def __eq__(self, other: object) -> bool:
        type(self).obj_eq_invocations += 1
        return self is other

    def __hash__(self) -> int:
        type(self).obj_hash_invocations += 1
        return JobRuntimeState.__hash__(self)


def test_non_parent_hostile_field_job_arrives_plain_typed_at_seam() -> None:
    # Terra every-job condition: the sanitized snapshot must cover EVERY
    # returned job, including non-parent graph jobs. A successor job
    # carrying a hostile job_id (str subclass claiming EQUAL) plus a raw
    # object identity probe must flow as a plain-typed snapshot: the
    # reused seam's successor identity check compares the snapshot's
    # plain job_id (durably represented -> NOOP_ALL_REPRESENTED), with
    # the hostile field comparators AND the raw-object comparators never
    # invoked anywhere. Under raw passthrough the hostile __ne__ is
    # invoked once inside the seam before the same outcome.
    child_key = GraphDispatchKey(GRAPH, RUN, CHILD).job_id
    probe_job = _ProbeSuccessorJob(
        job_id=_CountingHostileSuccessorJobId(child_key),
        work_order_ref="docs/work-orders/WO-P1-738-verified-next-ready.md",
        project_id="wo738-project",
        state=TaskState.READY,
        worker_id=None,
        attempt_count=0,
        max_attempts=3,
        recovery_classification=None,
        version=1,
    )
    outcome = _select(
        jobs=FakeJobs(
            {
                GraphDispatchKey(GRAPH, RUN, PARENT).job_id: _job(
                    TaskState.COMPLETE, PARENT, version=PARENT_VERSION
                ),
                child_key: probe_job,
            }
        ),
        verifier=FakeVerifier(_verdict()),
    )
    assert outcome.kind is VerifiedNextReadyOutcomeKind.NOOP
    assert outcome.planner_decision is NextReadyDecision.NOOP_ALL_REPRESENTED
    assert outcome.represented_node_ids == (CHILD,)
    assert outcome.selected_node_id is None
    assert outcome.blocker_code is None
    # hostile FIELD comparators never invoked (the seam compared a
    # plain-typed snapshot's job_id, not the raw subclass)
    assert _CountingHostileSuccessorJobId.eq_invocations == 0
    assert _CountingHostileSuccessorJobId.ne_invocations == 0
    assert _CountingHostileSuccessorJobId.hash_invocations == 0
    # raw OBJECT never compared or hashed anywhere (identity probe)
    assert _ProbeSuccessorJob.obj_eq_invocations == 0
    assert _ProbeSuccessorJob.obj_hash_invocations == 0
