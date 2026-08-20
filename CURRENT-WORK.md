# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Durable Work-class Runtime Foundation**

## Active work order

None. Most recently completed: `WO-P1-035 — Durable Job Execution Coordinator`.

## Completed foundation

- [x] Native execution core.
- [x] Fixed Git/verification adapters.
- [x] Transactional Git mutations.
- [x] Durable job state/checkpoint store.
- [x] Explicit durable execution coordinator with gated worker/version preconditions, attempt budget, evidence checkpoints, and recovery classification.
- [x] P1-035 verification: 11 targeted; 502 full-suite passed with 1 environment-specific Tk skip; PID 25396 preserved.

## Next safe action

Open a bounded operation-registry/backend work order that resolves allowlisted opaque `operation_ref` identifiers to fixed native adapter calls. Keep commands/config ephemeral and never turn the coordinator into a generic shell.

## Deferred/external

Worker 3 live transport provisioning, A-Wiki companion registration apply, GitHub remote publication, scheduler/background loop, model/worker routing, Discord transport.
