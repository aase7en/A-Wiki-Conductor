# WO-P1-576 — Codex Goal idle guard Phase A

Status: CLAIMED / GOVERNANCE BOOTSTRAP; source mutation blocked until post-bootstrap re-gate
Issue: #576
Claim: `WO-P1-576-GOAL-IDLE-GUARD-MAC-001`
Topology: `CONTROL_PLANE_ONLY`
Risk: `R3` — autonomous lifecycle / routing enforcement
Authority repo: `aase7en/A-Wiki-Conductor`
Execution repo: `aase7en/A-Wiki-Conductor`
Base SHA: `6c4bcdfebfde29990f92b7b76670830009ba6753`
Worktree: `/Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo576-goal-idle-guard`
Branch: `feat/wo-p1-576-codex-goal-idle-guard`

## Goal

Add the smallest deterministic, projection-only classifier that prevents repeated unchanged
Luna supervisor sweeps from being treated as useful continuation. Phase A produces decisions
only; it does not invoke Codex Goal APIs or own scheduling, claims, dispatch, retry, or completion.

Runtime defect boundary:
`HOOK TURN-END CONTROL != NATIVE GOAL AUTO-CONTINUATION CONTROL`.

The current operational mitigation remains authoritative:
`ACTIVE_WHILE_REAL_WORK_EXISTS -> PAUSED_WHEN_IDLE -> COMPLETE_ONLY_WHEN_PROJECT_COMPLETE`.

## Recovered facts at claim
- Parent Goal `01a0f2dd-eccd-7e61-ae55-8dbc37734662`: PAUSED, queue empty,
  tokensUsed 9,873,401, timeUsedSeconds 36,300.
- Watchdog Schedule: ACTIVE every 30 minutes on separate thread
  `01a0f451-6d13-7f70-a8c2-53b77c897a1e`.
- Sunday recovery at bootstrap: 217 terminal executions; zero
  `TERMINAL_UNHARVESTED/RUNNING/UNKNOWN/INTERRUPTED/PENDING_SCOPE`; lane list empty.
- `origin/main=6c4bcdfebfde29990f92b7b76670830009ba6753`.
- Canonical roots remain stale/dirty-protected and are not mutation surfaces.
- #575 owns the existing `sidecar_codex_bridge` successor surface and is parked behind #498.
- #549/#551 are waiting external; #537 claim is released.
- All three Phase-A paths and this branch/worktree were absent before bootstrap.

## Exact scope

Bootstrap-only scope before the first commit:
- NEW `docs/work-orders/WO-P1-576-codex-goal-idle-guard.md`.

After bootstrap commit and fresh mutation re-gate, planned source scope:
- NEW `src/a_conductor/codex_goal_idle_guard.py`.
- NEW `tests/test_codex_goal_idle_guard.py`.

Forbidden in Phase A:
- `src/a_conductor/sidecar_codex_bridge.py` and its tests;
- #498/#549/#551 owned paths;
- accepted #545 hook files;
- A-Faster/A-NightShift skill changes;
- raw Codex SQLite/session/lock mutation;
- Goal API pause/resume adapter implementation;
- any scheduler/task/claim/provider/retry/review/merge/completion authority.
## Required classifier contract

Inputs are already-verified bounded facts only: delegated execution classes, actionable queue
count, durable fingerprint/material-delta state, SAFE_READY candidate state, watchdog/Goal
identity relation, pending equivalent steer state, and task-bound GLM disposition state.

The projection must emit one typed action such as:
- `HARVEST_REQUIRED` when any terminal-unharvested execution exists;
- `CONFIG_TOPOLOGY_ERROR` when watchdog and Goal thread identities collide;
- `STALE_QUEUE_STEER` when an equivalent steer exceeds the accepted cadence bound;
- `RESUME_REQUIRED` only for a material delta or genuinely SAFE_READY candidate;
- `IDLE_PAUSE_REQUIRED` for unchanged, actionless idle truth;
- `REAL_GLM_DISPATCH_REQUIRED`, `BLOCKED:<reason>`, or
  `NOT_BENEFICIAL:<reason>` for an eligible task-bound route disposition.

No classifier result itself grants mutation or dispatch authority.

## RED matrix

1. all-idle census => `IDLE_PAUSE_REQUIRED`.
2. any terminal-unharvested => harvest-first; pause forbidden.
3. material delta / SAFE_READY => `RESUME_REQUIRED`.
4. eligible R2/R3 without durable disposition => GLM disposition required before more broad supervisor work.
5. unchanged fingerprint => no resume and no repeated Luna sweep.
6. equivalent pending steer => no duplicate; stale pending steer => `STALE_QUEUE_STEER`.
7. watchdog thread == Goal thread => `CONFIG_TOPOLOGY_ERROR`.
8. projection module has no I/O or authority side effects.
9. ambiguous/cached quota is never converted into GLM admission.
## Verification and acceptance

Implementation must be RED-first against the matrix above, then run:
- focused `tests/test_codex_goal_idle_guard.py`;
- directly related A-Faster/A-NightShift/CodexBridge tests selected from actual imports/contract use;
- `py_compile` for the new module;
- `git diff --check`, strict UTF-8, exact-scope and secret-shape checks.

Freeze one exact candidate SHA. R3 acceptance then requires independent exact-SHA review,
hosted CI, GPT integrator adjudication, expected-head merge, and post-main verification.

The runtime canary is a later acceptance step: supported Codex App Server Goal API only,
never raw SQLite/session/lock state. Phase A implementation itself remains pure.

## Routing

After the post-bootstrap gate, run exactly one task-bound A-Audit / GLM_OFFLOAD_ASSESSMENT.
Expected class if authority remains settled: `STRONG_IMPLEMENTATION`.
GLM-5.3 MAX is preferred bounded author for source/tests. Take one fresh CoinTH preflight
immediately before the useful real request. GLM may not merge or widen scope.

JEV is not required for this Phase-A implementation. Current executable JEV mode must be
recovered separately; no direct JEV call is authorized by this WO.

## Durable result / replay safety

Result/evidence belongs to this Issue/WO plus the Sunday durable execution identified at dispatch.
A terminal delegated run must be harvested and verified before repair/retry. RUNNING, UNKNOWN,
INTERRUPTED, AMBIGUOUS, or TERMINAL_UNHARVESTED never authorizes blind replay.

## Next safe action

Commit this docs-only bootstrap, re-pin exact worktree/HEAD/dirty state and collision/WIP truth,
then activate only the two new source/test paths if `SAFE_TO_MUTATE=YES`.
