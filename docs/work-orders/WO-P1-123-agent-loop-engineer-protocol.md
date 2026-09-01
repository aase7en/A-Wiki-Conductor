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

## Release evidence
- implementation/review HEAD: `6839f1d936bfdc1c2962f006baae7a121f6731a4`
- independent GLM-5.3 MAX review: PASS, P0/P1/P2 = 0; task SHA `00d64f4f0194c3ba10c502d232303a53a34f7b56e8ed2fb72081f3449a860c3a`
- PR #170 merged as `5ddf533fca4d236fbd3b9fcbc092cfbd6d3341b9`
- exact-head CI `33483988509`: Windows/macOS/Ubuntu SUCCESS
- post-main CI `33486497661`: SUCCESS
- GLM review claim released after result validation. P3 mailbox-history/schema/gitignore clarifications remain non-blocking successor hardening.
