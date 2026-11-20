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
from a_conductor.zero_relay import ResultIdentity, ReviewDisposition
from a_conductor.zero_relay_review_evidence import (
    compose_direct_review_evidence_from_store,
)
from a_conductor.zero_relay_review_task import (
    DirectReviewRoute,
    DirectReviewV2Route,
)
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
                worker: str = WORKER, graph_run_id: str = "run-1") -> ParallelReadyTask:
    assignment = SelectedAssignment(node_id="review-node-1", worker_id=worker)
    graph_key = GraphDispatchKey("zra2-review-graph", graph_run_id, "review-node-1")
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
        # complete provider-authority triple (mandatory for direct review
        # since Repair CR1 / packet a5ea7938): the LOCAL_MACHINE egress
        # boundary with a loopback endpoint evaluates ALLOWED_LOCAL
        provider_endpoint=ProviderEndpointConfig("zcode-desktop", BASE_URL),
        provider_security=_fixture_task_security(),
        expected_configuration_generation=1,
        require_quota=False,
    )


def _fixture_task_security():
    from a_conductor.provider_policy import (
        ProviderPolicyTaskSecurity,
        TaskNetworkPolicy,
        TaskPrivacyClass,
    )
    return ProviderPolicyTaskSecurity(
        privacy_class=TaskPrivacyClass.INTERNAL,
        network_policy=TaskNetworkPolicy.ALLOWLISTED,
        network_allowlist=("127.0.0.1",),
        secret_access=False,
    )


def _route(tmp_path: Path, *, contract_ref: str, task_path: str, task_sha: str,
           worker: str = WORKER, dispatch_execution_id: str | None = None,
           provider_id: str = "zcode-glm", project_id: str = PROJECT) -> DirectReviewRoute:
    task = _route_task(tmp_path, contract_ref=contract_ref, task_path=task_path,
                       task_sha=task_sha, worker=worker)
    dispatch = task.harness_dispatch
    return DirectReviewV2Route(
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
        author_task_contract_ref=AUTHOR.task_contract_ref,
        author_task_sha256=AUTHOR.task_sha256,
        author_result_ref=AUTHOR.result_ref,
    )


# RE1: the author identity the v2 route carries (C1 cross-binding needs it)
AUTHOR = ResultIdentity(
    task_contract_ref="work-order:author-223",
    task_sha256="1" * 64,
    result_ref="runs/author-result-223.json",
    result_sha256="c" * 64,
    attempt_id="attempt-1",
    generation=1,
    author_execution_id="exec-author-0001",
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


def _v2_response_bytes(plan) -> bytes:
    """A whole v2 review response bound to the plan's trusted facts (tests
    may carry verdict vocabulary; the production verifier never parses it)."""
    payload = {
        "schema": "zra2-review-result-v2",
        "review_contract_ref": plan.review_contract_ref,
        "reviewed_head": plan.head,
        "review_task_sha256": plan.review_task_sha256,
        "verdict": "ACCEPTED",
        "findings": [],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _write_run_artifacts(plan, execution_id: str, *, stdout: bytes,
                         report_overrides: dict | None = None) -> None:
    """Real on-disk stdout/report artifacts in the exact production shapes."""
    run_dir = Path(plan.repo_root) / "runs" / execution_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "stdout.log").write_bytes(stdout)
    (run_dir / "stderr.log").write_bytes(b"")
    (run_dir / "result.json").write_bytes(json.dumps({
        "schema": "zcode-result/1", "execution_id": execution_id,
    }).encode("utf-8"))
    report = {
        "schema": "zcode-report/1",
        "execution_id": execution_id,
        "task_packet_sha256": plan.review_task_sha256,
        "response_bytes": len(stdout),
        "response_sha256": hashlib.sha256(stdout).hexdigest(),
        "session_id": "session-zcode-226",
    }
    if report_overrides:
        report.update(report_overrides)
    (run_dir / "report.json").write_bytes(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


class FakeRunnerFactory:
    """Injectable runner seam: counts model effects, writes REAL durable
    records + on-disk artifacts in the accepted production shapes.

    The terminal exit-0 record mirrors the accepted supervised collect
    semantics: result metadata first, then the terminal execution state
    (VERIFICATION_REQUIRED on exit 0, FAILED otherwise)."""

    def __init__(self, *, drift: bool = False, exit_code: int = 0,
                 fail_before_record: bool = False,
                 execution_state=ExecutionProcessState.VERIFICATION_REQUIRED,
                 live_timeout: bool = False, fault_after_record: bool = False,
                 report_overrides: dict | None = None,
                 stdout_bytes: bytes | None = None) -> None:
        self.model_effects = 0
        self.drift = drift
        self.exit_code = exit_code
        self.fail_before_record = fail_before_record
        self.execution_state = execution_state
        self.live_timeout = live_timeout
        self.fault_after_record = fault_after_record
        self.report_overrides = report_overrides
        self.stdout_bytes = stdout_bytes
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

        def finalize(execution_id, *, exit_code, state):
            """Canonical store transitions mirroring supervised collect."""
            created = store.get(execution_id)
            with_result = store.set_result_metadata(
                execution_id,
                exit_code=exit_code,
                finished_at="2026-09-12T12:00:00Z",
                expected_version=created.version,
                evidence_ref=f"runs/{execution_id}/result.json",
            )
            return store.set_execution_state(
                execution_id,
                state,
                expected_version=with_result.version,
                evidence_ref=f"runs/{execution_id}/result.json",
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
                    # durable record stays LIVE; caller observes a timeout;
                    # the child still wrote its artifacts before hanging
                    execution_id = factory._live_execution_id()
                    execution_store.create(make_record(execution_id, ExecutionProcessState.RUNNING))
                    _write_run_artifacts(
                        plan, execution_id,
                        stdout=factory.stdout_bytes
                        if factory.stdout_bytes is not None
                        else _v2_response_bytes(plan),
                        report_overrides=factory.report_overrides,
                    )
                    return NativeCommandResult(
                        executable="ZCode.exe", argument_count=6, exit_code=None,
                        timed_out=True, stdout="", stderr="",
                        stdout_sha256=hashlib.sha256(b"").hexdigest(),
                        stderr_sha256=hashlib.sha256(b"").hexdigest(),
                        stdout_truncated=False, stderr_truncated=False,
                    )
                if factory.fault_after_record:
                    execution_id = factory._live_execution_id()
                    execution_store.create(make_record(execution_id, ExecutionProcessState.RUNNING))
                    raise RuntimeError("post-spawn store fault")
                stdout = (
                    factory.stdout_bytes
                    if factory.stdout_bytes is not None
                    else _v2_response_bytes(plan)
                )
                factory._n += 1
                execution_id = f"exec-fake226-{factory._n:04d}"
                factory.execution_ids.append(execution_id)
                execution_store.create(make_record(execution_id, ExecutionProcessState.RUNNING))
                _write_run_artifacts(
                    plan, execution_id, stdout=stdout,
                    report_overrides=factory.report_overrides,
                )
                terminal = factory.execution_state
                finalize(execution_id, exit_code=factory.exit_code, state=terminal)
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


def _seed_completed(authorities, plan, execution_id, *,
                    state=ExecutionProcessState.VERIFICATION_REQUIRED,
                    exit_code: int = 0, report_overrides: dict | None = None,
                    stdout_bytes: bytes | None = None):
    """Seed a completed exit-0 reviewer execution through the canonical
    store transitions (result truth first, then terminal state) plus the
    real on-disk artifacts — the durable truth a crashed winner leaves."""
    running = _record_for(plan, execution_id, state=ExecutionProcessState.RUNNING)
    authorities.execution_store.create(running)
    with_result = authorities.execution_store.set_result_metadata(
        execution_id, exit_code=exit_code, finished_at="2026-09-12T12:00:00Z",
        expected_version=running.version, evidence_ref=f"runs/{execution_id}/result.json",
    )
    final = authorities.execution_store.set_execution_state(
        execution_id, state, expected_version=with_result.version,
        evidence_ref=f"runs/{execution_id}/result.json",
    )
    _write_run_artifacts(
        plan, execution_id,
        stdout=stdout_bytes if stdout_bytes is not None else _v2_response_bytes(plan),
        report_overrides=report_overrides,
    )
    return final


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


def test_same_owner_reentry_after_cleanup_reconstructs_without_second_model_effect(tmp_path):
    """RED (PO2 + RE2-A): after the winner acquired resources and completed,
    a second caller sees EXISTING lease + EXISTING admission via reentry but
    must NOT run a second model effect — the durable job CAS decides, not
    resource reentry. RE2-A: now that the promotion event carries the exact
    resource identity, the replay reconstructs the exact REUSE_COMPLETED
    handoff from the released rows instead of failing LEASE_IDENTITY_UNPROVEN
    forever — still with ZERO new lease rows and ZERO new model effects."""
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
    # second full replay after the winner already cleaned up: the original
    # lease/admission rows are RELEASED; the promotion event's strict
    # identity proves them by exact id -> exact REUSE_COMPLETED truth
    lease_rows_before = len(_all_leases(authorities))
    admission_rows_before = len(_all_admissions(authorities))
    second = execute_review_dispatch(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        provider_store=authorities.provider_store, lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store, execution_store=authorities.execution_store,
        job_store=authorities.job_store, runner_factory=factory,
        secret_resolver=authorities.secret_resolver, repo_root=authorities.repo_root,
        executable=EXEC, bundle_js=BUNDLE, clock=lambda: NOW,
    )
    assert second.outcome == "REUSE_COMPLETED"
    assert second.handoff is not None
    assert second.handoff.runtime_execution_id == first.handoff.runtime_execution_id
    assert second.handoff.lease_id == first.handoff.lease_id
    assert second.handoff.admission_id == first.handoff.admission_id
    assert second.handoff.cleanup_terminal is True
    assert factory.model_effects == 1  # no second model effect
    assert len(_all_leases(authorities)) == lease_rows_before  # zero new rows
    assert len(_all_admissions(authorities)) == admission_rows_before


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


def test_completed_equivalent_replay_reconciles_admission_and_retains_lease_r6(tmp_path):
    """RED 14/32 (R6 amendment): same completed fingerprint -> no new
    model/launch/acquire effect. A legacy-evidence replay holds no durable
    exact lease id, so the owner-key lease row is retained (typed recovery,
    no handoff); the exact-dispatch admission still reconciles once."""
    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    # pre-existing completed equivalent (crash after model, before cleanup)
    _seed_completed(authorities, plan, "exec-pre-done")
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
    # R6: no durable exact lease id -> typed recovery, never a handoff
    assert result.outcome == "RECOVERY_REQUIRED"
    assert result.reason_code == "LEASE_OWNERSHIP_UNPROVEN"
    assert result.handoff is None
    assert factory.model_effects == 0  # no new model effect
    # the exact-dispatch admission was reconciled independently
    assert authorities.provider_store.get_admission(admission.admission.admission_id).status == "RELEASED"
    # the owner-key lease row was retained (never released by inference)
    assert authorities.lease_store.inspect_health(outcome.lease.lease_id, now=NOW).lease.released_at is None


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
    _seed_completed(authorities, plan, "exec-pre-done")
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


def test_timeout_retains_resources_then_terminal_reconcile_fails_closed_r6(tmp_path):
    """Sol obligation 3 RED (R6 amendment): a timeout leaves the durable
    execution LIVE — admission+lease stay ACTIVE (no release over a
    possibly-running child), no usable handoff. After terminality is later
    observed, the replay reconciles the exact-dispatch admission but —
    lacking a durable exact lease id — retains the owner-key lease row and
    returns typed recovery with no handoff (never an inference release)."""
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
    # terminality later observed (canonical store API): durable exit truth
    # first, then the terminal execution state
    with_result = authorities.execution_store.set_result_metadata(
        factory.execution_ids[0], exit_code=0,
        finished_at="2026-09-12T12:00:30Z", expected_version=1,
    )
    authorities.execution_store.set_execution_state(
        factory.execution_ids[0], ExecutionProcessState.SUCCEEDED,
        expected_version=with_result.version,
    )
    replay_factory = FakeRunnerFactory()
    replay = execute_review_dispatch(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        provider_store=authorities.provider_store, lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store, execution_store=authorities.execution_store,
        job_store=authorities.job_store, runner_factory=replay_factory,
        secret_resolver=authorities.secret_resolver, repo_root=authorities.repo_root,
        executable=EXEC, bundle_js=BUNDLE, clock=lambda: NOW,
    )
    # R6: legacy promotion evidence -> no exact lease id -> typed recovery
    assert replay.outcome == "RECOVERY_REQUIRED"
    assert replay.reason_code == "LEASE_OWNERSHIP_UNPROVEN"
    assert replay.handoff is None
    assert replay_factory.model_effects == 0
    final_admission = _admission_by_execution(authorities, route.dispatch_execution_id)
    assert final_admission.status == "RELEASED"  # independent reconcile
    final_leases = _all_leases(authorities)
    assert final_leases and all(l.released_at is None for l in final_leases)


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


# ── WO-P1-226 Repair R1: admission replay binding (wrong batch/generation
# must never be released or yield a usable handoff) ─────────────────────

def _replay_setup(tmp_path, *, batch_id=None, expected_generation=1):
    """Completed equivalent + exact ACTIVE lease + a canonical admission
    with caller-chosen batch/generation, all through real stores."""
    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    _seed_completed(authorities, plan, "exec-pre-done")
    outcome = authorities.lease_broker.acquire(route_task.lease_request, route_task.candidates)
    assert outcome.kind is LeaseOutcomeKind.LEASED
    admission = authorities.provider_store.acquire_admission(
        provider_id="zcode-glm", execution_id=route.dispatch_execution_id,
        batch_id=batch_id or plan.batch_id, expected_max_concurrency=2, now=NOW,
        ttl_seconds=600, expected_configuration_generation=expected_generation,
    ).admission
    return plan, authorities, route, route_task, admission


def _assert_rejected_replay_keeps_everything(authorities, route, result, code):
    assert result.outcome == "RECOVERY_REQUIRED"
    assert result.reason_code == code
    assert result.handoff is None
    # the mismatched admission is NOT released by this path
    admission = _admission_by_execution(authorities, route.dispatch_execution_id)
    assert admission is not None and admission.status == "ACTIVE"
    # the exact active lease is NOT released either (ownership unresolved)
    leases = _all_leases(authorities)
    assert leases and all(l.released_at is None for l in leases)


def test_replay_wrong_batch_admission_is_typed_recovery(tmp_path):
    """RED 1: wrong batch_id => typed recovery, no release, no handoff,
    zero new rows, zero model effect."""
    fresh = FakeRunnerFactory()
    plan, authorities, route, route_task, _ = _replay_setup(
        tmp_path, batch_id="zra2-review-batch-v1:" + "f" * 64)
    leases_before = len(_all_leases(authorities))
    admissions_before = len(_all_admissions(authorities))
    result = execute_review_dispatch(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        provider_store=authorities.provider_store, lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store, execution_store=authorities.execution_store,
        job_store=authorities.job_store, runner_factory=fresh,
        secret_resolver=authorities.secret_resolver, repo_root=authorities.repo_root,
        executable=EXEC, bundle_js=BUNDLE, clock=lambda: NOW,
    )
    _assert_rejected_replay_keeps_everything(authorities, route, result,
                                             "ADMISSION_REPLAY_BATCH_MISMATCH")
    assert fresh.model_effects == 0
    assert len(_all_leases(authorities)) == leases_before  # zero new rows
    assert len(_all_admissions(authorities)) == admissions_before  # zero acquisition


def test_replay_unknown_generation_when_expected_is_typed_recovery(tmp_path):
    """RED 2/3: persisted generation NULL while the plan requires a
    generation => typed recovery, nothing released, no handoff."""
    fresh = FakeRunnerFactory()
    plan, authorities, route, route_task, _ = _replay_setup(
        tmp_path, expected_generation=None)  # canonical store persists NULL
    leases_before = len(_all_leases(authorities))
    result = execute_review_dispatch(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        provider_store=authorities.provider_store, lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store, execution_store=authorities.execution_store,
        job_store=authorities.job_store, runner_factory=fresh,
        secret_resolver=authorities.secret_resolver, repo_root=authorities.repo_root,
        executable=EXEC, bundle_js=BUNDLE, clock=lambda: NOW,
    )
    _assert_rejected_replay_keeps_everything(authorities, route, result,
                                             "ADMISSION_REPLAY_GENERATION_UNKNOWN")
    assert fresh.model_effects == 0
    assert len(_all_leases(authorities)) == leases_before


def test_replay_wrong_generation_binding_fails_closed(tmp_path):
    """RED (wrong-generation class, real store row): a persisted generation
    that differs from the plan's expectation is a typed mismatch even when
    provider/execution/batch all match; the exact binding still resolves."""
    from a_conductor.zero_relay_review_execution import _find_held_admission_readonly
    plan, authorities, route, route_task, admission = _replay_setup(
        tmp_path, expected_generation=1)
    with pytest.raises(ZeroRelayReviewExecutionError) as e:
        _find_held_admission_readonly(
            authorities.provider_store, provider_id="zcode-glm",
            execution_id=route.dispatch_execution_id,
            batch_id=plan.batch_id, expected_generation=2,
        )
    assert e.value.code == "ADMISSION_REPLAY_GENERATION_MISMATCH"
    # exact identity still resolves through the same read-only authority
    ok = _find_held_admission_readonly(
        authorities.provider_store, provider_id="zcode-glm",
        execution_id=route.dispatch_execution_id,
        batch_id=plan.batch_id, expected_generation=1,
    )
    assert ok is not None and ok.admission_id == admission.admission_id


def test_replay_exact_identity_reconciles_admission_only_r6(tmp_path):
    """RED 4 (R6 amendment): exact batch + exact generation replay
    reconciles the exact-dispatch admission once (typed, no handoff, no
    model effect) — but the owner-key lease row is retained: without a
    durable exact lease id, exact dispatch keys alone never authorize a
    lease release."""
    factory = FakeRunnerFactory()
    plan, authorities, route, route_task, admission = _replay_setup(tmp_path)
    result = execute_review_dispatch(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        provider_store=authorities.provider_store, lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store, execution_store=authorities.execution_store,
        job_store=authorities.job_store, runner_factory=factory,
        secret_resolver=authorities.secret_resolver, repo_root=authorities.repo_root,
        executable=EXEC, bundle_js=BUNDLE, clock=lambda: NOW,
    )
    assert result.outcome == "RECOVERY_REQUIRED"
    assert result.reason_code == "LEASE_OWNERSHIP_UNPROVEN"
    assert result.handoff is None
    assert factory.model_effects == 0
    final_admission = _admission_by_execution(authorities, route.dispatch_execution_id)
    assert final_admission.status == "RELEASED"
    leases = _all_leases(authorities)
    assert leases and all(l.released_at is None for l in leases)


# ── WO-P1-226 combined repair: Astra AF1-AF4 adversarial REDs (ported from
# docs/reviews/wo226-astra-final/test_adversarial.py at frozen evidence
# 5df9ebe; same semantics, no live provider/process) ────────────────────

def _af_dispatch(a, route, task, factory):
    return execute_review_dispatch(
        route=route, route_task=task, provider_snapshot=a.snapshot,
        provider_store=a.provider_store, lease_broker=a.lease_broker,
        lease_store=a.lease_store, execution_store=a.execution_store,
        job_store=a.job_store, runner_factory=factory,
        secret_resolver=a.secret_resolver, repo_root=a.repo_root,
        executable=EXEC, bundle_js=BUNDLE, clock=lambda: NOW,
    )


def _af_resources(a):
    return {
        "admissions": [x.status for x in _all_admissions(a)],
        "leases_released": [x.released_at is not None for x in _all_leases(a)],
    }


def test_af1_loser_does_not_release_paused_winner_resources(tmp_path):
    """AF1: while the winning dispatch is paused after acquiring resources
    but before any runtime record exists, a concurrent losing dispatch must
    not release those resources — missing record is not quiescence proof."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    plan, a, route, task = _bridge(tmp_path)
    entered, proceed = Event(), Event()
    inner = FakeRunnerFactory()

    def paused_factory(**kwargs):
        entered.set()  # winner owns resources, but no runtime record yet
        assert proceed.wait(10), "probe barrier timed out"
        return inner(**kwargs)

    with ThreadPoolExecutor(max_workers=1) as pool:
        winner = pool.submit(_af_dispatch, a, route, task, paused_factory)
        try:
            assert entered.wait(10)
            before = _af_resources(a)
            loser = _af_dispatch(a, route, task, inner)
            after = _af_resources(a)
        finally:
            proceed.set()
        first = winner.result(timeout=30)
    assert after == before, "losing dispatch released still-owned winner resources"
    assert first.outcome == "EXECUTED"  # winner completes normally after resume


def test_af2_failed_terminal_after_timeout_releases_resources(tmp_path):
    """AF2 (R6 amendment): a retained timed-out execution that later becomes
    terminal FAILED must reconcile its exact-dispatch admission once — no
    handoff, no relaunch — while the owner-key lease row is retained (no
    durable exact lease id exists on a pure replay)."""
    factory = FakeRunnerFactory(live_timeout=True)
    plan, a, route, task = _bridge(tmp_path, runner_factory=factory)
    first = _af_dispatch(a, route, task, factory)
    assert first.handoff is None
    a.execution_store.set_execution_state(
        factory.execution_ids[0], ExecutionProcessState.FAILED, expected_version=1)
    replay = _af_dispatch(a, route, task, factory)
    after = _af_resources(a)
    assert replay.handoff is None
    assert replay.outcome == "RECOVERY_REQUIRED"
    assert after["admissions"] == ["RELEASED"], \
        "terminal failed child must release capacity without a usable handoff"
    assert after["leases_released"] == [False], \
        "R6: an owner-key lease is never released without exact identity"
    assert factory.model_effects == 1  # no relaunch


def test_af3_foreign_worker_terminal_record_cannot_create_handoff(tmp_path):
    """AF3: a same-fingerprint terminal record with a FOREIGN worker must be
    typed recovery after the run — never an EXECUTED handoff."""
    plan, a, route, task = _bridge(tmp_path)
    inner = FakeRunnerFactory()

    def foreign_factory(**kwargs):
        original = inner(**kwargs)

        class Runner:
            def execution_fingerprint_spec(self):
                return original.execution_fingerprint_spec()

            def run(self, **run_kwargs):
                a.execution_store.create(_record_for(
                    kwargs["plan"], "exec-foreign", worker="a-worker-99"))
                return NativeCommandResult(
                    executable="ZCode.exe", argument_count=6, exit_code=0,
                    timed_out=False, stdout="", stderr="",
                    stdout_sha256="0" * 64, stderr_sha256="0" * 64,
                    stdout_truncated=False, stderr_truncated=False,
                )

        return Runner()

    result = _af_dispatch(a, route, task, foreign_factory)
    assert result.handoff is None, "post-run path bypassed equivalent identity classifier"
    assert result.outcome == "RECOVERY_REQUIRED"
    assert "WORKER_MISMATCH" in result.reason_code


def test_af4_task_network_denied_blocks_before_effect(tmp_path):
    """AF4: the canonical provider policy for the trusted C0 task (network
    DENIED against an EXTERNAL_FIRST_PARTY egress boundary) must block
    before any acquisition/model effect."""
    from a_conductor.provider_policy import (
        ProviderPolicyTaskSecurity, TaskPrivacyClass, TaskNetworkPolicy,
        evaluate_provider_policy,
    )
    from a_conductor.provider_configuration import EgressBoundary

    plan, a, route, task = _bridge(tmp_path)
    profile = replace(task.provider_profile, egress_boundary=EgressBoundary.EXTERNAL_FIRST_PARTY)
    a.provider_store.save_provider(profile, expected_generation=1)
    a.provider_store.save_endpoint(
        ProviderEndpointConfig(profile.endpoint_ref, "https://provider.example.invalid"),
        expected_generation=1,
    )
    a.snapshot = a.provider_store.load_provider_snapshot(profile.provider_id)
    security = ProviderPolicyTaskSecurity(
        privacy_class=TaskPrivacyClass.INTERNAL,
        network_policy=TaskNetworkPolicy.DENIED,
    )
    task = replace(
        task, provider_profile=a.snapshot.profile,
        provider_endpoint=a.snapshot.endpoint, provider_security=security,
        expected_configuration_generation=a.snapshot.generation,
    )
    policy = evaluate_provider_policy(a.snapshot.profile, a.snapshot.endpoint, security)
    assert not policy.allowed and policy.reason_code == "TASK_NETWORK_DENIED"
    factory = FakeRunnerFactory()
    with pytest.raises(ZeroRelayReviewExecutionError) as e:
        _af_dispatch(a, route, task, factory)
    assert "TASK_NETWORK_DENIED" in e.value.code
    assert factory.model_effects == 0
    assert _af_resources(a) == {"admissions": [], "leases_released": []}


# ── WO-P1-226 Repair CR1 (packet a5ea7938; Astra comment 5649902034 +
# Sol amendments ce4709b/a5ea793): terminal-unusable generation binding
# and the mandatory provider-authority triple ───────────────────────────


def _cr1_terminal(tmp_path, *, persisted_generation,
                  state=ExecutionProcessState.FAILED):
    """Terminal-unusable replay with a caller-chosen persisted admission
    generation; provider/execution/batch are exact everywhere (real stores
    + canonical acquisition only)."""
    fresh = FakeRunnerFactory()
    plan, authorities, route, route_task, admission = _replay_setup(
        tmp_path, expected_generation=persisted_generation)
    seeded = authorities.execution_store.get("exec-pre-done")
    authorities.execution_store.set_execution_state(
        "exec-pre-done", state, expected_version=seeded.version)
    result = _af_dispatch(authorities, route, route_task, fresh)
    return plan, authorities, route, fresh, result


@pytest.mark.parametrize("state", [
    ExecutionProcessState.FAILED,
    ExecutionProcessState.PARTIAL,
    ExecutionProcessState.CANCELLED,
])
def test_cr1_terminal_unknown_persisted_generation_retains(tmp_path, state):
    """CR1 RED: terminal-unusable cleanup must keep the R1 generation gate.
    A persisted NULL configuration generation (correct provider/execution/
    batch) proves nothing about resource authority — BOTH the admission and
    the exact active lease must be retained, with no handoff, no model
    effect and zero new rows."""
    plan, authorities, route, fresh, result = _cr1_terminal(
        tmp_path, persisted_generation=None, state=state)
    assert result.outcome == "RECOVERY_REQUIRED" and result.handoff is None
    assert fresh.model_effects == 0
    admission = _admission_by_execution(authorities, route.dispatch_execution_id)
    assert admission is not None and admission.status == "ACTIVE"
    leases = _all_leases(authorities)
    assert leases and all(l.released_at is None for l in leases)


def test_cr1_terminal_wrong_persisted_generation_retains(tmp_path):
    """CR1 RED (wrong-generation class on the same cleanup path): a
    persisted generation differing from the plan's expectation must retain
    BOTH resources — the terminal-unusable path may not disable the
    required-generation gate."""
    from a_conductor.zero_relay_review_execution import _terminal_unusable_cleanup
    plan, authorities, route, route_task, admission = _replay_setup(
        tmp_path, expected_generation=1)  # persisted generation 1
    seeded = authorities.execution_store.get("exec-pre-done")
    authorities.execution_store.set_execution_state(
        "exec-pre-done", ExecutionProcessState.FAILED,
        expected_version=seeded.version)
    _terminal_unusable_cleanup(
        plan=plan, route_task=route_task,
        provider_store=authorities.provider_store,
        lease_store=authorities.lease_store, clock=lambda: NOW,
        expected_generation=2,  # plan-side expectation differs
    )
    admission = _admission_by_execution(authorities, route.dispatch_execution_id)
    assert admission is not None and admission.status == "ACTIVE"
    leases = _all_leases(authorities)
    assert leases and all(l.released_at is None for l in leases)


def test_cr1_exact_generation_terminal_cleanup_reconciles_admission_r6(tmp_path):
    """Positive preserved (R6 amendment): exact persisted generation
    terminal-unusable cleanup reconciles the exact-dispatch admission once
    — no handoff, no relaunch, zero model effects — while the owner-key
    lease row is retained (no exact lease id on a pure replay)."""
    plan, authorities, route, fresh, result = _cr1_terminal(
        tmp_path, persisted_generation=1)
    assert result.outcome == "RECOVERY_REQUIRED" and result.handoff is None
    assert fresh.model_effects == 0
    admission = _admission_by_execution(authorities, route.dispatch_execution_id)
    assert admission is not None and admission.status == "RELEASED"
    leases = _all_leases(authorities)
    assert leases and all(l.released_at is None for l in leases)


def test_cr1_authority_triple_missing_fails_closed_before_effect(tmp_path):
    """AF4 amendment RED (Sol a5ea793): an authority-less task — endpoint/
    security/generation all None — must fail closed in the PURE plan with
    the ambient snapshot NEVER substituted as authority, yielding zero
    resource rows and zero model effects."""
    contract_ref, task_path, task_sha = _review_contract(tmp_path)
    route = _route(tmp_path, contract_ref=contract_ref, task_path=task_path,
                   task_sha=task_sha)
    base_task = _route_task(tmp_path, contract_ref=contract_ref,
                            task_path=task_path, task_sha=task_sha)
    authorities = _Authorities(tmp_path)
    factory = FakeRunnerFactory()
    task = replace(base_task, provider_endpoint=None, provider_security=None,
                   expected_configuration_generation=None)
    with pytest.raises(ZeroRelayReviewExecutionError) as e:
        plan_reviewer_execution(
            route=route, route_task=task, provider_snapshot=authorities.snapshot,
            repo_root=authorities.repo_root, executable=EXEC, bundle_js=BUNDLE,
            timeout_seconds=120,
        )
    assert e.value.code == "REVIEW_PROVIDER_AUTHORITY_MISSING"
    with pytest.raises(ZeroRelayReviewExecutionError):
        _af_dispatch(authorities, route, task, factory)
    assert factory.model_effects == 0
    assert _af_resources(authorities) == {"admissions": [], "leases_released": []}


# ---------- WO223 R3 repair RED: Astra F2 ----------

def test_r3_v2_requirement_bound_route_reaches_wo226_planner(tmp_path: Path) -> None:
    from types import SimpleNamespace
    import test_zero_relay_review_task as review_task_tests
    from a_conductor.zero_relay_review_task import bind_direct_review_v2_route

    root, review, fs = review_task_tests._materialized_v2_real(tmp_path)
    task = review_task_tests._v2_route_task(root, review)
    binding = HarnessRuntimeBinding(
        harness_strategy=HarnessStrategy.ZCODE_APP_SERVER,
        runtime_provider_ref="runtime/provider",
        runtime_model_ref="runtime/model",
    )
    models = tuple(replace(model, runtime_binding=binding) for model in task.provider_profile.models)
    profile = replace(
        task.provider_profile,
        models=models,
        schema_version="1.1.0",
        harness_strategies=(HarnessStrategy.ZCODE_APP_SERVER,),
    )
    task = replace(
        task,
        provider_profile=profile,
        harness_dispatch=replace(
            task.harness_dispatch, harness_strategy=HarnessStrategy.ZCODE_APP_SERVER
        ),
    )
    route = bind_direct_review_v2_route(
        task, review, author=review_task_tests._identity(), filesystem=fs
    )
    plan = plan_reviewer_execution(
        route=route,
        route_task=task,
        provider_snapshot=SimpleNamespace(
            profile=profile, generation=7, endpoint=task.provider_endpoint
        ),
        repo_root=str(root),
        executable=EXEC,
        bundle_js=BUNDLE,
    )
    requirement = task.provider_requirement
    assert requirement is not None
    assert plan.operation_ref == requirement.operation_ref
    assert plan.fingerprint_spec.operation_ref == requirement.base_operation_ref



def test_r3_v2_planner_rejects_requirement_base_generation_and_security_drift(tmp_path: Path) -> None:
    from types import SimpleNamespace
    import test_zero_relay_review_task as review_task_tests
    from a_conductor.zero_relay_review_task import bind_direct_review_v2_route

    fixture_index = iter(range(10))

    def fixture():
        case_root = tmp_path / f"case-{next(fixture_index)}"
        root, review, fs = review_task_tests._materialized_v2_real(case_root)
        task = review_task_tests._v2_route_task(root, review)
        binding = HarnessRuntimeBinding(
            harness_strategy=HarnessStrategy.ZCODE_APP_SERVER,
            runtime_provider_ref="runtime/provider",
            runtime_model_ref="runtime/model",
        )
        models = tuple(replace(model, runtime_binding=binding) for model in task.provider_profile.models)
        profile = replace(
            task.provider_profile,
            models=models,
            schema_version="1.1.0",
            harness_strategies=(HarnessStrategy.ZCODE_APP_SERVER,),
        )
        task = replace(
            task,
            provider_profile=profile,
            harness_dispatch=replace(
                task.harness_dispatch, harness_strategy=HarnessStrategy.ZCODE_APP_SERVER
            ),
        )
        route = bind_direct_review_v2_route(
            task, review, author=review_task_tests._identity(), filesystem=fs
        )
        snapshot = SimpleNamespace(profile=profile, generation=7, endpoint=task.provider_endpoint)
        return root, task, route, snapshot

    root, task, route, snapshot = fixture()
    object.__setattr__(task.provider_requirement, "base_operation_ref", "zcode-task-v1:" + "f" * 64)
    with pytest.raises(ZeroRelayReviewExecutionError) as exc:
        plan_reviewer_execution(
            route=route, route_task=task, provider_snapshot=snapshot,
            repo_root=str(root), executable=EXEC, bundle_js=BUNDLE,
        )
    assert exc.value.code == "REVIEW_TASK_REQUIREMENT_BASE_OPERATION_MISMATCH"

    root, task, route, snapshot = fixture()
    object.__setattr__(task.provider_requirement, "expected_configuration_generation", 8)
    with pytest.raises(ZeroRelayReviewExecutionError) as exc:
        plan_reviewer_execution(
            route=route, route_task=task, provider_snapshot=snapshot,
            repo_root=str(root), executable=EXEC, bundle_js=BUNDLE,
        )
    assert exc.value.code == "REVIEW_TASK_REQUIREMENT_GENERATION_MISMATCH"

    root, task, route, snapshot = fixture()
    object.__setattr__(
        task.provider_requirement,
        "provider_security",
        review_task_tests._v2_security(host="other.example"),
    )
    with pytest.raises(ZeroRelayReviewExecutionError) as exc:
        plan_reviewer_execution(
            route=route, route_task=task, provider_snapshot=snapshot,
            repo_root=str(root), executable=EXEC, bundle_js=BUNDLE,
        )
    assert exc.value.code == "REVIEW_TASK_REQUIREMENT_SECURITY_MISMATCH"


def test_r3_v2_planner_rejects_wrapped_dispatch_operation_drift(tmp_path: Path) -> None:
    from types import SimpleNamespace
    import test_zero_relay_review_task as review_task_tests
    from a_conductor.zero_relay_review_task import bind_direct_review_v2_route

    root, review, fs = review_task_tests._materialized_v2_real(tmp_path)
    task = review_task_tests._v2_route_task(root, review)
    binding = HarnessRuntimeBinding(
        harness_strategy=HarnessStrategy.ZCODE_APP_SERVER,
        runtime_provider_ref="runtime/provider",
        runtime_model_ref="runtime/model",
    )
    models = tuple(replace(model, runtime_binding=binding) for model in task.provider_profile.models)
    profile = replace(
        task.provider_profile,
        models=models,
        schema_version="1.1.0",
        harness_strategies=(HarnessStrategy.ZCODE_APP_SERVER,),
    )
    task = replace(
        task,
        provider_profile=profile,
        harness_dispatch=replace(task.harness_dispatch, harness_strategy=HarnessStrategy.ZCODE_APP_SERVER),
    )
    route = bind_direct_review_v2_route(
        task, review, author=review_task_tests._identity(), filesystem=fs
    )
    object.__setattr__(task.dispatch_request, "operation_ref", "provider-op:" + "e" * 64)
    with pytest.raises(ZeroRelayReviewExecutionError) as exc:
        plan_reviewer_execution(
            route=route,
            route_task=task,
            provider_snapshot=SimpleNamespace(profile=profile, generation=7, endpoint=task.provider_endpoint),
            repo_root=str(root),
            executable=EXEC,
            bundle_js=BUNDLE,
        )
    assert exc.value.code == "REVIEW_OPERATION_REF_MISMATCH"


# ══════════════════════════════════════════════════════════════════════
# WO-P1-223 RE1 — verdict-blind verification + one version-CAS promotion
# BEFORE immutable handoff minting (closes production exit-0
# reachability without weakening fail-closed C1)
# ══════════════════════════════════════════════════════════════════════

def _route_for(tmp_path):
    """Re-derive the v2 route for the bridge fixtures of this tmp root."""
    contract_ref, task_path, task_sha = _review_contract(tmp_path)
    return _route(tmp_path, contract_ref=contract_ref, task_path=task_path,
                  task_sha=task_sha)


def test_re1_production_exit0_promotes_before_handoff_and_is_c1_eligible(tmp_path):
    """RE-1 RED discriminator: the accepted supervised collect semantics
    durably land every exit-0 reviewer run in VERIFICATION_REQUIRED. Only a
    verdict-blind verification + one existing-store version-CAS promotion
    BEFORE the handoff pins record state/version lets the production exit-0
    path mint a C1-eligible ACCEPTED handoff."""
    factory = FakeRunnerFactory()  # production shape: VR + exit 0 + artifacts
    result, authorities, backend = _execute(tmp_path, runner_factory=factory)
    assert result.outcome == "EXECUTED"
    handoff = result.handoff
    assert handoff is not None
    # promotion happened exactly once, BEFORE the handoff pinned the record
    assert handoff.record_state == "SUCCEEDED"
    promoted = authorities.execution_store.get(handoff.runtime_execution_id)
    assert promoted.execution_state is ExecutionProcessState.SUCCEEDED
    assert handoff.record_version == promoted.version
    # create -> result metadata -> terminal state -> promotion == version 4
    assert promoted.version == 4
    events = authorities.execution_store.list_events(promoted.execution_id)
    from a_conductor.zero_relay_review_verification import (
        parse_promotion_evidence_ref,
    )
    promotion_events = [
        e for e in events
        if e.evidence_ref is not None
        and e.evidence_ref.startswith("zra2-review-verification-v2:")
    ]
    assert len(promotion_events) == 1
    assert promotion_events[0].execution_state is ExecutionProcessState.SUCCEEDED
    # RE2-A: the promotion event carries the strict versioned exact
    # resource identity of THIS reviewer attempt
    identity = parse_promotion_evidence_ref(promotion_events[0].evidence_ref)
    assert identity.execution_id == promoted.execution_id
    assert identity.review_contract_ref == backend._plan.review_contract_ref
    assert identity.review_task_sha256 == backend._plan.review_task_sha256
    assert identity.worker_id == backend._plan.reviewer_worker_id
    assert identity.project_id == backend._plan.project_id
    assert identity.repo_root == backend._plan.repo_root
    assert identity.branch == backend._plan.branch
    assert identity.head == backend._plan.head
    assert identity.provider_id == backend._plan.provider_id
    assert identity.model_id == backend._plan.model_id
    assert identity.dispatch_execution_id == backend._plan.dispatch_execution_id
    assert identity.batch_id == backend._plan.batch_id
    assert identity.provider_generation == 1
    assert identity.lease_id == handoff.lease_id
    assert identity.lease_session_id == handoff.lease_session_id
    assert identity.lease_task_id == handoff.lease_task_id
    assert identity.admission_id == handoff.admission_id
    # the same durable store now composes the C1 evidence for the verdict
    evidence = compose_direct_review_evidence_from_store(
        author=AUTHOR, route=_route_for(tmp_path), handoff=handoff,
        store=authorities.execution_store,
    )
    assert evidence.disposition is ReviewDisposition.ACCEPTED
    assert evidence.reviewer_execution_id == handoff.runtime_execution_id


def test_re1_reconcile_after_crash_before_promotion_cannot_mint_handoff_r6(tmp_path):
    """Crash after the exit-0 model effect (record VR, resources still
    held), R6 amendment: the replay holds no durable exact lease id, so it
    must NOT release the owner-key lease, NOT mint a v2 promotion identity
    from owner-key inference, and NOT fabricate a handoff. The
    exact-dispatch admission reconciles independently; typed recovery is
    returned; the record keeps its pre-replay durable truth."""
    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    seeded = _seed_completed(authorities, plan, "exec-crash-vr")
    outcome = authorities.lease_broker.acquire(route_task.lease_request, route_task.candidates)
    assert outcome.kind is LeaseOutcomeKind.LEASED
    admission = authorities.provider_store.acquire_admission(
        provider_id="zcode-glm", execution_id=route.dispatch_execution_id,
        batch_id=plan.batch_id, expected_max_concurrency=2, now=NOW,
        ttl_seconds=600, expected_configuration_generation=1,
    ).admission
    result = execute_review_dispatch(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        provider_store=authorities.provider_store, lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store, execution_store=authorities.execution_store,
        job_store=authorities.job_store, runner_factory=factory,
        secret_resolver=authorities.secret_resolver, repo_root=authorities.repo_root,
        executable=EXEC, bundle_js=BUNDLE, clock=lambda: NOW,
    )
    assert result.outcome == "RECOVERY_REQUIRED"
    assert result.reason_code == "LEASE_OWNERSHIP_UNPROVEN"
    assert result.handoff is None
    assert factory.model_effects == 0
    # nothing was promoted or pinned: the durable truth is unchanged
    record = authorities.execution_store.get("exec-crash-vr")
    assert record.execution_state is ExecutionProcessState.VERIFICATION_REQUIRED
    assert record.version == seeded.version
    from a_conductor.zero_relay_review_verification import (
        resolve_promotion_resource_identity,
    )
    assert resolve_promotion_resource_identity(
        authorities.execution_store, "exec-crash-vr") is None
    # the exact-dispatch admission reconciled independently; lease retained
    assert authorities.provider_store.get_admission(
        admission.admission_id).status == "RELEASED"
    assert authorities.lease_store.inspect_health(
        outcome.lease.lease_id, now=NOW).lease.released_at is None


def test_re1_reconcile_after_promote_crash_retains_lease_r6(tmp_path):
    """Crash AFTER a legacy-evidence promotion (record SUCCEEDED, resources
    still held), R6 amendment: the replay has no durable exact lease id —
    it must not mutate the promoted record (no events, same version), must
    not release the owner-key lease, and returns typed recovery with no
    handoff; the exact-dispatch admission reconciles independently."""
    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    seeded = _seed_completed(authorities, plan, "exec-crash-promoted",
                             state=ExecutionProcessState.SUCCEEDED)
    events_before = authorities.execution_store.list_events(seeded.execution_id)
    outcome = authorities.lease_broker.acquire(route_task.lease_request, route_task.candidates)
    assert outcome.kind is LeaseOutcomeKind.LEASED
    admission = authorities.provider_store.acquire_admission(
        provider_id="zcode-glm", execution_id=route.dispatch_execution_id,
        batch_id=plan.batch_id, expected_max_concurrency=2, now=NOW,
        ttl_seconds=600, expected_configuration_generation=1,
    ).admission
    result = execute_review_dispatch(
        route=route, route_task=route_task, provider_snapshot=authorities.snapshot,
        provider_store=authorities.provider_store, lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store, execution_store=authorities.execution_store,
        job_store=authorities.job_store, runner_factory=factory,
        secret_resolver=authorities.secret_resolver, repo_root=authorities.repo_root,
        executable=EXEC, bundle_js=BUNDLE, clock=lambda: NOW,
    )
    assert result.outcome == "RECOVERY_REQUIRED"
    assert result.reason_code == "LEASE_OWNERSHIP_UNPROVEN"
    assert result.handoff is None
    assert factory.model_effects == 0
    # zero mutation of the promoted durable truth
    record = authorities.execution_store.get(seeded.execution_id)
    assert record.execution_state is ExecutionProcessState.SUCCEEDED
    assert record.version == seeded.version
    assert authorities.execution_store.list_events(seeded.execution_id) == events_before
    # admission reconciled independently; owner-key lease retained
    assert authorities.provider_store.get_admission(
        admission.admission_id).status == "RELEASED"
    assert authorities.lease_store.inspect_health(
        outcome.lease.lease_id, now=NOW).lease.released_at is None


def test_re1_verification_failure_cleans_up_and_mints_no_handoff(tmp_path):
    """Verification failure (tampered report binding): truthful terminal
    cleanup still happens, no promotion, and no success handoff."""
    factory = FakeRunnerFactory(report_overrides={"response_sha256": "9" * 64})
    result, authorities, backend = _execute(tmp_path, runner_factory=factory)
    assert result.outcome == "RECOVERY_REQUIRED"
    assert result.handoff is None
    assert result.reason_code.startswith("REVIEW_VERIFICATION_")
    # the durable record was NOT promoted
    record = authorities.execution_store.get(factory.execution_ids[0])
    assert record.execution_state is ExecutionProcessState.VERIFICATION_REQUIRED
    # truthful cleanup semantics are preserved
    admission = _admission_by_execution(authorities, backend._plan.dispatch_execution_id)
    assert admission is not None and admission.status == "RELEASED"
    leases = _all_leases(authorities)
    assert leases and all(l.released_at is not None for l in leases)


def test_re1_nonzero_exit_terminal_failure_never_promotes_or_mints(tmp_path):
    """A terminal-failure record (nonzero durable exit) is fail-closed
    terminal-unusable: no promotion, no handoff, cleanup only."""
    factory = FakeRunnerFactory(exit_code=3, execution_state=ExecutionProcessState.FAILED)
    result, authorities, backend = _execute(tmp_path, runner_factory=factory)
    assert result.outcome == "RECOVERY_REQUIRED"
    assert result.handoff is None
    record = authorities.execution_store.get(factory.execution_ids[0])
    assert record.execution_state is ExecutionProcessState.FAILED
    admission = _admission_by_execution(authorities, backend._plan.dispatch_execution_id)
    assert admission is not None and admission.status == "RELEASED"


def test_re1_live_winner_vr_record_is_not_stolen_by_reconcile(tmp_path):
    """AF1 extension (RE1): while a dispatch winner sits between its exit-0
    run and the promotion, a concurrent replay must not steal the promotion
    CAS or release its resources — the dispatch job is still EXECUTING."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    plan, authorities, route, route_task = _bridge(tmp_path)
    entered, proceed = Event(), Event()
    inner = FakeRunnerFactory()

    def paused_factory(**kwargs):
        runner = inner(**kwargs)
        original_run = runner.run

        def run(**run_kwargs):
            result = original_run(**run_kwargs)
            entered.set()  # VR record + artifacts are durable now
            assert proceed.wait(10), "probe barrier timed out"
            return result

        runner.run = run
        return runner

    with ThreadPoolExecutor(max_workers=1) as pool:
        winner = pool.submit(_af_dispatch, authorities, route, route_task, paused_factory)
        try:
            assert entered.wait(10)
            before = _af_resources(authorities)
            loser = _af_dispatch(authorities, route, route_task, inner)
            after = _af_resources(authorities)
        finally:
            proceed.set()
        first = winner.result(timeout=30)
    # the loser could not promote/release over the live winner
    assert after == before, "losing replay stole the live winner's resources"
    assert loser.outcome == "RECOVERY_REQUIRED"
    assert loser.reason_code == "REVIEW_WINNER_ACTIVE"
    assert loser.handoff is None
    assert inner.model_effects == 1
    # the winner alone promoted and minted the handoff
    assert first.outcome == "EXECUTED"
    assert first.handoff is not None
    assert first.handoff.record_state == "SUCCEEDED"


# ══════════════════════════════════════════════════════════════════════
# WO-P1-223 RE2-A — lost-handoff durable replay through the strict
# versioned promotion identity (exact historical lease/admission truth,
# zero second model effect, legacy evidence stays fail-closed)
# ══════════════════════════════════════════════════════════════════════

_V2_PREFIX = "zra2-review-verification-v2:"


def _identity_for(plan, execution_id, lease, admission, *, generation=1,
                  **overrides):
    from a_conductor.zero_relay_review_verification import (
        ReviewPromotionResourceIdentity,
    )

    fields = dict(
        execution_id=execution_id,
        review_contract_ref=plan.review_contract_ref,
        review_task_sha256=plan.review_task_sha256,
        worker_id=plan.reviewer_worker_id,
        project_id=plan.project_id,
        repo_root=plan.repo_root,
        branch=plan.branch,
        head=plan.head,
        provider_id=plan.provider_id,
        model_id=plan.model_id,
        dispatch_execution_id=plan.dispatch_execution_id,
        batch_id=plan.batch_id,
        provider_generation=generation,
        lease_id=lease.lease_id,
        lease_session_id=lease.session_id,
        lease_task_id=lease.task_id,
        admission_id=admission.admission_id,
    )
    fields.update(overrides)
    return ReviewPromotionResourceIdentity(**fields)


def _promote_v2(authorities, execution_id, identity, *, from_version,
                evidence_override=None):
    from a_conductor.zero_relay_review_verification import (
        build_promotion_evidence_ref,
    )

    evidence = evidence_override or build_promotion_evidence_ref(identity)
    return authorities.execution_store.set_execution_state(
        execution_id,
        ExecutionProcessState.SUCCEEDED,
        expected_version=from_version,
        evidence_ref=evidence,
    )


def _active_resources(authorities, route_task, plan, *, generation=1):
    lease_outcome = authorities.lease_broker.acquire(
        route_task.lease_request, route_task.candidates
    )
    assert lease_outcome.kind is LeaseOutcomeKind.LEASED
    admission = authorities.provider_store.acquire_admission(
        provider_id="zcode-glm", execution_id=plan.dispatch_execution_id,
        batch_id=plan.batch_id, expected_max_concurrency=2, now=NOW,
        ttl_seconds=600, expected_configuration_generation=generation,
    ).admission
    return lease_outcome.lease, admission


def test_re2a_lost_handoff_after_cleanup_reconstructs_exact_reuse_completed(tmp_path):
    """THE RE2-A defect RED: crash after promotion AND cleanup but before the
    in-memory handoff is consumed -> the active-only lease lookup resolves
    nothing forever. With the strict identity persisted at promotion, replay
    reconstructs the EXACT REUSE_COMPLETED handoff with zero new model
    effects, zero new lease/admission rows, and the existing C1 composer
    still accepts the reconstructed durable truth."""
    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    first = _af_dispatch(authorities, route, route_task, factory)
    assert first.outcome == "EXECUTED"
    original = first.handoff
    assert original is not None
    # the original rows are terminal (cleanup completed before the crash)
    original_lease = authorities.lease_store.inspect_health(
        original.lease_id, now=NOW).lease
    assert original_lease.released_at is not None
    assert authorities.provider_store.get_admission(
        original.admission_id).status == "RELEASED"
    rows_before = (len(_all_leases(authorities)),
                   len(_all_admissions(authorities)))
    fresh = FakeRunnerFactory()
    second = _af_dispatch(authorities, route, route_task, fresh)
    assert second.outcome == "REUSE_COMPLETED"
    handoff = second.handoff
    assert handoff is not None
    assert handoff.runtime_execution_id == original.runtime_execution_id
    assert handoff.lease_id == original.lease_id
    assert handoff.admission_id == original.admission_id
    assert handoff.record_state == "SUCCEEDED"
    assert handoff.record_version == original.record_version
    assert handoff.exit_code == 0
    assert handoff.cleanup_terminal is True
    assert handoff.lease_released is True
    assert handoff.admission_status == "RELEASED"
    assert handoff.lease_session_id == route_task.lease_request.session_id
    assert fresh.model_effects == 0
    assert (len(_all_leases(authorities)),
            len(_all_admissions(authorities))) == rows_before
    # the existing C1 composer still accepts the reconstructed handoff
    evidence = compose_direct_review_evidence_from_store(
        author=AUTHOR, route=_route_for(tmp_path), handoff=handoff,
        store=authorities.execution_store,
    )
    assert evidence.disposition is ReviewDisposition.ACCEPTED
    assert evidence.reviewer_execution_id == handoff.runtime_execution_id


def test_re2a_replay_is_idempotent_and_concurrent_without_second_effect(tmp_path):
    """Repeat and concurrent replays of a completed attempt are idempotent:
    every lane reconstructs the SAME exact identities, with zero new rows,
    zero new lease/acquisition and zero second model effect."""
    from concurrent.futures import ThreadPoolExecutor

    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    first = _af_dispatch(authorities, route, route_task, factory)
    assert first.outcome == "EXECUTED"
    original = first.handoff
    rows_before = (len(_all_leases(authorities)),
                   len(_all_admissions(authorities)))
    replay_factory = FakeRunnerFactory()
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [
            pool.submit(_af_dispatch, authorities, route, route_task,
                        replay_factory)
            for _ in range(4)
        ]
        outcomes = [f.result(timeout=120) for f in futures]
    assert {o.outcome for o in outcomes} == {"REUSE_COMPLETED"}
    assert {o.handoff.lease_id for o in outcomes} == {original.lease_id}
    assert {o.handoff.admission_id for o in outcomes} == {original.admission_id}
    assert replay_factory.model_effects == 0
    assert (len(_all_leases(authorities)),
            len(_all_admissions(authorities))) == rows_before
    records = authorities.execution_store.find_by_fingerprint(plan.fingerprint)
    assert len(records) == 1


def test_re2a_crash_after_promotion_before_cleanup_cleans_once(tmp_path):
    """Crash after the promotion but BEFORE cleanup: the exact original
    resources are still ACTIVE; replay resolves them by exact id through the
    existing historical APIs, performs the existing idempotent cleanup once,
    and reconstructs the REUSE_COMPLETED handoff — zero new rows/effects."""
    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    seeded = _seed_completed(authorities, plan, "exec-prom-crash")
    lease, admission = _active_resources(authorities, route_task, plan)
    identity = _identity_for(plan, "exec-prom-crash", lease, admission)
    promoted = _promote_v2(authorities, "exec-prom-crash", identity,
                           from_version=seeded.version)
    assert promoted.execution_state is ExecutionProcessState.SUCCEEDED
    rows_before = (len(_all_leases(authorities)),
                   len(_all_admissions(authorities)))
    fresh = FakeRunnerFactory()
    result = _af_dispatch(authorities, route, route_task, fresh)
    assert result.outcome == "REUSE_COMPLETED"
    handoff = result.handoff
    assert handoff is not None
    assert handoff.runtime_execution_id == "exec-prom-crash"
    assert handoff.lease_id == lease.lease_id
    assert handoff.admission_id == admission.admission_id
    assert fresh.model_effects == 0
    assert authorities.provider_store.get_admission(
        admission.admission_id).status == "RELEASED"
    assert authorities.lease_store.inspect_health(
        lease.lease_id, now=NOW).lease.released_at is not None
    assert (len(_all_leases(authorities)),
            len(_all_admissions(authorities))) == rows_before
    # second replay after cleanup: idempotent, exact same truth
    again = _af_dispatch(authorities, route, route_task, FakeRunnerFactory())
    assert again.outcome == "REUSE_COMPLETED"
    assert again.handoff.lease_id == lease.lease_id
    assert again.handoff.admission_id == admission.admission_id
    assert (len(_all_leases(authorities)),
            len(_all_admissions(authorities))) == rows_before


def test_re2a_generation_drift_replay_uses_event_pinned_generation(tmp_path):
    """Provider generation drift AFTER the completed attempt must not block
    the replay of completed work: the binding uses the generation pinned in
    the original promotion event, not the ambient store generation."""
    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    first = _af_dispatch(authorities, route, route_task, factory)
    assert first.outcome == "EXECUTED"
    original = first.handoff
    # the provider configuration advances after the attempt completed
    authorities.provider_store.save_endpoint(
        ProviderEndpointConfig("zcode-desktop", "http://127.0.0.2"),
        expected_generation=1,
    )
    drifted = authorities.provider_store.load_provider_snapshot("zcode-glm")
    assert int(drifted.generation) == 2
    rows_before = (len(_all_leases(authorities)),
                   len(_all_admissions(authorities)))
    fresh = FakeRunnerFactory()
    replay = _af_dispatch(authorities, route, route_task, fresh)
    assert replay.outcome == "REUSE_COMPLETED"
    assert replay.handoff is not None
    assert replay.handoff.lease_id == original.lease_id
    assert replay.handoff.admission_id == original.admission_id
    assert fresh.model_effects == 0
    assert (len(_all_leases(authorities)),
            len(_all_admissions(authorities))) == rows_before
    # direct reconcile with NO caller-side generation expectation also
    # reconstructs: the event-pinned generation alone drives the binding
    direct = reconcile_review_execution(
        plan=plan, route_task=route_task,
        provider_store=authorities.provider_store,
        lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store,
        execution_store=authorities.execution_store,
        clock=lambda: NOW, expected_generation=None,
    )
    assert direct.outcome == "REUSE_COMPLETED"
    assert direct.handoff.lease_id == original.lease_id


def test_re2a_active_same_owner_different_lease_id_is_typed_conflict(tmp_path):
    """An ACTIVE lease under the same owner keys but a DIFFERENT id than the
    event-pinned one is a typed conflict: nothing is released, no handoff,
    no model effect (the active lease belongs to a different attempt)."""
    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    first = _af_dispatch(authorities, route, route_task, factory)
    assert first.outcome == "EXECUTED"
    original = first.handoff
    # the original lease is released, so a NEW attempt may acquire the same
    # owner keys — a genuinely different lease id
    new_outcome = authorities.lease_broker.acquire(
        route_task.lease_request, route_task.candidates
    )
    assert new_outcome.kind is LeaseOutcomeKind.LEASED
    assert new_outcome.lease.lease_id != original.lease_id
    rows_before = (len(_all_leases(authorities)),
                   len(_all_admissions(authorities)))
    fresh = FakeRunnerFactory()
    result = _af_dispatch(authorities, route, route_task, fresh)
    assert result.outcome == "RECOVERY_REQUIRED"
    assert result.reason_code == "EVIDENCE_LEASE_IDENTITY_CONFLICT"
    assert result.handoff is None
    assert fresh.model_effects == 0
    # release NOTHING: the new active lease is untouched
    fresh_lease = authorities.lease_store.inspect_health(
        new_outcome.lease.lease_id, now=NOW).lease
    assert fresh_lease.released_at is None
    assert (len(_all_leases(authorities)),
            len(_all_admissions(authorities))) == rows_before


def test_re2a_foreign_and_missing_resource_pointers_fail_closed(tmp_path):
    """Foreign or missing lease/admission pointers inside the promotion
    identity are typed recovery: nothing is released, no handoff, no model
    effect, zero new rows."""
    cases = [
        ("admission-missing", dict(admission_id="provider-admission-never"),
         "EVIDENCE_ADMISSION_POINTER_MISSING"),
        ("admission-foreign", None, "EVIDENCE_ADMISSION_POINTER_FOREIGN"),
        ("lease-missing", dict(lease_id="lease-never-exists"),
         "EVIDENCE_LEASE_POINTER_MISSING"),
        ("lease-foreign", None, "EVIDENCE_LEASE_POINTER_FOREIGN"),
    ]
    for index, (kind, overrides, code) in enumerate(cases):
        case_root = Path(str(tmp_path) + f"ptr-{index}")
        plan_c, auth_c, route_c, task_c = _bridge(case_root)
        seeded = _seed_completed(auth_c, plan_c, f"exec-ptr-{index}")
        lease_c, admission_c = _active_resources(auth_c, task_c, plan_c)
        if kind == "admission-foreign":
            # a genuinely foreign admission row (different dispatch
            # execution id) inside the SAME canonical store
            foreign_admission = auth_c.provider_store.acquire_admission(
                provider_id="zcode-glm", execution_id="dispatch-foreign-0001",
                batch_id=plan_c.batch_id, expected_max_concurrency=2, now=NOW,
                ttl_seconds=600, expected_configuration_generation=1,
            ).admission
            overrides = dict(admission_id=foreign_admission.admission_id)
        if kind == "lease-foreign":
            # a genuinely foreign lease row (different owner task) on
            # another worker inside the SAME canonical store
            other_candidate = WorkerLeaseCandidate(
                worker_id="a-worker-02", state="READY", reserved=False,
                active_task=False, capabilities=("code",),
                runtime_id="runtime-a-worker-02", project_id=PROJECT,
                worktree=str(case_root), branch=BRANCH, head=HEAD,
                health_fresh=True, ownership_known=True, dirty_state="CLEAN",
                mutation_authorized=True,
            )
            other_request = replace(
                task_c.lease_request,
                task_id="zra2-review-v1:" + "e" * 64,
                required_runtime_id="runtime-a-worker-02",
                ordered_worker_ids=("a-worker-02",),
            )
            other_outcome = auth_c.lease_broker.acquire(
                other_request, (other_candidate,))
            assert other_outcome.kind is LeaseOutcomeKind.LEASED
            overrides = dict(lease_id=other_outcome.lease.lease_id)
        identity = _identity_for(plan_c, seeded.execution_id, lease_c,
                                 admission_c, **overrides)
        _promote_v2(auth_c, seeded.execution_id, identity,
                    from_version=seeded.version)
        fresh = FakeRunnerFactory()
        result = _af_dispatch(auth_c, route_c, task_c, fresh)
        assert result.outcome == "RECOVERY_REQUIRED", code
        assert result.reason_code == code
        assert result.handoff is None
        assert fresh.model_effects == 0
        # release NOTHING: both the exact and any foreign rows stay as-is
        leases = _all_leases(auth_c)
        assert leases and all(l.released_at is None for l in leases)
        admissions = _all_admissions(auth_c)
        assert admissions and all(a.status == "ACTIVE" for a in admissions)


def test_re2a_malformed_oversized_duplicate_evidence_fail_closed(tmp_path):
    """Malformed, oversized, wrong-shape or duplicate/ambiguous promotion
    identity evidence is typed recovery: nothing released, no handoff."""
    import dataclasses

    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    seeded = _seed_completed(authorities, plan, "exec-bad-evidence")
    lease, admission = _active_resources(authorities, route_task, plan)
    identity = _identity_for(plan, "exec-bad-evidence", lease, admission)
    valid = dataclasses.asdict(identity)
    malformed_refs = [
        _V2_PREFIX + "not-json{",
        _V2_PREFIX + json.dumps({"unexpected": True}),
        _V2_PREFIX + json.dumps(
            {k: v for k, v in valid.items() if k != "lease_id"}),
        _V2_PREFIX + json.dumps({**valid, "provider_generation": "1"}),
        _V2_PREFIX + json.dumps({**valid, "repo_root": "x" * 3000}),
        # deep but <=2048-char JSON: decoder recursion overflow is typed
        # malformed evidence, never an untyped RecursionError at replay
        _V2_PREFIX + "[" * ((2048 - len(_V2_PREFIX)) // 2)
        + "]" * ((2048 - len(_V2_PREFIX)) // 2),
    ]
    malformed_refs.extend(
        _V2_PREFIX + json.dumps({**valid, field: value})
        for field in ("review_task_sha256", "head")
        for value in (None, 1, [], {}, True)
    )
    for index, evidence in enumerate(malformed_refs):
        case_root = Path(str(tmp_path) + f"mal-{index}")
        factory_case = FakeRunnerFactory()
        plan_c, auth_c, route_c, task_c = _bridge(
            case_root, runner_factory=factory_case)
        seeded_c = _seed_completed(auth_c, plan_c, f"exec-mal-{index}")
        lease_c, admission_c = _active_resources(auth_c, task_c, plan_c)
        identity_c = _identity_for(plan_c, seeded_c.execution_id, lease_c,
                                   admission_c)
        _promote_v2(auth_c, seeded_c.execution_id, identity_c,
                    from_version=seeded_c.version, evidence_override=evidence)
        fresh = FakeRunnerFactory()
        result = _af_dispatch(auth_c, route_c, task_c, fresh)
        assert result.outcome == "RECOVERY_REQUIRED", evidence[:60]
        assert result.reason_code == "REVIEW_PROMOTION_EVIDENCE_MALFORMED"
        assert result.handoff is None
        assert fresh.model_effects == 0
        leases = _all_leases(auth_c)
        assert leases and all(l.released_at is None for l in leases)
        admissions = _all_admissions(auth_c)
        assert admissions and all(a.status == "ACTIVE" for a in admissions)

    # duplicate v2 promotion events are ambiguous -> typed recovery
    dup_root = Path(str(tmp_path) + "dup")
    factory_dup = FakeRunnerFactory()
    plan_d, auth_d, route_d, task_d = _bridge(dup_root, runner_factory=factory_dup)
    seeded_d = _seed_completed(auth_d, plan_d, "exec-dup-evidence")
    lease_d, admission_d = _active_resources(auth_d, task_d, plan_d)
    identity_d = _identity_for(plan_d, "exec-dup-evidence", lease_d, admission_d)
    promoted_d = _promote_v2(auth_d, "exec-dup-evidence", identity_d,
                             from_version=seeded_d.version)
    _promote_v2(auth_d, "exec-dup-evidence", identity_d,
                from_version=promoted_d.version)
    fresh = FakeRunnerFactory()
    result = _af_dispatch(auth_d, route_d, task_d, fresh)
    assert result.outcome == "RECOVERY_REQUIRED"
    assert result.reason_code == "REVIEW_PROMOTION_EVIDENCE_AMBIGUOUS"
    assert result.handoff is None
    assert fresh.model_effects == 0
    leases = _all_leases(auth_d)
    assert leases and all(l.released_at is None for l in leases)


def test_re2a_unknown_evidence_version_stays_legacy_fail_closed(tmp_path):
    """A promotion carrying an UNKNOWN evidence version is not trusted as
    identity evidence: replay keeps the prior fail-closed behavior when the
    original rows are no longer active-resolvable."""
    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    seeded = _seed_completed(authorities, plan, "exec-unknown-evidence")
    lease, admission = _active_resources(authorities, route_task, plan)
    # both resources already terminal: only identity evidence could prove them
    authorities.provider_store.release_admission(
        admission.admission_id, provider_id="zcode-glm",
        execution_id=plan.dispatch_execution_id, batch_id=plan.batch_id, now=NOW,
    )
    authorities.lease_store.release(
        lease.lease_id, session_id=lease.session_id, task_id=lease.task_id,
        released_at=NOW,
    )
    unknown = "zra2-review-verification-v3:" + json.dumps(
        {"lease_id": lease.lease_id, "admission_id": admission.admission_id}
    )
    _promote_v2(authorities, "exec-unknown-evidence", None,
                from_version=seeded.version, evidence_override=unknown)
    rows_before = len(_all_leases(authorities))
    fresh = FakeRunnerFactory()
    result = _af_dispatch(authorities, route, route_task, fresh)
    assert result.outcome == "RECOVERY_REQUIRED"
    assert result.reason_code == "LEASE_IDENTITY_UNPROVEN"
    assert result.handoff is None
    assert fresh.model_effects == 0
    assert len(_all_leases(authorities)) == rows_before


def test_re2a_stale_lease_is_never_force_released(tmp_path):
    """A STALE (expired, unreleased) lease pointed at by the identity is
    never force-released: the canonical release fence refuses it and the
    replay ends in typed recovery with no handoff."""
    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    seeded = _seed_completed(authorities, plan, "exec-stale-lease")
    acquire = authorities.lease_store.try_acquire_result(
        route_task.lease_request, route_task.candidates[0],
        lease_id="lease-stale-0001", acquired_at="2026-09-12T10:00:00Z",
        expires_at="2026-09-12T11:00:00Z",  # expired well before NOW
    )
    assert acquire.created is True
    stale_lease = acquire.lease
    admission = authorities.provider_store.acquire_admission(
        provider_id="zcode-glm", execution_id=plan.dispatch_execution_id,
        batch_id=plan.batch_id, expected_max_concurrency=2, now=NOW,
        ttl_seconds=600, expected_configuration_generation=1,
    ).admission
    authorities.provider_store.release_admission(
        admission.admission_id, provider_id="zcode-glm",
        execution_id=plan.dispatch_execution_id, batch_id=plan.batch_id, now=NOW,
    )
    identity = _identity_for(plan, "exec-stale-lease", stale_lease, admission)
    _promote_v2(authorities, "exec-stale-lease", identity,
                from_version=seeded.version)
    fresh = FakeRunnerFactory()
    result = _af_dispatch(authorities, route, route_task, fresh)
    assert result.outcome == "RECOVERY_REQUIRED"
    assert result.handoff is None
    assert result.reason_code.startswith("LEASE_CLEANUP_")
    assert fresh.model_effects == 0
    # the stale lease was NOT force-released
    row = authorities.lease_store.inspect_health(
        stale_lease.lease_id, now=NOW)
    from a_conductor.worker_lease import LeaseHealthKind
    assert row.kind is LeaseHealthKind.STALE
    assert row.lease.released_at is None


def test_re2a_legacy_promotion_evidence_keeps_fail_closed_behavior(tmp_path):
    """Legacy promotion evidence (no v2 identity) preserves the exact prior
    behavior: after the original rows become invisible to the active-only
    lookup, replay stays LEASE_IDENTITY_UNPROVEN with zero new rows."""
    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    seeded = _seed_completed(authorities, plan, "exec-legacy-evidence")
    lease, admission = _active_resources(authorities, route_task, plan)
    # legacy promotion evidence shape (plain prefix, no identity payload)
    authorities.execution_store.set_execution_state(
        "exec-legacy-evidence", ExecutionProcessState.SUCCEEDED,
        expected_version=seeded.version,
        evidence_ref="zra2-review-verification:exec-legacy-evidence",
    )
    authorities.provider_store.release_admission(
        admission.admission_id, provider_id="zcode-glm",
        execution_id=plan.dispatch_execution_id, batch_id=plan.batch_id, now=NOW,
    )
    authorities.lease_store.release(
        lease.lease_id, session_id=lease.session_id, task_id=lease.task_id,
        released_at=NOW,
    )
    rows_before = len(_all_leases(authorities))
    fresh = FakeRunnerFactory()
    result = _af_dispatch(authorities, route, route_task, fresh)
    assert result.outcome == "RECOVERY_REQUIRED"
    assert result.reason_code == "LEASE_IDENTITY_UNPROVEN"
    assert result.handoff is None
    assert fresh.model_effects == 0
    assert len(_all_leases(authorities)) == rows_before


# ── WO-P1-223 R3 repair (2026-09-15): truncation-safe admission recovery
# and EXISTING-lease launch ownership refusal ────────────────────────────


def _filler_admissions(authorities, plan, count: int) -> None:
    """Released filler admission rows (distinct dispatch executions) with
    strictly increasing acquired_at so newest-first paging is stable."""
    for i in range(count):
        execution_id = f"dispatch-filler-{i:04d}"
        admission = authorities.provider_store.acquire_admission(
            provider_id="zcode-glm", execution_id=execution_id,
            batch_id=plan.batch_id, expected_max_concurrency=2,
            now=NOW + timedelta(seconds=i), ttl_seconds=600,
            expected_configuration_generation=1,
        ).admission
        authorities.provider_store.release_admission(
            admission.admission_id, provider_id="zcode-glm",
            execution_id=execution_id, batch_id=plan.batch_id,
            now=NOW + timedelta(seconds=i),
        )


def test_r3_admission_recovery_beyond_default_page_is_never_false_absence(tmp_path):
    """R3 repair 2 RED: a bounded newest-first admission page must never
    convert possible truncation into None. The exact execution's admission,
    older than the store's default page, is still found by scanning up to
    the store's public maximum; genuine absence under a not-full page still
    resolves None."""
    from a_conductor.zero_relay_review_execution import _find_held_admission_readonly

    plan, authorities, route, route_task = _bridge(tmp_path)
    # the exact admission is the OLDEST row for this provider (still ACTIVE)
    exact = authorities.provider_store.acquire_admission(
        provider_id="zcode-glm", execution_id=route.dispatch_execution_id,
        batch_id=plan.batch_id, expected_max_concurrency=2,
        now=NOW - timedelta(seconds=1), ttl_seconds=600,
        expected_configuration_generation=1,
    ).admission
    # 60 newer released fillers push the exact row past the 50-row default
    _filler_admissions(authorities, plan, 60)
    found = _find_held_admission_readonly(
        authorities.provider_store, provider_id="zcode-glm",
        execution_id=route.dispatch_execution_id,
        batch_id=plan.batch_id, expected_generation=1,
    )
    assert found is not None and found.admission_id == exact.admission_id
    assert found.status == "ACTIVE"
    # genuine absence under a not-full page remains None (unchanged truth)
    absent = _find_held_admission_readonly(
        authorities.provider_store, provider_id="zcode-glm",
        execution_id="dispatch-never-existed",
        batch_id=plan.batch_id, expected_generation=1,
    )
    assert absent is None


def test_r3_admission_recovery_full_max_page_without_match_is_typed_unknown(tmp_path):
    """R3 repair 2 RED: when even the store's public maximum page is full
    with no exact execution match, absence is UNPROVEN — typed recovery
    (never a false None), and a legacy reconcile under it releases nothing."""
    from a_conductor.provider_config_store import _MAX_ADMISSION_LIST_LIMIT
    from a_conductor.zero_relay_review_execution import _find_held_admission_readonly

    plan, authorities, route, route_task = _bridge(tmp_path)
    _filler_admissions(authorities, plan, _MAX_ADMISSION_LIST_LIMIT)
    with pytest.raises(ZeroRelayReviewExecutionError) as exc:
        _find_held_admission_readonly(
            authorities.provider_store, provider_id="zcode-glm",
            execution_id=route.dispatch_execution_id,
            batch_id=plan.batch_id, expected_generation=1,
        )
    assert exc.value.code == "ADMISSION_PRESENCE_UNPROVEN"
    # end-to-end: a legacy reconcile over an unprovable page fails typed
    # and keeps the exact held lease unreleased (no fabricated absence)
    _seed_completed(authorities, plan, "exec-fullpage")
    outcome = authorities.lease_broker.acquire(
        route_task.lease_request, route_task.candidates)
    assert outcome.kind is LeaseOutcomeKind.LEASED
    result = reconcile_review_execution(
        plan=plan, route_task=route_task,
        provider_store=authorities.provider_store,
        lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store,
        execution_store=authorities.execution_store,
        clock=lambda: NOW, expected_generation=1,
    )
    assert result.outcome == "RECOVERY_REQUIRED"
    assert result.reason_code == "ADMISSION_PRESENCE_UNPROVEN"
    assert result.handoff is None
    held = authorities.lease_store.inspect_health(
        outcome.lease.lease_id, now=NOW).lease
    assert held.released_at is None


def _job_context(plan) -> JobExecutionContext:
    return JobExecutionContext(
        job_id=plan.dispatch_execution_id,
        work_order_ref=plan.review_contract_ref,
        project_id=plan.project_id,
        worker_id=plan.reviewer_worker_id,
        attempt_no=1,
        max_attempts=1,
    )


def test_r3_existing_owner_lease_refuses_second_dispatch_context(tmp_path):
    """R3 repair 3 RED (deterministic cross-dispatch): an EXISTING owner-key
    lease is the live winner's authorization, never a fresh launch authority.
    A second dispatch context reaching the backend launch path while the
    winner still holds the owner-key lease must refuse BEFORE any admission
    acquisition or model effect, must NOT release the live winner's shared
    lease, and total model effects stay exactly 1 (the winner's)."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    factory = FakeRunnerFactory()
    plan, authorities, route, route_task = _bridge(tmp_path, runner_factory=factory)
    entered, proceed = Event(), Event()

    def paused_factory(**kwargs):
        entered.set()  # winner owns lease+admission; no execution record yet
        assert proceed.wait(10), "probe barrier timed out"
        return factory(**kwargs)

    winner = _dispatch_backend(
        plan, authorities, route, route_task, runner_factory=paused_factory)
    with ThreadPoolExecutor(max_workers=1) as pool:
        winner_run = pool.submit(winner.execute, plan.operation_ref,
                                 _job_context(plan))
        try:
            assert entered.wait(10)
            loser = _dispatch_backend(
                plan, authorities, route, route_task, runner_factory=factory)
            loser_result = loser.execute(plan.operation_ref, _job_context(plan))
            assert loser_result.success is False
            assert loser.failure_code == "REVIEW_LEASE_EXISTING_NOT_AUTHORIZED"
            assert loser_result.error_code == "REVIEW_LEASE_EXISTING_NOT_AUTHORIZED"
            # refusal happened BEFORE admission/model effect and released
            # NOTHING of the live winner's shared resources
            assert factory.model_effects == 0
            leases = _all_leases(authorities)
            assert len(leases) == 1 and leases[0].released_at is None
            admissions = _all_admissions(authorities)
            assert len(admissions) == 1 and admissions[0].status == "ACTIVE"
        finally:
            proceed.set()
        winner_result = winner_run.result(timeout=60)
    assert winner_result.success is True
    assert factory.model_effects == 1  # total model effects stay exactly 1
    assert winner.handoff is not None and winner.handoff.outcome == "EXECUTED"
    # the WINNER (not the loser) performed the terminal cleanup
    admissions = _all_admissions(authorities)
    assert admissions and all(a.status == "RELEASED" for a in admissions)
    leases = _all_leases(authorities)
    assert leases and all(l.released_at is not None for l in leases)


# ── WO-P1-223 R5 repair (2026-09-15): an owner-key lease lookup is NOT
# dispatch provenance — recovery cleanup must positively attribute the
# owner-key lease to the exact dispatch or retain it (typed recovery) ────


def _identity_variant(tmp_path, base_plan, *, graph_run_id: str):
    """A DISTINCT dispatch/job identity for the same review contract: same
    session/task owner keys, worker, provider and project; only the
    GraphDispatch key (job id == dispatch execution id) differs."""
    task = _route_task(
        tmp_path, contract_ref=base_plan.review_contract_ref,
        task_path=base_plan.review_task_path,
        task_sha=base_plan.review_task_sha256, graph_run_id=graph_run_id,
    )
    route = _route(
        tmp_path, contract_ref=base_plan.review_contract_ref,
        task_path=base_plan.review_task_path,
        task_sha=base_plan.review_task_sha256,
        dispatch_execution_id=task.dispatch_request.key.job_id,
    )
    return route, task


def test_r5_cross_dispatch_loser_retains_live_winner_owner_key_lease(tmp_path):
    """R5 RED (Issue #214 R3 P1, true cross-dispatch entry): winner A paused
    after lease+admission acquisition but BEFORE any execution record;
    loser B (distinct dispatch/job identity) refuses the shared EXISTING
    lease; B's RECONCILE/no-record cleanup must NOT release A's owner-key
    lease or admission; a later C cannot obtain launch authority or a
    second model effect while A remains live; A then completes alone."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    factory = FakeRunnerFactory()
    plan_a, authorities, route_a, task_a = _bridge(tmp_path, runner_factory=factory)
    route_b, task_b = _identity_variant(tmp_path, plan_a, graph_run_id="run-2")
    route_c, task_c = _identity_variant(tmp_path, plan_a, graph_run_id="run-3")
    entered, proceed = Event(), Event()

    def paused_factory(**kwargs):
        entered.set()  # winner owns lease+admission; no execution record yet
        assert proceed.wait(10), "probe barrier timed out"
        return factory(**kwargs)

    with ThreadPoolExecutor(max_workers=1) as pool:
        winner = pool.submit(_af_dispatch, authorities, route_a, task_a,
                             paused_factory)
        try:
            assert entered.wait(10)
            loser = _af_dispatch(authorities, route_b, task_b,
                                 FakeRunnerFactory())
            # the loser refused EXISTING and its outcome is typed recovery
            assert loser.outcome == "RECOVERY_REQUIRED"
            assert loser.reason_code == "REVIEW_LEASE_EXISTING_NOT_AUTHORIZED"
            assert loser.handoff is None
            # the live winner's shared lease/admission were NOT released
            leases = _all_leases(authorities)
            assert len(leases) == 1 and leases[0].released_at is None
            admissions = _all_admissions(authorities)
            assert len(admissions) == 1 and admissions[0].status == "ACTIVE"
            # a later dispatch cannot obtain launch authority while A is live
            later = _af_dispatch(authorities, route_c, task_c,
                                 FakeRunnerFactory())
            assert later.outcome == "RECOVERY_REQUIRED"
            assert later.reason_code == "REVIEW_LEASE_EXISTING_NOT_AUTHORIZED"
            leases = _all_leases(authorities)
            assert len(leases) == 1 and leases[0].released_at is None
        finally:
            proceed.set()
        winner_result = winner.result(timeout=60)
    assert winner_result.outcome == "EXECUTED"
    assert factory.model_effects == 1  # exactly one model effect (the winner)
    assert winner_result.handoff is not None
    # the WINNER alone performed the terminal cleanup
    admissions = _all_admissions(authorities)
    assert admissions and all(a.status == "RELEASED" for a in admissions)
    leases = _all_leases(authorities)
    assert leases and all(l.released_at is not None for l in leases)


def test_r5_terminal_unusable_cross_dispatch_retains_owner_key_lease(tmp_path):
    """R5 RED (sibling `_terminal_unusable_cleanup`): a FAILED terminal
    equivalent replayed by a DISTINCT dispatch must not release the
    original attempt's owner-key lease through the AF2 cleanup — only the
    resource owner's own dispatch may clean it."""
    factory = FakeRunnerFactory(live_timeout=True)
    plan_a, authorities, route_a, task_a = _bridge(tmp_path, runner_factory=factory)
    first = _af_dispatch(authorities, route_a, task_a, factory)
    assert first.outcome == "RECOVERY_REQUIRED" and first.handoff is None
    # the retained live record later becomes terminal FAILED
    authorities.execution_store.set_execution_state(
        factory.execution_ids[0], ExecutionProcessState.FAILED, expected_version=1,
    )
    route_b, task_b = _identity_variant(tmp_path, plan_a, graph_run_id="run-2")
    loser = _af_dispatch(authorities, route_b, task_b, FakeRunnerFactory())
    assert loser.outcome == "RECOVERY_REQUIRED"
    assert loser.reason_code == "EQUIVALENT_TERMINAL_NOT_USABLE"
    # the cross-dispatch replay released NOTHING of the owner's resources
    leases = _all_leases(authorities)
    assert leases and all(l.released_at is None for l in leases)
    admissions = _all_admissions(authorities)
    assert admissions and all(a.status == "ACTIVE" for a in admissions)
    # the resource OWNER's own retry still reconciles the exact-dispatch
    # admission (R6): the owner-key lease row is retained — a pure replay
    # holds no durable exact lease id, so it is never released by inference
    owner_replay = _af_dispatch(authorities, route_a, task_a, FakeRunnerFactory())
    assert owner_replay.outcome == "RECOVERY_REQUIRED"
    assert owner_replay.reason_code == "EQUIVALENT_TERMINAL_NOT_USABLE"
    admissions = _all_admissions(authorities)
    assert admissions and all(a.status == "RELEASED" for a in admissions)
    leases = _all_leases(authorities)
    assert leases and all(l.released_at is None for l in leases)


def test_r5_legacy_released_admission_never_releases_or_pins_owner_key_lease(tmp_path):
    """R5 RED (legacy-upgrade identity construction): a legacy no-v2 replay
    whose exact-dispatch admission is already RELEASED cannot attribute the
    still-active owner-key lease — it may be a successor/foreign row. The
    replay must retain the lease, return typed recovery, and never pin that
    lease into new promotion evidence."""
    factory = FakeRunnerFactory()
    plan, authorities, route, task = _bridge(tmp_path, runner_factory=factory)
    seeded = _seed_completed(authorities, plan, "exec-legacy-unattr")
    # legacy promotion evidence (plain prefix, no identity payload)
    authorities.execution_store.set_execution_state(
        "exec-legacy-unattr", ExecutionProcessState.SUCCEEDED,
        expected_version=seeded.version,
        evidence_ref="zra2-review-verification:exec-legacy-unattr",
    )
    # original resources: lease still ACTIVE, admission already RELEASED
    lease = authorities.lease_broker.acquire(
        task.lease_request, task.candidates).lease
    admission = authorities.provider_store.acquire_admission(
        provider_id="zcode-glm", execution_id=route.dispatch_execution_id,
        batch_id=plan.batch_id, expected_max_concurrency=2, now=NOW,
        ttl_seconds=600, expected_configuration_generation=1,
    ).admission
    authorities.provider_store.release_admission(
        admission.admission_id, provider_id="zcode-glm",
        execution_id=route.dispatch_execution_id, batch_id=plan.batch_id,
        now=NOW,
    )
    result = _af_dispatch(authorities, route, task, FakeRunnerFactory())
    assert result.outcome == "RECOVERY_REQUIRED"
    assert result.reason_code == "LEASE_OWNERSHIP_UNPROVEN"
    assert result.handoff is None
    # the unattributable owner-key lease was retained, never released
    row = authorities.lease_store.inspect_health(lease.lease_id, now=NOW)
    assert row.lease.released_at is None
    # and no v2 promotion identity was minted over it (evidence stays legacy)
    from a_conductor.zero_relay_review_verification import (
        resolve_promotion_resource_identity,
    )
    assert resolve_promotion_resource_identity(
        authorities.execution_store, "exec-legacy-unattr") is None


def _active_lease_row(authorities):
    """The single unreleased lease row (owner-key invariant), for tests."""
    import sqlite3
    from types import SimpleNamespace
    conn = sqlite3.connect(str(authorities.lease_db))
    try:
        rows = conn.execute(
            "SELECT lease_id, released_at FROM worker_leases "
            "WHERE released_at IS NULL").fetchall()
    finally:
        conn.close()
    assert len(rows) == 1
    return SimpleNamespace(lease_id=rows[0][0], released_at=rows[0][1])


def test_r5_prior_dispatch_never_releases_successor_owner_key_lease(tmp_path):
    """R5 RED (successor lease): a prior dispatch whose own no-record
    attempt was already fully cleaned (its admission row is RELEASED) must
    never release a successor dispatch's fresh owner-key lease through the
    no-record recovery cleanup; the successor alone cleans its resources."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    crash = FakeRunnerFactory(fail_before_record=True)
    plan_a, authorities, route_a, task_a = _bridge(tmp_path, runner_factory=crash)
    first = _af_dispatch(authorities, route_a, task_a, crash)
    assert first.outcome == "NOT_ATTEMPTED_CLEANED"
    # the prior dispatch's own crash cleanup released its exact resources
    prior_admission = _admission_by_execution(
        authorities, route_a.dispatch_execution_id)
    assert prior_admission.status == "RELEASED"
    assert _all_leases(authorities) and all(
        l.released_at is not None for l in _all_leases(authorities))

    factory = FakeRunnerFactory()
    route_b, task_b = _identity_variant(tmp_path, plan_a, graph_run_id="run-2")
    entered, proceed = Event(), Event()

    def paused_factory(**kwargs):
        entered.set()  # successor owns a FRESH lease+admission, no record
        assert proceed.wait(10), "probe barrier timed out"
        return factory(**kwargs)

    with ThreadPoolExecutor(max_workers=1) as pool:
        successor = pool.submit(_af_dispatch, authorities, route_b, task_b,
                                paused_factory)
        try:
            assert entered.wait(10)
            successor_lease = _active_lease_row(authorities)
            # the PRIOR dispatch's retry must not release the successor's
            # fresh owner-key lease (prior admission row is RELEASED)
            prior_retry = _af_dispatch(authorities, route_a, task_a,
                                       FakeRunnerFactory())
            assert prior_retry.outcome == "RECOVERY_REQUIRED"
            row = authorities.lease_store.inspect_health(
                successor_lease.lease_id, now=NOW)
            assert row.lease.released_at is None
        finally:
            proceed.set()
        successor_result = successor.result(timeout=60)
    assert successor_result.outcome == "EXECUTED"
    assert factory.model_effects == 1
    # the successor alone performed its terminal cleanup
    leases = _all_leases(authorities)
    assert leases and all(l.released_at is not None for l in leases)
    admissions = _all_admissions(authorities)
    assert admissions and all(a.status == "RELEASED" for a in admissions)


# ── WO-P1-223 R6 repair (2026-09-15, Issue #214 comment 5684979092): an
# owner-key lease lookup plus an ACTIVE exact-dispatch admission is NOT
# exact lease provenance after the canonical stale-lease authority released
# the original row and a successor reacquired the same owner keys — only an
# exact lease id bound to this dispatch may authorize lease release or
# promotion pinning ────────────────────────────────────────────────────────


def _stale_release_lease(authorities, lease, *, tmp_path):
    """Canonical stale-lease reconcile through the REAL store authority:
    safely releases the expired unreleased lease row WITHOUT touching any
    provider admission — the exact R6 counterexample seam."""
    from a_conductor.domain import RecoveryClassification
    from a_conductor.worker_lease import WorkerLeaseRecoveryObservation

    result = authorities.lease_store.reconcile_stale(
        lease.lease_id,
        session_id=lease.session_id,
        task_id=lease.task_id,
        observation=WorkerLeaseRecoveryObservation(
            worker_id=lease.worker_id,
            worktree=str(tmp_path),
            branch=lease.branch,
            head=lease.expected_head,
            dirty_state="CLEAN",
            ownership_known=True,
            runtime_running=False,
            recovery_classification=RecoveryClassification.COMPLETE_VERIFIED,
            evidence_ref="test:r6-canonical-stale-release",
            observed_at=NOW + timedelta(hours=1),
        ),
    )
    assert result.lease.released_at is not None
    return result


def test_r6_terminal_cleanup_retains_successor_lease_after_stale_release(tmp_path):
    """R6 RED (terminal-unusable cleanup path): A owns L1+AdmA; the
    canonical lease reconcile_stale safely releases L1 while AdmA remains
    persisted ACTIVE; B acquires a fresh L2 under the same owner keys and is
    live. A's terminal-unusable replay must NEVER release L2 — owner-key +
    ACTIVE admission is not lease provenance. The exact-dispatch admission
    reconciles independently; L2 is retained; no second model effect."""
    factory = FakeRunnerFactory(live_timeout=True)
    plan_a, authorities, route_a, task_a = _bridge(tmp_path, runner_factory=factory)
    first = _af_dispatch(authorities, route_a, task_a, factory)
    assert first.outcome == "RECOVERY_REQUIRED" and first.handoff is None
    original = authorities.lease_store.inspect_health(
        _active_lease_row(authorities).lease_id, now=NOW).lease
    # the retained live record later becomes terminal FAILED (unusable)
    authorities.execution_store.set_execution_state(
        factory.execution_ids[0], ExecutionProcessState.FAILED, expected_version=1,
    )
    # canonical authority releases L1; the exact-dispatch admission stays ACTIVE
    _stale_release_lease(authorities, original, tmp_path=tmp_path)
    admission_a = _admission_by_execution(authorities, route_a.dispatch_execution_id)
    assert admission_a is not None and admission_a.status == "ACTIVE"
    # successor B holds a fresh live lease under the SAME owner keys
    route_b, task_b = _identity_variant(tmp_path, plan_a, graph_run_id="run-2")
    successor = authorities.lease_broker.acquire(task_b.lease_request, task_b.candidates)
    assert successor.kind is LeaseOutcomeKind.LEASED
    assert successor.lease.lease_id != original.lease_id
    replay_factory = FakeRunnerFactory()
    replay = _af_dispatch(authorities, route_a, task_a, replay_factory)
    assert replay.outcome == "RECOVERY_REQUIRED"
    assert replay.reason_code == "EQUIVALENT_TERMINAL_NOT_USABLE"
    assert replay.handoff is None
    # R6: B's live lease L2 was NOT released by A's replay
    l2 = authorities.lease_store.inspect_health(
        successor.lease.lease_id, now=NOW).lease
    assert l2.released_at is None
    # the exact-dispatch admission reconciled independently (exact identity)
    admission_after = _admission_by_execution(
        authorities, route_a.dispatch_execution_id)
    assert admission_after.status == "RELEASED"
    assert replay_factory.model_effects == 0


def test_r6_legacy_replay_never_releases_or_pins_successor_lease(tmp_path):
    """R6 RED (legacy/no-v2 reconcile path): the same counterexample on the
    completed replay path — L1 stale-released (admission persists ACTIVE),
    successor L2 live under the same owner keys. A's replay must retain L2,
    must NOT mint it into a v2 promotion identity (no owner-key-inference
    upgrade), promote nothing, and return typed recovery with no handoff;
    the exact-dispatch admission reconciles independently."""
    from a_conductor.zero_relay_review_verification import (
        resolve_promotion_resource_identity,
    )

    factory = FakeRunnerFactory()
    plan_a, authorities, route_a, task_a = _bridge(tmp_path, runner_factory=factory)
    _seed_completed(authorities, plan_a, "exec-r6-legacy")
    lease_a = authorities.lease_broker.acquire(
        task_a.lease_request, task_a.candidates).lease
    admission_a = authorities.provider_store.acquire_admission(
        provider_id="zcode-glm", execution_id=route_a.dispatch_execution_id,
        batch_id=plan_a.batch_id, expected_max_concurrency=2, now=NOW,
        ttl_seconds=600, expected_configuration_generation=1,
    ).admission
    _stale_release_lease(authorities, lease_a, tmp_path=tmp_path)
    route_b, task_b = _identity_variant(tmp_path, plan_a, graph_run_id="run-2")
    successor = authorities.lease_broker.acquire(task_b.lease_request, task_b.candidates)
    assert successor.kind is LeaseOutcomeKind.LEASED
    assert successor.lease.lease_id != lease_a.lease_id
    replay_factory = FakeRunnerFactory()
    replay = _af_dispatch(authorities, route_a, task_a, replay_factory)
    assert replay.outcome == "RECOVERY_REQUIRED"
    assert replay.reason_code == "LEASE_OWNERSHIP_UNPROVEN"
    assert replay.handoff is None
    assert replay_factory.model_effects == 0
    # R6: B's live lease was neither released ...
    l2 = authorities.lease_store.inspect_health(
        successor.lease.lease_id, now=NOW).lease
    assert l2.released_at is None
    # ... nor pinned: no v2 promotion identity was minted from it
    assert resolve_promotion_resource_identity(
        authorities.execution_store, "exec-r6-legacy") is None
    # nothing was promoted: the record keeps its pre-replay durable truth
    record = authorities.execution_store.get("exec-r6-legacy")
    assert record.execution_state is ExecutionProcessState.VERIFICATION_REQUIRED
    # the exact-dispatch admission reconciled independently
    assert authorities.provider_store.get_admission(
        admission_a.admission_id).status == "RELEASED"


def test_r6_recovery_cleanup_requires_exact_lease_id(tmp_path):
    """R6 RED (exact-id seam): the no-record recovery cleanup releases the
    owner-key lease row ONLY through the same-process backend's exact
    acquired id — never by owner-key inference. Same-process exact-id
    cleanup still works; a pure replay (no id) and a mismatched id retain
    the lease row while the exact-dispatch admission reconciles
    independently."""
    from a_conductor.zero_relay_review_execution import (
        _cleanup_held_resources_without_record,
    )

    def _held(root_name):
        root = Path(str(tmp_path) + root_name)
        plan, authorities, route, task = _bridge(root)
        lease = authorities.lease_broker.acquire(
            task.lease_request, task.candidates).lease
        admission = authorities.provider_store.acquire_admission(
            provider_id="zcode-glm", execution_id=route.dispatch_execution_id,
            batch_id=plan.batch_id, expected_max_concurrency=2, now=NOW,
            ttl_seconds=600, expected_configuration_generation=1,
        ).admission
        return plan, authorities, task, lease, admission

    # phase A: pure replay (no durable exact lease id) retains the lease
    plan, authorities, task, lease, admission = _held("a")
    assert _cleanup_held_resources_without_record(
        plan=plan, route_task=task, provider_store=authorities.provider_store,
        lease_broker=authorities.lease_broker, lease_store=authorities.lease_store,
        expected_generation=1, max_concurrency=2, clock=lambda: NOW,
        exact_lease_id=None,
    ) is False
    assert authorities.lease_store.inspect_health(
        lease.lease_id, now=NOW).lease.released_at is None
    assert authorities.provider_store.get_admission(
        admission.admission_id).status == "RELEASED"

    # phase B: the same-process exact id authorizes the exact release
    plan_b, auth_b, task_b, lease_b, admission_b = _held("b")
    assert _cleanup_held_resources_without_record(
        plan=plan_b, route_task=task_b, provider_store=auth_b.provider_store,
        lease_broker=auth_b.lease_broker, lease_store=auth_b.lease_store,
        expected_generation=1, max_concurrency=2, clock=lambda: NOW,
        exact_lease_id=lease_b.lease_id,
    ) is True
    assert auth_b.lease_store.inspect_health(
        lease_b.lease_id, now=NOW).lease.released_at is not None
    assert auth_b.provider_store.get_admission(
        admission_b.admission_id).status == "RELEASED"

    # phase C: a mismatched exact id never releases the row found now
    plan_c, auth_c, task_c, lease_c, admission_c = _held("c")
    assert _cleanup_held_resources_without_record(
        plan=plan_c, route_task=task_c, provider_store=auth_c.provider_store,
        lease_broker=auth_c.lease_broker, lease_store=auth_c.lease_store,
        expected_generation=1, max_concurrency=2, clock=lambda: NOW,
        exact_lease_id="lease-not-acquired-by-this-dispatch",
    ) is False
    assert auth_c.lease_store.inspect_health(
        lease_c.lease_id, now=NOW).lease.released_at is None
    assert auth_c.provider_store.get_admission(
        admission_c.admission_id).status == "RELEASED"


# ── WO-P1-223 R6b repair (2026-09-15, Issue #214 Sol integration): the
# exact-dispatch admission reconciles independently even when no active
# owner-key lease row exists, and an admission whose exact id does NOT match
# the same-process locator is retained with settled=False — never released,
# never counted as cleaned ─────────────────────────────────────────────────


def test_r6b_legacy_replay_reconciles_admission_when_lease_row_gone(tmp_path):
    """R6b RED (Sol gap 1): legacy completed replay where the canonical
    stale-lease authority already released the original lease and NO
    successor reacquired the owner keys. The exact-dispatch ACTIVE admission
    must still reconcile (be released) independently before the typed
    LEASE_IDENTITY_UNPROVEN return: no handoff, no promotion, no model
    effect, ZERO new rows."""
    from a_conductor.zero_relay_review_verification import (
        resolve_promotion_resource_identity,
    )

    factory = FakeRunnerFactory()
    plan_a, authorities, route_a, task_a = _bridge(tmp_path, runner_factory=factory)
    _seed_completed(authorities, plan_a, "exec-r6b-nolease")
    lease_a = authorities.lease_broker.acquire(
        task_a.lease_request, task_a.candidates).lease
    admission_a = authorities.provider_store.acquire_admission(
        provider_id="zcode-glm", execution_id=route_a.dispatch_execution_id,
        batch_id=plan_a.batch_id, expected_max_concurrency=2, now=NOW,
        ttl_seconds=600, expected_configuration_generation=1,
    ).admission
    # canonical authority releases L1; the exact-dispatch admission stays
    # ACTIVE; NO successor reacquires the owner keys
    _stale_release_lease(authorities, lease_a, tmp_path=tmp_path)
    assert authorities.provider_store.get_admission(
        admission_a.admission_id).status == "ACTIVE"
    rows_before = len(_all_leases(authorities))
    replay_factory = FakeRunnerFactory()
    replay = _af_dispatch(authorities, route_a, task_a, replay_factory)
    assert replay.outcome == "RECOVERY_REQUIRED"
    assert replay.reason_code == "LEASE_IDENTITY_UNPROVEN"
    assert replay.handoff is None
    assert replay_factory.model_effects == 0
    # R6b: the exact-dispatch admission reconciled independently
    assert authorities.provider_store.get_admission(
        admission_a.admission_id).status == "RELEASED"
    # no new rows, no promotion, no identity minting
    assert len(_all_leases(authorities)) == rows_before
    assert resolve_promotion_resource_identity(
        authorities.execution_store, "exec-r6b-nolease") is None
    record = authorities.execution_store.get("exec-r6b-nolease")
    assert record.execution_state is ExecutionProcessState.VERIFICATION_REQUIRED


def test_r6b_recovery_cleanup_admission_locator_mismatch_stays_recovery(tmp_path):
    """R6b RED (Sol gap 2): `_cleanup_held_resources_without_record` with an
    ACTIVE admission and a NON-None mismatched exact_admission_id must NOT
    count settled=True: the admission is retained (never released by a
    locator mismatch) and the cleanup returns False/recovery. A matching
    locator still settles True; an exact-bound lease still releases its own
    row while the mismatched admission keeps the outcome recovery."""
    from a_conductor.zero_relay_review_execution import (
        _cleanup_held_resources_without_record,
    )

    def _held(root_name, *, with_lease: bool):
        root = Path(str(tmp_path) + root_name)
        plan, authorities, route, task = _bridge(root)
        lease = None
        if with_lease:
            lease = authorities.lease_broker.acquire(
                task.lease_request, task.candidates).lease
        admission = authorities.provider_store.acquire_admission(
            provider_id="zcode-glm", execution_id=route.dispatch_execution_id,
            batch_id=plan.batch_id, expected_max_concurrency=2, now=NOW,
            ttl_seconds=600, expected_configuration_generation=1,
        ).admission
        return plan, authorities, task, lease, admission

    # phase A: mismatched admission locator, no lease row -> NOT settled
    plan_a, auth_a, task_a, _, admission_a = _held("a", with_lease=False)
    assert _cleanup_held_resources_without_record(
        plan=plan_a, route_task=task_a, provider_store=auth_a.provider_store,
        lease_broker=auth_a.lease_broker, lease_store=auth_a.lease_store,
        expected_generation=1, max_concurrency=2, clock=lambda: NOW,
        exact_admission_id="admission-not-acquired-by-this-dispatch",
    ) is False
    assert auth_a.provider_store.get_admission(
        admission_a.admission_id).status == "ACTIVE"

    # phase B (control): the matching locator settles the cleanup
    plan_b, auth_b, task_b, _, admission_b = _held("b", with_lease=False)
    assert _cleanup_held_resources_without_record(
        plan=plan_b, route_task=task_b, provider_store=auth_b.provider_store,
        lease_broker=auth_b.lease_broker, lease_store=auth_b.lease_store,
        expected_generation=1, max_concurrency=2, clock=lambda: NOW,
        exact_admission_id=admission_b.admission_id,
    ) is True
    assert auth_b.provider_store.get_admission(
        admission_b.admission_id).status == "RELEASED"

    # phase C: exact-bound lease releases its own row, but the mismatched
    # admission locator retains the admission and keeps the result False
    plan_c, auth_c, task_c, lease_c, admission_c = _held("c", with_lease=True)
    assert _cleanup_held_resources_without_record(
        plan=plan_c, route_task=task_c, provider_store=auth_c.provider_store,
        lease_broker=auth_c.lease_broker, lease_store=auth_c.lease_store,
        expected_generation=1, max_concurrency=2, clock=lambda: NOW,
        exact_lease_id=lease_c.lease_id,
        exact_admission_id="admission-not-acquired-by-this-dispatch",
    ) is False
    assert auth_c.lease_store.inspect_health(
        lease_c.lease_id, now=NOW).lease.released_at is not None
    assert auth_c.provider_store.get_admission(
        admission_c.admission_id).status == "ACTIVE"


def test_r6b_legacy_replay_admission_locator_mismatch_retains_admission(tmp_path):
    """R6b RED (sibling audit, LEASE_OWNERSHIP_UNPROVEN branch): the same
    mismatch shape on the legacy reconcile path — a non-None
    exact_admission_id naming a DIFFERENT row must never release the ACTIVE
    exact-dispatch admission found now (it may be a foreign/successor
    attempt's). Typed recovery stands; the successor lease is retained."""
    factory = FakeRunnerFactory()
    plan_a, authorities, route_a, task_a = _bridge(tmp_path, runner_factory=factory)
    _seed_completed(authorities, plan_a, "exec-r6b-locator")
    lease_a = authorities.lease_broker.acquire(
        task_a.lease_request, task_a.candidates).lease
    admission_a = authorities.provider_store.acquire_admission(
        provider_id="zcode-glm", execution_id=route_a.dispatch_execution_id,
        batch_id=plan_a.batch_id, expected_max_concurrency=2, now=NOW,
        ttl_seconds=600, expected_configuration_generation=1,
    ).admission
    _stale_release_lease(authorities, lease_a, tmp_path=tmp_path)
    route_b, task_b = _identity_variant(tmp_path, plan_a, graph_run_id="run-2")
    successor = authorities.lease_broker.acquire(task_b.lease_request, task_b.candidates)
    assert successor.kind is LeaseOutcomeKind.LEASED
    replay = reconcile_review_execution(
        plan=plan_a, route_task=task_a,
        provider_store=authorities.provider_store,
        lease_broker=authorities.lease_broker,
        lease_store=authorities.lease_store,
        execution_store=authorities.execution_store,
        clock=lambda: NOW, max_concurrency=2, expected_generation=1,
        exact_lease_id="lease-not-acquired-by-this-dispatch",
        exact_admission_id="admission-not-acquired-by-this-dispatch",
    )
    assert replay.outcome == "RECOVERY_REQUIRED"
    assert replay.reason_code == "LEASE_OWNERSHIP_UNPROVEN"
    assert replay.handoff is None
    # R6b: the mismatched locator retained the ACTIVE admission ...
    assert authorities.provider_store.get_admission(
        admission_a.admission_id).status == "ACTIVE"
    # ... and the successor lease row is still live
    l2 = authorities.lease_store.inspect_health(
        successor.lease.lease_id, now=NOW).lease
    assert l2.released_at is None
