# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Resilient Execution Supervisor MVP**

## Active work order

`docs/work-orders/WO-AC-RES-006-output-backpressure.md`

Status: `IN_PROGRESS`

## Completed resilient foundation

- AC-RES-001 durable execution record: `0a3040d`
- AC-RES-002 supervised subprocess: `03a623d`
- AC-RES-003 transport-loss state + claim preservation: `f9838a5`
- AC-RES-004 recovery reconciliation + repo identity gate: `bb5dab0`
- AC-RES-005 duplicate execution protection: `a0a2e52`

## AC-RES-006 micro-steps

- [x] 006-A fit analysis: reuse AC-RES-002 durable refs; no second logger
- [x] 006-B contract + claim coordination
- [ ] 006-C RED artifact confinement/backpressure/summary tests
- [ ] 006-D minimal bounded reader implementation
- [ ] 006-E regression + safety verification
- [ ] 006-F close/commit

## Invariant

Complete raw execution evidence stays on disk. Transports receive bounded tails/chunks/metadata/summaries only; caller never supplies an arbitrary path.

## Environment follow-up

Hermes/uv Python/Tcl-Tk full-suite environment remains independently diagnosed as unstable. Recommended remediation: Python build `20260623` or newer in a separate bounded environment work order.

## Next safe action

Commit AC-RES-006 coordination checkpoint, then write RED tests for durable-ref confinement, traversal/symlink escape, hard byte budgets, chunk/tail/digest behavior, invalid UTF-8 handling, and pytest summary extraction.
