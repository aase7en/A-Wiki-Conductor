# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Resilient Execution Supervisor MVP**

## Active work order

None.

## Completed resilient foundation

- AC-RES-001 durable execution record: `0a3040d`
- AC-RES-002 supervised subprocess: `03a623d`
- AC-RES-003 transport-loss state + claim preservation: `f9838a5`
- AC-RES-004 recovery reconciliation + repo identity gate: `bb5dab0`
- AC-RES-005 duplicate execution protection: `a0a2e52`
- AC-RES-006 output backpressure + bounded durable artifact reads: completion commit is the immediate transaction

## AC-RES-006 evidence

- 10 targeted tests; 80 AC-RES-001..006 focused/regression tests
- full durable logs remain on disk; transport-facing tail/chunk max 64 KiB
- full SHA-256 + size metadata without full response payload
- traversal/symlink confinement + invalid UTF-8 safety
- bounded pytest summary extraction
- no process/log/Git/network mutation API
- PID `25396` unchanged

## Project continuity rule

Before recommending a new chat/session because context is crowded, checkpoint active WO, HEAD/worktree, evidence, blockers/decisions, exact next safe action, and ownership/forbidden constraints in repository artifacts.

## Environment follow-up

Hermes/uv Python/Tcl-Tk full-suite environment remains independently diagnosed as unstable. Recommended remediation: Python build `20260623` or newer in a separate bounded environment work order.

## Next safe action

Open `AC-RES-007 — Fake Executor + Fault Injection`: deterministic local simulation of disconnect-before-launch, after-launch, mid-command, after-completion-before-result, delay, large output, nonzero exit, malformed response, duplicate request, and wrong identity. Do not use real Serena outages as the harness.
