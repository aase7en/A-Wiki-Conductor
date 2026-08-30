# WO-P1-113 — AHA-6 parallel READY-task execution

Date: 2026-08-30
Owner: GPT-5.6 Sol integrator
Status: ACTIVE / IMPLEMENTED / REVIEW_PENDING
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-aha6-parallel`
Branch: `feat/wo-p1-113-aha6-parallel-ready`
Base: `origin/main@64b6ef839f16a270295fb2c24649d01e0f54d862`
Parent: Sunday Family Harness Accelerator / AHA-6

## Goal

Prove fixed-pool parallel execution of two independent READY task packets without
creating a second scheduler, claim/lease system, task store, lifecycle or retry loop.
Each selected task must retain exact worktree/HEAD/scope authority, acquire a compatible
AHA-4B worker lease, and begin execution concurrently only while provider capacity and
quota evidence permit it. Uncertainty becomes reconcile/wait, never blind replay.

## Reuse classification

- **REUSE** `graph.scheduler.schedule_once()` / `SchedulePlan` as READY-selection authority.
- **REUSE** AHA-4A/4B `WorkerLeaseBroker` + SQLite lease recovery/quarantine authority.
- **REUSE** GE-7 durable job/graph-dispatch lifecycle for production execution.
- **REUSE** AHA-5 `HarnessDispatch`, `TaskPacketFile`, result/apply/repair contract.
- **REUSE** provider `max_concurrency`, `ProviderObservation`, `QuotaSnapshot`, freshness gate.
- **EXTEND** only a thin parallel batch coordination seam over those accepted contracts.

## Lane / repository safety contract

Allowed implementation scope:
- `src/a_conductor/parallel_ready_execution.py` (new thin integration seam only);
- `tests/test_parallel_ready_execution.py`;
- this work order and bounded coordination checkpoints in `COLLAB.md`, `CURRENT-WORK.md`,
  `handoff.md`, `docs/agent-collab/AGENT_TASKS.md`;
- user-requested AHA-6 governance extension: `docs/agent-collab/COLLAB_PROTOCOL.md`,
  `docs/agent-collab/CAPABILITY_MATRIX.md`, and `DEFECT_LESSONS.md` only for
  multi-agent loop/bridge rules, routing evidence, and reusable defects found in this slice.

Forbidden without a new explicit gate/claim:
- edits to `graph/scheduler.py`, `graph/dispatch.py`, `worker_lease.py`, durable job stores;
- provider credential values or copies of `L:\My Drive\A-Wiki-Data\.env`;
- installer/release, tunnel-client, North-Star, UI, QR and unrelated worktree scopes;
- new scheduler/router/task-store/retry/claim/lease implementations;
- rebind/reset/clean/stash/rebase/force-push of any existing worktree.

Repository gate at claim:
- remote/base main: `64b6ef839f16a270295fb2c24649d01e0f54d862`;
- GitHub open PRs: 0;
- A-Wiki live local claims: 0;
- root checkout remains protected/dirty and is outside mutation scope;
- existing dirty worktrees showed no overlap with this work order's files.

## Architecture invariant

`SchedulePlan -> provider/quota preflight -> WorkerLeaseBroker -> bounded concurrent runner`

The runner is injected. AHA-6 does not interpret provider execution as lifecycle truth,
does not release a mutation lease before proposal materialization/review, and never retries
an existing/recovery-required lease as a new execution.

## Acceptance criteria

1. Only nodes present in the exact `SchedulePlan.selected` batch can be executed; task/assignment drift fails closed.
2. Two independent selected mutation tasks with distinct workers/worktrees/scopes can hold two distinct active leases and enter the injected runner concurrently; a barrier/event test proves real overlap.
3. The batch honors each provider profile's `max_concurrency` including injected already-inflight capacity; excess work waits before lease acquisition/provider call.
4. Provider health must be fresh/AVAILABLE. For lanes requiring quota evidence, missing quota or non-positive remaining quota waits before lease acquisition/provider call.
5. Lease acquisition is exact and collision-safe. `WAIT`, `EXISTING`, `RECOVERY_REQUIRED`, or RDC fallback never cause an automatic execution replay.
6. Same-worker/scope races remain protected by the existing atomic lease store; the losing task is not dispatched.
7. Runner completion does not automatically release mutation leases; AHA-5 materialization/review/reconcile remains authoritative for release.
8. Runner/transport uncertainty is surfaced without an internal retry. Existing durable execution/recovery state decides what happens next.
9. No secret value is read into task/result/log evidence. CoinTH/GLM credentials resolve only from the approved external runtime secret mechanism rooted at `A-Wiki-Data/.env`.
10. CoinTH GLM dispatch requires a preflight observation carrying `remaining_5h`, `used_5h`, `limit_5h`, `window_reset_at`, `window_reset_in_sec`, normalized into existing provider quota evidence before dispatch.
11. Focused tests, relevant lease/scheduler/provider regressions, compileall, diff/scope/secret audit pass before PR.
12. Exact-head Windows/Ubuntu/macOS CI including Frozen Setup E2E passes; final PR head is re-audited before merge.

## RED-first implementation slices

A. Contract/identity + exact selected-task mapping.
B. Provider freshness/quota/max-concurrency preflight with no lease on wait.
C. Lease acquisition and non-replay semantics for EXISTING/RECOVERY/WAIT.
D. Concurrent runner execution with stable result ordering and active lease retention.
E. Race/collision/exception tests; relevant regression suite.
F. Optional real CoinTH/GLM proof only after external secret resolver + quota preflight are safely available.

## Initial evidence / checkpoint

- AHA-5 closeout PR #150 merged exact reviewed head `8b863b9` as main `64b6ef8`.
- Post-main CI `33286026232` SUCCESS: Windows full/packaging/Frozen Setup E2E + Ubuntu/macOS smoke.
- AHA-5 closeout and implementation worktrees/branches removed only after clean tree-equality proof.
- A-Wiki remote main checked read-only; brain/control-plane split still assigns worker/process/dispatch to A-Sunday Conductor.
- A-Wiki local checkout is stale/dirty and was not mutated; `.tmp/agent-claims.json` currently has zero claims.
- Existing Conductor scheduler, atomic lease broker/recovery, durable graph dispatch and provider quota model were inspected; no competing open PR exists.
- Provider quota already has `limit`, `used`, `remaining`, `reset_at`, `reset_in_seconds`; no second quota type is authorized.

Current status: `IMPLEMENTED / REVIEW_PENDING`.

## Implementation checkpoint ? 2026-08-30

- Implementation commit: `bad6567a7909f6cceb34d6debff20a23e5c42484`.
- Added only `parallel_ready_execution.py` + focused tests; scheduler, lease broker, job store and provider model were reused unchanged.
- Proves exact SchedulePlan mapping, provider freshness/quota/capacity waits before lease, atomic lease non-replay, same-scope collision blocking, two-task concurrent runner/GE-7 dispatch, gate deny-before-lease, lease retention, and per-task runner exception -> recovery-required without retry.
- Focused AHA-6: 13 passed. Relevant scheduler/dispatch/chaos/lease/provider/harness/AHA-5 regression: 193 passed. Compileall, diff-check and staged secret-pattern scan PASS.
- One regression invocation initially failed only because pytest ran outside repo root and a schema path was relative; rerun from the canonical worktree root passed without code changes.
- Fresh official Z.ai GLM-5.3 evidence (2026-08-14 launch) supports bounded code review/debug delegation: Terminal-Bench 3.0 28.3, DeepSWE v1.1 66.9, Z.ai Code Bench Max 34.5%. GPT retains architecture/integration/merge authority.

Next safe action: durable read-only GLM-5.3 MAX independent review packet -> GPT reads result directly -> bounded repair if needed -> full regression/audit -> PR/CI/re-audit.

## Governance scope extension checkpoint ? 2026-08-30

User explicitly requested durable multi-agent rules so GPT/GLM/future agents can exchange task/result state without human result copy-back. Pre-gate evidence: active AHA-6 worktree clean; GitHub open PRs 0; A-Wiki live local claims 0. `SAFE_TO_MUTATE = YES` for the three governance files added to allowed scope above. External agents remain read-only to coordination SSoT; the integrator is the single tracked SSoT writer.
