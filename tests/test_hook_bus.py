"""WO-P1-547 STM-1A RED-first tests for a_conductor.hook_bus (module absent).

Pins the frozen WO: exact-wire-byte production ingress + §7.4 typed rejects,
bounded dedupe/replay window, per-stream/aggregate caps with §16 class-aware
shedding, parsed-instant merge with append-only late sequence, terminal
consumer-exception handling, and no task/claim/execution authority.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from a_conductor.hook_bus import HookBus, HookBusError, HookIngressContext


class FakeClock:
    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def env(event_id: str, **over: object) -> dict[str, object]:
    e: dict[str, object] = {
        "schema_version": "1.0.0",
        "event_id": event_id,
        "event_type": "control.start.after",
        "hook_class": "OBSERVE",
        "phase": "after",
        "domain": "control",
        "action": "start",
        "occurred_at": "2026-09-26T07:00:20Z",
        "source": "a-conductor",
        "source_version": "1.2.3",
        "device_id": "device-01",
        "host_os": "macos",
        "privacy_class": "INTERNAL",
    }
    e.update(over)
    return e


def eid(n: int) -> str:
    return f"hk-{n:032x}"


def wire(e: dict[str, object]) -> bytes:
    return json.dumps(e).encode("utf-8")


def ctx(session: str = "sess-1") -> HookIngressContext:
    return HookIngressContext(
        source="a-conductor", device_id="device-01", session_id=session
    )


def test_production_ingress_rejects_parsed_object_calls() -> None:
    bus = HookBus(clock=FakeClock())
    with pytest.raises(HookBusError) as out:
        bus.accept(env(eid(1)), ctx())  # type: ignore[arg-type]
    assert out.value.code == "HOOK_EVENT_INVALID"


def test_exact_wire_byte_cap_65536_accepted_then_over_rejects() -> None:
    bus = HookBus(clock=FakeClock())
    e = env(eid(2), schema_version="1.1.0")  # forward-mode, benign unknown field
    e["pad"] = ""
    base = len(wire(e))
    e["pad"] = "x" * (65536 - base)
    exact = wire(e)
    assert len(exact) == 65536
    assert bus.accept(exact, ctx()).status == "ACCEPTED"
    e["pad"] += "x"
    with pytest.raises(HookBusError) as out:
        bus.accept(wire(e), ctx())
    assert out.value.code == "HOOK_EVENT_OVERSIZED"


def test_parser_and_security_rejects_are_typed_invalid() -> None:
    bus = HookBus(clock=FakeClock())
    inner = json.dumps(env(eid(3)))[1:-1]
    dup = ('{"schema_version": "1.0.0", ' + inner + "}").encode("utf-8")
    for bad in (
        dup,
        wire(env(eid(4), token="x")),
        wire(env(eid(5), summary="Bearer FAKE000000000000000000000000000")),
    ):
        with pytest.raises(HookBusError) as out:
            bus.accept(bad, ctx())
        assert out.value.code == "HOOK_EVENT_INVALID"


def test_non_standard_json_constants_rejected_at_parse() -> None:
    bus = HookBus(clock=FakeClock())
    for constant in ("NaN", "Infinity", "-Infinity"):
        raw = ('{"schema_version": ' + constant + "}").encode("utf-8")
        with pytest.raises(HookBusError) as out:
            bus.accept(raw, ctx())
        assert out.value.code == "HOOK_EVENT_INVALID"


def test_rejection_messages_do_not_interpolate_raw_content() -> None:
    bus = HookBus(clock=FakeClock())
    marker_key = "marker_api_key_name"
    nested_key = "deep_marker_password"
    bearer_value = "Bearer MARKERCREDENTIAL000000000000"
    duplicate = b'{"dup_marker": 1, "dup_marker": 2}'
    for bad in (
        b'{"schema_version": NaN}',
        duplicate,
        wire(env(eid(30), **{marker_key: "v"})),
        wire(env(eid(31), nested={nested_key: "v"})),
        wire(env(eid(32), summary=bearer_value)),
    ):
        with pytest.raises(HookBusError) as out:
            bus.accept(bad, ctx())
        assert out.value.code == "HOOK_EVENT_INVALID"
        message = str(out.value)
        assert marker_key not in message
        assert nested_key not in message
        assert bearer_value not in message
        assert "dup_marker" not in message


def test_different_major_version_rejects_unsupported() -> None:
    bus = HookBus(clock=FakeClock())
    with pytest.raises(HookBusError) as out:
        bus.accept(wire(env(eid(6), schema_version="2.0.0")), ctx())
    assert out.value.code == "HOOK_VERSION_UNSUPPORTED"


def test_dedupe_window_default_and_clamp() -> None:
    clock = FakeClock()
    bus = HookBus(clock=clock)
    first = wire(env(eid(7)))
    assert bus.accept(first, ctx()).status == "ACCEPTED"
    assert bus.accept(first, ctx()).status == "DUPLICATE"
    clock.now = 1801.0
    assert bus.accept(first, ctx()).status == "ACCEPTED"  # window expired
    clamped = HookBus(clock=clock, replay_window_seconds=100)  # clamp -> 300
    again = wire(env(eid(8)))
    clamped.accept(again, ctx())
    clock.now = 2050.0  # age 249 s: still inside the 300 s clamped window
    assert clamped.accept(again, ctx()).status == "DUPLICATE"
    clock.now = 2101.0  # age 300 s: expiry boundary is inclusive
    assert clamped.accept(again, ctx()).status == "ACCEPTED"


def test_identity_is_event_id_not_source_sequence() -> None:
    bus = HookBus(clock=FakeClock())
    assert bus.accept(wire(env(eid(9), sequence=1)), ctx()).status == "ACCEPTED"
    assert bus.accept(wire(env(eid(10), sequence=1)), ctx()).status == "ACCEPTED"
    # new observed session restarting sequence is not a duplicate
    assert (
        bus.accept(wire(env(eid(11), sequence=1)), ctx(session="sess-2")).status
        == "ACCEPTED"
    )


def test_merge_ranks_parsed_instants_and_late_sequence_only_appends() -> None:
    bus = HookBus(clock=FakeClock())
    late_txt = "2026-09-26T07:00:20.5Z"  # later instant, earlier raw string
    bus.accept(wire(env(eid(12), occurred_at=late_txt)), ctx(session="s-a"))
    bus.accept(wire(env(eid(13), occurred_at="2026-09-26T07:00:20Z")), ctx(session="s-b"))
    merged = bus.drain()
    assert [r.envelope["event_id"] for r in merged] == [eid(13), eid(12)]
    # late lower sequence appends with marker, never rewrites prior output
    bus.accept(wire(env(eid(14), sequence=2)), ctx(session="s-c"))
    first = bus.drain()
    assert [r.envelope["event_id"] for r in first] == [eid(14)]
    late = bus.drain()
    bus.accept(wire(env(eid(15), sequence=1)), ctx(session="s-c"))
    late = bus.drain()
    assert late[0].envelope["event_id"] == eid(15)
    assert "SEQUENCE_INVERSION" in late[0].markers
    assert [r.envelope["event_id"] for r in first] == [eid(14)]


def test_stream_cap_backpressure_atomic_retry_and_no_dedupe_on_reject() -> None:
    bus = HookBus(clock=FakeClock())
    for n in range(128):
        bus.accept(wire(env(eid(100 + n))), ctx())
    rejected = wire(env(eid(500)))
    with pytest.raises(HookBusError) as out:
        bus.accept(rejected, ctx())
    assert out.value.code == "HOOK_BACKPRESSURE"
    assert bus.health.degraded is True
    bus.drain(limit=1)
    assert bus.accept(rejected, ctx()).status == "ACCEPTED"  # no identity left
    assert bus.accept(rejected, ctx()).status == "DUPLICATE"


def test_guard_admission_sheds_oldest_observe_and_keeps_identity() -> None:
    bus = HookBus(clock=FakeClock())
    guard = {
        "failure_policy": "FAIL_CLOSED",
        "security_scope": False,
        "authority_scope": False,
    }
    for n in range(128):
        bus.accept(wire(env(eid(200 + n))), ctx())
    result = bus.accept(
        wire(
            env(
                eid(600),
                hook_class="GUARD",
                event_type="security.gate.before",
                domain="security",
                action="gate",
                phase="before",
                guard=guard,
            )
        ),
        ctx(),
    )
    assert result.status == "ACCEPTED"
    assert result.shed_count >= 1
    assert result.degraded is True
    assert bus.health.counters["queued_shed"] >= 1
    assert bus.health.degraded is True
    # shed record keeps dedupe identity: replay cannot reinsert it
    assert bus.accept(wire(env(eid(200))), ctx()).status == "DUPLICATE"


def test_oversized_context_rejects_without_allocating_stream() -> None:
    bus = HookBus(clock=FakeClock())
    with pytest.raises(HookBusError) as out:
        bus.accept(wire(env(eid(20))), ctx(session="s" * 257))
    assert out.value.code == "HOOK_CONTEXT_OVERSIZED"
    assert bus.stream_count == 0
    assert bus.health.degraded is True


def test_consumer_exception_terminal_and_isolated() -> None:
    bus = HookBus(clock=FakeClock())
    seen: list[str] = []
    def broken(record):
        seen.append("broken")
        raise RuntimeError("private diagnostic must not be retained")
    def healthy(record):
        assert bus.health.degraded
        assert bus.health.counters["consumer_exception"] == 1
        assert bus.health.conditions == frozenset({"HOOK_STREAM_DEGRADED"})
        seen.append(record.envelope["event_id"])
    bus.accept(wire(env(eid(700))), ctx())
    result = bus.dispatch((broken, healthy))
    assert seen == ["broken", eid(700)]
    assert len(result) == 1
    assert bus.drain() == []
    assert bus.dispatch((broken, healthy)) == []
    assert seen == ["broken", eid(700)]


@pytest.mark.parametrize("kind", [bytes, bytearray])
def test_hostile_wire_subclass_rejected_before_decode(kind):
    class Hostile(kind):
        def decode(self, *args, **kwargs):
            raise AssertionError("must not call attacker method")
    bus = HookBus(clock=FakeClock())
    with pytest.raises(HookBusError) as out:
        bus.accept(Hostile(wire(env(eid(701)))), ctx())
    assert out.value.code == "HOOK_EVENT_INVALID"
    assert bus.stream_count == 0


@pytest.mark.parametrize("field", ["prompt", "messages", "transcript", "cookie", "share_url", "session_url", "argv", "command_line", "shell_command"])
def test_all_forbidden_fields_scan_before_forward_projection(field):
    bus = HookBus(clock=FakeClock())
    with pytest.raises(HookBusError) as out:
        bus.accept(wire(env(eid(702), schema_version="1.1.0", future=[{field: "x"}])), ctx())
    assert out.value.code == "HOOK_EVENT_INVALID"


CORPUS = (
    "sk-FAKE0000000000000000000000000000000000",
    "ghp_FAKE0000000000000000000000000000000",
    "xoxb-FAKE-000000000000000000000000",
    "AKIAFAKE0000000000", "FAKESESSIONCOOKIE=0000000000000000",
    "-----BEGIN FAKE PRIVATE KEY-----", "https://chat.example/FAKE/share/0000",
    "Bearer FAKE000000000000000000000000000",
)


@pytest.mark.parametrize("secret", CORPUS)
def test_corpus_rejected_anywhere_before_forward_projection(secret):
    with pytest.raises(HookBusError) as out:
        HookBus(clock=FakeClock()).accept(wire(env(eid(703), schema_version="1.1.0", future=["prefix" + secret])), ctx())
    assert out.value.code == "HOOK_EVENT_INVALID"
    assert secret not in str(out.value)


@pytest.mark.parametrize("over", [
    {"sequence": True}, {"sequence": 1.0}, {"duration_ms": -1},
    {"event_type": "execution.start.after"}, {"occurred_at": "2026-02-30T00:00:00Z"},
    {"hook_class": "GUARD"}, {"hook_class": "COMMAND"}, {"privacy_class": "SECRET"},
    {"guard": {"failure_policy": "FAIL_CLOSED", "security_scope": False, "authority_scope": False}},
    {"evidence_refs": ["a", "a"]}, {"unknown": "benign"},
])
def test_schema_and_semantics_invalid_retains_nothing(over):
    bus = HookBus(clock=FakeClock())
    with pytest.raises(HookBusError) as out:
        bus.accept(wire(env(eid(704), **over)), ctx())
    assert out.value.code == "HOOK_EVENT_INVALID"
    assert bus.stream_count == 0


def test_forward_projection_preserves_known_constraints_and_nested_fields():
    bus = HookBus(clock=FakeClock())
    guard = {"failure_policy": "FAIL_CLOSED", "security_scope": True, "authority_scope": False, "future": 42}
    e = env(eid(705), schema_version="1.2.0", hook_class="GUARD", guard=guard, future={"ok": 1})
    bus.accept(wire(e), ctx())
    output = bus.drain()[0]
    assert "future" not in output.envelope
    assert "future" not in output.envelope["guard"]
    with pytest.raises(TypeError):
        output.envelope["guard"]["failure_policy"] = "FAIL_OPEN"
    guard["failure_policy"] = "FAIL_OPEN"
    with pytest.raises(HookBusError):
        bus.accept(wire(e), ctx())


def test_mixed_slots_k_way_heads_and_reused_sequence():
    bus = HookBus(clock=FakeClock())
    for n, seq, stamp in [(710, 3, "2026-09-26T07:00:21Z"), (711, None, "2026-09-26T07:00:19Z"), (712, 1, "2026-09-26T07:00:22Z")]:
        e = env(eid(n), occurred_at=stamp)
        if seq is not None: e["sequence"] = seq
        bus.accept(wire(e), ctx())
    bus.accept(wire(env(eid(713), occurred_at="2026-09-26T07:00:20Z")), ctx("other"))
    assert [r.envelope["event_id"] for r in bus.drain()] == [eid(713), eid(712), eid(711), eid(710)]
    bus.accept(wire(env(eid(714), sequence=3)), ctx())
    assert "SEQUENCE_INVERSION" in bus.drain()[0].markers


def test_stream_end_requires_explicit_observer_and_drain():
    bus = HookBus(clock=FakeClock(), max_streams=1)
    bus.accept(wire(env(eid(720))), ctx())
    with pytest.raises(HookBusError): bus.accept(wire(env(eid(721))), ctx("new"))
    bus.end_session(ctx())
    assert bus.stream_count == 1
    bus.drain()
    assert bus.stream_count == 0
    assert bus.accept(wire(env(eid(721))), ctx("new")).status == "ACCEPTED"


def test_active_empty_stream_retains_high_water_and_capacity():
    bus = HookBus(clock=FakeClock(), max_streams=1)
    bus.accept(wire(env(eid(722), sequence=9)), ctx())
    bus.drain()
    assert bus.stream_count == 1
    with pytest.raises(HookBusError) as out: bus.accept(wire(env(eid(723))), ctx("new"))
    assert out.value.code == "HOOK_BACKPRESSURE"
    assert bus.health.counters["stream_cap_exhaustion"] == 1


def guarded(n, **over):
    return env(eid(n), hook_class="GUARD", guard={"failure_policy": "FAIL_CLOSED", "security_scope": False, "authority_scope": False}, **over)


def test_impossible_guard_fit_does_not_partially_shed():
    first = wire(env(eid(730)))
    bus = HookBus(clock=FakeClock(), max_stream_bytes=len(first))
    bus.accept(first, ctx())
    large = wire(guarded(731, summary="x" * 512))
    with pytest.raises(HookBusError) as out: bus.accept(large, ctx())
    assert out.value.code == "HOOK_BACKPRESSURE"
    assert [r.envelope["event_id"] for r in bus.drain()] == [eid(730)]
    assert bus.health.counters["queued_shed"] == 0


def test_commit_failure_rolls_back_victims_identity_and_health(monkeypatch):
    bus = HookBus(clock=FakeClock(), max_stream_events=1)
    bus.accept(wire(env(eid(732))), ctx())
    old = bus._state
    original = bus._commit
    def fail(state):
        original(state)
        raise RuntimeError("injected commit failure")
    monkeypatch.setattr(bus, "_commit", fail)
    with pytest.raises(HookBusError): bus.accept(wire(guarded(733)), ctx())
    assert bus._state is old
    assert not bus.health.degraded
    monkeypatch.setattr(bus, "_commit", original)
    assert bus.accept(wire(guarded(733)), ctx()).status == "ACCEPTED"
    assert bus.accept(wire(guarded(733)), ctx()).status == "DUPLICATE"
    assert bus.accept(wire(env(eid(732))), ctx()).status == "DUPLICATE"


def test_runtime_field_rules_bound_to_canonical_schema():
    from a_conductor.hook_bus import _FIELDS
    schema = json.loads((Path(__file__).resolve().parents[1] / "docs/contracts/hook-contract-v1.schema.json").read_text())
    assert _FIELDS == {k: v for k, v in schema.items() if k in ("type", "additionalProperties", "required", "properties")}


@pytest.mark.parametrize("name", ["schema_version", "event_id", "event_type", "hook_class", "phase", "domain", "action", "occurred_at", "source", "source_version", "device_id", "host_os", "privacy_class"])
def test_all_required_fields_absent_or_wrong_type(name):
    for value in (None, [], {}, True, 1):
        e = env(eid(800)); e[name] = value
        with pytest.raises(HookBusError) as out: HookBus(clock=FakeClock()).accept(wire(e), ctx())
        assert out.value.code == "HOOK_EVENT_INVALID"
    e = env(eid(800)); del e[name]
    with pytest.raises(HookBusError): HookBus(clock=FakeClock()).accept(wire(e), ctx())


@pytest.mark.parametrize("raw", [b'\xff', b'null', b'[]', b'{}', b'{"x":', b'{"unknown":[{"x":1,"x":2}]}'])
def test_malformed_root_utf8_or_nested_duplicates(raw):
    bus = HookBus(clock=FakeClock())
    with pytest.raises(HookBusError) as out: bus.accept(raw, ctx())
    assert out.value.code == "HOOK_EVENT_INVALID"
    assert out.value.__cause__ is None
    assert bus.stream_count == bus.dedupe_count == 0


@pytest.mark.parametrize("field,bound", [("summary", 512), ("repo", 256), ("state", 32), ("evidence_digest", 128), ("correlation_id", 128)])
def test_optional_string_limits_at_and_above(field, bound):
    value = "A" * bound if field == "state" else "a" * bound
    bus = HookBus(clock=FakeClock())
    assert bus.accept(wire(env(eid(801), **{field: value})), ctx()).status == "ACCEPTED"
    with pytest.raises(HookBusError): bus.accept(wire(env(eid(802), **{field: value + value[0]})), ctx())


def test_schema_oracle_valid_class_payloads_and_forward_nested_projection():
    import jsonschema
    schema = json.loads((Path(__file__).resolve().parents[1] / "docs/contracts/hook-contract-v1.schema.json").read_text())
    command = env(eid(803), hook_class="COMMAND", command_request={"request_id": "r1", "command": "merge_request"})
    adapter = env(eid(804), event_type="transport.adapter_capabilities", domain="transport", action="adapter_capabilities", adapter={"adapter_id": "adapter1", "adapter_version": "1.0.0", "contract_version": "1.0.0", "emits": ["control.start"], "redaction_policy": "fake-secret-corpus/1", "supports_sequence": True})
    for e in (command, adapter, guarded(805)):
        jsonschema.Draft202012Validator(schema).validate(e)
        bus = HookBus(clock=FakeClock()); bus.accept(wire(e), ctx())
        from collections.abc import Mapping
        def thaw(value):
            if isinstance(value, Mapping): return {k: thaw(v) for k, v in value.items()}
            if isinstance(value, tuple): return [thaw(v) for v in value]
            return value
        admitted = thaw(bus.drain()[0].envelope)
        assert admitted == e
        jsonschema.Draft202012Validator(schema).validate(admitted)
        e["schema_version"] = "1.1.0"
        nested = next(k for k in ("command_request", "adapter", "guard") if k in e)
        e[nested]["future"] = "benign"
        bus = HookBus(clock=FakeClock()); bus.accept(wire(e), ctx())
        assert "future" not in bus.drain()[0].envelope[nested]
        e["schema_version"] = "1.0.0"
        with pytest.raises(HookBusError): HookBus(clock=FakeClock()).accept(wire(e), ctx())


@pytest.mark.parametrize("name,value,cap", [("source", "é" * 32, 64), ("device_id", "é" * 64, 128), ("session_id", "é" * 128, 256)])
def test_context_exact_utf8_limits_and_one_byte_over(name, value, cap):
    from dataclasses import replace
    context = replace(ctx(), **{name: value})
    assert len(value.encode()) == cap
    bus = HookBus(clock=FakeClock())
    assert bus.accept(wire(env(eid(806))), context).status == "ACCEPTED"
    assert bus.stream_key_bytes == sum(len(v.encode()) for v in (context.source, context.device_id, context.session_id)) + 2
    with pytest.raises(HookBusError) as out: bus.accept(wire(env(eid(807))), replace(context, **{name: value + "a"}))
    assert out.value.code == "HOOK_CONTEXT_OVERSIZED"
    assert bus.stream_count == bus.dedupe_count == 1


@pytest.mark.parametrize("context", [None, {}, HookIngressContext([], "d", "s"), HookIngressContext("s", "d", 1), HookIngressContext("s", "d", "\ud800")])
def test_malformed_plain_context_no_raw_exception_or_retention(context):
    bus = HookBus(clock=FakeClock())
    with pytest.raises(HookBusError) as out: bus.accept(wire(env(eid(808))), context)
    assert out.value.code == "HOOK_EVENT_INVALID"
    assert bus.stream_count == 0


def test_stream_identity_aggregate_cap_and_default_active_stream_cap():
    key_size = sum(len(v.encode()) for v in (ctx().source, ctx().device_id, ctx().session_id)) + 2
    bus = HookBus(clock=FakeClock(), max_stream_key_bytes=key_size)
    bus.accept(wire(env(eid(809))), ctx())
    with pytest.raises(HookBusError) as out: bus.accept(wire(env(eid(810))), ctx("sess-2"))
    assert out.value.code == "HOOK_BACKPRESSURE"
    assert bus.stream_count == 1
    bus = HookBus(clock=FakeClock())
    for n in range(128): bus.accept(wire(env(eid(900+n))), ctx(f"s{n}")); bus.drain()
    with pytest.raises(HookBusError): bus.accept(wire(env(eid(1100))), ctx("s128"))
    assert bus.stream_count == 128
    assert bus.health.counters["stream_cap_exhaustion"] == 1


def test_default_global_count_boundary_4096_4097():
    bus = HookBus(clock=FakeClock())
    for n in range(4096): bus.accept(wire(env(eid(2000+n))), ctx(f"s{n//128}"))
    assert bus.queued_count == 4096
    rejected = wire(env(eid(7000)))
    with pytest.raises(HookBusError): bus.accept(rejected, ctx("new"))
    assert bus.queued_count == bus.dedupe_count == 4096
    assert bus.stream_count == 32
    bus.drain(limit=1)
    assert bus.accept(rejected, ctx("new")).status == "ACCEPTED"


def padded(n, size):
    e = env(eid(n), schema_version="1.1.0", pad="")
    e["pad"] = "x" * (size - len(wire(e)))
    assert len(wire(e)) == size
    return wire(e)


@pytest.mark.parametrize("scope,cap,count,remaining", [("stream", 2*1024*1024, 31, 65536), ("global", 16*1024*1024, 255, 65536)])
def test_default_wire_byte_caps_below_at_above(scope, cap, count, remaining):
    bus = HookBus(clock=FakeClock())
    for n in range(count): bus.accept(padded(8000+n, 65536), ctx(f"s{n//32}" if scope == "global" else "s"))
    final_context = ctx("last" if scope == "global" else "s")
    bus.accept(padded(9000, remaining-1), final_context)
    assert bus.queued_bytes == cap - 1
    # Another tiny event cannot fit. A rejected event leaves no identity.
    with pytest.raises(HookBusError): bus.accept(wire(env(eid(9001))), final_context)
    bus.drain(limit=1)
    bus.accept(padded(9002, 65536), final_context)
    # Restore the missing one byte via a separate exact-at-cap run below.
    assert bus.queued_bytes == cap - 1
    exact = HookBus(clock=FakeClock())
    for n in range(count+1): exact.accept(padded(10000+n, 65536), ctx(f"s{n//32}" if scope == "global" else "s"))
    assert exact.queued_bytes == cap
    with pytest.raises(HookBusError): exact.accept(wire(env(eid(11000))), ctx("new" if scope == "global" else "s"))
    assert exact.queued_bytes == cap


def test_dedupe_hard_entry_cap_8192_8193_and_expiry_no_eviction():
    clock = FakeClock(); bus = HookBus(clock=clock)
    for n in range(8192): bus.accept(wire(env(eid(12000+n))), ctx()); bus.drain()
    assert bus.dedupe_count == 8192
    assert bus.dedupe_bytes == 8192 * (35+64) < 1024*1024
    incoming = wire(env(eid(22000)))
    with pytest.raises(HookBusError) as out: bus.accept(incoming, ctx())
    assert out.value.code == "HOOK_BACKPRESSURE"
    assert bus.dedupe_count == 8192
    assert bus.accept(wire(env(eid(12000))), ctx()).status == "DUPLICATE"
    clock.now = 1800
    assert bus.accept(incoming, ctx()).status == "ACCEPTED"
    assert bus.dedupe_count == 1


@pytest.mark.parametrize("tail,target,accepted", [("a", 1048575, True), ("aa", 1048576, True), ("aaa", 1048577, False)])
def test_dedupe_exact_hard_byte_boundary(tail, target, accepted):
    bus = HookBus(clock=FakeClock())
    for n in range(5460):
        identity = f"k{n:04d}" + "x" * 123
        assert len(identity) == 128
        bus.accept(wire(env(eid(23000+n), dedupe_key=identity)), ctx()); bus.drain()
    bus.accept(wire(env(eid(29000), dedupe_key="y"*126)), ctx()); bus.drain()
    assert bus.dedupe_bytes + len(tail) + 64 == target
    incoming = wire(env(eid(29001), dedupe_key=tail))
    if accepted:
        assert bus.accept(incoming, ctx()).status == "ACCEPTED"
        assert bus.dedupe_bytes == target
    else:
        old_bytes = bus.dedupe_bytes
        with pytest.raises(HookBusError) as out: bus.accept(incoming, ctx())
        assert out.value.code == "HOOK_BACKPRESSURE"
        assert bus.dedupe_bytes == old_bytes
        assert tail not in bus._state.dedupe
        assert bus.health.counters["dedupe_cap_exhaustion"] == 1


def test_explicit_dedupe_cross_device_sequence_and_maximum_replay_clamp():
    clock = FakeClock(); bus = HookBus(clock=clock, replay_window_seconds=100000)
    bus.accept(wire(env(eid(30000), dedupe_key="same")), ctx())
    assert bus.accept(wire(env(eid(30001), dedupe_key="same")), ctx("new")).status == "DUPLICATE"
    clock.now = 86399
    assert bus.accept(wire(env(eid(30000), dedupe_key="same")), ctx()).status == "DUPLICATE"
    clock.now = 86400
    assert bus.accept(wire(env(eid(30000), dedupe_key="same")), ctx()).status == "ACCEPTED"


def test_aggregate_shedding_oldest_and_local_pressure_restricts_victims():
    bus = HookBus(clock=FakeClock(), max_events=2)
    bus.accept(wire(env(eid(30002))), ctx("old"))
    bus.accept(wire(env(eid(30003), hook_class="ADVISORY")), ctx("new"))
    result = bus.accept(wire(guarded(30004)), ctx("guard"))
    assert result.shed_count == 1
    assert [r.envelope["event_id"] for r in bus.drain()] == [eid(30003), eid(30004)]
    assert bus.health.by_class["OBSERVE"]["queued_shed"] == 1
    bus = HookBus(clock=FakeClock(), max_stream_events=1)
    bus.accept(wire(env(eid(30005))), ctx("other"))
    bus.accept(wire(guarded(30006)), ctx("target"))
    with pytest.raises(HookBusError): bus.accept(wire(guarded(30007)), ctx("target"))
    assert {r.envelope["event_id"] for r in bus.drain()} == {eid(30005), eid(30006)}
    assert bus.health.counters["queued_shed"] == 0


def test_ended_stream_shed_to_empty_retires_atomically():
    bus = HookBus(clock=FakeClock(), max_events=1)
    bus.accept(wire(env(eid(30008))), ctx("ended")); bus.end_session(ctx("ended"))
    bus.accept(wire(guarded(30009)), ctx("active"))
    assert bus.stream_count == 1
    assert bus.drain()[0].envelope["event_id"] == eid(30009)


def test_configuration_hard_limits_clamped_and_replay_read_only():
    bus = HookBus(clock=FakeClock(), max_streams=999, max_stream_events=999, max_events=9999, max_dedupe_entries=99999)
    assert bus._limits == (128, 65536, 128, 2*1024*1024, 4096, 16*1024*1024, 8192, 1024*1024)
    with pytest.raises(AttributeError): bus.replay_window_seconds = 100000


def test_no_history_high_cardinality_health_or_runtime_authority():
    import ast
    p = Path(__file__).resolve().parents[1] / "src/a_conductor/hook_bus.py"
    tree = ast.parse(p.read_text())
    imports = {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert imports <= {"__future__", "json", "math", "re", "time", "dataclasses", "datetime", "types", "typing"}
    forbidden = {"open", "exec", "eval", "compile", "__import__", "read_text", "write_text", "connect", "Popen", "run"}
    assert not {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)} & forbidden
    bus = HookBus(clock=FakeClock(), max_streams=0)
    for n in range(100):
        with pytest.raises(HookBusError): bus.accept(wire(env(eid(31000+n))), ctx(f"unretained-{n}"))
    assert bus.stream_count == bus.dedupe_count == 0
    assert len(bus.health.counters) == 6
    assert len(bus.health.by_class) == 4
    assert all(len(c) == 6 for c in bus.health.by_class.values())
    bus = HookBus(clock=FakeClock())
    for n in range(100): bus.accept(wire(env(eid(32000+n))), ctx()); bus.drain()
    assert bus.queued_count == bus.queued_bytes == 0
    assert set(vars(bus)) == {"_clock", "_limits", "_state", "_replay_window_seconds"}


def test_mutable_wire_captured_before_injected_clock_runs():
    incoming = bytearray(wire(env(eid(33000))))
    exact = len(incoming)
    def clock():
        incoming.extend(b" " * 70000)
        return 0.0
    bus = HookBus(clock=clock)
    assert bus.accept(incoming, ctx()).status == "ACCEPTED"
    assert bus.queued_bytes == exact


def test_security_invalid_has_bounded_explicit_flag():
    with pytest.raises(HookBusError) as out:
        HookBus(clock=FakeClock()).accept(wire(env(eid(33001), schema_version="1.1.0", future={"prompt": "private"})), ctx())
    assert out.value.code == "HOOK_EVENT_INVALID"
    assert out.value.security_invalid is True
    assert str(out.value) == "HOOK_EVENT_INVALID"


@pytest.mark.parametrize("scope,cap,count", [("stream", 2*1024*1024, 31), ("global", 16*1024*1024, 255)])
def test_default_queue_bytes_exact_one_byte_over(scope, cap, count):
    bus = HookBus(clock=FakeClock())
    for n in range(count): bus.accept(padded(34000+n, 65536), ctx(f"s{n//32}" if scope == "global" else "s"))
    target = ctx("last" if scope == "global" else "s")
    incoming = wire(env(eid(35000)))
    bus.accept(padded(35001, 65536-len(incoming)+1), target)
    assert bus.queued_bytes + len(incoming) == cap + 1
    before = bus.queued_bytes
    with pytest.raises(HookBusError) as out: bus.accept(incoming, target)
    assert out.value.code == "HOOK_BACKPRESSURE"
    assert bus.queued_bytes == before
    assert eid(35000) not in bus._state.dedupe


@pytest.mark.parametrize("version", ["2.1234567890.1234567890", "9"*4400 + ".0.0"], ids=["long-minor", "huge-major"])
def test_different_major_gate_precedes_schema_length_and_integer_conversion(version):
    with pytest.raises(HookBusError) as out:
        HookBus(clock=FakeClock()).accept(wire(env(eid(36000), schema_version=version)), ctx())
    assert out.value.code == "HOOK_VERSION_UNSUPPORTED"


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), 10**1000], ids=["bool", "nan", "inf", "huge-int"])
def test_malformed_numeric_config_and_clock_fail_typed_without_mutation(value):
    if type(value) is int:
        assert HookBus(replay_window_seconds=value).replay_window_seconds == 86400
    else:
        with pytest.raises(HookBusError) as out: HookBus(replay_window_seconds=value)
        assert out.value.code == "HOOK_EVENT_INVALID"
    bus = HookBus(clock=lambda: value)
    with pytest.raises(HookBusError) as out: bus.accept(wire(env(eid(36001))), ctx())
    assert out.value.code == "HOOK_EVENT_INVALID"
    assert bus.stream_count == bus.dedupe_count == 0


@pytest.mark.parametrize("field,bound", [("duration_ms", 2147483647), ("sequence", 9007199254740991)])
def test_integer_bounds_zero_at_and_one_over(field, bound):
    for value in (0, bound):
        bus = HookBus(clock=FakeClock())
        assert bus.accept(wire(env(eid(36002), **{field: value})), ctx()).status == "ACCEPTED"
    for value in (-1, bound+1):
        with pytest.raises(HookBusError): HookBus(clock=FakeClock()).accept(wire(env(eid(36003), **{field: value})), ctx())


def test_array_bounds_and_nanosecond_head_rank():
    bus = HookBus(clock=FakeClock())
    bus.accept(wire(env(eid(36004), evidence_refs=[f"r{n}" for n in range(16)], occurred_at="2026-09-26T07:00:20.000000002Z")), ctx("late"))
    bus.accept(wire(env(eid(36005), occurred_at="2026-09-26T07:00:20.000000001Z")), ctx("early"))
    assert [r.envelope["event_id"] for r in bus.drain()] == [eid(36005), eid(36004)]
    with pytest.raises(HookBusError): bus.accept(wire(env(eid(36006), evidence_refs=[f"r{n}" for n in range(17)])), ctx())


def test_large_finite_monotonic_clock_does_not_shorten_replay_window():
    clock = FakeClock(1e308)
    bus = HookBus(clock=clock)
    e = wire(env(eid(36007)))
    assert bus.accept(e, ctx()).status == "ACCEPTED"
    assert bus.accept(e, ctx()).status == "DUPLICATE"


@pytest.mark.parametrize("space", ["\u00a0", "\u0085", "\u2003", "\u2009", "\u202f", "\u3000"], ids=["nbsp", "next-line", "em-space", "thin-space", "narrow-nbsp", "ideographic-space"])
@pytest.mark.parametrize("version", ["1.0.0", "1.1.0"], ids=["strict", "forward"])
def test_branch_unicode_whitespace_matches_canonical_schema(space, version):
    import jsonschema
    schema = json.loads((Path(__file__).resolve().parents[1] / "docs/contracts/hook-contract-v1.schema.json").read_text())
    e = env(eid(37000), branch="feat" + space + "repair", schema_version=version)
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(e))
    assert any(list(error.path) == ["branch"] and error.validator == "pattern" for error in errors)
    bus = HookBus(clock=FakeClock())
    with pytest.raises(HookBusError) as out:
        bus.accept(wire(e), ctx())
    assert out.value.code == "HOOK_EVENT_INVALID"
    assert bus.stream_count == bus.dedupe_count == bus.queued_count == 0


@pytest.mark.parametrize("branch", ["feat/repair", "feat/ไทย", "feat/修復", "feat/repair\u200b", "feat/repair\ufeff"])
def test_branch_non_whitespace_unicode_controls_match_schema(branch):
    import jsonschema
    schema = json.loads((Path(__file__).resolve().parents[1] / "docs/contracts/hook-contract-v1.schema.json").read_text())
    e = env(eid(37001), branch=branch)
    jsonschema.Draft202012Validator(schema).validate(e)
    bus = HookBus(clock=FakeClock())
    assert bus.accept(wire(e), ctx()).status == "ACCEPTED"
    assert bus.drain()[0].envelope["branch"] == branch
