from __future__ import annotations

from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from a_conductor.provider_configuration import (
    EgressBoundary,
    HarnessStrategy,
    ProviderConfiguration,
    ProviderEndpointConfig,
    ProviderModelConfiguration,
    ProviderProbeState,
    ProviderTrustClass,
    ProtocolFamily,
)
from a_conductor.zai_quota_probe import UrlLibJsonTransport, ZaiQuotaProbe

NOW = datetime(2026, 8, 30, 9, 0, tzinfo=timezone.utc)


def profile() -> ProviderConfiguration:
    return ProviderConfiguration(
        provider_id="zai-direct",
        display_name="Z.ai Direct",
        provider_type="cloud",
        protocol_family=ProtocolFamily.ANTHROPIC_MESSAGES,
        endpoint_ref="provider-config:zai/base-url",
        credential_ref="secret-ref:awiki-env/ZHIPU_API_KEY",
        trust_class=ProviderTrustClass.TRUSTED_THIRD_PARTY,
        egress_boundary=EgressBoundary.EXTERNAL_THIRD_PARTY,
        harness_strategies=(HarnessStrategy.CLAUDE_CODE_CLI,),
        max_concurrency=1,
        models=(ProviderModelConfiguration("glm-5.3", "GLM-5.3", supported_effort_levels=("MAX",)),),
        enabled=True,
    )


class FakeTransport:
    def __init__(self, status: int, payload: object) -> None:
        self.status = status
        self.payload = payload
        self.calls = []

    def get_json(self, url: str, *, authorization: str, timeout_seconds: float):
        self.calls.append((url, authorization, timeout_seconds))
        return self.status, self.payload


def probe_for(endpoint: str, transport: FakeTransport, secret_calls: list[str]) -> ZaiQuotaProbe:
    def resolve(reference: str) -> str:
        secret_calls.append(reference)
        return "secret-token"

    return ZaiQuotaProbe(resolve_credential=resolve, transport=transport, clock=lambda: NOW)


def test_non_zai_endpoint_fails_closed_without_secret_or_transport() -> None:
    transport = FakeTransport(200, {})
    secret_calls: list[str] = []
    result = probe_for("https://proxy.example/v1", transport, secret_calls).probe(
        profile(),
        ProviderEndpointConfig(profile().endpoint_ref, "https://proxy.example/v1"),
    )
    assert result.state is ProviderProbeState.UNAVAILABLE
    assert result.quota is None
    assert secret_calls == []
    assert transport.calls == []


def test_legacy_zai_tokens_limit_normalizes_complete_five_hour_tuple() -> None:
    transport = FakeTransport(200, {"data": {"limits": [{
        "type": "TOKENS_LIMIT", "usage": 1000, "currentValue": 400,
        "remaining": 600, "nextResetTime": 1788084000000,
    }]}})
    secret_calls: list[str] = []
    endpoint = ProviderEndpointConfig(profile().endpoint_ref, "https://api.z.ai/api/anthropic")
    result = probe_for(endpoint.base_url, transport, secret_calls).probe(profile(), endpoint)
    assert result.state is ProviderProbeState.OK
    assert result.quota is not None
    assert (result.quota.limit, result.quota.used, result.quota.remaining) == (1000, 400, 600)
    assert result.quota.window_type == "5h"
    assert result.quota.reset_at is not None
    assert result.quota.reset_in_seconds is not None
    assert secret_calls == [profile().credential_ref]
    assert transport.calls[0][0] == "https://api.z.ai/api/monitor/usage/quota/limit"
    assert transport.calls[0][1] == "secret-token"


def test_credit_limit_requires_explicit_five_hour_window_shape() -> None:
    payload = {"data": {"limits": [
        {"type": "CREDIT_LIMIT", "unit": 6, "number": 1, "usage": 9000, "currentValue": 100, "remaining": 8900, "nextResetTime": 1788500000000},
        {"type": "CREDIT_LIMIT", "unit": 3, "number": 5, "usage": 2000, "currentValue": 1653, "remaining": 346, "nextResetTime": 1788084000000},
    ]}}
    transport = FakeTransport(200, payload)
    secret_calls: list[str] = []
    endpoint = ProviderEndpointConfig(profile().endpoint_ref, "https://open.bigmodel.cn/api/anthropic")
    result = probe_for(endpoint.base_url, transport, secret_calls).probe(profile(), endpoint)
    assert result.state is ProviderProbeState.OK
    assert result.quota is not None
    assert result.quota.unit == "credits"
    assert result.quota.limit == 2000
    assert result.quota.used == 1653
    assert result.quota.remaining == 346


def test_malformed_or_incomplete_quota_never_becomes_available() -> None:
    transport = FakeTransport(200, {"data": {"limits": [{
        "type": "TOKENS_LIMIT", "usage": 1000, "remaining": 600,
    }]}})
    endpoint = ProviderEndpointConfig(profile().endpoint_ref, "https://api.z.ai/api/anthropic")
    result = probe_for(endpoint.base_url, transport, []).probe(profile(), endpoint)
    assert result.state is ProviderProbeState.UNAVAILABLE
    assert result.quota is None


def test_http_auth_and_rate_limit_are_typed_without_secret_echo() -> None:
    endpoint = ProviderEndpointConfig(profile().endpoint_ref, "https://api.z.ai/api/anthropic")
    auth = probe_for(endpoint.base_url, FakeTransport(401, {"msg": "bad"}), []).probe(profile(), endpoint)
    limited = probe_for(endpoint.base_url, FakeTransport(429, {"msg": "slow"}), []).probe(profile(), endpoint)
    assert auth.state is ProviderProbeState.AUTH_FAILED
    assert limited.state is ProviderProbeState.RATE_LIMITED
    assert auth.quota is None
    assert limited.quota is None


def test_official_current_percentage_only_quota_shape_stays_fail_closed() -> None:
    transport = FakeTransport(200, {"data": {"limits": [{
        "type": "TOKENS_LIMIT", "percentage": 42,
    }]}})
    secret_calls: list[str] = []
    endpoint = ProviderEndpointConfig(profile().endpoint_ref, "https://api.z.ai/api/anthropic")

    result = probe_for(endpoint.base_url, transport, secret_calls).probe(profile(), endpoint)

    assert result.state is ProviderProbeState.UNAVAILABLE
    assert result.quota is None
    assert secret_calls == [profile().credential_ref]
    assert len(transport.calls) == 1


def test_http_transport_never_follows_redirect_with_authorization() -> None:
    hits: list[tuple[str, str | None]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append((self.path, self.headers.get("Authorization")))
            if self.path == "/start":
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{self.server.server_port}/target")
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, format, *args):
            return
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, _payload = UrlLibJsonTransport().get_json(
            f"http://127.0.0.1:{server.server_port}/start",
            authorization="redirect-test-token",
            timeout_seconds=1.0,
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert status == 302
    assert hits == [("/start", "redirect-test-token")]


def test_zai_lookalike_anthropic_path_is_not_authorized_for_quota_probe() -> None:
    transport = FakeTransport(200, {})
    secret_calls: list[str] = []
    endpoint = ProviderEndpointConfig(
        profile().endpoint_ref,
        "https://api.z.ai/api/anthropic-evil",
    )

    result = probe_for(endpoint.base_url, transport, secret_calls).probe(profile(), endpoint)

    assert result.state is ProviderProbeState.UNAVAILABLE
    assert result.quota is None
    assert secret_calls == []
    assert transport.calls == []


def test_nonfinite_quota_numbers_fail_closed() -> None:
    payload = {"data": {"limits": [{
        "type": "CREDIT_LIMIT", "unit": 3, "number": 5,
        "usage": float("nan"), "currentValue": 1,
        "remaining": 1, "nextResetTime": 1788084000000,
    }]}}
    transport = FakeTransport(200, payload)
    endpoint = ProviderEndpointConfig(profile().endpoint_ref, "https://api.z.ai/api/anthropic")

    result = probe_for(endpoint.base_url, transport, []).probe(profile(), endpoint)

    assert result.state is ProviderProbeState.UNAVAILABLE
    assert result.quota is None


def test_zai_nondefault_tls_port_is_not_authorized_for_quota_secret() -> None:
    transport = FakeTransport(200, {})
    secret_calls: list[str] = []
    endpoint = ProviderEndpointConfig(
        profile().endpoint_ref,
        "https://api.z.ai:8443/api/anthropic",
    )

    result = probe_for(endpoint.base_url, transport, secret_calls).probe(profile(), endpoint)

    assert result.state is ProviderProbeState.UNAVAILABLE
    assert result.quota is None
    assert secret_calls == []
    assert transport.calls == []


def test_http_transport_rejects_oversized_response_body() -> None:
    body = b'{"data":"' + (b"x" * 512) + b'"}'

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, payload = UrlLibJsonTransport(max_response_bytes=128).get_json(
            f"http://127.0.0.1:{server.server_port}/quota",
            authorization="bounded-test-token",
            timeout_seconds=1.0,
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert status == 0
    assert payload == {}
