# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Resilient Execution Supervisor MVP**

## Active work order

None.

## Recently completed

- `P1-038 — Durable Job Control Service` at `4f300ca`.
- `AC-RES-001 — Durable Execution Record` at `0a3040d`.
- `AC-RES-002 — Supervised Subprocess Launch / Inspect / Collect` — exact-owned supervisor helper, durable child PID/log/result evidence, read-only inspect, no-rerun collect.

## AC-RES-002 evidence

- AC-RES-001+002 targeted regression: 38 passed
- internal helper uses `shell=False`; target executable allowlist + shell-intermediary denylist enforced
- target argv is not stored in SQLite/result JSON
- bounded real Windows smoke: `SUPERVISOR_RUNNING -> RESULT_AVAILABLE -> VERIFICATION_REQUIRED`, exit 0
- active Conductor listener preserved at PID 25396

## Environment follow-up

Current Hermes/uv Python build remains independently diagnosed as unstable for the legacy full-suite path. Recommended remediation: Python build `20260623` or newer in a separate bounded environment work order.

## Next safe action

Open `AC-RES-003 — Transport-Loss State & Lease Preservation`: add explicit transport-loss/reconnect events and policy around durable executions/jobs without touching process result state, never release ownership on temporary transport loss, and provide bounded transport retry-budget metadata only (no reconnect implementation yet).
