"""Runtime catalog + deterministic routing selection contracts (WO-P1-079).

The catalog is a pure metadata seam: availability is supplied observation,
selection is deterministic and fail-closed, and neither importing the module
nor calling the selector may probe processes, the network, or devices.
"""

from __future__ import annotations

from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parent.parent / "src"


def _available(entry):
    from a_conductor.runtime_catalog import (
        RuntimeAvailability,
        RuntimeObservation,
        mark_availability,
    )

    return mark_availability(
        entry,
        RuntimeAvailability.AVAILABLE,
        RuntimeObservation(source="test-observation"),
    )


def test_availability_states_are_explicit() -> None:
    from a_conductor.runtime_catalog import RuntimeAvailability

    assert {state.name for state in RuntimeAvailability} == {
        "INSTALLED",
        "AVAILABLE",
        "UNAVAILABLE",
        "UNKNOWN",
    }


def test_catalog_entry_carries_runtime_traits_availability_and_family() -> None:
    from a_conductor.domain import Capability, ExecutionSurfaceTraits, Runtime
    from a_conductor.runtime_catalog import (
        NATIVE_RUNTIME_FAMILY,
        RuntimeAvailability,
        RuntimeCatalogEntry,
    )

    entry = RuntimeCatalogEntry(
        runtime=Runtime("native-fs", "native", (Capability("filesystem.read"),)),
        traits=ExecutionSurfaceTraits(),
        availability=RuntimeAvailability.UNKNOWN,
        runtime_family=NATIVE_RUNTIME_FAMILY,
    )

    assert entry.runtime.runtime_id == "native-fs"
    assert entry.traits is not None
    assert entry.availability is RuntimeAvailability.UNKNOWN
    assert entry.runtime_family == "native"
    assert entry.capability_names == frozenset({"filesystem.read"})


def test_available_transition_requires_supplied_observation() -> None:
    from a_conductor.runtime_catalog import (
        RuntimeAvailability,
        RuntimeObservation,
        desktop_commander_entry,
        mark_availability,
    )

    entry = desktop_commander_entry("dc-local-gate")
    assert entry.availability is RuntimeAvailability.UNKNOWN

    with pytest.raises(ValueError):
        mark_availability(entry, RuntimeAvailability.AVAILABLE)

    with pytest.raises(ValueError):
        RuntimeObservation(source="   ")

    observed = mark_availability(
        entry,
        RuntimeAvailability.AVAILABLE,
        RuntimeObservation(source="conductor-preflight"),
    )
    assert observed.availability is RuntimeAvailability.AVAILABLE
    assert entry.availability is RuntimeAvailability.UNKNOWN  # original untouched

    installed = mark_availability(entry, RuntimeAvailability.INSTALLED)
    assert installed.availability is RuntimeAvailability.INSTALLED


def test_installed_unknown_or_unavailable_runtime_is_never_selected() -> None:
    from a_conductor.runtime_catalog import (
        RuntimeAvailability,
        RuntimeCatalog,
        desktop_commander_entry,
        mark_availability,
        select_runtime,
    )

    for state in (
        RuntimeAvailability.INSTALLED,
        RuntimeAvailability.UNAVAILABLE,
        RuntimeAvailability.UNKNOWN,
    ):
        entry = mark_availability(desktop_commander_entry("dc-gate"), state)
        catalog = RuntimeCatalog(entries=(entry,))
        assert select_runtime(catalog, ("process.interactive",)) is None


def test_remote_desktop_commander_selectable_only_with_remote_device_request() -> None:
    from a_conductor.desktop_commander_runtime import DesktopCommanderMode
    from a_conductor.runtime_catalog import (
        RuntimeAvailability,
        RuntimeCatalog,
        RuntimeObservation,
        desktop_commander_entry,
        mark_availability,
        select_runtime,
    )

    available_remote = mark_availability(
        desktop_commander_entry("dc-remote-1", mode=DesktopCommanderMode.REMOTE),
        RuntimeAvailability.AVAILABLE,
        RuntimeObservation(source="device-preflight"),
    )
    catalog = RuntimeCatalog(entries=(available_remote,))

    assert select_runtime(catalog, ("process.interactive",)) is None
    assert select_runtime(catalog, ("filesystem.read",)) is None

    pick = select_runtime(catalog, ("remote.device",))
    assert pick is not None
    assert pick.runtime.runtime_id == "dc-remote-1"

    combined = select_runtime(catalog, ("process.interactive", "remote.device"))
    assert combined is not None
    assert combined.runtime.runtime_id == "dc-remote-1"


def test_native_fixed_runtime_wins_when_sufficient() -> None:
    from a_conductor.domain import Capability, ExecutionSurfaceTraits, Runtime
    from a_conductor.runtime_catalog import (
        DESKTOP_COMMANDER_RUNTIME_FAMILY,
        SERENA_RUNTIME_FAMILY,
        RuntimeAvailability,
        RuntimeCatalog,
        RuntimeCatalogEntry,
        desktop_commander_entry,
        native_entry,
        select_runtime,
    )

    native = _available(native_entry("native-fs", ("filesystem.read",)))
    serena_fs = _available(
        RuntimeCatalogEntry(
            runtime=Runtime(
                "serena-fs", "serena", (Capability("filesystem.read"),)
            ),
            traits=ExecutionSurfaceTraits(),
            availability=RuntimeAvailability.UNKNOWN,
            runtime_family=SERENA_RUNTIME_FAMILY,
        )
    )
    commander = _available(desktop_commander_entry("dc-local-1"))

    pick = select_runtime(
        RuntimeCatalog(entries=(commander, serena_fs, native)),
        ("filesystem.read",),
    )
    assert pick is not None
    assert pick.runtime.runtime_id == "native-fs"

    without_native = select_runtime(
        RuntimeCatalog(entries=(commander, serena_fs)),
        ("filesystem.read",),
    )
    assert without_native is not None
    assert without_native.runtime.runtime_id == "serena-fs"

    # Desktop Commander stays out of plain fixed-capability routing entirely.
    only_dc = select_runtime(
        RuntimeCatalog(entries=(commander,)), ("filesystem.read",)
    )
    assert only_dc is None


def test_serena_preferred_for_semantic_code_as_pure_metadata() -> None:
    from a_conductor.domain import Capability, ExecutionSurfaceTraits, Runtime
    from a_conductor.runtime_catalog import (
        DESKTOP_COMMANDER_RUNTIME_FAMILY,
        SEMANTIC_CODE_CAPABILITY,
        SERENA_RUNTIME_FAMILY,
        RuntimeAvailability,
        RuntimeCatalog,
        RuntimeCatalogEntry,
        select_runtime,
        serena_entry,
    )

    serena = _available(serena_entry("serena-1"))
    assert serena.runtime.runtime_type == "serena"
    assert type(serena.runtime) is Runtime  # pure domain metadata, no engine object

    overlapping = (Capability(SEMANTIC_CODE_CAPABILITY), Capability("process.interactive"))
    serena_overlapping = _available(
        RuntimeCatalogEntry(
            runtime=Runtime("serena-overlap", "serena", overlapping),
            traits=ExecutionSurfaceTraits(),
            runtime_family=SERENA_RUNTIME_FAMILY,
            availability=RuntimeAvailability.UNKNOWN,
        )
    )
    dc_overlapping = _available(
        RuntimeCatalogEntry(
            runtime=Runtime("dc-overlap", "desktop-commander", overlapping),
            traits=ExecutionSurfaceTraits(),
            runtime_family=DESKTOP_COMMANDER_RUNTIME_FAMILY,
            availability=RuntimeAvailability.UNKNOWN,
        )
    )

    pick = select_runtime(
        RuntimeCatalog(entries=(dc_overlapping, serena_overlapping)),
        (SEMANTIC_CODE_CAPABILITY, "process.interactive"),
    )
    assert pick is not None
    assert pick.runtime.runtime_id == "serena-overlap"

    semantic_only = select_runtime(
        RuntimeCatalog(entries=(serena,)), (SEMANTIC_CODE_CAPABILITY,)
    )
    assert semantic_only is not None
    assert semantic_only.runtime.runtime_id == "serena-1"


def test_lexical_runtime_id_tie_break_is_stable() -> None:
    from a_conductor.runtime_catalog import RuntimeCatalog, native_entry, select_runtime

    alpha = _available(native_entry("native-alpha", ("filesystem.read",)))
    beta = _available(native_entry("native-beta", ("filesystem.read",)))

    first = select_runtime(
        RuntimeCatalog(entries=(beta, alpha)), ("filesystem.read",)
    )
    second = select_runtime(
        RuntimeCatalog(entries=(alpha, beta)), ("filesystem.read",)
    )
    assert first is not None and first.runtime.runtime_id == "native-alpha"
    assert second is not None and second.runtime.runtime_id == "native-alpha"


def test_no_match_and_empty_request_return_none() -> None:
    from a_conductor.runtime_catalog import (
        RuntimeCatalog,
        desktop_commander_entry,
        select_runtime,
    )

    commander = _available(desktop_commander_entry("dc-local-1"))
    catalog = RuntimeCatalog(entries=(commander,))

    assert select_runtime(catalog, ()) is None
    assert select_runtime(catalog, ("nonexistent.capability",)) is None
    assert select_runtime(catalog, ("filesystem.reads",)) is None  # exact names only
    assert select_runtime(catalog, ("Process.Interactive",)) is None  # case-sensitive
    assert select_runtime(RuntimeCatalog(), ("filesystem.read",)) is None

    with pytest.raises(ValueError):
        select_runtime(catalog, ("  ",))


def test_module_import_surface_is_pure_metadata() -> None:
    import ast

    allowed = {"__future__", "collections.abc", "dataclasses", "enum"}
    allowed_local = {"a_conductor.domain", "a_conductor.desktop_commander_runtime"}
    source = (SRC_DIR / "a_conductor" / "runtime_catalog.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            imported.add(node.module or "")
    unexpected = imported - allowed - allowed_local
    assert not unexpected, f"unexpected imports: {sorted(unexpected)}"


def test_module_body_and_selection_perform_no_io() -> None:
    """Poison common I/O entry points, then reload and select.

    Environment note (recorded per WO): the local hermes-agent venv
    interpreter cannot combine ``sys.addaudithook`` with bytecode
    compilation (``import json`` fails with ``AttributeError`` in
    ``_compile_bytecode``), so an audit-hook subprocess gate is not
    deterministic on this machine. Poisoned-callable reloading plus the
    AST import-surface test above give deterministic local evidence
    instead; audit-hook coverage can return on stock interpreters.
    """
    import builtins
    import importlib
    import os as os_mod
    import socket as socket_mod
    import subprocess as subprocess_mod

    from a_conductor.desktop_commander_runtime import DesktopCommanderMode

    def _poison(kind: str):
        def _raise(*args, **kwargs):
            raise AssertionError(f"unexpected {kind} during catalog use")

        return _raise

    real_open = builtins.open
    real_system = os_mod.system
    real_popen = subprocess_mod.Popen
    real_socket = socket_mod.socket
    try:
        builtins.open = _poison("open")
        os_mod.system = _poison("os.system")
        subprocess_mod.Popen = _poison("subprocess.Popen")
        socket_mod.socket = _poison("socket.socket")

        module = importlib.reload(
            importlib.import_module("a_conductor.runtime_catalog")
        )

        probe = module.RuntimeObservation(source="purity-probe")
        catalog = module.RuntimeCatalog(
            entries=(
                module.mark_availability(
                    module.desktop_commander_entry(
                        "dc-purity", mode=DesktopCommanderMode.REMOTE
                    ),
                    module.RuntimeAvailability.AVAILABLE,
                    probe,
                ),
                module.mark_availability(
                    module.native_entry("native-purity", ("filesystem.read",)),
                    module.RuntimeAvailability.AVAILABLE,
                    probe,
                ),
                module.mark_availability(
                    module.serena_entry("serena-purity"),
                    module.RuntimeAvailability.AVAILABLE,
                    probe,
                ),
            )
        )
        local_pick = module.select_runtime(catalog, ("filesystem.read",))
        assert local_pick is not None
        assert local_pick.runtime.runtime_id == "native-purity"
        remote_pick = module.select_runtime(catalog, ("remote.device",))
        assert remote_pick is not None
        assert remote_pick.runtime.runtime_id == "dc-purity"
        assert module.select_runtime(catalog, ("process.interactive",)) is None
    finally:
        builtins.open = real_open
        os_mod.system = real_system
        subprocess_mod.Popen = real_popen
        socket_mod.socket = real_socket
