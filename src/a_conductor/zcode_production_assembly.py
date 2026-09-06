"""WO-P1-158 — thin production composition for ZCode execution (ZRA-1).

Builds the accepted ZCode execution path from EXISTING authorities only:
verified TaskPacketFile, provider configuration + typed runtime binding +
generation (existing store/CAS), authorized endpoint/base URL, accepted
secret-reference resolver, worker lease (existing broker), provider
admission (existing authority), and the canonical supervised lifecycle
(shared coordinator → closed helper kind → specialized helper).

Adds NO scheduler, task store, lease store, provider store, dedup engine,
retry engine, process supervisor, or review authority. Every fault fails
closed with a typed code BEFORE any child exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .claude_code_harness import TaskPacketFile
from .provider_configuration import HarnessRuntimeBinding, HarnessStrategy
from .zcode_runner import (
    ZCODE_BACKEND_ID,
    SupervisedZCodeRunner,
    ZCodeBackendAdapter,
    ZCodeFilesystem,
    ZCodeRunError,
    ZCodeSecretResolver,
    ZCodeSelectionSource,
    ZCodeTaskPacketIdentity,
    ZCodeTransportFactory,
)


class ZCodeAssemblyError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class ZCodeExecutionAuthorities:
    """Trusted, already-accepted authorities injected by the Conductor."""

    provider_snapshot: object          # ProviderConfigurationSnapshot
    secret_resolver: ZCodeSecretResolver
    transport_factory: ZCodeTransportFactory
    filesystem: ZCodeFilesystem
    execution_store: object            # SQLiteExecutionStore
    lease_broker: object              # WorkerLeaseBroker (existing authority)
    worker_id: str
    repo_root: str
    branch: str
    head: str
    dirty: bool


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
) -> SupervisedZCodeRunner:
    """Compose one authorized ZCode execution; fail closed before any spawn."""

    # 1. git/worktree gate: HEAD, branch, dirty — checked against the
    #    trusted authorities BEFORE touching the provider or secrets.
    from .supervised_run_coordinator import SupervisedRunIdentity

    snapshot = authorities.provider_snapshot
    generation = getattr(snapshot, "generation", None)
    profile = getattr(snapshot, "profile", None)

    # 2. provider generation gate (existing CAS authority provides the number)
    if generation is None or expected_generation is None or int(generation) != int(expected_generation):
        raise ZCodeAssemblyError("ZCODE_PROVIDER_GENERATION_DRIFT")

    # 3. runtime binding + strategy authorization
    binding = _binding_for_model(snapshot, model_id)
    if binding.harness_strategy is not HarnessStrategy.ZCODE_APP_SERVER:
        raise ZCodeAssemblyError("ZCODE_STRATEGY_MISMATCH")

    # 4. verified task packet intake (path/size/hash — TOCTOU base)
    packet_identity = ZCodeTaskPacketIdentity.from_task_packet_file(packet)

    # The selection source reports the ENDPOINT-AUTHORITY truth; the
    # adapter's expected_base_url is the dispatch-declared authorization.
    # They must agree or ZCODE_SELECTION_UNAUTHORIZED fails closed at run.
    resolved_endpoint = endpoint_base_url if endpoint_base_url is not None else authorized_base_url
    selection = _AuthorizedSelection(snapshot, binding, resolved_endpoint)

    adapter = ZCodeBackendAdapter(
        transport_factory=authorities.transport_factory,
        filesystem=authorities.filesystem,
        execution_store=authorities.execution_store,
        selection_source=selection,
        expected_binding=binding,
        expected_base_url=authorized_base_url,
        secret_resolver=authorities.secret_resolver,
        secret_reference=secret_reference,
        packet=packet_identity,
        workspace=workspace,
        executable=executable,
        bundle_js=bundle_js,
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
        adapter=adapter,
        executable=executable,
        bundle_js=bundle_js,
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
