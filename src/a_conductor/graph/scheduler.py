"""GE-6 — Pure deterministic scheduler (ADR GE-0006).

schedule_once(...) -> SchedulePlan. NO polling, NO thread, NO dispatch,
NO job transition, NO filesystem mutation, NO UI dependency, NO network.

The scheduler receives ReadySet + worker snapshot + conflicts + policy,
and returns which nodes to assign to which workers. It does NOT launch
anything (that's GE-7 dispatch).

Ordering (D6-CAP): priority -> earlier topological rank -> lexical node ID.
Equivalent workers are chosen in stable worker-ID order (an explicit
binding/policy override may later take precedence; none exists yet).
Mutating nodes (non-empty write_set) require matching project/workspace
identity plus worker mutation authority, failing closed on missing or
ambiguous identity; read-only nodes are not blocked by mutation authority.
Gate/provider eligibility is an injected, deterministic input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set, Tuple

from .analyze import _parse_binding, write_sets_overlap
from .dag import topological_sort
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
class NodeEligibility:
    """Injected gate/provider eligibility facts for one node.

    Deterministic input only: the scheduler never probes gates or
    providers. Any refusal blocks the node without reserving a worker
    or dispatching anything (GE-7 stays out of scope).
    """

    gate_refused: bool = False
    provider_unavailable: bool = False
    rate_limited: bool = False

    @property
    def eligible(self) -> bool:
        return not (self.gate_refused or self.provider_unavailable or self.rate_limited)

    @property
    def reason(self) -> str:
        if self.gate_refused:
            return "gate refusal (NO-GO)"
        if self.provider_unavailable:
            return "provider unavailable"
        if self.rate_limited:
            return "rate limited / quota exhausted"
        return "eligible"


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


def _topological_rank(graph: TaskGraph) -> Dict[str, int]:
    """Deterministic Kahn topological rank per node (D6-CAP ordering)."""
    result = topological_sort(graph)
    if not result.order:
        return {}
    return {node_id: index for index, node_id in enumerate(result.order)}


def _node_identity(node: TaskNode) -> Tuple[str | None, str | None]:
    """Project/workspace identity carried by the node binding convention.

    Reuses the single ``ws:...|worker:...|project:...`` binding parser
    from the GE-4 analyzer; no second parser is introduced.
    """
    binding = _parse_binding(node)
    return binding.get("project"), binding.get("ws")


def _worker_identity_allows(
    worker: WorkerSnapshot,
    node_project: str | None,
    node_workspace: str | None,
    mutating: bool,
) -> bool:
    if not mutating:
        return True
    if node_project is not None and worker.project != node_project:
        return False
    if node_workspace is not None and worker.workspace != node_workspace:
        return False
    if not worker.mutation_authorized:
        return False
    return True


def schedule_once(
    graph: TaskGraph,
    ready: ReadySetResult,
    workers: Tuple[WorkerSnapshot, ...],
    policy: SchedulePolicy,
    *,
    running_write_sets: Dict[str, Tuple[str, ...]] | None = None,
    eligibility: Dict[str, NodeEligibility] | None = None,
) -> SchedulePlan:
    """Pure deterministic scheduling pass.

    Selects from the ReadySet by: priority → topological rank → node ID
    (lexical tie-break). Capacity bounded by: max_parallel + available
    workers. Conflicts: both against running nodes AND within the same
    batch, always through the single ``write_sets_overlap`` seam.
    Mutating nodes additionally require matching identity + authority.
    Ineligible nodes (gate/provider/quota) are blocked before any
    worker is considered.
    """
    running_ws = running_write_sets or {}
    eligibility_map = eligibility or {}
    selected: list[SelectedAssignment] = []
    blocked: list[BlockedReason] = []
    batch_write_sets: list[tuple[str, ...]] = []  # write sets selected this pass

    # Effective capacity: min of policy max_parallel and unreserved workers
    available_workers = [w for w in workers if w.state == "READY" and not w.reserved]
    # Stable worker-ID order: equivalent candidates must not depend on input order.
    available_workers.sort(key=lambda w: w.worker_id)
    effective_capacity = min(policy.max_parallel, len(available_workers))

    # Deterministic topological rank for same-priority ordering.
    topo_rank = _topological_rank(graph)

    # Sort ready nodes: higher priority, earlier topological rank, lexical ID
    ready_nodes = sorted(
        (graph.node(nid) for nid in ready.ready_ids),
        key=lambda n: (-n.priority, topo_rank.get(n.id, len(topo_rank)), n.id),
    )

    for node in ready_nodes:
        # Injected gate/provider eligibility first: block without reserving.
        node_eligibility = eligibility_map.get(node.id)
        if node_eligibility is not None and not node_eligibility.eligible:
            blocked.append(
                BlockedReason(
                    node.id, f"eligibility: {node_eligibility.reason}"
                )
            )
            continue

        if len(selected) >= effective_capacity:
            blocked.append(BlockedReason(node.id, "capacity: all slots filled"))
            continue

        mutating = bool(node.write_set)
        if mutating:
            node_project, node_workspace = _node_identity(node)
            if node_project is None and node_workspace is None:
                blocked.append(
                    BlockedReason(
                        node.id,
                        "identity: mutating node lacks project/workspace "
                        "binding (fail closed)",
                    )
                )
                continue
        else:
            node_project = node_workspace = None

        # Find a worker: capability match, then identity/authority when mutating.
        assigned_worker = None
        capability_matched = False
        identity_or_authority_matched = False
        for worker in available_workers:
            if any(s.worker_id == worker.worker_id for s in selected):
                continue
            if not all(cap in worker.capabilities for cap in node.worker_requirement):
                continue
            capability_matched = True
            if not _worker_identity_allows(
                worker, node_project, node_workspace, mutating
            ):
                continue
            identity_or_authority_matched = True
            assigned_worker = worker
            break

        if assigned_worker is None:
            if not available_workers:
                blocked.append(BlockedReason(node.id, "no available workers"))
            elif not capability_matched:
                blocked.append(
                    BlockedReason(node.id, "capability: no matching worker")
                )
            elif mutating and not identity_or_authority_matched:
                blocked.append(
                    BlockedReason(
                        node.id,
                        "identity: no worker with matching project/workspace "
                        "identity and mutation authority",
                    )
                )
            else:
                blocked.append(BlockedReason(node.id, "capability: no matching worker"))
            continue

        # Conflict check: against running nodes (single GE-4/GE-005A seam)
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
