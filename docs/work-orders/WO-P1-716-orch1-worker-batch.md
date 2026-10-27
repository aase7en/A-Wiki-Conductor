# WO-P1-716 ORCH-1/4 Worker Batch Dispatch

Identity schema: GITHUB_ISSUE_V1
Issue: #716

Parent: #709 (ORCH-1 foundation).

Status: AUTHOR_VERIFIED / FREEZE_FOR_INDEPENDENT_REVIEW / R3 / CONTROL_PLANE_ONLY.
Owner: Kilo author lane (not acceptance authority).
Claim: ORCH-1-4-WORKERBATCH-001 / #716 comment 6436145647; relocation authorized by user.
Base: origin/main a6210179883a1119746d9c8bcaa9ecced8970ad9.
Worktree: `A:\GitHub\_worktrees\AWC-orch1-dispatcher`.
Branch: `feat/orch1-worker-dispatcher`.
Device: Windows, local tool surface; device UUID not independently verified.

## Scope And Authority

### Authorized Addendum - 2026-10-27 Before Source Amendment

Authority: explicit orchestrator user instruction in this recovery session,
"CONTRACT DECISION GRANTED", conform-to-design precedent #718; commissioned
contract ORCH-1-foundation-design.md section 3 GuardPipeline table (Worker-batch
duplicate stage): reuse current durable execution/dedupe/recovery admission for
each exact selected task; #583 is not a worker deduper. This supersedes the
historical blocker below and the prohibition on /3 edits for this delta ONLY.

Extend the existing claim allowlist to orchestration_guards.py and
tests/test_orchestration_guards.py. The ONLY guard-source change permitted is
DuplicateGuard's WORKER_BATCH branch: NOT_APPLICABLE with metadata
{"worker_dedup": "DELEGATED_TO_EXECUTOR_ADMISSION"}. This is an accepted R3
semantics amendment, not dedup permission minted by the guard. UtilizationGuard,
AuthorityGuard, and all Parent behavior remain unchanged. RED-first guard tests
must pin the new expectation; dispatcher duplicate matrix must prove zero effects
using existing durable executor admission. Independent focused re-review of this
guard delta is REQUIRED before merge alongside the dispatcher PR. No merge is
authorized. Shared continuity documents and other worktrees remain untouched.

Final mutable allowlist: this WO, orchestration_guards.py, its test file,
orchestration_dispatcher.py, its test file, runtime_activation.py; at most one
thin facade only if required (none currently planned). R3 authority/failure model
and final USE checks below remain binding. Existing claim is retained, not replayed.

Original mutable allowlist (extended by the authorized addendum above): src/a_conductor/orchestration_dispatcher.py,
tests/test_orchestration_dispatcher.py, this WO, and additive
src/a_conductor/runtime_activation.py composition only. No facade file needed:
the explicitly activated runtime root exposes handle directly, with no public
operator/HTTP route or startup registration. Evidence under runs/WO-P1-716/.

## Adopted WIP And Authority Binding

User authorized relocation after the orchestrator removed the broken worktree
and its zero-commit branch. Do not recreate them. Adopt the 2026-10-24 skeleton
and tests as unproven WIP. Handoff described 70/102 lines; actual reads show
89 source / 128 test lines. Existing skeleton accepts caller-supplied admission,
mutable dict outcomes, invalid empty payload fixtures and a misspelled exception.
It has no canonical stores, runtime root or final USE authority. Retain only its
bounded coordinator responsibility; replace the unsafe protocol and tests.

Historical framing (superseded by the authorized addendum): the /2 receiver
returns NOT_APPLICABLE for workers; /3 DuplicateGuard denied workers. Do not
forge a Parent signal or preflight PASS. Compose the accepted receiver validation
and accepted UtilizationGuard/AuthorityGuard with worker job/dedup evidence in
the new dispatcher, preserving duplicate -> utilization -> authority order.
Read-only intent classification precedes scheduler batch lookup. Injected
authority readers own canonical intent/plan/task/READY generation and USE checks;
they are application dependencies, never signal fields or external receipts.

Bound this first implementation to one selected review task and one canonical
SQLite provider admission with max_concurrency=1. Existing atomic admission
serializes competing provider batches; reject other capacity shapes as
ORCH_WORKER_SERIALIZATION_UNPROVEN instead of creating an ORCH lock. Existing
worker lease store remains worker/hotspot authority. Root pins job/provider/lease
database identity; construction does not initialize stores. Jobs must already
exist NEW/READY with zero attempts; existing other states are observations or
reconciliation, never replay. Reuse job checkpoints for required pre/post audit.
At runner USE, re-read canonical binding and job version/result, provider
generation, WorkerLeasePreDispatchGuard and live worktree identity before the
accepted runner. No caller GuardResult or arbitrary execute(dict) adapter.

GLM_OFFLOAD=BLOCKED / ROUTE_UNVERIFIED for this recovery: native Task and
agent_manager dispatch tools are not exposed in this session. No provider
subdispatch or parallel subagent execution is claimed. The assigned author lane
used deterministic tools in parallel, not a fabricated independent reviewer.

REUSE accepted receiver/guard policies, scheduler, execution dedup/recovery,
provider authority, leases and PRE_DISPATCH. Do not edit accepted slices /1-/3
except the exact DuplicateGuard branch and focused tests authorized above,
#583/#517 policy, CI, CURRENT-WORK.md, handoff.md or COLLAB.md. Shared continuity
fold-back remains integrator-owned; this WO and issue comments carry checkpoint.
No secrets, live provider dispatch, runtime database writes, process changes,
Parent queue effects, new routes/operator verbs, or merge. Commit/push and one
PR are authorized only after honest verification and scope checks.

## Frozen Contract And Failure Model

One validated ENQUEUE / WORKER_BATCH intent may invoke at most one bounded
existing ParallelReadyExecutor batch with require_provider_authority=True.
Resolve scheduler plan/task map and classifier facts from authority readers,
not signal metadata or caller booleans. Only read-only review tasks may dispatch.
Mutable refill must deny CANONICAL_MUTABLE_CLAIM_AUTHORITY_UNAVAILABLE before
scheduler/provider/lease effects while #551 is unresolved.

Imports/construction perform no I/O. Runtime registration is explicit and
additive, never startup/refresh activation. Existing authority must serialize
admission; no ORCH mutex/store/semaphore substitutes for missing serialization.
Final USE checks bind provider generation, claim/lease, HEAD and result truth.
Unknown authority fails closed; possible effects retain canonical IDs and must
not be replayed to repair audit/observability loss. One immutable bounded outcome
uses design decision labels, typed reasons, subject/evidence/execution IDs and
observability_degraded. Output never recursively triggers work.

Proposed composition reason catalog, before any implementation uses it:
ORCH_WORKER_SERIALIZATION_UNPROVEN for absent existing serialization authority;
ORCH_WORKER_BINDING_INVALID for unresolved/mismatched scheduler/task binding;
ORCH_WORKER_AUTHORITY_UNAVAILABLE for missing required authority evidence;
ORCH_AUDIT_UNAVAILABLE for a failed required pre-effect checkpoint;
ORCH_OUTCOME_RECONCILIATION_REQUIRED for uncertain post-effect observation.
Additional frozen local codes: ORCH_SIGNAL_NOT_DISPATCHABLE (wrong kind/target),
ORCH_WORKER_REVIEW_ONLY (non-review intent), ORCH_WORKER_BINDING_DRIFT (late
generation/task map drift), ORCH_WORKER_USE_DENIED (malformed USE authority),
ORCH_DISPATCH_OBSERVED (validated runner result), ORCH_NO_ACTION (empty plan),
ORCH_EXECUTOR_REQUIRED (invalid application composition).
ORCH_REENTRANT_DENIED prevents a publisher calling back into the same handle;
it is an invocation-context guard, not a lock or durable dedup authority.
The final USE chain also runs at the backend call after durable EXECUTING,
not just at runner entry before graph/job transitions. Explicit non-refill
requests still check canonical occupancy budgets without inferring A-Faster
activation. One configured review worker slot and provider are bound by the
application composition; tasks outside that configured slot fail closed.
This catalog is frozen for this implementation (the old proposal-only status is
superseded). ORCH_NO_ACTION remains reserved, not emitted for malformed empty
plans. Preserve exact
existing typed guard/executor reasons wherever available. No catalog expansion
or scope extension is authorized implicitly by this packet.

## Acceptance And Verification

RED first against base/stub, then GREEN through the actual registered runtime
root and fixture-owned canonical stores. Prove happy path exactly once with
durable IDs and authority-sourced classifier facts; duplicate zero effects;
late claim/provider generation/HEAD/result drift refusal at USE; competing
producers/hotspot bounded capacity; mutable refill denial before effects;
required audit failure before/after effect; retained IDs without relaunch;
repeated invocation without self-triggered recursion.

Run focused new tests, existing three orchestration suites, discovered related
runtime_activation/parallel_ready/facade suites, compileall, diff-check, strict
UTF-8/no BOM, added-line secret scan, exact allowlist check, and the canonical
work-order identity suite. Record exact counts, not expected counts. Only then
AUTHOR_VERIFIED / FREEZE_FOR_INDEPENDENT_REVIEW, commit/push and one PR with
exact SHA evidence. Independent exact-SHA R3 review, hosted CI and acceptance
are separate NOT_RUN gates; merge remains unauthorized.

## Checkpoint

### Author Verification And Freeze - 2026-10-27

Recovery identity verified from Git and #716 comment 6441930085. Starting HEAD
and remote main both a6210179883a1119746d9c8bcaa9ecced8970ad9; dirty four-file
WIP matched the assignment. Initial checkpoint API lookup mistakenly used a
different repository owner and returned 404; corrected to verified remote
aase7en/A-Wiki-Conductor and successfully read the checkpoint and active claim.
No other worktree or shared continuity document was touched. The existing claim
ORCH-1-4-WORKERBATCH-001 remains reserved through review, not released.

The addendum above was written BEFORE any guard-source edit. RED run with
current-schema fixtures: 26 failed / 89 passed in 10.09s (4 new guard expectation
failures and 22 stale-dispatcher API failures). After current-schema ingress and
actual pipeline composition: 114 passed / 1 test-expectation failure; corrected
the test to assert a bounded ADMITTED_CONTEXT_INVALID rather than TypeError for
boolean admission. Extra adversarial RED: foreign work-order selected a task
and a late EXECUTING checkpoint allowed one backend call (2 failed / 24
deselected, 2.03s). Fixed exact work-order binding and captured the canonical
EXECUTING transition result before comparing fresh job truth at backend USE.
No new reason codes beyond the frozen catalog; existing job/guard/provider codes
are preserved where available.

Registered production composition is runtime_activation.activate_worker_batch_runtime:
explicit root -> Dispatcher.handle(signal, admitted=AdmittedContext) -> current
codec validation -> Parent-only receiver NOT_APPLICABLE -> injected scheduler
intent/plan/task readers -> actual GuardPipeline -> existing ParallelReadyExecutor
(require_provider_authority=True) -> SQLite provider admission -> WorkerLeaseBroker
-> guarded GraphDispatchParallelRunner -> DurableJobExecutionCoordinator ->
backend USE recheck. No public facade/route was added. Function definition/import
does not activate anything; composition does not initialize/read owning stores.
Canonical path identity resolution is performed explicitly at registration.

Guard delta is ONLY two replacement lines in the WORKER_BATCH branch. No
UtilizationGuard/AuthorityGuard/Parent behavior changed. DuplicateGuard says
NOT_APPLICABLE, never PASS; it delegates dedup to existing durable job/executor
admission. Fresh application roots observe the same canonical completed/inflight
job instead of creating an ORCH store or using signal-ID dedup. Provider-global
admission and canonical job version transitions retain final concurrent authority.

| Matrix row | Exact test / evidence |
|---|---|
| Current-schema receiver + pipeline | guard test_worker_pipeline_requires_authority_after_delegated_duplicate [True/False/None]: matching separate ingress, receiver NOT_APPLICABLE; only True admits; delegation metadata pinned |
| Happy, actual root, durable IDs, fact provenance | test_registered_root_happy_path_durable_ids_and_no_ambient_activation + test_registered_root_uses_actual_pipeline_and_authority_facts: one backend call, canonical job VERIFYING, exact job ID and canonical-ready/result evidence; facts are the injected scheduler object; pipeline called once |
| Durable duplicate, zero extra effects | test_duplicate_and_repeated_invocation_have_zero_new_effects: three repeats plus a fresh root/new signal ID; calls stay 1, job events/provider admissions/active leases unchanged; JOB_ALREADY_VERIFYING |
| Mutable before effects | test_nonreview_denied_before_scheduler_provider_lease [REFILL/EXPLICIT x mutable/unknown]: mutable exact CANONICAL_MUTABLE_CLAIM_AUTHORITY_UNAVAILABLE; batch/provider/lease spies receive zero calls |
| Late USE drift | test_late_drift_at_use_never_launches [claim/provider/head/result/generation/lease]: zero backend calls; backend-use tests separately inject head/result and claim/provider/lease/generation AFTER canonical EXECUTING and still launch zero |
| Contention / caps | test_two_producers_same_hotspot_atomic_capacity: one call; test_distinct_jobs_contend_on_existing_provider_capacity: different job IDs, second PROVIDER_CAPACITY_EXHAUSTED, one admission/lease/call; test_existing_worker_lease_caps_review_slot: occupied canonical worker lease retained, zero calls |
| Serialization / quota / occupancy | test_unknown_serialization_fails_closed: max_concurrency 2 denied; test_authority_classifier_facts_deny_refill [occupied/unknown quota], test_explicit_review_respects_global_occupancy: zero calls |
| Required audit before/after | test_required_audit_failure_never_replays [before/after]: before zero calls; after one call, RECONCILIATION_REQUIRED, retained job ID, observability_degraded=True; repeat never relaunches |
| Observer loss / no recursion | test_observer_failure_degrades_without_relaunch: dispatch observed with degradation, no replay; test_publisher_cannot_reenter_dispatch: one bounded callback refusal ORCH_REENTRANT_DENIED, one backend call |
| Identity / no ambient activation | wrong source/boolean ingress, separate ingress mismatch x3, foreign WO, canonical DB mismatch; test_runtime_registration_does_not_initialize_or_read_stores: zero reads/effects during explicit registration |

Final deterministic verification:
- Focused: `python -B -m pytest -q -p no:cacheprovider tests/test_orchestration_dispatcher.py tests/test_orchestration_guards.py tests/test_orchestration_receiver.py tests/test_orchestration.py --tb=short`: 287 passed in 9.19s (dispatcher 37, guards 91; receiver+codec 159).
- Related: `python -B -m pytest -q -p no:cacheprovider tests/test_runtime_activation.py tests/test_parallel_ready_execution.py --tb=short`: 95 passed in 9.88s.
- Identity: `python -B -m pytest -q -p no:cacheprovider tests/test_work_order_identity.py --tb=short`: 33 passed in 1.21s.
- compileall over the five changed Python files passed; generated source/test __pycache__ directories removed after compilation. Final strict UTF-8/no BOM, added-line secret scan, staged diff-check and exact six-file scope are recorded with the frozen issue comment.

Freeze delivery: two logical commits (authorized guard delta, then registered
dispatcher integration), normal push and one PR. Exact final SHA and PR URL are
recorded on #716; no self-referential SHA is embedded in this commit. Independent
focused R3 re-review of the guard delta AND the dispatcher is REQUIRED before
merge. Independent review and hosted CI are NOT_RUN at author freeze; no review
PASS, merge, completion of mutable refill, live provider dispatch, production
activation or exactly-once guarantee across crashes is claimed. Fixture happy
path exactly-one-call evidence is not a universal exactly-once guarantee.

Open risks: trusted application scheduler/claim readers and backend must be
bound by an actual admitted host; no automatic producer/startup registration.
This slice deliberately supports only one configured read-only review task,
one provider with concurrency 1, one batch per call. Claims/HEAD checks are
launch-boundary observations, not a new cross-device fence. Existing provider
admission/lease/job authorities own concurrent safety and uncertain recovery;
audit failure after possible effect requires reconciliation, not replay. #551
continues blocking mutable dispatch. Parent enqueue/replay is not implemented.
Next safe action: independent exact-SHA challenge including the focused guard
amendment; then hosted CI and integrator adjudication. NO merge by this lane.

### Fresh Recovery - 2026-10-27 (supersedes historical checkpoint below)

Existing Issue #716 comments were read; claim ORCH-1-4-WORKERBATCH-001
was not duplicated. The current user explicitly assigned the relocated lane
`A:\GitHub\_worktrees\AWC-orch1-dispatcher` / `feat/orch1-worker-dispatcher`.
Starting HEAD was 955822715917d5489c1bc193e6dc0cf278bc5e28. Actual adopted WIP
was 297 dispatcher lines, 290 test lines and an additive 54-line runtime root,
not the older 70/102-line skeleton described in the handoff. No source/test
content was changed by this recovery session.

Executed exactly: `git stash push -u`, `git fetch origin`,
`git merge --ff-only origin/main`, `git stash pop`. All succeeded without
conflicts. HEAD/base is a6210179883a1119746d9c8bcaa9ecced8970ad9. Dependencies
on repaired core PR #720 and runbook PR #721 are satisfied by this fetched base.
The stash was successfully restored and dropped by Git; adopted WIP remains
uncommitted. No other worktree or shared continuity file was changed.

Contract blocker: the current request requires execution through the actual
`GuardPipeline`, while forbidding modifications to orchestration_guards.py.
At this base DuplicateGuard.evaluate unconditionally refuses every WORKER_BATCH
effect (lines 46-48), and GuardPipeline.evaluate short-circuits on that refusal
(lines 187-188). Its sole constructor injection is the authority checker; there
is no worker duplicate-stage injection seam. The proposed composition in this
WO's historical framing uses the individual utilization/authority guards instead
of the required pipeline and therefore does not satisfy the current request.
No denial was converted into permission, no Parent signal was forged, and no
monkeypatch/subclass bypass was introduced.

Deterministic current-API probe: a valid orch-signal.v1 WORKER_BATCH ENQUEUE,
passed to SignalReceiver with a separate matching AdmittedContext, returns
NOT_APPLICABLE. The same valid signal passed to GuardPipeline returns
admitted=False / RECONCILIATION_REQUIRED, with
duplicate.reason_code=WORKER_DEDUP_AUTHORITY_REQUIRED and zero authority-checker
calls. Probe assertions passed. An initial direct Python probe lacked src on
sys.path and failed ModuleNotFoundError; the corrected probe explicitly added
src and proved the above result. No effect ports or runtime stores were used.

Adopted-WIP baseline command:
`python -B -m pytest -q -p no:cacheprovider tests/test_orchestration_dispatcher.py --tb=short`
returned 23 failed / 1 passed in 6.72s. All 23 failures occur at the obsolete
OrchestrationSignal constructor before handle/effect execution. The one passing
case is canonical database identity mismatch refusal, not worker matrix proof.
No happy/duplicate/drift/contention/mutable/audit/recursion matrix row is proven.

Checkpoint verification: work-order identity plus unchanged guard suites returned
121 passed in 6.51s using `python -B -m pytest -q -p no:cacheprovider
tests/test_work_order_identity.py tests/test_orchestration_guards.py`.
`git diff --check` passed for tracked WIP; the new WO remains untracked, so that
command does not validate its content. This is not candidate author verification.

Next safe action is integrator adjudication of the exact scope/contract conflict:
either authorize a bounded worker-dedup seam in the existing GuardPipeline under
a separately explicit guard-source/test scope, or explicitly ratify the design's
individual-guard worker composition instead of requiring GuardPipeline admission.
No source implementation, AUTHOR_VERIFIED freeze, commit, push, PR or merge is
claimed. Remaining candidate verification gates are NOT_RUN. Preserve the lane
and adopted WIP; no cleanup or claim release is inferred.

2026-10-27: AGENTS and FAST_EXECUTION_PROTOCOL fully read; DEFECT_LESSONS fully
read (838 lines); authoritative design fully read (481 lines). Guard source
and initial runtime_activation section inspected. Remaining mandatory accepted
source/test/boundary and entry reads are NOT_COMPLETE; no source admission.

git fetch origin main succeeded; origin/main matched the requested full SHA.
Authorized git worktree add was interrupted with tool error ChildProcess.kill.
Git registered the requested branch/worktree at base but left it locked
initializing, with an empty worktree-specific index.lock in shared metadata.
Two status observations showed all tracked paths as staged deletions and
checkout files as untracked. This is initialization residue, not author edits.
An index-only git read-tree HEAD attempt refused because index.lock exists;
it did not repair the index. Read-only Win32_Process inspection returned no
git.exe at observation time. No process was launched as a worker or terminated.

Do not stage, commit, clean, reset, checkout, or delete the apparent mass changes.
No lock or protected-root file was removed/edited. Metadata repair under the
protected root was not assumed authorized. Bootstrap WO/evidence writes are
the only intentional file changes. Existing AWC-orch1-dispatcher worktree at
the same base was observed; parent issue had no /4 claim at inspection time.
Do not adopt or modify that separate worktree without ownership reconciliation.

Source implementation, RED/GREEN, regression, encoding/secret checks,
freeze, commit, push and PR are NOT_RUN. The identity command was attempted:
python -B -m pytest -q -p no:cacheprovider tests/test_work_order_identity.py
returned exit 1, file or directory not found, and no tests ran (0.00s).
The incomplete checkout therefore cannot validate even the bootstrap identity.
No passing test counts or proven matrix rows.
No scope extension recorded. No delegated/model/provider execution performed.
Next safe action: reconcile the interrupted worktree initialization under an
explicitly permitted metadata-repair boundary, prove clean base/ownership,
complete startup reads, then claim source and start RED tests. Keep this
worktree and branch for recovery; no cleanup authority inferred.
