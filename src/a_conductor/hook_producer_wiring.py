"""WO-P1-592: bind the accepted lifecycle producer seam to the Hook Bus core.

STM-1B composition only. The producer seam is already accepted:
``SQLiteLifecycleEvidenceService`` takes optional ``hook_context_factory`` +
``hook_observe_sink`` collaborators (both-or-neither) and already isolates
every hook-path failure as ``OBSERVABILITY_DEGRADED`` so control truth never
changes. This module returns exactly that collaborator pair, wiring the sink
to one ``HookBus.accept`` per sanitized OBSERVE envelope.

Invariants (WO-P1-592 frozen contract):
- the sink never raises into the control path; admission outcomes
  (ACCEPTED / DUPLICATE / BACKPRESSURE / REJECTED / ERROR) are recorded in a
  bounded observability view only;
- identity is explicit per binding (device/source-version/host-os/session),
  never ambient inference;
- no persistence, scheduler, retry, network/process/Git side effects, no new
  authority: the bus/STM stay derived, bounded, rebuildable, and the durable
  ``SQLiteControlEventLog`` remains the only rebuild source.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable

from .control_hook_adapter import ControlHookContext
from .hook_bus import HookBus, HookIngressContext

__all__ = [
    "ProducerWiringError",
    "ProducerAdmission",
    "bind_control_event_producer",
]

_SOURCE = "a-conductor"
_DEVICE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_SOURCE_VERSION = re.compile(r"\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?")
_HOST_OS_VALUES = frozenset({"windows", "macos", "linux"})
_MAX_SESSION_CHARS = 256
_MAX_ADMISSIONS = 32


class ProducerWiringError(RuntimeError):
    """Typed code-only rejection of explicit binding inputs."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ProducerAdmission:
    """Bounded observability record; carries no envelope payload."""

    sequence: int
    status: str  # ACCEPTED | DUPLICATE | BACKPRESSURE | REJECTED | ERROR
    detail: str


class _ControlEventProducerSink:
    """Callable sink: one bus.accept per envelope; never raises."""

    def __init__(self, bus: HookBus, context: HookIngressContext,
                 serializer: Callable[[object], object]) -> None:
        self._bus = bus
        self._context = context
        self._serializer = serializer
        self._sequence = 0
        self._admissions: list[ProducerAdmission] = []

    @property
    def last_admission(self) -> ProducerAdmission | None:
        return self._admissions[-1] if self._admissions else None

    @property
    def admissions(self) -> tuple[ProducerAdmission, ...]:
        # Newest-last bounded view; the monotonic sequence is never truncated.
        return tuple(self._admissions)

    def _record(self, status: str, detail: str) -> None:
        self._sequence += 1
        self._admissions.append(ProducerAdmission(self._sequence, status, detail))
        if len(self._admissions) > _MAX_ADMISSIONS:
            del self._admissions[:-_MAX_ADMISSIONS]

    def __call__(self, envelope: dict[str, object]) -> None:
        try:
            wire = self._serializer(envelope)
            if type(wire) not in (bytes, bytearray):
                # HookBus ingests wire bytes only; a non-bytes serializer
                # result is a typed wiring rejection, never a raise.
                self._record("REJECTED", "PRODUCER_WIRE_NOT_BYTES")
                return
            admission = self._bus.accept(wire, self._context)
        except Exception as exc:  # noqa: BLE001 - control path must not see this
            name = type(exc).__name__
            if name == "HookBusError":
                detail = str(exc) or "HOOK_BUS_ERROR"
                status = "BACKPRESSURE" if "HOOK_BACKPRESSURE" in detail else "REJECTED"
            else:
                detail, status = name, "ERROR"
            self._record(status, detail)
            return
        status = getattr(admission, "status", "")
        if status == "DUPLICATE":
            self._record("DUPLICATE", "DUPLICATE")
        elif status == "ACCEPTED":
            shed = getattr(admission, "shed_count", 0)
            self._record("ACCEPTED", "ACCEPTED" if not shed else f"ACCEPTED_SHED_{shed}")
        else:
            # Unknown admission vocabulary stays visible, never silently OK.
            self._record("REJECTED", f"ADMISSION_{status or 'UNKNOWN'}")


def _validated_explicit(
    device_id: object, source_version: object, host_os: object, session_id: object,
) -> None:
    if not isinstance(device_id, str) or _DEVICE_ID.fullmatch(device_id) is None:
        raise ProducerWiringError("PRODUCER_DEVICE_ID_INVALID")
    if (not isinstance(source_version, str) or len(source_version) > 64
            or _SOURCE_VERSION.fullmatch(source_version) is None):
        raise ProducerWiringError("PRODUCER_SOURCE_VERSION_INVALID")
    if not isinstance(host_os, str) or host_os not in _HOST_OS_VALUES:
        raise ProducerWiringError("PRODUCER_HOST_OS_INVALID")
    if (not isinstance(session_id, str) or not 1 <= len(session_id) <= _MAX_SESSION_CHARS
            or any(ord(ch) < 32 or ord(ch) == 0x7F for ch in session_id)):
        raise ProducerWiringError("PRODUCER_SESSION_ID_INVALID")


def _json_bytes(envelope: object) -> bytes:
    return json.dumps(envelope).encode("utf-8")


def bind_control_event_producer(
    bus: HookBus,
    *,
    device_id: str,
    source_version: str,
    host_os: str,
    session_id: str,
    serializer: Callable[[object], object] = _json_bytes,
) -> tuple[Callable, Callable]:
    """Return ``(hook_context_factory, hook_observe_sink)`` for the accepted seam."""
    if not isinstance(bus, HookBus):
        raise ProducerWiringError("PRODUCER_BUS_INVALID")
    if not callable(serializer):
        raise ProducerWiringError("PRODUCER_SERIALIZER_INVALID")
    _validated_explicit(device_id, source_version, host_os, session_id)
    context = HookIngressContext(
        source=_SOURCE, device_id=device_id, session_id=session_id,
    )

    def hook_context_factory(event) -> ControlHookContext:
        recorded_at = getattr(event, "recorded_at", None)
        if not isinstance(recorded_at, str) or not recorded_at:
            raise ValueError("PRODUCER_RECORDED_AT_INVALID")
        return ControlHookContext(
            occurred_at=recorded_at,
            source_version=source_version,
            device_id=device_id,
            host_os=host_os,
        )

    sink = _ControlEventProducerSink(bus, context, serializer)
    return hook_context_factory, sink
