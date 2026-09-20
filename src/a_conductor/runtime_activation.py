"""Bounded manual runtime activation policy for WO-P1-433.

This module owns no scheduler, persistence, continuation, retry, or worker
provisioning authority.  It narrows an already-authoritative graph/run to one
explicit READY node and delegates execution to the accepted production stack.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Protocol

from .claude_code_harness import HarnessDispatch, MutationIntent, TaskPacketFile
from .elastic_worker_capacity import ElasticCapacityPolicy
from .graph.dispatch import (
    DispatchGateDecision,
    GraphDispatchCoordinator,
    GraphDispatchKey,
    GraphDispatchMode,
    GraphDispatchRequest,
    StaticWorkerDispatchModeResolver,
)
from .graph.domain import TaskGraph, TaskNode, TaskNodeStatus
from .graph.lifecycle_bridge import project_graph_node_states
from .graph.ready import ReadySetResult, compute_ready_set
from .graph.store import GraphStore
from .graph.scheduler import NodeEligibility, SchedulePolicy, SelectedAssignment
from .job_control import DurableJobControlService
from .job_execution import DurableJobExecutionCoordinator
from .job_store import JobStoreError, SQLiteJobStore
from .provider_config_store import ProviderConfigurationSnapshot
from .provider_configuration import HarnessStrategy
from .provider_execution_authority import ProviderExecutionRequirement
from .worker_candidate_assembly import ParallelReadyNodeContract
from .worker_lease import LeaseMutationIntent, WorkerLeaseRequest


class RuntimeActivationError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = _safe_text(code, "code")
        super().__init__(self.code)


def _safe_text(value: str, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or any(char in value for char in "\x00\r\n")
    ):
        raise ValueError(f"{field} is invalid")
    return value.strip()


@dataclass(frozen=True, slots=True)
class RuntimeActivationRequest:
    graph_id: str
    graph_run_id: str
    node_id: str
    runtime_kind: str
    project_root: str
    task_contract_ref: str
    task_packet_path: str
    provider_id: str
    model_id: str
    effort_level: str = "MAX"

    def __post_init__(self) -> None:
        object.__setattr__(self, "graph_id", _safe_text(self.graph_id, "graph_id"))
        object.__setattr__(
            self,
            "graph_run_id",
            _safe_text(self.graph_run_id, "graph_run_id"),
        )
        object.__setattr__(self, "node_id", _safe_text(self.node_id, "node_id"))
        object.__setattr__(
            self,
            "runtime_kind",
            _safe_text(self.runtime_kind, "runtime_kind"),
        )
        for field in (
            "project_root",
            "task_contract_ref",
            "task_packet_path",
            "provider_id",
            "model_id",
            "effort_level",
        ):
            object.__setattr__(
                self,
                field,
                _safe_text(getattr(self, field), field),
            )


@dataclass(frozen=True, slots=True)
class RuntimeActivationAuthority:
    task_id: str
    project_id: str
    worktree: str
    branch: str
    head: str
    mutation_allowed: bool
    allowed_files: tuple[str, ...]
    forbidden_files: tuple[str, ...]
    max_attempts: int
    timeout_seconds: int
    dispatch_mode: str
    worker_id: str | None
    worker_ids: tuple[str, ...]
    task_contract_sha256: str
    task_packet: TaskPacketFile


_HEAD_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")


def _mapping(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise RuntimeActivationError(f"ACTIVATION_{field.upper()}_INVALID")
    return value


def _text_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise RuntimeActivationError(f"ACTIVATION_{field.upper()}_INVALID")
    return tuple(item.strip() for item in value)


def _project_file(root: Path, value: str, field: str) -> Path:
    rel = Path(_safe_text(value, field))
    if rel.is_absolute():
        raise RuntimeActivationError(f"ACTIVATION_{field.upper()}_INVALID")
    path = (root / rel).resolve(strict=False)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise RuntimeActivationError(f"ACTIVATION_{field.upper()}_ESCAPES_PROJECT") from exc
    return path


def load_activation_authority(
    request: RuntimeActivationRequest,
) -> RuntimeActivationAuthority:
    """Consume existing task-contract and packet authority without creating state."""
    if not isinstance(request, RuntimeActivationRequest):
        raise ValueError("request must be RuntimeActivationRequest")
    try:
        root = Path(request.project_root).expanduser().resolve(strict=True)
    except OSError as exc:
        raise RuntimeActivationError("ACTIVATION_PROJECT_ROOT_UNAVAILABLE") from exc
    if not root.is_dir():
        raise RuntimeActivationError("ACTIVATION_PROJECT_ROOT_UNAVAILABLE")

    contract_path = _project_file(
        root,
        request.task_contract_ref,
        "task_contract_ref",
    )
    try:
        raw = contract_path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeActivationError("ACTIVATION_TASK_CONTRACT_INVALID") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0.0":
        raise RuntimeActivationError("ACTIVATION_TASK_CONTRACT_INVALID")

    try:
        task_id = _safe_text(payload.get("task_id"), "task_id")
        target = _mapping(payload.get("target"), "target")
        authority = _mapping(payload.get("authority"), "authority")
        scope = _mapping(payload.get("scope"), "scope")
        budget = _mapping(payload.get("budget"), "budget")
        retry = _mapping(payload.get("retry_policy"), "retry_policy")
        metadata = _mapping(payload.get("metadata"), "metadata")
        project_id = _safe_text(target.get("project_id"), "project_id")
        identity_policy = _safe_text(target.get("identity_policy"), "identity_policy")
        expected_worktree = _safe_text(
            target.get("expected_worktree_path"),
            "expected_worktree_path",
        )
        branch = _safe_text(target.get("expected_branch"), "expected_branch")
        head = _safe_text(target.get("expected_head"), "expected_head")
    except (TypeError, ValueError) as exc:
        raise RuntimeActivationError("ACTIVATION_TASK_CONTRACT_INVALID") from exc

    if identity_policy != "EXACT":
        raise RuntimeActivationError("ACTIVATION_EXACT_IDENTITY_REQUIRED")
    if not _HEAD_RE.fullmatch(head):
        raise RuntimeActivationError("ACTIVATION_HEAD_IDENTITY_INVALID")
    try:
        expected_root = Path(expected_worktree).expanduser().resolve(strict=False)
    except OSError as exc:
        raise RuntimeActivationError("ACTIVATION_WORKTREE_IDENTITY_INVALID") from exc
    if expected_root != root:
        raise RuntimeActivationError("ACTIVATION_WORKTREE_IDENTITY_MISMATCH")

    human_approval_required = authority.get("human_approval_required")
    mutation_allowed = authority.get("mutation_allowed")
    if not isinstance(human_approval_required, bool) or not isinstance(
        mutation_allowed, bool
    ):
        raise RuntimeActivationError("ACTIVATION_AUTHORITY_INVALID")
    if human_approval_required:
        raise RuntimeActivationError("HUMAN_APPROVAL_REQUIRED")

    try:
        dispatch_mode = GraphDispatchMode(
            _safe_text(metadata.get("dispatch_mode"), "dispatch_mode")
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeActivationError("DISPATCH_MODE_INVALID") from exc
    raw_worker_id = metadata.get("worker_id")
    try:
        worker_id = (
            None
            if raw_worker_id is None
            else _safe_text(raw_worker_id, "worker_id")
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeActivationError("INTERACTIVE_PULL_WORKER_INVALID") from exc
    if dispatch_mode is GraphDispatchMode.INTERACTIVE_PULL and worker_id is None:
        raise RuntimeActivationError("INTERACTIVE_PULL_WORKER_REQUIRED")
    raw_worker_ids = metadata.get("worker_ids")
    if dispatch_mode is GraphDispatchMode.PROGRAMMATIC_PUSH:
        try:
            worker_ids = _text_tuple(raw_worker_ids, "worker_ids")
        except RuntimeActivationError as exc:
            raise RuntimeActivationError("PROGRAMMATIC_PUSH_WORKERS_REQUIRED") from exc
        if not worker_ids or len(set(worker_ids)) != len(worker_ids):
            raise RuntimeActivationError("PROGRAMMATIC_PUSH_WORKERS_REQUIRED")
    else:
        worker_ids = ()

    allowed_files = _text_tuple(scope.get("allowed_files"), "allowed_files")
    forbidden_files = _text_tuple(scope.get("forbidden_files"), "forbidden_files")
    timeout_seconds = budget.get("max_elapsed_seconds")
    max_attempts = retry.get("max_attempts")
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, int)
        or not 1 <= timeout_seconds <= 14400
    ):
        raise RuntimeActivationError("ACTIVATION_TIMEOUT_INVALID")
    if (
        isinstance(max_attempts, bool)
        or not isinstance(max_attempts, int)
        or max_attempts < 1
    ):
        raise RuntimeActivationError("ACTIVATION_MAX_ATTEMPTS_INVALID")

    try:
        packet_path = Path(request.task_packet_path).expanduser().resolve(strict=True)
        packet_path.relative_to(root)
    except (OSError, ValueError) as exc:
        raise RuntimeActivationError("ACTIVATION_TASK_PACKET_INVALID") from exc
    if not packet_path.is_file():
        raise RuntimeActivationError("ACTIVATION_TASK_PACKET_INVALID")
    try:
        digest = hashlib.sha256(packet_path.read_bytes()).hexdigest()
        packet = TaskPacketFile(
            task_contract_ref=request.task_contract_ref,
            path=str(packet_path),
            sha256=digest,
        )
    except (OSError, ValueError) as exc:
        raise RuntimeActivationError("ACTIVATION_TASK_PACKET_INVALID") from exc

    return RuntimeActivationAuthority(
        task_id=task_id,
        project_id=project_id,
        worktree=str(root),
        branch=branch,
        head=head.lower(),
        mutation_allowed=mutation_allowed,
        allowed_files=allowed_files,
        forbidden_files=forbidden_files,
        max_attempts=max_attempts,
        timeout_seconds=timeout_seconds,
        dispatch_mode=dispatch_mode.value,
        worker_id=worker_id,
        worker_ids=worker_ids,
        task_contract_sha256=hashlib.sha256(raw).hexdigest(),
        task_packet=packet,
    )


class _OfferOnlyBackend:
    def execute(self, operation_ref, context):
        raise AssertionError("INTERACTIVE_PULL must never execute a backend")


def _pull_worker_row(control_center, authority: RuntimeActivationAuthority):
    snapshot = control_center.snapshot()
    worker_id = authority.worker_id
    if worker_id is None:
        raise RuntimeActivationError("INTERACTIVE_PULL_WORKER_REQUIRED")
    row = next(
        (item for item in snapshot.workers if item.worker_id == worker_id),
        None,
    )
    if row is None or row.assignment_id is None:
        raise RuntimeActivationError("INTERACTIVE_PULL_WORKER_UNAVAILABLE")
    if row.project_id != authority.project_id or row.project_root_path is None:
        raise RuntimeActivationError("INTERACTIVE_PULL_WORKER_PROJECT_MISMATCH")
    try:
        worker_root = Path(row.project_root_path).expanduser().resolve(strict=False)
        authority_root = Path(authority.worktree).expanduser().resolve(strict=False)
    except OSError as exc:
        raise RuntimeActivationError("INTERACTIVE_PULL_WORKER_PROJECT_MISMATCH") from exc
    if worker_root != authority_root:
        raise RuntimeActivationError("INTERACTIVE_PULL_WORKER_PROJECT_MISMATCH")
    if authority.mutation_allowed and row.mutation_allowed is not True:
        raise RuntimeActivationError("INTERACTIVE_PULL_MUTATION_UNAUTHORIZED")
    return row


def offer_interactive_runtime(
    *,
    database_path: str | Path,
    request: RuntimeActivationRequest,
    control_center,
):
    """Durably offer one exact pull-mode task without lease/provider/process launch."""
    authority = load_activation_authority(request)
    if authority.dispatch_mode != GraphDispatchMode.INTERACTIVE_PULL.value:
        raise RuntimeActivationError("INTERACTIVE_PULL_MODE_REQUIRED")
    row = _pull_worker_row(control_center, authority)

    try:
        graph = GraphStore.open_read_only(database_path).load_graph(request.graph_id)
    except Exception as exc:
        raise RuntimeActivationError("ACTIVATION_GRAPH_UNAVAILABLE") from exc
    node = next((item for item in graph.nodes() if item.id == request.node_id), None)
    if node is None:
        raise RuntimeActivationError("ACTIVATION_NODE_NOT_FOUND")
    if node.worker_requirement:
        raise RuntimeActivationError("RUNTIME_CAPABILITY_AUTHORITY_UNAVAILABLE")

    key = GraphDispatchKey(request.graph_id, request.graph_run_id, request.node_id)
    operation_ref = (
        "runtime-offer:"
        + hashlib.sha256(
            (
                authority.task_contract_sha256
                + chr(0)
                + key.job_id
            ).encode("utf-8")
        ).hexdigest()
    )
    dispatch_request = GraphDispatchRequest(
        key=key,
        assignment=SelectedAssignment(node.id, row.worker_id, node.priority),
        project_id=authority.project_id,
        work_order_ref=request.task_contract_ref,
        operation_ref=operation_ref,
        dispatch_mode=GraphDispatchMode.INTERACTIVE_PULL,
        max_attempts=authority.max_attempts,
    )
    gate = DispatchGateDecision.allow(
        evidence_ref=f"task-contract-sha256:{authority.task_contract_sha256}"
    )

    job_store = SQLiteJobStore(database_path)
    job_store.initialize()
    service = DurableJobControlService(
        store=job_store,
        coordinator=DurableJobExecutionCoordinator(
            store=job_store,
            backend=_OfferOnlyBackend(),
        ),
    )
    coordinator = GraphDispatchCoordinator(
        service=service,
        mode_resolver=StaticWorkerDispatchModeResolver(
            {row.worker_id: GraphDispatchMode.INTERACTIVE_PULL}
        ),
    )

    # A represented pull job is replay-safe: the coordinator verifies the
    # persisted metadata/worker binding and re-offers CLAIMED work without
    # executing the backend.
    try:
        existing = job_store.get_job(key.job_id)
    except JobStoreError as exc:
        if exc.code != "JOB_NOT_FOUND":
            raise
        states = project_graph_node_states(
            graph,
            request.graph_id,
            request.graph_run_id,
            job_store,
        )
        ready = compute_ready_set(graph, states)
        if request.node_id not in ready.ready_ids:
            raise RuntimeActivationError("ACTIVATION_NODE_NOT_READY")
    else:
        if (
            existing.work_order_ref != request.task_contract_ref
            or existing.project_id != authority.project_id
            or existing.worker_id not in {None, row.worker_id}
        ):
            raise RuntimeActivationError("ACTIVATION_JOB_IDENTITY_MISMATCH")

    return coordinator.dispatch(dispatch_request, gate=gate)


def build_activation_contract(
    request: RuntimeActivationRequest,
    node: TaskNode,
    *,
    database_path: str | Path,
    provider_snapshot: ProviderConfigurationSnapshot,
    ordered_worker_ids: tuple[str, ...],
) -> ParallelReadyNodeContract:
    """Derive one worker-neutral production contract from existing authorities."""
    if not isinstance(request, RuntimeActivationRequest):
        raise ValueError("request must be RuntimeActivationRequest")
    if not isinstance(node, TaskNode) or node.id != request.node_id:
        raise RuntimeActivationError("ACTIVATION_NODE_IDENTITY_MISMATCH")
    if not isinstance(provider_snapshot, ProviderConfigurationSnapshot):
        raise RuntimeActivationError("PROVIDER_SNAPSHOT_INVALID")
    if (
        not isinstance(ordered_worker_ids, tuple)
        or not ordered_worker_ids
        or not all(isinstance(item, str) and item.strip() for item in ordered_worker_ids)
        or len(set(ordered_worker_ids)) != len(ordered_worker_ids)
    ):
        raise RuntimeActivationError("WORKER_CANDIDATE_AUTHORITY_MISSING")

    authority = load_activation_authority(request)
    if authority.dispatch_mode != GraphDispatchMode.PROGRAMMATIC_PUSH.value:
        if authority.dispatch_mode == GraphDispatchMode.INTERACTIVE_PULL.value:
            raise RuntimeActivationError("INTERACTIVE_PULL_REQUIRES_OFFER_PATH")
        raise RuntimeActivationError("DISPATCH_MODE_INVALID")
    if tuple(item.strip() for item in ordered_worker_ids) != authority.worker_ids:
        raise RuntimeActivationError("WORKER_CANDIDATE_AUTHORITY_MISMATCH")
    profile = provider_snapshot.profile
    endpoint = provider_snapshot.endpoint
    generation = provider_snapshot.generation
    if profile.provider_id != request.provider_id:
        raise RuntimeActivationError("PROVIDER_IDENTITY_MISMATCH")
    if endpoint is None or endpoint.endpoint_ref != profile.endpoint_ref:
        raise RuntimeActivationError("PROVIDER_ENDPOINT_AUTHORITY_MISSING")
    if isinstance(generation, bool) or not isinstance(generation, int) or generation < 1:
        raise RuntimeActivationError("PROVIDER_GENERATION_AUTHORITY_MISSING")
    if HarnessStrategy.CLAUDE_CODE_CLI not in profile.harness_strategies:
        raise RuntimeActivationError("PROVIDER_HARNESS_NOT_AUTHORIZED")
    model = next(
        (item for item in profile.models if item.model_id == request.model_id),
        None,
    )
    if model is None:
        raise RuntimeActivationError("PROVIDER_MODEL_NOT_AUTHORIZED")
    if request.effort_level not in model.supported_effort_levels:
        raise RuntimeActivationError("PROVIDER_EFFORT_NOT_AUTHORIZED")

    key = GraphDispatchKey(
        request.graph_id,
        request.graph_run_id,
        request.node_id,
    )
    requirement = ProviderExecutionRequirement.from_task_contract_file(
        project_root=authority.worktree,
        provider_id=profile.provider_id,
        provider_authority_path=database_path,
        expected_configuration_generation=generation,
        task_contract_ref=request.task_contract_ref,
        base_operation_ref=f"runtime-activation:{key.job_id}",
    )

    if authority.mutation_allowed and not authority.allowed_files:
        raise RuntimeActivationError("ACTIVATION_MUTABLE_SCOPE_REQUIRED")
    lease_intent = (
        LeaseMutationIntent.MUTATION
        if authority.mutation_allowed
        else LeaseMutationIntent.READ_ONLY
    )
    harness_intent = (
        MutationIntent.PROJECT_MUTATION
        if authority.mutation_allowed
        else MutationIntent.READ_ONLY
    )
    mutable_scope = authority.allowed_files if authority.mutation_allowed else ()
    lease = WorkerLeaseRequest(
        session_id=key.job_id,
        task_id=authority.task_id,
        project_id=authority.project_id,
        ordered_worker_ids=tuple(item.strip() for item in ordered_worker_ids),
        required_capabilities=tuple(node.worker_requirement),
        required_runtime_id=None,
        worktree=authority.worktree,
        branch=authority.branch,
        expected_head=authority.head,
        mutation_intent=lease_intent,
        allowed_scope=authority.allowed_files,
        forbidden_scope=authority.forbidden_files,
        mutable_scope=mutable_scope,
        rdc_fallback_eligible=False,
        lease_ttl_seconds=authority.timeout_seconds + 60,
    )
    dispatch = HarnessDispatch(
        execution_id=key.job_id,
        task_contract_ref=request.task_contract_ref,
        project_id=authority.project_id,
        worktree_path=authority.worktree,
        expected_branch=authority.branch,
        expected_head=authority.head,
        provider_id=profile.provider_id,
        model_id=request.model_id,
        harness_strategy=HarnessStrategy.CLAUDE_CODE_CLI,
        mutation_intent=harness_intent,
        timeout_seconds=authority.timeout_seconds,
        max_output_bytes=100_000,
        effort_level=request.effort_level,
    )
    return ParallelReadyNodeContract(
        dispatch_key=key,
        project_id=authority.project_id,
        work_order_ref=request.task_contract_ref,
        operation_ref=requirement.operation_ref,
        dispatch_gate=DispatchGateDecision.allow(
            evidence_ref=f"task-contract-sha256:{requirement.authority_sha256}"
        ),
        lease_request=lease,
        provider_profile=profile,
        provider_observation=provider_snapshot.observation,
        provider_endpoint=endpoint,
        provider_security=requirement.provider_security,
        expected_configuration_generation=generation,
        harness_dispatch=dispatch,
        task_packet=authority.task_packet,
        require_quota=False,
        max_attempts=authority.max_attempts,
        provider_requirement=requirement,
    )


def derive_runtime_activation_batch_id(
    request: RuntimeActivationRequest,
) -> str:
    if not isinstance(request, RuntimeActivationRequest):
        raise ValueError("request must be RuntimeActivationRequest")
    material = b"runtime-activation-batch-v1\x00" + b"\x00".join(
        value.encode("utf-8")
        for value in (
            request.graph_id,
            request.graph_run_id,
            request.node_id,
            request.task_contract_ref,
        )
    )
    return "runtime-act-v1:" + hashlib.sha256(material).hexdigest()


class RuntimeActivationExecutor(Protocol):
    def execute_once(
        self,
        graph: TaskGraph,
        ready: ReadySetResult,
        contracts_by_node: Mapping[str, object],
        **kwargs,
    ) -> object: ...


GraphLoader = Callable[[str], TaskGraph]
StateProjector = Callable[[TaskGraph, str, str], Mapping[str, TaskNodeStatus]]
ContractBuilder = Callable[[RuntimeActivationRequest, TaskNode], object]


class RuntimeActivationService:
    """Execute one explicit READY node without selecting NEXT READY work."""

    def __init__(
        self,
        *,
        graph_loader: GraphLoader,
        state_projector: StateProjector,
        contract_builder: ContractBuilder,
        executor: RuntimeActivationExecutor,
        provider_inflight: Mapping[str, int] | None = None,
    ) -> None:
        if not callable(graph_loader):
            raise ValueError("graph_loader must be callable")
        if not callable(state_projector):
            raise ValueError("state_projector must be callable")
        if not callable(contract_builder):
            raise ValueError("contract_builder must be callable")
        if not callable(getattr(executor, "execute_once", None)):
            raise ValueError("executor must provide execute_once")
        self._graph_loader = graph_loader
        self._state_projector = state_projector
        self._contract_builder = contract_builder
        self._executor = executor
        self._provider_inflight = dict(provider_inflight or {})
        for provider_id, count in self._provider_inflight.items():
            _safe_text(provider_id, "provider_id")
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError("provider_inflight values must be non-negative integers")

    def _load_target(
        self,
        request: RuntimeActivationRequest,
    ) -> tuple[TaskGraph, TaskNode]:
        graph = self._graph_loader(request.graph_id)
        if not isinstance(graph, TaskGraph):
            raise RuntimeActivationError("ACTIVATION_GRAPH_INVALID")
        node = next(
            (item for item in graph.nodes() if item.id == request.node_id),
            None,
        )
        if node is None:
            raise RuntimeActivationError("ACTIVATION_NODE_NOT_FOUND")
        return graph, node

    def activate(self, request: RuntimeActivationRequest) -> object:
        if not isinstance(request, RuntimeActivationRequest):
            raise ValueError("request must be RuntimeActivationRequest")
        graph, node = self._load_target(request)

        # Current accepted main has no observed bridge from the canonical
        # TaskNode capability vocabulary to runtime supply.  Never satisfy
        # task demand by echoing it into worker capability evidence.
        if node.worker_requirement:
            raise RuntimeActivationError(
                "RUNTIME_CAPABILITY_AUTHORITY_UNAVAILABLE"
            )

        states = self._state_projector(
            graph,
            request.graph_id,
            request.graph_run_id,
        )
        if not isinstance(states, Mapping):
            raise RuntimeActivationError("ACTIVATION_STATE_EVIDENCE_INVALID")
        ready = compute_ready_set(graph, dict(states))
        check = ready.checks.get(request.node_id)
        if check is None or request.node_id not in ready.ready_ids:
            raise RuntimeActivationError("ACTIVATION_NODE_NOT_READY")

        # Focus the already-computed readiness evidence on the operator-named
        # node.  READY siblings are intentionally excluded: this is not ZRA-3.
        focused = ReadySetResult(
            checks={request.node_id: check},
            ready_ids={request.node_id},
        )
        contract = self._contract_builder(request, node)
        return self._executor.execute_once(
            graph,
            focused,
            {request.node_id: contract},
            schedule_policy=SchedulePolicy(max_parallel=1),
            provider_inflight=self._provider_inflight,
            runtime_kind=request.runtime_kind,
            elastic_policy=ElasticCapacityPolicy(
                enabled=False,
                max_extra_workers=0,
                permitted_runtime_kinds=(),
            ),
            eligibility={request.node_id: NodeEligibility()},
            batch_id=derive_runtime_activation_batch_id(request),
        )
