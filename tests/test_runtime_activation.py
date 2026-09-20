from __future__ import annotations

from dataclasses import dataclass

import pytest

from a_conductor.elastic_worker_capacity import ElasticCapacityPolicy
from a_conductor.graph.domain import TaskNode, TaskNodeStatus
from a_conductor.graph.graph import TaskGraphBuilder
from a_conductor.graph.scheduler import NodeEligibility, SchedulePolicy
from a_conductor.runtime_activation import (
    RuntimeActivationError,
    RuntimeActivationRequest,
    RuntimeActivationService,
)


@dataclass(frozen=True)
class _Contract:
    node_id: str


class _Executor:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def execute_once(self, graph, ready, contracts_by_node, **kwargs):
        self.calls.append(
            {
                "graph": graph,
                "ready": ready,
                "contracts": contracts_by_node,
                **kwargs,
            }
        )
        return "EXECUTED"


def _graph(*nodes: TaskNode):
    builder = TaskGraphBuilder()
    for node in nodes:
        builder.add_node(node)
    return builder.build()


def _request(node_id: str = "n1") -> RuntimeActivationRequest:
    return RuntimeActivationRequest(
        graph_id="graph-1",
        graph_run_id="run-1",
        node_id=node_id,
        runtime_kind="serena",
        batch_id="manual-batch-1",
    )


def _service(graph, states, executor: _Executor, built: list[str]):
    return RuntimeActivationService(
        graph_loader=lambda graph_id: graph,
        state_projector=lambda graph, graph_id, graph_run_id: states,
        contract_builder=lambda request, node: (
            built.append(node.id) or _Contract(node.id)
        ),
        executor=executor,
    )


def test_manual_activation_executes_only_exact_ready_node():
    graph = _graph(
        TaskNode("n1", "first"),
        TaskNode("n2", "second"),
    )
    executor = _Executor()
    built: list[str] = []
    service = _service(
        graph,
        {"n1": TaskNodeStatus.TODO, "n2": TaskNodeStatus.TODO},
        executor,
        built,
    )

    result = service.activate(_request("n2"))

    assert result == "EXECUTED"
    assert built == ["n2"]
    assert len(executor.calls) == 1
    call = executor.calls[0]
    assert call["ready"].ready_ids == {"n2"}
    assert set(call["contracts"]) == {"n2"}
    assert call["schedule_policy"] == SchedulePolicy(max_parallel=1)
    assert call["elastic_policy"] == ElasticCapacityPolicy(
        enabled=False,
        max_extra_workers=0,
        permitted_runtime_kinds=(),
    )
    assert call["eligibility"] == {"n2": NodeEligibility()}
    assert call["provider_inflight"] == {}
    assert call["batch_id"] == "manual-batch-1"


def test_manual_activation_refuses_non_ready_exact_node():
    graph = _graph(TaskNode("n1", "first"))
    executor = _Executor()
    built: list[str] = []
    service = _service(
        graph,
        {"n1": TaskNodeStatus.DOING},
        executor,
        built,
    )

    with pytest.raises(RuntimeActivationError, match="ACTIVATION_NODE_NOT_READY"):
        service.activate(_request())

    assert built == []
    assert executor.calls == []


def test_manual_activation_fails_closed_on_unproven_worker_capability():
    graph = _graph(
        TaskNode(
            "n1",
            "requires capability",
            worker_requirement=("repository-write",),
        )
    )
    executor = _Executor()
    built: list[str] = []
    service = _service(
        graph,
        {"n1": TaskNodeStatus.TODO},
        executor,
        built,
    )

    with pytest.raises(
        RuntimeActivationError,
        match="RUNTIME_CAPABILITY_AUTHORITY_UNAVAILABLE",
    ):
        service.activate(_request())

    assert built == []
    assert executor.calls == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("graph_id", ""),
        ("graph_run_id", "bad" + chr(10) + "run"),
        ("node_id", " "),
        ("runtime_kind", ""),
        ("batch_id", ""),
    ],
)
def test_activation_request_rejects_unsafe_identity_text(field: str, value: str):
    values = {
        "graph_id": "graph-1",
        "graph_run_id": "run-1",
        "node_id": "n1",
        "runtime_kind": "serena",
        "batch_id": "manual-batch-1",
    }
    values[field] = value

    with pytest.raises(ValueError):
        RuntimeActivationRequest(**values)
