"""Authenticated, replay-protected wire protocol for SunDay Runtime remote calls.

This module is intentionally transport-neutral.  It defines a compact signed
request envelope and a bounded replay window.  It owns no scheduling, claims,
providers, review, retry, completion, merge, or project-memory authority.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from typing import Callable, Mapping


PROTOCOL_VERSION = 1
DEFAULT_MAX_AGE_MS = 60_000
DEFAULT_MAX_FUTURE_SKEW_MS = 5_000
DEFAULT_MAX_BODY_BYTES = 1_048_576
DEFAULT_REPLAY_CAPACITY = 4_096
_MAX_IDENTITY_TEXT_CHARS = 128


class RemoteProtocolError(RuntimeError):
    """Stable fail-closed protocol error."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _require_text(
    value: object,
    code: str,
    *,
    max_chars: int | None = None,
) -> str:
    if not isinstance(value, str) or not value.strip() or "\\x00" in value:
        raise RemoteProtocolError(code)
    rendered = value.strip()
    if max_chars is not None and len(rendered) > max_chars:
        raise RemoteProtocolError(code)
    return rendered

def _require_int(value: object, code: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise RemoteProtocolError(code)
    return value


def _require_payload(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise RemoteProtocolError("PROTOCOL_INVALID")
    rendered: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key or "\x00" in key:
            raise RemoteProtocolError("PROTOCOL_INVALID")
        rendered[key] = item
    return rendered


def _normalize_secret(secret: bytes | bytearray | memoryview) -> bytes:
    if not isinstance(secret, (bytes, bytearray, memoryview)):
        raise RemoteProtocolError("AUTH_SECRET_INVALID")
    value = bytes(secret)
    if len(value) < 32:
        raise RemoteProtocolError("AUTH_SECRET_INVALID")
    return value


def _canonical_unsigned_payload(
    *,
    version: int,
    request_id: str,
    issued_at_ms: int,
    nonce: str,
    operation: str,
    payload: Mapping[str, object],
) -> bytes:
    body = {
        "issued_at_ms": issued_at_ms,
        "nonce": nonce,
        "operation": operation,
        "payload": dict(payload),
        "request_id": request_id,
        "version": version,
    }
    try:
        rendered = json.dumps(
            body,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise RemoteProtocolError("PROTOCOL_INVALID") from exc
    return rendered.encode("utf-8")


@dataclass(frozen=True, slots=True)
class RemoteRequestEnvelope:
    version: int
    request_id: str
    issued_at_ms: int
    nonce: str
    operation: str
    payload: dict[str, object]
    signature: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "RemoteRequestEnvelope":
        if not isinstance(value, Mapping):
            raise RemoteProtocolError("PROTOCOL_INVALID")
        expected = {
            "version",
            "request_id",
            "issued_at_ms",
            "nonce",
            "operation",
            "payload",
            "signature",
        }
        if set(value) != expected:
            raise RemoteProtocolError("PROTOCOL_INVALID")
        version = _require_int(value.get("version"), "PROTOCOL_INVALID")
        if version != PROTOCOL_VERSION:
            raise RemoteProtocolError("PROTOCOL_VERSION_UNSUPPORTED")
        issued_at_ms = _require_int(value.get("issued_at_ms"), "PROTOCOL_INVALID")
        if issued_at_ms < 0:
            raise RemoteProtocolError("PROTOCOL_INVALID")
        request_id = _require_text(value.get("request_id"), "PROTOCOL_INVALID", max_chars=_MAX_IDENTITY_TEXT_CHARS)
        nonce = _require_text(value.get("nonce"), "PROTOCOL_INVALID", max_chars=_MAX_IDENTITY_TEXT_CHARS)
        operation = _require_text(value.get("operation"), "PROTOCOL_INVALID", max_chars=_MAX_IDENTITY_TEXT_CHARS)
        signature = _require_text(value.get("signature"), "AUTH_INVALID")
        if len(signature) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in signature):
            raise RemoteProtocolError("AUTH_INVALID")
        payload = _require_payload(value.get("payload"))
        return cls(
            version=version,
            request_id=request_id,
            issued_at_ms=issued_at_ms,
            nonce=nonce,
            operation=operation,
            payload=payload,
            signature=signature.lower(),
        )

    def unsigned_bytes(self) -> bytes:
        return _canonical_unsigned_payload(
            version=self.version,
            request_id=self.request_id,
            issued_at_ms=self.issued_at_ms,
            nonce=self.nonce,
            operation=self.operation,
            payload=self.payload,
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "version": self.version,
            "request_id": self.request_id,
            "issued_at_ms": self.issued_at_ms,
            "nonce": self.nonce,
            "operation": self.operation,
            "payload": dict(self.payload),
            "signature": self.signature,
        }

    def to_json_bytes(self) -> bytes:
        try:
            return json.dumps(
                self.to_mapping(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise RemoteProtocolError("PROTOCOL_INVALID") from exc


@dataclass(frozen=True, slots=True)
class VerifiedRemoteRequest:
    request_id: str
    operation: str
    payload: dict[str, object]
    issued_at_ms: int
    nonce: str


class ReplayWindow:
    """Bounded in-memory replay guard keyed by both request id and nonce."""

    def __init__(
        self,
        *,
        capacity: int = DEFAULT_REPLAY_CAPACITY,
        retention_ms: int = DEFAULT_MAX_AGE_MS + DEFAULT_MAX_FUTURE_SKEW_MS,
    ) -> None:
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 1:
            raise ValueError("capacity must be a positive integer")
        if not isinstance(retention_ms, int) or isinstance(retention_ms, bool) or retention_ms < 1:
            raise ValueError("retention_ms must be a positive integer")
        self._capacity = capacity
        self._retention_ms = retention_ms
        self._request_ids: OrderedDict[str, int] = OrderedDict()
        self._nonces: OrderedDict[str, int] = OrderedDict()
        self._lock = Lock()

    @staticmethod
    def _purge(container: OrderedDict[str, int], cutoff_ms: int) -> None:
        while container:
            _, seen_ms = next(iter(container.items()))
            if seen_ms >= cutoff_ms:
                break
            container.popitem(last=False)

    def _trim_capacity(self) -> None:
        while len(self._request_ids) > self._capacity:
            self._request_ids.popitem(last=False)
        while len(self._nonces) > self._capacity:
            self._nonces.popitem(last=False)

    def check_and_record(self, request_id: str, nonce: str, *, now_ms: int) -> None:
        with self._lock:
            cutoff = now_ms - self._retention_ms
            self._purge(self._request_ids, cutoff)
            self._purge(self._nonces, cutoff)
            if request_id in self._request_ids or nonce in self._nonces:
                raise RemoteProtocolError("REPLAY_DETECTED")
            self._request_ids[request_id] = now_ms
            self._nonces[nonce] = now_ms
            self._trim_capacity()


def sign_request(
    *,
    secret: bytes | bytearray | memoryview,
    operation: str,
    payload: Mapping[str, object] | None = None,
    request_id: str | None = None,
    nonce: str | None = None,
    issued_at_ms: int | None = None,
    clock_ms: Callable[[], int] | None = None,
) -> RemoteRequestEnvelope:
    key = _normalize_secret(secret)
    operation_text = _require_text(operation, "PROTOCOL_INVALID", max_chars=_MAX_IDENTITY_TEXT_CHARS)
    request_text = request_id or secrets.token_hex(16)
    nonce_text = nonce or secrets.token_hex(16)
    _require_text(request_text, "PROTOCOL_INVALID", max_chars=_MAX_IDENTITY_TEXT_CHARS)
    _require_text(nonce_text, "PROTOCOL_INVALID", max_chars=_MAX_IDENTITY_TEXT_CHARS)
    payload_dict = _require_payload({} if payload is None else payload)
    if issued_at_ms is None:
        source = clock_ms or (lambda: time.time_ns() // 1_000_000)
        issued = _require_int(source(), "PROTOCOL_INVALID")
    else:
        issued = _require_int(issued_at_ms, "PROTOCOL_INVALID")
    if issued < 0:
        raise RemoteProtocolError("PROTOCOL_INVALID")
    unsigned = _canonical_unsigned_payload(
        version=PROTOCOL_VERSION,
        request_id=request_text,
        issued_at_ms=issued,
        nonce=nonce_text,
        operation=operation_text,
        payload=payload_dict,
    )
    signature = hmac.new(key, unsigned, hashlib.sha256).hexdigest()
    return RemoteRequestEnvelope(
        version=PROTOCOL_VERSION,
        request_id=request_text,
        issued_at_ms=issued,
        nonce=nonce_text,
        operation=operation_text,
        payload=payload_dict,
        signature=signature,
    )


def parse_and_verify_request(
    body: bytes,
    *,
    secret: bytes | bytearray | memoryview,
    replay_window: ReplayWindow,
    now_ms: int | None = None,
    clock_ms: Callable[[], int] | None = None,
    max_age_ms: int = DEFAULT_MAX_AGE_MS,
    max_future_skew_ms: int = DEFAULT_MAX_FUTURE_SKEW_MS,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
) -> VerifiedRemoteRequest:
    key = _normalize_secret(secret)
    if not isinstance(body, (bytes, bytearray, memoryview)):
        raise RemoteProtocolError("PROTOCOL_INVALID")
    raw = bytes(body)
    if len(raw) > max_body_bytes:
        raise RemoteProtocolError("REQUEST_TOO_LARGE")
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RemoteProtocolError("PROTOCOL_INVALID") from exc
    envelope = RemoteRequestEnvelope.from_mapping(decoded)
    expected = hmac.new(key, envelope.unsigned_bytes(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, envelope.signature):
        raise RemoteProtocolError("AUTH_INVALID")
    if now_ms is None:
        source = clock_ms or (lambda: time.time_ns() // 1_000_000)
        now = _require_int(source(), "PROTOCOL_INVALID")
    else:
        now = _require_int(now_ms, "PROTOCOL_INVALID")
    if envelope.issued_at_ms < now - max_age_ms:
        raise RemoteProtocolError("REQUEST_EXPIRED")
    if envelope.issued_at_ms > now + max_future_skew_ms:
        raise RemoteProtocolError("REQUEST_FROM_FUTURE")
    replay_window.check_and_record(envelope.request_id, envelope.nonce, now_ms=now)
    return VerifiedRemoteRequest(
        request_id=envelope.request_id,
        operation=envelope.operation,
        payload=dict(envelope.payload),
        issued_at_ms=envelope.issued_at_ms,
        nonce=envelope.nonce,
    )
