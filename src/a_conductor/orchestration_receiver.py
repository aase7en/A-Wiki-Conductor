"""Bounded read-only evidence collection; admission is not effect authority.

Ports are supplied by an authenticated composition root. Queue and turn
readers return one cursor-bound page at a time; the receiver follows cursors
until an explicit terminal None with per-page identity checks. Incomplete or
ambiguous pagination is never represented as complete evidence.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Protocol

from .codex_goal_api_adapter import QueueEntry, TurnEvidence
from .orchestration import OrchestrationError, OrchestrationSignal, encode_signal


@dataclass(frozen=True, slots=True)
class AdmittedContext:
    """Separately authenticated ingress identity from the composition root.

    A claimed source in signal data is not authentication; this value comes
    from the trusted operator/launcher/runtime boundary and is compared
    against the signal before any authority read.
    """

    source_ref: str
    project_id: str
    task_ref: str | None = None


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
    def list_turns(self, thread_id: str, cursor: str | None) -> dict:
        """Return one page: items: list[TurnEvidence], explicit nextCursor, binding."""
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

    def _admitted(self, signal: OrchestrationSignal, admitted: AdmittedContext) -> str | None:
        if (type(admitted) is not AdmittedContext
                or not _identifier(admitted.source_ref)
                or not _identifier(admitted.project_id)
                or (admitted.task_ref is not None and not _identifier(admitted.task_ref))):
            return "ADMITTED_CONTEXT_INVALID"
        if (signal.source_ref != admitted.source_ref
                or signal.project_id != admitted.project_id):
            return "ADMITTED_CONTEXT_MISMATCH"
        if signal.kind in ("ENQUEUE", "REPLAY"):
            if admitted.task_ref is None or signal.task_ref != admitted.task_ref:
                return "ADMITTED_CONTEXT_MISMATCH"
        elif admitted.task_ref is not None and signal.task_ref != admitted.task_ref:
            return "ADMITTED_CONTEXT_MISMATCH"
        return None

    def handle(self, signal: OrchestrationSignal, *,
               admitted: AdmittedContext) -> ReceiverResult:
        evidence = {"queue_pages": (), "queue_entries": (), "turn_pages": (),
                    "turns": (), "queue_evidence_complete": False,
                    "turn_evidence_complete": False, "queue_next_cursor": None,
                    "turn_next_cursor": None}
        bound = None

        def result(reason):
            return ReceiverResult(reason == "EVIDENCE_COLLECTED", evidence, reason,
                                  bound.operation_id if bound else None,
                                  bound.thread_id if bound else None)

        try:
            encode_signal(signal)
        except OrchestrationError as exc:
            return result(exc.code)
        # Trusted ingress binding precedes every authority read.
        reason = self._admitted(signal, admitted)
        if reason:
            return result(reason)
        if (signal.kind not in ("ENQUEUE", "REPLAY")
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

        def listing(reader, page_key, entry_key, cursor_key, validate_entry,
                    record_limit):
            """Follow cursors until an explicit terminal None, bounded by pages."""
            cursor = None
            cursors = set()
            ids = set()
            total = 0
            for _ in range(self._max_pages):
                try:
                    page = reader(bound.thread_id, cursor)
                except Exception:
                    return "EVIDENCE_MISSING", None
                if page is None:
                    return "EVIDENCE_MISSING", None
                if (type(page) is not dict or len(page) != 3
                        or any(type(key) is not str for key in page)
                        or set(page) != {"items", "nextCursor", "binding"}):
                    return "RECONCILIATION_REQUIRED", None
                items, next_cursor, page_binding = page["items"], page["nextCursor"], page["binding"]
                # Later pages may be newer than collection start. Check identity
                # now and freshness against the completion clock, never start time.
                reason = check_binding(page_binding, now, freshness=False)
                if reason:
                    return reason, None
                if type(items) is not list:
                    return "RECONCILIATION_REQUIRED", None
                total += len(items)
                if total > record_limit:
                    return "EVIDENCE_OVERFLOW", None
                if next_cursor is not None and (not _identifier(next_cursor) or next_cursor in cursors):
                    return "RECONCILIATION_REQUIRED", None
                page_ids = set()
                for entry in items:
                    identity = validate_entry(entry)
                    if identity is None or identity in ids or identity in page_ids:
                        return "RECONCILIATION_REQUIRED", None
                    page_ids.add(identity)
                ids.update(page_ids)
                bindings.append(page_binding)
                # Own the retained containers, not the reader's mutable page/list.
                evidence[page_key] += ({"items": tuple(items), "nextCursor": next_cursor,
                                        "binding": page_binding},)
                evidence[entry_key] += tuple(items)
                evidence[cursor_key] = next_cursor
                if next_cursor is None:
                    return None, None
                cursors.add(next_cursor)
                cursor = next_cursor
            return "EVIDENCE_OVERFLOW", None

        def queue_entry(entry):
            if (type(entry) is not QueueEntry or not _identifier(entry.submission_id)
                    or not _identifier(entry.client_user_message_id)):
                return None
            return entry.submission_id

        def turn_entry(turn):
            if (type(turn) is not TurnEvidence or not _identifier(turn.turn_id)
                    or type(turn.status) is not str
                    or turn.status not in ("completed", "interrupted", "failed", "inProgress")):
                return None
            return turn.turn_id

        reason, _ = listing(self._queue_reader.list_queue_items,
                            "queue_pages", "queue_entries", "queue_next_cursor",
                            queue_entry, 512)
        if reason:
            return result(reason)
        reason, _ = listing(self._turn_reader.list_turns,
                            "turn_pages", "turns", "turn_next_cursor",
                            turn_entry, 512)
        if reason:
            return result(reason)
        try:
            finished_at = self._clock()
        except Exception:
            return result("EVIDENCE_MISSING")
        for observed in bindings:
            reason = check_binding(observed, finished_at)
            if reason:
                return result(reason)
        if finished_at < now:
            return result("RECONCILIATION_REQUIRED")
        evidence["queue_evidence_complete"] = True
        evidence["turn_evidence_complete"] = True
        return result("EVIDENCE_COLLECTED")
