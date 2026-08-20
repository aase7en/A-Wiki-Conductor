# WO-P1-005: Read-Only Windows Runtime Observation Adapter

Status: in_progress
Lane/files: `src/a_conductor/windows_observer.py`, `src/a_conductor/__init__.py`, `tests/test_windows_observer.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-005-windows-runtime-observation.md`
Branch: main
Model tier: mid

## Goal + Acceptance criteria

Implement a bounded **read-only** Windows observation adapter that collects process/PID-file/health-port/readyz facts for Serena-backed workers and feeds existing pure safety classifiers. No lifecycle mutation is allowed.

Acceptance:
- tests written before implementation;
- command execution is injected behind a small interface so tests do not execute PowerShell;
- PID-file observation is read-only and distinguishes absent/invalid/stale facts without deleting files;
- process observation obtains executable/profile facts without exposing full command lines in public result objects;
- health-port observation returns listening + owning PID facts;
- readiness probe is bounded and read-only;
- dynamic PID/port values are validated as integers before command construction;
- no start/stop/kill/restart/remove/write operations exist in this module;
- `pytest`, `compileall`, forbidden-mutation scan, and `git diff --check` pass.

## Reference pattern

- `docs/contracts/serena-runtime-manager.md` sections 6-13.
- `src/a_conductor/runtime_safety.py` — classifiers consume observations but do no I/O.
- validated prototype status/start/stop scripts — read-only evidence only.

## Steps

1. Write failing tests for parsing/observation boundaries and injected command runner.
2. Capture RED result.
3. Implement minimal read-only observer.
4. Run tests to GREEN.
5. Review commands for injection/mutation risks and redaction behavior.
6. Update checkpoint/current-work/handoff and commit.

## Forbidden

- No process start/stop/kill/restart.
- No `Remove-Item`, file deletion, PID-file cleanup, runtime-profile writes, or tunnel provisioning.
- No credential decryption/access.
- No broad process enumeration beyond the exact PID/port observation needed.
- No A-Wiki/Phase6 mutation.
- No Git remote/push.

## Verify commands

- `pytest -q`
- `python -m compileall -q src`
- `git diff --check`
- scan observer source for mutation primitives (`Stop-Process`, `Start-Process`, `taskkill`, `Remove-Item`, `os.kill`, write/delete APIs).

## Checkpoint log

- [2026-08-20] ChatGPT/Sunday-Conducter: opened after reusable Serena worker-profile commit `4e36681`. Scope is read-only observation only; lifecycle mutation remains forbidden.
