# WO226 independent contract audit — Astra

Verdict: **CHANGES_REQUIRED_FOR_PACKET_RELEASE**. Two proven composition blockers (F1/F2),
one confirmed cleanup API incompatibility to spell out (F3), and four architecture proof
questions (Q1–Q4). This is a pre-implementation contract review, not a finding that nonexistent
WO226 production code already made duplicate provider calls. Sol retains release/adjudication.

## Pinned authority and scope

- Review WO: `WO-P1-226-ASTRA-CONTRACT-REVIEW-001`, owner Poppy Javis / Astra.
- Source: `7afb33d738086db50bc027c4c47165179a1cb96f` (merged WO225).
- Reviewed WO226/GLM packet: PR308 `a4f2122a1549526aa00c68131ffafd36cf9b24c7`.
- Downstream WO223 packet: `76855b95f8f0b7892f6e5205fc20b13a88a71746`.
- Pre-experiment claim: [Issue214 comment5646610817](https://github.com/aase7en/A-Wiki-Conductor/issues/214#issuecomment-5646610817), claim commit `b483a41`.
- Separate worktree/branch `A-Wiki-Conductor-wo226-astra` / `docs/wo226-astra-contract-review`.
- No production source, tests, public API, schema, dependency or Sol/GLM document changes;
  no live provider call, secret resolution against real storage, real process start, or merge.
- The older root CURRENT-WORK/handoff projections are stale relative to Issue214/current Git.
  User forbids editing other owners' files: scoped continuity in `wo226-astra/` is the fold input,
  with global continuity remaining Sol-owned. This is a review artifact, not a new campaign.

All source positions below refer to the pinned source SHA; packet section numbers refer to
PR308's pinned WO. Evidence: [probe.py](wo226-astra/probe.py),
[observations.json](wo226-astra/observations.json), [source hashes](wo226-astra/source-sha256.json).

## Identity chain and authority

| Link | Actual authority and required relation | Review conclusion |
| --- | --- | --- |
| Author -> deterministic review task | `zero_relay_review_task.py:247–313` re-derives refs/content/hash from `ResultIdentity` + reviewed HEAD; verifies exact file/root/path | Rebind from original typed task/materialized task/author/NativeFileSystem. `DirectReviewRoute.__post_init__` at 242 checks only role/intent; typed route alone is not proof of provenance. |
| Review task -> selected route | Same binder: packet SHA/contract, dispatch task/branch/HEAD, selected assignment worker, provider/model, project/worktree; WO225 lease intent/task at 295–299; `worker_lease.py:273` rejects READ_ONLY nonempty mutable scope | Reuse repaired binder; no rescheduling/reselection in WO226. Author/runtime independence must also be checked downstream, not just author/dispatch inequality at 304. |
| Route -> admission | `zcode_production_assembly.py:227–329`: required independent dispatch project/batch/execution; canonical ACTIVE/nonexpired admission matches provider, generation, batch and dispatch ID | `route.dispatch_execution_id == admission.execution_id`; this is NOT runtime execution identity. |
| Packet/runtime -> fingerprint | `zcode_runner.py:201–216` operation hashes exact contract + full packet SHA; assembly 53–82/347–354 hashes provider/model/endpoint/runtime refs/generation; coordinator 232–249 constructs canonical fingerprint spec | Keep exactly one derivation shared by pure preflight and launch. Full provider identity is represented through runtime ref, not separate DurableExecutionRecord fields. |
| Fingerprint -> runtime record | coordinator 330–385 generates runtime ID; store 306–367 persists it; guard 198–259 assesses lookup result | Dispatch ID may differ from runtime ID. F1/F2 mean fingerprint lookup alone is not exclusive execution ownership or safe multiplicity resolution. |
| Worker/worktree -> runtime | `ExecutionFingerprintSpec` 94–105 and `_identity_matches` 187–199 omit worker/session/lease/admission; record 97–125 has worker but no cleanup authority IDs | WO226 §5.2 correctly demands separate worker equality. Re-read lease owner/session/task, exact worktree, HEAD, runtime and provenance; do not infer them solely from fingerprint equality. |
| Runtime -> physical artifacts | coordinator 350–371 attaches refs; supervised helper 606–627 writes report before process result, binds runtime ID + packet SHA + response byte count/hash | `report.execution_id == handoff.runtime_execution_id == record.execution_id`; `result.json` is process metadata. C0 logical result ref is not a child write path. |
| Handoff -> C1 | WO223 §§3.3–3.5 consumes accepted WO226 handoff, canonical record and complete raw bytes | C1 must hash captured raw bytes and compare report length/hash; strict v2 JSON semantics remain WO223-owned. Helper report lacks contract_ref: bind record.work_order_ref to route contract, not fabricated report fields. |

## Proven findings

### F1 — existing dedup is observation, not atomic launch ownership (blocking)

**Locations:** `supervised_run_coordinator.py:330–385`; `supervised_execution.py:427–452`;
`execution_store.py:306–367`; `worker_lease.py:993–1003`;
`provider_config_store.py:881–921`. WO226 §§5, 8, 11, 13.

**Trigger:** two requests for the same fingerprint both complete `find_by_fingerprint` before
either creates its record. An exact same-owner request can also receive the existing canonical
lease and admission: lease `created=False`, admission `EXISTING`.

**Observed:** a deterministic barrier captures both empty SQLite lookup results. Real coordinator
+ canonical SQLite store + synthetic supervised completion produce **2 distinct runtime records,
2 launch calls, both exit 0**. A second probe uses the **real SupervisedExecutionService** and a
controller that throws before spawning: **2 process-effect port calls, 2 durable RECOVERY_REQUIRED
records, 0 actual processes**. Canonical lease/admission reentry is separately exercised and returns
the same resource IDs. This demonstrates each relevant seam; it is not a full assembled reviewer
E2E (WO226 is absent, and current assembly rejects READ_ONLY).

**Impact:** blindly wrapping the proposed flow does not establish at-most-one model invocation.
SQLite `BEGIN IMMEDIATE` protects each record insert but uniqueness is only on runtime execution ID;
each coordinator generates a different UUID. Canonical capacity admission and an active lease
are not evidence of a single launch winner for same-owner reentry. Rechecking dedup after acquisition
narrows the race but does not by itself make check/create/effect atomic.

**Required proof:** specify and prove a canonical, durable winner before model effect, including
same-session reentry and separate processes. No second scheduler/store/lock authority should be
invented. Whether an existing JobStore CAS/ownership path can provide this inside the released
scope is Sol's decision (Q1); if not, WO226 must stop at DESIGN_GAP, not silently expand shared scope.

### F2 — existing duplicate authority selects newest and ignores older live equivalents (blocking)

**Locations:** `execution_store.py:384–405` orders fingerprint matches by `created_at DESC, rowid DESC`;
`execution_deduplication.py:207–251` uses `matches[0]` only. WO226 §8 says multiple records must be
resolved through that existing authority.

**Trigger:** one fingerprint has two valid identity-matching records, older RUNNING and newer
VERIFICATION_REQUIRED. This is possible once F1 creates duplicates; imported/recovery history can
also expose multiplicity. The probe creates canonical records through the coordinator and sets
the older state through the canonical store API, not a forged frozen-object mutation.

**Observed:** `REUSE_COMPLETED`, selecting newer record while older record remains RUNNING.
No conflict aggregation or reconciliation of the older execution occurs. Guard-only foreign-worker
probe also returns REUSE_COMPLETED, confirming the already-documented separate worker obligation.

**Impact:** using that assessment to authorize reusable handoff/resource cleanup can hide an
outstanding equivalent execution. A globally unrelated newest execution is correctly excluded by
fingerprint filtering (positive control passes); the defect concerns **same-fingerprint multiplicity**.
The packet's ban on newest-row heuristics is insufficient when the prescribed authority itself
implements newest-only selection.

**Required proof:** multiplicity must fail closed/reconcile before handoff or cleanup. Test both
insertion orders, older-live/newer-completed, conflicting workers, and dual completed histories.
A bounded reviewer-specific guard may reject ambiguity before consuming the shared guard; any
change to shared dedup semantics requires Sol's explicit scope adjudication. Do not adopt `[0]`
as exact handoff identity.

### F3 — provider release and lease release have different replay contracts (confirmed caveat)

**Locations:** `provider_config_store.py:1031–1076`, especially 1059–1060;
`worker_lease.py:1249–1295`, especially 1275–1277; provider exact reread at 959–970.
WO226 §10 correctly requires canonical release truth, but the implementation packet should state
this concrete API difference.

**Trigger:** release commits, caller loses acknowledgement, then repeats cleanup after restart.

**Observed:** provider first release persists RELEASED; repeat raises
`PROVIDER_ADMISSION_NOT_ACTIVE`; exact `get_admission(id)` returns RELEASED. WorkerLease repeat
returns `(released=False, already_released=True)`. Foreign session release raises
`LEASE_OWNER_MISMATCH`; after legitimate old release + acquisition by a new session, retrying the
old lease does not release the new owner's lease. An old in-memory lease snapshot still appears
active, confirming why current store reread is required.

**Impact:** neither exception swallowing nor one generic truthy/idempotent-release adapter is valid.
`ProviderAdmissionRecord` has no `already_released` flag. Reusing first-run `release_admission`
blindly can strand reconstruction in recovery despite a successful cleanup; accepting arbitrary
NOT_ACTIVE without exact reread can assert cleanup for the wrong state.

**Required proof:** read the pinned admission ID, revalidate provider/dispatch/batch/generation and
terminal release evidence; accept the known RELEASED equivalent without reacquiring capacity.
For leases accept only `(True,False)` or `(False,True)` plus exact identity/current truth; reject
`(False,False)` and `(True,True)`. The malformed shapes are constructible API values in the synthetic
probe; **WO226's consuming handoff validator does not exist yet**, so no consumer rejection is
claimed. Do not edit GoalCloseout or use WO224 scope.

## READ_ONLY compatibility and minimum extension

Actual assembly test: mutation control PASS; canonical-type READ_ONLY lease with empty scope ->
`ZCODE_LEASE_MUTATION_INTENT_INSUFFICIENT` at assembly 262–263. This is intended ZRA-1 behavior,
not a new defect. Minimum compatible shape: keep the existing mutation entrypoint/default and its
nonempty requested-scope checks (272–283); add an explicit review-only path that requires READ_ONLY
and both lease/requested mutable scopes empty. Share all other authority checks and pure plan
construction. Do not convert a READ_ONLY lease into MUTATION or widen allowed scopes to fit.

Preserve project/task/worker/worktree/branch/HEAD fences; provider generation/model/endpoint/secret-ref
binding; exact packet rehash before send; supervised process identity; report-before-result;
unknown-process recovery; and permission denial. `zcode_protocol.py:307–310` always replies
`approved:false`, and the focused protocol regression passes. That test proves a received request
is denied, **not** that every possible app-server file write must request permission (Q4).

## Crash / replay cuts

| Cut | Current evidence | Required WO226 behavior |
| --- | --- | --- |
| After dedup, before durable record | F1 barrier exposes two SAFE decisions | Durable single launch winner; request loss must not let another writer bypass unresolved ownership |
| Record persisted, before effect | QUEUED/STARTING -> ATTACH_RUNNING in canonical guard | Reconcile exact owned execution; do not assume a child exists or launch because observation is missing |
| Effect may have happened, no terminal result | RUNNING -> ATTACH_RUNNING; RECOVERY_REQUIRED -> BLOCKED_UNKNOWN | Existing supervised/recovery semantics, no blind retry/release on timeout |
| Result/collect succeeded, caller lost before handoff | Reopen SQLite, new coordinator + synthetic durable launcher: same runtime ID, 0 additional launch calls | Continue cleanup on exact resources; this probe proves transport reuse, not full handoff reconstruction |
| Admission release committed, ack lost | F3: repeat error, exact reread RELEASED | Canonical reread and identity fence; no capacity reacquire |
| Lease released, owner changes before replay | Old snapshot looks active; foreign owner release rejected; old-ID retry leaves new owner untouched | Fresh exact lease health + session/task fence, never resolve lease by newest/worker-only lookup |
| Ambiguous cleanup return | Both malformed LeaseReleaseResult shapes constructible; consumer absent | Typed RECOVERY_REQUIRED; no usable handoff, no model replay |

A successful execution record alone has no lease ID/session/admission/batch/dispatch cleanup link
(`execution_record.py:97–125`). An immutable handoff created only after all effects cannot by itself
supply that missing pre-handoff recovery authority. See Q2.

## Proof obligations for Sol

| ID | Obligation / discriminator | Current review evidence | Packet disposition |
| --- | --- | --- | --- |
| PO1 | Two concurrent same-fingerprint calls -> <=1 model-effect winner | F1 fails at coordinator and real service effect port | **BLOCK** until winner protocol is explicit/provable |
| PO2 | Same-owner lease/admission reentry cannot authorize second winner | Real APIs return same lease and EXISTING admission | Include same-session and cross-process REDs; capacity=1 is insufficient proof |
| PO3 | Older live equivalent is not hidden by newer completion | F2 returns REUSE_COMPLETED | **BLOCK** ambiguous multiplicity before cleanup/handoff |
| PO4 | Unrelated interleaved runtime cannot hijack review | PASS: exact fingerprint resolves same record | Retain positive plus before/after interleaving tests in implementation |
| PO5 | Exact completed replay makes no extra call | PASS: original 1, reconstructed launcher 0; same runtime ID | Retain; additionally test the actual WO226 handoff once implemented |
| PO6 | Task bytes/contract/HEAD/provider/model/runtime refs/generation/endpoint change never reuses old result | PASS: 9 changes all SAFE_TO_LAUNCH assessment; no new effect invoked | Plan and launch must share same derivation; SAFE is dedup only, not provider permission |
| PO7 | Worker equality independent of fingerprint | Guard-only negative reuses foreign-worker result | WO226 §5.2 already correct; test explicit bridge rejection |
| PO8 | READ_ONLY never enters mutation mode; ZRA-1 unchanged | Actual assembly rejects READ_ONLY; mutation positive passes; 109 related tests pass | Bounded explicit-mode extension; no default gate weakening |
| PO9 | Lease owner drift/unknown release produces no usable handoff or new model call | API owner fences and replacement isolation proven; ambiguous shapes observed | Fresh store fencing plus missing consumer test required after implementation |
| PO10 | Crash cleanup can be reconstructed from exact durable links | Record lacks resource IDs; no handoff implementation | Q2 design decision before claiming crash-safe handoff |
| PO11 | Dispatch ID != runtime ID remains valid but cross-bound | Actual assembly derives job/runtime separately; C1 packet now agrees | Positive end-to-end synthetic bridge test required; no equality shortcut |
| PO12 | Plan has zero acquire/release/secret-value/process/store-mutation effects and launch cannot drift | Pure seam is planned, not implemented | Keep WO226 §5.1; effect spies and plan equality REDs |
| PO13 | Artifact refs and captured bytes belong to exact execution | Helper producer chain inspected; C1 raw-byte rules already explicit | WO226 transport provenance; WO223 strict semantic/parser proof separately |
| PO14 | Permission request denied; all reviewer writes blocked by an actual authority | Denial regression PASS; universal tool-write mediation unproven | Q4, do not report a sandbox guarantee from a protocol response test |

## Architecture questions (not proven production defects)

- **Q1 — winner authority within current scope:** Which existing durable JobStore CAS/ownership
  transition supplies exclusivity for a fingerprint across threads/processes and survives crash?
  `SQLiteJobStore.transition/checkpoint` are existing versioned primitives, but this review has
  not proven a complete composition. A mutex or second preflight alone is not an accepted solution.
  If shared coordinator/store semantics must change, Sol must decide bounded scope before GLM.
- **Q2 — resource association before effects:** Identify the existing canonical job checkpoint/event
  and stable evidence reference that records route/dispatch/batch, exact acquired lease/session and
  admission IDs, and runtime fingerprint/execution relationship before any unrecoverable cut.
  What proves each missing checkpoint means not-attempted rather than lost acknowledgement?
  Provider deterministic dispatch/batch aids lookup; it does not encode lease session. Reuse existing
  durable evidence rather than add schema/store. No claim that a new schema is necessary.
- **Q3 — replay vs cleanup wording:** §5/§8 call REUSE_COMPLETED a no-new-effect path, while §10
  requires incomplete cleanup after a completed model run to reconcile. Clarify: no new model,
  lease acquisition or admission acquisition; already-owned cleanup/reconciliation may still be
  necessary. Define final record-version freeze after collect/cleanup and exact replay equality.
- **Q4 — enforced reviewer write boundary:** Which accepted runtime/tool/OS authority guarantees
  every write to reviewed code needs a denied permission? The repository has a denial handler,
  not evidence here of universal mediation. Distinguish permitted supervisor `runs/**` artifact
  writes from forbidden reviewer source edits. Resolve with a supported synthetic authority test or
  retain explicit unproven status; this is not a request for an unapproved live provider call.

## Confirmed-only GLM packet amendment draft for Sol

Fold these into the **existing WO226 packet before release**, not a new WO/campaign:

1. Add REDs at the shared lifecycle boundary for same-fingerprint concurrent requests with identical
   owner/session/lease/admission; force both empty lookups using barriers. Count model-effect port
   entries and durable runtime IDs. Prove one durable winner through an existing authorized authority.
   A second guard check or capacity=1 alone is not acceptance. If the released source scope cannot
   provide this, checkpoint DESIGN_GAP with exact call graph and stop for Sol adjudication.
2. Before any reusable handoff or resource release, reject/reconcile multiple equivalent fingerprint
   records. Test older RUNNING + newer completed and both insertion orders. Do not treat the current
   guard's `matches[0]` decision as a proof that no other execution remains active. Keep worker
   cross-binding mandatory and do not change global shared dedup semantics without scope authority.
3. Implement cleanup per the actual APIs: provider lost-ack replay requires exact admission reread
   (RELEASED plus provider/dispatch/batch/generation binding); NOT_ACTIVE alone is insufficient.
   Worker release accepts exactly the two valid boolean shapes; malformed/contradictory/foreign
   owner results must not yield handoff, reacquire or invoke the model. Preserve the new owner's lease.

Keep all existing WO226 restrictions: no ID equality, no live provider, no C1 semantic parsing,
no GoalCloseout/WO208 work, no second store/scheduler, and stop on unauthorized shared-source needs.
Q1–Q4 are Sol architecture adjudication inputs, not unconfirmed GLM repair instructions.

## Reproduction and limits

From the review branch at the pinned source tree:

```sh
PYTHONPATH=src:. python3 docs/reviews/wo226-astra/probe.py
python3 -m pytest -q tests/test_zero_relay_review_task.py tests/test_zcode_authority_bound_assembly.py tests/test_zcode_final_targeted_repair.py tests/test_zcode_phase_c.py::test_permission_requests_are_denied
```

Native macOS/Python execution: probe assertions PASS, **13 observation groups**; focused existing
regressions **109 passed in 0.51s**. TemporaryDirectory contains every test database and synthetic
artifact. The proof imports pinned existing fixture helpers; source-hash preflight prevents silently
running against changed source/fixtures. Real service race uses a controller that always throws
before spawn. No socket/provider client is invoked. Restart is simulated caller memory loss with
fresh store/coordinator/launcher, not an OS-kill or installed-runtime claim. The source-hash manifest
is evidence transport only and does not define production authority.

Passing probe assertions characterize observed counterexamples; they do **not** mean WO226 is green.
No complete READ_ONLY reviewer bridge or cleanup handoff exists at this source pin. Therefore those
post-implementation obligations remain for Sol/GLM. This review's deliverable is the independent
contract adjudication, proof table and amendment above; it does not accept/release implementation.
