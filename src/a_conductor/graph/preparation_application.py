"""WO-P1-470 — ZRA-3A Child-B preparation + binding application seam.

One injectable ``PreparationApplication`` service object that validates an
already-authoritative graph-run preparation intent against durable JobStore
checkpoint evidence, invokes the accepted GraphStore v2 ``prepare_run``
primitive exactly once per call after every fail-closed check, and reconstructs
typed ``RuntimeActivationRequest`` values from trusted binding/current
authorities with fresh digest checks.

This module owns no job lifecycle, scheduler, retry, idempotency, completion,
provider selection, runtime activation, dispatch or NEXT_READY authority:
JobStore is read-only here (``get_job`` + ``list_events`` only), GraphStore
owns run/binding persistence and replay, and the intent author outside this
seam mints and checkpoints the preparation ref before the first prepare.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

from ..domain import Project, TaskState
from ..job_store import JobEvent, JobEventType, JobStoreError
from ..registry import RegistryNotFoundError
from ..runtime_activation import RuntimeActivationRequest
from .domain import TaskGraph
from .store import GraphRunBindingSpec, GraphStoreError


_PREPARATION_REF_RE = re.compile(r"^graph-run-preparation-v1:[0-9a-f]{32}$")
_PREPARATION_EVIDENCE_RE = re.compile(
    r"^graph-run-preparation:(graph-run-preparation-v1:[0-9a-f]{32})$"
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:")
_TERMINAL_JOB_STATES = frozenset(
    {TaskState.COMPLETE, TaskState.FAILED, TaskState.CANCELLED}
)
_EVIDENCE_PREFIX = "graph-run-preparation:"


class PreparationApplicationError(RuntimeError):
    """Stable typed Child-B preparation failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class NodeBindingIntent:
    """Caller-submitted per-node binding intent; validation lives in prepare."""

    node_id: str
    runtime_kind: str
    task_contract_ref: str
    task_contract_sha256: str
    task_packet_ref: str
    task_packet_sha256: str
    provider_id: str
    model_id: str
    effort_level: str


@dataclass(frozen=True, slots=True)
class PreparationIntent:
    """One already-authoritative preparation intent; not authority by itself."""

    preparation_ref: str
    driving_job_id: str
    graph_id: str
    project_id: str
    work_order_ref: str
    bindings: tuple[NodeBindingIntent, ...]


@dataclass(frozen=True, slots=True)
class PreparationResult:
    run: object
    activation_requests: tuple[RuntimeActivationRequest, ...]


class JobReadPort(Protocol):
    def get_job(self, job_id: str) -> object: ...

    def list_events(self, job_id: str) -> tuple[JobEvent, ...]: ...


class GraphPreparePort(Protocol):
    def load_graph(self, graph_id: str) -> TaskGraph: ...

    def prepare_run(
        self,
        *,
        graph_id: str,
        project_id: str,
        preparation_ref: str,
        bindings: Iterable[GraphRunBindingSpec],
    ) -> object: ...

    def load_graph_run_bindings(self, run_id: str) -> tuple[object, ...]: ...


class ProjectRegistryPort(Protocol):
    def get_project(self, project_id: str) -> Project: ...


class ProviderAuthorityPort(Protocol):
    def get_provider_snapshot(self, provider_id: str) -> object | None: ...


def _require_preparation_ref(value: object) -> str:
    if not isinstance(value, str) or _PREPARATION_REF_RE.fullmatch(value) is None:
        raise PreparationApplicationError("PREPARATION_REF_INVALID")
    return value


def _canonical_preparation_refs(events: Iterable[JobEvent]) -> set[str]:
    refs: set[str] = set()
    for event in events:
        if event.event_type is not JobEventType.CHECKPOINT:
            continue
        ref_text = event.checkpoint_ref
        if not isinstance(ref_text, str):
            continue
        match = _PREPARATION_EVIDENCE_RE.fullmatch(ref_text)
        if match is not None:
            refs.add(match.group(1))
    return refs


def _require_project_relative_ref(value: object, *, code: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise PreparationApplicationError(code)
    if (
        value.startswith("/")
        or "\\" in value
        or _WINDOWS_ABSOLUTE_RE.match(value) is not None
    ):
        raise PreparationApplicationError(code)
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise PreparationApplicationError(code)
    return value


def _require_sha256(value: object, *, code: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise PreparationApplicationError(code)
    return value


def _require_reconstruction_text(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
        or any(char in value for char in ("\x00", "\r", "\n"))
    ):
        raise PreparationApplicationError("ACTIVATION_RECONSTRUCTION_INVALID")
    return value


def _require_node_id(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise PreparationApplicationError("BINDING_NODE_INVALID")
    return value


def _require_explicit_route_field(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise PreparationApplicationError("ROUTE_SELECTION_REQUIRED")
    return value


def _verify_file_digest(
    root: Path,
    ref: str,
    expected_sha256: str,
    *,
    unavailable: str,
    mismatch: str,
) -> None:
    path = (root / ref).resolve(strict=False)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise PreparationApplicationError(unavailable) from exc
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise PreparationApplicationError(mismatch)


class PreparationApplication:
    """Verify one preparation intent, prepare once, reconstruct activation."""

    def __init__(
        self,
        *,
        job_store: JobReadPort,
        graph_store: GraphPreparePort,
        project_registry: ProjectRegistryPort,
        provider_authority: ProviderAuthorityPort,
    ) -> None:
        self._job_store = job_store
        self._graph_store = graph_store
        self._project_registry = project_registry
        self._provider_authority = provider_authority

    def prepare(self, intent: PreparationIntent) -> PreparationResult:
        if not isinstance(intent, PreparationIntent):
            raise PreparationApplicationError("PREPARATION_INTENT_INVALID")
        preparation_ref = _require_preparation_ref(intent.preparation_ref)

        job = self._load_driving_job(intent.driving_job_id)
        self._require_usable_driving_job(job, intent)

        durable_refs = _canonical_preparation_refs(
            self._list_events(intent.driving_job_id)
        )
        if not durable_refs:
            raise PreparationApplicationError("PREPARATION_PROVENANCE_MISSING")
        if len(durable_refs) > 1:
            raise PreparationApplicationError("PREPARATION_PROVENANCE_AMBIGUOUS")
        sole_ref = next(iter(durable_refs))
        if sole_ref != preparation_ref:
            raise PreparationApplicationError("PREPARATION_PROVENANCE_MISMATCH")

        project = self._load_project(intent.project_id)
        graph = self._load_graph(intent.graph_id)
        nodes = {node.id: node for node in graph.nodes()}

        specs = tuple(
            self._validated_binding_spec(binding, nodes, project)
            for binding in tuple(intent.bindings)
        )
        run = self._prepare_run(intent, preparation_ref, specs)
        durable_bindings = self._load_durable_bindings(run)
        activation_requests = tuple(
            self._reconstruct_activation_request(record, run, project)
            for record in durable_bindings
        )
        return PreparationResult(run=run, activation_requests=activation_requests)

    def _load_driving_job(self, job_id: str) -> object:
        try:
            return self._job_store.get_job(job_id)
        except JobStoreError as exc:
            raise PreparationApplicationError(exc.code) from exc

    def _list_events(self, job_id: str) -> tuple[JobEvent, ...]:
        try:
            return self._job_store.list_events(job_id)
        except JobStoreError as exc:
            raise PreparationApplicationError(exc.code) from exc

    @staticmethod
    def _require_usable_driving_job(job: object, intent: PreparationIntent) -> None:
        if getattr(job, "state", None) in _TERMINAL_JOB_STATES:
            raise PreparationApplicationError("DRIVING_JOB_TERMINAL")
        if getattr(job, "project_id", None) != intent.project_id:
            raise PreparationApplicationError("DRIVING_JOB_PROJECT_MISMATCH")
        if getattr(job, "work_order_ref", None) != intent.work_order_ref:
            raise PreparationApplicationError("DRIVING_JOB_WORK_ORDER_MISMATCH")

    def _load_project(self, project_id: str) -> Project:
        try:
            return self._project_registry.get_project(project_id)
        except RegistryNotFoundError as exc:
            raise PreparationApplicationError("PROJECT_AUTHORITY_UNAVAILABLE") from exc

    def _load_graph(self, graph_id: str) -> TaskGraph:
        try:
            graph = self._graph_store.load_graph(graph_id)
        except GraphStoreError as exc:
            raise PreparationApplicationError("GRAPH_UNAVAILABLE") from exc
        if not isinstance(graph, TaskGraph) or not graph.nodes():
            raise PreparationApplicationError("GRAPH_UNAVAILABLE")
        return graph

    def _validated_binding_spec(
        self,
        binding: NodeBindingIntent,
        nodes: dict[str, object],
        project: Project,
    ) -> GraphRunBindingSpec:
        node_id = _require_node_id(binding.node_id)
        node = nodes.get(node_id)
        if node is None:
            raise PreparationApplicationError("BINDING_NODE_INVALID")

        contract_ref = _require_project_relative_ref(
            binding.task_contract_ref, code="TASK_CONTRACT_REF_INVALID"
        )
        packet_ref = _require_project_relative_ref(
            binding.task_packet_ref, code="TASK_PACKET_REF_INVALID"
        )
        contract_sha256 = _require_sha256(
            binding.task_contract_sha256, code="TASK_CONTRACT_DIGEST_INVALID"
        )
        packet_sha256 = _require_sha256(
            binding.task_packet_sha256, code="TASK_PACKET_DIGEST_INVALID"
        )
        root = Path(project.root_path)
        _verify_file_digest(
            root,
            contract_ref,
            contract_sha256,
            unavailable="TASK_CONTRACT_UNAVAILABLE",
            mismatch="TASK_CONTRACT_DIGEST_MISMATCH",
        )
        _verify_file_digest(
            root,
            packet_ref,
            packet_sha256,
            unavailable="TASK_PACKET_UNAVAILABLE",
            mismatch="TASK_PACKET_DIGEST_MISMATCH",
        )

        if not isinstance(binding.runtime_kind, str) or binding.runtime_kind != "serena":
            raise PreparationApplicationError("RUNTIME_KIND_AUTHORITY_UNAVAILABLE")

        provider_id = _require_explicit_route_field(binding.provider_id)
        model_id = _require_explicit_route_field(binding.model_id)
        effort_level = _require_explicit_route_field(binding.effort_level)
        self._authorize_route(provider_id, model_id, effort_level)

        if getattr(node, "worker_requirement", None):
            raise PreparationApplicationError(
                "RUNTIME_CAPABILITY_AUTHORITY_UNAVAILABLE"
            )

        return GraphRunBindingSpec(
            node_id=node_id,
            runtime_kind=binding.runtime_kind,
            task_contract_ref=contract_ref,
            task_contract_sha256=contract_sha256,
            task_packet_ref=packet_ref,
            task_packet_sha256=packet_sha256,
            provider_id=provider_id,
            model_id=model_id,
            effort_level=effort_level,
        )

    def _authorize_route(
        self, provider_id: str, model_id: str, effort_level: str
    ) -> None:
        snapshot = self._provider_authority.get_provider_snapshot(provider_id)
        profile = getattr(snapshot, "profile", None)
        if profile is None or getattr(profile, "provider_id", None) != provider_id:
            raise PreparationApplicationError("ROUTE_SELECTION_UNAUTHORIZED")
        if getattr(profile, "enabled", True) is not True:
            raise PreparationApplicationError("ROUTE_SELECTION_UNAUTHORIZED")
        model = next(
            (
                item
                for item in (getattr(profile, "models", None) or ())
                if getattr(item, "model_id", None) == model_id
            ),
            None,
        )
        if model is None:
            raise PreparationApplicationError("ROUTE_SELECTION_UNAUTHORIZED")
        if effort_level not in (
            getattr(model, "supported_effort_levels", None) or ()
        ):
            raise PreparationApplicationError("ROUTE_SELECTION_UNAUTHORIZED")

    def _prepare_run(
        self,
        intent: PreparationIntent,
        preparation_ref: str,
        specs: tuple[GraphRunBindingSpec, ...],
    ) -> object:
        try:
            return self._graph_store.prepare_run(
                graph_id=intent.graph_id,
                project_id=intent.project_id,
                preparation_ref=preparation_ref,
                bindings=specs,
            )
        except GraphStoreError as exc:
            raise PreparationApplicationError(exc.code) from exc

    def _load_durable_bindings(self, run: object) -> tuple[object, ...]:
        run_id = _require_reconstruction_text(getattr(run, "run_id", None))
        try:
            return self._graph_store.load_graph_run_bindings(run_id)
        except GraphStoreError as exc:
            raise PreparationApplicationError(exc.code) from exc

    def _reconstruct_activation_request(
        self, record: object, run: object, project: Project
    ) -> RuntimeActivationRequest:
        node_id = _require_reconstruction_text(getattr(record, "node_id", None))
        runtime_kind = _require_reconstruction_text(
            getattr(record, "runtime_kind", None)
        )
        if runtime_kind != "serena":
            raise PreparationApplicationError("ACTIVATION_RECONSTRUCTION_INVALID")
        contract_ref = _require_project_relative_ref(
            getattr(record, "task_contract_ref", None),
            code="ACTIVATION_RECONSTRUCTION_INVALID",
        )
        packet_ref = _require_project_relative_ref(
            getattr(record, "task_packet_ref", None),
            code="ACTIVATION_RECONSTRUCTION_INVALID",
        )
        contract_sha256 = _require_sha256(
            getattr(record, "task_contract_sha256", None),
            code="ACTIVATION_RECONSTRUCTION_INVALID",
        )
        packet_sha256 = _require_sha256(
            getattr(record, "task_packet_sha256", None),
            code="ACTIVATION_RECONSTRUCTION_INVALID",
        )
        provider_id = _require_reconstruction_text(
            getattr(record, "provider_id", None)
        )
        model_id = _require_reconstruction_text(getattr(record, "model_id", None))
        effort_level = _require_reconstruction_text(
            getattr(record, "effort_level", None)
        )

        root = Path(project.root_path)
        _verify_file_digest(
            root,
            contract_ref,
            contract_sha256,
            unavailable="ACTIVATION_RECONSTRUCTION_STALE",
            mismatch="ACTIVATION_RECONSTRUCTION_STALE",
        )
        _verify_file_digest(
            root,
            packet_ref,
            packet_sha256,
            unavailable="ACTIVATION_RECONSTRUCTION_STALE",
            mismatch="ACTIVATION_RECONSTRUCTION_STALE",
        )

        return RuntimeActivationRequest(
            graph_id=_require_reconstruction_text(getattr(run, "graph_id", None)),
            graph_run_id=_require_reconstruction_text(getattr(run, "run_id", None)),
            node_id=node_id,
            runtime_kind=runtime_kind,
            project_root=_require_reconstruction_text(project.root_path),
            task_contract_ref=contract_ref,
            task_packet_path=str((root / packet_ref).resolve(strict=False)),
            provider_id=provider_id,
            model_id=model_id,
            effort_level=effort_level,
        )
