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

Current status: `REPAIRED / REREVIEW_PENDING`.

## Implementation checkpoint — 2026-08-30

- Implementation commit: `bad6567a7909f6cceb34d6debff20a23e5c42484`.
- Added only `parallel_ready_execution.py` + focused tests; scheduler, lease broker, job store and provider model were reused unchanged.
- Proves exact SchedulePlan mapping, provider freshness/quota/capacity waits before lease, atomic lease non-replay, same-scope collision blocking, two-task concurrent runner/GE-7 dispatch, gate deny-before-lease, lease retention, and per-task runner exception -> recovery-required without retry.
- Focused AHA-6: 13 passed. Relevant scheduler/dispatch/chaos/lease/provider/harness/AHA-5 regression: 193 passed. Compileall, diff-check and staged secret-pattern scan PASS.
- One regression invocation initially failed only because pytest ran outside repo root and a schema path was relative; rerun from the canonical worktree root passed without code changes.
- Fresh official Z.ai GLM-5.3 evidence (2026-08-14 launch) supports bounded code review/debug delegation: Terminal-Bench 3.0 28.3, DeepSWE v1.1 66.9, Z.ai Code Bench Max 34.5%. GPT retains architecture/integration/merge authority.

Next safe action: durable read-only GLM-5.3 MAX independent review packet -> GPT reads result directly -> bounded repair if needed -> full regression/audit -> PR/CI/re-audit.

## Governance scope extension checkpoint — 2026-08-30

User explicitly requested durable multi-agent rules so GPT/GLM/future agents can exchange task/result state without human result copy-back. Pre-gate evidence: active AHA-6 worktree clean; GitHub open PRs 0; A-Wiki live local claims 0. `SAFE_TO_MUTATE = YES` for the three governance files added to allowed scope above. External agents remain read-only to coordination SSoT; the integrator is the single tracked SSoT writer.

## Full-loop / collaboration checkpoint — 2026-08-30

- Fresh `grill-with-docs` upstream check: local 7-line wrapper matches current `mattpocock/skills` main behavior (`/grilling` + `/domain-modeling`); upstream commit history shows grill alignment work on 2026-08-06. An upstream issue opened 2026-08-26 reports grill can jump into implementation without an explicit spec/task handoff, so this repo now enforces a separate plan/task/claim gate before mutation.
- Full local `python -m pytest -q`: 1696 passed, 5 skipped, 2 failed. Both failures are the already-documented Desktop Commander GPU environment limitation (`OpenGL`/WGL dependency set absent); AHA-6 touched no GPU files. WO-P1-097 already records exact-head GitHub CI as final GPU authority for this machine.
- Relevant AHA-6 regression remains 193 passed; focused = 13 passed; compileall/diff-check/secret scan PASS.
- Read-only installed DB inspection confirms `%LOCALAPPDATA%\A-Conductor\control-center.sqlite` has no `provider_*` tables. Production still has only the `EnvironmentReferenceResolver` protocol, not a concrete Drive-backed provider resolver. Automatic CoinTH/GLM therefore remains fail-closed and no provider call was attempted.
- Human one-way bridge is the accepted current fallback: runtime task/result files live only under ignored `runs/`; the human relays one task pointer; GLM writes the result there; GPT reads it directly and is the single writer that folds status/evidence into tracked SSoT.
- Collaboration protocol now forbids per-agent roadmap/handoff/memory clones and codifies the full loop-engineer cycle with explicit plan/task gate, independent exact-SHA review, realistic E2E, defect memory, PR/CI/re-audit/merge proof.

Next safe action: commit this governance checkpoint, regenerate the ignored GLM review task against that exact clean HEAD, then obtain the read-only GLM-5.3 MAX review via automatic dispatch only if secret+quota gates become provably ready; otherwise use the one-direction human relay.

## Independent GLM review + repair checkpoint — 2026-08-30

- Read-only task `aha6-glm-review-001` was bound to exact clean HEAD `ae3dae595b6acc173657e15120c48068fcc4af7a`; task SHA256 `c27d14ebe738f12fb305c5371f2f694d54fa7728071dc7953ef4469e22a576e7`; reviewed source/test SHA256 matched. Result identity matched `cointh-glm / glm-5.3` and returned `CHANGES_REQUIRED`.
- Accepted correctness defect: the lease-admission loop could raise on malformed `LEASED` broker outcomes after sibling leases were acquired, erasing structured sibling batch evidence. RED tests reproduced both missing-lease and selected-worker-drift paths.
- Repair commit `2a4d8fd786a9d3086a8cd2a298b8ee8cfcb6adc8`: both paths now become per-task `LEASE_RECOVERY_REQUIRED`; valid siblings continue; unknown future lease outcome kinds fail closed instead of raising `KeyError`.
- Accepted integration risk, not solved by a duplicate authority: provider `max_concurrency` is batch-local against the injected snapshot. `ParallelReadyExecutor.execute()` now documents that concurrent batch starts using one snapshot are unsupported. Production assembly must serialize admission per provider or reuse an existing atomic capacity authority before this seam is wired live. This remains a blocker for production assembly, not permission to add a second provider semaphore/store inside AHA-6.
- P3 review items about runner diagnostic richness, read-only lease lifecycle, and internal thread cap remain hardening backlog; current runner concurrency is already bounded by the upstream `SchedulePlan` policy and mutation leases intentionally remain active for AHA-5 reconcile.
- Post-repair verification: focused = 16 passed; related scheduler/dispatch/chaos/lease/provider/harness/AHA-5 regression = 196 passed; compileall/diff-check/secret scan PASS. Full local suite = 1698 passed, 5 skipped, 2 failed only on the pre-existing Desktop Commander GPU/OpenGL/Tcl dependency limitation outside AHA-6.
- Durable defect lesson #25 records the batch-evidence failure mode and prevention rule.

Next safe action: checkpoint this review/repair state, generate `aha6-glm-rereview-002` against the exact clean repair+SSoT HEAD, obtain independent read-only re-review via the one-way bridge, then audit -> Draft PR -> exact-head CI -> re-audit/merge.
