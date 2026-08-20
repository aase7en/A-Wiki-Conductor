# WO-AC-RES-005: Duplicate Execution Protection

Status: in_progress
Lane/files: `src/a_conductor/execution_deduplication.py`, `src/a_conductor/execution_store.py`, `src/a_conductor/__init__.py`, `tests/test_execution_deduplication.py`, `tests/test_execution_store.py`, `docs/contracts/duplicate-execution-protection.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-AC-RES-005-duplicate-execution-protection.md`
Branch: main
Model tier: high

## Goal

Prevent an equivalent substantial execution from being launched twice merely because the requesting transport/session repeated a request. Compute canonical fingerprints, find durable matches, and classify whether the caller must attach/monitor, reuse completed evidence, launch because no prior equivalent exists, or stop for unknown/partial provenance.

## Reuse classification

`EXTEND`: reuse AC-RES-001 durable execution records/state and SQLite store. This slice is a decision/lookup layer only; AC-RES-002 remains the launch engine.

## Acceptance

- Canonical fingerprint is derived from bounded execution identity + normalized argv in memory; argv is not persisted by this component.
- Equivalent fingerprint generation is deterministic across repeated calls.
- SQLite store can read records by fingerprint newest-first without mutation.
- Live equivalent states return `ATTACH_RUNNING`; no new launch is requested.
- Completed/verification/failure result states return `REUSE_COMPLETED`; duplicate request does not rerun automatically.
- Partial/unknown/recovery/cancelled states return `BLOCKED_UNKNOWN`.
- No equivalent record returns `SAFE_TO_LAUNCH`.
- Exact durable identity fields are rechecked even after fingerprint match; hash alone is not authority.
- No launch/retry/process/Git/network mutation API is exposed.
- Targeted/regression + compileall/diff/schema safety gates pass.

## Micro-steps

- [x] 005-A fit analysis: fingerprint exists in record but builder/query/decision layer are absent.
- [x] 005-B coordination + contract checkpoint.
- [ ] 005-C RED fingerprint/store lookup/decision tests.
- [ ] 005-D minimal implementation.
- [ ] 005-E regression + safety verification.
- [ ] 005-F close/commit.

## Forbidden

- No process launch or retry.
- No automatic failover/routing.
- No persisted raw argv/environment/prompt.
- No fingerprint-only trust without identity recheck.
- No A-Wiki/Phase6 mutation.

## Verify

- targeted duplicate-protection/store tests
- AC-RES-001..005 focused regression
- compileall/diff/schema safety
- PID 25396 unchanged

## Checkpoint log

- [2026-08-20] Opened from clean AC-RES-004 completion `bb5dab0`.
