from __future__ import annotations

import json
from pathlib import Path

import pytest

from a_conductor.provider_configuration import (
    EgressBoundary,
    ProviderConfiguration,
    ProviderEndpointConfig,
    ProviderTrustClass,
)
from a_conductor.provider_policy import (
    ProviderPolicyDecision,
    ProviderPolicyTaskSecurity,
    TaskNetworkPolicy,
    TaskPrivacyClass,
    evaluate_provider_policy,
)


ENDPOINT = ProviderEndpointConfig("endpoint:glm", "https://api.provider.example/v1")


def profile(
    *,
    trust_class=ProviderTrustClass.TRUSTED_THIRD_PARTY,
    egress_boundary=EgressBoundary.EXTERNAL_THIRD_PARTY,
) -> ProviderConfiguration:
    return ProviderConfiguration(
        provider_id="glm-policy",
        display_name="GLM",
        provider_type="proxy",
        protocol_family="ANTHROPIC_MESSAGES",
        endpoint_ref=ENDPOINT.endpoint_ref,
        credential_ref="secret-ref:glm/token",
        trust_class=trust_class,
        egress_boundary=egress_boundary,
        harness_strategies=("CLAUDE_CODE_CLI",),
        max_concurrency=2,
        models=({"model_id": "glm-5.3", "display_name": "GLM 5.3"},),
        enabled=True,
    )


def task(
    *,
    privacy=TaskPrivacyClass.PUBLIC,
    policy=TaskNetworkPolicy.ALLOWLISTED,
    allowlist=("api.provider.example",),
    secret_access=False,
) -> ProviderPolicyTaskSecurity:
    return ProviderPolicyTaskSecurity(
        privacy_class=privacy,
        network_policy=policy,
        network_allowlist=allowlist,
        secret_access=secret_access,
    )


def test_schema_enum_values_stay_aligned_with_task_contract() -> None:
    schema = json.loads(
        Path("schemas/task-contract.schema.json").read_text(encoding="utf-8")
    )
    security = schema["properties"]["security"]["properties"]
    assert set(security["privacy_class"]["enum"]) == {
        item.value for item in TaskPrivacyClass
    }
    assert set(security["network_policy"]["enum"]) == {
        item.value for item in TaskNetworkPolicy
    }


def test_unknown_trust_or_egress_always_denies() -> None:
    assert (
        evaluate_provider_policy(
            profile(trust_class=ProviderTrustClass.UNKNOWN), ENDPOINT, task()
        ).reason_code
        == "PROVIDER_TRUST_UNKNOWN"
    )
    assert (
        evaluate_provider_policy(
            profile(egress_boundary=EgressBoundary.UNKNOWN), ENDPOINT, task()
        ).reason_code
        == "PROVIDER_EGRESS_UNKNOWN"
    )


def test_unresolved_inherit_network_policy_denies() -> None:
    decision = evaluate_provider_policy(
        profile(), ENDPOINT, task(policy=TaskNetworkPolicy.INHERIT)
    )
    assert decision.allowed is False
    assert decision.reason_code == "TASK_NETWORK_POLICY_UNRESOLVED"


def test_external_egress_with_denied_network_denies_but_local_stays_eligible() -> None:
    denied = evaluate_provider_policy(
        profile(), ENDPOINT, task(policy=TaskNetworkPolicy.DENIED)
    )
    assert denied.allowed is False and denied.reason_code == "TASK_NETWORK_DENIED"
    local = evaluate_provider_policy(
        profile(egress_boundary=EgressBoundary.LOCAL_MACHINE),
        None,
        task(policy=TaskNetworkPolicy.DENIED),
    )
    assert local.allowed is True and local.reason_code == "POLICY_ALLOWED_LOCAL_EGRESS"
    no_egress = evaluate_provider_policy(
        profile(egress_boundary=EgressBoundary.NO_EGRESS),
        None,
        task(policy=TaskNetworkPolicy.DENIED),
    )
    assert no_egress.allowed is True


def test_allowlisted_requires_exact_normalized_host_no_wildcards() -> None:
    exact = evaluate_provider_policy(
        profile(), ENDPOINT, task(allowlist=("API.Provider.Example.",)
        )
    )
    assert exact.allowed is True
    for bad in ("provider.example", "api.provider.example.evil.com", "*.provider.example"):
        decision = evaluate_provider_policy(
            profile(), ENDPOINT, task(allowlist=(bad,))
        )
        assert decision.allowed is False, bad
        assert decision.reason_code == "ENDPOINT_NOT_ALLOWLISTED"
    missing_endpoint = evaluate_provider_policy(profile(), None, task())
    assert missing_endpoint.allowed is False
    assert missing_endpoint.reason_code == "ENDPOINT_NOT_ALLOWLISTED"


def test_secret_privacy_or_secret_access_denies_external_only() -> None:
    secret = evaluate_provider_policy(
        profile(), ENDPOINT, task(privacy=TaskPrivacyClass.SECRET)
    )
    assert secret.allowed is False and secret.reason_code == "SECRET_TASK_EXTERNAL_DENIED"
    secret_flag = evaluate_provider_policy(
        profile(), ENDPOINT, task(secret_access=True)
    )
    assert secret_flag.reason_code == "SECRET_TASK_EXTERNAL_DENIED"
    first_party_secret = evaluate_provider_policy(
        profile(
            trust_class=ProviderTrustClass.FIRST_PARTY,
            egress_boundary=EgressBoundary.EXTERNAL_FIRST_PARTY,
        ),
        ENDPOINT,
        task(privacy=TaskPrivacyClass.SECRET),
    )
    assert first_party_secret.allowed is False
    local_secret = evaluate_provider_policy(
        profile(egress_boundary=EgressBoundary.LOCAL_MACHINE),
        None,
        task(privacy=TaskPrivacyClass.SECRET, policy=TaskNetworkPolicy.DENIED),
    )
    assert local_secret.allowed is True


def test_sensitive_denies_third_party_and_requires_allowlist_for_first_party() -> None:
    third_party = evaluate_provider_policy(
        profile(), ENDPOINT, task(privacy=TaskPrivacyClass.SENSITIVE)
    )
    assert third_party.allowed is False
    assert third_party.reason_code == "SENSITIVE_THIRD_PARTY_EXTERNAL_DENIED"
    first_party_ok = evaluate_provider_policy(
        profile(
            trust_class=ProviderTrustClass.FIRST_PARTY,
            egress_boundary=EgressBoundary.EXTERNAL_FIRST_PARTY,
        ),
        ENDPOINT,
        task(privacy=TaskPrivacyClass.SENSITIVE),
    )
    assert first_party_ok.allowed is True
    first_party_blocked = evaluate_provider_policy(
        profile(
            trust_class=ProviderTrustClass.FIRST_PARTY,
            egress_boundary=EgressBoundary.EXTERNAL_FIRST_PARTY,
        ),
        ENDPOINT,
        task(privacy=TaskPrivacyClass.SENSITIVE, allowlist=("other.example",)),
    )
    assert first_party_blocked.allowed is False
    assert first_party_blocked.reason_code == "SENSITIVE_FIRST_PARTY_ALLOWLIST_REQUIRED"


def test_internal_third_party_requires_allowlist_first_party_needs_permission() -> None:
    third_party_blocked = evaluate_provider_policy(
        profile(), ENDPOINT, task(privacy=TaskPrivacyClass.INTERNAL, allowlist=())
    )
    assert third_party_blocked.allowed is False
    assert third_party_blocked.reason_code == "INTERNAL_THIRD_PARTY_ALLOWLIST_REQUIRED"
    third_party_ok = evaluate_provider_policy(
        profile(), ENDPOINT, task(privacy=TaskPrivacyClass.INTERNAL)
    )
    assert third_party_ok.allowed is True
    first_party_denied = evaluate_provider_policy(
        profile(
            trust_class=ProviderTrustClass.FIRST_PARTY,
            egress_boundary=EgressBoundary.EXTERNAL_FIRST_PARTY,
        ),
        ENDPOINT,
        task(privacy=TaskPrivacyClass.INTERNAL, policy=TaskNetworkPolicy.DENIED),
    )
    assert first_party_denied.reason_code == "TASK_NETWORK_DENIED"


def test_public_external_passes_only_when_network_permits() -> None:
    allowed = evaluate_provider_policy(profile(), ENDPOINT, task())
    assert allowed.allowed is True and allowed.reason_code == "POLICY_ALLOWED_EXTERNAL_EGRESS"
    denied = evaluate_provider_policy(
        profile(), ENDPOINT, task(policy=TaskNetworkPolicy.DENIED)
    )
    assert denied.allowed is False
    unresolved = evaluate_provider_policy(
        profile(), ENDPOINT, task(policy=TaskNetworkPolicy.INHERIT)
    )
    assert unresolved.allowed is False


@pytest.mark.parametrize(
    "boundary", [EgressBoundary.LOCAL_MACHINE, EgressBoundary.NO_EGRESS]
)
def test_local_or_no_egress_boundary_rejects_external_endpoint_mismatch(boundary) -> None:
    decision = evaluate_provider_policy(
        profile(egress_boundary=boundary),
        ENDPOINT,
        task(privacy=TaskPrivacyClass.SECRET, policy=TaskNetworkPolicy.DENIED),
    )
    assert decision.allowed is False
    assert decision.reason_code == "PROVIDER_EGRESS_ENDPOINT_MISMATCH"


def test_local_boundary_accepts_explicit_loopback_endpoint() -> None:
    local_endpoint = ProviderEndpointConfig("endpoint:glm", "http://127.0.0.1:3456/v1")
    decision = evaluate_provider_policy(
        profile(egress_boundary=EgressBoundary.LOCAL_MACHINE),
        local_endpoint,
        task(privacy=TaskPrivacyClass.SECRET, policy=TaskNetworkPolicy.DENIED),
    )
    assert decision.allowed is True
    assert decision.reason_code == "POLICY_ALLOWED_LOCAL_EGRESS"
