# WO-P1-431 — RUNTIME-AUTH-1 Production Durable Runtime Authority Composition

Status: R3_IMPLEMENTED_LOCAL / AWAITING_EXACT_SHA_REVIEW_AND_GPT_ACCEPTANCE
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

WO431 bounded R3 implementation executed as claim
`WO-P1-431-RUNTIME-AUTHORITY-IMPL-001` on branch
`feat/wo-p1-431-runtime-authority-identity` from exact base
`ccdbe99d87af0e33d316513457790da576e11bab` (post-#432 main), mutable scope
held to `desktop_control.py` + `tests/test_desktop_control.py` + this WO.

RED-first proof (before implementation, focused subset): 3 RED —
`test_wo431_open_retains_resolved_canonical_control_db_as_authority_locator`
(AttributeError: no retained locator), `test_wo431_open_job_control_rejects_identity_mismatch_before_mutation`
(ImportError: no typed `RuntimeAuthorityError`; pre-gate `open_job_control`
accepted an arbitrary sibling DB), and
`test_wo431_open_job_control_accepts_exact_canonical_db_with_supervised_preference`
(no locator identity to pin). Legacy fail-closed and no-owning-store
construction were pinned green pre-change and stay green.

Implemented seam (smallest design, frozen #431 model):
- `RuntimeAuthorityError(ValueError)` typed codes `RUNTIME_AUTHORITY_UNBOUND`
  and `AUTHORITY_DATABASE_IDENTITY_MISMATCH`;
- `DesktopControlService.open()` retains its already-resolved canonical
  control DB (`Path.expanduser().resolve(strict=False)`); direct construction
  derives the locator from the settings store when no explicit locator is
  given; exposed read-only as `runtime_authority_database`;
- `open_job_control()` compares the requested path's exact resolved identity
  against the retained locator BEFORE `DurableJobControlService.open` and
  passes the canonical identity onward; mismatch leaves the target file
  nonexistent and the canonical table inventory unchanged.

Cockpit semantics unchanged and fail-closed: read path constructs no
`SQLiteJobStore`/`SQLiteExecutionStore`/`SQLiteWorkerLeaseStore` (explicitly
pinned via module-level monkeypatch), never initializes/migrates; legacy
canonical DB without runtime tables stays usable and projects
UNKNOWN/EVIDENCE_INCOMPLETE with `EXECUTION_AUTHORITY_READ_FAILED` /
`LEASE_AUTHORITY_READ_FAILED` and no created files/tables.

#433 dependency refinement: runtime producer activation (#433) remains the
only authorized path that may initialize job/execution/lease tables inside
the canonical control DB. This slice is authority identity/composition only —
ordinary desktop use still does NOT produce durable runtime rows, and Cockpit
product binding remains #429's after #433.

Verification: `tests/test_desktop_control.py` +
`tests/test_cockpit_projection.py` = 83 passed; related
job/execution/lease/provider/operator suites = 219 passed; py_compile OK;
`git diff --check` clean; strict UTF-8/no-U+FFFD OK; added-line secret scan 0
hits. One local commit created on the claimed branch; NOT pushed/merged;
independent exact-SHA review + GPT-5.6 Sol acceptance still required.
