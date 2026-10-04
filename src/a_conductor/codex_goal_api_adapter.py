"""WO-P1-576B: a pure, injected App Server 0.159.0 translator.

Field provenance: openai/codex tag rust-v0.159.0 resolves to commit
687a119f0fcaace47e1f1abcc77cec6c813fd6da. Under that commit, read
codex-rs/app-server-protocol/src/protocol/v2/{thread,thread_data,turn}.rs
and schema/typescript/v2/ThreadGoalStatus.ts (in app-server-protocol).
Canonical evidence: A-Wiki-Conductor #576 comments 5981598729, 5981760977;
queue append semantics: #583 comment 5982737256. The source/schema proves
wire fields; the evidence authorizes only caller-attested blocked -> active.

The injected callable owns transport and its admission. This module has no
client, discovery, credentials, scheduler, persistence, retries, or followups.
Each execute is one explicit caller action. Queue correlation is not a dedupe
key. An ambiguous write/resume remains UNKNOWN; retry safety is never implied.

Responses are bounded *projections*, not complete protocol validation. Only
IDs, status, deletion observation and one page cursor leave the decoder. Extra
fields must be bounded plain JSON data; unknown schema/type facts stay UNKNOWN.
Limits below are local defensive policy, not asserted App Server capabilities.
OBSERVED records an API observation, not admission, ownership, completion,
review, merge, or authority to take another action. Activation is not a CAS:
the caller is responsible for a current independently admitted observation.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Callable
from unicodedata import category

APP_SERVER_VERSION = "0.159.0"
MAX_PAGE_ITEMS = 32
MAX_ID_CHARS = 256
MAX_TEXT_CHARS = 16_384
MAX_RESPONSE_CHARS = 65_536
MAX_RESPONSE_NODES = 4_096
MAX_RESPONSE_DEPTH = 12
MAX_CONTAINER_ITEMS = 128
MAX_OBJECT_FIELDS = 64


class GoalApiOperation(Enum):
    GOAL_GET = "thread/goal/get"
    GOAL_ACTIVATE = "thread/goal/set"
    QUEUE_ADD = "thread/queue/add"
    QUEUE_LIST = "thread/queue/list"
    QUEUE_DELETE = "thread/queue/delete"
    TURNS_LIST = "thread/turns/list"
    RESUME = "thread/resume"


class OutcomeState(Enum):
    OBSERVED = "OBSERVED"
    UNKNOWN = "UNKNOWN"


class GoalApiAdapterError(ValueError):
    """Code-only preflight rejection; the request callable was not invoked."""


@dataclass(frozen=True)
class GoalApiIntent:
    operation: GoalApiOperation
    thread_id: str
    observed_goal_status: str | None = None
    text: str | None = None
    client_user_message_id: str | None = None
    queued_submission_id: str | None = None
    cursor: str | None = None
    limit: int = MAX_PAGE_ITEMS


@dataclass(frozen=True)
class QueueEntry:
    submission_id: str
    client_user_message_id: str


@dataclass(frozen=True)
class TurnEvidence:
    turn_id: str
    status: str


@dataclass(frozen=True)
class GoalApiOutcome:
    operation: GoalApiOperation
    thread_id: str
    state: OutcomeState
    reason_code: str
    # These are server-observed IDs, including bounded IDs from UNKNOWN replies.
    # The operation identifies their kind; they never retarget the supplied ID.
    observed_ids: tuple[str, ...] = ()
    goal_status: str | None = None
    queue_entries: tuple[QueueEntry, ...] = ()
    turns: tuple[TurnEvidence, ...] = ()
    deleted: bool | None = None
    next_cursor: str | None = None


class _ResponseUnknown(Exception):
    pass


def _identifier(value: object) -> bool:
    return (
        type(value) is str and 0 < len(value) <= MAX_ID_CHARS
        and value == value.strip()
        and not any(category(char).startswith("C") for char in value)
    )


def _text(value: object) -> bool:
    return (
        type(value) is str and 0 < len(value) <= MAX_TEXT_CHARS
        and bool(value.strip())
        and not any(category(char).startswith("C") and char not in "\n\r\t" for char in value)
    )


def _version(version: object) -> None:
    if type(version) is not str or version != APP_SERVER_VERSION:
        raise GoalApiAdapterError("GOAL_API_VERSION_UNPROVEN")


def build_goal_api_request(
    intent: GoalApiIntent, *, app_server_version: str
) -> tuple[str, dict]:
    """Build one source-proven request subset; never discover a thread or method."""
    _version(app_server_version)
    if type(intent) is not GoalApiIntent:
        raise GoalApiAdapterError("GOAL_API_INTENT_INVALID")
    if type(intent.operation) is not GoalApiOperation or not _identifier(intent.thread_id):
        raise GoalApiAdapterError("GOAL_API_INTENT_INVALID")
    op = intent.operation
    allowed = set()
    params = {"threadId": intent.thread_id}
    if op is GoalApiOperation.GOAL_ACTIVATE:
        allowed.add("observed_goal_status")
        if type(intent.observed_goal_status) is not str or intent.observed_goal_status != "blocked":
            raise GoalApiAdapterError("GOAL_API_INTENT_INVALID")
        params["status"] = "active"
    elif op is GoalApiOperation.QUEUE_ADD:
        allowed.update(("text", "client_user_message_id"))
        if not _text(intent.text) or not _identifier(intent.client_user_message_id):
            raise GoalApiAdapterError("GOAL_API_INTENT_INVALID")
        # Text.text_elements is source-defaulted; omit it rather than infer a field.
        params["input"] = [{"type": "text", "text": intent.text}]
        params["clientUserMessageId"] = intent.client_user_message_id
    elif op is GoalApiOperation.QUEUE_DELETE:
        allowed.add("queued_submission_id")
        if not _identifier(intent.queued_submission_id):
            raise GoalApiAdapterError("GOAL_API_INTENT_INVALID")
        params["queuedSubmissionId"] = intent.queued_submission_id
    elif op in (GoalApiOperation.QUEUE_LIST, GoalApiOperation.TURNS_LIST):
        allowed.add("cursor")
        if type(intent.limit) is not int or not 1 <= intent.limit <= MAX_PAGE_ITEMS:
            raise GoalApiAdapterError("GOAL_API_INTENT_INVALID")
        params["limit"] = intent.limit
        if intent.cursor is not None:
            if not _identifier(intent.cursor):
                raise GoalApiAdapterError("GOAL_API_INTENT_INVALID")
            params["cursor"] = intent.cursor
    elif op is GoalApiOperation.RESUME:
        params["excludeTurns"] = True
    for name in ("observed_goal_status", "text", "client_user_message_id", "queued_submission_id", "cursor"):
        if name not in allowed and getattr(intent, name) is not None:
            raise GoalApiAdapterError("GOAL_API_INTENT_INVALID")
    if op not in (GoalApiOperation.QUEUE_LIST, GoalApiOperation.TURNS_LIST):
        if type(intent.limit) is not int or intent.limit != MAX_PAGE_ITEMS:
            raise GoalApiAdapterError("GOAL_API_INTENT_INVALID")
    return op.value, params


def _plain_object(value: object) -> bool:
    # Test key types before fixed-key lookups; hostile equality/hash cannot run.
    return (type(value) is dict and len(value) <= MAX_OBJECT_FIELDS
            and all(type(key) is str for key in value))


def _bounded_json(value: object) -> None:
    budget = [0, 0]

    def visit(node: object, depth: int) -> None:
        budget[0] += 1
        if depth > MAX_RESPONSE_DEPTH or budget[0] > MAX_RESPONSE_NODES:
            raise _ResponseUnknown()
        kind = type(node)
        if kind is str:
            budget[1] += len(node)
            if len(node) > MAX_TEXT_CHARS or budget[1] > MAX_RESPONSE_CHARS:
                raise _ResponseUnknown()
            if any(category(char) == "Cs" for char in node):
                raise _ResponseUnknown()
        elif node is None or kind is bool:
            return
        elif kind is int:
            if not -(1 << 63) <= node < (1 << 63):
                raise _ResponseUnknown()
        elif kind is dict:
            if not _plain_object(node):
                raise _ResponseUnknown()
            for key, child in node.items():
                visit(key, depth + 1)
                visit(child, depth + 1)
        elif kind is list:
            if len(node) > MAX_CONTAINER_ITEMS:
                raise _ResponseUnknown()
            for child in node:
                visit(child, depth + 1)
        else:
            # Decoded plain JSON subset only; no coercion or object protocols.
            raise _ResponseUnknown()

    visit(value, 0)


def _observed_ids(op: GoalApiOperation, reply: object) -> tuple[str, ...]:
    """Retain shallow, bounded plain IDs even if another reply field is invalid."""
    if not _plain_object(reply):
        return ()
    candidates = []
    if op in (GoalApiOperation.GOAL_GET, GoalApiOperation.GOAL_ACTIVATE):
        child = reply.get("goal")
        if _plain_object(child):
            candidates.append(child.get("threadId"))
    elif op is GoalApiOperation.RESUME:
        child = reply.get("thread")
        if _plain_object(child):
            candidates.append(child.get("id"))
    elif op is GoalApiOperation.QUEUE_ADD:
        child = reply.get("queuedSubmission")
        if _plain_object(child):
            candidates.append(child.get("id"))
    elif op in (GoalApiOperation.QUEUE_LIST, GoalApiOperation.TURNS_LIST):
        data = reply.get("data")
        if type(data) is list and len(data) <= MAX_PAGE_ITEMS:
            for child in data:
                if _plain_object(child):
                    candidates.append(child.get("id"))
    # Exact plain str gate precedes set membership (hash-disabled subclasses fail).
    return tuple(dict.fromkeys(value for value in candidates if _identifier(value)))


def _required(obj: dict, key: str) -> object:
    if key not in obj:
        raise _ResponseUnknown()
    return obj[key]


def _id_field(obj: dict, key: str) -> str:
    value = _required(obj, key)
    if not _identifier(value):
        raise _ResponseUnknown()
    return value


def _cursor(reply: dict) -> str | None:
    cursor = _required(reply, "nextCursor")
    if cursor is not None and not _identifier(cursor):
        raise _ResponseUnknown()
    return cursor


def _queue_entry(value: object) -> QueueEntry:
    if not _plain_object(value):
        raise _ResponseUnknown()
    inputs = _required(value, "input")
    if type(inputs) is not list or not inputs:
        raise _ResponseUnknown()
    # Only the source-proven text subset is decoded. Other input variants or
    # text element shapes are unsupported observations, never coerced to text.
    for item in inputs:
        if not _plain_object(item) or _required(item, "type") != "text":
            raise _ResponseUnknown()
        text = _required(item, "text")
        if type(text) is not str:
            raise _ResponseUnknown()
        elements = item.get("text_elements", [])
        if type(elements) is not list or elements:
            raise _ResponseUnknown()
    return QueueEntry(_id_field(value, "id"), _id_field(value, "clientUserMessageId"))


def _decode(intent: GoalApiIntent, reply: object, ids: tuple[str, ...]) -> GoalApiOutcome:
    _bounded_json(reply)
    if not _plain_object(reply):
        raise _ResponseUnknown()
    op = intent.operation
    values = {}
    if op in (GoalApiOperation.GOAL_GET, GoalApiOperation.GOAL_ACTIVATE):
        goal = _required(reply, "goal")
        if goal is None and op is GoalApiOperation.GOAL_GET:
            pass
        elif _plain_object(goal):
            if _id_field(goal, "threadId") != intent.thread_id:
                raise _ResponseUnknown()
            status = _required(goal, "status")
            if type(status) is not str or status not in {
                "active", "paused", "blocked", "usageLimited", "budgetLimited", "complete"
            }:
                raise _ResponseUnknown()
            if op is GoalApiOperation.GOAL_ACTIVATE and status != "active":
                raise _ResponseUnknown()
            values["goal_status"] = status
        else:
            raise _ResponseUnknown()
    elif op is GoalApiOperation.QUEUE_ADD:
        entry = _queue_entry(_required(reply, "queuedSubmission"))
        if entry.client_user_message_id != intent.client_user_message_id:
            raise _ResponseUnknown()
        values["queue_entries"] = (entry,)
    elif op is GoalApiOperation.QUEUE_DELETE:
        deleted = _required(reply, "deleted")
        if type(deleted) is not bool:
            raise _ResponseUnknown()
        values["deleted"] = deleted
    elif op in (GoalApiOperation.QUEUE_LIST, GoalApiOperation.TURNS_LIST):
        data = _required(reply, "data")
        if type(data) is not list or len(data) > intent.limit:
            raise _ResponseUnknown()
        values["next_cursor"] = _cursor(reply)
        if op is GoalApiOperation.QUEUE_LIST:
            entries = tuple(_queue_entry(child) for child in data)
            if len({entry.submission_id for entry in entries}) != len(entries):
                raise _ResponseUnknown()
            values["queue_entries"] = entries
        else:
            turns = []
            for child in data:
                if not _plain_object(child):
                    raise _ResponseUnknown()
                turn_id = _id_field(child, "id")
                status = _required(child, "status")
                if type(status) is not str or status not in {"completed", "interrupted", "failed", "inProgress"}:
                    raise _ResponseUnknown()
                turns.append(TurnEvidence(turn_id, status))
            if len({turn.turn_id for turn in turns}) != len(turns):
                raise _ResponseUnknown()
            values["turns"] = tuple(turns)
    elif op is GoalApiOperation.RESUME:
        thread = _required(reply, "thread")
        if not _plain_object(thread) or _id_field(thread, "id") != intent.thread_id:
            raise _ResponseUnknown()
        turns = _required(thread, "turns")
        if type(turns) is not list or turns:
            raise _ResponseUnknown()
    return GoalApiOutcome(op, intent.thread_id, OutcomeState.OBSERVED,
                          "GOAL_API_OBSERVED", observed_ids=ids, **values)


class CodexGoalApiAdapter:
    """One injected request per execute; callers retain all runtime authority."""

    def __init__(self, request: Callable[[str, dict], object], *, app_server_version: str):
        _version(app_server_version)
        if not callable(request):
            raise GoalApiAdapterError("GOAL_API_REQUEST_INVALID")
        self._request = request
        self._version = app_server_version

    def execute(self, intent: GoalApiIntent) -> GoalApiOutcome:
        method, params = build_goal_api_request(intent, app_server_version=self._version)
        # Freeze the validated binding independently of caller-owned references.
        # Even an injected hook that mutates the original cannot retarget decode.
        intent = replace(intent)
        try:
            reply = self._request(method, params)
        except Exception:
            return GoalApiOutcome(intent.operation, intent.thread_id, OutcomeState.UNKNOWN,
                                  "GOAL_API_TRANSPORT_UNKNOWN")
        ids = _observed_ids(intent.operation, reply)
        try:
            return _decode(intent, reply, ids)
        except _ResponseUnknown:
            return GoalApiOutcome(intent.operation, intent.thread_id, OutcomeState.UNKNOWN,
                                  "GOAL_API_RESPONSE_UNKNOWN", observed_ids=ids)
