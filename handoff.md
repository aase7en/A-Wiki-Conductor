# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Current objective

Continue from the completed Phase 1 local Control Center MVP toward the Work-class durable agent tunnel North Star. The current slice is the first deterministic Native Execution Layer core; A-Wiki remains brain/policy/orchestration knowledge and Serena remains the semantic code specialist.

## Current task

`WO-P1-031 — Native Execution Core`

Status: `IN_PROGRESS`

## Reuse / ownership decision

P1-031 passed the A-Wiki reuse-before-build gate and is classified `EXTEND`: reviewed A-Wiki authoritative protocol/skill surfaces contain shell wrappers/routing policy but no general host execution engine that should replace this A-Conductor runtime responsibility.

Binding contract: `docs/contracts/native-execution-core.md`.

## Baseline evidence

- Base HEAD: `ce00f13 feat: complete worker runtime setup workflow`.
- Worktree was clean before P1-031.
- Prior full suite: 423 passed.
- A-Wiki ↔ A-Conductor boundary: `docs/contracts/a-wiki-a-conductor-integration.md`.
- Active Conductor listener previously preserved at `127.0.0.1:18011`, PID `25396`.

## Current scope

Implement only:
- project-root-confined bounded text read/list/write;
- atomic write with mutation authority and SHA-256 overwrite precondition;
- `shell=False` argv subprocess primitive;
- explicit executable allowlist, confined cwd, timeout, conservative environment, allowed env overrides, bounded stdout/stderr + digests.

Do not implement delete/move, destructive Git, generic model-facing shell, provider/tunnel provisioning, or A-Wiki mutations.

## External / deferred gate

`DR-P1-003 / BLOCKED_EXTERNAL`: Worker 3 live Stage B still requires a unique authorized transport binding. The A-Wiki companion registration payload is prepared but not applied from this Conductor-pinned surface.

## Next safe action

Commit the docs/claim checkpoint, write RED `tests/test_native_execution.py`, implement `src/a_conductor/native_execution.py`, then run targeted/full/compile/diff gates before closing the work order.

## Resume instructions

Read `AGENTS.md` -> `PROJECT-PLAN.md` -> `docs/contracts/a-wiki-a-conductor-integration.md` -> `docs/contracts/native-execution-core.md` -> `COLLAB.md` -> `CURRENT-WORK.md` -> this file -> active WO; verify branch/HEAD/status before mutation.
