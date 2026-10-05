"""Bounded manual runtime activation policy for WO-P1-433.

This module owns no scheduler, persistence, continuation, retry, or worker
provisioning authority.  It narrows an already-authoritative graph/run to one
explicit READY node and delegates execution to the accepted production stack.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Callable, Mapping, Protocol

from .claude_code_harness import HarnessDispatch, MutationIntent, TaskPacketFile
from .claude_code_job_backend import ClaudeCodeOperationDefinition
from .elastic_worker_capacity import (
    ElasticCapacityPolicy,
    ElasticWorkerCapacityCoordinator,
    ProductionElasticWorkerExecutor,
    SQLiteWorkerProvisioningReservations,
)
from .graph.dispatch import (
    DispatchGateDecision,
    GraphDispatchCoordinator,
    GraphDispatchError,
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
from .execution_store import SQLiteExecutionStore
from .job_control import DurableJobControlService
from .job_execution import DurableJobExecutionCoordinator
from .owned_process import WindowsOwnedProcessController
from .parallel_ready_execution import GraphDispatchParallelRunner, ParallelReadyExecutor
from .job_store import JobStoreError, SQLiteJobStore
from .provider_config_store import ProviderConfigurationSnapshot
from .provider_configuration import HarnessStrategy
from .provider_execution_authority import ProviderExecutionRequirement
from .provider_runtime_assembly import build_sqlite_supervised_claude_job_backend
from .supervised_execution import SupervisedExecutionService
from .windows_io import LoopbackReadyzHttpProbe, StrictPowerShellInspectionRunner
from .windows_observer import WindowsRuntimeObserver
from .worker_candidate_assembly import (
    MappingRuntimeCapabilityResolver,
    NativeGitWorktreeStateObserver,
    ParallelReadyNodeContract,
    WorkerCandidateAssembler,
)
from .worker_lease import (
    LeaseMutationIntent,
    SQLiteWorkerLeaseStore,
    WorkerLeaseBroker,
    WorkerLeaseRequest,
)


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


def _offer_interactive_runtime(
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

    try:
        return coordinator.dispatch(dispatch_request, gate=gate)
    except (GraphDispatchError, JobStoreError) as exc:
        raise RuntimeActivationError(
            getattr(exc, "code", None) or "INTERACTIVE_PULL_DISPATCH_FAILED"
        ) from exc


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
        expected_authority_sha256=authority.task_contract_sha256,
    )

    if authority.mutation_allowed and not authority.allowed_files:
        raise RuntimeActivationError("ACTIVATION_MUTABLE_SCOPE_REQUIRED")
    if authority.mutation_allowed:
        raise RuntimeActivationError("PROGRAMMATIC_MUTATION_BACKEND_UNAVAILABLE")
    lease_intent = LeaseMutationIntent.READ_ONLY
    harness_intent = MutationIntent.READ_ONLY
    mutable_scope: tuple[str, ...] = ()
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
        # READ_ONLY RUNTIME-ACT-1 deliberately keeps the accepted Claude
        # backend's optional quota gate off. Provider generation, admission,
        # policy and readiness remain enforced by their existing authorities.
        require_quota=False,
        max_attempts=authority.max_attempts,
        provider_requirement=requirement,
    )


def _require_programmatic_push_platform(
    *, platform_name: str | None = None
) -> None:
    """Fail closed where the accepted owned-process supervisor is unavailable.

    The current production supervised Claude assembly is backed by the accepted
    Windows ownership/PowerShell observer stack.  Exposing the CLI on another
    host must not imply that PROGRAMMATIC_PUSH can launch there.
    """
    resolved = os.name if platform_name is None else platform_name
    if resolved != "nt":
        raise RuntimeActivationError("PROGRAMMATIC_PUSH_PLATFORM_UNSUPPORTED")


class _AuthorizedWorkerSupplyAssembler:
    """Restrict existing observed supply to task-authorized push workers."""

    def __init__(self, base: WorkerCandidateAssembler, worker_ids: tuple[str, ...]) -> None:
        if not isinstance(base, WorkerCandidateAssembler):
            raise ValueError("base must be WorkerCandidateAssembler")
        if not worker_ids:
            raise ValueError("worker_ids must not be empty")
        self._base = base
        self._worker_ids = tuple(worker_ids)

    @property
    def lease_evidence_database_path(self):
        return self._base.lease_evidence_database_path

    def _filter(self, records):
        by_id = {item.worker_id: item for item in records}
        return tuple(by_id[item] for item in self._worker_ids if item in by_id)

    def assemble_all(self):
        return self._filter(self._base.assemble_all())

    def assemble_all_for_owner(self, *, session_id: str, task_id: str):
        return self._filter(
            self._base.assemble_all_for_owner(
                session_id=session_id,
                task_id=task_id,
            )
        )

    def assemble(self, worker_id: str):
        if worker_id not in self._worker_ids:
            raise RuntimeActivationError("WORKER_NOT_AUTHORIZED_FOR_PUSH")
        return self._base.assemble(worker_id)

    def assemble_for_owner(
        self,
        worker_id: str,
        *,
        session_id: str,
        task_id: str,
    ):
        if worker_id not in self._worker_ids:
            raise RuntimeActivationError("WORKER_NOT_AUTHORIZED_FOR_PUSH")
        return self._base.assemble_for_owner(
            worker_id,
            session_id=session_id,
            task_id=task_id,
        )


class _NoElasticProvisioner:
    def provision(self, *args, **kwargs):
        raise AssertionError("elastic provisioning is disabled for WO-P1-433")


class _SelectedWorkerClaudeBackend:
    """Bind the scheduler-selected worker into the accepted Claude job backend."""

    def __init__(
        self,
        *,
        database_path: Path,
        contract: ParallelReadyNodeContract,
        execution_store: SQLiteExecutionStore,
        clock: Callable[[], object],
    ) -> None:
        self._database_path = database_path
        self._contract = contract
        self._execution_store = execution_store
        self._clock = clock

    def execute(self, operation_ref, context):
        from .job_execution import JobExecutionContext

        if not isinstance(context, JobExecutionContext):
            raise ValueError("context must be JobExecutionContext")
        if operation_ref != self._contract.operation_ref:
            raise ValueError("RUNTIME_ACTIVATION_OPERATION_MISMATCH")
        if context.worker_id not in self._contract.lease_request.ordered_worker_ids:
            raise ValueError("RUNTIME_ACTIVATION_WORKER_MISMATCH")

        definition = ClaudeCodeOperationDefinition(
            operation_ref=self._contract.operation_ref,
            dispatch=self._contract.harness_dispatch,
            packet=self._contract.task_packet,
            worker_id=context.worker_id,
            provider_security=self._contract.provider_security,
            expected_configuration_generation=(
                self._contract.expected_configuration_generation
            ),
            require_quota=self._contract.require_quota,
            provider_requirement=self._contract.provider_requirement,
        )
        observer = WindowsRuntimeObserver(
            runner=StrictPowerShellInspectionRunner(),
            http_probe=LoopbackReadyzHttpProbe(),
        )
        controller = WindowsOwnedProcessController(observer=observer)
        supervised = SupervisedExecutionService(
            store=self._execution_store,
            controller=controller,
            observer=observer,
            allowed_target_executables=("claude",),
            python_executable=sys.executable,
        )
        backend = build_sqlite_supervised_claude_job_backend(
            database_path=self._database_path,
            operations=(definition,),
            execution_store=self._execution_store,
            supervised=supervised,
            clock=self._clock,
        )
        return backend.execute(operation_ref, context)


def _build_runtime_job_backend(
    *,
    database_path: Path,
    contract: ParallelReadyNodeContract,
    execution_store: SQLiteExecutionStore,
    clock: Callable[[], object],
):
    return _SelectedWorkerClaudeBackend(
        database_path=database_path,
        contract=contract,
        execution_store=execution_store,
        clock=clock,
    )


def _require_canonical_runtime_dependencies(
    database_path: str | Path,
    *,
    settings_store,
    provider_store,
) -> Path:
    canonical = Path(database_path).expanduser().resolve(strict=False)
    for source, code in (
        (settings_store, "SETTINGS_AUTHORITY_UNAVAILABLE"),
        (provider_store, "PROVIDER_AUTHORITY_UNAVAILABLE"),
    ):
        raw = getattr(source, "database_path", None)
        if raw is None:
            raise RuntimeActivationError(code)
        observed = Path(raw).expanduser().resolve(strict=False)
        if observed != canonical:
            raise RuntimeActivationError("AUTHORITY_DATABASE_IDENTITY_MISMATCH")
    return canonical


def _programmatic_worker_binding(
    control_center,
    authority: RuntimeActivationAuthority,
) -> tuple[tuple[str, ...], dict[str, tuple[str, ...]]]:
    """Bind exact authorized workers and their current runtime IDs from one snapshot."""
    snapshot = control_center.snapshot()
    by_id = {row.worker_id: row for row in snapshot.workers}
    root = Path(authority.worktree).expanduser().resolve(strict=False)
    accepted: list[str] = []
    runtime_capabilities: dict[str, tuple[str, ...]] = {}
    for worker_id in authority.worker_ids:
        row = by_id.get(worker_id)
        if (
            row is None
            or row.assignment_id is None
            or row.project_id != authority.project_id
            or row.project_root_path is None
            or row.runtime_id is None
        ):
            raise RuntimeActivationError("PROGRAMMATIC_PUSH_WORKER_UNAVAILABLE")
        try:
            worker_root = Path(row.project_root_path).expanduser().resolve(
                strict=False
            )
        except OSError as exc:
            raise RuntimeActivationError(
                "PROGRAMMATIC_PUSH_WORKER_PROJECT_MISMATCH"
            ) from exc
        if worker_root != root:
            raise RuntimeActivationError(
                "PROGRAMMATIC_PUSH_WORKER_PROJECT_MISMATCH"
            )
        accepted.append(worker_id)
        # This marker proves only that the already-authorized worker has an
        # observed Serena runtime. It is NOT task capability authority:
        # non-empty TaskNode capability demand is rejected before this binding.
        runtime_capabilities[row.runtime_id] = ("runtime:serena",)
    if tuple(accepted) != authority.worker_ids:
        raise RuntimeActivationError("WORKER_CANDIDATE_AUTHORITY_MISMATCH")
    return tuple(accepted), runtime_capabilities


def _provider_inflight_count(provider_store, snapshot, now: object) -> int:
    if not hasattr(now, "tzinfo") or getattr(now, "tzinfo", None) is None:
        raise RuntimeActivationError("ACTIVATION_CLOCK_INVALID")
    generation = snapshot.generation
    if isinstance(generation, bool) or not isinstance(generation, int):
        raise RuntimeActivationError("PROVIDER_GENERATION_AUTHORITY_MISSING")
    try:
        records = provider_store.list_provider_admissions(
            provider_id=snapshot.profile.provider_id,
            limit=200,
        )
    except Exception as exc:
        raise RuntimeActivationError(
            "PROVIDER_INFLIGHT_EVIDENCE_UNAVAILABLE"
        ) from exc
    # The accepted owner exposes a bounded recent-list API. A full page means
    # older active evidence may exist outside the observation window, so fail
    # closed at scheduler capacity rather than under-counting.
    if len(records) >= 200:
        return snapshot.profile.max_concurrency
    count = 0
    for record in records:
        if (
            record.status == "ACTIVE"
            and record.released_at is None
            and record.configuration_generation == generation
            and record.expires_at > now
        ):
            count += 1
    return count


_RUNTIME_AUTHORITY_INITIALIZATION_LOCK = Lock()


def _initialize_runtime_authority_stores(
    database_path: Path,
    *,
    provider_store,
    provider_id: str,
):
    """Serialize same-process schema assembly without creating new authority."""

    with _RUNTIME_AUTHORITY_INITIALIZATION_LOCK:
        return _initialize_runtime_authority_stores_unlocked(
            database_path,
            provider_store=provider_store,
            provider_id=provider_id,
        )


def _initialize_runtime_authority_stores_unlocked(
    database_path: Path,
    *,
    provider_store,
    provider_id: str,
):
    """Initialize existing owning schemas, then prove each is readable.

    Partial initialization is intentionally surfaced as RECOVERY_REQUIRED.
    This helper never launches a backend and never retries a failed external
    side effect; the DDL owners themselves are idempotent CREATE-IF-NOT-EXISTS
    stores so a reconciled operator can re-open the same sacrificial database.
    """
    try:
        job_store = SQLiteJobStore(database_path)
        job_store.initialize()
        try:
            job_store.get_job("runtime-activation-schema-probe")
        except Exception as exc:
            if getattr(exc, "code", None) != "JOB_NOT_FOUND":
                raise
        else:
            raise RuntimeActivationError("JOB_SCHEMA_VERIFICATION_FAILED")

        execution_store = SQLiteExecutionStore(database_path)
        execution_store.initialize()
        try:
            execution_store.get("runtime-activation-schema-probe")
        except Exception as exc:
            if getattr(exc, "code", None) != "EXECUTION_NOT_FOUND":
                raise
        else:
            raise RuntimeActivationError("EXECUTION_SCHEMA_VERIFICATION_FAILED")

        lease_store = SQLiteWorkerLeaseStore(database_path)
        lease_store.list_active()
        provider_store.list_provider_admissions(
            provider_id=provider_id,
            limit=1,
        )
    except RuntimeActivationError:
        raise
    except Exception as exc:
        raise RuntimeActivationError(
            "RUNTIME_AUTHORITY_INITIALIZATION_RECOVERY_REQUIRED"
        ) from exc

    return job_store, execution_store, lease_store


def activate_production_runtime(
    *,
    database_path: str | Path,
    request: RuntimeActivationRequest,
    control_center,
    settings_store,
    provider_store,
    lifecycle,
    clock: Callable[[], object],
):
    """Activate one explicit task over existing durable production authorities."""
    canonical = _require_canonical_runtime_dependencies(
        database_path,
        settings_store=settings_store,
        provider_store=provider_store,
    )
    if not callable(clock):
        raise ValueError("clock must be callable")
    authority = load_activation_authority(request)
    if authority.dispatch_mode == GraphDispatchMode.INTERACTIVE_PULL.value:
        return _offer_interactive_runtime(
            database_path=canonical,
            request=request,
            control_center=control_center,
        )
    if authority.dispatch_mode != GraphDispatchMode.PROGRAMMATIC_PUSH.value:
        raise RuntimeActivationError("DISPATCH_MODE_INVALID")
    _require_programmatic_push_platform()

    # Validate all read-side authorities before initializing write-capable
    # runtime stores.
    try:
        graph = GraphStore.open_read_only(canonical).load_graph(request.graph_id)
    except Exception as exc:
        raise RuntimeActivationError("ACTIVATION_GRAPH_UNAVAILABLE") from exc
    node = next((item for item in graph.nodes() if item.id == request.node_id), None)
    if node is None:
        raise RuntimeActivationError("ACTIVATION_NODE_NOT_FOUND")
    if node.worker_requirement:
        raise RuntimeActivationError("RUNTIME_CAPABILITY_AUTHORITY_UNAVAILABLE")

    worker_ids, runtime_capabilities = _programmatic_worker_binding(
        control_center,
        authority,
    )
    snapshot = provider_store.load_provider_snapshot(request.provider_id)
    if snapshot is None:
        raise RuntimeActivationError("PROVIDER_SNAPSHOT_UNAVAILABLE")
    contract = build_activation_contract(
        request,
        node,
        database_path=canonical,
        provider_snapshot=snapshot,
        ordered_worker_ids=worker_ids,
    )
    now = clock()
    provider_inflight = {
        snapshot.profile.provider_id: _provider_inflight_count(
            provider_store,
            snapshot,
            now,
        )
    }

    # Explicit activation is the owner boundary at which existing runtime
    # schemas may be initialized in the canonical database.  The helper also
    # performs bounded post-initialization read-back before any backend exists.
    job_store, execution_store, lease_store = _initialize_runtime_authority_stores(
        canonical,
        provider_store=provider_store,
        provider_id=snapshot.profile.provider_id,
    )

    candidate_base = WorkerCandidateAssembler(
        control_center=control_center,
        config_store=settings_store,
        lifecycle_context_provider=lifecycle,
        git_state_observer=NativeGitWorktreeStateObserver(),
        lease_store=lease_store,
        capability_resolver=MappingRuntimeCapabilityResolver(
            runtime_capabilities
        ),
    )
    candidate_assembler = _AuthorizedWorkerSupplyAssembler(
        candidate_base,
        worker_ids,
    )
    broker = WorkerLeaseBroker(
        store=lease_store,
        lease_id_factory=lambda: f"runtime-lease-{uuid.uuid4().hex}",
        clock=clock,
    )
    reservations = SQLiteWorkerProvisioningReservations(lease_store)
    capacity = ElasticWorkerCapacityCoordinator(
        broker=broker,
        reservations=reservations,
        provisioner=_NoElasticProvisioner(),
        candidate_assembler=candidate_assembler,
        reservation_id_factory=lambda: f"runtime-reservation-{uuid.uuid4().hex}",
        clock=clock,
    )

    backend = _build_runtime_job_backend(
        database_path=canonical,
        contract=contract,
        execution_store=execution_store,
        clock=clock,
    )
    durable = DurableJobControlService(
        store=job_store,
        coordinator=DurableJobExecutionCoordinator(
            store=job_store,
            backend=backend,
        ),
    )
    coordinator = GraphDispatchCoordinator(
        service=durable,
        mode_resolver=StaticWorkerDispatchModeResolver(
            {
                worker_id: GraphDispatchMode.PROGRAMMATIC_PUSH
                for worker_id in worker_ids
            }
        ),
    )
    runner = GraphDispatchParallelRunner(coordinator)
    parallel = ParallelReadyExecutor(
        broker=broker,
        runner=runner,
        clock=clock,
        provider_admission_store=provider_store,
        require_provider_authority=True,
        lease_health_reader=lease_store,
        require_pre_dispatch_guard=True,
    )
    executor = ProductionElasticWorkerExecutor(
        candidate_assembler=candidate_assembler,
        capacity_coordinator=capacity,
        parallel_executor=parallel,
    )

    service = RuntimeActivationService(
        graph_loader=lambda graph_id: graph,
        state_projector=lambda current_graph, graph_id, graph_run_id: (
            project_graph_node_states(
                current_graph,
                graph_id,
                graph_run_id,
                job_store,
            )
        ),
        contract_builder=lambda current_request, current_node: contract,
        executor=executor,
        provider_inflight=provider_inflight,
    )
    return service.activate(request)


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
