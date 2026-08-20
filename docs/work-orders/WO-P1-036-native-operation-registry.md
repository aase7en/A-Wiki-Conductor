# WO-P1-036: Allowlisted Native Operation Registry + Backend

Status: completed
Lane/files: `src/a_conductor/native_operations.py`, `src/a_conductor/__init__.py`, `tests/test_native_operations.py`, `docs/contracts/native-operation-registry.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-036-native-operation-registry.md`
Branch: main
Model tier: high

## Goal

Resolve opaque operation references to a small enum-backed set of fixed native adapter methods and return digest-based evidence to the durable job execution coordinator without exposing an arbitrary argv/shell surface.

## A-Wiki classification

`EXTEND`: A-Wiki chooses/authorizes work at the policy/orchestration layer. A-Conductor resolves already-approved operation IDs to deterministic local execution primitives.

## Initial operation kinds

- `GIT_STATUS`
- `GIT_WORKING_DIFF`
- `GIT_CACHED_DIFF`
- `PYTEST`
- `COMPILEALL`

## Acceptance

- Registry definitions contain operation ref, enum kind, confined path list, timeout only.
- No executable/argv/shell/command field exists in operation definitions.
- Duplicate/unregistered refs are code-only errors.
- Worker adapter resolution is explicit and code-only on missing worker.
- Backend dispatches only to fixed NativeGitReadAdapter / NativeVerificationAdapter methods.
- Success is exit code 0 and not timed out.
- Git read failure recovery classification = `NO_MUTATION`.
- Verification failure/timeout recovery classification = `UNKNOWN` (conservative).
- Evidence ref is a deterministic digest over result metadata/hashes; stdout/stderr text is not embedded.
- End-to-end coordinator + SQLite job store test proves raw command output is not persisted.
- Full suite + compileall + diff/static safety gates pass.

## Forbidden

- No arbitrary argv or shell string.
- No Git mutation operations.
- No filesystem write/delete operations.
- No scheduler/router/model selection.
- No operation registry persistence yet.
- No A-Wiki/GitHub mutation.

## Verify

- `python -m pytest tests/test_native_operations.py -q`
- `python -m pytest -q`
- `python -m compileall -q src`
- `git diff --check`

## Checkpoint log

- [2026-08-20] Opened from clean durable-execution-coordinator baseline `0de7365`.
- [2026-08-20] Contract defined; local claim opened from baseline `0de7365`.
- [2026-08-20] RED missing-module gate captured before implementation.
- [2026-08-20] Targeted registry/backend GREEN: 15/15 including end-to-end digest-only durable evidence.
- [2026-08-20] Full verification: 518 passed; compileall/diff/static API safety passed; active Conductor PID 25396 preserved.
