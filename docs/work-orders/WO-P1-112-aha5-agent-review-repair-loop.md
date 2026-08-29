# WO-P1-112 — AHA-5 multi-agent review/repair loop

Date: 2026-08-29
Owner: GPT-5.6 Sol integrator
Status: ACTIVE / CONTRACT-FIRST
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-aha5-review-repair`
Branch: `feat/wo-p1-112-aha5-agent-review-repair-loop`
Base: `origin/main@7f9a16f6dfafe17f3795167da22d4886945611e0`
Parent: Sunday Family Harness Accelerator / AHA-5

## Goal

Prove one GPT-plan/review -> GLM-implement/repair vertical slice where task, status,
result, diff and deterministic evidence move through durable repository state rather
than human copy/paste. Human prompt relay is fallback only when direct provider
execution is unavailable.

## Reuse classification

**EXTEND + WRAP** the accepted Claude-Code harness, durable job state, execution
artifacts, provider configuration, supervised native runner and AHA-4B worker lease.
Modernize stale `docs/agent-collab/*`; do not create a second scheduler, memory,
claim system, task store, retry lifecycle or provider-specific orchestration model.
## Lane contract

### GPT integrator lane
- owns architecture, task packet, acceptance criteria, review, merge and release authority;
- may edit coordination/docs plus integration surfaces assigned by this WO;
- must read GLM result/evidence directly from durable files/artifacts;
- must never treat an agent's `DONE` claim as acceptance evidence.

### GLM implementation/repair lane
- receives one immutable task packet reference plus exact worktree/branch/HEAD;
- mutates only its leased allowed scope in an isolated worktree;
- writes status/result to the task's durable result destination;
- records tests, diff summary, blockers and next safe action there;
- never edits GPT-owned coordination files, merges PRs, publishes releases or changes credentials.

### Future-agent lanes
Use the same packet/result contract. Provider/model names are metadata, not lifecycle
semantics. Two mutable lanes may run concurrently only when lease/scope checks prove
non-overlap.

## Required durable packet fields

`task_id`, `goal`, `owner`, `provider`, `model`, `worktree`, `branch`, `expected_head`,
`allowed_scope`, `forbidden_scope`, `acceptance`, `verification`, `evidence_destination`,
`status`, `checkpoint_at`, `result_ref`, `next_safe_action`.
## Acceptance criteria

1. One bounded GLM implementation task can be dispatched without result copy/paste.
2. Mutation is impossible without exact identity + active compatible worker lease.
3. Mutation is confined to allowed scope; forbidden/overlap/dirty uncertainty fails closed.
4. Result packet/evidence survives process/session/model rotation and is re-readable by GPT.
5. GPT can issue one bounded repair round from failed review without a new human prompt.
6. Timeout/transport loss becomes uncertain ownership/reconciliation, never blind replay.
7. Secret values never enter tracked packets, logs or result artifacts.
8. Stale/hard-coded `docs/agent-collab/*` becomes provider-neutral and points to SSoT.
9. Existing READ_ONLY Claude harness behavior remains backward compatible.
10. Focused + integration + chaos/race tests, compileall, diff/scope/secret audit and
    exact-head Windows/Ubuntu/macOS CI including Frozen Setup E2E pass before merge.

## GLM suitability evidence

Official Z.ai GLM-5.3 evidence reviewed before delegation: Terminal-Bench 3.0 28.3,
DeepSWE v1.1 66.9 and Z.ai Code Bench Max 34.5%; Z.ai recommends max reasoning for
coding and officially supports GLM Coding Plan through Claude Code. This makes GLM
appropriate for bounded implementation/repair, while GPT retains architecture,
trust-boundary review and merge authority.

## Initial implementation gap

The accepted harness already verifies task packet hashes, provider readiness, structured
JSON output, durable job evidence and secret redaction, but deliberately rejects mutation
(`HARNESS_MUTATION_NOT_READY`) and supervised Claude native execution sets
`mutation_allowed=False`. AHA-5 must open only a lease-bound scoped mutation path rather
than bypass these gates.

Next: checkpoint claim -> write RED contract tests -> smallest mutation/result bridge ->
independent review -> real GLM vertical slice -> bounded repair slice -> CI/merge loop.
