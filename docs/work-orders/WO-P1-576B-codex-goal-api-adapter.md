# WO-P1-576B — Codex Goal API adapter (Phase B child)

Issue: #576
Parent: WO-P1-576-codex-goal-idle-guard (Phase A accepted post-main)
Claim ID: WO-P1-576B-GOAL-API-ADAPTER-MAC-001
Claim record: Issue #576 comment `5982559265`
Topology: CONTROL_PLANE_ONLY
Risk: R3 — Goal lifecycle and queue control
Status: DOCS-ONLY GOVERNANCE BOOTSTRAP; Phase-B source mutation requires a fresh post-bootstrap gate.

## 1. Task boundary

Add a pure, caller-injected adapter for the supported Codex App Server Goal/queue operations that Phase A deliberately does not execute. It translates explicit typed intents and bounded transport results; it owns no scheduling, claims, retry, dispatch, review, merge, or completion authority. Phase-A `codex_goal_idle_guard.py` remains the decision projection and is read-only input.

This child exists only for the observed App Server 0.159.0 recovery arc. The runtime canary and successor migration are recorded in Issue #576 comments `5981598729` and `5981760977`. Source changes may use only those directly proven facts. Do not infer unobserved protocol, authorization, or lifecycle behavior.

## 2. Exact scope

### This bootstrap — mutable now

- `docs/work-orders/WO-P1-576B-codex-goal-api-adapter.md` in the isolated A-Wiki bootstrap worktree and branch recorded in Issue #576 comment `5982559265`.
- Issue #576 child-claim evidence only.

### Later Phase-B source — NOT YET MUTABLE

Only after this bootstrap is accepted and merged, then after a fresh global WIP/collision/dirty gate, current-main re-pin, and exact source-claim generation 2:

- `src/a_conductor/codex_goal_api_adapter.py`
- `tests/test_codex_goal_api_adapter.py`

These paths are new-file-only. Do not modify the Phase-A classifier, `sidecar_codex_bridge.py`, its tests, accepted hooks, schedules, Goal/thread state, or any other source, test, policy, or runtime file.

The exact future source worktree, branch, base SHA, owner, and scope digest must be bound in the accepted source claim after the bootstrap merge. Any main-head drift invalidates that binding and requires a fresh focused gate.

## 3. Proven facts and strict unknowns

The current accepted host evidence directly establishes these method names: `thread/goal/get`, `thread/goal/set`, `thread/queue/add`, `thread/queue/list`, `thread/queue/delete`, `thread/turns/list`, and `thread/resume` with `excludeTurns=true`. It establishes only the observed Goal transition `BLOCKED→ACTIVE`, metadata-only resume, one queued recovery-steer consumption, and the recorded migration outcomes.

For Phase B, use exact method names and only the empirically recorded request/result fields that the post-bootstrap source/contract review can bind. Plain-type and bounded normalization must fail closed on malformed returns. Ambiguous write/resume outcomes remain typed UNKNOWN and are never retried automatically.

The following remain outside scope until separately proven and authorized: any `PAUSED` transition/API mechanism; queue idempotency, dedupe keys, and retry semantics; authentication/authorization behavior; schedule control; thread identity discovery/binding rules; cross-host/version support; `thread/queue/start`; raw SQLite, session, or lock access. In particular, the observed post-reconciliation self-pause is an outcome fact and does not identify a callable pause API.

## 4. Ordered gates

1. Accept and merge this docs-only child bootstrap through the normal docs-only gates.
2. Re-pin current A-Wiki main and inspect the exact post-bootstrap diff; rebuild global WIP/collision/dirty state. Preserve #547's untracked lane, #575's exact candidate/CI/review gate, and #581's quarantined SRM artifact without overlap.
3. Establish exact source worktree/branch/HEAD, claim generation 2, and only the two new paths above. Re-run the normal mutation gate.
4. Read the current source entry/graph/policies and `DEFECT_LESSONS.md`; independently verify that every field/method included in the adapter is proven by the accepted 0.159.0 evidence. Unknown semantics remain excluded.
5. Run exactly one task-bound A-Audit recommendation and one `GLM_OFFLOAD_ASSESSMENT` for this child after deterministic eligibility. For eligible heavy implementation, use the accepted GLM-5.3 MAX route only after a fresh fail-closed CoinTH preflight immediately before dispatch. No dispatch is part of this bootstrap.
6. Implement RED-first tests, then the pure adapter within the exact new-file scope. Verify focused and directly related tests, type/shape failures, no-retry behavior, scope, diff hygiene, encoding, and secret boundaries. Do not run live Goal/queue calls as a test substitute.
7. Freeze exact SHA; obtain independent exact-SHA R3 review, exact-head hosted CI, GPT adjudication, expected-head merge, and post-main verification.

## 5. Required regression matrix

- Accept only the single observed `BLOCKED→ACTIVE` Goal transition; every unproven transition fails closed.
- Preserve `excludeTurns=true` for metadata-only `thread/resume`.
- Bind every operation to an explicitly supplied thread ID; never discover a target from ambient runtime state.
- Normalize malformed/hostile transport responses to typed UNKNOWN without echoing payloads.
- Ambiguous queue-write or resume results cause no retry and preserve observed IDs as evidence.
- No adapter result grants a Goal change, replay, claim, mutation, review, merge, or completion authority.
- Structural guard forbids database/session/lock access, credentials, schedules, and mutation of Phase-A or #575-owned files.

## 6. Bootstrap prohibition and next safe action

This bootstrap authorizes only the work-order file and child claim record. It authorizes no Phase-B source/test edit, runtime API call, quota probe, provider dispatch, or claim transfer. Re-run the complete gate immediately after acceptance/merge. If exact binding, WIP, semantics, or ownership remains UNKNOWN, preserve a typed blocker and do not begin Phase-B implementation.
