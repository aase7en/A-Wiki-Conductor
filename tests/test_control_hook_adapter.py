from __future__ import annotations

import copy
import json
import uuid
from dataclasses import fields as dataclass_fields
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from a_conductor.control_events import ControlEvent
from a_conductor.control_hook_adapter import (
    ControlHookContext,
    ControlHookNormalizationError,
    normalize_control_event,
)
from a_conductor.origin_provenance import derive_origin_chat_session_ref

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "contracts" / "hook-contract-v1.schema.json"
ADAPTER_SOURCE = ROOT / "src" / "a_conductor" / "control_hook_adapter.py"

VALID_HEX = "0123456789abcdef0123456789abcdef"
FAKE_SHARE_URL = "https://chat.example/" + "FAKE/share/0000"
FAKE_CHAT_URL = "https://chat.openai.com/c/" + "sess-abc123"
FAKE_BEARER = "Bearer " + "FAKE" + "0" * 27
FAKE_SK = "sk-" + "FAKE" + "0" * 36
FAKE_GHP = "ghp_" + "FAKE" + "0" * 31
FAKE_COOKIE = "FAKESESSIONCOOKIE=" + "0" * 16

OPTIONAL_FIELDS = (
    "lane_id",
    "task_id",
    "work_order",
    "task_topology",
    "authority_repo",
    "execution_repo",
    "repo",
    "worktree",
    "branch",
    "head_sha",
    "claim_ref",
    "execution_id",
    "harness_id",
    "model_id",
    "effort",
    "state",
    "blocker_code",
    "correlation_id",
    "causation_id",
    "evidence_refs",
    "evidence_digest",
    "summary",
    "origin_surface",
    "origin_chat_session_ref",
)

CORE_FIELDS = (
    "schema_version",
    "event_id",
    "event_type",
    "hook_class",
    "phase",
    "domain",
    "action",
    "occurred_at",
    "source",
    "source_version",
    "device_id",
    "host_os",
    "privacy_class",
)

FORBIDDEN_INVENTED_FIELDS = (
    "sequence",
    "dedupe_key",
    "duration_ms",
    "guard",
    "command_request",
    "command_digest",
    "command_ref",
    "adapter",
    "worker_id",
    "project_id",
)


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    import json

    return Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def make_event(event_type: str = "START", event_id: str | None = None) -> ControlEvent:
    return ControlEvent(
        event_id=event_id if event_id is not None else f"event-{uuid.uuid4().hex}",
        event_type=event_type,
        worker_id="a-worker-01",
        project_id="project-1",
    )


def make_context(**overrides: object) -> ControlHookContext:
    base: dict[str, object] = {
        "occurred_at": "2026-09-19T07:48:08Z",
        "source_version": "1.2.3",
        "device_id": "device-01",
        "host_os": "windows",
    }
    base.update(overrides)
    return ControlHookContext(**base)


def full_optional_context() -> ControlHookContext:
    return make_context(
        lane_id="WO-P1-383-HOOK1-CONTROL-NORMALIZATION-001",
        task_id="WO-P1-383",
        work_order="WO-P1-383",
        task_topology="CONTROL_PLANE_ONLY",
        authority_repo="aase7en/A-Wiki-Conductor",
        execution_repo="aase7en/A-Wiki-Conductor",
        repo="aase7en/A-Wiki-Conductor",
        worktree="A:/GitHub/_worktrees/wo383",
        branch="feat/wo-p1-383-hook1-control-normalization",
        head_sha="04b8d159aebf8cd957f31f177cd4b1cd5604bc52",
        claim_ref="WO-P1-383-HOOK1-CONTROL-NORMALIZATION-001",
        execution_id="exec-0001",
        harness_id="kilo",
        model_id="glm-5.3",
        effort="max",
        state="RUNNING",
        blocker_code="NONE",
        correlation_id="corr-0001",
        causation_id=f"hk-{VALID_HEX}",
        evidence_refs=["runs/WO-P1-383/author/attempt-0001/task.md"],
        evidence_digest="0123456789abcdef",
        summary="hook1 control normalization",
    )


def test_production_shape_event_id_maps_to_stable_hk_hex_twice() -> None:
    event = make_event()
    first = normalize_control_event(event, make_context())
    second = normalize_control_event(event, make_context())
    assert first["event_id"] == f"hk-{event.event_id[len('event-'):]}"
    assert first["event_id"] == second["event_id"]
    assert first == second


@pytest.mark.parametrize(
    "bad_id",
    [
        "EVENT-0123456789abcdef0123456789abcdef",
        "event-0123456789ABCDEF0123456789ABCDEF",
        "hk-0123456789abcdef0123456789abcdef",
        "event-0123456789abcdef0123456789abcde",
        "event-0123456789abcdef0123456789abcdeff",
        "event-0123456789abcdef0123456789abcdeg",
        "event-",
        "",
        "event-0123456789abcdef0123456789abcde\n",
        " event-0123456789abcdef0123456789abcdef",
    ],
)
def test_malformed_source_event_ids_fail_typed(bad_id: str) -> None:
    with pytest.raises(ControlHookNormalizationError) as exc_info:
        normalize_control_event(make_event(event_id=bad_id), make_context())
    assert exc_info.value.code == "CONTROL_HOOK_EVENT_ID_MALFORMED"


def test_non_control_event_object_fails_typed() -> None:
    with pytest.raises(ControlHookNormalizationError) as exc_info:
        normalize_control_event(
            "event-0123456789abcdef0123456789abcdef", make_context()
        )
    assert exc_info.value.code == "CONTROL_HOOK_EVENT_INVALID"


@pytest.mark.parametrize(
    "source_type,expected_event_type,action",
    [
        ("START", "control.start.after", "start"),
        ("STOP", "control.stop.after", "stop"),
        ("RESTART", "control.restart.after", "restart"),
        ("RELEASE", "control.release.after", "release"),
    ],
)
def test_lifecycle_mappings_exact(
    source_type: str, expected_event_type: str, action: str
) -> None:
    envelope = normalize_control_event(
        make_event(event_type=source_type), make_context()
    )
    assert envelope["event_type"] == expected_event_type
    assert envelope["domain"] == "control"
    assert envelope["action"] == action
    assert envelope["phase"] == "after"
    assert envelope["hook_class"] == "OBSERVE"
    assert envelope["source"] == "a-conductor"
    assert envelope["privacy_class"] == "INTERNAL"
    assert envelope["schema_version"] == "1.0.0"


@pytest.mark.parametrize("source_type", ["PAUSE", "start", "Start", "", "RESUME"])
def test_unknown_source_event_type_fails_typed(source_type: str) -> None:
    with pytest.raises(ControlHookNormalizationError) as exc_info:
        normalize_control_event(make_event(event_type=source_type), make_context())
    assert exc_info.value.code == "CONTROL_HOOK_EVENT_TYPE_UNSUPPORTED"


@pytest.mark.parametrize("source_type", ["START", "STOP", "RESTART", "RELEASE"])
def test_generated_envelopes_validate_against_hook_contract_schema(
    validator: Draft202012Validator, source_type: str
) -> None:
    envelope = normalize_control_event(make_event(event_type=source_type), make_context())
    errors = list(validator.iter_errors(envelope))
    assert errors == []


def test_full_optional_envelope_validates_against_schema(
    validator: Draft202012Validator,
) -> None:
    envelope = normalize_control_event(make_event(), full_optional_context())
    assert list(validator.iter_errors(envelope)) == []


def test_fractional_occurred_at_is_accepted(
    validator: Draft202012Validator,
) -> None:
    envelope = normalize_control_event(
        make_event(), make_context(occurred_at="2026-09-19T07:48:08.123456789Z")
    )
    assert list(validator.iter_errors(envelope)) == []


@pytest.mark.parametrize(
    "bad_occurred_at",
    [
        "2026-09-19T07:48:08+00:00",
        "2026-09-19T07:48:08z",
        "2026-09-19T07:48:08",
        "2026-09-19 07:48:08Z",
        "2026-13-19T07:48:08Z",
        "not-a-timestamp",
        "",
        42,
    ],
)
def test_invalid_occurred_at_fails_typed(bad_occurred_at: object) -> None:
    with pytest.raises(ControlHookNormalizationError) as exc_info:
        normalize_control_event(
            make_event(), make_context(occurred_at=bad_occurred_at)
        )
    assert exc_info.value.code == "CONTROL_HOOK_OCCURRED_AT_INVALID"


@pytest.mark.parametrize(
    "field,bad_value",
    [
        ("source_version", "1.2"),
        ("source_version", "v1.2.3"),
        ("source_version", "1.2.3+build"),
        ("device_id", "-device-01"),
        ("device_id", "device 01"),
        ("device_id", ""),
        ("device_id", "D" + "a" * 64),
        ("host_os", "Windows"),
        ("host_os", "android"),
        ("host_os", ""),
    ],
)
def test_invalid_required_context_fails_typed(field: str, bad_value: object) -> None:
    with pytest.raises(ControlHookNormalizationError) as exc_info:
        normalize_control_event(make_event(), make_context(**{field: bad_value}))
    assert exc_info.value.code == f"CONTROL_HOOK_{field.upper()}_INVALID"


@pytest.mark.parametrize("field", ["occurred_at", "source_version", "device_id", "host_os"])
def test_missing_required_context_fails_typed(field: str) -> None:
    with pytest.raises(ControlHookNormalizationError) as exc_info:
        normalize_control_event(make_event(), make_context(**{field: None}))
    assert exc_info.value.code == "CONTROL_HOOK_CONTEXT_REQUIRED"


def test_worker_and_project_ids_are_not_projected_as_hook_authority() -> None:
    envelope = normalize_control_event(make_event(), make_context())
    for key in ("lane_id", "task_id", "work_order"):
        assert key not in envelope
    assert "a-worker-01" not in envelope.values()
    assert "project-1" not in envelope.values()


def test_explicit_optional_context_passes_through_unchanged() -> None:
    context = full_optional_context()
    envelope = normalize_control_event(make_event(), context)
    for name in OPTIONAL_FIELDS:
        expected = getattr(context, name)
        if expected is None:
            assert name not in envelope
            continue
        if name == "evidence_refs":
            assert envelope[name] == list(expected)
        else:
            assert envelope[name] == expected


@pytest.mark.parametrize(
    "field,bad_value",
    [
        ("lane_id", " lane-01"),
        ("lane_id", ""),
        ("task_id", "task/01"),
        ("work_order", "wo 383"),
        ("task_topology", "control_plane_only"),
        ("task_topology", "CROSS_REPO_PLAN"),
        ("authority_repo", ""),
        ("authority_repo", "repo\nwith-newline"),
        ("execution_repo", "x" * 257),
        ("repo", "repo\x00nul"),
        ("worktree", ""),
        ("branch", "branch with space"),
        ("branch", "branch\n"),
        ("head_sha", "04B8D159AEBF"),
        ("head_sha", "zzzz"),
        ("claim_ref", " claim"),
        ("execution_id", "exec 1"),
        ("harness_id", "-harness"),
        ("model_id", "model id"),
        ("effort", "MAX"),
        ("state", "running"),
        ("state", "R"),
        ("blocker_code", "blocker-code"),
        ("correlation_id", " corr"),
        ("causation_id", "event-0123456789abcdef0123456789abcdef"),
        ("causation_id", "hk-0123456789ABCDEF0123456789ABCDEF"),
        ("evidence_digest", "0123456789abc"),
        ("evidence_digest", "0123456789abcdeg"),
        ("summary", ""),
        ("summary", "line1\nline2"),
        ("summary", "x" * 513),
        ("summary", FAKE_SK + " leaked"),
        ("summary", FAKE_GHP + " leaked"),
        ("summary", FAKE_BEARER + " token"),
    ],
)
def test_invalid_optional_context_fails_not_truncates(field: str, bad_value: object) -> None:
    with pytest.raises(ControlHookNormalizationError) as exc_info:
        normalize_control_event(make_event(), make_context(**{field: bad_value}))
    assert exc_info.value.code == "CONTROL_HOOK_CONTEXT_FIELD_INVALID"


def test_invalid_evidence_refs_fail_typed() -> None:
    for bad in (
        [" bad-ref"],
        ["a" * 257],
        ["ref-a", "ref-a"],
        ["ref-a"] * 17,
        "ref-not-a-list",
        [42],
    ):
        with pytest.raises(ControlHookNormalizationError) as exc_info:
            normalize_control_event(make_event(), make_context(evidence_refs=bad))
        assert exc_info.value.code == "CONTROL_HOOK_CONTEXT_FIELD_INVALID"


def test_omitted_optional_context_stays_omitted() -> None:
    envelope = normalize_control_event(make_event(), make_context())
    for name in OPTIONAL_FIELDS:
        assert name not in envelope


def test_no_sequence_dedupe_guard_command_or_adapter_invented() -> None:
    envelope = normalize_control_event(make_event(), full_optional_context())
    allowed = set(CORE_FIELDS) | set(OPTIONAL_FIELDS)
    assert set(envelope) <= allowed
    for name in FORBIDDEN_INVENTED_FIELDS:
        assert name not in envelope


def test_source_event_and_context_are_not_mutated() -> None:
    event = make_event()
    context = full_optional_context()
    event_snapshot = copy.deepcopy(event)
    context_snapshot = copy.deepcopy(context)
    normalize_control_event(event, context)
    assert event == event_snapshot
    assert context == context_snapshot
    assert context.evidence_refs == list(context_snapshot.evidence_refs)


def test_context_is_frozen_and_slotted() -> None:
    context = make_context()
    with pytest.raises(Exception):
        context.device_id = "other-device"
    assert not hasattr(context, "__dict__")


def test_error_is_typed_with_bounded_codes() -> None:
    error = ControlHookNormalizationError("CONTROL_HOOK_TEST")
    assert isinstance(error, RuntimeError)
    assert error.code == "CONTROL_HOOK_TEST"


def test_adapter_exposes_only_binding_api() -> None:
    module = __import__("a_conductor.control_hook_adapter", fromlist=[""])
    assert module.__all__ == [
        "ControlHookContext",
        "ControlHookNormalizationError",
        "normalize_control_event",
    ]
    for name in module.__all__:
        assert callable(getattr(module, name, None)) or isinstance(
            getattr(module, name, None), type
        )


def test_context_field_names_are_exactly_required_plus_allowed_optional() -> None:
    names = {field.name for field in dataclass_fields(ControlHookContext)}
    required = {"occurred_at", "source_version", "device_id", "host_os"}
    assert required <= names
    assert names - required == set(OPTIONAL_FIELDS)


def test_production_source_has_no_jsonschema_dependency() -> None:
    source = ADAPTER_SOURCE.read_text(encoding="utf-8")
    assert "jsonschema" not in source


def test_source_version_64_char_boundary_accepted_and_schema_valid(
    validator: Draft202012Validator,
) -> None:
    source_version = "1.2.3-" + "a" * 58
    assert len(source_version) == 64
    envelope = normalize_control_event(
        make_event(), make_context(source_version=source_version)
    )
    assert envelope["source_version"] == source_version
    assert list(validator.iter_errors(envelope)) == []


@pytest.mark.parametrize("prerelease_length", [59, 100])
def test_source_version_over_64_chars_fails_typed_not_truncates(
    prerelease_length: int,
) -> None:
    source_version = "1.2.3-" + "a" * prerelease_length
    assert len(source_version) >= 65
    with pytest.raises(ControlHookNormalizationError) as exc_info:
        normalize_control_event(
            make_event(), make_context(source_version=source_version)
        )
    assert exc_info.value.code == "CONTROL_HOOK_SOURCE_VERSION_INVALID"


@pytest.mark.parametrize(
    "field",
    ["claim_ref", "execution_id", "harness_id", "model_id"],
)
def test_slash_bearing_hook_path_refs_accepted_and_schema_valid(
    validator: Draft202012Validator, field: str
) -> None:
    reference = "owner/reference-01"
    envelope = normalize_control_event(make_event(), make_context(**{field: reference}))
    assert envelope[field] == reference
    assert list(validator.iter_errors(envelope)) == []


@pytest.mark.parametrize(
    "field",
    ["lane_id", "task_id", "work_order", "correlation_id"],
)
def test_slash_bearing_non_path_refs_rejected(field: str) -> None:
    with pytest.raises(ControlHookNormalizationError) as exc_info:
        normalize_control_event(
            make_event(), make_context(**{field: "owner/reference-01"})
        )
    assert exc_info.value.code == "CONTROL_HOOK_CONTEXT_FIELD_INVALID"


@pytest.mark.parametrize(
    "bad_occurred_at",
    [
        "2026-09-19T24:48:08Z",
        "2026-09-19T07:60:08Z",
        "2026-02-30T07:48:08Z",
        "2026-04-31T07:48:08Z",
        "2026-09-19T07:48:08.1234567890Z",
        "2026-09-19T07:48:61Z",
    ],
)
def test_out_of_range_or_impossible_occurred_at_fails_typed(
    bad_occurred_at: str,
) -> None:
    with pytest.raises(ControlHookNormalizationError) as exc_info:
        normalize_control_event(make_event(), make_context(occurred_at=bad_occurred_at))
    assert exc_info.value.code == "CONTROL_HOOK_OCCURRED_AT_INVALID"


def test_leap_second_occurred_at_matches_rfc3339_contract_and_schema(
    validator: Draft202012Validator,
) -> None:
    occurred_at = "2026-12-31T23:59:60Z"
    envelope = normalize_control_event(
        make_event(), make_context(occurred_at=occurred_at)
    )
    assert envelope["occurred_at"] == occurred_at
    assert list(validator.iter_errors(envelope)) == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("lane_id", "L" + "a" * 63),
        ("task_id", "T" + "a" * 63),
        ("work_order", "W" + "a" * 63),
        ("claim_ref", "C" + "a" * 127),
        ("execution_id", "E" + "a" * 127),
        ("harness_id", "H" + "a" * 127),
        ("model_id", "M" + "a" * 127),
        ("correlation_id", "R" + "a" * 127),
        ("device_id", "D" + "a" * 63),
        ("head_sha", "0" * 64),
        ("evidence_digest", "0" * 128),
        ("effort", "e" + "a" * 31),
        ("state", "S" + "A" * 31),
        ("blocker_code", "B" + "A" * 63),
        ("authority_repo", "a" * 256),
        ("execution_repo", "b" * 256),
        ("repo", "c" * 256),
        ("worktree", "d" * 256),
        ("branch", "e" * 256),
        ("summary", "s" * 512),
    ],
)
def test_field_max_length_boundaries_accepted_and_schema_valid(
    validator: Draft202012Validator, field: str, value: str
) -> None:
    envelope = normalize_control_event(make_event(), make_context(**{field: value}))
    assert envelope[field] == value
    assert list(validator.iter_errors(envelope)) == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("lane_id", "L" + "a" * 64),
        ("task_id", "T" + "a" * 64),
        ("work_order", "W" + "a" * 64),
        ("claim_ref", "C" + "a" * 128),
        ("execution_id", "E" + "a" * 128),
        ("harness_id", "H" + "a" * 128),
        ("model_id", "M" + "a" * 128),
        ("correlation_id", "R" + "a" * 128),
        ("head_sha", "0" * 65),
        ("evidence_digest", "0" * 129),
        ("effort", "e" + "a" * 32),
        ("state", "S" + "A" * 32),
        ("blocker_code", "B" + "A" * 64),
        ("authority_repo", "a" * 257),
        ("branch", "e" * 257),
    ],
)
def test_field_over_max_length_fails_typed_not_truncates(
    field: str, value: str
) -> None:
    with pytest.raises(ControlHookNormalizationError) as exc_info:
        normalize_control_event(make_event(), make_context(**{field: value}))
    assert exc_info.value.code == "CONTROL_HOOK_CONTEXT_FIELD_INVALID"


def test_evidence_refs_max_boundaries_accepted_and_schema_valid(
    validator: Draft202012Validator,
) -> None:
    refs = [f"r{i:02d}/" + "a" * 252 for i in range(16)]
    assert all(len(ref) == 256 for ref in refs)
    envelope = normalize_control_event(make_event(), make_context(evidence_refs=refs))
    assert envelope["evidence_refs"] == refs
    assert list(validator.iter_errors(envelope)) == []


FAKE_ORIGIN_KEY = bytes(range(32))
RAW_ORIGIN_SESSION_ID = "sess-FAKE-0123456789abcdef"
DERIVED_ORIGIN_REF = derive_origin_chat_session_ref(
    FAKE_ORIGIN_KEY,
    key_version="k1",
    origin_surface="kilo",
    raw_session_ref=RAW_ORIGIN_SESSION_ID,
)


def origin_context(**overrides: object) -> ControlHookContext:
    values: dict[str, object] = {
        "origin_surface": "kilo",
        "origin_chat_session_ref": DERIVED_ORIGIN_REF,
    }
    values.update(overrides)
    return make_context(**values)


def test_origin_fields_round_trip_into_envelope_and_json() -> None:
    envelope = normalize_control_event(make_event(), origin_context())
    assert envelope["origin_surface"] == "kilo"
    assert envelope["origin_chat_session_ref"] == DERIVED_ORIGIN_REF
    serialized = json.dumps(envelope)
    assert RAW_ORIGIN_SESSION_ID not in serialized
    assert json.loads(serialized) == envelope


@pytest.mark.parametrize(
    "surface", ["a-conductor", "srm", "claude-code", "kilo", "rdc"]
)
def test_each_accepted_origin_surface_round_trips(surface: str) -> None:
    envelope = normalize_control_event(
        make_event(), origin_context(origin_surface=surface)
    )
    assert envelope["origin_surface"] == surface


@pytest.mark.parametrize(
    "bad_surface",
    [
        "chatgpt",
        "slack",
        "CHATGPT",
        "Kilo",
        " kilo",
        "kilo ",
        "",
        "kil o",
        42,
        b"kilo",
    ],
)
def test_unknown_or_malformed_origin_surface_fails_typed(
    bad_surface: object,
) -> None:
    with pytest.raises(ControlHookNormalizationError) as exc_info:
        normalize_control_event(
            make_event(), origin_context(origin_surface=bad_surface)
        )
    assert exc_info.value.code == "CONTROL_HOOK_CONTEXT_FIELD_INVALID"


@pytest.mark.parametrize(
    "bad_ref",
    [
        RAW_ORIGIN_SESSION_ID,
        RAW_ORIGIN_SESSION_ID.upper(),
        FAKE_SHARE_URL,
        FAKE_CHAT_URL,
        FAKE_BEARER,
        FAKE_SK,
        FAKE_COOKIE,
        "origin-chat-v1:k1:" + "0F" * 32,
        "origin-chat-v1:k1:" + "0f" * 31,
        "origin-chat-v1:k1:" + "0f" * 33,
        "origin-chat-v1:k1:" + "0f" * 32 + ":extra",
        "origin-chat-v2:k1:" + "0f" * 32,
        "origin-chat-v1:K1:" + "0f" * 32,
        "origin-chat-v1:" + "0f" * 32,
        "origin-chat-v1:k1",
        " origin-chat-v1:k1:" + "0f" * 32,
        "origin-chat-v1:k1:" + "0f" * 32 + "\n",
        "hk-" + "0f" * 16,
        "",
        42,
    ],
)
def test_raw_looking_or_malformed_origin_ref_fails_typed(bad_ref: object) -> None:
    with pytest.raises(ControlHookNormalizationError) as exc_info:
        normalize_control_event(
            make_event(), origin_context(origin_chat_session_ref=bad_ref)
        )
    assert exc_info.value.code == "CONTROL_HOOK_CONTEXT_FIELD_INVALID"
    assert str(exc_info.value) == "CONTROL_HOOK_CONTEXT_FIELD_INVALID"
    if isinstance(bad_ref, str) and bad_ref.strip():
        assert bad_ref not in str(exc_info.value)


def test_origin_fields_absent_stays_backward_compatible() -> None:
    envelope = normalize_control_event(make_event(), make_context())
    assert "origin_surface" not in envelope
    assert "origin_chat_session_ref" not in envelope


def test_origin_fields_change_nothing_else_authority_neutral() -> None:
    event = make_event()
    without_origin = normalize_control_event(event, make_context())
    with_origin = normalize_control_event(event, origin_context())
    for key, value in without_origin.items():
        assert with_origin[key] == value
    assert set(with_origin) == set(without_origin) | {
        "origin_surface",
        "origin_chat_session_ref",
    }
    assert with_origin["hook_class"] == "OBSERVE"
    assert with_origin["event_id"] == without_origin["event_id"]


def test_origin_only_surface_without_ref_is_accepted() -> None:
    envelope = normalize_control_event(
        make_event(), origin_context(origin_chat_session_ref=None)
    )
    assert envelope["origin_surface"] == "kilo"
    assert "origin_chat_session_ref" not in envelope


def test_hook_observation_failure_does_not_mutate_inputs() -> None:
    event = make_event()
    context = origin_context(origin_surface="chatgpt")
    with pytest.raises(ControlHookNormalizationError):
        normalize_control_event(event, context)
    assert context.origin_surface == "chatgpt"
