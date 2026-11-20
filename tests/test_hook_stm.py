"""WO-P1-547 STM-1A RED-first tests for a_conductor.hook_stm.

Pins the frozen WO: explicit partition identity with unbound fallbacks and
UTF-8 byte caps, monotonic TTL with clamp (occurred_at never drives
freshness), fail-stale restart, bounded rebuild input, deterministic
stale-first/oldest-refresh eviction with capacity rejection, and
authority-over-STM reconciliation.
"""
from __future__ import annotations

import json

import pytest

from a_conductor.hook_stm import HookStm, StmError, StmPartition


class FakeClock:
    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def part(**over: object) -> StmPartition:
    base: dict[str, object] = {
        "project_ref": "proj-1",
        "task_id": "task-1",
        "device_id": "device-01",
        "lane_id": "lane-1",
    }
    base.update(over)
    return StmPartition(**base)  # type: ignore[arg-type]


def rec(state: str = "RUNNING", pad: int = 0) -> dict[str, object]:
    r: dict[str, object] = {"state": state, "occurred_at": "2026-09-26T07:00:20Z"}
    if pad:
        r["pad"] = "x" * pad
    return r


def test_partition_identity_fallbacks_and_oversize_rejects() -> None:
    stm = HookStm(clock=FakeClock())
    unbound = StmPartition(project_ref="p", device_id="d")
    assert unbound.task_ref == "UNBOUND_TASK"
    assert unbound.lane_ref == "UNBOUND_LANE"
    with pytest.raises(StmError) as out:
        stm.update(part(project_ref="p" * 257), rec(), 100)
    assert out.value.code == "STM_PARTITION_ID_OVERSIZED"
    assert stm.partition_count == 0  # never truncated or retained


def test_ttl_uses_injected_monotonic_clock_with_clamp() -> None:
    clock = FakeClock()
    stm = HookStm(clock=clock)
    assert stm.rebuild(part(), hook_records=[(rec(), 120)], authority_refs=["auth://1"]).state == "FRESH"
    clock.now = 1799.0
    assert stm.read(part()).state == "FRESH"  # occurred_at age is irrelevant
    clock.now = 1800.0
    stale = stm.read(part())  # reads never extend TTL; age >= TTL expires
    assert stale.state == "STALE"
    assert stale.rebuild_required is True
    low = HookStm(clock=FakeClock(), ttl_seconds=100)  # clamped to 300
    low.rebuild(part(), hook_records=[(rec(), 120)], authority_refs=[])
    low.clock.now = 300.0
    assert low.read(part()).state == "STALE"
    high = HookStm(clock=FakeClock(), ttl_seconds=90000)  # clamped to 86400
    high.rebuild(part(), hook_records=[(rec(), 120)], authority_refs=[])
    high.clock.now = 86400.0
    assert high.read(part()).state == "STALE"


def test_loss_or_restart_begins_rebuild_required_never_empty_fresh() -> None:
    stm = HookStm(clock=FakeClock())
    result = stm.read(part())
    assert result.state == "UNKNOWN"
    assert result.rebuild_required is True
    assert result.records == ()


def test_rebuild_input_caps_reject_without_partial_state() -> None:
    clock = FakeClock()
    stm = HookStm(clock=clock, rebuild_byte_limit=1024)
    with pytest.raises(StmError) as out:
        stm.rebuild(
            part(),
            hook_records=[(rec(), 900), (rec(), 200)],
            authority_refs=["r" * 100],
        )
    assert out.value.code == "STM_REBUILD_INPUT_LIMIT"
    assert stm.read(part()).state == "UNKNOWN"  # no truncation/partial rebuild
    assert (
        stm.rebuild(part(), hook_records=[(rec(), 900)], authority_refs=["é" * 62]).state
        == "FRESH"
    )  # at-cap input accepted when otherwise valid
    default_items = [(rec(pad=0), 10)] * 2048
    default_stm = HookStm(clock=clock)
    before = default_stm.rebuild(part(), [(rec(), 10)], []).records
    with pytest.raises(StmError) as retention_over:
        default_stm.rebuild(part(), hook_records=default_items, authority_refs=[])
    assert retention_over.value.code == "STM_CAPACITY_EXCEEDED"
    assert default_stm.read(part()).state == "STALE"
    assert default_stm.read(part()).records == before
    with pytest.raises(StmError) as default_over:
        default_stm.rebuild(part(), hook_records=default_items + [(rec(), 10)], authority_refs=[])
    assert default_over.value.code == "STM_REBUILD_INPUT_LIMIT"

    hard_limit = HookStm(clock=clock, rebuild_item_limit=4096)
    for count in (4095, 4096):
        items = [(rec(pad=0), 10)] * count
        with pytest.raises(StmError) as retention_over:
            hard_limit.rebuild(part(), hook_records=items, authority_refs=[])
        assert retention_over.value.code == "STM_CAPACITY_EXCEEDED"
        assert hard_limit.read(part()).state == "UNKNOWN"
    with pytest.raises(StmError) as over:
        hard_limit.rebuild(part(), hook_records=[(rec(pad=0), 10)] * 4097, authority_refs=[])
    assert over.value.code == "STM_REBUILD_INPUT_LIMIT"


def test_rebuild_item_cap_counts_hooks_plus_authority_refs() -> None:
    stm = HookStm(clock=FakeClock(), rebuild_item_limit=3)
    records = [(rec(), 120)]
    assert stm.rebuild(part(), records, ["a", "b"]).state == "FRESH"
    with pytest.raises(StmError) as out:
        stm.rebuild(part(task_id="over"), records, ["a", "b", "c"])
    assert out.value.code == "STM_REBUILD_INPUT_LIMIT"
    assert stm.read(part(task_id="over")).state == "UNKNOWN"
    assert stm.partition_count == 1


def test_rebuild_byte_cap_uses_exact_wire_lengths_and_utf8_refs() -> None:
    stm = HookStm(clock=FakeClock(), rebuild_byte_limit=1024)
    records = [(rec(), 900)]
    assert stm.rebuild(part(), records, ["é" * 62]).state == "FRESH"
    with pytest.raises(StmError) as out:
        stm.rebuild(part(), records, ["é" * 62 + "x"])
    assert out.value.code == "STM_REBUILD_INPUT_LIMIT"
    after = stm.read(part())
    assert after.state == "STALE"
    assert after.rebuild_required is True
    assert after.records == tuple(records)  # no partial replacement
    assert stm.rebuild(part(), records, ["é" * 62]).state == "FRESH"


def test_rebuild_item_rejection_marks_retained_partition_stale() -> None:
    stm = HookStm(clock=FakeClock(), rebuild_item_limit=2)
    records = [(rec(), 120)]
    stm.rebuild(part(), records, ["auth://1"])
    with pytest.raises(StmError) as out:
        stm.rebuild(part(), [(rec("DONE"), 120)], ["auth://2", "auth://3"])
    assert out.value.code == "STM_REBUILD_INPUT_LIMIT"
    after = stm.read(part())
    assert after.state == "STALE"
    assert after.rebuild_required is True
    assert after.records == tuple(records)


def test_rebuild_reference_has_1024_utf8_byte_cap() -> None:
    stm = HookStm(clock=FakeClock())
    assert stm.rebuild(part(), [], ["é" * 512]).state == "FRESH"
    with pytest.raises(StmError) as out:
        stm.rebuild(part(task_id="over"), [], ["é" * 512 + "x"])
    assert out.value.code == "STM_REBUILD_INPUT_LIMIT"
    assert stm.read(part(task_id="over")).state == "UNKNOWN"


@pytest.mark.parametrize(
    ("options", "wire_bytes"),
    [({}, 4 * 1024 * 1024), ({"rebuild_byte_limit": 8 * 1024 * 1024 + 1}, 8 * 1024 * 1024)],
)
@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_rebuild_byte_default_and_hard_maximum(
    options: dict[str, int], wire_bytes: int, delta: int
) -> None:
    stm = HookStm(clock=FakeClock(), **options)
    if delta <= 0:
        assert stm.rebuild(part(), [(rec(), wire_bytes + delta)], []).state == "FRESH"
    else:
        with pytest.raises(StmError) as out:
            stm.rebuild(part(), [(rec(), wire_bytes + delta)], [])
        assert out.value.code == "STM_REBUILD_INPUT_LIMIT"
        assert stm.read(part()).state == "UNKNOWN"
    with pytest.raises(StmError) as out:
        stm.rebuild(part(), [(rec(), wire_bytes + 1)], [])
    assert out.value.code == "STM_REBUILD_INPUT_LIMIT"


def test_rebuild_item_configuration_cannot_raise_hard_maximum() -> None:
    stm = HookStm(clock=FakeClock(), rebuild_item_limit=4097)
    records = [(rec(), 10)] * 4095
    with pytest.raises(StmError) as retention_over:
        stm.rebuild(part(), records, ["auth://1"])
    assert retention_over.value.code == "STM_CAPACITY_EXCEEDED"
    assert stm.read(part()).state == "UNKNOWN"
    with pytest.raises(StmError) as out:
        stm.rebuild(part(), records, ["auth://1", "auth://2"])
    assert out.value.code == "STM_REBUILD_INPUT_LIMIT"


@pytest.mark.parametrize("wire_bytes", [-1, True, 1.5])
def test_rebuild_invalid_wire_length_cannot_bypass_byte_cap(wire_bytes: object) -> None:
    stm = HookStm(clock=FakeClock())
    with pytest.raises(StmError) as out:
        stm.rebuild(part(), [(rec(), wire_bytes)], [])  # type: ignore[list-item]
    assert out.value.code == "STM_REBUILD_INPUT_LIMIT"
    assert stm.read(part()).state == "UNKNOWN"


def test_deterministic_eviction_and_capacity_rejection() -> None:
    clock = FakeClock(0.0)
    stm = HookStm(
        clock=clock,
        max_partitions=2,
        records_per_partition=2,
        bytes_per_partition=4096,
        bytes_total=8192,
    )
    stm.rebuild(part(task_id="t1"), hook_records=[(rec(), 100)], authority_refs=[])
    clock.now = 10.0
    stm.rebuild(part(task_id="t2"), hook_records=[(rec(), 100)], authority_refs=[])
    clock.now = 20.0
    stm.rebuild(part(task_id="t3"), hook_records=[(rec(), 100)], authority_refs=[])
    # oldest monotonic refresh (t1) evicted; exact identity is the tie-break
    assert stm.read(part(task_id="t1")).state == "UNKNOWN"
    assert stm.read(part(task_id="t1")).rebuild_required is True
    assert stm.read(part(task_id="t2")).state == "FRESH"
    with pytest.raises(StmError) as out:
        stm.update(part(task_id="t2"), rec(pad=4200), 4300)  # +128 allowance > 4096
    assert out.value.code == "STM_CAPACITY_EXCEEDED"
    degraded = stm.read(part(task_id="t2"))
    assert degraded.state in {"STALE", "UNKNOWN"}
    assert degraded.rebuild_required is True


def test_eviction_prefers_explicit_stale_then_exact_identity_at_refresh_tie() -> None:
    clock = FakeClock()
    stm = HookStm(clock=clock, max_partitions=2, rebuild_item_limit=1)
    stm.rebuild(part(task_id="fresh"), [(rec(), 120)], [])
    clock.now = 10
    stm.rebuild(part(task_id="stale"), [(rec(), 120)], [])
    with pytest.raises(StmError):
        stm.rebuild(part(task_id="stale"), [(rec(), 120)], ["auth://1"])
    stm.update(part(task_id="new"), rec(), 120)
    assert stm.read(part(task_id="stale")).state == "UNKNOWN"
    assert stm.read(part(task_id="fresh")).state == "FRESH"

    tied = HookStm(clock=clock, max_partitions=2)
    tied.update(part(task_id="b"), rec(), 120)
    tied.update(part(task_id="a"), rec(), 120)
    tied.update(part(task_id="c"), rec(), 120)
    assert tied.read(part(task_id="a")).state == "UNKNOWN"
    assert tied.read(part(task_id="b")).state == "FRESH"


def test_eviction_expiry_uses_monotonic_time_not_occurred_at() -> None:
    clock = FakeClock()
    stm = HookStm(clock=clock, max_partitions=2, ttl_seconds=300)
    stm.update(part(task_id="expired"), rec(), 120)
    clock.now = 299
    stm.update(part(task_id="fresh"), {"occurred_at": "1900-01-01T00:00:00Z"}, 120)
    clock.now = 300
    stm.update(part(task_id="new"), rec(), 120)
    assert stm.read(part(task_id="expired")).state == "UNKNOWN"
    assert stm.read(part(task_id="fresh")).state == "FRESH"


@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_projection_byte_bound_includes_wire_length_allowance_and_key_once(delta: int) -> None:
    partition = part(project_ref="é")
    # Normative compact JSON serialization of the retained (projection, wire-length) pair.
    record_bytes = len('[{"label":"é"},17]'.encode("utf-8")) + 128
    key_bytes = len("\x1f".join(("é", "task-1", "device-01", "lane-1")).encode("utf-8"))
    total = key_bytes + record_bytes
    stm = HookStm(clock=FakeClock(), bytes_per_partition=total - delta)
    if delta == 1:
        with pytest.raises(StmError) as out:
            stm.update(partition, {"label": "é"}, 17)
        assert out.value.code == "STM_CAPACITY_EXCEEDED"
        assert stm.read(partition).state == "UNKNOWN"
    else:
        stm.update(partition, {"label": "é"}, 17)
        assert stm.read(partition).state == "FRESH"

    # A second record includes its allowance but does not charge the partition key again.
    two = HookStm(clock=FakeClock(), bytes_per_partition=key_bytes + 2 * record_bytes)
    two.update(partition, {"label": "é"}, 17)
    two.update(partition, {"label": "é"}, 17)
    assert len(two.read(partition).records) == 2


def test_empty_partition_key_bytes_participate_in_aggregate_budget() -> None:
    partition = part()
    key_bytes = len("\x1f".join(("proj-1", "task-1", "device-01", "lane-1")).encode("utf-8"))
    at_cap = HookStm(clock=FakeClock(), bytes_total=key_bytes)
    assert at_cap.rebuild(partition, [], []).state == "FRESH"
    over = HookStm(clock=FakeClock(), bytes_total=key_bytes - 1)
    with pytest.raises(StmError) as out:
        over.rebuild(partition, [], [])
    assert out.value.code == "STM_CAPACITY_EXCEEDED"
    assert over.partition_count == 0
    assert over.read(partition).state == "UNKNOWN"


def test_record_count_rejection_preserves_records_and_requires_rebuild() -> None:
    stm = HookStm(clock=FakeClock(), records_per_partition=2)
    stm.update(part(), rec(), 120)
    stm.update(part(), rec("DONE"), 120)
    before = stm.read(part()).records
    with pytest.raises(StmError) as out:
        stm.update(part(), rec("OTHER"), 120)
    assert out.value.code == "STM_CAPACITY_EXCEEDED"
    after = stm.read(part())
    assert after.state == "STALE"
    assert after.rebuild_required is True
    assert after.records == before
    stm.update(part(task_id="other"), rec(), 120)
    assert stm.read(part()).state == "STALE"
    assert stm.rebuild(part(), [(rec(), 120)], []).state == "FRESH"


def test_existing_partition_aggregate_pressure_never_evicts_other_partition() -> None:
    clock = FakeClock()
    stm = HookStm(clock=clock, records_total=2)
    stm.update(part(task_id="old"), rec(), 120)
    clock.now = 1
    stm.update(part(task_id="target"), rec(), 120)
    before = stm.read(part(task_id="target")).records
    with pytest.raises(StmError) as out:
        stm.update(part(task_id="target"), rec(), 120)
    assert out.value.code == "STM_CAPACITY_EXCEEDED"
    assert stm.read(part(task_id="old")).state == "FRESH"
    assert stm.read(part(task_id="target")).state == "STALE"
    assert stm.read(part(task_id="target")).records == before


def test_impossible_aggregate_admission_preserves_other_partitions() -> None:
    stm = HookStm(clock=FakeClock(), records_total=1)
    stm.update(part(task_id="old"), rec(), 120)
    with pytest.raises(StmError) as out:
        stm.rebuild(part(task_id="new"), [(rec(), 120)] * 2, [])
    assert out.value.code == "STM_CAPACITY_EXCEEDED"
    assert stm.read(part(task_id="old")).state == "FRESH"
    assert stm.read(part(task_id="new")).state == "UNKNOWN"


@pytest.mark.parametrize("options,limit", [({}, 128), ({"records_per_partition": 257}, 256)])
def test_per_partition_record_default_and_hard_maximum(options: dict[str, int], limit: int) -> None:
    stm = HookStm(clock=FakeClock(), **options)
    for _ in range(limit):
        stm.update(part(), {"label": "x"}, 17)
    with pytest.raises(StmError) as out:
        stm.update(part(), {"label": "x"}, 17)
    assert out.value.code == "STM_CAPACITY_EXCEEDED"
    assert len(stm.read(part()).records) == limit


def key_bytes(partition: StmPartition) -> int:
    return len("\x1f".join((partition.project_ref, partition.task_ref,
                          partition.device_id, partition.lane_ref)).encode("utf-8"))


def unit_bytes(unit: object) -> int:
    return len(json.dumps(unit, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")) + 128


def projection_at_total(partition: StmPartition, total: int) -> dict[str, object]:
    padding = total - key_bytes(partition) - unit_bytes([{"pad": ""}, 17])
    assert padding >= 0
    return {"pad": "x" * padding}


def test_new_partition_aggregate_count_pressure_evicts_oldest() -> None:
    clock = FakeClock()
    stm = HookStm(clock=clock, records_total=2)
    stm.update(part(task_id="old"), rec(), 120)
    clock.now = 1
    stm.update(part(task_id="keep"), rec(), 120)
    clock.now = 2
    stm.update(part(task_id="new"), rec(), 120)
    assert stm.read(part(task_id="old")).state == "UNKNOWN"
    assert stm.read(part(task_id="old")).rebuild_required is True
    assert stm.read(part(task_id="keep")).state == "FRESH"
    assert stm.read(part(task_id="new")).state == "FRESH"


@pytest.mark.parametrize("admission", ["update", "rebuild"])
def test_new_partition_that_exceeds_own_cap_never_evicts(admission: str) -> None:
    stm = HookStm(clock=FakeClock(), max_partitions=1, records_per_partition=1,
                  bytes_per_partition=300)
    stm.rebuild(part(task_id="keep"), [], [])
    before = stm.read(part(task_id="keep"))
    with pytest.raises(StmError) as out:
        if admission == "update":
            stm.update(part(task_id="oversized"), rec(pad=300), 120)
        else:
            stm.rebuild(part(task_id="oversized"), [(rec(), 120)] * 2, [])
    assert out.value.code == "STM_CAPACITY_EXCEEDED"
    assert stm.partition_count == 1
    assert stm.read(part(task_id="keep")) == before
    assert stm.read(part(task_id="oversized")).state == "UNKNOWN"


def test_existing_rebuild_capacity_failure_is_atomic_and_only_target_stale() -> None:
    stm = HookStm(clock=FakeClock(), records_total=2)
    old = part(task_id="keep")
    target = part(task_id="target")
    stm.rebuild(old, [(rec(), 120)], [])
    before = stm.rebuild(target, [(rec("OLD"), 120)], [])
    with pytest.raises(StmError) as out:
        stm.rebuild(target, [(rec("NEW"), 120)], ["auth://new"])
    assert out.value.code == "STM_CAPACITY_EXCEEDED"
    assert stm.read(old).state == "FRESH"
    after = stm.read(target)
    assert after.records == before.records
    assert after.state == "STALE" and after.rebuild_required
    assert stm.rebuild(target, [(rec("NEW"), 120)], []).state == "FRESH"


def test_references_share_record_and_canonical_byte_budgets() -> None:
    partition = part()
    reference = 'auth://é/"\\'
    exact = key_bytes(partition) + unit_bytes([rec(), 120]) + unit_bytes(reference)
    stm = HookStm(clock=FakeClock(), records_per_partition=2, records_total=2,
                  bytes_per_partition=exact, bytes_total=exact)
    assert stm.rebuild(partition, [(rec(), 120)], [reference]).state == "FRESH"
    assert stm.record_count == 2 and stm.accounted_bytes == exact
    with pytest.raises(StmError) as out:
        stm.update(partition, rec(), 120)
    assert out.value.code == "STM_CAPACITY_EXCEEDED"
    assert stm.record_count == 2 and stm.accounted_bytes == exact
    assert stm.read(partition).state == "STALE"
    over = HookStm(clock=FakeClock(), bytes_per_partition=exact - 1)
    with pytest.raises(StmError) as out:
        over.rebuild(partition, [(rec(), 120)], [reference])
    assert out.value.code == "STM_CAPACITY_EXCEEDED"
    assert over.partition_count == 0


def test_reference_only_partition_counts_for_aggregate_eviction() -> None:
    clock = FakeClock()
    stm = HookStm(clock=clock, records_total=2)
    stm.rebuild(part(task_id="old"), [], ["r1"])
    clock.now = 1
    stm.rebuild(part(task_id="keep"), [], ["r2"])
    clock.now = 2
    stm.rebuild(part(task_id="new"), [], ["r3"])
    assert stm.record_count == 2
    assert stm.read(part(task_id="old")).state == "UNKNOWN"
    assert stm.read(part(task_id="keep")).state == "FRESH"


@pytest.mark.parametrize("delta", [-1, 0, 1])
@pytest.mark.parametrize("options,cap", [({}, 512 * 1024),
                                         ({"bytes_per_partition": 1024 * 1024 + 1}, 1024 * 1024)])
def test_per_partition_default_hard_byte_cap_minus_at_plus_one(
    delta: int, options: dict[str, int], cap: int
) -> None:
    partition = part()
    stm = HookStm(clock=FakeClock(), **options)
    before = stm.rebuild(partition, [], [])
    candidate = projection_at_total(partition, cap + delta)
    if delta <= 0:
        stm.update(partition, candidate, 17)
        assert stm.accounted_bytes == cap + delta
        assert stm.read(partition).state == "FRESH"
    else:
        with pytest.raises(StmError) as out:
            stm.update(partition, candidate, 17)
        assert out.value.code == "STM_CAPACITY_EXCEEDED"
        assert stm.read(partition).records == before.records
        assert stm.read(partition).state == "STALE"
        assert stm.accounted_bytes == key_bytes(partition)


@pytest.mark.parametrize("delta", [-1, 0, 1])
@pytest.mark.parametrize("options,cap", [({}, 4 * 1024 * 1024),
                                         ({"bytes_total": 8 * 1024 * 1024 + 1}, 8 * 1024 * 1024)])
def test_aggregate_default_hard_byte_cap_existing_update_never_evicts(
    delta: int, options: dict[str, int], cap: int
) -> None:
    chunk = cap // 8
    stm = HookStm(clock=FakeClock(), **options,
                  bytes_per_partition=1024 * 1024)
    for index in range(8):
        partition = part(task_id=f"keep-{index}")
        stm.update(partition, projection_at_total(partition, chunk - 256), 17)
    target = part(task_id="target")
    before = stm.rebuild(target, [], [])
    candidate = projection_at_total(target, 2048 + delta)
    if delta <= 0:
        stm.update(target, candidate, 17)
        assert stm.accounted_bytes == cap + delta
        assert stm.read(target).state == "FRESH"
    else:
        with pytest.raises(StmError) as out:
            stm.update(target, candidate, 17)
        assert out.value.code == "STM_CAPACITY_EXCEEDED"
        assert stm.read(target).state == "STALE"
        assert stm.read(target).records == before.records
    assert stm.partition_count == 9
    for index in range(8):
        assert stm.read(part(task_id=f"keep-{index}")).state == "FRESH"


@pytest.mark.parametrize("options,limit", [({}, 128), ({"max_partitions": 257}, 256)])
def test_partition_default_hard_maximum_and_missing_read(options: dict[str, int], limit: int) -> None:
    stm = HookStm(clock=FakeClock(), **options)
    for index in range(limit + 1):
        stm.rebuild(part(task_id=f"p-{index:03}"), [], [])
    assert stm.partition_count == limit
    assert stm.read(part(task_id="p-000")).state == "UNKNOWN"
    assert stm.read(part(task_id="p-000")).rebuild_required


@pytest.mark.parametrize("options,limit", [({}, 2048), ({"records_total": 4097}, 4096)])
def test_aggregate_record_default_hard_maximum_existing_update(options: dict[str, int], limit: int) -> None:
    stm = HookStm(clock=FakeClock(), records_per_partition=256, **options)
    partition_count = limit // 256 + 1
    for index in range(limit):
        stm.update(part(task_id=f"p-{index % partition_count}"), {"label": "x"}, 17)
    before = stm.read(part(task_id="p-0")).records
    assert stm.record_count == limit
    with pytest.raises(StmError) as out:
        stm.update(part(task_id="p-0"), {"label": "x"}, 17)
    assert out.value.code == "STM_CAPACITY_EXCEEDED"
    assert stm.record_count == limit
    assert stm.partition_count == partition_count
    assert stm.read(part(task_id="p-0")).records == before
    assert stm.read(part(task_id="p-0")).state == "STALE"


def test_new_partition_byte_pressure_can_evict_multiple_stale_then_oldest() -> None:
    clock = FakeClock()
    stm = HookStm(clock=clock, bytes_total=1000, rebuild_item_limit=1)
    for index in range(3):
        clock.now = index
        partition = part(task_id=f"old-{index}")
        stm.update(partition, projection_at_total(partition, 300), 17)
    with pytest.raises(StmError):
        stm.rebuild(part(task_id="old-2"), [(rec(), 120)], ["over"])
    new = part(task_id="new")
    stm.update(new, projection_at_total(new, 650), 17)
    assert stm.accounted_bytes == 950
    assert stm.read(part(task_id="old-2")).state == "UNKNOWN"  # stale first
    assert stm.read(part(task_id="old-0")).state == "UNKNOWN"  # then oldest
    assert stm.read(part(task_id="old-1")).state == "FRESH"


def test_input_gate_precedes_retention_gate_and_never_copies_over_limit() -> None:
    class Uncopyable(dict):
        def __iter__(self):
            raise AssertionError("input rejection must precede projection work")

        def keys(self):
            raise AssertionError("input rejection must precede projection work")

    stm = HookStm(clock=FakeClock(), records_per_partition=0, rebuild_item_limit=1)
    with pytest.raises(StmError) as out:
        stm.rebuild(part(), [(Uncopyable(), 1)] * 2, [])
    assert out.value.code == "STM_REBUILD_INPUT_LIMIT"
    assert stm.partition_count == 0
    with pytest.raises(StmError) as out:
        stm.rebuild(part(), [(Uncopyable(), 1)], [])
    assert out.value.code == "STM_CAPACITY_EXCEEDED"


def test_capacity_accounting_owns_nested_projection_and_read_copies() -> None:
    projection = {"nested": {"label": "before"}}
    stm = HookStm(clock=FakeClock())
    stm.update(part(), projection, 17)
    accounted = stm.accounted_bytes
    projection["nested"]["label"] = "x" * (1024 * 1024)
    result = stm.read(part())
    assert result.records[0][0]["nested"]["label"] == "before"
    result.records[0][0]["nested"]["label"] = "caller-owned"
    assert stm.read(part()).records[0][0]["nested"]["label"] == "before"
    rebuilt = stm.rebuild(part(), [({"nested": {"label": "rebuilt"}}, 17)], [])
    rebuilt.records[0][0]["nested"]["label"] = "caller-owned"
    assert stm.read(part()).records[0][0]["nested"]["label"] == "rebuilt"
    assert stm.accounted_bytes == accounted + 1  # rebuilt is one ASCII byte longer


def test_successful_update_does_not_clear_rebuild_required_latch() -> None:
    stm = HookStm(clock=FakeClock(), records_per_partition=2)
    stm.update(part(), rec(), 120)
    with pytest.raises(StmError):
        stm.rebuild(part(), [(rec(), 120)] * 3, [])
    stm.update(part(), rec("NEW"), 120)
    assert stm.read(part()).state == "STALE"
    assert stm.rebuild(part(), [(rec(), 120)], []).state == "FRESH"


def test_authoritative_contradiction_beats_derived_projection() -> None:
    clock = FakeClock()
    stm = HookStm(clock=clock)
    stm.rebuild(part(), hook_records=[(rec("RUNNING"), 120)], authority_refs=[])
    result = stm.reconcile(
        part(), authority_state={"state": "DONE"}, authority_ref="auth://run/1"
    )
    assert result.derived_degraded is True  # conflicting derived fields superseded
    after = stm.read(part())
    assert after.state == "FRESH"
    assert after.derived_degraded is True
    assert after.authority_ref == "auth://run/1"
    assert after.records[0][0]["state"] == "DONE"
    assert after.records[0][0]["occurred_at"] == "2026-09-26T07:00:20Z"
    assert len(after.records) == 1  # no historical Hook append or full authority record
    assert after.records[0][1] == 120  # original Hook admission measurement remains exact


def test_reconcile_matching_fields_retains_only_pointer_and_no_new_authority_fields() -> None:
    clock = FakeClock()
    stm = HookStm(clock=clock)
    before = stm.rebuild(part(), [(rec(), 120)], ["auth://other"])
    clock.now = 10
    observation = {"state": "RUNNING", "authority_only": "not cached"}
    result = stm.reconcile(part(), authority_state=observation, authority_ref="auth://run/1")
    assert result.state == "FRESH" and not result.derived_degraded
    assert result.records == before.records
    assert result.authority_ref == "auth://run/1"
    assert stm.record_count == 3  # Hook, rebuild reference, latest reconciliation pointer
    assert stm.accounted_bytes == key_bytes(part()) + unit_bytes([rec(), 120]) + unit_bytes("auth://other") + unit_bytes("auth://run/1")
    observation["state"] = "caller mutation"
    assert stm.read(part()).records == before.records
    clock.now = 1809
    assert stm.read(part()).state == "FRESH"
    clock.now = 1810
    assert stm.read(part()).state == "STALE"  # reconciliation refresh uses injected monotonic time


def test_reconcile_keeps_latest_pointer_without_unbounded_reference_history() -> None:
    stm = HookStm(clock=FakeClock(), records_per_partition=2, records_total=2)
    stm.update(part(), rec(), 120)
    for index in range(10):
        result = stm.reconcile(part(), authority_state={"state": "RUNNING"}, authority_ref=f"auth://run/{index}")
        assert result.authority_ref == f"auth://run/{index}"
        assert stm.record_count == 2
    assert stm.accounted_bytes == key_bytes(part()) + unit_bytes([rec(), 120]) + unit_bytes("auth://run/9")
    stm.update(part(task_id="new"), rec(), 120)  # pointer counts toward aggregate eviction
    assert stm.read(part()).state == "UNKNOWN"


def test_reconcile_supersedes_overlapping_values_and_preserves_other_fields() -> None:
    stm = HookStm(clock=FakeClock())
    records = [({"state": "RUNNING", "nested": {"owner": "old"}, "keep": "a"}, 100),
               ({"state": "QUEUED", "keep": "b"}, 120)]
    stm.rebuild(part(), records, [])
    observation = {"state": "DONE", "nested": {"owner": "new"}, "authority_only": "not retained"}
    result = stm.reconcile(part(), authority_state=observation, authority_ref="auth://fresh")
    corrected = [({"state": "DONE", "nested": {"owner": "new"}, "keep": "a"}, 100),
                 ({"state": "DONE", "keep": "b"}, 120)]
    assert result.records == tuple(corrected)
    assert result.derived_degraded
    assert stm.accounted_bytes == key_bytes(part()) + sum(unit_bytes([record, wire]) for record, wire in corrected) + unit_bytes("auth://fresh")
    observation["nested"]["owner"] = "caller-owned"
    assert stm.read(part()).records[0][0]["nested"]["owner"] == "new"
    result.records[0][0]["keep"] = "caller-owned"
    assert stm.read(part()).records[0][0]["keep"] == "a"


@pytest.mark.parametrize("stale_cause", ["expiry", "capacity"])
def test_reconcile_never_rebuilds_stale_cache_from_its_own_records(stale_cause: str) -> None:
    clock = FakeClock()
    stm = HookStm(clock=clock, records_per_partition=2)
    stm.update(part(), rec(), 120)
    if stale_cause == "expiry":
        clock.now = 1800
    else:
        with pytest.raises(StmError):
            stm.rebuild(part(), [(rec(), 120)] * 3, [])
    result = stm.reconcile(part(), authority_state={"state": "DONE"}, authority_ref="auth://fresh")
    assert result.state == "STALE" and result.rebuild_required
    assert result.derived_degraded
    assert result.records[0][0]["state"] == "DONE"
    assert stm.rebuild(part(), [(rec("NEW"), 120)], ["auth://fresh"]).state == "FRESH"
    assert stm.read(part()).authority_ref is None
    assert not stm.read(part()).derived_degraded


def test_reconcile_missing_partition_does_not_manufacture_fresh_empty_state() -> None:
    stm = HookStm(clock=FakeClock())
    result = stm.reconcile(part(), authority_state={"state": "DONE"}, authority_ref="auth://fresh")
    assert result.state == "UNKNOWN" and result.rebuild_required
    assert result.records == ()
    assert stm.partition_count == 0 and stm.record_count == 0


@pytest.mark.parametrize("options", [{"records_per_partition": 1}, {"records_total": 1}])
def test_reconcile_pointer_capacity_rejects_atomically_and_preserves_prior_records(options) -> None:
    stm = HookStm(clock=FakeClock(), **options)
    stm.update(part(), rec(), 120)
    before = stm.read(part()).records
    with pytest.raises(StmError) as out:
        stm.reconcile(part(), authority_state={"state": "DONE"}, authority_ref="auth://fresh")
    assert out.value.code == "STM_CAPACITY_EXCEEDED"
    after = stm.read(part())
    assert after.state == "STALE" and after.rebuild_required
    assert after.records == before
    assert after.authority_ref is None
    assert stm.record_count == 1


def test_reconcile_pointer_byte_pressure_never_evicts_another_retained_partition() -> None:
    one = part()
    other = part(task_id="other")
    cap = key_bytes(one) + unit_bytes([rec(), 120]) + key_bytes(other) + unit_bytes([rec(), 120])
    stm = HookStm(clock=FakeClock(), bytes_total=cap)
    stm.update(one, rec(), 120)
    stm.update(other, rec(), 120)
    with pytest.raises(StmError) as out:
        stm.reconcile(one, authority_state={"state": "RUNNING"}, authority_ref="auth://fresh")
    assert out.value.code == "STM_CAPACITY_EXCEEDED"
    assert stm.read(one).state == "STALE"
    assert stm.read(other).state == "FRESH"
    assert stm.partition_count == 2 and stm.accounted_bytes == cap


def test_reconcile_pointer_utf8_exact_bound_and_oversize_fail_stale() -> None:
    stm = HookStm(clock=FakeClock())
    stm.update(part(), rec(), 120)
    reference = "é" * 512
    assert stm.reconcile(part(), authority_state={"state": "RUNNING"}, authority_ref=reference).state == "FRESH"
    before = stm.read(part())
    with pytest.raises(StmError) as out:
        stm.reconcile(part(), authority_state={"state": "DONE"}, authority_ref=reference + "x")
    assert out.value.code == "STM_REBUILD_INPUT_LIMIT"
    after = stm.read(part())
    assert after.state == "STALE" and after.records == before.records
    assert after.authority_ref == reference


@pytest.mark.parametrize("observation", [None, [], {"state": object()}, {"state": float("nan")},
                                          {"state": float("inf")}, {1: "invalid key"}])
def test_reconcile_invalid_observation_cannot_leave_partition_fresh(observation) -> None:
    stm = HookStm(clock=FakeClock())
    stm.update(part(), rec(), 120)
    before = stm.read(part()).records
    with pytest.raises(StmError) as out:
        stm.reconcile(part(), authority_state=observation, authority_ref="auth://fresh")
    assert out.value.code == "STM_REBUILD_INPUT_LIMIT"
    assert stm.read(part()).state == "STALE"
    assert stm.read(part()).records == before


def test_reconcile_hostile_data_methods_never_execute():
    class HostileDict(dict):
        def items(self):
            raise AssertionError("do not invoke injected object protocols")

    class HostileStr(str):
        def __eq__(self, other):
            raise AssertionError("do not invoke injected object protocols")

    stm = HookStm(clock=FakeClock())
    stm.update(part(), rec(), 120)
    for observation, reference in [(HostileDict(state="DONE"), "ref"),
                                    ({"state": HostileStr("DONE")}, "ref"),
                                    ({"nested": HostileDict(owner="new")}, "ref"),
                                    ({"state": "DONE"}, HostileStr("ref"))]:
        with pytest.raises(StmError) as out:
            stm.reconcile(part(), authority_state=observation, authority_ref=reference)
        assert out.value.code == "STM_REBUILD_INPUT_LIMIT"
    assert stm.read(part()).state == "STALE"


def test_reconcile_cyclic_deep_and_oversized_observation_fail_before_retention():
    stm = HookStm(clock=FakeClock())
    stm.update(part(), rec(), 120)
    cycle = []
    cycle.append(cycle)
    deep = None
    for _ in range(20):
        deep = [deep]
    for observation in ({"state": cycle}, {"state": deep}, {str(i): None for i in range(4097)},
                        {"state": "x" * (8 * 1024 * 1024 + 1)}):
        with pytest.raises(StmError) as out:
            stm.reconcile(part(), authority_state=observation, authority_ref="ref")
        assert out.value.code == "STM_REBUILD_INPUT_LIMIT"
    assert stm.read(part()).authority_ref is None


def test_reconciliation_pointer_and_degradation_survive_update_until_explicit_rebuild():
    stm = HookStm(clock=FakeClock())
    stm.update(part(), rec(), 120)
    stm.reconcile(part(), authority_state={"state": "DONE"}, authority_ref="auth://fresh")
    stm.update(part(), {"diagnostic": "new"}, 17)
    after = stm.read(part())
    assert after.authority_ref == "auth://fresh" and after.derived_degraded
    assert stm.record_count == 3


@pytest.mark.parametrize("derived,observed", [(1, True), (1.0, 1),
                                             ({"value": 1}, {"value": True})])
def test_reconcile_json_type_changes_are_conflicts_not_python_equality(derived, observed):
    stm = HookStm(clock=FakeClock())
    stm.update(part(), {"value": derived}, 17)
    result = stm.reconcile(part(), authority_state={"value": observed}, authority_ref="ref")
    assert result.derived_degraded
    actual = result.records[0][0]["value"]
    assert json.dumps(actual, sort_keys=True) == json.dumps(observed, sort_keys=True)


@pytest.mark.parametrize("resource", ["partition", "aggregate"])
def test_reconcile_corrected_value_growth_rejects_atomically_without_eviction(resource):
    target, other = part(), part(task_id="other")
    target_before = key_bytes(target) + unit_bytes([{"state": "x"}, 17])
    other_before = key_bytes(other) + unit_bytes([{"state": "x"}, 17])
    limit = target_before + unit_bytes("ref") + 4
    options = ({"bytes_per_partition": limit} if resource == "partition"
               else {"bytes_total": limit + other_before})
    stm = HookStm(clock=FakeClock(), **options)
    stm.update(target, {"state": "x"}, 17)
    stm.update(other, {"state": "x"}, 17)
    before = stm.read(target).records
    with pytest.raises(StmError) as out:
        stm.reconcile(target, authority_state={"state": "longer-state"}, authority_ref="ref")
    assert out.value.code == "STM_CAPACITY_EXCEEDED"
    result = stm.read(target)
    assert result.records == before and result.state == "STALE"
    assert result.authority_ref is None
    assert stm.read(other).state == "FRESH"
    assert stm.accounted_bytes == target_before + other_before
    assert stm.partition_count == 2
