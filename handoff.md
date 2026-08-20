# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Current objective

Build the durable runtime layer needed for Work-class resumable execution while keeping A-Wiki authoritative for planning, work-order content, memory, and orchestration policy.

## Current task

`WO-P1-034 — Durable Job State + Checkpoint Store`

Status: `IN_PROGRESS`

## Baseline

- Native execution foundation complete through transactional Git mutations.
- Latest completed feature commit before this work order: `23443fe`.
- Full suite at that checkpoint: 461 passed.
- Active Conductor listener remained `127.0.0.1:18011`, PID `25396`.

## P1-034 boundary

- A-Wiki work orders are referenced opaquely; their prompt/spec content is not copied into the job DB.
- A-Conductor stores operational state: TaskState, worker claim, attempt budget, recovery classification, optimistic version, append-only checkpoint/evidence metadata.
- No planner/router/scheduler/background loop in this work order.
- No A-Wiki repo mutation.

## Next safe action

Commit the P1-034 coordination/contract checkpoint, then write RED transition-policy tests before implementing `job_state.py`; persistence tests and `job_store.py` come after the pure policy is green.

## Resume order

`AGENTS.md -> PROJECT-PLAN.md -> docs/contracts/a-wiki-a-conductor-integration.md -> docs/contracts/durable-job-state.md -> COLLAB.md -> CURRENT-WORK.md -> handoff.md -> active work order -> git status/HEAD`.
