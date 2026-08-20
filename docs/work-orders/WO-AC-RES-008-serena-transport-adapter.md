# WO-AC-RES-008: Serena Transport Adapter Integration

Status: in_progress
Lane/files: `src/a_conductor/serena_transport_adapter.py`, `src/a_conductor/__init__.py`, `tests/test_serena_transport_adapter.py`, `docs/contracts/serena-transport-adapter.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-AC-RES-008-serena-transport-adapter.md`
Branch: main
Model tier: high

## Goal

Map observed Serena/MCP transport events (HTTP 502/503/504, connector session termination, health-probe failures) and Serena project-binding identity onto the existing AC-RES-003 transport states and AC-RES-004 recovery identity gate, so real Serena executions are supervised through the same provider-neutral model validated in AC-RES-007.

## Reuse classification

`WRAP + EXTEND`: AC-RES-003 stays owner of transport-state mutation; AC-RES-004 stays owner of recovery decisions; AC-RES-007 fake stays the fault harness. This slice adds only a deterministic Serena-specific mapping layer and binding-aware repository observer. No new job/execution state machine.

A-Wiki reuse-before-build gate (2026-08-20): A-Wiki GitHub `aase7en/A-Wiki` searched for `serena adapter`, `resilient execution`, `supervised`, `claim_acquire` — no overlap; no active A-Wiki work orders on this surface. A-Wiki local main is 105 behind origin/main, so GitHub state (authoritative) was inspected directly, not the local worktree.

## Required scenarios

- single transient MCP HTTP error → DEGRADED, transport-only mutation
- repeated MCP HTTP errors → LOST
- connector session terminated → LOST immediately
- health-probe failures → DEGRADED then UNAVAILABLE
- healthy event after degradation → CONNECTED without touching execution state
- transport loss never mutates execution/process state or job claim
- binding branch/head agreement passes facts to recovery
- binding branch/head mismatch blocks recovery before collect
- record root vs binding worktree disagreement blocks recovery
- integrated: fake executor + adapter-driven LOST + binding observer recovers result without relaunch

## Acceptance

- Adapter performs no network, process, file, or Git I/O; it maps structured events only.
- Classification is deterministic from the ordered event window; thresholds are explicit constructor policy.
- All mutations flow through `ExecutionTransportService`; no direct store writes.
- `CONNECTED/DEGRADED/LOST/UNAVAILABLE` transitions preserve execution state and job ownership.
- Binding observer wraps a read-only facts observer and adds only binding-agreement checks.
- Integrated test reuses the `DeterministicFaultExecutor` harness; launch count stays 1.
- No real Serena/MCP/tunnel/PID mutation; temp stores/repos only.

## Micro-steps

- [x] 008-A reuse gate + coordination + contract checkpoint
- [ ] 008-B RED adapter scenario tests
- [ ] 008-C implement deterministic mapping + binding observer
- [ ] 008-D integrated recovery tests via fake executor
- [ ] 008-E regression + safety verification
- [ ] 008-F close/commit/push

## Forbidden

- No real Serena outage injection; no MCP/tunnel/network calls.
- No new execution/job state machine, scheduler, retry, or failover.
- No production automatic retry decisions in the adapter.
- No A-Wiki/Phase6 mutation.
- No broad process kills or PID 25396 interference.

## Checkpoint log

- [2026-08-20] Opened from AC-RES-007 completion `97f6a06`; GitHub remote `origin` now exists (private repo `aase7en/A-Wiki-Conductor`), `main` pushed.
