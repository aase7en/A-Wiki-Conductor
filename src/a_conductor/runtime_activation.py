"""Bounded manual runtime activation policy for WO-P1-433.

This module owns no scheduler, persistence, continuation, retry, or worker
provisioning authority.  It narrows an already-authoritative graph/run to one
explicit READY node and delegates execution to the accepted production stack.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Protocol

from .elastic_worker_capacity import ElasticCapacityPolicy
from .graph.domain import TaskGraph, TaskNode, TaskNodeStatus
from .graph.ready import ReadySetResult, compute_ready_set
from .graph.scheduler import NodeEligibility, SchedulePolicy


class RuntimeActivationError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = _safe_text(code, "code")
        super().__init__(self.code)


def _safe_text(value: str, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or any(char in value for char in "\x00\r\n")
    ):
        raise ValueError(f"{field} is invalid")
    return value.strip()


@dataclass(frozen=True, slots=True)
class RuntimeActivationRequest:
    graph_id: str
    graph_run_id: str
    node_id: str
    runtime_kind: str
    batch_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "graph_id", _safe_text(self.graph_id, "graph_id"))
        object.__setattr__(
            self,
            "graph_run_id",
            _safe_text(self.graph_run_id, "graph_run_id"),
        )
        object.__setattr__(self, "node_id", _safe_text(self.node_id, "node_id"))
        object.__setattr__(
            self,
            "runtime_kind",
            _safe_text(self.runtime_kind, "runtime_kind"),
        )
        object.__setattr__(self, "batch_id", _safe_text(self.batch_id, "batch_id"))


class RuntimeActivationExecutor(Protocol):
    def execute_once(
        self,
        graph: TaskGraph,
        ready: ReadySetResult,
        contracts_by_node: Mapping[str, object],
        **kwargs,
    ) -> object: ...


GraphLoader = Callable[[str], TaskGraph]
StateProjector = Callable[[TaskGraph, str, str], Mapping[str, TaskNodeStatus]]
ContractBuilder = Callable[[RuntimeActivationRequest, TaskNode], object]


class RuntimeActivationService:
    """Execute one explicit READY node without selecting NEXT READY work."""

    def __init__(
        self,
        *,
        graph_loader: GraphLoader,
        state_projector: StateProjector,
        contract_builder: ContractBuilder,
        executor: RuntimeActivationExecutor,
    ) -> None:
        if not callable(graph_loader):
            raise ValueError("graph_loader must be callable")
        if not callable(state_projector):
            raise ValueError("state_projector must be callable")
        if not callable(contract_builder):
            raise ValueError("contract_builder must be callable")
        if not callable(getattr(executor, "execute_once", None)):
            raise ValueError("executor must provide execute_once")
        self._graph_loader = graph_loader
        self._state_projector = state_projector
        self._contract_builder = contract_builder
        self._executor = executor

    def _load_target(
        self,
        request: RuntimeActivationRequest,
    ) -> tuple[TaskGraph, TaskNode]:
        graph = self._graph_loader(request.graph_id)
        if not isinstance(graph, TaskGraph):
            raise RuntimeActivationError("ACTIVATION_GRAPH_INVALID")
        node = next(
            (item for item in graph.nodes() if item.id == request.node_id),
            None,
        )
        if node is None:
            raise RuntimeActivationError("ACTIVATION_NODE_NOT_FOUND")
        return graph, node

    def activate(self, request: RuntimeActivationRequest) -> object:
        if not isinstance(request, RuntimeActivationRequest):
            raise ValueError("request must be RuntimeActivationRequest")
        graph, node = self._load_target(request)

        # Current accepted main has no observed bridge from the canonical
        # TaskNode capability vocabulary to runtime supply.  Never satisfy
        # task demand by echoing it into worker capability evidence.
        if node.worker_requirement:
            raise RuntimeActivationError(
                "RUNTIME_CAPABILITY_AUTHORITY_UNAVAILABLE"
            )

        states = self._state_projector(
            graph,
            request.graph_id,
            request.graph_run_id,
        )
        if not isinstance(states, Mapping):
            raise RuntimeActivationError("ACTIVATION_STATE_EVIDENCE_INVALID")
        ready = compute_ready_set(graph, dict(states))
        check = ready.checks.get(request.node_id)
        if check is None or request.node_id not in ready.ready_ids:
            raise RuntimeActivationError("ACTIVATION_NODE_NOT_READY")

        # Focus the already-computed readiness evidence on the operator-named
        # node.  READY siblings are intentionally excluded: this is not ZRA-3.
        focused = ReadySetResult(
            checks={request.node_id: check},
            ready_ids={request.node_id},
        )
        contract = self._contract_builder(request, node)
        return self._executor.execute_once(
            graph,
            focused,
            {request.node_id: contract},
            schedule_policy=SchedulePolicy(max_parallel=1),
            provider_inflight={},
            runtime_kind=request.runtime_kind,
            elastic_policy=ElasticCapacityPolicy(
                enabled=False,
                max_extra_workers=0,
                permitted_runtime_kinds=(),
            ),
            eligibility={request.node_id: NodeEligibility()},
            batch_id=request.batch_id,
        )
