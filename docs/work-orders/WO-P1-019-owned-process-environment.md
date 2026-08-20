# WO-P1-019: Owned-Process Environment Isolation

Status: in_progress
Lane/files: `src/a_conductor/owned_process.py`, `src/a_conductor/serena_materializer.py`, `src/a_conductor/__init__.py`, `tests/test_owned_process.py`, `tests/test_serena_materializer.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-019-owned-process-environment.md`
Branch: main
Model tier: high

## Goal

Add explicit, allowlisted child-process environment isolation needed for per-worker `SERENA_HOME`, without permitting arbitrary environment overrides or silently inheriting the entire parent environment.

## Acceptance

- tests first / RED before implementation;
- `OwnedProcessSpec` supports immutable environment overrides;
- only `SERENA_HOME` is allowed as an A-Conductor override in this phase;
- duplicate/blank/NUL/unknown environment keys/values are rejected;
- `SERENA_HOME` must resolve under the process `allowed_root`;
- Windows spawner builds a fresh child environment from a documented safe inherited-key allowlist plus explicit overrides;
- parent-only secret-like variables are not forwarded by default;
- safe inherited keys preserve original case/value when supplied;
- Popen still uses direct argv + `shell=False`;
- Serena materializer emits `SERENA_HOME` override into `OwnedProcessSpec`;
- real integration remains dummy-process only; no live Serena/tunnel/A-Worker 3 mutation;
- full suite + compileall + diff/static review pass.

## Forbidden

- No arbitrary user-provided environment key injection.
- No raw whole-parent `os.environ` pass-through.
- No secret values in errors/logs.
- No live worker mutation.
- No Git remote/push.

## Checkpoint log

- [2026-08-20] Opened after P1-018 commit `7a42bfd`; worktree clean.
