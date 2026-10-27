from copy import deepcopy
from dataclasses import replace

import pytest

from a_conductor.a_faster_utilization_guard import (
    AFasterActivation, QuotaAdmission, UtilizationFacts,
)
from a_conductor.codex_goal_api_adapter import QueueEntry, TurnEvidence
from a_conductor.codex_queue_submission_guard import queue_submission_task_key
from a_conductor.orchestration import OrchestrationSignal
from a_conductor.orchestration_guards import (
    AuthorityGuard, DuplicateGuard, GuardPipeline, GuardResult, UtilizationGuard,
)


def signal(kind="ENQUEUE", trigger="EXPLICIT", target="PARENT_QUEUE"):
    payload = {"target": target, "trigger": trigger, "intent_ref": "intent:1"}
    if target == "PARENT_QUEUE":
        payload["parent_binding_ref"] = "parent:1"
    else:
        payload.update(ready_plan_ref="plan:1", task_map_ref="map:1")
    if kind == "REPLAY":
        payload["recovery_evidence_ref"] = "recovery:1"
        payload["prior_submission_ref" if target == "PARENT_QUEUE"
                else "prior_execution_ref"] = "prior:1"
    if kind == "LIFECYCLE":
        payload = dict(hook_event_ref="hook:1", subject_ref="job:1", observation_ref="obs:1")
    if kind == "UTILIZATION":
        payload = dict(census_ref="census:1", ready_set_ref="ready:1",
                       activation_ref="activation:1", provider_observation_ref="quota:1")
    return OrchestrationSignal("orch-signal.v1", "signal:1", kind,
                               "2026-10-23T19:00:00Z", "source:1", "project:1",
                               payload, "task:1", "wo:1", None)


def evidence(**changes):
    return dict(queue_entries=(), turns=(), queue_evidence_complete=True,
                turn_evidence_complete=True) | changes


def facts(**changes):
    return replace(UtilizationFacts(
        activation=AFasterActivation.ACTIVE, ready_mutable_candidates=3,
        ready_review_candidates=1, glm_quota_admission=QuotaAdmission.QUOTA_AVAILABLE,
        glm_route_ready=True), **changes)


@pytest.mark.parametrize("kind", ["ENQUEUE", "REPLAY"])
def test_duplicate_clear(kind):
    result = DuplicateGuard().evaluate(signal(kind), evidence=evidence())
    assert result.admitted is True
    assert result.reason == "PASS"
    assert result.metadata["reason_code"] == "QUEUE_GUARD_CLEAR"


def test_duplicate_preserves_positive_evidence_over_incomplete():
    result = DuplicateGuard().evaluate(signal(), evidence=evidence(
        queue_entries=(QueueEntry("submission:1", queue_submission_task_key("task:1")),),
        queue_evidence_complete=False))
    assert not result.admitted
    assert result.reason == "DUPLICATE_TASK_SUBMISSION_PENDING"
    assert result.metadata["duplicate_submission_ids"] == ("submission:1",)


@pytest.mark.parametrize("changes", [
    {"queue_evidence_complete": False}, {"turn_evidence_complete": False},
    {"queue_evidence_complete": None}, {"queue_evidence_complete": 1},
    {"queue_next_cursor": "next"}, {"turn_next_cursor": "next"},
    {"turns": (TurnEvidence("turn:1", "interrupted"),)},
    {"queue_entries": []}, {"queue_entries": (object(),)}, {"unknown": True},
])
def test_duplicate_reconciliation(changes):
    result = DuplicateGuard().evaluate(signal(), evidence=evidence(**changes))
    assert result.admitted is False
    assert result.reason == "RECONCILIATION_REQUIRED"


def test_duplicate_missing_and_worker_delegates_to_executor_admission():
    assert not DuplicateGuard().evaluate(signal()).admitted
    result = DuplicateGuard().evaluate(signal(target="WORKER_BATCH"), evidence=evidence())
    assert not result.admitted
    assert result.reason == "NOT_APPLICABLE"
    assert result.metadata == {"worker_dedup": "DELEGATED_TO_EXECUTOR_ADMISSION"}


@pytest.mark.parametrize("authorized", [True, False, None])
def test_worker_pipeline_requires_authority_after_delegated_duplicate(authorized):
    from a_conductor.orchestration_receiver import AdmittedContext, SignalReceiver
    item = signal(target="WORKER_BATCH", trigger="REFILL")
    receiver = SignalReceiver(queue_reader=None, turn_reader=None,
        binding_reader=lambda *_: pytest.fail("Parent reader must not run"),
        clock=lambda: pytest.fail("Parent clock must not run"))
    received = receiver.handle(item, admitted=AdmittedContext("source:1", "project:1", "task:1"))
    assert received.reason == "NOT_APPLICABLE"
    calls = []
    def checker(task, scope):
        calls.append((task, scope))
        return authorized
    result = GuardPipeline(checker).evaluate(item, utilization_facts=facts(),
        lane_class="review", scope=("src",))
    assert result.admitted is (authorized is True)
    assert calls == [("task:1", ("src",))]
    assert result.metadata["duplicate"] == {"worker_dedup": "DELEGATED_TO_EXECUTOR_ADMISSION"}


def test_receiver_page_diagnostics_are_not_passed_to_existing_guard():
    assert DuplicateGuard().evaluate(
        signal(), evidence=evidence(queue_pages=(), turn_pages=(), turn_binding=object())).admitted


@pytest.mark.parametrize("kind", ["LIFECYCLE", "UTILIZATION"])
def test_observation_guards_not_applicable(kind):
    item = signal(kind)
    for guard in (DuplicateGuard(), UtilizationGuard(), AuthorityGuard()):
        result = guard.evaluate(item)
        assert result.reason == "NOT_APPLICABLE"


def test_utilization_advisory_underutilization():
    result = UtilizationGuard().evaluate(signal(trigger="REFILL"), utilization_facts=facts())
    assert result.admitted is True
    assert result.metadata["a_faster_underutilized"] is True
    assert result.metadata["auto_refill_required"] is True


def test_explicit_utilization_not_applicable():
    assert UtilizationGuard().evaluate(signal()).reason == "NOT_APPLICABLE"


@pytest.mark.parametrize("changes", [
    {"occupied_mutable_lanes": 3}, {"occupied_review_lanes": 1},
    {"occupied_mutable_lanes": 3, "occupied_review_lanes": 1},
])
def test_capacity_exhausted_independently(changes):
    result = UtilizationGuard().evaluate(signal(trigger="REFILL"), utilization_facts=facts(**changes))
    assert not result.admitted
    assert result.reason == "CAPACITY_EXHAUSTED"


@pytest.mark.parametrize("lane,changes", [
    ("mutable", {"occupied_review_lanes": 1}),
    ("review", {"occupied_mutable_lanes": 3}),
])
def test_partial_capacity_selected_by_application_not_combined(lane, changes):
    assert UtilizationGuard().evaluate(signal(trigger="REFILL"), lane_class=lane,
                                       utilization_facts=facts(**changes)).admitted


@pytest.mark.parametrize("lane,changes", [
    ("mutable", {"occupied_mutable_lanes": 3}),
    ("review", {"occupied_review_lanes": 1}),
    ("mutable", {"ready_mutable_candidates": 0}),
    ("review", {"ready_review_candidates": 0}),
])
def test_other_class_capacity_or_ready_candidates_cannot_be_borrowed(lane, changes):
    assert not UtilizationGuard().evaluate(signal(trigger="REFILL"), lane_class=lane,
                                           utilization_facts=facts(**changes)).admitted


@pytest.mark.parametrize("lane", [True, 1, "unknown", [], "MUTABLE"])
def test_invalid_lane_class_fails_closed(lane):
    assert not UtilizationGuard().evaluate(signal(trigger="REFILL"), lane_class=lane,
                                           utilization_facts=facts()).admitted


@pytest.mark.parametrize("changes", [
    {"glm_quota_admission": quota} for quota in QuotaAdmission
    if quota is not QuotaAdmission.QUOTA_AVAILABLE
] + [{"glm_route_ready": False}, {"activation": AFasterActivation.NOT_INVOKED},
     {"activation": AFasterActivation.EXPLANATION_ONLY},
     {"ready_mutable_candidates": 0, "ready_review_candidates": 0}])
def test_refill_unknown_or_unavailable_not_admitted(changes):
    assert not UtilizationGuard().evaluate(
        signal(trigger="REFILL"), utilization_facts=facts(**changes)).admitted


@pytest.mark.parametrize("field,value", [
    ("activation", "A_FASTER_ACTIVE"), ("glm_quota_admission", "QUOTA_AVAILABLE"),
    ("glm_route_ready", 1), ("sol_direct_long_labor_active", None),
    ("occupied_mutable_lanes", True), ("occupied_review_lanes", -1),
    ("mutable_lanes_budget", 4), ("review_lanes_budget", 2),
    ("mutable_lanes_budget", 0), ("occupied_mutable_lanes", 4),
])
def test_utilization_revalidates_dataclass_fields(field, value):
    item = facts()
    object.__setattr__(item, field, value)
    result = UtilizationGuard().evaluate(signal(trigger="REFILL"), utilization_facts=item)
    assert result.admitted is False
    assert result.reason == "RECONCILIATION_REQUIRED"


def test_missing_utilization_fails_closed():
    assert not UtilizationGuard().evaluate(signal(trigger="REFILL")).admitted


@pytest.mark.parametrize("answer", [True, False, None, 1, "PASS", GuardResult(True, "PASS", {})])
def test_authority_exact_bool_only(answer):
    calls = []
    def checker(task_ref, scope):
        calls.append((task_ref, scope))
        return answer
    result = AuthorityGuard(checker).evaluate(signal(), scope=("src/a_conductor/x.py",))
    assert result.admitted is (answer is True)
    assert calls == [("task:1", ("src/a_conductor/x.py",))]
    if answer is not True:
        assert result.reason == "AUTHORITY_DENIED"


@pytest.mark.parametrize("scope", [(), [], ("",), ("a", "a"), ("a\nb",), (1,)])
def test_authority_missing_or_invalid_scope(scope):
    def forbidden(*args):
        pytest.fail("invalid scope must not reach authority")
    assert not AuthorityGuard(forbidden).evaluate(signal(), scope=scope).admitted


def test_missing_and_failing_authority():
    assert not AuthorityGuard().evaluate(signal(), scope=("src",)).admitted
    def unavailable(*args):
        raise RuntimeError("private authority details")
    result = AuthorityGuard(unavailable).evaluate(signal(), scope=("src",))
    assert not result.admitted
    assert "private" not in repr(result)


def test_pipeline_fixed_order(monkeypatch):
    calls = []
    for cls, label in ((DuplicateGuard, "duplicate"), (UtilizationGuard, "utilization"),
                       (AuthorityGuard, "authority")):
        def spy(self, *args, _label=label, **kwargs):
            calls.append(_label)
            return GuardResult(True, "PASS", {})
        monkeypatch.setattr(cls, "evaluate", spy)
    assert GuardPipeline().evaluate(signal(), scope=("src",)).admitted
    assert calls == ["duplicate", "utilization", "authority"]


@pytest.mark.parametrize("deny_at", [0, 1, 2])
def test_pipeline_short_circuit(monkeypatch, deny_at):
    calls = []
    for index, cls in enumerate((DuplicateGuard, UtilizationGuard, AuthorityGuard)):
        def spy(self, *args, _index=index, **kwargs):
            calls.append(_index)
            return GuardResult(_index != deny_at, "DENY" if _index == deny_at else "PASS", {})
        monkeypatch.setattr(cls, "evaluate", spy)
    assert not GuardPipeline().evaluate(signal()).admitted
    assert calls == list(range(deny_at + 1))


def test_not_applicable_skipped_but_authority_called(monkeypatch):
    monkeypatch.setattr(DuplicateGuard, "evaluate", lambda *a, **k: GuardResult(False, "NOT_APPLICABLE", {}))
    calls = []
    def authorize(task, scope):
        calls.append(task)
        return True
    assert GuardPipeline(authorize).evaluate(signal(), scope=("src",)).admitted
    assert calls == ["task:1"]


def test_forged_pass_does_not_bypass_authority(monkeypatch):
    monkeypatch.setattr(DuplicateGuard, "evaluate", lambda *a, **k: GuardResult(True, "PASS", {}))
    monkeypatch.setattr(UtilizationGuard, "evaluate", lambda *a, **k: GuardResult(True, "PASS", {}))
    assert GuardPipeline(lambda *a: False).evaluate(signal(), scope=("src",)).reason == "AUTHORITY_DENIED"


@pytest.mark.parametrize("kind", ["LIFECYCLE", "UTILIZATION"])
def test_observation_never_admits_effect(kind):
    assert GuardPipeline(lambda *a: True).evaluate(signal(kind)).admitted is False


def test_pipeline_happy_and_no_signal_or_evidence_rewrites():
    item, observed, usage = signal(trigger="REFILL"), evidence(), facts()
    before = deepcopy((item, observed, usage))
    result = GuardPipeline(lambda *a: True).evaluate(
        item, evidence=observed, utilization_facts=usage, scope=("src",))
    assert result.admitted is True
    assert result.metadata["utilization"]["a_faster_underutilized"] is True
    assert (item, observed, usage) == before


def test_signal_forgery_rejected_before_guards(monkeypatch):
    item = signal()
    item.payload["authority"] = "PASS"
    def forbidden(*args, **kwargs):
        pytest.fail("invalid DTO must not reach guards")
    monkeypatch.setattr(DuplicateGuard, "evaluate", forbidden)
    assert GuardPipeline(lambda *a: True).evaluate(item).reason == "SIGNAL_UNKNOWN_KEY"


@pytest.mark.parametrize("count", [512, 513])
def test_duplicate_evidence_bounds_are_not_truncated(count):
    rows = tuple(QueueEntry(f"submission:{i}", f"other-task:{i}") for i in range(count))
    result = DuplicateGuard().evaluate(signal(), evidence=evidence(queue_entries=rows))
    assert result.admitted is (count == 512)


def test_existing_guard_is_called_without_rewriting_evidence(monkeypatch):
    import a_conductor.orchestration_guards as guards
    original = guards.evaluate_bootstrap_guard
    observed = evidence(turns=(TurnEvidence("turn:1", "completed"),))
    calls = []
    def spy(task, **kwargs):
        calls.append((task, kwargs))
        return original(task, **kwargs)
    monkeypatch.setattr(guards, "evaluate_bootstrap_guard", spy)
    assert DuplicateGuard().evaluate(signal(), evidence=observed).admitted
    assert calls == [("task:1", observed)]
    assert calls[0][1]["turns"] is observed["turns"]


def test_existing_classifier_is_called_and_no_candidate_is_invented(monkeypatch):
    import a_conductor.orchestration_guards as guards
    original = guards.classify_utilization
    supplied = facts(ready_mutable_candidates=1, ready_review_candidates=0)
    calls = []
    def spy(usage):
        calls.append(usage)
        return original(usage)
    monkeypatch.setattr(guards, "classify_utilization", spy)
    result = UtilizationGuard().evaluate(signal(trigger="REFILL"),
                                         utilization_facts=supplied, lane_class="mutable")
    assert calls == [supplied]
    assert result.admitted
    assert result.metadata["fanout_target_mutable"] == 1
    assert result.metadata["fanout_target_review"] == 0
    assert "NO_INDEPENDENT_READY_WORK" in result.metadata["blockers"]


def test_authority_cannot_be_skipped_for_effect(monkeypatch):
    monkeypatch.setattr(AuthorityGuard, "evaluate", lambda *a, **k: GuardResult(True, "NOT_APPLICABLE", {}))
    assert GuardPipeline().evaluate(signal(), evidence=evidence()).reason == "AUTHORITY_DENIED"


@pytest.mark.parametrize("bad_result", [None, True, {"admitted": True},
    GuardResult(1, "PASS", {}), GuardResult(True, None, {}), GuardResult(True, "PASS", None)])
def test_malformed_guard_result_fails_closed(monkeypatch, bad_result):
    monkeypatch.setattr(DuplicateGuard, "evaluate", lambda *a, **k: bad_result)
    result = GuardPipeline(lambda *a: True).evaluate(signal())
    assert not result.admitted
    assert result.reason == "RECONCILIATION_REQUIRED"


def test_guard_exception_short_circuits_without_private_details(monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("private evidence details")
    def forbidden(*args):
        pytest.fail("authority must not run after guard failure")
    monkeypatch.setattr(DuplicateGuard, "evaluate", broken)
    result = GuardPipeline(forbidden).evaluate(signal())
    assert not result.admitted
    assert "private" not in repr(result)


def test_denial_does_not_modify_signal():
    item = signal()
    before = deepcopy(item)
    assert not GuardPipeline(lambda *a: False).evaluate(
        item, evidence=evidence(), scope=("src",)).admitted
    assert item == before


def test_sol_policy_blocker_cannot_be_turned_into_refill_admission():
    result = UtilizationGuard().evaluate(signal(trigger="REFILL"), utilization_facts=facts(
        sol_direct_long_labor_active=True, sol_direct_labor_glm_eligible=True))
    assert not result.admitted
