"""Serena/MCP transport-event mapping onto the AC-RES-003 transport model.

Deterministic, I/O-free adapter: classification consumes structured events
that were already observed elsewhere; transport mutation flows exclusively
through ``ExecutionTransportService``; recovery decisions stay in
AC-RES-004. This module never retries, reconnects, fails over, or touches
processes, files, network, or Git.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol, Sequence

from .execution_record import DurableExecutionRecord, TransportState
from .recovery_reconciliation import RecoveryRepositoryObservation
from .serena_runtime import ProjectIdentityPolicy, SerenaProjectBinding
from .transport_recovery import ExecutionTransportService, TransportMutationOutcome


class SerenaTransportEventKind(str, Enum):
    MCP_HTTP_502 = "MCP_HTTP_502"
    MCP_HTTP_503 = "MCP_HTTP_503"
    MCP_HTTP_504 = "MCP_HTTP_504"
    CONNECTOR_SESSION_TERMINATED = "CONNECTOR_SESSION_TERMINATED"
    HEALTH_PROBE_TIMEOUT = "HEALTH_PROBE_TIMEOUT"
    HEALTH_PROBE_REFUSED = "HEALTH_PROBE_REFUSED"
    HEALTH_PROBE_INVALID = "HEALTH_PROBE_INVALID"
    MCP_OK = "MCP_OK"
    HEALTH_PROBE_OK = "HEALTH_PROBE_OK"


_MCP_HTTP_KINDS = frozenset(
    {
        SerenaTransportEventKind.MCP_HTTP_502,
        SerenaTransportEventKind.MCP_HTTP_503,
        SerenaTransportEventKind.MCP_HTTP_504,
    }
)
_PROBE_KINDS = frozenset(
    {
        SerenaTransportEventKind.HEALTH_PROBE_TIMEOUT,
        SerenaTransportEventKind.HEALTH_PROBE_REFUSED,
        SerenaTransportEventKind.HEALTH_PROBE_INVALID,
    }
)
_HEALTHY_KINDS = frozenset(
    {
        SerenaTransportEventKind.MCP_OK,
        SerenaTransportEventKind.HEALTH_PROBE_OK,
    }
)

_EVIDENCE_BY_KIND = {
    SerenaTransportEventKind.MCP_HTTP_502: "serena:mcp-502",
    SerenaTransportEventKind.MCP_HTTP_503: "serena:mcp-503",
    SerenaTransportEventKind.MCP_HTTP_504: "serena:mcp-504",
    SerenaTransportEventKind.CONNECTOR_SESSION_TERMINATED: "serena:session-terminated",
    SerenaTransportEventKind.HEALTH_PROBE_TIMEOUT: "serena:probe-timeout",
    SerenaTransportEventKind.HEALTH_PROBE_REFUSED: "serena:probe-refused",
    SerenaTransportEventKind.HEALTH_PROBE_INVALID: "serena:probe-invalid",
    SerenaTransportEventKind.MCP_OK: "serena:mcp-ok",
    SerenaTransportEventKind.HEALTH_PROBE_OK: "serena:probe-ok",
}


@dataclass(frozen=True, slots=True)
class SerenaTransportEvent:
    kind: SerenaTransportEventKind
    detail: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, SerenaTransportEventKind):
            raise ValueError("kind must be a SerenaTransportEventKind")
        if self.detail is not None and (
            not isinstance(self.detail, str) or not self.detail.strip() or "\x00" in self.detail
        ):
            raise ValueError("detail must be a non-blank string or None")


@dataclass(frozen=True, slots=True)
class SerenaTransportClassification:
    target_state: TransportState | None
    evidence_code: str | None
    consecutive_failures: int


def _require_positive_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{field_name} must be >= 1")
    return value


def classify_serena_transport_events(
    events: Sequence[SerenaTransportEvent],
    *,
    lost_after: int = 2,
    unavailable_after: int = 2,
) -> SerenaTransportClassification:
    """Classify an ordered event window into one transport-state target.

    The failure streak counts events from the end of the window backwards
    until the first healthy event; the family (MCP HTTP vs health probe) of
    the final failure selects the escalation target. A healthy final event
    reconnects; an empty window requests no mutation.
    """
    if isinstance(events, (str, bytes)) or not isinstance(events, Sequence):
        raise ValueError("events must be a sequence of SerenaTransportEvent")
    _require_positive_int(lost_after, "lost_after")
    _require_positive_int(unavailable_after, "unavailable_after")
    for index, event in enumerate(events):
        if not isinstance(event, SerenaTransportEvent):
            raise ValueError(f"events[{index}] must be a SerenaTransportEvent")

    streak = 0
    last_failure: SerenaTransportEvent | None = None
    for event in reversed(events):
        if event.kind in _HEALTHY_KINDS:
            break
        streak += 1
        last_failure = event

    if streak == 0:
        if not events:
            return SerenaTransportClassification(
                target_state=None,
                evidence_code=None,
                consecutive_failures=0,
            )
        return SerenaTransportClassification(
            target_state=TransportState.CONNECTED,
            evidence_code=_EVIDENCE_BY_KIND[events[-1].kind],
            consecutive_failures=0,
        )

    assert last_failure is not None
    evidence = _EVIDENCE_BY_KIND[last_failure.kind]
    if last_failure.kind is SerenaTransportEventKind.CONNECTOR_SESSION_TERMINATED:
        return SerenaTransportClassification(
            target_state=TransportState.LOST,
            evidence_code=evidence,
            consecutive_failures=streak,
        )
    if last_failure.kind in _PROBE_KINDS:
        target = (
            TransportState.UNAVAILABLE
            if streak >= unavailable_after
            else TransportState.DEGRADED
        )
    else:
        target = (
            TransportState.LOST
            if streak >= lost_after
            else TransportState.DEGRADED
        )
    return SerenaTransportClassification(
        target_state=target,
        evidence_code=evidence,
        consecutive_failures=streak,
    )


class _TransportMutationService(Protocol):
    def mark_connected(self, execution_id: str, *, expected_version: int, evidence_ref: str | None = None) -> TransportMutationOutcome: ...
    def mark_degraded(self, execution_id: str, *, expected_version: int, evidence_ref: str | None) -> TransportMutationOutcome: ...
    def mark_lost(self, execution_id: str, *, expected_version: int, evidence_ref: str | None) -> TransportMutationOutcome: ...
    def mark_unavailable(self, execution_id: str, *, expected_version: int, evidence_ref: str | None) -> TransportMutationOutcome: ...


class SerenaTransportAdapter:
    """Apply classified Serena transport events through the transport service."""

    def __init__(
        self,
        *,
        transport_service: _TransportMutationService,
        lost_after: int = 2,
        unavailable_after: int = 2,
    ) -> None:
        for method_name in ("mark_connected", "mark_degraded", "mark_lost", "mark_unavailable"):
            if not callable(getattr(transport_service, method_name, None)):
                raise ValueError(f"transport_service must provide {method_name}")
        self._transport_service = transport_service
        self._lost_after = _require_positive_int(lost_after, "lost_after")
        self._unavailable_after = _require_positive_int(unavailable_after, "unavailable_after")

    def apply(
        self,
        execution_id: str,
        events: Sequence[SerenaTransportEvent],
        *,
        expected_version: int,
    ) -> TransportMutationOutcome | None:
        if not isinstance(execution_id, str) or not execution_id.strip():
            raise ValueError("execution_id must not be blank")
        _require_positive_int(expected_version, "expected_version")
        classification = classify_serena_transport_events(
            events,
            lost_after=self._lost_after,
            unavailable_after=self._unavailable_after,
        )
        if classification.target_state is None:
            return None
        evidence = classification.evidence_code
        if classification.target_state is TransportState.CONNECTED:
            return self._transport_service.mark_connected(
                execution_id,
                expected_version=expected_version,
                evidence_ref=evidence,
            )
        if classification.target_state is TransportState.DEGRADED:
            return self._transport_service.mark_degraded(
                execution_id,
                expected_version=expected_version,
                evidence_ref=evidence,
            )
        if classification.target_state is TransportState.LOST:
            return self._transport_service.mark_lost(
                execution_id,
                expected_version=expected_version,
                evidence_ref=evidence,
            )
        return self._transport_service.mark_unavailable(
            execution_id,
            expected_version=expected_version,
            evidence_ref=evidence,
        )


class _RepositoryFactsObserver(Protocol):
    def observe(self, record: DurableExecutionRecord) -> RecoveryRepositoryObservation: ...


class SerenaProjectBindingRepositoryObserver:
    """Wrap read-only repository facts with Serena project-binding agreement."""

    def __init__(self, *, binding: SerenaProjectBinding, inner: _RepositoryFactsObserver) -> None:
        if not isinstance(binding, SerenaProjectBinding):
            raise ValueError("binding must be a SerenaProjectBinding")
        if not callable(getattr(inner, "observe", None)):
            raise ValueError("inner must provide observe()")
        self._binding = binding
        self._inner = inner

    def observe(self, record: DurableExecutionRecord) -> RecoveryRepositoryObservation:
        if not isinstance(record, DurableExecutionRecord):
            raise ValueError("record must be a DurableExecutionRecord")
        record_root = Path(record.repo_root).expanduser().resolve(strict=False)
        binding_root = Path(self._binding.worktree_path).expanduser().resolve(strict=False)
        if record_root != binding_root:
            return RecoveryRepositoryObservation(
                repo_root=str(record_root),
                branch=None,
                head=None,
                dirty=None,
                error_code="SERENA_BINDING_WORKTREE_MISMATCH",
            )

        observation = self._inner.observe(record)
        if not isinstance(observation, RecoveryRepositoryObservation):
            raise ValueError("inner observer must return a RecoveryRepositoryObservation")
        if observation.error_code is not None:
            return observation
        if self._binding.identity_policy is not ProjectIdentityPolicy.EXACT:
            return observation
        if (
            self._binding.expected_branch is not None
            and observation.branch != self._binding.expected_branch
        ) or (
            self._binding.expected_head is not None
            and observation.head != self._binding.expected_head
        ):
            return dataclasses.replace(
                observation,
                error_code="SERENA_BINDING_IDENTITY_MISMATCH",
            )
        return observation
