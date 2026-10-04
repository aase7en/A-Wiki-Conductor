# WO-P1-576 — Codex Goal idle guard Phase A

Status: Phase A accepted post-main; Phase B docs-only bootstrap identity repair in PR #584. Phase-B source mutation remains NOT YET MUTABLE pending bootstrap acceptance and a fresh full gate.
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

## Phase B — Codex Goal API adapter (child claim `WO-P1-576B-GOAL-API-ADAPTER-MAC-001`)

Phase B is a child of this existing canonical Issue #576 work order. Its first PR attempt used a new nonnumeric `WO-P1-576B-...` filename, which the frozen work-order identity test correctly rejects. Keep the identity corpus frozen and maintain one canonical numeric WO; this section carries the child packet without introducing another work-order identity.

### Phase-B objective and authority boundary

Add a pure, caller-injected adapter for the supported Codex App Server Goal/queue operations that Phase A deliberately does not execute. It translates explicit typed intents and bounded transport results; it owns no scheduling, claims, retry, dispatch, review, merge, or completion authority. Phase-A `codex_goal_idle_guard.py` remains the decision projection and read-only input.

This child exists only for the observed App Server 0.159.0 recovery arc. The runtime canary and successor migration are recorded in Issue #576 comments `5981598729` and `5981760977`. Implementation may use only those directly proven facts; it must not infer unobserved protocol, authorization, or lifecycle behavior.

### Phase-B scope and gate

The current bootstrap repair may edit this existing work-order file only, under the child claim generation 2 recorded in Issue #576 comment `5983877425`. It removes the unmerged malformed child-WO file from PR #584 and keeps the parent Phase-A source/test paths unchanged.

Later Phase-B source scope remains **NOT YET MUTABLE** until this docs-only bootstrap is accepted/merged, a fresh global WIP/collision/dirty gate passes, current main is re-pinned, and an exact source-claim generation is recorded:

- `src/a_conductor/codex_goal_api_adapter.py`
- `tests/test_codex_goal_api_adapter.py`

These paths are new-file-only. The existing Phase-A idle-guard module is read-only input. `sidecar_codex_bridge.py` and its tests remain owned by #575 and are forbidden here. Any main-head drift invalidates a later source binding and requires a fresh focused gate.

### Proven facts and strict unknowns

Accepted host evidence directly establishes `thread/goal/get`, `thread/goal/set`, `thread/queue/add`, `thread/queue/list`, `thread/queue/delete`, `thread/turns/list`, and `thread/resume` with `excludeTurns=true`. It establishes only the observed Goal transition `BLOCKED→ACTIVE`, metadata-only resume, one queued recovery-steer consumption, and the recorded migration outcomes.

For Phase B, use exact method names and only empirically recorded request/result fields that the post-bootstrap source/contract review can bind. Plain-type and bounded normalization must fail closed on malformed returns. Ambiguous write/resume outcomes remain typed UNKNOWN and are never retried automatically.

Outside scope until separately proven and authorized: any PAUSED transition/API mechanism; queue idempotency, dedupe keys, and retry semantics; authentication/authorization behavior; schedule control; thread identity discovery/binding rules; cross-host/version support; `thread/queue/start`; raw SQLite, session, or lock access. The observed post-reconciliation self-pause is an outcome fact and does not identify a callable pause API.

### Ordered gates and regression matrix

1. Accept and merge the docs-only child bootstrap through its normal docs gates.
2. Re-pin current A-Wiki main; inspect the exact post-main diff; rebuild global WIP/collision/dirty state; preserve #547, #575, and #581 ownership without overlap.
3. Establish exact source worktree/branch/HEAD, child claim generation, and only the two new paths above; rerun the normal mutation gate.
4. Independently verify every adapter field/method against accepted App Server 0.159.0 evidence. Unknown semantics remain excluded.
5. Run exactly one task-bound A-Audit recommendation and one `GLM_OFFLOAD_ASSESSMENT` after deterministic eligibility. For eligible heavy implementation, use accepted GLM-5.3 MAX only after one fresh fail-closed CoinTH preflight immediately before dispatch. No dispatch belongs to this bootstrap.
6. Implement RED-first tests, then the pure adapter within exact new-file scope. Verify focused and directly related tests, hostile/malformed shapes, no-retry behavior, scope, diff hygiene, encoding, and secret boundaries. Do not use live Goal/queue calls as a test substitute.
7. Freeze exact SHA; obtain independent exact-SHA R3 review, exact-head hosted CI, GPT adjudication, expected-head merge, and post-main verification.

Required regression cases:

- Accept only the single observed `BLOCKED→ACTIVE` Goal transition; fail closed for every unproven transition.
- Preserve `excludeTurns=true` for metadata-only `thread/resume`.
- Bind every operation to an explicitly supplied thread ID; never discover a target from ambient runtime state.
- Normalize malformed/hostile transport responses to typed UNKNOWN without echoing payloads.
- Ambiguous queue-write or resume results cause no retry and preserve observed IDs as evidence.
- No adapter result grants a Goal change, replay, claim, mutation, review, merge, or completion authority.
- Structural guard forbids database/session/lock access, credentials, schedules, and mutation of Phase-A or #575-owned paths.

This child claim and the current PR authorize docs-only governance repair. They grant no Phase-B source/test edit, runtime API call, quota probe, provider dispatch, claim transfer, or merge. After bootstrap acceptance, rerun the complete mutation/WIP/collision/dirty gate immediately; preserve a typed blocker if any identity, semantics, or ownership input is UNKNOWN.
