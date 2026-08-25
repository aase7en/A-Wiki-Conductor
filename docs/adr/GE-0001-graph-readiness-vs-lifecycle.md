# GE-0001 — Graph readiness is a DAG; lifecycle stays a durable state machine

Status: PROPOSED (draft by GLM 5.3 for GPT-5.6 Sol MAX decision — user-authorized prep)
Date: 2026-08-25
Inputs: GE-0 status report + A-Wiki reuse gate (both in session records); program directive "Do NOT blindly encode VERIFY→REPAIR→VERIFY as a cyclic dependency graph".

## Decision

Model execution readiness as an acyclic dependency graph (TaskGraph over TaskNodes/TaskEdges), and keep retry/repair/recovery inside the existing durable lifecycle state machine (`job_state.py`, `lifecycle_*.py`, `recovery_reconciliation.py`). The graph answers only "what is READY and why"; the state machine owns "what happened, how many attempts, what repairs". A repair creates a NEW attempt (and may add NEW nodes); it never creates a back-edge in the graph.

## Consequences

- Ready = dependency-resolved ∧ resources available ∧ no exclusive-write conflict ∧ capability match ∧ safety gates pass ∧ provider constraints allow dispatch (per program rule).
- Fan-in completeness lives in the graph (expected/terminal/success/fail/missing children per parent); verification outcomes stay lifecycle events.
- Existing durability invariants (idempotency, checkpoints, attempt budgets, dedup) are untouched — the graph composes on top.

## Alternatives rejected

- Cyclic graph with VERIFY→REPAIR edges: couples scheduling to retry policy; cycle detection would need exemptions; contradicts program directive.
- Everything-in-lifecycle (no graph): cannot express parallelism, hidden file/git/resource conflicts, or fan-in barriers — the actual GE goals.
