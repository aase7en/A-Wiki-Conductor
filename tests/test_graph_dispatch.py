from __future__ import annotations

from pathlib import Path

import pytest

from a_conductor.domain import TaskState
from a_conductor.graph.dispatch import (
    DispatchGateDecision,
    GraphDispatchAction,
    GraphDispatchCoordinator,
    GraphDispatchError,
    GraphDispatchKey,
    GraphDispatchMode,
    GraphDispatchRequest,
    StaticWorkerDispatchModeResolver,
)
from a_conductor.graph.scheduler import SelectedAssignment
from a_conductor.job_control import DurableJobControlService
from a_conductor.job_store import JobEventType, JobStoreError
from a_conductor.native_execution import NativeCommandResult
from a_conductor.native_operations import (
    NativeOperationDefinition,
    NativeOperationKind,
    WorkerNativeAdapters,
)


def _result_ok() -> NativeCommandResult:
    return NativeCommandResult(
        executable="python.exe", argument_count=3, exit_code=0, timed_out=False,
        stdout="ok", stderr="", stdout_sha256="a" * 64, stderr_sha256="b" * 64,
        stdout_truncated=False, stderr_truncated=False,
    )

class FakeGit:
    def status_short(self, *, timeout_seconds=10):
        return _result_ok()

    def working_diff(self, paths=(), *, timeout_seconds=15):
        return _result_ok()

    def cached_diff(self, paths=(), *, timeout_seconds=15):
        return _result_ok()


class FakeVerification:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[str, tuple[str, ...], int]] = []

    def pytest(self, paths=("tests",), *, timeout_seconds=120):
        self.calls.append(("pytest", tuple(paths), timeout_seconds))
        if self.fail:
            raise RuntimeError("backend uncertainty")
        return _result_ok()

    def compileall(self, paths=("src",), *, timeout_seconds=120):
        return _result_ok()


class FakeResolver:
    def __init__(self, *, fail: bool = False) -> None:
        self.verification = FakeVerification(fail=fail)
        self.calls: list[str] = []
    def resolve(self, worker_id: str) -> WorkerNativeAdapters:
        self.calls.append(worker_id)
        return WorkerNativeAdapters(git=FakeGit(), verification=self.verification)


def _open_service(tmp_path: Path, *, fail: bool = False):
    resolver = FakeResolver(fail=fail)
    service = DurableJobControlService.open(
        tmp_path / "control.sqlite",
        operations=(
            NativeOperationDefinition(
                operation_ref="op:graph-pytest",
                kind=NativeOperationKind.PYTEST,
                paths=("tests/test_graph_dispatch.py",),
                timeout_seconds=30,
            ),
        ),
        native_resolver=resolver,
    )
    return service, resolver


def _request(*, run_id: str = "run-1", project_id: str = "project-1", worker_id: str = "a-worker-01"):
    return GraphDispatchRequest(
        key=GraphDispatchKey("graph-1", run_id, "node-1"),
        assignment=SelectedAssignment(node_id="node-1", worker_id=worker_id, priority=3),
        project_id=project_id,
        work_order_ref="docs/work-orders/WO-P1-094-aha4-durable-graph-dispatch.md",
        operation_ref="op:graph-pytest",
        dispatch_mode=GraphDispatchMode.PROGRAMMATIC_PUSH,
        max_attempts=3,
    )

def test_dispatch_key_is_stable_and_graph_run_scoped() -> None:
    first = GraphDispatchKey("graph-1", "run-1", "node-1")
    same = GraphDispatchKey("graph-1", "run-1", "node-1")
    other_run = GraphDispatchKey("graph-1", "run-2", "node-1")

    assert first.job_id == same.job_id
    assert first.job_id.startswith("graph-dispatch-")
    assert len(first.job_id.removeprefix("graph-dispatch-")) == 64
    assert first.job_id != other_run.job_id


def test_same_key_reuses_one_job_and_does_not_execute_twice(tmp_path: Path) -> None:
    service, resolver = _open_service(tmp_path)
    coordinator = _coordinator(service)

    first = coordinator.dispatch(_request(), gate=DispatchGateDecision.allow())
    second = coordinator.dispatch(_request(), gate=DispatchGateDecision.allow())

    assert first.action is GraphDispatchAction.EXECUTED
    assert first.job.state is TaskState.VERIFYING
    assert second.action is GraphDispatchAction.EXISTING
    assert second.job == first.job
    assert resolver.calls == ["a-worker-01"]
    created = [e for e in service.list_events(first.job.job_id) if e.event_type is JobEventType.CREATED]
    assert len(created) == 1


def test_different_graph_runs_create_distinct_jobs(tmp_path: Path) -> None:
    service, _ = _open_service(tmp_path)
    coordinator = _coordinator(service)
    one = coordinator.dispatch(_request(run_id="run-1"), gate=DispatchGateDecision.deny("NO_GO"))
    two = coordinator.dispatch(_request(run_id="run-2"), gate=DispatchGateDecision.deny("NO_GO"))
    assert one.job.job_id != two.job.job_id

def test_exact_scheduled_worker_is_claimed_and_used(tmp_path: Path) -> None:
    service, resolver = _open_service(tmp_path)
    result = _coordinator(service).dispatch(
        _request(worker_id="a-worker-02"), gate=DispatchGateDecision.allow()
    )
    assert result.action is GraphDispatchAction.EXECUTED
    assert result.job.worker_id == "a-worker-02"
    assert resolver.calls == ["a-worker-02"]


def test_gate_no_go_blocks_before_attempt_and_can_resume(tmp_path: Path) -> None:
    service, resolver = _open_service(tmp_path)
    coordinator = _coordinator(service)

    blocked = coordinator.dispatch(
        _request(), gate=DispatchGateDecision.deny("HUMAN_APPROVAL_WAIT", evidence_ref="gate:e1")
    )
    assert blocked.action is GraphDispatchAction.BLOCKED
    assert blocked.job.state is TaskState.BLOCKED
    assert blocked.job.attempt_count == 0
    assert blocked.job.worker_id is None
    assert resolver.calls == []

    resumed = coordinator.dispatch(_request(), gate=DispatchGateDecision.allow())
    assert resumed.action is GraphDispatchAction.EXECUTED
    assert resumed.job.state is TaskState.VERIFYING
    assert resumed.job.attempt_count == 1
    assert resolver.calls == ["a-worker-01"]


def test_backend_uncertainty_enters_recovery_and_retry_does_not_relaunch(tmp_path: Path) -> None:
    service, resolver = _open_service(tmp_path, fail=True)
    coordinator = _coordinator(service)
    first = coordinator.dispatch(_request(), gate=DispatchGateDecision.allow())
    second = coordinator.dispatch(_request(), gate=DispatchGateDecision.allow())

    assert first.action is GraphDispatchAction.RECONCILE
    assert first.job.state is TaskState.RECOVERY_NEEDED
    assert first.job.attempt_count == 1
    assert second.action is GraphDispatchAction.RECONCILE
    assert second.job == first.job
    assert resolver.calls == ["a-worker-01"]

class RacingService:
    """Inject one optimistic-version race before worker claim."""

    def __init__(self, inner: DurableJobControlService) -> None:
        self.inner = inner
        self.raced = False
        self.execute_calls = 0

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def claim(self, job_id: str, *, expected_version: int, worker_id: str):
        if not self.raced:
            self.raced = True
            self.inner.checkpoint(
                job_id,
                expected_version=expected_version,
                checkpoint_ref="race:version-bump",
            )
        return self.inner.claim(
            job_id, expected_version=expected_version, worker_id=worker_id
        )

    def execute_operation(self, *args, **kwargs):
        self.execute_calls += 1
        return self.inner.execute_operation(*args, **kwargs)


def test_stale_claim_version_reconciles_without_external_execution(tmp_path: Path) -> None:
    service, resolver = _open_service(tmp_path)
    racing = RacingService(service)
    result = _coordinator(racing).dispatch(
        _request(), gate=DispatchGateDecision.allow()
    )
    assert result.action is GraphDispatchAction.RECONCILE
    assert result.reason_code == "JOB_VERSION_CONFLICT"
    assert result.job.state is TaskState.READY
    assert result.job.attempt_count == 0
    assert racing.execute_calls == 0
    assert resolver.calls == []

def test_same_dispatch_key_with_different_project_fails_closed(tmp_path: Path) -> None:
    service, _ = _open_service(tmp_path)
    coordinator = _coordinator(service)
    coordinator.dispatch(_request(project_id="project-1"), gate=DispatchGateDecision.deny("NO_GO"))

    with pytest.raises(GraphDispatchError) as exc_info:
        coordinator.dispatch(
            _request(project_id="project-2"), gate=DispatchGateDecision.allow()
        )
    assert exc_info.value.code == "DISPATCH_JOB_IDENTITY_MISMATCH"


def test_request_node_must_match_scheduler_assignment() -> None:
    with pytest.raises(ValueError):
        GraphDispatchRequest(
            key=GraphDispatchKey("graph-1", "run-1", "node-a"),
            assignment=SelectedAssignment(node_id="node-b", worker_id="a-worker-01"),
            project_id="project-1",
            work_order_ref="wo",
            operation_ref="op:graph-pytest",
            dispatch_mode=GraphDispatchMode.PROGRAMMATIC_PUSH,
        )

def test_interactive_pull_is_durably_offered_without_fake_push(tmp_path: Path) -> None:
    service, resolver = _open_service(tmp_path)
    request = GraphDispatchRequest(
        key=GraphDispatchKey("graph-1", "run-pull", "node-1"),
        assignment=SelectedAssignment(node_id="node-1", worker_id="a-worker-01"),
        project_id="project-1",
        work_order_ref="wo-pull",
        operation_ref="op:graph-pytest",
        dispatch_mode=GraphDispatchMode.INTERACTIVE_PULL,
    )
    coordinator = _coordinator(
        service, modes={"a-worker-01": GraphDispatchMode.INTERACTIVE_PULL}
    )
    first = coordinator.dispatch(request, gate=DispatchGateDecision.allow())
    second = coordinator.dispatch(request, gate=DispatchGateDecision.allow())

    assert first.action is GraphDispatchAction.OFFERED
    assert first.job.state is TaskState.CLAIMED
    assert first.job.attempt_count == 0
    assert second.action is GraphDispatchAction.OFFERED
    assert second.job == first.job
    assert resolver.calls == []


def test_allow_gate_evidence_is_persisted_before_execution(tmp_path: Path) -> None:
    service, _ = _open_service(tmp_path)
    result = _coordinator(service).dispatch(
        _request(), gate=DispatchGateDecision.allow(evidence_ref="gate:allow:e1")
    )
    gating_event = next(
        event for event in service.list_events(result.job.job_id)
        if event.to_state is TaskState.GATING
    )
    assert gating_event.evidence_ref == "gate:allow:e1"

def test_same_key_with_different_operation_fails_closed(tmp_path: Path) -> None:
    service, _ = _open_service(tmp_path)
    coordinator = _coordinator(service)
    coordinator.dispatch(_request(), gate=DispatchGateDecision.deny("NO_GO"))
    original = _request()
    changed = GraphDispatchRequest(
        key=original.key,
        assignment=original.assignment,
        project_id=original.project_id,
        work_order_ref=original.work_order_ref,
        operation_ref="op:different",
        dispatch_mode=original.dispatch_mode,
        max_attempts=original.max_attempts,
    )
    with pytest.raises(GraphDispatchError) as exc_info:
        coordinator.dispatch(changed, gate=DispatchGateDecision.allow())
    assert exc_info.value.code == "DISPATCH_JOB_IDENTITY_MISMATCH"


def test_same_key_with_different_dispatch_mode_fails_closed(tmp_path: Path) -> None:
    service, _ = _open_service(tmp_path)
    coordinator = _coordinator(service)
    coordinator.dispatch(_request(), gate=DispatchGateDecision.deny("NO_GO"))
    original = _request()
    changed = GraphDispatchRequest(
        key=original.key,
        assignment=original.assignment,
        project_id=original.project_id,
        work_order_ref=original.work_order_ref,
        operation_ref=original.operation_ref,
        dispatch_mode=GraphDispatchMode.INTERACTIVE_PULL,
        max_attempts=original.max_attempts,
    )
    changed_mode_coordinator = _coordinator(
        service, modes={"a-worker-01": GraphDispatchMode.INTERACTIVE_PULL}
    )
    with pytest.raises(GraphDispatchError) as exc_info:
        changed_mode_coordinator.dispatch(changed, gate=DispatchGateDecision.allow())
    assert exc_info.value.code == "DISPATCH_JOB_IDENTITY_MISMATCH"

class LostAfterGateService:
    """Simulate observer transport loss after the durable GATING write."""

    def __init__(self, inner: DurableJobControlService) -> None:
        self.inner = inner
        self.lost = False
        self.execute_calls = 0

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def gate(self, job_id: str, **kwargs):
        gated = self.inner.gate(job_id, **kwargs)
        if not self.lost:
            self.lost = True
            raise JobStoreError("JOB_VERSION_CONFLICT")
        return gated

    def execute_operation(self, *args, **kwargs):
        self.execute_calls += 1
        return self.inner.execute_operation(*args, **kwargs)


def test_transport_loss_after_gating_reconciles_then_resumes_once(tmp_path: Path) -> None:
    service, resolver = _open_service(tmp_path)
    lossy = LostAfterGateService(service)
    coordinator = _coordinator(lossy)

    first = coordinator.dispatch(
        _request(), gate=DispatchGateDecision.allow(evidence_ref="gate:allow:e2")
    )
    assert first.action is GraphDispatchAction.RECONCILE
    assert first.reason_code == "JOB_VERSION_CONFLICT"
    assert first.job.state is TaskState.GATING
    assert first.job.attempt_count == 0
    assert lossy.execute_calls == 0
    assert resolver.calls == []

    second = coordinator.dispatch(_request(), gate=DispatchGateDecision.allow())
    assert second.action is GraphDispatchAction.EXECUTED
    assert second.job.state is TaskState.VERIFYING
    assert second.job.attempt_count == 1
    assert lossy.execute_calls == 1
    assert resolver.calls == ["a-worker-01"]


class SelectiveResolver:
    def __init__(self, *, failing_workers: set[str]) -> None:
        self.failing_workers = set(failing_workers)
        self.calls: list[str] = []
        self.verifications: dict[str, FakeVerification] = {}

    def resolve(self, worker_id: str) -> WorkerNativeAdapters:
        self.calls.append(worker_id)
        verification = self.verifications.setdefault(
            worker_id,
            FakeVerification(fail=worker_id in self.failing_workers),
        )
        return WorkerNativeAdapters(git=FakeGit(), verification=verification)


def _open_selective_service(tmp_path: Path, failing_workers: set[str]):
    resolver = SelectiveResolver(failing_workers=failing_workers)
    service = DurableJobControlService.open(
        tmp_path / "control.sqlite",
        operations=(
            NativeOperationDefinition(
                operation_ref="op:graph-pytest",
                kind=NativeOperationKind.PYTEST,
                paths=("tests/test_graph_dispatch.py",),
                timeout_seconds=30,
            ),
        ),
        native_resolver=resolver,
    )
    return service, resolver

def _coordinator(service, *, modes=None):
    mapping = modes or {
        "a-worker-01": GraphDispatchMode.PROGRAMMATIC_PUSH,
        "a-worker-02": GraphDispatchMode.PROGRAMMATIC_PUSH,
    }
    return GraphDispatchCoordinator(
        service=service,
        mode_resolver=StaticWorkerDispatchModeResolver(mapping),
    )


def test_one_node_failure_does_not_corrupt_independent_dispatch(tmp_path: Path) -> None:
    service, resolver = _open_selective_service(
        tmp_path, failing_workers={"a-worker-01"}
    )
    coordinator = _coordinator(service)

    failed = coordinator.dispatch(
        _request(run_id="run-fail", worker_id="a-worker-01"),
        gate=DispatchGateDecision.allow(),
    )
    healthy = coordinator.dispatch(
        _request(run_id="run-ok", worker_id="a-worker-02"),
        gate=DispatchGateDecision.allow(),
    )

    assert failed.action is GraphDispatchAction.RECONCILE
    assert failed.job.state is TaskState.RECOVERY_NEEDED
    assert healthy.action is GraphDispatchAction.EXECUTED
    assert healthy.job.state is TaskState.VERIFYING
    assert failed.job.job_id != healthy.job.job_id
    assert resolver.calls == ["a-worker-01", "a-worker-02"]


def test_unknown_worker_dispatch_mode_fails_closed_before_job_creation(tmp_path: Path) -> None:
    service, resolver = _open_service(tmp_path)
    coordinator = _coordinator(service, modes={"a-worker-02": GraphDispatchMode.PROGRAMMATIC_PUSH})

    with pytest.raises(GraphDispatchError) as exc_info:
        coordinator.dispatch(_request(), gate=DispatchGateDecision.allow())

    assert exc_info.value.code == "DISPATCH_MODE_UNKNOWN"
    assert resolver.calls == []
    with pytest.raises(JobStoreError) as job_exc:
        service.get_job(_request().key.job_id)
    assert job_exc.value.code == "JOB_NOT_FOUND"


def test_request_dispatch_mode_must_match_authoritative_worker_mode(tmp_path: Path) -> None:
    service, resolver = _open_service(tmp_path)
    coordinator = _coordinator(
        service, modes={"a-worker-01": GraphDispatchMode.INTERACTIVE_PULL}
    )

    with pytest.raises(GraphDispatchError) as exc_info:
        coordinator.dispatch(_request(), gate=DispatchGateDecision.allow())

    assert exc_info.value.code == "DISPATCH_MODE_MISMATCH"
    assert resolver.calls == []
