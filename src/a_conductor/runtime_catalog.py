"""Deterministic runtime catalog and routing selection seam.

Pure metadata only (WO-P1-079 / North Star N2): the catalog never probes
the filesystem, processes, the network, MCP, Node, or devices. Availability
is supplied observation; readiness is never inferred from configuration or
profile existence. Selection is exact-name, fail-closed, native-first with
Serena preferred over Desktop Commander for semantic-code work, and a
stable lexical runtime-id tie-break within the same family priority.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from enum import Enum

from .desktop_commander_runtime import (
    DesktopCommanderMode,
    build_desktop_commander_profile,
)
from .domain import Capability, ExecutionSurfaceTraits, Runtime


class RuntimeAvailability(str, Enum):
    """Explicit availability lifecycle for a catalogued runtime.

    Only ``AVAILABLE`` means executable-ready. ``INSTALLED`` records
    presence alone and must never be treated as readiness.
    """

    INSTALLED = "INSTALLED"
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class RuntimeObservation:
    """Supplied readiness evidence. The catalog never produces this itself."""

    source: str

    def __post_init__(self) -> None:
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("source must not be blank")


@dataclass(frozen=True, slots=True)
class RuntimeCatalogEntry:
    runtime: Runtime
    traits: ExecutionSurfaceTraits
    runtime_family: str
    availability: RuntimeAvailability = RuntimeAvailability.UNKNOWN

    def __post_init__(self) -> None:
        if not isinstance(self.availability, RuntimeAvailability):
            raise ValueError("availability must be a RuntimeAvailability")
        if not isinstance(self.traits, ExecutionSurfaceTraits):
            raise ValueError("traits must be ExecutionSurfaceTraits")
        if not isinstance(self.runtime_family, str) or not self.runtime_family.strip():
            raise ValueError("runtime_family must not be blank")

    @property
    def capability_names(self) -> frozenset[str]:
        return frozenset(item.name for item in self.runtime.capabilities)


NATIVE_RUNTIME_FAMILY = "native"
SERENA_RUNTIME_FAMILY = "serena"
DESKTOP_COMMANDER_RUNTIME_FAMILY = "desktop-commander"

SEMANTIC_CODE_CAPABILITY = "semantic.code"
REMOTE_DEVICE_CAPABILITY = "remote.device"

#: Desktop Commander joins selection only when the request materially needs
#: interactive, long-running, or remote-device execution.
DESKTOP_COMMANDER_ESSENTIAL_CAPABILITIES = frozenset(
    {
        "process.interactive",
        "process.long-running",
        REMOTE_DEVICE_CAPABILITY,
    }
)

_FAMILY_PRIORITY = {
    NATIVE_RUNTIME_FAMILY: 0,
    SERENA_RUNTIME_FAMILY: 1,
    DESKTOP_COMMANDER_RUNTIME_FAMILY: 2,
}
_UNLISTED_FAMILY_PRIORITY = 3


def mark_availability(
    entry: RuntimeCatalogEntry,
    availability: RuntimeAvailability,
    observation: RuntimeObservation | None = None,
) -> RuntimeCatalogEntry:
    """Return a new entry with explicit availability.

    Fail-closed: entering ``AVAILABLE`` requires a supplied
    ``RuntimeObservation``; configuration/profile existence alone can never
    mark a runtime executable-ready.
    """
    if not isinstance(availability, RuntimeAvailability):
        raise ValueError("availability must be a RuntimeAvailability")
    if availability is RuntimeAvailability.AVAILABLE and not isinstance(
        observation, RuntimeObservation
    ):
        raise ValueError("marking AVAILABLE requires a supplied RuntimeObservation")
    return replace(entry, availability=availability)


def native_entry(
    runtime_id: str,
    capability_names: Iterable[str],
    availability: RuntimeAvailability = RuntimeAvailability.UNKNOWN,
) -> RuntimeCatalogEntry:
    return RuntimeCatalogEntry(
        runtime=Runtime(
            runtime_id=runtime_id,
            runtime_type=NATIVE_RUNTIME_FAMILY,
            capabilities=tuple(Capability(name) for name in capability_names),
        ),
        traits=ExecutionSurfaceTraits(),
        runtime_family=NATIVE_RUNTIME_FAMILY,
        availability=availability,
    )


def serena_entry(
    runtime_id: str,
    availability: RuntimeAvailability = RuntimeAvailability.UNKNOWN,
) -> RuntimeCatalogEntry:
    return RuntimeCatalogEntry(
        runtime=Runtime(
            runtime_id=runtime_id,
            runtime_type=SERENA_RUNTIME_FAMILY,
            capabilities=(
                Capability(SEMANTIC_CODE_CAPABILITY),
                Capability("repo.tools"),
            ),
        ),
        traits=ExecutionSurfaceTraits(),
        runtime_family=SERENA_RUNTIME_FAMILY,
        availability=availability,
    )


def desktop_commander_entry(
    runtime_id: str,
    mode: DesktopCommanderMode = DesktopCommanderMode.LOCAL,
    availability: RuntimeAvailability = RuntimeAvailability.UNKNOWN,
) -> RuntimeCatalogEntry:
    profile = build_desktop_commander_profile(runtime_id, mode)
    return RuntimeCatalogEntry(
        runtime=profile.runtime,
        traits=profile.traits,
        runtime_family=DESKTOP_COMMANDER_RUNTIME_FAMILY,
        availability=availability,
    )


@dataclass(frozen=True, slots=True)
class RuntimeCatalog:
    entries: tuple[RuntimeCatalogEntry, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "entries", tuple(self.entries))

    def with_entry(self, entry: RuntimeCatalogEntry) -> RuntimeCatalog:
        return RuntimeCatalog(entries=(*self.entries, entry))


def _is_selectable(entry: RuntimeCatalogEntry, requested: frozenset[str]) -> bool:
    if entry.availability is not RuntimeAvailability.AVAILABLE:
        return False
    capabilities = entry.capability_names
    if not requested <= capabilities:
        return False
    if (
        REMOTE_DEVICE_CAPABILITY in capabilities
        and REMOTE_DEVICE_CAPABILITY not in requested
    ):
        return False
    if entry.runtime_family == DESKTOP_COMMANDER_RUNTIME_FAMILY and not (
        requested & DESKTOP_COMMANDER_ESSENTIAL_CAPABILITIES
    ):
        return False
    return True


def select_runtime(
    catalog: RuntimeCatalog,
    requested_capabilities: Iterable[str],
) -> RuntimeCatalogEntry | None:
    """Deterministically select an executable-ready runtime, or ``None``.

    Exact capability-name matching only. Ordering: native fixed adapters
    first when sufficient, Serena before Desktop Commander for
    semantic-code work, Desktop Commander only when its interactive /
    long-running / remote-device capability materially serves the request.
    Ties break by lexical ``runtime_id`` and never depend on catalog order.
    """
    requested = frozenset(requested_capabilities)
    for name in requested:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("requested capability names must not be blank")
    if not requested:
        return None
    eligible = [entry for entry in catalog.entries if _is_selectable(entry, requested)]
    if not eligible:
        return None
    return min(
        eligible,
        key=lambda entry: (
            _FAMILY_PRIORITY.get(entry.runtime_family, _UNLISTED_FAMILY_PRIORITY),
            entry.runtime.runtime_id,
        ),
    )
