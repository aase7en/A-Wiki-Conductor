# WO-P1-003: Pure Runtime Safety Validators

Status: done
Lane/files: `src/a_conductor/runtime_safety.py`, `src/a_conductor/__init__.py`, `tests/test_runtime_safety.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-003-runtime-safety-validators.md`
Branch: main
Model tier: mid

## Goal + Acceptance criteria

Implement deterministic, side-effect-free safety classification for runtime ownership/collision checks before any real process supervision exists.

Acceptance:
- tests written before implementation;
- classify PID/process ownership as `ABSENT`, `OWNED`, `STALE`, `MISMATCH`, or `UNKNOWN`;
- classify health-port binding as free/self-owned/collision/unknown;
- classify tunnel/profile binding as free/self-owned/collision;
- classify exact worktree mutating assignment as available/self-owned/conflict;
- pure functions only; no OS/process/network/filesystem mutation;
- no product/provider names hard-coded in core safety logic;
- `pytest`, `compileall`, and `git diff --check` pass.

## Reference pattern

- `docs/contracts/serena-runtime-manager.md` sections 6-12.
- `docs/contracts/core-domain.md` invariants INV-005, INV-006, INV-015.

## Steps

1. Write failing tests for ownership/collision classifications.
2. Capture RED result.
3. Implement minimal enums/dataclasses/functions.
4. Run tests to GREEN.
5. Review that module imports no subprocess/socket/network/process APIs.
6. Update checkpoint/current-work/handoff and commit.

## Forbidden

- No `subprocess`, `os.kill`, PowerShell, shell, socket, HTTP, tunnel, or Serena calls.
- No process start/stop/restart.
- No filesystem writes from runtime-safety functions.
- No SQLite/broker/UI/provider integration.
- No A-Wiki/Phase6 mutation.
- No Git remote/push.

## Verify commands

- `pytest -q`
- `python -m compileall -q src`
- `git diff --check`
- import scan for forbidden side-effect modules/APIs.

## Checkpoint log

- [2026-08-20] ChatGPT/Sunday-Conducter: opened after runtime-manager contract commit `2b2ecbd`. Scope is pure deterministic classification only.
- [2026-08-20] RED checkpoint: `pytest -q` failed during collection with `ModuleNotFoundError: a_conductor.runtime_safety` as expected; no runtime-safety implementation existed yet.
- [2026-08-20] GREEN checkpoint: implemented pure side-effect-free ownership/collision classifiers in `src/a_conductor/runtime_safety.py`. Verification: `pytest -q` = 41 passed; `compileall` PASS; `git diff --check` PASS; forbidden process/network/provider import/product scan clean. No process, tunnel, network, filesystem mutation, broker, or UI behavior added.
