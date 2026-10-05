"""Pure, bounded Hook Contract 1.0.0 consumer (WO-P1-547).

Exact wire ingress precedes raw security scan, version projection and closed
schema validation. Queues/dedupe/health are one in-memory transaction. This
single-owner core performs no I/O, retries or task/claim/command mutations.
Consumers serialize calls; session end is explicit observer evidence, and an
observer must never reintroduce a retired session identity.
"""
from __future__ import annotations

import json
import math
import re
import time
from dataclasses import dataclass, replace
from datetime import datetime
from types import MappingProxyType
from typing import Callable, Mapping

HOOK_EVENT_INVALID = "HOOK_EVENT_INVALID"

__all__ = ["HOOK_EVENT_INVALID", "HookBus", "HookBusError", "HookIngressContext",
           "HookAdmission", "HookRecord", "HookHealth"]


class HookBusError(Exception):
    """Fixed-code failure; raw input and exception diagnostics are not echoed."""
    def __init__(self, code: str, message: str = "", *, security_invalid: bool = False) -> None:
        self.code = code
        self.security_invalid = security_invalid
        super().__init__(code)


# Exact field rules from docs/contracts/hook-contract-v1.schema.json, 1.0.0.
# Kept as an embedded validation specification: no runtime schema/file I/O.
# Tests bind this table to the canonical schema and exercise its conditionals.
_FIELDS = {'type': 'object',
 'additionalProperties': False,
 'required': ['schema_version',
              'event_id',
              'event_type',
              'hook_class',
              'phase',
              'domain',
              'action',
              'occurred_at',
              'source',
              'source_version',
              'device_id',
              'host_os',
              'privacy_class'],
 'properties': {'schema_version': {'type': 'string',
                                   'pattern': '^1\\.\\d+\\.\\d+$',
                                   'maxLength': 16},
                'event_id': {'type': 'string', 'pattern': '^hk-[0-9a-f]{32}$', 'maxLength': 35},
                'event_type': {'type': 'string',
                               'pattern': '^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*){1,2}$',
                               'maxLength': 96},
                'hook_class': {'enum': ['OBSERVE', 'ADVISORY', 'GUARD', 'COMMAND']},
                'phase': {'enum': ['before', 'after', 'within', 'terminal']},
                'domain': {'enum': ['control',
                                    'execution',
                                    'process',
                                    'tool',
                                    'workspace',
                                    'batch',
                                    'semantic',
                                    'transport',
                                    'device',
                                    'advisory',
                                    'security']},
                'action': {'type': 'string', 'pattern': '^[a-z][a-z0-9_]{0,31}$'},
                'occurred_at': {'type': 'string',
                                'pattern': '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d{1,9})?Z$',
                                'maxLength': 32},
                'source': {'enum': ['a-conductor', 'srm', 'claude-code', 'kilo', 'rdc']},
                'source_version': {'type': 'string',
                                   'pattern': '^\\d+\\.\\d+\\.\\d+(-[0-9A-Za-z.-]+)?$',
                                   'maxLength': 64},
                'device_id': {'type': 'string',
                              'pattern': '^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$',
                              'maxLength': 64},
                'host_os': {'enum': ['windows', 'macos', 'linux']},
                'privacy_class': {'enum': ['PUBLIC', 'INTERNAL', 'SENSITIVE']},
                'lane_id': {'type': 'string',
                            'pattern': '^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$',
                            'maxLength': 64},
                'task_id': {'type': 'string',
                            'pattern': '^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$',
                            'maxLength': 64},
                'work_order': {'type': 'string',
                               'pattern': '^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$',
                               'maxLength': 64},
                'task_topology': {'enum': ['CONTROL_PLANE_ONLY',
                                           'EXECUTION_SUBSTRATE_ONLY',
                                           'CROSS_REPO',
                                           'UNBOUND']},
                'authority_repo': {'type': 'string', 'minLength': 1, 'maxLength': 256},
                'execution_repo': {'type': 'string', 'minLength': 1, 'maxLength': 256},
                'repo': {'type': 'string', 'minLength': 1, 'maxLength': 256},
                'worktree': {'type': 'string', 'minLength': 1, 'maxLength': 256},
                'branch': {'type': 'string', 'pattern': '^[^\\s]{1,256}$', 'maxLength': 256},
                'head_sha': {'type': 'string', 'pattern': '^[0-9a-f]{7,64}$', 'maxLength': 64},
                'claim_ref': {'type': 'string',
                              'pattern': '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$',
                              'maxLength': 128},
                'execution_id': {'type': 'string',
                                 'pattern': '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$',
                                 'maxLength': 128},
                'harness_id': {'type': 'string',
                               'pattern': '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$',
                               'maxLength': 128},
                'model_id': {'type': 'string',
                             'pattern': '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$',
                             'maxLength': 128},
                'effort': {'type': 'string',
                           'pattern': '^[a-z0-9][a-z0-9._-]{0,31}$',
                           'maxLength': 32},
                'state': {'type': 'string', 'pattern': '^[A-Z][A-Z0-9_]{1,31}$', 'maxLength': 32},
                'duration_ms': {'type': 'integer', 'minimum': 0, 'maximum': 2147483647},
                'blocker_code': {'type': 'string',
                                 'pattern': '^[A-Z][A-Z0-9_]{1,63}$',
                                 'maxLength': 64},
                'sequence': {'type': 'integer', 'minimum': 0, 'maximum': 9007199254740991},
                'dedupe_key': {'type': 'string',
                               'pattern': '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$',
                               'maxLength': 128},
                'correlation_id': {'type': 'string',
                                   'pattern': '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$',
                                   'maxLength': 128},
                'causation_id': {'type': 'string', 'pattern': '^hk-[0-9a-f]{32}$', 'maxLength': 35},
                'evidence_refs': {'type': 'array',
                                  'maxItems': 16,
                                  'uniqueItems': True,
                                  'items': {'type': 'string',
                                            'pattern': '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$',
                                            'maxLength': 256}},
                'evidence_digest': {'type': 'string',
                                    'pattern': '^[0-9a-f]{16,128}$',
                                    'maxLength': 128},
                'summary': {'type': 'string', 'minLength': 1, 'maxLength': 512},
                'command_digest': {'type': 'string',
                                   'pattern': '^[0-9a-f]{16,128}$',
                                   'maxLength': 128},
                'command_ref': {'type': 'string',
                                'pattern': '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$',
                                'maxLength': 128},
                'guard': {'type': 'object',
                          'additionalProperties': False,
                          'required': ['failure_policy', 'security_scope', 'authority_scope'],
                          'properties': {'failure_policy': {'enum': ['FAIL_CLOSED', 'FAIL_OPEN']},
                                         'security_scope': {'type': 'boolean'},
                                         'authority_scope': {'type': 'boolean'},
                                         'policy_ref': {'type': 'string',
                                                        'pattern': '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$',
                                                        'maxLength': 256}}},
                'command_request': {'type': 'object',
                                    'additionalProperties': False,
                                    'required': ['request_id', 'command'],
                                    'properties': {'request_id': {'type': 'string',
                                                                  'pattern': '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$',
                                                                  'maxLength': 128},
                                                   'command': {'enum': ['pause',
                                                                        'cancel',
                                                                        'retry',
                                                                        'recover',
                                                                        'reassign',
                                                                        'release_lane',
                                                                        'cleanup_request',
                                                                        'merge_request']},
                                                   'target_ref': {'type': 'string',
                                                                  'pattern': '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$',
                                                                  'maxLength': 128},
                                                   'justification': {'type': 'string',
                                                                     'minLength': 1,
                                                                     'maxLength': 512}}},
                'adapter': {'type': 'object',
                            'additionalProperties': False,
                            'required': ['adapter_id',
                                         'adapter_version',
                                         'contract_version',
                                         'emits',
                                         'redaction_policy',
                                         'supports_sequence'],
                            'properties': {'adapter_id': {'type': 'string',
                                                          'pattern': '^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$',
                                                          'maxLength': 64},
                                           'adapter_version': {'type': 'string',
                                                               'pattern': '^\\d+\\.\\d+\\.\\d+(-[0-9A-Za-z.-]+)?$',
                                                               'maxLength': 64},
                                           'contract_version': {'type': 'string',
                                                                'pattern': '^1\\.\\d+\\.\\d+$',
                                                                'maxLength': 16},
                                           'emits': {'type': 'array',
                                                     'maxItems': 64,
                                                     'uniqueItems': True,
                                                     'items': {'type': 'string',
                                                               'pattern': '^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*){1,2}$',
                                                               'maxLength': 96}},
                                           'redaction_policy': {'type': 'string',
                                                                'pattern': '^[a-z0-9][a-z0-9._/-]{0,63}$',
                                                                'maxLength': 64},
                                           'supports_sequence': {'type': 'boolean'}}}}}
_CLASSES = ("OBSERVE", "ADVISORY", "GUARD", "COMMAND")
_CAUSES = ("incoming_rejection", "queued_shed", "dedupe_cap_exhaustion",
           "stream_cap_exhaustion", "oversized_context", "consumer_exception")
_FORBIDDEN = frozenset(("prompt", "messages", "transcript", "token", "api_key",
    "apikey", "secret", "secret_value", "password", "credential_value", "cookie",
    "share_url", "session_url", "argv", "command_line", "shell_command"))
_SECRET_TOKENS = ("token", "secret", "password", "passwd", "api_key", "apikey",
                  "private_key", "credential", "authorization")
_CORPUS = (
    "sk-FAKE0000000000000000000000000000000000",
    "ghp_FAKE0000000000000000000000000000000",
    "xoxb-FAKE-000000000000000000000000", "AKIAFAKE0000000000",
    "FAKESESSIONCOOKIE=0000000000000000", "-----BEGIN FAKE PRIVATE KEY-----",
    "https://chat.example/FAKE/share/0000", "Bearer FAKE000000000000000000000000000",
)
_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}")
_VERSION = re.compile(r"([0-9]+)\.([0-9]+)\.([0-9]+)")


def _invalid(*, security=False):
    raise HookBusError(HOOK_EVENT_INVALID, security_invalid=security) from None


def _pairs(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            _invalid()
        result[k] = v
    return result


def _constant(_):
    _invalid()


def _security(root):
    stack = [root]
    while stack:
        item = stack.pop()
        if type(item) is dict:
            for key, value in item.items():
                if key.lower() in _FORBIDDEN or any(t in key.lower() for t in _SECRET_TOKENS):
                    _invalid(security=True)
                stack.append(value)
        elif type(item) is list:
            stack.extend(item)
        elif type(item) is str:
            if any(s in item for s in _CORPUS) or _BEARER.search(item):
                _invalid(security=True)
            # Escaped unpaired surrogates cannot become retained UTF-8 text.
            try:
                item.encode("utf-8")
            except UnicodeError:
                _invalid()


def _validate(value, spec):
    kind = spec.get("type")
    if "enum" in spec and (type(value) is not str or value not in spec["enum"]):
        _invalid()
    if kind == "string":
        if type(value) is not str or not spec.get("minLength", 0) <= len(value) <= spec.get("maxLength", 65536):
            _invalid()
        # Canonical branch \s includes Unicode whitespace; other rules keep
        # their existing pattern flags.
        flags = 0 if spec is _FIELDS["properties"]["branch"] else re.ASCII
        if "pattern" in spec and re.fullmatch(spec["pattern"], value, flags) is None:
            _invalid()
    elif kind == "integer":
        if type(value) is not int or not spec.get("minimum", 0) <= value <= spec["maximum"]:
            _invalid()
    elif kind == "boolean":
        if type(value) is not bool:
            _invalid()
    elif kind == "array":
        if type(value) is not list or len(value) > spec["maxItems"]:
            _invalid()
        for item in value:
            _validate(item, spec["items"])
        if spec.get("uniqueItems") and len(set(value)) != len(value):
            _invalid()
    elif kind == "object":
        if type(value) is not dict or not set(spec["required"]) <= value.keys() or value.keys() - spec["properties"].keys():
            _invalid()
        for k, item in value.items():
            _validate(item, spec["properties"][k])


def _instant(stamp):
    # Exact nanoseconds, including fractions beyond datetime microseconds.
    whole, sep, fraction = stamp[:-1].partition(".")
    try:
        dt = datetime.strptime(whole, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        _invalid()
    return (dt.toordinal() * 86400 + dt.hour * 3600 + dt.minute * 60 + dt.second) * 10**9 + int(fraction.ljust(9, "0") if sep else "0")


def _ingest(wire):
    if type(wire) not in (bytes, bytearray):
        _invalid()
    if len(wire) > 65536:
        raise HookBusError("HOOK_EVENT_OVERSIZED")
    wire = bytes(wire)  # Capture exact mutable input before any injected callback.
    try:
        value = json.loads(wire.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
    except (UnicodeError, ValueError, RecursionError):
        _invalid()
    if type(value) is not dict:
        _invalid()
    _security(value)
    version = value.get("schema_version")
    match = _VERSION.fullmatch(version) if type(version) is str else None
    if match and match[1].lstrip("0") != "1":
        raise HookBusError("HOOK_VERSION_UNSUPPORTED")
    if match and match[2].strip("0"):
        value = {k: v for k, v in value.items() if k in _FIELDS["properties"]}
        for name in ("guard", "command_request", "adapter"):
            if type(value.get(name)) is dict:
                known = _FIELDS["properties"][name]["properties"]
                value[name] = {k: v for k, v in value[name].items() if k in known}
    _validate(value, _FIELDS)
    cls = value["hook_class"]
    if (cls == "GUARD") != ("guard" in value) or (cls == "COMMAND") != ("command_request" in value):
        _invalid()
    if "guard" in value:
        guard = value["guard"]
        if (guard["security_scope"] or guard["authority_scope"]) and guard["failure_policy"] != "FAIL_CLOSED":
            _invalid()
    if "adapter" in value and (cls != "OBSERVE" or value["event_type"] != "transport.adapter_capabilities" or value["domain"] != "transport" or value["action"] != "adapter_capabilities"):
        _invalid()
    if value["event_type"].split(".")[:2] != [value["domain"], value["action"]]:
        _invalid()
    return value, _instant(value["occurred_at"]), len(wire)


def _freeze(value):
    if type(value) is dict:
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if type(value) is list:
        return tuple(_freeze(v) for v in value)
    return value


@dataclass(frozen=True)
class HookIngressContext:
    source: str
    device_id: str
    session_id: str


@dataclass(frozen=True)
class HookAdmission:
    status: str
    degraded: bool
    shed_count: int = 0
    markers: tuple[str, ...] = ()


@dataclass(frozen=True)
class HookRecord:
    envelope: Mapping[str, object]
    markers: tuple[str, ...]
    interleaving: str = "OBSERVED_INTERLEAVING"


@dataclass(frozen=True)
class HookHealth:
    degraded: bool
    counters: Mapping[str, int]
    by_class: Mapping[str, Mapping[str, int]]
    conditions: frozenset[str]


@dataclass(frozen=True)
class _Entry:
    record: HookRecord
    wire_bytes: int
    ordinal: int
    instant: int


@dataclass(frozen=True)
class _Stream:
    encoded_key: bytes
    queue: tuple[_Entry, ...] = ()
    high_water: int | None = None
    ended: bool = False


@dataclass(frozen=True)
class _State:
    streams: dict
    dedupe: dict
    ordinal: int
    health: HookHealth


def _health(previous, cls, cause, count=1, pressure=False):
    counters = dict(previous.counters)
    counters[cause] += count
    by_class = {k: dict(v) for k, v in previous.by_class.items()}
    by_class[cls][cause] += count
    conditions = previous.conditions | {"HOOK_STREAM_DEGRADED"}
    if pressure:
        conditions |= {"HOOK_BACKPRESSURE"}
    return HookHealth(True, MappingProxyType(counters), _freeze(by_class), frozenset(conditions))


def _ordered(queue):
    sequenced = iter(sorted((e for e in queue if "sequence" in e.record.envelope), key=lambda e: (e.record.envelope["sequence"], e.ordinal)))
    return tuple(next(sequenced) if "sequence" in e.record.envelope else e for e in queue)


class HookBus:
    """Single-owner bounded core; callers supply observed context and callbacks."""
    def __init__(self, clock: Callable[[], float] | None = None, *, replay_window_seconds=1800,
                 max_streams=128, max_stream_key_bytes=65536,
                 max_stream_events=128, max_stream_bytes=2*1024*1024,
                 max_events=4096, max_bytes=16*1024*1024,
                 max_dedupe_entries=8192, max_dedupe_bytes=1024*1024):
        self._clock = clock if clock is not None else time.monotonic
        if not callable(self._clock) or type(replay_window_seconds) not in (int, float) or (type(replay_window_seconds) is float and not math.isfinite(replay_window_seconds)):
            _invalid()
        self._replay_window_seconds = max(300, min(86400, replay_window_seconds))
        limits = (max_streams, max_stream_key_bytes, max_stream_events, max_stream_bytes,
                  max_events, max_bytes, max_dedupe_entries, max_dedupe_bytes)
        hard = (128, 65536, 128, 2*1024*1024, 4096, 16*1024*1024, 8192, 1024*1024)
        if any(type(v) is not int or v < 0 for v in limits):
            _invalid()
        self._limits = tuple(min(v, h) for v, h in zip(limits, hard))
        health = HookHealth(False, MappingProxyType({c: 0 for c in _CAUSES}),
                            _freeze({k: {c: 0 for c in _CAUSES} for k in _CLASSES}), frozenset())
        self._state = _State({}, {}, 0, health)

    @property
    def replay_window_seconds(self):
        return self._replay_window_seconds

    @property
    def health(self):
        return self._state.health

    @property
    def stream_count(self):
        return len(self._state.streams)

    @property
    def queued_count(self):
        return sum(len(s.queue) for s in self._state.streams.values())

    @property
    def queued_bytes(self):
        return sum(e.wire_bytes for s in self._state.streams.values() for e in s.queue)

    @property
    def dedupe_count(self):
        return len(self._state.dedupe)

    @property
    def dedupe_bytes(self):
        return sum(size for _, size in self._state.dedupe.values())

    @property
    def stream_key_bytes(self):
        return sum(len(s.encoded_key) for s in self._state.streams.values())

    def _commit(self, state):
        # Single swap: the candidate contains all reservations and health.
        self._state = state

    def _transaction(self, state):
        prior = self._state
        try:
            self._commit(state)
        except Exception:
            self._state = prior
            _invalid()

    def _context(self, context, cls):
        if type(context) is not HookIngressContext:
            _invalid()
        values = (context.source, context.device_id, context.session_id)
        if any(type(v) is not str or not v or "\0" in v for v in values):
            _invalid()
        try:
            parts = tuple(v.encode("utf-8") for v in values)
        except UnicodeError:
            _invalid()
        encoded = b"\0".join(parts)
        if any(len(v) > n for v, n in zip(parts, (64, 128, 256))) or len(encoded) > 512:
            self._transaction(replace(self._state, health=_health(self.health, cls, "oversized_context")))
            raise HookBusError("HOOK_CONTEXT_OVERSIZED")
        return values, encoded

    def _pressure(self, cls, cause="incoming_rejection"):
        health = _health(self.health, cls, cause, pressure=True)
        if cause != "incoming_rejection":
            health = _health(health, cls, "incoming_rejection", pressure=True)
        self._transaction(replace(self._state, health=health))
        raise HookBusError("HOOK_BACKPRESSURE")

    def accept(self, event: bytes | bytearray, context: HookIngressContext) -> HookAdmission:
        envelope, instant, wire_size = _ingest(event)
        cls = envelope["hook_class"]
        key, encoded = self._context(context, cls)
        try:
            now = self._clock()
        except Exception:
            _invalid()
        if type(now) not in (int, float):
            _invalid()
        try:
            finite = math.isfinite(now)
        except OverflowError:
            _invalid()
        if not finite:
            _invalid()
        old = self._state
        # Compare elapsed age; adding TTL to a large float can erase the TTL.
        dedupe = {k: v for k, v in old.dedupe.items() if now - v[0] < self.replay_window_seconds}
        identity = envelope.get("dedupe_key", envelope["event_id"])
        if identity in dedupe:
            self._transaction(replace(old, dedupe=dedupe))
            return HookAdmission("DUPLICATE", self.health.degraded)
        size = len(identity.encode("utf-8")) + 64
        ms, mk, se, sb, ge, gb, de, db = self._limits
        if len(dedupe) + 1 > de or sum(v[1] for v in dedupe.values()) + size > db:
            self._pressure(cls, "dedupe_cap_exhaustion")
        streams = dict(old.streams)
        if key not in streams:
            if len(streams) + 1 > ms or sum(len(s.encoded_key) for s in streams.values()) + len(encoded) > mk:
                self._pressure(cls, "stream_cap_exhaustion")
            streams[key] = _Stream(encoded)
        if streams[key].ended:
            _invalid()
        stream = streams[key]
        markers = ()
        if "sequence" in envelope and stream.high_water is not None and envelope["sequence"] <= stream.high_water:
            markers = ("SEQUENCE_INVERSION",)
        entry = _Entry(HookRecord(_freeze(envelope), markers), wire_size, old.ordinal + 1, instant)
        victims = []
        while True:
            local = streams[key].queue
            local_bad = len(local) + 1 > se or sum(e.wire_bytes for e in local) + entry.wire_bytes > sb
            global_bad = sum(len(s.queue) for s in streams.values()) + 1 > ge or sum(e.wire_bytes for s in streams.values() for e in s.queue) + entry.wire_bytes > gb
            if not local_bad and not global_bad:
                break
            if cls not in ("GUARD", "COMMAND"):
                self._pressure(cls)
            eligible = [(e.ordinal, s.encoded_key, k, e) for k, s in streams.items() if not local_bad or k == key for e in s.queue if e.record.envelope["hook_class"] in ("OBSERVE", "ADVISORY")]
            if not eligible:
                self._pressure(cls)
            _, _, victim_key, victim = min(eligible, key=lambda x: (x[0], x[1]))
            victim_stream = streams[victim_key]
            streams[victim_key] = replace(victim_stream, queue=tuple(e for e in victim_stream.queue if e is not victim))
            victims.append(victim)
        health = old.health
        for victim in victims:
            health = _health(health, victim.record.envelope["hook_class"], "queued_shed", pressure=True)
        if markers:
            health = replace(health, degraded=True, conditions=health.conditions | {"HOOK_STREAM_DEGRADED"})
        streams[key] = replace(streams[key], queue=_ordered(streams[key].queue + (entry,)))
        dedupe[identity] = (now, size)
        streams = {k: s for k, s in streams.items() if not (s.ended and not s.queue)}
        self._transaction(_State(streams, dedupe, entry.ordinal, health))
        return HookAdmission("ACCEPTED", self.health.degraded, len(victims), markers)

    def end_session(self, context: HookIngressContext):
        key, _ = self._context(context, "OBSERVE")
        streams = dict(self._state.streams)
        stream = streams.get(key)
        if stream is not None:
            if stream.queue:
                streams[key] = replace(stream, ended=True)
            else:
                del streams[key]
            self._transaction(replace(self._state, streams=streams))

    def drain(self, limit: int | None = None) -> list[HookRecord]:
        if limit is not None and (type(limit) is not int or limit < 0):
            _invalid()
        streams = dict(self._state.streams)
        result = []
        bound = self._limits[4] if limit is None else min(limit, self._limits[4])
        while len(result) < bound:
            heads = [(s.queue[0], k) for k, s in streams.items() if s.queue]
            if not heads:
                break
            entry, key = min(heads, key=lambda pair: (pair[0].instant, pair[0].record.envelope["source"], pair[0].record.envelope["event_id"]))
            stream = streams[key]
            sequence = entry.record.envelope.get("sequence")
            high = stream.high_water
            if sequence is not None:
                high = sequence if high is None else max(high, sequence)
            rest = stream.queue[1:]
            if stream.ended and not rest:
                del streams[key]
            else:
                streams[key] = replace(stream, queue=rest, high_water=high)
            result.append(entry.record)
        self._transaction(replace(self._state, streams=streams))
        return result

    def dispatch(self, consumers, limit: int | None = None) -> list[HookRecord]:
        """One terminal attempt per supplied consumer, no retained subscribers.

        Caller owns callback authority and lifecycle. Snapshot a bounded plain
        list/tuple (at most 128 callbacks); no callback registration/history is
        retained. Exception details are discarded before the next callback.
        """
        if type(consumers) not in (tuple, list) or len(consumers) > 128 or any(not callable(c) for c in consumers):
            _invalid()
        callbacks = tuple(consumers)
        records = self.drain(limit)
        for record in records:
            for callback in callbacks:
                try:
                    callback(record)
                except Exception:
                    cls = record.envelope["hook_class"]
                    self._transaction(replace(self._state, health=_health(self.health, cls, "consumer_exception")))
        return records
