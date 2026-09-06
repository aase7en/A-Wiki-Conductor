"""WO-P1-158 — thin production composition for ZCode execution (ZRA-1).

Builds the accepted ZCode execution path from EXISTING authorities only:
verified TaskPacketFile, provider configuration + typed runtime binding +
generation (existing store/CAS), authorized endpoint/base URL, accepted
secret-reference resolver, worker lease (existing broker), provider
admission (existing authority), and the canonical supervised lifecycle:

    assemble_zcode_execution
    -> SupervisedZCodeRunner
    -> SupervisedRunCoordinator
    -> ZCodeServiceLifecycleLauncher
    -> SupervisedExecutionService (helper kind ZCODE_APP_SERVER_V1)
    -> zcode_supervised_helper.py (real specialized helper subprocess)
    -> app-server child

The specialized helper is the ONLY production process lifecycle for ZCode
execution; no in-process transport adapter is constructed here. Adds NO
scheduler, task store, lease store, provider store, dedup engine, retry
engine, process supervisor, or review authority. Every fault fails closed
with a typed code BEFORE any child exists.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .claude_code_harness import TaskPacketFile
from .provider_configuration import HarnessRuntimeBinding, HarnessStrategy
from .zcode_runner import (
    ZCODE_BACKEND_ID,
    SupervisedZCodeRunner,
    ZCodeFilesystem,
    ZCodeProcessTruthChildObserver,
    ZCodeRunError,
    ZCodeSecretResolver,
    ZCodeSelectionSource,
    ZCodeServiceLifecycleLauncher,
    ZCodeTaskPacketIdentity,
    ZCodeTransportFactory,
)


class ZCodeAssemblyError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def derive_zcode_runtime_identity(
    *,
    provider_id: str,
    model_id: str,
    endpoint_base_url: str,
    runtime_provider_ref: str,
    runtime_model_ref: str,
    generation: int,
) -> str:
    """Deterministic domain-separated RUNTIME execution identity.

    Full SHA-256 (never truncated) over the canonical byte encoding
    ``"zcode-runtime-v1" || provider_id || NUL || model_id || NUL ||
    endpoint_base_url || NUL || runtime_provider_ref || NUL ||
    runtime_model_ref || NUL || generation`` — built ONLY from trusted
    canonical runtime facts (provider snapshot + binding + generation).
    Callers can never supply or influence the identity string; the same
    task under a different model/runtime binding therefore can never alias
    or reuse the previous execution."""
    material = b"zcode-runtime-v1" + b"\x00".join(
        part.encode("utf-8")
        for part in (
            provider_id,
            model_id,
            endpoint_base_url,
            runtime_provider_ref,
            runtime_model_ref,
            str(int(generation)),
        )
    )
    return f"zcode-runtime-v1:{hashlib.sha256(material).hexdigest()}"


@dataclass(frozen=True, slots=True)
class ZCodeExecutionAuthorities:
    """Trusted, already-accepted authorities injected by the Conductor.

    ``lease_evidence`` / ``admission_evidence`` carry the ACCEPTED lease /
    provider-admission records from the higher-level coordinator. The
    assembly consumes them at the final side-effect boundary; it never
    acquires, re-acquires, or schedules leases/admissions itself.

    ``supervised_controller`` / ``supervised_observer`` / ``python_executable``
    are the REAL owned-process authorities required to construct the
    production ``SupervisedExecutionService``; without them the assembly
    fails closed — there is no alternate in-process lifecycle.
    """

    provider_snapshot: object          # ProviderConfigurationSnapshot
    secret_resolver: ZCodeSecretResolver
    execution_store: object            # SQLiteExecutionStore
    # adapter-era seams (optional): the production specialized-helper path
    # does not consume them; they remain for non-production adapter callers.
    transport_factory: ZCodeTransportFactory | None = None
    filesystem: ZCodeFilesystem | None = None
    supervised_controller: object | None = None   # OwnedProcessController (REQUIRED)
    supervised_observer: object | None = None     # SupervisedProcessObserver (REQUIRED)
    python_executable: str = ""                    # REQUIRED for the real helper
    lease_evidence: object | None = None   # accepted canonical WorkerLease (REQUIRED)
    admission_evidence: object | None = None  # accepted canonical ProviderAdmissionRecord (REQUIRED)
    dispatch_batch_id: str = ""                    # independently-derived dispatch batch identity (REQUIRED)
    dispatch_execution_id: str | None = None       # optional execution binding from the dispatch context
    project_id: str = ""                           # dispatch-context project identity (vs lease)
    requested_mutable_scope: tuple[str, ...] = ()  # declared mutation targets (vs lease scope authority)
    worker_id: str = ""
    repo_root: str = ""
    branch: str = ""
    head: str = ""
    dirty: bool = False


def _binding_for_model(provider_snapshot, model_id: str) -> HarnessRuntimeBinding:
    profile = getattr(provider_snapshot, "profile", None)
    if profile is None:
        raise ZCodeAssemblyError("ZCODE_PROVIDER_UNAVAILABLE")
    if HarnessStrategy.ZCODE_APP_SERVER not in profile.harness_strategies:
        raise ZCodeAssemblyError("ZCODE_STRATEGY_NOT_CONFIGURED")
    model = next((m for m in profile.models if m.model_id == model_id), None)
    if model is None or model.runtime_binding is None:
        raise ZCodeAssemblyError("ZCODE_RUNTIME_BINDING_MISSING")
    return model.runtime_binding


class _AuthorizedSelection(ZCodeSelectionSource):
    """Selection source bound to the accepted provider snapshot + generation."""

    def __init__(self, provider_snapshot, binding: HarnessRuntimeBinding, base_url: str):
        self._snapshot = provider_snapshot
        self._binding = binding
        self._base_url = base_url

    def resolved_selection(self) -> dict:
        profile = getattr(self._snapshot, "profile", None)
        if profile is None:
            raise ZCodeAssemblyError("ZCODE_PROVIDER_UNAVAILABLE")
        if HarnessStrategy.ZCODE_APP_SERVER not in profile.harness_strategies:
            raise ZCodeAssemblyError("ZCODE_STRATEGY_NOT_CONFIGURED")
        return {
            "runtime_binding": self._binding,
            "runtime_base_url": self._base_url,
            "runtime_source_enabled": True,
        }


def assemble_zcode_execution(
    *,
    authorities: ZCodeExecutionAuthorities,
    packet: TaskPacketFile,
    model_id: str,
    expected_generation: int,
    expected_base_url: str,
    secret_reference: str,
    workspace: str,
    executable: str,
    bundle_js: str,
    deadline_seconds: float = 300.0,
) -> SupervisedZCodeRunner:
    """Compose one authorized ZCode execution; fail closed before any spawn.

    Every gate below must pass or NO child exists: observed dirty state →
    provider generation CAS → ZCODE strategy + per-model runtime binding →
    verified TaskPacketFile intake → the dispatch CONTEXT (independently
    derived batch identity) → the CANONICAL WorkerLease record bound to
    worker/worktree/branch/HEAD/task/project/mutation-intent/scope/active/
    expiry → the CANONICAL ProviderAdmissionRecord bound to
    provider/status/generation/expiry AND to the dispatch context
    (batch/execution identity) → the provider-snapshot ENDPOINT authority
    (``expected_base_url`` is only the caller's requested-route ASSERTION —
    it must match the snapshot authority and is never itself authority) →
    the derived runtime execution identity (``zcode-runtime-v1:<full sha>``)
    → REAL supervised-service authorities → the specialized-helper lifecycle.
    """

    from datetime import datetime, timezone as _tz

    from .provider_config_store import ProviderAdmissionRecord
    from .registry import windows_worktree_key
    from .supervised_run_coordinator import SupervisedRunIdentity
    from .worker_lease import LeaseMutationIntent, WorkerLease

    snapshot = authorities.provider_snapshot
    generation = getattr(snapshot, "generation", None)
    profile = getattr(snapshot, "profile", None)

    # 1. observed dirty state fails closed before anything else
    if authorities.dirty:
        raise ZCodeAssemblyError("ZCODE_WORKTREE_DIRTY")

    # 2. provider generation gate (existing CAS authority provides the number)
    if generation is None or expected_generation is None or int(generation) != int(expected_generation):
        raise ZCodeAssemblyError("ZCODE_PROVIDER_GENERATION_DRIFT")

    # 3. runtime binding + strategy authorization
    binding = _binding_for_model(snapshot, model_id)
    if binding.harness_strategy is not HarnessStrategy.ZCODE_APP_SERVER:
        raise ZCodeAssemblyError("ZCODE_STRATEGY_MISMATCH")

    # 4. verified task packet intake (confined path/size/hash — TOCTOU base)
    packet_identity = ZCodeTaskPacketIdentity.from_task_packet_file(
        packet, trusted_root=authorities.repo_root
    )

    # 5. LEASE authority: the assembly consumes the accepted CANONICAL
    #    WorkerLease record (the higher-level broker's authority) and binds
    #    it to THIS execution context. It never acquires or schedules leases
    #    itself, and nothing except a real WorkerLease satisfies the gate.
    lease = authorities.lease_evidence
    if lease is None:
        raise ZCodeAssemblyError("ZCODE_LEASE_ADMISSION_MISSING")
    if not isinstance(lease, WorkerLease):
        raise ZCodeAssemblyError("ZCODE_LEASE_INVALID")
    verify_execution_context(
        branch=authorities.branch,
        head=authorities.head,
        dirty=authorities.dirty,
        lease=lease,
    )
    if lease.worker_id != authorities.worker_id:
        raise ZCodeAssemblyError("ZCODE_LEASE_WORKER_MISMATCH")
    if lease.worktree_key != windows_worktree_key(authorities.repo_root):
        raise ZCodeAssemblyError("ZCODE_LEASE_WORKTREE_MISMATCH")
    if lease.task_id != packet.task_contract_ref:
        raise ZCodeAssemblyError("ZCODE_LEASE_TASK_MISMATCH")
    if authorities.project_id and authorities.project_id != lease.project_id:
        raise ZCodeAssemblyError("ZCODE_PROJECT_MISMATCH")
    # this production path executes a mutation-capable agent task: a
    # READ_ONLY lease can never authorize it
    if lease.mutation_intent is not LeaseMutationIntent.MUTATION:
        raise ZCodeAssemblyError("ZCODE_LEASE_MUTATION_INTENT_INSUFFICIENT")
    # declared mutation targets must be within the lease's allowed scope and
    # must never overlap its forbidden scope (existing overlap authority)
    from fnmatch import fnmatchcase

    from .worker_lease import _mutable_scope_is_authorized

    requested_scope = tuple(authorities.requested_mutable_scope or ())
    if requested_scope:
        if not _mutable_scope_is_authorized(lease.allowed_scope, requested_scope):
            raise ZCodeAssemblyError("ZCODE_SCOPE_NOT_AUTHORIZED")
        for expression in requested_scope:
            if expression in lease.forbidden_scope or any(
                fnmatchcase(expression, pattern) for pattern in lease.forbidden_scope
            ):
                raise ZCodeAssemblyError("ZCODE_SCOPE_FORBIDDEN")
    if lease.released_at is not None or lease.quarantined_at is not None:
        raise ZCodeAssemblyError("ZCODE_LEASE_NOT_ACTIVE")
    if lease.expires_at is not None:
        try:
            expires = datetime.fromisoformat(str(lease.expires_at).replace("Z", "+00:00"))
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=_tz.utc)
        except ValueError:
            raise ZCodeAssemblyError("ZCODE_LEASE_INVALID") from None
        if expires <= datetime.now(_tz.utc):
            raise ZCodeAssemblyError("ZCODE_LEASE_EXPIRED")

    # 6. PROVIDER ADMISSION authority: same consume-don't-reacquire rule —
    #    only the canonical ProviderAdmissionRecord satisfies the gate, and
    #    it must be bound to the INDEPENDENTLY-DERIVED dispatch context (the
    #    expected identity comes from the higher-level coordinator, NEVER
    #    from the admission record itself, so an unrelated active admission
    #    for the same provider/generation cannot authorize this execution).
    if not isinstance(authorities.dispatch_batch_id, str) or not authorities.dispatch_batch_id.strip():
        raise ZCodeAssemblyError("ZCODE_DISPATCH_CONTEXT_MISSING")
    admission = authorities.admission_evidence
    if admission is None:
        raise ZCodeAssemblyError("ZCODE_PROVIDER_ADMISSION_MISSING")
    if not isinstance(admission, ProviderAdmissionRecord):
        raise ZCodeAssemblyError("ZCODE_ADMISSION_INVALID")
    if admission.provider_id != profile.provider_id:
        raise ZCodeAssemblyError("ZCODE_ADMISSION_PROVIDER_MISMATCH")
    if admission.status != "ADMITTED":
        raise ZCodeAssemblyError("ZCODE_ADMISSION_NOT_ADMITTED")
    if (
        admission.configuration_generation is None
        or int(admission.configuration_generation) != int(expected_generation)
    ):
        raise ZCodeAssemblyError("ZCODE_ADMISSION_GENERATION_DRIFT")
    if admission.expires_at is None or admission.expires_at.tzinfo is None:
        raise ZCodeAssemblyError("ZCODE_ADMISSION_INVALID")
    if admission.expires_at <= datetime.now(_tz.utc):
        raise ZCodeAssemblyError("ZCODE_ADMISSION_EXPIRED")
    if admission.batch_id != authorities.dispatch_batch_id:
        raise ZCodeAssemblyError("ZCODE_ADMISSION_BATCH_MISMATCH")
    if (
        authorities.dispatch_execution_id is not None
        and admission.execution_id != authorities.dispatch_execution_id
    ):
        raise ZCodeAssemblyError("ZCODE_ADMISSION_EXECUTION_MISMATCH")

    # 7. ENDPOINT authority: the observed truth is the provider-snapshot
    #    endpoint configuration. ``expected_base_url`` is ONLY the caller's
    #    requested-route assertion — it must match the snapshot authority
    #    exactly; the caller can never define both sides of the comparison.
    endpoint = getattr(snapshot, "endpoint", None)
    endpoint_base_url = getattr(endpoint, "base_url", None)
    if not isinstance(endpoint_base_url, str) or not endpoint_base_url.strip():
        raise ZCodeAssemblyError("ZCODE_ENDPOINT_AUTHORITY_MISSING")
    if expected_base_url.strip() != endpoint_base_url.strip():
        raise ZCodeAssemblyError("ZCODE_ENDPOINT_UNAUTHORIZED")
    selection = _AuthorizedSelection(snapshot, binding, endpoint_base_url)

    # 8. RUNTIME EXECUTION IDENTITY: derived (never caller-supplied) from
    #    the trusted canonical runtime facts — same task under a different
    #    model/runtime binding can never alias or reuse this execution.
    runtime_profile_ref = derive_zcode_runtime_identity(
        provider_id=profile.provider_id,
        model_id=model_id,
        endpoint_base_url=endpoint_base_url,
        runtime_provider_ref=binding.runtime_provider_ref,
        runtime_model_ref=binding.runtime_model_ref,
        generation=int(generation),
    )

    # 8. REAL production supervised lifecycle: the specialized helper through
    #    SupervisedExecutionService + ZCODE_APP_SERVER_V1. The service
    #    authorities are MANDATORY — no in-process transport fallback exists.
    if (
        authorities.supervised_controller is None
        or authorities.supervised_observer is None
        or not isinstance(authorities.python_executable, str)
        or not authorities.python_executable.strip()
    ):
        raise ZCodeAssemblyError("ZCODE_SERVICE_AUTHORITY_MISSING")

    from .supervised_execution import SupervisedExecutionService, SupervisedHelperKind

    try:
        service = SupervisedExecutionService(
            store=authorities.execution_store,
            controller=authorities.supervised_controller,
            observer=authorities.supervised_observer,
            allowed_target_executables=(Path(executable).name,),
            python_executable=authorities.python_executable,
            startup_poll_attempts=100,
            startup_poll_delay_seconds=0.05,
            helper_kinds={SupervisedHelperKind.ZCODE_APP_SERVER_V1},
        )
    except (TypeError, ValueError) as exc:
        raise ZCodeAssemblyError("ZCODE_SERVICE_AUTHORITY_INVALID") from exc

    launcher = ZCodeServiceLifecycleLauncher(
        service=service,
        selection_source=selection,
        expected_binding=binding,
        expected_base_url=endpoint_base_url,  # snapshot endpoint authority
        secret_resolver=authorities.secret_resolver,
        secret_reference=secret_reference,
        packet=packet_identity,
        executable=executable,
        bundle_js=bundle_js,
        deadline_seconds=deadline_seconds,
        execution_store=authorities.execution_store,
        child_observer=ZCodeProcessTruthChildObserver(),
    )
    identity = SupervisedRunIdentity(
        job_id=f"job:{packet.task_contract_ref}",
        work_order_ref=packet.task_contract_ref,
        project_id=lease.project_id,  # trusted project identity from the LEASE
        worker_id=authorities.worker_id,
        backend_id=ZCODE_BACKEND_ID,
        branch=authorities.branch,
        head_before=authorities.head,
        runtime_profile_ref=runtime_profile_ref,  # derived runtime identity
        repo_root=authorities.repo_root,
    )
    return SupervisedZCodeRunner(
        execution_store=authorities.execution_store,
        identity=identity,
        adapter=launcher,
        executable=executable,
        bundle_js=bundle_js,
        task_packet=packet_identity,
    )


def verify_execution_context(
    *,
    branch: str,
    head: str,
    dirty: bool,
    lease: "object",
) -> None:
    """Worktree gate: OBSERVED context vs the LEASE authority record.

    The lease is the canonical accepted authority for branch/HEAD; the
    caller never supplies the expected pair. Drift or mismatch fails
    closed before any child exists."""
    if dirty:
        raise ZCodeAssemblyError("ZCODE_WORKTREE_DIRTY")
    if branch != lease.branch:
        raise ZCodeAssemblyError("ZCODE_BRANCH_DRIFT")
    if head.casefold() != str(lease.expected_head).casefold():
        raise ZCodeAssemblyError("ZCODE_HEAD_DRIFT")
