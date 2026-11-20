"""Closed, inert ORCH-1/1 codec contract — orch-signal.v1 (no runtime admission)."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from a_conductor.orchestration import (
    OrchestrationError,
    OrchestrationOutcome,
    OrchestrationSignal,
    decode_outcome,
    decode_signal,
    encode_outcome,
    encode_signal,
)

KINDS = ["ENQUEUE", "REPLAY", "UTILIZATION", "LIFECYCLE"]


def payload_for(kind, target="PARENT_QUEUE"):
    payload = {
        "ENQUEUE": {"target": target, "intent_ref": "intent:1", "trigger": "EXPLICIT"},
        "REPLAY": {"target": target, "intent_ref": "intent:1", "trigger": "REFILL",
                   "recovery_evidence_ref": "recovery:1"},
        "UTILIZATION": {"census_ref": "census:1", "ready_set_ref": "ready:1",
                        "activation_ref": "activation:1", "provider_observation_ref": "provider:1"},
        "LIFECYCLE": {"hook_event_ref": "hook:1", "subject_ref": "job:1",
                      "observation_ref": "observation:1"},
    }[kind]
    if kind in ("ENQUEUE", "REPLAY"):
        if target == "PARENT_QUEUE":
            payload["parent_binding_ref"] = "parent:1"
            if kind == "REPLAY":
                payload["prior_submission_ref"] = "submission:1"
        else:
            payload.update(ready_plan_ref="plan:1", task_map_ref="map:1")
            if kind == "REPLAY":
                payload["prior_execution_ref"] = "execution:1"
    return payload


def envelope(kind="ENQUEUE", target="PARENT_QUEUE", *, effects=True):
    value = dict(schema_version="orch-signal.v1", signal_id="signal:1",
                 kind=kind, occurred_at="2026-10-23T19:10:30Z",
                 source_ref="producer:1", project_id="project:1",
                 payload=payload_for(kind, target))
    if effects or kind in ("ENQUEUE", "REPLAY"):
        value["task_ref"] = "task:709"
        value["work_order_ref"] = "wo:709"
    return value


def outcome_envelope():
    return dict(signal_id="signal:1", kind="ENQUEUE", decision="NO_ACTION",
                reason_code="DUPLICATE", evidence_refs=["evidence:1"],
                observability_degraded=False)


def wire(value):
    return json.dumps(value, separators=(",", ":")).encode("utf-8")


def rejects(data, code):
    with pytest.raises(OrchestrationError) as caught:
        decode_signal(data)
    assert str(caught.value) == code
    assert caught.value.code == code


def rejects_outcome(data, code):
    with pytest.raises(OrchestrationError) as caught:
        decode_outcome(data)
    assert caught.value.code == code


@pytest.mark.parametrize("kind", KINDS)
def test_round_trip(kind):
    signal = OrchestrationSignal(**envelope(kind))
    assert decode_signal(encode_signal(signal), expected_source="producer:1") == signal


@pytest.mark.parametrize("kind", ["ENQUEUE", "REPLAY"])
def test_worker_target_round_trip(kind):
    signal = OrchestrationSignal(**envelope(kind, "WORKER_BATCH"))
    assert decode_signal(encode_signal(signal)) == signal


def test_optional_observation_fields_round_trip_absent():
    value = envelope("UTILIZATION", effects=False)
    signal = OrchestrationSignal(**value)
    assert signal.task_ref is signal.work_order_ref is None
    assert decode_signal(encode_signal(signal)) == signal
    assert b"task_ref" not in encode_signal(signal)


@pytest.mark.parametrize("raw", [b"", b"{", b"{} trailing", b'{"x":}', b"[]", b"null"])
def test_malformed_json_or_nonobject(raw):
    rejects(raw, "SIGNAL_JSON_INVALID")


def test_unknown_kind():
    value = envelope()
    value["kind"] = "LAUNCH"
    rejects(wire(value), "SIGNAL_TYPE_UNKNOWN")


def test_unsupported_schema_version_refused_never_downgraded():
    value = envelope()
    value["schema_version"] = "orch-signal.v2"
    rejects(wire(value), "SIGNAL_VERSION_UNSUPPORTED")
    value["schema_version"] = 1
    rejects(wire(value), "SIGNAL_VERSION_UNSUPPORTED")
    del value["schema_version"]
    rejects(wire(value), "SIGNAL_MISSING_KEY")


@pytest.mark.parametrize("key", ["schema_version", "signal_id", "kind", "occurred_at",
                                 "source_ref", "project_id", "payload"])
def test_required_core_keys(key):
    value = envelope()
    del value[key]
    rejects(wire(value), "SIGNAL_MISSING_KEY")


@pytest.mark.parametrize("key", ["task_ref", "work_order_ref"])
def test_effect_kinds_require_task_and_work_order(key):
    value = envelope()
    del value[key]
    rejects(wire(value), "SIGNAL_MISSING_KEY")
    observation = envelope("UTILIZATION", effects=False)
    assert decode_signal(wire(observation)).signal_id == "signal:1"


@pytest.mark.parametrize("raw", [b'{"x":"a","x":"b"}', b'{"x":1,"x":2}',
                                 b'{"payload":{"x":{},"x":{}}}',
                                 b'{"source_ref":"a","source_r\\u0065f":"b"}'])
def test_duplicate_keys(raw):
    rejects(raw, "SIGNAL_DUPLICATE_KEY")


@pytest.mark.parametrize("location", ["envelope", "payload"])
def test_unknown_keys(location):
    value = envelope()
    container = value if location == "envelope" else value["payload"]
    container["authority"] = True
    rejects(wire(value), "SIGNAL_UNKNOWN_KEY")


def test_depth_bound_precedes_parser_and_schema():
    rejects(b"[" * 5 + b"]" * 5, "SIGNAL_DEPTH_EXCEEDED")
    rejects(b"[" * 10000, "SIGNAL_DEPTH_EXCEEDED")
    # Exactly 4 containers reaches schema validation rather than depth overflow.
    rejects(b'{"x":' * 4 + b"null" + b"}" * 4, "SIGNAL_MISSING_KEY")


def test_deep_payload_rejected_before_schema():
    raw = wire(envelope()).replace(b'"payload":{', b'"payload":' + b'[' * 5 + b'{', 1)
    rejects(raw, "SIGNAL_DEPTH_EXCEEDED")


def test_brackets_and_escaped_quotes_in_strings_are_not_depth():
    value = envelope()
    value["binding_ref"] = '["' * 3 + "\\"
    assert decode_signal(wire(value)).binding_ref == value["binding_ref"]


def test_field_bound_precedes_parser_and_schema():
    # 65 object keys exceed the 64-field contract before JSON parsing.
    raw = b"{" + b",".join(b'"k%d":null' % i for i in range(65)) + b"}"
    rejects(raw, "SIGNAL_FIELDS_EXCEEDED")
    # Exactly 64 fields reaches schema validation rather than field overflow.
    raw = b"{" + b",".join(b'"k%d":null' % i for i in range(64)) + b"}"
    rejects(raw, "SIGNAL_MISSING_KEY")


def test_byte_bound_inclusive_and_checked_before_decoding():
    raw = wire(envelope())
    assert decode_signal(raw + b" " * (16384 - len(raw))).signal_id == "signal:1"
    rejects(raw + b" " * (16385 - len(raw)), "SIGNAL_SIZE_EXCEEDED")
    rejects(b"\xff" * 16385, "SIGNAL_SIZE_EXCEEDED")


@pytest.mark.parametrize("raw", [b"\xff", b"\xc0\xaf", b"\xed\xa0\x80"])
def test_non_utf8(raw):
    rejects(raw, "SIGNAL_ENCODING_INVALID")


@pytest.mark.parametrize("token", ["0", "true", "null", "[]", '""'])
def test_wrong_required_scalar_type(token):
    value = envelope()
    rejects(wire(value).replace(b'"signal:1"', token.encode()), "SIGNAL_VALUE_INVALID")


@pytest.mark.parametrize("token", ["9" * 5000, "1e999999", "NaN", "Infinity", "-Infinity", "1.2"])
def test_numeric_tokens_rejected_without_conversion(token):
    rejects(wire(envelope()).replace(b'"signal:1"', token.encode()), "SIGNAL_VALUE_INVALID")


@pytest.mark.parametrize("stamp", ["2026-02-30T12:00:00Z", "2026-10-23", "2026-10-23T12:00:00",
                                   "2026-10-23X12:00:00Z", "2026-10-23T12:00:00+24:00",
                                   "2026-10-23T12:00:00+01:99"])
def test_invalid_timestamp(stamp):
    value = envelope()
    value["occurred_at"] = stamp
    rejects(wire(value), "SIGNAL_VALUE_INVALID")


@pytest.mark.parametrize("stamp", ["2026-10-23T12:00:00+07:00", "2026-10-23T12:00:00.123456Z"])
def test_aware_iso_timestamp(stamp):
    value = envelope()
    value["occurred_at"] = stamp
    assert decode_signal(wire(value)).occurred_at == stamp


def test_source_binding():
    with pytest.raises(OrchestrationError, match="^SIGNAL_SOURCE_MISMATCH$"):
        decode_signal(wire(envelope()), expected_source="producer:other")
    with pytest.raises(OrchestrationError, match="^SIGNAL_VALUE_INVALID$"):
        decode_signal(wire(envelope()), expected_source="")


def test_envelope_identifier_bounds():
    value = envelope()
    value["signal_id"] = "s" * 129
    rejects(wire(value), "SIGNAL_VALUE_INVALID")
    value = envelope()
    value["binding_ref"] = "b" * 257
    rejects(wire(value), "SIGNAL_VALUE_INVALID")


def test_payload_target_keys_are_exclusive():
    value = envelope()
    value["payload"]["ready_plan_ref"] = "plan:1"
    rejects(wire(value), "SIGNAL_UNKNOWN_KEY")


def test_type_specific_required_payload():
    value = envelope("LIFECYCLE")
    del value["payload"]["hook_event_ref"]
    rejects(wire(value), "SIGNAL_MISSING_KEY")


@pytest.mark.parametrize("kind", KINDS)
def test_empty_payload_rejected(kind):
    value = envelope(kind)
    value["payload"] = {}
    rejects(wire(value), "SIGNAL_MISSING_KEY")


@pytest.mark.parametrize("field", ["target", "trigger"])
def test_unknown_target_or_trigger(field):
    value = envelope()
    value["payload"][field] = "UNKNOWN"
    rejects(wire(value), "SIGNAL_VALUE_INVALID")


def test_replay_prior_target_binding():
    value = envelope("REPLAY")
    value["payload"]["prior_execution_ref"] = "execution:1"
    rejects(wire(value), "SIGNAL_UNKNOWN_KEY")


def test_deterministic_encoding_and_key_order():
    value = envelope()
    a = OrchestrationSignal(**value)
    reordered = dict(reversed(list(value.items())))
    reordered["payload"] = dict(reversed(list(reordered["payload"].items())))
    b = OrchestrationSignal(**reordered)
    assert encode_signal(a) == encode_signal(b) == wire(json.loads(encode_signal(a)))
    assert list(json.loads(encode_signal(a))) == sorted(value)


def test_encoder_revalidates_mutable_payload_and_rejects_cycles():
    signal = OrchestrationSignal(**envelope())
    signal.payload["intent_ref"] = signal.payload
    with pytest.raises(OrchestrationError, match="^SIGNAL_DEPTH_EXCEEDED$"):
        encode_signal(signal)
    with pytest.raises(OrchestrationError, match="^SIGNAL_VALUE_INVALID$"):
        encode_signal({})


def test_encoder_bounds_before_serializing():
    signal = OrchestrationSignal(**{**envelope(), "binding_ref": "x" * 16385})
    with pytest.raises(OrchestrationError, match="^SIGNAL_SIZE_EXCEEDED$"):
        encode_signal(signal)


def test_encoder_total_field_bound():
    signal = OrchestrationSignal(**{**envelope(), "payload": None})
    signal = OrchestrationSignal(**{**envelope(),
                                    "payload": {f"ref{i}": "x" for i in range(60)}})
    with pytest.raises(OrchestrationError, match="^SIGNAL_FIELDS_EXCEEDED$"):
        encode_signal(signal)


# ---- bounded outcome envelope (foundation section 3; never a signal kind) ----

def test_outcome_round_trip_and_defaults():
    outcome = OrchestrationOutcome(**{**outcome_envelope(), "evidence_refs": ("evidence:1",)})
    assert decode_outcome(encode_outcome(outcome)) == outcome
    assert outcome.submission_ref is outcome.execution_ref is None


def test_outcome_requires_commissioned_shape():
    value = outcome_envelope()
    del value["decision"]
    rejects_outcome(wire(value), "SIGNAL_MISSING_KEY")
    value = outcome_envelope()
    value["authority"] = True
    rejects_outcome(wire(value), "SIGNAL_UNKNOWN_KEY")


def test_outcome_mutually_exclusive_effect_refs():
    value = outcome_envelope()
    value.update(submission_ref="submission:1", execution_ref="execution:1")
    rejects_outcome(wire(value), "SIGNAL_VALUE_INVALID")


@pytest.mark.parametrize("field,value,code", [
    ("decision", "SUCCEEDED", "SIGNAL_VALUE_INVALID"),
    ("evidence_refs", [None], "SIGNAL_VALUE_INVALID"),
    ("evidence_refs", ["ref"] * 17, "SIGNAL_VALUE_INVALID"),
    ("observability_degraded", 1, "SIGNAL_VALUE_INVALID"),
    ("kind", "OUTCOME", "SIGNAL_TYPE_UNKNOWN")])
def test_outcome_strict_types(field, value, code):
    data = outcome_envelope()
    data[field] = value
    rejects_outcome(wire(data), code)


def test_signal_kind_rejects_outcome():
    value = envelope()
    value["kind"] = "OUTCOME"
    rejects(wire(value), "SIGNAL_TYPE_UNKNOWN")


def test_optional_numeric_or_null_token_is_invalid_not_absent():
    # A numeric/None token in an optional field must be rejected as an invalid
    # value, never silently treated as an absent field.
    value = envelope("UTILIZATION", effects=False)
    value["binding_ref"] = 5
    rejects(wire(value), "SIGNAL_VALUE_INVALID")
    value["binding_ref"] = None
    rejects(wire(value), "SIGNAL_VALUE_INVALID")
    # Same rule for effect-required fields: present-but-invalid is not "missing".
    raw = wire(envelope()).replace(b'"task:709"', b"NaN")
    rejects(raw, "SIGNAL_VALUE_INVALID")
    raw = wire(envelope()).replace(b'"task:709"', b"null")
    rejects(raw, "SIGNAL_VALUE_INVALID")


def test_outcome_evidence_refs_custom_iterable_is_never_coerced():
    outcome = OrchestrationOutcome(**{**outcome_envelope(),
                                      "evidence_refs": {"evidence:1"}})
    with pytest.raises(OrchestrationError, match="^SIGNAL_VALUE_INVALID$"):
        encode_outcome(outcome)
    generator = (ref for ref in ["evidence:1"])
    outcome = OrchestrationOutcome(**{**outcome_envelope(), "evidence_refs": generator})
    with pytest.raises(OrchestrationError, match="^SIGNAL_VALUE_INVALID$"):
        encode_outcome(outcome)


def test_import_has_no_writes_network_or_process_effects(tmp_path):
    script = '''
import sys, os
__file__ = "<codec-import-probe>"
def guard(event, args):
    if event == "open":
        frame = sys._getframe()
        while frame:
            if frame.f_globals.get("__name__") == "a_conductor.orchestration":
                raise AssertionError("module-initiated file I/O on import")
            frame = frame.f_back
        mode, flags = args[1:3]
        if (isinstance(mode, str) and any(c in mode for c in "wax+")) or (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)):
            raise AssertionError("file write on import")
    if event.startswith(("socket.", "subprocess.", "os.system", "os.mkdir", "os.remove", "os.rename")):
        raise AssertionError(event)
sys.addaudithook(guard)
import a_conductor.orchestration
'''
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    before = list(tmp_path.iterdir())
    result = subprocess.run([sys.executable, "-B", "-c", script], cwd=tmp_path,
                            env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert list(tmp_path.iterdir()) == before
