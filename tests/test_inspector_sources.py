"""WO-P1-739 RED contract: fixture-owned reads, no network or live devices."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from a_conductor import local_instances
from a_conductor.inspector_sources import (
    collect_local_hook_rows,
    collect_local_skill_rows,
    collect_local_tool_rows,
)
from a_conductor.local_instances import InstanceHealthState

NOW = datetime(2026, 11, 9, 10, 0, tzinfo=timezone.utc)
REGISTRY = "skills-registry.json"
FAKE_TUNNEL_ID = "tunnel_" + "a" * 32


def _instance(root: Path, name: str = "fixture", *, configured: bool = True) -> Path:
    folder = root / name
    folder.mkdir(parents=True)
    (folder / "instance.ps1").write_text(
        f"$InstanceName = '{name}'\n"
        f"$ProjectPath = '{root.as_posix()}'\n"
        "$HealthListenAddress = '127.0.0.1:1'\n",
        encoding="utf-8",
    )
    if configured:
        (folder / "config").mkdir()
        (folder / "config" / "tunnel-id.txt").write_text(FAKE_TUNNEL_ID, encoding="utf-8")
    return folder


def _contracts(root: Path) -> Path:
    folder = root / "docs" / "contracts"
    folder.mkdir(parents=True)
    schema = {
        "$id": "urn:a-conductor:schema:hook-contract:1.0.0",
        "properties": {
            "schema_version": {"type": "string", "pattern": r"^1\.\d+\.\d+$"},
            "hook_class": {"enum": ["OBSERVE", "ADVISORY", "GUARD", "COMMAND"]},
            "guard": {"properties": {
                "failure_policy": {"enum": ["FAIL_CLOSED", "FAIL_OPEN"]},
            }},
        },
    }
    (folder / "hook-contract-v1.schema.json").write_text(json.dumps(schema), encoding="utf-8")
    for harness in ("claude", "kilo"):
        (folder / f"{harness}-hook-adapter-v1.md").write_text(
            f"# {harness.title()} Hook Adapter v1\n"
            "Contract version emitted: Hook Contract v1 `1.0.0`\n"
            "Only OBSERVE-class normalized events are emitted by adapter v1.\n"
            "The adapter MUST NOT emit GUARD or COMMAND envelopes.\n"
            "Capability/version mismatch gates fail closed; no emission.\n",
            encoding="utf-8",
        )
    (root / "src" / "a_conductor").mkdir(parents=True)
    (root / "src" / "a_conductor" / "control_hook_adapter.py").write_text(
        '"""Pure ControlEvent projection into an OBSERVE envelope."""\n'
        'HOOK_SCHEMA_VERSION = "1.0.0"\n', encoding="utf-8",
    )
    return folder


def _entry(name: str, **changes: object) -> dict:
    return {
        "name": name, "aliases": [], "domain": ["engineering"],
        "lifecycle_phase": "review", "category": "pipeline", "source": "repo",
        "path": f"skills/awiki/{name}/SKILL.md", "agents": ["all", "kilo"],
        "version": "1.0.0", "status": "canonical", "description": "Fixture skill",
        "invocation": "manual", "invocation_hint": f"/{name}",
        "a_phase": "review", "triggers": ["fixture review", "inspect"], **changes,
    }


def _registry(root: Path, entries: list[dict] | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / REGISTRY
    path.write_text(json.dumps({
        "schema_version": 3, "generated_at": "2026-08-09",
        "skills": entries if entries is not None else [_entry("present"), _entry("missing")],
    }), encoding="utf-8")
    skill = root / "skills" / "awiki" / "present" / "SKILL.md"
    skill.parent.mkdir(parents=True, exist_ok=True)
    skill.write_text("# Fixture skill\n", encoding="utf-8")
    os.utime(path, (NOW.timestamp(), NOW.timestamp()))
    return path


def test_dead_probe_is_disconnected_and_does_not_leak_pairing_id(tmp_path: Path) -> None:
    _instance(tmp_path)
    calls = []

    def dead_probe(instance):
        calls.append(f"http://{instance.health_address}/readyz")
        return InstanceHealthState.STOPPED

    rows, notes = collect_local_tool_rows(tmp_path, probe=dead_probe)
    assert notes == ()
    assert calls == ["http://127.0.0.1:1/readyz"]
    assert len(rows) == 1
    assert rows[0].state == "DISCONNECTED"
    assert rows[0].phase == "REGISTERED"
    assert rows[0].provenance == "probe:readyz"
    assert rows[0].name == "fixture"
    assert rows[0].device == "windows-local"
    assert rows[0].category == "connector"
    assert rows[0].source == "instance.ps1 discovery"
    assert rows[0].registration_evidence
    assert FAKE_TUNNEL_ID not in repr((rows, notes))


def test_ok_probe_proves_ready_and_connected_not_injected(tmp_path: Path) -> None:
    _instance(tmp_path)
    rows, notes = collect_local_tool_rows(tmp_path, probe=lambda instance: InstanceHealthState.READY)
    assert notes == ()
    assert rows[0].state == "READY"
    assert rows[0].phase == "CONNECTED"
    assert rows[0].last_verified is not None
    assert rows[0].provenance == "probe:readyz"


def test_explicit_no_probe_is_discovery_only(tmp_path: Path, monkeypatch) -> None:
    _instance(tmp_path)

    def forbidden_probe(*args, **kwargs):
        pytest.fail("discovery-only must never call health")

    monkeypatch.setattr(local_instances, "instance_health_state", forbidden_probe)
    rows, notes = collect_local_tool_rows(tmp_path, probe=None)
    assert notes == ()
    assert rows[0].state == "UNKNOWN"
    assert rows[0].phase == "REGISTERED"
    assert rows[0].last_verified is None
    assert rows[0].provenance == "discovery-only"


def test_omitted_probe_reuses_existing_health_checker(tmp_path: Path, monkeypatch) -> None:
    _instance(tmp_path)
    calls = []

    def health(instance, **kwargs):
        calls.append(instance.name)
        return InstanceHealthState.READY

    monkeypatch.setattr(local_instances, "instance_health_state", health)
    rows, notes = collect_local_tool_rows(tmp_path)
    assert notes == ()
    assert calls == ["fixture"]
    assert rows[0].state == "READY"


def test_no_tunnel_configuration_cannot_prove_connected(tmp_path: Path) -> None:
    _instance(tmp_path, configured=False)
    rows, _ = collect_local_tool_rows(tmp_path, probe=lambda instance: InstanceHealthState.READY)
    assert rows[0].state == "READY"
    assert rows[0].phase == "STARTED"


def test_unknown_health_is_not_ready(tmp_path: Path) -> None:
    _instance(tmp_path)
    rows, _ = collect_local_tool_rows(tmp_path, probe=lambda instance: "garbage")
    assert rows[0].state == "UNKNOWN"
    assert rows[0].phase == "REGISTERED"


def test_transport_exception_is_disconnected_and_other_instances_survive(tmp_path: Path) -> None:
    _instance(tmp_path, "dead")
    _instance(tmp_path, "live")

    def probe(instance):
        if instance.name == "dead":
            raise ConnectionError("token=FAKE0000000000000000")
        return InstanceHealthState.READY

    rows, notes = collect_local_tool_rows(tmp_path, probe=probe)
    by_name = {row.name: row for row in rows}
    assert by_name["dead"].state == "DISCONNECTED"
    assert by_name["dead"].last_error == "TOOL_PROBE_TRANSPORT_ERROR"
    assert by_name["live"].state == "READY"
    assert "TOOL_PROBE_TRANSPORT_ERROR" in notes
    assert "FAKE" not in repr((rows, notes))


def test_unexpected_probe_failure_is_typed_degradation(tmp_path: Path) -> None:
    _instance(tmp_path)

    def probe(instance):
        raise RuntimeError("credential=FAKE0000000000000000")

    rows, notes = collect_local_tool_rows(tmp_path, probe=probe)
    assert rows[0].state == "DEGRADED"
    assert rows[0].last_error == "TOOL_PROBE_FAILED"
    assert "TOOL_PROBE_FAILED" in notes
    assert "FAKE" not in repr((rows, notes))


def test_discovery_failure_is_typed_not_raised(tmp_path: Path, monkeypatch) -> None:
    def discover(*args, **kwargs):
        raise PermissionError("token=FAKE0000000000000000")

    monkeypatch.setattr(local_instances, "discover_local_instances", discover)
    rows, notes = collect_local_tool_rows(tmp_path, probe=None)
    assert rows == ()
    assert "TOOLS_DISCOVERY_UNAVAILABLE" in notes
    assert "FAKE" not in repr(notes)


def test_missing_instances_root_is_empty(tmp_path: Path) -> None:
    rows, notes = collect_local_tool_rows(tmp_path / "absent", probe=None)
    assert rows == ()
    assert notes == ()


def test_hook_contracts_describe_presence_not_runtime_liveness(tmp_path: Path) -> None:
    _contracts(tmp_path)
    rows, notes = collect_local_hook_rows(tmp_path)
    assert notes == ()
    assert len(rows) == 7
    bus = [row for row in rows if row.name.startswith("HookBus:")]
    assert {row.hook_class for row in bus} == {"OBSERVE", "ADVISORY", "GUARD", "COMMAND"}
    assert {row.name for row in rows} >= {
        "control-hook-adapter", "claude-hook-adapter", "kilo-hook-adapter",
    }
    for row in rows:
        assert row.enabled is True
        assert row.state == "UNKNOWN"
        assert row.provenance == "contract-only"
        assert "1.0.0" in row.authority_source
        assert row.last_event == ""
    for row in rows:
        if row.name.endswith("hook-adapter"):
            assert row.hook_class == "OBSERVE"
            assert row.fail_mode == "UNKNOWN", "Version gates do not establish GUARD authority"
    assert next(row for row in bus if row.hook_class == "GUARD").fail_mode == "UNKNOWN"


def test_guard_fail_closed_requires_explicit_contract_evidence(tmp_path: Path) -> None:
    contracts = _contracts(tmp_path)
    (contracts / "hook-contract-v1.md").write_text(
        "# Hook Contract v1\n"
        "Security/authority GUARD hooks MUST use FAIL_CLOSED.\n",
        encoding="utf-8",
    )
    rows, _ = collect_local_hook_rows(tmp_path)
    guard = next(row for row in rows if row.name == "HookBus:GUARD")
    assert guard.fail_mode == "FAIL_CLOSED"
    assert guard.state == "UNKNOWN"


def test_missing_hook_doc_is_omitted_and_degraded(tmp_path: Path) -> None:
    contracts = _contracts(tmp_path)
    (contracts / "kilo-hook-adapter-v1.md").unlink()
    rows, notes = collect_local_hook_rows(tmp_path)
    assert "kilo-hook-adapter" not in {row.name for row in rows}
    assert "claude-hook-adapter" in {row.name for row in rows}
    assert "HOOK_CONTRACT_UNAVAILABLE" in notes


def test_malformed_hook_schema_does_not_drop_other_contracts(tmp_path: Path) -> None:
    contracts = _contracts(tmp_path)
    (contracts / "hook-contract-v1.schema.json").write_text("{bad", encoding="utf-8")
    rows, notes = collect_local_hook_rows(tmp_path)
    assert "claude-hook-adapter" in {row.name for row in rows}
    assert not any(row.name.startswith("HookBus:") for row in rows)
    assert "HOOK_CONTRACT_INVALID" in notes


def test_skills_use_real_registry_shape_and_file_existence(tmp_path: Path) -> None:
    _registry(tmp_path)
    rows, notes = collect_local_skill_rows(tmp_path, now=NOW)
    assert notes == ()
    by_name = {row.name: row for row in rows}
    assert set(by_name) == {"present", "missing"}
    assert by_name["present"].state == "AVAILABLE"
    assert by_name["missing"].state == "UNKNOWN"
    for row in rows:
        assert row.registry_source == REGISTRY
        assert "fixture review" in row.routing_hint
        assert "inspect" in row.routing_hint
        assert "all" in row.harness and "kilo" in row.harness
        assert row.provenance == "registry-only"
        assert row.deprecated is False
        assert row.duplicate is False


@pytest.mark.parametrize("contents", [None, "{bad", "[]", '{"skills": 3}'])
def test_missing_or_invalid_registry_is_typed_degradation(tmp_path: Path, contents) -> None:
    if contents is not None:
        (tmp_path / REGISTRY).write_text(contents, encoding="utf-8")
    rows, notes = collect_local_skill_rows(tmp_path, now=NOW)
    assert rows == ()
    assert "SKILLS_REGISTRY_UNAVAILABLE" in notes


def test_unreadable_registry_is_typed_degradation(tmp_path: Path, monkeypatch) -> None:
    registry = _registry(tmp_path)
    original = Path.open

    def guarded_open(path, *args, **kwargs):
        if path == registry:
            raise PermissionError("token=FAKE0000000000000000")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    rows, notes = collect_local_skill_rows(tmp_path, now=NOW)
    assert rows == ()
    assert "SKILLS_REGISTRY_UNAVAILABLE" in notes
    assert "FAKE" not in repr(notes)


def test_registry_mtime_controls_staleness(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    stale = NOW.timestamp() - 7 * 24 * 60 * 60 - 1
    os.utime(registry, (stale, stale))
    rows, _ = collect_local_skill_rows(tmp_path, now=NOW)
    by_name = {row.name: row for row in rows}
    assert by_name["present"].state == "STALE"
    assert by_name["missing"].state == "UNKNOWN"


def test_custom_freshness_boundary_is_inclusive(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    boundary = NOW.timestamp() - 60
    os.utime(registry, (boundary, boundary))
    rows, _ = collect_local_skill_rows(tmp_path, max_age_seconds=60, now=NOW)
    assert next(row for row in rows if row.name == "present").state == "AVAILABLE"
    os.utime(registry, (boundary - 1, boundary - 1))
    rows, _ = collect_local_skill_rows(tmp_path, max_age_seconds=60, now=NOW)
    assert next(row for row in rows if row.name == "present").state == "STALE"


def test_deprecated_and_duplicate_registry_entries_are_visible(tmp_path: Path) -> None:
    _registry(tmp_path, [_entry("present", status="deprecated"), _entry("present")])
    rows, _ = collect_local_skill_rows(tmp_path, now=NOW)
    assert len(rows) == 2
    assert rows[0].deprecated is True
    assert rows[1].deprecated is False
    assert all(row.duplicate is True for row in rows)


def test_bad_skill_item_does_not_hide_valid_neighbor(tmp_path: Path) -> None:
    _registry(tmp_path, [_entry("present"), {"name": "bad", "path": 3}])
    rows, notes = collect_local_skill_rows(tmp_path, now=NOW)
    assert [row.name for row in rows] == ["present"]
    assert "SKILL_ENTRY_INVALID" in notes


def test_collectors_do_not_modify_fixture_files(tmp_path: Path) -> None:
    instances, repo, awiki = tmp_path / "instances", tmp_path / "repo", tmp_path / "awiki"
    _instance(instances)
    _contracts(repo)
    _registry(awiki)
    before = {path.relative_to(tmp_path): (path.read_bytes(), path.stat().st_mtime_ns)
              for path in tmp_path.rglob("*") if path.is_file()}
    collect_local_tool_rows(instances, probe=None)
    collect_local_hook_rows(repo)
    collect_local_skill_rows(awiki, now=NOW)
    after = {path.relative_to(tmp_path): (path.read_bytes(), path.stat().st_mtime_ns)
             for path in tmp_path.rglob("*") if path.is_file()}
    assert after == before
