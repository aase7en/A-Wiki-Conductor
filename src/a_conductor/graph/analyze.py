"""GE-4 — dependency analyzer: derive hidden conflicts from node metadata.

Scans a TaskGraph for pairs of nodes whose write_sets, workspace bindings,
or worker bindings collide, producing dependency edges the planner didn't
declare explicitly (D4: only true predecessor relations become edges;
the scheduler decides how to sequence them).

No scheduler or dispatch logic here — this module only *reports* conflicts.
"""

from __future__ import annotations

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


def _tokenize_glob(pattern: str) -> tuple[str, ...]:
    """Tokenize a glob into ``*`` / ``?`` / single-character tokens.

    fnmatch character classes (``[...]``) are treated conservatively as a
    single-character wildcard: for a write-conflict seam, over-detecting a
    conflict is safe while under-detecting is the defect.
    """
    tokens: list[str] = []
    i = 0
    length = len(pattern)
    while i < length:
        char = pattern[i]
        if char == "*":
            tokens.append("*")
            i += 1
        elif char == "?":
            tokens.append("?")
            i += 1
        elif char == "[":
            j = i + 1
            if j < length and pattern[j] in "!^":
                j += 1
            if j < length and pattern[j] == "]":
                j += 1  # a leading ']' is a literal member, not the closer
            while j < length and pattern[j] != "]":
                j += 1
            tokens.append("?")
            i = j + 1 if j < length else length
        else:
            tokens.append(char)
            i += 1
    return tuple(tokens)


def _globs_share_a_path(a: tuple[str, ...], b: tuple[str, ...]) -> bool:
    """True when one concrete path can be matched by both token globs.

    Deterministic glob-vs-glob intersection via memoized two-pointer
    matching: a ``*`` may match empty, any run of the other side's
    literal characters, or pair with the other side's ``*``/``?``.
    """
    memo: dict[tuple[int, int], bool] = {}

    def visit(i: int, j: int) -> bool:
        key = (i, j)
        if key in memo:
            return memo[key]
        if i == len(a) and j == len(b):
            return True
        if i == len(a):
            return all(token == "*" for token in b[j:])
        if j == len(b):
            return all(token == "*" for token in a[i:])
        token_a = a[i]
        token_b = b[j]
        if token_a == "*" or token_b == "*":
            # At least one wildcard: it may match empty (advance its side)
            # or consume one matched character (advance the other side).
            result = visit(i + 1, j) or visit(i, j + 1)
        elif token_a == "?" or token_b == "?" or token_a == token_b:
            result = visit(i + 1, j + 1)
        else:
            result = False
        memo[key] = result
        return result

    return visit(0, 0)


def paths_overlap(pattern: str, path: str) -> bool:
    """Authoritative glob-aware path overlap check (WO-GE-005A).

    Deterministic glob-vs-glob intersection: True when some concrete
    path is matched by BOTH expressions. ``**`` collapses to ``*``
    (fnmatch has no path-segment awareness). Distinct literals that mere
    share a prefix/suffix (``src/a.py`` vs ``src/a.py.bak``) do NOT
    overlap; two wildcards whose match sets intersect (``src/*/a.py`` vs
    ``src/x/*.py`` share ``src/x/a.py``) DO overlap.

    This is the single seam consumed by both GE-4 (analyze_conflicts)
    and GE-5 (compute_ready_set) — no second overlap algorithm allowed.
    """
    norm_pattern = pattern.replace("**/", "*").replace("**", "*")
    norm_path = path.replace("**/", "*").replace("**", "*")
    return _globs_share_a_path(
        _tokenize_glob(norm_pattern), _tokenize_glob(norm_path)
    )


def write_sets_overlap(a_set: tuple[str, ...], b_set: tuple[str, ...]) -> bool:
    """Check if two write-set tuples share at least one glob-aware overlap.

    This is the single authoritative seam for write-conflict detection.
    Both GE-4 analyzer and GE-5 ReadySet must call this — no separate
    literal-equality copies.
    """
    for a_path in a_set:
        for b_path in b_set:
            if a_path == b_path:
                return True
            if paths_overlap(a_path, b_path):
                return True
    return False


def _write_sets_overlap(a: TaskNode, b: TaskNode) -> bool:
    """Node-level wrapper over the authoritative write_sets_overlap seam."""
    return write_sets_overlap(a.write_set, b.write_set)


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
