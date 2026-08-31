# WO-P1-121 — Post-Merge Dispatch Evidence Binding Repair

Date: 2026-08-31
Owner: GPT-5.6 Sol integrator
Status: ACTIVE / RED_FIRST
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-dispatch-evidence-repair`
Branch: `fix/wo-p1-121-dispatch-evidence-binding`
Base: `887ef3c9c640a612dffc1a3baeab42b70f6aa12f`
Priority: P1 trust-boundary repair before unattended provider execution

## Trigger

Ultra independent review of merged WO-P1-117 head `6f19c924...` returned `CHANGES_REQUIRED` after deterministic fault injection. The reviewed dispatch/store files are byte-identical on current main, so the findings remain applicable after PR #161.

Confirmed findings:
- F1 P1 — unsupported normal runner returns can fall through to `RUN_COMPLETED` and release provider admission;
- F2 P1 — accepted typed evidence is not bound to the dispatched job/project/work-order/worker;
- F3 P1/P2 — `EXISTING` / `BLOCKED` / `OFFERED` can carry contradictory nested execution evidence while still releasing capacity.

Classification: `REUSE + EXTEND` the existing WO117 consumer-side typed policy. No new scheduler, store, lifecycle, retry, capacity, or provider authority.
## Mutable scope

- `src/a_conductor/parallel_ready_execution.py`
- `tests/test_parallel_ready_execution.py`
- this work order
- `DEFECT_LESSONS.md` only after the repair is accepted locally

Forbidden: provider configuration/store/runtime files owned by WO118A; worker lease/candidate/elastic files owned by WO120; scheduler/graph/job lifecycle redesign; live provider/credential/worker/tunnel mutation.

## Acceptance

1. With a held provider admission, any non-`GraphDispatchResult` normal return is recovery-required, never completion, and never releases provider capacity. Without a provider admission, the original injected generic-runner stage-completion contract remains valid.
2. Positive/terminal typed evidence must match the current dispatch job ID, project ID, work-order ref and max-attempt policy; worker-bound states must match the acquired lease worker.
3. `EXECUTED` requires VERIFYING + matching successful `JobExecutionOutcome` and exact task/lease identity.
4. `EXISTING` may release only for canonical state/evidence combinations; non-executing actions require `execution is None`.
5. `BLOCKED` requires BLOCKED + no nested execution; `OFFERED` requires CLAIMED + exact lease worker + no nested execution.
6. Contradictory/foreign/malformed evidence retains provider admission and yields stable typed recovery.
7. A valid successful sibling remains independently successful when another lane is malformed.
8. Existing WO117 SQLite TTL/exact-release behavior remains unchanged.
9. Focused + impact-expanded regression, compileall, diff/scope/secret/UTF-8 gates pass before commit/PR.

## Evidence source

Ultra result: `A:\GitHub\A-Wiki-Conductor-provider-dispatch-safety\runs\wo117-independent-review-001\result.md`. It reviewed exact `6f19c924...`, reproduced seven unsafe admission releases while the actual job remained EXECUTING, and explicitly recommended a bounded post-merge repair rather than lifecycle redesign.

## Implementation checkpoint — 2026-08-31

RED on exact main `887ef3c9...`: WO121 focused matrix = `10 failed / 1 passed`. Unsupported `None`/`dict`, five task-identity drifts, and contradictory nested execution all reproduced unsafe release/completion behavior.

GREEN repair is consumer-side only:
- with a held provider admission, unsupported normal returns -> `DISPATCH_RESULT_UNSUPPORTED`, recovery, admission retained; generic no-admission returns are handled by the later compatibility checkpoint;
- typed result job identity binds exact job/project/work-order/max-attempts and canonical worker ownership to task + acquired lease;
- `EXECUTED` additionally requires a real attempt (`attempt_count >= 1`) plus matching successful execution evidence;
- `EXISTING`/`BLOCKED`/`OFFERED` require `execution is None`; contradictory nested execution remains capacity-consuming recovery;
- legacy success test doubles now return canonical typed execution evidence rather than relying on dictionary fallthrough.

Verification: WO121 focused `13 passed`; full parallel file `56 passed`; impact-expanded provider/graph/lease/elastic/harness/supervisor/native suite `366 passed`; compileall, `git diff --check`, UTF-8 gate PASS. No provider-store, worker-capacity, scheduler, lifecycle, live credential, worker or tunnel mutation.
## Generic-runner compatibility repair — 2026-08-31

Post-implementation GPT audit re-read WO-P1-113 and found the first WO121 repair over-tightened the injected `ParallelReadyRunner -> object` seam: unknown normal returns became recovery even when no provider admission store existed. That was a compatibility regression, not needed to close Ultra F1.

RED: provider-backed unknown-return safety controls remained green, while a generic no-admission runner returning a dictionary incorrectly produced `RUNNER_RECOVERY_REQUIRED`.

Repair: only no-admission + non-`GraphDispatchResult` returns retain the original stage-level `RUN_COMPLETED` behavior. Once provider capacity is admitted, unknown normal returns still require recovery and retain capacity. Typed `GraphDispatchResult` evidence remains subject to exact identity/action/state policy in both modes.

Verification: targeted safety/compatibility `3 passed`; full parallel `57 passed`; final broader provider/store/runtime/graph/lease/candidate/elastic/Claude supervised suite `284 passed`. The earlier Ultra rereview packets are superseded by the next exact-head packet.
