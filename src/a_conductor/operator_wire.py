"""Strict bounded JSON wire codec for A-Conductor operator messages.

This module contains no network, socket, HTTP, Telegram, Discord, credential,
SQL, subprocess, planner, or execution implementation. It only serializes and
validates the already-bounded operator protocol types.
"""

from __future__ import annotations

import json
from typing import Any

from .operator_protocol import (
    OperatorProtocolError,
    OperatorRequest,
    OperatorResponse,
    parse_operator_request,
)


DEFAULT_REQUEST_MAX_BYTES = 4096
DEFAULT_RESPONSE_MAX_BYTES = 8192


class OperatorWireError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _require_limit(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise OperatorWireError("OPERATOR_WIRE_LIMIT_INVALID")
    return value


def _ensure_size(data: bytes, max_bytes: int) -> None:
    if len(data) > max_bytes:
        raise OperatorWireError("OPERATOR_WIRE_TOO_LARGE")


def _strict_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise OperatorWireError("OPERATOR_WIRE_DUPLICATE_KEY")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ValueError("non-finite JSON constant")


def _decode_object(data: bytes, *, max_bytes: int) -> dict[str, Any]:
    max_bytes = _require_limit(max_bytes)
    if not isinstance(data, bytes):
        raise OperatorWireError("OPERATOR_WIRE_BYTES_REQUIRED")
    _ensure_size(data, max_bytes)
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise OperatorWireError("OPERATOR_WIRE_INVALID_UTF8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_strict_object_pairs,
            parse_constant=_reject_constant,
        )
    except OperatorWireError:
        raise
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise OperatorWireError("OPERATOR_WIRE_INVALID_JSON") from exc
    if not isinstance(value, dict):
        raise OperatorWireError("OPERATOR_WIRE_OBJECT_REQUIRED")
    return value


def _encode_mapping(mapping: dict[str, Any], *, max_bytes: int) -> bytes:
    max_bytes = _require_limit(max_bytes)
    try:
        data = json.dumps(
            mapping,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise OperatorWireError("OPERATOR_WIRE_ENCODE_FAILED") from exc
    _ensure_size(data, max_bytes)
    return data


def _request_mapping(request: OperatorRequest) -> dict[str, Any]:
    if not isinstance(request, OperatorRequest):
        raise OperatorWireError("OPERATOR_WIRE_REQUEST_INVALID")
    mapping: dict[str, Any] = {
        "protocol_version": request.protocol_version,
        "action": request.action.value,
    }
    for field_name in (
        "job_id",
        "work_order_ref",
        "project_id",
        "max_attempts",
        "expected_version",
        "worker_id",
        "checkpoint_ref",
        "evidence_ref",
        "operation_ref",
    ):
        value = getattr(request, field_name)
        if value is not None:
            mapping[field_name] = value
    return mapping


def _response_mapping(response: OperatorResponse) -> dict[str, Any]:
    if not isinstance(response, OperatorResponse):
        raise OperatorWireError("OPERATOR_WIRE_RESPONSE_INVALID")
    mapping: dict[str, Any] = {
        "ok": response.ok,
        "code": response.code,
        "refs": list(response.refs),
    }
    for field_name in (
        "job_id",
        "state",
        "version",
        "worker_id",
        "attempt_count",
        "max_attempts",
    ):
        value = getattr(response, field_name)
        if value is not None:
            mapping[field_name] = value
    return mapping


def encode_operator_request(
    request: OperatorRequest,
    *,
    max_bytes: int = DEFAULT_REQUEST_MAX_BYTES,
) -> bytes:
    return _encode_mapping(_request_mapping(request), max_bytes=max_bytes)


def decode_operator_request(
    data: bytes,
    *,
    max_bytes: int = DEFAULT_REQUEST_MAX_BYTES,
) -> OperatorRequest:
    mapping = _decode_object(data, max_bytes=max_bytes)
    try:
        return parse_operator_request(mapping)
    except OperatorProtocolError as exc:
        raise OperatorWireError(exc.code) from exc


def encode_operator_response(
    response: OperatorResponse,
    *,
    max_bytes: int = DEFAULT_RESPONSE_MAX_BYTES,
) -> bytes:
    return _encode_mapping(_response_mapping(response), max_bytes=max_bytes)


def decode_operator_response(
    data: bytes,
    *,
    max_bytes: int = DEFAULT_RESPONSE_MAX_BYTES,
) -> OperatorResponse:
    mapping = _decode_object(data, max_bytes=max_bytes)
    required = {"ok", "code"}
    optional = {
        "job_id",
        "state",
        "version",
        "worker_id",
        "attempt_count",
        "max_attempts",
        "refs",
    }
    keys = set(mapping)
    if not required.issubset(keys) or not keys.issubset(required | optional):
        raise OperatorWireError("OPERATOR_WIRE_FIELDS_INVALID")

    refs = mapping.get("refs", [])
    if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
        raise OperatorWireError("OPERATOR_WIRE_RESPONSE_INVALID")

    try:
        return OperatorResponse(
            ok=mapping["ok"],
            code=mapping["code"],
            job_id=mapping.get("job_id"),
            state=mapping.get("state"),
            version=mapping.get("version"),
            worker_id=mapping.get("worker_id"),
            attempt_count=mapping.get("attempt_count"),
            max_attempts=mapping.get("max_attempts"),
            refs=tuple(refs),
        )
    except (OperatorProtocolError, TypeError, ValueError) as exc:
        raise OperatorWireError("OPERATOR_WIRE_RESPONSE_INVALID") from exc
