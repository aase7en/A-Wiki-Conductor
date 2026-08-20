# WO-P1-037: Native Worker Adapter Assembly

Status: in_progress
Lane/files: `src/a_conductor/native_operation_assembly.py`, `src/a_conductor/__init__.py`, `tests/test_native_operation_assembly.py`, `docs/contracts/native-worker-adapter-assembly.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-037-native-worker-adapter-assembly.md`
Branch: main
Model tier: high

## Goal

Resolve a worker's current Control Center assignment into a fresh confined NativeExecutionScope and fixed Git/verification adapters for the allowlisted native operation backend.

## Acceptance

- Reads fresh Control Center snapshot on every resolve; no stale assignment cache.
- Unknown/unassigned worker fails code-only; no fallback worker/project.
- Exact assigned `project_root_path` becomes NativeExecutionScope root.
- `mutation_allowed` is copied exactly from current assignment.
- Allowed executables are only configured Git + Python executable names.
- No environment override authority by default.
- Missing/non-directory project root fails before adapter construction.
- Reassignment is reflected on the next resolve.
- Default assembly produces NativeGitReadAdapter + NativeVerificationAdapter only; no Git mutation adapter.
- Adapter factories are injectable for deterministic tests but receive only the validated scope.
- Full suite + compileall + diff/static safety gates pass.

## Forbidden

- No worker lifecycle/process/tunnel mutation.
- No project registration/assignment mutation.
- No scheduler/router/planner/model selection.
- No generic command runner surface.
- No A-Wiki/GitHub mutation.

## Verify

- `python -m pytest tests/test_native_operation_assembly.py -q`
- `python -m pytest -q`
- `python -m compileall -q src`
- `git diff --check`

## Checkpoint log

- [2026-08-20] Opened from clean allowlisted-operation-backend baseline `50bc4c7`.
- [2026-08-20] Contract defined; local claim opened from baseline `50bc4c7`.
