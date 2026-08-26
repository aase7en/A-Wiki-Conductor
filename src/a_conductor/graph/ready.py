"""GE-5 — ReadySet computation (ADR GE-0001 "Resource-aware scheduling rule").

A node is READY only when:
1. Dependencies satisfied (all predecessors done or skipped)
2. No resource conflict with a running node (GE-4 FILE_WRITE overlap)
3. Node itself is in TODO status (not done/doing/blocked/skipped)

Readiness != execution: the scheduler picks from ReadySet by capacity and
policy (GE-6, gated on GPT design review).
"""

from __future__ import annotations

from .analyze import write_sets_overlap

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Set

from .domain import TaskGraph, TaskNodeStatus


class BlockerKind(str, Enum):
    DEPENDENCY = "dependency"
    RESOURCE = "resource"
    WORKER = "worker"
    GATE = "gate"


@dataclass(frozen=True, slots=True)
class Blocker:
    kind: BlockerKind
    detail: str

    def __str__(self) -> str:
        return f"[{self.kind.value}] {self.detail}"


@dataclass(frozen=True, slots=True)
class ReadyCheck:
    node_id: str
    is_ready: bool
    blockers: tuple[Blocker, ...]

    @property
    def reason(self) -> str:
        if self.is_ready:
            return "ready"
        return "; ".join(str(b) for b in self.blockers)


@dataclass(frozen=True, slots=True)
class ReadySetResult:
    checks: Dict[str, ReadyCheck]
    ready_ids: Set[str]

    @property
    def blocked_count(self) -> int:
        return sum(1 for c in self.checks.values() if not c.is_ready)


def compute_ready_set(
    graph: TaskGraph,
    node_states: dict[str, TaskNodeStatus],
) -> ReadySetResult:
    """Compute which nodes are ready to run given current statuses.

    Args:
        graph: the TaskGraph with nodes + edges
        node_states: current status per node_id (missing = TODO default)

    Returns:
        ReadySetResult with per-node checks + the set of ready node IDs.
    """
    checks: dict[str, ReadyCheck] = {}
    ready: set[str] = set()

    nodes_by_id = {n.id: n for n in graph.nodes()}
    edges_to = {n.id: [] for n in graph.nodes()}
    for edge in graph.edges():
        edges_to[edge.to_id].append(edge)

    # Collect write sets of running nodes for resource conflict detection.
    # Uses the authoritative glob-aware seam from GE-4 (WO-GE-005A).
    running_write_sets: dict[str, tuple[str, ...]] = {}
    for node in graph.nodes():
        state = node_states.get(node.id, TaskNodeStatus.TODO)
        if state is TaskNodeStatus.DOING and node.write_set:
            running_write_sets[node.id] = node.write_set

    for node in graph.nodes():
        node_id = node.id
        state = node_states.get(node_id, TaskNodeStatus.TODO)
        blockers: list[Blocker] = []

        # Gate: node must be in TODO status
        if state is not TaskNodeStatus.TODO:
            blockers.append(
                Blocker(BlockerKind.GATE, f"status is {state.value}, not todo")
            )

        # Dependency: all predecessors must be done or skipped
        for edge in edges_to[node_id]:
            pred_state = node_states.get(edge.from_id, TaskNodeStatus.TODO)
            if pred_state not in (TaskNodeStatus.DONE, TaskNodeStatus.SKIPPED):
                blockers.append(
                    Blocker(
                        BlockerKind.DEPENDENCY,
                        f"waiting for {edge.from_id} (status: {pred_state.value})",
                    )
                )

        # Resource: no write-set conflict with a running node
        if node.write_set:
            for running_id, running_ws in running_write_sets.items():
                if running_id != node_id and write_sets_overlap(node.write_set, running_ws):
                    blockers.append(
                        Blocker(
                            BlockerKind.RESOURCE,
                            f"write conflict with running node {running_id}",
                        )
                    )

        is_ready = len(blockers) == 0
        checks[node_id] = ReadyCheck(
            node_id=node_id,
            is_ready=is_ready,
            blockers=tuple(blockers),
        )
        if is_ready:
            ready.add(node_id)

    return ReadySetResult(checks=checks, ready_ids=ready)
