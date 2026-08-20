from __future__ import annotations

import json

import pytest

from a_conductor.operator_protocol import OperatorResponse, parse_operator_request
from a_conductor.operator_wire import (
    OperatorWireError,
    decode_operator_request,
    decode_operator_response,
    encode_operator_request,
    encode_operator_response,
)


def create_request():
    return parse_operator_request(
        {
            "protocol_version": "operator.v1",
            "action": "job.create",
            "job_id": "job-104",
            "work_order_ref": "A-Wiki:WO-OCR-104",
            "project_id": "wastewater",
            "max_attempts": 5,
        }
    )


def test_request_round_trip_is_stable_compact_utf8_json() -> None:
    request = create_request()
    encoded = encode_operator_request(request)
    assert isinstance(encoded, bytes)
    assert b" " not in encoded
    decoded = decode_operator_request(encoded)
    assert decoded == request
    assert encode_operator_request(decoded) == encoded


def test_response_round_trip_preserves_bounded_metadata_only() -> None:
    response = OperatorResponse(
        ok=True,
        code="OK",
        job_id="job-104",
        state="VERIFYING",
        version=5,
        worker_id="a-worker-02",
        attempt_count=1,
        max_attempts=3,
        refs=("native:sha256:abc123", "event-2"),
    )
    encoded = encode_operator_response(response)
    decoded = decode_operator_response(encoded)
    assert decoded == response
    mapping = json.loads(encoded.decode("utf-8"))
    assert set(mapping) == {
        "ok",
        "code",
        "job_id",
        "state",
        "version",
        "worker_id",
        "attempt_count",
        "max_attempts",
        "refs",
    }
    assert "stdout" not in mapping
    assert "stderr" not in mapping
    assert "payload" not in mapping


def test_none_optional_fields_are_omitted_from_wire() -> None:
    encoded = encode_operator_response(OperatorResponse(ok=False, code="OFFLINE"))
    assert json.loads(encoded.decode("utf-8")) == {"code": "OFFLINE", "ok": False, "refs": []}


def test_duplicate_json_keys_are_rejected() -> None:
    raw = b'{"protocol_version":"operator.v1","action":"status","action":"job.get"}'
    with pytest.raises(OperatorWireError) as exc_info:
        decode_operator_request(raw)
    assert exc_info.value.code == "OPERATOR_WIRE_DUPLICATE_KEY"


def test_non_finite_json_constants_are_rejected() -> None:
    raw = b'{"ok":true,"code":"OK","version":NaN}'
    with pytest.raises(OperatorWireError) as exc_info:
        decode_operator_response(raw)
    assert exc_info.value.code == "OPERATOR_WIRE_INVALID_JSON"


@pytest.mark.parametrize("raw", [b"[]", b"null", b'"text"', b"1"])
def test_top_level_must_be_json_object(raw: bytes) -> None:
    with pytest.raises(OperatorWireError) as exc_info:
        decode_operator_request(raw)
    assert exc_info.value.code == "OPERATOR_WIRE_OBJECT_REQUIRED"


def test_unknown_response_fields_are_rejected_not_ignored() -> None:
    raw = b'{"ok":true,"code":"OK","stdout":"private"}'
    with pytest.raises(OperatorWireError) as exc_info:
        decode_operator_response(raw)
    assert exc_info.value.code == "OPERATOR_WIRE_FIELDS_INVALID"


def test_request_unknown_command_field_is_rejected_by_protocol_policy() -> None:
    raw = (
        b'{"protocol_version":"operator.v1","action":"job.execute",'
        b'"job_id":"job-1","expected_version":2,"worker_id":"a-worker-01",'
        b'"operation_ref":"verify.pytest.ocr","command":"git reset --hard"}'
    )
    with pytest.raises(OperatorWireError) as exc_info:
        decode_operator_request(raw)
    assert exc_info.value.code == "OPERATOR_FIELDS_INVALID"


def test_wire_size_is_bounded_before_decode() -> None:
    raw = b"{" + b"x" * 100 + b"}"
    with pytest.raises(OperatorWireError) as exc_info:
        decode_operator_request(raw, max_bytes=32)
    assert exc_info.value.code == "OPERATOR_WIRE_TOO_LARGE"


def test_encode_respects_wire_size_bound() -> None:
    response = OperatorResponse(ok=True, code="OK", refs=tuple(f"evidence:{i}" for i in range(20)))
    with pytest.raises(OperatorWireError) as exc_info:
        encode_operator_response(response, max_bytes=32)
    assert exc_info.value.code == "OPERATOR_WIRE_TOO_LARGE"


@pytest.mark.parametrize("value", ["{}", bytearray(b"{}"), memoryview(b"{}"), 123])
def test_decode_requires_immutable_bytes(value: object) -> None:
    with pytest.raises(OperatorWireError) as exc_info:
        decode_operator_request(value)  # type: ignore[arg-type]
    assert exc_info.value.code == "OPERATOR_WIRE_BYTES_REQUIRED"


def test_invalid_utf8_is_rejected() -> None:
    with pytest.raises(OperatorWireError) as exc_info:
        decode_operator_response(b"\xff\xfe")
    assert exc_info.value.code == "OPERATOR_WIRE_INVALID_UTF8"


def test_response_refs_must_be_array_of_identifiers() -> None:
    with pytest.raises(OperatorWireError) as exc_info:
        decode_operator_response(b'{"ok":true,"code":"OK","refs":"not-a-list"}')
    assert exc_info.value.code == "OPERATOR_WIRE_RESPONSE_INVALID"

    with pytest.raises(OperatorWireError) as exc_info:
        decode_operator_response(b'{"ok":true,"code":"OK","refs":["valid","contains spaces"]}')
    assert exc_info.value.code == "OPERATOR_WIRE_RESPONSE_INVALID"


def test_response_required_fields_are_enforced() -> None:
    with pytest.raises(OperatorWireError) as exc_info:
        decode_operator_response(b'{"ok":true}')
    assert exc_info.value.code == "OPERATOR_WIRE_FIELDS_INVALID"
