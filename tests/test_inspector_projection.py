"""WO-P1-739 RED contract: pure, bounded and truthful inspector views."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

import pytest

import a_conductor.inspector_projection as module
from a_conductor.inspector_projection import (
    HookInspectorRow,
    InspectorProjectionError,
    InspectorState,
    SkillInspectorRow,
    ToolInspectorRow,
    ToolPhase,
    build_inspector_views,
)

NOW = datetime(2026, 11, 9, 10, 0, tzinfo=timezone.utc)


def _tool(**changes: object) -> ToolInspectorRow:
    return replace(ToolInspectorRow(
        name="local-connector", device="windows-local", category="connector",
        source="instance.ps1 discovery", phase=ToolPhase.REGISTERED,
        state=InspectorState.UNKNOWN, registration_evidence="instance.ps1",
        last_verified=None, last_error="", next_safe_action="Inspect health",
        provenance="discovery-only",
    ), **changes)


def _hook(**changes: object) -> HookInspectorRow:
    return replace(HookInspectorRow(
        name="control-hook-adapter", hook_class="OBSERVE",
        authority_source="contract:1.0.0", enabled=True, fail_mode="UNKNOWN",
        state=InspectorState.UNKNOWN, last_event="", last_error="",
        provenance="contract-only",
    ), **changes)


def _skill(**changes: object) -> SkillInspectorRow:
    return replace(SkillInspectorRow(
        name="fixture-skill", state="AVAILABLE",
        registry_source="skills-registry.json", routing_hint="fixture trigger",
        harness="all", deprecated=False, duplicate=False,
        provenance="registry-only",
    ), **changes)


def _views(*, tools=(), hooks=(), skills=()) -> dict:
    return build_inspector_views(tools=tools, hooks=hooks, skills=skills, now=NOW)


def test_imports_are_pure() -> None:
    banned = {"subprocess", "socket", "urllib", "sqlite3", "shutil", "requests", "http"}
    for value in vars(module).values():
        if isinstance(value, ModuleType):
            assert value.__name__.split(".")[0] not in banned
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name.split(".")[0] not in banned for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in banned
            assert node.level == 0, "Projection must not import I/O-bearing project modules"


def test_enum_contract_and_frozen_rows() -> None:
    assert {state.value for state in InspectorState} == {
        "READY", "UNKNOWN", "STALE", "DISCONNECTED", "DEGRADED",
    }
    assert {phase.value for phase in ToolPhase} == {
        "REGISTERED", "STARTED", "CONNECTED", "INJECTED", "UNKNOWN",
    }
    for row in (_tool(), _hook(), _skill()):
        with pytest.raises(FrozenInstanceError):
            row.name = "changed"


@pytest.mark.parametrize("section,builder", [
    ("tools", _tool), ("hooks", _hook), ("skills", _skill),
])
def test_unknown_state_is_clamped_never_ready(section, builder) -> None:
    result = _views(**{section: (builder(state="garbage"),)})
    assert result[section][0]["state"] == "UNKNOWN"
    assert result["summary"][section]["counts"]["UNKNOWN"] == 1
    assert result["summary"][section]["counts"].get("READY", 0) == 0


def test_unknown_phase_and_hook_enums_are_clamped() -> None:
    result = _views(tools=(_tool(phase="garbage"),), hooks=(
        _hook(hook_class="garbage", fail_mode="garbage"),
    ))
    assert result["tools"][0]["phase"] == "UNKNOWN"
    assert result["hooks"][0]["hook_class"] == "UNKNOWN"
    assert result["hooks"][0]["fail_mode"] == "UNKNOWN"


@pytest.mark.parametrize("phase", tuple(ToolPhase))
def test_tool_phase_is_not_runtime_readiness(phase: ToolPhase) -> None:
    row = _views(tools=(_tool(phase=phase),))["tools"][0]
    assert row["phase"] == phase.value
    assert row["state"] == "UNKNOWN"


@pytest.mark.parametrize("state", tuple(InspectorState))
def test_states_are_first_class_in_every_section(state: InspectorState) -> None:
    result = _views(tools=(_tool(state=state),), hooks=(_hook(state=state),),
                    skills=(_skill(state=state),))
    for section in ("tools", "hooks", "skills"):
        assert result[section][0]["state"] == state.value
        assert result["summary"][section]["counts"][state.value] == 1


def test_available_is_skill_only_and_not_ready() -> None:
    result = _views(tools=(_tool(state="AVAILABLE"),), skills=(_skill(),))
    assert result["tools"][0]["state"] == "UNKNOWN"
    assert result["skills"][0]["state"] == "AVAILABLE"
    assert result["summary"]["skills"]["counts"]["AVAILABLE"] == 1
    assert result["summary"]["skills"]["counts"].get("READY", 0) == 0


@pytest.mark.parametrize("section,builder", [
    ("tools", _tool), ("hooks", _hook), ("skills", _skill),
])
def test_bounds_drop_oldest_and_count_only_retained_rows(section, builder) -> None:
    rows = tuple(builder(name=f"row-{index:03}") for index in range(129))
    result = _views(**{section: rows})
    assert len(result[section]) == 128
    assert result[section][0]["name"] == "row-001"
    assert result[section][-1]["name"] == "row-128"
    summary = result["summary"][section]
    assert summary["truncated"] is True
    assert summary["dropped"] == 1
    assert sum(summary["counts"].values()) == 128


@pytest.mark.parametrize("secret", [
    "Bearer FAKE000000000000000000000000000",
    "sk-FAKE0000000000000000000000000000000000",
    "ghp_FAKE0000000000000000000000000000000",
    "api_key=FAKE0000000000000000000000",
    "token=FAKE0000000000000000000000",
    "credential=FAKE0000000000000000000000",
    "-----BEGIN PRIVATE KEY----- FAKE",
    "x" * 210 + " token=FAKE0000000000000000000000",
])
def test_secret_shaped_errors_are_redacted_before_length_cap(secret: str) -> None:
    result = _views(tools=(_tool(last_error=secret),), hooks=(_hook(last_error=secret),))
    assert result["tools"][0]["last_error"] == "[REDACTED]"
    assert result["hooks"][0]["last_error"] == "[REDACTED]"
    assert secret not in repr(result)


@pytest.mark.parametrize("section,builder", [
    ("tools", _tool), ("hooks", _hook), ("skills", _skill),
])
def test_all_free_text_fields_are_capped_and_secret_free(section, builder) -> None:
    original = builder()
    for field in fields(original):
        if field.name in {"state", "phase", "hook_class", "fail_mode"}:
            continue
        if isinstance(getattr(original, field.name), str):
            long_row = replace(original, **{field.name: "x" * 250})
            assert len(_views(**{section: (long_row,)})[section][0][field.name]) <= 200
            secret_row = replace(original, **{field.name: "token=FAKE0000000000000000"})
            assert _views(**{section: (secret_row,)})[section][0][field.name] == "[REDACTED]"


@pytest.mark.parametrize("bad", [None, object(), {"name": "foreign"}, "row"])
def test_foreign_rows_raise_code_only_error(bad: object) -> None:
    with pytest.raises(InspectorProjectionError) as caught:
        _views(tools=(bad,))
    assert caught.value.code == "INSPECTOR_PROJECTION_INVALID_INPUT"
    assert str(caught.value) == caught.value.code


@pytest.mark.parametrize("bad", ["", "   ", None, 3])
@pytest.mark.parametrize("section,builder", [
    ("tools", _tool), ("hooks", _hook), ("skills", _skill),
])
def test_every_row_requires_a_nonempty_string_name(section, builder, bad) -> None:
    with pytest.raises(InspectorProjectionError) as caught:
        _views(**{section: (builder(name=bad),)})
    assert caught.value.code == "INSPECTOR_PROJECTION_INVALID_INPUT"


def test_discarded_oldest_row_is_still_validated() -> None:
    with pytest.raises(InspectorProjectionError):
        _views(tools=(_tool(name=""),) + tuple(_tool() for _ in range(128)))


def test_hostile_iterator_raises_typed_error() -> None:
    class Hostile:
        def __iter__(self):
            raise RuntimeError("token=FAKE0000000000000000")

    with pytest.raises(InspectorProjectionError) as caught:
        _views(tools=Hostile())
    assert caught.value.code == "INSPECTOR_PROJECTION_INVALID_INPUT"
    assert "FAKE" not in str(caught.value)


@pytest.mark.parametrize("row,section", [
    (_tool(last_verified=True), "tools"),
    (_tool(device=object()), "tools"),
    (_hook(enabled="yes"), "hooks"),
    (_skill(deprecated="false"), "skills"),
    (_skill(duplicate=1), "skills"),
])
def test_malformed_scalar_fields_are_not_coerced(row, section) -> None:
    with pytest.raises(InspectorProjectionError):
        _views(**{section: (row,)})


@pytest.mark.parametrize("verified", [None, 1794218400, "2026-11-09T10:00:00Z"])
def test_last_verified_preserves_supported_types(verified) -> None:
    row = _views(tools=(_tool(last_verified=verified),))["tools"][0]
    assert row["last_verified"] == verified


def test_summary_provenance_and_frozen_input_determinism() -> None:
    tools = (_tool(state="READY", provenance="probe:readyz"), _tool(state="STALE"))
    hooks, skills = (_hook(),), (_skill(),)
    before = repr((tools, hooks, skills))
    first = _views(tools=tools, hooks=hooks, skills=skills)
    second = _views(tools=tools, hooks=hooks, skills=skills)
    assert first == second
    assert repr((tools, hooks, skills)) == before
    assert set(first) == {"tools", "hooks", "skills", "summary"}
    assert first["summary"]["generated_at"] == NOW.isoformat()
    assert first["tools"][0]["provenance"] == "probe:readyz"
    assert first["hooks"][0]["provenance"] == "contract-only"
    assert first["skills"][0]["provenance"] == "registry-only"
    assert first["summary"]["tools"]["counts"]["READY"] == 1
    assert first["summary"]["tools"]["counts"]["STALE"] == 1
    for section in ("tools", "hooks", "skills"):
        assert first["summary"][section]["truncated"] is False
        assert first["summary"][section]["dropped"] == 0


def test_empty_sections_have_empty_counts() -> None:
    result = _views()
    for section in ("tools", "hooks", "skills"):
        assert len(result[section]) == 0
        assert sum(result["summary"][section]["counts"].values()) == 0
