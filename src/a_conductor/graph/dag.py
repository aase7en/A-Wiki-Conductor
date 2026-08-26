"""GE-3 — DAG engine: topological sort, ready levels, cycle detection.

Port of A-Wiki ``scripts/eval/dag_eval.py`` semantics with attribution
(ADR GE-0004, decision D1): Kahn's algorithm, cycle path reconstruction,
and parallel-within-level execution ordering.

Credit: the algorithmic core (Kahn topological sort with indegree
tracking, cycle detection via remaining-subgraph DFS walk) originates
from A-Wiki's eval pipeline. This port adds typed DagResult, ready
levels as first-class output, and integration with the GE-1a/1b domain.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Tuple

from .domain import TaskGraph


@dataclass(frozen=True, slots=True)
class DagResult:
    """Result of a topological sort: order + levels + cycle (if any)."""

    order: Tuple[str, ...]
    levels: Tuple[Tuple[str, ...], ...] | None
    cycle: list[str] | None


def topological_sort(graph: TaskGraph) -> DagResult:
    """Kahn's algorithm with ready-level computation and cycle naming.

    Returns a DagResult with:
    - ``order``: a valid topological ordering (empty if cyclic)
    - ``levels``: nodes grouped by parallel-ready wave (None if cyclic)
    - ``cycle``: the actual cycle path as node-id list (None if acyclic)
    """
    nodes = graph.node_ids()
    if not nodes:
        return DagResult(order=(), levels=(), cycle=None)

    indegree: dict[str, int] = {n: 0 for n in nodes}
    adjacency: dict[str, list[str]] = {n: [] for n in nodes}
    for edge in graph.edges():
        adjacency[edge.from_id].append(edge.to_id)
        indegree[edge.to_id] += 1

    # Kahn's algorithm: process nodes with indegree 0, decrement neighbors.
    queue: deque[str] = deque(sorted(n for n in nodes if indegree[n] == 0))
    order: list[str] = []
    levels: list[tuple[str, ...]] = []

    remaining = set(nodes)
    while queue:
        # All nodes currently in the queue are at the same ready level.
        current_level = tuple(sorted(queue))
        levels.append(current_level)
        next_queue: deque[str] = deque()
        for _ in range(len(queue)):
            current = queue.popleft()
            order.append(current)
            remaining.discard(current)
            for neighbor in adjacency[current]:
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    next_queue.append(neighbor)
        queue = next_queue

    if remaining:
        # Cycle detected: reconstruct the actual cycle path via DFS.
        cycle = _reconstruct_cycle(remaining, adjacency)
        return DagResult(order=(), levels=None, cycle=cycle)

    return DagResult(order=tuple(order), levels=tuple(levels), cycle=None)


def compute_ready_levels(graph: TaskGraph) -> list[tuple[str, ...]]:
    """Return nodes grouped by parallel-ready wave (level 0 = no deps)."""
    result = topological_sort(graph)
    if result.cycle is not None:
        raise ValueError(
            "Cannot compute ready levels for a cyclic graph; "
            "cycle: " + " -> ".join(result.cycle)
        )
    return list(result.levels or ())


def validate_acyclic(graph: TaskGraph) -> list[str] | None:
    """Return the cycle path if the graph is cyclic, or None if acyclic."""
    return topological_sort(graph).cycle


def _reconstruct_cycle(
    remaining: set[str], adjacency: dict[str, list[str]]
) -> list[str]:
    """Walk the remaining subgraph to find one actual cycle path."""
    # Build sub-adjacency restricted to remaining nodes.
    sub_adj: dict[str, list[str]] = {
        n: [t for t in adjacency.get(n, []) if t in remaining]
        for n in remaining
    }

    start = sorted(remaining)[0]
    path: list[str] = []
    seen: dict[str, int] = {}

    current: str | None = start
    while current is not None and current not in seen:
        seen[current] = len(path)
        path.append(current)
        neighbors = sub_adj.get(current, [])
        current = neighbors[0] if neighbors else None

    if current is not None and current in seen:
        # Found a node we've already visited — that's the cycle entry.
        return path[seen[current] :] + [current]

    # Shouldn't reach here if remaining is non-empty and all have deps,
    # but return what we have as a safety net.
    return path + [path[0]] if path else list(remaining)
