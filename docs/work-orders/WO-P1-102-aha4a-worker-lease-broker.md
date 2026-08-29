# WO-P1-102 — AHA-4A worker lease broker + automatic fallback

Date: 2026-08-28
Owner: GPT-5.6 Sol integrator
Status: REVIEW_READY — RETRY/SCOPE HARDENING GREEN / PR #131
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-aha4a-lease`
Branch: `feat/wo-p1-102-aha4a-worker-lease-broker`
Base/reconciled main: `origin/main@39f0253cc4f8896cffa78b6772ce6ffd2e229736`
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

## Implementation checkpoint — 2026-08-28

Implemented in new `worker_lease.py` only:
- immutable request/candidate/lease/outcome + typed rejection vocabulary;
- atomic SQLite active-worker lease constraint across independent connections;
- atomic mutable-scope conflict check using canonical GE `write_sets_overlap`;
- deterministic caller-ordered candidate fallback;
- fail-closed health/ownership/dirty/identity/capability/mutation preflight;
- exact-owner idempotent release; expiry metadata is recorded but never auto-reclaimed in AHA-4A;
- explicit RDC fallback only for eligible read-only requests.

TDD/evidence:
- initial RED: `ModuleNotFoundError: a_conductor.worker_lease`;
- race RED: two different workers could both lease overlapping mutable scope; fixed under one `BEGIN IMMEDIATE` transaction;
- focused: **29 passed**;
- focused race suite repeated **10/10 PASS**;
- registry/persistence/graph/job + lease regression: **140 passed**;
- `python -m compileall -q src/a_conductor`: PASS;
- `git diff --check`: PASS;
- forbidden-import + bounded real-secret-prefix scan: PASS.

Deep-review checkpoint — 2026-08-29:
- RED found `allowed_scope` was not an authority: wider mutable scope could escape the task contract. Fixed with conservative fail-closed scope authorization; literal paths may be covered by an allowed glob, while unproven wider globs are rejected.
- RED found uncertain-delivery retry could allocate a second worker for the same `session_id/task_id`. Added atomic active owner/task uniqueness, idempotent attach, and `LEASE_REQUEST_CONFLICT` on contract drift.
- required capabilities are persisted and checked on retry; concurrent same-owner requests converge on one lease.
- post-reconcile focused **35 passed**; relevant registry/persistence/graph/job/lease regression **145 passed**; compileall/diff-check PASS.
- resume RED found outcome classification was incomplete: a concurrent same-owner loser could atomically attach the existing lease but broker still labeled both outcomes `LEASED`. Added explicit `EXISTING`;
- independent RED then proved lease-ID comparison was not a reliable created/existing authority when concurrent brokers proposed the same lease ID. Added atomic `LeaseStoreAcquireResult.created`; broker classification now consumes store transaction truth, while public `try_acquire()` remains backward-compatible. Same proposed lease ID race is covered deterministically; focused **36 passed**, broad registry/persistence/graph/job/lease regression **220 passed**, race repeat **10/10 PASS**, compileall/diff-check PASS.
- these review-discovered defects remain recorded here because `DEFECT_LESSONS.md` policy is for user-reported defects.

Post-main reconciliation: merged accepted `origin/main@39f0253cc4f8896cffa78b6772ce6ffd2e229736` without rebase/conflict. Focused **35 passed**, relevant broad regression **219 passed**, compileall/diff-check PASS.

Next gate: push reconciled head -> update/audit PR #131 exact remote diff -> independent read-only review -> exact-head Windows/Ubuntu/macOS CI -> merge only if green.
