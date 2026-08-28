# Worker Auto-Fallback + GLM-5.3 Benchmark Plan

Status: ACTIVE ROADMAP ADDENDUM
Date: 2026-08-28
Parent: Sunday Family Multi-Model Agent Harness Accelerator

## Decision

Add a worker lease broker and automatic fallback layer to A-Sunday Conductor. Chat/model sessions should request capability, not hard-code `SunDay-Worker N`.

Reuse classification: `EXTEND` existing registry/assignment + future GE scheduler seams. Do not create a second scheduler/router/task store.

## Target behavior

`REQUEST -> RECOVER SSoT -> CANDIDATE WORKERS -> PREFLIGHT -> ATOMIC LEASE -> EXECUTE -> HEARTBEAT -> CHECKPOINT -> RELEASE`

A candidate is skipped when it has an active task/lease, non-STOPPED mutation, unknown dirty state, incompatible project/runtime, overlapping mutable worktree/scope, stale health, or unresolved ownership.

Fallback order is policy-driven: next eligible semantic worker -> RDC for eligible shell/read-only work -> wait/queue -> optional elastic worker only after capacity policy exists.
## Proposed lease record

- `lease_id`, `worker_id`, `session_id`, `task_id`, `project_id`
- worktree / branch / expected HEAD
- allowed + forbidden mutable scope
- acquired / heartbeat / expiry timestamps
- mutation intent + runtime identity

Atomic claim is mandatory. Two chats racing for the same worker must produce one winner; the loser retries another eligible worker without rebinding or interrupting the winner.

## Roadmap insertion

- **AHA-4** — durable dispatch integration on accepted GE seams.
- **AHA-4A** — worker lease broker + eligibility preflight + automatic fallback.
- **AHA-4B** — lease heartbeat, stale-owner recovery, quarantine, fairness/backpressure.
- **AHA-5** — GPT↔GLM review/repair loop using brokered workers.
- **AHA-6** — parallel independent READY tasks; prove no ownership collision.
- **AHA-6B** — optional elastic worker capacity after fixed-pool correctness is proven.

AHA-4A must land before broad autonomous parallel execution.
## GLM-5.3 evidence benchmark

Current repository evidence, not a synthetic model-speed benchmark:

- PR #104 / GE-6 is a GLM-owned bounded algorithmic lane: pure deterministic scheduler, 5 changed files, 505 additions / 17 deletions. Its PR description records 88 combined graph tests passing.
- Independent recheck on 2026-08-28 ran the seven current `test_graph_*.py` files in that GLM worktree: **83 passed in 1.76s**.
- The same PR is currently open and non-mergeable against newer `main`, showing that bounded implementation can be productive while final integration/reconciliation still needs explicit ownership + deterministic review.

### Suitability score for work during AHA-3/AHA-4

| Work type | GLM fit | Use now? |
|---|---:|---|
| isolated deterministic implementation + tests | 5/5 | Yes |
| repository archaeology / symbol tracing | 5/5 | Yes |
| fix a bounded failing test in owned scope | 5/5 | Yes |
| reconcile its own GE-6 branch with current main | 4/5 | Yes, with scope gate |
| independent review against acceptance criteria | 4/5 | Yes, read-only |
| cross-cutting SSoT/hotspot architecture | 2/5 | Lead/review by GPT |
| secrets/trust-boundary final approval | 2/5 | GPT + deterministic checks |
| release/merge authority | 1/5 | No; evidence only |

Recommended immediate GLM lane: finish/reconcile PR #104 only. It is already GLM-owned and does not overlap AHA-3 files.
## Completion plan from current state

1. Finish **AHA-3** fake-runner Claude Code harness; focused regression, secret/scope scan, PR/CI/merge.
2. Reconcile **GE-6 / PR #104** on its existing GLM-owned branch; do not mix AHA files.
3. Define/accept the remaining GE durable-dispatch seam required by **AHA-4**; no second scheduler.
4. Implement **AHA-4** durable harness dispatch with stable execution identity, duplicate protection, bounded evidence, transport-loss reconciliation.
5. Implement **AHA-4A** worker eligibility + atomic lease broker + ordered fallback; deterministic race tests first.
6. Implement **AHA-4B** heartbeat/expiry/quarantine/stale-owner recovery; chaos tests for crash/disconnect/dirty worktree.
7. Prove **AHA-5** GPT-plan/review ↔ GLM-implement/repair vertical slice without manual prompt copying.
8. Prove **AHA-6** two independent READY tasks in isolated worktrees; assert no lease/scope collisions.
9. Add **AHA-6B** elastic capacity only if fixed-pool benchmark is green.
10. Build **AHA-7** Models & Agents UI on the existing command center; no second dashboard.
11. Add **AHA-8** providers one adapter at a time with the same contract tests.
12. Run full E2E/chaos/security/release audit; update README checklist from evidence; release the next verified version.