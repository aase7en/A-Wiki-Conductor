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

## Implementation checkpoint — attempt-0001 (2026-09-22)

Status: IMPLEMENTED (uncommitted, awaiting GPT-5.6 Sol harvest + independent review).

- Dispatch HEAD verified exactly: `a86f21f0cc4e183b69a9f9aa05a6dacd810eba0f`, clean tree before mutation, branch `feat/wo-p1-493-msp3-origin-projection`.
- RED first: 11 new tests failed on missing `CockpitOriginObservation` / `CockpitOriginDisplay` / `origin_display` before any source change.
- GREEN: `python -m pytest tests/test_cockpit_projection.py tests/test_desktop_control.py -q` = **99 passed** (88 pre-existing + 11 new). Affected UI/projection regression set = 120 passed, 78 skipped (known Tcl/display environment skips only).
- `py_compile` on all changed Python: OK. `git diff --check`: OK.
- Dirty tracked paths exactly: `src/a_conductor/cockpit_projection.py`, `src/a_conductor/desktop_ui.py`, `tests/test_cockpit_projection.py`, `tests/test_desktop_control.py`, plus this WO file — all within the declared mutable scope. No commit/push/merge performed.

### Changed symbols (additive only)

- `cockpit_projection.py`: new `CockpitOriginObservation` (opaque MSP-1 `origin-chat-v1:<kv>:<64hex>` grammar gate; unsupported provenance stays constructible with payload stripped, renders typed UNKNOWN only), new `CockpitOriginDisplay`, `_origin_display()`, mirrored MSP-1 vocabulary constants, `CockpitLaneInputs.origin` (defaulted), `CockpitLaneProjection.origin_display` (defaulted), origin wired into `project_cockpit_lane` common dict and `_stale_lane`, `build_observed_lane_inputs(..., origins=())` deterministic earliest-observed join by `execution_id`.
- `desktop_ui.py`: one ORIGIN display line per lane in `cockpit_monitor_lines`.

### Authority-neutrality proof (test-pinned)

- origin present vs absent leaves state/markers/blocker/replay/next-action/gates/process identity/execution/job/transport/hook/wtl equivalent;
- multiple origins for one lane stay one lane, one identity/lease/owner (deterministic earliest pin, order-independent);
- unsupported provenance renders `ORIGIN_PROVENANCE_UNSUPPORTED` UNKNOWN display, payload never held or rendered;
- raw/secret-shaped refs rejected at DTO boundary (`ORIGIN_REF_MUST_BE_OPAQUE_DERIVED_REF`);
- pre-MSP1 absence renders typed `NOT_RECORDED`/`UNAVAILABLE`, never inferred;
- terminal-unharvested and DEGRADED runtime states unchanged with origin present;
- origin drift between pins renders STALE with origin display `UNKNOWN/SOURCE_DRIFT_DETECTED`;
- service-level: unchanged `desktop_control.py` composition renders typed UNAVAILABLE origin display on every lane, legacy DB gains no tables, directory inventory unchanged;
- no new command/dispatch/retry/cancel/merge/reassign surface; `desktop_control.py`, `origin_provenance.py`, `control_hook_adapter.py` untouched (verified by dirty-path scope).

### Residual

- Live origin observation wiring lands with #482 MSP-1 acceptance; this slice intentionally leaves composed lanes typed UNAVAILABLE/NOT_RECORDED.
- Pending gates: independent GLM-5.3 MAX R3 review, hosted CI, expected-head merge + post-main verification.
