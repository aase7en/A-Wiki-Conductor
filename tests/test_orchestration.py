"""Closed, inert ORCH-1/1 codec contract (no runtime admission)."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from a_conductor.orchestration import (
    OrchestrationError,
    OrchestrationSignal,
    decode_signal,
    encode_signal,
)


def envelope(kind="enqueue", target="PARENT_QUEUE"):
    payload = {
        "enqueue": {"target": target, "intent_ref": "intent:1", "trigger": "EXPLICIT"},
        "replay": {"target": target, "intent_ref": "intent:1", "trigger": "REFILL",
                   "recovery_evidence_ref": "recovery:1"},
        "utilization": {"census_ref": "census:1", "ready_set_ref": "ready:1",
                        "activation_ref": "activation:1", "provider_observation_ref": "provider:1"},
        "lifecycle": {"hook_event_ref": "hook:1", "subject_ref": "job:1",
                      "observation_ref": "observation:1"},
        "outcome": {"decision": "NO_ACTION", "reason_code": "DUPLICATE",
                    "evidence_refs": ["evidence:1"], "observability_degraded": False},
    }[kind]
    if kind in ("enqueue", "replay"):
        if target == "PARENT_QUEUE":
            payload["parent_binding_ref"] = "parent:1"
            if kind == "replay":
                payload["prior_submission_ref"] = "submission:1"
        else:
            payload.update(ready_plan_ref="plan:1", task_map_ref="map:1")
            if kind == "replay":
                payload["prior_execution_ref"] = "execution:1"
    return dict(signal_type=kind, task_ref="task:709", source="producer:1",
                timestamp="2026-10-23T19:10:30Z", payload=payload,
                metadata={"correlation_ref": "correlation:1", "evidence_refs": []})


def wire(value):
    return json.dumps(value, separators=(",", ":")).encode("utf-8")


def rejects(data, code):
    with pytest.raises(OrchestrationError) as caught:
        decode_signal(data)
    assert str(caught.value) == code
    assert caught.value.code == code


@pytest.mark.parametrize("kind", ["enqueue", "replay", "utilization", "lifecycle", "outcome"])
def test_round_trip(kind):
    signal = OrchestrationSignal(**envelope(kind))
    assert decode_signal(encode_signal(signal), expected_source="producer:1") == signal


@pytest.mark.parametrize("kind", ["enqueue", "replay"])
def test_worker_target_round_trip(kind):
    signal = OrchestrationSignal(**envelope(kind, "WORKER_BATCH"))
    assert decode_signal(encode_signal(signal)) == signal


@pytest.mark.parametrize("raw", [b"", b"{", b"{} trailing", b'{"x":}', b"[]", b"null"])
def test_malformed_json_or_nonobject(raw):
    rejects(raw, "SIGNAL_JSON_INVALID")


def test_unknown_kind():
    value = envelope()
    value["signal_type"] = "launch"
    rejects(wire(value), "SIGNAL_TYPE_UNKNOWN")


@pytest.mark.parametrize("key", list(envelope()))
def test_required_keys(key):
    value = envelope()
    del value[key]
    rejects(wire(value), "SIGNAL_MISSING_KEY")


@pytest.mark.parametrize("raw", [b'{"x":"a","x":"b"}', b'{"x":1,"x":2}',
                                    b'{"payload":{"x":{},"x":{}}}',
                                    b'{"source":"a","sour\\u0063e":"b"}'])
def test_duplicate_keys(raw):
    rejects(raw, "SIGNAL_DUPLICATE_KEY")


@pytest.mark.parametrize("location", ["envelope", "payload", "metadata"])
def test_unknown_keys(location):
    value = envelope()
    container = value if location == "envelope" else value[location]
    container["authority"] = True
    rejects(wire(value), "SIGNAL_UNKNOWN_KEY")


def test_depth_bound_precedes_parser_and_schema():
    rejects(b"[" * 33 + b"]" * 33, "SIGNAL_DEPTH_EXCEEDED")
    rejects(b"[" * 10000, "SIGNAL_DEPTH_EXCEEDED")
    # Exactly 32 containers reaches schema validation rather than depth overflow.
    rejects(b'{"x":' * 32 + b"null" + b"}" * 32, "SIGNAL_MISSING_KEY")


def test_deep_payload_rejected_before_schema():
    raw = wire(envelope()).replace(b'"payload":{', b'"payload":' + b'[' * 33 + b'{', 1)
    rejects(raw, "SIGNAL_DEPTH_EXCEEDED")


def test_brackets_and_escaped_quotes_in_strings_are_not_depth():
    value = envelope()
    value["metadata"]["audit_ref"] = '["' * 30 + "\\"
    assert decode_signal(wire(value)).metadata == value["metadata"]


def test_byte_bound_inclusive_and_checked_before_decoding():
    raw = wire(envelope())
    assert decode_signal(raw + b" " * (65536 - len(raw))).task_ref == "task:709"
    rejects(raw + b" " * (65537 - len(raw)), "SIGNAL_SIZE_EXCEEDED")
    rejects(b"\xff" * 65537, "SIGNAL_SIZE_EXCEEDED")


@pytest.mark.parametrize("raw", [b"\xff", b"\xc0\xaf", b"\xed\xa0\x80"])
def test_non_utf8(raw):
    rejects(raw, "SIGNAL_ENCODING_INVALID")


@pytest.mark.parametrize("token", ["0", "true", "null", "[]", '""'])
def test_wrong_required_scalar_type(token):
    value = envelope()
    rejects(wire(value).replace(b'"task:709"', token.encode()), "SIGNAL_VALUE_INVALID")


@pytest.mark.parametrize("token", ["9" * 5000, "1e999999", "NaN", "Infinity", "-Infinity", "1.2"])
def test_numeric_tokens_rejected_without_conversion(token):
    rejects(wire(envelope()).replace(b'"task:709"', token.encode()), "SIGNAL_VALUE_INVALID")


@pytest.mark.parametrize("stamp", ["2026-02-30T12:00:00Z", "2026-10-23", "2026-10-23T12:00:00",
                                  "2026-10-23X12:00:00Z", "2026-10-23T12:00:00+24:00",
                                  "2026-10-23T12:00:00+01:99"])
def test_invalid_timestamp(stamp):
    value = envelope()
    value["timestamp"] = stamp
    rejects(wire(value), "SIGNAL_VALUE_INVALID")


@pytest.mark.parametrize("stamp", ["2026-10-23T12:00:00+07:00", "2026-10-23T12:00:00.123456Z"])
def test_aware_iso_timestamp(stamp):
    value = envelope()
    value["timestamp"] = stamp
    assert decode_signal(wire(value)).timestamp == stamp


def test_source_binding():
    with pytest.raises(OrchestrationError, match="^SIGNAL_SOURCE_MISMATCH$"):
        decode_signal(wire(envelope()), expected_source="producer:other")
    with pytest.raises(OrchestrationError, match="^SIGNAL_VALUE_INVALID$"):
        decode_signal(wire(envelope()), expected_source="")


def test_payload_target_keys_are_exclusive():
    value = envelope()
    value["payload"]["ready_plan_ref"] = "plan:1"
    rejects(wire(value), "SIGNAL_UNKNOWN_KEY")


def test_type_specific_required_payload():
    value = envelope("lifecycle")
    del value["payload"]["hook_event_ref"]
    rejects(wire(value), "SIGNAL_MISSING_KEY")


@pytest.mark.parametrize("kind", ["enqueue", "replay", "utilization", "lifecycle", "outcome"])
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
    value = envelope("replay")
    value["payload"]["prior_execution_ref"] = "execution:1"
    rejects(wire(value), "SIGNAL_UNKNOWN_KEY")


def test_outcome_mutually_exclusive_effect_refs():
    value = envelope("outcome")
    value["payload"].update(submission_ref="submission:1", execution_ref="execution:1")
    rejects(wire(value), "SIGNAL_VALUE_INVALID")


@pytest.mark.parametrize("field,value", [("decision", "SUCCEEDED"), ("evidence_refs", [None]),
                                        ("observability_degraded", 1)])
def test_outcome_strict_types(field, value):
    data = envelope("outcome")
    data["payload"][field] = value
    rejects(wire(data), "SIGNAL_VALUE_INVALID")


@pytest.mark.parametrize("change", [None, [], {"evidence_refs": ["ref"] * 17},
                                   {"audit_ref": "x" * 257}, {"audit_ref": "\ud800"},
                                   {"audit_ref": {"nested": "ref"}}])
def test_metadata_bounds_and_shape(change):
    value = envelope()
    value["metadata"] = change
    rejects(wire(value), "SIGNAL_VALUE_INVALID")


def test_deterministic_encoding_and_key_order():
    value = envelope()
    a = OrchestrationSignal(**value)
    reordered = dict(reversed(list(value.items())))
    reordered["payload"] = dict(reversed(list(value["payload"].items())))
    b = OrchestrationSignal(**reordered)
    assert encode_signal(a) == encode_signal(b) == wire(json.loads(encode_signal(a)))
    assert list(json.loads(encode_signal(a))) == sorted(value)


def test_encoder_revalidates_mutable_payload_and_rejects_cycles():
    signal = OrchestrationSignal(**envelope())
    signal.metadata["audit_ref"] = signal.metadata
    with pytest.raises(OrchestrationError, match="^SIGNAL_DEPTH_EXCEEDED$"):
        encode_signal(signal)
    with pytest.raises(OrchestrationError, match="^SIGNAL_VALUE_INVALID$"):
        encode_signal({})


def test_encoder_bounds_before_serializing():
    signal = OrchestrationSignal(**envelope())
    signal.metadata["audit_ref"] = "x" * 65537
    with pytest.raises(OrchestrationError, match="^SIGNAL_SIZE_EXCEEDED$"):
        encode_signal(signal)


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
