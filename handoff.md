# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Current objective

Resilient Execution Supervisor MVP: final primitive AC-RES-008 — map Serena/MCP transport events and project-binding identity onto the generic AC-RES-003/004 model.

## Current task

`WO-AC-RES-008 — Serena Transport Adapter Integration`

Status: `IN_PROGRESS`

## Baseline

- branch `main`, tracking `origin/main` (`https://github.com/aase7en/A-Wiki-Conductor.git`, private, created 2026-08-20 by explicit user decision)
- AC-RES-007 completion `97f6a06`; full suite 726 passed, 1 skipped at that commit
- active Conductor listener remains PID `25396`

## Boundary

Adapter = deterministic mapping only (no I/O). AC-RES-003/004/005/006 remain authoritative for transport mutation, recovery, dedup, output. AC-RES-007 fake remains the fault harness.

## A-Wiki gate result (2026-08-20)

A-Wiki GitHub searched (`serena adapter`, `resilient execution`, `supervised`, `claim_acquire`): no overlap; A-Wiki local main is 105 behind origin, so GitHub was inspected directly. Classification: `WRAP + EXTEND`.

## Context rollover rule

If context becomes crowded, checkpoint repository continuity before recommending a new session; new sessions resume from repository artifacts.

## Next safe action

Write RED tests for `tests/test_serena_transport_adapter.py` (event classification, binding identity, integrated fake-executor recovery), then implement `src/a_conductor/serena_transport_adapter.py`.
