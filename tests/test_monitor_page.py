"""WO-P1-599: UI-1 read-only monitor page — truth-preserving, token-safe.

Encodes the frozen page contract: constant self-contained bytes (CSP,
no external requests), token held memory-only from the URL fragment,
UNKNOWN/STALE/DEGRADED rendered as explicit badges, GET-only page, and the
authn-gated GET /monitor route on the monitor API.
"""
from __future__ import annotations

import json
import re
import socket
import time
import urllib.error
import urllib.request

import pytest

from a_conductor.monitor_api import MonitorApiConfig, MonitorApiServer
from a_conductor.monitor_projection import build_monitor_views
from a_conductor.monitor_page import MONITOR_PAGE_BYTES, monitor_page_bytes


def start_server(provider=None):
    def default_provider():
        return build_monitor_views(
            bus_health={"degraded": False, "counters": {"OBSERVE": 3},
                        "conditions": []},
            timeline_records=[],
            stm_states=[{"partition": "p1", "state": "FRESH",
                         "rebuild_required": False, "record_count": 1}],
            correlation=None,
        )

    server = MonitorApiServer(provider or default_provider,
                              MonitorApiConfig(port=0))
    server.start()
    return server


def http_get(server, path, *, token="?", origin=None):
    url = f"http://127.0.0.1:{server.port}{path}"
    request = urllib.request.Request(url)
    request.add_header("Authorization", f"Bearer {token}")
    if origin is not None:
        request.add_header("Origin", origin)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers, exc.read()


# --- pure page bytes ---------------------------------------------------------

def test_page_bytes_are_constant_and_self_contained():
    assert monitor_page_bytes() is MONITOR_PAGE_BYTES
    page = MONITOR_PAGE_BYTES.decode("utf-8")
    assert page.lstrip().startswith("<!DOCTYPE html>")
    # CSP: no external origins of any kind.
    assert "default-src 'none'" in page
    assert "connect-src 'self'" in page
    # No external resource references at all.
    assert "http://" not in page and "https://" not in page
    # No state interpolation: the bytes carry no runtime values.
    assert "{" + "health" not in page  # no server-side templating markers


def test_page_token_handling_is_memory_only():
    page = MONITOR_PAGE_BYTES.decode("utf-8")
    assert "location.hash" in page
    assert "history.replaceState" in page  # strip token from URL
    forbidden = ("localStorage", "sessionStorage", "document.cookie")
    for marker in forbidden:
        assert marker not in page
    assert "Authorization" in page  # token only ever goes in this header


def test_page_is_get_only_and_truth_preserving():
    page = MONITOR_PAGE_BYTES.decode("utf-8")
    # No mutation affordances: fetch-based GET only (default method).
    assert "fetch(" in page
    assert "method:" not in page or '"POST"' not in page
    assert "'POST'" not in page and '"PUT"' not in page and '"DELETE"' not in page
    # Truth badges are explicit labels.
    for label in ("UNKNOWN", "STALE", "DEGRADED"):
        assert label in page
    assert "rebuild_required" in page  # STM recovery semantics surfaced


def test_page_polls_snapshot_with_backoff():
    page = MONITOR_PAGE_BYTES.decode("utf-8")
    assert "/snapshot" in page
    assert "403" in page and "503" in page  # explicit forbidden/error states


# --- /monitor route ----------------------------------------------------------

def test_monitor_route_requires_token():
    server = start_server()
    try:
        status, _, body = http_get(server, "/monitor", token="wrong")
        assert status == 403
        assert b"MONITOR_FORBIDDEN" in body
        assert server.token.encode() not in body
    finally:
        server.stop()


def test_monitor_route_serves_page_with_valid_token():
    server = start_server()
    try:
        status, headers, body = http_get(server, "/monitor", token=server.token)
        assert status == 200
        assert headers.get("Content-Type") == "text/html; charset=utf-8"
        assert body == MONITOR_PAGE_BYTES
        assert server.token.encode() not in body
    finally:
        server.stop()


def test_monitor_route_rejects_foreign_origin():
    server = start_server()
    try:
        status, _, body = http_get(server, "/monitor", token=server.token,
                                   origin="https://evil.example")
        assert status == 403 and b"MONITOR_FORBIDDEN" in body
    finally:
        server.stop()


def test_monitor_route_rejects_dns_rebinding_host():
    server = start_server()
    try:
        with socket.create_connection(("127.0.0.1", server.port), timeout=5) as s:
            s.sendall((
                f"GET /monitor HTTP/1.1\r\nHost: evil.example:{server.port}\r\n"
                f"Authorization: Bearer {server.token}\r\nConnection: close\r\n\r\n"
            ).encode("utf-8"))
            s.settimeout(3)
            data = b""
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                data += chunk
        first = data.splitlines()[0]
        assert b"403" in first and b"MONITOR_FORBIDDEN" in data
    finally:
        server.stop()


def test_monitor_route_post_is_read_only():
    server = start_server()
    try:
        with socket.create_connection(("127.0.0.1", server.port), timeout=5) as s:
            s.sendall((
                f"POST /monitor HTTP/1.1\r\nHost: 127.0.0.1:{server.port}\r\n"
                f"Authorization: Bearer {server.token}\r\nConnection: close\r\n\r\n"
            ).encode("utf-8"))
            s.settimeout(3)
            data = b""
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                data += chunk
        assert b"405" in data.splitlines()[0] and b"MONITOR_READ_ONLY" in data
    finally:
        server.stop()
