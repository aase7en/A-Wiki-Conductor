# A-Conductor Deterministic Fault-Injection Contract

Status: Phase 1 test-support contract
Work order: `WO-AC-RES-007`

## Purpose

Recovery reliability must be tested deterministically without repeatedly breaking real Serena/MCP/tunnels. A local fake executor simulates transport timing, process state, durable result availability, and output volume while production recovery logic remains unchanged.

## Boundary

The fake is test infrastructure. It may implement the supervised `inspect/collect` shape and write temp-repository evidence, but it is not a production execution backend and must not be wired into normal worker routing.

## Determinism

Scenarios advance only through explicit test actions. No background threads, random sleeps, wall-clock races, or real network failures are required.

## Scenarios

- `NORMAL_SUCCESS`
- `DISCONNECT_BEFORE_LAUNCH`
- `DISCONNECT_AFTER_LAUNCH`
- `DISCONNECT_MID_COMMAND`
- `DISCONNECT_AFTER_COMPLETION`
- `DELAYED_SUCCESS`
- `LARGE_STDOUT`
- `NONZERO_EXIT`
- `MALFORMED_RESULT`
- `UNKNOWN_PROCESS`

## Required observable facts

- whether target ever started;
- launch count;
- whether transport loss was simulated;
- whether process is still running;
- whether result is available;
- durable stdout/stderr/result refs;
- exit code when known;
- never-started vs unknown provenance must remain distinguishable.

## Integration expectations

Tests should combine the fake with production AC-RES primitives:

- AC-RES-003 transport loss/ownership preservation;
- AC-RES-004 recovery reconciliation;
- AC-RES-005 duplicate execution protection;
- AC-RES-006 output backpressure.

The fake itself must not encode the expected production recovery decision.

## Safety

- temp directories/databases only;
- no real Serena/PID/tunnel manipulation;
- no infinite loop/background daemon;
- no network access;
- no destructive Git.
