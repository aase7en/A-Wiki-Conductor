# WO-P1-159 — Loop Engineering Adoption Foundation

Status: ACTIVE / R2 FOUNDATION
Owner: GPT-5.6 Sol
Date: 2026-09-06

## Goal

Adopt the strongest reusable ideas from `cobusgreyling/loop-engineering`
without creating duplicate A-Wiki/A-Conductor authorities or importing a
parallel Node orchestration stack.

## Repository identity

- Repository: `aase7en/A-Wiki-Conductor`
- Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo159-loop-engineering`
- Branch: `feat/wo-p1-159-loop-engineering-adoption`
- Base HEAD: `f0ddd0b9245cef7a7525a670f470e1de595d4615`
- Root checkout: protected/stale/dirty; never mutate it.

## Reuse-before-build classification

- Existing task budget/retry contract: **REUSE**
- Existing scheduler/job/provider/lease/review authorities: **REUSE**
- Upstream Loop Pattern Registry concept/schema: **ADAPT**
- Upstream run-history circuit-breaker concept: **ADAPT / Python-native**
- A-Doctor readiness scoring: **EXTEND LATER**
- Static mutation safety gate: **EXTEND EXISTING GATES LATER**
- Upstream Node/TypeScript orchestration runtime: **REJECT AS DEPENDENCY**
- New parallel scheduler, mailbox, claim store, or SSoT: **FORBIDDEN**

Upstream research pin:
`cobusgreyling/loop-engineering@e1c9d5f5e23655b65d04c5617aff77ab3ad58c16`
(MIT; Copyright 2026 Cobus Greyling and contributors).

## Allowed scope

- `docs/work-orders/WO-P1-159-loop-engineering-adoption.md`
- new `docs/research/**loop-engineering**`
- new `docs/plans/**loop-engineering**`
- new `schemas/loop-recipe.schema.json`
- new `src/a_conductor/loop_guard.py`
- new `tests/test_loop_guard.py`
- `README.md` credit/reference only
- `THIRD-PARTY-NOTICES.md` upstream MIT notice only

## Forbidden scope

- `PROJECT-PLAN.md`, `AGENTS.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`
- current WO154/WO155 files except read-only research
- scheduler, graph dispatch, job store/state, provider runtime/authority
- live workers, tunnels, credentials, live control database
- A-Wiki mutation

## Acceptance

1. Current upstream is pinned and license/credit preserved.
2. Roadmap separates reuse/adapt/build/reject decisions and dependency order.
3. Loop Recipe schema adds reusable autonomous-loop metadata without replacing Task Contract.
4. Deterministic guard detects iteration cap, repeated identical failure,
   consecutive no-progress, token cap, elapsed-time cap, and cost cap.
5. Guard is pure/no-I/O/no-LLM and does not replay side effects.
6. Focused tests cover continue + every breaker reason + validation/priority.
7. README credits Cobus Greyling / loop-engineering.
8. MIT notice is preserved for materially adapted upstream concepts/schema.
9. No shared hotspot or active ZRA implementation scope changes.

## Verification

- `python -m pytest tests/test_loop_guard.py -q`
- schema JSON parse check
- `python -m compileall src/a_conductor/loop_guard.py`
- `git diff --check`
- inspect `git diff --name-only origin/main...HEAD`

## Checkpoint

Initial gate: `SAFE_TO_MUTATE = YES` for this isolated worktree and the
allowed scope above. Shared SSoT fold-back is intentionally deferred until
WO154 releases its hotspot ownership.

Implementation evidence:
- RED baseline: `ModuleNotFoundError: a_conductor.loop_guard`.
- First GREEN attempt exposed a real streak-accounting bug; repaired test-first.
- Self-review exposed optional `tokens_used=None`; regression added and boundary hardened.
- Focused + adjacent impact suite: `48 passed`.
- `python -m compileall -q src/a_conductor/loop_guard.py`: PASS.
- JSON Schema Draft 2020-12 self-check: PASS.
- Valid CI-sweeper recipe sample: PASS.
- EVENT recipe without `event_type`: correctly rejected.
- Unknown autonomy level: correctly rejected.
- `git diff --check`: PASS.
- Full frozen-candidate suite: `2182 passed, 5 skipped, 2 failed`.
- The two full-suite failures are `ENVIRONMENT_FAILURE`: the invoked Python
  environment lacks Pillow/OpenGL for `test_gpu_particle_logo.py`; WO159
  changes no GPU/logo/runtime dependency file. Existing project handoff also
  records the same class of known optional-GPU local failures.
- Fresh `origin/main` remains base `f0ddd0b9245cef7a7525a670f470e1de595d4615`.

Current status: `FROZEN_CANDIDATE / SELF_REVIEW_PASS`, not merge-ready.
Cached scope review: 8 intended files only; no unstaged delta and no shared
hotspot mutation. Independent review is still required.
Next safe action: commit/push this frozen candidate and open a Draft PR, then
require independent review + exact-head CI before any merge.
