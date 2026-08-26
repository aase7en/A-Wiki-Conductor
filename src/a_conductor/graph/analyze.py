"""GE-4 — dependency analyzer: derive hidden conflicts from node metadata.

Scans a TaskGraph for pairs of nodes whose write_sets, workspace bindings,
or worker bindings collide, producing dependency edges the planner didn't
declare explicitly (D4: only true predecessor relations become edges;
the scheduler decides how to sequence them).

No scheduler or dispatch logic here — this module only *reports* conflicts.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Tuple

from .domain import DependencyType, TaskGraph, TaskNode


@dataclass(frozen=True, slots=True)
class ConflictsReport:
    """All derived conflicts + summary counts."""

    conflicts: Tuple[Tuple[str, str, DependencyType], ...]
    already_sequenced: int  # pairs where the planner already has an edge

    def conflict_count(self, dep_type: DependencyType) -> int:
        return sum(1 for _s, _t, t in self.conflicts if t is dep_type)

    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0


def _parse_binding(node: TaskNode) -> dict[str, str]:
    """Extract workspace/worker bindings from model_requirement.

    Bindings are pipe-separated: ``ws:A:/repo|worker:w1``
    """
    result: dict[str, str] = {}
    if node.model_requirement:
        for part in node.model_requirement.split("|"):
            if ":" in part:
                key, _, val = part.partition(":")
                result[key] = val
    return result


def _paths_overlap(pattern: str, path: str) -> bool:
    """Check if a glob pattern matches a concrete path (or vice versa).

    Handles ``**`` recursive globs by collapsing them to ``*`` for
    fnmatch purposes (``**`` in practice means "any depth including zero").
    """
    # Normalize ** to * for fnmatch compatibility
    norm_pattern = pattern.replace("**/", "*").replace("**", "*")
    norm_path = path.replace("**/", "*").replace("**", "*")
    if fnmatch.fnmatch(norm_path, norm_pattern):
        return True
    if fnmatch.fnmatch(norm_pattern, norm_path):
        return True
    # Direct substring check catches simple prefix overlaps
    if norm_pattern in norm_path or norm_path in norm_pattern:
        return True
    return False


def _write_sets_overlap(a: TaskNode, b: TaskNode) -> bool:
    """Check if two nodes' write sets share at least one path/glob overlap."""
    for a_path in a.write_set:
        for b_path in b.write_set:
            if a_path == b_path:
                return True
            if _paths_overlap(a_path, b_path):
                return True
    return False


def analyze_conflicts(graph: TaskGraph) -> ConflictsReport:
    """Scan for hidden resource conflicts between pairs of nodes.

    Derives FILE_WRITE (overlapping write sets), WORKSPACE_WRITE (same
    workspace), and WORKER (same physical worker) conflicts.
    """
    nodes = graph.nodes()
    conflicts: list[tuple[str, str, DependencyType]] = []
    existing_edges = {(e.from_id, e.to_id) for e in graph.edges()}
    already_sequenced = 0

    for i, node_a in enumerate(nodes):
        for node_b in nodes[i + 1 :]:
            pair = (node_a.id, node_b.id)
            pair_reversed = (node_b.id, node_a.id)

            # FILE_WRITE: overlapping write sets
            if _write_sets_overlap(node_a, node_b):
                if pair in existing_edges or pair_reversed in existing_edges:
                    already_sequenced += 1
                conflicts.append((node_a.id, node_b.id, DependencyType.FILE_WRITE))

            # WORKSPACE_WRITE: same workspace binding
            binding_a = _parse_binding(node_a)
            binding_b = _parse_binding(node_b)
            ws_a = binding_a.get("ws")
            ws_b = binding_b.get("ws")
            if ws_a and ws_b and ws_a == ws_b:
                conflicts.append((node_a.id, node_b.id, DependencyType.WORKSPACE_WRITE))

            # WORKER: same physical worker binding
            worker_a = binding_a.get("worker")
            worker_b = binding_b.get("worker")
            if worker_a and worker_b and worker_a == worker_b:
                conflicts.append((node_a.id, node_b.id, DependencyType.WORKER))

    return ConflictsReport(
        conflicts=tuple(conflicts),
        already_sequenced=already_sequenced,
    )
