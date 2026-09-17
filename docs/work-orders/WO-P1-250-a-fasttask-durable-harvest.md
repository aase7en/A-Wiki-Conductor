# WO-P1-250 — A-FastTask durable delegated-run recovery

Status: IN_PROGRESS (phase 2 candidate authored after WO247 release)
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
WO247 / PR #332 was accepted and merged as `b42d5b433ea67a7986af1132af56a584f5109a8f`; its six-path claim was released in Issue #331. This branch re-pinned `origin/main` and integrated that accepted A-FastTask base before Phase 2 mutation.

The Phase 2 router/binder delta makes a session instruction equivalent to “use A-FastTask and continue” automatically perform `RECOVER -> RECONCILE OUTSTANDING EXECUTIONS -> HARVEST TERMINAL RESULTS -> CONTINUE NEXT READY` without asking the user to reconstruct old chat history. The skill now requires outstanding delegated-run reconciliation before new READY work and records the reconciliation/harvest disposition in its routing output; `material-boundary.md` defines fresh-session state handling and rollover checkpoint fields.

A-FastTask remains router-only. It selects/invokes existing liveness, execution, checkpoint, takeover, and harvest authorities; it does not own execution lifecycle state itself.

## Verification
R2 gates: exact scope, diff/UTF-8/link/secret checks, frozen SHA, independent read-only review, exact-head CI, merge, post-main verification. After acceptance, recover and resume the existing SunDayRemoteMCP lanes from actual runtime/Git evidence rather than chat memory.
## 2026-09-17 phase-1 recovery checkpoint

Fresh-session reconciliation found the prior WO247 review and WO250 GLM author attempts had exited. WO250 had produced no tracked policy edits and no declared result artifact; Git showed only this work order untracked. That prior author attempt is therefore treated as interrupted/no-source-effect evidence, not DONE, and no blind replay was performed.

Phase 1 is now authored in the isolated WO250 worktree under the four allowed tracked paths only. Required next gate: deterministic diff/scope/UTF-8/reference/secret checks, then freeze. Phase 2 stays blocked until WO247 / PR #332 is accepted, merged, and its six-path claim is released.


## 2026-09-18 Phase-2 candidate checkpoint

Recovered three terminal GLM lanes before new work: the WO247 exact-SHA review/rereview, the SunDayRemoteMCP cancel/shim P2 repair candidate, and the Issue #341 semantic spike. WO247 was accepted/merged/released; semantic-spike output was folded into Issue #341; the SunDayRemoteMCP P2 candidate is under separate Issue #344 independent review and does not overlap this A-Wiki docs hotspot.

Phase 2 mutates only `.agents/skills/a-fasttask/SKILL.md`, `.agents/skills/a-fasttask/references/material-boundary.md`, and this WO on top of the already-committed Phase-1 files. Required next gate: deterministic scope/diff/UTF-8/reference/secret checks, freeze exact SHA, then independent read-only exact-SHA review and exact-head CI.

## 2026-09-18 06:33 +07:00 — session rollover checkpoint

The current ChatGPT session is intentionally rolling over because context is large. Detailed durable local handoff is at `runs/WO-P1-250/session-rollover-20260918-0633.md`. A fresh session must use A-FastTask and recover actual Git/GitHub/runtime state before trusting this summary.

Current exact state:
- WO247 / PR #332 accepted and merged at `b42d5b433ea67a7986af1132af56a584f5109a8f`.
- WO250 PR #345 remains OPEN/DRAFT. Semantic candidate `258890e21059db2d064d2e76ba352f7e35274d73` had CI run `35276849639` `success`; docs-only rollover checkpoint commits were appended after that SHA, so a fresh session MUST re-pin the current PR head from GitHub and require exact-head CI + independent exact-SHA review for that current head before acceptance/merge. CI run `35287744156` was started for an intermediate rollover head and is historical unless it matches the re-pinned head.
- SunDayRemoteMCP canonical `main` remains clean at accepted local-MVP SHA `5a9fde46ffaa5230b8814a4a30b510d7aac37d3d`.
- WO-SRM-003 / Issue #344 candidate `0c185a7c6fac709a447b3d65b48f0ef1375fa43e` passed Sol/native build, focused P2-R regressions, supervisor suite and diff-check. Kilo review attempts ended without a declared result because of tool-permission/transport/invocation failures; `runs/WO-SRM-003/rereview-result.md` is absent. Classify as `INTERRUPTED/NO_RESULT` unless fresh runtime reconciliation proves otherwise; never count it as PASS or blindly redispatch.
- WO-SRM-004 / Issue #346 SEM-0 completed cleanly at `eb893560f3ed14e218e80ee521cbc96289c72d49`; build/focused/scope/diff checks are green and candidate is frozen awaiting independent review.
- Issue #341 holds the provider-neutral semantic/LSP roadmap; independent implementation only, no current Serena GPL code copy and no SolidLSP reuse without separate provenance review.
- Issue #342 tracks Kilo credential/status/share-URL redaction; Issue #343 tracks stale Kilo MCP registry/backend lifecycle.

Fresh-session priority under default one-read-only-review WIP:
`RECOVER WO-SRM-003 review -> exact-SHA review 0c185a7 -> re-pin PR #345 current head and review that exact SHA -> SEM-0 review eb89356 -> accepted fan-in -> continue Issue #341 SEM-1a`.

Before each new material GLM dispatch, refresh CoinTH quota/readiness via the approved secret-safe resolver. Re-probe RDC because it has continued working despite a zero-remaining usage indicator. Preserve the dirty A-Wiki root and all foreign worktrees; no reset/clean/stash/force/broad-kill.
