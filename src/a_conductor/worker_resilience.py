"""Worker / MCP transport resilience state machine (WO-P1-156).

Encodes the incident-proven health/recovery policy of the SunDay Worker
fleet: independent per-layer health signals, one derived state per worker,
restart-scoped recovery actions (a transport failure never restarts a local
worker), anti-flap circuits with stable-window reset, bounded restart
budgets, exact process identity (PID reuse rejection), and durable recovery
state that carries no secret values.

This module is a pure policy/state layer. It owns no scheduler, worker
registry, lease system, or process-control authority: callers execute the
returned actions through the existing instance lifecycle seams.
"""

from __future__ import annotations

import json
import os
import random
import re
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from .claude_code_harness import _redact_text

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_CREDENTIAL_TEXT_RE = re.compile(
    r"(?i)(?:authorization\s*[:=]|bearer\s+[A-Za-z0-9._~+/=-]{12,}|"
    r"cookie\s*[:=]|set-cookie\s*[:=]|"
    r"(?:api[_ -]?key|access[_ -]?key(?:[_ -]?id)?|access[_ -]?token|refresh[_ -]?token|"
    r"client[_ -]?secret|private[_ -]?key|password|passwd|passphrase|secret|token|auth|credential)"
    r"\s*[:=]\s*[^\s]{4,}|"
    r"sk-ant-[A-Za-z0-9_-]{8,}|sk-(?:proj-|live-|test-)?[A-Za-z0-9_]{16,}|"
    r"gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{12,}|"
    r"ya29\.[A-Za-z0-9._-]{8,}|xox[baprs]-[A-Za-z0-9-]{8,}|"
    r"[A-Za-z][A-Za-z0-9+.-]*://[^\s/:@]+:[^\s/@]+@)"
)
_TRANSPORT_EVIDENCE_RE = re.compile(
    r"(?i)(?:TUNNEL_START_FAILED|TUNNEL_[A-Z_]*|REMOTE_SESSION[A-Z_]*|"
    r"RATE_LIMIT|ENDPOINT_MISSING|HTTP 429|HTTP 404|SESSION_TERMINATED)"
)
_MAX_STORE_EVENTS = 256


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


class RecoveryAction(str, Enum):
    NONE = "NONE"
    REPROBE = "REPROBE"
    BACKOFF_WAIT = "BACKOFF_WAIT"
    RECONCILE_ENDPOINT = "RECONCILE_ENDPOINT"
    RECONNECT_SESSION = "RECONNECT_SESSION"
    RESTART_TUNNEL = "RESTART_TUNNEL"
    RESTART_COMPONENT = "RESTART_COMPONENT"
    RESTART_FROM_SPEC = "RESTART_FROM_SPEC"
    AWAIT_OPERATOR = "AWAIT_OPERATOR"
    QUARANTINE = "QUARANTINE"


class CircuitStatus(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass(frozen=True, slots=True)
class WorkerHealthProbes:
    """One independent probe per layer; None means unknown, never guessed."""

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


@dataclass(frozen=True, slots=True)
class RestartBudget:
    limit: int
    used: int = 0

    def __post_init__(self) -> None:
        if (
            isinstance(self.limit, bool)
            or not isinstance(self.limit, int)
            or self.limit < 1
        ):
            raise ValueError("limit must be a positive integer")
        if isinstance(self.used, bool) or not isinstance(self.used, int) or self.used < 0:
            raise ValueError("used must be non-negative")

    @property
    def available(self) -> bool:
        return self.used < self.limit


def recovery_action(
    state: WorkerDerivedState,
    *,
    circuit: "WorkerCircuit",
    budget: RestartBudget,
    durable_launch_spec: bool = False,
    gate: "RepositoryGate | None" = None,
) -> RecoveryAction:
    if not isinstance(state, WorkerDerivedState):
        raise ValueError("state must be WorkerDerivedState")
    if not isinstance(circuit, WorkerCircuit):
        raise ValueError("circuit must be WorkerCircuit")
    if not isinstance(budget, RestartBudget):
        raise ValueError("budget must be RestartBudget")
    if gate is not None and not isinstance(gate, RepositoryGate):
        raise ValueError("gate must be RepositoryGate")
    if circuit.status is CircuitStatus.OPEN:
        return RecoveryAction.QUARANTINE
    if state is WorkerDerivedState.QUARANTINED:
        return RecoveryAction.QUARANTINE
    if state is WorkerDerivedState.HEALTHY:
        return RecoveryAction.NONE
    if state is WorkerDerivedState.SUSPECT:
        return RecoveryAction.REPROBE
    if state is WorkerDerivedState.RATE_LIMITED:
        return RecoveryAction.BACKOFF_WAIT
    if state is WorkerDerivedState.ENDPOINT_MISSING:
        return RecoveryAction.RECONCILE_ENDPOINT
    if state is WorkerDerivedState.REMOTE_SESSION_STALE:
        return RecoveryAction.RECONNECT_SESSION
    if state is WorkerDerivedState.TUNNEL_DOWN:
        return RecoveryAction.RESTART_TUNNEL
    if gate is not None and not gate.mutation_permitted:
        # Unknown/unsafe dirty state or ownership blocks every restart or
        # reassignment of the local worker, independent of budget/spec.
        if state in (WorkerDerivedState.MCP_DOWN, WorkerDerivedState.PROCESS_DOWN):
            return RecoveryAction.AWAIT_OPERATOR
    if state is WorkerDerivedState.MCP_DOWN:
        return RecoveryAction.RESTART_COMPONENT
    if state is WorkerDerivedState.PROCESS_DOWN:
        if not budget.available:
            return RecoveryAction.QUARANTINE
        if not durable_launch_spec:
            return RecoveryAction.AWAIT_OPERATOR
        return RecoveryAction.RESTART_FROM_SPEC
    return RecoveryAction.AWAIT_OPERATOR


@dataclass(frozen=True, slots=True)
class BackoffSchedule:
    base_seconds: float
    cap_seconds: float
    jitter_fraction: float = 0.0

    def __post_init__(self) -> None:
        for name in ("base_seconds", "cap_seconds"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
                raise ValueError(f"{name} must be positive")
        if (
            isinstance(self.jitter_fraction, bool)
            or not isinstance(self.jitter_fraction, (int, float))
            or not 0 <= self.jitter_fraction < 1
        ):
            raise ValueError("jitter_fraction must be within [0, 1)")

    def delay_seconds(
        self, *, attempt: int, retry_after_seconds: float | None = None
    ) -> float:
        if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 0:
            raise ValueError("attempt must be non-negative")
        if retry_after_seconds is not None:
            if (
                isinstance(retry_after_seconds, bool)
                or not isinstance(retry_after_seconds, (int, float))
                or retry_after_seconds < 0
            ):
                raise ValueError("retry_after_seconds must be non-negative")
            return min(float(retry_after_seconds), self.cap_seconds)
        raw = float(self.base_seconds) * (2 ** min(attempt, 62))
        delay = min(raw, float(self.cap_seconds))
        if self.jitter_fraction > 0:
            factor = 1.0 + random.uniform(-self.jitter_fraction, self.jitter_fraction)
            delay = min(delay * factor, float(self.cap_seconds))
        return delay


class WorkerCircuit:
    """Anti-flap circuit: open on threshold, half-open after cooldown,
    closed only after a stable healthy window inside half-open."""

    def __init__(
        self,
        *,
        failure_threshold: int,
        cooldown_seconds: float,
        stable_window_seconds: float,
    ) -> None:
        if (
            isinstance(failure_threshold, bool)
            or not isinstance(failure_threshold, int)
            or failure_threshold < 1
        ):
            raise ValueError("failure_threshold must be positive")
        for name in ("cooldown_seconds", "stable_window_seconds"):
            value = locals()[name]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                raise ValueError(f"{name} must be non-negative")
        self._failure_threshold = failure_threshold
        self._cooldown = float(cooldown_seconds)
        self._stable_window = float(stable_window_seconds)
        self._status = CircuitStatus.CLOSED
        self._failures = 0
        self._opened_at: datetime | None = None
        self._stable_since: datetime | None = None

    @property
    def status(self) -> CircuitStatus:
        return self._status

    @property
    def failures(self) -> int:
        return self._failures

    def _as_utc(self, now: datetime) -> datetime:
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        return now.astimezone(timezone.utc)

    def record_failure(self, *, now: datetime) -> CircuitStatus:
        current = self._as_utc(now)
        if self._status is CircuitStatus.HALF_OPEN:
            self._status = CircuitStatus.OPEN
            self._opened_at = current
            self._stable_since = None
            self._failures = 1
            return self._status
        self._failures += 1
        self._stable_since = None
        if self._failures >= self._failure_threshold:
            self._status = CircuitStatus.OPEN
            self._opened_at = current
        return self._status

    def record_probe_success(self, *, now: datetime) -> CircuitStatus:
        current = self._as_utc(now)
        self.status_after(now=current)
        if self._status is CircuitStatus.OPEN:
            return self._status
        if self._status is CircuitStatus.HALF_OPEN:
            if self._stable_since is None:
                self._stable_since = current
            return self._status
        self._failures = 0
        return self._status

    def status_after(self, *, now: datetime) -> CircuitStatus:
        current = self._as_utc(now)
        if self._status is CircuitStatus.OPEN and self._opened_at is not None:
            if (current - self._opened_at).total_seconds() >= self._cooldown:
                self._status = CircuitStatus.HALF_OPEN
                self._stable_since = None
        if self._status is CircuitStatus.HALF_OPEN and self._stable_since is not None:
            if (current - self._stable_since).total_seconds() >= self._stable_window:
                self._status = CircuitStatus.CLOSED
                self._failures = 0
                self._stable_since = None
        return self._status


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


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.astimezone(timezone.utc).isoformat()


def _parse_iso(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("timestamp is invalid")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class WorkerRecoveryState:
    worker_id: str
    launch_spec_fingerprint: str
    identity: WorkerProcessIdentity
    endpoint_ref: str
    tunnel_ref: str
    project: str | None
    worktree: str | None
    branch: str | None
    head: str | None
    active_task: str | None
    claim_ref: str | None
    last_healthy_at: datetime | None
    failure_layer: str | None
    failure_reason: str | None
    recovery_attempts: int
    circuit_state: str
    last_execution_identity: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.worker_id, str) or not self.worker_id.strip():
            raise ValueError("worker_id is invalid")
        if not isinstance(self.launch_spec_fingerprint, str) or not self.launch_spec_fingerprint:
            raise ValueError("launch_spec_fingerprint is invalid")
        if not isinstance(self.identity, WorkerProcessIdentity):
            raise ValueError("identity must be WorkerProcessIdentity")
        for name in ("endpoint_ref", "tunnel_ref"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} is invalid")
        if isinstance(self.recovery_attempts, bool) or not isinstance(
            self.recovery_attempts, int
        ) or self.recovery_attempts < 0:
            raise ValueError("recovery_attempts must be non-negative")
        if not isinstance(self.circuit_state, str) or not self.circuit_state.strip():
            raise ValueError("circuit_state is invalid")

    def as_dict(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "launch_spec_fingerprint": self.launch_spec_fingerprint,
            "identity": {
                "pid": self.identity.pid,
                "process_start_epoch": self.identity.process_start_epoch,
                "executable": self.identity.executable,
                "command_sha256": self.identity.command_sha256,
            },
            "endpoint_ref": self.endpoint_ref,
            "tunnel_ref": self.tunnel_ref,
            "project": self.project,
            "worktree": self.worktree,
            "branch": self.branch,
            "head": self.head,
            "active_task": self.active_task,
            "claim_ref": self.claim_ref,
            "last_healthy_at": _iso(self.last_healthy_at),
            "failure_layer": self.failure_layer,
            "failure_reason": self.failure_reason,
            "recovery_attempts": self.recovery_attempts,
            "circuit_state": self.circuit_state,
            "last_execution_identity": self.last_execution_identity,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkerRecoveryState":
        if not isinstance(data, dict):
            raise ValueError("state payload must be a mapping")
        identity = WorkerProcessIdentity(**data["identity"])
        return cls(
            worker_id=data["worker_id"],
            launch_spec_fingerprint=data["launch_spec_fingerprint"],
            identity=identity,
            endpoint_ref=data["endpoint_ref"],
            tunnel_ref=data["tunnel_ref"],
            project=data.get("project"),
            worktree=data.get("worktree"),
            branch=data.get("branch"),
            head=data.get("head"),
            active_task=data.get("active_task"),
            claim_ref=data.get("claim_ref"),
            last_healthy_at=_parse_iso(data.get("last_healthy_at")),
            failure_layer=data.get("failure_layer"),
            failure_reason=data.get("failure_reason"),
            recovery_attempts=data["recovery_attempts"],
            circuit_state=data["circuit_state"],
            last_execution_identity=data.get("last_execution_identity"),
        )


class WorkerRecoveryStore:
    """Durable recovery-state persistence; JSON, atomic, secret-free by contract.

    Concurrency boundary (explicit): same-process concurrent upserts and event
    records on one path are serialized through a per-path lock and unique
    temporary files, so parallel in-process recoveries are lossless. There is
    NO cross-process locking: exactly one Conductor process may own a store
    path. A second process mutating the same file is an ownership violation
    outside this store's authority.
    """

    def __init__(self, path: Path | str, *, max_events: int = _MAX_STORE_EVENTS) -> None:
        self._path = Path(path)
        self._max_events = max_events
        self._lock = _store_lock(self._path)

    # -- raw payload helpers (callers hold the lock) --
    def _read_raw(self) -> dict[str, Any]:
        if not self._path.is_file():
            return {"workers": {}, "events": {}}
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("recovery store payload is invalid")
        raw.setdefault("workers", {})
        raw.setdefault("events", {})
        return raw

    def _write_raw(self, payload: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        handle, temp_name = tempfile.mkstemp(
            dir=str(self._path.parent), prefix=self._path.name + ".", suffix=".tmp"
        )
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, indent=2, sort_keys=True)
                stream.flush()
            os.replace(temp_name, self._path)
        except BaseException:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise

    def upsert(
        self,
        state: WorkerRecoveryState,
        *,
        redaction_values: tuple[str, ...] = (),
    ) -> None:
        """Persist one worker's state, sanitized at this boundary: credential
        shapes and supplied secret values never reach the file."""
        if not isinstance(state, WorkerRecoveryState):
            raise ValueError("state must be WorkerRecoveryState")
        safe = sanitize_worker_recovery_state(state, redaction_values)
        with self._lock:
            payload = self._read_raw()
            payload["workers"][safe.worker_id] = safe.as_dict()
            self._write_raw(payload)

    def load(self) -> dict[str, WorkerRecoveryState]:
        with self._lock:
            payload = self._read_raw()
        workers = payload["workers"]
        if not isinstance(workers, dict):
            raise ValueError("recovery store payload is invalid")
        return {
            key: WorkerRecoveryState.from_dict(value)
            for key, value in workers.items()
        }

    def record_event(self, worker_id: str, event_id: str, *, now: datetime) -> bool:
        """Durably idempotent recovery event: True only on first sight, across
        process restarts, with bounded retention (oldest events dropped)."""
        if not isinstance(worker_id, str) or not worker_id.strip():
            raise ValueError("worker_id is invalid")
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("event_id is invalid")
        stamp = _iso(_parse_iso(now.isoformat()))
        with self._lock:
            payload = self._read_raw()
            events: dict[str, dict[str, str]] = payload["events"]
            worker_events = events.setdefault(worker_id, {})
            if event_id in worker_events:
                return False
            worker_events[event_id] = stamp or ""
            flat = [
                (worker, event, when)
                for worker, by_event in events.items()
                for event, when in by_event.items()
            ]
            if len(flat) > self._max_events:
                flat.sort(key=lambda item: item[2])
                for worker, event, _ in flat[: len(flat) - self._max_events]:
                    events[worker].pop(event, None)
                    if not events[worker]:
                        events.pop(worker, None)
            self._write_raw(payload)
        return True


_STORE_LOCKS: dict[str, threading.Lock] = {}
_STORE_LOCKS_GUARD = threading.Lock()


def _store_lock(path: Path) -> threading.Lock:
    key = str(path).casefold()
    with _STORE_LOCKS_GUARD:
        return _STORE_LOCKS.setdefault(key, threading.Lock())


_FREE_TEXT_FIELDS = (
    "endpoint_ref",
    "tunnel_ref",
    "project",
    "worktree",
    "branch",
    "active_task",
    "claim_ref",
    "failure_layer",
    "failure_reason",
    "last_execution_identity",
)


def _sanitize_free_text(value: object, redaction_values: tuple[str, ...]) -> object:
    if not isinstance(value, str) or not value:
        return value
    text = _redact_text(value, tuple(v for v in redaction_values if v))
    if _CREDENTIAL_TEXT_RE.search(text):
        return "[REDACTED]"
    return text


def sanitize_worker_recovery_state(
    state: WorkerRecoveryState,
    redaction_values: tuple[str, ...] = (),
) -> WorkerRecoveryState:
    """Return a persistence-safe copy: known secret values are redacted and
    any credential-bearing free-text field is neutralized wholesale."""
    if not isinstance(state, WorkerRecoveryState):
        raise ValueError("state must be WorkerRecoveryState")
    changes = {
        name: _sanitize_free_text(getattr(state, name), redaction_values)
        for name in _FREE_TEXT_FIELDS
    }
    from dataclasses import replace
    return replace(state, **changes)



@dataclass(frozen=True, slots=True)
class RepositoryGate:
    """Per-worker repository/ownership gate: mutation is permitted only when
    the dirty state is known AND safe AND ownership/task state is known-safe."""

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
    """A recovered worker may accept work only when it is HEALTHY and the
    repository/ownership gate permits mutation (Phase E availability rule)."""
    if not isinstance(state, WorkerDerivedState):
        raise ValueError("state must be WorkerDerivedState")
    if not isinstance(gate, RepositoryGate):
        raise ValueError("gate must be RepositoryGate")
    return state is WorkerDerivedState.HEALTHY and gate.mutation_permitted


def plan_parallel_recovery(
    states_by_worker,
    *,
    circuit_by_worker,
    budget_by_worker,
    durable_spec_by_worker=None,
    gates_by_worker=None,
):
    """Plan one bounded action per worker independently and deterministically.

    No cross-worker interference: every input worker receives exactly one
    action and planning is a pure function of its inputs (replay-stable).
    A worker missing its circuit or budget is a hard input error, never a
    silent skip, so independent recoveries cannot collide through omissions.
    """
    if not isinstance(states_by_worker, dict) or not states_by_worker:
        raise ValueError("states_by_worker must be a non-empty mapping")
    specs = durable_spec_by_worker or {}
    gates = gates_by_worker or {}
    plan = {}
    for worker, state in states_by_worker.items():
        circuit = circuit_by_worker.get(worker)
        if not isinstance(circuit, WorkerCircuit):
            raise ValueError(f"circuit missing for worker {worker!r}")
        budget = budget_by_worker.get(worker)
        if not isinstance(budget, RestartBudget):
            raise ValueError(f"budget missing for worker {worker!r}")
        plan[worker] = recovery_action(
            state,
            circuit=circuit,
            budget=budget,
            durable_launch_spec=bool(specs.get(worker, False)),
            gate=gates.get(worker),
        )
    return plan


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

    A fleet outage exists when at least `min_affected` workers show a
    transport-layer failure simultaneously (same probe round) — detected by
    the monitoring loop before any operator notices missing surfaces. With
    `transport_only`, only shared-transport layers (tunnel / remote session)
    count; rate limits and endpoint misses are excluded.

    Post-amplification support: the WO156 wrapper tears the whole instance
    down when a tunnel exits, so the probe round AFTER an outage may see
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
