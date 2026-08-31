"""Production worker-supply assembly for scheduler and lease preflight.

This module owns no worker registry, scheduler, lease lifecycle, process probe,
or Git mutation. It converts already-authoritative durable and live evidence
into the existing ``WorkerSnapshot`` and ``WorkerLeaseCandidate`` models.
Unknown or malformed evidence becomes a fail-closed per-worker record so one
bad worker never erases evidence for healthy siblings.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol, Sequence

from .control_center import ControlCenterSnapshot, WorkerScreenRow
from .domain import WorkerState
from .graph.scheduler import WorkerSnapshot
from .lifecycle import LifecycleAction, LifecycleContext
from .native_adapters import NativeGitReadAdapter
from .native_execution import NativeExecutionError, NativeExecutionScope
from .project_identity import GitReadOnlyRunner, StrictReadOnlyGitRunner
from .registry import windows_worktree_key
from .runtime_safety import PortBindingState, ProcessOwnership, TunnelBindingState
from .serena_runtime import SerenaProjectBinding
from .worker_lease import WorkerLease, WorkerLeaseCandidate


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
        self._identity = identity_runner or StrictReadOnlyGitRunner(git_executable=self._git_executable)

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
                scope, git_executable=self._git_executable
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
    if row.state is not WorkerState.READY:
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

    def _row(self, worker_id: str) -> WorkerScreenRow:
        value = _text(worker_id, "worker_id", max_length=128)
        snapshot = self._control_center.snapshot()
        if not isinstance(snapshot, ControlCenterSnapshot):
            raise WorkerCandidateAssemblyError("CONTROL_CENTER_SNAPSHOT_INVALID")
        for row in snapshot.workers:
            if row.worker_id == value:
                return row
        raise WorkerCandidateAssemblyError("WORKER_NOT_FOUND")

    def _lease_evidence(
        self, worker_id: str, worktree: str | None
    ) -> tuple[bool, tuple[tuple[str, ...], ...]]:
        active = self._leases.list_active()
        if not isinstance(active, tuple) or not all(isinstance(item, WorkerLease) for item in active):
            raise WorkerCandidateAssemblyError("LEASE_EVIDENCE_INVALID")
        reserved = any(item.worker_id == worker_id for item in active)
        scopes: list[tuple[str, ...]] = []
        if worktree is not None:
            key = windows_worktree_key(worktree)
            for item in active:
                if item.worktree_key == key and item.mutable_scope:
                    scopes.append(item.mutable_scope)
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
        return WorkerSupplyRecord(row.worker_id, scheduler, candidate, reason_code)

    def assemble(self, worker_id: str) -> WorkerSupplyRecord:
        row = self._row(worker_id)
        if row.assignment_id is None or row.project_id is None or row.project_root_path is None:
            reserved, scopes = self._lease_evidence(row.worker_id, row.project_root_path)
            return self._closed(row, "ASSIGNMENT_MISSING", reserved=reserved, scopes=scopes)

        binding = self._config_store.get_project_binding(row.project_id)
        if not isinstance(binding, SerenaProjectBinding):
            reserved, scopes = self._lease_evidence(row.worker_id, row.project_root_path)
            return self._closed(row, "PROJECT_BINDING_MISSING", reserved=reserved, scopes=scopes)
        if windows_worktree_key(binding.worktree_path) != windows_worktree_key(row.project_root_path):
            reserved, scopes = self._lease_evidence(row.worker_id, binding.worktree_path)
            return self._closed(
                row,
                "PROJECT_BINDING_DRIFT",
                worktree=binding.worktree_path,
                reserved=reserved,
                scopes=scopes,
            )

        reserved, scopes = self._lease_evidence(row.worker_id, binding.worktree_path)
        try:
            capabilities = tuple(self._capabilities.resolve(row.runtime_id))
        except Exception:
            return self._closed(
                row,
                "CAPABILITY_EVIDENCE_FAILED",
                worktree=binding.worktree_path,
                reserved=reserved,
                scopes=scopes,
            )
        if not capabilities or not all(isinstance(item, str) and item.strip() for item in capabilities):
            return self._closed(
                row,
                "CAPABILITY_EVIDENCE_MISSING",
                worktree=binding.worktree_path,
                reserved=reserved,
                scopes=scopes,
            )

        try:
            context = self._lifecycle.observe(row.worker_id, LifecycleAction.START)
        except Exception:
            return self._closed(
                row,
                "LIFECYCLE_OBSERVATION_FAILED",
                worktree=binding.worktree_path,
                reserved=reserved,
                scopes=scopes,
            )
        if not isinstance(context, LifecycleContext) or context.action is not LifecycleAction.START:
            return self._closed(
                row,
                "LIFECYCLE_OBSERVATION_INVALID",
                worktree=binding.worktree_path,
                reserved=reserved,
                scopes=scopes,
            )
        if not _observation_known(context):
            return self._closed(
                row,
                "RUNTIME_OBSERVATION_UNKNOWN",
                worktree=binding.worktree_path,
                reserved=reserved,
                scopes=scopes,
            )

        try:
            git = self._git.observe(binding.worktree_path)
        except Exception:
            return self._closed(
                row,
                "GIT_OBSERVATION_FAILED",
                worktree=binding.worktree_path,
                reserved=reserved,
                scopes=scopes,
            )
        if not isinstance(git, GitWorktreeState):
            return self._closed(
                row,
                "GIT_OBSERVATION_INVALID",
                worktree=binding.worktree_path,
                reserved=reserved,
                scopes=scopes,
            )

        state = "READY" if _runtime_ready(context, row) else "UNKNOWN"
        mutation_allowed = bool(row.mutation_allowed) and git.dirty_state == "CLEAN" and state == "READY"
        scheduler = WorkerSnapshot(
            worker_id=row.worker_id,
            state=state,
            capabilities=capabilities,
            reserved=reserved,
            project=row.project_id,
            workspace=binding.worktree_path,
            mutation_authorized=mutation_allowed,
        )
        candidate = WorkerLeaseCandidate(
            worker_id=row.worker_id,
            state=state,
            reserved=reserved,
            active_task=reserved,
            capabilities=capabilities,
            runtime_id=row.runtime_id,
            project_id=row.project_id,
            worktree=binding.worktree_path,
            branch=git.branch,
            head=git.head,
            health_fresh=True,
            ownership_known=context.process_ownership is not ProcessOwnership.UNKNOWN,
            dirty_state=git.dirty_state,
            mutation_authorized=bool(row.mutation_allowed),
            occupied_mutable_scopes=scopes,
        )
        reason = "READY_DIRTY" if state == "READY" and git.dirty_state == "DIRTY" else (
            "READY" if state == "READY" else "WORKER_NOT_READY"
        )
        return WorkerSupplyRecord(row.worker_id, scheduler, candidate, reason)

    def assemble_all(self) -> tuple[WorkerSupplyRecord, ...]:
        snapshot = self._control_center.snapshot()
        if not isinstance(snapshot, ControlCenterSnapshot):
            raise WorkerCandidateAssemblyError("CONTROL_CENTER_SNAPSHOT_INVALID")
        records: list[WorkerSupplyRecord] = []
        for row in snapshot.workers:
            try:
                records.append(self.assemble(row.worker_id))
            except WorkerCandidateAssemblyError:
                records.append(self._closed(row, "ASSEMBLY_RECOVERY_REQUIRED"))
            except Exception:
                records.append(self._closed(row, "ASSEMBLY_EXCEPTION"))
        return tuple(records)
