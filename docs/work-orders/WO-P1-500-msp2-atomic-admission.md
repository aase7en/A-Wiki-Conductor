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

## Current-state advisory adjudication (Flash / 2026-09-23)

The read-only GLM-5.3-Flash current-state challenge returned
`ADVISORY_PASS (conditional)` on exact HEAD
`256f8812c78aa7ce04011a6c04448364b5dad729`. The following P1 decisions are
now frozen for the next shaping step; they do **not** yet authorize source
mutation.

### P1-1 — takeover authority

MSP-2A does **not** add cross-session takeover. Existing owner-only release/
reconcile semantics remain fail-closed. A dead owner may leave a lease stale or
quarantined, but a foreign session does not gain release/takeover authority.
Typed takeover belongs to MSP-2C after an accepted claim-generation/recovery
authority is identified. Chat/origin provenance never grants takeover.

### P1-2 — lease-store identity / split authority

MSP-2A makes a deliberately bounded claim: one-winner atomicity applies only
among callers sharing the same accepted local WorkerLease SQLite authority.
It must not describe a second SQLite path as the same authority. The store
identity must be observable/bindable for #498 and later integration rather than
silently re-derived by each guard. A durable global/cross-device claim remains
A-Wiki `repo_coordination_claim` authority, not WorkerLease.

The first source slice may add a stable read-only store identity if needed to
prove same-store binding, but must not create another DB or registry. Any
unresolved/mismatched store identity is fail-closed.

### P1-3 — legacy / NULL hotspot identity and mixed versions

A new binary must never treat an active mutation row with missing/legacy
`hotspot_key` as independent. Such a row blocks/requires reconciliation rather
than creating an unfenced path. Additive migration must preserve existing rows
and explicit-column readers/writers.

Concurrent old/new writer binaries cannot be advertised as providing the new
cross-worktree atomic guarantee because an old writer does not understand the
new hotspot fence. Deployment/compatibility therefore has an explicit
homogeneous-writer gate: until all mutation admission writers understand the
new fence, enforcement state remains partial/fail-closed rather than
`GUARD_ENFORCED` globally.

Concurrent initialization/migration and active legacy rows require deterministic
tests before source acceptance.

### P1-4 — session namespace

`WorkerLease.session_id` is the A-Sunday control-plane lease-owner session
identity, not a ChatGPT conversation/origin provenance identifier. MSP-1 origin
refs remain observational. Chat/session loss does not rewrite lease ownership;
recovery/takeover must use accepted durable lease/claim authority.

### MSP-2A bounded guarantee

MSP-2A targets **same accepted local store + same logical Git repository
hotspot + overlapping mutable scope => at most one active mutation lease**.
It does not claim:

- cross-device atomicity;
- global WIP counting;
- automatic foreign-session takeover;
- claim-generation convergence;
- protection from an old binary that bypasses the new fence;
- #498 PRE_DISPATCH GUARD semantics.

Those boundaries remain separate accepted authorities/phases.

### Canonical hotspot direction

The leading candidate is a digest of the canonical physical Git common
directory, because separate worktrees of one logical repository share that
directory while unrelated repositories do not. Resolution must occur before
the SQLite write transaction and use an injectable resolver for deterministic
tests. Reuse existing DEX final-path/canonical-digest semantics rather than
creating a fourth path-normalization authority.

`project_id` is not included in the physical repo hotspot key because it is an
operator/control grouping, not Git physical identity; two project IDs pointing
at the same physical repository must not create false independence.

Windows mutable-scope case semantics remain a separate decision and must be
frozen/tested before MSP-2A source mutation; do not silently change historical
`write_sets_overlap()` behavior inside the hotspot-identity change.

### Additional required REDs before source authorization

- real two-process same-DB race;
- distinct worktree paths sharing one Git common-dir + overlapping scope;
- junction/reparse/case/separator alias convergence for hotspot identity;
- store-path/identity mismatch fail-closed;
- active legacy NULL-hotspot row blocks new mutation admission;
- concurrent initialize/additive migration;
- old-reader/new-row compatibility plus explicit mixed-writer limitation;
- ambiguous SQLite write result never authorizes launch;
- stale HEAD after lease admission remains #498/reverification responsibility;
- owner-death/takeover remains blocked until MSP-2C authority exists.

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

## MSP-2A implementation checkpoint (2026-09-23)

Status: SOURCE SLICE IMPLEMENTED — candidate frozen for independent review.

Binding: worktree `A:\GitHub\_worktrees\A-Wiki-Conductor-wo500-msp2a`, branch
`feat/wo-p1-500-msp2a-hotspot-admission`, dispatch HEAD
`202b172d3e27fbebe707e30b690d4678cba529d7`, base main
`19ee92ca3888ce563ac743cfcca7707334cc8189`. Not committed, not pushed.

Exact mutation scope (3 files):
- `src/a_conductor/worker_lease.py`
- `tests/test_msp2_atomic_admission.py` (new)
- `docs/work-orders/WO-P1-500-msp2-atomic-admission.md` (this checkpoint)

`tests/test_worker_lease.py` and `tests/test_worker_lease_recovery.py`
remained untouched and pass unchanged. `dex_identity.py` untouched (reused).

### Design delivered

- Additive schema: nullable `worker_leases.hotspot_key` via migration inside
  `BEGIN IMMEDIATE` with duplicate-column tolerance, so concurrent
  initialization/migration is deterministic across connections/processes.
- Injectable `hotspot_resolver` at `SQLiteWorkerLeaseStore` construction.
  Default resolver (accepted seam reuse, no new normalization authority):
  1. existing worktree with Git metadata → digest of canonicalized Git common
     dir (`canonicalize_existing_root` + `canonical_root_digest`), converging
     linked worktrees of one repository (junction/reparse/case/separator);
  2. existing directory without Git metadata → digest of the canonicalized
     directory itself;
  3. absent path → digest of the accepted legacy `worktree_key` spelling,
     preserving historical admission equivalence classes exactly.
- Mutation admission resolves the hotspot BEFORE the write transaction;
  `BEGIN IMMEDIATE` now fences active mutation leases by `hotspot_key`
  (not `worktree_key`) plus `write_sets_overlap` (unchanged seam).
- Fail-closed typed boundaries: `HOTSPOT_IDENTITY_FAILED` (resolver
  failure/invalid output), `HOTSPOT_RECONCILIATION_REQUIRED` (any active
  legacy mutation row with NULL hotspot blocks new mutation admission until
  reconciled; the row's own owner retry still reuses its lease).
- Same-owner retry with hotspot drift → `LEASE_REQUEST_CONFLICT` (store and
  broker paths; broker resolves only for real stores, keeping duck-typed
  legacy stores working).
- Observable compatibility state: `hotspot_fence_status()` returns
  `LOCAL_FENCE_ENFORCED` / `LOCAL_FENCE_RECONCILIATION_REQUIRED` with counts —
  deliberately not a global `GUARD_ENFORCED` claim for #498.
- Store identity: read-only `store_identity` digest of the canonical DB path
  (stable across instances of the same physical DB; bindable evidence only).
- Read-only leases: no hotspot resolution, NULL hotspot persisted, never
  fence or get fenced by mutation hotspot authority (behavior preserved).

### Verification evidence

- `tests/test_msp2_atomic_admission.py`: 30 passed (RED-first; import failure
  observed before implementation). Covers the full MSP-2A adversarial floor:
  independent-connection race, distinct-worktree same-hotspot convergence
  (physical Git common-dir fixture, case/separator/junction alias convergence,
  `_winapi.CreateJunction` on win32), disjoint hotspot/scope independence,
  legacy NULL row blocking + owner-retry carve-out + release unblocking,
  additive migration preservation, concurrent initialize on fresh/legacy DB,
  drift/resolver-failure fail-closed, store identity stability, seam identity
  (`worker_lease.write_sets_overlap is analyze.write_sets_overlap`),
  provenance independence, DB-restart fence persistence, released-lease
  re-acquisition, read-only non-authority, fence-status observability, a true
  two-process same-hotspot race (file-handshake subprocess, exactly one
  winner), and a subprocess DB-contention test.
- Existing suites: `test_worker_lease.py` + `test_worker_lease_recovery.py` +
  `test_dex_identity.py` 95 passed; dependency-selected importers: elastic
  capacity/fencing 48, parallel-ready/goal-closeout/production-closeout 153,
  zcode-production/zero-relay-review/cockpit/desktop-control 245,
  agent-change-packets/provider-runtime-assembly/runtime-activation/
  worker-candidate-assembly/worktree-lifecycle 248 — all passed.
- `python -m compileall` clean; `git diff --check` clean; dirty scope audited
  to exactly the three allowed paths above.

### Known limitations (bounded claim)

- Local-store-only atomicity: two different SQLite DB paths are different
  authorities (observable via `store_identity`; no cross-device convergence).
- Mixed old/new mutation writers are not globally safe: an old binary can
  still write NULL-hotspot mutation rows; `hotspot_fence_status()` reflects
  only what this store can see. `LOCAL_FENCE_ENFORCED` ≠ `GUARD_ENFORCED`.
- Submodule worktrees converge onto their superproject's Git common dir
  (conservative over-blocking, never false independence).
- No foreign-session takeover (P1-1); stale/quarantined leases still require
  accepted owner recovery.
- Same-owner retry against a legacy NULL-hotspot row cannot detect drift and
  reuses the lease (legacy compatibility; it never admits a second lease).

### Remaining R3 review risks

- Independent exact-SHA review of the resolver tier semantics (especially the
  absent-path legacy fallback tier) and of the global legacy-NULL block
  (blocks all new mutations store-wide until reconciliation — intended
  fail-closed behavior, reviewer should confirm deployment impact).
- Broker duck-typed store detection (`getattr resolve_mutation_hotspot`) —
  confirm no production fake-store path masks the fence.
- Hosted CI run on the exact reviewed head before merge (repo delivery gate).
