# WO-P1-032: Native Git + Verification Adapters

Status: in_progress
Lane/files: `src/a_conductor/native_adapters.py`, `src/a_conductor/__init__.py`, `tests/test_native_adapters.py`, `docs/contracts/native-execution-adapters.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-032-native-git-verification-adapters.md`
Branch: main
Model tier: high

## Goal

Put fixed-method adapters over `NativeSubprocessRunner` so A-Conductor can inspect Git state and run known verification commands without exposing arbitrary model-generated shell strings.

## A-Wiki classification

`EXTEND`, inheriting P1-031. A-Wiki owns routing/policy; A-Conductor owns deterministic execution enforcement.

## Acceptance

- RED tests before implementation.
- Git adapter exposes fixed read-only methods only: status, working-tree diff, cached diff. No add/commit/reset/clean/checkout/stash/rebase/merge/push.
- Git commands always include per-command `safe.directory`, use the bound project root, and place user-supplied paths after `--` with root confinement validation.
- Verification adapter exposes fixed pytest and compileall command shapes only.
- Verification paths are confined, must exist, and cannot be interpreted as options.
- Verification commands declare mutation intent because test/build tooling may create caches/artifacts; read-only project scopes refuse them.
- Adapters return `NativeCommandResult` evidence without persisting raw argv/environment.
- Full suite, compileall, diff/static safety gates pass.

## Forbidden

- No generic `run(command_string)` adapter.
- No Git mutation/network operations.
- No shell=True.
- No A-Wiki repo mutation.
- No tunnel/provider provisioning.

## Verify

- `python -m pytest tests/test_native_adapters.py -q`
- `python -m pytest -q`
- `python -m compileall -q src`
- `git diff --check`

## Checkpoint log

- [2026-08-20] Opened from clean P1-031 commit `24f4e33`.
