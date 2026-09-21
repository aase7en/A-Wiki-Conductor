# WO-P1-461 — ZRA-3A Child A GraphStore v2 Run-Authority Persistence

Status: R3_REPAIRED / LOCAL_GREEN / FREEZE_PENDING
Issue: #461
Parent: #215
Accepted design: #452 / PR #454
Topology: CONTROL_PLANE_ONLY
Risk: R3 — durable schema identity, migration, transaction, replay/idempotency authority.
Claim: WO-P1-461-GRAPHSTORE-V2-RUN-AUTHORITY-001
Owner: GPT-5.6 Sol integrator.

## Exact binding

- repo: `aase7en/A-Wiki-Conductor`
- device: `DESKTOP-7IB57R4`
- worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo461-graphstore-v2`
- branch: `feat/wo-p1-461-graphstore-v2-run-authority`
- exact base: `eb9305957d4bfc71b1e53bca1206b84c9ee1105b`
- claim ref: `WO-P1-461-GRAPHSTORE-V2-RUN-AUTHORITY-001`
- mutable scope:
  - this Work Order;
  - `src/a_conductor/graph/store.py`;
  - `tests/test_graph_store.py`;
  - `tests/test_graph_run_authority.py` only if the focused RED matrix warrants separation.
- forbidden scope: ControlCenter/project registry, provider/job/execution/lease stores,
  scheduler/ready/dispatch/NEXT_READY, runtime activation, graph domain model,
  graph package exports, WO449/BWA successors, WO453/SunDayRemoteMCP,
  `CURRENT-WORK.md`, and `handoff.md`.

## Recovered prerequisite state

- WO452 / PR #454: COMPLETE / CLOSED / POST_MAIN_VERIFIED.
- WO449 / PR #460: COMPLETE_VERIFIED / merged as current main `eb930595...`;
  post-main CI `35571427476` is terminal SUCCESS across Windows/Ubuntu/macOS.
- WO453 / PR #456: separate Mac-owned one-document lane; current old candidate
  `2a49df85...` is waiting for Mac-owned fan-in of current main. Windows has no
  mutation authority there.
- Issue #433: CLOSED; generic/manual runtime activation remains separate.
- Issue #215 retains automatic parent-completion -> NEXT_READY authority.
- PR #316 retains `CURRENT-WORK.md` and `handoff.md`.
- protected root `A:\GitHub\A-Wiki-Conductor` remains stale/untracked and untouched.

## Reuse-before-build authority model

Child A extends the existing GraphStore only. It does not create another graph
registry, project registry, route selector, runtime scheduler, retry engine, job
store, or completion plane.

Accepted durable authority is exactly:
1. existing persisted TaskGraph definition in GraphStore;
2. one v2 graph-run preparation record;
3. zero or more immutable per-node binding records owned by that run.

The legacy `graph_runs.status` column remains compatibility shape only. It is not
promoted to execution/currentness/completion authority.

## v2 persisted shape

`graph_runs` preserves v1 columns and adds nullable migration-compatible:
- `project_id TEXT`
- `graph_definition_sha256 TEXT`
- `preparation_ref TEXT`
- `preparation_sha256 TEXT`

A unique index applies to non-null `preparation_ref`. Legacy rows remain null
for new authority columns and never acquire inferred activation authority.

Add `graph_run_bindings` with immutable identity:
- `run_id TEXT NOT NULL` -> `graph_runs(run_id)`
- `node_id TEXT NOT NULL`
- `runtime_kind TEXT NOT NULL`
- `task_contract_ref TEXT NOT NULL`
- `task_contract_sha256 TEXT NOT NULL`
- `task_packet_ref TEXT NOT NULL`
- `task_packet_sha256 TEXT NOT NULL`
- `provider_id TEXT NOT NULL`
- `model_id TEXT NOT NULL`
- `effort_level TEXT NOT NULL`
- `bound_at TEXT NOT NULL`
- primary key `(run_id, node_id)`

Application/store validation must keep non-empty bounded identity text and
canonical lowercase 64-hex SHA-256 values fail closed. Every connection touching
bindings keeps `PRAGMA foreign_keys=ON`.

Child A does not validate ControlCenter project roots or live provider policy.
Those application-authority checks belong to Child B. Child A does enforce its
own persistence contract, including exact `runtime_kind == "serena"`, explicit
nonblank pre-pinned route fields, canonical refs/hashes, graph/node existence and
the current capability boundary required by the accepted design.

## Graph-definition identity

Canonicalization version: `graph-definition-v1`.

Digest bytes:
`b"graph-definition-v1\0" + canonical_json_utf8`

Canonical JSON includes every persisted TaskNode field and every edge:
- nodes sorted by node id;
- tuple fields serialized as arrays;
- enums serialized by value;
- edges sorted by `(from_id, to_id, dep_type)`;
- `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False)`;
- strict UTF-8, no BOM/trailing newline in digest material.

Missing graph and persisted-empty/no-node graph both fail before run minting.
Child A must not invent a graph-header registry to distinguish them.

## Preparation identity / replay model

The caller supplies one stable opaque nonblank bounded `preparation_ref`.
GraphStore never infers one from timestamps, latest rows, branches, filenames,
chat/process state, or a server-generated run id.

Preparation digest domain:
`b"graph-run-preparation-v1\0" + canonical_preparation_json`

Digest includes exactly graph/project/graph-definition identity plus the
canonical sorted binding intent. It excludes server-generated/observational
fields such as run id and timestamps.

Replay rules:
- first unseen ref: mint exactly one `graph-run-v1:<uuid4hex>` inside the
  transaction and persist the complete run + bindings;
- same ref + same digest: re-read and exact-compare the durable run and complete
  binding set before returning the same run id;
- same ref + different intent: typed identity mismatch;
- same digest but missing/extra/malformed/mismatching durable rows: typed
  recovery-required;
- intentional rerun: caller uses a new preparation ref;
- no public persistence-producing `mint_run()` or rebind/update API.

## Transaction / migration failure model

Writable initialization must validate exact schema/version shape before mutation.
Supported inputs only:
- fresh graph DB;
- exact canonical v1;
- exact canonical v1 with the version-row crash edge when shape proves v1;
- exact canonical v2.

Wrong/partial/foreign shape or unsupported version fails typed and unchanged.

v1 -> v2 migration occurs inside one `BEGIN IMMEDIATE`:
1. re-read version and exact table/index/constraint/FK shape under lock;
2. converge if another initializer already completed canonical v2;
3. otherwise require exact canonical v1;
4. add nullable v2 run columns;
5. create exact binding table/indexes;
6. re-read/verify canonical v2;
7. stamp version 2;
8. re-read durable winner;
9. commit.

No legacy binding backfill. Any failure rolls back.

`open_read_only()` performs no DDL/migration. Valid v1 graph reads remain
available. A v1 binding/run-authority lookup fails typed with
`GRAPH_RUN_BINDING_AUTHORITY_UNAVAILABLE`.

SQLite busy/locked acquisition is a bounded typed store/preparation failure.
No sleep loop, spin loop or blind retry is authorized.

## Frozen Child-A test-facing API

The RED contract pins the bounded public surface inside `graph.store` only:
- `GraphStoreError(code)` typed persistence failure;
- `GraphRunBindingSpec` immutable preparation-intent record;
- `GraphRunRecord` typed persisted run record;
- `GraphRunBindingRecord` typed persisted binding record;
- `canonical_graph_definition_sha256(graph)`;
- `GraphStore.prepare_run(...)`;
- `GraphStore.load_graph_run(run_id)`;
- `GraphStore.load_graph_run_bindings(run_id)`.

No package-level export is authorized. Child B may consume these directly after Child A acceptance.

## Required typed outcomes

Stable codes must distinguish at least:
- unsupported schema version;
- invalid schema shape;
- binding authority unavailable in read-only v1;
- invalid preparation input / missing ref;
- preparation identity mismatch;
- preparation recovery required;
- graph missing/empty/stale definition;
- binding/node/field/hash/ref/runtime-kind invalid;
- store/preparation lock or SQLite failure.

Raw SQLite/internal decode exceptions must not become authority decisions.

## RED-first matrix

Before production source mutation, tracked tests must demonstrate failures for:
1. unsupported version unchanged;
2. wrong-shaped v1/v2 unchanged;
3. partial v2 not stamped;
4. exact v1 migrates to exact v2 and preserves legacy run/graph rows;
5. migration fabricates no legacy binding;
6. concurrent initialization converges to one exact v2;
7. read-only v1 graph reads work with zero DDL and binding lookup typed-fails;
8. write-lock contention fails boundedly without retry;
9. graph digest deterministic across insertion/order/restart;
10. Unicode graph metadata hashes deterministically with strict UTF-8;
11. semantic node/edge change changes digest;
12. missing/empty graph fails before run minting;
13. first preparation mints one run;
14. lost-response replay with same ref/intent returns same run after exact durable comparison;
15. same ref/different intent fails identity mismatch;
16. new ref creates a different run;
17. injected pre-commit failure leaves no partial run/bindings;
18. concurrent identical prepare converges on one run;
19. concurrent conflicting prepare yields one winner + typed mismatch;
20. missing/extra/malformed/mismatching durable binding on replay yields recovery-required;
21. unknown binding node fails before commit;
22. duplicate binding identity cannot be rebound;
23. prepared-only rows remain inert; no expiry/GC/status lifecycle is added.

RED evidence must be captured before `store.py` production implementation.

### RED evidence — 2026-09-21

Command:
`python -m pytest tests/test_graph_store.py tests/test_graph_run_authority.py -q`

Observed before any production-source mutation:
- existing GraphStore regression: 9 PASS;
- new Child-A authority matrix: 23 expected FAIL;
- first failure boundary is the intentionally absent typed v2 API surface;
- runtime: 2.48 s;
- `src/a_conductor/graph/store.py` remains byte-identical to `main@eb930595...` at this checkpoint.

This is the required RED boundary. Implementation must not weaken/delete the tests merely to turn GREEN.

### GREEN / local implementation evidence — 2026-09-21

Recovered an already-started claimed implementation with no live WO461 executor process.
The dirty source remained inside the exact one-file production scope.

First focused harvest:
- 31 PASS / 1 FAIL;
- only failure: concurrent v1 initializers could inspect a transient migration shape before acquiring writer authority.

Bounded repair:
- writable schema classification now occurs only after `BEGIN IMMEDIATE`;
- no retry/sleep loop was added;
- unsupported/invalid schema still rolls back and fails typed.

Post-repair:
- `python -m pytest tests/test_graph_store.py tests/test_graph_run_authority.py -q`: 32 PASS;
- `python -m pytest tests -q -k graph`: 213 PASS / 3 SKIP / 3963 deselected;
- skips are unrelated Tk-display availability cases;
- `git diff --check`: clean;
- tracked mutable diff remains only this WO plus `src/a_conductor/graph/store.py`.

### Adversarial exact-schema repair cycle — 2026-09-21

Detached exact-SHA audit of candidate `c1962d6b582856a39c39a3815856f6d345de1009`
found two deterministic schema-shape gaps:
- a same-name UNIQUE partial preparation index with the wrong WHERE predicate was accepted;
- a same-column/FK `graph_run_bindings` table with required CHECK constraints removed was accepted.

Both violate the WO requirement that v2 table/index/constraint/FK shape be exact and
fail closed. Temp-database probes reproduced both false accepts without touching live data.

Repair:
- canonicalize and compare the binding-table `sqlite_master.sql` against the exact
  Child-A DDL;
- canonicalize and compare the preparation-index `sqlite_master.sql` against the
  exact `WHERE preparation_ref IS NOT NULL` DDL;
- add executable regressions proving both corrupted shapes fail typed and remain unchanged.

Post-repair evidence:
- focused GraphStore/run-authority: 34 PASS;
- graph impact: 215 PASS / 3 unrelated Tk-display SKIP;
- concurrency/replay stress: 20 iterations × 3 tests = 60 PASS;
- `git diff --check`: clean;
- repair diff remains inside `src/a_conductor/graph/store.py` +
  `tests/test_graph_run_authority.py` plus this WO evidence.

## Verification / acceptance

- RED then bounded GREEN implementation;
- focused GraphStore/run-authority suites;
- directly related graph persistence/operator regressions;
- migration/concurrency/fault probes;
- `git diff --check` and exact scope proof;
- frozen exact candidate SHA;
- one strongest independent GLM-5.3 MAX exact-SHA R3 review;
- exact-head hosted CI;
- GPT-5.6 Sol acceptance;
- expected-head merge;
- detached post-main proof and Issue #461 closeout.

No merge/acceptance is delegated to the implementation agent.
