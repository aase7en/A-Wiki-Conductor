# WO-P1-218 — ZRA-2 Phase C0 independent-review hardening

Status: ACTIVE / BOUNDED REPAIR
Parent: WO-P1-216 / Issue #214 / PR #296
Base candidate: `ade1628247a4512fa879c10bfd093d14f51d487f`
Owner: GPT-5.6 Sol integrator as bounded repair author
Risk: R3 identity / trust boundary

## Findings reproduced on exact parent
1. Successful review-task publication can return success without re-reading persisted bytes. A deterministic post-publication mutation produced `persisted_sha256 != actual_sha256` while `materialize_review_task()` returned success.
2. Direct route binding accepts an arbitrary packet path outside `dispatch.worktree_path` when the string merely ends with the deterministic relative task path.

## Mutable scope
- `src/a_conductor/zero_relay_review_task.py`
- `tests/test_zero_relay_review_task.py`
- this WO

Everything else read-only. No scheduler/provider/lease/mailbox/ReviewEvidence lifecycle changes. No C1/Phase-D/merge authority.

## Required repair
- RED first for both exact reproducers.
- After successful create, re-read through `NativeFileSystem` and verify relative path, content hash, size, and exact content before returning success; unverifiable/mismatch fails typed.
- Route binding must require exact normalized task path under the authoritative dispatch worktree, not suffix matching. Preserve Windows path semantics without inventing a second path authority.
- Existing `ParallelReadyTask` trust fences remain reused; do not mutate that module.

## Acceptance
Focused tests plus WO216 regression floor green, no new authority, exact scope only, hosted CI green, and fresh independent exact-SHA rereview by a non-author before acceptance/merge.

## Repair checkpoint — 2026-09-12
- RED exact parent `ade1628247a4512fa879c10bfd093d14f51d487f`: 2/2 reproducers failed as intended.
- Fix 1: successful publication now always re-reads via `NativeFileSystem.read_text()` and verifies relative path, exact content, UTF-8 byte size, and SHA before returning; mismatch after create -> `REVIEW_TASK_STATE_UNVERIFIABLE`; pre-existing divergent bytes remain `REVIEW_TASK_COLLISION`.
- Fix 2: direct route now derives the exact expected packet path from authoritative `dispatch.worktree_path + deterministic relative task path` and compares using existing `windows_worktree_key`; suffix-only paths outside the worktree fail `REVIEW_PACKET_MISMATCH`.
- No changes to `ParallelReadyTask`, scheduler, provider, lease, mailbox, ReviewEvidence, or filesystem authority.
- Verification: WO216 floor plus repair tests = 339 passed; compileall, `git diff --check`, strict UTF-8/no U+FFFD PASS.
- Repair author is GPT-5.6 Sol; independent exact-SHA rereview remains required before acceptance/merge.
