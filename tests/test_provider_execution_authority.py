from __future__ import annotations

import hashlib
import json

import pytest

from a_conductor.provider_execution_authority import ProviderExecutionRequirement
from a_conductor.provider_policy import TaskNetworkPolicy, TaskPrivacyClass


def authority_bytes(*, privacy="INTERNAL", network="ALLOWLISTED", secret=False) -> bytes:
    payload = {
        "schema_version": "1.0.0",
        "task_id": "task-wo118b",
        "goal": "bounded provider execution",
        "risk_class": "HIGH",
        "authority": {"requested_by": "test", "mutation_allowed": False, "human_approval_required": False},
        "target": {"project_id": "project-1", "identity_policy": "EXACT"},
        "scope": {"allowed_files": [], "forbidden_files": [], "allowed_commands": [], "forbidden_commands": []},
        "acceptance": {"criteria": ["typed result"], "verify_commands": [], "review_required": True},
        "security": {
            "privacy_class": privacy,
            "network_policy": network,
            "network_allowlist": ["provider.example"],
            "secret_access": secret,
        },
        "budget": {"max_elapsed_seconds": 300},
        "retry_policy": {"max_attempts": 1, "max_identical_failures": 1, "on_lease_expiry": "RECOVERY_REQUIRED"},
        "escalation": {"conditions": ["SECURITY_BOUNDARY_CHANGE"]},
        "required_evidence": ["TEST_RESULT"],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build(tmp_path, raw: bytes, *, generation=1, base_operation_ref="operation-node"):
    path = tmp_path / "docs" / "tasks" / "node.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return ProviderExecutionRequirement.from_task_contract_file(
        project_root=tmp_path, provider_id="provider-glm-shared", provider_authority_path=tmp_path / "provider.sqlite",
        expected_configuration_generation=generation,
        task_contract_ref="docs/tasks/node.json", base_operation_ref=base_operation_ref,
        expected_authority_sha256=hashlib.sha256(raw).hexdigest(),
    )


def test_requirement_derives_security_and_stable_digest_from_exact_authority_bytes(tmp_path) -> None:
    raw = authority_bytes()
    first = build(tmp_path, raw)
    second = build(tmp_path, raw)

    assert first == second
    assert first.provider_security.privacy_class is TaskPrivacyClass.INTERNAL
    assert first.provider_security.network_policy is TaskNetworkPolicy.ALLOWLISTED
    assert first.provider_security.network_allowlist == ("provider.example",)
    assert first.provider_security.secret_access is False
    assert first.authority_sha256 == hashlib.sha256(raw).hexdigest()
    assert first.requirement_sha256 == second.requirement_sha256
    assert first.operation_ref == second.operation_ref
    assert first.operation_ref.startswith("provider-op:")


def test_changed_security_or_generation_changes_durable_requirement_identity(tmp_path) -> None:
    base = build(tmp_path, authority_bytes())
    secret = build(tmp_path, authority_bytes(privacy="SECRET", secret=True))
    generation2 = build(tmp_path, authority_bytes(), generation=2)

    assert len({base.requirement_sha256, secret.requirement_sha256, generation2.requirement_sha256}) == 3
    assert len({base.operation_ref, secret.operation_ref, generation2.operation_ref}) == 3


def test_authority_hash_mismatch_and_missing_security_fail_closed(tmp_path) -> None:
    raw = authority_bytes()
    path = tmp_path / "docs" / "tasks" / "node.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    with pytest.raises(ValueError, match="authority_sha256"):
        ProviderExecutionRequirement.from_task_contract_file(
            project_root=tmp_path, provider_id="provider-glm-shared", provider_authority_path=tmp_path / "provider.sqlite",
            expected_configuration_generation=1, task_contract_ref="docs/tasks/node.json",
            base_operation_ref="operation-node", expected_authority_sha256="0" * 64,
        )

    missing = json.dumps({"schema_version": "1.0.0", "task_id": "task"}).encode()
    with pytest.raises(ValueError, match="security"):
        build(tmp_path, missing)


def _provider_profile(endpoint_ref: str = "endpoint-ref:test"):
    from a_conductor.provider_configuration import (
        EgressBoundary, HarnessStrategy, ProtocolFamily, ProviderConfiguration,
        ProviderModelConfiguration, ProviderTrustClass,
    )
    return ProviderConfiguration(
        provider_id="provider-glm-shared", display_name="GLM", provider_type="proxy",
        protocol_family=ProtocolFamily.ANTHROPIC_MESSAGES, endpoint_ref=endpoint_ref,
        credential_ref="secret-ref:test", trust_class=ProviderTrustClass.TRUSTED_THIRD_PARTY,
        egress_boundary=EgressBoundary.EXTERNAL_THIRD_PARTY,
        harness_strategies=(HarnessStrategy.CLAUDE_CODE_CLI,), max_concurrency=1,
        models=(ProviderModelConfiguration("glm-5.3", "GLM 5.3"),), enabled=True,
    )

def test_authority_uses_only_fresh_snapshot_route_and_exact_generation(tmp_path) -> None:
    from datetime import datetime, timezone
    from a_conductor.provider_config_store import SQLiteProviderConfigStore
    from a_conductor.provider_configuration import ProviderEndpointConfig, ProviderHealth, ProviderObservation
    from a_conductor.provider_execution_authority import ProviderExecutionAuthority

    store = SQLiteProviderConfigStore(tmp_path / "provider.sqlite")
    profile = _provider_profile()
    store.save_endpoint(ProviderEndpointConfig(profile.endpoint_ref, "https://evil.example/v1"))
    store.save_provider(profile)
    store.save_observation(ProviderObservation(
        provider_id=profile.provider_id, health=ProviderHealth.AVAILABLE,
        observed_at=datetime(2026, 9, 1, tzinfo=timezone.utc), provenance="test",
        configuration_generation=1,
    ))
    requirement = build(tmp_path, authority_bytes(), generation=1)
    decision = ProviderExecutionAuthority(store).authorize(
        requirement, now=datetime(2026, 9, 1, tzinfo=timezone.utc)
    )
    assert decision.allowed is False
    assert decision.reason_code == "INTERNAL_THIRD_PARTY_ALLOWLIST_REQUIRED"

    snapshot = store.load_provider_snapshot(profile.provider_id)
    assert snapshot is not None
    store.save_provider(
        type(profile)(**{**snapshot.profile.as_dict(), "display_name": "GLM v2"}),
        expected_generation=1,
    )
    stale = ProviderExecutionAuthority(store).authorize(
        requirement, now=datetime(2026, 9, 1, tzinfo=timezone.utc)
    )
    assert stale.allowed is False
    assert stale.reason_code == "PROVIDER_CONFIGURATION_STALE"


def test_authority_rejects_different_provider_store_identity(tmp_path) -> None:
    from datetime import datetime, timezone
    from a_conductor.provider_config_store import SQLiteProviderConfigStore
    from a_conductor.provider_execution_authority import ProviderExecutionAuthority

    requirement = build(tmp_path, authority_bytes(), generation=1)
    other = SQLiteProviderConfigStore(tmp_path / "other-provider.sqlite")
    decision = ProviderExecutionAuthority(other).authorize(
        requirement, now=datetime(2026, 9, 1, tzinfo=timezone.utc)
    )
    assert decision.allowed is False
    assert decision.reason_code == "PROVIDER_AUTHORITY_STORE_MISMATCH"
