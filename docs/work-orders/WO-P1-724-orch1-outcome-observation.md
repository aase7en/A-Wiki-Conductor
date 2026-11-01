# WO-P1-724 ORCH-1/6 Outcome And Lifecycle Observation

Identity schema: GITHUB_ISSUE_V1
Issue: #724
Parent: #709.
Status: AUTHOR_VERIFIED / FREEZE_FOR_INDEPENDENT_REVIEW / R3 / CONTROL_PLANE_ONLY.
Owner: ses_e6788660fffen6RmTb5pESt1Ua (AUTHOR; not acceptance authority).
Claim: ORCH-1-6-OUTCOME-001.
Base: 93908aff8e9a0e3c2e2807c27fde0288993577bd (remote main verified).
Worktree: `A:\GitHub\_worktrees\AWC-orch1-outcome`.
Branch: `feat/orch1-outcome-observation`.

## Scope And Authority

Explicit assignment authorizes implementation, verification, commits, push and PR,
NO merge, runtime activation or live provider/worker operation. Sole mutable scope:
NEW `src/a_conductor/orchestration_outcome.py`,
NEW `tests/test_orchestration_outcome.py`, this WO,
additive `src/a_conductor/runtime_activation.py`, and only a thin default-None
outcome-port change in `src/a_conductor/orchestration_dispatcher.py` if required.
The dispatcher already has a default-None callable publisher; reuse it. Any thin
change must preserve existing results except typed observability degradation.
Shared CURRENT-WORK.md, handoff.md and COLLAB.md remain integrator-owned; this WO
and Issue #724 checkpoints carry their fold-back. Protected root and other lanes
are read-only. No new receipt/schema/store/scheduler/claim/dispatch authority.

## Frozen Contract And Failure Model

Authority: foundation design section 3 OutcomePublisher, section 6 Lifecycle And
STM, section 7 row /6. REUSE accepted outcome codec, owning durable job checkpoint
and execution refs, normalize_control_event, HookBus and HookStm. No new control
event mapping: only actual supported owning ControlEvents may be projected; absent
or unsupported events publish nothing with typed unavailable guidance. Do not
manufacture worker lifecycle events for task decisions. Observer outputs never
enter the effect path. Inject authority readers; no I/O at import/construction.

One bounded immutable outcome; dispatch result IDs/reasons preserved. Required
audit failure BEFORE effect blocks effect; AFTER possible effect reconciles with
retained IDs, no relaunch. Publisher failure only degrades observability. Reentrant
publication is typed refused. Missing/stale/overflow STM rebuilds only from fresh
authority through existing normalize/HookBus accept/HookStm derivation; unavailable
bus/TTL/authority means typed unavailable, never execution permission. Stop #531
receipt schema and existing context caps remain unchanged. Compact caller guidance
contains codes only, no raw exceptions/prompts/provider text.

## Acceptance And Verification

RED-first new suite covers before/after audit, publisher loss, reentrancy, supported
and unsupported mapping/closed keys, stale/missing/overflow STM rebuild and TTL,
no recursive dispatch, unchanged Stop/context limits. Then orchestration suites,
HookBus/HookStm/control adapter suites, identity (33), compileall with bytecode
cleanup, strict UTF-8, diff-check and secret/scope checks. Freeze exact SHA, push,
open PR and post evidence to #724; independent R3 review/hosted CI/acceptance stay
integrator-owned. No merge or live-runtime certificate.

## Recovery Checkpoint

2026-11-01: remote main verified exact base; no prior /6 issue/branch/worktree found.
Created Issue #724 and isolated worktree before source mutation. Root remains
stale main with pre-existing untracked .kilo/; untouched. Prior /4 publisher seam
exists. Normalizer supports only START/STOP/RESTART/RELEASE; no invented outcome
event. Native Goal unavailable in delegated sessions, so execute bounded turn and
checkpoint here/on issue. Already-delegated author lane: GLM_OFFLOAD=NOT_BENEFICIAL;
no further provider dispatch. Next: finish source/readiness inspection, RED tests.

## Implementation Checkpoint

2026-11-01: claim posted on #724 comment 6562424838; parent cross-ref
6562424912. Startup source/authority inspection and DEFECT_LESSONS #46-#59 read.
Remote main remains the requested base. Windows RDC is offline (device
ff685af5-9031-4b3b-84ff-61dc8f1a840c); native local tools verified worktree and
executed tests. SunDay execution tools/resources not exposed; no delegated
execution or live provider/worker effect. Only fixture-owned SQLite jobs/events.

RED first: missing orchestration_outcome module (1 collection error). Initial
implementation: 33 passed. Adversarial RED: 5 failed / 31 passed exposed fallback
refresh of rejected snapshots/pointers. Fixed by allowing authority-pointer-only
rebuild solely after existing HookBus schema/security admission or its typed
backpressure, never arbitrary reader/normalizer rejection. No copied validator.
Outcome + codec/receiver/guards/dispatcher: 323 passed in 10.27s (36 new cases).

Concrete seams: OutcomePublisher callable returns accepted OrchestrationOutcome;
publish returns immutable PublicationResult with fixed compact guidance. Runtime
adds optional outcome_publisher mutually exclusive with legacy publisher (no
automatic registration/startup). Dispatcher only propagates the typed outcome's
observability_degraded flag; legacy callbacks returning None remain unchanged.
Guard composition retains code but no metadata/IDs; admitted guard is NO_ACTION,
not a dispatch capability. Multiple effect IDs fail typed rather than truncate.
ObservationSnapshot is a trusted application read port, not serialized evidence:
exact partition/task/job IDs, <=16 existing events, <=30s read age at completion.
Every invocation rereads authority, regardless of STM freshness. Actual supported
ControlEvents only, minimal existing context keys, no task-event impersonation.
HookBus admission precedes STM rebuild; overflow can rebuild only the validated
authority pointer with unavailable guidance. Bus drain stays application-owned;
publisher does not drain unrelated events or register dispatch subscribers.

The next-action text above is superseded by the continuation freeze below.

## Continuation Freeze

2026-11-02 Windows continuation, explicitly authorized by the user, retained the
same claim, worktree, branch and five-file allowlist. Disk HEAD was still the exact
base above; no existing PR was found. Preserved all predecessor edits and verified
the completed adversarial repairs rather than repeating implementation. Shared
CURRENT-WORK/handoff remain stale integrator-owned snapshots and were not edited.
No new executor/provider was dispatched; no independent review is claimed.

Fresh native verification (`python -B -m pytest -q -p no:cacheprovider`):

| Battery | Exact files | Result |
|---|---|---|
| Focused outcome/adversarial | test_orchestration_outcome.py | 37 passed |
| Existing orchestration | test_orchestration.py, test_orchestration_receiver.py, test_orchestration_guards.py, test_orchestration_dispatcher.py | 287 passed |
| Hook/lifecycle regression | test_hook_bus.py, test_hook_stm.py, test_control_hook_adapter.py, test_hook_contract_schema.py, test_hook_producer_wiring.py, test_codex_a_sunday_hooks.py | 564 passed |
| Runtime/execution/identity | test_runtime_activation.py, test_parallel_ready_execution.py, test_job_control.py, test_job_execution.py, test_work_order_identity.py | 148 passed |
| Identity confirmation (overlaps prior row) | test_work_order_identity.py | 33 passed |

Total unique battery: 1,036 passed, zero failed/skipped. The historical 36-new /
323-total orchestration count is not the current disk count: this continuation
observed 37 focused / 324 combined, without changing source or tests. Historical
RED evidence remains predecessor checkpoint evidence, not a new RED run.

Per design section 7 row /6 acceptance:

| Requirement | Deterministic evidence in test_orchestration_outcome.py |
|---|---|
| Required audit BEFORE effect | test_registered_root_audit_failure_before_after_effect_retains_ids[before]: reconciliation, retained canonical job ID, zero runner calls |
| Required audit AFTER possible effect | Same test [after]: one runner call; second invocation never relaunches |
| Publisher failure degrades observation only | test_registered_publisher_failure_degrades_only_never_relaunches: decision/reason preserved, degraded=True, one total launch |
| Reentrancy / no recursive dispatch | test_raw_error_not_exposed_and_reentrancy_is_typed; test_observation_callback_cannot_recursively_dispatch: typed refusal / ORCH_REENTRANT_DENIED, one total launch |
| Fresh-authority STM rebuild | test_missing_stale_overflow_stm_rebuilds_only_from_fresh_authority[missing/stale/overflow]; reader invoked again even with fresh cache |
| Observer overflow / TTL / binding failure | test_overflow_is_typed_unavailable_with_authority_reference_rebuild[bus/stm], latched degradation, TTL/future/slow-reader and six binding-bound cases: unavailable, no execution repair |
| Real existing events -> sanitized OBSERVE | test_registered_root_reads_canonical_checkpoint_and_existing_control_event; supported START/STOP/RESTART/RELEASE mapping cases; missing/unsupported events publish nothing |
| Stop schema / compact context unchanged | test_stop_receipt_schema_and_context_budgets_unchanged plus 564 hook/lifecycle regressions: exact existing receipt keys; 262144-byte stdin, 65536-byte receipt, each context <=4096 bytes |

Hygiene: compileall passed for the three changed production modules plus the new
test; generated bytecode removed. Strict UTF-8, scoped secret scan (only the
intentional ghp_FAKE negative fixture), staged diff-check and five-file scope
checks passed. Exact frozen commit/PR and changed-line counts are published on
Issue #724 after commit/push, avoiding a self-referential commit SHA in this file.

Next safe action: independent R3 review and hosted CI on that exact frozen SHA;
integrator adjudicates findings and acceptance. NO merge, runtime activation,
Parent queue admission, mutable refill acceptance or live-runtime certificate.
