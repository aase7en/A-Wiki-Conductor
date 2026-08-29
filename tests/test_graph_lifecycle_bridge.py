from __future__ import annotations

import pytest

from a_conductor.domain import RecoveryClassification, TaskState
from a_conductor.graph.dispatch import GraphDispatchKey
from a_conductor.graph.domain import TaskNode, TaskNodeStatus
from a_conductor.graph.graph import build_graph
from a_conductor.graph.lifecycle_bridge import (
    GraphLifecycleBridgeError,
    project_graph_node_states,
    project_job_state,
)
from a_conductor.job_state import JobRuntimeState
from a_conductor.job_store import JobStoreError


def _job(state: TaskState, *, job_id: str = "job-1") -> JobRuntimeState:
    return JobRuntimeState(
        job_id=job_id,
        work_order_ref="wo:test",
        project_id="project-1",
        state=state,
        worker_id=None,
        attempt_count=0,
        max_attempts=3,
        recovery_classification=(
            RecoveryClassification.UNKNOWN
            if state is TaskState.RECOVERY_NEEDED
            else None
        ),
        version=1,
    )


def test_task_state_projection_is_explicit_and_exhaustive() -> None:
    expected = {
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
    assert set(expected) == set(TaskState)
    for state, projected in expected.items():
        assert project_job_state(_job(state)) is projected


class FakeJobs:
    def __init__(self, jobs: dict[str, JobRuntimeState]) -> None:
        self.jobs = jobs
        self.calls: list[str] = []
        self.errors: dict[str, JobStoreError] = {}

    def get_job(self, job_id: str) -> JobRuntimeState:
        self.calls.append(job_id)
        if job_id in self.errors:
            raise self.errors[job_id]
        if job_id not in self.jobs:
            raise JobStoreError("JOB_NOT_FOUND")
        return self.jobs[job_id]


def _graph():
    return build_graph(
        [
            TaskNode(id="a", objective="a"),
            TaskNode(id="b", objective="b"),
            TaskNode(id="c", objective="c"),
        ],
        [],
    )


def test_graph_projection_reuses_dispatch_identity_and_missing_is_todo() -> None:
    key_a = GraphDispatchKey("graph-1", "run-1", "a")
    key_b = GraphDispatchKey("graph-1", "run-1", "b")
    key_c = GraphDispatchKey("graph-1", "run-1", "c")
    jobs = FakeJobs(
        {
            key_a.job_id: _job(TaskState.COMPLETE, job_id=key_a.job_id),
            key_b.job_id: _job(TaskState.EXECUTING, job_id=key_b.job_id),
        }
    )

    states = project_graph_node_states(_graph(), "graph-1", "run-1", jobs)

    assert states == {
        "a": TaskNodeStatus.DONE,
        "b": TaskNodeStatus.DOING,
        "c": TaskNodeStatus.TODO,
    }
    assert jobs.calls == [key_a.job_id, key_b.job_id, key_c.job_id]


def test_non_not_found_store_error_propagates_fail_closed() -> None:
    key = GraphDispatchKey("graph-1", "run-1", "a")
    jobs = FakeJobs({})
    jobs.errors[key.job_id] = JobStoreError("JOB_STORE_READ_FAILED")

    with pytest.raises(JobStoreError) as exc:
        project_graph_node_states(_graph(), "graph-1", "run-1", jobs)
    assert exc.value.code == "JOB_STORE_READ_FAILED"


def test_mismatched_durable_job_identity_fails_closed() -> None:
    key = GraphDispatchKey("graph-1", "run-1", "a")
    jobs = FakeJobs(
        {key.job_id: _job(TaskState.COMPLETE, job_id="different-job")}
    )

    with pytest.raises(GraphLifecycleBridgeError) as exc:
        project_graph_node_states(_graph(), "graph-1", "run-1", jobs)
    assert exc.value.code == "GRAPH_JOB_IDENTITY_MISMATCH"


def test_bridge_requires_read_only_get_job_port() -> None:
    class MissingPort:
        pass

    with pytest.raises(ValueError, match="get_job"):
        project_graph_node_states(_graph(), "graph-1", "run-1", MissingPort())


def test_project_job_state_rejects_non_job_state() -> None:
    with pytest.raises(ValueError, match="JobRuntimeState"):
        project_job_state(object())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("predecessor_state", "downstream_ready"),
    [
        (TaskState.COMPLETE, True),
        (TaskState.CANCELLED, True),
        (TaskState.VERIFYING, False),
        (TaskState.CHANGES_REQUIRED, False),
        (TaskState.REPAIRING, False),
        (TaskState.RECOVERY_NEEDED, False),
        (TaskState.FAILED, False),
    ],
)
def test_projection_composes_with_ready_set_without_premature_downstream(
    predecessor_state: TaskState, downstream_ready: bool
) -> None:
    from a_conductor.graph.domain import TaskEdge
    from a_conductor.graph.ready import compute_ready_set

    graph = build_graph(
        [TaskNode(id="a", objective="a"), TaskNode(id="b", objective="b")],
        [TaskEdge("a", "b")],
    )
    key = GraphDispatchKey("graph-1", "run-1", "a")
    jobs = FakeJobs({key.job_id: _job(predecessor_state, job_id=key.job_id)})
    states = project_graph_node_states(graph, "graph-1", "run-1", jobs)
    ready = compute_ready_set(graph, states)
    assert ("b" in ready.ready_ids) is downstream_ready
