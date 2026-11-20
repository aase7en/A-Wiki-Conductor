# WO-P1-517 — A-Faster Utilization Enforcement

Status: ACTIVE / AUTHORING
Issue: #517
Risk: R3 — coordination and dispatch-policy enforcement
Topology: CONTROL_PLANE_ONLY
Claim: WO-P1-517-AFUTIL-MAC-001
Base: 84696b2360197c981d6f9fa2f33fb065b7b8ef07
Worktree: /Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo517-a-faster-util
Branch: feat/wo-p1-517-a-faster-utilization

## Goal
Make A-Faster underutilization machine-detectable without creating a scheduler or second authority. When A-Faster is active, safe independent READY capacity must not remain idle without a typed blocker.

## Exact mutable scope
- docs/plans/2026-09-19-a-faster-hook-stm-observability-roadmap.md
- this work order
- DEFECT_LESSONS.md
- .agents/skills/a-faster/SKILL.md
- tests/test_a_faster_invocation_contract.py
- src/a_conductor/a_faster_utilization_guard.py
- tests/test_a_faster_utilization_guard.py

## Required behavior
RED-first pure deterministic helper for FANOUT_TARGET, UNUSED_SAFE_CAPACITY, A_FASTER_UNDERUTILIZED and AUTO_REFILL_REQUIRED; activation receipt semantics in the skill/tests; GLM-first/Sol-integrator roles preserved; no quota-burning or manufactured work. Do not touch #498-owned pre_dispatch_guard.py or its WO/tests. Shared executable PRE_DISPATCH wiring is successor scope after #498 releases.

## Bootstrap defects to preserve
Attempt-0001 exposed two orchestration defects before accepted authoring: quota admission was incorrectly inferred by matching serialized command text after the real probe returned SECRET_SOURCE_UNAVAILABLE, and Kilo was launched without explicit --dir so its session inspected protected root main instead of the bound worktree. Attempt-0002 fixed those defects but exposed a third privacy defect: the operator's global Kilo config had share=auto, so delegated sessions emitted share links even though A-Faster never requested sharing. All invalid executions were cancelled and harvested, all four accidental session shares were explicitly revoked, and Git reconciliation proved no GLM-created scoped tracked side effects. Accepted enforcement must consume structured admission evidence, require explicit --dir plus in-session repo/worktree/branch/HEAD proof before mutation, and run delegated Kilo with a per-run share=disabled override unless sharing is separately authorized.

## Acceptance
Focused/related tests, py_compile, diff/UTF-8/secret/scope checks, frozen SHA, independent R3 review, exact-head CI, GPT acceptance/post-main. No self-merge.

## Attempt-0004 author checkpoint (2026-09-24)

- Executor: GLM-5.3 authoring lane, claim `WO-P1-517-AFUTIL-MAC-001`, base `84696b2360197c981d6f9fa2f33fb065b7b8ef07` (verified in-session before mutation; launcher independently proved Kilo share=disabled).
- RED-first proof: `tests/test_a_faster_utilization_guard.py` failed on missing module; 8 new invocation-contract tests failed against unmodified skill/roadmap/DEFECT_LESSONS before any docs edit. RED exposed one real boundary defect (fanout computed without the activation receipt) that was repaired in implementation.
- GREEN: implemented pure deterministic classifier `src/a_conductor/a_faster_utilization_guard.py` (`FANOUT_TARGET` / `UNUSED_SAFE_CAPACITY` / `A_FASTER_UNDERUTILIZED` / `AUTO_REFILL_REQUIRED`, `A_FASTER_ACTIVE` vs `A_FASTER_EXPLANATION_ONLY` tasking boundary, typed blockers incl. `SOL_DIRECT_LONG_LABOR_WHILE_GLM_CAPACITY_IDLE`, `NO_INDEPENDENT_READY_WORK`, quota fail-closed states, `DELEGATION_LAUNCH_PRECONDITIONS`; no scheduler/dispatch/claim/lease/provider/merge authority; no I/O; no quota probing).
- Docs: skill utilization-enforcement + activation-receipt + launch-discipline sections; roadmap policy-only seam subsection after §16; DEFECT_LESSONS #55 preserving all three bootstrap lessons. #498-owned `pre_dispatch_guard.py`/WO/tests untouched and not created.
- Evidence: `runs/WO-P1-517/author/attempt-0004/result.md`. Not committed; no merge authority claimed.
