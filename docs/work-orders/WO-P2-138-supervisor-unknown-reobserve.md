# WO-P2-138 — Bounded supervisor UNKNOWN re-observation

Date: 2026-09-02
Owner / integrator: GPT-5.6 Sol MAX
Status: VERIFIED / READY_FOR_INDEPENDENT_REVIEW
Priority: P2 supervised execution reliability
Base: `9a88b1d38d90bf8ce98dcef9a5108e270e8d2b48`
Worktree: `A:\GitHub\A-Wiki-Conductor-wo138-supervisor-unknown-reobserve`
Branch: `fix/wo-p2-138-supervisor-unknown-reobserve`

## Defect evidence
A real Windows integration run returned `BACKEND_REPORTED_FAILURE`, while the same run later contained durable `result.json` with `exit_code=0`. The reviewed WO137 child-PID-read repair does not touch this caller polling boundary.

## Goal
Prevent one transient pre-result `SUPERVISOR_OWNERSHIP_UNKNOWN` observation from winning over a shortly-arriving durable result, without repeating launch/termination/collect side effects or weakening fail-closed ownership errors.

## Mutable scope
- `src/a_conductor/supervised_command_runner.py`
- `tests/test_supervised_command_runner.py`
- this work order

## Forbidden
- `src/a_conductor/supervised_execution.py` (WO137 scope)
- owned-process launch/termination implementation
- job/scheduler/provider/UI/graph/release state
- shared SSoT until closeout
- live Workers/tunnels/credentials

## RED-first acceptance
1. `UNKNOWN -> RESULT_AVAILABLE` resolves to result, not recovery.
2. Persistent UNKNOWN uses a small finite re-observation budget; no unbounded wait.
3. Caller timeout still wins if the deadline is crossed during observation/re-observation.
4. `SUPERVISOR_EXITED_RESULT_MISSING` remains immediate recovery.
5. MISMATCH/ABSENT/unexpected recovery codes remain immediate recovery.
6. No launch/termination is repeated; poll remains inspection-only until collect after result.
7. No sleep after the final bounded UNKNOWN observation.
8. Existing timeout/result tests stay green.
9. Real Windows `test_supervised_mode_routes_pytest_through_durable_execution` stress exceeds the observed failure window.
10. Related supervised/job/runtime matrices, compileall, diff, UTF-8, scope and secret audits pass.

## Dependency / merge rule
WO138 is source-disjoint from WO137. Either may be reviewed independently, but eventual main must contain both repairs before supervised reliability is considered closed. Any new SHA invalidates prior exact-head review evidence.

## Next
Commit/push claim checkpoint → deterministic RED → narrow repair → focused/impact/Windows stress → freeze exact SHA → independent review when an external reviewer is available → PR/CI/merge/post-main → Defect Memory + SSoT closeout.
## GPT repair checkpoint — 2026-09-02
- Clean RED after fixing one test-setup mistake: 3 intended failures / 1 non-UNKNOWN guard pass. Current code returned on the first `SUPERVISOR_OWNERSHIP_UNKNOWN` instead of re-observing.
- Repair is limited to `_poll_until_resolved()`: at most 3 consecutive UNKNOWN observations total, caller deadline checked first, and every other recovery code remains immediate fail-closed.
- No launch, termination, collect, store, scheduler, provider, UI or graph authority changed.
- Focused `tests/test_supervised_command_runner.py`: 15/15 PASS.
- Related supervised/owned-process/runtime/job/execution matrix: 122/122 PASS.
- Real Windows regression `test_supervised_mode_routes_pytest_through_durable_execution`: 20/20 PASS after repair.
- Current tracked delta before final gate: this work order + `supervised_command_runner.py` + `test_supervised_command_runner.py` only.
- Final CI-equivalent split-process gate on the repaired working tree: GUI 279 PASS; local-instance lifecycle 23 PASS; supervised-command 15 PASS; all 117 remaining core test files PASS in isolated processes; smoke `A-CONDUCTOR_SMOKE_OK`.
- Final compileall, `git diff --check`, exact 3-file scope, strict UTF-8, U+FFFD/triple-question-mark and production added-line secret scans all PASS.
- Candidate is ready to freeze. Next: commit/push exact SHA → detached Git-blob review packet → independent review → PR/CI.