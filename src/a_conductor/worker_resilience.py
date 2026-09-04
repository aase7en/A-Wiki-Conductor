"""Worker / MCP transport resilience policy layer (WO-P1-156).

Pure policy over the ONE durable recovery authority
(`ConnectorRecoveryCoordinator` + `ConnectorRecoveryStore` /
`SQLiteSerenaConfigStore.instance_recovery`). This module owns NO durable
state, NO restart loop, NO backoff/circuit authority and NO process control:
it classifies per-layer health into one derived worker state, maps that to a
coordinator disposition (health literal + closed-set reason code + restart
permission), correlates shared-transport outages (including the
post-amplification observation), gates worker availability on
repository/ownership evidence, and verifies exact process identity.

The existing coordinator owns bounded retries, backoff, DEGRADED state,
manual-stop suppression and durable records. Reason codes are drawn from a
closed set so no credential-bearing diagnostic text is ever persisted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_TRANSPORT_EVIDENCE_RE = re.compile(
    r"(?i)(?:TUNNEL_START_FAILED|TUNNEL_[A-Z_]*|REMOTE_SESSION[A-Z_]*|"
    r"RATE_LIMIT|ENDPOINT_MISSING|HTTP 429|HTTP 404|SESSION_TERMINATED)"
)


class WorkerDerivedState(str, Enum):
    HEALTHY = "HEALTHY"
    SUSPECT = "SUSPECT"
    PROCESS_DOWN = "PROCESS_DOWN"
    MCP_DOWN = "MCP_DOWN"
    TUNNEL_DOWN = "TUNNEL_DOWN"
    REMOTE_SESSION_STALE = "REMOTE_SESSION_STALE"
    RATE_LIMITED = "RATE_LIMITED"
    ENDPOINT_MISSING = "ENDPOINT_MISSING"
    OWNERSHIP_BLOCKED = "OWNERSHIP_BLOCKED"
    TASK_AMBIGUOUS = "TASK_AMBIGUOUS"
    QUARANTINED = "QUARANTINED"


@dataclass(frozen=True, slots=True)
class WorkerHealthProbes:
    """One independent probe per layer; absence of a signal is never guessed."""

    process_alive: bool
    mcp_ready: bool
    tunnel_reachable: bool
    remote_session_ready: bool
    ownership_safe: bool
    task_state_known: bool
    remote_http_status: int | None = None


def classify_worker(
    probes: WorkerHealthProbes,
    *,
    first_failure_seen: bool,
    quarantined: bool = False,
) -> WorkerDerivedState:
    if not isinstance(probes, WorkerHealthProbes):
        raise ValueError("probes must be WorkerHealthProbes")
    if quarantined:
        return WorkerDerivedState.QUARANTINED
    if not probes.process_alive:
        return WorkerDerivedState.PROCESS_DOWN
    if first_failure_seen:
        return WorkerDerivedState.SUSPECT
    if not probes.mcp_ready:
        return WorkerDerivedState.MCP_DOWN
    if probes.remote_http_status == 429:
        return WorkerDerivedState.RATE_LIMITED
    if probes.remote_http_status == 404:
        return WorkerDerivedState.ENDPOINT_MISSING
    if not probes.tunnel_reachable:
        return WorkerDerivedState.TUNNEL_DOWN
    if not probes.remote_session_ready:
        return WorkerDerivedState.REMOTE_SESSION_STALE
    if not probes.ownership_safe:
        return WorkerDerivedState.OWNERSHIP_BLOCKED
    if not probes.task_state_known:
        return WorkerDerivedState.TASK_AMBIGUOUS
    return WorkerDerivedState.HEALTHY


# ---------------- coordinator bridge (single recovery authority) ----------------

# The coordinator restarts an instance only when it observes non-READY
# health, so dispositions that must never restart a live process report
# READY with a recorded reason instead.
class DispositionHealth(str, Enum):
    READY = "READY"
    UNEXPECTED_STOPPED = "UNEXPECTED_STOPPED"


# Closed set of reason codes; nothing else may reach durable state.
REASON_CODES = frozenset({
    "HEALTHY",
    "SUSPECT_REPROBE",
    "RATE_LIMITED_BACKOFF",
    "ENDPOINT_RECONCILE",
    "REMOTE_SESSION_RECONNECT",
    "TRANSPORT_DOWN",
    "MCP_DOWN",
    "UNEXPECTED_STOPPED",
    "OWNERSHIP_HOLD",
    "TASK_AMBIGUOUS_HOLD",
    "QUARANTINED_HOLD",
})


@dataclass(frozen=True, slots=True)
class CoordinatorDisposition:
    health: DispositionHealth
    reason_code: str
    restart_permitted: bool
    suppress_recovery: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.health, DispositionHealth):
            raise ValueError("health is invalid")
        if self.reason_code not in REASON_CODES:
            raise ValueError("reason_code is not from the closed set")
        if not isinstance(self.restart_permitted, bool) or not isinstance(
            self.suppress_recovery, bool
        ):
            raise ValueError("flags must be bool")


def coordinator_disposition(state: WorkerDerivedState) -> CoordinatorDisposition:
    """Map one derived worker state onto the single recovery authority.

    429/404/stale-session dispositions never restart the local process; a
    tunnel/MCP/process death reports UNEXPECTED_STOPPED so the coordinator
    performs exactly one bounded recovery (its own backoff/limits govern);
    ownership/task ambiguity suppresses automatic recovery entirely.
    """
    if not isinstance(state, WorkerDerivedState):
        raise ValueError("state must be WorkerDerivedState")
    if state is WorkerDerivedState.HEALTHY:
        return CoordinatorDisposition(DispositionHealth.READY, "HEALTHY", False)
    if state is WorkerDerivedState.SUSPECT:
        return CoordinatorDisposition(DispositionHealth.READY, "SUSPECT_REPROBE", False)
    if state is WorkerDerivedState.RATE_LIMITED:
        return CoordinatorDisposition(DispositionHealth.READY, "RATE_LIMITED_BACKOFF", False)
    if state is WorkerDerivedState.ENDPOINT_MISSING:
        return CoordinatorDisposition(DispositionHealth.READY, "ENDPOINT_RECONCILE", False)
    if state is WorkerDerivedState.REMOTE_SESSION_STALE:
        return CoordinatorDisposition(
            DispositionHealth.READY, "REMOTE_SESSION_RECONNECT", False
        )
    if state is WorkerDerivedState.TUNNEL_DOWN:
        return CoordinatorDisposition(
            DispositionHealth.UNEXPECTED_STOPPED, "TRANSPORT_DOWN", True
        )
    if state is WorkerDerivedState.MCP_DOWN:
        return CoordinatorDisposition(
            DispositionHealth.UNEXPECTED_STOPPED, "MCP_DOWN", True
        )
    if state is WorkerDerivedState.PROCESS_DOWN:
        return CoordinatorDisposition(
            DispositionHealth.UNEXPECTED_STOPPED, "UNEXPECTED_STOPPED", True
        )
    if state is WorkerDerivedState.OWNERSHIP_BLOCKED:
        return CoordinatorDisposition(
            DispositionHealth.READY, "OWNERSHIP_HOLD", False, suppress_recovery=True
        )
    if state is WorkerDerivedState.TASK_AMBIGUOUS:
        return CoordinatorDisposition(
            DispositionHealth.READY, "TASK_AMBIGUOUS_HOLD", False, suppress_recovery=True
        )
    return CoordinatorDisposition(
        DispositionHealth.READY, "QUARANTINED_HOLD", False, suppress_recovery=True
    )


def plan_parallel_recovery(states_by_worker: Mapping[str, WorkerDerivedState]):
    """One disposition per worker, independently and deterministically.

    Planning is a pure function of the input mapping: replay-stable, every
    input worker appears exactly once in the output, and ownership is
    enforced per worker by each disposition's suppress flag (never by
    plan-level arbitration), so parallel recoveries cannot collide.
    """
    if not isinstance(states_by_worker, dict) or not states_by_worker:
        raise ValueError("states_by_worker must be a non-empty mapping")
    return {
        worker: coordinator_disposition(state)
        for worker, state in states_by_worker.items()
    }


class ObservationDeduper:
    """Policy-layer flap guard: report only derived-state TRANSITIONS.

    A duplicate health observation of the same down-state (same failure
    epoch, no intervening recovery) is not re-reported to the recovery
    authority, so a duplicated probe never produces a duplicate restart.
    A genuine re-death always shows an intervening healthy observation and
    is therefore reported. Process-scoped by design; durable dedupe lives in
    the authority's records.
    """

    def __init__(self) -> None:
        self._previous: dict[str, WorkerDerivedState] = {}

    def should_report(self, worker: str, state: WorkerDerivedState) -> bool:
        if not isinstance(worker, str) or not worker.strip():
            raise ValueError("worker is invalid")
        if not isinstance(state, WorkerDerivedState):
            raise ValueError("state must be WorkerDerivedState")
        previous = self._previous.get(worker)
        self._previous[worker] = state
        return previous is None or previous is not state


# ---------------- repository / ownership availability gate ----------------

@dataclass(frozen=True, slots=True)
class RepositoryGate:
    """Mutation is permitted only when dirty state is known AND safe AND
    ownership/task state is known-safe (Phase E availability rule)."""

    dirty_state_known: bool
    dirty_safe: bool
    ownership_safe: bool
    task_state_known: bool

    @property
    def mutation_permitted(self) -> bool:
        return (
            self.dirty_state_known
            and self.dirty_safe
            and self.ownership_safe
            and self.task_state_known
        )


def worker_available_for_work(
    state: WorkerDerivedState, gate: RepositoryGate
) -> bool:
    if not isinstance(state, WorkerDerivedState):
        raise ValueError("state must be WorkerDerivedState")
    if not isinstance(gate, RepositoryGate):
        raise ValueError("gate must be RepositoryGate")
    return state is WorkerDerivedState.HEALTHY and gate.mutation_permitted


# ---------------- exact process identity ----------------

@dataclass(frozen=True, slots=True)
class WorkerProcessIdentity:
    pid: int
    process_start_epoch: float
    executable: str
    command_sha256: str

    def __post_init__(self) -> None:
        if isinstance(self.pid, bool) or not isinstance(self.pid, int) or self.pid < 1:
            raise ValueError("pid must be positive")
        if (
            isinstance(self.process_start_epoch, bool)
            or not isinstance(self.process_start_epoch, (int, float))
            or self.process_start_epoch <= 0
        ):
            raise ValueError("process_start_epoch must be positive")
        if not isinstance(self.executable, str) or not self.executable.strip():
            raise ValueError("executable is invalid")
        if not _SHA256_RE.fullmatch(self.command_sha256 or ""):
            raise ValueError("command_sha256 is invalid")

    def matches(self, other: "WorkerProcessIdentity") -> bool:
        if not isinstance(other, WorkerProcessIdentity):
            return False
        return (
            self.pid == other.pid
            and self.process_start_epoch == other.process_start_epoch
            and self.executable.casefold() == other.executable.casefold()
            and self.command_sha256.casefold() == other.command_sha256.casefold()
        )


# ---------------- shared-transport fleet correlation ----------------

_TRANSPORT_STATE_LAYERS = (
    (WorkerDerivedState.TUNNEL_DOWN, "TUNNEL"),
    (WorkerDerivedState.REMOTE_SESSION_STALE, "REMOTE_SESSION"),
    (WorkerDerivedState.RATE_LIMITED, "RATE_LIMIT"),
    (WorkerDerivedState.ENDPOINT_MISSING, "ENDPOINT"),
)
_SHARED_TRANSPORT_LAYERS = frozenset({"TUNNEL", "REMOTE_SESSION"})


@dataclass(frozen=True, slots=True)
class FleetOutageReport:
    affected_workers: tuple[str, ...]
    layers: tuple[str, ...]


def detect_fleet_outage(
    probes_by_worker,
    *,
    min_affected: int = 2,
    transport_only: bool = False,
    recent_failures_by_worker: Mapping[str, Sequence[str]] | None = None,
) -> FleetOutageReport | None:
    """Deterministically flag a shared-transport outage from ONE probe round.

    Post-amplification support: the wrapper tears the whole instance down
    when a tunnel exits, so the probe round AFTER an outage may see
    PROCESS_DOWN everywhere. A PROCESS_DOWN worker is attributed to the
    shared-transport outage (layer TRANSPORT_AMPLIFIED) only when its durable
    recent failure evidence names a transport-layer cause; simultaneous
    process deaths without such evidence are never called a network outage.
    """
    if not isinstance(probes_by_worker, dict) or not probes_by_worker:
        raise ValueError("probes_by_worker must be a non-empty mapping")
    if isinstance(min_affected, bool) or not isinstance(min_affected, int) or min_affected < 1:
        raise ValueError("min_affected must be positive")
    layer_by_state = dict(_TRANSPORT_STATE_LAYERS)
    recent = recent_failures_by_worker or {}
    affected: list[str] = []
    layers: list[str] = []
    for worker in sorted(probes_by_worker):
        probes = probes_by_worker[worker]
        if not isinstance(probes, WorkerHealthProbes):
            raise ValueError("probe payload must be WorkerHealthProbes")
        state = classify_worker(probes, first_failure_seen=False)
        layer = layer_by_state.get(state)
        if layer is None and state is WorkerDerivedState.PROCESS_DOWN:
            evidence = recent.get(worker) or ()
            if any(
                isinstance(item, str) and _TRANSPORT_EVIDENCE_RE.search(item)
                for item in evidence
            ):
                layer = "TRANSPORT_AMPLIFIED"
        if layer is None:
            continue
        if transport_only and layer not in _SHARED_TRANSPORT_LAYERS and layer != "TRANSPORT_AMPLIFIED":
            continue
        affected.append(worker)
        if layer not in layers:
            layers.append(layer)
    if len(affected) < min_affected:
        return None
    return FleetOutageReport(affected_workers=tuple(affected), layers=tuple(layers))
