# WO-P1-250 — A-FastTask durable delegated-run recovery

Status: IN_PROGRESS (phase 1 candidate complete; phase 2 blocked on WO247 release)
Issue: #339
Risk: R2 NORMAL — binding continuity/routing policy
Owner/integrator: GPT-5.6 Sol
Base: `018779d0d2f5a7a7a21adb277e23a617692c36fd`

## Problem
A normal ChatGPT turn can time out or roll context while a dispatched Kilo/GLM process continues. A fresh chat does not inherently remember that execution. Chat/session lifetime is therefore not execution lifetime.

Failure modes: forgotten harvest, duplicate redispatch, conflicting mutation, or forcing the user to reconstruct prior work. A live PID/heartbeat is not proof of progress; the 2026-09-17 SunDayRemoteMCP reproduction had live GLM processes with no tracked source effect and only planning artifacts.

## Required invariant
`CHAT/TURN LOSS != EXECUTION FAILURE` and `NEW SESSION != NEW TASK`.
Recovery must come from existing durable task/execution evidence plus actual runtime/Git state, never chat memory alone.

## Phase 1 — allowed now
Mutate only:
- `docs/agent-collab/EXECUTION_LIVENESS_PROTOCOL.md`
- `DEFECT_LESSONS.md`
- `PROJECT-PLAN.md`
- this work order

`.agents/skills/a-fasttask/**` remains READ_ONLY until WO-P1-247 / PR #332 is accepted, merged, and its six-path claim released. No source/runtime/provider/DB changes.

Required policy: every material delegated dispatch must leave a recoverable pointer using existing authorities: work order/task, lane, executor/provider/model, repo/worktree/branch/base/current SHA, scope/claim, process/session identity if known, start time, log/result/evidence destinations, retry safety, and expected completion evidence. Never persist secrets.

Fresh-session recovery must reconcile process/session + logs/result + Git/worktree + existing durable job state and derive at least `RUNNING`, `TERMINAL_UNHARVESTED`, `STALLED`, `INTERRUPTED`, or `UNKNOWN`. Harvest terminal-unharvested work before blind redispatch or conflicting mutation. `STALLED`, timeout, or transport loss never grants replay authority.

Before context/session rollover, checkpoint all outstanding delegated execution identities, evidence destinations, and the exact next harvest/reconcile action.

## Master-roadmap milestone — DEX
Reuse the existing resilient execution supervisor; do not create a shadow scheduler/task/claim/review/completion authority.
- DEX-0: durable dispatch pointer bound to existing execution/job authority.
- DEX-1: A-FastTask entry recovery + terminal-result harvest.
- DEX-2: supervisor/reconciler independent of ChatGPT turn lifetime.
- DEX-3: completion event/notification via supported operator surfaces; never claim plain chat self-wakes.
- DEX-4: SunDay Runtime/SunDayRemoteMCP batch `dispatch/status/harvest/recover` adapter as execution substrate only.
- DEX-5: reboot/process-loss recovery with explicit ambiguous states and no blind replay.
- DEX-6: deterministic E2E faults for chat timeout, context rollover, transport loss, worker exit, machine restart, and terminal result awaiting harvest.

## Phase 2 — after WO247 release
Re-pin new `main`, integrate the accepted WO247 A-FastTask base, then make the smallest router/binder delta so a session instruction equivalent to “use A-FastTask and continue” automatically performs `RECOVER -> RECONCILE OUTSTANDING EXECUTIONS -> HARVEST TERMINAL RESULTS -> CONTINUE NEXT READY` without asking the user to reconstruct old chat history.

A-FastTask remains router-only. It may select/invoke existing liveness, execution, checkpoint, takeover, and harvest authorities; it must not own execution lifecycle state itself.

## Verification
R2 gates: exact scope, diff/UTF-8/link/secret checks, frozen SHA, independent read-only review, exact-head CI, merge, post-main verification. After acceptance, recover and resume the existing SunDayRemoteMCP lanes from actual runtime/Git evidence rather than chat memory.
## 2026-09-17 phase-1 recovery checkpoint

Fresh-session reconciliation found the prior WO247 review and WO250 GLM author attempts had exited. WO250 had produced no tracked policy edits and no declared result artifact; Git showed only this work order untracked. That prior author attempt is therefore treated as interrupted/no-source-effect evidence, not DONE, and no blind replay was performed.

Phase 1 is now authored in the isolated WO250 worktree under the four allowed tracked paths only. Required next gate: deterministic diff/scope/UTF-8/reference/secret checks, then freeze. Phase 2 stays blocked until WO247 / PR #332 is accepted, merged, and its six-path claim is released.

