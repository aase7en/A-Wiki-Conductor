# WO-P1-019: Owned-Process Environment Isolation

Status: completed
Lane/files: `src/a_conductor/owned_process.py`, `src/a_conductor/serena_materializer.py`, `src/a_conductor/__init__.py`, `tests/test_owned_process.py`, `tests/test_serena_materializer.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-019-owned-process-environment.md`
Branch: main
Model tier: high

## Goal

Add explicit, allowlisted child-process environment isolation needed for per-worker `SERENA_HOME`, without permitting arbitrary environment overrides or silently inheriting the entire parent environment.

## Acceptance evidence

- RED: 8 expected failures because `OwnedProcessSpec` had no `environment_overrides` and materializer did not emit them.
- `environment_overrides` is immutable tuple metadata on `OwnedProcessSpec`.
- Only `SERENA_HOME` is accepted in this phase; duplicate/unknown/blank/NUL values are rejected.
- `SERENA_HOME` is resolved and confined under `allowed_root`.
- `WindowsProcessSpawner` builds a fresh environment from a safe inherited-key allowlist plus explicit overrides.
- Parent-only secret-like variables are not forwarded by default; tests explicitly exclude `OPENAI_API_KEY` and `CUSTOM_SECRET` from child env.
- Safe inherited key spelling/value is preserved.
- `Popen` remains direct argv + `shell=False`.
- Serena materializer emits `(("SERENA_HOME", <isolated path>),)`.
- Targeted tests: `42 passed`.
- Full suite: `300 passed in 4.20s`.
- `compileall`: PASS.
- `git diff --check`: PASS.
- Atomic active-worker preservation: Sunday-Conducter PID `25396` before/after full suite.
- No live Serena/tunnel/A-Worker 3 mutation.

## Checkpoint log

- [2026-08-20] Opened after P1-018 commit `7a42bfd`.
- [2026-08-20] Coordination commit `e8c401a`.
- [2026-08-20] RED environment-contract checkpoint captured.
- [2026-08-20] GREEN targeted 42/42; full suite 300/300; active worker preserved. Work order complete.
