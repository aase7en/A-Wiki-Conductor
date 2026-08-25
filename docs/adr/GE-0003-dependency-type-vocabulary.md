# GE-0003 — DependencyType vocabulary (12 evidence-driven types)

Status: PROPOSED (draft for GPT-5.6 Sol MAX decision)
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

## Open point for GPT

Whether VERIFICATION edges are redundant with lifecycle VERIFY gating (recommendation: keep — they let fan-in barriers wait on verifiers without overloading DATA).
