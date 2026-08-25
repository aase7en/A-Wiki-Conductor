# GE-0002 — TaskNode contract: awiki-task/v1 fields + Conductor domain + graph fields

Status: PROPOSED (draft for GPT-5.6 Sol MAX decision)
Date: 2026-08-25
Inputs: A-Wiki `schemas/awiki-task/v1.schema.json` (20-value capability enum, assigned roles, rich statuses), Conductor `domain.py` (Worker/Runtime/Provider/Capability/Execution/ReviewResult), program's candidate TaskNode fields.

## Decision

TaskNode = union of three sources, no duplicates:

- Identity/objective/status: keep `awiki-task/v1` vocabulary (id, objective, status incl. `blocked/security_stop/scope_drift/max_review_cycles`, `assigned.{executor,reviewer,architect,tester}.requires`, `required_capabilities`).
- Execution reality: Conductor domain (worker/runtime/provider bindings, attempt counters, artifacts via `execution_artifacts.py`, verification/ref: existing VERIFY/REVIEW outcomes).
- Graph additions (NEW, Conductor-owned): `dependencies: [{node_id, type: DependencyType}]`, `read_set`/`write_set` (path globs), `resources` (exclusive/ shared claims), `priority`, `timeout`, `retry_policy_ref` (pointer into lifecycle policy, not inline), `expected_outputs` (for fan-in completeness).

## Rationale

Brain schema stays untouched (HOLD phases 8-11) — graph fields live in Conductor's own schema layer that REFERENCES awiki-task/v1 as the base contract. D2 (schema ownership) resolves as: no brain mutation needed for GE-1.

## Open point for GPT

Confirm the exact minimal field list for GE-1 (proposal above) before implementation.
