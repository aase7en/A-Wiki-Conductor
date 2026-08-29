"""GE-9 read-only durable lifecycle -> graph status projection.

The durable job state machine remains authoritative. This module only projects
that truth into ``TaskNodeStatus`` for graph readiness/operator consumers; it
cannot create, transition, checkpoint, retry, dispatch, or mutate either store.
"""

from __future__ import annotations

from typing import Protocol

from ..domain import TaskState
from ..job_state import JobRuntimeState
from ..job_store import JobStoreError
from .dispatch import GraphDispatchKey
from .domain import TaskGraph, TaskNodeStatus


class GraphLifecycleBridgeError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class GraphJobStateReader(Protocol):
    def get_job(self, job_id: str) -> JobRuntimeState: ...


_TASK_STATE_PROJECTION = {
    TaskState.NEW: TaskNodeStatus.TODO,
    TaskState.PLANNING: TaskNodeStatus.TODO,
    TaskState.READY: TaskNodeStatus.TODO,
    TaskState.CLAIMED: TaskNodeStatus.DOING,
    TaskState.GATING: TaskNodeStatus.DOING,
    TaskState.EXECUTING: TaskNodeStatus.DOING,
    TaskState.VERIFYING: TaskNodeStatus.DOING,
    TaskState.REVIEW_PENDING: TaskNodeStatus.DOING,
    TaskState.CHANGES_REQUIRED: TaskNodeStatus.DOING,
    TaskState.REPAIRING: TaskNodeStatus.DOING,
    TaskState.BLOCKED: TaskNodeStatus.BLOCKED,
    TaskState.RECOVERY_NEEDED: TaskNodeStatus.BLOCKED,
    TaskState.COMPLETE: TaskNodeStatus.DONE,
    TaskState.FAILED: TaskNodeStatus.BLOCKED,
    TaskState.CANCELLED: TaskNodeStatus.SKIPPED,
}


def project_job_state(job: JobRuntimeState) -> TaskNodeStatus:
    """Pure exhaustive projection of one durable job runtime state."""

    if not isinstance(job, JobRuntimeState):
        raise ValueError("job must be JobRuntimeState")
    try:
        return _TASK_STATE_PROJECTION[job.state]
    except KeyError as exc:
        raise GraphLifecycleBridgeError("TASK_STATE_UNCLASSIFIED") from exc


def project_graph_node_states(
    graph: TaskGraph,
    graph_id: str,
    graph_run_id: str,
    jobs: GraphJobStateReader,
) -> dict[str, TaskNodeStatus]:
    """Read durable graph-run jobs and project node states without mutation."""

    if not isinstance(graph, TaskGraph):
        raise ValueError("graph must be TaskGraph")
    get_job = getattr(jobs, "get_job", None)
    if not callable(get_job):
        raise ValueError("jobs must provide read-only get_job")

    projected: dict[str, TaskNodeStatus] = {}
    for node in graph.nodes():
        key = GraphDispatchKey(graph_id, graph_run_id, node.id)
        try:
            job = get_job(key.job_id)
        except JobStoreError as exc:
            if exc.code != "JOB_NOT_FOUND":
                raise
            projected[node.id] = TaskNodeStatus.TODO
            continue
        if not isinstance(job, JobRuntimeState):
            raise GraphLifecycleBridgeError("GRAPH_JOB_INVALID")
        if job.job_id != key.job_id:
            raise GraphLifecycleBridgeError("GRAPH_JOB_IDENTITY_MISMATCH")
        projected[node.id] = project_job_state(job)
    return projected
