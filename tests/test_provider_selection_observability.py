"""WO128 T1 — pure provider selection/fallback observability projection tests.

The projection is one-provider-at-a-time, store-free, and must never invent
selection or fallback authority. Missing evidence is ``UNKNOWN``; absent
fallback authority is ``NOT_EVALUATED``; these are constants, not derivations.
"""

from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone

import pytest

from a_conductor.provider_config_store import ProviderAdmissionRecord
from a_conductor.provider_selection_observability import (
    EXPIRY_NOT_EVALUATED,
    EXPIRY_PAST_EXPIRY_RECONCILE_REQUIRED,
    EXPIRY_TERMINAL,
    GENERATION_MATCHES_CURRENT,
    GENERATION_STALE_VS_CURRENT,
    GENERATION_UNKNOWN,
    AdmissionEvidence,
    ProviderSelectionEvidence,
    project_provider_selection_evidence,
)


NOW = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)


def make_record(**overrides) -> ProviderAdmissionRecord:
    data = dict(
        admission_id="admission-001",
        provider_id="provider-test",
        execution_id="exec-1",
        batch_id="batch-1",
        acquired_at=NOW - timedelta(minutes=10),
        expires_at=NOW + timedelta(minutes=10),
        status="ACTIVE",
        released_at=None,
        reconciled_at=None,
        configuration_generation=3,
    )
    data.update(overrides)
    return ProviderAdmissionRecord(**data)


def project(records, *, provider_id="provider-test", generation=3, now=None):
    return project_provider_selection_evidence(
        provider_id=provider_id,
        current_configuration_generation=generation,
        admissions=tuple(records),
        now=now,
    )


def test_wo128_projection_no_admissions_keeps_unknown_and_not_evaluated() -> None:
    evidence = project(())
    assert isinstance(evidence, ProviderSelectionEvidence)
    assert evidence.selection_reason == "UNKNOWN"
    assert evidence.fallback_reason == "NOT_EVALUATED"
    assert evidence.admissions == ()
    assert evidence.current_configuration_generation == 3


def test_wo128_projection_generation_match_and_drift() -> None:
    matching = project([make_record(configuration_generation=3)])
    assert matching.admissions[0].generation_relation == GENERATION_MATCHES_CURRENT
    assert matching.admissions[0].generation_relation == "MATCHES_CURRENT"

    drifted = project([make_record(configuration_generation=2)])
    assert drifted.admissions[0].generation_relation == GENERATION_STALE_VS_CURRENT
    assert drifted.admissions[0].generation_relation == "STALE_VS_CURRENT"


def test_wo128_projection_generation_unknown_cases() -> None:
    legacy = project([make_record(configuration_generation=None)])
    assert legacy.admissions[0].generation_relation == GENERATION_UNKNOWN

    unknown_current = project([make_record()], generation=None)
    assert unknown_current.admissions[0].generation_relation == GENERATION_UNKNOWN
    assert unknown_current.current_configuration_generation is None


def test_wo128_projection_released_is_terminal_observed_fact() -> None:
    released_at = NOW - timedelta(minutes=1)
    released = project([
        make_record(
            status="RELEASED",
            released_at=released_at,
            reconciled_at=released_at,
            expires_at=NOW - timedelta(minutes=2),
        )
    ], now=NOW)
    item = released.admissions[0]
    assert item.status == "RELEASED"
    assert item.released_at == released_at
    assert item.expiry_observation == EXPIRY_TERMINAL
    # a released grant is a capacity fact, never an execution-outcome claim
    assert not any(
        word in repr(item).upper()
        for word in ("RUNNING", "COMPLETED", "SUCCEEDED", "FAILED")
    )


def test_wo128_projection_active_past_expiry_is_reconcile_unknown() -> None:
    past = project([make_record(expires_at=NOW - timedelta(seconds=1))], now=NOW)
    item = past.admissions[0]
    assert item.status == "ACTIVE"
    assert item.expiry_observation == EXPIRY_PAST_EXPIRY_RECONCILE_REQUIRED
    assert item.expiry_observation == "PAST_EXPIRY_RECONCILE_REQUIRED"
    assert "RUNNING" not in repr(item).upper()

    persisted_expired = project([make_record(status="EXPIRED")], now=NOW)
    assert persisted_expired.admissions[0].expiry_observation == EXPIRY_PAST_EXPIRY_RECONCILE_REQUIRED

    not_expired = project([make_record(expires_at=NOW + timedelta(seconds=1))], now=NOW)
    assert not_expired.admissions[0].expiry_observation == "NOT_EXPIRED"


def test_wo128_projection_expiry_not_evaluated_without_clock() -> None:
    evidence = project([make_record(expires_at=NOW - timedelta(seconds=1))], now=None)
    assert evidence.admissions[0].expiry_observation == EXPIRY_NOT_EVALUATED
    assert evidence.admissions[0].expiry_observation == "EXPIRY_NOT_EVALUATED"


def test_wo128_projection_near_miss_ids_never_joined() -> None:
    near_misses = (
        make_record(execution_id="exec-1", batch_id="batch-1", admission_id="admission-001"),
        make_record(execution_id="exec-11", batch_id="batch-11", admission_id="admission-011"),
        make_record(execution_id="exec-1 ", batch_id="batch-1", admission_id="admission-002"),
    )
    evidence = project(near_misses)
    assert len(evidence.admissions) == 3
    assert {item.execution_id for item in evidence.admissions} == {
        "exec-1", "exec-11", "exec-1 ",
    }
    assert all(isinstance(item, AdmissionEvidence) for item in evidence.admissions)
    # no API exists that could correlate them: exact IDs only, verbatim
    assert not hasattr(evidence, "joined_task") and not hasattr(evidence, "task_join")


def test_wo128_projection_two_providers_independent_no_cross_provider_api() -> None:
    failing_provider_a = project(
        [make_record(status="EXPIRED", provider_id="provider-a")],
        provider_id="provider-a",
        generation=None,
        now=NOW,
    )
    healthy_provider_b = project(
        [make_record(status="ACTIVE", provider_id="provider-b")],
        provider_id="provider-b",
        generation=3,
        now=NOW,
    )
    assert failing_provider_a.fallback_reason == "NOT_EVALUATED"
    assert healthy_provider_b.fallback_reason == "NOT_EVALUATED"
    assert failing_provider_a.provider_id == "provider-a"
    assert healthy_provider_b.provider_id == "provider-b"

    signature = inspect.signature(project_provider_selection_evidence)
    assert "provider_id" in signature.parameters
    assert not any(
        "providers" in name for name in signature.parameters
    ), "projection must accept exactly one provider at a time"
    module = __import__(
        "a_conductor.provider_selection_observability", fromlist=["x"]
    )
    public_functions = {
        name
        for name, obj in inspect.getmembers(module, inspect.isfunction)
        if not name.startswith("_") and obj.__module__ == module.__name__
    }
    assert public_functions == {"project_provider_selection_evidence"}, (
        "the projection module must expose exactly one public single-provider entry point"
    )


def test_wo128_projection_selection_reason_unknown_regardless_of_fixture() -> None:
    healthy = project(
        [make_record(status="ACTIVE", configuration_generation=3)], now=NOW
    )
    assert healthy.selection_reason == "UNKNOWN"
    with_admissions = project(
        [make_record(status="ACTIVE", configuration_generation=3)]
    )
    assert with_admissions.selection_reason == "UNKNOWN"


def test_wo128_projection_invalid_inputs_fail_closed() -> None:
    with pytest.raises(ValueError):
        project_provider_selection_evidence(
            provider_id="  ",
            current_configuration_generation=1,
            admissions=(),
        )
    with pytest.raises(ValueError):
        project_provider_selection_evidence(
            provider_id="provider-test",
            current_configuration_generation=0,
            admissions=(),
        )
    with pytest.raises(ValueError):
        project_provider_selection_evidence(
            provider_id="provider-test",
            current_configuration_generation=True,
            admissions=(),
        )
    with pytest.raises(ValueError):
        project_provider_selection_evidence(
            provider_id="provider-test",
            current_configuration_generation=1,
            admissions=(make_record(provider_id="provider-other"),),
        )
    with pytest.raises(ValueError):
        project_provider_selection_evidence(
            provider_id="provider-test",
            current_configuration_generation=1,
            admissions=("not-a-record",),
        )
    with pytest.raises(ValueError):
        project_provider_selection_evidence(
            provider_id="provider-test",
            current_configuration_generation=1,
            admissions=(),
            now=NOW.replace(tzinfo=None),
        )
    with pytest.raises(ValueError):
        project([make_record(status="RUNNING")], now=NOW)
    with pytest.raises(ValueError):
        project([make_record(status="")], now=NOW)


def test_wo128_projection_deterministic_ordering_stress() -> None:
    records = tuple(
        make_record(
            admission_id=f"admission-{index:03d}",
            execution_id=f"exec-{index}",
            acquired_at=NOW - timedelta(minutes=index),
        )
        for index in range(12)
    )
    expected = project(records, now=NOW)
    shuffled = tuple(reversed(records))
    assert project(shuffled, now=NOW).admissions == expected.admissions
    assert project(records, now=NOW) == expected
    assert project(records, now=NOW) == expected

    by_id = {record.admission_id: record for record in records}
    ids = [item.admission_id for item in expected.admissions]
    assert len(ids) == 12 and len(set(ids)) == 12
    for first, second in zip(ids, ids[1:]):
        left, right = by_id[first].acquired_at, by_id[second].acquired_at
        assert left > right or (left == right and first > second)
