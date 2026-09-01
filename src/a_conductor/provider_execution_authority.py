"""Immutable provider-execution authority derived from exact task-contract bytes.

This leaf module owns no store, scheduler, runner, secret access, or lifecycle.
It binds canonical task security and provider generation to one non-secret digest.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .provider_config_store import ProviderConfigurationSnapshot
from .provider_configuration import is_provider_ready
from .provider_policy import (
    evaluate_provider_policy,
    ProviderPolicyTaskSecurity,
    TaskNetworkPolicy,
    TaskPrivacyClass,
)

_MAX_GENERATION = (1 << 63) - 1
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_FACTORY_TOKEN = object()

_TASK_REQUIRED = frozenset({
    "schema_version", "task_id", "goal", "risk_class", "authority", "target",
    "scope", "acceptance", "security", "budget", "retry_policy", "escalation",
    "required_evidence",
})
_TASK_ALLOWED = _TASK_REQUIRED | frozenset({"work_order_ref", "task_type", "routing", "metadata"})
_RISK_CLASSES = frozenset({"LOW", "NORMAL", "HIGH", "HUMAN_REQUIRED"})


def _task_contract_payload(authority_bytes: bytes) -> dict[str, object]:
    try:
        payload = json.loads(authority_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("task-contract authority is invalid") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0.0":
        raise ValueError("task-contract authority is invalid")
    if "security" not in payload:
        raise ValueError("task-contract security is incomplete")
    if not _TASK_REQUIRED.issubset(payload) or not set(payload).issubset(_TASK_ALLOWED):
        raise ValueError("task-contract authority is incomplete")
    if not isinstance(payload.get("task_id"), str) or not str(payload["task_id"]).strip():
        raise ValueError("task-contract task_id is invalid")
    if not isinstance(payload.get("goal"), str) or not str(payload["goal"]).strip():
        raise ValueError("task-contract goal is invalid")
    if payload.get("risk_class") not in _RISK_CLASSES:
        raise ValueError("task-contract risk_class is invalid")
    for field in ("authority", "target", "scope", "acceptance", "budget", "retry_policy", "escalation"):
        if not isinstance(payload.get(field), dict):
            raise ValueError(f"task-contract {field} is invalid")
    if not isinstance(payload.get("required_evidence"), list) or not payload["required_evidence"]:
        raise ValueError("task-contract required_evidence is invalid")
    return payload


def _provider_authority_ref(value: str | Path) -> str:
    path = Path(value).expanduser().resolve(strict=False)
    normalized = str(path).replace("\\", "/").casefold()
    return "provider-db:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _text(value: str, field: str, *, max_length: int) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ValueError(f"{field} is invalid")
    cleaned = value.strip()
    if len(cleaned) > max_length or any(ch in cleaned for ch in "\r\n"):
        raise ValueError(f"{field} is invalid")
    return cleaned


def _generation(value: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= _MAX_GENERATION
    ):
        raise ValueError("expected_configuration_generation must be positive")
    return value


def _security(payload: object) -> ProviderPolicyTaskSecurity:
    if not isinstance(payload, dict):
        raise ValueError("task-contract security is invalid")
    allowed = {"privacy_class", "network_policy", "network_allowlist", "secret_access"}
    if not set(payload).issubset(allowed):
        raise ValueError("task-contract security is invalid")
    if not {"privacy_class", "network_policy", "secret_access"}.issubset(payload):
        raise ValueError("task-contract security is incomplete")
    allowlist = payload.get("network_allowlist", ())
    if not isinstance(allowlist, list):
        raise ValueError("task-contract network_allowlist is invalid")
    try:
        return ProviderPolicyTaskSecurity(
            privacy_class=TaskPrivacyClass(payload["privacy_class"]),
            network_policy=TaskNetworkPolicy(payload["network_policy"]),
            network_allowlist=tuple(allowlist),
            secret_access=payload["secret_access"],
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("task-contract security is invalid") from exc


@dataclass(frozen=True, slots=True, init=False)
class ProviderExecutionRequirement:
    provider_id: str
    provider_authority_ref: str
    expected_configuration_generation: int
    task_contract_ref: str
    authority_sha256: str
    provider_security: ProviderPolicyTaskSecurity
    base_operation_ref: str
    requirement_sha256: str
    operation_ref: str

    def __init__(
        self,
        *,
        provider_id: str,
        provider_authority_ref: str,
        expected_configuration_generation: int,
        task_contract_ref: str,
        authority_sha256: str,
        provider_security: ProviderPolicyTaskSecurity,
        base_operation_ref: str,
        requirement_sha256: str,
        operation_ref: str,
        _token: object | None = None,
    ) -> None:
        if _token is not _FACTORY_TOKEN:
            raise ValueError("provider requirement must be derived from task-contract authority")
        for field, value in locals().copy().items():
            if field not in {"self", "_token"}:
                object.__setattr__(self, field, value)

    def matches_provider_authority_path(self, value: str | Path) -> bool:
        return self.provider_authority_ref == _provider_authority_ref(value)

    @classmethod
    def from_task_contract_file(
        cls, *, project_root: str | Path, provider_id: str, provider_authority_path: str | Path,
        expected_configuration_generation: int, task_contract_ref: str,
        base_operation_ref: str, expected_authority_sha256: str | None = None,
    ) -> "ProviderExecutionRequirement":
        root = Path(project_root).expanduser().resolve(strict=False)
        if not root.is_dir():
            raise ValueError("project_root must be an existing directory")
        ref = _text(task_contract_ref, "task_contract_ref", max_length=512)
        rel = Path(ref)
        if rel.is_absolute():
            raise ValueError("task_contract_ref must be project-relative")
        path = (root / rel).resolve(strict=False)
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError("task_contract_ref escapes project_root") from exc
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise ValueError("task-contract authority is unavailable") from exc
        actual = hashlib.sha256(raw).hexdigest()
        if expected_authority_sha256 is not None and (
            not isinstance(expected_authority_sha256, str)
            or not _SHA256_RE.fullmatch(expected_authority_sha256)
            or expected_authority_sha256.casefold() != actual
        ):
            raise ValueError("authority_sha256 mismatch")
        return cls._from_task_contract_bytes(
            provider_id=provider_id, provider_authority_ref=_provider_authority_ref(provider_authority_path), expected_configuration_generation=expected_configuration_generation,
            task_contract_ref=ref, authority_bytes=raw, authority_sha256=actual,
            base_operation_ref=base_operation_ref,
        )

    @classmethod
    def _from_task_contract_bytes(
        cls,
        *,
        provider_id: str,
        provider_authority_ref: str,
        expected_configuration_generation: int,
        task_contract_ref: str,
        authority_bytes: bytes,
        authority_sha256: str,
        base_operation_ref: str,
    ) -> "ProviderExecutionRequirement":
        provider_id = _text(provider_id, "provider_id", max_length=128)
        provider_authority_ref = _text(provider_authority_ref, "provider_authority_ref", max_length=128)
        task_contract_ref = _text(task_contract_ref, "task_contract_ref", max_length=512)
        base_operation_ref = _text(base_operation_ref, "base_operation_ref", max_length=128)
        generation = _generation(expected_configuration_generation)
        if not isinstance(authority_bytes, bytes) or not authority_bytes:
            raise ValueError("authority_bytes is invalid")
        if not isinstance(authority_sha256, str) or not _SHA256_RE.fullmatch(authority_sha256):
            raise ValueError("authority_sha256 is invalid")
        actual_sha = hashlib.sha256(authority_bytes).hexdigest()
        if actual_sha != authority_sha256.casefold():
            raise ValueError("authority_sha256 mismatch")
        payload = _task_contract_payload(authority_bytes)
        security = _security(payload.get("security"))
        canonical = {
            "authority_sha256": actual_sha,
            "base_operation_ref": base_operation_ref,
            "expected_configuration_generation": generation,
            "provider_authority_ref": provider_authority_ref,
            "provider_id": provider_id,
            "security": {
                "network_allowlist": list(security.network_allowlist),
                "network_policy": security.network_policy.value,
                "privacy_class": security.privacy_class.value,
                "secret_access": security.secret_access,
            },
            "task_contract_ref": task_contract_ref,
        }
        raw = json.dumps(
            canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
        requirement_sha = hashlib.sha256(raw).hexdigest()
        operation_ref = f"provider-op:{hashlib.sha256((base_operation_ref + chr(0) + requirement_sha).encode()).hexdigest()}"
        return cls(
            provider_id=provider_id,
            provider_authority_ref=provider_authority_ref,
            expected_configuration_generation=generation,
            task_contract_ref=task_contract_ref,
            authority_sha256=actual_sha,
            provider_security=security,
            base_operation_ref=base_operation_ref,
            requirement_sha256=requirement_sha,
            operation_ref=operation_ref,
            _token=_FACTORY_TOKEN,
        )


@dataclass(frozen=True, slots=True)
class ProviderExecutionAuthorization:
    allowed: bool
    gate_refused: bool
    provider_unavailable: bool
    rate_limited: bool
    reason_code: str
    snapshot: ProviderConfigurationSnapshot | None = None


class ProviderSnapshotAuthoritySource(Protocol):
    database_path: object

    def load_provider_snapshot(
        self, provider_id: str
    ) -> ProviderConfigurationSnapshot | None: ...


class ProviderExecutionAuthority:
    """Fresh single-snapshot authorization over one canonical provider store."""

    def __init__(self, source: ProviderSnapshotAuthoritySource) -> None:
        if not callable(getattr(source, "load_provider_snapshot", None)):
            raise ValueError("source must provide load_provider_snapshot")
        raw_path = getattr(source, "database_path", None)
        self._database_path = (
            None if raw_path is None else Path(raw_path).expanduser().resolve(strict=False)
        )
        self._source = source

    @property
    def database_path(self) -> Path | None:
        return self._database_path

    def authorize(
        self,
        requirement: ProviderExecutionRequirement,
        *,
        now: object,
        require_quota: bool = False,
    ) -> ProviderExecutionAuthorization:
        if not isinstance(requirement, ProviderExecutionRequirement):
            raise ValueError("requirement must be ProviderExecutionRequirement")
        if self._database_path is None or _provider_authority_ref(self._database_path) != requirement.provider_authority_ref:
            return ProviderExecutionAuthorization(False, False, True, False, "PROVIDER_AUTHORITY_STORE_MISMATCH")
        if not isinstance(require_quota, bool):
            raise ValueError("require_quota must be bool")
        try:
            snapshot = self._source.load_provider_snapshot(requirement.provider_id)
        except Exception:
            return ProviderExecutionAuthorization(
                False, False, True, False, "PROVIDER_AUTHORITY_SNAPSHOT_FAILED"
            )
        if not isinstance(snapshot, ProviderConfigurationSnapshot):
            return ProviderExecutionAuthorization(
                False, False, True, False, "PROVIDER_CONFIGURATION_UNAVAILABLE"
            )
        if snapshot.generation != requirement.expected_configuration_generation:
            return ProviderExecutionAuthorization(
                False, False, True, False, "PROVIDER_CONFIGURATION_STALE", snapshot
            )
        if snapshot.endpoint is None:
            return ProviderExecutionAuthorization(
                False, False, True, False, "PROVIDER_CONFIGURATION_UNAVAILABLE", snapshot
            )
        if snapshot.profile.provider_id != requirement.provider_id:
            return ProviderExecutionAuthorization(
                False, False, True, False, "PROVIDER_CONFIGURATION_DRIFT", snapshot
            )
        policy = evaluate_provider_policy(
            snapshot.profile, snapshot.endpoint, requirement.provider_security
        )
        if not policy.allowed:
            return ProviderExecutionAuthorization(
                False, True, False, False, policy.reason_code, snapshot
            )
        if not is_provider_ready(
            snapshot.profile,
            snapshot.observation,
            now=now,
            expected_generation=snapshot.generation,
        ):
            return ProviderExecutionAuthorization(
                False, False, True, False, "PROVIDER_NOT_READY", snapshot
            )
        if require_quota:
            quota = None if snapshot.observation is None else snapshot.observation.quota
            required = () if quota is None else (
                quota.limit, quota.used, quota.remaining, quota.reset_at, quota.reset_in_seconds
            )
            if quota is None or any(value is None for value in required):
                return ProviderExecutionAuthorization(
                    False, False, False, True, "PROVIDER_QUOTA_UNKNOWN", snapshot
                )
            if quota.remaining is not None and quota.remaining <= 0:
                return ProviderExecutionAuthorization(
                    False, False, False, True, "PROVIDER_QUOTA_EXHAUSTED", snapshot
                )
        return ProviderExecutionAuthorization(
            True, False, False, False, "PROVIDER_AUTHORITY_ALLOWED", snapshot
        )
