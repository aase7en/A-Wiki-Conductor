# WO-AC-RES-004: Recovery Reconciliation + Repo Identity Gate

Status: in_progress
Lane/files: `src/a_conductor/recovery_reconciliation.py`, `src/a_conductor/__init__.py`, `tests/test_recovery_reconciliation.py`, `docs/contracts/recovery-reconciliation.md`, `AGENTS.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-AC-RES-004-recovery-reconciliation.md`
Branch: main
Model tier: high

## Goal

After transport returns, reconcile the original supervised execution against durable process/result evidence and current repo identity before permitting any next mutation. Never rerun simply because transport disappeared.

## Reuse classification

`WRAP + EXTEND`: reuse AC-RES-002 inspect/collect, AC-RES-003 ownership-gated transport restoration, `StrictReadOnlyGitRunner`, `NativeGitReadAdapter.status_short`, and AC-RES-001 execution state.

## Acceptance

- Reconnect reconciliation first validates durable job/execution worker ownership through AC-RES-003.
- Root/branch/HEAD identity is checked read-only against durable execution identity.
- If original supervisor is alive, mark/retain `PROCESS_STILL_RUNNING` and return MONITOR_ORIGINAL; never relaunch.
- If durable result exists, collect original result; exit 0 yields VERIFY next action, nonzero yields FAILED/REVIEW next action.
- Missing/malformed result after supervisor exit yields `RECOVERY_REQUIRED`; no rerun.
- Wrong root/branch/HEAD blocks recovery before further repo mutation.
- Dirty worktree after result collection blocks automatic continuation; evidence must be reviewed rather than guessed.
- Reconciliation exposes no retry/relaunch/checkout/reset/clean/commit/push API.
- Targeted tests + compileall/diff pass.

## Forbidden

- No blind retry.
- No auto-clean/reset/stash/checkout.
- No automatic failover.
- No Serena-specific reconnect code.
- No mutation of A-Wiki/Phase6 repos.

## Verify

- targeted reconciliation + Git identity tests
- regression AC-RES-002/003
- compileall/diff
- PID 25396 unchanged

## Checkpoint log

- [2026-08-20] Opened from clean AC-RES-003 completion `f9838a5`.

## Micro-step checkpoint

- [x] 004-A fit/reuse inspection: reuse AC-RES-001/002/003 + read-only Git identity/status.
- [x] 004-B coordination + context-window rollover rule captured.
- [ ] 004-C RED recovery/identity tests.
- [ ] 004-D minimal reconciler.
- [ ] 004-E regression/verification.
- [ ] 004-F close + commit.

- [2026-08-20] Resume baseline verified at `f9838a5`; only this WO was untracked before claim.
