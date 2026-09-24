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

The bus consumes a Hook Contract frame that is already normalized by an
accepted adapter/boundary. It MUST NOT reimplement the full JSON Schema.

It defensively validates only transport invariants required for safe bounded
delivery: mapping shape, schema version, bounded serialized size, event_id,
optional dedupe_key, occurred_at, source/device stream identity, hook_class,
and ordering inputs required by Hook Contract v1.

Dedupe key = explicit contract dedupe_key when present, otherwise global event_id.
Distinct event_id values are never collapsed merely because source/sequence match.
Late/out-of-order events remain observable; they do not rewrite authoritative truth.

The bus is bounded and synchronous/deterministic in STM-1A. Capacity exhaustion
returns typed HOOK_BACKPRESSURE; it does not block or mutate the authoritative
producer record. Consumer failure is isolated and typed as observability degradation.

## STM semantics

STM partitions only derived working state needed by later monitor projection.
Every partition has bounded capacity and explicit freshness metadata.
TTL expiry yields STM_STALE/UNKNOWN projection; it never changes authoritative state.
Eviction is deterministic and bounded. Loss/restart yields STM_REBUILD_REQUIRED.
Rebuild consumes accepted authoritative/event references; STM is never its own source.

When STM conflicts with a fresh authoritative observation, authority wins
deterministically and the stale STM value is replaced/marked degraded rather than
being used to authorize mutation, retry, merge, completion or ownership.
## Failure matrix / RED obligations

Before implementation prove RED for:
1. duplicate delivery is idempotent;
2. distinct event_id with same source/sequence is retained;
3. out-of-order/late event remains bounded and deterministically ordered;
4. invalid or oversized frame is rejected typed;
5. queue saturation returns HOOK_BACKPRESSURE with no authority side effect;
6. one consumer exception does not corrupt another consumer/authoritative truth;
7. TTL expiry returns STM_STALE;
8. eviction is bounded/deterministic;
9. in-memory loss requires STM_REBUILD_REQUIRED and reconstructs from injected authority;
10. authoritative contradiction wins over derived STM;
11. secret/fake-secret corpus never appears in STM projection;
12. no network/process/Git/SQLite/task/claim/lease mutation primitive exists in STM-1A.

## Verification / acceptance

- focused RED/GREEN tests for both new modules;
- Hook Contract schema/control-hook regressions remain green;
- cockpit projection regressions remain green without modification;
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
