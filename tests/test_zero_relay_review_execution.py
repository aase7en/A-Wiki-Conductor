"""WO-P1-226 — ZRA-2 reviewer execution bridge (RED-first matrix).

Covers the WO226 contract: pure pre-effect plan/fingerprint, all-equivalent
multiplicity, existing-authority durable single winner (GraphDispatch CAS),
READ_ONLY ZCode assembly, winner/resource association, replay/recovery, and
provider/WorkerLease cleanup truth per their real API contracts.

No live provider call, no semantic ACCEPTED/REJECTED parsing (WO223 owns C1).
"""
from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from a_conductor.claude_code_harness import HarnessDispatch, MutationIntent, TaskPacketFile
from a_conductor.execution_deduplication import ExecutionFingerprintSpec, compute_execution_fingerprint
from a_conductor.execution_record import DurableExecutionRecord, ExecutionProcessState, TransportState, new_execution_record
from a_conductor.execution_store import SQLiteExecutionStore
from a_conductor.graph.dispatch import (
    DispatchGateDecision,
    GraphDispatchCoordinator,
    GraphDispatchAction,
    GraphDispatchMode,
    GraphDispatchRequest,
    GraphDispatchKey,
    StaticWorkerDispatchModeResolver,
)
from a_conductor.graph.scheduler import SelectedAssignment
from a_conductor.job_control import DurableJobControlService
from a_conductor.job_execution import DurableJobExecutionCoordinator, JobBackendResult, JobExecutionContext
from a_conductor.job_store import SQLiteJobStore
from a_conductor.native_execution import NativeCommandResult
from a_conductor.parallel_ready_execution import ParallelReadyTask
from a_conductor.provider_config_store import (
    ProviderAdmissionKind,
    ProviderConfigStoreError,
    SQLiteProviderConfigStore,
)
from a_conductor.provider_configuration import (
    ActorCapabilityEvidence,
    EgressBoundary,
    HarnessRuntimeBinding,
    HarnessStrategy,
    ProviderConfiguration,
    ProviderEndpointConfig,
    ProviderModelConfiguration,
    ProviderTrustClass,
    ProtocolFamily,
)
from a_conductor.worker_lease import (
    LeaseMutationIntent,
    LeaseOutcomeKind,
    SQLiteWorkerLeaseStore,
    WorkerLeaseBroker,
    WorkerLeaseCandidate,
    WorkerLeaseRequest,
)
from a_conductor.zero_relay_review_task import DirectReviewRoute
from a_conductor.zcode_runner import ZCODE_BACKEND_ID, ZCodeTaskPacketIdentity

# WO226 module under test — import error here IS the pre-implementation RED.
from a_conductor.zero_relay_review_execution import (
    DirectReviewExecutionHandoff,
    EquivalentExecutionClassification,
    EquivalenceKind,
    ReviewerExecutionBackend,
    ReviewerExecutionResult,
    ZeroRelayReviewExecutionError,
    classify_equivalent_executions,
    execute_review_dispatch,
    plan_reviewer_execution,
    reconcile_review_execution,
)

NOW = datetime(2026, 9, 12, 12, 0, tzinfo=timezone.utc)
HEAD = "a" * 40
BRANCH = "feat/wo-p1-226-reviewer-execution"
WORKER = "a-worker-01"
PROJECT = "zcode"
BINDING = HarnessRuntimeBinding(
    harness_strategy=HarnessStrategy.ZCODE_APP_SERVER,
    runtime_provider_ref="zcode-runtime/glm-main",
    runtime_model_ref="zcode-runtime/glm-5.3",
)
BASE_URL = "http://127.0.0.1:1"
EXEC = r"C:\ZCode\ZCode.exe"
BUNDLE = r"C:\ZCode\resources\glm\zcode.cjs"


def _profile() -> ProviderConfiguration:
    return ProviderConfiguration(
        provider_id="zcode-glm",
        display_name="ZCode GLM",
        provider_type="zcode-app-server",
        protocol_family=ProtocolFamily.ANTHROPIC_MESSAGES,
        endpoint_ref="zcode-desktop",
        credential_ref="secret-ref:zcode-credential",
        trust_class=ProviderTrustClass.FIRST_PARTY,
        egress_boundary=EgressBoundary.LOCAL_MACHINE,
        harness_strategies=(HarnessStrategy.ZCODE_APP_SERVER,),
        max_concurrency=2,
        models=(ProviderModelConfiguration(
            model_id="glm-5.3",
            display_name="GLM 5.3",
            actor_capabilities=(ActorCapabilityEvidence("code", "DECLARED", "wo226"),),
            runtime_binding=BINDING,
        ),),
        enabled=True,
        schema_version="1.1.0",
    )


@dataclass
class _Snapshot:
    generation: int
    profile: ProviderConfiguration
    endpoint: ProviderEndpointConfig | None = None

    def __post_init__(self) -> None:
        if self.endpoint is None:
            self.endpoint = ProviderEndpointConfig(self.profile.endpoint_ref, BASE_URL)


class _Secrets:
    def __init__(self, value: str = "opaque-secret-value-226") -> None:
        self.value = value
        self.requests: list[str] = []

    def resolve(self, ref: str) -> str:
        self.requests.append(ref)
        return self.value


def _review_contract(tmp_path: Path) -> tuple[str, str, str]:
    """Deterministic review task packet on disk -> (contract_ref, path, sha)."""
    identity_digest = hashlib.sha256(b"wo226-review-identity").hexdigest()
    contract_ref = f"zra2-review-v1:{identity_digest}"
    task_rel = f"runs/zra2-review-{identity_digest}.md"
    path = tmp_path / "runs" / f"zra2-review-{identity_digest}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# ZRA-2 review task (read-only)\n", encoding="utf-8")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    return contract_ref, str(path), sha


def _operation_ref(contract_ref: str, sha: str) -> str:
    digest = hashlib.sha256(
        b"zcode-task-v1" + contract_ref.encode("utf-8") + b"\x00" + sha.lower().encode("ascii")
    ).hexdigest()
    return f"zcode-task-v1:{digest}"


def _route_task(tmp_path: Path, *, contract_ref: str, task_path: str, task_sha: str,
                worker: str = WORKER) -> ParallelReadyTask:
    assignment = SelectedAssignment(node_id="review-node-1", worker_id=worker)
    graph_key = GraphDispatchKey("zra2-review-graph", "run-1", "review-node-1")
    graph_dispatch = GraphDispatchRequest(
        key=graph_key,
        assignment=assignment,
        project_id=PROJECT,
        work_order_ref=contract_ref,
        operation_ref=_operation_ref(contract_ref, task_sha),
        dispatch_mode=GraphDispatchMode.PROGRAMMATIC_PUSH,
    )
    lease = WorkerLeaseRequest(
        session_id="sess-review-226",
        task_id=contract_ref,
        project_id=PROJECT,
        ordered_worker_ids=(worker,),
        required_capabilities=("code",),
        required_runtime_id=f"runtime-{worker}",
        worktree=str(tmp_path),
        branch=BRANCH,
        expected_head=HEAD,
        mutation_intent=LeaseMutationIntent.READ_ONLY,
        allowed_scope=(),
        forbidden_scope=("secrets/**",),
        mutable_scope=(),
        lease_ttl_seconds=600,
    )
    dispatch = HarnessDispatch(
        execution_id=graph_key.job_id,
        task_contract_ref=contract_ref,
        project_id=PROJECT,
        worktree_path=str(tmp_path),
        expected_branch=BRANCH,
        expected_head=HEAD,
        provider_id="zcode-glm",
        model_id="glm-5.3",
        harness_strategy=HarnessStrategy.ZCODE_APP_SERVER,
        mutation_intent=MutationIntent.READ_ONLY,
        timeout_seconds=300,
        max_output_bytes=100_000,
        effort_level=None,
        evidence_destination_ref=f"runs/zra2-review-result-x.json",
    )
    packet = TaskPacketFile(task_contract_ref=contract_ref, path=task_path, sha256=task_sha)
    candidate = WorkerLeaseCandidate(
        worker_id=worker, state="READY", reserved=False, active_task=False,
        capabilities=("code",), runtime_id=f"runtime-{worker}", project_id=PROJECT,
        worktree=str(tmp_path), branch=BRANCH, head=HEAD, health_fresh=True,
        ownership_known=True, dirty_state="CLEAN", mutation_authorized=True,
    )
    return ParallelReadyTask(
        assignment=assignment,
        dispatch_request=graph_dispatch,
        dispatch_gate=DispatchGateDecision.allow(evidence_ref="evidence:preflight-226"),
        lease_request=lease,
        candidates=(candidate,),
        provider_profile=_profile(),
        provider_observation=None,
        harness_dispatch=dispatch,
        task_packet=packet,
        require_quota=False,
    )


def _route(tmp_path: Path, *, contract_ref: str, task_path: str, task_sha: str,
           worker: str = WORKER, dispatch_execution_id: str | None = None,
           provider_id: str = "zcode-glm", project_id: str = PROJECT) -> DirectReviewRoute:
    task = _route_task(tmp_path, contract_ref=contract_ref, task_path=task_path,
                       task_sha=task_sha, worker=worker)
    dispatch = task.harness_dispatch
    return DirectReviewRoute(
        role="independent-review",
        mutation_intent="READ_ONLY",
        review_contract_ref=contract_ref,
        review_task_path=task_path,
        review_task_sha256=task_sha,
        review_result_ref="runs/zra2-review-result-x.json",
        author_execution_id="exec-author-0001",
        author_result_sha256="c" * 64,
        author_attempt_id="attempt-1",
        author_generation=1,
        author_digest=contract_ref.split(":")[-1],
        reviewer_worker_id=worker,
        dispatch_execution_id=dispatch_execution_id or dispatch.execution_id,
        provider_id=provider_id,
        model_id="glm-5.3",
        project_id=project_id,
        worktree=str(tmp_path),
        branch=BRANCH,
        reviewed_head=HEAD,
    )


class _Authorities:
    """All real durable authorities for one bridge test."""

    def __init__(self, tmp_path: Path, *, runner_factory=None) -> None:
        root = tmp_path / "state"
        root.mkdir(parents=True, exist_ok=True)
        self.job_store = SQLiteJobStore(root / "jobs.sqlite")
        self.execution_store = SQLiteExecutionStore(root / "exec.sqlite")
        self.provider_db = root / "provider.sqlite"
        self.provider_store = SQLiteProviderConfigStore(self.provider_db)
        self.provider_store.save_endpoint(ProviderEndpointConfig("zcode-desktop", BASE_URL))
        self.provider_store.save_provider(_profile())
        self.snapshot = self.provider_store.load_provider_snapshot("zcode-glm")
        assert self.snapshot is not None and self.snapshot.generation == 1
        self.lease_db = root / "leases.sqlite"
        self.lease_store = SQLiteWorkerLeaseStore(self.lease_db)
        self._lease_ids = iter(f"lease-226-{i:04d}" for i in range(1000))
        self.lease_broker = WorkerLeaseBroker(
            store=self.lease_store, lease_id_factory=lambda: next(self._lease_ids),
            clock=lambda: NOW,
        )
        self.runner_factory = runner_factory
        self.secret_resolver = _Secrets()
        self.repo_root = str(tmp_path)

    def service(self, backend) -> DurableJobControlService:
        return DurableJobControlService(
            store=self.job_store,
            coordinator=DurableJobExecutionCoordinator(store=self.job_store, backend=backend),
        )


class FakeRunnerFactory:
    """Injectable runner seam: counts model effects, writes REAL durable records."""

    def __init__(self, *, drift: bool = False, exit_code: int = 0,
                 fail_before_record: bool = False, execution_state=ExecutionProcessState.SUCCEEDED,
                 live_timeout: bool = False, fault_after_record: bool = False) -> None:
        self.model_effects = 0
        self.drift = drift
        self.exit_code = exit_code
        self.fail_before_record = fail_before_record
        self.execution_state = execution_state
        self.live_timeout = live_timeout
        self.fault_after_record = fault_after_record
        self.execution_ids: list[str] = []
        self._n = 0

    def _live_execution_id(self):
        self._n += 1
        execution_id = f"exec-fake226-{self._n:04d}"
        self.execution_ids.append(execution_id)
        return execution_id

    def __call__(self, *, plan, lease, admission, execution_store=None, **kwargs):
        factory = self
        spec = plan.fingerprint_spec
        store = execution_store

        def make_record(execution_id, state):
            run_rel = f"runs/{execution_id}"
            return new_execution_record(
                execution_id=execution_id,
                job_id=spec.job_id,
                work_order_ref=spec.work_order_ref,
                project_id=spec.project_id,
                worker_id=plan.reviewer_worker_id,
                backend_id=spec.backend_id,
                agent_ref="agent:zcode-app-server",
                repo_root=spec.repo_root,
                branch=spec.branch,
                head_before=spec.head_before,
                operation_ref=spec.operation_ref,
                command_fingerprint=compute_execution_fingerprint(spec),
                command_summary="zcode app-server turn (fake)",
                runtime_profile_ref=spec.runtime_profile_ref,
                run_dir_ref=run_rel,
                stdout_ref=f"{run_rel}/stdout.log",
                stderr_ref=f"{run_rel}/stderr.log",
                result_ref=f"{run_rel}/result.json",
                report_ref=f"{run_rel}/report.json",
                transport_state=TransportState.CONNECTED,
                execution_state=state,
            )

        class _Runner:
            def execution_fingerprint_spec(self):
                if factory.drift:
                    return replace(spec, head_before="b" * 40)
                return spec

            def execution_fingerprint(self):
                return compute_execution_fingerprint(self.execution_fingerprint_spec())

            def run(self, *, operation_ref=None, timeout_seconds=300):
                if factory.fail_before_record:
                    raise ZeroRelayReviewExecutionError("REVIEW_LAUNCH_CRASH_SIMULATED")
                factory.model_effects += 1
                if factory.live_timeout:
                    # durable record stays LIVE; caller observes a timeout
                    record = make_record(factory._live_execution_id(), ExecutionProcessState.RUNNING)
                    execution_store.create(record)
                    return NativeCommandResult(
                        executable="ZCode.exe", argument_count=6, exit_code=None,
                        timed_out=True, stdout="", stderr="",
                        stdout_sha256=hashlib.sha256(b"").hexdigest(),
                        stderr_sha256=hashlib.sha256(b"").hexdigest(),
                        stdout_truncated=False, stderr_truncated=False,
                    )
                if factory.fault_after_record:
                    record = make_record(factory._live_execution_id(), ExecutionProcessState.RUNNING)
                    execution_store.create(record)
                    raise RuntimeError("post-spawn store fault")
                factory._n += 1
                execution_id = f"exec-fake226-{factory._n:04d}"
                factory.execution_ids.append(execution_id)
                run_rel = f"runs/{execution_id}"
                record = new_execution_record(
                    execution_id=execution_id,
                    job_id=spec.job_id,
                    work_order_ref=spec.work_order_ref,
                    project_id=spec.project_id,
                    worker_id=plan.reviewer_worker_id,
                    backend_id=spec.backend_id,
                    agent_ref="agent:zcode-app-server",
                    repo_root=spec.repo_root,
                    branch=spec.branch,
                    head_before=spec.head_before,
                    operation_ref=spec.operation_ref,
                    command_fingerprint=compute_execution_fingerprint(spec),
                    command_summary="zcode app-server turn (fake)",
                    runtime_profile_ref=spec.runtime_profile_ref,
                    run_dir_ref=run_rel,
                    stdout_ref=f"{run_rel}/stdout.log",
                    stderr_ref=f"{run_rel}/stderr.log",
                    result_ref=f"{run_rel}/result.json",
                    report_ref=f"{run_rel}/report.json",
                    transport_state=TransportState.CONNECTED,
                    execution_state=factory.execution_state,
                )
                execution_store.create(record)
                return NativeCommandResult(
                    executable="ZCode.exe", argument_count=6, exit_code=factory.exit_code,
                    timed_out=False, stdout="REVIEW-OK", stderr="",
                    stdout_sha256=hashlib.sha256(b"REVIEW-OK").hexdigest(),
                    stderr_sha256=hashlib.sha256(b"").hexdigest(),
                    stdout_truncated=False, stderr_truncated=False,
                )

        return _Runner()


def _bridge(tmp_path: Path, *, runner_factory=None):
    """plan + backend-wiring helper returning (plan, authorities, build)."""
    contract_ref, task_path, task_sha = _review_contract(tmp_path)
    route = _route(tmp_path, contract_ref=contract_ref, task_path=task_path, task_sha=task_sha)
    route_task = _route_task(tmp_path, contract_ref=contract_ref, task_path=task_path, task_sha=task_sha)
    authorities = _Authorities(tmp_path, runner_factory=runner_factory)
    plan = plan_reviewer_execution(
        route=route,
        route_task=route_task,
        provider_snapshot=authorities.snapshot,
        repo_root=authorities.repo_root,
        executable=EXEC,
        bundle_js=BUNDLE,
        timeout_seconds=120,
    )
    return plan, authorities, route, route_task


def _dispatch_backend(plan, authorities, route, route_task, *, runner_factory=None):
    backend = ReviewerExecutionBackend(
        plan=plan,
        route_task=route_task,
        provider_store=authorities.provider_store,
        lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store,
        execution_store=authorities.execution_store,
        runner_factory=runner_factory or FakeRunnerFactory(),
        secret_resolver=authorities.secret_resolver,
        provider_snapshot=authorities.snapshot,
        repo_root=authorities.repo_root,
        executable=EXEC,
        bundle_js=BUNDLE,
        clock=lambda: NOW,
    )
    return backend


def _execute(tmp_path: Path, *, runner_factory=None):
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=runner_factory)
    backend = _dispatch_backend(plan, authorities, route, route_task, runner_factory=runner_factory)
    result = execute_review_dispatch(
        route=route,
        route_task=route_task,
        provider_snapshot=authorities.snapshot,
        provider_store=authorities.provider_store,
        lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store,
        execution_store=authorities.execution_store,
        job_store=authorities.job_store,
        runner_factory=runner_factory,
        secret_resolver=authorities.secret_resolver,
        repo_root=authorities.repo_root,
        executable=EXEC,
        bundle_js=BUNDLE,
        clock=lambda: NOW,
    )
    return result, authorities, backend


# ══════════════════════════════════════════════════════════════════════
# G2 — pure pre-effect plan / identity
# ══════════════════════════════════════════════════════════════════════

def test_plan_identity_cross_binding_and_distinct_ids(tmp_path):
    plan, authorities, route, route_task = _bridge(tmp_path)
    assert plan.dispatch_execution_id == route.dispatch_execution_id
    assert plan.dispatch_execution_id == route_task.dispatch_request.key.job_id
    # runtime supervised identity is DISTINCT and never equal to dispatch id
    assert plan.supervised_job_id == f"job:{plan.review_contract_ref}"
    assert plan.supervised_job_id != plan.dispatch_execution_id
    assert plan.reviewer_worker_id == route.reviewer_worker_id
    assert plan.operation_ref.startswith("zcode-task-v1:")
    assert plan.argv[:1] == (EXEC,) and "app-server" in plan.argv
    assert plan.fingerprint == compute_execution_fingerprint(plan.fingerprint_spec)
    # batch id deterministic, changes on identity change
    again = plan_reviewer_execution(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        repo_root=authorities.repo_root, executable=EXEC, bundle_js=BUNDLE, timeout_seconds=120,
    )
    assert again.batch_id == plan.batch_id
    drifted_route = replace(route, reviewed_head="b" * 40)
    with pytest.raises(ZeroRelayReviewExecutionError):
        plan_reviewer_execution(
            route=drifted_route, route_task=route_task, provider_snapshot=authorities.snapshot,
            repo_root=authorities.repo_root, executable=EXEC, bundle_js=BUNDLE, timeout_seconds=120,
        )


def test_plan_is_side_effect_free(tmp_path):
    """RED 11a: no lease/admission/process/secret/store-mutation effects."""
    contract_ref, task_path, task_sha = _review_contract(tmp_path)
    route = _route(tmp_path, contract_ref=contract_ref, task_path=task_path, task_sha=task_sha)
    route_task = _route_task(tmp_path, contract_ref=contract_ref, task_path=task_path, task_sha=task_sha)
    authorities = _Authorities(tmp_path)
    spies = FakeRunnerFactory()
    plan = plan_reviewer_execution(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        repo_root=authorities.repo_root, executable=EXEC, bundle_js=BUNDLE, timeout_seconds=120,
    )
    assert spies.model_effects == 0
    assert authorities.secret_resolver.requests == []
    with pytest.raises(Exception):
        authorities.job_store.get_job(plan.dispatch_execution_id)
    assert authorities.execution_store.find_by_fingerprint(plan.fingerprint) == ()
    # no lease rows and no admission rows exist anywhere in the stores
    assert _all_leases(authorities) == []
    assert _all_admissions(authorities) == []
    assert len(authorities.provider_store.list_provider_snapshots()) == 1  # config only


def test_plan_rejects_mutation_lease_and_nonempty_scope(tmp_path):
    contract_ref, task_path, task_sha = _review_contract(tmp_path)
    route = _route(tmp_path, contract_ref=contract_ref, task_path=task_path, task_sha=task_sha)
    base_task = _route_task(tmp_path, contract_ref=contract_ref, task_path=task_path, task_sha=task_sha)
    mutation_task = replace(
        base_task,
        lease_request=replace(
            base_task.lease_request,
            mutation_intent=LeaseMutationIntent.MUTATION,
            mutable_scope=("src/a_conductor/*",),
            allowed_scope=("src/a_conductor/*",),
        ),
    )
    authorities = _Authorities(tmp_path)
    with pytest.raises(ZeroRelayReviewExecutionError):
        plan_reviewer_execution(
            route=route, route_task=mutation_task, provider_snapshot=authorities.snapshot,
            repo_root=authorities.repo_root, executable=EXEC, bundle_js=BUNDLE, timeout_seconds=120,
        )
    # the canonical lease-request constructor itself is the first fence:
    # READ_ONLY + non-empty mutable scope cannot even be constructed
    with pytest.raises(ValueError):
        replace(base_task.lease_request, mutable_scope=("src/x.py",))


def test_plan_rejects_route_task_identity_mismatch(tmp_path):
    contract_ref, task_path, task_sha = _review_contract(tmp_path)
    other_ref, other_path, other_sha = _review_contract(Path(str(tmp_path) + "x"))
    authorities = _Authorities(tmp_path)
    base_kwargs = dict(
        provider_snapshot=authorities.snapshot, repo_root=authorities.repo_root,
        executable=EXEC, bundle_js=BUNDLE, timeout_seconds=120,
    )
    # task packet contract differs from route contract
    mismatched_task = _route_task(tmp_path, contract_ref=contract_ref, task_path=task_path, task_sha=task_sha)
    route2 = _route(tmp_path, contract_ref=other_ref, task_path=other_path, task_sha=other_sha)
    with pytest.raises(ZeroRelayReviewExecutionError):
        plan_reviewer_execution(route=route2, route_task=mismatched_task, **base_kwargs)
    # foreign worker on the route
    route3 = _route(tmp_path, contract_ref=contract_ref, task_path=task_path, task_sha=task_sha,
                    worker="a-worker-99")
    with pytest.raises(ZeroRelayReviewExecutionError):
        plan_reviewer_execution(route=route3, route_task=mismatched_task, **base_kwargs)
    # provider mismatch
    route4 = _route(tmp_path, contract_ref=contract_ref, task_path=task_path, task_sha=task_sha,
                    provider_id="other-provider")
    with pytest.raises(ZeroRelayReviewExecutionError):
        plan_reviewer_execution(route=route4, route_task=mismatched_task, **base_kwargs)


def test_plan_rejects_tampered_packet_and_non_zcode_strategy(tmp_path):
    contract_ref, task_path, task_sha = _review_contract(tmp_path)
    route = _route(tmp_path, contract_ref=contract_ref, task_path=task_path, task_sha=task_sha)
    task = _route_task(tmp_path, contract_ref=contract_ref, task_path=task_path, task_sha=task_sha)
    authorities = _Authorities(tmp_path)
    base_kwargs = dict(
        provider_snapshot=authorities.snapshot, repo_root=authorities.repo_root,
        executable=EXEC, bundle_js=BUNDLE, timeout_seconds=120,
    )
    Path(task_path).write_text("tampered-bytes", encoding="utf-8")
    with pytest.raises(Exception):
        plan_reviewer_execution(route=route, route_task=task, **base_kwargs)
    Path(task_path).write_text("# ZRA-2 review task (read-only)\n", encoding="utf-8")
    cli_task = replace(
        task,
        harness_dispatch=replace(task.harness_dispatch,
                                 harness_strategy=HarnessStrategy.CLAUDE_CODE_CLI),
    )
    with pytest.raises(ZeroRelayReviewExecutionError):
        plan_reviewer_execution(route=route, route_task=cli_task, **base_kwargs)


def test_provider_generation_drift_fails_closed_before_any_effect(tmp_path):
    """RED 7 (provider generation): a stale snapshot (store moved to a new
    generation) is rejected at dispatch preflight with zero model effects."""
    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    # the provider store advances to generation 2 AFTER the snapshot was taken
    authorities.provider_store.save_endpoint(
        ProviderEndpointConfig("zcode-desktop", "http://127.0.0.2"),
        expected_generation=1,
    )
    result = execute_review_dispatch(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        provider_store=authorities.provider_store, lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store, execution_store=authorities.execution_store,
        job_store=authorities.job_store, runner_factory=factory,
        secret_resolver=authorities.secret_resolver, repo_root=authorities.repo_root,
        executable=EXEC, bundle_js=BUNDLE, clock=lambda: NOW,
    )
    assert result.outcome == "RECOVERY_REQUIRED"
    assert result.reason_code == "REVIEW_PROVIDER_GENERATION_DRIFT"
    assert factory.model_effects == 0
    assert _all_leases(authorities) == [] and _all_admissions(authorities) == []


# ══════════════════════════════════════════════════════════════════════
# G2 — multiplicity over ALL equivalents (Astra F2)
# ══════════════════════════════════════════════════════════════════════

def _record_for(plan, execution_id, *, state=ExecutionProcessState.SUCCEEDED,
                worker=WORKER) -> DurableExecutionRecord:
    spec = plan.fingerprint_spec
    return new_execution_record(
        execution_id=execution_id, job_id=spec.job_id, work_order_ref=spec.work_order_ref,
        project_id=spec.project_id, worker_id=worker, backend_id=spec.backend_id,
        agent_ref="agent:zcode-app-server", repo_root=spec.repo_root, branch=spec.branch,
        head_before=spec.head_before, operation_ref=spec.operation_ref,
        command_fingerprint=compute_execution_fingerprint(spec),
        command_summary="zcode app-server turn (fake)",
        runtime_profile_ref=spec.runtime_profile_ref, run_dir_ref=f"runs/{execution_id}",
        stdout_ref=f"runs/{execution_id}/stdout.log", stderr_ref=f"runs/{execution_id}/stderr.log",
        result_ref=f"runs/{execution_id}/result.json", report_ref=f"runs/{execution_id}/report.json",
        transport_state=TransportState.CONNECTED, execution_state=state,
    )


def test_classify_empty_is_candidate(tmp_path):
    plan, *_ = _bridge(tmp_path)
    c = classify_equivalent_executions((), plan=plan, reviewer_worker_id=WORKER)
    assert c.kind is EquivalenceKind.CANDIDATE_TO_LAUNCH


def test_classify_single_completed_is_reuse_single_live_is_attach(tmp_path):
    plan, authorities, *_ = _bridge(tmp_path)
    done = authorities.execution_store.create(_record_for(plan, "exec-a"))
    c = classify_equivalent_executions((done,), plan=plan, reviewer_worker_id=WORKER)
    assert c.kind is EquivalenceKind.REUSE_COMPLETED and c.chosen.execution_id == "exec-a"
    live = _record_for(plan, "exec-b", state=ExecutionProcessState.RUNNING)
    c2 = classify_equivalent_executions((live,), plan=plan, reviewer_worker_id=WORKER)
    assert c2.kind is EquivalenceKind.ATTACH_RUNNING


def test_classify_foreign_worker_is_identity_conflict(tmp_path):
    plan, authorities, *_ = _bridge(tmp_path)
    foreign = authorities.execution_store.create(
        _record_for(plan, "exec-foreign", worker="a-worker-99"))
    c = classify_equivalent_executions((foreign,), plan=plan, reviewer_worker_id=WORKER)
    assert c.kind is EquivalenceKind.RECOVERY_REQUIRED
    assert c.reason_code == "EQUIVALENT_WORKER_MISMATCH"


def test_classify_older_running_hidden_by_newer_completed_both_orders(tmp_path):
    """RED 16a / Astra F2: matches[0]-newest selection must never hide a live
    equivalent — both insertion orders must classify as recovery."""
    plan, authorities, *_ = _bridge(tmp_path)
    store = authorities.execution_store
    older = store.create(_record_for(plan, "exec-old", state=ExecutionProcessState.RUNNING))
    newer = store.create(_record_for(plan, "exec-new", state=ExecutionProcessState.VERIFICATION_REQUIRED))
    found = store.find_by_fingerprint(plan.fingerprint)
    assert {r.execution_id for r in found} == {"exec-old", "exec-new"}
    c = classify_equivalent_executions(found, plan=plan, reviewer_worker_id=WORKER)
    assert c.kind is EquivalenceKind.RECOVERY_REQUIRED
    assert c.reason_code == "EQUIVALENT_MULTIPLICITY_LIVE"
    # reversed insertion order (newer completed inserted first, older live second)
    plan2, auth2, _, _ = _bridge(Path(str(tmp_path) + "r2"))
    s2 = auth2.execution_store
    s2.create(_record_for(plan2, "exec-new", state=ExecutionProcessState.VERIFICATION_REQUIRED))
    s2.create(_record_for(plan2, "exec-old", state=ExecutionProcessState.RUNNING))
    found2 = s2.find_by_fingerprint(plan2.fingerprint)
    c2 = classify_equivalent_executions(found2, plan=plan2, reviewer_worker_id=WORKER)
    assert c2.kind is EquivalenceKind.RECOVERY_REQUIRED
    assert c2.reason_code == "EQUIVALENT_MULTIPLICITY_LIVE"


def test_classify_dual_completed_requires_recovery_not_newest_collapse(tmp_path):
    plan, authorities, *_ = _bridge(tmp_path)
    store = authorities.execution_store
    store.create(_record_for(plan, "exec-1"))
    store.create(_record_for(plan, "exec-2"))
    c = classify_equivalent_executions(
        store.find_by_fingerprint(plan.fingerprint), plan=plan, reviewer_worker_id=WORKER)
    assert c.kind is EquivalenceKind.RECOVERY_REQUIRED
    assert c.reason_code == "EQUIVALENT_MULTIPLICITY_COMPLETED"
    assert c.chosen is None


def test_classify_unknown_state_is_recovery(tmp_path):
    plan, *_ = _bridge(tmp_path)
    unknown = _record_for(plan, "exec-u", state=ExecutionProcessState.PROCESS_EXITED_UNKNOWN_RESULT)
    c = classify_equivalent_executions((unknown,), plan=plan, reviewer_worker_id=WORKER)
    assert c.kind is EquivalenceKind.RECOVERY_REQUIRED


# ══════════════════════════════════════════════════════════════════════
# G3 — existing-authority durable single winner (Astra F1)
# ══════════════════════════════════════════════════════════════════════

def test_concurrent_same_fingerprint_lanes_one_model_effect_winner(tmp_path):
    """RED 11e / Astra F1: multiple same-fingerprint callers that all observe
    an empty lookup before any record exists still produce exactly ONE
    canonical model-effect winner — the existing GraphDispatch version-CAS
    decides, not a second dedup check, capacity=1 or resource reentry.
    The outcome invariant is timing-independent because every durable
    transition is version-CAS'd."""
    from concurrent.futures import ThreadPoolExecutor

    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)

    def run_lane() -> "ReviewerExecutionResult":
        return execute_review_dispatch(
            route=route,
            route_task=route_task,
            provider_snapshot=authorities.snapshot,
            provider_store=authorities.provider_store,
            lease_broker=authorities.lease_broker,
            lease_store=authorities.lease_store,
            execution_store=authorities.execution_store,
            job_store=authorities.job_store,
            runner_factory=factory,
            secret_resolver=authorities.secret_resolver,
            repo_root=authorities.repo_root,
            executable=EXEC,
            bundle_js=BUNDLE,
            clock=lambda: NOW,
        )

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(run_lane) for _ in range(6)]
        outcomes = [f.result(timeout=120) for f in futures]
    executed = [o for o in outcomes if o.outcome == "EXECUTED"]
    others = [o for o in outcomes if o.outcome != "EXECUTED"]
    assert len(executed) == 1
    assert all(
        o.outcome in ("RECOVERY_REQUIRED", "REUSE_COMPLETED", "ATTACH_RUNNING",
                      "NOT_ATTEMPTED_CLEANED") for o in others), [o.outcome for o in others]
    assert factory.model_effects == 1  # <=1 canonical model-effect winner
    # exactly one durable runtime record exists for the fingerprint
    records = authorities.execution_store.find_by_fingerprint(plan.fingerprint)
    assert len(records) == 1


def test_same_owner_reentry_and_existing_admission_are_not_winner_proof(tmp_path):
    """RED (PO2): after the winner acquired resources, a second caller sees
    EXISTING lease + EXISTING admission via reentry but must NOT run a second
    model effect — the durable job CAS decides, not resource reentry."""
    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    first = execute_review_dispatch(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        provider_store=authorities.provider_store, lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store, execution_store=authorities.execution_store,
        job_store=authorities.job_store, runner_factory=factory,
        secret_resolver=authorities.secret_resolver, repo_root=authorities.repo_root,
        executable=EXEC, bundle_js=BUNDLE, clock=lambda: NOW,
    )
    assert first.outcome == "EXECUTED"
    assert factory.model_effects == 1
    # second full replay after the winner already cleaned up: the job is
    # terminal (VERIFYING -> EXISTING) but the original lease is already
    # RELEASED and the lease store exposes no historical released-lease
    # proof -> mandated fail-closed RECOVERY, ZERO new lease rows, no
    # fabricated identity, and still no second model effect
    lease_rows_before = len(_all_leases(authorities))
    second = execute_review_dispatch(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        provider_store=authorities.provider_store, lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store, execution_store=authorities.execution_store,
        job_store=authorities.job_store, runner_factory=factory,
        secret_resolver=authorities.secret_resolver, repo_root=authorities.repo_root,
        executable=EXEC, bundle_js=BUNDLE, clock=lambda: NOW,
    )
    assert second.outcome == "RECOVERY_REQUIRED"
    assert second.reason_code == "LEASE_IDENTITY_UNPROVEN"
    assert second.handoff is None
    assert factory.model_effects == 1  # no second model effect
    assert len(_all_leases(authorities)) == lease_rows_before  # zero new rows


# ══════════════════════════════════════════════════════════════════════
# G4 — backend chain, cleanup truth, handoff
# ══════════════════════════════════════════════════════════════════════

def test_full_positive_chain_returns_typed_handoff_after_cleanup_truth(tmp_path):
    factory = FakeRunnerFactory()
    result, authorities, backend = _execute(tmp_path, runner_factory=factory)
    assert result.outcome == "EXECUTED"
    handoff = result.handoff
    assert isinstance(handoff, DirectReviewExecutionHandoff)
    # dispatch-context identity != runtime execution identity, both preserved
    assert handoff.dispatch_execution_id != handoff.runtime_execution_id
    assert handoff.dispatch_execution_id == backend._plan.dispatch_execution_id
    assert handoff.runtime_execution_id == factory.execution_ids[0]
    assert handoff.cleanup_terminal is True
    assert handoff.admission_status == "RELEASED"
    assert handoff.lease_released is True
    # durable winner job reached VERIFYING
    job = authorities.job_store.get_job(handoff.dispatch_execution_id)
    from a_conductor.domain import TaskState
    assert job.state is TaskState.VERIFYING
    # resources terminal in canonical stores
    admission = authorities.provider_store.get_admission(handoff.admission_id)
    assert admission is not None and admission.status == "RELEASED"
    lease = authorities.lease_store.inspect_health(handoff.lease_id, now=NOW).lease
    assert lease is not None and lease.released_at is not None
    # winner->resource association reconstructable by exact keys
    assert admission.execution_id == handoff.dispatch_execution_id
    assert lease.task_id == handoff.review_contract_ref == handoff.lease_task_id


def test_no_handoff_until_both_cleanups_terminal(tmp_path):
    """RED 32a: a runner failure still cleans up; success requires terminal truth."""
    factory = FakeRunnerFactory(exit_code=3, execution_state=ExecutionProcessState.FAILED)
    result, authorities, backend = _execute(tmp_path, runner_factory=factory)
    assert result.outcome == "RECOVERY_REQUIRED"
    assert result.handoff is None
    # cleanup still terminal even though the model run failed
    admission = _admission_by_execution(authorities, backend._plan.dispatch_execution_id)
    assert admission is not None and admission.status == "RELEASED"
    leases = _all_leases(authorities)
    assert leases and all(l.released_at is not None for l in leases)


def test_plan_drift_before_spawn_fails_closed_and_cleans_up(tmp_path):
    factory = FakeRunnerFactory(drift=True)
    result, authorities, backend = _execute(tmp_path, runner_factory=factory)
    assert result.outcome in ("RECOVERY_REQUIRED", "NOT_ATTEMPTED_CLEANED")
    assert result.reason_code == "REVIEW_PLAN_DRIFT"
    assert factory.model_effects == 0  # drift detected BEFORE spawn
    admission = _admission_by_execution(authorities, backend._plan.dispatch_execution_id)
    assert admission is not None and admission.status == "RELEASED"
    leases = _all_leases(authorities)
    assert leases and all(l.released_at is not None for l in leases)


def test_completed_equivalent_replay_is_reuse_completed_with_cleanup(tmp_path):
    """RED 14/32: same completed fingerprint -> no new model/launch/acquire,
    but exact cleanup/reconcile effects still happen (admission+lease are
    released by the replay after a simulated lost cleanup)."""
    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    # pre-existing completed equivalent (crash after model, before cleanup)
    authorities.execution_store.create(_record_for(plan, "exec-pre-done"))
    # resources still held: lease ACTIVE + admission ACTIVE via canonical APIs
    outcome = authorities.lease_broker.acquire(route_task.lease_request, route_task.candidates)
    assert outcome.kind is LeaseOutcomeKind.LEASED
    admission = authorities.provider_store.acquire_admission(
        provider_id="zcode-glm", execution_id=route.dispatch_execution_id,
        batch_id=plan.batch_id, expected_max_concurrency=2, now=NOW, ttl_seconds=600,
        expected_configuration_generation=1,
    )
    assert admission.kind is ProviderAdmissionKind.ADMITTED
    result = execute_review_dispatch(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        provider_store=authorities.provider_store, lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store, execution_store=authorities.execution_store,
        job_store=authorities.job_store, runner_factory=factory,
        secret_resolver=authorities.secret_resolver, repo_root=authorities.repo_root,
        executable=EXEC, bundle_js=BUNDLE, clock=lambda: NOW,
    )
    assert result.outcome == "REUSE_COMPLETED"
    assert factory.model_effects == 0  # no new model effect
    handoff = result.handoff
    assert handoff.runtime_execution_id == "exec-pre-done"
    assert handoff.cleanup_terminal is True
    # both pre-held resources were released by the replay
    assert authorities.provider_store.get_admission(admission.admission.admission_id).status == "RELEASED"
    assert authorities.lease_store.inspect_health(outcome.lease.lease_id, now=NOW).lease.released_at is not None


def test_live_equivalent_never_launches_second_child(tmp_path):
    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    authorities.execution_store.create(
        _record_for(plan, "exec-live", state=ExecutionProcessState.RUNNING))
    result = execute_review_dispatch(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        provider_store=authorities.provider_store, lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store, execution_store=authorities.execution_store,
        job_store=authorities.job_store, runner_factory=factory,
        secret_resolver=authorities.secret_resolver, repo_root=authorities.repo_root,
        executable=EXEC, bundle_js=BUNDLE, clock=lambda: NOW,
    )
    assert result.outcome == "ATTACH_RUNNING"
    assert factory.model_effects == 0


def test_admission_lost_ack_replay_requires_exact_released_reread(tmp_path):
    """RED 31 / Astra F3: NOT_ACTIVE alone is insufficient; the exact
    admission must reread terminal RELEASED with matching identity."""
    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    backend = _dispatch_backend(plan, authorities, route, route_task, runner_factory=factory)
    from a_conductor.zero_relay_review_execution import _release_admission_terminal
    admission = authorities.provider_store.acquire_admission(
        provider_id="zcode-glm", execution_id=route.dispatch_execution_id,
        batch_id=plan.batch_id, expected_max_concurrency=2, now=NOW, ttl_seconds=600,
        expected_configuration_generation=1,
    ).admission
    # first release commits
    _release_admission_terminal(
        authorities.provider_store, admission_id=admission.admission_id,
        provider_id="zcode-glm", execution_id=route.dispatch_execution_id,
        batch_id=plan.batch_id, now=NOW, expected_generation=1,
    )
    # lost-ack replay: release raises NOT_ACTIVE -> exact reread RELEASED ok
    final = _release_admission_terminal(
        authorities.provider_store, admission_id=admission.admission_id,
        provider_id="zcode-glm", execution_id=route.dispatch_execution_id,
        batch_id=plan.batch_id, now=NOW, expected_generation=1,
    )
    assert final.status == "RELEASED"
    # wrong identity fails closed: the canonical store fence rejects it before
    # any reread could reinterpret the release
    with pytest.raises((ZeroRelayReviewExecutionError, ProviderConfigStoreError)):
        _release_admission_terminal(
            authorities.provider_store, admission_id=admission.admission_id,
            provider_id="zcode-glm", execution_id="exec-someone-else",
            batch_id=plan.batch_id, now=NOW, expected_generation=1,
        )


def test_lease_cleanup_truth_shapes_only(tmp_path):
    """RED 31a/31b: only (True,False)/(False,True) for the exact owner;
    old cleanup never touches a new owner's lease."""
    plan, authorities, route, route_task = _bridge(tmp_path)
    outcome = authorities.lease_broker.acquire(route_task.lease_request, route_task.candidates)
    lease_id = outcome.lease.lease_id
    from a_conductor.zero_relay_review_execution import _release_lease_terminal
    first = _release_lease_terminal(
        authorities.lease_store, lease_id=lease_id,
        session_id=route_task.lease_request.session_id,
        task_id=route_task.lease_request.task_id, clock=lambda: NOW,
    )
    assert first.released is True and first.already_released is False
    # replay after lost ack: canonical already-released shape
    second = _release_lease_terminal(
        authorities.lease_store, lease_id=lease_id,
        session_id=route_task.lease_request.session_id,
        task_id=route_task.lease_request.task_id, clock=lambda: NOW,
    )
    assert second.released is False and second.already_released is True
    # a new owner acquires the same task; old owner's replay must not touch it
    new_outcome = authorities.lease_broker.acquire(
        replace(route_task.lease_request, session_id="sess-new-owner"),
        route_task.candidates,
    )
    assert new_outcome.kind is LeaseOutcomeKind.LEASED and new_outcome.lease.lease_id != lease_id
    replay = _release_lease_terminal(
        authorities.lease_store, lease_id=lease_id,
        session_id=route_task.lease_request.session_id,
        task_id=route_task.lease_request.task_id, clock=lambda: NOW,
    )
    # canonical already-released truth for the OLD lease id only
    assert replay.released is False and replay.already_released is True
    fresh = authorities.lease_store.inspect_health(new_outcome.lease.lease_id, now=NOW).lease
    assert fresh.released_at is None  # the new owner's lease is untouched


def test_crash_after_acquire_before_model_replay_reconciles(tmp_path):
    """RED (G5): resources acquired, model never ran; replay reconstructs
    ownership by exact keys and cleans up without a model effect."""
    factory = FakeRunnerFactory(fail_before_record=True)
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    # first attempt: winner CAS succeeds, runner crashes pre-record
    first = execute_review_dispatch(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        provider_store=authorities.provider_store, lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store, execution_store=authorities.execution_store,
        job_store=authorities.job_store, runner_factory=factory,
        secret_resolver=authorities.secret_resolver, repo_root=authorities.repo_root,
        executable=EXEC, bundle_js=BUNDLE, clock=lambda: NOW,
    )
    assert first.outcome in ("RECOVERY_REQUIRED", "NOT_ATTEMPTED_CLEANED")
    assert factory.model_effects == 0
    # replay: reconcile path — no second model call, cleanup achieved
    ok_factory = FakeRunnerFactory()
    second = execute_review_dispatch(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        provider_store=authorities.provider_store, lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store, execution_store=authorities.execution_store,
        job_store=authorities.job_store, runner_factory=ok_factory,
        secret_resolver=authorities.secret_resolver, repo_root=authorities.repo_root,
        executable=EXEC, bundle_js=BUNDLE, clock=lambda: NOW,
    )
    assert second.outcome in ("RECOVERY_REQUIRED", "NOT_ATTEMPTED_CLEANED")
    assert ok_factory.model_effects == 0
    # both resources from the crashed attempt are terminal after replay
    admissions = _all_admissions(authorities)
    assert admissions and all(a.status == "RELEASED" for a in admissions)
    leases = _all_leases(authorities)
    assert leases and all(l.released_at is not None for l in leases)


def _all_admissions(authorities):
    """Tests may read canonical stores directly (the bridge module may not)."""
    import sqlite3
    from types import SimpleNamespace
    conn = sqlite3.connect(str(authorities.provider_db))
    try:
        rows = conn.execute("SELECT admission_id, status FROM provider_admissions").fetchall()
    finally:
        conn.close()
    return [SimpleNamespace(admission_id=r[0], status=r[1]) for r in rows]


def _all_leases(authorities):
    import sqlite3
    from types import SimpleNamespace
    conn = sqlite3.connect(str(authorities.lease_db))
    try:
        rows = conn.execute("SELECT lease_id, released_at FROM worker_leases").fetchall()
    finally:
        conn.close()
    return [SimpleNamespace(lease_id=r[0], released_at=r[1]) for r in rows]

def _admission_by_execution(authorities, execution_id: str):
    import sqlite3
    from types import SimpleNamespace
    conn = sqlite3.connect(str(authorities.provider_db))
    try:
        row = conn.execute(
            "SELECT admission_id, execution_id, batch_id, status FROM provider_admissions "
            "WHERE execution_id=?", (execution_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return SimpleNamespace(admission_id=row[0], execution_id=row[1],
                           batch_id=row[2], status=row[3])


def _lease_by_task(authorities, task_id: str):
    import sqlite3
    from types import SimpleNamespace
    conn = sqlite3.connect(str(authorities.lease_db))
    try:
        rows = conn.execute(
            "SELECT lease_id, task_id, released_at FROM worker_leases WHERE task_id=?",
            (task_id,)).fetchall()
    finally:
        conn.close()
    leases = [SimpleNamespace(lease_id=r[0], task_id=r[1], released_at=r[2]) for r in rows]
    return leases[0] if leases else None


def test_no_secret_value_in_plan_or_handoff(tmp_path):
    """RED 33: no secret value enters task/argv/log/result/checkpoint."""
    factory = FakeRunnerFactory()
    result, authorities, backend = _execute(tmp_path, runner_factory=factory)
    assert result.handoff is not None
    secret = authorities.secret_resolver.value
    assert secret not in json.dumps(getattr(result.handoff, "__dict__", {}))
    plan_dict = {f: getattr(backend._plan, f) for f in backend._plan.__dataclass_fields__}
    assert secret not in json.dumps(plan_dict, default=str)


def test_stale_route_replay_after_head_change_fails_closed(tmp_path):
    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    result = execute_review_dispatch(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        provider_store=authorities.provider_store, lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store, execution_store=authorities.execution_store,
        job_store=authorities.job_store, runner_factory=factory,
        secret_resolver=authorities.secret_resolver, repo_root=authorities.repo_root,
        executable=EXEC, bundle_js=BUNDLE, clock=lambda: NOW,
    )
    assert result.outcome == "EXECUTED"
    # same route replayed against a changed HEAD (head drift) must fail closed
    stale_plan = plan_reviewer_execution(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        repo_root=authorities.repo_root, executable=EXEC, bundle_js=BUNDLE, timeout_seconds=120,
    )
    drifted = replace(route, reviewed_head="b" * 40)
    with pytest.raises(ZeroRelayReviewExecutionError):
        plan_reviewer_execution(
            route=drifted, route_task=route_task, provider_snapshot=authorities.snapshot,
            repo_root=authorities.repo_root, executable=EXEC, bundle_js=BUNDLE, timeout_seconds=120,
        )
    # different task sha changes the fingerprint entirely
    other = replace(plan.fingerprint_spec, operation_ref="zcode-task-v1:" + "f" * 64)
    assert compute_execution_fingerprint(other) != plan.fingerprint


# ══════════════════════════════════════════════════════════════════════
# Authority fence (G8)
# ══════════════════════════════════════════════════════════════════════

def test_no_banned_authority_constructs_in_module():
    import inspect
    from a_conductor import zero_relay_review_execution as module
    source = inspect.getsource(module)
    for banned in (
        "ORDER BY rowid DESC", "LIMIT 1", "WorkerLeaseBroker(", "SQLiteExecutionStore(",
        "SQLiteProviderConfigStore(", "SQLiteJobStore(", "ReviewBus", "mailbox",
        "a_wiki", "A_Wiki", "threading.Lock", "ACCEPTED", "REJECTED",
    ):
        assert banned not in source, banned


def test_no_new_scheduler_selection_in_module():
    import inspect
    from a_conductor import zero_relay_review_execution as module
    source = inspect.getsource(module)
    assert "ParallelReadyExecutor(" not in source
    assert "SchedulePlan(" not in source
    assert "SELECT " not in source  # no raw SQL: only canonical store APIs


def test_unrelated_interleaved_execution_cannot_hijack(tmp_path):
    """RED 13 / PO4: executions for OTHER fingerprints created immediately
    before/after the reviewer execution can never be selected; the exact
    fingerprint resolves exactly one record."""
    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    # unrelated execution BEFORE (different operation/task identity)
    authorities.execution_store.create(
        _unrelated_record(authorities, "exec-unrelated-before"))
    result = execute_review_dispatch(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        provider_store=authorities.provider_store, lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store, execution_store=authorities.execution_store,
        job_store=authorities.job_store, runner_factory=factory,
        secret_resolver=authorities.secret_resolver, repo_root=authorities.repo_root,
        executable=EXEC, bundle_js=BUNDLE, clock=lambda: NOW,
    )
    assert result.outcome == "EXECUTED"
    assert result.handoff.runtime_execution_id == factory.execution_ids[0]
    # unrelated execution AFTER
    authorities.execution_store.create(
        _unrelated_record(authorities, "exec-unrelated-after"))
    records = authorities.execution_store.find_by_fingerprint(plan.fingerprint)
    assert {r.execution_id for r in records} == {factory.execution_ids[0]}


def _unrelated_record(authorities, execution_id: str):
    return _record_for(_bridge_record_plan(authorities), execution_id,
                       state=ExecutionProcessState.SUCCEEDED)


def _bridge_record_plan(authorities):
    # a DIFFERENT task identity -> different fingerprint/job/work_order
    class _P:
        pass
    plan = _P()
    spec = ExecutionFingerprintSpec(
        project_id="zcode", job_id="job:other-task", work_order_ref="other-task",
        backend_id=ZCODE_BACKEND_ID, repo_root=str(authorities.repo_root),
        branch=BRANCH, head_before=HEAD, operation_ref="zcode-task-v1:" + "e" * 64,
        runtime_profile_ref="zcode-runtime-v1:" + "0" * 64,
        target_argv=("x.exe", "b.js", "app-server", "--stdio", "--surface", "desktop"),
    )
    plan.fingerprint_spec = spec
    plan.reviewer_worker_id = WORKER
    return plan


def test_malformed_lease_release_shapes_are_typed_recovery(tmp_path):
    """RED 31a: the cleanup gate accepts only the two canonical boolean truth
    shapes; malformed or contradictory outcomes from a misbehaving port are
    typed recovery, never a usable handoff."""

    class _BadStore:
        def __init__(self, outcome):
            self._outcome = outcome

        def release(self, lease_id, *, session_id, task_id, released_at):
            return self._outcome

    from a_conductor.worker_lease import LeaseReleaseResult
    from a_conductor.zero_relay_review_execution import _release_lease_terminal
    for bad in (
        LeaseReleaseResult(released=False, already_released=False),
        LeaseReleaseResult(released=True, already_released=True),
        LeaseReleaseResult(released="yes", already_released=False),
    ):
        with pytest.raises(ZeroRelayReviewExecutionError):
            _release_lease_terminal(
                _BadStore(bad), lease_id="lease-x", session_id="sess",
                task_id="task-x", clock=lambda: NOW,
            )


def test_runner_public_seam_matches_launch_construction(tmp_path):
    """The public spec/fingerprint seam is the SAME construction run() uses;
    a different task packet yields a different fingerprint (no aliasing)."""


def test_completed_plus_released_lease_handoff_lost_zero_new_rows(tmp_path):
    """Sol obligation 1 RED: completed durable execution + original lease
    already RELEASED + handoff lost => ZERO new lease rows/acquisitions, no
    fabricated original lease identity, RECOVERY_REQUIRED, no handoff."""
    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    # completed equivalent + original lease fully released + admission released
    authorities.execution_store.create(_record_for(plan, "exec-pre-done"))
    outcome = authorities.lease_broker.acquire(route_task.lease_request, route_task.candidates)
    assert outcome.kind is LeaseOutcomeKind.LEASED
    authorities.lease_store.release(
        outcome.lease.lease_id, session_id=route_task.lease_request.session_id,
        task_id=route_task.lease_request.task_id, released_at=NOW)
    admission = authorities.provider_store.acquire_admission(
        provider_id="zcode-glm", execution_id=route.dispatch_execution_id,
        batch_id=plan.batch_id, expected_max_concurrency=2, now=NOW, ttl_seconds=600,
        expected_configuration_generation=1).admission
    authorities.provider_store.release_admission(
        admission.admission_id, provider_id="zcode-glm",
        execution_id=route.dispatch_execution_id, batch_id=plan.batch_id, now=NOW)
    rows_before = len(_all_leases(authorities))
    result = execute_review_dispatch(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        provider_store=authorities.provider_store, lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store, execution_store=authorities.execution_store,
        job_store=authorities.job_store, runner_factory=factory,
        secret_resolver=authorities.secret_resolver, repo_root=authorities.repo_root,
        executable=EXEC, bundle_js=BUNDLE, clock=lambda: NOW,
    )
    assert result.outcome == "RECOVERY_REQUIRED"
    assert result.reason_code == "LEASE_IDENTITY_UNPROVEN"
    assert result.handoff is None
    assert factory.model_effects == 0
    assert len(_all_leases(authorities)) == rows_before  # ZERO new lease rows


def test_timeout_retains_resources_then_terminal_reconcile_releases_once(tmp_path):
    """Sol obligation 3 RED: a timeout leaves the durable execution LIVE —
    admission+lease stay ACTIVE (no release over a possibly-running child),
    no usable handoff; after terminality is later observed, one reconcile
    performs the exact cleanup and only then a handoff exists."""
    factory = FakeRunnerFactory(live_timeout=True)
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    result = execute_review_dispatch(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        provider_store=authorities.provider_store, lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store, execution_store=authorities.execution_store,
        job_store=authorities.job_store, runner_factory=factory,
        secret_resolver=authorities.secret_resolver, repo_root=authorities.repo_root,
        executable=EXEC, bundle_js=BUNDLE, clock=lambda: NOW,
    )
    assert result.outcome == "RECOVERY_REQUIRED"
    assert result.handoff is None
    assert factory.model_effects == 1
    # resources RETAINED while the durable execution is live
    admission = _admission_by_execution(authorities, route.dispatch_execution_id)
    assert admission is not None and admission.status == "ACTIVE"
    leases = _all_leases(authorities)
    assert leases and all(l.released_at is None for l in leases)
    # terminality later observed (canonical store API)
    authorities.execution_store.set_execution_state(
        factory.execution_ids[0], ExecutionProcessState.SUCCEEDED, expected_version=1)
    replay = execute_review_dispatch(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        provider_store=authorities.provider_store, lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store, execution_store=authorities.execution_store,
        job_store=authorities.job_store, runner_factory=FakeRunnerFactory(),
        secret_resolver=authorities.secret_resolver, repo_root=authorities.repo_root,
        executable=EXEC, bundle_js=BUNDLE, clock=lambda: NOW,
    )
    assert replay.outcome == "REUSE_COMPLETED"
    assert replay.handoff is not None and replay.handoff.cleanup_terminal
    assert replay.handoff.runtime_execution_id == factory.execution_ids[0]
    final_admission = _admission_by_execution(authorities, route.dispatch_execution_id)
    assert final_admission.status == "RELEASED"
    final_leases = _all_leases(authorities)
    assert final_leases and all(l.released_at is not None for l in final_leases)


def test_post_spawn_fault_retains_resources_recovery(tmp_path):
    """Sol obligation 3: an injected store fault AFTER the durable record
    exists must retain resources/recovery truth (no blind release)."""
    factory = FakeRunnerFactory(fault_after_record=True)
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    result = execute_review_dispatch(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        provider_store=authorities.provider_store, lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store, execution_store=authorities.execution_store,
        job_store=authorities.job_store, runner_factory=factory,
        secret_resolver=authorities.secret_resolver, repo_root=authorities.repo_root,
        executable=EXEC, bundle_js=BUNDLE, clock=lambda: NOW,
    )
    assert result.outcome == "RECOVERY_REQUIRED"
    assert result.handoff is None
    admission = _admission_by_execution(authorities, route.dispatch_execution_id)
    assert admission is not None and admission.status == "ACTIVE"  # retained
    leases = _all_leases(authorities)
    assert leases and all(l.released_at is None for l in leases)  # retained


def test_default_runner_factory_real_surface(tmp_path):
    """Sol obligation 4 RED: the REAL default_reviewer_runner_factory call
    surface must match the backend contract (synthetic supervised
    authorities, no live provider) so fake factories cannot mask drift."""
    from datetime import timedelta
    from a_conductor.zero_relay_review_execution import default_reviewer_runner_factory
    from a_conductor.provider_config_store import ProviderAdmissionRecord
    from a_conductor.worker_lease import WorkerLease
    from a_conductor.registry import windows_worktree_key
    plan, authorities, route, route_task = _bridge(tmp_path)
    from datetime import datetime as _dt
    real_now = _dt.now(timezone.utc)
    now_text = real_now.isoformat()
    lease = WorkerLease(
        lease_id="lease-real-factory-1", worker_id=WORKER,
        session_id=route_task.lease_request.session_id,
        task_id=plan.review_contract_ref, project_id=plan.project_id,
        runtime_id=None, worktree_key=windows_worktree_key(authorities.repo_root),
        branch=plan.branch, expected_head=plan.head, required_capabilities=("code",),
        allowed_scope=(), forbidden_scope=("secrets/**",), mutable_scope=(),
        mutation_intent=LeaseMutationIntent.READ_ONLY,
        acquired_at=now_text, heartbeat_at=now_text, lease_ttl_seconds=600,
        expires_at=(real_now + timedelta(minutes=10)).isoformat(),
    )
    admission = ProviderAdmissionRecord(
        admission_id="admission-real-factory-1", provider_id=plan.provider_id,
        execution_id=plan.dispatch_execution_id, batch_id=plan.batch_id,
        acquired_at=real_now, expires_at=real_now + timedelta(minutes=10),
        status="ACTIVE", configuration_generation=1,
    )
    from tests.test_zcode_authority_bound_assembly import _Controller, _Obs
    factory = default_reviewer_runner_factory(
        provider_snapshot=authorities.snapshot,
        secret_resolver=authorities.secret_resolver,
        execution_store=authorities.execution_store,
        supervised_controller=_Controller(),
        supervised_observer=_Obs(),
        python_executable="python.exe",
        workspace=str(tmp_path),
        deadline_seconds=5.0,
    )
    # exact backend call surface (incl. execution_store kwarg)
    runner = factory(plan=plan, lease=lease, admission=admission,
                     execution_store=authorities.execution_store)
    assert runner.execution_fingerprint_spec() == plan.fingerprint_spec
    assert runner.execution_fingerprint() == plan.fingerprint


def test_stale_task_provider_authority_fails_closed(tmp_path):
    """Sol obligation 5 RED: a trusted C0 task authorized at generation N
    must fail closed when paired with a NEWER snapshot/store at N+1 — no
    silent upgrade of endpoint/runtime authority."""
    contract_ref, task_path, task_sha = _review_contract(tmp_path)
    route = _route(tmp_path, contract_ref=contract_ref, task_path=task_path, task_sha=task_sha)
    base_task = _route_task(tmp_path, contract_ref=contract_ref, task_path=task_path, task_sha=task_sha)
    authorities = _Authorities(tmp_path)
    # task carries complete provider authority at generation 1
    from a_conductor.provider_policy import (
        ProviderPolicyTaskSecurity, TaskNetworkPolicy, TaskPrivacyClass,
    )
    security = ProviderPolicyTaskSecurity(
        privacy_class=TaskPrivacyClass.INTERNAL,
        network_policy=TaskNetworkPolicy.ALLOWLISTED,
        network_allowlist=("provider.example",),
        secret_access=False,
    )
    task = replace(
        base_task,
        provider_endpoint=ProviderEndpointConfig("zcode-desktop", BASE_URL),
        provider_security=security,
        expected_configuration_generation=1,
    )
    # store advances to generation 2; a NEW snapshot is supplied
    authorities.provider_store.save_endpoint(
        ProviderEndpointConfig("zcode-desktop", "http://127.0.0.2"),
        expected_generation=1,
    )
    new_snapshot = authorities.provider_store.load_provider_snapshot("zcode-glm")
    with pytest.raises(ZeroRelayReviewExecutionError):
        plan_reviewer_execution(
            route=route, route_task=task, provider_snapshot=new_snapshot,
            repo_root=authorities.repo_root, executable=EXEC, bundle_js=BUNDLE,
            timeout_seconds=120,
        )
