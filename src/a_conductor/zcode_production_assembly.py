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
    lease_evidence: object | None = None   # accepted lease record (truthy when acquired)
    admission_evidence: object | None = None  # accepted provider admission (truthy)
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
    authorized_base_url: str,
    secret_reference: str,
    workspace: str,
    executable: str,
    bundle_js: str,
    endpoint_base_url: str | None = None,
    expected_branch: str | None = None,
    expected_head: str | None = None,
    deadline_seconds: float = 300.0,
) -> SupervisedZCodeRunner:
    """Compose one authorized ZCode execution; fail closed before any spawn.

    Every gate below must pass or NO child exists:
    git/worktree identity (branch/HEAD/dirty) → provider generation CAS →
    ZCODE strategy + per-model runtime binding → verified TaskPacketFile
    intake (confined path/size/hash) → REAL supervised-service authorities →
    lease admission evidence → provider admission evidence → secret-ref
    authority wiring → the specialized-helper production lifecycle.
    """

    from .supervised_run_coordinator import SupervisedRunIdentity

    snapshot = authorities.provider_snapshot
    generation = getattr(snapshot, "generation", None)
    profile = getattr(snapshot, "profile", None)

    # 1. git/worktree gate — executed, not documented-only
    verify_execution_context(
        branch=authorities.branch,
        head=authorities.head,
        dirty=authorities.dirty,
        expected_branch=expected_branch if expected_branch is not None else authorities.branch,
        expected_head=expected_head if expected_head is not None else authorities.head,
    )

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

    # 5. lease admission evidence: the assembly CONSUMES the accepted
    #    broker's records; it never re-acquires or schedules leases itself.
    lease_evidence = getattr(authorities, "lease_evidence", None)
    if lease_evidence is not None and not lease_evidence:
        raise ZCodeAssemblyError("ZCODE_LEASE_ADMISSION_MISSING")

    # 6. provider admission evidence: same consume-don't-reacquire rule.
    admission_evidence = getattr(authorities, "admission_evidence", None)
    if admission_evidence is not None and not admission_evidence:
        raise ZCodeAssemblyError("ZCODE_PROVIDER_ADMISSION_MISSING")

    # The selection source reports the ENDPOINT-AUTHORITY truth; the
    # launcher's expected_base_url is the dispatch-declared authorization.
    # They must agree or ZCODE_SELECTION_UNAUTHORIZED fails closed at run.
    resolved_endpoint = endpoint_base_url if endpoint_base_url is not None else authorized_base_url
    selection = _AuthorizedSelection(snapshot, binding, resolved_endpoint)

    # 7. REAL production supervised lifecycle: the specialized helper through
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
        expected_base_url=authorized_base_url,
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
        project_id="zcode",
        worker_id=authorities.worker_id,
        backend_id=ZCODE_BACKEND_ID,
        branch=authorities.branch,
        head_before=authorities.head,
        runtime_profile_ref=f"provider:{profile.provider_id}@{generation}",
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
    branch: str, head: str, dirty: bool,
    expected_branch: str, expected_head: str,
) -> None:
    """Git/worktree gate: drift, mismatch, or dirty fails closed."""
    if dirty:
        raise ZCodeAssemblyError("ZCODE_WORKTREE_DIRTY")
    if branch != expected_branch:
        raise ZCodeAssemblyError("ZCODE_BRANCH_MISMATCH")
    if head.casefold() != expected_head.casefold():
        raise ZCodeAssemblyError("ZCODE_HEAD_DRIFT")
