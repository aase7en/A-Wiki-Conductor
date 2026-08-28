# HANDOFF — A-Sunday Conductor

Last updated: 2026-08-28 — WO-P1-094 / AHA-4

## Current Objective

Eliminate manual prompt copying by connecting accepted GE-6 scheduling to the existing durable job-control execution authority. AHA-4 is the durable dispatch layer; AHA-4A/4B worker lease/fallback/heartbeat remain later slices.

## Repository State

- Repository: `aase7en/A-Wiki-Conductor`
- Worktree: `A:\GitHub\A-Wiki-Conductor-aha4`
- Branch: `feat/wo-p1-094-aha4-durable-graph-dispatch`
- Base/accepted main at claim: `023c7b65026b0ff536cd1d802d6010e381a4447a`
- Work order: `docs/work-orders/WO-P1-094-aha4-durable-graph-dispatch.md`
- Shared root is protected/read-only.

## Accepted Baseline

- AHA-1 contracts merged `c3ca84c`.
- AHA-2 provider configuration/observation merged `ca4cd98`.
- AHA-3 bounded Claude Code read-only harness merged `ab28dc7`.
- PR #118 Windows Tk CI isolation merged `ad106282`.
- PR #117 harness phase transition merged `8db3226`.
- GE-6 PR #104 exact head `694b8dee053e48d805596b527525cada875848a4` passed independent 114-test recheck + exact-head 3-OS CI and merged as `023c7b6`.

## AHA-4 Architecture Boundary

Accepted ADR: `docs/adr/GE-0007-dispatch-through-durable-job-control.md`.

Classification: **REUSE + WRAP + EXTEND**.

Authority remains:
- `DurableJobControlService`
- `SQLiteJobStore`
- `DurableJobExecutionCoordinator`
- supervised execution + canonical execution fingerprint/dedup

Do not create a graph-specific lifecycle/store/retry counter/process runner/dedup system. Do not route internal graph dispatch through `operator_dispatch.py`.

Stable semantic key: `{graph_id, graph_run_id, node_id}`.

Expected transaction:
`resolve/recover job -> READY -> exact worker claim(CAS) -> injected gates -> GATING -> execute_operation -> VERIFYING or RECOVERY_NEEDED -> reconcile`.

Gate refusal must occur before EXECUTING so it consumes zero attempts. Transport/backend uncertainty never authorizes blind replay.

## Local Implementation Evidence

- stable graph-run job identity + immutable dispatch metadata implemented;
- authoritative injected dispatch-mode resolver blocks unknown/mismatch before job launch;
- exact-worker CAS + gate denial/release + INTERACTIVE_PULL offer + PROGRAMMATIC_PUSH durable execution implemented;
- transport loss after durable GATING reconciles then resumes once; node-local backend failure leaves independent dispatch healthy;
- `test_graph_dispatch.py`: **18 passed**; graph/job-control/dedup/recovery: **183 passed**; AHA-2/AHA-3 + dispatch: **107 passed**.

## Protected Parallel Work

- PR #108 installer target ownership: do not touch installer scope.
- `feat/north-star-runtime-sunday-family`: preserved integration lineage; do not mutate.
- dirty/detached audit lanes remain protected.
- live provider/gateway/user DB remains fail-closed and out of this slice.

## Next Safe Action

1. local final gate is GREEN: compileall PASS, staged diff-check PASS, exact 8-file scope PASS, bounded secret scan PASS;
2. Draft PR #119 is open at old head `3b97cfa`; remote audit found and locally fixed same-key worker drift by pinning scheduled `worker_id`;
3. commit/push that fix, then require fresh exact-head Windows/Ubuntu/macOS CI. Old-head run `33158379414` had Ubuntu/macOS green and Windows failed `test_supervised_command_runner.py::test_timeout_leaves_durable_running_execution_then_retry_attaches`; local repeated suite = 5/5 green;
4. merge/cleanup only after evidence is green;
5. continue AHA-4 in a new bounded micro-slice that bridges the accepted AHA-3 Claude Code harness into this durable job-control execution authority; AHA-4 is not COMPLETE until that bridge is proven;
6. only then proceed to AHA-4A worker lease/fallback and AHA-4B heartbeat/stale recovery.

## Safety

`SAFE_TO_MUTATE = YES` only in `A:\GitHub\A-Wiki-Conductor-aha4` and WO-P1-094 allowed scope.
