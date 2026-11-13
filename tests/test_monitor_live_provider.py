"""WO-P1-750: live monitor producer unit tests; injected fakes only, no live data."""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from a_conductor.inspector_projection import (
    HookInspectorRow, SkillInspectorRow, ToolInspectorRow,
)
from a_conductor.monitor_live_provider import (
    MONITOR_NOT_COLLECTED, MONITOR_PLACEHOLDER, build_live_monitor_provider,
)

AWIKI_DEFAULT = Path(r"A:\GitHub\A-Wiki")


def tool_row(**overrides):
    fields = dict(name="worker-a", device="windows-local", category="connector",
                  source="instance.ps1 discovery", phase="REGISTERED", state="READY",
                  registration_evidence="instance.ps1", last_verified=None,
                  last_error="", next_safe_action="Inspect health evidence",
                  provenance="probe:readyz")
    fields.update(overrides)
    return ToolInspectorRow(**fields)


def hook_row(**overrides):
    fields = dict(name="HookBus:GUARD", hook_class="GUARD",
                  authority_source="docs/contracts/hook-contract-v1.schema.json:1.0.0",
                  enabled=True, fail_mode="FAIL_CLOSED", state="UNKNOWN",
                  last_event="", last_error="", provenance="contract-only")
    fields.update(overrides)
    return HookInspectorRow(**fields)


def skill_row(**overrides):
    fields = dict(name="skill-a", state="AVAILABLE",
                  registry_source="skills-registry.json", routing_hint="route hints",
                  harness="kilo", deprecated=False, duplicate=False,
                  provenance="registry-only")
    fields.update(overrides)
    return SkillInspectorRow(**fields)


def ok_collectors(skill_rows=()):
    return (
        lambda: ((tool_row(),), ()),
        lambda repo_root: ((hook_row(),), ()),
        lambda **kwargs: (tuple(skill_rows), ()),
    )


def test_kill_switch_returns_exact_placeholder_verbatim():
    provider = build_live_monitor_provider(env={"A_CONDUCTOR_MONITOR_PROJECTION": "off"})
    assert provider() == {"mode": "off", "monitor": {
        "error": "MONITOR_PROJECTION_UNAVAILABLE", "gate": "OPTIONAL_READ_PORT_UNAVAILABLE"}}
    assert provider()["monitor"] == MONITOR_PLACEHOLDER


def test_kill_switch_seeds_placeholder_before_first_collection():
    provider = build_live_monitor_provider(env={"A_CONDUCTOR_MONITOR_PROJECTION": "off"})
    assert provider.initial_child == MONITOR_PLACEHOLDER
    tools, hooks, skills = ok_collectors()
    live = build_live_monitor_provider(env={}, tool_collector=tools,
                                       hook_collector=hooks, skill_collector=skills)
    assert live.initial_child == MONITOR_NOT_COLLECTED


def test_live_assembly_builds_sanitized_views_from_existing_collectors():
    tools, hooks, skills = ok_collectors((skill_row(), skill_row(state="STALE")))
    result = build_live_monitor_provider(
        env={}, tool_collector=tools, hook_collector=hooks, skill_collector=skills)()
    assert result["mode"] == "live"
    views = result["monitor"]
    assert set(views) == {"health", "timeline", "stm", "correlation", "inspector"}
    assert views["health"] == {"degraded": True, "counters": {},
                               "conditions": ["MONITOR_BUS_ABSENT"]}
    assert views["timeline"] == [] and views["stm"] == []
    assert views["correlation"] == {"state": "UNKNOWN"}
    assert views["inspector"]["summary"]["tools"]["counts"] == {"READY": 1}
    assert views["inspector"]["summary"]["skills"]["counts"] == {"AVAILABLE": 1, "STALE": 1}
    assert views["inspector"]["tools"][0]["name"] == "worker-a"
    assert views["inspector"]["summary"]["generated_at"].endswith("+00:00")


@pytest.mark.parametrize("section,gate", [("tools", "TOOLS"), ("hooks", "HOOKS"),
                                          ("skills", "SKILLS")])
def test_collector_failure_yields_typed_error_child_per_section(section, gate):
    def broken(*args, **kwargs):
        raise OSError("private-failure-detail")
    kwargs = {"tool_collector": lambda: ((), ()),
              "hook_collector": lambda repo_root: ((), ()),
              "skill_collector": lambda **kwargs: ((), ())}
    kwargs[f"{section[:-1]}_collector"] = broken
    result = build_live_monitor_provider(env={}, **kwargs)()
    assert result["mode"] == "error"
    assert result["monitor"] == {"error": "MONITOR_LIVE_PROJECTION_FAILED", "gate": gate}
    assert "private" not in json.dumps(result)


def test_awiki_root_override_reaches_skills_collector_and_unset_preserves_default():
    captured = {}

    def fake_skills(**kwargs):
        captured.update(kwargs)
        return (), ()

    build_live_monitor_provider(env={"A_CONDUCTOR_AWIKI_ROOT": "/tmp/awiki-test"},
                                skill_collector=fake_skills)()
    assert captured == {"awiki_root": "/tmp/awiki-test"}
    captured.clear()
    build_live_monitor_provider(env={}, skill_collector=fake_skills)()
    assert captured == {}  # collector default preserved verbatim (Windows behavior)


def test_no_collection_at_factory_or_wiring_time():
    calls = []

    def counting():
        calls.append(1)
        return (tool_row(),), ()

    provider = build_live_monitor_provider(env={}, tool_collector=counting,
                                           hook_collector=lambda repo_root: ((), ()),
                                           skill_collector=lambda **k: ((), ()))
    assert not calls
    result = provider()
    assert len(calls) == 1
    assert result["mode"] == "live"


def test_credential_shaped_row_is_redacted_end_to_end():
    secret_row = skill_row(routing_hint="invoke with token=abcd1234 now")
    tools, hooks, skills = ok_collectors((secret_row,))
    result = build_live_monitor_provider(
        env={}, tool_collector=tools, hook_collector=hooks, skill_collector=skills)()
    text = json.dumps(result)
    assert "abcd1234" not in text
    assert "[REDACTED]" in text
    assert result["monitor"]["inspector"]["skills"][0]["routing_hint"] == "[REDACTED]"


def test_invalid_inspector_rows_degrade_without_typed_failure():
    def bad_skills(**kwargs):
        return ((1, 2, 3), ())

    tools, hooks, _ = ok_collectors()
    result = build_live_monitor_provider(env={}, tool_collector=tools,
                                         hook_collector=hooks,
                                         skill_collector=bad_skills)()
    assert result["mode"] == "live"
    assert result["monitor"]["inspector"]["state"] == "DEGRADED"


def test_summary_reports_collector_side_truncation_bounds():
    rows = tuple(skill_row(name=f"skill-{index}") for index in range(130))
    tools, hooks, skills = ok_collectors(rows)
    views = build_live_monitor_provider(
        env={}, tool_collector=tools, hook_collector=hooks, skill_collector=skills)()["monitor"]
    assert views["inspector"]["summary"]["skills"]["truncated"] is True
    assert views["inspector"]["summary"]["skills"]["dropped"] == 2
    assert len(views["inspector"]["skills"]) == 128


def test_off_accepts_case_and_whitespace_and_other_values_stay_live():
    assert build_live_monitor_provider(
        env={"A_CONDUCTOR_MONITOR_PROJECTION": " Off "})()["mode"] == "off"
    tools, hooks, skills = ok_collectors()
    enabled = build_live_monitor_provider(env={"A_CONDUCTOR_MONITOR_PROJECTION": "enabled"},
                                          tool_collector=tools, hook_collector=hooks,
                                          skill_collector=skills)()
    assert enabled["mode"] == "live"
    assert build_live_monitor_provider(env={}, tool_collector=tools,
                                       hook_collector=hooks, skill_collector=skills)()["mode"] == "live"
