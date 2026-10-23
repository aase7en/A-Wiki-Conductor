"""Pure internal signal codec. Decoding data never grants execution authority."""

from dataclasses import dataclass
from datetime import datetime
import json
import re


class OrchestrationError(ValueError):
    """Bounded reason code; never includes untrusted input."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class OrchestrationSignal:
    """Untrusted internal data; mutable dictionaries are revalidated on encode."""

    signal_type: str
    task_ref: str
    source: str
    timestamp: str
    payload: dict
    metadata: dict


def _keys(value, required, optional=()):
    if type(value) is not dict:
        raise OrchestrationError("SIGNAL_VALUE_INVALID")
    if set(required) - value.keys():
        raise OrchestrationError("SIGNAL_MISSING_KEY")
    if value.keys() - (set(required) | set(optional)):
        raise OrchestrationError("SIGNAL_UNKNOWN_KEY")


def _ref(value, limit=256):
    if (type(value) is not str or not 1 <= len(value) <= limit
            or any(not 33 <= ord(char) <= 126 for char in value)):
        raise OrchestrationError("SIGNAL_VALUE_INVALID")


def _refs(value):
    if type(value) is not list or len(value) > 16:
        raise OrchestrationError("SIGNAL_VALUE_INVALID")
    for ref in value:
        _ref(ref)


def _validate(value, expected_source=None):
    _keys(value, ("signal_type", "task_ref", "source", "timestamp", "payload", "metadata"))
    kind = value["signal_type"]
    if type(kind) is not str:
        raise OrchestrationError("SIGNAL_VALUE_INVALID")
    if kind not in ("enqueue", "replay", "utilization", "lifecycle", "outcome"):
        raise OrchestrationError("SIGNAL_TYPE_UNKNOWN")
    _ref(value["task_ref"], 128)
    _ref(value["source"], 128)
    if expected_source is not None:
        _ref(expected_source, 128)
        if value["source"] != expected_source:
            raise OrchestrationError("SIGNAL_SOURCE_MISMATCH")
    stamp = value["timestamp"]
    if (type(stamp) is not str or len(stamp) > 40 or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
            r"(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])", stamp)):
        raise OrchestrationError("SIGNAL_VALUE_INVALID")
    try:
        datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        raise OrchestrationError("SIGNAL_VALUE_INVALID") from None

    payload = value["payload"]
    if type(payload) is not dict:
        raise OrchestrationError("SIGNAL_VALUE_INVALID")
    optional = ()
    if kind in ("enqueue", "replay"):
        if "target" not in payload:
            raise OrchestrationError("SIGNAL_MISSING_KEY")
        target = payload["target"]
        if type(target) is not str or target not in ("PARENT_QUEUE", "WORKER_BATCH"):
            raise OrchestrationError("SIGNAL_VALUE_INVALID")
        required = ["target", "intent_ref", "trigger"]
        required += (["parent_binding_ref"] if target == "PARENT_QUEUE"
                     else ["ready_plan_ref", "task_map_ref"])
        if kind == "replay":
            required += ["recovery_evidence_ref", "prior_submission_ref"
                         if target == "PARENT_QUEUE" else "prior_execution_ref"]
        _keys(payload, required)
        if type(payload["trigger"]) is not str or payload["trigger"] not in ("EXPLICIT", "REFILL"):
            raise OrchestrationError("SIGNAL_VALUE_INVALID")
    elif kind == "utilization":
        required = ("census_ref", "ready_set_ref", "activation_ref", "provider_observation_ref")
    elif kind == "lifecycle":
        required = ("hook_event_ref", "subject_ref", "observation_ref")
    else:
        required = ("decision", "reason_code", "evidence_refs")
        optional = ("submission_ref", "execution_ref", "observability_degraded")
    _keys(payload, required, optional)
    if kind == "outcome":
        if (type(payload["decision"]) is not str or payload["decision"] not in (
                "OBSERVED_ONLY", "NO_ACTION", "DENIED", "RECONCILIATION_REQUIRED",
                "SUBMISSION_OBSERVED", "DISPATCH_OBSERVED")):
            raise OrchestrationError("SIGNAL_VALUE_INVALID")
        if "submission_ref" in payload and "execution_ref" in payload:
            raise OrchestrationError("SIGNAL_VALUE_INVALID")
    for key, item in payload.items():
        if key == "evidence_refs":
            _refs(item)
        elif key == "observability_degraded":
            if type(item) is not bool:
                raise OrchestrationError("SIGNAL_VALUE_INVALID")
        else:
            _ref(item)
    metadata = value["metadata"]
    _keys(metadata, (), ("correlation_ref", "binding_ref", "producer_ref", "audit_ref", "evidence_refs"))
    for key, item in metadata.items():
        if key == "evidence_refs":
            _refs(item)
        else:
            _ref(item)


def _bounded_tree(value):
    # Iterative preflight bounds cycles, width and strings before JSON encoding.
    pending = [(value, 0)]
    budget = 65536
    while pending:
        item, parent_depth = pending.pop()
        budget -= 1
        if type(item) in (dict, list):
            depth = parent_depth + 1
            if depth > 32:
                raise OrchestrationError("SIGNAL_DEPTH_EXCEEDED")
            if len(item) > 65536:
                raise OrchestrationError("SIGNAL_SIZE_EXCEEDED")
            if type(item) is dict:
                for key, child in item.items():
                    if type(key) is not str:
                        raise OrchestrationError("SIGNAL_VALUE_INVALID")
                    pending.append((key, depth))
                    pending.append((child, depth))
            else:
                pending.extend((child, depth) for child in item)
        elif type(item) is str:
            if len(item) > 65536:
                raise OrchestrationError("SIGNAL_SIZE_EXCEEDED")
            if any(0xD800 <= ord(char) <= 0xDFFF for char in item):
                raise OrchestrationError("SIGNAL_ENCODING_INVALID")
            budget -= len(json.dumps(item, ensure_ascii=True))
        elif type(item) is not bool and item is not None:
            raise OrchestrationError("SIGNAL_VALUE_INVALID")
        if budget < 0:
            raise OrchestrationError("SIGNAL_SIZE_EXCEEDED")


def encode_signal(signal: OrchestrationSignal) -> bytes:
    """Validate and encode deterministically; no authority or side effects."""
    if type(signal) is not OrchestrationSignal:
        raise OrchestrationError("SIGNAL_VALUE_INVALID")
    value = {key: getattr(signal, key) for key in (
        "signal_type", "task_ref", "source", "timestamp", "payload", "metadata")}
    _bounded_tree(value)
    _validate(value)
    data = json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")
    if len(data) > 65536:
        raise OrchestrationError("SIGNAL_SIZE_EXCEEDED")
    return data


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


def decode_signal(data: bytes, *, expected_source: str | None = None) -> OrchestrationSignal:
    """Decode untrusted bytes; expected_source is a comparison, not authentication."""
    if type(data) is not bytes:
        raise OrchestrationError("SIGNAL_VALUE_INVALID")
    if len(data) > 65536:
        raise OrchestrationError("SIGNAL_SIZE_EXCEEDED")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise OrchestrationError("SIGNAL_ENCODING_INVALID") from None
    # JSON's decoder recurses before object hooks run. Bound containers first,
    # ignoring delimiters inside strings (including escaped quotes/backslashes).
    depth = 0
    in_string = False
    escaped = False
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
            if depth > 32:
                raise OrchestrationError("SIGNAL_DEPTH_EXCEEDED")
        elif char in "}]":
            depth -= 1
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
    _validate(value, expected_source)
    return OrchestrationSignal(**value)
