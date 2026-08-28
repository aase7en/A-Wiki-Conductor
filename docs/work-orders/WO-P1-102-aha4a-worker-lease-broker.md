# WO-P1-102 — AHA-4A worker lease broker + automatic fallback

Date: 2026-08-28
Owner: GPT-5.6 Sol integrator
Status: ACTIVE — CLAIM / DESIGN LOCK
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-aha4a-lease`
Branch: `feat/wo-p1-102-aha4a-worker-lease-broker`
Base: `origin/main@08369ade59206cbe2bc80a314d49d3daa50038b7`
Parent: Sunday Family Harness Accelerator / AHA-4A

## Goal

Add atomic worker leasing, injected eligibility preflight, and ordered automatic fallback so callers request eligible execution capacity instead of stealing or hard-coding a busy worker. This is runtime coordination in A-Sunday Conductor; A-Wiki work-order claims remain a separate brain/governance authority.

## Reuse classification

**EXTEND + WRAP** existing `ControlPlaneRegistry`, GE-6 worker/scheduler facts, `windows_worktree_key`, and GE conflict semantics. No second scheduler, task store, job lifecycle, dispatch system, retry loop, or A-Wiki claim system.

## Allowed scope

- new `src/a_conductor/worker_lease.py`
- new `tests/test_worker_lease.py`
- this work order, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`
- only if deterministic integration proves necessary: one additive scheduler/dispatch adapter file + focused test, recorded before mutation

## Forbidden scope

- A-Wiki repository mutation or duplicate work-order/claim semantics
- graph scheduling order/priority/conflict policy changes
- AHA-4B heartbeat/expiry reclamation/quarantine/fairness/backpressure
- connector recovery / PR #125 / live tunnel fleet
- installer PR #108
- North Star branch
- provider DB/gateway/live credentials
- broad parallel execution (AHA-6)

## Contract

`ordered candidates -> deterministic preflight -> atomic SQLite lease attempt -> next candidate on contention -> typed RDC fallback or WAIT`.

A lease carries: lease/worker/session/task/project identity, runtime, worktree/branch/expected HEAD, allowed+forbidden scope, mutation intent, acquisition timestamp, and future expiry metadata. AHA-4A never reclaims an expired/stale lease automatically; AHA-4B owns heartbeat/expiry recovery.

## Acceptance

1. Two independent brokers racing for one worker produce one lease winner; the loser never steals it.
2. Loser automatically tries the next eligible ordered candidate.
3. Active task/lease, non-READY/reserved worker, capability/runtime/project/worktree/branch/HEAD mismatch, stale health, unknown ownership/dirty state, unauthorized mutation, and overlapping mutable scope are skipped with typed reasons.
4. Mutating work fails closed unless the candidate is known clean and exact identity matches.
5. Read-only RDC fallback is returned only when explicitly eligible; mutating work never silently falls to RDC.
6. Equivalent eligible workers fall back in stable caller-provided order; no random rebinding.
7. Releasing a lease is exact-owner only and idempotent for the same lease identity.
8. Lease persistence is atomic under SQLite `BEGIN IMMEDIATE` / unique active-worker constraint or an equivalent deterministic CAS.
9. A losing contention path does not mutate registry assignment, task state, or another lease.
10. Deterministic race/fallback tests, focused+broad regression, compileall, diff/scope audit, remote diff audit, and exact-head 3-OS CI pass before merge.

## First TDD sequence

1. RED: two independent store connections race to lease one worker; exactly one wins.
2. GREEN: smallest atomic lease store + immutable lease/request/result vocabulary.
3. RED/GREEN: first candidate busy -> second eligible candidate selected deterministically.
4. RED/GREEN: dirty/unknown/identity/scope failures are typed and fail closed.
5. RED/GREEN: read-only RDC fallback is explicit; mutation returns WAIT when no worker is safe.
6. Add exact-owner release + persistence reload tests.
7. Run regression/audit/PR loop.

## Safety gate

`SAFE_TO_MUTATE = YES` only after the WO-P1-102 claim is committed/pushed from this isolated worktree and `origin/main` remains non-overlapping.
