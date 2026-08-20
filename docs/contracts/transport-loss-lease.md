# Transport-Loss State & Lease Preservation Contract

Status: AC-RES-003 binding contract
Parent: `docs/contracts/resilient-execution-supervisor.md`
Depends on: AC-RES-001 durable execution records + existing durable job claims

## Core invariant

> Transport loss changes transport health only. It does not decide process/result state and does not release ownership.

## Ownership source

A-Conductor must reuse the existing durable job worker claim. AC-RES-003 does not introduce a second execution lease table or incompatible claim protocol.

Before persisting a transport-state mutation, the service verifies:
- execution record exists;
- referenced durable job exists;
- durable job worker_id is still present;
- job worker_id equals execution worker_id.

If ownership no longer matches, transport mutation is blocked with a stable error code. The service does not repair/reassign ownership automatically.

## Transport mutations

Bounded operations:
- mark connected
- mark degraded
- mark lost
- mark unavailable

These operations:
- mutate only `TransportState`;
- preserve `ExecutionProcessState` exactly;
- preserve durable job state and worker claim exactly;
- are idempotent when the requested state already matches;
- append the existing bounded `TRANSPORT_STATE_CHANGED` execution event only when state actually changes.

## Evidence

Transport evidence is an opaque reference such as `transport:http-502-incident-17`; raw HTTP response bodies, stack traces, credentials and secret-bearing text do not belong in execution metadata.

## Explicitly deferred

- actual reconnect/reinitialize operations;
- retry/backoff counters and health telemetry;
- repo identity reconciliation after reconnect;
- claim expiry/release policy;
- backend failover/routing.

Those belong to later resilient-execution slices.