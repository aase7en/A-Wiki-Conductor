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

The bus then follows the contract-owned security floor without becoming a second
schema authority: duplicate JSON object keys at any depth fail HOOK_EVENT_INVALID;
the fully parsed raw envelope is recursively scanned for Hook Contract §10
forbidden field names and §11 fake-secret-corpus strings before any projection.
It validates the transport/core invariants needed by downstream processing and
rejects unsupported major versions with HOOK_VERSION_UNSUPPORTED. Same-major
newer-minor forward projection remains an upstream accepted normalization
responsibility in STM-1A; the bus never invents or reconstructs unknown semantics.

Dedupe identity is explicit dedupe_key when present, otherwise global event_id.
Distinct event_id values are never collapsed because source/sequence match.
The consumer-owned replay window defaults to 1800 s and is clamped to
300–86400 s; dedupe state is bounded by both expiry and configured capacity.

Ordering stream identity is (source, device_id, bus-observed session_id). The
session_id is consumer context, never synthesized into the Hook envelope.
hook_bus.py owns per-stream queues, append-only emitted history and deterministic
stable k-way merge. Sequence orders only buffered events within one observed
stream; a new observed session may restart sequence. A late lower/reused sequence
never rewrites emitted history and instead appends at observed arrival with a
typed inversion/degraded marker. Cross-stream heads rank by parsed
(occurred_at_instant, source, event_id), never by raw timestamp string and never
as causal/global truth.

The bus is bounded and synchronous/deterministic in STM-1A. Saturation returns
HOOK_BACKPRESSURE and records local HOOK_STREAM_DEGRADED state without depending
on re-enqueueing an event onto the degraded stream. Shedding is observability-only:
OBSERVE/ADVISORY may be shed first; loss of GUARD-rejection/COMMAND visibility is
never silent and never re-decided by the bus. Consumer failure is isolated and
cannot block or mutate authoritative producer/task/execution truth.

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

At capacity, deterministic eviction removes expired/stale partitions first, then
the partition with the oldest monotonic refresh time; exact partition identity is
the stable tie-break. Reads do not silently extend TTL. Purge/compaction never
changes durable task/claim/execution truth.

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
4. late lower/reused sequence never rewrites emitted history; per-stream
   sequence and stable k-way merge use parsed RFC3339 instants only between heads;
5. exact incoming UTF-8 bytes at 65536 are accepted when otherwise valid and
   >65536 reject HOOK_EVENT_OVERSIZED; production object-only ingress rejects;
6. duplicate JSON keys, Hook Contract forbidden raw field names and every
   fake-secret-corpus item reject HOOK_EVENT_INVALID before downstream storage;
7. different-major version rejects HOOK_VERSION_UNSUPPORTED and newer-minor
   input is accepted only after upstream known-form normalization;
8. saturation emits HOOK_BACKPRESSURE then local HOOK_STREAM_DEGRADED without
   re-enqueue dependency; class-aware shedding never silently loses
   GUARD-rejection/COMMAND visibility and never becomes execution authority;
9. one consumer exception does not corrupt another consumer or authoritative truth;
10. injected monotonic TTL expiry returns STM_STALE while occurred_at changes do not;
11. deterministic stale-first/oldest-refresh eviction obeys configured capacity;
12. in-memory loss starts STM_REBUILD_REQUIRED and pre-rebuild reads stay
    STALE/UNKNOWN until injected authority + accepted recent-event replay succeeds;
13. authoritative contradiction is reconciled before a partition can return FRESH;
14. no network/process/Git/SQLite/task/claim/lease mutation primitive exists in STM-1A.

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
