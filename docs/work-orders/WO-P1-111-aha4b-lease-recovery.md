# WO-P1-111 ? AHA-4B lease heartbeat + stale-owner recovery

Date: 2026-08-29
Owner: GPT-5.6 Sol integrator
Status: REVIEW_READY ? LOCAL GREEN / PR PENDING
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-aha4b-lease-recovery`
Branch: `feat/wo-p1-111-aha4b-lease-recovery`
Base: `origin/main@b7a2149cb5e40c596ae6934506e1a360263ecc3d`
Parent: Sunday Family Harness Accelerator / AHA-4B

## Goal

Extend the accepted AHA-4A worker lease authority with exact-owner heartbeat, stale evidence, quarantine and reconciliation before reuse. Expiry/heartbeat loss is never retry or release authority by itself.

## Reuse classification

**EXTEND + WRAP** `SQLiteWorkerLeaseStore`, `WorkerLeaseBroker`, canonical repository/worktree identity and accepted resilient-execution recovery invariants. A-Wiki GitHub was inspected read-only; no competing A-Wiki lease/heartbeat implementation was found. Do not create a second scheduler, task lifecycle, retry authority, work-order claim system, or process supervisor.

## Allowed scope

- `src/a_conductor/worker_lease.py`
- `tests/test_worker_lease.py`
- additive `tests/test_worker_lease_recovery.py`
- this work order, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`

## Forbidden scope

- live Worker/tunnel-client mutation or WO-P1-096 operational soak
- A-Wiki repository mutation or claim semantics
- graph scheduler order/priority changes
- execution retry/relaunch authority
- connector recovery, installer, release publication, North Star worktree
- provider credentials/configuration

## Binding invariants

1. Heartbeat is exact lease + session + task owner only and monotonic; wrong owner fails closed.
2. Expiry or missed heartbeat marks ownership stale/uncertain; it never releases or reassigns the lease automatically.
3. A stale mutating lease remains capacity-blocking until deterministic reconciliation proves reuse-safe state.
4. Dirty/unknown repo state, identity mismatch, running/unknown runtime state, or insufficient evidence quarantines the lease and preserves ownership.
5. Reuse-safe release requires an explicit reconciliation classification proving no live mutation authority remains; release is atomic and audited in lease state.
6. Heartbeat/reconciliation races cannot revive a released lease, steal ownership, or release a renewed live lease.
7. Existing AHA-4A retry-safe attachment, mutable-scope conflict, ordered fallback and exact-owner release semantics remain unchanged.
8. No background thread/poll loop. Callers provide observations/clock; this slice is deterministic application state only.
9. Fairness/backpressure remains bounded: stale/quarantined leases stay visible as typed blockers; broker never skips them by stealing the worker. Broad queue scheduling remains GE/AHA-6 authority.
10. Focused race/chaos tests, relevant recovery regression, compileall, diff/scope/secret audit, remote diff audit and exact-head 3-OS CI must pass before merge.

## TDD sequence

1. RED: exact-owner heartbeat API absent; wrong-owner and released-lease heartbeat must fail closed.
2. RED: expired lease is currently indistinguishable from healthy active capacity; add typed lease health without auto-release.
3. RED: stale lease reconciliation must quarantine ambiguous/dirty/running observations and preserve the active lease.
4. GREEN: smallest atomic store fields/API for heartbeat + quarantine + reconciliation evidence.
5. RED/GREEN: explicit safe classification can release stale lease; racing heartbeat/reconcile cannot release a renewed lease.
6. Chaos: crash/disconnect, dirty worktree, branch/HEAD drift, same-owner heartbeat race, stale observation race.
7. Regression + PR/CI/merge loop.

## Initial evidence

- AHA-4A merged via PR #131 as `b7a2149cb5e40c596ae6934506e1a360263ecc3d`.
- post-main CI `33256317010` passed Windows/Ubuntu/macOS; Windows passed build, archive verification, Portable smoke and Frozen Setup install/uninstall E2E.
- local lease + recovery baseline: **47 passed**.
- primary checkout remains protected/dirty only at `assets/donate-promptpay-qr.png`; this isolated worktree is clean.

Next: commit/push this claim, then add failing heartbeat/reconciliation tests before production code.


## Implementation checkpoint ? 2026-08-29

Implemented as a bounded extension of the accepted AHA-4A lease store:
- broker-created leases now carry a bounded TTL, persisted heartbeat timestamp and expiry;
- exact-owner heartbeat is monotonic and cannot revive an expired, released or quarantined lease;
- owner retry on stale/quarantined capacity returns `RECOVERY_REQUIRED`, never fallback/rebind;
- stale capacity stays active and blocks worker/scope reuse until explicit reconciliation;
- canonical `RecoveryClassification` is reused; no second recovery vocabulary or lifecycle was created;
- dirty/unknown/running/identity-drift evidence quarantines the lease while preserving ownership;
- `NO_MUTATION` requires original HEAD identity before safe release; `COMPLETE_VERIFIED` may release a clean/stopped lease after the expected mutation changed HEAD;
- reconciliation observations are monotonic against heartbeat/quarantine/reconciliation evidence, preventing stale replay from releasing newer ownership state;
- direct exact-owner release is now fail-closed after expiry/quarantine and rejects release timestamps older than the latest heartbeat;
- legacy AHA-4A SQLite databases migrate additively, preserving active leases and deriving legacy TTL from stored acquisition/expiry where possible;
- no background poll/thread, subprocess, scheduler, retry loop, live Worker operation or A-Wiki mutation was added.

Review-discovered defects closed before checkpoint:
1. stale reconciliation evidence could replay after a newer heartbeat/quarantine and release a lease; fixed with monotonic evidence authority;
2. inherited AHA-4A `release()` could bypass AHA-4B reconciliation after expiry/quarantine; fixed by requiring recovery for uncertain ownership and preserving only active exact-owner release;
3. a fallback test initially used the same mutable scope on worker 2; canonical overlap correctly blocked it, so the test was corrected to exercise non-overlapping fallback rather than weakening the conflict gate.
4. owner retry could return the stale pre-health lookup snapshot when a heartbeat raced between owner lookup and health inspection; fixed by returning the exact latest lease snapshot from the health read.

Evidence:
- AHA-4A + AHA-4B focused: **69 passed**;
- lease/recovery/domain/job/registry/persistence/graph integration: **247 passed**;
- race stress: heartbeat?reconcile **20/20**, same-worker contention **20/20**, same-owner convergence **20/20**;
- compileall: PASS;
- `git diff --check`: PASS;
- forbidden execution/retry surface scan: clean;
- bounded secret-pattern scan: clean.

Next gate: scope audit -> commit/push -> Draft PR -> exact remote diff audit -> independent review -> exact-head Windows/Ubuntu/macOS CI -> merge only if green.
