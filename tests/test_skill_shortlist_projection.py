"""WO-P1-755 RED contract: canonical skill shortlist hint projection (SFU26 card 08).

Trigger-presence matching with NFC+casefold parity against A-Wiki
routing.py ``normalize()`` and DOCUMENTED non-parity: no ASCII prefix-boundary
regex, no length weights, no threshold, no tier-2 description fallback, no
tier-3 a-flow spine, no stop-list. The projection is deterministic and pure:
zero provider/semantic/typesafe imports, zero clock/network/store I/O beyond
the injected loader call, fixtures are never mutated, and every hint carries
``non_authoritative=True`` with no execution-granting fields.
"""

from __future__ import annotations

import ast
import builtins
import json
import os
import unicodedata
from dataclasses import fields as dc_fields
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

import pytest

from a_conductor.inspector_sources import SkillRegistrySnapshot, load_skill_registry
from a_conductor.skill_shortlist_projection import (
    DISPOSITION_ABSTAIN,
    DISPOSITION_NEEDS_DISAMBIGUATION,
    DISPOSITION_SUGGEST_SINGLE,
    INPUT_INVALID,
    REGISTRY_UNAVAILABLE,
    DeprecatedSkillMatch,
    SkillShortlistCandidate,
    SkillShortlistHint,
    normalize_query,
    project_skill_shortlist,
)

NOW = datetime(2026, 11, 14, 9, 0, tzinfo=timezone.utc)
REGISTRY = "skills-registry.json"


def _skill(name: str, *, triggers: tuple[str, ...] = (), status: str = "canonical",
           canonical: str | None = None, migrated_to: str | None = None,
           note: str | None = None, agents: tuple[str, ...] = ("kilo",),
           invocation_hint: str | None = None, a_phase: str | None = None,
           description: str | None = None) -> dict:
    entry: dict = {
        "name": name, "aliases": [], "domain": ["engineering"],
        "lifecycle_phase": "review", "category": "pipeline", "source": "repo",
        "path": f"skills/awiki/{name}/SKILL.md", "agents": list(agents),
        "version": "1.0.0", "status": status,
    }
    if triggers:
        entry["triggers"] = list(triggers)
    if canonical is not None:
        entry["canonical"] = canonical
    if migrated_to is not None:
        entry["migrated_to"] = migrated_to
    if note is not None:
        entry["note"] = note
    if invocation_hint is not None:
        entry["invocation_hint"] = invocation_hint
    if a_phase is not None:
        entry["a_phase"] = a_phase
    if description is not None:
        entry["description"] = description
    return entry


def _snapshot(entries: list[dict], *, staleness: str = "AVAILABLE") -> SkillRegistrySnapshot:
    valid = tuple(entries)
    return SkillRegistrySnapshot(
        entries=valid,
        entry_states=tuple("AVAILABLE" for _ in valid),
        duplicate_flags=tuple(False for _ in valid),
        invalid_entry_count=0,
        generated_at="2026-11-14",
        staleness=staleness,
        source_path="/fixtures/skills-registry.json",
    )


def _fixture_registry(root: Path, entries: list[dict]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / REGISTRY
    path.write_text(json.dumps({
        "schema_version": 3, "generated_at": "2026-11-14", "skills": entries,
    }, ensure_ascii=False), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Dispositions (0 / 1 / N)
# ---------------------------------------------------------------------------


def test_zero_matches_abstains_without_spine_fallback() -> None:
    entries = [_skill("a-claim", triggers=["claim", "จอง"])]
    hint = project_skill_shortlist("refactor the renderer", _snapshot(entries))
    assert hint.disposition == DISPOSITION_ABSTAIN
    assert hint.candidates == ()
    assert hint.deprecated_matches == ()
    assert hint.non_authoritative is True


def test_single_match_suggests_single_with_candidate_fields() -> None:
    entries = [_skill(
        "a-claim", triggers=["claim", "จอง"], agents=("kilo", "codex"),
        invocation_hint="/a-claim", a_phase="review",
    )]
    hint = project_skill_shortlist("please claim the worker slot", _snapshot(entries))
    assert hint.disposition == DISPOSITION_SUGGEST_SINGLE
    assert len(hint.candidates) == 1
    candidate = hint.candidates[0]
    assert candidate.name == "a-claim"
    assert candidate.matched_triggers == ("claim",)
    assert candidate.agents == ("kilo", "codex")
    assert candidate.invocation_hint == "/a-claim"
    assert candidate.a_phase == "review"


def test_multiple_matches_need_disambiguation_ordered_by_count_then_name() -> None:
    entries = [
        _skill("zz-single", triggers=["deploy"]),
        _skill("aa-triple", triggers=["deploy", "release", "rollback"]),
        _skill("mm-double", triggers=["deploy", "release"]),
    ]
    hint = project_skill_shortlist("deploy release rollback plan", _snapshot(entries))
    assert hint.disposition == DISPOSITION_NEEDS_DISAMBIGUATION
    assert [candidate.name for candidate in hint.candidates] == [
        "aa-triple", "mm-double", "zz-single",
    ]
    assert hint.candidates[0].matched_triggers == ("deploy", "release", "rollback")


# ---------------------------------------------------------------------------
# NFC + casefold parity (the only parity point) and Thai matching
# ---------------------------------------------------------------------------


def test_thai_trigger_matches_mixed_thai_english_objective() -> None:
    entries = [_skill("a-claim", triggers=["claim", "จอง", "coordination"])]
    hint = project_skill_shortlist("ช่วย จอง worker slot แล้ว claim ด้วย", _snapshot(entries))
    assert hint.disposition == DISPOSITION_SUGGEST_SINGLE
    assert hint.candidates[0].name == "a-claim"
    assert hint.candidates[0].matched_triggers == ("claim", "จอง")


def test_nfc_casefold_parity_fingerprint_and_matching() -> None:
    assert normalize_query("CaFe\u0301") == unicodedata.normalize("NFC", "café").casefold()
    entries = [_skill("note-skill", triggers=["café"])]
    nfd_objective = "open the cafe\u0301 notes"
    hint = project_skill_shortlist(nfd_objective, _snapshot(entries))
    assert hint.disposition == DISPOSITION_SUGGEST_SINGLE
    upper = project_skill_shortlist(nfd_objective.upper(), _snapshot(entries))
    assert upper.disposition == DISPOSITION_SUGGEST_SINGLE
    first = project_skill_shortlist(nfd_objective, _snapshot(entries))
    assert first.fingerprint == hint.fingerprint
    assert hint.fingerprint == project_skill_shortlist(
        unicodedata.normalize("NFC", nfd_objective), _snapshot(entries),
    ).fingerprint
    assert hint.fingerprint != project_skill_shortlist(
        "other objective", _snapshot(entries),
    ).fingerprint


# ---------------------------------------------------------------------------
# Documented intentional non-parity vs A-Wiki routing.py
# ---------------------------------------------------------------------------


def test_ascii_substring_matches_without_boundary_rule_intentional_non_parity() -> None:
    """INTENTIONAL NON-PARITY: A-Wiki routing.py gates ASCII triggers behind a
    prefix-boundary regex ``(?<![a-z0-9])trigger``, so ``error`` would NOT hit
    ``terror``. This consumer deliberately matches pure substring presence
    after NFC+casefold (card 08 contract) — presence-only, no boundary rule."""
    entries = [_skill("lint-guard", triggers=["error"])]
    hint = project_skill_shortlist("investigate the terror flake", _snapshot(entries))
    assert hint.disposition == DISPOSITION_SUGGEST_SINGLE
    assert [candidate.name for candidate in hint.candidates] == ["lint-guard"]
    assert hint.candidates[0].matched_triggers == ("error",)


def test_open_suffix_and_non_ascii_substring_remain_parity_directions() -> None:
    """Parity documentation: routing.py matches ASCII triggers with an open
    suffix (``error`` hits ``errors``) and non-ASCII triggers by plain
    substring — both behave identically here."""
    entries = [_skill("lint-guard", triggers=["error"]), _skill("a-claim", triggers=["จอง"])]
    hint = project_skill_shortlist("swallow errors and จอง slots", _snapshot(entries))
    assert hint.disposition == DISPOSITION_NEEDS_DISAMBIGUATION
    assert [candidate.name for candidate in hint.candidates] == ["a-claim", "lint-guard"]


def test_no_score_threshold_weak_trigger_still_suggests_intentional_non_parity() -> None:
    """INTENTIONAL NON-PARITY: routing.py scores ``seo`` (3 chars) at weight 1,
    below DEFAULT_THRESHOLD 2, so it would return nothing; this consumer has
    no threshold and suggests on a single presence match."""
    entries = [_skill("seo-audit", triggers=["seo"])]
    hint = project_skill_shortlist("seo checklist for the launch", _snapshot(entries))
    assert hint.disposition == DISPOSITION_SUGGEST_SINGLE


def test_no_stop_list_generic_trigger_still_matches_intentional_non_parity() -> None:
    """INTENTIONAL NON-PARITY: routing.py drops STOP_TRIGGERS such as ``fix``;
    this consumer has no stop-list."""
    entries = [_skill("a-debug", triggers=["fix"])]
    hint = project_skill_shortlist("fix the broken import", _snapshot(entries))
    assert hint.disposition == DISPOSITION_SUGGEST_SINGLE
    assert hint.candidates[0].name == "a-debug"


def test_no_length_weights_tie_breaks_by_name_intentional_non_parity() -> None:
    """INTENTIONAL NON-PARITY: routing.py weights longer triggers higher, so it
    would rank ``beta`` (9-char trigger) above ``alpha`` (3-char). This
    consumer orders equal-count candidates by name only."""
    entries = [
        _skill("alpha", triggers=["seo"]),
        _skill("beta", triggers=["verylongtriggerphrase"]),
    ]
    hint = project_skill_shortlist("seo plus verylongtriggerphrase", _snapshot(entries))
    assert hint.disposition == DISPOSITION_NEEDS_DISAMBIGUATION
    assert [candidate.name for candidate in hint.candidates] == ["alpha", "beta"]


def test_no_description_fallback_and_no_name_matching() -> None:
    """INTENTIONAL NON-PARITY: no tier-2 description fallback and no bare-name
    matching — only declared triggers participate."""
    entries = [_skill(
        "deploy-service", triggers=["release"],
        description="deploys services to the fleet",
    )]
    hint = project_skill_shortlist("deploys services via deploy-service", _snapshot(entries))
    assert hint.disposition == DISPOSITION_ABSTAIN
    assert hint.candidates == ()


# ---------------------------------------------------------------------------
# Deprecated, alias, duplicate entries
# ---------------------------------------------------------------------------


def test_deprecated_matches_surface_and_are_never_suggested() -> None:
    entries = [
        _skill("old-router", triggers=["route"], status="deprecated",
               migrated_to="a-router", note="catalog consolidation 2026-08-22"),
        _skill("a-router", triggers=["route"]),
    ]
    hint = project_skill_shortlist("route this request", _snapshot(entries))
    assert [candidate.name for candidate in hint.candidates] == ["a-router"]
    assert hint.disposition == DISPOSITION_SUGGEST_SINGLE
    assert len(hint.deprecated_matches) == 1
    match = hint.deprecated_matches[0]
    assert isinstance(match, DeprecatedSkillMatch)
    assert (match.name, match.migrated_to, match.note) == (
        "old-router", "a-router", "catalog consolidation 2026-08-22",
    )


def test_deprecated_match_alone_never_becomes_candidate() -> None:
    entries = [_skill("old-router", triggers=["route"], status="deprecated",
                      migrated_to="a-router", note="gone")]
    hint = project_skill_shortlist("route this request", _snapshot(entries))
    assert hint.candidates == ()
    assert hint.disposition == DISPOSITION_ABSTAIN
    assert [match.name for match in hint.deprecated_matches] == ["old-router"]


def test_alias_resolves_to_present_canonical_target() -> None:
    entries = [
        _skill("claim-shortcut", triggers=["จอง"], status="alias", canonical="a-claim"),
        _skill("a-claim", triggers=["claim"]),
    ]
    hint = project_skill_shortlist("จอง the slot", _snapshot(entries))
    assert hint.disposition == DISPOSITION_SUGGEST_SINGLE
    assert [candidate.name for candidate in hint.candidates] == ["a-claim"]
    assert hint.candidates[0].matched_triggers == ("จอง",)
    assert hint.unresolved_aliases == ()
    assert hint.deprecated_matches == ()


def test_alias_merges_matched_triggers_into_directly_matched_target() -> None:
    entries = [
        _skill("claim-shortcut", triggers=["จอง"], status="alias", canonical="a-claim"),
        _skill("a-claim", triggers=["claim", "จอง"]),
    ]
    hint = project_skill_shortlist("จอง and claim", _snapshot(entries))
    assert hint.candidates[0].matched_triggers == ("claim", "จอง")


def test_alias_with_absent_noncanonical_or_missing_target_is_flagged() -> None:
    missing = _skill("alias-a", triggers=["t1"], status="alias", canonical="ghost-skill")
    deprecated_target = [
        _skill("alias-b", triggers=["t2"], status="alias", canonical="old-router"),
        _skill("old-router", triggers=["t2"], status="deprecated",
               migrated_to="a-router", note="gone"),
    ]
    no_field = _skill("alias-c", triggers=["t3"], status="alias")
    hint = project_skill_shortlist("t1", _snapshot([missing]))
    assert hint.unresolved_aliases == ("alias-a",)
    assert hint.candidates == ()
    hint = project_skill_shortlist("t2", _snapshot(deprecated_target))
    assert hint.unresolved_aliases == ("alias-b",)
    assert hint.candidates == ()
    hint = project_skill_shortlist("t3", _snapshot([no_field]))
    assert hint.unresolved_aliases == ("alias-c",)


def test_duplicate_canonical_names_project_honestly() -> None:
    entries = [
        _skill("dup-skill", triggers=["claim"]),
        _skill("dup-skill", triggers=["book"]),
    ]
    hint = project_skill_shortlist("claim and book", _snapshot(entries))
    assert hint.disposition == DISPOSITION_NEEDS_DISAMBIGUATION
    assert len(hint.candidates) == 2
    assert {candidate.name for candidate in hint.candidates} == {"dup-skill"}


# ---------------------------------------------------------------------------
# Staleness carried, registry failure typed, invalid input typed
# ---------------------------------------------------------------------------


def test_stale_registry_still_returns_results_with_degraded_confidence() -> None:
    entries = [_skill("a-claim", triggers=["claim"])]
    hint = project_skill_shortlist("claim it", _snapshot(entries, staleness="STALE"))
    assert hint.staleness == "STALE"
    assert hint.confidence == "STALE"
    assert hint.disposition == DISPOSITION_SUGGEST_SINGLE
    assert hint.non_authoritative is True


def test_unknown_staleness_carries_unknown_confidence() -> None:
    entries = [_skill("a-claim", triggers=["claim"])]
    hint = project_skill_shortlist("claim it", _snapshot(entries, staleness="UNKNOWN"))
    assert hint.staleness == "UNKNOWN"
    assert hint.confidence == "UNKNOWN"
    assert hint.disposition == DISPOSITION_SUGGEST_SINGLE


def test_injected_loader_failure_returns_typed_unavailable_hint() -> None:
    def broken_loader() -> SkillRegistrySnapshot:
        raise ValueError("SKILLS_REGISTRY_UNAVAILABLE")

    hint = project_skill_shortlist("claim", broken_loader)
    assert hint.registry_status == REGISTRY_UNAVAILABLE
    assert hint.disposition == DISPOSITION_ABSTAIN
    assert hint.candidates == ()
    assert hint.staleness == "UNKNOWN"
    assert hint.confidence == "UNKNOWN"
    assert hint.input_status == "VALID"
    assert hint.non_authoritative is True


def test_foreign_registry_object_fails_closed_unavailable() -> None:
    hint = project_skill_shortlist("claim", object())
    assert hint.registry_status == REGISTRY_UNAVAILABLE
    assert hint.disposition == DISPOSITION_ABSTAIN

    dict_without_shape = {"skills": []}
    hint = project_skill_shortlist("claim", dict_without_shape)
    assert hint.registry_status == REGISTRY_UNAVAILABLE

    def garbage_loader():
        return 42

    hint = project_skill_shortlist("claim", garbage_loader)
    assert hint.registry_status == REGISTRY_UNAVAILABLE


@pytest.mark.parametrize("bad", ["", "   \n\t ", "x" * 4097, 7, None, object()])
def test_invalid_objective_is_typed_marker(bad: object) -> None:
    entries = [_skill("a-claim", triggers=["claim"])]
    hint = project_skill_shortlist(bad, _snapshot(entries))
    assert hint.input_status == INPUT_INVALID
    assert hint.disposition == DISPOSITION_ABSTAIN
    assert hint.candidates == ()
    assert hint.registry_status == "OK"
    assert hint.non_authoritative is True


def test_objective_bound_4096_is_inclusive() -> None:
    entries = [_skill("a-claim", triggers=["claim"])]
    hint = project_skill_shortlist("y" * 4096, _snapshot(entries))
    assert hint.input_status == "VALID"
    hint = project_skill_shortlist("y" * 4097, _snapshot(entries))
    assert hint.input_status == INPUT_INVALID


# ---------------------------------------------------------------------------
# Schema, purity, determinism, no-mutation
# ---------------------------------------------------------------------------


def test_hint_schema_is_frozen_and_never_execution_granting() -> None:
    assert {f.name for f in dc_fields(SkillShortlistHint)} == {
        "fingerprint", "disposition", "candidates", "deprecated_matches",
        "unresolved_aliases", "staleness", "confidence", "input_status",
        "registry_status", "non_authoritative",
    }
    assert {f.name for f in dc_fields(SkillShortlistCandidate)} == {
        "name", "matched_triggers", "agents", "invocation_hint", "a_phase",
    }
    assert {f.name for f in dc_fields(DeprecatedSkillMatch)} == {
        "name", "migrated_to", "note",
    }
    with pytest.raises(TypeError):
        SkillShortlistHint(
            fingerprint="", disposition=DISPOSITION_ABSTAIN, candidates=(),
            deprecated_matches=(), unresolved_aliases=(), staleness="UNKNOWN",
            confidence="UNKNOWN", input_status="VALID", registry_status="OK",
            non_authoritative=False,
        )
    entries = [_skill("a-claim", triggers=["claim"])]
    hint = project_skill_shortlist("claim", _snapshot(entries))
    assert hint.non_authoritative is True
    with pytest.raises(Exception):
        hint.disposition = DISPOSITION_SUGGEST_SINGLE


def test_module_source_imports_are_pure_allowlist() -> None:
    import a_conductor.skill_shortlist_projection as module

    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    assert roots <= {"__future__", "dataclasses", "unicodedata", "hashlib"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            assert "semantic" not in ast.dump(node)
            assert "typesafe" not in ast.dump(node)
            assert "provider" not in ast.dump(node)


def test_runtime_import_graph_has_no_provider_modules() -> None:
    import a_conductor.skill_shortlist_projection as module

    seen: set[int] = set()
    stack = [module]
    while stack:
        current = stack.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        for value in vars(current).values():
            if type(value) is ModuleType:
                stack.append(value)
    names = {item.__name__ for item in seen if type(item) is ModuleType}
    assert not [name for name in names if name.startswith("a_conductor.")]
    assert not [name for name in names
                if any(tag in name for tag in ("semantic", "typesafe", "provider"))]


def test_projection_performs_no_io_and_does_not_mutate_fixtures(
    tmp_path: Path, monkeypatch,
) -> None:
    entries = [
        _skill("a-claim", triggers=["claim", "จอง"]),
        _skill("old-claim", triggers=["book"], status="deprecated",
               migrated_to="a-claim", note="gone"),
    ]
    root = tmp_path / "awiki"
    _fixture_registry(root, entries)
    before = {path.relative_to(tmp_path): (path.read_bytes(), path.stat().st_mtime_ns)
              for path in tmp_path.rglob("*") if path.is_file()}
    snapshot = load_skill_registry(root, max_age_seconds=7 * 24 * 60 * 60, now=NOW)

    def forbidden_open(*args: object, **kwargs: object) -> object:
        raise AssertionError("projection must not perform file I/O")

    monkeypatch.setattr(builtins, "open", forbidden_open)
    try:
        hint = project_skill_shortlist("จอง the slot", snapshot)
    finally:
        monkeypatch.undo()
    assert hint.disposition == DISPOSITION_SUGGEST_SINGLE
    assert hint.candidates[0].name == "a-claim"
    after = {path.relative_to(tmp_path): (path.read_bytes(), path.stat().st_mtime_ns)
             for path in tmp_path.rglob("*") if path.is_file()}
    assert after == before


def test_loader_snapshot_feeds_projection_roundtrip_with_staleness(tmp_path: Path) -> None:
    entries = [
        _skill("a-claim", triggers=["claim", "จอง"], invocation_hint="/a-claim"),
        _skill("a-debug", triggers=["fix"], status="deprecated",
               migrated_to="a-debug-next", note="renamed"),
    ]
    root = tmp_path / "awiki"
    registry = _fixture_registry(root, entries)
    stale = NOW.timestamp() - 8 * 24 * 60 * 60
    os.utime(registry, (stale, stale))
    snapshot = load_skill_registry(root, max_age_seconds=7 * 24 * 60 * 60, now=NOW)
    assert snapshot.staleness == "STALE"
    hint = project_skill_shortlist("จอง slot แล้ว claim และ fix typo", snapshot)
    assert hint.staleness == "STALE"
    assert hint.confidence == "STALE"
    assert hint.disposition == DISPOSITION_SUGGEST_SINGLE
    assert hint.candidates[0].name == "a-claim"
    assert hint.candidates[0].matched_triggers == ("claim", "จอง")
    assert [match.name for match in hint.deprecated_matches] == ["a-debug"]
