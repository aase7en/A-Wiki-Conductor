# WO-P1-549 — A-Faster executable auto-refill bridge

Status: ACTIVE / AUTHORING
Issue: #549
Risk: R3 — dispatch/control-plane enforcement
Topology: CONTROL_PLANE_ONLY
Authority repo: A-Wiki-Conductor
Base: c4d4cf4da830cb313a4569a386edcff0a77266c2
Branch: feat/wo-p1-549-a-faster-autorefill
Worktree: /Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo549-autorefill

## Goal
Close the accepted A-Faster POLICY_ONLY utilization gap without creating a scheduler or second authority. An active A-Faster/NightShift supervisor must be able to consume the existing deterministic utilization verdict and execute one bounded refill batch through existing scheduler-owned READY assignments, WorkerLease/provider/dedupe authority, PRE_DISPATCH guard, and ParallelReadyExecutor.

## Global invariants
- max 3 simultaneously active mutable lanes; max 1 independent review lane;
- Issue #537 may retain at most 2 borrowed waiting/parked mutable claims, never active writer slots;
- one mutable hotspot = one mutation owner;
- no manufactured work or blind redispatch;
- fresh CoinTH proxy quota + independent upstream readiness before every material GLM dispatch;
- SunDayRemoteMCP remains execution/capability substrate; no execution-repo mutation in this WO;
- model/device identity grants no task/claim/mutation/review/merge/completion authority.

## Frozen mutable scope
Lane A — core bridge:
- src/a_conductor/a_faster_auto_refill.py
- tests/test_a_faster_auto_refill.py

Lane B — Codex/A-Faster integration:
- .codex/hooks/a_sunday_lifecycle.py
- tests/test_codex_a_sunday_hooks.py
- .agents/skills/a-faster/SKILL.md

Integrator-only:
- docs/work-orders/WO-P1-549-a-faster-executable-auto-refill.md

Lane C is install/runtime verification only on clean supervisor worktrees and user Codex trust configuration; it owns no tracked repo mutation.

## Required executable behavior
1. Accept only an A_FASTER_ACTIVE utilization verdict produced by the existing classifier.
2. Require AUTO_REFILL_REQUIRED and positive FANOUT_TARGET; otherwise launch nothing.
3. Consume an existing scheduler-owned SchedulePlan and exact ParallelReadyTask mapping; never discover/create READY work.
4. Bound selected mutable work to the existing global budget and verdict fanout target; never count borrowed waiting claims as active compute.
5. Delegate the bounded batch only through the injected existing ParallelReadyExecutor path; all lease/provider/dedupe/PRE_DISPATCH truth remains owned by existing authorities.
6. Any malformed/drifted/missing inputs fail closed before execute().
7. Produce a bounded typed refill result/evidence projection only; no durable scheduler/task/claim/retry/review/merge/completion state.
8. Codex hook context must direct the supervisor to the executable bridge when A-Faster markers require refill; the hook itself must not launch or mint authority.

## Acceptance
RED first; focused/related GREEN; py_compile; JSON/hook smoke; diff --check; UTF-8; added-line secret scan; exact-SHA Windows and macOS smoke; independent R3 review; exact-head CI; Sol acceptance and post-main verification. Canonical dirty worktrees are never reset/cleaned/stashed.
