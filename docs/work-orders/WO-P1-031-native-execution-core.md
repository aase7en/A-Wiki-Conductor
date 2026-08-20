# WO-P1-031: Native Execution Core

Status: in_progress
Lane/files: `src/a_conductor/native_execution.py`, `src/a_conductor/__init__.py`, `tests/test_native_execution.py`, `docs/contracts/native-execution-core.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-031-native-execution-core.md`
Branch: main
Model tier: high

## Goal

Add the first bounded deterministic Native Execution Layer for A-Conductor: project-root-confined text filesystem primitives and an authorized `shell=False` subprocess primitive with timeout, safe environment handling, bounded captured output, and code-only failures. This is execution infrastructure, not a second A-Wiki orchestrator and not a generic LLM shell.

## A-Wiki reuse-before-build classification

`EXTEND`. A-Wiki owns orchestration/routing/policy and contains shell wrappers that invoke tools, but no authoritative general native execution runtime was found in the reviewed `AGENTS.md`, `docs/protocols/**`, and `skills/awiki/**` surfaces. A-Conductor therefore owns deterministic runtime enforcement while consuming A-Wiki policy.

## Acceptance

- RED tests precede implementation.
- Every filesystem path is relative to an explicitly configured project root and rejects absolute/traversal/symlink escape.
- Read/list operations are bounded and deterministic.
- Writes require mutation authority, are atomic, and existing-file overwrite requires an expected SHA-256 precondition.
- No delete/move/recursive mutation primitive in this work order.
- Subprocess execution accepts argv sequences only, always uses `shell=False`, requires an explicit allowed-executable policy, confined existing cwd, bounded timeout, conservative inherited environment, and only explicitly allowed environment overrides.
- Command result captures exit/timed-out state plus bounded stdout/stderr and SHA-256 digests; raw command arguments are not persisted by this primitive.
- Generic native subprocess primitive is not directly exposed to an LLM; future adapters/policy gates construct authorized command specs.
- Existing tests remain green; compileall and diff check pass.

## Forbidden

- No shell string execution / `shell=True`.
- No command auto-approval based on model output.
- No delete/clean/reset/checkout/stash/rebase/merge/force-push capability.
- No network/provider/tunnel provisioning.
- No secret persistence or raw env dump.
- No changes to A-Wiki repo.

## Verify commands

- `python -m pytest tests/test_native_execution.py -q`
- `python -m pytest -q`
- `python -m compileall -q src`
- `git diff --check`

## Checkpoint log

- [2026-08-20] Opened from clean `main` at `ce00f13`; A-Wiki reuse gate classified this slice as `EXTEND`.
