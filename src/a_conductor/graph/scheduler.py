"""GE-6 — Pure deterministic scheduler (ADR GE-0006).

schedule_once(...) -> SchedulePlan. NO polling, NO thread, NO dispatch,
NO job transition, NO filesystem mutation, NO UI dependency, NO network.

The scheduler receives ReadySet + worker snapshot + conflicts + policy,
and returns which nodes to assign to which workers. It does NOT launch
anything (that's GE-7 dispatch).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set, Tuple

from .domain import TaskGraph, TaskNode, TaskNodeStatus
from .ready import ReadySetResult


@dataclass(frozen=True, slots=True)
class WorkerSnapshot:
    """Scheduling facts for one worker slot (application port, not UI)."""

    worker_id: str
    state: str = "READY"
    capabilities: Tuple[str, ...] = ()
    reserved: bool = False
    project: str | None = None
    workspace: str | None = None
    mutation_authorized: bool = True


@dataclass(frozen=True, slots=True)
class SchedulePolicy:
    """Injected scheduling configuration (no magic constants)."""

    max_parallel: int = 5


@dataclass(frozen=True, slots=True)
class SelectedAssignment:
    """One node→worker binding chosen by the scheduler."""

    node_id: str
    worker_id: str
    priority: int = 0


@dataclass(frozen=True, slots=True)
class BlockedReason:
    """Why a ready node was not selected."""

    node_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class SchedulePlan:
    """Immutable result of one scheduling pass."""

    selected: Tuple[SelectedAssignment, ...]
    blocked: Tuple[BlockedReason, ...]
    capacity_evidence: str

    @property
    def selected_count(self) -> int:
        return len(self.selected)


def schedule_once(
    graph: TaskGraph,
    ready: ReadySetResult,
    workers: Tuple[WorkerSnapshot, ...],
    policy: SchedulePolicy,
    *,
    running_write_sets: Dict[str, Tuple[str, ...]] | None = None,
) -> SchedulePlan:
    """Pure deterministic scheduling pass.

    Selects from the ReadySet by: priority → node ID (lexical tiebreak).
    Capacity bounded by: max_parallel + available workers.
    Conflicts: both against running nodes AND within the same batch.
    """
    from .analyze import write_sets_overlap

    running_ws = running_write_sets or {}
    selected: list[SelectedAssignment] = []
    blocked: list[BlockedReason] = []
    batch_write_sets: list[tuple[str, ...]] = []  # write sets selected this pass

    # Effective capacity: min of policy max_parallel and unreserved workers
    available_workers = [w for w in workers if w.state == "READY" and not w.reserved]
    effective_capacity = min(policy.max_parallel, len(available_workers))

    # Sort ready nodes: higher priority first, then lexical ID
    ready_nodes = sorted(
        (graph.node(nid) for nid in ready.ready_ids),
        key=lambda n: (-n.priority, n.id),
    )

    worker_iter = iter(available_workers)

    for node in ready_nodes:
        if len(selected) >= effective_capacity:
            blocked.append(BlockedReason(node.id, "capacity: all slots filled"))
            continue

        # Find next available worker with matching capabilities
        assigned_worker = None
        for worker in available_workers:
            if any(s.worker_id == worker.worker_id for s in selected):
                continue
            if all(cap in worker.capabilities for cap in node.worker_requirement):
                if worker.mutation_authorized:
                    assigned_worker = worker
                    break

        if assigned_worker is None:
            if available_workers:
                blocked.append(
                    BlockedReason(node.id, "capability: no matching worker")
                )
            else:
                blocked.append(BlockedReason(node.id, "no available workers"))
            continue

        # Conflict check: against running nodes
        if node.write_set:
            conflict = False
            for running_id, running_paths in running_ws.items():
                if write_sets_overlap(node.write_set, running_paths):
                    blocked.append(
                        BlockedReason(
                            node.id,
                            f"resource conflict with running {running_id}",
                        )
                    )
                    conflict = True
                    break
            if conflict:
                continue

            # Conflict check: within same batch (already selected this pass)
            batch_conflict = False
            for already_selected_ws in batch_write_sets:
                if write_sets_overlap(node.write_set, already_selected_ws):
                    blocked.append(
                        BlockedReason(node.id, "resource conflict in same batch")
                    )
                    batch_conflict = True
                    break
            if batch_conflict:
                continue

        # All checks pass — select
        selected.append(
            SelectedAssignment(
                node_id=node.id,
                worker_id=assigned_worker.worker_id,
                priority=node.priority,
            )
        )
        if node.write_set:
            batch_write_sets.append(node.write_set)

    evidence = (
        f"capacity={effective_capacity}/{policy.max_parallel} "
        f"workers_ready={len(available_workers)}/{len(workers)} "
        f"selected={len(selected)} blocked={len(blocked)}"
    )

    return SchedulePlan(
        selected=tuple(selected),
        blocked=tuple(blocked),
        capacity_evidence=evidence,
    )
