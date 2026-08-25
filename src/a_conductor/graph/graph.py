"""GE-1b — TaskGraph assembly + structural invariants (ADR GE-0001).

Builds on GE-1a domain. Enforces acyclicity at graph construction time
(Kahn's algorithm — semantics credited to A-Wiki's scripts/eval/dag_eval.py
per ADR GE-0004 decision D1; full DAG engine arrives in GE-3).

Only true predecessor relations participate in ordering (D4 guardrail):
every TaskEdge is a precedence edge for cycle purposes, regardless of
DependencyType, because each accepted type denotes "to_id waits for
from_id" in some dimension.
"""

from __future__ import annotations

from collections import deque
from typing import Iterable

from .domain import TaskEdge, TaskGraph, TaskNode


class GraphCycleError(ValueError):
    """Raised when adding edges would make the graph cyclic."""

    def __init__(self, cycle: list[str]) -> None:
        self.cycle = cycle
        super().__init__(
            "TaskGraph must stay acyclic; cycle detected: " + " -> ".join(cycle)
        )


class TaskGraphBuilder:
    """Assemble a TaskGraph incrementally with full validation.

    Validation happens up-front: every add_* call re-runs cycle detection
    so an invalid graph can never exist (fail-fast invariant).
    """

    def __init__(self) -> None:
        self._graph = TaskGraph()

    def add_node(self, node: TaskNode) -> "TaskGraphBuilder":
        self._graph.add_node(node)
        return self

    def add_edge(self, edge: TaskEdge) -> "TaskGraphBuilder":
        self._graph.add_edge(edge)
        cycle = _find_cycle(self._graph)
        if cycle:
            # Roll back the offending edge before raising.
            self._graph._edges.remove(edge)
            self._graph._edge_keys.discard((edge.from_id, edge.to_id, edge.dep_type))
            raise GraphCycleError(cycle)
        return self

    def build(self) -> TaskGraph:
        return self._graph


def _find_cycle(graph: TaskGraph) -> list[str] | None:
    """Return one cycle as a node-id list, or None if acyclic (Kahn)."""
    nodes = graph.node_ids()
    indegree: dict[str, int] = {n: 0 for n in nodes}
    adjacency: dict[str, list[str]] = {n: [] for n in nodes}
    for edge in graph.edges():
        adjacency[edge.from_id].append(edge.to_id)
        indegree[edge.to_id] += 1

    queue: deque[str] = deque(n for n in nodes if indegree[n] == 0)
    visited = 0
    while queue:
        current = queue.popleft()
        visited += 1
        for neighbor in adjacency[current]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)

    if visited == len(nodes):
        return None

    # Reconstruct one actual cycle from the remaining subgraph via DFS.
    remaining = [n for n in nodes if indegree[n] > 0]
    sub_adj: dict[str, list[str]] = {
        n: [t for t in adjacency[n] if indegree.get(t, 0) > 0] for n in remaining
    }
    start = remaining[0]
    path: list[str] = []
    seen: dict[str, int] = {}
    current = start
    while current not in seen:
        seen[current] = len(path)
        path.append(current)
        current = sub_adj[current][0] if sub_adj[current] else current
    return path[seen[current] :] + [current]


def build_graph(
    nodes: Iterable[TaskNode], edges: Iterable[TaskEdge] = ()
) -> TaskGraph:
    """Convenience assembly: nodes first, then edges, validating as we go."""
    builder = TaskGraphBuilder()
    for node in nodes:
        builder.add_node(node)
    for edge in edges:
        builder.add_edge(edge)
    return builder.build()
