"""WO-P1-736 — read-only prepared-run successor reconstruction seam.

Given an EXPLICIT graph-run identity (``graph_id`` + ``run_id``) and a
planner-selected ``node_id``, reconstruct the existing activation request
ONLY after validating the durable run/node binding and the current
contract/packet identity. This is a pure composition over injected,
fixture-ownable ports; it performs NO new-run preparation, NO "latest"
selection, NO dispatch, NO durable writes, NO scheduler, NO network, and
never bypasses the ORCH-1/7 HOLD.

Reused seams (verified at base 722c4a5):
- ``GraphStore.load_graph_run``            (src/a_conductor/graph/store.py:1061)
- ``GraphStore.load_graph_run_bindings``   (src/a_conductor/graph/store.py:1084)
- ``PreparationApplication._reconstruct_activation_request``
    (src/a_conductor/graph/preparation_application.py:396) — the request
    shape, project-relative/digest validation rules, and the project-root
    binding of contract/packet verification are mirrored here read-only;
    that method itself stays the write-path authority.

Contract/packet digest verification is bound to the RESOLVED durable
project root (project identity): the digest port is invoked as
``current_digest(resolved_root, ref)`` so digests observed under another
project's root can never validate this project's request, mirroring the
write path's ``_verify_file_digest(root, ref, ...)`` binding.

Typed fail-closed blocker reason codes (all raised as
``PreparedRunReconstructionError`` with ``.code`` set to exactly one of):

- ``PREPARED_RUN_INPUT_INVALID``            caller identity text invalid
- ``PREPARED_RUN_NOT_FOUND``                store reports run absent
- ``PREPARED_RUN_STORE_BLOCKED``            other store failure, including
    unexpected store/port exceptions and malformed binding iterables
    (original store code preserved on ``.store_code`` when the failure is
    a typed ``GraphStoreError``; otherwise ``.store_code`` is None)
- ``PREPARED_RUN_RECORD_INVALID``           store returned a malformed run
    record or one whose durable run_id contradicts the request
- ``PREPARED_RUN_IDENTITY_MISMATCH``        durable graph identity differs
    from the explicit requested identity (foreign/wrong run)
- ``PREPARED_RUN_NOT_PREPARED``             durable run lacks valid v2
    prepared identity markers: project id / preparation ref fail store
    text rules or definition/preparation digests fail the SHA-256 rule
    (absent, empty, or malformed)
- ``PREPARED_RUN_PROJECT_UNAVAILABLE``      project root authority cannot
    resolve the durable project id, the resolved root fails, or the
    authority returns a non-absolute root (rejected BEFORE any resolution
    use so no digest observation or request path can bind to the process
    CWD)
- ``PREPARED_RUN_BINDING_AUTHORITY_UNAVAILABLE`` binding authority shape
    unavailable (legacy/unknown schema)
- ``PREPARED_RUN_NODE_NOT_BOUND``           selected node has no binding
- ``PREPARED_RUN_NODE_BINDING_AMBIGUOUS``   duplicate bindings for the
    selected node
- ``PREPARED_RUN_BINDING_RECORD_INVALID``   binding record malformed or its
    durable run_id contradicts the request
- ``PREPARED_RUN_RUNTIME_KIND_UNAUTHORIZED`` durable runtime kind is not
    the accepted ``serena`` authority
- ``PREPARED_RUN_CONTRACT_UNAVAILABLE``     current contract digest
    unresolvable under the resolved durable project root
- ``PREPARED_RUN_CONTRACT_DIGEST_MISMATCH`` current contract identity
    drifted from the durable binding
- ``PREPARED_RUN_PACKET_UNAVAILABLE``       current packet digest
    unresolvable under the resolved durable project root, or the durable
    packet path cannot be resolved at the request boundary (contained
    path-resolution failure)
- ``PREPARED_RUN_PACKET_DIGEST_MISMATCH``   current packet identity
    drifted from the durable binding

Ambiguity, drift, missing or duplicate binding never recover into a new
run; every failure above is terminal for this call.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

from .runtime_activation import RuntimeActivationRequest
from .graph.store import (
    GraphRunBindingRecord,
    GraphRunRecord,
    GraphStoreError,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:")
_ACCEPTED_RUNTIME_KIND = "serena"
_MAX_PREPARED_TEXT = 512


class PreparedRunReconstructionError(RuntimeError):
    """Typed fail-closed prepared-run reconstruction blocker."""

    def __init__(
        self, code: str, *, store_code: str | None = None
    ) -> None:
        self.code = code
        self.store_code = store_code
        super().__init__(code if store_code is None else f"{code}:{store_code}")


class PreparedRunStorePort(Protocol):
    """Structural port satisfied by ``GraphStore`` (store.py:1061/:1084)."""

    def load_graph_run(self, run_id: str) -> GraphRunRecord: ...

    def load_graph_run_bindings(
        self, run_id: str
    ) -> tuple[GraphRunBindingRecord, ...]: ...


class ProjectRootPort(Protocol):
    def project_root(self, project_id: str) -> str | None: ...


class ArtifactDigestPort(Protocol):
    def current_digest(self, project_root: str, ref: str) -> str | None: ...


def _require_identity_text(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
    ):
        raise PreparedRunReconstructionError("PREPARED_RUN_INPUT_INVALID")
    return value


def _require_reconstruction_text(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
        or any(char in value for char in ("\x00", "\r", "\n"))
    ):
        raise PreparedRunReconstructionError("PREPARED_RUN_BINDING_RECORD_INVALID")
    return value


def _require_project_root(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
        or any(char in value for char in ("\x00", "\r", "\n"))
        or not Path(value).is_absolute()
    ):
        raise PreparedRunReconstructionError("PREPARED_RUN_PROJECT_UNAVAILABLE")
    return value


def _require_project_relative_ref(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise PreparedRunReconstructionError("PREPARED_RUN_BINDING_RECORD_INVALID")
    if any(char in value for char in ("\x00", "\r", "\n")):
        raise PreparedRunReconstructionError("PREPARED_RUN_BINDING_RECORD_INVALID")
    if (
        value.startswith("/")
        or "\\" in value
        or _WINDOWS_ABSOLUTE_RE.match(value) is not None
    ):
        raise PreparedRunReconstructionError("PREPARED_RUN_BINDING_RECORD_INVALID")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise PreparedRunReconstructionError("PREPARED_RUN_BINDING_RECORD_INVALID")
    return value


def _require_sha256(value: object) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise PreparedRunReconstructionError("PREPARED_RUN_BINDING_RECORD_INVALID")
    return value


def _is_valid_prepared_text(value: object) -> bool:
    """Store text rules (store.py:283 ``_require_text``), readiness-neutral."""
    return (
        isinstance(value, str)
        and bool(value)
        and len(value) <= _MAX_PREPARED_TEXT
        and value == value.strip()
        and not any(char in value for char in ("\x00", "\r", "\n"))
    )


def _is_valid_prepared_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _store_code(exc: GraphStoreError) -> str | None:
    code = getattr(exc, "code", None)
    return code if isinstance(code, str) else None


def _load_run(run_store: PreparedRunStorePort, run_id: str) -> object:
    try:
        return run_store.load_graph_run(run_id)
    except GraphStoreError as exc:
        if _store_code(exc) == "GRAPH_RUN_NOT_FOUND":
            raise PreparedRunReconstructionError("PREPARED_RUN_NOT_FOUND") from exc
        raise PreparedRunReconstructionError(
            "PREPARED_RUN_STORE_BLOCKED", store_code=_store_code(exc)
        ) from exc
    except Exception as exc:
        raise PreparedRunReconstructionError(
            "PREPARED_RUN_STORE_BLOCKED"
        ) from exc


def _load_bindings(
    run_store: PreparedRunStorePort, run_id: str
) -> tuple[object, ...]:
    try:
        return tuple(run_store.load_graph_run_bindings(run_id))
    except GraphStoreError as exc:
        if _store_code(exc) == "GRAPH_RUN_BINDING_AUTHORITY_UNAVAILABLE":
            raise PreparedRunReconstructionError(
                "PREPARED_RUN_BINDING_AUTHORITY_UNAVAILABLE",
                store_code=_store_code(exc),
            ) from exc
        raise PreparedRunReconstructionError(
            "PREPARED_RUN_STORE_BLOCKED", store_code=_store_code(exc)
        ) from exc
    except Exception as exc:
        raise PreparedRunReconstructionError(
            "PREPARED_RUN_STORE_BLOCKED"
        ) from exc


def _require_prepared_identity(run: GraphRunRecord) -> str:
    if not _is_valid_prepared_text(run.project_id):
        raise PreparedRunReconstructionError("PREPARED_RUN_NOT_PREPARED")
    if not _is_valid_prepared_sha256(run.graph_definition_sha256):
        raise PreparedRunReconstructionError("PREPARED_RUN_NOT_PREPARED")
    if not _is_valid_prepared_text(run.preparation_ref):
        raise PreparedRunReconstructionError("PREPARED_RUN_NOT_PREPARED")
    if not _is_valid_prepared_sha256(run.preparation_sha256):
        raise PreparedRunReconstructionError("PREPARED_RUN_NOT_PREPARED")
    return run.project_id


def _load_project_root(project_roots: ProjectRootPort, project_id: str) -> str:
    try:
        raw_root = project_roots.project_root(project_id)
    except Exception as exc:
        raise PreparedRunReconstructionError(
            "PREPARED_RUN_PROJECT_UNAVAILABLE"
        ) from exc
    return _require_project_root(raw_root)


def _resolve_durable_root(project_root: str) -> str:
    try:
        return str(Path(project_root).resolve(strict=False))
    except Exception as exc:
        raise PreparedRunReconstructionError(
            "PREPARED_RUN_PROJECT_UNAVAILABLE"
        ) from exc


def _require_current_identity(
    artifact_digests: ArtifactDigestPort,
    *,
    project_root: str,
    ref: str,
    durable_sha256: str,
    unavailable_code: str,
    mismatch_code: str,
) -> None:
    try:
        current = artifact_digests.current_digest(project_root, ref)
    except Exception as exc:
        raise PreparedRunReconstructionError(unavailable_code) from exc
    if not isinstance(current, str) or not current:
        raise PreparedRunReconstructionError(unavailable_code)
    if current != durable_sha256:
        raise PreparedRunReconstructionError(mismatch_code)


def _resolve_packet_path(project_root: str, packet_ref: str) -> str:
    """Contain path-resolution failure at its boundary (R2-F2)."""
    try:
        return str((Path(project_root) / packet_ref).resolve(strict=False))
    except Exception as exc:
        raise PreparedRunReconstructionError(
            "PREPARED_RUN_PACKET_UNAVAILABLE"
        ) from exc


def reconstruct_prepared_activation_request(
    *,
    run_store: PreparedRunStorePort,
    project_roots: ProjectRootPort,
    artifact_digests: ArtifactDigestPort,
    graph_id: str,
    run_id: str,
    node_id: str,
) -> RuntimeActivationRequest:
    """Reconstruct the existing activation request for one prepared run.

    Read-only composition: exactly one ``load_graph_run`` read, exactly one
    ``load_graph_run_bindings`` read, plus one resolved project-root
    observation and two current contract/packet digest observations bound
    to that resolved durable project root. No store writes, no "latest"
    selection, no dispatch, no recovery into a new run.
    """
    graph_id = _require_identity_text(graph_id)
    run_id = _require_identity_text(run_id)
    node_id = _require_identity_text(node_id)

    run = _load_run(run_store, run_id)
    if not isinstance(run, GraphRunRecord) or run.run_id != run_id:
        raise PreparedRunReconstructionError("PREPARED_RUN_RECORD_INVALID")
    if run.graph_id != graph_id:
        raise PreparedRunReconstructionError("PREPARED_RUN_IDENTITY_MISMATCH")
    project_id = _require_prepared_identity(run)

    project_root = _load_project_root(project_roots, project_id)
    resolved_root = _resolve_durable_root(project_root)

    bindings = _load_bindings(run_store, run_id)
    selected: list[GraphRunBindingRecord] = []
    for record in bindings:
        if not isinstance(record, GraphRunBindingRecord) or record.run_id != run_id:
            raise PreparedRunReconstructionError("PREPARED_RUN_BINDING_RECORD_INVALID")
        if record.node_id == node_id:
            selected.append(record)
    if not selected:
        raise PreparedRunReconstructionError("PREPARED_RUN_NODE_NOT_BOUND")
    if len(selected) > 1:
        raise PreparedRunReconstructionError("PREPARED_RUN_NODE_BINDING_AMBIGUOUS")
    binding = selected[0]

    if _require_reconstruction_text(binding.node_id) != node_id:
        raise PreparedRunReconstructionError("PREPARED_RUN_BINDING_RECORD_INVALID")
    runtime_kind = _require_reconstruction_text(binding.runtime_kind)
    if runtime_kind != _ACCEPTED_RUNTIME_KIND:
        raise PreparedRunReconstructionError("PREPARED_RUN_RUNTIME_KIND_UNAUTHORIZED")
    contract_ref = _require_project_relative_ref(binding.task_contract_ref)
    contract_sha256 = _require_sha256(binding.task_contract_sha256)
    packet_ref = _require_project_relative_ref(binding.task_packet_ref)
    packet_sha256 = _require_sha256(binding.task_packet_sha256)
    provider_id = _require_reconstruction_text(binding.provider_id)
    model_id = _require_reconstruction_text(binding.model_id)
    effort_level = _require_reconstruction_text(binding.effort_level)

    _require_current_identity(
        artifact_digests,
        project_root=resolved_root,
        ref=contract_ref,
        durable_sha256=contract_sha256,
        unavailable_code="PREPARED_RUN_CONTRACT_UNAVAILABLE",
        mismatch_code="PREPARED_RUN_CONTRACT_DIGEST_MISMATCH",
    )
    _require_current_identity(
        artifact_digests,
        project_root=resolved_root,
        ref=packet_ref,
        durable_sha256=packet_sha256,
        unavailable_code="PREPARED_RUN_PACKET_UNAVAILABLE",
        mismatch_code="PREPARED_RUN_PACKET_DIGEST_MISMATCH",
    )

    return RuntimeActivationRequest(
        graph_id=run.graph_id,
        graph_run_id=run.run_id,
        node_id=node_id,
        runtime_kind=runtime_kind,
        project_root=resolved_root,
        task_contract_ref=contract_ref,
        task_packet_path=_resolve_packet_path(resolved_root, packet_ref),
        provider_id=provider_id,
        model_id=model_id,
        effort_level=effort_level,
    )
