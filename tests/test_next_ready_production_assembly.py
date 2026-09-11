from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import Mock

import pytest

from a_conductor.domain import TaskState
from a_conductor.elastic_worker_capacity import (
    ElasticCapacityPolicy,
    ProductionElasticExecutionKind,
    ProductionElasticExecutionResult,
)
from a_conductor.graph.dispatch import GraphDispatchKey
from a_conductor.graph.domain import DependencyType, TaskEdge, TaskGraph, TaskNode
from a_conductor.graph.scheduler import NodeEligibility, SchedulePlan, SchedulePolicy
from a_conductor.job_state import JobRuntimeState
from a_conductor.job_store import JobEvent, JobEventType, JobStoreError
from a_conductor.worker_candidate_assembly import ParallelReadyNodeContract
from a_conductor.next_ready_production_assembly import (
    NextReadyProductionAssembly,
    NextReadyProductionError,
    NextReadyProductionOutcome,
    derive_zra3_batch_id,
)

GRAPH = "graph-zra3"
RUN = "run-1"
PARENT = "A"
WORK_ORDER = "docs/tasks/A.md"
SHA = "a" * 40


def _graph(*, fork: bool = False) -> TaskGraph:
    graph = TaskGraph()
    graph.add_node(TaskNode(id="A", objective="parent"))
    graph.add_node(TaskNode(id="B1", objective="child-1"))
    graph.add_edge(TaskEdge("A", "B1", DependencyType.ORDERING))
    if fork:
        graph.add_node(TaskNode(id="B2", objective="child-2"))
        graph.add_edge(TaskEdge("A", "B2", DependencyType.ORDERING))
    return graph


def _job(node_id: str, state: TaskState, *, work_order_ref: str | None = None) -> JobRuntimeState:
    return JobRuntimeState(
        job_id=GraphDispatchKey(GRAPH, RUN, node_id).job_id,
        work_order_ref=work_order_ref or f"docs/tasks/{node_id}.md",
        project_id="project-1",
        state=state,
        worker_id=None,
        attempt_count=0,
        max_attempts=3,
        recovery_classification=None,
        version=3,
    )


def _complete_event(
    *,
    job_id: str | None = None,
    evidence_ref: str | None = None,
    to_state: TaskState = TaskState.COMPLETE,
) -> JobEvent:
    return JobEvent(
        event_id="event-1",
        job_id=job_id or GraphDispatchKey(GRAPH, RUN, PARENT).job_id,
        sequence_no=1,
        event_type=JobEventType.TRANSITION,
        from_state=TaskState.REVIEW_PENDING,
        to_state=to_state,
        worker_id=None,
        recovery_classification=None,
        checkpoint_ref=None,
        evidence_ref=(
            evidence_ref
            if evidence_ref is not None
            else f"closeout:complete:{WORK_ORDER}:{SHA}"
        ),
        recorded_at="2026-09-11T14:00:00Z",
    )


class FakeJobs:
    def __init__(self, *, parent_state: TaskState = TaskState.COMPLETE, events=None) -> None:
        parent = _job(PARENT, parent_state, work_order_ref=WORK_ORDER)
        self.jobs = {parent.job_id: parent}
        self.events = tuple(events if events is not None else (_complete_event(),))

    def get_job(self, job_id: str) -> JobRuntimeState:
        try:
            return self.jobs[job_id]
        except KeyError as exc:
            raise JobStoreError("JOB_NOT_FOUND") from exc

    def list_events(self, job_id: str):
        if job_id not in self.jobs:
            raise JobStoreError("JOB_NOT_FOUND")
        return self.events


class FakeGraphs:
    def __init__(self, graph: TaskGraph) -> None:
        self.graph = graph
        self.calls: list[str] = []

    def load_graph(self, graph_id: str) -> TaskGraph:
        self.calls.append(graph_id)
        return self.graph


@dataclass(frozen=True)
class FakeContract:
    dispatch_key: GraphDispatchKey


class FakeExecutor:
    def __init__(self, kind: ProductionElasticExecutionKind) -> None:
        self.kind = kind
        self.calls: list[dict[str, object]] = []

    def execute_once(self, graph, ready, contracts_by_node, **kwargs):
        self.calls.append(
            {
                "graph": graph,
                "ready": ready,
                "contracts_by_node": contracts_by_node,
                **kwargs,
            }
        )
        return ProductionElasticExecutionResult(
            self.kind,
            self.kind.value,
            SchedulePlan((), (), "test-capacity"),
        )


def _assembly(*, jobs=None, graph=None, kind=ProductionElasticExecutionKind.FIXED_POOL_EXECUTED):
    executor = FakeExecutor(kind)
    assembly = NextReadyProductionAssembly(
        jobs=jobs or FakeJobs(),
        graphs=FakeGraphs(graph or _graph()),
        executor=executor,
    )
    return assembly, executor


def _contract(node_id: str) -> ParallelReadyNodeContract:
    contract = Mock(spec=ParallelReadyNodeContract)
    contract.dispatch_key = GraphDispatchKey(GRAPH, RUN, node_id)
    return contract


def _run(assembly: NextReadyProductionAssembly, *, contracts=None, eligibility=None):
    contracts = contracts if contracts is not None else {"B1": _contract("B1")}
    eligibility = eligibility if eligibility is not None else {"B1": NodeEligibility()}
    return assembly.execute_once(
        graph_id=GRAPH,
        graph_run_id=RUN,
        parent_node_id=PARENT,
        contracts_by_node=contracts,
        schedule_policy=SchedulePolicy(max_parallel=5),
        provider_inflight={},
        runtime_kind="local",
        elastic_policy=ElasticCapacityPolicy(False, 0, ("local",)),
        eligibility=eligibility,
    )


def test_parent_not_complete_is_noop_without_executor_call() -> None:
    assembly, executor = _assembly(jobs=FakeJobs(parent_state=TaskState.REVIEW_PENDING))
    result = _run(assembly)
    assert result.outcome is NextReadyProductionOutcome.NOOP
    assert executor.calls == []


def test_complete_parent_missing_event_fails_closed() -> None:
    assembly, executor = _assembly(jobs=FakeJobs(events=()))
    with pytest.raises(NextReadyProductionError) as excinfo:
        _run(assembly)
    assert excinfo.value.code == "PARENT_COMPLETION_EVENT_MISSING"
    assert executor.calls == []


def test_complete_parent_foreign_event_fails_closed() -> None:
    foreign = _complete_event(job_id=GraphDispatchKey(GRAPH, "other-run", PARENT).job_id)
    assembly, executor = _assembly(jobs=FakeJobs(events=(foreign,)))
    with pytest.raises(NextReadyProductionError) as excinfo:
        _run(assembly)
    assert excinfo.value.code == "PARENT_COMPLETION_EVENT_IDENTITY_MISMATCH"
    assert executor.calls == []


def test_complete_parent_missing_evidence_fails_closed() -> None:
    missing = JobEvent(
        event_id="event-1",
        job_id=GraphDispatchKey(GRAPH, RUN, PARENT).job_id,
        sequence_no=1,
        event_type=JobEventType.TRANSITION,
        from_state=TaskState.REVIEW_PENDING,
        to_state=TaskState.COMPLETE,
        worker_id=None,
        recovery_classification=None,
        checkpoint_ref=None,
        evidence_ref=None,
        recorded_at="2026-09-11T14:00:00Z",
    )
    assembly, executor = _assembly(jobs=FakeJobs(events=(missing,)))
    with pytest.raises(NextReadyProductionError) as excinfo:
        _run(assembly)
    assert excinfo.value.code == "PARENT_COMPLETION_EVIDENCE_MISSING"
    assert executor.calls == []


@pytest.mark.parametrize(
    "evidence",
    ["closeout:complete:wrong-task:" + SHA, "closeout:complete:" + WORK_ORDER + ":not-a-sha"],
)
def test_malformed_or_foreign_completion_evidence_fails_closed(evidence: str) -> None:
    assembly, executor = _assembly(jobs=FakeJobs(events=(_complete_event(evidence_ref=evidence),)))
    with pytest.raises(NextReadyProductionError) as excinfo:
        _run(assembly)
    assert excinfo.value.code == "PARENT_COMPLETION_EVIDENCE_INVALID"
    assert executor.calls == []


def test_multiple_ready_successors_focuses_exactly_one_node() -> None:
    assembly, executor = _assembly(graph=_graph(fork=True))
    result = _run(
        assembly,
        contracts={"B1": _contract("B1"), "B2": _contract("B2")},
        eligibility={"B1": NodeEligibility(), "B2": NodeEligibility()},
    )
    assert result.outcome is NextReadyProductionOutcome.EXECUTED
    assert result.selected_node_id == "B1"
    assert len(executor.calls) == 1
    call = executor.calls[0]
    assert call["ready"].ready_ids == {"B1"}
    assert set(call["contracts_by_node"]) == {"B1"}


def test_missing_selected_contract_fails_closed() -> None:
    assembly, executor = _assembly()
    with pytest.raises(NextReadyProductionError) as excinfo:
        _run(assembly, contracts={})
    assert excinfo.value.code == "SELECTED_CONTRACT_MISSING"
    assert executor.calls == []


def test_selected_contract_wrong_type_fails_closed() -> None:
    assembly, executor = _assembly()
    bad = FakeContract(GraphDispatchKey(GRAPH, RUN, "B1"))
    with pytest.raises(NextReadyProductionError) as excinfo:
        _run(assembly, contracts={"B1": bad})
    assert excinfo.value.code == "SELECTED_CONTRACT_INVALID"
    assert executor.calls == []


def test_selected_eligibility_missing_fails_closed() -> None:
    assembly, executor = _assembly()
    with pytest.raises(NextReadyProductionError) as excinfo:
        _run(assembly, eligibility={})
    assert excinfo.value.code == "SELECTED_ELIGIBILITY_MISSING"
    assert executor.calls == []


def test_selected_eligibility_invalid_fails_closed() -> None:
    assembly, executor = _assembly()
    with pytest.raises(NextReadyProductionError) as excinfo:
        _run(assembly, eligibility={"B1": object()})
    assert excinfo.value.code == "SELECTED_ELIGIBILITY_INVALID"
    assert executor.calls == []


def test_selected_contract_graph_identity_drift_fails_closed() -> None:
    assembly, executor = _assembly()
    bad = _contract("B1")
    bad.dispatch_key = GraphDispatchKey(GRAPH, "foreign-run", "B1")
    with pytest.raises(NextReadyProductionError) as excinfo:
        _run(assembly, contracts={"B1": bad})
    assert excinfo.value.code == "SELECTED_CONTRACT_IDENTITY_MISMATCH"
    assert executor.calls == []


def test_batch_identity_is_deterministic_and_bound_to_selected_job() -> None:
    job_id = GraphDispatchKey(GRAPH, RUN, "B1").job_id
    first = derive_zra3_batch_id(GRAPH, RUN, job_id)
    second = derive_zra3_batch_id(GRAPH, RUN, job_id)
    other = derive_zra3_batch_id(GRAPH, RUN, GraphDispatchKey(GRAPH, RUN, "B2").job_id)
    assert first == second
    assert first.startswith("zra3b1:")
    assert first != other


@pytest.mark.parametrize(
    ("downstream", "expected"),
    [
        (ProductionElasticExecutionKind.WAIT, NextReadyProductionOutcome.WAIT),
        (ProductionElasticExecutionKind.RECOVERY_REQUIRED, NextReadyProductionOutcome.RECOVERY_REQUIRED),
        (ProductionElasticExecutionKind.FIXED_POOL_EXECUTED, NextReadyProductionOutcome.EXECUTED),
        (ProductionElasticExecutionKind.ELASTIC_EXECUTED, NextReadyProductionOutcome.EXECUTED),
    ],
)
def test_downstream_result_mapped_without_retry(downstream, expected) -> None:
    assembly, executor = _assembly(kind=downstream)
    result = _run(assembly)
    assert result.outcome is expected
    assert len(executor.calls) == 1


def test_represented_successor_is_noop_and_not_reexecuted() -> None:
    jobs = FakeJobs()
    jobs.jobs[GraphDispatchKey(GRAPH, RUN, "B1").job_id] = _job("B1", TaskState.EXECUTING)
    assembly, executor = _assembly(jobs=jobs)
    result = _run(assembly)
    assert result.outcome is NextReadyProductionOutcome.NOOP
    assert executor.calls == []


def test_recovery_successor_requires_reconcile_and_no_executor_call() -> None:
    from a_conductor.domain import RecoveryClassification

    jobs = FakeJobs()
    jobs.jobs[GraphDispatchKey(GRAPH, RUN, "B1").job_id] = JobRuntimeState(
        job_id=GraphDispatchKey(GRAPH, RUN, "B1").job_id,
        work_order_ref="docs/tasks/B1.md",
        project_id="project-1",
        state=TaskState.RECOVERY_NEEDED,
        worker_id=None,
        attempt_count=1,
        max_attempts=3,
        recovery_classification=RecoveryClassification.UNKNOWN,
        version=4,
    )
    assembly, executor = _assembly(jobs=jobs)
    result = _run(assembly)
    assert result.outcome is NextReadyProductionOutcome.RECONCILE
    assert executor.calls == []
