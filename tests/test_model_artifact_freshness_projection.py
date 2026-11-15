"""WO-P1-757 (SFU26 card 09) tests: model-intel artifact freshness projection.

Pure-projection contract tests over an injectable artifact snapshot/loader.
The projection must read A-Wiki model artifacts honestly (per-artifact read
state, mtime staleness, embedded timestamp parse states, typed flags,
cross-artifact observations) without touching the clock/network/store beyond
the injected inputs, without echoing raw paths, and without any provider
imports or readiness/exec vocabulary.
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import importlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from a_conductor.model_artifact_freshness_projection import (
    DEFAULT_MAX_AGE_SECONDS_BY_ARTIFACT,
    ModelArtifactEmbeddedFlags,
    ModelArtifactRecord,
    ModelFreshnessNote,
    ModelIntelFreshnessReport,
    project_model_artifact_freshness,
)

NOW = datetime(2026, 11, 15, 12, 0, 0, tzinfo=timezone.utc)

SCOUT_KEY = "model_scout_current"
ROSTER_KEY = "model_roster"
POLICY_KEY = "model_router_policy"
CATALOG_KEY = "model_catalog"
CAPABILITY_KEY = "model_capability_cache"
ALL_KEYS = (SCOUT_KEY, ROSTER_KEY, POLICY_KEY, CATALOG_KEY, CAPABILITY_KEY)

SCRUBBED_PATH = "/Users/aase7en/Library/model-intel/model-scout-current.json"


def _scout_raw(
    *,
    generated_at: str = "2026-11-15T11:00:00+00:00",
    volatile: bool = True,
    offline: bool = False,
    recommendations: dict | None = None,
    extra: dict | None = None,
) -> str:
    body: dict = {
        "generated_at": generated_at,
        "volatile": volatile,
        "offline": offline,
        "recommendations": {"TIER1": ["glm-5.3"]} if recommendations is None else recommendations,
    }
    if extra:
        body.update(extra)
    return json.dumps(body)


def _roster_raw(*, generated_line: str | None = "Generated: 2026-11-14") -> str:
    lines = ["# A-Wiki model roster"]
    if generated_line is not None:
        lines.append(generated_line)
    lines.append('MODEL_TIER1_PRIMARY="glm-5.3"')
    return "\n".join(lines) + "\n"


def _policy_raw(
    *,
    policy_generated_at: str = "2026-08-20T09:12:00",
    scout_echo: str | None = "2026-11-15T11:00:00+00:00",
    seeds: str = "0",
) -> str:
    lines = [
        "Generated: 2026-08-20 09:12:00",
        f'MODEL_ROUTER_POLICY_GENERATED_AT="{policy_generated_at}"',
    ]
    if scout_echo is not None:
        lines.append(f'MODEL_SCOUT_GENERATED_AT="{scout_echo}"')
    lines.append(f'MODEL_IDS_ARE_SEEDS="{seeds}"')
    return "\n".join(lines) + "\n"


def _catalog_raw(*, model_count: int = 2) -> str:
    return json.dumps({"model_count": model_count})


def _capability_raw(*, as_of: str = "2026-10-01T00:00:00+00:00", confidence: str = "training") -> str:
    return json.dumps({"as_of": as_of, "confidence": confidence, "base": "wiki/context/model-roster.conf"})


def _material(raw: str | bytes | None, *, mtime: float | None = None) -> dict:
    return {"raw": raw, "mtime_epoch_seconds": mtime}


def _base_materials() -> dict:
    fresh = NOW.timestamp() - 600.0
    return {
        SCOUT_KEY: _material(_scout_raw(), mtime=fresh),
        ROSTER_KEY: _material(_roster_raw(), mtime=fresh),
        POLICY_KEY: _material(_policy_raw(), mtime=fresh),
        CATALOG_KEY: _material(_catalog_raw(), mtime=fresh),
        CAPABILITY_KEY: _material(_capability_raw(), mtime=fresh),
    }


class _ObjectMaterial:
    def __init__(self, raw, mtime_epoch_seconds=None, source_path=None):
        self.raw = raw
        self.mtime_epoch_seconds = mtime_epoch_seconds
        self.source_path = source_path


class _ObjectSnapshot:
    def __init__(self, artifacts):
        self.artifacts = artifacts


def _project(materials=None, *, now=NOW, **kwargs):
    return project_model_artifact_freshness(
        {"artifacts": _base_materials() if materials is None else materials},
        now=now,
        **kwargs,
    )


def _record_by_key(report: ModelIntelFreshnessReport, key: str) -> ModelArtifactRecord:
    matches = [record for record in report.artifacts if record.artifact_key == key]
    assert len(matches) == 1
    return matches[0]


# ---------------------------------------------------------------------------
# baseline projection shape
# ---------------------------------------------------------------------------


def test_full_snapshot_projects_five_available_records_in_canonical_order() -> None:
    report = _project()

    assert report.degraded is False
    assert report.degraded_reason is None
    assert report.non_authoritative is True
    assert [record.artifact_key for record in report.artifacts] == list(ALL_KEYS)
    for key in ALL_KEYS:
        record = _record_by_key(report, key)
        assert record.read_state == "AVAILABLE"
        assert record.read_reason == "OK"
        assert record.mtime_staleness == "AVAILABLE"
        assert record.file_age_seconds == 600.0
    assert _record_by_key(report, SCOUT_KEY).decision_input_role == (
        "POLICY_TIER_PRIMARY_AND_RACE_OVERRIDE_SOURCE"
    )
    assert _record_by_key(report, ROSTER_KEY).decision_input_role == (
        "POLICY_TIER_SLOTS_FALLBACKS_TIER3_AND_RACE_BASE_SOURCE"
    )
    assert _record_by_key(report, POLICY_KEY).decision_input_role == "COMPOSED_ROUTER_POLICY_SOURCE"
    assert _record_by_key(report, CATALOG_KEY).decision_input_role == "MODEL_MATCH_TIER_PRICE_MATRIX_SOURCE"
    assert _record_by_key(report, CAPABILITY_KEY).decision_input_role == "CAPABILITY_SCORES_BY_FAMILY_SOURCE"


def test_report_records_carry_fingerprint_size_and_typed_flags() -> None:
    report = _project()
    scout = _record_by_key(report, SCOUT_KEY)
    roster = _record_by_key(report, ROSTER_KEY)
    policy = _record_by_key(report, POLICY_KEY)
    catalog = _record_by_key(report, CATALOG_KEY)
    capability = _record_by_key(report, CAPABILITY_KEY)

    raw = _scout_raw().encode("utf-8")
    assert scout.content_fingerprint == hashlib.sha256(raw).hexdigest()
    assert scout.size_bytes == len(raw)
    assert scout.embedded_flags == ModelArtifactEmbeddedFlags(volatile=True, offline=False)
    assert scout.recommendations_empty is False

    assert roster.embedded_flags == ModelArtifactEmbeddedFlags()
    assert roster.recommendations_empty is None
    assert policy.embedded_flags == ModelArtifactEmbeddedFlags(model_ids_are_seeds=False)
    assert catalog.embedded_flags == ModelArtifactEmbeddedFlags(model_count=2)
    assert capability.embedded_flags == ModelArtifactEmbeddedFlags(confidence="training")


def test_bytes_raw_material_fingerprint_and_size() -> None:
    materials = _base_materials()
    materials[CATALOG_KEY] = _material(b'{"model_count": 2}', mtime=NOW.timestamp() - 600.0)
    report = _project(materials)

    catalog = _record_by_key(report, CATALOG_KEY)
    assert catalog.content_fingerprint == hashlib.sha256(b'{"model_count": 2}').hexdigest()
    assert catalog.size_bytes == len(b'{"model_count": 2}')


# ---------------------------------------------------------------------------
# mtime staleness axes
# ---------------------------------------------------------------------------


def test_per_artifact_default_thresholds_differ_and_documented() -> None:
    age_seven_hours = NOW.timestamp() - (7 * 3600.0)
    materials = _base_materials()
    materials[SCOUT_KEY] = _material(_scout_raw(), mtime=age_seven_hours)
    materials[ROSTER_KEY] = _material(_roster_raw(), mtime=age_seven_hours)
    report = _project(materials)

    assert _record_by_key(report, SCOUT_KEY).mtime_staleness == "STALE"
    assert _record_by_key(report, ROSTER_KEY).mtime_staleness == "AVAILABLE"
    assert DEFAULT_MAX_AGE_SECONDS_BY_ARTIFACT[SCOUT_KEY] < DEFAULT_MAX_AGE_SECONDS_BY_ARTIFACT[ROSTER_KEY]
    assert set(DEFAULT_MAX_AGE_SECONDS_BY_ARTIFACT) == set(ALL_KEYS)


def test_injected_max_age_mapping_overrides_defaults_per_artifact() -> None:
    materials = _base_materials()
    materials[SCOUT_KEY] = _material(_scout_raw(), mtime=NOW.timestamp() - 3600.0)
    report = _project(
        materials,
        max_age_seconds={SCOUT_KEY: 60, CATALOG_KEY: 60 * 60 * 24 * 7},
    )
    assert _record_by_key(report, SCOUT_KEY).mtime_staleness == "STALE"


def test_future_mtime_is_unknown_not_stale_or_available() -> None:
    materials = _base_materials()
    materials[SCOUT_KEY] = _material(_scout_raw(), mtime=NOW.timestamp() + 60.0)
    report = _project(materials)

    scout = _record_by_key(report, SCOUT_KEY)
    assert scout.mtime_staleness == "UNKNOWN"
    assert scout.read_state == "AVAILABLE"


def test_missing_mtime_is_unknown_with_no_age() -> None:
    materials = _base_materials()
    materials[SCOUT_KEY] = _material(_scout_raw(), mtime=None)
    report = _project(materials)

    scout = _record_by_key(report, SCOUT_KEY)
    assert scout.mtime_staleness == "UNKNOWN"
    assert scout.file_age_seconds is None
    assert scout.read_state == "AVAILABLE"


# ---------------------------------------------------------------------------
# read-state axes
# ---------------------------------------------------------------------------


def test_absent_artifact_yields_typed_absent_record() -> None:
    materials = _base_materials()
    del materials[CATALOG_KEY]
    report = _project(materials)

    catalog = _record_by_key(report, CATALOG_KEY)
    assert catalog.read_state == "ABSENT"
    assert catalog.read_reason == "ARTIFACT_ABSENT"
    assert catalog.mtime_staleness == "UNKNOWN"
    assert catalog.file_age_seconds is None
    assert catalog.content_fingerprint is None
    assert catalog.size_bytes is None
    assert catalog.embedded_flags == ModelArtifactEmbeddedFlags()
    assert report.degraded is False


def test_loader_signalled_absence_via_none_raw_is_typed_absent() -> None:
    materials = _base_materials()
    materials[CATALOG_KEY] = _material(None)
    report = _project(materials)
    assert _record_by_key(report, CATALOG_KEY).read_state == "ABSENT"


def test_unparseable_json_is_typed_not_failed() -> None:
    materials = _base_materials()
    materials[SCOUT_KEY] = _material("not json {", mtime=NOW.timestamp() - 600.0)
    report = _project(materials)

    scout = _record_by_key(report, SCOUT_KEY)
    assert scout.read_state == "UNPARSEABLE"
    assert scout.read_reason == "EMBEDDED_JSON_INVALID"
    assert scout.mtime_staleness == "AVAILABLE"
    assert scout.generated_at_raw is None
    assert scout.content_fingerprint == hashlib.sha256(b"not json {").hexdigest()


def test_json_wrong_shape_is_typed_unparseable() -> None:
    materials = _base_materials()
    materials[CATALOG_KEY] = _material("[1, 2, 3]", mtime=NOW.timestamp() - 600.0)
    report = _project(materials)
    catalog = _record_by_key(report, CATALOG_KEY)
    assert catalog.read_state == "UNPARSEABLE"
    assert catalog.read_reason == "EMBEDDED_JSON_SHAPE_INVALID"


def test_unparseable_conf_is_typed_not_failed() -> None:
    materials = _base_materials()
    materials[ROSTER_KEY] = _material(":: no keys no header ::", mtime=NOW.timestamp() - 600.0)
    report = _project(materials)

    roster = _record_by_key(report, ROSTER_KEY)
    assert roster.read_state == "UNPARSEABLE"
    assert roster.read_reason == "EMBEDDED_CONF_INVALID"


def test_unreadable_material_is_typed_not_failed() -> None:
    materials = _base_materials()
    materials[SCOUT_KEY] = _material(12345, mtime=NOW.timestamp() - 600.0)
    report = _project(materials)

    scout = _record_by_key(report, SCOUT_KEY)
    assert scout.read_state == "UNREADABLE"
    assert scout.read_reason == "ARTIFACT_MATERIAL_MALFORMED"
    assert scout.mtime_staleness == "UNKNOWN"
    assert scout.content_fingerprint is None


# ---------------------------------------------------------------------------
# embedded timestamp parse-state axes
# ---------------------------------------------------------------------------


def test_offset_iso_timestamp_parses_as_offset() -> None:
    report = _project()
    scout = _record_by_key(report, SCOUT_KEY)
    assert scout.generated_at_raw == "2026-11-15T11:00:00+00:00"
    assert scout.generated_at_parse_state == "PARSED_OFFSET"


def test_z_suffix_offset_timestamp_parses_as_offset() -> None:
    materials = _base_materials()
    materials[SCOUT_KEY] = _material(_scout_raw(generated_at="2026-11-15T11:00:00Z"), mtime=NOW.timestamp() - 600.0)
    report = _project(materials)
    assert _record_by_key(report, SCOUT_KEY).generated_at_parse_state == "PARSED_OFFSET"


def test_naive_local_timestamp_is_labeled_never_converted() -> None:
    report = _project()
    policy = _record_by_key(report, POLICY_KEY)
    assert policy.generated_at_raw == "2026-08-20T09:12:00"
    assert policy.generated_at_parse_state == "PARSED_NAIVE_LOCAL"
    assert "2026-08-20T09:12:00+00:00" not in repr(report)
    assert "2026-08-20T09:12:00Z" not in repr(report)


def test_date_only_roster_header_parses_as_naive_local() -> None:
    report = _project()
    roster = _record_by_key(report, ROSTER_KEY)
    assert roster.generated_at_raw == "2026-11-14"
    assert roster.generated_at_parse_state == "PARSED_NAIVE_LOCAL"


def test_capability_as_of_parses_as_offset() -> None:
    report = _project()
    capability = _record_by_key(report, CAPABILITY_KEY)
    assert capability.generated_at_raw == "2026-10-01T00:00:00+00:00"
    assert capability.generated_at_parse_state == "PARSED_OFFSET"


def test_garbage_timestamp_is_labeled_unparseable_not_failed() -> None:
    materials = _base_materials()
    materials[SCOUT_KEY] = _material(
        _scout_raw(generated_at="not-a-timestamp"), mtime=NOW.timestamp() - 600.0
    )
    report = _project(materials)
    scout = _record_by_key(report, SCOUT_KEY)
    assert scout.read_state == "AVAILABLE"
    assert scout.generated_at_raw == "not-a-timestamp"
    assert scout.generated_at_parse_state == "UNPARSEABLE"


def test_missing_embedded_timestamp_has_no_parse_state() -> None:
    report = _project()
    catalog = _record_by_key(report, CATALOG_KEY)
    assert catalog.generated_at_raw is None
    assert catalog.generated_at_parse_state is None


# ---------------------------------------------------------------------------
# present-but-empty artifacts stay typed AVAILABLE
# ---------------------------------------------------------------------------


def test_empty_scout_recommendations_typed_not_failed() -> None:
    materials = _base_materials()
    materials[SCOUT_KEY] = _material(_scout_raw(recommendations={}), mtime=NOW.timestamp() - 600.0)
    report = _project(materials)

    scout = _record_by_key(report, SCOUT_KEY)
    assert scout.read_state == "AVAILABLE"
    assert scout.read_reason == "OK"
    assert scout.recommendations_empty is True


def test_empty_catalog_model_count_zero_typed_not_failed() -> None:
    materials = _base_materials()
    materials[CATALOG_KEY] = _material(_catalog_raw(model_count=0), mtime=NOW.timestamp() - 600.0)
    report = _project(materials)

    catalog = _record_by_key(report, CATALOG_KEY)
    assert catalog.read_state == "AVAILABLE"
    assert catalog.embedded_flags == ModelArtifactEmbeddedFlags(model_count=0)


# ---------------------------------------------------------------------------
# cross-artifact observations
# ---------------------------------------------------------------------------


def test_roster_newer_than_policy_emits_drift_note_with_values() -> None:
    report = _project()
    drift_notes = [note for note in report.observations if note.note_kind == "ROSTER_NEWER_THAN_POLICY"]
    assert len(drift_notes) == 1
    note = drift_notes[0]
    assert note.severity == "DRIFT"
    assert note.left_raw == "2026-11-14"
    assert note.right_raw == "2026-08-20T09:12:00"
    assert note.comparison_basis == "NAIVE_LOCAL_WALL"
    assert note.left_label == "model_roster"
    assert note.right_label == "model_router_policy"


def test_roster_older_than_policy_emits_no_drift_note() -> None:
    materials = _base_materials()
    materials[ROSTER_KEY] = _material(_roster_raw(generated_line="Generated: 2026-08-19"), mtime=NOW.timestamp() - 600.0)
    report = _project(materials)
    assert not [note for note in report.observations if note.note_kind == "ROSTER_NEWER_THAN_POLICY"]


def test_scout_echo_mismatch_emits_note_with_both_values() -> None:
    materials = _base_materials()
    materials[POLICY_KEY] = _material(
        _policy_raw(scout_echo="2026-11-15T10:00:00+00:00"), mtime=NOW.timestamp() - 600.0
    )
    report = _project(materials)

    mismatch_notes = [note for note in report.observations if note.note_kind == "SCOUT_ECHO_MISMATCH"]
    assert len(mismatch_notes) == 1
    note = mismatch_notes[0]
    assert note.severity == "MISMATCH"
    assert note.left_raw == "2026-11-15T10:00:00+00:00"
    assert note.right_raw == "2026-11-15T11:00:00+00:00"
    assert note.comparison_basis == "OFFSET_INSTANT"


def test_matching_scout_echo_emits_no_note() -> None:
    materials = _base_materials()
    materials[POLICY_KEY] = _material(
        _policy_raw(scout_echo="2026-11-15T11:00:00Z"), mtime=NOW.timestamp() - 600.0
    )
    report = _project(materials)
    assert not [note for note in report.observations if note.note_kind == "SCOUT_ECHO_MISMATCH"]


def test_seeds_active_emits_warning_note() -> None:
    materials = _base_materials()
    materials[POLICY_KEY] = _material(_policy_raw(seeds="1"), mtime=NOW.timestamp() - 600.0)
    report = _project(materials)

    seeds_notes = [note for note in report.observations if note.note_kind == "SEEDS_ACTIVE"]
    assert len(seeds_notes) == 1
    note = seeds_notes[0]
    assert note.severity == "WARNING"
    assert note.left_raw == "1"
    assert note.left_label == "model_router_policy.MODEL_IDS_ARE_SEEDS"
    assert note.right_raw is None
    assert note.comparison_basis is None


def test_comparison_skipped_when_either_side_does_not_parse() -> None:
    materials = _base_materials()
    materials[ROSTER_KEY] = _material(_roster_raw(generated_line=None), mtime=NOW.timestamp() - 600.0)
    materials[POLICY_KEY] = _material(
        _policy_raw(scout_echo="garbage"), mtime=NOW.timestamp() - 600.0
    )
    report = _project(materials)

    kinds = {note.note_kind for note in report.observations}
    assert "ROSTER_NEWER_THAN_POLICY" not in kinds
    assert "SCOUT_ECHO_MISMATCH" not in kinds
    assert report.degraded is False


# ---------------------------------------------------------------------------
# path scrubbing / authority vocabulary / purity / structure
# ---------------------------------------------------------------------------


def test_raw_paths_never_appear_in_report_output() -> None:
    materials = {
        SCOUT_KEY: _ObjectMaterial(
            _scout_raw(extra={"source": SCRUBBED_PATH}),
            mtime_epoch_seconds=NOW.timestamp() - 600.0,
            source_path=SCRUBBED_PATH,
        ),
        ROSTER_KEY: _ObjectMaterial(_roster_raw(), mtime_epoch_seconds=NOW.timestamp() - 600.0),
        POLICY_KEY: _ObjectMaterial(_policy_raw(), mtime_epoch_seconds=NOW.timestamp() - 600.0),
        CATALOG_KEY: _ObjectMaterial(_catalog_raw(), mtime_epoch_seconds=NOW.timestamp() - 600.0),
        CAPABILITY_KEY: _ObjectMaterial(_capability_raw(), mtime_epoch_seconds=NOW.timestamp() - 600.0),
    }
    report = project_model_artifact_freshness(_ObjectSnapshot(materials), now=NOW)

    assert report.degraded is False
    rendered = repr(report) + str(report)
    assert SCRUBBED_PATH not in rendered
    assert "/Users/aase7en" not in rendered
    for record in report.artifacts:
        blob = repr(record) + str(record)
        assert SCRUBBED_PATH not in blob
        assert "/Users/aase7en" not in blob
    names = {field.name for field in dataclasses.fields(ModelArtifactRecord)}
    names |= {field.name for field in dataclasses.fields(ModelIntelFreshnessReport)}
    names |= {field.name for field in dataclasses.fields(ModelFreshnessNote)}
    names |= {field.name for field in dataclasses.fields(ModelArtifactEmbeddedFlags)}
    assert "source_path" not in names


def test_report_is_non_authoritative_and_free_of_readiness_exec_vocabulary() -> None:
    report = _project()
    assert report.non_authoritative is True
    with pytest.raises(TypeError):
        ModelIntelFreshnessReport(artifacts=(), observations=(), non_authoritative=False)

    banned_markers = ("ready", "authoriz", "execut", "activate", "purchase", "refresh")
    for cls in (ModelIntelFreshnessReport, ModelArtifactRecord, ModelFreshnessNote, ModelArtifactEmbeddedFlags):
        for field in dataclasses.fields(cls):
            lowered = field.name.lower()
            assert not any(marker in lowered for marker in banned_markers), (cls.__name__, field.name)


def test_module_has_zero_provider_imports_and_stays_pure() -> None:
    module = importlib.import_module("a_conductor.model_artifact_freshness_projection")
    source = Path(module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])

    allowed = {"__future__", "collections", "dataclasses", "datetime", "hashlib", "json", "typing"}
    assert imported <= allowed, imported
    assert not any(name.startswith("provider") for name in imported)


def test_dataclasses_are_frozen_and_slotted() -> None:
    report = _project()
    record = report.artifacts[0]
    pinned = (
        (report, "degraded"),
        (record, "read_state"),
        (record.embedded_flags, "volatile"),
    )
    for obj, field_name in pinned:
        assert not hasattr(obj, "__dict__")
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(obj, field_name, "tampered")


# ---------------------------------------------------------------------------
# injectable now / thresholds validation
# ---------------------------------------------------------------------------


def test_naive_now_fails_closed() -> None:
    with pytest.raises(ValueError, match="aware datetime"):
        project_model_artifact_freshness({"artifacts": _base_materials()}, now=datetime(2026, 11, 15, 12, 0, 0))


@pytest.mark.parametrize("bad", [-1, True, "600", 1.5j])
def test_invalid_max_age_fails_closed(bad) -> None:
    with pytest.raises(ValueError, match="max_age_seconds"):
        project_model_artifact_freshness({"artifacts": _base_materials()}, now=NOW, max_age_seconds=bad)


def test_unknown_max_age_mapping_key_fails_closed() -> None:
    with pytest.raises(ValueError, match="unknown artifact key"):
        project_model_artifact_freshness(
            {"artifacts": _base_materials()}, now=NOW, max_age_seconds={"bogus_key": 60}
        )


# ---------------------------------------------------------------------------
# loader-injection axes
# ---------------------------------------------------------------------------


def test_loader_success_yields_full_report() -> None:
    report = project_model_artifact_freshness(lambda: {"artifacts": _base_materials()}, now=NOW)
    assert report.degraded is False
    assert len(report.artifacts) == len(ALL_KEYS)


def test_loader_failure_yields_typed_degraded_report_not_exception() -> None:
    def _raising_loader():
        raise RuntimeError("simulated loader outage")

    report = project_model_artifact_freshness(_raising_loader, now=NOW)
    assert report.degraded is True
    assert report.degraded_reason == "LOADER_FAILURE"
    assert report.artifacts == ()
    assert report.observations == ()
    assert report.non_authoritative is True


def test_snapshot_shape_failure_yields_typed_degraded_report_not_exception() -> None:
    report = project_model_artifact_freshness(42, now=NOW)
    assert report.degraded is True
    assert report.degraded_reason == "SNAPSHOT_SHAPE_INVALID"
    assert report.artifacts == ()
    assert report.non_authoritative is True
