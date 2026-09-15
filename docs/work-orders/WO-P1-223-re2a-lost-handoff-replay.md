# WO-P1-223 RE2-A — Lost-Handoff Durable Replay Repair

Status: ACTIVE / R3 / CLAIMED
Claim: `WO-P1-223-RE2A-LOST-HANDOFF-REPLAY-001`
Owner: GPT-5.6 Sol integrator; bounded implementation may transfer to GLM-5.3 MAX on this same claim/worktree.
Date: 2026-09-15

## Authority and exact state

Authority order: actual runtime/Git/GitHub/durable Issue state > claims/checkpoints/evidence > this WO/CURRENT-WORK/handoff > chat.
Driving durable authority: GitHub Issue #214.
Repo: `aase7en/A-Wiki-Conductor`.
Windows device: `DESKTOP-7IB57R4`.
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo223-re2a-replay`.
Branch: `fix/wo-p1-223-re2a-lost-handoff-replay`.
Base: `082705889e26023079e73deacb7f642eb122713b`.
Origin main at claim: `67744e98e538b000579bff4a45616d3a178a824b`.
PR #319 remains OPEN/DRAFT at `42221020c02c507decfb396ac8c3b9da54d523bc`; do not merge until replacement candidate passes R3 gates.

## Problem

RE1 made exit-0 reviewer executions acceptance-reachable by verifying and promoting `VERIFICATION_REQUIRED -> SUCCEEDED` before handoff. A crash after promotion/cleanup but before the in-memory handoff is consumed leaves exact durable execution truth but loses the original lease locator. Replay uses active-only lease lookup and therefore returns `LEASE_IDENTITY_UNPROVEN` forever after the released row becomes invisible by owner-key lookup.
## Accepted RE2-A architecture

Reuse the existing execution promotion event and existing historical resource APIs. At the existing SUCCEEDED promotion CAS, before cleanup, persist a strict versioned resource-identity payload in `execution_events.evidence_ref` containing the exact original lease/admission locators and required cross-bind facts.

Replay of a completed execution must resolve the exact historical resources with existing authorities:
- `lease_store.inspect_health(lease_id)`;
- `provider_store.get_admission(admission_id)`;
- existing plan/task/route/execution identity checks.

Required cross-binding includes exact task/review contract, worker, project, worktree, branch, reviewed HEAD, lease session, provider, dispatch execution, deterministic batch, and provider generation pinned at the original attempt. A foreign/conflicting/stale/ambiguous/malformed pointer fails closed and must not release another resource.

If the exact original resources are still active, perform existing idempotent terminal cleanup. If already released, prove that truth by exact ID. Then reconstruct the existing `REUSE_COMPLETED` handoff with zero second model effect. Do not change C1 verdict semantics.

Legacy/no-v2-event behavior remains fail-closed. Direct verifier callers without the new identity input preserve the legacy evidence format/behavior.

## Mutable tracked scope

Implementation source/test scope only:
1. `src/a_conductor/zero_relay_review_verification.py`
2. `src/a_conductor/zero_relay_review_execution.py`
3. `tests/test_zero_relay_review_verification.py`
4. `tests/test_zero_relay_review_execution.py`

Continuity scope for this WO:
- this work-order file;
- `CURRENT-WORK.md`;
- `handoff.md`.
## Forbidden scope

Do not mutate execution store/schema, job store/state machine/coordinator, provider store, worker lease implementation, C1 evidence/task semantics, Phase-D/WO205, WO227/ZRA-3, A-Wiki, live provider/runtime, credentials/secrets, or protected root checkout. No reset/clean/stash/rebase/merge/force-push. No second lifecycle/store/scheduler/review/claim/lease authority.

Pre-promotion hard-crash liveness (`EXECUTING + VERIFICATION_REQUIRED`) is a separate RE2-B/continuity-liveness adjudication. RE2-A must not directly transition job lifecycle state.

## RED-first acceptance matrix

At minimum prove:
- post-cleanup lost handoff reconstructs exact original lease/admission and returns `REUSE_COMPLETED`;
- zero new model effect and zero new lease/admission rows on replay;
- crash after promotion but before cleanup resolves active exact resources and cleans once;
- replay works after provider generation drift by binding the original event-pinned generation;
- active same-owner lease with a different lease id is a typed conflict and is not released;
- foreign lease/admission pointer, malformed/oversized evidence, duplicate/ambiguous promotion evidence and missing resource fail closed;
- stale/unproven lease is never force-released;
- legacy promotion evidence preserves the old fail-closed behavior;
- concurrent/idempotent replay cannot create a second model effect;
- reconstructed handoff remains accepted by existing C1 composition without weakening C1.

## Delivery gates

R3 loop: RED -> bounded implementation -> targeted+related regression -> adversarial/fault matrix -> diff/scope/secret/UTF-8 checks -> frozen exact SHA -> independent exact-SHA review -> repair if confirmed -> hosted CI on exact head -> GPT expected-head acceptance -> non-force fast-forward PR #319 only if ancestry/live remote truth still matches -> merge -> post-main CI -> Issue #214 checkpoint.

Any production repair after freeze creates a new candidate SHA and requires rereview. GLM may implement/test/repair inside this scope, but cannot accept, merge, widen scope, use live provider credentials, or claim completion authority.
## File-first continuity protocol

This file is the durable task memory for RE2-A. A fresh session must not depend on prior chat. Resume in this order:
1. read `00-AGENT-ENTRY.md`, `PROJECT-GRAPH.yaml`, `AGENTS.md`;
2. verify device/repo/worktree/branch/HEAD/dirty state and fetch current GitHub Issue #214 + PR #319 truth;
3. read `CURRENT-WORK.md`, this WO, `handoff.md`, `DEFECT_LESSONS.md`, and the zero-relay / fast-execution / collaboration nodes selected by the graph;
4. inspect `runs/WO-P1-223-RE2A/status.json` and `result.md` if present;
5. reconcile any contradiction before mutation.

Meaningful checkpoints must record: exact HEAD, branch/worktree, owner/executor, dirty state, tests/evidence, findings/blockers, scope/forbidden scope, candidate/review/CI/merge status, and exact next safe action. Issue #214 mirrors major boundaries so loss of one local worktree does not erase continuity.

## Checkpoint 2026-09-15 — claim/bootstrap

Recovered base and remote truth after restart; Issue #214 claim comment `5674623000` created. Fresh worktree/branch created from exact clean `082705889e26023079e73deacb7f642eb122713b`. Tracked continuity bootstrap is in progress. Source mutation remains blocked until the continuity commit is clean and a fresh source gate passes.

`SAFE_TO_MUTATE_RE2A_DOCS=YES`
`SAFE_TO_MUTATE_RE2A_SOURCE=NO`

Next safe action: finish/verify/commit tracked continuity bootstrap, create ignored lane task/status/result packet, re-gate exact worktree, checkpoint Issue #214, then transfer the bounded four-file source/test implementation to GLM-5.3 MAX while GPT runs independent architecture/fault/integration lanes.