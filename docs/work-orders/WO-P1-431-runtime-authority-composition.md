# WO-P1-431 — RUNTIME-AUTH-1 Production Durable Runtime Authority Composition

Status: R3_AUTHORITY_MODEL_FROZEN / SOURCE_BLOCKED_ON_424_ACCEPTANCE
Issue: #431
Blocks: #429 COCKPIT-1B / LOCAL-USABLE-1
Topology: CONTROL_PLANE_ONLY
Risk: R3 — durable execution/lease authority identity and production composition.
Claim: WO-P1-431-RUNTIME-AUTHORITY-SHAPING-001
Owner: GPT-5.6 Sol integrator.

## Exact binding

- repo: `A:\\GitHub\\A-Wiki-Conductor`
- worktree: `A:\\GitHub\\_worktrees\\A-Wiki-Conductor-wo431-runtime-authority-shaping`
- branch: `docs/wo-p1-431-runtime-authority-shaping`
- base/current main: `946cf036a57c813852060ab65264fe4e155e37e0`
- current mutable scope: this Work Order only
- source mutation: FORBIDDEN until this R3 authority/failure model is frozen,
  #424 overlap is resolved, and a fresh exact claim/scope gate passes
- evidence: `runs/WO-P1-431/`

## Problem

A-Sunday already has durable job, execution, lease, provider and lifecycle
stores, but ordinary desktop startup currently composes only the Control Center,
settings/provider stores and lifecycle coordinator. Runtime Cockpit therefore
has no production-bound execution/lease read authority.

The fix must productize an existing authority identity. It must not create a
Cockpit database, scan ignored run mailboxes as a new status authority, or infer
a runtime DB from filenames/table presence.
## Reuse-before-build findings

REUSE / EXTEND:
- `DesktopControlService.open(database_path)` canonicalizes one control DB for
  registry/settings/provider/lifecycle composition.
- `SQLiteJobStore` and `SQLiteExecutionStore` are namespaced stores whose
  initialization comments explicitly support concurrent callers sharing the
  same control database.
- `SQLiteWorkerLeaseStore` is the canonical worker-capacity lease authority;
  constructor initialization/migration belongs to the lease owner, not readers.
- provider runtime assembly explicitly says it builds from one existing control
  database and validates provider-authority path identity.
- graph operator view is read-only and consumes job tables from a caller-bound DB.
- GOT closeout reuses job + canonical lease authorities but its ProjectionFacts
  is explicitly not an authority database.
- `operator.v1` wraps an injected durable job-control service.

CUT / FORBID:
- Cockpit-specific DB or schema;
- implicit table-existence discovery as identity;
- `runs/**/execution-pointer.json` scanning as a new product authority;
- PID/branch/prose/age inference;
- initializing job/execution/lease schemas from a read-only monitor tick.

## R3 authority decision (frozen for source-entry gate)

Canonical product authority identity is the **existing canonical control
database path supplied to product composition**. Runtime stores may use
namespaced tables inside that same SQLite file when their owning subsystem is
activated.

This is an identity rule, not a claim that every installed DB already contains
every runtime table. Missing runtime schema/data means that authority is
currently unavailable and read-only consumers must emit UNKNOWN.

The desktop/control facade should retain/expose this already-canonical path so
job/execution/lease/operator/cockpit composition can compare exact database
identity instead of accepting arbitrary sibling paths.
## Initialization / migration ownership

- Control Center/provider/settings keep their existing initialization behavior.
- `SQLiteJobStore` / `SQLiteExecutionStore` initialize only through the
  accepted durable-runtime owner when that subsystem is used; ordinary Cockpit
  reads never initialize them.
- `SQLiteWorkerLeaseStore` initializes on construction; therefore Cockpit must
  never construct it merely to observe leases.
- Product startup must not fabricate empty runtime truth by eagerly constructing
  write-capable runtime stores only for UI visibility.
- If a later product decision enables durable runtime at startup, that is an
  explicit migration/activation step with copied/sacrificial DB proof, rollback,
  concurrency and legacy-schema tests before touching a live DB.

## Failure model

Fail closed:
1. canonical path unavailable -> RUNTIME_AUTHORITY_UNBOUND;
2. requested writer path differs from canonical control DB -> AUTHORITY_DATABASE_IDENTITY_MISMATCH;
3. read-only DB exists but runtime tables absent -> AUTHORITY_SCHEMA_UNAVAILABLE / UNKNOWN;
4. schema version unsupported -> preserve owning store's typed unsupported error;
5. concurrent initialization -> idempotent existing store semantics, no second lock/store;
6. lease/execution/job sources disagree on DB identity -> no composition;
7. read source drifts during one projection -> STALE/EVIDENCE_INCOMPLETE;
8. transport/process uncertainty -> recovery/reconcile; never replay from UI.

No authority is created by a property, DTO, UI field or database pathname.
Authority remains the accepted owning stores and their durable records.
## Dependency and overlap gate

PR #428 / WO424 exact `e624728d...` currently owns/changes
`desktop_control.py` and its independent exact-SHA review is still active.
RUNTIME-AUTH-1 source work MUST NOT mutate that hotspot until #424 is
terminally adjudicated.

Preferred disposition if #424 code review is otherwise clean:
- explicitly re-scope #428 as Cockpit projection/read-adapter foundation;
- merge only after exact-SHA R2 code-safety gates pass under the reduced claim;
- then implement RUNTIME-AUTH-1 from then-current main.

If #424 has code defects, repair/adjudicate those first; do not stack a writer
on a moving/unaccepted hotspot.

## Source-shaping target after dependency clears

Smallest candidate scope to prove before mutation:
- MODIFY `src/a_conductor/desktop_control.py` for canonical runtime-authority
  identity retention/comparison and safe composition exposure;
- focused `tests/test_desktop_control.py` identity/mismatch/legacy-DB tests;
- this Work Order.

Any need to mutate `desktop_app.py`, execution/job/lease store schemas, or
provider/graph/runtime assembly is `SCOPE_EXPANSION_REQUIRED` and requires a
fresh R3 decision. Do not silently add those paths.
## RED-first acceptance matrix

Before implementation, tests must prove:
1. DesktopControlService.open canonicalizes one authority path and retains it;
2. a job/runtime composition request using a different DB fails before mutation;
3. same canonical DB is accepted without creating a second authority identity;
4. read-only authority locator access creates no tables/files;
5. legacy control DB without runtime tables remains usable and reports runtime
   authority unavailable rather than complete/empty by implication;
6. exact path remains stable across cwd changes;
7. existing provider/settings identity invariant remains intact;
8. no Cockpit read constructs SQLiteWorkerLeaseStore or calls initialize();
9. no source path introduces a second scheduler/store/retry/claim authority;
10. existing concurrent job/execution initialization semantics remain green.

## Verification and acceptance

R3 implementation requires:
- focused RED/GREEN tests;
- related desktop/job/execution/lease/provider/operator regressions;
- copied/sacrificial legacy-DB proof if initialization behavior changes;
- concurrency/fault checks for any initialization path;
- exact scope/diff/UTF-8/secret hygiene;
- frozen SHA;
- strongest independent GLM-5.3 MAX exact-SHA review;
- exact-head hosted CI;
- GPT-5.6 Sol acceptance;
- expected-head merge + detached post-main proof.

## Deterministic shaping proofs

Temp-only compatibility proof on Windows used a fresh temporary SQLite path and
the real production classes. It did not touch the installed live database.

One exact path was supplied to:
- `DesktopControlService.open()`;
- `SQLiteJobStore.initialize()`;
- `SQLiteExecutionStore.initialize()`;
- `SQLiteWorkerLeaseStore`.

Observed proof:
- every store/facade retained the same canonical path: `DB_IDENTITY_EQUAL=True`;
- job tables, `execution_records`, and `worker_leases` coexisted in one file;
- all three authorities reopened successfully from the same path;
- no second database identity was required.

A separate temp-only concurrency stress launched 24 initializations against one
fresh shared SQLite file (8 job + 8 execution + 8 lease) and observed
`CONCURRENT_TOTAL=24`, `CONCURRENT_ERRORS=0`.

These proofs establish compatibility/mechanism only. They do not by themselves
authorize migration of an installed database or make a pathname authoritative.
The authority decision remains the product composition contract plus the
existing owning stores.

## Frozen R3 authority model

GPT-5.6 Sol integrator freezes the shaping decision for the next implementation
gate:
1. the product composition's canonical control database path is the single
   runtime-authority identity locator;
2. existing job/execution/lease stores remain the only durable authorities and
   may use namespaced tables in that same file;
3. initialization/migration is performed only by the owning runtime subsystem,
   never by Cockpit/read-only observation;
4. a legacy installed database with absent runtime tables is valid but exposes
   runtime authority as unavailable/UNKNOWN until an authorized runtime owner
   activates those stores;
5. exact identity mismatch fails before mutation;
6. no filename/table scan/runs-directory scan creates authority;
7. later activation/migration of an installed database remains a consequential
   R3 product step requiring sacrificial-copy, rollback, concurrency, schema and
   post-migration verification before any live mutation.

## Current checkpoint

WO424 has now been explicitly re-scoped to COCKPIT-1A foundation at exact
`823263bc46c756a3fbb081edfecfa5e94020c9a4`. Its fresh independent foundation
R2 is active as
`run:WO-P1-424:foundation-r2:1:a1:63df92c0fb0c`; exact-head CI #1087 is also
active. Product/test blobs are unchanged from the prior reviewed `e624728d...`
candidate.

Therefore WO431 source mutation remains blocked until #424 foundation is
accepted and merged, because `desktop_control.py` is the overlapping hotspot.
After post-main re-pin, rerun the source mutation gate from then-current main
using the frozen authority model above.

#429 remains `DEPENDENCY_REQUIRED` until a WO431 implementation is accepted.
