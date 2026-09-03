"""Pure AIP-2 decoder for fake/read-only AiPASS discovery facts.

This module performs no transport, browser, credential, persistence, readiness,
authorization, admission, or execution work. Callers supply already-observed
payloads; the result is an ephemeral, generation-bound projection only.
"""

from __future__ import annotations

import math
import re
from ipaddress import ip_address
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping

from .provider_configuration import QuotaSnapshot


_MODEL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@+\-]{0,127}$")
_RAW_ENDPOINT_HOST_RE = re.compile(
    r"^(?:localhost|(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,62}[A-Za-z0-9])?\.)+"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,62}[A-Za-z0-9])?)\.?$",
    re.IGNORECASE,
)
_MODEL_KINDS = frozenset({"chat", "image", "video", "music", "research"})
_MAX_JSON_SAFE_NUMBER = (1 << 53) - 1
_FACTORY_TOKEN = object()
_PUBLIC_METADATA_FORBIDDEN_RE = re.compile(
    r"(?i)(?:https?://|wss?://|\bauthorization\s*[:=]|\bcookie\s*[:=]|"
    r"\b(?:api[_ -]?key|access[_ -]?key(?:[_ -]?id)?|access[_ -]?token|refresh[_ -]?token|password|passphrase|"
    r"client[_ -]?secret|private[_ -]?key|session(?:[_ -]?id)?|token|secret|credential|auth)\s*[:=]|"
    r"\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)*_(?:api_key|token|password|passwd|secret|client_secret|private_key|access_key(?:_id)?|session_token)\s*[:=]|"
    r"\bbasic\s+(?=[A-Za-z0-9+/=]{20,})(?=[A-Za-z0-9+/]*[0-9+/=])[A-Za-z0-9+/]+={0,2}\b|"
    r"-----BEGIN (?:(?:RSA|EC|OPENSSH|ENCRYPTED) )?PRIVATE KEY-----|"
    r"\bssh-(?:rsa|ed25519)\s+(?=[A-Za-z0-9+/=]{20,})(?=[A-Za-z0-9+/]*[0-9+/=])[A-Za-z0-9+/]+={0,2}|"
    r"\b(?:localhost|(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}):\d{1,5}\b|"
    r"\b(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}/[^\s/]+|\b(?:\d{1,3}\.){3}\d{1,3}:\d{1,5}\b|"
    r"\b(?:10(?:\.\d{1,3}){3}|127(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b|"
    r"\[[0-9A-Fa-f:]+\]:\d{1,5}\b|^/|"
    r"(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|\\\\|/(?!\s)(?:[^/\s]+/)+[^/\s]+))"
)
_CREDENTIAL_SHAPED_RE = re.compile(
    r"(?i)(?:^|[\s._/@:+-])(?:bearer\s+[A-Za-z0-9._~+/=-]{16,}|gh[pousr]_|"
    r"github_pat_[A-Za-z0-9_]{16,}|sk-ant-|sk-(?:proj-|live-)?[A-Za-z0-9_]{16,}|"
    r"(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}|glpat-[A-Za-z0-9_-]{16,}|"
    r"npm_[A-Za-z0-9]{16,}|pypi-[A-Za-z0-9_-]{16,}|akia[0-9a-z]|asia[0-9a-z]{16}|"
    r"aiza[0-9a-z]|ya29\.|eyj[0-9a-z]|xox[baprs]-)"
)


class AiPassDiscoveryState(str, Enum):
    OK = "OK"
    EMPTY = "EMPTY"
    UNAVAILABLE = "UNAVAILABLE"
    STALE = "STALE"
    MALFORMED = "MALFORMED"
    UNSUPPORTED = "UNSUPPORTED"

@dataclass(frozen=True, slots=True, init=False)
class AiPassDiscoveredModel:
    model_id: str
    name: str
    free_credit: bool | None
    kind: str | None
    is_default: bool | None

    def __init__(
        self, model_id: str, name: str, free_credit: bool | None,
        kind: str | None, is_default: bool | None, *, _token: object | None = None,
    ) -> None:
        if _token is not _FACTORY_TOKEN:
            raise ValueError("discovery model must be factory-created")
        for field, value in locals().copy().items():
            if field not in {"self", "_token"}:
                object.__setattr__(self, field, value)

    def to_dict(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "free_credit": self.free_credit,
            "kind": self.kind,
            "is_default": self.is_default,
        }


@dataclass(frozen=True, slots=True, init=False)
class AiPassDiscoverySnapshot:
    state: AiPassDiscoveryState
    reason_code: str
    models: tuple[AiPassDiscoveredModel, ...] = ()
    shared_quota: QuotaSnapshot | None = None
    video_quota: QuotaSnapshot | None = None
    configuration_generation: int | None = None
    observed_at: datetime | None = None
    quota_fetched_at: datetime | None = None

    def __init__(
        self, state: AiPassDiscoveryState, reason_code: str,
        models: tuple[AiPassDiscoveredModel, ...] = (),
        shared_quota: QuotaSnapshot | None = None,
        video_quota: QuotaSnapshot | None = None,
        configuration_generation: int | None = None,
        observed_at: datetime | None = None,
        quota_fetched_at: datetime | None = None, *, _token: object | None = None,
    ) -> None:
        if _token is not _FACTORY_TOKEN:
            raise ValueError("discovery snapshot must be factory-created")
        for field, value in locals().copy().items():
            if field not in {"self", "_token"}:
                object.__setattr__(self, field, value)

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "reason_code": self.reason_code,
            "models": [item.to_dict() for item in self.models],
            "shared_quota": None if self.shared_quota is None else self.shared_quota.as_dict(),
            "video_quota": None if self.video_quota is None else self.video_quota.as_dict(),
            "configuration_generation": self.configuration_generation,
            "observed_at": None if self.observed_at is None else _time_text(self.observed_at),
            "quota_fetched_at": (
                None if self.quota_fetched_at is None else _time_text(self.quota_fetched_at)
            ),
        }


def _time(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("time must be timezone-aware")
    return value.astimezone(timezone.utc)


def _time_text(value: datetime) -> str:
    return _time(value).isoformat().replace("+00:00", "Z")


def _safe_text(value: object, *, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError("text is invalid")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("text is invalid")
    return value


def _looks_like_raw_endpoint(value: str) -> bool:
    text = value.strip()
    if _RAW_ENDPOINT_HOST_RE.fullmatch(text):
        return True
    candidate = text[1:-1] if text.startswith("[") and text.endswith("]") else text
    try:
        ip_address(candidate)
    except ValueError:
        return False
    return True


def _display_name(value: object, *, fallback: str) -> str:
    try:
        text = _safe_text(value, maximum=128)
    except ValueError:
        return fallback
    if (
        _PUBLIC_METADATA_FORBIDDEN_RE.search(text)
        or _CREDENTIAL_SHAPED_RE.search(text)
        or _looks_like_raw_endpoint(text)
    ):
        return fallback
    return text

def _number(value: object) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("number is invalid")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("number is invalid")
    if value < 0 or value > _MAX_JSON_SAFE_NUMBER:
        raise ValueError("number is outside the bounded JSON numeric domain")
    return value


def _epoch_millis(value: object) -> datetime:
    number = _number(value)
    try:
        return datetime.fromtimestamp(number / 1000, tz=timezone.utc)
    except (OSError, OverflowError, ValueError) as exc:
        raise ValueError("epoch milliseconds are invalid") from exc


def _reset_at(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("reset time is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("reset time is invalid") from exc
    return _time(parsed)


def _consistent(limit: int | float, used: int | float, remaining: int | float) -> bool:
    return math.isclose(limit, used + remaining, rel_tol=1e-9, abs_tol=1e-6)


def _decode_models(payload: object) -> tuple[AiPassDiscoveredModel, ...]:
    if not isinstance(payload, Mapping):
        raise ValueError("model payload is malformed")
    if payload.get("object") != "list":
        raise NotImplementedError("model payload is unsupported")
    data = payload.get("data")
    if not isinstance(data, list):
        raise ValueError("model payload is malformed")
    models: list[AiPassDiscoveredModel] = []
    seen: set[str] = set()
    for raw in data:
        if not isinstance(raw, Mapping):
            raise ValueError("model record is malformed")
        model_id = raw.get("id")
        if (
            not isinstance(model_id, str)
            or not _MODEL_ID_RE.fullmatch(model_id)
            or _CREDENTIAL_SHAPED_RE.search(model_id)
        ):
            raise ValueError("model id is invalid")
        if model_id in seen:
            raise ValueError("model id is duplicated")
        seen.add(model_id)
        name = _display_name(raw.get("name", model_id), fallback=model_id)
        free_credit = raw.get("free_credit")
        if free_credit is not None and not isinstance(free_credit, bool):
            raise ValueError("free_credit is invalid")
        kind = raw.get("kind")
        if kind is not None:
            kind = kind if isinstance(kind, str) and kind in _MODEL_KINDS else None
        is_default = raw.get("is_default")
        if is_default is not None and not isinstance(is_default, bool):
            raise ValueError("is_default is invalid")
        models.append(AiPassDiscoveredModel(model_id, name, free_credit, kind, is_default, _token=_FACTORY_TOKEN))
    return tuple(sorted(models, key=lambda item: item.model_id))


def _quota_triplet(raw: Mapping[str, object], *, remaining_key: str) -> tuple[int | float, int | float, int | float]:
    limit = _number(raw["limit"])
    used = _number(raw["used"])
    remaining = _number(raw[remaining_key])
    if not _consistent(limit, used, remaining):
        raise ValueError("quota tuple is contradictory")
    return limit, used, remaining

def _decode_quota(
    payload: object,
) -> tuple[QuotaSnapshot | None, QuotaSnapshot | None, datetime | None]:
    if payload is None or payload == {}:
        return None, None, None
    if not isinstance(payload, Mapping):
        raise ValueError("quota payload is malformed")

    fetched_at = _epoch_millis(payload["fetchedAt"]) if payload else None
    if payload and fetched_at is None:
        raise ValueError("quota fetched time is unavailable")

    shared: QuotaSnapshot | None = None
    shared_keys = {"limit", "used", "available"}
    if shared_keys & set(payload):
        if not shared_keys.issubset(payload):
            raise ValueError("shared quota is incomplete")
        limit, used, remaining = _quota_triplet(payload, remaining_key="available")
        shared = QuotaSnapshot(
            window_type="aipass_shared_credits",
            limit=limit,
            used=used,
            remaining=remaining,
            reset_at=_reset_at(payload.get("periodEndsAt")),
            unit="credits",
        )

    video: QuotaSnapshot | None = None
    raw_video = payload.get("video")
    if raw_video is not None:
        if not isinstance(raw_video, Mapping):
            raise ValueError("video quota is malformed")
        if not {"limit", "used", "remaining"}.issubset(raw_video):
            raise ValueError("video quota is incomplete")
        limit, used, remaining = _quota_triplet(raw_video, remaining_key="remaining")
        video = QuotaSnapshot(
            window_type="aipass_video",
            limit=limit,
            used=used,
            remaining=remaining,
            unit="generations",
        )
    return shared, video, fetched_at

def _context(
    *,
    observed_at: datetime,
    now: datetime,
    configuration_generation: int,
    stale_after_seconds: int | float,
) -> tuple[datetime, datetime, float]:
    if (
        isinstance(configuration_generation, bool)
        or not isinstance(configuration_generation, int)
        or configuration_generation < 1
    ):
        raise ValueError("configuration generation is invalid")
    if (
        isinstance(stale_after_seconds, bool)
        or not isinstance(stale_after_seconds, (int, float))
        or not math.isfinite(stale_after_seconds)
        or stale_after_seconds < 0
    ):
        raise ValueError("stale budget is invalid")
    observed = _time(observed_at)
    current = _time(now)
    age = (current - observed).total_seconds()
    if age < 0:
        raise ValueError("observation is from the future")
    return observed, current, age


def _empty_result(state: AiPassDiscoveryState, reason: str) -> AiPassDiscoverySnapshot:
    return AiPassDiscoverySnapshot(state=state, reason_code=reason, _token=_FACTORY_TOKEN)

def build_aipass_discovery(
    *,
    models_payload: object,
    quota_payload: object,
    observed_at: datetime,
    now: datetime,
    configuration_generation: int,
    stale_after_seconds: int | float = 300,
) -> AiPassDiscoverySnapshot:
    """Decode supplied fake/read-only discovery payloads without performing I/O."""
    try:
        observed, _current, age = _context(
            observed_at=observed_at,
            now=now,
            configuration_generation=configuration_generation,
            stale_after_seconds=stale_after_seconds,
        )
    except (TypeError, ValueError):
        return _empty_result(AiPassDiscoveryState.MALFORMED, "DISCOVERY_CONTEXT_INVALID")

    if models_payload is None:
        return _empty_result(AiPassDiscoveryState.UNAVAILABLE, "DISCOVERY_UNAVAILABLE")

    try:
        models = _decode_models(models_payload)
    except NotImplementedError:
        return _empty_result(AiPassDiscoveryState.UNSUPPORTED, "MODEL_PAYLOAD_UNSUPPORTED")
    except (TypeError, ValueError):
        return _empty_result(AiPassDiscoveryState.MALFORMED, "MODEL_PAYLOAD_MALFORMED")

    try:
        shared_quota, video_quota, quota_fetched_at = _decode_quota(quota_payload)
        if quota_fetched_at is not None and quota_fetched_at > observed:
            raise ValueError("quota fetched time is after observation")
    except (KeyError, TypeError, ValueError):
        return _empty_result(AiPassDiscoveryState.MALFORMED, "QUOTA_PAYLOAD_MALFORMED")
    source_age = age
    if quota_fetched_at is not None:
        source_age = max(source_age, (_current - quota_fetched_at).total_seconds())
    if source_age > stale_after_seconds:
        state = AiPassDiscoveryState.STALE
        reason = "DISCOVERY_STALE"
    elif not models:
        state = AiPassDiscoveryState.EMPTY
        reason = "DISCOVERY_EMPTY"
    else:
        state = AiPassDiscoveryState.OK
        reason = "DISCOVERY_OK"

    return AiPassDiscoverySnapshot(
        state=state,
        reason_code=reason,
        models=models,
        shared_quota=shared_quota,
        video_quota=video_quota,
        configuration_generation=configuration_generation,
        observed_at=observed,
        quota_fetched_at=quota_fetched_at,
        _token=_FACTORY_TOKEN,
    )
