# WO-P1-117 — Provider Dispatch Outcome + Admission Lifetime Safety

Date: 2026-08-31
Owner: GPT-5.6 Sol integrator
Status: IMPLEMENTED / REVIEW_PENDING
Repository: `aase7en/A-Wiki-Conductor`
Base: `origin/main@22b2d1ab8e430ef651675231696b1171a0a26d94`
Priority: P1 trust-boundary repair before unattended provider execution

## Goal

Make provider capacity ownership follow durable execution certainty. A normal Python return must not be treated as completed when durable dispatch says `RECONCILE`, and elapsed TTL must not silently free provider capacity while execution outcome is unknown.

## Evidence / defect boundary

Independent Ultra shaping identified R1/R2; GPT integrator re-read the source and confirmed both against merged main-equivalent code:
- `GraphDispatchCoordinator.dispatch()` can return `GraphDispatchAction.RECONCILE` without raising.
- `ParallelReadyExecutor` currently releases provider admission and records `RUN_COMPLETED` for every normal runner return.
- `SQLiteProviderConfigStore.acquire_admission()` converts every expired ACTIVE row to `EXPIRED` using time alone, then stops counting it toward concurrency.

Classification: `REUSE + EXTEND` existing graph-dispatch and provider-admission authorities. No second scheduler, execution store, capacity ledger, heartbeat service or retry engine.
## Allowed scope

- `src/a_conductor/parallel_ready_execution.py`
- `src/a_conductor/provider_config_store.py`
- focused tests for the above seams
- bounded SSoT for this WO

## Forbidden scope

- provider endpoint/profile generation or trust/egress policy semantics (WO-P1-118)
- provider output capture/redaction (WO-P1-119)
- worker/elastic reservation semantics (WO-P1-120)
- scheduler semantics, job-state transition tables, UI, connectors/tunnels, secrets, A-Wiki mutation
- automatic expiry-based replay or a second provider-capacity authority

## RED-first acceptance

1. A runner returning typed durable `RECONCILE` never becomes `RUN_COMPLETED` and never releases the admission as if provider work were terminal.
2. Unsupported/malformed runner outcomes fail closed with sibling batch evidence preserved.
3. A provider call proven to have reached its declared post-execution durable state may release admission exactly once; duplicate/replayed dispatch remains idempotent.
4. TTL expiry alone does not grant new provider capacity while the old execution is unknown; uncertainty remains capacity-consuming/recovery-required.
5. Explicit release requires exact provider/execution/batch identity and remains atomic across processes.
6. Existing capacity/concurrency tests remain green after the conservative lifetime rule.
7. Expired/unknown admissions expose typed reconciliation evidence; malformed timestamps fail typed before comparison.
8. No background sweeper/thread is introduced; callers provide clock/evidence and durable authority remains SQLite provider state.
9. Focused + related regressions, concurrency tests, compileall, diff/scope/secret audit pass.
10. Independent exact-SHA review and 3-OS CI are required before merge.

## Verification targets

At minimum extend:
- `tests/test_parallel_ready_execution.py` with a normal-return `GraphDispatchAction.RECONCILE` case that keeps admission ACTIVE and returns typed recovery;
- `tests/test_provider_config_store.py` replacing the unsafe “expired grants new capacity” expectation with fail-closed unknown-execution semantics plus explicit release/reconcile coverage;
- cross-process/concurrent admission regression at `max_concurrency=1`.

## Dependency / concurrency

May run concurrently with WO-P1-119 and WO-P1-120 because mutable source scopes are disjoint. WO-P1-118 is queued behind this WO because both require `provider_config_store.py`.

## Implementation checkpoint — 2026-08-31

- Worktree: `A:\GitHub\A-Wiki-Conductor-provider-dispatch-safety`
- Branch: `fix/wo-p1-117-provider-dispatch-admission-safety`
- Source/test commits: `7a575d162b47cd63ceddfe3943108cd8f3a4f38e` + `afeaf6d520039fe8dca6ba6cacaf2f1adcddd822` + `76b45b0099d3cd623a9e1af5ee8623378712b7af`
- RED proved durable `RECONCILE` false-success, TTL-only over-admission, malformed `EXECUTED` evidence acceptance, and `EXISTING + FAILED` false-success.
- Spawned-process stale-admission test proves expired-but-unknown work still fences `max_concurrency=1` across processes.
- Positive control proves valid typed `EXECUTED` with matching successful `JobExecutionOutcome` releases capacity and remains `RUN_COMPLETED`.
- Impact-expanded regression: `210 passed`; compileall and `git diff --check` PASS.
- Draft PR: `#160`; final exact-head CI must rerun after `76b45b0` and this checkpoint commit.
- Next gate: commit this bounded defect/WO checkpoint, push final head, rerun exact-head CI, generate independent exact-SHA review packet, and merge only after review + CI pass.
