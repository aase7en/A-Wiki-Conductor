# WO-P1-013: Lifecycle Resume Planner from Durable Journal

Status: done
Lane/files: `src/a_conductor/lifecycle_recovery.py`, `src/a_conductor/__init__.py`, `tests/test_lifecycle_recovery.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-013-lifecycle-resume-planner.md`
Branch: main
Model tier: mid

## Goal + Acceptance criteria

Implement a pure lifecycle-specific recovery/resume planner that validates durable journal checkpoints as an exact prefix of an approved lifecycle plan and returns the next safe symbolic step only after external reconciliation says observed state is consistent with that journal.

Acceptance:
- tests written before implementation;
- lifecycle-specific assessment vocabulary: `CONSISTENT_WITH_JOURNAL`, `MUTATION_AHEAD_OF_JOURNAL`, `UNEXPECTED_DRIFT`, `UNKNOWN`;
- recovery planner accepts explicit transaction ID, approved `LifecyclePlan`, checkpoint tuple, and reconciliation assessment;
- checkpoints must use one transaction ID, contiguous sequence numbers from 1, matching action, and exact step-prefix order;
- structural mismatch -> `REFUSE`;
- `UNKNOWN` or `MUTATION_AHEAD_OF_JOURNAL` -> `RECOVERY_REQUIRED`, never resume;
- `UNEXPECTED_DRIFT` -> `REFUSE`;
- consistent empty/prefix journal -> `RESUME` with remaining symbolic steps;
- consistent complete journal -> `COMPLETE`;
- non-PROCEED lifecycle plan is not resumable;
- no I/O/process/network/persistence behavior;
- full tests, compileall, I/O scan, and `git diff --check` pass.

## Reference pattern

- `src/a_conductor/lifecycle.py` approved symbolic plans.
- `src/a_conductor/lifecycle_executor.py` transaction/checkpoint semantics.
- `src/a_conductor/lifecycle_journal.py` append-only ordered journal.
- continuity rule: do not repeat a vanished worker's mutation until actual state is reconciled.

## Steps

1. Write failing structural/reconciliation/resume tests.
2. Capture RED result.
3. Implement immutable assessment/result types + pure planner.
4. Run targeted then full tests to GREEN.
5. Review that uncertain/ahead/drift states never return RESUME.
6. Update checkpoint/current-work/handoff and commit.

## Forbidden

- No observer/process/network/filesystem/SQLite calls.
- No lifecycle execution or mutation.
- No repository-recovery classification reuse that blurs lifecycle semantics.
- No A-Wiki/Phase6 mutation.
- No Git remote/push.

## Verify commands

- `python -m pytest tests -q --basetemp=runtime/pytest-temp`
- `python -m compileall -q src`
- `git diff --check`
- source scan for I/O/mutation imports.

## Checkpoint log

- [2026-08-20] ChatGPT/Sunday-Conducter: opened after append-only lifecycle journal commit `2997072`. Recovery vocabulary is intentionally lifecycle-specific rather than reusing repository mutation classifications.

- [2026-08-20] RED checkpoint: `src/a_conductor/lifecycle_recovery.py` confirmed absent; targeted recovery tests failed during collection with `ModuleNotFoundError: a_conductor.lifecycle_recovery` as expected.

- [2026-08-20] GREEN checkpoint: implemented pure lifecycle-specific recovery/resume planner validating exact transaction/action/sequence/step prefix plus external reconciliation assessment. Targeted tests 17 passed; full suite 233 passed; compileall PASS; `git diff --check` PASS; I/O/mutation scan clean. `RESUME` is possible only for `CONSISTENT_WITH_JOURNAL`; mutation-ahead/unknown require recovery and drift refuses execution. No machine inspection or mutation added.
