from __future__ import annotations

import copy
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

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "contracts" / "hook-contract-v1.schema.json"
ADAPTER_SOURCE = ROOT / "src" / "a_conductor" / "control_hook_adapter.py"

VALID_HEX = "0123456789abcdef0123456789abcdef"

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
        ("summary", "sk-FAKE0000000000000000000000000000000000 leaked"),
        ("summary", "ghp_FAKE0000000000000000000000000000000 leaked"),
        ("summary", "Bearer FAKE000000000000000000000000000 token"),
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
