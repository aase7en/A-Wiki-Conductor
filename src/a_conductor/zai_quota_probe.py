"""Provider-matched Z.ai five-hour quota probe.

The probe is inert for non-Z.ai endpoints. Credentials are resolved only after
an explicit supported HTTPS route is proven and are passed only to the bounded
HTTP transport boundary.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Callable, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .provider_configuration import (
    ProviderConfiguration,
    ProviderEndpointConfig,
    ProviderProbeResult,
    ProviderProbeState,
    QuotaSnapshot,
)

_SUPPORTED_HOSTS = frozenset({"api.z.ai", "open.bigmodel.cn", "dev.bigmodel.cn"})
_QUOTA_PATH = "/api/monitor/usage/quota/limit"


class ZaiQuotaTransport(Protocol):
    def get_json(
        self,
        url: str,
        *,
        authorization: str,
        timeout_seconds: float,
    ) -> tuple[int, object]: ...


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class UrlLibJsonTransport:
    """Small bounded HTTPS JSON GET transport with no credential logging."""

    def __init__(self, *, max_response_bytes: int = 1_048_576) -> None:
        if isinstance(max_response_bytes, bool) or not isinstance(max_response_bytes, int):
            raise ValueError("max_response_bytes must be a positive integer")
        if max_response_bytes < 1:
            raise ValueError("max_response_bytes must be a positive integer")
        self._max_response_bytes = max_response_bytes

    def get_json(
        self,
        url: str,
        *,
        authorization: str,
        timeout_seconds: float,
    ) -> tuple[int, object]:
        request = Request(
            url,
            method="GET",
            headers={
                "Authorization": authorization,
                "Accept-Language": "en-US,en",
                "Content-Type": "application/json",
            },
        )
        try:
            opener = build_opener(_NoRedirectHandler())
            with opener.open(request, timeout=timeout_seconds) as response:
                status = int(response.getcode())
                raw = response.read(self._max_response_bytes + 1)
        except HTTPError as exc:
            status = int(exc.code)
            raw = exc.read(self._max_response_bytes + 1)
        except URLError:
            return 0, {}
        if len(raw) > self._max_response_bytes:
            return 0, {}
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeError, json.JSONDecodeError):
            payload = {}
        return status, payload


def _supported_origin(endpoint: ProviderEndpointConfig) -> str | None:
    parsed = urlsplit(endpoint.base_url)
    host = (parsed.hostname or "").casefold()
    if parsed.scheme.casefold() != "https" or host not in _SUPPORTED_HOSTS:
        return None
    if parsed.port not in {None, 443}:
        return None
    path = parsed.path.rstrip("/")
    if path != "/api/anthropic" and not path.startswith("/api/anthropic/"):
        return None
    port = f":{parsed.port}" if parsed.port is not None else ""
    return f"https://{host}{port}"


def supports_zai_quota_endpoint(endpoint: ProviderEndpointConfig) -> bool:
    return isinstance(endpoint, ProviderEndpointConfig) and _supported_origin(endpoint) is not None


def _number(value: object) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return value


def _five_hour_item(payload: object) -> Mapping[str, object] | None:
    if not isinstance(payload, Mapping):
        return None
    data = payload.get("data", payload)
    if not isinstance(data, Mapping):
        return None
    limits = data.get("limits")
    if not isinstance(limits, list):
        return None
    for item in limits:
        if not isinstance(item, Mapping):
            continue
        limit_type = item.get("type")
        unit = item.get("unit")
        number = item.get("number")
        if limit_type == "TOKENS_LIMIT":
            if (unit is None and number is None) or (unit == 3 and number == 5):
                return item
        if limit_type == "CREDIT_LIMIT" and unit == 3 and number == 5:
            return item
    return None


def _quota_from_payload(payload: object, *, now: datetime) -> QuotaSnapshot | None:
    item = _five_hour_item(payload)
    if item is None:
        return None
    limit = _number(item.get("usage"))
    used = _number(item.get("currentValue"))
    remaining = _number(item.get("remaining"))
    reset_raw = _number(item.get("nextResetTime"))
    if None in (limit, used, remaining, reset_raw):
        return None
    reset_seconds = float(reset_raw)
    if reset_seconds > 1_000_000_000_000:
        reset_seconds /= 1000
    try:
        reset_at = datetime.fromtimestamp(reset_seconds, tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None
    current = now.astimezone(timezone.utc)
    reset_in_seconds = max(0, int((reset_at - current).total_seconds()))
    unit = "credits" if item.get("type") == "CREDIT_LIMIT" else "tokens"
    return QuotaSnapshot(
        window_type="5h",
        limit=limit,
        used=used,
        remaining=remaining,
        reset_at=reset_at,
        reset_in_seconds=reset_in_seconds,
        unit=unit,
    )


class ZaiQuotaProbe:
    """Probe an explicit Z.ai Anthropic-compatible route for five-hour quota."""

    def __init__(
        self,
        *,
        resolve_credential: Callable[[str], str],
        transport: ZaiQuotaTransport | None = None,
        clock: Callable[[], datetime],
        timeout_seconds: float = 5.0,
    ) -> None:
        if not callable(resolve_credential):
            raise ValueError("resolve_credential must be callable")
        if not callable(clock):
            raise ValueError("clock must be callable")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._resolve_credential = resolve_credential
        self._transport = transport or UrlLibJsonTransport()
        self._clock = clock
        self._timeout_seconds = float(timeout_seconds)

    def probe(
        self,
        profile: ProviderConfiguration,
        endpoint: ProviderEndpointConfig,
    ) -> ProviderProbeResult:
        if not isinstance(profile, ProviderConfiguration) or not isinstance(endpoint, ProviderEndpointConfig):
            raise ValueError("profile and endpoint must use provider configuration contracts")
        if endpoint.endpoint_ref != profile.endpoint_ref:
            return ProviderProbeResult(ProviderProbeState.UNAVAILABLE)
        origin = _supported_origin(endpoint)
        if origin is None:
            return ProviderProbeResult(ProviderProbeState.UNAVAILABLE)
        try:
            credential = self._resolve_credential(profile.credential_ref)
        except Exception:
            return ProviderProbeResult(ProviderProbeState.AUTH_FAILED)
        if not isinstance(credential, str) or not credential:
            return ProviderProbeResult(ProviderProbeState.AUTH_FAILED)
        try:
            status, payload = self._transport.get_json(
                origin + _QUOTA_PATH,
                authorization=credential,
                timeout_seconds=self._timeout_seconds,
            )
        except Exception:
            return ProviderProbeResult(ProviderProbeState.UNAVAILABLE)
        if status in {401, 403}:
            return ProviderProbeResult(ProviderProbeState.AUTH_FAILED)
        if status == 429:
            return ProviderProbeResult(ProviderProbeState.RATE_LIMITED)
        if status != 200:
            return ProviderProbeResult(ProviderProbeState.UNAVAILABLE)
        now = self._clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            return ProviderProbeResult(ProviderProbeState.UNAVAILABLE)
        quota = _quota_from_payload(payload, now=now)
        if quota is None:
            return ProviderProbeResult(ProviderProbeState.UNAVAILABLE)
        state = (
            ProviderProbeState.QUOTA_EXHAUSTED
            if quota.remaining is not None and quota.remaining <= 0
            else ProviderProbeState.OK
        )
        return ProviderProbeResult(state, quota=quota)
