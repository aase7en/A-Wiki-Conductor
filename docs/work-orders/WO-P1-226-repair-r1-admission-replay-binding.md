# WO-P1-226 Repair R1 — admission replay binding

Status: READY_FOR_GLM_REPAIR / R3 / SOURCE NOT MERGEABLE UNTIL REREVIEW
Parent: WO-P1-226 / PR #314
Rejected exact candidate: `78ec598b9830d802f54eb47642130693a038a39c`
Integrator/reviewer: GPT-5.6 Sol
Preferred repair executor: ZCode GLM-5.3 MAX

## 1. Exact blocking finding

Independent exact-SHA R3 review reproduced a P1 replay identity defect against the canonical `SQLiteProviderConfigStore`.

Canonical provider admission authority is unique by `(provider_id, execution_id)`, but `acquire_admission()` additionally treats `batch_id` drift and configuration-generation drift as `RECOVERY_REQUIRED`.

At candidate `78ec598...`, WO226 replay uses `_find_held_admission_readonly()` to locate by provider/execution, then `_reconcile_cleanup()` releases using the stored row's own `batch_id`, and `_cleanup_only_handoff()` accepts that row without proving it matches the current `ReviewerExecutionPlan.batch_id` / expected generation.

Reproduction on exact candidate:

- pre-existing completed equivalent durable execution;
- exact active WorkerLease;
- canonical provider admission with correct provider/execution but `batch_id='WRONG-BATCH'`;
- call `execute_review_dispatch()` with the valid current plan.

Observed:

`outcome=REUSE_COMPLETED` and `handoff.admission_batch_id='WRONG-BATCH'`.

This bypasses canonical admission replay semantics and permits a usable handoff from the wrong durable admission identity.

## 2. Required repair

Reuse existing provider-store authority. Do not add schema/store/lock/journal.

Read-only replay/reconciliation MUST cross-bind the located admission to all available plan authority before release or handoff:

- `provider_id == plan.provider_id`;
- `execution_id == plan.dispatch_execution_id`;
- `batch_id == plan.batch_id`;
- persisted `configuration_generation` is present when an expected generation exists and equals that expected generation.

Mismatch or unknown required generation => typed `RECOVERY_REQUIRED`, no admission release, no lease release caused by this mismatched replay, no handoff, no new acquisition.

Preserve provider `NOT_ACTIVE -> exact RELEASED reread` semantics for the correct identity.

## 3. Mandatory REDs

At minimum add deterministic tests proving:

1. completed equivalent + exact active lease + wrong-batch admission -> `RECOVERY_REQUIRED`, zero model effect, no handoff, wrong admission remains unreleased by this path;
2. completed equivalent + exact active lease + wrong/unknown persisted generation when generation is required -> `RECOVERY_REQUIRED`, no handoff/release;
3. exact batch + exact generation replay still performs one canonical cleanup and yields the existing valid `REUSE_COMPLETED` handoff;
4. read-only replay performs zero new lease/admission acquisition rows.

Use real `SQLiteProviderConfigStore` / `SQLiteWorkerLeaseStore`, not only fake ports.

## 4. Preserve prior accepted obligations

Do not regress any previously closed WO226 obligations:

- recovery lookup is read-only, never acquire-as-proof;
- no fabricated cleanup handoff;
- timeout/live process retains lease/admission;
- default real runner-factory seam matches backend;
- stale C0 provider generation/endpoint fails closed;
- all-equivalent multiplicity checks every record;
- cleanup failures remain typed recovery;
- no semantic C1 `ACCEPTED/REJECTED` parsing.

No changes to global provider admission semantics, WorkerLease schema, GraphDispatch lifecycle, execution-store schema, scheduler, GoalCloseout, or WO223/C1.

## 5. Allowed source scope

Repair should normally touch only:

- `src/a_conductor/zero_relay_review_execution.py`;
- `tests/test_zero_relay_review_execution.py`.

Any additional source/test path requires explicit evidence and GPT scope adjudication before mutation.

## 6. Verification floor

Before freeze:

- new REDs green for the correct reason;
- full `tests/test_zero_relay_review_execution.py` green;
- directly related ZCode assembly/composition/runner regressions green;
- provider admission + WorkerLease + GraphDispatch/job/ParallelReady regressions green;
- compile/import, `git diff --check`, UTF-8/scope/secret-shape checks pass;
- exact changed paths remain within released repair scope.

Then freeze ONE new candidate SHA, push PR #314, update durable result/checkpoint, trigger exact-head hosted CI, and STOP for independent GPT exact-SHA rereview. Do not merge.

## 7. Integrator amendment — fold Astra AF1-AF4 into the same repair round

Independent Astra exact-SHA review of `78ec598b9830d802f54eb47642130693a038a39c` froze additional evidence at `5df9ebef48063fcae96fcb7fed0cc8d68b47fcfe`. Sol adopts AF1-AF4 into this repair. They are not a second WO or second source owner.

Required outcomes in addition to the admission batch/generation repair:

1. **AF1 / P1:** losing concurrent dispatch cannot clean resources that may belong to a live winner before a runtime record appears. Absence of record is not proof of crash/quiescence. Use existing durable job/ownership authority; if original scope cannot prove safe ownership, STOP `DESIGN_GAP`.
2. **AF2 / P2:** a retained timeout that later becomes a terminal non-success execution must release its exact admission/lease once, without handoff/relaunch. Live/UNKNOWN retains resources. Terminal-unusable cleanup is still bound to the plan's required provider configuration generation: wrong or unknown required generation is typed recovery and MUST NOT release either admission or lease. Add explicit terminal-FAILED REDs for wrong generation and unknown required generation; the exact-generation AF2 cleanup remains the positive control.
3. **AF3 / P1:** post-run candidate selection must apply full equivalent identity + reviewer-worker validation before cleanup/handoff, not cardinality/state alone.
4. **AF4 / P1:** trusted C0 provider endpoint/security/generation must also consume canonical provider-policy evaluation before acquisition/effect; policy denial fails closed. For direct review, the provider-authority triple is mandatory rather than optional: `provider_endpoint`, `provider_security`, and positive `expected_configuration_generation` must all be present and cross-bound before any lease/admission/model effect. All-None/missing authority is typed fail-closed; never upgrade it from ambient/current snapshot state. Add a non-vacuous all-None RED with zero resource rows/effects and preserve the production full-authority positive path.

Binding review artifacts are in `A:\GitHub\_worktrees\A-Wiki-Conductor-wo226-astra-final-review\docs\reviews\wo226-astra-final\`, including `test_adversarial.py` and `GLM-REPAIR.md`. Port meaningful REDs into `tests/test_zero_relay_review_execution.py`; do not depend on the review worktree at runtime.

The repair remains bounded to `src/a_conductor/zero_relay_review_execution.py` and `tests/test_zero_relay_review_execution.py` unless exact evidence requires explicit scope expansion. No schema, lifecycle, scheduler, provider-store, WorkerLease-store, dedup-store, or semantic C1 authority changes are released by this amendment.
