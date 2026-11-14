"""Canonical skill shortlist hint projection (WO-P1-755, SFU26 card 08).

Pure, deterministic consumer of a validated skills-registry snapshot produced
by ``a_conductor.inspector_sources.load_skill_registry`` (or any object with
the same shape: ``entries`` tuple/list of validated registry dicts plus a
``staleness`` string; a zero-argument loader callable may be injected instead
and its failure degrades to the typed unavailable hint).

Matching is trigger-presence only, with NFC+casefold parity against A-Wiki
``scripts/skills_registry/routing.py`` ``normalize()`` — the ONLY parity point.
Documented intentional non-parity vs routing.py:

- no ASCII prefix-boundary regex: substring presence deliberately matches
  ``error`` inside ``terror`` where routing.py's ``(?<![a-z0-9])`` rule would
  not (prefix-boundary with open suffix still agrees on ``errors``);
- no trigger length weights: equal candidate counts order by name;
- no score threshold: a single weak trigger alone can suggest;
- no tier-2 description fallback and no bare-name matching: only declared
  triggers participate;
- no tier-3 a-flow spine: zero matches abstain instead of returning a spine
  entry;
- no stop-list: generic triggers such as ``fix`` still match.

Disposition vocabulary over canonical candidates (deprecated and unresolved
alias matches never count): 0 -> ``ABSTAIN``, exactly 1 -> ``SUGGEST_SINGLE``,
more than 1 -> ``NEEDS_DISAMBIGUATION``. Registry staleness is carried as
``confidence`` labeling (``HIGH``/``STALE``/``UNKNOWN``) and never blocks a
result. The hint is advisory only: ``non_authoritative`` is pinned ``True``
and no field grants execution, claim, routing or admission authority. The
module imports nothing beyond stdlib (dataclasses/unicodedata/hashlib),
performs no clock/network/store I/O beyond the optionally injected loader
call, and never mutates its inputs.
"""

from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import dataclass, field

DISPOSITION_ABSTAIN = "ABSTAIN"
DISPOSITION_SUGGEST_SINGLE = "SUGGEST_SINGLE"
DISPOSITION_NEEDS_DISAMBIGUATION = "NEEDS_DISAMBIGUATION"

REGISTRY_UNAVAILABLE = "SKILLS_REGISTRY_UNAVAILABLE"
INPUT_INVALID = "SKILL_SHORTLIST_INPUT_INVALID"
REGISTRY_OK = "OK"
INPUT_VALID = "VALID"

CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_STALE = "STALE"
CONFIDENCE_UNKNOWN = "UNKNOWN"

MAX_OBJECTIVE_CHARS = 4096

_REGISTRY_STALENESS = frozenset({"AVAILABLE", "STALE", "UNKNOWN"})
_CONFIDENCE_BY_STALENESS = {
    "AVAILABLE": CONFIDENCE_HIGH,
    "STALE": CONFIDENCE_STALE,
    "UNKNOWN": CONFIDENCE_UNKNOWN,
}


@dataclass(frozen=True, slots=True)
class SkillShortlistCandidate:
    """One canonical skill worth considering; advisory metadata only."""

    name: str
    matched_triggers: tuple[str, ...]
    agents: tuple[str, ...]
    invocation_hint: str
    a_phase: str


@dataclass(frozen=True, slots=True)
class DeprecatedSkillMatch:
    """A deprecated registry entry whose triggers matched; never suggested."""

    name: str
    migrated_to: str
    note: str


@dataclass(frozen=True, slots=True)
class SkillShortlistHint:
    """Frozen, non-authoritative shortlist hint; never executes anything."""

    fingerprint: str
    disposition: str
    candidates: tuple[SkillShortlistCandidate, ...]
    deprecated_matches: tuple[DeprecatedSkillMatch, ...]
    unresolved_aliases: tuple[str, ...]
    staleness: str
    confidence: str
    input_status: str
    registry_status: str
    non_authoritative: bool = field(default=True, init=False)


def normalize_query(text: str) -> str:
    """NFC-normalise and casefold — parity point with A-Wiki routing.normalize."""
    return unicodedata.normalize("NFC", text or "").casefold()


def _fingerprint(objective_text: str) -> str:
    return hashlib.sha256(normalize_query(objective_text).encode("utf-8")).hexdigest()


def _entry_name(entry: dict) -> str:
    name = entry.get("name")
    return name if type(name) is str else ""


def _matched_triggers(entry: dict, objective_norm: str) -> list[str]:
    matched: list[str] = []
    seen: set[str] = set()
    for raw in entry.get("triggers", ()):
        if type(raw) is not str:
            continue
        normalized = normalize_query(raw)
        if not normalized or normalized in seen:
            continue
        if normalized in objective_norm:
            seen.add(normalized)
            matched.append(raw)
    return matched


def _resolve_snapshot(registry_snapshot: object) -> tuple[tuple[dict, ...], str] | None:
    """Duck-validate the snapshot contract; None means typed unavailable."""
    if callable(registry_snapshot):
        try:
            registry_snapshot = registry_snapshot()
        except Exception:
            return None
    entries = getattr(registry_snapshot, "entries", None)
    staleness = getattr(registry_snapshot, "staleness", None)
    if type(entries) not in (tuple, list) or type(staleness) is not str:
        return None
    if any(type(entry) is not dict for entry in entries):
        return None
    return tuple(entries), (staleness if staleness in _REGISTRY_STALENESS else "UNKNOWN")


def _ordered_matched(entry: dict, merged: list[str], merged_norms: set[str]) -> tuple[str, ...]:
    """Candidate's own matched triggers (registry order) first, then alias-
    contributed matches in merge order; deduped by normalized form."""
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in entry.get("triggers", ()):
        normalized = normalize_query(raw) if type(raw) is str else ""
        if not normalized or normalized in seen or normalized not in merged_norms:
            continue
        seen.add(normalized)
        ordered.append(raw)
    for raw in merged:
        normalized = normalize_query(raw) if type(raw) is str else ""
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(raw)
    return tuple(ordered)


def _degraded_hint(
    fingerprint: str,
    *,
    staleness: str,
    confidence: str,
    input_status: str,
    registry_status: str,
) -> SkillShortlistHint:
    return SkillShortlistHint(
        fingerprint=fingerprint,
        disposition=DISPOSITION_ABSTAIN,
        candidates=(),
        deprecated_matches=(),
        unresolved_aliases=(),
        staleness=staleness,
        confidence=confidence,
        input_status=input_status,
        registry_status=registry_status,
    )


def project_skill_shortlist(
    objective_text: object,
    registry_snapshot: object,
) -> SkillShortlistHint:
    """Project an objective onto canonical skills as a non-authoritative hint.

    ``registry_snapshot`` is a loaded snapshot object (``entries`` + 
    ``staleness``) or a zero-argument loader callable; loader failures become
    the typed ``SKILLS_REGISTRY_UNAVAILABLE`` hint, never an exception.
    """
    fingerprint = _fingerprint(objective_text) if type(objective_text) is str else ""
    input_valid = (type(objective_text) is str and bool(objective_text.strip())
                   and len(objective_text) <= MAX_OBJECTIVE_CHARS)
    resolved = _resolve_snapshot(registry_snapshot)
    if resolved is None:
        return _degraded_hint(
            fingerprint, staleness="UNKNOWN", confidence=CONFIDENCE_UNKNOWN,
            input_status=INPUT_VALID if input_valid else INPUT_INVALID,
            registry_status=REGISTRY_UNAVAILABLE,
        )
    entries, staleness = resolved
    confidence = _CONFIDENCE_BY_STALENESS[staleness]
    if not input_valid:
        return _degraded_hint(
            fingerprint, staleness=staleness, confidence=confidence,
            input_status=INPUT_INVALID, registry_status=REGISTRY_OK,
        )
    objective_norm = normalize_query(objective_text)
    canonical_targets: dict[str, list[int]] = {}
    for index, entry in enumerate(entries):
        if entry.get("status") == "canonical" and _entry_name(entry):
            canonical_targets.setdefault(_entry_name(entry), []).append(index)
    merged_by_index: dict[int, list[str]] = {}
    merged_norms_by_index: dict[int, set[str]] = {}
    deprecated_matches: list[DeprecatedSkillMatch] = []
    unresolved_aliases: list[str] = []
    for index, entry in enumerate(entries):
        matched = _matched_triggers(entry, objective_norm)
        if not matched:
            continue
        status = entry.get("status")
        if status == "canonical":
            bucket = merged_by_index.setdefault(index, [])
            norms = merged_norms_by_index.setdefault(index, set())
            for raw in matched:
                normalized = normalize_query(raw)
                if normalized not in norms:
                    norms.add(normalized)
                    bucket.append(raw)
        elif status == "deprecated":
            migrated_to = entry.get("migrated_to")
            note = entry.get("note")
            deprecated_matches.append(DeprecatedSkillMatch(
                name=_entry_name(entry),
                migrated_to=migrated_to if type(migrated_to) is str else "",
                note=note if type(note) is str else "",
            ))
        elif status == "alias":
            target = entry.get("canonical")
            target_indices = canonical_targets.get(target, []) if type(target) is str else []
            if target_indices:
                for target_index in target_indices:
                    bucket = merged_by_index.setdefault(target_index, [])
                    norms = merged_norms_by_index.setdefault(target_index, set())
                    for raw in matched:
                        normalized = normalize_query(raw)
                        if normalized not in norms:
                            norms.add(normalized)
                            bucket.append(raw)
            else:
                unresolved_aliases.append(_entry_name(entry))
    ordered_indices = sorted(merged_by_index, key=lambda index: (
        -len(merged_norms_by_index[index]), _entry_name(entries[index]),
    ))
    candidates: list[SkillShortlistCandidate] = []
    for index in ordered_indices:
        entry = entries[index]
        agents = entry.get("agents")
        invocation_hint = entry.get("invocation_hint")
        a_phase = entry.get("a_phase")
        candidates.append(SkillShortlistCandidate(
            name=_entry_name(entry),
            matched_triggers=_ordered_matched(
                entry, merged_by_index[index], merged_norms_by_index[index],
            ),
            agents=tuple(item for item in agents if type(item) is str)
            if type(agents) is list else (),
            invocation_hint=invocation_hint if type(invocation_hint) is str else "",
            a_phase=a_phase if type(a_phase) is str else "",
        ))
    if len(candidates) == 1:
        disposition = DISPOSITION_SUGGEST_SINGLE
    elif candidates:
        disposition = DISPOSITION_NEEDS_DISAMBIGUATION
    else:
        disposition = DISPOSITION_ABSTAIN
    return SkillShortlistHint(
        fingerprint=fingerprint,
        disposition=disposition,
        candidates=tuple(candidates),
        deprecated_matches=tuple(deprecated_matches),
        unresolved_aliases=tuple(unresolved_aliases),
        staleness=staleness,
        confidence=confidence,
        input_status=INPUT_VALID,
        registry_status=REGISTRY_OK,
    )
