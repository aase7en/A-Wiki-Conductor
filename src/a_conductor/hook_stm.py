"""WO-P1-547 STM-1A: bounded derived partition retention.

Split 1 covered explicit partition identity with unbound fallbacks and
UTF-8 byte-cap rejection before any allocation or retention. Split 2
adds only the monotonic TTL/freshness slice for
``test_ttl_uses_injected_monotonic_clock_with_clamp``: injected-clock
rebuild/read, default TTL 1800 s clamped to 300-86400 s inclusive,
reads that never extend TTL, and UNKNOWN/REBUILD_REQUIRED reads for
absent partitions.

Rebuild input bounds use Hook admission wire lengths and UTF-8 authority
references, with a combined item count and rejection before replacement.
Capacity counts Hook pairs and authority references as retained units,
using canonical JSON bytes plus the WO allowance and identity bytes.
New partitions may evict stale/expired then oldest-refresh partitions;
existing partition replacements reject atomically without evicting others.
Reconciliation supersedes overlapping projected values from an injected fresh
observation, retaining only its bounded reference and a degradation flag.

Authority boundary: derived in-memory observability only. This module
owns no task/claim/lease/execution/review/merge/completion truth and
contains no network, process, Git, or SQLite primitives.
"""
from __future__ import annotations

import json
import time
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Callable, Mapping, Sequence

__all__ = ["HookStm", "StmError", "StmPartition", "StmReadResult"]

_PROJECT_REF_MAX_BYTES = 256
_TASK_REF_MAX_BYTES = 256
_DEVICE_ID_MAX_BYTES = 128
_LANE_REF_MAX_BYTES = 256
_COMBINED_KEY_MAX_BYTES = 1024
_KEY_SEPARATOR = "\x1f"

_UNBOUND_TASK = "UNBOUND_TASK"
_UNBOUND_LANE = "UNBOUND_LANE"

_TTL_DEFAULT_SECONDS = 1800.0
_TTL_MIN_SECONDS = 300.0
_TTL_MAX_SECONDS = 86400.0

_REBUILD_ITEM_DEFAULT = 2048
_REBUILD_ITEM_MAX = 4096
_REBUILD_BYTE_DEFAULT = 4 * 1024 * 1024
_REBUILD_BYTE_MAX = 8 * 1024 * 1024
_AUTHORITY_REF_MAX_BYTES = 1024

_PARTITION_DEFAULT = 128
_PARTITION_MAX = 256
_PARTITION_RECORD_DEFAULT = 128
_PARTITION_RECORD_MAX = 256
_TOTAL_RECORD_DEFAULT = 2048
_TOTAL_RECORD_MAX = 4096
_PARTITION_BYTE_DEFAULT = 512 * 1024
_PARTITION_BYTE_MAX = 1024 * 1024
_TOTAL_BYTE_DEFAULT = 4 * 1024 * 1024
_TOTAL_BYTE_MAX = 8 * 1024 * 1024
_UNIT_ALLOWANCE_BYTES = 128
_AUTHORITY_MAX_DEPTH = 12  # local plain-data defense, not an authority schema


class StmError(Exception):
    """Typed STM failure; ``code`` carries the WO-P1-547 STM_* code."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class StmPartition:
    """Explicit consumer-observed partition context (raw fields only)."""

    project_ref: str
    device_id: str
    task_id: str | None = None
    work_order: str | None = None
    lane_id: str | None = None

    @property
    def task_ref(self) -> str:
        """task_id, else work_order, else visibly UNBOUND_TASK."""
        if self.task_id is not None:
            return self.task_id
        if self.work_order is not None:
            return self.work_order
        return _UNBOUND_TASK

    @property
    def lane_ref(self) -> str:
        """lane_id, else visibly UNBOUND_LANE."""
        return self.lane_id if self.lane_id is not None else _UNBOUND_LANE


@dataclass(frozen=True)
class StmReadResult:
    """Derived read outcome for one partition identity.

    ``state`` is FRESH, STALE (expired or rebuild input rejected), or
    UNKNOWN (nothing retained); ``rebuild_required`` is true for every
    non-fresh outcome. ``records`` is the retained projection.
    """

    state: str
    rebuild_required: bool
    records: tuple[tuple[dict[str, object], int], ...] = ()
    derived_degraded: bool = False
    authority_ref: str | None = None


PartitionKey = tuple[str, str, str, str]


def _partition_key(partition: StmPartition) -> PartitionKey:
    """Enforce identity byte caps, then return the resolved identity.

    Raises ``StmError("STM_PARTITION_ID_OVERSIZED")`` before the caller
    looks up or retains anything; oversize values are never truncated or
    normalized into a different identity.
    """
    components = (
        ("project_ref", partition.project_ref, _PROJECT_REF_MAX_BYTES),
        ("task_ref", partition.task_ref, _TASK_REF_MAX_BYTES),
        ("device_id", partition.device_id, _DEVICE_ID_MAX_BYTES),
        ("lane_ref", partition.lane_ref, _LANE_REF_MAX_BYTES),
    )
    for name, value, cap in components:
        if len(value.encode("utf-8")) > cap:
            raise StmError(
                "STM_PARTITION_ID_OVERSIZED",
                f"{name} exceeds {cap} UTF-8 bytes",
            )
    encoded = _KEY_SEPARATOR.join(value for _, value, _ in components)
    if len(encoded.encode("utf-8")) > _COMBINED_KEY_MAX_BYTES:
        raise StmError(
            "STM_PARTITION_ID_OVERSIZED",
            f"combined partition key exceeds {_COMBINED_KEY_MAX_BYTES} UTF-8 bytes",
        )
    return (
        partition.project_ref,
        partition.task_ref,
        partition.device_id,
        partition.lane_ref,
    )


@dataclass
class _PartitionState:
    """Owned projection data and its exact bounded accounting."""

    refreshed_at: float
    records: list[tuple[dict[str, object], int]] = field(default_factory=list)
    authority_refs: tuple[str, ...] = ()
    rebuild_required: bool = False
    accounted_bytes: int = 0
    derived_degraded: bool = False
    reconciliation_ref: str | None = None

    @property
    def unit_count(self) -> int:
        return (len(self.records) + len(self.authority_refs)
                + (1 if self.reconciliation_ref is not None else 0))


def _key_bytes(key: PartitionKey) -> int:
    return len(_KEY_SEPARATOR.join(key).encode("utf-8"))


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _owned_unit(unit: object) -> tuple[object, int]:
    """Canonical accounting also detaches nested caller-owned projection data."""
    try:
        serialized = _canonical_json(unit)
        size = len(serialized.encode("utf-8")) + _UNIT_ALLOWANCE_BYTES
        return json.loads(serialized), size
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise StmError("STM_CAPACITY_EXCEEDED") from None


def _validate_observation(observation: object) -> None:
    """Accept bounded plain facts only, without invoking injected protocols.

    This is defensive shape/size validation, not provenance or freshness
    admission. Those facts remain the injected observation owner's obligation.
    The complete mapping is never retained as an authority record.
    """
    budget = [0, 0]

    def visit(value: object, depth: int) -> None:
        budget[0] += 1
        if budget[0] > _REBUILD_ITEM_MAX or depth > _AUTHORITY_MAX_DEPTH:
            raise StmError("STM_REBUILD_INPUT_LIMIT")
        kind = type(value)
        if value is None or kind is bool:
            return
        if kind is str:
            if len(value) > _REBUILD_BYTE_MAX:
                raise StmError("STM_REBUILD_INPUT_LIMIT")
            budget[1] += len(value.encode("utf-8"))
            if budget[1] > _REBUILD_BYTE_MAX:
                raise StmError("STM_REBUILD_INPUT_LIMIT")
        elif kind is int:
            if value.bit_length() > 64:
                raise StmError("STM_REBUILD_INPUT_LIMIT")
        elif kind is float:
            if value != value or value in (float("inf"), float("-inf")):
                raise StmError("STM_REBUILD_INPUT_LIMIT")
        elif kind is dict:
            if len(value) > _REBUILD_ITEM_MAX or any(type(key) is not str for key in value):
                raise StmError("STM_REBUILD_INPUT_LIMIT")
            for key, child in value.items():
                visit(key, depth + 1)
                visit(child, depth + 1)
        elif kind is list:
            if len(value) > _REBUILD_ITEM_MAX:
                raise StmError("STM_REBUILD_INPUT_LIMIT")
            for child in value:
                visit(child, depth + 1)
        else:
            raise StmError("STM_REBUILD_INPUT_LIMIT")

    if type(observation) is not dict:
        raise StmError("STM_REBUILD_INPUT_LIMIT")
    visit(observation, 0)


class HookStm:
    """Derived, rebuildable short-term working set (partial STM-1A).

    Input admission precedes retained-state admission. Only new partitions
    may trigger deterministic eviction. This cache never becomes an authority
    or its own rebuild source. Fresh observations are explicitly injected.
    """

    def __init__(
        self,
        clock: Callable[[], float] | None = None,
        ttl_seconds: float = _TTL_DEFAULT_SECONDS,
        rebuild_item_limit: int = _REBUILD_ITEM_DEFAULT,
        rebuild_byte_limit: int = _REBUILD_BYTE_DEFAULT,
        max_partitions: int = _PARTITION_DEFAULT,
        records_per_partition: int = _PARTITION_RECORD_DEFAULT,
        records_total: int = _TOTAL_RECORD_DEFAULT,
        bytes_per_partition: int = _PARTITION_BYTE_DEFAULT,
        bytes_total: int = _TOTAL_BYTE_DEFAULT,
    ) -> None:
        # Injected monotonic clock; occurred_at never drives STM state.
        self.clock = clock if clock is not None else time.monotonic
        # Constructor TTL is clamped to the WO bounds before first use
        # and is fixed for the instance lifetime.
        self._ttl_seconds: float = max(
            _TTL_MIN_SECONDS, min(_TTL_MAX_SECONDS, float(ttl_seconds))
        )
        self._rebuild_item_limit = max(0, min(_REBUILD_ITEM_MAX, int(rebuild_item_limit)))
        self._rebuild_byte_limit = max(0, min(_REBUILD_BYTE_MAX, int(rebuild_byte_limit)))
        self._max_partitions = max(0, min(_PARTITION_MAX, int(max_partitions)))
        self._records_per_partition = max(0, min(_PARTITION_RECORD_MAX, int(records_per_partition)))
        self._records_total = max(0, min(_TOTAL_RECORD_MAX, int(records_total)))
        self._bytes_per_partition = max(0, min(_PARTITION_BYTE_MAX, int(bytes_per_partition)))
        self._bytes_total = max(0, min(_TOTAL_BYTE_MAX, int(bytes_total)))
        self._partitions: dict[PartitionKey, _PartitionState] = {}

    @property
    def partition_count(self) -> int:
        return len(self._partitions)

    @property
    def record_count(self) -> int:
        """Retained Hook pairs plus references, not durable event counts."""
        return sum(state.unit_count for state in self._partitions.values())

    @property
    def accounted_bytes(self) -> int:
        return sum(state.accounted_bytes for state in self._partitions.values())

    def _capacity_failure(self, key: PartitionKey) -> None:
        state = self._partitions.get(key)
        if state is not None:
            state.rebuild_required = True
        raise StmError("STM_CAPACITY_EXCEEDED")

    def _check_candidate(self, key: PartitionKey, count: int, size: int) -> None:
        # An irreducible candidate cannot be made admissible by eviction.
        if (count > self._records_per_partition or count > self._records_total
                or size > self._bytes_per_partition or size > self._bytes_total):
            self._capacity_failure(key)

    def _admit(self, key: PartitionKey, candidate: _PartitionState) -> None:
        self._check_candidate(key, candidate.unit_count, candidate.accounted_bytes)
        prior = self._partitions.get(key)
        count = self.record_count + candidate.unit_count
        size = self.accounted_bytes + candidate.accounted_bytes
        partitions = self.partition_count + 1
        if prior is not None:
            count -= prior.unit_count
            size -= prior.accounted_bytes
            partitions -= 1

        def fits() -> bool:
            return (partitions <= self._max_partitions and count <= self._records_total
                    and size <= self._bytes_total)

        victims = []
        if not fits():
            if prior is not None:
                self._capacity_failure(key)  # retained-target replacement never evicts
            now = candidate.refreshed_at
            ordered = sorted(
                self._partitions,
                key=lambda identity: (
                    not (self._partitions[identity].rebuild_required
                         or now - self._partitions[identity].refreshed_at >= self._ttl_seconds),
                    self._partitions[identity].refreshed_at,
                    identity,
                ),
            )
            for identity in ordered:
                victims.append(identity)
                victim = self._partitions[identity]
                count -= victim.unit_count
                size -= victim.accounted_bytes
                partitions -= 1
                if fits():
                    break
        if not fits():
            self._capacity_failure(key)
        # Prepare all removals and insertion away from live state, then swap.
        # A failed plan/copy never leaves partial eviction or replacement.
        replacement = self._partitions.copy()
        for identity in victims:
            del replacement[identity]
        replacement[key] = candidate
        self._partitions = replacement

    def update(
        self,
        partition: StmPartition,
        record: Mapping[str, object],
        wire_bytes: int,
    ) -> None:
        """Accept one derived projection record under an explicit identity.

        Rejection preserves prior target records but marks them stale; a
        missing target remains absent. The retained-target path never evicts.
        """
        key = _partition_key(partition)
        prior = self._partitions.get(key)
        count = (prior.unit_count if prior is not None else 0) + 1
        size = prior.accounted_bytes if prior is not None else _key_bytes(key)
        self._check_candidate(key, count, size)
        if type(wire_bytes) is not int or wire_bytes < 0:
            self._capacity_failure(key)
        try:
            pair, unit_bytes = _owned_unit([dict(record), wire_bytes])
        except StmError:
            self._capacity_failure(key)
        self._check_candidate(key, count, size + unit_bytes)
        candidate = _PartitionState(
            refreshed_at=self.clock(),
            records=(list(prior.records) if prior is not None else []) + [(pair[0], pair[1])],
            authority_refs=prior.authority_refs if prior is not None else (),
            rebuild_required=prior.rebuild_required if prior is not None else False,
            accounted_bytes=size + unit_bytes,
            derived_degraded=prior.derived_degraded if prior is not None else False,
            reconciliation_ref=prior.reconciliation_ref if prior is not None else None,
        )
        self._admit(key, candidate)

    def rebuild(
        self,
        partition: StmPartition,
        hook_records: Sequence[tuple[Mapping[str, object], int]],
        authority_refs: Sequence[str],
    ) -> StmReadResult:
        """Replace one partition's derived working set from replay input.

        The refresh instant is the injected monotonic clock at rebuild
        time; hook-record ``occurred_at`` values are presentation
        metadata and never drive freshness. Input bounds count Hook records
        plus authority references, and original wire lengths plus reference
        UTF-8 bytes only. Rejection retains old records as STALE and does not
        create a missing partition. Explicit rebuild resets reconciliation
        metadata; this method never uses STM itself as its replay source.
        """
        key = _partition_key(partition)
        input_limited = len(hook_records) + len(authority_refs) > self._rebuild_item_limit
        input_bytes = 0
        if not input_limited:
            for _, wire_bytes in hook_records:
                # Measured wire lengths must not lower or corrupt the total.
                if type(wire_bytes) is not int or wire_bytes < 0:
                    input_limited = True
                    break
                input_bytes += wire_bytes
                if input_bytes > self._rebuild_byte_limit:
                    input_limited = True
                    break
        if not input_limited:
            for reference in authority_refs:
                reference_bytes = len(reference.encode("utf-8"))
                input_bytes += reference_bytes
                if (
                    reference_bytes > _AUTHORITY_REF_MAX_BYTES
                    or input_bytes > self._rebuild_byte_limit
                ):
                    input_limited = True
                    break
        if input_limited:
            state = self._partitions.get(key)
            if state is not None:
                state.rebuild_required = True
            raise StmError("STM_REBUILD_INPUT_LIMIT")
        count = len(hook_records) + len(authority_refs)
        size = _key_bytes(key)
        self._check_candidate(key, count, size)
        records = []
        references = []
        try:
            for record, wire_bytes in hook_records:
                pair, unit_bytes = _owned_unit([dict(record), wire_bytes])
                size += unit_bytes
                self._check_candidate(key, count, size)
                records.append((pair[0], pair[1]))
            for reference in authority_refs:
                owned, unit_bytes = _owned_unit(reference)
                size += unit_bytes
                self._check_candidate(key, count, size)
                references.append(owned)
        except StmError:
            self._capacity_failure(key)
        candidate = _PartitionState(
            refreshed_at=self.clock(),
            records=records,
            authority_refs=tuple(references),
            accounted_bytes=size,
        )
        self._admit(key, candidate)
        return StmReadResult(
            state="FRESH",
            rebuild_required=False,
            records=tuple(deepcopy(records)),
        )

    def reconcile(
        self,
        partition: StmPartition,
        *,
        authority_state: Mapping[str, object],
        authority_ref: str,
    ) -> StmReadResult:
        """Supersede conflicting projected values before returning a view.

        The caller supplies an admitted fresh observation; this method neither
        reads authority nor proves freshness. Only already-projected overlapping
        fields are corrected. No Hook is appended, unrelated field introduced,
        or full authority mapping retained (WO interpretation #547:5985972194).
        Keep one latest pointer as a counted reference unit, not pointer history.
        Missing/stale caches still require explicit authority-bound rebuild and
        replay. Capacity failure preserves prior records as STALE atomically.
        """
        key = _partition_key(partition)
        prior = self._partitions.get(key)
        try:
            if (type(authority_ref) is not str or not authority_ref
                    or len(authority_ref.encode("utf-8")) > _AUTHORITY_REF_MAX_BYTES):
                raise StmError("STM_REBUILD_INPUT_LIMIT")
            _validate_observation(authority_state)
        except (StmError, UnicodeError):
            if prior is not None:
                prior.rebuild_required = True
            raise StmError("STM_REBUILD_INPUT_LIMIT") from None
        if prior is None:
            return StmReadResult("UNKNOWN", True)
        count = prior.unit_count + (1 if prior.reconciliation_ref is None else 0)
        self._check_candidate(key, count, _key_bytes(key))
        records = []
        size = _key_bytes(key)
        degraded = prior.derived_degraded
        try:
            for projection, wire_bytes in prior.records:
                corrected = deepcopy(projection)
                for name, observed in authority_state.items():
                    if name in corrected and _canonical_json(corrected[name]) != _canonical_json(observed):
                        corrected[name] = observed
                        degraded = True
                pair, measured = _owned_unit([corrected, wire_bytes])
                size += measured
                self._check_candidate(key, count, size)
                records.append((pair[0], pair[1]))
            for reference in (*prior.authority_refs, authority_ref):
                _, measured = _owned_unit(reference)
                size += measured
                self._check_candidate(key, count, size)
        except StmError:
            self._capacity_failure(key)
        now = self.clock()
        candidate = _PartitionState(
            refreshed_at=now, records=records, authority_refs=prior.authority_refs,
            rebuild_required=(prior.rebuild_required
                              or now - prior.refreshed_at >= self._ttl_seconds),
            accounted_bytes=size, derived_degraded=degraded,
            reconciliation_ref=authority_ref,
        )
        self._admit(key, candidate)
        return self.read(partition)

    def read(self, partition: StmPartition) -> StmReadResult:
        """Read one partition's derived working set without extending TTL.

        Absent partitions read UNKNOWN/REBUILD_REQUIRED; a retained
        partition is STALE after rejected rebuild input or once monotonic
        age >= the effective TTL.
        Reads never refresh or otherwise mutate retained state.
        """
        key = _partition_key(partition)
        state = self._partitions.get(key)
        if state is None:
            return StmReadResult(
                state="UNKNOWN", rebuild_required=True, records=()
            )
        age = self.clock() - state.refreshed_at
        if state.rebuild_required or age >= self._ttl_seconds:
            return StmReadResult(
                state="STALE",
                rebuild_required=True,
                records=tuple(deepcopy(state.records)),
                derived_degraded=state.derived_degraded,
                authority_ref=state.reconciliation_ref,
            )
        return StmReadResult(
            state="FRESH",
            rebuild_required=False,
            records=tuple(deepcopy(state.records)),
            derived_degraded=state.derived_degraded,
            authority_ref=state.reconciliation_ref,
        )
