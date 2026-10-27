"""Pure internal signal codec (orch-signal.v1). Decoding data never grants execution authority."""

from dataclasses import dataclass
from datetime import datetime
import json
import re

SCHEMA_VERSION = "orch-signal.v1"
SIZE_LIMIT = 16384
DEPTH_LIMIT = 4
FIELD_LIMIT = 64
REF_LIMIT = 256
EVIDENCE_REF_LIMIT = 16
IDENTIFIER_LIMIT = 128
KINDS = ("ENQUEUE", "REPLAY", "UTILIZATION", "LIFECYCLE")
EFFECT_KINDS = ("ENQUEUE", "REPLAY")
OUTCOME_DECISIONS = ("OBSERVED_ONLY", "NO_ACTION", "DENIED",
                     "RECONCILIATION_REQUIRED", "SUBMISSION_OBSERVED",
                     "DISPATCH_OBSERVED")

_SIGNAL_FIELDS = ("schema_version", "signal_id", "kind", "occurred_at",
                  "source_ref", "project_id", "payload")
_SIGNAL_OPTIONAL = ("task_ref", "work_order_ref", "binding_ref")
_OUTCOME_FIELDS = ("signal_id", "kind", "decision", "reason_code",
                   "evidence_refs", "observability_degraded",
                   "submission_ref", "execution_ref")


class OrchestrationError(ValueError):
    """Bounded reason code; never includes untrusted input."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class OrchestrationSignal:
    """Untrusted internal data; mutable containers are revalidated on encode.

    task_ref/work_order_ref are required for effect kinds and may be absent
    only for project-level observations. binding_ref is an optional locator
    for an existing repo/worktree/branch/HEAD/task/claim tuple.
    """

    schema_version: str
    signal_id: str
    kind: str
    occurred_at: str
    source_ref: str
    project_id: str
    payload: dict
    task_ref: str | None = None
    work_order_ref: str | None = None
    binding_ref: str | None = None


@dataclass(frozen=True, slots=True)
class OrchestrationOutcome:
    """Bounded immutable outcome envelope; never an execution authority."""

    signal_id: str
    kind: str
    decision: str
    reason_code: str
    evidence_refs: tuple
    submission_ref: str | None = None
    execution_ref: str | None = None
    observability_degraded: bool = False


def _keys(value, required, optional=()):
    if type(value) is not dict:
        raise OrchestrationError("SIGNAL_VALUE_INVALID")
    if set(required) - value.keys():
        raise OrchestrationError("SIGNAL_MISSING_KEY")
    if value.keys() - (set(required) | set(optional)):
        raise OrchestrationError("SIGNAL_UNKNOWN_KEY")


def _ref(value, limit=REF_LIMIT):
    if (type(value) is not str or not 1 <= len(value) <= limit
            or any(not 33 <= ord(char) <= 126 for char in value)):
        raise OrchestrationError("SIGNAL_VALUE_INVALID")


def _refs(value):
    if type(value) is not list or len(value) > EVIDENCE_REF_LIMIT:
        raise OrchestrationError("SIGNAL_VALUE_INVALID")
    for ref in value:
        _ref(ref)


def _timestamp(stamp):
    if (type(stamp) is not str or len(stamp) > 40 or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
            r"(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])", stamp)):
        raise OrchestrationError("SIGNAL_VALUE_INVALID")
    try:
        datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        raise OrchestrationError("SIGNAL_VALUE_INVALID") from None


def _payload_contract(kind, payload):
    if type(payload) is not dict:
        raise OrchestrationError("SIGNAL_VALUE_INVALID")
    if kind in EFFECT_KINDS:
        if "target" not in payload:
            raise OrchestrationError("SIGNAL_MISSING_KEY")
        target = payload["target"]
        if type(target) is not str or target not in ("PARENT_QUEUE", "WORKER_BATCH"):
            raise OrchestrationError("SIGNAL_VALUE_INVALID")
        required = ["target", "intent_ref", "trigger"]
        required += (["parent_binding_ref"] if target == "PARENT_QUEUE"
                     else ["ready_plan_ref", "task_map_ref"])
        if kind == "REPLAY":
            required += ["recovery_evidence_ref", "prior_submission_ref"
                         if target == "PARENT_QUEUE" else "prior_execution_ref"]
        _keys(payload, required)
        if type(payload["trigger"]) is not str or payload["trigger"] not in ("EXPLICIT", "REFILL"):
            raise OrchestrationError("SIGNAL_VALUE_INVALID")
    elif kind == "UTILIZATION":
        required = ("census_ref", "ready_set_ref", "activation_ref", "provider_observation_ref")
        _keys(payload, required)
    else:
        required = ("hook_event_ref", "subject_ref", "observation_ref")
        _keys(payload, required)
    for item in payload.values():
        _ref(item)


def _validate(value, expected_source=None):
    _keys(value, _SIGNAL_FIELDS, _SIGNAL_OPTIONAL)
    if value["schema_version"] != SCHEMA_VERSION or type(value["schema_version"]) is not str:
        raise OrchestrationError("SIGNAL_VERSION_UNSUPPORTED")
    kind = value["kind"]
    if type(kind) is not str or kind not in KINDS:
        raise OrchestrationError("SIGNAL_TYPE_UNKNOWN")
    _ref(value["signal_id"], IDENTIFIER_LIMIT)
    _ref(value["source_ref"], IDENTIFIER_LIMIT)
    _ref(value["project_id"], IDENTIFIER_LIMIT)
    if expected_source is not None:
        _ref(expected_source, IDENTIFIER_LIMIT)
        if value["source_ref"] != expected_source:
            raise OrchestrationError("SIGNAL_SOURCE_MISMATCH")
    _timestamp(value["occurred_at"])
    for name, limit in (("task_ref", IDENTIFIER_LIMIT),
                        ("work_order_ref", IDENTIFIER_LIMIT),
                        ("binding_ref", REF_LIMIT)):
        if value.get(name) is not None:
            _ref(value[name], limit)
    if kind in EFFECT_KINDS:
        for name in ("task_ref", "work_order_ref"):
            if value.get(name) is None:
                raise OrchestrationError("SIGNAL_MISSING_KEY")
    _payload_contract(kind, value["payload"])


def _bounded_tree(value):
    # Iterative preflight bounds cycles, depth, total fields and strings
    # before JSON encoding.
    pending = [(value, 0)]
    budget = SIZE_LIMIT
    fields = 0
    while pending:
        item, parent_depth = pending.pop()
        budget -= 1
        if type(item) in (dict, list):
            depth = parent_depth + 1
            if depth > DEPTH_LIMIT:
                raise OrchestrationError("SIGNAL_DEPTH_EXCEEDED")
            if len(item) > FIELD_LIMIT:
                raise OrchestrationError("SIGNAL_FIELDS_EXCEEDED")
            fields += len(item)
            if fields > FIELD_LIMIT:
                raise OrchestrationError("SIGNAL_FIELDS_EXCEEDED")
            if type(item) is dict:
                for key, child in item.items():
                    if type(key) is not str:
                        raise OrchestrationError("SIGNAL_VALUE_INVALID")
                    pending.append((key, depth))
                    pending.append((child, depth))
            else:
                pending.extend((child, depth) for child in item)
        elif type(item) is str:
            budget -= len(json.dumps(item, ensure_ascii=True))
        elif type(item) is not bool and item is not None:
            raise OrchestrationError("SIGNAL_VALUE_INVALID")
        if budget < 0:
            raise OrchestrationError("SIGNAL_SIZE_EXCEEDED")


def _signal_value(signal: OrchestrationSignal) -> dict:
    if type(signal) is not OrchestrationSignal:
        raise OrchestrationError("SIGNAL_VALUE_INVALID")
    value = {name: getattr(signal, name) for name in (
        "schema_version", "signal_id", "kind", "occurred_at", "source_ref",
        "project_id", "task_ref", "work_order_ref", "binding_ref", "payload")}
    return {key: item for key, item in value.items() if item is not None}


def _encode(value) -> bytes:
    _bounded_tree(value)
    data = json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")
    if len(data) > SIZE_LIMIT:
        raise OrchestrationError("SIGNAL_SIZE_EXCEEDED")
    return data


def encode_signal(signal: OrchestrationSignal) -> bytes:
    """Validate and encode deterministically; no authority or side effects."""
    value = _signal_value(signal)
    _bounded_tree(value)
    _validate(value)
    return _encode(value)


def encode_outcome(outcome: OrchestrationOutcome) -> bytes:
    """Validate and encode the bounded outcome envelope deterministically."""
    if type(outcome) is not OrchestrationOutcome:
        raise OrchestrationError("SIGNAL_VALUE_INVALID")
    refs = list(outcome.evidence_refs)
    value = {"signal_id": outcome.signal_id, "kind": outcome.kind,
             "decision": outcome.decision, "reason_code": outcome.reason_code,
             "evidence_refs": refs, "observability_degraded": outcome.observability_degraded}
    if outcome.submission_ref is not None:
        value["submission_ref"] = outcome.submission_ref
    if outcome.execution_ref is not None:
        value["execution_ref"] = outcome.execution_ref
    _bounded_tree(value)
    _validate_outcome(value)
    return _encode(value)


def _validate_outcome(value):
    _keys(value, _OUTCOME_FIELDS[:6], _OUTCOME_FIELDS[6:])
    _ref(value["signal_id"], IDENTIFIER_LIMIT)
    if type(value["kind"]) is not str or value["kind"] not in KINDS:
        raise OrchestrationError("SIGNAL_TYPE_UNKNOWN")
    if (type(value["decision"]) is not str
            or value["decision"] not in OUTCOME_DECISIONS):
        raise OrchestrationError("SIGNAL_VALUE_INVALID")
    _ref(value["reason_code"], IDENTIFIER_LIMIT)
    _refs(value["evidence_refs"])
    if type(value["observability_degraded"]) is not bool:
        raise OrchestrationError("SIGNAL_VALUE_INVALID")
    if "submission_ref" in value and "execution_ref" in value:
        raise OrchestrationError("SIGNAL_VALUE_INVALID")
    for name in ("submission_ref", "execution_ref"):
        if name in value:
            _ref(value[name], IDENTIFIER_LIMIT)


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise OrchestrationError("SIGNAL_DUPLICATE_KEY")
        value[key] = item
    return value


def _numeric_token(_token):
    # Null is forbidden in every schema position. Avoid numeric conversion while
    # letting object hooks detect duplicate keys before value validation.
    return None


def _bounded_text(text):
    # Reject depth and total-field overflow before JSON parsing. Every colon
    # outside a string is an object-key separator, so counting them bounds the
    # total field count without parsing.
    depth = 0
    in_string = False
    escaped = False
    fields = 0
    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in "{[":
            depth += 1
            if depth > DEPTH_LIMIT:
                raise OrchestrationError("SIGNAL_DEPTH_EXCEEDED")
        elif char in "}]":
            depth -= 1
        elif char == ":":
            fields += 1
            if fields > FIELD_LIMIT:
                raise OrchestrationError("SIGNAL_FIELDS_EXCEEDED")
    return text


def _parse(data: bytes):
    if type(data) is not bytes:
        raise OrchestrationError("SIGNAL_VALUE_INVALID")
    if len(data) > SIZE_LIMIT:
        raise OrchestrationError("SIGNAL_SIZE_EXCEEDED")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise OrchestrationError("SIGNAL_ENCODING_INVALID") from None
    # JSON's decoder recurses before object hooks run. Bound containers and
    # total fields first, ignoring delimiters inside strings (including
    # escaped quotes/backslashes).
    _bounded_text(text)
    try:
        value = json.loads(text, object_pairs_hook=_unique_object,
                           parse_int=_numeric_token, parse_float=_numeric_token,
                           parse_constant=_numeric_token)
    except (ValueError, RecursionError) as exc:
        if isinstance(exc, OrchestrationError):
            raise
        raise OrchestrationError("SIGNAL_JSON_INVALID") from None
    if type(value) is not dict:
        raise OrchestrationError("SIGNAL_JSON_INVALID")
    return value


def decode_signal(data: bytes, *, expected_source: str | None = None) -> OrchestrationSignal:
    """Decode untrusted bytes; expected_source is a comparison, not authentication."""
    value = _parse(data)
    _validate(value, expected_source)
    return OrchestrationSignal(
        schema_version=value["schema_version"], signal_id=value["signal_id"],
        kind=value["kind"], occurred_at=value["occurred_at"],
        source_ref=value["source_ref"], project_id=value["project_id"],
        task_ref=value.get("task_ref"), work_order_ref=value.get("work_order_ref"),
        binding_ref=value.get("binding_ref"), payload=value["payload"])


def decode_outcome(data: bytes) -> OrchestrationOutcome:
    """Decode the bounded outcome envelope; never an execution authority."""
    value = _parse(data)
    _validate_outcome(value)
    return OrchestrationOutcome(
        signal_id=value["signal_id"], kind=value["kind"],
        decision=value["decision"], reason_code=value["reason_code"],
        evidence_refs=tuple(value["evidence_refs"]),
        submission_ref=value.get("submission_ref"),
        execution_ref=value.get("execution_ref"),
        observability_degraded=value["observability_degraded"])
