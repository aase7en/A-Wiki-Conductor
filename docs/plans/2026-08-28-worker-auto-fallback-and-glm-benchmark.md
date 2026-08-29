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

- PR #104 / GE-6 was a GLM-owned bounded algorithmic lane and is now accepted: final head `694b8dee` merged as `023c7b65` after the recorded scheduler acceptance gaps were repaired and exact-head 3-OS CI passed.
- Earlier independent GPT recheck ran the seven `test_graph_*.py` files: **83 passed in 1.76s**. This confirms useful bounded implementation throughput, not final acceptance.
- Independent GPT review against accepted ADR GE-0006 found four current acceptance gaps: topological-rank ordering is omitted, equivalent worker choice depends on input order instead of stable worker ID, mutating project/workspace identity is not enforced, and gate/provider eligibility input is missing. These were posted as a PR review comment for the owner to repair.
- Historical Windows CI failures in supervised-command/Tk isolation were repaired through the bounded CI lane; PR #104 later passed exact-head Windows/Ubuntu/macOS CI and merged. Those failures remain useful benchmark evidence but are no longer an active blocker.

### Suitability score for work during AHA-3/AHA-4

| Work type | GLM fit | Use now? |
|---|---:|---|
| isolated deterministic implementation + tests | 5/5 | Yes |
| repository archaeology / symbol tracing | 5/5 | Yes |
| fix a bounded failing test in owned scope | 5/5 | Yes |
| reconcile its own bounded branch with current main | 4/5 | Yes, only when that branch is explicitly GLM-owned |
| independent review against acceptance criteria | 4/5 | Yes, read-only |
| cross-cutting SSoT/hotspot architecture | 2/5 | Lead/review by GPT |
| secrets/trust-boundary final approval | 2/5 | GPT + deterministic checks |
| release/merge authority | 1/5 | No; evidence only |

Recommended immediate GLM mutation lane: **none while AHA-4A / PR #131 is actively owned by the GPT integrator with protected local work**. GLM remains a strong fit for a separately authorized bounded review or implementation lane after ownership/scope is released.
## Completion plan from current state

1. **AHA-3 COMPLETE** — PR #116 merged `ab28dc7`; fake-runner/read-only harness, focused regressions, scope/secret checks, and 3-OS CI passed.
2. **GE-6 COMPLETE** — PR #104 merged as `023c7b65` after exact-head 3-OS CI green.
3. **AHA-4 COMPLETE** — durable graph dispatch merged via PR #119 as `5cc417c9`; no second scheduler/lifecycle/store was introduced.
4. **AHA-4A ACTIVE / PROTECTED** — WO-P1-102 / draft PR #131 owns worker eligibility + atomic lease broker + ordered fallback. Its isolated worktree contains protected local changes; no other agent may rebind or mutate that scope.
5. After AHA-4A is accepted and ownership released, implement **AHA-4B** heartbeat/expiry/quarantine/stale-owner recovery with chaos tests for crash/disconnect/dirty worktree.
6. Prove **AHA-5** GPT-plan/review ↔ GLM-implement/repair vertical slice without manual prompt copying.
7. Prove **AHA-6** two independent READY tasks in isolated worktrees; assert no lease/scope collisions.
8. Add **AHA-6B** elastic capacity only if fixed-pool benchmark is green.
9. Build **AHA-7** Models & Agents UI on the existing command center; no second dashboard.
10. Add **AHA-8** providers one adapter at a time with the same contract tests.
11. Run full E2E/chaos/security/release audit; update README checklist from evidence; release the next verified version.
## Live benchmark once the router can dispatch GLM directly

Use the same bounded task packet across providers and record:
- time to first valid patch and time to deterministic GREEN;
- number of repair rounds / human copy-paste interventions;
- acceptance-criteria coverage and test pass rate;
- mutable-scope violations / unsafe Git attempts / secret-policy violations;
- diff size versus task size and regression count;
- provider latency, quota consumed, and estimated cost when observable;
- recovery success after forced transport loss / stale lease.

Candidate benchmark set: one repository-archaeology task, one isolated bug fix, one deterministic feature+tests task, one branch-reconciliation task, and one read-only review. Final routing weights must come from these measured outcomes, not vendor preference.
