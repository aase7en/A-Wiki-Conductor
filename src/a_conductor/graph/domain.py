"""GE-1a — graph domain contract (ADR GE-0001..0005, decisions D1-D5).

Pure data + invariants only: no persistence, scheduling, dispatch, or
lifecycle integration (D5 limits this node to domain + tests).

Guardrails encoded here:
- D2: TaskNode carries NO dependency field — TaskEdge/TaskGraph own
  dependency relations (single source of truth).
- D2: node status is planning metadata; execution/retry state stays in
  the existing lifecycle state machine.
- D4: the 12-value DependencyType vocabulary ships exactly as accepted;
  HUMAN_APPROVAL is a readiness gate type, never a repair back-edge
  (ordering semantics arrive with GE-3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple


class DependencyType(str, Enum):
    """Accepted 12-value vocabulary (ADR GE-0003, decision D4)."""

    DATA = "DATA"
    ORDERING = "ORDERING"
    FILE_WRITE = "FILE_WRITE"
    WORKSPACE_WRITE = "WORKSPACE_WRITE"
    GIT = "GIT"
    WORKER = "WORKER"
    RUNTIME = "RUNTIME"
    PROVIDER = "PROVIDER"
    RATE_LIMIT = "RATE_LIMIT"
    RESOURCE = "RESOURCE"
    VERIFICATION = "VERIFICATION"
    HUMAN_APPROVAL = "HUMAN_APPROVAL"


class TaskNodeStatus(str, Enum):
    """Planning metadata only (D2). Execution/retry state stays in the
    existing lifecycle state machine, never here."""

    TODO = "todo"
    DOING = "doing"
    DONE = "done"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


# 20-value vendor-neutral capability enum from awiki-task/v1 (ADR GE-0002).
CAPABILITY_VOCABULARY: Tuple[str, ...] = (
    "repository-read",
    "repository-write",
    "shell",
    "tests",
    "code-review",
    "deep-reasoning",
    "architecture-review",
    "security-review",
    "long-context",
    "web-research",
    "documentation",
    "translation",
    "data-analysis",
    "independent-judgement",
    "project-code-context",
    "symbol-search",
    "call-graph",
    "blast-radius",
    "memory-read",
    "memory-write",
)


@dataclass(frozen=True, slots=True)
class TaskNode:
    """A unit of schedulable work (ADR GE-0002).

    Deliberately carries no dependency field: TaskEdge/TaskGraph own
    dependency relations (decision D2).
    """

    id: str
    objective: str
    expected_outputs: Tuple[str, ...] = ()
    read_set: Tuple[str, ...] = ()
    write_set: Tuple[str, ...] = ()
    worker_requirement: Tuple[str, ...] = ()
    model_requirement: str | None = None
    priority: int = 0
    timeout_seconds: int | None = None
    retry_policy_ref: str | None = None
    status: TaskNodeStatus = TaskNodeStatus.TODO
    artifacts: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("TaskNode.id must be a non-empty string")
        for capability in self.worker_requirement:
            if capability not in CAPABILITY_VOCABULARY:
                raise ValueError(
                    f"TaskNode {self.id!r}: unknown capability {capability!r}"
                )
        if self.priority < 0:
            raise ValueError("TaskNode.priority must be >= 0")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("TaskNode.timeout_seconds must be > 0 when set")


@dataclass(frozen=True, slots=True)
class TaskEdge:
    """A directed dependency relation between two TaskNodes (D2)."""

    from_id: str
    to_id: str
    dep_type: DependencyType = DependencyType.DATA


@dataclass(slots=True)
class TaskGraph:
    """An ordered collection of nodes + dependency edges with invariants.

    Only true predecessor relations belong here (D4 guardrail); dynamic
    constraints (worker/runtime/provider/rate-limit conflicts) stay
    readiness/scheduler reasons unless a deterministic analyzer
    explicitly materializes a safe ordering.
    """

    _nodes: dict = field(default_factory=dict)
    _edges: list = field(default_factory=list)
    _edge_keys: set = field(default_factory=set)

    def add_node(self, node: TaskNode) -> None:
        if node.id in self._nodes:
            raise ValueError(f"TaskNode {node.id!r} already exists in the graph")
        self._nodes[node.id] = node

    def add_edge(self, edge: TaskEdge) -> None:
        if edge.from_id not in self._nodes:
            raise ValueError(f"TaskEdge references unknown from_id {edge.from_id!r}")
        if edge.to_id not in self._nodes:
            raise ValueError(f"TaskEdge references unknown to_id {edge.to_id!r}")
        if edge.from_id == edge.to_id:
            raise ValueError("TaskEdge cannot be a self-edge")
        key = (edge.from_id, edge.to_id, edge.dep_type)
        if key in self._edge_keys:
            raise ValueError(
                f"TaskEdge {edge.from_id!r} -> {edge.to_id!r} "
                f"({edge.dep_type.value}) already exists"
            )
        self._edge_keys.add(key)
        self._edges.append(edge)

    def node(self, node_id: str) -> TaskNode:
        return self._nodes[node_id]

    def nodes(self) -> Tuple[TaskNode, ...]:
        return tuple(self._nodes.values())

    def node_ids(self) -> Tuple[str, ...]:
        return tuple(self._nodes.keys())

    def edges(self) -> Tuple[TaskEdge, ...]:
        return tuple(self._edges)

    def edges_from(self, node_id: str) -> Tuple[TaskEdge, ...]:
        return tuple(e for e in self._edges if e.from_id == node_id)

    def edges_to(self, node_id: str) -> Tuple[TaskEdge, ...]:
        return tuple(e for e in self._edges if e.to_id == node_id)
