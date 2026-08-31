"""Pure provider trust/egress policy over task-contract security vocabulary.

This module is side-effect free: it resolves no credentials, launches no
processes, allocates no workers, mutates no provider state, and infers no
authorization from health or quota evidence. It consumes exactly the
``task-contract/v1`` security vocabulary (``privacy_class``, ``network_policy``,
``network_allowlist``, ``secret_access``) plus provider trust/egress metadata,
and returns one typed allow/deny decision. Unknown or missing policy evidence
always fails closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlsplit

from .provider_configuration import (
    EgressBoundary,
    ProviderConfiguration,
    ProviderEndpointConfig,
    ProviderTrustClass,
)


class TaskPrivacyClass(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    SENSITIVE = "SENSITIVE"
    SECRET = "SECRET"


class TaskNetworkPolicy(str, Enum):
    DENIED = "DENIED"
    ALLOWLISTED = "ALLOWLISTED"
    INHERIT = "INHERIT"


@dataclass(frozen=True, slots=True)
class ProviderPolicyTaskSecurity:
    """Typed task security inputs from the task-contract/v1 vocabulary."""

    privacy_class: TaskPrivacyClass
    network_policy: TaskNetworkPolicy
    network_allowlist: tuple[str, ...] = ()
    secret_access: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.privacy_class, TaskPrivacyClass):
            raise ValueError("privacy_class is invalid")
        if not isinstance(self.network_policy, TaskNetworkPolicy):
            raise ValueError("network_policy is invalid")
        if isinstance(self.network_allowlist, (str, bytes)):
            raise ValueError("network_allowlist must be a sequence of hosts")
        allowlist = tuple(
            item.strip().casefold().rstrip(".")
            for item in self.network_allowlist
            if isinstance(item, str) and item.strip()
        )
        if len(allowlist) != len(tuple(self.network_allowlist)):
            raise ValueError("network_allowlist entries must be non-blank strings")
        if not isinstance(self.secret_access, bool):
            raise ValueError("secret_access must be bool")
        object.__setattr__(self, "network_allowlist", allowlist)


@dataclass(frozen=True, slots=True)
class ProviderPolicyDecision:
    allowed: bool
    reason_code: str


_ALLOWED_LOCAL = ProviderPolicyDecision(True, "POLICY_ALLOWED_LOCAL_EGRESS")
_ALLOWED_EXTERNAL = ProviderPolicyDecision(True, "POLICY_ALLOWED_EXTERNAL_EGRESS")


def _deny(reason_code: str) -> ProviderPolicyDecision:
    return ProviderPolicyDecision(False, reason_code)


def _endpoint_host(endpoint: ProviderEndpointConfig | None) -> str | None:
    if endpoint is None:
        return None
    parsed = urlsplit(endpoint.base_url)
    host = parsed.hostname
    if host is None:
        return None
    return host.casefold().rstrip(".")


def evaluate_provider_policy(
    profile: ProviderConfiguration,
    endpoint: ProviderEndpointConfig | None,
    task: ProviderPolicyTaskSecurity,
) -> ProviderPolicyDecision:
    """Evaluate one fail-closed trust/egress decision. Pure; no I/O."""
    if not isinstance(profile, ProviderConfiguration):
        raise ValueError("profile must be ProviderConfiguration")
    if endpoint is not None and not isinstance(endpoint, ProviderEndpointConfig):
        raise ValueError("endpoint must be ProviderEndpointConfig or None")
    if not isinstance(task, ProviderPolicyTaskSecurity):
        raise ValueError("task must be ProviderPolicyTaskSecurity")

    if profile.trust_class is ProviderTrustClass.UNKNOWN:
        return _deny("PROVIDER_TRUST_UNKNOWN")
    if profile.egress_boundary is EgressBoundary.UNKNOWN:
        return _deny("PROVIDER_EGRESS_UNKNOWN")
    if task.network_policy is TaskNetworkPolicy.INHERIT:
        return _deny("TASK_NETWORK_POLICY_UNRESOLVED")

    boundary = profile.egress_boundary
    if boundary in (EgressBoundary.LOCAL_MACHINE, EgressBoundary.NO_EGRESS):
        # Local/no-egress paths stay subject to known trust metadata above but
        # never require an external host allowlist.
        return _ALLOWED_LOCAL

    host = _endpoint_host(endpoint)
    allowlisted = host is not None and host in task.network_allowlist

    if task.network_policy is TaskNetworkPolicy.DENIED:
        return _deny("TASK_NETWORK_DENIED")
    if task.privacy_class is TaskPrivacyClass.SECRET or task.secret_access:
        return _deny("SECRET_TASK_EXTERNAL_DENIED")
    if task.privacy_class is TaskPrivacyClass.SENSITIVE:
        if boundary is EgressBoundary.EXTERNAL_THIRD_PARTY:
            return _deny("SENSITIVE_THIRD_PARTY_EXTERNAL_DENIED")
        if not allowlisted:
            return _deny("SENSITIVE_FIRST_PARTY_ALLOWLIST_REQUIRED")
    elif task.privacy_class is TaskPrivacyClass.INTERNAL:
        if boundary is EgressBoundary.EXTERNAL_THIRD_PARTY and not allowlisted:
            return _deny("INTERNAL_THIRD_PARTY_ALLOWLIST_REQUIRED")
    if task.network_policy is TaskNetworkPolicy.ALLOWLISTED and not allowlisted:
        return _deny("ENDPOINT_NOT_ALLOWLISTED")
    return _ALLOWED_EXTERNAL
