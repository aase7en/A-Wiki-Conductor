# WO-P1-404 — A-Faster self-directing multi-session multilane profile

Status: ACTIVE / READY_FOR_REVIEW
Issue: #404
Risk: R3 — routing/provider/recovery policy
Topology: CONTROL_PLANE_ONLY

## Binding
- Authority repo: `A:\GitHub\A-Wiki-Conductor`
- Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo404-a-faster-self-directing`
- Branch: `feat/wo-p1-404-a-faster-self-directing`
- Base / dispatch head: `c85484c23f6de86cf69edf1df6ab8b6e003cefd9`
- Claim: `WO-P1-404-A-FASTER-SELF-DIRECTING-001`
- Owner/integrator: GPT-5.6 Sol
- Preferred author: GLM-5.3 MAX via an admitted Kilo/Claude harness
- Evidence: `runs/WO-P1-404/`

## Goal

Make the phrase “use A-Faster” / “ใช้ A-Faster” sufficient for a substantial A-Sunday engineering session to recover project-wide delegated work, reconstruct the global WIP budget occupancy projection, fill safe non-overlapping free lanes automatically, route bounded work to the right GLM class/harness, and continue through harvest/fan-in without requiring the user to repeat multiagent/multilane instructions.

This EXTENDS the accepted A-Faster/A-FastTask contracts. It creates no scheduler, lane registry, task store, claim/lease store, review/completion authority, provider authority or memory SSoT.

## Exact mutable scope
- `.agents/skills/a-faster/SKILL.md`
- `.agents/skills/a-faster/references/multidevice.md`
- `docs/work-orders/WO-P1-404-a-faster-self-directing-multilane.md`

Everything else is read-only.

## Required behavior

1. Every A-Faster invocation starts with project/task delegated-run census + Git/runtime reconciliation before new dispatch.
2. Different ChatGPT sessions share one global 3 mutable + 1 independent-review budget. A new session never implies empty WIP.
3. `RUNNING` is never redispatched. `TERMINAL_UNHARVESTED` is harvested before conflicting work. Unknown/transport-loss state is reconciled before replay.
4. Once occupancy is known, A-Faster automatically fills available WIP from independent READY nodes; it does not wait for the human to restate “multiagent/multilane/multitasking”.
5. GLM-5.3 MAX is preferred for bounded R2/R3 implementation/repair and required qualified independent R3 review when admitted.
6. GLM-5.3-Flash is preferred for bounded read-only reconnaissance, census help, dependency/scope analysis, packet shaping and diagnosis; Flash never substitutes for a required MAX review.
7. Kilo Code CLI / Claude Code CLI are harnesses only. Every material dispatch refreshes CoinTH quota, proves exact harness/model/effort route and writes a durable run pointer before/at launch. No silent fallback.
8. Ponytail is automatically considered on Claude lanes for simplification/pre-implementation/review when verified available; it remains advisory.
9. Caveman is automatically considered only for transient worker-to-worker/token compression where exact semantics remain unambiguous. Never compress persisted WOs, issues, PRs, commits, evidence, security warnings, commands, identifiers, units or contract language.
10. Replace wording that could imply a global mutable WIP “ledger” with “global WIP budget / reconstructed occupancy projection”.
11. A-Faster continues safe next steps automatically after routing; it stops only on a real gate/blocker/terminal completion.
12. No model/skill/plugin gains mutation/claim/review/acceptance authority from this profile.

## Verification
- `git diff --check`
- exact three-path scope
- strict UTF-8 / no U+FFFD
- skill frontmatter + reference existence
- `tests/test_work_order_identity.py`
- added-line secret-shaped scan
- independent exact-SHA R3 review
- exact-head hosted CI
- expected-head merge and post-main proof

## Replay safety

Before any retry or fresh-session continuation, recover `runs/WO-P1-404/`, actual process identity, Git state and GitHub Issue/PR state. Never infer failure from chat/tool timeout alone.

## Author evidence

- Attempt: 0001 — GLM-5.3 MAX (effort max) via Kilo Code CLI harness, lane M1, this worktree.
- Evidence directory: `runs/WO-P1-404/author/attempt-0001/` (gitignored).
- Changes: one-clause invocation contract; explicit AUTO-FILL after recovery/census/harvest + collision gate up to the global `3 mutable + 1 review` budget; explicit multi-session shared-budget/timeout semantics; explicit autonomous continuation; Ponytail/Caveman automatic-consideration scoping; “single global WIP ledger” wording replaced with global WIP budget / reconstructed occupancy projection semantics. No cleanup-implementation, installer, or version-pinning widening.
- Verification: `git diff --check` clean; exact three-path scope; strict UTF-8 / no U+FFFD; frontmatter + referenced files valid; `tests/test_work_order_identity.py` green; added-line secret-shaped scan clean; duplication/contradiction diff review done.
- Status: READY_FOR_REVIEW — awaiting independent exact-SHA R3 review and exact-head hosted CI on the pushed branch head. Integrator (GPT-5.6 Sol) merges; no self-accept/merge by the author lane.
