# WO-P1-500 — MSP-2 atomic multi-session hotspot admission

Status: SHAPING / SOURCE NOT AUTHORIZED
Issue: #500
Parent: #475 — Multi-Session Provenance & Collision Hardening
Related consumer: #498 — A-Faster executable GUARD enforcement
Topology: CONTROL_PLANE_ONLY
Risk: R3 — concurrent mutation ownership / claim / fencing / replay safety
Reuse classification: EXTEND

## Binding

Authority repo: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo500-msp2-shaping`
Branch: `docs/wo-p1-500-msp2-atomic-admission`
Base: `29183fed35188df4723593311ed2e0f86c3bb049`

Phase-0 mutable scope:
- `docs/work-orders/WO-P1-500-msp2-atomic-admission.md`

Everything else is read-only until an exact implementation slice is accepted.

## Goal

Close the multi-session observe -> claim/admit -> writer-launch race so two
independent A-Faster/ChatGPT integrators that target the same mutable hotspot
cannot both become material mutation owners.

Required result:
- one transactional/fenced admission winner per mutable hotspot;
- loser gets typed conflict/attach/recovery outcome and launches no writer;
- disjoint hotspots may proceed in parallel within global WIP;
- release/recovery permits later takeover only after actual authority release;
- ambiguous/unknown authority fails closed.

## Authority boundary

MSP-2 does NOT create:
- a session-lock DB;
- browser/Extension lock;
- a new claim store;
- a scheduler;
- retry/completion/review authority;
- a second task DB or control plane.

It reuses existing A-Wiki claim identity plus A-Conductor worker lease/fencing
mechanics. Origin/session provenance is context only and never owns admission.

## Existing atomic seam — REUSE

`src/a_conductor/worker_lease.py` already provides the strongest durable
transaction boundary found in shaping:

`WorkerLeaseStore.try_acquire_result(...)`:
- opens SQLite `BEGIN IMMEDIATE`;
- reuses the exact session/task owner when the request matches;
- blocks a worker that already has an active lease;
- respects provisioning reservations;
- for MUTATION requests, reads active mutation leases and rejects overlapping
  `mutable_scope` via `write_sets_overlap(...)`;
- inserts the lease in the same transaction;
- commits only after all fences pass;
- has active-worker and active-owner/task UNIQUE indexes;
- returns typed no-lease or raises typed `MUTABLE_SCOPE_OVERLAP` rather than
  launching work itself.

Existing tests already prove:
- two workers cannot atomically lease overlapping mutable scope;
- the store conflict is typed and the broker does not bypass it;
- non-overlapping mutation scopes can lease different workers;
- conflicting re-acquire/request drift fails.

This is the authority substrate to EXTEND, not replace.

## Gap to prove

Current mutation-overlap query is scoped to:

`released_at IS NULL AND worktree_key = <candidate worktree> AND mutation_intent = MUTATION`

Therefore current accepted behavior clearly fences overlapping scopes inside one
normalized worktree identity.

MSP-2 must determine the accepted **project/repository hotspot identity** for
two distinct worktrees/sessions that still target the same logical mutable
hotspot. It must not guess that two worktree paths imply independent authority.

The shaping question is whether to:
1. extend the existing lease record/schema with a canonical repo/hotspot key;
2. derive a stable hotspot/fence key from already-accepted project/repo/worktree
   identity without schema growth; or
3. reuse an existing accepted claim-generation/binding key that already spans
   worktrees.

No source/schema choice is authorized until read-only impact analysis + RED
design proves which option preserves existing lease compatibility.

## Relationship to execution dedupe

`DuplicateExecutionGuard` is not the atomic hotspot authority:
- it assesses durable execution fingerprints;
- it owns no launch/retry/claim authority;
- its execution-store fingerprint index is non-unique;
- assessment followed by launch is check-then-act under concurrent sessions.

MSP-2 runs at the claim/lease/fencing layer. Execution dedupe remains a second,
downstream protection against equivalent executions.

## Relationship to #498 GUARD

#498 PRE_DISPATCH GUARD consumes MSP-2 admission truth.

Order for a fresh material writer:
1. recover authoritative state;
2. bind exact task/claim/repo/worktree/HEAD/scope;
3. acquire/confirm MSP-2 atomic hotspot admission;
4. run execution dedupe / attach-reuse checks;
5. run required executable PRE_DISPATCH GUARD;
6. only then create/launch a fresh execution.

#498 must not implement its own admission store or claim algorithm.

## Required admission identity

The final contract must bind enough authority to prevent false aliasing and
false independence. At minimum shaping must account for:
- project ID;
- authority/target repo identity;
- task/work-order/claim identity;
- branch and exact expected HEAD where material;
- canonical mutable hotspot/write set;
- worker/runtime owner;
- lease generation/fence generation if existing authority exposes one;
- mutation intent.

Origin chat/session reference is explicitly excluded from ownership identity.

## Failure model

Fail closed on:
- same-hotspot active admission by another owner;
- stale expected HEAD;
- stale/expired/quarantined lease that has not been reconciled;
- ambiguous project/repo/hotspot identity;
- claim/lease owner mismatch;
- worktree/repo identity mismatch;
- unknown transaction/store outcome;
- crash/restart where release cannot be proven;
- inconsistent projection vs durable lease truth.

Transport/UI/session loss never releases authority.

## RED/adversarial matrix

Before implementation, failing tests must cover:

1. two independent sessions race for same hotspot across different workers =>
   exactly one winner;
2. race uses two independent DB connections/process-equivalent callers;
3. loser creates no second lease and receives typed conflict/attach outcome;
4. loser cannot create execution record or invoke backend launch in integration
   with the supervised dispatch path;
5. same mutable write set in two different worktree paths that map to the same
   logical repo/hotspot => one winner;
6. truly disjoint hotspots admit concurrently within WIP;
7. stale HEAD fails closed;
8. task/claim/request drift fails closed;
9. expired lease does not become reusable until accepted recovery/release rules
   say so;
10. crash after admission before launch leaves recoverable fenced truth;
11. released lease permits valid later takeover;
12. chat/session loss alone does not release lease;
13. DB restart preserves active fence;
14. scope wildcard/path normalization cannot bypass overlap;
15. Windows path/case normalization cannot create two hotspot identities;
16. origin provenance changes do not affect ownership/admission;
17. Hook Bus/STM/Monitor loss cannot change winner;
18. no new task/claim/session-lock store appears.

## Phase plan

### MSP-2A — hotspot identity / atomic lease contract

Read-only design then minimal worker-lease extension if required. Freeze the
canonical hotspot/fence identity and transactional behavior.

### MSP-2B — A-Faster/supervised admission integration

Require accepted admission before any fresh material writer dispatch. Compose
with #498 PRE_DISPATCH GUARD and existing execution dedupe.

### MSP-2C — fault/recovery/takeover proof

Crash/restart, release/takeover, stale lease, ambiguous state and multi-process
race tests.

## Phase-0 acceptance

- docs-only diff;
- actual lease/store/test seams cited;
- independent read-only shaping/adversarial challenge;
- no source/schema mutation;
- no shadow authority design;
- exact implementation scope frozen only after advisory findings are folded.

## Future source gate

Before any `src/a_conductor/` mutation:
- read `DEFECT_LESSONS.md`;
- re-pin then-current main and open claims;
- prove no overlapping lease/store schema owner;
- freeze exact source/test/schema scope;
- dispatch GLM-5.3 MAX under R3;
- deterministic race/fault suites;
- independent exact-SHA MAX review + hosted CI;
- expected-head merge + post-main verification.
