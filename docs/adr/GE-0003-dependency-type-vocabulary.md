# GE-0003 — DependencyType vocabulary (12 evidence-driven types)

Status: ACCEPTED — GPT-5.6 Sol MAX integrator decision, 2026-08-26
Date: 2026-08-25

## Decision

Ship exactly the program-mandated set, aligned with existing A-Wiki content-graph edge naming (`depends` is the existing verb in `.wiki-graph.json`):

`DATA` (artifact produced → consumed) · `ORDERING` (no data, strict sequence) ·
`FILE_WRITE` (same file in both write_sets) · `WORKSPACE_WRITE` (same repo/worktree) ·
`GIT` (branch/ref collision) · `WORKER` (same physical SunDay slot) ·
`RUNTIME` (same Serena/runtime process) · `PROVIDER` (same model provider) ·
`RATE_LIMIT` (quota window) · `RESOURCE` (generic exclusive claim) ·
`VERIFICATION` (verifier must pass first) · `HUMAN_APPROVAL` (gate).

Rules: DATA/ORDERING are planner-declared; FILE_WRITE/GIT/WORKER/RUNTIME are DERIVED from node write_sets/bindings by the dependency analyzer (hidden-conflict detection); RATE_LIMIT/PROVIDER come from provider metadata; HUMAN_APPROVAL maps to lifecycle human gates. Future types require evidence (per program rule).

## Accepted semantic guardrail

Keep all 12 values as the initial vocabulary, including `VERIFICATION`, but do not treat every value as a persisted precedence edge. Only a relation that identifies a real predecessor participates in Kahn topological ordering. Dynamic/resource constraints such as worker/runtime/provider/rate-limit conflicts remain readiness/scheduler reasons unless the deterministic analyzer explicitly materializes a safe ordering. `HUMAN_APPROVAL` is a readiness gate. No dependency type is allowed to create a repair/retry back-edge or receive a cycle-detection exemption.
