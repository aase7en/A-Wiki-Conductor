# WO-P1-547 — STM-1 bounded Hook Bus + derived in-memory STM

Status: SHAPING / SOURCE BLOCKED
Issue: #547
Topology: CONTROL_PLANE_ONLY
Risk: R3
Claim: WO-P1-547-STM1-HOOK-BUS-MAC-001
Base: c4d4cf4da830cb313a4569a386edcff0a77266c2
Worktree: /Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo547-stm1
Branch: docs/wo-p1-547-stm1-hook-bus

## Objective

Deliver roadmap P5 as a bounded observability pipeline:
normalized Hook Contract events -> bounded in-process bus -> derived rebuildable
short-term working set. Bus/STM loss must never change task, claim, lease,
execution, review, merge, release, or completion truth.

This WO is the authority boundary for P5 shaping. The bootstrap claim permits
only this file. Product/source mutation requires a second mutation gate after
the source scope below is independently challenged and frozen.

## Predecessors / authority

- WO-P1-257 roadmap defines P5 before MON-1/UI-1/ACT-1.
- Hook Contract v1 owns envelope semantics, dedupe identity and ordering rules.
- WO-P1-383 control normalization projects accepted ControlEvent truth to OBSERVE.
- WO-P1-375/376 harness adapters are OBSERVE-only and grant no task authority.
- WO-P1-389 preserves SRM native event truth; normalization failure is visibility degradation.
## Reuse decision

REUSE:
- Hook Contract v1 global event_id / optional dedupe_key semantics;
- accepted normalized OBSERVE envelopes and redaction constraints;
- existing durable control/execution records as factual authority;
- cockpit_projection.py as a later read-only consumer pattern.

EXTEND:
- one bounded in-process Hook Bus;
- one derived in-memory STM working set.

FORBIDDEN:
- another event/task/job/claim/lease/retry/review/completion store;
- persistent STM database in STM-1A;
- scheduler or command gateway;
- producer/adaptor rewrites merely to feed this bus;
- Web/Extension/remote API;
- raw prompts, secrets, credential values or raw command lines.

## Minimal architecture

STM-1A is pure core only. Candidate source scope:
- NEW src/a_conductor/hook_bus.py
- NEW src/a_conductor/hook_stm.py
- NEW tests/test_hook_bus.py
- NEW tests/test_hook_stm.py
- this Work Order

No __init__.py export is required for the first slice. No existing producer,
adapter, event store, cockpit or UI source is modified by STM-1A.
## Contract boundary

The production bus ingress accepts the **exact UTF-8 serialized bytes** emitted
across the Hook Bus seam plus explicit consumer-observed session context. An
object-only call is test/helper scope only and is not production conformance.
Before parsing, the bus enforces the Hook Contract v1 65536-byte MUST cap on
those exact incoming bytes; it never reserializes a parsed object to prove size.

Hook Contract v1 and its published schema remain the sole normative authority;
the bus is its consumer implementation, not a second schema authority. At this
production ingress seam the bus owns execution of the complete normative §7.4
algorithm against the exact bytes: byte bound, strict UTF-8 and duplicate-aware
parse, raw-envelope security scan, version/mode selection, newer-minor optional
projection, strict validation against the known schema, and semantic checks.
There is no assumed or unnamed upstream-normalization boundary. An existing
accepted runtime validator may be called if it implements this exact contract;
otherwise STM-1A must implement the consumer algorithm at this seam and
cross-check it against the normative conformance tests. Production ingress
rejects parsed-object/pre-normalized-object calls because they cannot prove the
wire-byte/security ordering. Oversize input returns HOOK_EVENT_OVERSIZED;
duplicate-key, malformed, raw-security, strict-schema, or semantic failures
return HOOK_EVENT_INVALID; unsupported major versions return
HOOK_VERSION_UNSUPPORTED. Raw security scanning always precedes dropping
unknown optional fields.

Dedupe identity is explicit dedupe_key when present, otherwise global event_id.
Distinct event_id values are never collapsed because source/sequence match.
The consumer-owned replay window defaults to 1800 s and is clamped to
300–86400 s; dedupe state is bounded by expiry, entry count, and accounted
bytes. Expired entries may be purged before admission. An unexpired identity is
never evicted to make room: if the dedupe budget is full, the new input is
rejected as HOOK_BACKPRESSURE and is not marked accepted/deduped.

Ordering stream identity is (source, device_id, bus-observed session_id). The
session_id is consumer context, never synthesized into the Hook envelope.
hook_bus.py owns bounded per-stream queues and deterministic stable k-way merge;
sequence orders only buffered events within one observed stream, and a new
observed session may restart sequence. A late lower/reused sequence never
rewrites output already returned by a prior drain; it is returned at observed
arrival with a typed inversion/degraded marker. Cross-stream heads rank by
parsed (occurred_at_instant, source, event_id), never by raw timestamp string
and never as causal/global truth. The bus does not keep an unbounded in-memory
emitted-history list: emitted records are immutable drain results, and any
retained recent projection belongs to the separately bounded STM below.

## Resource bounds and overload behavior

These are conservative STM-1A defaults and hard maxima. Constructor settings
may be lowered but MUST be rejected or clamped if they exceed the hard maximum.
Changing a maximum requires a separate Work Order with soak/load evidence.

| Bus resource | Default | Hard maximum / rule |
|---|---:|---|
| observed stream records | 128 | 128 per bus instance |
| queued events per stream | 128 | 128 |
| queued UTF-8 bytes per stream | 2 MiB | 2 MiB |
| queued events across all streams | 4096 | 4096 |
| queued exact wire bytes across all streams | 16 MiB | 16 MiB |
| unexpired dedupe identities | 8192 | 8192 entries and 1 MiB accounted identity bytes |
| retained emitted history | 0 | no internal event-history list; drain output is bounded by the queue caps |

Queued-byte accounting uses the original accepted wire-byte length, never a
reserialized object. Dedupe identity byte accounting uses UTF-8 identity bytes
plus a documented fixed record allowance; both the byte and entry caps apply.
The stream table, queue metadata, and per-stream degradation fields are all
bounded by the stream cap. Fixed-size aggregate counters may record saturation;
they MUST NOT retain arbitrary identities for streams that could not be
admitted.

No accepted queued event is evicted to make room. If any stream, per-stream,
aggregate queue, byte, or dedupe cap would be exceeded, reject that input as
HOOK_BACKPRESSURE, report HOOK_STREAM_DEGRADED through the bounded local
degradation state, and leave existing queues and unexpired dedupe identities
unchanged. A stream-cap rejection MUST NOT allocate a stream entry. Do not
depend on re-enqueueing a degradation event onto the full/degraded queue.
Stream records are retained while their consumer-observed sessions remain
active so sequence high-water state is not silently discarded. The bus may
retire a stream only after the existing session observer reports that exact
session ended and its queue is drained; a retired session identity must not be
reintroduced by that observer. Active-stream count then falls and new observed
sessions may be admitted. If the observer cannot prove session end, retain the
record and fail closed at the stream cap.
There is no silent shedding in STM-1A. OBSERVE/ADVISORY may be prioritized for
future shedding only in a separately reviewed scope; GUARD-rejection/COMMAND
visibility is never silently lost or re-decided by the bus. Consumer failure
is isolated and cannot block or mutate authoritative producer/task/execution
truth. Initial fail-closed saturation behavior may reduce observability until
bounded state drains or the in-memory bus is rebuilt; it never changes task
authority.

## STM semantics

STM partitions only derived working state needed by later monitor projection.
The partition identity is explicit consumer context:
(project_ref, task_ref, device_id, lane_ref). project_ref comes from the accepted
A-Sunday lane/project binding, not from a new Hook envelope field; task_ref uses
task_id then work_order then UNBOUND_TASK; lane_ref uses lane_id then UNBOUND_LANE.
Missing optional identity therefore remains visibly unbound rather than inferred.

TTL/freshness uses an injected monotonic clock at bus acceptance or authoritative
rebuild/reconciliation time. Envelope occurred_at is presentation/interleave
metadata only and never drives freshness, expiry or authority. Default TTL and
per-partition capacity are constructor/config inputs with bounded clamps and are
fully controllable by a fake clock in tests.

STM-1A uses these conservative defaults and hard maxima:

| STM resource | Default | Hard maximum / rule |
|---|---:|---|
| retained partitions | 128 | 256 |
| projection records per partition | 128 | 256 |
| projection records across all partitions | 2048 | 4096 |
| accounted projected bytes per partition | 512 KiB | 1 MiB |
| accounted projected bytes across STM | 4 MiB | 8 MiB |
| records in one authoritative rebuild input | 2048 | 4096 |
| exact bytes in one rebuild input | 4 MiB | 8 MiB |

Accounted projected bytes are measured with one deterministic compact UTF-8
encoding of the bounded, already-sanitized projection plus a fixed per-record
allowance. This internal accounting is not evidence of the original Hook wire
size. Rebuild input includes accepted recent Hook records and authority/result
references; each reference is capped at 1024 UTF-8 bytes. Configuration may be
lowered, never raised above these maxima. Reads do not silently extend TTL.

At capacity, deterministic eviction removes expired/stale partitions first, then
the partition with the oldest monotonic refresh time; exact partition identity
is the stable tie-break. Every eviction removes only derived STM state and makes
a subsequent cache miss UNKNOWN/REBUILD_REQUIRED until rebuilt; it must never
look like a fresh empty partition. If the incoming record still cannot fit its
per-partition or aggregate count/byte budget, reject it with
STM_CAPACITY_EXCEEDED and mark an already-retained affected partition
STALE/REBUILD_REQUIRED. A new partition that cannot be admitted remains absent,
and a read for it is UNKNOWN. If a rebuild exceeds either input cap, return
STM_REBUILD_INPUT_LIMIT without truncating input and keep reads
STALE/UNKNOWN/REBUILD_REQUIRED. Purge, compaction, eviction, and rejected updates
never change durable task/claim/execution truth.

Loss/restart begins in STM_REBUILD_REQUIRED. Until an injected authoritative
re-read plus accepted recent-event replay completes, reads return explicit
STALE/UNKNOWN/REBUILD_REQUIRED state and never an empty-as-fresh projection.
Rebuild input is authority/result references plus accepted recent Hook events;
STM is never its own rebuild source.

Authority reconciliation runs before a partition may be returned FRESH whenever
a fresh authoritative observation is supplied. If derived STM conflicts, the
authoritative observation wins immediately; conflicting derived fields are
superseded/marked degraded and cannot authorize mutation, retry, merge,
completion or ownership. The injected authoritative reference/revision used for
that reconciliation is retained only as a bounded pointer/digest, never copied
as a second authority record.
## Failure matrix / RED obligations

Before implementation prove RED for:
1. same event_id / deliberate dedupe_key redelivery is idempotent inside the
   consumer-owned replay window; the default is 1800 s, clamp 300–86400 s,
   and dedupe memory is capacity-bounded as well as time-bounded;
2. distinct event_id values with the same source/sequence are retained;
3. sequence restart under a new bus-observed session is not a duplicate;
4. late lower/reused sequence never rewrites previously returned drain output; per-stream
   sequence and stable k-way merge use parsed RFC3339 instants only between heads;
5. exact incoming UTF-8 bytes at 65536 are accepted when otherwise valid and
   >65536 reject HOOK_EVENT_OVERSIZED; production object-only ingress rejects;
6. duplicate JSON keys, Hook Contract forbidden raw field names and every
   fake-secret-corpus item reject HOOK_EVENT_INVALID before downstream storage;
7. different-major version rejects HOOK_VERSION_UNSUPPORTED and newer-minor
   input is security-scanned, projected, strictly validated, and semantically
   checked by the normative §7.4 consumer algorithm before acceptance;
8. saturation emits HOOK_BACKPRESSURE and local HOOK_STREAM_DEGRADED without
   re-enqueue dependency; STM-1A sheds no class silently and never becomes
   execution authority;
9. one consumer exception does not corrupt another consumer or authoritative truth;
10. injected monotonic TTL expiry returns STM_STALE while occurred_at changes do not;
11. deterministic stale-first/oldest-refresh eviction obeys configured capacity;
12. in-memory loss starts STM_REBUILD_REQUIRED and pre-rebuild reads stay
    STALE/UNKNOWN until injected authority + accepted recent-event replay succeeds;
13. authoritative contradiction is reconciled before a partition can return FRESH;
14. no network/process/Git/SQLite/task/claim/lease mutation primitive exists in STM-1A.
15. every stream/per-stream/global queue and byte cap is enforced at the exact
    boundary; overflow returns HOOK_BACKPRESSURE without accepting or evicting
    an existing queued event, and a new over-cap stream allocates no stream row;
16. dedupe saturation purges expired identities only, never evicts an unexpired
    identity, and rejects the incoming event with HOOK_BACKPRESSURE;
17. repeated drains do not retain an unbounded history, and a late inversion
    appends to caller-observed output without modifying an earlier drain result;
18. STM partition, per-partition, aggregate, and rebuild record/byte caps are
    exercised at, below, and above their bounds; over-limit rebuilds are never
    truncated into a FRESH result;
19. capacity eviction/rejection is deterministic and every subsequent missing
    or evicted-partition read is UNKNOWN/REBUILD_REQUIRED until authority-bound
    rebuild succeeds.

## Independent R3 shaping review checkpoint

Exact docs candidate 7f043e532d8dde4b6b70427170da7c4a899022ff was reviewed
read-only by GLM-5.3 MAX through Sunday execution exec-mufu0ecz-9x37cx6n.
Verified exit code was 0; verdict NEEDS_FIX (P0=0, P1=3, P2=3, P3=2).

The blocking findings were accepted and repaired in this WO before any source
authorization: exact-byte/security ingress, observed-session ordering/merge
ownership, deterministic STM partition/TTL/freshness/eviction/rebuild,
bounded replay/dedupe, typed backpressure/degradation, and fail-stale
post-loss reads. The proposed NEW-only STM-1A path set is unchanged.
A fresh exact-SHA rereview is required; the first review is not acceptance.

## Verification / acceptance

- record the mandatory DEFECT_LESSONS.md read before any src/a_conductor mutation;
- focused RED/GREEN tests for both new modules;
- Hook Contract schema/control-hook regressions remain green;
- cockpit projection regressions remain green without modification;
- full repository test suite green on the frozen source candidate;
- py_compile + git diff --check + strict UTF-8/U+FFFD scan;
- exact changed-path set equals frozen STM-1A scope;
- added-line secret scan clean;
- freeze exact candidate SHA;
- independent R3 exact-SHA review plus hosted CI;
- Sol exact-SHA acceptance, expected-head merge and post-main verification.

## Successor boundary

STM-1B may wire accepted producers to the core only after STM-1A acceptance and
must receive a separate claim/scope. P6 MON-1 then consumes the derived projection.
P8 ACT-1 Command Gateway remains a later authority seam; P5 never grants it.
#498B/C/D remain blocked on that accepted centralized action seam, not on STM itself.
