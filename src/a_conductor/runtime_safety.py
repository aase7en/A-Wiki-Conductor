"""Pure runtime ownership and collision classification.

No function in this module performs process, network, filesystem, tunnel, or
runtime-engine I/O. The caller supplies observations; these functions only
classify them according to the runtime-manager contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProcessOwnership(str, Enum):
    ABSENT = "ABSENT"
    OWNED = "OWNED"
    STALE = "STALE"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class PortBindingState(str, Enum):
    FREE = "FREE"
    OWNED = "OWNED"
    COLLISION = "COLLISION"
    UNKNOWN = "UNKNOWN"


class TunnelBindingState(str, Enum):
    FREE = "FREE"
    OWNED = "OWNED"
    COLLISION = "COLLISION"


class WorktreeBindingState(str, Enum):
    AVAILABLE = "AVAILABLE"
    OWNED = "OWNED"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True, slots=True)
class ProcessObservation:
    """Observed facts used to classify process ownership.

    ``None`` means the caller could not establish that fact. The classifier
    never reaches outside this value to discover missing information.
    """

    pid_metadata_present: bool
    pid: int | None
    process_exists: bool | None
    executable_matches: bool | None
    profile_matches: bool | None


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value


def classify_process_ownership(observation: ProcessObservation) -> ProcessOwnership:
    if not observation.pid_metadata_present:
        return ProcessOwnership.ABSENT

    if observation.pid is None or observation.pid <= 0:
        return ProcessOwnership.MISMATCH

    if observation.process_exists is False:
        return ProcessOwnership.STALE

    if observation.process_exists is None:
        return ProcessOwnership.UNKNOWN

    if observation.executable_matches is False or observation.profile_matches is False:
        return ProcessOwnership.MISMATCH

    if observation.executable_matches is None or observation.profile_matches is None:
        return ProcessOwnership.UNKNOWN

    return ProcessOwnership.OWNED


def classify_port_binding(
    *,
    listening: bool | None,
    owning_pid: int | None,
    expected_pid: int | None,
) -> PortBindingState:
    if listening is False:
        return PortBindingState.FREE

    if listening is None:
        return PortBindingState.UNKNOWN

    if owning_pid is None or owning_pid <= 0:
        return PortBindingState.UNKNOWN

    if expected_pid is not None and expected_pid > 0 and owning_pid == expected_pid:
        return PortBindingState.OWNED

    return PortBindingState.COLLISION


def classify_tunnel_binding(
    *,
    binding_ref: str,
    active_owner_worker_id: str | None,
    requesting_worker_id: str,
) -> TunnelBindingState:
    _require_text(binding_ref, "binding_ref")
    _require_text(requesting_worker_id, "requesting_worker_id")

    if active_owner_worker_id is None:
        return TunnelBindingState.FREE

    _require_text(active_owner_worker_id, "active_owner_worker_id")
    if active_owner_worker_id == requesting_worker_id:
        return TunnelBindingState.OWNED

    return TunnelBindingState.COLLISION


def classify_worktree_binding(
    *,
    worktree_key: str,
    active_mutating_worker_id: str | None,
    requesting_worker_id: str,
) -> WorktreeBindingState:
    _require_text(worktree_key, "worktree_key")
    _require_text(requesting_worker_id, "requesting_worker_id")

    if active_mutating_worker_id is None:
        return WorktreeBindingState.AVAILABLE

    _require_text(active_mutating_worker_id, "active_mutating_worker_id")
    if active_mutating_worker_id == requesting_worker_id:
        return WorktreeBindingState.OWNED

    return WorktreeBindingState.CONFLICT
