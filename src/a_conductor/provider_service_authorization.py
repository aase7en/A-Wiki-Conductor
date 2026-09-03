"""Pure provider service-authorization gate.

This module owns only SERVICE_AUTHORIZED. It performs no I/O and does not
change provider readiness, task policy, admission, quota, or execution state.
External authorization evidence is represented only by a SHA-256 digest.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import re

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_TERMS_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@-]{1,255}$")


class ServiceAuthorizationState(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    BLOCKED_EXTERNAL = "BLOCKED_EXTERNAL"
    UNKNOWN = "UNKNOWN"


class ServiceIntegrationMode(str, Enum):
    FAKE = "FAKE"
    READ_ONLY = "READ_ONLY"
    LIVE = "LIVE"


def _text(value: object, field: str, *, max_length: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    text = value.strip()
    if not text or len(text) > max_length or _CONTROL_RE.search(text):
        raise ValueError(f"{field} is invalid")
    return text


def _terms_identity(value: object) -> str:
    text = _text(value, "terms_identity", max_length=256)
    if not _TERMS_ID_RE.fullmatch(text):
        raise ValueError("terms_identity is invalid")
    return text


def _generation(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("configuration_generation must be a positive integer")
    return value


def _aware_utc(value: object, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"{field} must be timezone-aware")
    offset = value.utcoffset()
    if offset is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class ProviderServiceAuthorizationRecord:
    provider_id: str
    state: ServiceAuthorizationState
    integration_mode: ServiceIntegrationMode
    terms_identity: str
    evidence_sha256: str | None
    observed_at: datetime
    recheck_after: datetime
    configuration_generation: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_id", _text(self.provider_id, "provider_id", max_length=128))
        if not isinstance(self.state, ServiceAuthorizationState):
            raise ValueError("state must be ServiceAuthorizationState")
        if not isinstance(self.integration_mode, ServiceIntegrationMode):
            raise ValueError("integration_mode must be ServiceIntegrationMode")
        object.__setattr__(self, "terms_identity", _terms_identity(self.terms_identity))
        evidence = self.evidence_sha256
        if evidence is not None:
            if not isinstance(evidence, str) or not _SHA256_RE.fullmatch(evidence):
                raise ValueError("evidence_sha256 must be a SHA-256 hex digest or None")
            evidence = evidence.casefold()
        if self.state is ServiceAuthorizationState.AUTHORIZED and evidence is None:
            raise ValueError("evidence_sha256 is required for AUTHORIZED state")
        object.__setattr__(self, "evidence_sha256", evidence)

        observed = _aware_utc(self.observed_at, "observed_at")
        recheck = _aware_utc(self.recheck_after, "recheck_after")
        if recheck <= observed:
            raise ValueError("recheck_after must be later than observed_at")
        object.__setattr__(self, "observed_at", observed)
        object.__setattr__(self, "recheck_after", recheck)
        object.__setattr__(
            self, "configuration_generation", _generation(self.configuration_generation)
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "provider_id": self.provider_id,
            "state": self.state.value,
            "integration_mode": self.integration_mode.value,
            "terms_identity": self.terms_identity,
            "evidence_sha256": self.evidence_sha256,
            "observed_at": self.observed_at.isoformat(),
            "recheck_after": self.recheck_after.isoformat(),
            "configuration_generation": self.configuration_generation,
        }


@dataclass(frozen=True, slots=True)
class ProviderServiceAuthorizationDecision:
    allowed: bool
    reason_code: str
    state: ServiceAuthorizationState | None
    requested_mode: ServiceIntegrationMode

    def __post_init__(self) -> None:
        if not isinstance(self.allowed, bool):
            raise ValueError("allowed must be bool")
        object.__setattr__(self, "reason_code", _text(self.reason_code, "reason_code", max_length=128))
        if self.state is not None and not isinstance(self.state, ServiceAuthorizationState):
            raise ValueError("state must be ServiceAuthorizationState or None")
        if not isinstance(self.requested_mode, ServiceIntegrationMode):
            raise ValueError("requested_mode must be ServiceIntegrationMode")

    def to_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "reason_code": self.reason_code,
            "state": None if self.state is None else self.state.value,
            "requested_mode": self.requested_mode.value,
        }


def _decision(
    allowed: bool,
    reason_code: str,
    state: ServiceAuthorizationState | None,
    mode: ServiceIntegrationMode,
) -> ProviderServiceAuthorizationDecision:
    return ProviderServiceAuthorizationDecision(allowed, reason_code, state, mode)


def evaluate_provider_service_authorization(
    record: ProviderServiceAuthorizationRecord | None,
    *,
    provider_id: str,
    requested_mode: ServiceIntegrationMode,
    terms_identity: str,
    expected_configuration_generation: int,
    now: datetime,
) -> ProviderServiceAuthorizationDecision:
    """Evaluate service permission only; never infer readiness or task authority."""
    provider = _text(provider_id, "provider_id", max_length=128)
    terms = _terms_identity(terms_identity)
    generation = _generation(expected_configuration_generation)
    current = _aware_utc(now, "now")
    if not isinstance(requested_mode, ServiceIntegrationMode):
        raise ValueError("requested_mode must be ServiceIntegrationMode")

    if requested_mode is ServiceIntegrationMode.FAKE:
        return _decision(
            True, "SERVICE_AUTHORIZATION_NOT_REQUIRED_FAKE", None, requested_mode
        )
    if record is None:
        return _decision(False, "SERVICE_AUTHORIZATION_REQUIRED", None, requested_mode)
    if not isinstance(record, ProviderServiceAuthorizationRecord):
        raise ValueError("record must be ProviderServiceAuthorizationRecord or None")
    if record.provider_id != provider:
        return _decision(
            False, "SERVICE_AUTHORIZATION_PROVIDER_MISMATCH", record.state, requested_mode
        )
    if record.integration_mode is not requested_mode:
        return _decision(
            False, "SERVICE_AUTHORIZATION_MODE_MISMATCH", record.state, requested_mode
        )
    if record.terms_identity != terms:
        return _decision(
            False, "SERVICE_AUTHORIZATION_TERMS_STALE", record.state, requested_mode
        )
    if record.configuration_generation != generation:
        return _decision(
            False, "SERVICE_AUTHORIZATION_GENERATION_STALE", record.state, requested_mode
        )
    if current < record.observed_at or current >= record.recheck_after:
        return _decision(
            False, "SERVICE_AUTHORIZATION_EVIDENCE_STALE", record.state, requested_mode
        )
    if record.state is ServiceAuthorizationState.UNKNOWN:
        return _decision(
            False, "SERVICE_AUTHORIZATION_UNKNOWN", record.state, requested_mode
        )
    if record.state is ServiceAuthorizationState.BLOCKED_EXTERNAL:
        return _decision(
            False, "SERVICE_AUTHORIZATION_BLOCKED_EXTERNAL", record.state, requested_mode
        )
    if record.state is not ServiceAuthorizationState.AUTHORIZED:
        return _decision(
            False, "SERVICE_AUTHORIZATION_UNKNOWN", record.state, requested_mode
        )
    return _decision(
        True, "SERVICE_AUTHORIZATION_ALLOWED", record.state, requested_mode
    )
