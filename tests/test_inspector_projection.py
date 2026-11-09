"""WO-P1-739: RED-first fixture matrix for the inspector read-only projection.

Encodes the WO §4 matrix over three injected evidence ports (registry
snapshot, hook evidence, tool evidence). All inputs are plain data; the
projection must never read live state, never infer per-item health from
bus-level signals, and never emit health where the evidence contract does
not define it. Secrets fed into any emitted field position must come out
redacted. Same inputs must produce an identical view twice.
"""
from __future__ import annotations

import copy
import dataclasses
import json

import pytest

from a_conductor.inspector_projection import (
    InspectorProjectionError,
    build_inspector_view,
    default_secret_predicate,
)

NOW = "2026-11-09T08:00:00+00:00"
FRESH = "2026-11-09T07:59:30+00:00"  # 30s old (< default max age 900s)
OLD = "2026-11-09T07:00:00+00:00"  # 1h old (> default max age 900s)
FUTURE = "2026-11-09T09:00:00+00:00"  # 1h in the future of NOW (negative age)

SECRET_TOKEN = "ghp_A1b2C3d4E5f6G7h8I9j0K2l3M4n5"
SECRET_KEY = "sk-proj-9f8e7d6c5b4a392817465544332211ff"


def registry_port(items=(), *, missing=False, present=True):
    port = {"items": list(items)}
    if missing:
        port["missing"] = True
    if not present:
        port["present"] = False
    return port


def reg_item(item_id, kind, *, route="hooks/claim-apply", source="a-wiki:registry@main",
             revision="rev-1", observed_at=FRESH):
    entry = {"item_id": item_id, "kind": kind, "route": route, "source": source}
    if revision is not None:
        entry["revision"] = revision
    if observed_at is not None:
        entry["observed_at"] = observed_at
    return entry


def hook_port(items, *, bus=None):
    port = {"items": list(items)}
    if bus is not None:
        port["bus"] = bus
    return port


def hook_record(item_id, *, classification="hard", available=True, observed_at=FRESH,
                source="hookbus:snapshot-42", revision=None, observation_id="obs-1"):
    record = {"item_id": item_id, "source": source, "observed_at": observed_at,
              "observation_id": observation_id}
    if revision is not None:
        record["revision"] = revision
    if classification is not None:
        record["classification"] = classification
    if available is not None:
        record["available"] = available
    return record


def tool_port(items):
    return {"items": list(items)}


def tool_record(item_id, *, connection="connected", available=True, observed_at=FRESH,
                source="device-probe", revision=None, observation_id="obs-2"):
    record = {"item_id": item_id, "source": source, "observed_at": observed_at,
              "observation_id": observation_id}
    if revision is not None:
        record["revision"] = revision
    if connection is not None:
        record["device_connection"] = connection
    if available is not None:
        record["available"] = available
    return record


def build(registry=None, hooks=None, tools=None, **kwargs):
    return build_inspector_view(
        registry if registry is not None else registry_port([reg_item("h1", "hook")]),
        hooks if hooks is not None else hook_port([]),
        tools if tools is not None else tool_port([]),
        now=NOW, **kwargs,
    )


def item_by_id(view, item_id):
    matches = [i for i in view.items if i.item_id == item_id]
    assert len(matches) == 1, f"expected exactly one {item_id!r} item, got {matches}"
    return matches[0]


def serialized(view):
    return json.dumps(dataclasses.asdict(view), sort_keys=True)


# --- 1. absent registration -> UNKNOWN + reason, never READY --------------

def test_absent_registration_is_unknown_not_ready():
    view = build(
        registry=registry_port([]),  # registry exists but item is absent
        hooks=hook_port([hook_record("orphan-hook", available=True, observed_at=FRESH)]),
    )
    item = item_by_id(view, "orphan-hook")
    assert item.state == "UNKNOWN"
    assert item.reason == "absent-registration"
    assert item.availability == "asserted"  # evidence is visible, but...
    assert item.state != "READY"


# --- 2. stale evidence -> STALE + reason ----------------------------------

def test_stale_evidence_is_stale_with_reason():
    view = build(
        registry=registry_port([reg_item("t1", "tool", route="devices/t1")]),
        tools=tool_port([tool_record("t1", available=True, observed_at=OLD)]),
    )
    item = item_by_id(view, "t1")
    assert item.state == "STALE"
    assert item.reason == "stale-evidence"
    assert item.state != "READY"


def test_stale_evidence_respects_explicit_max_age():
    view = build(
        registry=registry_port([reg_item("t1", "tool")]),
        tools=tool_port([tool_record("t1", available=True, observed_at=FRESH)]),
        max_age_seconds=10,  # 30s-old evidence is stale under a tighter rule
    )
    assert item_by_id(view, "t1").state == "STALE"


# --- 3. disconnected device -> DISCONNECTED + reason, no health claims ----

def test_disconnected_device_is_disconnected_no_health_claims():
    view = build(
        registry=registry_port([reg_item("pi5", "tool", route="devices/pi5")]),
        tools=tool_port([tool_record("pi5", connection="disconnected",
                                     available=True, observed_at=FRESH)]),
    )
    item = item_by_id(view, "pi5")
    assert item.state == "DISCONNECTED"
    assert item.reason == "disconnected-device"
    assert item.availability == "unavailable"
    # even available=True must not yield any health claim while disconnected
    assert item.state not in ("READY", "DEGRADED")


# --- 4. duplicate startup -> UNKNOWN + duplicate-startup, no arbitrary pick

def test_duplicate_startup_is_unknown_no_arbitrary_pick():
    records = [
        hook_record("h1", available=True, observed_at=FRESH,
                    source="hookbus:snapshot-42", observation_id="obs-1"),
        hook_record("h1", available=False, observed_at=FRESH,
                    source="hookbus:snapshot-42", observation_id="obs-2"),
    ]
    view = build(
        registry=registry_port([reg_item("h1", "hook")]),
        hooks=hook_port(records),
    )
    item = item_by_id(view, "h1")
    assert item.state == "UNKNOWN"
    assert item.reason == "duplicate-startup"
    assert item.state != "READY"


# --- 5. HookBus backpressure -> bus DEGRADED only, hooks stay UNKNOWN -----

def test_hookbus_backpressure_degrades_bus_not_individual_hooks():
    bus = {"backpressure": True, "conditions": ["queue-saturated"],
           "observed_at": FRESH, "source": "hookbus:health"}
    view = build(
        registry=registry_port([reg_item("h1", "hook")]),
        hooks=hook_port([
            # fresh observation, but availability is NOT asserted:
            hook_record("h1", classification="hard", available=None,
                        observed_at=FRESH),
        ], bus=bus),
    )
    assert view.hook_bus.degraded is True
    assert view.hook_bus.state == "DEGRADED"
    assert view.hook_bus.reason == "bus-backpressure"
    hook = item_by_id(view, "h1")
    assert hook.state == "UNKNOWN"
    assert hook.reason == "availability-not-asserted"
    assert hook.state != "DEGRADED"


def test_bus_view_is_unknown_without_bus_evidence():
    view = build(hooks=hook_port([]))
    assert view.hook_bus.state == "UNKNOWN"
    assert view.hook_bus.degraded is False


# --- 6. missing skill registry -> UNKNOWN + missing-registry, not an error -

def test_missing_skill_registry_is_unknown_not_error():
    view = build(
        registry=registry_port([], missing=True),  # explicit missing flag
        tools=tool_port([tool_record("t1", available=True, observed_at=FRESH)]),
    )
    assert view.registry_missing is True
    item = item_by_id(view, "t1")
    assert item.state == "UNKNOWN"
    assert item.reason == "missing-registry"
    assert item.state != "READY"
    assert view.items  # empty registry list is not an error


def test_registry_absent_flag_via_present_false_is_missing():
    view = build(
        registry=registry_port([], present=False),
        hooks=hook_port([hook_record("h1", available=True)]),
    )
    assert view.registry_missing is True
    assert item_by_id(view, "h1").reason == "missing-registry"


# --- 7. secret redaction across every emitted field position ---------------

def test_secret_redaction_across_facts_reasons_and_source_metadata():
    view = build(
        registry=registry_port([
            reg_item(SECRET_KEY, "hook", route=f"hooks/{SECRET_TOKEN}",
                     source=f"registry?token={SECRET_TOKEN}"),
            reg_item("t1", "tool", route=f"devices/pi5?key={SECRET_KEY}",
                     source=f"device?password={SECRET_TOKEN}"),
        ]),
        hooks=hook_port([
            hook_record(SECRET_KEY, classification="hard",
                        available=True, source=f"hookbus?token={SECRET_TOKEN}"),
        ], bus={"backpressure": True, "conditions": [f"queue:{SECRET_TOKEN}"],
                "observed_at": FRESH, "source": f"hookbus?secret={SECRET_TOKEN}"}),
        tools=tool_port([
            tool_record("t1", available=True, source=f"probe?api_key={SECRET_TOKEN}"),
        ]),
    )
    text = serialized(view)
    assert SECRET_TOKEN not in text
    assert SECRET_KEY not in text
    # redacted placeholders must actually appear at the injected positions
    assert "[REDACTED]" in text
    for item in view.items:
        for value in item.facts.values():
            assert SECRET_TOKEN not in value and SECRET_KEY not in value
        assert SECRET_TOKEN not in item.source and SECRET_KEY not in item.source
        assert SECRET_TOKEN not in item.reason and SECRET_KEY not in item.reason
    for condition in view.hook_bus.conditions:
        assert SECRET_TOKEN not in condition
    assert SECRET_TOKEN not in view.hook_bus.source


def test_injectable_redactor_covers_every_emitted_value_including_reasons():
    redact_everything = lambda field_name, value: True  # noqa: E731
    view = build(secret_predicate=redact_everything)
    text = serialized(view)
    assert "[REDACTED]" in text
    assert "hooks/claim-apply" not in text
    assert "a-wiki:registry@main" not in text
    assert "hookbus:snapshot-42" not in text
    # even emitted item ids pass through the injected redactor
    assert all(item.item_id == "[REDACTED]" for item in view.items)
    hook = next(item for item in view.items if item.domain == "hook")
    assert hook.facts["route"] == "[REDACTED]"
    assert hook.source == "[REDACTED]"
    # facts and source metadata are covered; the emitted reason vocabulary
    # passes through the same redactor pipeline (defensive, uniform).
    assert all(
        value == "[REDACTED]"
        for item in view.items
        for value in item.facts.values()
    )


def test_default_secret_predicate_flags_named_and_high_entropy_values():
    assert default_secret_predicate("api_key", "ordinary-value") is True
    assert default_secret_predicate("route", "hooks/claim-apply") is False
    assert default_secret_predicate("source", "hookbus:snapshot-42") is False
    assert default_secret_predicate("route", SECRET_TOKEN) is True
    assert default_secret_predicate("anything", "aaaaaaaaaaaaaaaaaaaaaaaa") is False


# --- 8. happy path: full evidence -> defined states + provenance facts ----

def test_happy_path_full_evidence_yields_ready_with_provenance():
    view = build(
        registry=registry_port([
            reg_item("h1", "hook", route="hooks/claim-apply"),
            reg_item("pi5", "tool", route="devices/pi5"),
        ]),
        hooks=hook_port([
            # correlated to the registration record (source + revision match)
            hook_record("h1", classification="hard", available=True,
                        observed_at=FRESH, source="a-wiki:registry@main",
                        revision="rev-1"),
        ], bus={"backpressure": False, "observed_at": FRESH}),
        tools=tool_port([
            tool_record("pi5", connection="connected", available=True,
                        observed_at=FRESH, source="a-wiki:registry@main",
                        revision="rev-1"),
        ]),
    )
    hook = item_by_id(view, "h1")
    assert hook.state == "READY"
    assert hook.reason == "ready-evidence"
    assert hook.domain == "hook"
    assert hook.availability == "asserted"
    assert hook.source == "a-wiki:registry@main"  # registration-correlated provenance
    assert hook.observed_at == FRESH
    assert hook.facts["route"] == "hooks/claim-apply"
    assert hook.facts["kind"] == "hook"
    assert hook.facts["classification"] == "hard"  # verbatim hard/soft

    tool = item_by_id(view, "pi5")
    assert tool.state == "READY"
    assert tool.domain == "tool"
    assert tool.facts["route"] == "devices/pi5"

    # A-Wiki classification is hard/soft verbatim, never OBSERVE/GUARD.
    text = serialized(view)
    assert "OBSERVE" not in text and "GUARD" not in text
    assert view.hook_bus.degraded is False
    assert view.hook_bus.state == "UNKNOWN"  # no contract-defined bus READY


def test_registered_item_without_evidence_is_unknown_not_ready():
    view = build(registry=registry_port([reg_item("h2", "hook")]),
                 hooks=hook_port([]))
    item = item_by_id(view, "h2")
    assert item.state == "UNKNOWN"
    assert item.reason == "no-evidence"
    assert item.availability == "absent"
    assert item.source == "a-wiki:registry@main"  # registration provenance


def test_explicit_unavailable_evidence_never_implies_healthy():
    view = build(
        registry=registry_port([reg_item("h1", "hook")]),
        hooks=hook_port([hook_record("h1", available=False, observed_at=FRESH)]),
    )
    item = item_by_id(view, "h1")
    assert item.state == "UNKNOWN"
    assert item.reason == "availability-false"


def test_unparseable_observed_at_is_freshness_unknown():
    view = build(
        registry=registry_port([reg_item("h1", "hook")]),
        hooks=hook_port([hook_record("h1", available=True,
                                     observed_at="not-a-timestamp")]),
    )
    item = item_by_id(view, "h1")
    assert item.state == "UNKNOWN"
    assert item.reason == "freshness-unobserved"


# --- 9. unrecognized input fields dropped (fail closed to allowlist) ------

def test_unrecognized_input_fields_dropped():
    registry_item = reg_item("h1", "hook")
    registry_item.update({"env": "prod", "admin_token": SECRET_TOKEN,
                          "raw_payload": {"nested": True}})
    hook_rec = hook_record("h1", available=True)
    hook_rec.update({"cookies": "session=xyz", "notes": "internal note"})
    snapshot = registry_port([registry_item])
    snapshot.update({"debug": True, "operator_note": "scratch"})
    hook_port_data = hook_port([hook_rec])
    hook_port_data.update({"trace": "leak-me"})
    view = build(registry=snapshot, hooks=hook_port_data)
    text = serialized(view)
    assert "env" not in text and "admin_token" not in text
    assert "raw_payload" not in text and "nested" not in text
    assert "cookies" not in text and "notes" not in text
    assert "debug" not in text and "operator_note" not in text
    assert "trace" not in text and "leak-me" not in text
    hook = item_by_id(view, "h1")
    assert set(hook.facts) <= {"kind", "route", "classification"}


# --- 10. determinism: same inputs -> identical output twice ---------------

def test_deterministic_same_inputs_identical_output_twice():
    registry = registry_port([reg_item("h1", "hook"), reg_item("pi5", "tool")])
    hooks = hook_port([hook_record("h1", classification="soft", available=True)],
                      bus={"backpressure": False, "observed_at": FRESH})
    tools = tool_port([tool_record("pi5", available=True)])
    first = build_inspector_view(registry, hooks, tools, now=NOW)
    second = build_inspector_view(registry, hooks, tools, now=NOW)
    assert first == second
    assert serialized(first) == serialized(second)
    assert repr(first) == repr(second)


def test_projection_is_pure_does_not_mutate_inputs():
    registry = registry_port([reg_item("h1", "hook")])
    hooks = hook_port([hook_record("h1", available=True)])
    tools = tool_port([tool_record("pi5", available=True)])
    registry_before = copy.deepcopy(registry)
    hooks_before = copy.deepcopy(hooks)
    tools_before = copy.deepcopy(tools)
    build_inspector_view(registry, hooks, tools, now=NOW)
    assert registry == registry_before
    assert hooks == hooks_before
    assert tools == tools_before


# --- malformed input is typed-rejected (fail closed, never fabricated) ----

def test_malformed_inputs_are_typed_rejected():
    with pytest.raises(InspectorProjectionError):
        build_inspector_view(None, hook_port([]), tool_port([]), now=NOW)
    with pytest.raises(InspectorProjectionError):
        build(registry=registry_port([{"kind": "hook"}]))  # missing item_id
    with pytest.raises(InspectorProjectionError):
        build(hooks=hook_port([hook_record("h1", available="yes")]))  # non-bool
    with pytest.raises(InspectorProjectionError):
        build(hooks=hook_port([hook_record("h1", observed_at=42)]))  # non-str
    with pytest.raises(InspectorProjectionError):
        build_inspector_view(registry_port([]), hook_port([]), tool_port([]),
                             now="not-a-timestamp")
    with pytest.raises(InspectorProjectionError):
        build(max_age_seconds=0)


# ===========================================================================
# Repair round 1 RED tests (independent review R1 findings F1-F6)
# ===========================================================================

# --- F1: embedded credential segments + composing custom predicate --------

def test_embedded_low_entropy_credential_segments_are_scrubbed():
    view = build(
        registry=registry_port([
            reg_item("h1", "hook", source="a-wiki:registry@main?password=abcd1234"),
            reg_item("h2", "hook", source="a-wiki:registry@main"),
        ]),
        hooks=hook_port([
            hook_record("h2", available=True, source="hookbus:label?token=abc123"),
        ]),
    )
    text = serialized(view)
    assert "abcd1234" not in text
    assert "abc123" not in text
    h1 = item_by_id(view, "h1")
    assert h1.source == "a-wiki:registry@main?password=[REDACTED]"
    h2 = item_by_id(view, "h2")
    assert h2.source == "hookbus:label?token=[REDACTED]"


def test_bearer_credential_segments_are_scrubbed():
    view = build(
        registry=registry_port([reg_item("h2", "hook", source="a-wiki:registry@main")]),
        hooks=hook_port([hook_record("h2", available=True,
                                     source="hookbus:probe Bearer abc123xyz")]),
    )
    text = serialized(view)
    assert "abc123xyz" not in text
    assert item_by_id(view, "h2").source == "hookbus:probe Bearer [REDACTED]"


def test_custom_predicate_composes_with_default_strategy():
    def custom(field_name, value):
        return value == "custom-marked"

    view = build(
        registry=registry_port([
            reg_item("h1", "hook", source="a-wiki:registry@main"),
            reg_item("h2", "hook", source="a-wiki:registry@main?password=abcd1234"),
        ]),
        hooks=hook_port([hook_record("h1", available=True, source="custom-marked")]),
        secret_predicate=custom,
    )
    text = serialized(view)
    assert "custom-marked" not in text  # custom predicate fired (h1 evidence source)
    assert "abcd1234" not in text       # default strategy still applied (h2 registration)


def test_default_secret_predicate_detects_embedded_credential_segments():
    assert default_secret_predicate("source", "hookbus:label?token=abc123") is True
    assert default_secret_predicate("route", "hooks/x?password=abcd1234") is True
    assert default_secret_predicate("route", "hooks/claim-apply") is False
    assert default_secret_predicate("route", "hooks/x Bearer abc123") is True


# --- F2: READY requires provenance, fresh registration, correlation, domain -

def test_ready_requires_non_empty_registration_source_and_revision():
    view = build(
        registry=registry_port([reg_item("h1", "hook", revision=None)]),
        hooks=hook_port([hook_record("h1", available=True,
                                     source="a-wiki:registry@main", revision="rev-1")]),
    )
    item = item_by_id(view, "h1")
    assert item.state == "UNKNOWN"
    assert item.reason == "provenance-missing"
    assert item.state != "READY"


def test_ready_requires_fresh_registration_observation():
    view = build(
        registry=registry_port([reg_item("h1", "hook", observed_at=OLD)]),
        hooks=hook_port([hook_record("h1", available=True,
                                     source="a-wiki:registry@main", revision="rev-1")]),
    )
    item = item_by_id(view, "h1")
    assert item.state == "UNKNOWN"
    assert item.reason == "registration-stale"


def test_ready_requires_correlated_evidence_source_and_revision():
    # reviewer probe: READY emitted with evidence source=None
    view = build(
        registry=registry_port([reg_item("h1", "hook")]),
        hooks=hook_port([hook_record("h1", available=True, source=None,
                                     revision="rev-1")]),
    )
    item = item_by_id(view, "h1")
    assert item.state == "UNKNOWN"
    assert item.reason == "evidence-uncorrelated"
    assert item.state != "READY"

    # uncorrelated source identity
    view = build(
        registry=registry_port([reg_item("h1", "hook")]),
        hooks=hook_port([hook_record("h1", available=True, source="hookbus:snapshot-42",
                                     revision="rev-1")]),
    )
    assert item_by_id(view, "h1").reason == "evidence-uncorrelated"

    # revision mismatch
    view = build(
        registry=registry_port([reg_item("h1", "hook")]),
        hooks=hook_port([hook_record("h1", available=True,
                                     source="a-wiki:registry@main", revision="rev-9")]),
    )
    assert item_by_id(view, "h1").reason == "evidence-uncorrelated"


def test_ready_rejects_cross_domain_evidence():
    # reviewer probe: hook-port evidence justifying a TOOL registration
    view = build(
        registry=registry_port([reg_item("t1", "tool", route="devices/t1")]),
        hooks=hook_port([hook_record("t1", available=True,
                                     source="a-wiki:registry@main", revision="rev-1")]),
    )
    item = item_by_id(view, "t1")
    assert item.state == "UNKNOWN"
    assert item.reason == "domain-mismatch"
    assert item.domain == "tool"
    assert item.state != "READY"

    # mirror probe: tool-port evidence against a hook registration
    view = build(
        registry=registry_port([reg_item("h1", "hook")]),
        tools=tool_port([tool_record("h1", available=True,
                                     source="a-wiki:registry@main", revision="rev-1")]),
    )
    assert item_by_id(view, "h1").reason == "domain-mismatch"


# --- F3: future-dated observations are invalid, bus freshness checked first -

def test_future_dated_item_evidence_is_freshness_invalid_not_ready():
    view = build(
        registry=registry_port([reg_item("h1", "hook")]),
        hooks=hook_port([hook_record("h1", available=True, observed_at=FUTURE)]),
    )
    item = item_by_id(view, "h1")
    assert item.state == "UNKNOWN"
    assert item.reason == "freshness-invalid"
    assert item.state != "READY"


def test_old_bus_evidence_with_backpressure_is_stale_not_degraded():
    bus = {"backpressure": True, "conditions": ["queue-saturated"],
           "observed_at": OLD, "source": "hookbus:health"}
    view = build(hooks=hook_port([], bus=bus))
    assert view.hook_bus.state == "STALE"
    assert view.hook_bus.reason == "bus-evidence-stale"
    assert view.hook_bus.degraded is False


def test_future_dated_bus_evidence_with_backpressure_is_stale_not_degraded():
    bus = {"backpressure": True, "observed_at": FUTURE, "source": "hookbus:health"}
    view = build(hooks=hook_port([], bus=bus))
    assert view.hook_bus.state == "STALE"
    assert view.hook_bus.reason == "bus-freshness-invalid"
    assert view.hook_bus.degraded is False


# --- F4: oversized port input fails closed, never silent last-256 truncation

def test_oversized_port_items_fail_closed_instead_of_silent_truncation():
    unavailable = hook_record("h1", available=False, observation_id="obs-unavailable")
    identical_available = [hook_record("h1", available=True, observation_id="obs-avail")
                           for _ in range(256)]
    records = [unavailable] + identical_available  # 257; cap would drop the conflict
    with pytest.raises(InspectorProjectionError):
        build(registry=registry_port([reg_item("h1", "hook")]),
              hooks=hook_port(records))


def test_port_cap_boundary_of_256_records_is_accepted():
    records = [hook_record("h1", available=True, observation_id=f"obs-{index}")
               for index in range(256)]
    view = build(registry=registry_port([reg_item("h1", "hook")]),
                 hooks=hook_port(records))
    assert view.items  # exactly at the documented cap: accepted, no typed error


# --- F5: hard/soft vocabulary validation + conflicting classification -------

def test_non_hard_soft_classification_is_typed_rejected():
    with pytest.raises(InspectorProjectionError):
        build(registry=registry_port([reg_item("h1", "hook")]),
              hooks=hook_port([hook_record("h1", classification="GUARD",
                                           available=True)]))
    with pytest.raises(InspectorProjectionError):
        build(registry=registry_port([reg_item("h1", "hook")]),
              hooks=hook_port([hook_record("h1", classification="observe",
                                           available=True)]))


def test_conflicting_classification_is_unknown_with_classification_suppressed():
    records = [
        hook_record("h1", classification="hard", source="hookbus:snapshot-42",
                    observation_id="obs-1"),
        hook_record("h1", classification="soft", source="hookbus:snapshot-42",
                    observation_id="obs-2"),
    ]
    view = build(registry=registry_port([reg_item("h1", "hook")]),
                 hooks=hook_port(records))
    item = item_by_id(view, "h1")
    assert item.state == "UNKNOWN"
    assert item.reason == "conflicting-classification"
    assert item.facts.get("classification") is None
    assert item.state != "READY"


def test_classification_never_picked_from_first_record_when_disagreeing():
    records = [
        hook_record("h1", classification="hard", source="hookbus:snapshot-42",
                    observation_id="obs-1"),
        hook_record("h1", classification=None, available=True,
                    source="hookbus:snapshot-42",
                    observation_id="obs-2"),  # classification absent on this record
    ]
    view = build(registry=registry_port([reg_item("h1", "hook")]),
                 hooks=hook_port(records))
    item = item_by_id(view, "h1")
    assert item.reason == "conflicting-classification"
    assert "classification" not in item.facts


# --- F6: every emitted string field is redacted; no injected secret survives -

def _iter_string_leaves(node, path="root"):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _iter_string_leaves(value, f"{path}.{key}")
    elif isinstance(node, (list, tuple)):
        for index, value in enumerate(node):
            yield from _iter_string_leaves(value, f"{path}[{index}]")
    elif isinstance(node, str) and node:
        yield path, node


def test_every_emitted_string_field_survives_no_injected_secret():
    view = build(
        registry=registry_port([
            reg_item(f"h-{SECRET_TOKEN}", "hook", route=f"hooks/x?token={SECRET_TOKEN}",
                     source=f"reg?secret={SECRET_TOKEN}", revision=f"rev-{SECRET_TOKEN}"),
            reg_item(f"t-{SECRET_TOKEN}", "tool", route=f"devices/y?key={SECRET_TOKEN}",
                     source=f"reg2?password={SECRET_TOKEN}"),
            reg_item("reg-only", "hook", source=f"reg3?password=abcd1234"),
        ]),
        hooks=hook_port([
            hook_record(f"h-{SECRET_TOKEN}", classification="hard", available=True,
                        observed_at=f"{FRESH}#{SECRET_TOKEN}",
                        source=f"reg?secret={SECRET_TOKEN}",
                        revision=f"rev-{SECRET_TOKEN}"),
        ], bus={"backpressure": True, "conditions": [f"queue:password=abcd1234",
                                                     f"queue:{SECRET_TOKEN}"],
                "observed_at": f"{FRESH}#{SECRET_TOKEN}",
                "source": f"bus?password={SECRET_TOKEN}"}),
        tools=tool_port([
            tool_record(f"t-{SECRET_TOKEN}", available=True,
                        observed_at=f"{FRESH}#{SECRET_TOKEN}",
                        source=f"probe?key={SECRET_TOKEN}",
                        revision=f"rev-{SECRET_TOKEN}"),
        ]),
    )
    data = dataclasses.asdict(view)
    for path, value in _iter_string_leaves(data):
        assert SECRET_TOKEN not in value, f"token survived at {path}"
        assert "abcd1234" not in value, f"embedded credential survived at {path}"
    # the sanitizer must actually engage somewhere
    assert "[REDACTED]" in json.dumps(data, sort_keys=True)
    # documented constant-safe vocabularies stay valid
    for item in view.items:
        assert item.domain in ("hook", "tool")
        assert item.availability in ("asserted", "not-asserted", "unavailable", "absent")


# ===========================================================================
# Repair round 2 RED tests (independent review R2 findings G1-G5)
# ===========================================================================

# --- G1 (P1): revision omitted from dedup signatures -> order-dependent ----

def test_r2_g1_revision_difference_is_conflicting_evidence_in_both_orders():
    first = hook_record("h1", available=True, source="hookbus:snapshot-42",
                        revision="rev-1", observation_id="obs-1")
    second = hook_record("h1", available=True, source="hookbus:snapshot-42",
                         revision="rev-2", observation_id="obs-1")
    registry = registry_port([reg_item("h1", "hook", revision="rev-1")])
    for records in ([first, second], [second, first]):  # both input orders
        view = build(registry=registry, hooks=hook_port(records))
        item = item_by_id(view, "h1")
        assert item.state == "UNKNOWN", records
        assert item.reason == "conflicting-evidence", records
        assert item.state != "READY", records


# --- G2 (P1): confusable credential markers bypass ASCII-only scrubbing ----

def test_r2_g2_cyrillic_o_token_label_is_fully_redacted():
    # 'tоken' below uses Cyrillic о (U+043E), not ASCII o
    confusable = "hookbus:label?tоken=abc123"
    assert default_secret_predicate("source", confusable) is True
    view = build(
        registry=registry_port([reg_item("h2", "hook")]),
        hooks=hook_port([hook_record("h2", available=True, source=confusable)]),
    )
    assert "abc123" not in serialized(view)
    assert item_by_id(view, "h2").source == "[REDACTED]"


def test_r2_g2_mixed_script_bearer_label_is_fully_redacted():
    # 'Bеarer' below mixes ASCII B with Cyrillic е (U+0435)
    confusable = "hookbus:probe Bеarer abc123xyz"
    assert default_secret_predicate("source", confusable) is True
    view = build(
        registry=registry_port([reg_item("h2", "hook")]),
        hooks=hook_port([hook_record("h2", available=True, source=confusable)]),
    )
    assert "abc123xyz" not in serialized(view)
    assert item_by_id(view, "h2").source == "[REDACTED]"


def test_r2_g2_fullwidth_equals_assignment_is_fully_redacted():
    # '＝' is the fullwidth equals sign (U+FF1D), NFKC-folds to '='
    confusable = "hookbus:label?token＝abc123"
    assert default_secret_predicate("source", confusable) is True
    view = build(
        registry=registry_port([reg_item("h2", "hook")]),
        hooks=hook_port([hook_record("h2", available=True, source=confusable)]),
    )
    assert "abc123" not in serialized(view)
    assert item_by_id(view, "h2").source == "[REDACTED]"


# --- G3 (P1): truncated registration identity collides with evidence -------

def test_r2_g3_prefix_collision_does_not_correlate_to_ready():
    # registration identity is longer than MAX_VALUE (128); evidence identity
    # equals only its first 128 chars -> different identities, must not join
    long_identity = "a-wiki:registry@main/" + "x" * 128 + "-real"
    assert len(long_identity) > 128
    view = build(
        registry=registry_port([reg_item("h1", "hook", source=long_identity,
                                         revision="rev-1")]),
        hooks=hook_port([hook_record("h1", available=True,
                                     source=long_identity[:128],
                                     revision="rev-1")]),
    )
    item = item_by_id(view, "h1")
    assert item.state == "UNKNOWN"
    assert item.reason == "evidence-uncorrelated"
    assert item.state != "READY"


def test_r2_g3_complete_identity_still_correlates_to_ready():
    # control: correlation compares COMPLETE (pre-truncation) identities
    long_identity = "a-wiki:registry@main/" + "x" * 128 + "-real"
    view = build(
        registry=registry_port([reg_item("h1", "hook", source=long_identity,
                                         revision="rev-1")]),
        hooks=hook_port([hook_record("h1", available=True, source=long_identity,
                                     revision="rev-1")]),
    )
    item = item_by_id(view, "h1")
    assert item.state == "READY"
    assert item.reason == "ready-evidence"


# --- G4 (P2): whitespace-only identities must not count as provenance ------

def test_r2_g4_whitespace_only_identities_are_provenance_missing_not_ready():
    view = build(
        registry=registry_port([reg_item("h1", "hook", source=" ", revision=" ")]),
        hooks=hook_port([hook_record("h1", available=True, source=" ",
                                     revision=" ")]),
    )
    item = item_by_id(view, "h1")
    assert item.state == "UNKNOWN"
    assert item.reason == "provenance-missing"
    assert item.state != "READY"


def test_r2_g4_identity_whitespace_is_normalized_for_exact_match():
    # control: identities validate and compare on STRIPPED values consistently
    view = build(
        registry=registry_port([reg_item("h1", "hook",
                                         source=" a-wiki:registry@main ",
                                         revision=" rev-1 ")]),
        hooks=hook_port([hook_record("h1", available=True,
                                     source="a-wiki:registry@main",
                                     revision="rev-1")]),
    )
    item = item_by_id(view, "h1")
    assert item.state == "READY"
    assert item.reason == "ready-evidence"


# --- G5 (P2): bus without provable freshness must not assert backpressure --

def test_r2_g5_bus_without_observation_time_is_unknown_not_degraded():
    bus = {"backpressure": True, "conditions": ["queue-saturated"],
           "source": "hookbus:health"}  # observed_at absent
    view = build(hooks=hook_port([], bus=bus))
    assert view.hook_bus.state == "UNKNOWN"
    assert view.hook_bus.reason == "bus-freshness-unobserved"
    assert view.hook_bus.degraded is False


def test_r2_g5_bus_with_unparseable_time_is_unknown_not_degraded():
    bus = {"backpressure": True, "observed_at": "not-a-timestamp",
           "source": "hookbus:health"}
    view = build(hooks=hook_port([], bus=bus))
    assert view.hook_bus.state == "UNKNOWN"
    assert view.hook_bus.reason == "bus-freshness-unobserved"
    assert view.hook_bus.degraded is False


# ===========================================================================
# Repair round 3 RED tests (final adjudicated repair findings H1-H3)
# ===========================================================================

# --- H1 (P1): ASCII-marker early return skips the folded-copy scan --------

def test_r3_h1_dual_credential_mixed_script_value_fully_redacted():
    # 'tоken' below uses Cyrillic о (U+043E): the ASCII 'token=one' segment
    # fires on the original copy, but the fold-only 'tоken=two' segment must
    # not survive the ASCII surgical scrub either — both scans must complete.
    mixed = "label?token=one&tоken=two"
    assert default_secret_predicate("source", mixed) is True
    view = build(
        registry=registry_port([reg_item("h2", "hook")]),
        hooks=hook_port([hook_record("h2", available=True, source=mixed)]),
    )
    text = serialized(view)
    assert item_by_id(view, "h2").source == "[REDACTED]", text
    assert "two" not in text  # fold-only credential run must not survive


def test_r3_h1_triple_credential_mixed_script_value_fully_redacted():
    # two ASCII-fired segments + one fold-only segment: scrubbing the ASCII
    # segments first must not hide the fold-only 'tоken=three' credential.
    mixed = "label?token=one&password=two&tоken=three"
    assert default_secret_predicate("source", mixed) is True
    view = build(
        registry=registry_port([reg_item("h2", "hook")]),
        hooks=hook_port([hook_record("h2", available=True, source=mixed)]),
    )
    text = serialized(view)
    assert item_by_id(view, "h2").source == "[REDACTED]", text
    assert "three" not in text  # fold-only credential run must not survive


def test_r3_h1_pure_ascii_multi_segment_remains_surgical():
    # control: a value whose credential segments ALL fire on the ASCII copy
    # keeps the surgical per-segment scrub (no whole-value redaction).
    ascii_value = "label?token=one&password=two"
    view = build(
        registry=registry_port([reg_item("h2", "hook")]),
        hooks=hook_port([hook_record("h2", available=True, source=ascii_value)]),
    )
    item = item_by_id(view, "h2")
    assert item.source == "label?token=[REDACTED]&password=[REDACTED]"
    assert "one" not in serialized(view)
    assert "two" not in serialized(view)


# --- H2 (P2): absent 'available' vs 'available=None' dedup order-dependence -

def test_r3_h2_absent_vs_none_availability_is_order_independent():
    # the two records agree on every dedup fact except HOW availability is
    # unasserted (key absent vs explicit None); _availability_of currently
    # distinguishes them while the dedup signature collapses them, so the
    # surviving record — and the emitted availability — depends on order.
    base = {"item_id": "h1", "source": "hookbus:snapshot-42",
            "observed_at": "not-a-timestamp", "observation_id": "obs-1",
            "classification": "hard"}
    absent_record = dict(base)  # 'available' key ABSENT
    none_record = dict(base, available=None)  # explicit None assertion
    registry = registry_port([reg_item("h1", "hook")])
    outputs = []
    for records in ([absent_record, none_record], [none_record, absent_record]):
        view = build(registry=registry, hooks=hook_port(records))
        outputs.append(serialized(view))
    assert outputs[0] == outputs[1]
    item = item_by_id(view, "h1")
    assert item.reason == "freshness-unobserved"
    assert item.availability == "not-asserted"  # one canonical unasserted token


# --- H3 (P2): field-name heuristic must fold confusable field NAMES --------

def test_r3_h3_confusable_field_names_are_secret_shaped():
    # 'tоken' uses Cyrillic о (U+043E); 'kеy' mixes ASCII k/y with Cyrillic
    # е (U+0435); 'Ｓecret' starts with fullwidth Ｓ (U+FF33). The heuristic
    # must NFKC + confusable-fold the field NAME the same way it folds values.
    assert default_secret_predicate("tоken", "abc123") is True
    assert default_secret_predicate("Ｓecret", "abc123") is True
    assert default_secret_predicate("kеy", "abc123") is True
    assert default_secret_predicate("password", "abc123") is True  # ASCII control
