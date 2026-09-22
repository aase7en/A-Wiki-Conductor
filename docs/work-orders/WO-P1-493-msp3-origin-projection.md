# WO-P1-493 — MSP-3 read-model origin/session observability projection

Status: ACTIVE / IMPLEMENTATION READY
Issue: #493
Parent: #475
Topology: CONTROL_PLANE_ONLY
Risk: R3
Claim: WO-P1-493-MSP3-WINDOWS-001
Authority repo: A:\GitHub\A-Wiki-Conductor
Worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo493-msp3
Branch: feat/wo-p1-493-msp3-origin-projection
Base SHA: 90d92bff51f1547548199be941c85c54d0a9fd3a

## Goal

Extend the accepted cockpit read model with privacy-preserving origin/session provenance display without granting origin data any mutation, ownership, scheduling, review, retry or completion authority.

## Mutable scope

- src/a_conductor/cockpit_projection.py
- src/a_conductor/desktop_ui.py
- tests/test_cockpit_projection.py
- tests/test_desktop_control.py
- docs/work-orders/WO-P1-493-msp3-origin-projection.md

Everything else is read-only.

## Required invariants

- Origin/session provenance is observation/context only.
- Origin data must not alter CockpitState, process authority, gates, replay_safety, next_safe_action, claim/lease owner, writer selection, scheduler, retry, review or completion authority.
- Missing pre-MSP1 provenance renders typed NOT_RECORDED/UNAVAILABLE and is never inferred.
- Unsupported provenance renders UNKNOWN/degraded display only.
- Multiple origins referring to one durable lane remain one lane and one durable owner.
- Takeover follows accepted lease release/new lease only.
- Monitor restart reconstructs from durable read-only authority; monitor state is never authority.
- Do not populate live CockpitGitObservation in this slice.
- Do not wire provider/operator view in this slice.
- Do not modify control_hook_adapter.py or origin_provenance.py; #482 owns those paths.

## JEV protected scope — forbidden

Issue #484 / JEV family and active #492 JEV-1C are protected. Do not touch:
- scripts/jev_shadow_benchmark.py
- scripts/jev_typesafe_contract.py
- tests/test_jev_shadow_benchmark.py
- tests/test_jev_typesafe_contract.py
- tests/fixtures/jev_shadow/**
- docs/work-orders/WO-P1-484-*
- docs/work-orders/WO-P1-486-*
- docs/work-orders/WO-P1-488-*
- docs/work-orders/WO-P1-492-*
- docs/plans/2026-09-22-jev-system-one-acceleration-roadmap.md

## Concurrent protected scope

- #482 MSP-1: src/a_conductor/origin_provenance.py, src/a_conductor/control_hook_adapter.py and related tests/WO.
- #480 A-Faster delegated-run artifact identity follow-up until PR #490 completes.
- #265 runtime self-heal operational authority.

## RED-first acceptance

1. Origin present vs absent leaves state/gates/process authority/replay/next action equivalent except origin display.
2. Multiple origins for one lane never create multiple owners/lanes.
3. Unsupported origin provenance yields typed UNKNOWN display only.
4. Terminal-unharvested remains terminal-unharvested with origin data.
5. Unknown runtime remains UNKNOWN/DEGRADED.
6. Fresh facade/read model reconstructs equivalent projection after restart.
7. No command/dispatch/retry/cancel/merge/reassign surface appears.
8. Authority DB reads remain read-only.
9. Raw-ID/secret-shaped values are rejected or never rendered.
10. Cross-repo/SHA display values cannot mutate authority.

## Verification

- python -m pytest tests/test_cockpit_projection.py tests/test_desktop_control.py -q
- py_compile changed Python
- git diff --check
- focused no-write / authority-neutrality checks
- final dirty scope exactly within this WO
- independent GLM-5.3 MAX R3 review
- hosted CI
- expected-head merge + post-main verification

Before source mutation read DEFECT_LESSONS.md and re-run exact mutation gate.
