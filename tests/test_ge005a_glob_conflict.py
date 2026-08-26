"""WO-GE-005A — ReadySet must reuse GE-4 glob-aware conflict semantics.

Defect: ready.py's _write_sets_conflict used literal string equality,
so a running node writing `src/**/*.py` and a TODO node writing
`src/specific.py` were incorrectly considered conflict-free.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from a_conductor.graph.domain import TaskNode, TaskNodeStatus
from a_conductor.graph.graph import build_graph
from a_conductor.graph.ready import compute_ready_set


def _node(
    node_id: str,
    status: TaskNodeStatus = TaskNodeStatus.TODO,
    write_set: tuple[str, ...] = (),
) -> TaskNode:
    return TaskNode(
        id=node_id,
        objective=f"obj {node_id}",
        status=status,
        write_set=write_set,
    )


# --- glob vs literal must conflict in ReadySet (the GE-005A defect) ----------


def test_glob_running_blocks_literal_todo() -> None:
    """Running `src/**/*.py` must block TODO `src/specific.py`."""
    graph = build_graph(
        [
            _node("running", status=TaskNodeStatus.DOING, write_set=("src/**/*.py",)),
            _node("todo", write_set=("src/specific.py",)),
        ],
        [],
    )
    result = compute_ready_set(graph, {"running": TaskNodeStatus.DOING})
    assert "todo" not in result.ready_ids, (
        "GE-005A defect: glob `src/**/*.py` should block literal `src/specific.py`"
    )
    blockers = result.checks["todo"].blockers
    assert any("running" in b.detail for b in blockers)


def test_literal_running_blocks_glob_todo() -> None:
    """Running `src/specific.py` must block TODO `src/**/*.py` (reverse orientation)."""
    graph = build_graph(
        [
            _node("running", status=TaskNodeStatus.DOING, write_set=("src/specific.py",)),
            _node("todo", write_set=("src/**/*.py",)),
        ],
        [],
    )
    result = compute_ready_set(graph, {"running": TaskNodeStatus.DOING})
    assert "todo" not in result.ready_ids


def test_disjoint_paths_still_ready() -> None:
    """Non-overlapping write sets must NOT conflict."""
    graph = build_graph(
        [
            _node("running", status=TaskNodeStatus.DOING, write_set=("src/a/*.py",)),
            _node("todo", write_set=("docs/*.md",)),
        ],
        [],
    )
    result = compute_ready_set(graph, {"running": TaskNodeStatus.DOING})
    assert "todo" in result.ready_ids


def test_partial_glob_overlap_conflicts() -> None:
    """`src/**/*.py` overlaps `src/sub/deep.py` through recursive glob."""
    graph = build_graph(
        [
            _node("r", status=TaskNodeStatus.DOING, write_set=("src/**/*.py",)),
            _node("t", write_set=("src/sub/deep.py",)),
        ],
        [],
    )
    result = compute_ready_set(graph, {"r": TaskNodeStatus.DOING})
    assert "t" not in result.ready_ids


def test_wildcard_conflicts_with_exact() -> None:
    """`*.py` overlaps `anything.py` via fnmatch wildcard."""
    graph = build_graph(
        [
            _node("r", status=TaskNodeStatus.DOING, write_set=("*.py",)),
            _node("t", write_set=("anything.py",)),
        ],
        [],
    )
    result = compute_ready_set(graph, {"r": TaskNodeStatus.DOING})
    assert "t" not in result.ready_ids
