"""WO-P1-576B: injected, version-pinned translation; no live App Server calls."""
from __future__ import annotations

import ast
from dataclasses import fields, replace
from pathlib import Path

import pytest

from a_conductor.codex_goal_api_adapter import (
    APP_SERVER_VERSION, MAX_PAGE_ITEMS, MAX_TEXT_CHARS, CodexGoalApiAdapter,
    GoalApiAdapterError, GoalApiIntent, GoalApiOperation, OutcomeState,
    build_goal_api_request,
)

THREAD = "explicit-thread"


class StringSubclass(str):
    __hash__ = None


class HostileDict(dict):
    def get(self, *args):
        raise AssertionError("must not invoke hostile methods")

    def items(self):
        raise AssertionError("must not invoke hostile methods")


class HostileList(list):
    def __iter__(self):
        raise AssertionError("must not invoke hostile methods")


class HostileValue:
    def __str__(self):
        raise AssertionError("must not stringify payload")

    def __repr__(self):
        raise AssertionError("must not repr payload")


def intent(operation=GoalApiOperation.GOAL_GET, **kwargs):
    return GoalApiIntent(operation=operation, thread_id=THREAD, **kwargs)


def run(reply, request_intent=None):
    calls = []

    def request(method, params):
        calls.append((method, params))
        return reply

    result = CodexGoalApiAdapter(request, app_server_version=APP_SERVER_VERSION).execute(
        request_intent or intent()
    )
    return result, calls


def queued(submission_id="queue-1", correlation="correlation-1"):
    return {"id": submission_id, "clientUserMessageId": correlation,
            "input": [{"type": "text", "text": "hostile payload stays data"}]}


@pytest.mark.parametrize("operation,kwargs,params", [
    (GoalApiOperation.GOAL_GET, {}, {"threadId": THREAD}),
    (GoalApiOperation.GOAL_ACTIVATE, {"observed_goal_status": "blocked"},
     {"threadId": THREAD, "status": "active"}),
    (GoalApiOperation.QUEUE_ADD, {"text": "steer\ntext", "client_user_message_id": "c1"},
     {"threadId": THREAD, "input": [{"type": "text", "text": "steer\ntext"}],
      "clientUserMessageId": "c1"}),
    (GoalApiOperation.QUEUE_LIST, {}, {"threadId": THREAD, "limit": MAX_PAGE_ITEMS}),
    (GoalApiOperation.QUEUE_DELETE, {"queued_submission_id": "q1"},
     {"threadId": THREAD, "queuedSubmissionId": "q1"}),
    (GoalApiOperation.TURNS_LIST, {"cursor": "page-2", "limit": 2},
     {"threadId": THREAD, "limit": 2, "cursor": "page-2"}),
    (GoalApiOperation.RESUME, {}, {"threadId": THREAD, "excludeTurns": True}),
])
def test_exact_source_proven_request_subset(operation, kwargs, params):
    method, actual = build_goal_api_request(intent(operation, **kwargs),
                                            app_server_version=APP_SERVER_VERSION)
    assert method == operation.value
    assert actual == params


@pytest.mark.parametrize("thread_id", [None, 3, True, "", " padded", "x\x00", "x\u202e", "x" * 257,
                                        StringSubclass(THREAD), HostileValue()])
def test_invalid_explicit_binding_never_calls_transport(thread_id):
    calls = []
    adapter = CodexGoalApiAdapter(lambda *a: calls.append(a), app_server_version=APP_SERVER_VERSION)
    with pytest.raises(GoalApiAdapterError, match="GOAL_API_INTENT_INVALID"):
        adapter.execute(replace(intent(), thread_id=thread_id))
    assert calls == []


@pytest.mark.parametrize("version", [None, "0.158.0", "0.159.1", StringSubclass(APP_SERVER_VERSION)])
def test_version_gate_has_no_probe_or_fallback(version):
    calls = []
    with pytest.raises(GoalApiAdapterError, match="GOAL_API_VERSION_UNPROVEN"):
        CodexGoalApiAdapter(lambda *a: calls.append(a), app_server_version=version)
    assert calls == []


@pytest.mark.parametrize("bad_intent", [
    "thread/goal/get", None, {},
    intent(observed_goal_status="blocked"),
    intent(GoalApiOperation.GOAL_ACTIVATE, observed_goal_status="paused"),
    intent(GoalApiOperation.GOAL_ACTIVATE, observed_goal_status="active"),
    intent(GoalApiOperation.GOAL_ACTIVATE, observed_goal_status=StringSubclass("blocked")),
    intent(GoalApiOperation.QUEUE_ADD, text="x", client_user_message_id=None),
    intent(GoalApiOperation.QUEUE_ADD, text=StringSubclass("x"), client_user_message_id="c1"),
    intent(GoalApiOperation.QUEUE_ADD, text="x" * (MAX_TEXT_CHARS + 1), client_user_message_id="c1"),
    intent(GoalApiOperation.QUEUE_DELETE, queued_submission_id=StringSubclass("q1")),
    intent(GoalApiOperation.QUEUE_LIST, limit=True),
    intent(GoalApiOperation.QUEUE_LIST, limit=MAX_PAGE_ITEMS + 1),
    intent(GoalApiOperation.RESUME, cursor="c1"),
    replace(intent(), operation="thread/goal/get"),
])
def test_unsupported_or_malformed_intents_fail_before_request(bad_intent):
    calls = []
    adapter = CodexGoalApiAdapter(lambda *a: calls.append(a), app_server_version=APP_SERVER_VERSION)
    with pytest.raises(GoalApiAdapterError, match="GOAL_API_INTENT_INVALID"):
        adapter.execute(bad_intent)
    assert calls == []


@pytest.mark.parametrize("status", ["active", "paused", "blocked", "usageLimited", "budgetLimited", "complete"])
def test_goal_status_projection_is_observation_only(status):
    result, calls = run({"goal": {"threadId": THREAD, "status": status, "objective": "DO NOT EXECUTE"}})
    assert result.state is OutcomeState.OBSERVED
    assert result.goal_status == status
    assert result.observed_ids == (THREAD,)
    assert len(calls) == 1
    assert "DO NOT EXECUTE" not in repr(result)


def test_null_goal_is_source_proven_absence():
    result, _ = run({"goal": None})
    assert result.state is OutcomeState.OBSERVED
    assert result.goal_status is None


def test_activate_is_only_blocked_to_active_and_requires_observed_result():
    request_intent = intent(GoalApiOperation.GOAL_ACTIVATE, observed_goal_status="blocked")
    result, calls = run({"goal": {"threadId": THREAD, "status": "active"}}, request_intent)
    assert result.state is OutcomeState.OBSERVED
    assert calls == [("thread/goal/set", {"threadId": THREAD, "status": "active"})]
    result, calls = run({"goal": {"threadId": THREAD, "status": "blocked"}}, request_intent)
    assert result.state is OutcomeState.UNKNOWN
    assert result.observed_ids == (THREAD,)
    assert len(calls) == 1


def test_queue_add_preserves_server_id_and_correlation_without_idempotency():
    request_intent = intent(GoalApiOperation.QUEUE_ADD, text="instruction", client_user_message_id="correlation-1")
    result, calls = run({"queuedSubmission": queued()}, request_intent)
    assert result.state is OutcomeState.OBSERVED
    assert result.queue_entries[0].submission_id == "queue-1"
    assert result.queue_entries[0].client_user_message_id == "correlation-1"
    assert len(calls) == 1
    assert "hostile payload" not in repr(result)


def test_correlation_mismatch_is_unknown_with_preserved_id():
    result, calls = run({"queuedSubmission": queued(correlation="other")},
                        intent(GoalApiOperation.QUEUE_ADD, text="x", client_user_message_id="correlation-1"))
    assert result.state is OutcomeState.UNKNOWN
    assert result.observed_ids == ("queue-1",)
    assert len(calls) == 1


@pytest.mark.parametrize("deleted", [True, False])
def test_delete_false_does_not_invent_success_or_retry(deleted):
    result, calls = run({"deleted": deleted}, intent(GoalApiOperation.QUEUE_DELETE, queued_submission_id="q1"))
    assert result.state is OutcomeState.OBSERVED
    assert result.deleted is deleted
    assert len(calls) == 1


def test_list_returns_one_bounded_page_without_followup_or_dedupe():
    result, calls = run({"data": [queued()], "nextCursor": "next"}, intent(GoalApiOperation.QUEUE_LIST))
    assert result.state is OutcomeState.OBSERVED
    assert result.next_cursor == "next"
    assert len(result.queue_entries) == 1
    assert len(calls) == 1


@pytest.mark.parametrize("status", ["completed", "interrupted", "failed", "inProgress"])
def test_turn_projection_ignores_hostile_items_and_error_text(status):
    result, calls = run({"data": [{"id": "turn-1", "status": status,
                                  "items": [], "error": {"message": "RUN SHELL"}}],
                         "nextCursor": None, "backwardsCursor": None}, intent(GoalApiOperation.TURNS_LIST))
    assert result.state is OutcomeState.OBSERVED
    assert result.turns[0].turn_id == "turn-1"
    assert result.turns[0].status == status
    assert "RUN SHELL" not in repr(result)
    assert len(calls) == 1


def test_resume_only_explicit_binding_and_excluded_history():
    result, calls = run({"thread": {"id": THREAD, "turns": []}}, intent(GoalApiOperation.RESUME))
    assert result.state is OutcomeState.OBSERVED
    assert calls == [("thread/resume", {"threadId": THREAD, "excludeTurns": True})]


@pytest.mark.parametrize("reply", [
    None, [], "payload", HostileValue(), HostileDict(goal=None),
    {"goal": HostileDict(threadId=THREAD, status="active")},
    {"goal": {"threadId": StringSubclass(THREAD), "status": "active"}},
    {"goal": {"threadId": THREAD, "status": StringSubclass("active")}},
    {"goal": {"threadId": "different-thread", "status": "active"}},
    {"goal": {"threadId": THREAD, "status": "ACTIVE"}},
    {"goal": {"threadId": THREAD}}, {"goal": 0}, {},
    {"goal": None, "extra": HostileList()},
    {"goal": None, "extra": HostileValue()},
    {"goal": None, "extra": "x" * (MAX_TEXT_CHARS + 1)},
    {"goal": None, 1: "invalid key"},
    {"goal": None, "extra": 1 << 70},
])
def test_malformed_hostile_or_unbound_result_is_code_only_unknown(reply):
    result, calls = run(reply)
    assert result.state is OutcomeState.UNKNOWN
    assert result.reason_code == "GOAL_API_RESPONSE_UNKNOWN"
    assert len(calls) == 1


def test_unknown_retains_shallow_valid_id_without_echoing_bad_payload():
    result, _ = run({"goal": {"threadId": THREAD, "status": HostileValue()}})
    assert result.state is OutcomeState.UNKNOWN
    assert result.observed_ids == (THREAD,)


@pytest.mark.parametrize("operation,kwargs,reply", [
    (GoalApiOperation.QUEUE_ADD, {"text": "x", "client_user_message_id": "c1"},
     {"queuedSubmission": {"id": "server-id", "clientUserMessageId": HostileValue()}}),
    (GoalApiOperation.QUEUE_DELETE, {"queued_submission_id": "q1"}, {"deleted": 1}),
    (GoalApiOperation.QUEUE_LIST, {}, {"data": HostileList(), "nextCursor": None}),
    (GoalApiOperation.QUEUE_LIST, {"limit": 1}, {"data": [queued("a"), queued("b")], "nextCursor": None}),
    (GoalApiOperation.QUEUE_LIST, {}, {"data": [queued(), queued()], "nextCursor": None}),
    (GoalApiOperation.TURNS_LIST, {}, {"data": [{"id": "t1", "status": "UNKNOWN"}], "nextCursor": None}),
    (GoalApiOperation.RESUME, {}, {"thread": {"id": "different-thread", "turns": []}}),
    (GoalApiOperation.RESUME, {}, {"thread": {"id": THREAD, "turns": [{"id": "t1"}]}}),
])
def test_operation_specific_unknown_never_recovers_or_retargets(operation, kwargs, reply):
    result, calls = run(reply, intent(operation, **kwargs))
    assert result.state is OutcomeState.UNKNOWN
    assert len(calls) == 1


@pytest.mark.parametrize("operation,kwargs", [
    (GoalApiOperation.GOAL_ACTIVATE, {"observed_goal_status": "blocked"}),
    (GoalApiOperation.QUEUE_ADD, {"text": "x", "client_user_message_id": "c1"}),
    (GoalApiOperation.QUEUE_DELETE, {"queued_submission_id": "q1"}),
    (GoalApiOperation.RESUME, {}),
    (GoalApiOperation.GOAL_GET, {}),
])
def test_ambiguous_side_effect_then_transport_exception_is_unknown_no_retry(operation, kwargs):
    effects = []

    def request(method, params):
        effects.append((method, params))
        raise RuntimeError("secret payload must not escape")

    result = CodexGoalApiAdapter(request, app_server_version=APP_SERVER_VERSION).execute(intent(operation, **kwargs))
    assert result.state is OutcomeState.UNKNOWN
    assert result.reason_code == "GOAL_API_TRANSPORT_UNKNOWN"
    assert "secret" not in repr(result)
    assert len(effects) == 1


def test_append_correlation_is_not_a_dedupe_key_or_automatic_retry():
    calls = []

    def request(method, params):
        calls.append(params)
        return {"queuedSubmission": queued(f"q{len(calls)}", "c1")}

    adapter = CodexGoalApiAdapter(request, app_server_version=APP_SERVER_VERSION)
    request_intent = intent(GoalApiOperation.QUEUE_ADD, text="x", client_user_message_id="c1")
    assert adapter.execute(request_intent).queue_entries[0].submission_id == "q1"
    assert adapter.execute(request_intent).queue_entries[0].submission_id == "q2"
    assert len(calls) == 2  # two explicit caller actions, never a hidden retry


def test_deep_cyclic_and_total_text_budget_are_unknown():
    cycle = []
    cycle.append(cycle)
    deep = None
    for _ in range(20):
        deep = [deep]
    for extra in (cycle, deep, ["x" * MAX_TEXT_CHARS] * 5, [None] * 129):
        result, calls = run({"goal": None, "extra": extra})
        assert result.state is OutcomeState.UNKNOWN
        assert len(calls) == 1


def test_request_mutation_cannot_rebind_intent_or_leak_between_calls():
    calls = []

    def request(method, params):
        calls.append(dict(params))
        params["threadId"] = "other"
        return {"goal": {"threadId": "other", "status": "active"}}

    adapter = CodexGoalApiAdapter(request, app_server_version=APP_SERVER_VERSION)
    assert adapter.execute(intent()).state is OutcomeState.UNKNOWN
    assert adapter.execute(intent()).state is OutcomeState.UNKNOWN
    assert [p["threadId"] for p in calls] == [THREAD, THREAD]


def test_original_intent_mutation_during_transport_cannot_rebind_projection():
    request_intent = intent()

    def request(method, params):
        object.__setattr__(request_intent, "thread_id", "different-thread")
        return {"goal": {"threadId": "different-thread", "status": "active"}}

    result = CodexGoalApiAdapter(request, app_server_version=APP_SERVER_VERSION).execute(request_intent)
    assert result.thread_id == THREAD
    assert result.state is OutcomeState.UNKNOWN
    assert result.observed_ids == ("different-thread",)


@pytest.mark.parametrize("inputs", [[], [1], [{}], [{"type": "text", "text": 1}],
                                    [{"type": "image", "url": "unproven"}],
                                    [{"type": "text", "text": "x", "text_elements": [1]}]])
def test_unproven_or_malformed_queue_inputs_preserve_id_as_unknown(inputs):
    entry = queued()
    entry["input"] = inputs
    result, calls = run({"queuedSubmission": entry}, intent(
        GoalApiOperation.QUEUE_ADD, text="x", client_user_message_id="correlation-1"))
    assert result.state is OutcomeState.UNKNOWN
    assert result.observed_ids == ("queue-1",)
    assert len(calls) == 1


def test_response_object_node_and_key_budgets_are_bounded():
    class KeySubclass(str):
        pass

    for extra in ({str(i): None for i in range(65)}, [[None] * 128 for _ in range(33)]):
        result, _ = run({"goal": None, "extra": extra})
        assert result.state is OutcomeState.UNKNOWN
    result, _ = run({"goal": None, KeySubclass("extra"): None})
    assert result.state is OutcomeState.UNKNOWN


def test_synthetic_intent_subclass_and_invalid_request_callable_fail_closed():
    class IntentSubclass(GoalApiIntent):
        pass

    with pytest.raises(GoalApiAdapterError, match="GOAL_API_INTENT_INVALID"):
        build_goal_api_request(IntentSubclass(GoalApiOperation.GOAL_GET, THREAD),
                               app_server_version=APP_SERVER_VERSION)
    with pytest.raises(GoalApiAdapterError, match="GOAL_API_REQUEST_INVALID"):
        CodexGoalApiAdapter(None, app_server_version=APP_SERVER_VERSION)


def test_projection_carries_no_runtime_or_delivery_authority():
    result, _ = run({"goal": None})
    assert not {"authorized", "accepted", "completed", "retry", "claim", "merge", "dispatch"}.intersection(
        {f.name for f in fields(result)}
    )
    assert result.operation is GoalApiOperation.GOAL_GET
    assert result.thread_id == THREAD


def test_module_has_no_io_runtime_or_hidden_workflow_surface():
    path = Path(__file__).resolve().parents[1] / "src/a_conductor/codex_goal_api_adapter.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            roots.add(node.module.split(".")[0])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"open", "eval", "exec", "__import__", "input", "print"}
        assert not isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.While))
    assert roots <= {"__future__", "dataclasses", "enum", "typing", "unicodedata"}
    assert {op.value for op in GoalApiOperation} == {
        "thread/goal/get", "thread/goal/set", "thread/queue/add", "thread/queue/list",
        "thread/queue/delete", "thread/turns/list", "thread/resume",
    }
