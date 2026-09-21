from __future__ import annotations

import ast
import dataclasses
import inspect
import json
import socket
import subprocess
import types
from datetime import datetime, timedelta, timezone

import pytest

from a_conductor.provider_configuration import (
    EFFORT_LEVELS,
    EgressBoundary,
    HarnessStrategy,
    ModelCostClass,
    ProtocolFamily,
    ProviderConfiguration,
    ProviderEndpointConfig,
    ProviderHealth,
    ProviderModelConfiguration,
    ProviderObservation,
    ProviderTrustClass,
    QuotaSnapshot,
)
from a_conductor.provider_policy import (
    ProviderPolicyTaskSecurity,
    TaskNetworkPolicy,
    TaskPrivacyClass,
)
from a_conductor.provider_service_authorization import (
    ProviderServiceAuthorizationRecord,
    ServiceAuthorizationState,
    ServiceIntegrationMode,
)
from a_conductor.provider_fallback_policy import (
    ProviderFallbackCandidate,
    ProviderSelectionCostPolicy,
    SelectionStage,
    SelectionOutcome,
    ServiceAuthorizationContext,
    select_pre_attempt_provider,
)

NOW = datetime(2026, 9, 21, 7, 0, tzinfo=timezone.utc)
GENERATION = 7
EVIDENCE_SHA = "a" * 64
_DEFAULT = object()


def make_model(
    model_id: str = "glm-5",
    cost: ModelCostClass = ModelCostClass.FREE,
    efforts: tuple[str, ...] = ("LOW", "HIGH", "MAX"),
) -> ProviderModelConfiguration:
    return ProviderModelConfiguration(
        model_id=model_id,
        display_name=model_id,
        cost_class=cost,
        supported_effort_levels=efforts,
    )


def make_profile(
    provider_id: str = "provider-a",
    models: tuple[ProviderModelConfiguration, ...] | None = None,
    enabled: bool = True,
    trust: ProviderTrustClass = ProviderTrustClass.TRUSTED_THIRD_PARTY,
    egress: EgressBoundary = EgressBoundary.EXTERNAL_THIRD_PARTY,
) -> ProviderConfiguration:
    return ProviderConfiguration(
        provider_id=provider_id,
        display_name=provider_id,
        provider_type="test-provider",
        protocol_family=ProtocolFamily.OPENAI_COMPATIBLE,
        endpoint_ref=f"endpoint:{provider_id}",
        credential_ref=f"secret-ref:{provider_id}",
        trust_class=trust,
        egress_boundary=egress,
        harness_strategies=(HarnessStrategy.DIRECT_API,),
        max_concurrency=1,
        models=models if models is not None else (make_model(),),
        enabled=enabled,
    )


def make_endpoint(profile: ProviderConfiguration) -> ProviderEndpointConfig:
    return ProviderEndpointConfig(
        endpoint_ref=profile.endpoint_ref,
        base_url="https://api.example.com",
    )


def make_observation(
    profile: ProviderConfiguration,
    *,
    generation: int | None = GENERATION,
    health: ProviderHealth = ProviderHealth.AVAILABLE,
    observed_at: datetime = NOW,
    quota: QuotaSnapshot | None = None,
) -> ProviderObservation:
    return ProviderObservation(
        provider_id=profile.provider_id,
        health=health,
        observed_at=observed_at,
        provenance="test-probe",
        configuration_generation=generation,
        quota=quota,
    )


def make_quota(
    *,
    limit: int | float | None = 100,
    used: int | float | None = 20,
    remaining: int | float | None = 80,
) -> QuotaSnapshot:
    return QuotaSnapshot(
        window_type="5h",
        limit=limit,
        used=used,
        remaining=remaining,
        reset_at=NOW,
        reset_in_seconds=3600,
        unit="tokens",
    )


def make_service_record(
    provider_id: str = "provider-a",
    *,
    generation: int = GENERATION,
    state: ServiceAuthorizationState = ServiceAuthorizationState.AUTHORIZED,
    mode: ServiceIntegrationMode = ServiceIntegrationMode.LIVE,
) -> ProviderServiceAuthorizationRecord:
    return ProviderServiceAuthorizationRecord(
        provider_id=provider_id,
        service_identity="conductor",
        state=state,
        integration_mode=mode,
        terms_identity="conductor-terms@2026-01-01",
        evidence_sha256=EVIDENCE_SHA,
        observed_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        recheck_after=datetime(2026, 12, 31, tzinfo=timezone.utc),
        configuration_generation=generation,
    )


def make_candidate(
    *,
    profile: ProviderConfiguration | None = None,
    model: ProviderModelConfiguration | None = None,
    endpoint: object = _DEFAULT,
    observation: object = _DEFAULT,
    generation: int = GENERATION,
    service_record: object = _DEFAULT,
    quota: object = _DEFAULT,
) -> ProviderFallbackCandidate:
    resolved_profile = profile if profile is not None else make_profile()
    return ProviderFallbackCandidate(
        provider_id=resolved_profile.provider_id,
        model=model if model is not None else resolved_profile.models[0],
        profile=resolved_profile,
        endpoint=(
            make_endpoint(resolved_profile)
            if endpoint is _DEFAULT
            else endpoint
        ),
        observation=(
            make_observation(resolved_profile, generation=generation)
            if observation is _DEFAULT
            else observation
        ),
        expected_configuration_generation=generation,
        service_authorization=(
            make_service_record(resolved_profile.provider_id, generation=generation)
            if service_record is _DEFAULT
            else service_record
        ),
        quota=make_quota() if quota is _DEFAULT else quota,
    )


def make_task_security(
    *,
    privacy: TaskPrivacyClass = TaskPrivacyClass.PUBLIC,
    network: TaskNetworkPolicy = TaskNetworkPolicy.ALLOWLISTED,
    allowlist: tuple[str, ...] = ("api.example.com",),
) -> ProviderPolicyTaskSecurity:
    return ProviderPolicyTaskSecurity(
        privacy_class=privacy,
        network_policy=network,
        network_allowlist=allowlist,
    )


def select(
    candidates,
    *,
    effort: str = "HIGH",
    cost_policy: ProviderSelectionCostPolicy | None = None,
    task_security: ProviderPolicyTaskSecurity | None = None,
    service_mode: ServiceIntegrationMode = ServiceIntegrationMode.LIVE,
    now: datetime = NOW,
):
    return select_pre_attempt_provider(
        tuple(candidates),
        task_security=task_security if task_security is not None else make_task_security(),
        requested_effort=effort,
        cost_policy=(
            cost_policy
            if cost_policy is not None
            else ProviderSelectionCostPolicy(allow_paid_substitution=True)
        ),
        service=ServiceAuthorizationContext(
            service_identity="conductor",
            terms_identity="conductor-terms@2026-01-01",
            requested_mode=service_mode,
        ),
        now=now,
    )


def selected_valid_candidate(
    provider_id: str = "provider-a",
    **kwargs,
) -> ProviderFallbackCandidate:
    profile = make_profile(provider_id=provider_id)
    return make_candidate(profile=profile, **kwargs)


# --- Floor 1: unauthorized / outside explicit set -------------------------------


def test_empty_explicit_set_is_typed_no_candidate() -> None:
    result = select(())
    assert result.outcome is SelectionOutcome.NO_CANDIDATE_EMPTY_SET
    assert result.provider_id is None
    assert result.model_id is None
    assert result.expected_configuration_generation is None


def test_unauthorized_service_candidate_is_rejected() -> None:
    blocked = make_candidate(
        service_record=make_service_record(
            state=ServiceAuthorizationState.BLOCKED_EXTERNAL
        )
    )
    result = select((blocked,))
    assert result.outcome is SelectionOutcome.NO_CANDIDATE_ALL_INELIGIBLE
    assert result.evaluations[0].reason_code.startswith("SERVICE_AUTHORIZATION_DENIED")
    assert result.evaluations[0].stage is SelectionStage.READY


def test_service_mode_mismatch_is_rejected() -> None:
    mismatched = make_candidate(
        service_record=make_service_record(mode=ServiceIntegrationMode.READ_ONLY)
    )
    result = select((mismatched,), service_mode=ServiceIntegrationMode.LIVE)
    assert result.outcome is SelectionOutcome.NO_CANDIDATE_ALL_INELIGIBLE
    assert "SERVICE_AUTHORIZATION_MODE_MISMATCH" in result.evaluations[0].reason_code


def test_missing_service_record_fails_closed_for_live_mode() -> None:
    no_record = make_candidate(service_record=None)
    result = select((no_record,), service_mode=ServiceIntegrationMode.LIVE)
    assert result.outcome is SelectionOutcome.NO_CANDIDATE_ALL_INELIGIBLE
    assert "SERVICE_AUTHORIZATION_REQUIRED" in result.evaluations[0].reason_code


def test_fake_mode_requires_no_service_record() -> None:
    no_record = make_candidate(service_record=None)
    result = select((no_record,), service_mode=ServiceIntegrationMode.FAKE)
    assert result.outcome is SelectionOutcome.SELECTED
    assert result.provider_id == "provider-a"


def test_outside_explicit_set_is_never_selected() -> None:
    # provider-a is fully valid but outside the supplied set; only provider-b is
    # explicitly authorized for this attempt.
    result = select((selected_valid_candidate("provider-b"),))
    assert result.outcome is SelectionOutcome.SELECTED
    assert result.provider_id == "provider-b"


def test_no_cross_call_candidate_memory() -> None:
    first = select((selected_valid_candidate("provider-a"),))
    second = select((selected_valid_candidate("provider-b"),))
    assert first.provider_id == "provider-a"
    assert second.provider_id == "provider-b"
    assert "provider-a" not in second.to_json()


# --- Floor 2: stale/missing generation/readiness evidence ------------------------


@pytest.mark.parametrize(
    ("observation", "expected_reason"),
    [
        (None, "READINESS_EVIDENCE_MISSING"),
        (
            make_observation(
                make_profile(), generation=None, quota=None
            ),
            "READINESS_GENERATION_MISSING",
        ),
        (
            make_observation(
                make_profile(), generation=GENERATION - 1, quota=None
            ),
            "READINESS_GENERATION_STALE",
        ),
        (
            make_observation(
                make_profile(),
                observed_at=NOW - timedelta(seconds=600),
                quota=None,
            ),
            "READINESS_OBSERVATION_STALE",
        ),
        (
            make_observation(
                make_profile(), health=ProviderHealth.DEGRADED, quota=None
            ),
            "READINESS_OBSERVATION_STALE",
        ),
    ],
)
def test_missing_or_stale_readiness_evidence_selects_nothing(
    observation, expected_reason: str
) -> None:
    candidate = make_candidate(observation=observation)
    result = select((candidate,))
    assert result.outcome is SelectionOutcome.NO_CANDIDATE_ALL_INELIGIBLE
    assert result.evaluations[0].reason_code == expected_reason
    assert result.evaluations[0].stage is SelectionStage.CAPABLE


def test_disabled_provider_is_rejected() -> None:
    candidate = make_candidate(profile=make_profile(enabled=False))
    result = select((candidate,))
    assert result.evaluations[0].reason_code == "PROVIDER_DISABLED"


def test_service_record_generation_stale_is_rejected() -> None:
    candidate = make_candidate(
        service_record=make_service_record(generation=GENERATION - 1)
    )
    result = select((candidate,))
    assert "SERVICE_AUTHORIZATION_GENERATION_STALE" in result.evaluations[0].reason_code


# --- Floor 3: unsupported model/effort -------------------------------------------


def test_unsupported_effort_is_ineligible() -> None:
    profile = make_profile(models=(make_model(efforts=("LOW",)),))
    candidate = make_candidate(profile=profile)
    result = select((candidate,), effort="MAX")
    assert result.outcome is SelectionOutcome.NO_CANDIDATE_ALL_INELIGIBLE
    assert result.evaluations[0].reason_code == "EFFORT_UNSUPPORTED"
    assert result.evaluations[0].stage is SelectionStage.NOT_CAPABLE


def test_default_effort_is_always_capable() -> None:
    profile = make_profile(models=(make_model(efforts=("LOW",)),))
    candidate = make_candidate(profile=profile)
    result = select((candidate,), effort="DEFAULT")
    assert result.outcome is SelectionOutcome.SELECTED


def test_model_missing_from_provider_configuration_is_ineligible() -> None:
    profile = make_profile(models=(make_model(model_id="glm-5"),))
    stranger = make_model(model_id="stranger-model")
    candidate = make_candidate(profile=profile, model=stranger)
    result = select((candidate,))
    assert result.evaluations[0].reason_code == "MODEL_NOT_IN_PROVIDER_CONFIGURATION"
    assert result.evaluations[0].stage is SelectionStage.NOT_CAPABLE


def test_model_configuration_drift_is_ineligible() -> None:
    profile = make_profile(models=(make_model(cost=ModelCostClass.FREE),))
    drifted = make_model(cost=ModelCostClass.PREMIUM)
    candidate = make_candidate(profile=profile, model=drifted)
    result = select((candidate,))
    assert result.evaluations[0].reason_code == "MODEL_CONFIGURATION_MISMATCH"


# --- Floor 4: task/service authorization denial ----------------------------------


def test_task_policy_denial_is_ineligible() -> None:
    candidate = make_candidate()
    result = select(
        (candidate,),
        task_security=make_task_security(
            privacy=TaskPrivacyClass.SENSITIVE, allowlist=()
        ),
    )
    assert result.evaluations[0].reason_code.startswith("PROVIDER_POLICY_DENIED")
    assert result.evaluations[0].stage is SelectionStage.READY


def test_local_provider_with_external_endpoint_is_denied_by_policy() -> None:
    profile = make_profile(
        trust=ProviderTrustClass.LOCAL, egress=EgressBoundary.LOCAL_MACHINE
    )
    candidate = make_candidate(profile=profile)
    result = select((candidate,))
    assert result.evaluations[0].reason_code.startswith("PROVIDER_POLICY_DENIED")


# --- Floor 5: quota gates ---------------------------------------------------------


@pytest.mark.parametrize(
    ("quota", "expected_reason"),
    [
        (make_quota(used=100, remaining=0), "QUOTA_EXHAUSTED"),
        (None, "QUOTA_UNKNOWN"),
        (make_quota(limit=None), "QUOTA_UNKNOWN"),
        (make_quota(used=10, remaining=80), "QUOTA_UNKNOWN"),
    ],
)
def test_bad_quota_evidence_is_ineligible(quota, expected_reason: str) -> None:
    candidate = make_candidate(quota=quota)
    result = select((candidate,))
    assert result.evaluations[0].reason_code == expected_reason
    assert result.evaluations[0].stage is SelectionStage.AUTHORIZED


def test_low_quota_is_not_exhausted_and_remains_eligible() -> None:
    candidate = make_candidate(quota=make_quota(used=80, remaining=20))
    result = select((candidate,))
    assert result.outcome is SelectionOutcome.SELECTED


def test_unknown_quota_is_never_promoted_over_known_available() -> None:
    unknown = make_candidate(quota=None)
    known = make_candidate(
        profile=make_profile(provider_id="provider-known"),
        quota=make_quota(used=80, remaining=20),
    )
    result = select((unknown, known))
    # Explicit order still wins selection among *eligible* candidates, but the
    # unknown-quota candidate must itself be ineligible — never optimistically
    # promoted to eligible.
    assert result.provider_id == "provider-known"
    assert result.evaluations[0].eligible is False
    assert result.evaluations[0].reason_code == "QUOTA_UNKNOWN"


# --- Floor 6: cost ceiling / paid substitution ------------------------------------


def test_paid_substitution_not_authorized_by_default() -> None:
    profile = make_profile(models=(make_model(cost=ModelCostClass.PREMIUM),))
    candidate = make_candidate(profile=profile)
    result = select((candidate,), cost_policy=ProviderSelectionCostPolicy())
    assert result.evaluations[0].reason_code == "PAID_SUBSTITUTION_NOT_AUTHORIZED"
    assert result.outcome is SelectionOutcome.NO_CANDIDATE_ALL_INELIGIBLE


def test_cost_ceiling_is_enforced() -> None:
    profile = make_profile(models=(make_model(cost=ModelCostClass.PREMIUM),))
    candidate = make_candidate(profile=profile)
    result = select(
        (candidate,),
        cost_policy=ProviderSelectionCostPolicy(
            allow_paid_substitution=True,
            max_cost_class=ModelCostClass.LOW_COST,
        ),
    )
    assert result.evaluations[0].reason_code == "COST_CEILING_EXCEEDED"


def test_unknown_cost_class_fails_closed() -> None:
    profile = make_profile(models=(make_model(cost=ModelCostClass.UNKNOWN),))
    candidate = make_candidate(profile=profile)
    result = select(
        (candidate,),
        cost_policy=ProviderSelectionCostPolicy(allow_paid_substitution=True),
    )
    assert result.evaluations[0].reason_code == "COST_CLASS_UNKNOWN"


def test_unknown_cost_class_requires_explicit_allow() -> None:
    profile = make_profile(models=(make_model(cost=ModelCostClass.UNKNOWN),))
    candidate = make_candidate(profile=profile)
    result = select(
        (candidate,),
        cost_policy=ProviderSelectionCostPolicy(
            allow_paid_substitution=True,
            allow_unknown_cost_class=True,
        ),
    )
    assert result.outcome is SelectionOutcome.SELECTED


# --- Floor 7: deterministic first eligible choice ---------------------------------


def test_first_eligible_in_explicit_order_wins_over_cheaper_later_candidate() -> None:
    paid = make_candidate(
        profile=make_profile(
            provider_id="provider-paid",
            models=(make_model(cost=ModelCostClass.PREMIUM),),
        )
    )
    free = make_candidate(
        profile=make_profile(
            provider_id="provider-free",
            models=(make_model(cost=ModelCostClass.FREE),),
        )
    )
    result = select((paid, free))
    assert result.outcome is SelectionOutcome.SELECTED
    assert result.provider_id == "provider-paid"
    assert result.reason_code == "SELECTED_FIRST_ELIGIBLE_IN_EXPLICIT_ORDER"


def test_ineligible_first_candidate_is_skipped_deterministically() -> None:
    ineligible = make_candidate(quota=make_quota(used=100, remaining=0))
    eligible = selected_valid_candidate("provider-b")
    result = select((ineligible, eligible))
    assert result.provider_id == "provider-b"
    assert [ev.provider_id for ev in result.evaluations] == ["provider-a", "provider-b"]


# --- Floor 8: same-input equality/byte-stable result ------------------------------


def test_same_inputs_produce_equal_byte_stable_results() -> None:
    def build_inputs():
        return (
            (
                make_candidate(
                    profile=make_profile(
                        provider_id="provider-a",
                        models=(make_model(cost=ModelCostClass.LOW_COST),),
                    )
                ),
                selected_valid_candidate("provider-b"),
            ),
            make_task_security(),
        )

    candidates_a, task_a = build_inputs()
    candidates_b, task_b = build_inputs()
    first = select(candidates_a, task_security=task_a)
    second = select(candidates_b, task_security=task_b)

    assert first == second
    assert first.to_json() == second.to_json()
    assert first.result_sha256 == second.result_sha256
    assert json.loads(first.to_json()) == first.to_dict()
    assert first is not second


# --- Floor 9 + 11: never ADMITTED, no fabricated WO128 history --------------------


def test_selected_result_never_claims_admitted() -> None:
    result = select((selected_valid_candidate(),))
    assert result.outcome is SelectionOutcome.SELECTED
    selected_evaluation = next(
        ev for ev in result.evaluations if ev.provider_id == result.provider_id
    )
    assert selected_evaluation.stage is SelectionStage.AUTHORIZED
    for evaluation in result.evaluations:
        assert evaluation.stage is not SelectionStage.ADMITTED
    assert "ADMITTED" not in result.to_json()


def test_result_carries_no_fabricated_historical_evidence() -> None:
    result = select((selected_valid_candidate(),))
    payload = result.to_dict()
    assert set(payload) == {
        "outcome",
        "provider_id",
        "model_id",
        "expected_configuration_generation",
        "requested_effort",
        "reason_code",
        "evaluations",
    }
    serialized = result.to_json()
    assert "admission" not in serialized.lower()
    assert "fallback_reason" not in serialized
    assert "selection_history" not in serialized


def test_selected_identity_and_generation_are_returned() -> None:
    result = select((selected_valid_candidate("provider-a"),), effort="MAX")
    assert result.provider_id == "provider-a"
    assert result.model_id == "glm-5"
    assert result.expected_configuration_generation == GENERATION
    assert result.requested_effort == "MAX"


# --- Floor 10: no filesystem/network/subprocess/store side effects ----------------


def test_selection_trips_no_io_probes(monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise AssertionError("side-effect probe tripped")

    monkeypatch.setattr("builtins.open", boom)
    monkeypatch.setattr(socket, "socket", boom)
    monkeypatch.setattr(subprocess, "Popen", boom)
    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(subprocess, "check_output", boom)

    result = select((selected_valid_candidate(),))
    assert result.outcome is SelectionOutcome.SELECTED
    rejected = select(
        (make_candidate(quota=None),),
    )
    assert rejected.outcome is SelectionOutcome.NO_CANDIDATE_ALL_INELIGIBLE


# --- Floor 12: #215/WO433 authority unchanged --------------------------------------


_AUTHORITY_IMPORT_ROOTS = frozenset(
    {
        "asyncio",
        "ctypes",
        "http",
        "io",
        "keyring",
        "multiprocessing",
        "os",
        "pathlib",
        "requests",
        "secrets",
        "shutil",
        "signal",
        "socket",
        "ssl",
        "subprocess",
        "sys",
        "tempfile",
        "threading",
        "urllib",
    }
)
_AUTHORITY_IDENTIFIERS = frozenset(
    {
        "GraphDispatch",
        "NEXT_READY",
        "Popen",
        "activate",
        "admit",
        "admission",
        "check_call",
        "check_output",
        "connect",
        "credential",
        "dispatch",
        "environ",
        "getenv",
        "launch",
        "password",
        "persist",
        "recv",
        "retry",
        "save",
        "secret",
        "secrets",
        "send",
        "store",
        "token",
        "urlopen",
    }
)


def test_runtime_activation_authority_remains_untouched() -> None:
    import a_conductor.provider_fallback_policy as module

    tree = ast.parse(inspect.getsource(module))

    import_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            import_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None and node.level == 0:
                import_roots.add(node.module.split(".")[0])
    assert not import_roots & _AUTHORITY_IMPORT_ROOTS

    code_identifiers: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            code_identifiers.add(node.id)
        elif isinstance(node, ast.Attribute):
            code_identifiers.add(node.attr)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            code_identifiers.add(node.name)
        elif isinstance(node, ast.alias):
            code_identifiers.add((node.asname or node.name).split(".")[0])
    assert not code_identifiers & _AUTHORITY_IDENTIFIERS

    assert not set(vars(module)) & _AUTHORITY_IDENTIFIERS

    public_functions = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]
    assert public_functions == ["select_pre_attempt_provider"]

    for forbidden in ("activate", "dispatch", "launch", "retry", "admit"):
        assert not hasattr(module, forbidden)


# --- Aggressive input validation ---------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"effort": "ULTRA"},
        {"effort": ""},
        {"task_security": "not-a-task-security"},
        {"cost_policy": "not-a-cost-policy"},
        {"now": datetime(2026, 9, 21, 7, 0)},
    ],
)
def test_invalid_selection_inputs_fail_closed(kwargs) -> None:
    with pytest.raises(ValueError):
        select((selected_valid_candidate(),), **kwargs)


def test_non_candidate_items_fail_closed() -> None:
    with pytest.raises(ValueError):
        select(("provider-a",))


def test_candidate_identity_mismatch_fails_closed() -> None:
    profile = make_profile(provider_id="provider-a")
    with pytest.raises(ValueError):
        ProviderFallbackCandidate(
            provider_id="provider-b",
            model=profile.models[0],
            profile=profile,
            endpoint=make_endpoint(profile),
            observation=make_observation(profile),
            expected_configuration_generation=GENERATION,
            service_authorization=make_service_record("provider-b"),
            quota=make_quota(),
        )


def test_candidate_observation_identity_mismatch_fails_closed() -> None:
    profile = make_profile(provider_id="provider-a")
    stranger_observation = make_observation(make_profile(provider_id="provider-z"))
    with pytest.raises(ValueError):
        ProviderFallbackCandidate(
            provider_id="provider-a",
            model=profile.models[0],
            profile=profile,
            endpoint=make_endpoint(profile),
            observation=stranger_observation,
            expected_configuration_generation=GENERATION,
            service_authorization=make_service_record("provider-a"),
            quota=make_quota(),
        )


def test_candidate_non_positive_generation_fails_closed() -> None:
    profile = make_profile()
    with pytest.raises(ValueError):
        ProviderFallbackCandidate(
            provider_id="provider-a",
            model=profile.models[0],
            profile=profile,
            endpoint=make_endpoint(profile),
            observation=make_observation(profile),
            expected_configuration_generation=0,
            service_authorization=make_service_record("provider-a"),
            quota=make_quota(),
        )


def test_effort_vocabulary_matches_repo_contract() -> None:
    assert EFFORT_LEVELS == {"LOW", "HIGH", "MAX", "DEFAULT"}
