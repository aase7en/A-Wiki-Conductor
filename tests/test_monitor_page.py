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
from datetime import datetime, timezone

import pytest

from a_conductor.monitor_api import MonitorApiConfig, MonitorApiServer
from a_conductor.monitor_projection import build_monitor_views
from a_conductor.monitor_page import MONITOR_PAGE_BYTES, monitor_page_bytes
from a_conductor.inspector_projection import (
    ToolInspectorRow, build_inspector_views,
)


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
    # Backoff contract: no fixed-rate interval; self-scheduling with growth.
    assert "setInterval" not in page
    assert "backoff" in page and "setTimeout" in page
    # A rejected token must halt the fetch loop entirely: the fatal branch
    # RETHROWS so the reschedule .then is skipped (structural marker of the
    # actual halt mechanism — presence of the function name alone proved
    # vacuous in round 2).
    assert "throw e; }  // fatal: skip reschedule" in page
    assert ".catch(function () {});  // swallow the expected fatal rejection" in page


def test_page_escapes_badge_labels_and_clamps_correlation_state():
    page = MONITOR_PAGE_BYTES.decode("utf-8")
    # badge() must escape its label like every other dynamic sink.
    assert "esc(label)" in page
    # Only enum-known good correlation states render green.
    assert '"OBSERVED"' in page  # explicit allowlist for the ok class


def test_page_has_flat_inspector_groups_and_disconnected_badge():
    page = MONITOR_PAGE_BYTES.decode("utf-8")
    assert re.findall(r"<h2>(.*?)</h2>", page) == [
        "Health", "Timeline", "STM partitions", "Correlation", "Inspector",
    ]
    assert '<div id="inspector-section">' in page
    assert "function renderInspector(v)" in page
    assert "renderInspector(views.inspector);" in page
    for group in ("Tools", "Hooks", "Skills"):
        assert group in page
    assert ".disconnected{" in page
    assert '"DISCONNECTED" ? "disconnected"' in page
    assert 'badge("UNKNOWN", "unknown") + " no inspector evidence"' in page
    assert 'known.indexOf(state) === -1' in page
    assert 'group[0] === "skills"' in page and 'known.push("AVAILABLE")' in page
    assert "rows.slice(-128)" in page
    assert 'esc(String(r.name || "UNKNOWN")' in page
    assert "esc(label)" in page
    assert "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'" in page
    assert re.findall(r"https?://", page, re.IGNORECASE) == []
    for marker in ("localStorage", "sessionStorage", "document.cookie"):
        assert marker not in page
    # The Python string must not turn a JS escaped double-quote key into """.
    assert '\'"\':"&quot;"' in page


def _monitor_with_inspector(inspector=None):
    return build_monitor_views(
        bus_health={"degraded": False, "counters": {"OBSERVE": 3}, "conditions": []},
        timeline_records=[], stm_states=[], correlation=None, inspector=inspector,
    )


def _inspector_fixture():
    return build_inspector_views(
        tools=(ToolInspectorRow(
            name="fixture", device="windows-local", category="connector",
            source="instance.ps1 discovery", phase="REGISTERED", state="UNKNOWN",
            registration_evidence="instance.ps1", last_verified=None, last_error="",
            next_safe_action="Inspect health", provenance="discovery-only",
        ),), hooks=(), skills=(),
        now=datetime(2026, 11, 9, 10, 0, tzinfo=timezone.utc),
    )


def test_monitor_inspector_absence_is_explicit_unknown():
    views = _monitor_with_inspector()
    assert views["inspector"] == {"state": "UNKNOWN", "reason": "INSPECTOR_NOT_PROVIDED"}
    assert views["health"] == {"degraded": False, "counters": {"OBSERVE": 3}, "conditions": []}
    assert views["timeline"] == [] and views["stm"] == []
    assert views["correlation"] == {"state": "UNKNOWN"}


@pytest.mark.parametrize("inspector", [{}, [], {"tools": "bad"}, {"state": "READY"}])
def test_invalid_inspector_degrades_only_its_own_view(inspector):
    views = _monitor_with_inspector(inspector)
    assert views["inspector"] == {"state": "DEGRADED", "reason": "INSPECTOR_PROJECTION_INVALID"}
    assert views["health"]["degraded"] is False


def test_monitor_inspector_revalidates_redacts_and_recounts_without_mutation():
    inspector = _inspector_fixture()
    inspector["tools"][0]["state"] = "invented"
    inspector["tools"][0]["phase"] = "invented"
    inspector["tools"][0]["last_error"] = "token=FAKE0000000000000000000000"
    inspector["tools"][0]["private_payload"] = "must not pass"
    inspector["summary"]["tools"]["counts"] = {"READY": 99}
    before = json.dumps(inspector, sort_keys=True)
    view = _monitor_with_inspector(inspector)["inspector"]
    assert view["tools"][0]["state"] == "UNKNOWN"
    assert view["tools"][0]["phase"] == "UNKNOWN"
    assert view["tools"][0]["last_error"] == "[REDACTED]"
    assert view["summary"]["tools"]["counts"] == {"UNKNOWN": 1}
    assert "private_payload" not in view["tools"][0]
    assert json.dumps(inspector, sort_keys=True) == before


def test_monitor_inspector_preserves_truncation_evidence():
    inspector = _inspector_fixture()
    inspector["tools"] *= 129
    inspector["summary"]["tools"]["truncated"] = True
    inspector["summary"]["tools"]["dropped"] = 2
    view = _monitor_with_inspector(inspector)["inspector"]
    assert len(view["tools"]) == 128
    assert view["summary"]["tools"]["counts"] == {"UNKNOWN": 128}
    assert view["summary"]["tools"]["truncated"] is True
    assert view["summary"]["tools"]["dropped"] == 3


def test_monitor_inspector_hostile_dict_and_bad_row_are_isolated():
    class Hostile(dict):
        def __getitem__(self, key):
            raise RuntimeError("token=FAKE0000000000000000")

    for inspector in (Hostile(), _inspector_fixture()):
        if type(inspector) is dict:
            inspector["tools"][0]["name"] = ""
        view = _monitor_with_inspector(inspector)["inspector"]
        assert view == {"state": "DEGRADED", "reason": "INSPECTOR_PROJECTION_INVALID"}


@pytest.mark.parametrize("secret", [
    "Authorization: Basic RkFLRTpGQUtF",
    'Authorization: Digest username="FAKE", response="FAKE"',
    "ftp://fixture-user:FAKE-PASSWORD@example.invalid/path",
    "t\u043eken=FAKE-CREDENTIAL",
    "\uff54\uff4f\uff4b\uff45\uff4e=FAKE-CREDENTIAL",
])
@pytest.mark.parametrize("section,field", [
    ("tools", "name"), ("tools", "last_error"),
    ("skills", "routing_hint"), ("hooks", "provenance"),
])
def test_monitor_reprojection_redacts_auth_userinfo_and_unicode_markers(secret, section, field):
    inspector = _inspector_fixture()
    inspector["hooks"] = [{
        "name": "fixture-hook", "hook_class": "OBSERVE", "authority_source": "contract:1.0.0",
        "enabled": True, "fail_mode": "UNKNOWN", "state": "UNKNOWN",
        "last_event": "", "last_error": "", "provenance": "contract-only",
    }]
    inspector["skills"] = [{
        "name": "fixture-skill", "state": "AVAILABLE", "registry_source": "skills-registry.json",
        "routing_hint": "fixture", "harness": "all", "deprecated": False,
        "duplicate": False, "provenance": "registry-only",
    }]
    inspector[section][0][field] = secret
    view = _monitor_with_inspector(inspector)
    assert view["inspector"][section][0][field] == "[REDACTED]"
    serialized = json.dumps(view, ensure_ascii=False)
    assert secret not in serialized
    assert "FAKE" not in serialized


@pytest.mark.parametrize("sign", [-1, 1])
def test_monitor_oversized_last_verified_is_isolated_and_snapshot_serializes(sign):
    inspector = _inspector_fixture()
    inspector["tools"][0]["last_verified"] = sign * 10**5000
    baseline = _monitor_with_inspector()
    view = _monitor_with_inspector(inspector)
    assert view["inspector"] == {"state": "DEGRADED", "reason": "INSPECTOR_PROJECTION_INVALID"}
    for key in ("health", "timeline", "stm", "correlation"):
        assert view[key] == baseline[key]
    assert json.loads(json.dumps(view)) == view


@pytest.mark.parametrize("verified", [-(2**53), 2**53])
def test_monitor_last_verified_safe_integer_endpoints_serialize(verified):
    inspector = _inspector_fixture()
    inspector["tools"][0]["last_verified"] = verified
    view = _monitor_with_inspector(inspector)
    assert view["inspector"]["tools"][0]["last_verified"] == verified
    assert json.loads(json.dumps(view)) == view


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
