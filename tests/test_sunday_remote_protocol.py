from __future__ import annotations

import json

import pytest

from a_conductor.sunday_remote_protocol import (
    ReplayWindow,
    RemoteProtocolError,
    parse_and_verify_request,
    sign_request,
)


SECRET = b"s" * 32
NOW = 1_789_617_600_000


def test_signed_request_round_trips() -> None:
    envelope = sign_request(
        secret=SECRET,
        operation="context.verify",
        payload={},
        request_id="req-1",
        nonce="nonce-1",
        issued_at_ms=NOW,
    )

    request = parse_and_verify_request(
        envelope.to_json_bytes(),
        secret=SECRET,
        replay_window=ReplayWindow(),
        now_ms=NOW,
    )

    assert request.request_id == "req-1"
    assert request.operation == "context.verify"
    assert request.payload == {}


def test_tampered_payload_fails_authentication() -> None:
    envelope = sign_request(
        secret=SECRET,
        operation="fs.read",
        payload={"path": "README.md"},
        request_id="req-2",
        nonce="nonce-2",
        issued_at_ms=NOW,
    )
    decoded = json.loads(envelope.to_json_bytes().decode("utf-8"))
    decoded["payload"]["path"] = "pyproject.toml"

    with pytest.raises(RemoteProtocolError, match="AUTH_INVALID") as exc_info:
        parse_and_verify_request(
            json.dumps(decoded).encode("utf-8"),
            secret=SECRET,
            replay_window=ReplayWindow(),
            now_ms=NOW,
        )

    assert exc_info.value.code == "AUTH_INVALID"


def test_replay_is_rejected_after_first_verified_delivery() -> None:
    replay = ReplayWindow()
    envelope = sign_request(
        secret=SECRET,
        operation="context.verify",
        payload={},
        request_id="req-replay",
        nonce="nonce-replay",
        issued_at_ms=NOW,
    )

    parse_and_verify_request(
        envelope.to_json_bytes(),
        secret=SECRET,
        replay_window=replay,
        now_ms=NOW,
    )

    with pytest.raises(RemoteProtocolError, match="REPLAY_DETECTED") as exc_info:
        parse_and_verify_request(
            envelope.to_json_bytes(),
            secret=SECRET,
            replay_window=replay,
            now_ms=NOW,
        )

    assert exc_info.value.code == "REPLAY_DETECTED"


def test_expired_request_fails_closed() -> None:
    envelope = sign_request(
        secret=SECRET,
        operation="context.verify",
        payload={},
        request_id="req-old",
        nonce="nonce-old",
        issued_at_ms=NOW - 60_001,
    )

    with pytest.raises(RemoteProtocolError, match="REQUEST_EXPIRED"):
        parse_and_verify_request(
            envelope.to_json_bytes(),
            secret=SECRET,
            replay_window=ReplayWindow(),
            now_ms=NOW,
        )


def test_future_request_fails_closed() -> None:
    envelope = sign_request(
        secret=SECRET,
        operation="context.verify",
        payload={},
        request_id="req-future",
        nonce="nonce-future",
        issued_at_ms=NOW + 5_001,
    )

    with pytest.raises(RemoteProtocolError, match="REQUEST_FROM_FUTURE"):
        parse_and_verify_request(
            envelope.to_json_bytes(),
            secret=SECRET,
            replay_window=ReplayWindow(),
            now_ms=NOW,
        )


def test_unexpected_protocol_version_is_rejected() -> None:
    envelope = sign_request(
        secret=SECRET,
        operation="context.verify",
        payload={},
        request_id="req-version",
        nonce="nonce-version",
        issued_at_ms=NOW,
    )
    decoded = json.loads(envelope.to_json_bytes().decode("utf-8"))
    decoded["version"] = 2

    with pytest.raises(RemoteProtocolError, match="PROTOCOL_VERSION_UNSUPPORTED"):
        parse_and_verify_request(
            json.dumps(decoded).encode("utf-8"),
            secret=SECRET,
            replay_window=ReplayWindow(),
            now_ms=NOW,
        )


def test_secret_must_be_at_least_32_bytes() -> None:
    with pytest.raises(RemoteProtocolError, match="AUTH_SECRET_INVALID"):
        sign_request(secret=b"too-short", operation="context.verify")
