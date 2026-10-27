from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from a_conductor.codex_goal_api_adapter import QueueEntry, TurnEvidence
from a_conductor.orchestration import OrchestrationSignal
from a_conductor.orchestration_receiver import (
    AdmittedContext,
    EvidenceBinding,
    SignalReceiver,
)

NOW = datetime(2026, 10, 23, 19, 0, tzinfo=timezone.utc)


def signal():
    return OrchestrationSignal(
        "orch-signal.v1", "signal:1", "ENQUEUE", "2000-01-01T00:00:00Z",
        "operator", "project:1",
        {"target": "PARENT_QUEUE", "intent_ref": "intent:1", "trigger": "EXPLICIT",
         "parent_binding_ref": "binding:1"},
        "task:709", "wo:709", None,
    )


def admitted(**changes):
    return replace(AdmittedContext("operator", "project:1", "task:709"), **changes)


def binding(**changes):
    return replace(EvidenceBinding("task:709", "binding:1", "thread:1", "op:1", NOW),
                   **changes)


def page(items=(), cursor=None, **changes):
    return {"items": items if items is None else list(items),
            "nextCursor": cursor, "binding": binding(**changes)}


class Readers:
    def __init__(self, pages=None, turn_pages=None):
        self.pages = [page()] if pages is None else pages
        self.turn_pages = [page()] if turn_pages is None else turn_pages
        self.calls = []

    def list_queue_items(self, thread_id, cursor):
        self.calls.append(("queue", thread_id, cursor))
        return self.pages[len([c for c in self.calls if c[0] == "queue"]) - 1]

    def list_turns(self, thread_id, cursor):
        self.calls.append(("turns", thread_id, cursor))
        return self.turn_pages[len([c for c in self.calls if c[0] == "turns"]) - 1]


def receiver(readers, resolved=None, clock=lambda: NOW, **kwargs):
    return SignalReceiver(queue_reader=readers, turn_reader=readers,
                          binding_reader=lambda task, ref: binding() if resolved is None else resolved,
                          clock=clock, **kwargs)


def handle(readers, sig=None, ctx=None, **kwargs):
    return receiver(readers, **kwargs).handle(sig or signal(),
                                               admitted=ctx if ctx is not None else admitted())


def test_happy_path_collects_all_pages_and_turns():
    first, last = QueueEntry("submission:1", "client:1"), QueueEntry("submission:2", "client:2")
    turns = [TurnEvidence("turn:1", "completed")]
    readers = Readers([page([first], "cursor:2"), page([last])],
                      [page(turns, "turn-cursor:2"), page([TurnEvidence("turn:2", "interrupted")])])
    result = handle(readers)
    assert result.admitted and result.reason == "EVIDENCE_COLLECTED"
    assert result.operation_id == "op:1" and result.thread_id == "thread:1"
    assert result.evidence["queue_entries"] == (first, last)
    assert result.evidence["turns"] == (TurnEvidence("turn:1", "completed"),
                                        TurnEvidence("turn:2", "interrupted"))
    assert len(result.evidence["queue_pages"]) == 2
    assert len(result.evidence["turn_pages"]) == 2
    assert result.evidence["queue_evidence_complete"] is True
    assert result.evidence["turn_evidence_complete"] is True
    assert readers.calls[:2] == [("queue", "thread:1", None), ("queue", "thread:1", "cursor:2")]
    assert readers.calls[2:] == [("turns", "thread:1", None), ("turns", "thread:1", "turn-cursor:2")]


def test_empty_queue_and_turns_are_valid_complete_evidence():
    result = handle(Readers())
    assert result.admitted
    assert result.evidence["queue_entries"] == result.evidence["turns"] == ()


# ---- P1: separately admitted ingress binding precedes every authority read ----

@pytest.mark.parametrize("ctx", [admitted(source_ref="forged"),
                                 admitted(project_id="other-project"),
                                 admitted(task_ref="other-task"),
                                 admitted(task_ref=None)])
def test_forged_or_foreign_admitted_context_never_reads_authority(ctx):
    readers = Readers()
    result = handle(readers, ctx=ctx)
    assert not result.admitted and result.reason == "ADMITTED_CONTEXT_MISMATCH"
    assert readers.calls == []
    assert result.operation_id is result.thread_id is None


@pytest.mark.parametrize("ctx", ["operator", AdmittedContext("", "project:1", "task:709"),
                                 AdmittedContext("operator", {}, "task:709"),
                                 AdmittedContext("operator", "project:1", 7)])
def test_malformed_admitted_context_is_invalid_before_reads(ctx):
    readers = Readers()
    result = handle(readers, ctx=ctx)
    assert not result.admitted and result.reason == "ADMITTED_CONTEXT_INVALID"
    assert readers.calls == []


def test_absent_admitted_context_is_invalid_before_reads():
    readers = Readers()
    result = receiver(readers).handle(signal(), admitted=None)
    assert not result.admitted and result.reason == "ADMITTED_CONTEXT_INVALID"
    assert readers.calls == []


def test_matching_context_still_required_for_replay():
    replay = replace(signal(), kind="REPLAY", payload={**signal().payload,
                      "prior_submission_ref": "prior:1", "recovery_evidence_ref": "recover:1"})
    assert handle(Readers(), replay).admitted
    assert handle(Readers(), replay, ctx=admitted(task_ref=None)).reason == "ADMITTED_CONTEXT_MISMATCH"


# ---- bounded pagination for both listings ----

@pytest.mark.parametrize("bad", [None, {}, {"items": []}, {"nextCursor": None}])
def test_missing_or_broken_queue_page_fails_closed(bad):
    readers = Readers([bad])
    result = handle(readers)
    assert not result.admitted
    assert result.reason == ("EVIDENCE_MISSING" if bad is None else "RECONCILIATION_REQUIRED")
    assert not result.evidence["queue_evidence_complete"]
    assert not any(c[0] == "turns" for c in readers.calls)


@pytest.mark.parametrize("bad", [None, {}, {"items": []}, {"nextCursor": None}])
def test_missing_or_broken_turn_page_fails_closed(bad):
    readers = Readers(turn_pages=[bad])
    result = handle(readers)
    assert not result.admitted
    assert result.reason == ("EVIDENCE_MISSING" if bad is None else "RECONCILIATION_REQUIRED")
    assert not result.evidence["turn_evidence_complete"]
    assert result.evidence["queue_evidence_complete"] is False


@pytest.mark.parametrize("where", ["resolved", "queue", "turns"])
def test_stale_evidence_blocks(where):
    old = binding(observed_at=NOW - timedelta(seconds=61))
    readers = Readers([page()])
    resolved = old if where == "resolved" else binding()
    if where == "queue":
        readers.pages[0]["binding"] = old
    if where == "turns":
        readers.turn_pages[0]["binding"] = old
    result = handle(readers, resolved=resolved)
    assert not result.admitted and result.reason == "EVIDENCE_STALE"


def test_collection_expiry_is_checked_after_last_reader():
    times = iter([NOW, NOW + timedelta(seconds=61)])
    result = handle(Readers(), clock=lambda: next(times))
    assert not result.admitted and result.reason == "EVIDENCE_STALE"


@pytest.mark.parametrize("listing", ["queue", "turns"])
def test_exact_page_budget_completes(listing):
    pages = [page(cursor=f"cursor:{i}") for i in range(31)] + [page()]
    readers = Readers(pages, pages) if listing == "queue" else Readers([page()], pages)
    assert handle(readers).admitted


@pytest.mark.parametrize("listing", ["queue", "turns"])
def test_overflow_stops_without_reading_page_33_even_if_empty(listing):
    pages = [page(cursor=f"cursor:{i}") for i in range(33)]
    readers = Readers(pages, pages) if listing == "queue" else Readers([page()], pages)
    result = handle(readers)
    assert not result.admitted and result.reason == "EVIDENCE_OVERFLOW"
    assert len([c for c in readers.calls if c[0] == listing]) == 32


@pytest.mark.parametrize("cursor", ["", 1, [], True])
def test_invalid_queue_cursor_fails_closed(cursor):
    result = handle(Readers([page(cursor=cursor)]))
    assert not result.admitted and result.reason == "RECONCILIATION_REQUIRED"


@pytest.mark.parametrize("cursor", ["", 1, [], True])
def test_invalid_turn_cursor_fails_closed(cursor):
    result = handle(Readers(turn_pages=[page(cursor=cursor)]))
    assert not result.admitted and result.reason == "RECONCILIATION_REQUIRED"


@pytest.mark.parametrize("listing", ["queue", "turns"])
def test_cursor_cycle_requires_reconciliation(listing):
    cycle = [page(cursor="a"), page(cursor="b"), page(cursor="a")]
    readers = Readers(cycle, cycle) if listing == "queue" else Readers([page()], cycle)
    result = handle(readers)
    assert not result.admitted and result.reason == "RECONCILIATION_REQUIRED"


@pytest.mark.parametrize("field,value", [("thread_id", "other"), ("operation_id", "other"),
                                         ("task_ref", "other"), ("binding_ref", "other")])
@pytest.mark.parametrize("where", ["queue", "turns"])
def test_foreign_binding_cannot_be_used(field, value, where):
    readers = Readers()
    foreign = binding(**{field: value})
    if where == "queue":
        readers.pages[0]["binding"] = foreign
    else:
        readers.turn_pages[0]["binding"] = foreign
    result = handle(readers)
    assert not result.admitted and result.reason == "RECONCILIATION_REQUIRED"


@pytest.mark.parametrize("stamp", [None, NOW.replace(tzinfo=None), NOW + timedelta(seconds=1)])
def test_invalid_or_future_authority_time_is_not_fresh(stamp):
    result = handle(Readers(), resolved=binding(observed_at=stamp))
    assert not result.admitted and result.reason == "RECONCILIATION_REQUIRED"


def test_duplicate_queue_id_across_pages_keeps_partial_rows_but_never_admits():
    entry = QueueEntry("same", "client")
    result = handle(Readers([page([entry], "a"), page([entry])]))
    assert not result.admitted and result.reason == "RECONCILIATION_REQUIRED"
    assert result.evidence["queue_entries"] == (entry,)


def test_duplicate_turn_id_on_later_page_requires_reconciliation():
    turn = TurnEvidence("same-turn", "completed")
    result = handle(Readers(turn_pages=[page([turn], "t2"), page([turn])]))
    assert not result.admitted and result.reason == "RECONCILIATION_REQUIRED"
    assert result.evidence["turns"] == (turn,)


@pytest.mark.parametrize("count,admitted", [(512, True), (513, False)])
def test_entry_and_turn_bounds(count, admitted):
    entries = [QueueEntry(f"q:{i}", f"c:{i}") for i in range(count)]
    result = handle(Readers([page(entries)]))
    assert result.admitted is admitted
    if not admitted:
        assert result.reason == "EVIDENCE_OVERFLOW"
    turns = [TurnEvidence(f"t:{i}", "completed") for i in range(count)]
    result = handle(Readers(turn_pages=[page(turns)]))
    assert result.admitted is admitted
    if not admitted:
        assert result.reason == "EVIDENCE_OVERFLOW"


@pytest.mark.parametrize("turns", [None, [{}], [TurnEvidence("t", "unknown")],
                                  [TurnEvidence("t", "completed"), TurnEvidence("t", "failed")]])
def test_missing_malformed_or_duplicate_turns_fail_closed(turns):
    readers = Readers(turn_pages=[page(turns)])
    assert not handle(readers).admitted


@pytest.mark.parametrize("stage", ["list_queue_items", "list_turns"])
def test_reader_exception_is_code_only_and_not_retried(stage):
    readers = Readers()
    calls = []

    def fail(*args):
        calls.append(args)
        raise RuntimeError("private transport detail")

    setattr(readers, stage, fail)
    result = handle(readers)
    assert not result.admitted and result.reason == "EVIDENCE_MISSING"
    assert "private" not in repr(result)
    assert len(calls) == 1


def test_binding_resolver_missing_or_foreign_prevents_any_listing():
    for resolved in [False, {}, binding(task_ref="other"), binding(binding_ref="other")]:
        readers = Readers()
        result = handle(readers, resolved=resolved)
        assert not result.admitted and not readers.calls
        assert result.operation_id is result.thread_id is None


def test_unsupported_target_and_invalid_signal_do_not_read_authority():
    readers = Readers()
    worker = replace(signal(), payload={"target": "WORKER_BATCH", "intent_ref": "i",
                                        "ready_plan_ref": "p", "task_map_ref": "m", "trigger": "EXPLICIT"})
    assert handle(readers, worker).reason == "NOT_APPLICABLE"
    assert handle(readers, replace(signal(), source_ref="")).reason == "SIGNAL_VALUE_INVALID"
    assert readers.calls == []


@pytest.mark.parametrize("budget", [0, 33, True, "32"])
def test_page_budget_cannot_disable_hard_limit(budget):
    with pytest.raises(ValueError, match="RECEIVER_CONFIGURATION_INVALID"):
        receiver(Readers(), max_pages=budget)


def test_pages_observed_during_collection_can_be_newer_than_start():
    readers = Readers([page(observed_at=NOW + timedelta(seconds=1))],
                      [page(observed_at=NOW + timedelta(seconds=2))])
    times = iter([NOW, NOW + timedelta(seconds=3)])
    assert handle(readers, clock=lambda: next(times)).admitted


def test_freshness_boundary_and_backward_clock():
    times = iter([NOW, NOW + timedelta(seconds=60)])
    assert handle(Readers(), clock=lambda: next(times)).admitted
    times = iter([NOW, NOW - timedelta(seconds=1)])
    assert handle(Readers(), clock=lambda: next(times)).reason == "RECONCILIATION_REQUIRED"


@pytest.mark.parametrize("items", [None, (), [{}], [QueueEntry("", "client")],
                                  [QueueEntry("q", "")], [QueueEntry("q", "client\n")]])
def test_malformed_queue_records_are_not_complete(items):
    value = page()
    value["items"] = items
    result = handle(Readers([value]))
    assert not result.admitted and result.reason == "RECONCILIATION_REQUIRED"


def test_retained_queue_and_turn_pages_do_not_alias_reader_containers():
    readers = Readers([page([QueueEntry("q", "c")])], [page([TurnEvidence("t", "completed")])])
    result = handle(readers)
    readers.pages[0]["items"].clear()
    readers.pages[0]["nextCursor"] = "changed"
    readers.turn_pages[0]["items"].clear()
    assert result.evidence["queue_pages"][0]["items"] == (QueueEntry("q", "c"),)
    assert result.evidence["queue_pages"][0]["nextCursor"] is None
    assert result.evidence["turn_pages"][0]["items"] == (TurnEvidence("t", "completed"),)


def test_binding_reader_exception_is_bounded_and_never_lists():
    readers = Readers()

    def fail(*args):
        raise RuntimeError("private binding failure")

    result = SignalReceiver(queue_reader=readers, turn_reader=readers,
                            binding_reader=fail, clock=lambda: NOW).handle(signal(), admitted=admitted())
    assert not result.admitted and result.reason == "EVIDENCE_MISSING"
    assert readers.calls == []
