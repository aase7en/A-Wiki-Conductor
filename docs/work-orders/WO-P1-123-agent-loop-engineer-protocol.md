# WO-P1-123 - Loop Engineer multi-agent protocol

Date: 2026-09-01
Owner: GPT-5.6 Sol integrator
Status: IMPLEMENTED / REVIEW_PENDING
Priority: P1 coordination safety / operator burden reduction

## Goal
Make multi-agent execution resumable from durable project state so the human supplies direction, not result transport. GPT/Conductor routes non-overlapping lanes, agents read exact task packets, update stable result/status destinations in place, and the integrator consumes those files directly.

## Scope
- `COLLAB.md`
- `docs/agent-collab/AGENT_TASKS.md`
- this work order

No runtime/source/UI/provider/tunnel mutation.

## Acceptance
1. One binding Loop Engineer order is documented from SSoT recovery through next-ready-node loop.
2. Parallel lanes require explicit non-overlap and one owner/integrator.
3. Stable `runs/<task-id>/task.md` + `result.md`/`status.json` mailbox is update-in-place; agents never require human result copy-back.
4. When auto-dispatch is unavailable, human relays only one short pointer prompt.
5. Resume/review reads durable status before new work; stale `DONE` text never overrides evidence.

## Verification
- `git diff --check`
- UTF-8 read of all changed files
- source diff is empty

## Implementation checkpoint - 2026-09-01

- Added the binding Loop Engineer execution order to the lane index.
- Added stable update-in-place task/status/result mailbox rules and the no-copy-back human fallback.
- Added integrator routing/non-overlap requirements to `COLLAB.md`.
- Verification: `git diff --check` PASS; UTF-8 read PASS; source diff empty.
- Independent exact-head review and CI remain required before merge.
