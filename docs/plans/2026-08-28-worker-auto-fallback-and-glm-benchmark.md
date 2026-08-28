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

- PR #104 / GE-6 is a GLM-owned bounded algorithmic lane. After owner-led reconciliation its worktree reported **92 graph tests passing**; GitHub head is currently `b0febf20`.
- Earlier independent GPT recheck ran the seven `test_graph_*.py` files: **83 passed in 1.76s**. This confirms useful bounded implementation throughput, not final acceptance.
- Independent GPT review against accepted ADR GE-0006 found four current acceptance gaps: topological-rank ordering is omitted, equivalent worker choice depends on input order instead of stable worker ID, mutating project/workspace identity is not enforced, and gate/provider eligibility input is missing. These were posted as a PR review comment for the owner to repair.
- Windows CI additionally failed in the existing supervised-command timeout suite rather than a scheduler assertion; a rerun was requested to classify that independently. The PR remains blocked until both scheduler acceptance and exact-head CI are green.

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

1. **AHA-3 COMPLETE** — PR #116 merged `ab28dc7`; fake-runner/read-only harness, focused regressions, scope/secret checks, and 3-OS CI passed.
2. Repair/accept **GE-6 / PR #104** on its existing GLM-owned branch using the independent ADR review findings; do not mix AHA files.
3. Reuse the already accepted GE-7 durable-dispatch contract for **AHA-4**; implement only after GE-6 merges, with no second scheduler/lifecycle/store.
4. Implement **AHA-4** durable harness dispatch with stable execution identity, duplicate protection, bounded evidence, transport-loss reconciliation.
5. Implement **AHA-4A** worker eligibility + atomic lease broker + ordered fallback; deterministic race tests first.
6. Implement **AHA-4B** heartbeat/expiry/quarantine/stale-owner recovery; chaos tests for crash/disconnect/dirty worktree.
7. Prove **AHA-5** GPT-plan/review ↔ GLM-implement/repair vertical slice without manual prompt copying.
8. Prove **AHA-6** two independent READY tasks in isolated worktrees; assert no lease/scope collisions.
9. Add **AHA-6B** elastic capacity only if fixed-pool benchmark is green.
10. Build **AHA-7** Models & Agents UI on the existing command center; no second dashboard.
11. Add **AHA-8** providers one adapter at a time with the same contract tests.
12. Run full E2E/chaos/security/release audit; update README checklist from evidence; release the next verified version.
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