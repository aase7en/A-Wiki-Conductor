# A-Conductor Serena Transport Adapter Contract

Status: Phase 1 integration contract
Work order: `WO-AC-RES-008`

## Purpose

Real Serena/MCP transports fail in known ways (HTTP 502/503/504, connector session termination, health-probe timeouts). These must be recorded through the provider-neutral AC-RES-003 transport model instead of ad-hoc Serena-specific recovery logic.

## Boundary

The adapter maps structured, already-observed events to transport-state transitions via `ExecutionTransportService`, and maps `SerenaProjectBinding` expectations onto the AC-RES-004 repository identity gate. It performs no I/O of its own: no network, process, file, or Git access. Recovery decisions stay in AC-RES-004; dedup stays in AC-RES-005; output stays in AC-RES-006.

## Deterministic classification

- `MCP_HTTP_502/503/504`: first consecutive failure → `DEGRADED`; at/after `lost_after` consecutive failures → `LOST`.
- `CONNECTOR_SESSION_TERMINATED`: definitive → `LOST` immediately.
- `HEALTH_PROBE_TIMEOUT/REFUSED/INVALID`: first → `DEGRADED`; at/after `unavailable_after` consecutive failures → `UNAVAILABLE`.
- `MCP_OK` / `HEALTH_PROBE_OK`: → `CONNECTED` and resets the consecutive-failure window.
- Empty window → no mutation.

## Identity mapping

- The record's `repo_root` must equal the binding `worktree_path`, else `SERENA_BINDING_WORKTREE_MISMATCH`.
- Under `EXACT` policy, observed branch/head must equal `expected_branch`/`expected_head` when present, else `SERENA_BINDING_IDENTITY_MISMATCH`.
- Mismatches surface as error codes on the repository observation so AC-RES-004 blocks recovery before any mutation or collect.

## Safety

- Transport mutation never changes execution/process state or job ownership.
- No real Serena/MCP/tunnel interaction in tests; the AC-RES-007 fake executor is the harness.
- Temp stores/repos only.
