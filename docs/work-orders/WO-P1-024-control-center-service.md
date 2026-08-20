# WO-P1-024: Control Center Application Service

Status: completed
Lane/files: `src/a_conductor/control_center.py`, `src/a_conductor/__init__.py`, `tests/test_control_center.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-024-control-center-service.md`
Branch: main
Model tier: mid/high

## Goal

Create the local application-service/facade used by the desktop Projects/Workers screen. It owns registry/persistence transactions and immutable UI projections, but not process lifecycle execution.

## Acceptance evidence

- RED: module missing before implementation.
- Fresh store bootstraps exactly `a-worker-01..03` / `A-Worker 1..3` once.
- Reopen preserves projects/workers/assignments.
- Project registration verifies existing directory read-only and never initializes Git.
- Stable generated project IDs derive from normalized path; duplicate root returns existing project.
- Assignment/release uses existing registry collision/busy rules and persists after success.
- Persistence save failure reloads last durable registry state and raises `PERSISTENCE_FAILED`.
- Immutable `ControlCenterSnapshot` projects worker assignment/project/path/state for UI.
- Targeted tests: `10 passed`.
- Full suite: `353 passed in 5.46s`.
- `compileall`: PASS.
- `git diff --check`: PASS.
- Static scan: no subprocess/Git/network mutation primitives.
- Classification: `NEW` local UI/application facade; it does not replace or duplicate A-Wiki task/work-order/claim coordination.

## Checkpoint log

- [2026-08-20] Opened after Stage B gate checkpoint `bef2d66`.
- [2026-08-20] Coordination commit `b322655`.
- [2026-08-20] RED module-missing checkpoint.
- [2026-08-20] GREEN targeted 10/10, full 353/353. Complete.
