# WO-AC-RES-006: Output Backpressure + Durable Reports

Status: in_progress
Lane/files: `src/a_conductor/execution_artifacts.py`, `src/a_conductor/__init__.py`, `tests/test_execution_artifacts.py`, `docs/contracts/output-backpressure.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-AC-RES-006-output-backpressure.md`
Branch: main
Model tier: high

## Goal

Expose complete AC-RES-002 durable stdout/stderr/report evidence through bounded local read/tail/chunk/summary APIs so transports never need to carry unbounded command output.

## Reuse classification

`WRAP + EXTEND`: AC-RES-002 remains owner of durable log creation. This slice reads only refs already present in `DurableExecutionRecord`; it does not redirect/spawn/log processes itself.

## Acceptance

- Only enum-selected durable `stdout_ref`, `stderr_ref`, or `report_ref` can be read; caller cannot supply arbitrary filesystem path.
- Artifact refs are re-resolved under durable repo root and run directory; traversal/symlink escape is blocked.
- Tail and chunk reads enforce a hard maximum byte budget.
- Full file SHA-256 and total byte size are available as evidence without returning full content.
- Missing/unconfigured artifacts return explicit error codes.
- UTF-8 decode uses replacement for invalid bytes without crashing.
- Pytest summary parser can report passed/failed/skipped/warnings/duration from bounded tail when present.
- No process/network/Git/filesystem mutation API.
- Regression + compileall/diff + PID gates pass.

## Micro-steps

- [x] 006-A fit analysis: reuse AC-RES-002 durable stdout/stderr/report refs; no second logger.
- [x] 006-B coordination + contract checkpoint.
- [ ] 006-C RED artifact confinement/backpressure/summary tests.
- [ ] 006-D minimal bounded reader implementation.
- [ ] 006-E regression + safety verification.
- [ ] 006-F close/commit.

## Forbidden

- No process launch/retry.
- No arbitrary path read API.
- No unbounded file read returned to caller.
- No log deletion/truncation/rotation mutation yet.
- No network/Telegram/Discord transport implementation.

## Verify

- targeted artifact tests
- AC-RES-001..006 focused regression
- compileall/diff/static read-only scan
- PID 25396 unchanged

## Checkpoint log

- [2026-08-20] Opened from clean AC-RES-005 completion `a0a2e52`.
