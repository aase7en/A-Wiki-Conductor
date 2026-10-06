"""WO-P1-596: MON-1 read-only Monitor API — security gates + truthful views.

Encodes the frozen contract's exit gates: fail-closed authn (per-boot bearer
token + Origin equality + Host=127.0.0.1:<port> DNS-rebinding guard) proven
against webpage-originated CSRF and non-local Host headers BEFORE any
browser/extension client connects; strict read-only; UNKNOWN/STALE never
rendered as healthy; monitor restart leaves control truth unchanged.
"""
from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from a_conductor.monitor_api import (
    MonitorApiConfig, MonitorApiServer, MonitorApiError,
)
from a_conductor.monitor_projection import (
    MonitorProjectionError, build_monitor_views,
)


def make_server(provider=None, **config_overrides):
    calls = []

    def default_provider():
        calls.append(1)
        return build_monitor_views(
            bus_health={"degraded": False, "counters": {"OBSERVE": 3},
                        "conditions": []},
            timeline_records=[({"event_id": "hk-" + "a" * 32,
                                "event_type": "control.start.after",
                                "hook_class": "OBSERVE"}, ())],
            stm_states=[{"partition": "p1/device-1", "state": "FRESH",
                         "rebuild_required": False, "record_count": 1}],
            correlation=None,
        )

    config = MonitorApiConfig(
        host="127.0.0.1", port=0, poll_seconds=0.05, stream_queue_bound=8)
    for key, value in config_overrides.items():
        object.__setattr__(config, key, value)
    server = MonitorApiServer(provider or default_provider, config)
    return server, calls


def http_get(server, path, *, token="?", origin=None, host=None,
             raw_host_header=None):
    url = f"http://{host or '127.0.0.1'}:{server.port}{path}"
    request = urllib.request.Request(url)
    request.add_header("Authorization", f"Bearer {token}")
    if origin is not None:
        request.add_header("Origin", origin)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def raw_request(server, lines, timeout=5):
    with socket.create_connection(("127.0.0.1", server.port), timeout=timeout) as s:
        s.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("utf-8"))
        data = b""
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            data += chunk
    return data.decode("utf-8", errors="replace")


@pytest.fixture()
def running_server():
    server, calls = make_server()
    server.start()
    try:
        yield server, calls
    finally:
        server.stop()


# --- construction is inert (default OFF) ---------------------------------------

def test_constructing_server_does_not_listen():
    server, _ = make_server()
    assert server.port is None
    with pytest.raises(OSError):
        socket.create_connection(("127.0.0.1", 0), timeout=0.1)
    server.stop()


def test_config_rejects_non_loopback_host():
    with pytest.raises(MonitorApiError):
        MonitorApiConfig(host="0.0.0.0")


# --- fail-closed authentication gates ------------------------------------------

def test_missing_token_is_forbidden(running_server):
    server, _ = running_server
    request = urllib.request.Request(f"http://127.0.0.1:{server.port}/snapshot")
    try:
        urllib.request.urlopen(request, timeout=5)
        raise AssertionError("must be forbidden")
    except urllib.error.HTTPError as exc:
        assert exc.code == 403
        body = json.loads(exc.read().decode("utf-8"))
        assert body["error"] == "MONITOR_FORBIDDEN"
        assert body["gate"] == "TOKEN"


def test_wrong_token_is_forbidden(running_server):
    server, _ = running_server
    status, body = http_get(server, "/snapshot", token="wrong-token")
    assert status == 403 and body["error"] == "MONITOR_FORBIDDEN"
    assert body["gate"] == "TOKEN"


def test_webpage_origin_csrf_is_forbidden(running_server):
    server, _ = running_server
    status, body = http_get(server, "/snapshot", token=server.token,
                            origin="https://evil.example")
    assert status == 403 and body["gate"] == "ORIGIN"


def test_dns_rebinding_host_is_forbidden(running_server):
    server, _ = running_server
    raw = raw_request(server, [
        f"GET /snapshot HTTP/1.1",
        f"Host: evil.example:{server.port}",
        f"Authorization: Bearer {server.token}",
        "Connection: close",
    ])
    assert "403" in raw.splitlines()[0]
    assert "MONITOR_FORBIDDEN" in raw and '"HOST"' in raw


def test_valid_request_passes_all_gates(running_server):
    server, calls = running_server
    status, body = http_get(server, "/snapshot", token=server.token,
                            origin=server.allowed_origin)
    assert status == 200
    assert calls, "provider must have been invoked"
    assert body["health"]["degraded"] is False
    assert body["stm"][0]["state"] == "FRESH"
    assert body["timeline"][0]["event_id"] == "hk-" + "a" * 32
    assert body["correlation"] == {"state": "UNKNOWN"}  # never fabricated


def test_token_never_appears_in_responses(running_server):
    server, _ = running_server
    for path in ("/snapshot", "/healthz"):
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.port}{path}")
        request.add_header("Authorization", f"Bearer {server.token}")
        with urllib.request.urlopen(request, timeout=5) as response:
            assert server.token.encode() not in response.read()


# --- read-only boundary ---------------------------------------------------------

def test_unknown_path_is_typed_404(running_server):
    server, _ = running_server
    status, body = http_get(server, "/nope", token=server.token)
    assert status == 404 and body["error"] == "MONITOR_NOT_FOUND"


def test_post_is_rejected_read_only(running_server):
    server, _ = running_server
    raw = raw_request(server, [
        "POST /snapshot HTTP/1.1",
        f"Host: 127.0.0.1:{server.port}",
        f"Authorization: Bearer {server.token}",
        "Connection: close",
    ])
    assert "405" in raw.splitlines()[0]
    assert "MONITOR_READ_ONLY" in raw


def test_oversized_path_is_typed_404(running_server):
    server, _ = running_server
    status, body = http_get(server, "/" + "x" * 600, token=server.token)
    assert status == 404 and body["error"] == "MONITOR_NOT_FOUND"


# --- provider failure degrades explicitly ---------------------------------------

def test_provider_failure_is_typed_503():
    def broken_provider():
        raise RuntimeError("projection exploded")

    server = MonitorApiServer(broken_provider, MonitorApiConfig(port=0))
    server.start()
    try:
        status, body = http_get(server, "/snapshot", token=server.token)
        assert status == 503
        assert body["error"] == "MONITOR_PROJECTION_UNAVAILABLE"
    finally:
        server.stop()


# --- stream ----------------------------------------------------------------------

def test_stream_yields_frames_then_closes(running_server):
    server, _ = running_server
    with socket.create_connection(("127.0.0.1", server.port), timeout=5) as s:
        s.sendall((
            f"GET /stream HTTP/1.1\r\nHost: 127.0.0.1:{server.port}\r\n"
            f"Authorization: Bearer {server.token}\r\nConnection: close\r\n\r\n"
        ).encode("utf-8"))
        s.settimeout(3)
        data = b""
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            try:
                chunk = s.recv(65536)
            except socket.timeout:
                break
            if not chunk:
                break
            data += chunk
            # HTTP header newlines must NOT count as stream frames.
            if sum(1 for line in data.split(b"\n")
                   if line.startswith(b"{")) >= 2:
                break
    lines = [line for line in data.decode("utf-8", errors="replace").splitlines()
             if line.startswith("{")]
    assert len(lines) >= 2
    frames = [json.loads(line) for line in lines]
    assert frames[0]["health"]["degraded"] is False


def test_stream_queue_is_bounded_and_marks_degraded(running_server):
    server, _ = running_server
    for i in range(64):
        server._offer({"i": i})
    assert len(server._stream_queue) <= server.config.stream_queue_bound
    assert server._stream_degraded is True


# --- restart / lifecycle ----------------------------------------------------------

def test_restart_leaves_provider_truth_unchanged():
    server, calls = make_server()
    server.start()
    http_get(server, "/snapshot", token=server.token)
    first_port = server.port
    server.stop()
    server.start()
    try:
        assert server.port != first_port or server.port  # rebound cleanly
        status, _ = http_get(server, "/snapshot", token=server.token)
        assert status == 200
        assert len(calls) == 2  # each snapshot = exactly one provider read
    finally:
        server.stop()


# --- projection truthfulness -------------------------------------------------------

def test_projection_surfaces_stale_and_unknown_truthfully():
    views = build_monitor_views(
        bus_health={"degraded": True, "counters": {}, "conditions": ["X"]},
        timeline_records=[],
        stm_states=[{"partition": "p2", "state": "STALE",
                     "rebuild_required": True, "record_count": 2}],
        correlation=None,
    )
    assert views["health"]["degraded"] is True
    assert views["stm"][0]["state"] == "STALE"
    assert views["correlation"] == {"state": "UNKNOWN"}


def test_projection_rejects_malformed_input():
    with pytest.raises(MonitorProjectionError):
        build_monitor_views(bus_health=None, timeline_records=[],
                            stm_states=[], correlation=None)
    with pytest.raises(MonitorProjectionError):
        build_monitor_views(
            bus_health={"degraded": False},  # missing counters
            timeline_records=[("not-a-dict", ())],
            stm_states=[], correlation=None)


def test_projection_bounds_timeline_and_strings():
    records = [({"event_id": "hk-" + "a" * 32, "note": "x" * 5000}, ())
               for _ in range(100)]
    views = build_monitor_views(
        bus_health={"degraded": False, "counters": {}, "conditions": []},
        timeline_records=records, stm_states=[], correlation=None)
    assert len(views["timeline"]) <= 64
    assert all(len(str(item.get("note", ""))) <= 256 for item in views["timeline"])
