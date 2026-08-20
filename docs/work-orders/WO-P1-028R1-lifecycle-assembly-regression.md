# WO-P1-028R1: Lifecycle Assembly Contract Regression Repair

Status: completed
Lane/files: `src/a_conductor/lifecycle_assembly.py`, `tests/test_lifecycle_assembly.py`, `docs/work-orders/WO-P1-028R1-lifecycle-assembly-regression.md`
Branch: main
Model tier: high

## Goal

Repair two internally inconsistent behaviors introduced together in `e5405ca` and exposed by the P1-030 full-suite gate.

## Acceptance

- `LocalLifecycleContextProvider` calls `classify_worktree_binding` using its current `worktree_key` contract.
- assignment clear success test passes the actual project ID.
- wrong project ID is explicitly tested and remains `ASSIGNMENT_IDENTITY_MISMATCH` + recovery-required.
- targeted `tests/test_lifecycle_assembly.py` passes.
- no P1-030 source/test files are staged in this repair commit.

## Forbidden

- No behavior weakening of assignment identity safety.
- No changes to process/tunnel lifecycle.
- No reset/clean/stash/checkout/switch.
- No remote/push.

## Checkpoint log

- [2026-08-20] Opened after P1-030 full suite exposed 4 baseline failures from `e5405ca`; repair scope proven to two contract mismatches.
- [2026-08-20] Targeted verification: `tests/test_lifecycle_assembly.py` = 8 passed.
