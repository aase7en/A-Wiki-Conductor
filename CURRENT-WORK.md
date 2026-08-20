# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Resilient Execution Supervisor MVP**

## Active work order

None.

## Recently completed

- `P1-038 — Durable Job Control Service` at `4f300ca`.
- `AC-RES-001 — Durable Execution Record` — stable execution identity, independent transport/execution state, optimistic versioning and append-only bounded metadata events.
- Resilient Execution Supervisor architecture at `c57bd2a`.
- Operator/Telegram/wire foundation committed through `984a20e`.

## AC-RES-001 evidence

- pure model + SQLite store targeted tests: 22 passed
- `TRANSPORT=LOST` with `EXECUTION=RUNNING` is persisted without implicit failure
- raw prompt/transcript/command/env/stdout/stderr fields absent from model/schema
- no process launch/retry/reconnect/Serena-specific logic added

## Environment follow-up

Current Hermes/uv Python build remains independently diagnosed as unstable for the legacy full-suite path. Recommended remediation is Python build `20260623` or newer in a separate bounded environment work order. Do not mutate it casually.

## Next safe action

Open `AC-RES-002 — Supervised Subprocess`: reuse `WindowsOwnedProcessController`/native execution primitives to allocate a durable run directory, launch an exact owned process with redirected durable logs, persist PID, and expose inspect/collect without depending on one long transport request.
