# WO-P1-452 — ZRA-3A graph-run authority and successor activation-binding design

Identity schema: GITHUB_ISSUE_V1
Issue: #452

Status: DESIGN CANDIDATE / SOURCE HOLD
Parent authority: Issue #215 / claim `GPT1-ZRA3-PREFLIGHT-001`
Accepted governance predecessor: Issue #447 / PR #448
Accepted generic activation owner: Issue #433 / RUNTIME-ACT-1
Integrator / design owner: GPT-5.6 Sol — Windows lane
Repository: A-Wiki-Conductor
Topology: CONTROL_PLANE_ONLY
Risk: R3 — durable identity / migration / replay / automatic-continuation trust boundary
Prepared base: `3db441f3aa2ec7ef3a7f41ce98d41df047b72a3c`
Governance worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo452-design`
Governance branch: `docs/wo-p1-452-zra3a-design`

## 1. Objective

Define the smallest truthful durable authority that lets a future #215 automatic continuation safely obtain the complete identity needed by the already-accepted #433 runtime-activation primitive.

The required chain is:

`prepared graph run -> immutable per-node activation selection -> fresh authority revalidation -> RuntimeActivationRequest -> accepted #433 activation`

This work order is design/governance only. It grants no source mutation.

`SAFE_TO_MUTATE_ZRA3_SOURCE = NO`

## 2. Current accepted authority split

### Issue #215 owns

- automatic accepted-completion -> NEXT_READY trigger and successor selection;
- exact parent-completion/provenance validation;
- one-tick continuation/reconcile semantics;
- no blind retry, no same-tick retry, and no ZRA-4 fan-out;
- consumption of an already-authoritative successor activation selection.

### Issue #433 owns

- the sole generic/manual production runtime-activation primitive;
- the sole accepted generic `ParallelReadyNodeContract` composition path;
- fresh task-contract/worktree/branch/HEAD/scope/budget/dispatch validation;
- fresh provider/model/effort/generation/endpoint validation;
- worker/lease/job/execution composition and durable dispatch/recovery.

### This design may own only

- graph-run preparation identity;
- immutable per-node activation-selection identity for that prepared run;
- persistence/migration needed for those two authorities.

It must not create a second scheduler, graph/job lifecycle, provider registry, lease store, execution store, review authority, completion authority, retry engine, or generic activation front door.

## 3. Confirmed current-main gaps

Current main `3db441f3...` proves all of the following. This base includes the disjoint WO449 Browser-Wake contract history through PR #455; that four-file fan-in does not touch the WO452 authority surface. A later WO449 cycle-2 security repair remains separately owned and cannot grant or revoke WO452 mutation authority.

### 3.1 Graph-run identity has semantics but no production authority

GE-7 defines semantic dispatch identity as:

`{graph_id, graph_run_id, node_id}`

GE-7 also requires:

- an intentional rerun of the same graph creates a new `graph_run_id`;
- recovery/reconnect of the same run preserves the existing `graph_run_id`.

`GraphStore` already contains a `graph_runs` table, but there is no accepted production writer/API that creates or restores graph-run authority.

Today `graph_run_id` can enter the explicit activation path as a caller/CLI string. Persisting that string after the fact would not prove who minted it or whether a retry is the same run.

### 3.2 No READY-node -> activation reverse authority exists

`RuntimeActivationRequest` currently requires ten values:

1. `graph_id`
2. `graph_run_id`
3. `node_id`
4. `runtime_kind`
5. `project_root`
6. `task_contract_ref`
7. `task_packet_path`
8. `provider_id`
9. `model_id`
10. `effort_level`

The graph domain does not durably bind a node to the selection fields needed to build that request.

`GraphDispatch` metadata is created at/after dispatch and is replay/dedup evidence. It is not a pre-dispatch reverse index.

### 3.3 Generic node_events is not sufficient R3 authority

Current `node_events` has:

- `graph_id`;
- `node_id`;
- free-text `event_type`;
- free-text/JSON `payload`;
- no first-class `graph_run_id`;
- no `UNIQUE(run_id, node_id)` authority boundary.

Therefore “latest matching JSON event” would create implicit-current inference and ambiguous duplicate-binding semantics. GE-11 explicitly rejects implicit latest/current graph-run inference.

`node_events` may remain an audit surface. It must not become the activation-binding authority.

## 4. Deterministic GraphStore defect evidence

Read-only source archaeology plus sacrificial temporary SQLite probes on exact main proved the current writable initializer is not fail-closed.

Current v1 initialization runs `CREATE TABLE IF NOT EXISTS` and then overwrites/stamps:

`schema_version = 1`

Observed defects:

1. an existing `schema_version=999` was accepted by `GraphStore(path)` and changed to `1`;
2. an existing wrong-shaped `graph_runs` table with `status INTEGER` was accepted and retained while version `1` was stamped/kept.

Therefore GraphStore must not become a production run/binding writer until schema authority is hardened.

## 5. Graph definition identity is required

`GraphStore.save_graph(graph, graph_id)` replaces nodes and edges beneath an existing `graph_id`.

Without a pinned graph definition identity, the same `graph_run_id` could observe different topology/constraints after restart while preserving the same durable dispatch key namespace.

A prepared run therefore binds one deterministic graph-definition digest.

Any graph-definition drift under the same `graph_id` makes the prepared run stale and fails closed. Intentional execution of the changed graph requires a new preparation and a new graph run.

## 6. Design classification

Classification: **EXTEND + REUSE**.

### EXTEND

Extend the existing GraphStore authority with:

- fail-closed schema version/shape reconciliation;
- typed graph-run preparation identity;
- typed immutable per-node activation bindings.

### REUSE

Reuse, without copying their authority:

- ControlCenter project registry for `project_id -> root_path`;
- task contract for exact worktree/branch/HEAD/scope/budget/dispatch authority;
- task packet bytes for packet identity;
- provider store for current provider/model/generation/endpoint validity authority;
- the explicit run-preparation request/front door for per-node route-selection intent — never an advisory ranking result or inferred default;
- worker/lease stores for current worker authority;
- DurableJobControl/GraphDispatch for job lifecycle, dedup and recovery;
- #433 for generic production runtime activation;
- #215 for parent-completion/NEXT_READY policy.

A new standalone activation registry/store is forbidden.

## 7. Corrected GraphStore v2 authority model

The design uses two typed levels:

1. one graph-run preparation record;
2. zero or more immutable per-node activation bindings belonging to that run.

### 7.1 graph_runs v2 fields

Retain existing v1 columns for compatibility:

- `run_id TEXT PRIMARY KEY`
- `graph_id TEXT NOT NULL`
- existing `status`, `created_at`, `completed_at`

Add nullable migration-compatible authority columns:

- `project_id TEXT`
- `graph_definition_sha256 TEXT`
- `preparation_ref TEXT`
- `preparation_sha256 TEXT`

Add a unique index for non-null `preparation_ref`.

Legacy v1 rows remain nullable and are preserved exactly. They do not become automatic-activation authority merely because the database is migrated.

The existing `status` column is not promoted into a graph/job lifecycle authority. A v2 preparation insert may leave the existing v1 default `pending` solely to satisfy the preserved table shape; no new code may update or interpret that column as execution/currentness truth. Automatic continuation must use durable job/closeout authority instead.

### 7.2 graph_run_bindings v2 relation

Add a typed relation:

```text
graph_run_bindings
- run_id                  TEXT NOT NULL  FK -> graph_runs(run_id)
- node_id                 TEXT NOT NULL
- runtime_kind            TEXT NOT NULL
- task_contract_ref       TEXT NOT NULL
- task_contract_sha256    TEXT NOT NULL
- task_packet_ref         TEXT NOT NULL
- task_packet_sha256      TEXT NOT NULL
- provider_id             TEXT NOT NULL
- model_id                TEXT NOT NULL
- effort_level            TEXT NOT NULL
- bound_at                TEXT NOT NULL
PRIMARY KEY (run_id, node_id)
```

`task_contract_ref` and `task_packet_ref` are canonical project-relative references. Before hashing or persistence they must be normalized against the resolved project root, reject absolute paths, empty segments, `.` / `..`, NUL/newline ambiguity and root escape, then serialize with `/` separators so the same semantic path has one durable representation. Absolute project-root paths are not duplicated into GraphStore.

The v2 table/API must also enforce non-empty bounded text and canonical lower-case 64-hex SHA-256 values through application validation plus SQLite `CHECK` constraints where practical. `PRAGMA foreign_keys=ON` remains mandatory for every GraphStore connection that can touch the binding relation.

For this first bounded ZRA-3A path, `runtime_kind` is **not** a free vocabulary. Accepted #433 fixed-pool source proves an observed Serena runtime (`runtime:serena`) but exposes no generic runtime-kind selection authority. Therefore the only accepted persisted value in this slice is exactly `serena`. Any other value fails `RUNTIME_KIND_AUTHORITY_UNAVAILABLE`. A future additional runtime kind requires a separately accepted runtime-routing authority; Child A/B must not infer one from elastic-capacity configuration, CLI defaults or arbitrary strings.

There is no update/rebind API. A conflicting binding for the same `(run_id, node_id)` is a typed identity mismatch. Intentional new selection requires a new prepared run.

## 8. Project-root authority

The binding does not persist `project_root`.

Current main already has a durable ControlCenter project registry with:

`project_id -> Project.root_path`

The preparation/consumer application seam must:

1. read the run's `project_id`;
2. resolve that exact project through the existing ControlCenter registry;
3. obtain the current registered root path;
4. use that root to resolve project-relative contract/packet refs;
5. let accepted #433 `load_activation_authority()` exact-check the task contract's expected worktree/branch/HEAD.

A missing project, changed project identity, or root mismatch fails closed.

This avoids a second project/worktree registry in GraphStore.

## 9. Graph definition digest

The run row stores one `graph_definition_sha256`.

Canonicalization version: `graph-definition-v1`.

Input is canonical UTF-8 JSON containing:

- nodes sorted by node id;
- every persisted TaskNode field, with tuples represented as arrays and enums represented by values;
- edges sorted by `(from_id, to_id, dep_type)`;
- `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False)` semantics, encoded as strict UTF-8 with no BOM or trailing newline in the digest material.

Digest material is domain-separated:

`"graph-definition-v1\0" || canonical_json_bytes`

Including all persisted node fields is intentionally conservative: replacing any persisted graph definition under the same `graph_id` invalidates the prepared run rather than silently changing its meaning.

At binding consumption, the graph is reloaded and its digest must exact-match the run row before a request can be constructed.

### 9.1 Empty/missing graph ambiguity

Current v1 GraphStore has no graph-header row. `save_graph()` persists only node/edge rows and `list_graph_ids()` derives existence only from `graph_nodes`. Therefore an empty graph saved under a graph id is durably indistinguishable from a missing graph id.

Child A must **not** add a new graph-definition registry merely to hide this ambiguity. Run preparation is allowed only when the exact `graph_id` has at least one persisted TaskNode and the loaded graph canonicalizes successfully. Empty/missing/corrupt graph input fails typed before run-id minting or any run/binding insert. If future product requirements need executable empty graphs, that requires a separate accepted graph-identity/schema decision.

## 10. Preparation identity and no-blind-replay

A random server-minted run id alone is not replay-safe.

Failure case:

`prepare commits -> response is lost -> caller retries -> new UUID is minted`

That would create two graph runs for one transport-level intent.

Therefore the prepare API requires a caller-stable, opaque `preparation_ref` used only as an idempotency identity.

### 10.1 preparation_ref semantics

- non-empty, bounded, opaque text;
- not a `graph_run_id`;
- not a job/task/completion authority;
- stable across retry/recovery of one preparation request;
- intentionally new graph rerun uses a new `preparation_ref`.

The application caller owns preserving/reusing the same ref across a retry. **The ref must be durable before the first prepare attempt.** A volatile random value held only in process/chat memory is insufficient because a crash before observing the response would lose the recovery key. Child B must obtain or checkpoint the ref through an already-accepted durable operation/task evidence seam before the first call. If no such caller-side durable seam is available at Child-B release time, stop at `DESIGN_GAP` rather than inventing a second idempotency store. The GraphStore service never infers the ref from time, latest rows, prose, branch names, filenames, or mutable process state.

### 10.2 preparation_sha256

The service computes a canonical preparation digest over exactly the preparation-intent fields:

- `graph_id`;
- `project_id`;
- `graph_definition_sha256`;
- bindings sorted by `node_id`, where each binding contributes exactly `node_id`, `runtime_kind`, `task_contract_ref`, `task_contract_sha256`, `task_packet_ref`, `task_packet_sha256`, `provider_id`, `model_id`, and `effort_level`.

Server-generated or observational fields are deliberately excluded: `run_id`, `bound_at`, graph-run `created_at`, `completed_at`, and legacy `status` are **not** preparation-digest material. This is required so commit-success/response-loss replay of unchanged intent cannot false-mismatch because a timestamp or server-minted id differs.

Domain separation:

`"graph-run-preparation-v1\0" || canonical_preparation_json`

### 10.3 replay rules

- no existing `preparation_ref`: mint one new `graph-run-v1:<uuid4hex>` inside the prepare transaction and persist the complete run + bindings;
- same `preparation_ref` + same `preparation_sha256`: re-read the exact run row **and the complete persisted binding set**, canonicalize/compare them with the requested preparation, and only then return the existing exact `run_id`;
- same ref/digest but missing, extra, malformed or mismatching durable run/binding rows: fail `GRAPH_RUN_PREPARATION_RECOVERY_REQUIRED` rather than blessing partial/corrupt state;
- same `preparation_ref` + different digest: fail `GRAPH_RUN_PREPARATION_IDENTITY_MISMATCH`;
- intentional rerun: new `preparation_ref` -> new server-minted run id;
- automatic successor continuation inside an already-prepared run never mints a run id; it reuses the exact existing `graph_run_id`.

There is no public persistence-producing `mint_run()` operation.

## 11. Atomic preparation transaction

One writable store operation owns the database transaction.

Logical sequence under one `BEGIN IMMEDIATE`:

1. re-read/validate GraphStore v2 version and exact schema shape;
2. look up `preparation_ref`;
3. if present, load the exact run row plus complete binding set, verify schema/canonical field validity, compare preparation digest **and** canonical durable contents, then return/reject without mutation;
4. verify graph id exists and the supplied graph digest matches the stored graph definition just read;
5. require every binding `node_id` to exist in that exact loaded graph, reject duplicate/unknown nodes, require that node's `worker_requirement` is empty for the current #433 capability boundary, require `runtime_kind == "serena"`, and validate canonical contract/packet refs and hashes before persistence;
6. require an explicit pre-pinned provider/model/effort selection for every supplied binding; validate it against current accepted provider configuration/policy but do not rank, infer, default or fall back;
7. mint `graph_run_id` only when this preparation does not already exist;
8. insert one run row including project/digest/preparation identity;
9. insert the complete supplied per-node binding set;
10. re-read the run plus complete binding set from SQLite and exact-compare all authority fields to the canonical requested preparation;
11. commit.

Crash before commit leaves no run/bindings. Crash after commit is recovered by `preparation_ref`.

SQLite write-lock contention is bounded by the existing connection/store policy. `SQLITE_BUSY`/`SQLITE_LOCKED` or equivalent acquisition failure returns a typed store/preparation failure; this design adds no spin loop, sleep loop or blind retry around `BEGIN IMMEDIATE`.

No partially prepared run is externally authoritative.

## 12. Schema v1 -> v2 migration requirements

Migration must follow the repository's proven fail-closed store patterns, especially `SQLiteExecutionStore._reconcile_schema_version()`.

### 12.1 Before any mutation

Read:

- existing `schema_version`;
- `sqlite_master`;
- exact `PRAGMA table_info` shapes;
- required indexes/constraints, including the unique non-null preparation-ref index, `(run_id,node_id)` primary key, run foreign key and canonical field `CHECK`s;
- foreign-key enforcement state for the writable connection.

Reject unsupported versions and foreign/partial/wrong-shaped tables before stamping or altering anything. A table with the right column names but wrong declared types, nullability, defaults, primary-key order, foreign-key target, index uniqueness or canonical checks is not accepted authority.

### 12.2 Supported inputs

- fresh database with no graph schema;
- exact canonical v1;
- exact canonical v1 with the version-row crash edge, only when all v1 tables/meta shape proves canonical;
- exact canonical v2.

Anything else fails closed.

### 12.3 Under write lock

For v1 migration:

1. `BEGIN IMMEDIATE`;
2. re-read version and every relevant table shape;
3. if another caller already completed canonical v2, validate and return;
4. otherwise require exact canonical v1;
5. add the nullable v2 graph-run columns;
6. create the typed binding table and required indexes;
7. re-read and verify resulting canonical v2 shape;
8. stamp version `2`;
9. re-read the durable version winner;
10. commit.

No backfill invents preparation/binding authority for legacy runs.

### 12.4 Fresh initialization

Fresh initialization creates canonical v2 directly and uses an idempotent schema-version stamp. Concurrent initializers converge on the same canonical winner.

### 12.5 Read-only compatibility

`GraphStore.open_read_only()` performs no DDL and no migration.

GE-11 planning/operator reads of a valid legacy v1 database remain available.

A new read-only binding lookup against v1 returns a typed `GRAPH_RUN_BINDING_AUTHORITY_UNAVAILABLE`; it must not auto-upgrade the database.

### 12.6 Rollback

Any unsupported version, shape mismatch, SQLite failure or post-migration verification failure rolls back. The prior database must not be silently restamped to a supported version.

## 13. Immutable selection vs fresh authority

### Persist as immutable selection identity

At run preparation:

- graph_id;
- graph_run_id;
- project_id;
- graph definition digest;
- preparation ref/digest;
- node_id;
- runtime_kind;
- task_contract_ref + SHA-256;
- task_packet_ref + SHA-256;
- provider_id;
- model_id;
- effort_level.

### Revalidate freshly at consumption/activation

Do not persist as replacement authority:

- absolute project root;
- branch/HEAD/worktree current observation;
- task-contract current bytes;
- task-packet current bytes;
- task scope/budget/retry/dispatch mode;
- provider generation/endpoint/readiness/admission;
- live worker candidates/capabilities;
- lease/reservation state;
- job/execution state;
- READY state;
- parent completion/review/closeout truth;
- quota;
- execution/review/completion outcomes.

Binding consumption first verifies immutable digests/current project/graph identity, then #433 revalidates current authorities before any runtime store or external execution.

### 13.1 Explicit route-selection authority

Current main does **not** contain an accepted automatic provider/model selector. `provider_cost_preference.rank_provider_candidates()` is advisory preference evidence only; `provider_selection_observability` deliberately reports absent selection authority as `UNKNOWN`; `TaskNode.model_requirement` is not a canonical provider route.

Therefore the first bounded ZRA-3A preparation path is explicit, not automatic routing:

1. the accepted run-preparation front door/request must supply one complete per-node route selection: `provider_id`, `model_id`, `effort_level`; its runtime discriminator is fixed to exact `runtime_kind="serena"` by this slice;
2. absence of any required provider/model/effort field fails closed — no default provider, inferred model, cost-ranked winner or silent fallback;
3. any runtime kind other than exact `serena` fails `RUNTIME_KIND_AUTHORITY_UNAVAILABLE`; neither `ElasticCapacityPolicy.permitted_runtime_kinds` nor the #433 CLI/dataclass default is selection authority for this fixed-pool path;
4. Child B validates the explicitly selected provider/model/effort against current accepted provider configuration/policy and validates the fixed runtime discriminator, but **does not choose** among candidates;
5. the validated explicit selection becomes immutable run-binding identity only because the whole preparation is bound to the durable `preparation_ref`/digest transaction;
6. #433 still performs fresh provider/model/effort/generation/endpoint/readiness/admission checks at activation time and may reject a route that was valid when prepared;
7. automatic provider/model selection, runtime-kind expansion, cost-aware switching or fallback is a separate future routing-authority slice and cannot be introduced by Child A, Child B or #215 continuation integration.

A free caller string presented outside the accepted run-preparation front door is not route authority. Child B reconstruction must populate every `RuntimeActivationRequest` field explicitly from trusted binding/current authorities; it must never rely on the request dataclass or CLI defaults.

## 14. Consumer flow

A future binding consumer performs:

1. load exact `graph_run_id`;
2. require v2 run authority fields;
3. resolve `project_id` through current ControlCenter registry;
4. reload graph and exact-check graph definition digest;
5. load exact `(run_id, node_id)` binding;
6. resolve project-relative contract and packet refs beneath the resolved project root;
7. exact-check current contract and packet SHA-256 against the immutable binding;
8. construct one `RuntimeActivationRequest`;
9. call accepted #433 activation once;
10. return the typed downstream result.

It never selects NEXT_READY. #215 performs selection and hands the already-selected `node_id` to this consumer.

## 15. Continuation semantics

The eventual #215 continuation tick remains:

1. observe exact parent/graph/run durable state;
2. require parent durably COMPLETE at the accepted closeout boundary;
3. re-project graph-run states through existing `GraphDispatchKey`;
4. compute READY using existing graph policy;
5. select at most one successor through accepted policy;
6. obtain the exact typed activation binding for that same existing run;
7. fresh-revalidate binding/current authorities;
8. invoke #433 at most once;
9. return;
10. stop.

No poll loop, no same-tick retry, no volatile continued flag, no blind dispatch on UNKNOWN/RECOVERY_REQUIRED.

## 16. Cross-store crash/replay boundary

Graph run/binding preparation and durable job creation are separate authority transactions by design.

This is acceptable only because:

- run/binding preparation commits before dispatch;
- GraphDispatch derives stable job identity from exact `{graph_id, graph_run_id, node_id}`;
- existing durable job/dispatch metadata deduplicates/reconciles dispatch;
- a crash after preparation but before job creation leaves an inert prepared binding;
- a prepared-but-never-dispatched run/binding remains inert evidence only; this slice adds no implicit garbage-collection, expiry, cancellation or lifecycle transition for it;
- a crash after job creation uses existing durable job/execution recovery;
- no cross-store pseudo-transaction or second replay ledger is introduced.

## 17. Rejected alternatives

### Generic node_events JSON

Rejected as R3 authority: no run key, no per-run/node uniqueness, free-text payload, latest-event ambiguity.

### Put activation fields on TaskNode/artifacts/model_requirement

Rejected: TaskNode is graph-domain planning/scheduling data; this would mix execution authority into graph definition and create ambiguous currentness.

### Pre-create durable jobs to hold activation identity

Rejected: job store does not carry the full selection fields and creating jobs during preparation would mutate execution lifecycle before activation.

### Reuse GraphDispatch metadata as reverse lookup

Rejected: metadata is created at/after dispatch and is a hash checkpoint, not pre-dispatch queryable selection authority.

### Store absolute project_root in GraphStore

Rejected: ControlCenter already owns `project_id -> root_path`; duplicating it creates stale project identity.

### Public mint_run followed by later binding writes

Rejected: crash windows create unbound runs and retry can mint duplicates.

### Infer latest run, latest task packet, branch convention, filenames or prose

Rejected: violates GE-11 and the no-inference authority rule.

### Treat advisory provider ranking or free caller strings as route authority

Rejected: current cost/quota ranking is explicitly advisory, provider-selection observability reports missing selection authority as `UNKNOWN`, and #433 validates a requested route but does not choose one. The first ZRA-3A path accepts only an explicit route supplied through the accepted run-preparation front door and fails closed when it is absent or invalid.

## 18. Ordered implementation decomposition

One large source WO is not authorized.

### Child A — GraphStore v2 persistence/run-authority foundation

Owns only:

- fail-closed v1/v2 schema reconciliation;
- graph definition canonical digest helper;
- typed v2 persistence records;
- atomic preparation persistence/idempotency primitive;
- typed read APIs;
- store-level migration/concurrency tests.

No DesktopControl, no runtime activation, no NEXT_READY.

### Child B — preparation + binding application seam

Consumes Child A and existing ControlCenter/task-contract/provider authorities.

Owns:

- project-id resolution;
- preparation input validation;
- contract/packet digest validation;
- validation/binding of exact `runtime_kind="serena"` plus the caller's explicit pre-pinned `provider_id/model_id/effort_level` selection;
- rejection of non-Serena runtime kinds, non-empty node `worker_requirement` under the current #433 capability boundary, missing route selection, advisory-ranking substitution, implicit defaults and fallback;
- thin application/service seam;
- typed binding-to-`RuntimeActivationRequest` reconstruction with fresh digest checks.

It does not select successors, does not rank/select providers/models, and does not dispatch.

### Child C — #215 automatic continuation integration

Consumes accepted Child B + accepted #433.

Owns only:

- parent-completion gate;
- READY re-observation/selection;
- one selected binding lookup;
- one accepted #433 call;
- one-tick/no-blind-replay integration.

No new durable state.

Children are ordered A -> B -> C. Each consequential boundary receives its own exact-SHA acceptance and current-main re-pin.

## 19. Future RED-first matrix

### Schema authority

1. unsupported schema version is rejected and unchanged;
2. wrong-shaped v1/v2 table is rejected and unchanged;
3. partial v2 shape is rejected and not stamped;
4. exact v1 migrates to exact v2;
5. legacy v1 graph/run rows are preserved byte/field-equivalent;
6. no legacy activation binding is fabricated;
7. two concurrent initializers converge on exact v2;
8. read-only v1 stays read-only and usable for GE-11 graph reads;
9. read-only v1 binding lookup fails typed with no DDL;
10. SQLite write-lock contention returns bounded typed failure and creates no internal retry/spin loop.

### Graph definition identity

11. same graph canonicalizes deterministically across restart;
12. node insertion/order differences do not change digest when semantic graph is equal;
13. non-ASCII graph metadata canonicalizes with `ensure_ascii=False` + strict UTF-8 deterministically;
14. semantic node/edge change changes digest;
15. same graph_id with changed definition makes prepared run stale;
16. missing graph id and persisted-empty/no-node graph are both rejected before run minting under current schema.

### Preparation replay/concurrency

17. first preparation mints one server-side run id inside the transaction;
18. commit + lost response + same preparation_ref/digest returns the same run id after exact durable run+binding-set comparison;
19. missing/blank preparation_ref fails closed — no volatile implicit mint path exists;
20. same preparation_ref with different intent fails identity mismatch;
21. intentional rerun with new preparation_ref creates a different run id;
22. injected failure before commit leaves no partial run/bindings;
23. two concurrent identical prepares converge on one run;
24. concurrent conflicting prepares with the same ref produce one winner + typed mismatch;
25. duplicate `(run_id,node_id)` binding cannot change identity;
26. same ref/digest with a missing persisted binding fails `GRAPH_RUN_PREPARATION_RECOVERY_REQUIRED`;
27. same ref/digest with an extra, malformed or mismatching durable binding fails recovery-required rather than returning the run id;
28. a binding whose `node_id` is absent from the exact loaded graph is rejected before any run/binding commit;
29. prepared-but-never-dispatched rows remain inert and do not acquire implicit expiry/GC/cancel lifecycle authority.

### Project/contract/packet binding

30. missing project_id fails closed;
31. changed registered project root causes exact authority failure;
32. absolute/escaping/ambiguous contract ref fails before persistence;
33. absolute/escaping/ambiguous packet ref fails before persistence;
34. semantically equivalent refs canonicalize to one `/`-separated durable representation;
35. malformed/noncanonical SHA-256 values fail before persistence/read acceptance;
36. contract SHA drift -> stale binding;
37. packet SHA drift -> stale binding.

### Provider/runtime selection

38. missing explicit `provider_id/model_id/effort_level` selection at prepare fails closed;
39. runtime kind other than exact `serena` fails `RUNTIME_KIND_AUTHORITY_UNAVAILABLE` before persistence/activation;
40. a selected node with non-empty `worker_requirement` fails `RUNTIME_CAPABILITY_AUTHORITY_UNAVAILABLE` before run/binding commit under the current #433 capability boundary;
41. unknown/unauthorized provider/model/effort at prepare fails;
42. advisory cost/quota ranking, CLI/dataclass defaults, inference and fallback cannot become route authority;
43. provider/model later deauthorized fails through fresh #433 checks;
44. current provider generation/endpoint is never read from the binding row.

### Continuation/replay boundary

45. zero READY -> no binding activation;
46. parent not COMPLETE -> no activation;
47. one READY with valid binding -> #433 called at most once;
48. missing/stale binding -> no #433 call;
49. existing successor durable job -> reconcile/existing behavior, no second physical execution;
50. WAIT -> no same-tick retry;
51. RECOVERY_REQUIRED -> no same-tick retry;
52. restart uses same graph_run_id and existing binding/job identity;
53. no implicit latest/current graph-run query exists in the automatic authority path.

## 20. Likely future source/test scope

This design does not grant these mutations, but the expected smallest shapes are:

### Child A likely scope

- `src/a_conductor/graph/store.py`
- one small typed graph-run authority/persistence module if needed
- `src/a_conductor/graph/__init__.py` only if an export is required
- `tests/test_graph_store.py`
- one focused graph-run authority test file if warranted

### Child B likely scope

- one new bounded application/service module or a narrow existing facade seam;
- focused tests for preparation/binding reconstruction;
- no scheduler/job/execution lifecycle changes.

### Child C likely scope

To be freshly re-archaeologized after A/B acceptance. Historical ZRA-3 source branches are evidence only and must not be ported wholesale.

## 21. Source-release gate

Before any Child A tracked source mutation:

1. this exact governance candidate is committed/pushed on one design-only branch;
2. changed-file scope is exactly this WO;
3. work-order identity/hygiene checks pass;
4. exact-head hosted CI passes;
5. independent exact-SHA R3 design review returns P0/P1/P2 = 0;
6. GPT-5.6 Sol explicitly accepts the corrected design;
7. expected-head merge succeeds;
8. post-main CI succeeds;
9. current main is re-pinned;
10. Issue #215 still confirms the same ownership split;
11. open PR/worktree/claim overlap is rechecked;
12. `DEFECT_LESSONS.md` is re-read before `src/a_conductor/` mutation;
13. Child A receives a new exact issue/claim/worktree/branch and frozen mutable scope;
14. RED tests are added before production code.

Until all gates pass:

`SAFE_TO_MUTATE_ZRA3_SOURCE = NO`

## 22. Cross-device / review-WIP continuity

Windows current session owns only this WO452 governance file.

Mac owns WO453 / PR #456 design-only on `docs/work-orders/WO-P1-453-fmg-prod-canonical-srm-cutover.md`; this Windows lane does not mutate that file, branch, worktree or SunDayRemoteMCP cutover state. PR #456 is still based on pre-`3db441f3...` main and Mac has already been told to re-pin/fan-in the disjoint main delta before final review/acceptance.

WO449/PR #455 remains a separate four-file Browser-Wake ownership history. Issue #449 is currently closed, but an independently verified cycle-2 non-corpus credential-shape HOLD remains unresolved in merged `main@3db441f3...`; this lane observes that conflict only and does not mutate/reopen its issue, branch, worktree or files.

The prior WO452 exact-SHA reviewer is terminal/harvested. WO449's rereviewer later ran on exact `5550f14...`; at this checkpoint its reviewer PID is no longer live and its detached result reports PASS, but folding/acceptance remains the WO449 owner session's responsibility. Before any new WO452 reviewer dispatch this lane must recheck actual process/pointer/Issue state and must not overlap an active WO449 or Mac reviewer.

A previous temporary review-slot overlap remains historical process evidence only. It grants no authority and does not erase exact-SHA review requirements.

## 23. Current verdict

The activation-identity gap is real.

The earlier generic-node-events design is rejected.

The corrected candidate direction is:

**typed GraphStore v2 run preparation + explicit pre-pinned per-node route binding + existing-authority fresh revalidation**

with:

- strict fail-closed migration;
- ControlCenter `project_id -> root_path` reuse;
- graph definition digest with explicit UTF-8 canonicalization;
- replay-safe `preparation_ref` + preparation digest;
- graph_run_id minted only inside atomic prepare;
- exact fixed `runtime_kind="serena"` plus explicit provider/model/effort selection at the accepted preparation front door — no generic runtime routing, advisory ranking, default or fallback authority;
- exact preparation digest over intent fields only, excluding server-minted ids/timestamps and legacy status;
- non-empty `worker_requirement` fails closed before preparation while #433 lacks accepted capability-supply authority;
- same-run continuation reusing the existing graph_run_id;
- inert prepared-only rows and bounded lock-failure semantics;
- no second scheduler/lifecycle/activation/model-routing authority.

Historical exact candidate `8edaa315...` received independent `PASS_DESIGN` with P0/P1/P2/P3 = 0/0/0/5 and exact-head CI green, but was superseded because Sol found the provider-route authority ambiguity after review dispatch.

Historical exact candidate `2cdabef...` then received independent `PASS_DESIGN` with P0/P1/P2/P3 = 0/0/0/5 and exact-head CI run `35563767403` green on Windows/Ubuntu/macOS. Sol adjudication nevertheless rejected it for final acceptance after proving that accepted #433 has no generic runtime-kind authority and that preparation-digest intent fields must explicitly exclude server-generated state. Those review/CI results remain historical evidence only after this repair.

Current mutation verdict:

`SAFE_TO_MUTATE_ZRA3_SOURCE = NO`

Exact next safe action: freeze a new one-file governance SHA with the fixed-Serena/runtime-capability/digest-intent repair, rerun deterministic identity/hygiene checks and exact-head CI, then obtain a fresh exact-SHA independent R3 design review only after global review occupancy is verified zero.
