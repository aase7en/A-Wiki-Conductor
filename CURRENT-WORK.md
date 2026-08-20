# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Durable Work-class Runtime Foundation**

## Active work order

None. Most recently completed: `WO-P1-037 — Native Worker Adapter Assembly`.

## Completed foundation

- [x] Native execution core.
- [x] Fixed Git/verification adapters.
- [x] Transactional Git mutations.
- [x] Durable job state/checkpoint store.
- [x] Durable job execution coordinator.
- [x] Allowlisted native operation registry/backend.
- [x] Fresh Control Center worker assignment -> confined native Git-read/verification adapter assembly.
- [x] P1-037 verification: 8 targeted + 525 full-suite passed, 1 Tk environment skip; PID 25396 preserved.

## Next safe action

Open an application-level Durable Job Control Service that composes job store + execution coordinator/backend behind a small command API suitable for future Discord/Desktop adapters. No scheduler/router/planner.
