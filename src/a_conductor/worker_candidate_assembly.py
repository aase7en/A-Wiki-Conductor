"""Production worker-supply assembly for scheduler and lease preflight.

This module owns no worker registry, scheduler, lease lifecycle, process probe,
or Git mutation. It converts already-authoritative durable and live evidence
into the existing ``WorkerSnapshot`` and ``WorkerLeaseCandidate`` models.
Unknown or malformed evidence becomes a fail-closed per-worker record so one
bad worker never erases evidence for healthy siblings.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping, Protocol, Sequence

from .claude_code_harness import HarnessDispatch, TaskPacketFile
from .control_center import ControlCenterSnapshot, WorkerScreenRow
from .domain import WorkerState
from .graph.dispatch import (
    DispatchGateDecision,
    GraphDispatchKey,
    GraphDispatchMode,
    GraphDispatchRequest,
)
from .graph.scheduler import SchedulePlan, WorkerSnapshot
from .lifecycle import LifecycleAction, LifecycleContext
from .native_adapters import NativeGitReadAdapter
from .parallel_ready_execution import ParallelReadyTask
from .native_execution import NativeExecutionError, NativeExecutionScope
from .project_identity import GitReadOnlyRunner, StrictReadOnlyGitRunner
from .provider_configuration import ProviderConfiguration, ProviderObservation
from .registry import windows_worktree_key
from .runtime_safety import PortBindingState, ProcessOwnership, TunnelBindingState
from .serena_runtime import SerenaProjectBinding
from .worker_lease import (
    WorkerLease,
    WorkerLeaseCandidate,
    WorkerLeaseRequest,
    WorkerProvisioningReservationRecord,
)


class WorkerCandidateAssemblyError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _text(value: str, field_name: str, *, max_length: int = 512) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    cleaned = value.strip()
    if len(cleaned) > max_length or any(ch in cleaned for ch in "\x00\r\n"):
        raise ValueError(f"{field_name} is invalid")
    return cleaned


@dataclass(frozen=True, slots=True)
class GitWorktreeState:
    branch: str
    head: str
    dirty_state: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "branch", _text(self.branch, "branch", max_length=256))
        head = _text(self.head, "head", max_length=64).lower()
        if len(head) < 7 or any(ch not in "0123456789abcdef" for ch in head):
            raise ValueError("head must be a git object id")
        object.__setattr__(self, "head", head)
        dirty = _text(self.dirty_state, "dirty_state", max_length=16).upper()
        if dirty not in {"CLEAN", "DIRTY", "UNKNOWN"}:
            raise ValueError("dirty_state is invalid")
        object.__setattr__(self, "dirty_state", dirty)


@dataclass(frozen=True, slots=True)
class WorkerSupplyRecord:
    worker_id: str
    scheduler: WorkerSnapshot
    candidate: WorkerLeaseCandidate
    reason_code: str

    def __post_init__(self) -> None:
        _text(self.worker_id, "worker_id", max_length=128)
        _text(self.reason_code, "reason_code", max_length=128)
        if self.scheduler.worker_id != self.worker_id:
            raise ValueError("scheduler worker identity mismatch")
        if self.candidate.worker_id != self.worker_id:
            raise ValueError("candidate worker identity mismatch")


class ControlCenterPort(Protocol):
    def snapshot(self) -> ControlCenterSnapshot: ...


class ProjectBindingPort(Protocol):
    def get_project_binding(self, project_id: str) -> SerenaProjectBinding | None: ...


class LifecycleObservationPort(Protocol):
    def observe(self, worker_id: str, action: LifecycleAction) -> LifecycleContext: ...


class GitWorktreeStatePort(Protocol):
    def observe(self, worktree: str) -> GitWorktreeState: ...


class LeaseEvidencePort(Protocol):
    def list_active(self) -> tuple[WorkerLease, ...]: ...

    def list_provisioning_reservations(
        self, *, consuming_only: bool = False
    ) -> tuple[WorkerProvisioningReservationRecord, ...]: ...


class RuntimeCapabilityPort(Protocol):
    def resolve(self, runtime_id: str | None) -> tuple[str, ...]: ...


class MappingRuntimeCapabilityResolver:
    """Read-only capability mapping supplied by the existing runtime catalog/config."""

    def __init__(self, values: Mapping[str, Sequence[str]]) -> None:
        self._values = {
            _text(runtime_id, "runtime_id", max_length=128): tuple(
                _text(item, "capability", max_length=128) for item in capabilities
            )
            for runtime_id, capabilities in values.items()
        }

    def resolve(self, runtime_id: str | None) -> tuple[str, ...]:
        if runtime_id is None:
            return ()
        return self._values.get(runtime_id, ())


class NativeGitWorktreeStateObserver:
    """Reuse the accepted fixed-shape Git readers; never runs arbitrary Git."""

    def __init__(
        self,
        *,
        git_executable: str = "git",
        identity_runner: GitReadOnlyRunner | None = None,
    ) -> None:
        self._git_executable = _text(git_executable, "git_executable", max_length=260)
        self._identity = identity_runner or StrictReadOnlyGitRunner(
            git_executable=self._git_executable
        )

    def observe(self, worktree: str) -> GitWorktreeState:
        try:
            root = Path(worktree).expanduser().resolve(strict=False)
        except OSError as exc:
            raise WorkerCandidateAssemblyError("GIT_WORKTREE_INVALID") from exc
        branch = self._identity.branch(root)
        head = self._identity.head(root)
        if not branch.success or not head.success:
            raise WorkerCandidateAssemblyError("GIT_IDENTITY_UNAVAILABLE")
        try:
            scope = NativeExecutionScope(
                root=root,
                mutation_allowed=False,
                allowed_executables=(self._git_executable,),
                max_timeout_seconds=30,
            )
            status = NativeGitReadAdapter(
                scope,
                git_executable=self._git_executable,
            ).status_short(timeout_seconds=10)
        except NativeExecutionError as exc:
            raise WorkerCandidateAssemblyError("GIT_STATUS_UNAVAILABLE") from exc
        if status.timed_out or status.exit_code != 0:
            raise WorkerCandidateAssemblyError("GIT_STATUS_UNAVAILABLE")
        return GitWorktreeState(
            branch=branch.stdout,
            head=head.stdout,
            dirty_state="DIRTY" if status.stdout.strip() else "CLEAN",
        )


def _runtime_ready(context: LifecycleContext, row: WorkerScreenRow) -> bool:
    if row.state is not WorkerState.READY or context.worker_state is not row.state:
        return False
    if context.assignment_present is not True or context.project_exists is not True:
        return False
    if context.process_ownership is not ProcessOwnership.OWNED:
        return False
    if context.port_binding is not PortBindingState.OWNED or context.ready is not True:
        return False
    if context.project_identity_ok is not True:
        return False
    if context.tunnel_required and context.tunnel_binding is not TunnelBindingState.OWNED:
        return False
    return True


def _observation_known(context: LifecycleContext) -> bool:
    return (
        context.process_ownership is not ProcessOwnership.UNKNOWN
        and context.port_binding is not PortBindingState.UNKNOWN
        and context.ready is not None
        and context.project_identity_ok is not None
    )


class WorkerCandidateAssembler:
    def __init__(
        self,
        *,
        control_center: ControlCenterPort,
        config_store: ProjectBindingPort,
        lifecycle_context_provider: LifecycleObservationPort,
        git_state_observer: GitWorktreeStatePort,
        lease_store: LeaseEvidencePort,
        capability_resolver: RuntimeCapabilityPort,
    ) -> None:
        self._control_center = control_center
        self._config_store = config_store
        self._lifecycle = lifecycle_context_provider
        self._git = git_state_observer
        self._leases = lease_store
        self._capabilities = capability_resolver

    def _snapshot(self) -> ControlCenterSnapshot:
        snapshot = self._control_center.snapshot()
        if not isinstance(snapshot, ControlCenterSnapshot):
            raise WorkerCandidateAssemblyError("CONTROL_CENTER_SNAPSHOT_INVALID")
        return snapshot

    def _active_leases(self) -> tuple[WorkerLease, ...]:
        active = self._leases.list_active()
        if not isinstance(active, tuple) or not all(
            isinstance(item, WorkerLease) for item in active
        ):
            raise WorkerCandidateAssemblyError("LEASE_EVIDENCE_INVALID")
        return active

    def _provisioning_reservations(
        self,
    ) -> tuple[WorkerProvisioningReservationRecord, ...]:
        reservations = self._leases.list_provisioning_reservations(
            consuming_only=True
        )
        if not isinstance(reservations, tuple) or not all(
            isinstance(item, WorkerProvisioningReservationRecord)
            for item in reservations
        ):
            raise WorkerCandidateAssemblyError(
                "PROVISIONING_RESERVATION_EVIDENCE_INVALID"
            )
        return reservations

    @staticmethod
    def _find_row(
        snapshot: ControlCenterSnapshot,
        worker_id: str,
    ) -> WorkerScreenRow:
        value = _text(worker_id, "worker_id", max_length=128)
        for row in snapshot.workers:
            if row.worker_id == value:
                return row
        raise WorkerCandidateAssemblyError("WORKER_NOT_FOUND")

    @staticmethod
    def _capacity_evidence(
        worker_id: str,
        worktree: str | None,
        active: tuple[WorkerLease, ...],
        reservations: tuple[WorkerProvisioningReservationRecord, ...],
        *,
        owner_session_id: str | None = None,
        owner_task_id: str | None = None,
    ) -> tuple[bool, tuple[tuple[str, ...], ...]]:
        reserved = any(item.worker_id == worker_id for item in active)
        scopes: list[tuple[str, ...]] = []
        key = None if worktree is None else windows_worktree_key(worktree)
        if key is not None:
            for item in active:
                if item.worktree_key == key and item.mutable_scope:
                    scopes.append(item.mutable_scope)

        for reservation in reservations:
            if reservation.state not in {"PROVISIONED", "RECOVERY_REQUIRED"}:
                continue
            owner_match = (
                reservation.state == "PROVISIONED"
                and owner_session_id is not None
                and owner_task_id is not None
                and reservation.session_id == owner_session_id
                and reservation.task_id == owner_task_id
            )
            if owner_match:
                continue
            if reservation.worker_id == worker_id:
                reserved = True
            if (
                key is not None
                and reservation.worktree_key == key
                and reservation.mutable_scope
            ):
                scopes.append(reservation.mutable_scope)
        return reserved, tuple(scopes)

    def _closed(
        self,
        row: WorkerScreenRow,
        reason_code: str,
        *,
        worktree: str | None = None,
        reserved: bool = False,
        scopes: tuple[tuple[str, ...], ...] = (),
    ) -> WorkerSupplyRecord:
        workspace = worktree or row.project_root_path
        scheduler = WorkerSnapshot(
            worker_id=row.worker_id,
            state="UNKNOWN",
            capabilities=(),
            reserved=reserved,
            project=row.project_id,
            workspace=workspace,
            mutation_authorized=False,
        )
        candidate = WorkerLeaseCandidate(
            worker_id=row.worker_id,
            state="UNKNOWN",
            reserved=reserved,
            active_task=reserved,
            capabilities=(),
            runtime_id=row.runtime_id,
            project_id=row.project_id,
            worktree=workspace,
            branch=None,
            head=None,
            health_fresh=False,
            ownership_known=False,
            dirty_state="UNKNOWN",
            mutation_authorized=False,
            occupied_mutable_scopes=scopes,
        )
        return WorkerSupplyRecord(
            row.worker_id,
            scheduler,
            candidate,
            reason_code,
        )

    def _assemble_row(
        self,
        row: WorkerScreenRow,
        active: tuple[WorkerLease, ...],
        reservations: tuple[WorkerProvisioningReservationRecord, ...],
        *,
        owner_session_id: str | None = None,
        owner_task_id: str | None = None,
    ) -> WorkerSupplyRecord:
        if (
            row.assignment_id is None
            or row.project_id is None
            or row.project_root_path is None
        ):
            reserved, scopes = self._capacity_evidence(
                row.worker_id,
                row.project_root_path,
                active,
                reservations,
                owner_session_id=owner_session_id,
                owner_task_id=owner_task_id,
            )
            return self._closed(
                row,
                "ASSIGNMENT_MISSING",
                reserved=reserved,
                scopes=scopes,
            )

        binding = self._config_store.get_project_binding(row.project_id)
        if not isinstance(binding, SerenaProjectBinding):
            reserved, scopes = self._capacity_evidence(
                row.worker_id,
                row.project_root_path,
                active,
                reservations,
                owner_session_id=owner_session_id,
                owner_task_id=owner_task_id,
            )
            return self._closed(
                row,
                "PROJECT_BINDING_MISSING",
                reserved=reserved,
                scopes=scopes,
            )
        if windows_worktree_key(binding.worktree_path) != windows_worktree_key(
            row.project_root_path
        ):
            reserved, scopes = self._capacity_evidence(
                row.worker_id,
                binding.worktree_path,
                active,
                reservations,
                owner_session_id=owner_session_id,
                owner_task_id=owner_task_id,
            )
            return self._closed(
                row,
                "PROJECT_BINDING_DRIFT",
                worktree=binding.worktree_path,
                reserved=reserved,
                scopes=scopes,
            )

        reserved_by_lease, scopes = self._capacity_evidence(
            row.worker_id,
            binding.worktree_path,
            active,
            reservations,
            owner_session_id=owner_session_id,
            owner_task_id=owner_task_id,
        )
        try:
            capabilities = tuple(self._capabilities.resolve(row.runtime_id))
        except Exception:
            return self._closed(
                row,
                "CAPABILITY_EVIDENCE_FAILED",
                worktree=binding.worktree_path,
                reserved=reserved_by_lease,
                scopes=scopes,
            )
        if not capabilities or not all(
            isinstance(item, str) and item.strip() for item in capabilities
        ):
            return self._closed(
                row,
                "CAPABILITY_EVIDENCE_MISSING",
                worktree=binding.worktree_path,
                reserved=reserved_by_lease,
                scopes=scopes,
            )

        try:
            context = self._lifecycle.observe(
                row.worker_id,
                LifecycleAction.START,
            )
        except Exception:
            return self._closed(
                row,
                "LIFECYCLE_OBSERVATION_FAILED",
                worktree=binding.worktree_path,
                reserved=reserved_by_lease,
                scopes=scopes,
            )
        if not isinstance(context, LifecycleContext) or context.action is not LifecycleAction.START:
            return self._closed(
                row,
                "LIFECYCLE_OBSERVATION_INVALID",
                worktree=binding.worktree_path,
                reserved=reserved_by_lease,
                scopes=scopes,
            )
        if not _observation_known(context):
            return self._closed(
                row,
                "RUNTIME_OBSERVATION_UNKNOWN",
                worktree=binding.worktree_path,
                reserved=reserved_by_lease or bool(context.active_task),
                scopes=scopes,
            )

        try:
            git = self._git.observe(binding.worktree_path)
        except Exception:
            return self._closed(
                row,
                "GIT_OBSERVATION_FAILED",
                worktree=binding.worktree_path,
                reserved=reserved_by_lease or bool(context.active_task),
                scopes=scopes,
            )
        if not isinstance(git, GitWorktreeState):
            return self._closed(
                row,
                "GIT_OBSERVATION_INVALID",
                worktree=binding.worktree_path,
                reserved=reserved_by_lease or bool(context.active_task),
                scopes=scopes,
            )

        state = "READY" if _runtime_ready(context, row) else "UNKNOWN"
        has_active_task = reserved_by_lease or bool(context.active_task)
        durable_mutation_allowed = bool(row.mutation_allowed) and bool(
            binding.mutation_allowed
        )
        mutation_allowed = (
            durable_mutation_allowed
            and git.dirty_state == "CLEAN"
            and state == "READY"
            and not has_active_task
        )
        scheduler = WorkerSnapshot(
            worker_id=row.worker_id,
            state=state,
            capabilities=capabilities,
            reserved=has_active_task,
            project=row.project_id,
            workspace=binding.worktree_path,
            mutation_authorized=mutation_allowed,
        )
        candidate = WorkerLeaseCandidate(
            worker_id=row.worker_id,
            state=state,
            reserved=has_active_task,
            active_task=has_active_task,
            capabilities=capabilities,
            runtime_id=row.runtime_id,
            project_id=row.project_id,
            worktree=binding.worktree_path,
            branch=git.branch,
            head=git.head,
            health_fresh=True,
            ownership_known=(
                context.process_ownership is not ProcessOwnership.UNKNOWN
            ),
            dirty_state=git.dirty_state,
            mutation_authorized=durable_mutation_allowed,
            occupied_mutable_scopes=scopes,
        )
        reason = (
            "READY_DIRTY"
            if state == "READY" and git.dirty_state == "DIRTY"
            else "READY"
            if state == "READY"
            else "WORKER_NOT_READY"
        )
        return WorkerSupplyRecord(
            row.worker_id,
            scheduler,
            candidate,
            reason,
        )

    def _evidence_snapshot(
        self,
    ) -> tuple[tuple[WorkerLease, ...], tuple[WorkerProvisioningReservationRecord, ...]]:
        return self._active_leases(), self._provisioning_reservations()

    def assemble(self, worker_id: str) -> WorkerSupplyRecord:
        snapshot = self._snapshot()
        active, reservations = self._evidence_snapshot()
        row = self._find_row(snapshot, worker_id)
        return self._assemble_row(row, active, reservations)

    def assemble_for_owner(
        self,
        worker_id: str,
        *,
        session_id: str,
        task_id: str,
    ) -> WorkerSupplyRecord:
        session_id = _text(session_id, "session_id", max_length=128)
        task_id = _text(task_id, "task_id", max_length=256)
        snapshot = self._snapshot()
        active, reservations = self._evidence_snapshot()
        row = self._find_row(snapshot, worker_id)
        return self._assemble_row(
            row,
            active,
            reservations,
            owner_session_id=session_id,
            owner_task_id=task_id,
        )

    def _assemble_all(
        self,
        *,
        owner_session_id: str | None = None,
        owner_task_id: str | None = None,
    ) -> tuple[WorkerSupplyRecord, ...]:
        snapshot = self._snapshot()
        try:
            active, reservations = self._evidence_snapshot()
        except Exception:
            return tuple(
                self._closed(row, "CAPACITY_EVIDENCE_INVALID")
                for row in snapshot.workers
            )

        records: list[WorkerSupplyRecord] = []
        for row in snapshot.workers:
            try:
                records.append(
                    self._assemble_row(
                        row,
                        active,
                        reservations,
                        owner_session_id=owner_session_id,
                        owner_task_id=owner_task_id,
                    )
                )
            except WorkerCandidateAssemblyError:
                records.append(self._closed(row, "ASSEMBLY_RECOVERY_REQUIRED"))
            except Exception:
                records.append(self._closed(row, "ASSEMBLY_EXCEPTION"))
        return tuple(records)

    def assemble_all(self) -> tuple[WorkerSupplyRecord, ...]:
        return self._assemble_all()

    def assemble_all_for_owner(
        self, *, session_id: str, task_id: str
    ) -> tuple[WorkerSupplyRecord, ...]:
        return self._assemble_all(
            owner_session_id=_text(session_id, "session_id", max_length=128),
            owner_task_id=_text(task_id, "task_id", max_length=256),
        )


@dataclass(frozen=True, slots=True)
class WorkerSupplySnapshot:
    """One production scheduling/lease evidence snapshot."""

    scheduler_workers: tuple[WorkerSnapshot, ...]
    lease_candidates: tuple[WorkerLeaseCandidate, ...]

    def __post_init__(self) -> None:
        schedulers = tuple(self.scheduler_workers)
        candidates = tuple(self.lease_candidates)
        if not all(isinstance(item, WorkerSnapshot) for item in schedulers):
            raise ValueError("scheduler_workers must contain WorkerSnapshot values")
        if not all(isinstance(item, WorkerLeaseCandidate) for item in candidates):
            raise ValueError("lease_candidates must contain WorkerLeaseCandidate values")
        scheduler_ids = tuple(item.worker_id for item in schedulers)
        candidate_ids = tuple(item.worker_id for item in candidates)
        if len(set(scheduler_ids)) != len(scheduler_ids):
            raise ValueError("scheduler worker IDs must be unique")
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("lease candidate worker IDs must be unique")
        object.__setattr__(self, "scheduler_workers", schedulers)
        object.__setattr__(self, "lease_candidates", candidates)

    @classmethod
    def from_records(cls, records: Sequence[WorkerSupplyRecord]) -> "WorkerSupplySnapshot":
        values = tuple(records)
        if not all(isinstance(item, WorkerSupplyRecord) for item in values):
            raise ValueError("records must contain WorkerSupplyRecord values")
        return cls(
            scheduler_workers=tuple(item.scheduler for item in values),
            lease_candidates=tuple(item.candidate for item in values),
        )


@dataclass(frozen=True, slots=True)
class ParallelReadyNodeContract:
    """Worker-neutral durable inputs needed to materialize one selected task."""

    dispatch_key: GraphDispatchKey
    project_id: str
    work_order_ref: str
    operation_ref: str
    dispatch_gate: DispatchGateDecision
    lease_request: WorkerLeaseRequest
    provider_profile: ProviderConfiguration
    provider_observation: ProviderObservation | None
    harness_dispatch: HarnessDispatch
    task_packet: TaskPacketFile
    require_quota: bool = False
    max_attempts: int = 3

    def __post_init__(self) -> None:
        if not isinstance(self.dispatch_key, GraphDispatchKey):
            raise ValueError("dispatch_key must be GraphDispatchKey")
        object.__setattr__(self, "project_id", _text(self.project_id, "project_id"))
        object.__setattr__(self, "work_order_ref", _text(self.work_order_ref, "work_order_ref"))
        object.__setattr__(self, "operation_ref", _text(self.operation_ref, "operation_ref"))
        if not isinstance(self.dispatch_gate, DispatchGateDecision):
            raise ValueError("dispatch_gate must be DispatchGateDecision")
        if not isinstance(self.lease_request, WorkerLeaseRequest):
            raise ValueError("lease_request must be WorkerLeaseRequest")
        if not isinstance(self.provider_profile, ProviderConfiguration):
            raise ValueError("provider_profile must be ProviderConfiguration")
        if self.provider_observation is not None and not isinstance(
            self.provider_observation, ProviderObservation
        ):
            raise ValueError("provider_observation must be ProviderObservation or None")
        if not isinstance(self.harness_dispatch, HarnessDispatch):
            raise ValueError("harness_dispatch must be HarnessDispatch")
        if not isinstance(self.task_packet, TaskPacketFile):
            raise ValueError("task_packet must be TaskPacketFile")
        if not isinstance(self.require_quota, bool):
            raise ValueError("require_quota must be bool")
        if isinstance(self.max_attempts, bool) or not isinstance(self.max_attempts, int) or self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.lease_request.project_id != self.project_id:
            raise ValueError("lease project identity mismatch")
        if self.harness_dispatch.project_id != self.project_id:
            raise ValueError("harness project identity mismatch")
        if self.harness_dispatch.task_contract_ref != self.work_order_ref:
            raise ValueError("harness work-order identity mismatch")
        if self.task_packet.task_contract_ref != self.work_order_ref:
            raise ValueError("task packet contract mismatch")


def assemble_parallel_ready_tasks(
    plan: SchedulePlan,
    contracts_by_node: Mapping[str, ParallelReadyNodeContract],
    supply: WorkerSupplySnapshot,
) -> dict[str, ParallelReadyTask]:
    """Bind scheduler selections to exactly one freshly observed lease candidate."""
    if not isinstance(plan, SchedulePlan):
        raise ValueError("plan must be SchedulePlan")
    if not isinstance(contracts_by_node, Mapping):
        raise ValueError("contracts_by_node must be a mapping")
    if not isinstance(supply, WorkerSupplySnapshot):
        raise ValueError("supply must be WorkerSupplySnapshot")
    selected_ids = tuple(item.node_id for item in plan.selected)
    if len(set(selected_ids)) != len(selected_ids):
        raise ValueError("selected node IDs must be unique")
    if set(contracts_by_node) != set(selected_ids):
        raise ValueError("selected contract mapping mismatch")
    candidates = {item.worker_id: item for item in supply.lease_candidates}

    tasks: dict[str, ParallelReadyTask] = {}
    for assignment in plan.selected:
        contract = contracts_by_node[assignment.node_id]
        if not isinstance(contract, ParallelReadyNodeContract):
            raise ValueError("contract mapping values must be ParallelReadyNodeContract")
        if contract.dispatch_key.node_id != assignment.node_id:
            raise ValueError("dispatch key node does not match selected assignment")
        candidate = candidates.get(assignment.worker_id)
        if candidate is None:
            raise ValueError("selected worker missing from fresh worker supply")
        request = contract.lease_request
        if candidate.project_id != request.project_id:
            raise ValueError("selected worker project identity mismatch")
        if candidate.worktree is None or windows_worktree_key(candidate.worktree) != windows_worktree_key(request.worktree):
            raise ValueError("selected worker worktree identity mismatch")
        if candidate.branch != request.branch:
            raise ValueError("selected worker branch identity mismatch")
        if candidate.head is None or candidate.head.casefold() != request.expected_head.casefold():
            raise ValueError("selected worker head identity mismatch")
        lease_request = replace(
            request,
            ordered_worker_ids=(assignment.worker_id,),
            required_runtime_id=candidate.runtime_id,
        )
        dispatch_request = GraphDispatchRequest(
            key=contract.dispatch_key,
            assignment=assignment,
            project_id=contract.project_id,
            work_order_ref=contract.work_order_ref,
            operation_ref=contract.operation_ref,
            dispatch_mode=GraphDispatchMode.PROGRAMMATIC_PUSH,
            max_attempts=contract.max_attempts,
        )
        tasks[assignment.node_id] = ParallelReadyTask(
            assignment=assignment,
            dispatch_request=dispatch_request,
            dispatch_gate=contract.dispatch_gate,
            lease_request=lease_request,
            candidates=(candidate,),
            provider_profile=contract.provider_profile,
            provider_observation=contract.provider_observation,
            harness_dispatch=contract.harness_dispatch,
            task_packet=contract.task_packet,
            require_quota=contract.require_quota,
        )
    return tasks
