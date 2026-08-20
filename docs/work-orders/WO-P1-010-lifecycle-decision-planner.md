# WO-P1-010: Pure Runtime Lifecycle Decision Planner

Status: in_progress
Lane/files: `src/a_conductor/lifecycle.py`, `src/a_conductor/__init__.py`, `tests/test_lifecycle.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-010-lifecycle-decision-planner.md`
Branch: main
Model tier: mid

## Goal + Acceptance criteria

Define deterministic, side-effect-free decisions for `START`, `STOP`, `RESTART`, and `RELEASE` before any lifecycle executor is allowed to mutate processes or runtime files.

Acceptance:
- tests written before implementation;
- output decision is one of `PROCEED`, `NOOP`, `REFUSE`, `RECOVERY_REQUIRED`;
- planner consumes existing ownership/collision/assignment/worker-state facts only;
- START refuses missing assignment/project, worktree/tunnel/port collision, PID mismatch/unknown; stale/inconsistent resources require recovery; already healthy owned runtime becomes NOOP;
- STOP is targeted-policy only: absent -> NOOP, stale -> recovery, mismatch/unknown -> refuse, owned -> proceed;
- RESTART never means blind kill+start; ownership must be known and assignment/project valid;
- RELEASE requires no active task and stopped/reconciled runtime; already free -> NOOP;
- output contains symbolic lifecycle steps only, never commands;
- no process/filesystem/network/persistence I/O;
- full tests, compileall, I/O scan, and `git diff --check` pass.

## Reference pattern

- `docs/contracts/serena-runtime-manager.md` sections 7-10.
- `src/a_conductor/runtime_safety.py`.
- `src/a_conductor/worker_status.py`.
- `src/a_conductor/registry.py`.

## Steps

1. Write failing lifecycle-policy tests.
2. Capture RED result.
3. Implement immutable context/plan types + pure planner.
4. Run tests to GREEN.
5. Review planner for blind retry/stop/release paths.
6. Update checkpoint/current-work/handoff and commit.

## Forbidden

- No subprocess/shell/PowerShell/network/filesystem/persistence calls.
- No target process start/stop/kill/restart.
- No PID cleanup/profile rendering.
- No A-Wiki/Phase6 mutation.
- No Git remote/push.

## Verify commands

- `python -m pytest tests -q --basetemp=runtime/pytest-temp`
- `python -m compileall -q src`
- `git diff --check`
- source scan for I/O/mutation imports/primitives.

## Checkpoint log

- [2026-08-20] ChatGPT/Sunday-Conducter: opened after SQLite registry persistence commit `f32f192`. This is the final pure policy layer before a future lifecycle executor can mutate target runtime state.
