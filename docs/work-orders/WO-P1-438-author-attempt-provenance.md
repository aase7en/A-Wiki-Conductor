# WO-P1-438 — durable author-attempt provenance design / RED contract

Date: 2026-09-16
Status: IMPLEMENTATION CANDIDATE / R3 / CANONICAL IDENTITY REBOUND
Issue: #438
Identity schema: GITHUB_ISSUE_V1
Canonical authority: Issue #438 / WO-P1-438
Historical authority alias: Issue #330 / WO-P1-246
Historical claim alias: WO-P1-246-AUTHOR-PROVENANCE-SOURCE-001
Driving dependency: Issue #214 / WO-P1-205 Phase-D
Owner/integrator: GPT-5.6 Sol
Exact design base: `018779d0d2f5a7a7a21adb277e23a617692c36fd`
Branch: `docs/wo-p1-246-author-attempt-provenance-current-main`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo246-provenance-design-current`

## Canonical identity migration - 2026-09-20

This design was minted as WO-P1-246 before WO-P1-381 / WO-P1-386 established and froze the repository current GitHub-backed Work Order identity policy. It remained unmerged when the WO-P1-386 legacy exception corpus was frozen, so the deterministic guard correctly rejects introducing the old low-number filename now.

Issue #438 / WO-P1-438 is the canonical live identity for implementation, review, merge, and closeout. Issue #330 and every pre-rebind WO-P1-246 branch, claim, lane/run ID, commit, test name, and prose reference remain immutable historical evidence aliases. They are not rewritten and they do not constitute a second live authority.

The frozen legacy exception fixture is intentionally unchanged. This identity migration changes no production/test semantics.

Current implementation branch remains the historical alias feat/wo-p1-246-author-attempt-provenance.

Revision r2 (2026-09-16): folds in the independent fourth-pass rereview
findings (column-shape-driven migration incl. the "tables present, meta row
absent" crash edge; explicit execution_id binding surface for Phase-D;
result-artifact binding statement; single-transaction migration shape; DDL
CHECK defense-in-depth) and the GPT-5.6 Sol adjudication on generation
authority: prefix-only repair classification is REJECTED; generation 1
requires a verified authorized repair contract/lineage recomputed from the
deterministic materializer output before author launch. This revision grants
no source mutation.

Revision r3 (2026-09-17): finishing pass on the same adjudication, same
base — aligns the §8 RED contract with the recomputed-lineage generation
authority (tests 6, 9-13, 16, 31), adds §10 rejected alternatives 11-12,
extends §9 scope with the materializer recomputation seam and the §3.5
binding-surface amendment rule, and re-verifies the §2.2 runner-chain
formatting repair (the execution chain stays a fenced block, never glued
paragraph lines; pinned by the deterministic document checks in §11 step
1). Grants no source mutation.

Revision r4 (2026-09-17): docs-only repair after the independent rereview
of r3, same base — (1) removes the bare `author_generation` /
`author_provenance_required` trust fields from publicly constructible
`SupervisedRunIdentity` and replaces them with the single enforced
proof-carrying `AuthorProvenanceBinding` (§3.6), produced only by the
trusted classification seam; the attempt ID remains coordinator-minted
only after `SAFE_TO_LAUNCH`; (2) pins §3.3 generation-1 lineage
reconstruction to durable trusted evidence only (store-re-read rejected
execution, re-read and re-hashed persisted artifacts, existing review
payload parser; caller hashes/verdict/findings never accepted) and BLOCKS
generation-1 author launch until the Phase-D predecessor — a durable
rejected-review linkage the current source does not have (new §2.6) —
exists; (3) relocates defense-in-depth required-pair validation to the
`SupervisedRunCoordinator.run()` pre-delegation seam, so
`supervised_execution.py` stays unchanged (tests 16-17 aligned); (4) names
the lineage-reconstruction home/seam and its re-hash fail-closed rule; and
(5) corrects §4.2 migration wording: the current `executescript`
completes/commits DDL before the explicit `BEGIN IMMEDIATE` migration
transaction for ALTERs+meta, and legacy NULL provenance can never serve as
generation-1 rejected lineage. Grants no source mutation.

Revision r5 (2026-09-17): Sol + independent-review repair on the same base — fixes the migration seam to run inside `SQLiteExecutionStore.initialize()` after the committed `executescript` DDL and before the strict version gate; pins fresh-v2 DDL versus legacy ALTER migration; expands the generation-1 predecessor to the complete durable `RepairTaskMaterializationRequest` lineage; replaces side-effecting `materialize_repair_task()` classification with a shared pure identity derivation; broadens repair-namespace fail-closed detection; and restores the actual `ZCodeServiceLifecycleLauncher` hop in the production chain. Grants no source mutation.

`SAFE_TO_MUTATE_SOURCE=NO`.

This packet resolves only the durable provenance design gap required by WO205
§6/§14. It does not implement Phase-D and grants no source mutation. It must
not create a second scheduler, retry engine, task/job store, claim/lease system,
review lifecycle, provider authority, provenance side-store, or completion
state machine.

## 1. Problem and semantic separation

`zero_relay.ResultIdentity` requires exact `attempt_id`, `generation`, and
`author_execution_id`. Current production author execution persists
`author_execution_id` through `DurableExecutionRecord.execution_id`, but no
accepted durable authority persists the author attempt identity or Zero-Relay
generation 0/1.

These existing values are NOT substitutes:

- `JobRuntimeState.attempt_count`: retry/attempt-budget accounting.
- provider `configuration_generation`: provider configuration CAS/versioning.
- execution-store `version`: record mutation CAS.
- caller hints, wall-clock timestamps, downstream review fields, or prose.

Author provenance is execution-scoped identity. It is not a retry counter and
is not a provider/configuration generation.

## 2. Fresh source archaeology at exact base

### 2.1 Generic JobStore path

`job_state.plan_job_transition()` increments `attempt_count` when entering
`TaskState.EXECUTING`. `job_execution.JobExecutionCoordinator.execute()`
durably commits that transition before invoking its backend. This is a valid
generic job-attempt budget boundary, but it is not the complete production
ZCode author path.

### 2.2 Production ZCode author path

`assemble_zcode_execution()` verifies the `TaskPacketFile` through
`ZCodeTaskPacketIdentity.from_task_packet_file()`, including confined path,
bounded read, and packet hash. The canonical operation identity is derived from
`task_contract_ref + packet_sha256`.

The assembly then creates:

`SupervisedRunIdentity.work_order_ref = packet.task_contract_ref`

and runs:

```text
assemble_zcode_execution()
→ SupervisedZCodeRunner
→ SupervisedRunCoordinator
→ ZCodeServiceLifecycleLauncher
→ SupervisedExecutionService
→ ExecutionStore
→ external helper/model process
```

This path does not traverse `JobExecutionCoordinator` or the JobStore
`GATING -> EXECUTING` transition. JobStore-only provenance issuance is
therefore rejected.

### 2.3 Common durable pre-effect seam

For a genuinely new supervised execution,
`SupervisedRunCoordinator.run()` takes the `SAFE_TO_LAUNCH` branch, constructs
one `DurableExecutionRecord`, and hands it to `SupervisedExecutionService`.

`SupervisedExecutionService.launch()` durably performs:

1. `ExecutionStore.create(record)`;
2. transition to `STARTING` with `supervised:launch-intent`;
3. only then `controller.start(...)`.

For this design, "first external/model effect" means the helper/process spawn
at `controller.start(...)`. Credential/reference resolution may occur earlier,
but it is not the model/process effect whose attempt provenance must precede
launch.

Therefore the record created at this seam is the correct persistence owner for
author attempt provenance.

### 2.4 Dedup / replay behavior

The supervised fingerprint intentionally excludes random attempt identity.
Equivalent existing records become `ATTACH_RUNNING`, `REUSE_COMPLETED`, or
`BLOCKED_UNKNOWN`; those branches must never mint new author provenance.

The repair materializer produces a deterministic contract ref:

`zra2-repair-v1:<sha256>`

and its request accepts only `generation == 1`. The request itself carries
the exact rejected lineage — `rejected_task_sha256`,
`rejected_result_sha256`, `review_reason_id`, and the `AgentRepairRequest`
(task/provider/model/base_head/`source_result_ref`/result
destination/review findings) — and the identity digest is derived over that
full lineage plus the rendered task, so one repair chain maps to exactly one
contract ref, one operation ref, and one supervised fingerprint. The
materializer is currently a deterministic producer/consumer contract, not a
production provenance issuer; current source has no production caller of
`materialize_repair_task()`.

A repair packet has a distinct contract identity and therefore a distinct
supervised fingerprint from the original packet. Because the contract ref is
content-derived over the rejected lineage, recomputing the materializer over
that exact lineage is a verifiable repair authority (used by §3.3); the
ref's string shape alone is not.

### 2.5 Downstream consumers

C0/C1 review routing and review evidence copy/cross-bind an already-existing
`ResultIdentity.attempt_id`, `generation`, and `author_execution_id`.
`GoalCloseout` also consumes attempt identity downstream.

None of those boundaries may mint or synthesize missing author provenance.

### 2.6 Rejected-review linkage archaeology (generation-1 blocker)

Fresh source facts at this base, each verified against the exact files:

1. The review v2 task prompt and authority documents ARE durably
   persisted at deterministic paths derived FROM the author
   `ResultIdentity` + reviewed head
   (`deterministic_review_v2_refs()` / `materialize_review_v2_task()` in
   `zero_relay_review_task.py`), and the authority document embeds the
   author `task_contract_ref`, `task_sha256`, result ref/sha, attempt id,
   generation, and `author_execution_id`. This is a durable ONE-WAY
   author→review-contract document chain written BEFORE the reviewer runs;
   it carries no verdict and no reviewer execution identity.
2. `zero_relay.ReviewEvidence` — the only value that binds the
   rejected-author identity, `reviewer_execution_id`, and disposition
   into one cross-checked artifact — is composed in-process by
   `compose_direct_review_evidence[_from_store]`
   (`zero_relay_review_evidence.py`) and is persisted by NO production
   caller at this base.
3. `DirectReviewV2Route` and `DirectReviewExecutionHandoff` (which alone
   carries the reviewer `runtime_execution_id`) are in-process transport
   values; nothing writes them to any store.
4. The reviewer execution record durably carries
   `work_order_ref = review_contract_ref`, never the rejected author
   execution id; the RE2-A promotion evidence
   (`ReviewPromotionResourceIdentity`) persists review-side identity
   (contract/task sha, lease/admission locators) but no author execution
   binding.
5. `SQLiteExecutionStore` exposes exactly `get(execution_id)`,
   `find_by_fingerprint(fingerprint)`, and `list_events(execution_id)` —
   no query by contract ref, work order ref, or author execution.

Therefore: the current source has NO durable production link from a
rejected author execution to the exact reviewer execution and its parsed
verdict artifact. WO246 must not invent, assume, or overclaim one (§10.17).
Generation-1 author launch stays BLOCKED (§3.3) until the Phase-D
predecessor seam — a durable rejected-review linkage persisted by the
accepted review lifecycle and re-readable through existing store/artifact
APIs — exists under its own explicit scope.

## 3. Accepted authority model

### 3.1 Durable record fields

Extend `DurableExecutionRecord` with two immutable optional fields:

- `author_attempt_id: str | None`
- `author_generation: int | None`

They form one atomic semantic pair:

- both present; or
- both `None`.

When present:

- `author_attempt_id` is non-blank, single-line, bounded opaque text;
- `author_generation` is exactly `0` or `1`.

`None/None` is valid for legacy rows and for supervised executions that have
not been proven to be a Zero-Relay author path. Mixed presence or any other
generation is invalid and must fail closed while reconstructing the record.

The execution record's existing `execution_id` remains the
`ResultIdentity.author_execution_id`.

### 3.2 Attempt-ID mint boundary

The author attempt ID is minted only for a fresh author-eligible
execution — one whose `SupervisedRunIdentity` carries an
`AuthorProvenanceBinding` (§3.6) — in `SupervisedRunCoordinator.run()`
after dedup has returned `SAFE_TO_LAUNCH` and before the first
external/model effect (§2.3: the record persists before
`controller.start(...)`).

The minted pair is persisted on the exact artifact-owning
`DurableExecutionRecord` — the same record that owns `run_dir_ref`,
`stdout_ref`/`stderr_ref`, and `result_ref` — by riding the single existing
creation INSERT (`ExecutionStore.create(record)`). There is no second
write, sidecar table, or post-launch stamp, so no crash window exists
between record creation and provenance persistence.

Format:

`author-attempt-v1:<full uuid4 hex>`

The token is opaque. No caller may provide or override it.

`ATTACH_RUNNING`, `REUSE_COMPLETED`, recovery, restart, polling, collection,
or downstream review must reuse the persisted pair from the exact existing
record and must never mint a replacement.

### 3.3 Generation authority

`author_generation` is NOT a free integer parameter to the coordinator, and a string prefix is NOT authority. Sol adjudication remains: generation 1 requires exact deterministic recomputation over durable rejected lineage.

`SupervisedRunIdentity` gains exactly ONE optional provenance field:

- `author_provenance: AuthorProvenanceBinding | None = None` — the proof-carrying type of §3.6, produced only by the trusted classification seam. Binding present means author-eligible launch; `None` means not author-eligible.

No bare `author_generation` integer and no `author_provenance_required` boolean are added to public identity/plan types.

Classification happens only inside `_assemble_zcode_execution_impl`, after packet and lease authority are verified and before `SupervisedRunIdentity` is constructed:

- generation `0`: original author execution under the accepted verified task packet + canonical lease binding;
- repair namespace: any contract whose ref begins with the reserved family prefix `zra2-repair-` enters the repair-proof path and can NEVER silently downgrade to generation 0. Unknown versions, malformed suffixes, uppercase/short digests, or any unsupported repair-family form fail closed with a typed assembly error;
- generation `1`: only after the full durable predecessor in §2.6/§3.3a exists. The classifier reconstructs the COMPLETE `RepairTaskMaterializationRequest` from durable trusted evidence, then invokes a shared PURE identity derivation in `zero_relay_repair_materializer.py` (provisionally `derive_repair_task_identity(request)`) that returns canonical rendered bytes/hash, path, and `zra2-repair-v1:<digest>` without filesystem mutation. The derived contract ref, packet SHA-256, canonical packet path, and bytes/hash must match the packet being launched exactly;
- the classifier must NOT call `materialize_repair_task()` for authority because that function may create the canonical packet file. Classification is read-only with respect to task artifacts; materialization remains a producer step owned by its existing lifecycle;
- at this exact base the complete durable predecessor does not exist, therefore every repair-family author launch is BLOCKED before external effect;
- `review_only=True` carries no author provenance and mints no author attempt identity.

Caller integers, prefixes, hashes, verdicts, findings, or prebuilt repair requests are never authority. The generic coordinator never infers Zero-Relay semantics from arbitrary work-order strings.

### 3.3a Generation-1 lineage reconstruction: home, seams, input provenance

Home/seam: reconstruction lives in `zero_relay_author_provenance.py` and is invoked only from the `_assemble_zcode_execution_impl` classification branch. It adds no store, scheduler, query authority, retry engine, or lifecycle authority.

The generation-1 identity digest is defined by the COMPLETE `RepairTaskMaterializationRequest`, not merely the three top-level lineage fields. Durable reconstruction therefore needs all of:

- `rejected_task_sha256`
- `rejected_result_sha256`
- `review_reason_id`
- `repair_request.task_id`
- `repair_request.provider_id`
- `repair_request.model_id`
- `repair_request.base_head`
- `repair_request.source_result_ref`
- `repair_request.result_destination_ref`
- `repair_request.review_findings`

A caller may supply only a locator such as rejected `execution_id`; it may never supply any of the facts above as authority.

Current-base archaeology proves the durable sources are incomplete: `DurableExecutionRecord` has no task-packet ref/hash; its `runtime_profile_ref` is an opaque runtime identity rather than provider/model facts; current review persistence does not durably cross-bind the rejected author execution to reviewer execution + parsed verdict; and no accepted durable surface reconstructs `review_reason_id`, repair task/result destinations, or the complete findings set as one repair request.

Therefore generation-1 remains structurally blocked. The Phase-D predecessor must first persist or make reconstructable, through EXISTING accepted review/event/evidence authority, a complete repair-lineage record cross-bound to the rejected author execution and exact reviewer outcome. That predecessor must also be discoverable starting from the repair packet/contract identity being launched (or an equivalent deterministic locator), because the repair digest is not invertible. It must include an accepted task artifact locator/hash (or equivalent deterministic source) plus every field needed to reconstruct the `RepairTaskMaterializationRequest`. The exact persistence shape is outside WO246 and must have its own work order/scope; no provenance side-store is invented here.

When that predecessor exists, reconstruction must:

1. re-read the rejected execution via existing `ExecutionStore.get()`;
2. re-read every referenced persisted artifact through existing artifact/filesystem authority and re-hash it;
3. resolve the exact reviewer execution only from durable accepted review linkage and re-parse its payload with existing `parse_review_v2_response()`;
4. reconstruct every repair-request field from those durable facts;
5. call only the pure repair-identity derivation helper, never the side-effecting materializer;
6. require exact equality with the packet being launched.

Any missing/mismatched/unbound input fails closed before launch. Legacy `NULL/NULL` author provenance can never serve as rejected-author evidence.

### 3.4 Generic/Claude/native executions

Generic `SupervisedCommandRunner` / Claude/native executions and reviewer
supervised executions are not required to carry author provenance: their
identities carry no `AuthorProvenanceBinding` and their records
legitimately persist `author_attempt_id=None, author_generation=None`.

They must not be silently upgraded merely because they traverse the same
supervised coordinator; a trusted task-packet authority would have to be
proven and wired explicitly first. Because the binding type has no public
construction path (§3.6), a generic/native/reviewer caller cannot
self-assert one.

An author-eligible Zero-Relay launch (identity carries a binding) fails
closed with a typed provenance-authority-missing error BEFORE any
external effect, at TWO layers:

1. at assembly, when classification or repair-lineage recomputation fails
   (§3.3/§3.3a);
2. defense in depth at the exact in-scope launch seam:
   `SupervisedRunCoordinator.run()`, pre-delegation — after the
   `SAFE_TO_LAUNCH` mint/stamp and BEFORE the plan is handed to
   `supervised.launch(plan)`, the coordinator re-validates the fully
   constructed record pair iff the identity carries a binding. A
   required-but-absent or malformed pair aborts before delegation, so
   `controller.start(...)` is never reached.

`supervised_execution.py` is intentionally NOT modified (§9): the service
persists exactly the record it is handed, and it cannot know
provenance-required-ness without a new trust field crossing
`SupervisedLaunchPlan` or the record — which would reintroduce the exact
self-attestation surface §3.6 removes (rejected alternative §10.15).

Phase-D composition against such an unprovenanced record fails closed with
typed provenance unknown.

### 3.5 Exact result composition seam

Add one small pure composition module, provisionally
`zero_relay_author_provenance.py`, that:

1. consumes an exact `DurableExecutionRecord`;
2. requires present valid author provenance;
3. cross-binds the supplied task contract ref to `record.work_order_ref`;
4. cross-binds the supplied result ref to `record.result_ref`;
5. consumes already-computed exact task/result SHA-256 values;
6. returns `ResultIdentity` with:
   - `attempt_id = record.author_attempt_id`
   - `generation = record.author_generation`
   - `author_execution_id = record.execution_id`.

It never looks up provenance by fingerprint and never mints anything.

Legacy/foreign/unprovenanced rows fail with stable typed
`AUTHOR_PROVENANCE_UNKNOWN`. Task/result binding mismatch fails with a distinct
typed identity-mismatch error.

Execution/result acceptance remains owned by the existing Phase-D verification
and review authorities; this seam supplies identity, not acceptance.

Binding surface (Phase-D prerequisite, settle at the source gate):
`SupervisedRunCoordinator.run()` currently returns `NativeCommandResult`
without the execution_id, and `find_by_fingerprint` is ambiguous under the
pre-existing concurrent-create race (§5.3). Phase-D must obtain the exact
`execution_id` at mint time through an explicit run-outcome/handle extension
or another exact documented surface — never fingerprint lookup. This is not
a WO246 provenance-field blocker, but it must be settled before Phase-D
implementation so the forbidden fingerprint disambiguation cannot silently
return.

Artifact binding: on the ZCode path, `record.result_ref` IS the chosen ZRA
result artifact — the supervised child-result metadata artifact
(`<run_dir>/result.json` by policy; the zcode backend policy overrides only
`report_ref`). Composition item 4 binds `ResultIdentity` to exactly that
artifact and fails closed on divergence, which satisfies WO205 §6.162's
"explicitly chosen and source-mapped" requirement for this seam; any
different Phase-D artifact choice must be an explicit future decision.

### 3.6 Minimal trusted type/seam: `AuthorProvenanceBinding`

One frozen, pure-data, PROOF-CARRYING value type in the new
`zero_relay_author_provenance.py` module:

- `author_generation: int` — `0` or `1`, from §3.3 authority;
- `task_contract_ref: str` — the exact verified packet contract the
  classification bound to;
- `task_packet_sha256: str` — the verified packet digest;
- generation-1 only (`None` for generation 0), the re-derived lineage
  proof: `rejected_execution_id`, `rejected_task_sha256`,
  `rejected_result_sha256`, `review_reason_id`, and the recomputed
  repair packet sha256 — the durable evidence the classification
  verified, carried so the mint and audits can re-bind without trusting
  any caller fact.

It deliberately carries NO attempt id: the attempt ID is minted only by
`SupervisedRunCoordinator.run()` in the `SAFE_TO_LAUNCH` new-record branch
iff `identity.author_provenance` is a binding — minted beside the existing
`exec-` id and stamped into the new record together with the binding's
generation (§3.2). The binding's `task_contract_ref` must equal the
identity's and record's `work_order_ref` (the same verified packet) at
mint, or the launch fails closed before persistence.

Production seam (exactly one producer): the classification branch of
`_assemble_zcode_execution_impl` (§3.3), via a single factory function in
`zero_relay_author_provenance.py` that re-runs the §3.3 verification
before returning a binding. The dataclass constructor is non-public —
direct construction requires a module-private construction ticket and
raises a typed error otherwise — so generic/native/reviewer callers and
`SupervisedRunIdentity` direct constructors cannot self-assert a
generation (this is convention-plus-enforcement, not cryptography;
forgery via `object.__setattr__`/`dataclasses.replace` is out of model
and rejected, §10.14). The RED contract pins it: no other production
module constructs or imports the factory except the assembly.

The type is a value crossing existing seams only. It creates no second
store, table, scheduler, retry engine, claim/lease system, review lifecycle,
provider authority, or completion state machine; admission authority
remains the existing assembly gates, and persistence remains the single
`execution_records` INSERT.

## 4. Persistence and migration contract

The provenance pair is stored on the existing `execution_records` row. A
separate provenance table/store is rejected because it would create another
persistence authority and an avoidable crash window between record creation
and provenance persistence.

Bump the execution-store schema from v1 to v2.

New nullable columns:

- `author_attempt_id TEXT`
- `author_generation INTEGER`

### 4.1 New database

A fresh v2 database is created by the `initialize()` `executescript` with both provenance columns already present in `execution_records`:

- `author_attempt_id TEXT`
- `author_generation INTEGER`

Fresh-v2 CREATE TABLE DDL also carries defense-in-depth CHECK constraints for generation `{0,1}` and both-or-neither NULL shape. Record-layer reconstruction validation remains authoritative for every database shape.

After the DDL script commits, `initialize()` validates the resulting column shape before stamping `schema_version=2`. Test 1 must prove both the v2 columns and the fresh-DB CHECK behavior.

### 4.2 v1 → v2 migration

For existing databases the migration happens INSIDE `SQLiteExecutionStore.initialize()` after the current `executescript` DDL has completed/committed and BEFORE the old strict version comparison would reject schema v1.

Required control flow:

1. run the v2 `CREATE TABLE IF NOT EXISTS` / index DDL. On a fresh DB this creates the v2 table with provenance CHECKs; on an existing v1 DB the existing table is unchanged;
2. read `execution_store_meta.schema_version` (which may be absent after the historical DDL-committed/meta-write crash edge) and inspect `PRAGMA table_info(execution_records)`;
3. if version is `2`, require valid v2 column shape or fail closed;
4. if version is `1`, or version is absent while the table is legacy/partial-v2 shaped, open ONE explicit `BEGIN IMMEDIATE` migration transaction, re-read BOTH the schema-version meta row and column shape, add only missing nullable provenance columns with `ALTER TABLE`, validate the resulting v2 shape, then update/insert schema version `2` and commit;
5. if version is absent and the table already has valid v2 shape (fresh creation or a DDL-committed/meta-write crash), stamp version `2` only after that shape validation;
6. any unsupported version or inconsistent/unrecognized column shape fails closed with a stable execution-schema error.

The explicit migration transaction is therefore nested in the `initialize()` control flow, not called after `initialize()` returns. This removes the unreachable-seam bug in r4.

Existing rows are preserved exactly and receive `NULL/NULL`; there is no backfill and no synthetic provenance. Migrated legacy tables use nullable `ALTER TABLE ADD COLUMN` steps and therefore do not acquire the fresh-table CHECK set. SQLite can attach some column-local CHECKs during `ADD COLUMN`, but the equivalent cross-column both-or-neither constraint cannot be retrofitted without a table rebuild; WO246 deliberately avoids that rebuild. Record-layer both-or-neither/generation validation is therefore mandatory and authoritative for migrated rows.

The one-column-present state should be unreachable from the accepted transaction but may exist after foreign/manual tampering; migration repairs only the missing column, validates, then stamps `2`. Old binaries opening v2 remain expected to fail their strict version gate; no downgrade is supported.

## 5. Immutability, CAS, crash, and concurrency semantics

### 5.1 Immutability

The provenance pair is insert-time identity. Existing `set_*` / `_update`
operations must never update it.

CAS version increments apply to mutable execution state only and do not change
attempt/generation provenance.

### 5.2 Crash windows

- crash after durable record create but before `STARTING`: provenance already
  exists; replay must recover/attach the same record;
- crash after `STARTING` but before process spawn: same rule;
- spawn failure / `RECOVERY_REQUIRED`: provenance stays on that execution;
- completed replay / result reuse: provenance is reused unchanged.

No crash/recovery path may mint a second pair for the same execution record.

### 5.3 Pre-existing duplicate-launch TOCTOU

`DuplicateExecutionGuard.assess()` is currently check-then-act and
`command_fingerprint` is not unique. Two concurrent coordinators can
theoretically both observe `SAFE_TO_LAUNCH` and create distinct execution
records.

WO246 does not silently redesign that accepted dedup lifecycle.

For WO246:

- each distinct execution record receives a distinct author attempt ID;
- provenance/result composition binds by exact `execution_id`, never "latest
  matching fingerprint";
- no record may borrow another record's provenance;
- an adversarial test must pin this non-mixing property.

Any future fix to make fingerprint launch admission atomic requires its own
authority/scope because it changes execution/dedup semantics.

## 6. Legacy and backward-compatibility behavior

Legacy schema-v1 executions migrate as `NULL/NULL`.

They may still be inspected/recovered through existing execution semantics,
but they are NOT eligible to construct a Zero-Relay `ResultIdentity`.

No timestamp, task hash, provider generation, retry count, record version,
fingerprint order, review field, or caller hint may backfill them.

Legacy `NULL/NULL` rows can never serve as generation-1 rejected lineage:
`NULL` provenance is UNKNOWN, not evidence of a rejected author attempt,
and §3.3a reconstruction reads only present, re-hashed, bound durable
artifacts from provenanced records.

Typed recovery/re-execution under an authorized current task contract is the
only path to obtain current author provenance.

## 7. Dedup / fingerprint implications

Do NOT add `author_attempt_id` or `author_generation` to
`ExecutionFingerprintSpec` or the canonical fingerprint payload.

Reason:

- attempt identity is minted after dedup says a new effect is authorized;
- putting random attempt identity into the fingerprint would defeat replay;
- generation is already bound by the verified task contract authority on the
  ZCode author path — the accepted author contract for generation 0, the
  recomputed repair lineage of §3.3 for generation 1;
- repair packets are distinct deterministic task contracts.

A regression test must prove the fingerprint bytes/digest are unchanged by the
new provenance fields.

## 8. RED-first adversarial contract

Before GREEN implementation, add failing tests for all of these cases.

### Persistence / migration

1. Fresh store creates schema v2 with both nullable provenance columns AND its fresh-table DDL CHECKs reject invalid generation / mixed-NULL provenance at SQL level.
2. Realistic v1 store migrates to v2 preserving every existing row/value.
3. Legacy rows emerge as `None/None`; no backfill.
4. Migration is idempotent.
5. Partial migration (one column already present, meta still v1 — foreign/
   manual state) repairs safely.
6. Tables present with NO meta row (DDL-committed/meta-crash edge): migration
   is driven by `PRAGMA table_info` column shape and stamps v2 only after the
   shape is proven.
7. Unsupported/invalid schema shape fails closed.
8. Mixed NULL provenance or generation outside `{0,1}` reconstructs as
   `EXECUTION_RECORD_INVALID`.

### Mint / persistence order

9. ZCode original author run under the accepted author task authority
   (verified packet + `lease.task_id == packet.task_contract_ref`) gets
   generation 0 and one opaque attempt ID.
10. Any `zra2-repair-` family packet at this base — complete durable repair lineage is unavailable (§2.6/§3.3a) — fails closed with the typed lineage-unavailable/unsupported-repair assembly error BEFORE launch; never generation 0; no external effect. Positive generation-1 launch remains blocked until the predecessor exists.
11. Repair-family contract without a verifiable lineage — including malformed `v1`, uppercase/short digest, unknown `zra2-repair-v2:` (or later unsupported version), digest mismatch, incomplete/unbound lineage, or missing/re-hash-mismatched durable artifacts — fails closed BEFORE launch; never generation 0.
12. Prefix-only grammar match without recomputed lineage classifies nothing:
    no prefix-derived classification path exists.
13. No public `author_generation`, `author_provenance_required`, integer, or
    contract-prefix parameter exists on any assembly or coordinator
    signature; `SupervisedRunIdentity` exposes no bare generation/required
    trust field — its only provenance surface is
    `author_provenance: AuthorProvenanceBinding | None`.
14. Reviewer assembly gets no author provenance.
15. Generic/native supervised run gets no author provenance by default.
16. Author-eligible launch (binding present) whose required provenance pair
    is absent or malformed on the constructed record fails closed at the
    `SupervisedRunCoordinator.run()` pre-delegation check, BEFORE the plan
    is handed to `supervised.launch(plan)`: `controller.start(...)` is
    never invoked; no external effect is observed.
17. Through the UNCHANGED `SupervisedExecutionService.launch()`, the record
    persisted by `ExecutionStore.create(record)` already carries the
    stamped pair by the time `controller.start(...)` is reached — the
    store observes the pair before any spawn, with no
    `supervised_execution.py` modification.
18. Spawn failure/recovery retains the same pair.

### Replay / immutability

19. `ATTACH_RUNNING` reuses the persisted pair and does not call the mint.
20. `REUSE_COMPLETED` reuses the persisted pair and does not call the mint.
21. Re-open/restart reads the exact same pair.
22. Every existing `set_*` mutation/CAS path preserves the pair byte-for-byte.

### ResultIdentity composition

23. Exact proven record composes the seven `ResultIdentity` fields correctly.
24. Legacy/unprovenanced record → `AUTHOR_PROVENANCE_UNKNOWN`.
25. task-contract mismatch → typed identity mismatch.
26. result-ref mismatch → typed identity mismatch.
27. no fingerprint lookup can substitute another execution record.
28. two records with one fingerprint retain distinct attempt IDs and cannot
    cross-compose provenance/results.

### Regression / boundaries

29. Fingerprint canonical bytes and digest remain unchanged.
30. provider `configuration_generation`, `attempt_count`, execution-store
    version, timestamps, downstream review fields, and caller hints remain
    unused as provenance authority.
31. Pure derivation parity (mandatory): the new pure repair-identity helper and `materialize_repair_task()` produce exactly the same rendered bytes/hash, canonical path and `zra2-repair-v1:<digest>` for one verified request; the pure helper performs ZERO filesystem writes. Only that derived identity is eligible for future generation-1 classification. Launch still fails closed per test 10 until the durable predecessor exists.
32. current review/GoalCloseout modules remain consumers only.
33. Self-attestation rejection: `AuthorProvenanceBinding` cannot be
    constructed outside its single classification factory (direct
    construction raises the typed construction error); a reviewer or
    generic/native identity constructed directly with any
    provenance-shaped input mints nothing and persists `None/None`; a
    coordinator handed a binding-less identity never stamps a pair.

## 9. Smallest plausible future source scope

This section is a design result only. It is NOT yet a mutation grant.

Expected minimum source frontier:

- `src/a_conductor/execution_record.py`
- `src/a_conductor/execution_store.py`
- `src/a_conductor/supervised_run_coordinator.py`
- `src/a_conductor/zcode_production_assembly.py`
- `src/a_conductor/zero_relay_repair_materializer.py` (extract/reuse one pure deterministic repair-identity derivation helper shared with the existing materializer; no behavior change to the producer/materialization contract)
- NEW `src/a_conductor/zero_relay_author_provenance.py` (composition seam
  of §3.5, the `AuthorProvenanceBinding` of §3.6, and the §3.3a lineage
  reconstruction functions — the reconstruction home)
- focused tests for those boundaries, extending existing test modules where
  possible rather than creating duplicate test authorities.

Explicitly OUT of this frontier at r5:

- `supervised_execution.py` — unchanged. Defense-in-depth pair validation
  lives at the coordinator pre-delegation seam (§3.4); the service
  persists exactly the record it is handed, so the store observes the
  stamped pair before `controller.start(...)` without any service edit.
  Adding the check inside `SupervisedExecutionService.launch()` would
  require a new trust field crossing `SupervisedLaunchPlan` and is
  rejected (§10.15).
- the durable rejected-review linkage (Phase-D predecessor, §2.6) — the
  missing production link from a rejected author execution to the exact
  reviewer execution/artifact. It must be persisted by the accepted
  review lifecycle under its OWN explicit design/mutation scope (own work
  order; the natural candidate surfaces are the existing review
  evidence/promotion seams — e.g., persisting the composite
  rejected-author + `reviewer_execution_id` + disposition value through
  the existing event/evidence authority — but that decision is NOT made
  here). Until it exists, generation-1 author launch stays blocked and
  this frontier must not grow to simulate it.

If the Phase-D binding-surface decision (§3.5) requires extending the run
outcome/handle beyond `supervised_run_coordinator.py` (for example
`zcode_runner.py`), that file list must be amended explicitly at the
source gate before touching it.

Expected unchanged authorities:

- `job_state.py` / JobStore attempt accounting;
- provider configuration/admission semantics;
- worker lease semantics;
- `zero_relay.py` decision state machine;
- C0/C1 review lifecycle;
- `goal_closeout.py`;
- scheduler/task/claim state;
- WO205 source;
- WO227/ZRA-3;
- Browser Wake;
- credentials / secret storage.

If implementation archaeology proves another file is necessary, the source
gate must be amended explicitly before touching it.

## 10. Rejected alternatives

1. **JobStore-only issuance** — rejected: production ZCode author path bypasses
   JobExecutionCoordinator/JobStore.
2. **Caller-provided attempt ID, generation integer, or contract-prefix
   hint** — rejected: caller hints are not durable provenance authority.
3. **Generic coordinator derives generation from arbitrary work-order strings**
   — rejected: it would assign Zero-Relay author semantics to native/reviewer
   executions lacking proven author packet authority.
4. **Provider configuration generation** — rejected: different semantic
   counter.
5. **Execution-store CAS version** — rejected: record mutation version, not
   attempt identity.
6. **`attempt_count`** — rejected: retry budget/accounting, not opaque identity.
7. **Separate provenance table/store** — rejected: duplicate persistence
   authority plus an additional crash window.
8. **Backfill legacy rows** — rejected: would fabricate identity after the
   effect.
9. **Put random attempt ID in the fingerprint** — rejected: breaks dedup/replay.
10. **Downstream review/GoalCloseout minting** — rejected: those are consumers.
11. **Prefix-only repair classification** — rejected (Sol adjudication
    2026-09-16): a `zra2-repair-v1:` grammar match alone is not authority;
    generation 1 requires recomputation of the deterministic materializer
    output over its exact rejected task/result/review lineage, cross-checked
    before author launch.
12. **Silent downgrade of unprovable repair-namespace contracts to
    generation 0** — rejected: a contract claiming the repair namespace
    without a verifiable lineage fails closed instead.
13. **Bare `author_generation`/`author_provenance_required` trust fields on
    publicly constructible `SupervisedRunIdentity`** — rejected: any
    caller could self-assert mint authority and make the generic
    coordinator mint author provenance for a native/reviewer execution;
    replaced by the single enforced proof-carrying binding (§3.6).
14. **Direct/self-attested `AuthorProvenanceBinding` construction** —
    rejected: the type has no public constructor path; only the single
    classification factory over durable evidence can produce it. Forgery
    via `object.__setattr__`/`dataclasses.replace` is out of model and
    pinned by test 33.
15. **Defense-in-depth required-pair validation inside
    `SupervisedExecutionService.launch()`** — rejected: the generic
    service cannot know provenance-required-ness without a new trust
    field crossing `SupervisedLaunchPlan`/record, reintroducing the
    §10.13 self-attestation surface; the check stays at the coordinator
    pre-delegation seam and `supervised_execution.py` stays unchanged.
16. **Generation-1 lineage from caller-provided hashes, verdicts, or
    findings** — rejected: §3.3a accepts durable evidence only —
    store-re-read rejected execution, re-read/re-hashed persisted
    artifacts, persisted review routing/payload re-parsed by the existing
    parser; a caller may name an `execution_id` locator, never a fact.
17. **Inventing the durable rejected-review linkage inside WO246** —
    rejected: no durable production link from a rejected author execution
    to the exact reviewer execution/artifact exists at this base (§2.6);
    fabricating one inside this packet would overclaim a seam the source
    does not have. Generation-1 author launch stays blocked until the
    Phase-D predecessor exists under its own scope (§9).

## 11. Design acceptance gate

Risk remains **R3**.

This r5 candidate incorporates the independent r4 review and Sol source adjudication: migration now executes inside `initialize()` before the strict version gate; fresh-v2 DDL and legacy ALTER shapes are explicit; generation-1 requires the complete durable `RepairTaskMaterializationRequest`; classification uses a pure no-write identity derivation; broad `zra2-repair-` family detection fails closed; and the actual lifecycle-launcher hop is restored. Generation-1 remains BLOCKED until its separate durable predecessor exists. Steps 3-5 below must run against this exact amended text before freeze.

Before any source/test/schema mutation:

1. deterministic document checks:
   - exact one-file scope: only this work-order file differs from the
     design base;
   - `git diff --check` clean (no whitespace errors);
   - strict UTF-8 decode of this file succeeds;
   - the §2.2 runner chain is intact as one fenced code block (never
     glued paragraph lines);
2. fresh CoinTH quota/readiness preflight;
3. independent GLM-5.3 read-only design rereview of this exact draft;
4. Worker/source challenge where available;
5. GPT-5.6 Sol adjudication against actual source, explicitly re-confirming the load-bearing seams in `supervised_execution.py`, `execution_deduplication.py`, `zero_relay.py`, `zero_relay_review_execution.py`, `zero_relay_review_verification.py`, `zero_relay_repair_materializer.py`, `agent_change_packets.py`, `job_state.py`, `job_execution.py`, and `goal_closeout.py`;
6. freeze/persist this design candidate;
7. publish an explicit exact source/test mutation scope and claim on Issue #330.

Until all seven steps pass:

`SAFE_TO_MUTATE_SOURCE=NO`.

No implementation, schema edit, test edit, merge, or deployment is authorized
by this design document alone.


## 2026-09-21 — merged/post-main/session-rollover checkpoint

Canonical candidate `f93e16377f500d16cbed66763058c2f4a2237790` received an independent GLM-5.3 MAX exact-SHA R3 review: PASS, P0/P1/P2=0, P3=3 non-blocking. The review finished at 2026-09-20T18:50:23Z. Exact-head CI #1102 / run `35529389831` completed SUCCESS at 2026-09-20T19:01:42Z. Both gates therefore existed before PR #336 merged at 2026-09-21T06:20:49+07 as `75d9e96e46e15cc8ef647d12194d677657689bde`.

Detached post-main verification at `A:\GitHub\_worktrees\A-Wiki-Conductor-post438-75d9e96` proved all 11 WO438 blobs identical to the reviewed candidate, focused 177 PASS, identity 33 PASS, `git diff --check` PASS and `py_compile` PASS. A wrapper-only PowerShell `[Math]::Max` arity error occurred after all verification and changed no repository state.

Hosted post-main push CI run `35544371466` on exact merge SHA `75d9e96...` completed SUCCESS on Windows, Ubuntu and macOS, including core suites, Portable/Setup build, archive verification, Portable smoke and Setup install/uninstall E2E. Issue #438 is CLOSED / COMPLETE / POST_MAIN_VERIFIED and its claim is released. Current remote main is `894c64d...` after disjoint PR #440 continuity drift; WO438 candidate/merge remain ancestors and its source/test paths are unchanged. Issue #214 now has `PHASE_D_§14_NEXT_READY=YES`; source mutation remains NO until WO205 §14 steps 1–7 complete on then-current main.
