"""Bounded read-only evidence collection; admission is not effect authority.

Ports are supplied by an authenticated composition root. A turn reader must
attest the exact complete list it just returned via evidence_binding, including
empty lists. These are local ports, not new App Server wire fields or adapters.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Protocol

from .codex_goal_api_adapter import QueueEntry, TurnEvidence
from .orchestration import OrchestrationError, OrchestrationSignal, encode_signal


@dataclass(frozen=True, slots=True)
class EvidenceBinding:
    """Authority-reader provenance, never constructed from signal assertions."""

    task_ref: str
    binding_ref: str
    thread_id: str
    operation_id: str
    observed_at: datetime


class QueueReader(Protocol):
    def list_queue_items(self, thread_id: str, cursor: str | None) -> dict:
        """Return items: list[QueueEntry], explicit nextCursor, binding."""
        ...


class TurnReader(Protocol):
    def list_turns(self, thread_id: str) -> list[TurnEvidence]:
        """Return the complete listing, not a single truncated adapter page."""
        ...

    def evidence_binding(self, thread_id: str) -> EvidenceBinding:
        """Attest identity and observation time of the exact returned listing."""
        ...


@dataclass(frozen=True, slots=True)
class ReceiverResult:
    admitted: bool
    evidence: dict
    reason: str
    operation_id: str | None
    thread_id: str | None


def _identifier(value: object) -> bool:
    return (type(value) is str and 1 <= len(value) <= 256
            and all(33 <= ord(char) <= 126 for char in value))


def _instant(value: object) -> bool:
    try:
        return type(value) is datetime and value.tzinfo is not None and value.utcoffset() is not None
    except Exception:
        return False


class SignalReceiver:
    """One bounded collection, no retries, writes, guard calls or activation.

    operation_id identifies the authority-bound collection, not a transport
    method. Queue/turn adapters own request-operation validation before they
    supply this provenance. All listings must share this collection identity.
    """

    def __init__(self, *, queue_reader: QueueReader, turn_reader: TurnReader,
                 binding_reader: Callable[[str, str], EvidenceBinding],
                 clock: Callable[[], datetime], max_pages: int = 32,
                 max_age: timedelta = timedelta(seconds=60)):
        if (type(max_pages) is not int or not 1 <= max_pages <= 32
                or type(max_age) is not timedelta or max_age <= timedelta(0)
                or not callable(binding_reader) or not callable(clock)):
            raise ValueError("RECEIVER_CONFIGURATION_INVALID")
        self._queue_reader = queue_reader
        self._turn_reader = turn_reader
        self._binding_reader = binding_reader
        self._clock = clock
        self._max_pages = max_pages
        self._max_age = max_age

    def handle(self, signal: OrchestrationSignal) -> ReceiverResult:
        evidence = {"queue_pages": (), "queue_entries": (), "turns": (),
                    "queue_evidence_complete": False, "turn_evidence_complete": False,
                    "queue_next_cursor": None, "turn_next_cursor": None}
        bound = None

        def result(reason):
            return ReceiverResult(reason == "EVIDENCE_COLLECTED", evidence, reason,
                                  bound.operation_id if bound else None,
                                  bound.thread_id if bound else None)

        try:
            encode_signal(signal)
        except OrchestrationError as exc:
            return result(exc.code)
        if (signal.signal_type not in ("enqueue", "replay")
                or signal.payload["target"] != "PARENT_QUEUE"):
            return result("NOT_APPLICABLE")
        # Freeze the locator before injected readers can mutate caller dictionaries.
        task_ref, binding_ref = signal.task_ref, signal.payload["parent_binding_ref"]
        try:
            candidate = self._binding_reader(task_ref, binding_ref)
            now = self._clock()
        except Exception:
            return result("EVIDENCE_MISSING")

        def check_binding(value, at, *, freshness=True):
            if value is None:
                return "EVIDENCE_MISSING"
            if (type(value) is not EvidenceBinding or not _instant(at)
                    or not _instant(value.observed_at)
                    or not all(_identifier(getattr(value, name)) for name in (
                        "task_ref", "binding_ref", "thread_id", "operation_id"))
                    or value.task_ref != task_ref or value.binding_ref != binding_ref):
                return "RECONCILIATION_REQUIRED"
            if bound is not None and any(getattr(value, name) != getattr(bound, name)
                                         for name in ("thread_id", "operation_id")):
                return "RECONCILIATION_REQUIRED"
            if not freshness:
                return None
            try:
                age = at - value.observed_at
            except Exception:
                return "RECONCILIATION_REQUIRED"
            if age < timedelta(0):
                return "RECONCILIATION_REQUIRED"
            return "EVIDENCE_STALE" if age > self._max_age else None

        reason = check_binding(candidate, now)
        if reason:
            return result(reason)
        bound = candidate
        bindings = [bound]
        cursor = None
        cursors = set()
        ids = set()
        for _ in range(self._max_pages):
            try:
                page = self._queue_reader.list_queue_items(bound.thread_id, cursor)
            except Exception:
                return result("EVIDENCE_MISSING")
            if page is None:
                return result("EVIDENCE_MISSING")
            if (type(page) is not dict or len(page) != 3
                    or any(type(key) is not str for key in page)
                    or set(page) != {"items", "nextCursor", "binding"}):
                return result("RECONCILIATION_REQUIRED")
            items, next_cursor, page_binding = page["items"], page["nextCursor"], page["binding"]
            # Later pages may be newer than collection start. Check identity
            # now and freshness against the completion clock, never start time.
            reason = check_binding(page_binding, now, freshness=False)
            if reason:
                return result(reason)
            if type(items) is not list:
                return result("RECONCILIATION_REQUIRED")
            if len(items) + len(evidence["queue_entries"]) > 512:
                return result("EVIDENCE_OVERFLOW")
            if next_cursor is not None and (not _identifier(next_cursor) or next_cursor in cursors):
                return result("RECONCILIATION_REQUIRED")
            page_ids = set()
            for entry in items:
                if (type(entry) is not QueueEntry or not _identifier(entry.submission_id)
                        or not _identifier(entry.client_user_message_id)
                        or entry.submission_id in ids or entry.submission_id in page_ids):
                    return result("RECONCILIATION_REQUIRED")
                page_ids.add(entry.submission_id)
            ids.update(page_ids)
            bindings.append(page_binding)
            # Own the retained containers, not the reader's mutable page/list.
            evidence["queue_pages"] += ({"items": tuple(items), "nextCursor": next_cursor,
                                         "binding": page_binding},)
            evidence["queue_entries"] += tuple(items)
            evidence["queue_next_cursor"] = next_cursor
            if next_cursor is None:
                break
            cursors.add(next_cursor)
            cursor = next_cursor
        else:
            return result("EVIDENCE_OVERFLOW")
        try:
            turns = self._turn_reader.list_turns(bound.thread_id)
            turn_binding = self._turn_reader.evidence_binding(bound.thread_id)
            finished_at = self._clock()
        except Exception:
            return result("EVIDENCE_MISSING")
        if turns is None:
            return result("EVIDENCE_MISSING")
        if type(turns) is not list:
            return result("RECONCILIATION_REQUIRED")
        if len(turns) > 512:
            return result("EVIDENCE_OVERFLOW")
        ids = set()
        for turn in turns:
            if (type(turn) is not TurnEvidence or not _identifier(turn.turn_id)
                    or type(turn.status) is not str
                    or turn.status not in ("completed", "interrupted", "failed", "inProgress")
                    or turn.turn_id in ids):
                return result("RECONCILIATION_REQUIRED")
            ids.add(turn.turn_id)
        for observed in (*bindings, turn_binding):
            reason = check_binding(observed, finished_at)
            if reason:
                return result(reason)
        if finished_at < now:
            return result("RECONCILIATION_REQUIRED")
        evidence["turns"] = tuple(turns)
        evidence["turn_binding"] = turn_binding
        evidence["queue_evidence_complete"] = True
        evidence["turn_evidence_complete"] = True
        return result("EVIDENCE_COLLECTED")
