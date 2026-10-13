# WO-P1-647 — durable credentialExp across LocalAgent restart

Status: OPEN — implementation lane (SRM source; AWC docs only)
Issue: #647
Parent: #495 (overnight goal Priority 3); predecessor WO-P1-643 (B-2 review P3-3 flag).
Risk: R2 — single-runtime persistence semantics, offline/test-only; composes already-shipped verified writers only.
Topology: EXECUTION_SUBSTRATE_ONLY. Compatibility: SRM `3be057a` + AWC main (re-pin on drift). NONOVERLAPPING with the frozen WO-P1-646 stdio-adapter hotspot (different files; #646 files forbidden here).

## Scope

Persist `credentialExp` in `AgentDurableState` (written by enroll and by verified `refresh()` only); construction/`restart()` prefers the persisted bound over the integrator-injected enrollment-time value; legacy states without the field fall back to the injected bound. NO new writer of a larger bound — unverified expiry inflation is impossible by construction (the only verified writer is the shipped refresh path).

## Deterministic matrix (RED first)

refresh at T (exp=T+86400) → restart → NEW command executes at clock ∈ (old injected bound, T+86400) · duplicate still served · legacy state → injected bound (negative control) · failed refresh persists no exp change.

## Forbidden

Public endpoints; production credentials; real enrollment/FS; write tools; weakening shipped contracts; touching WO-P1-646 files (offline-local-agent-stdio.ts, its fixtures/tests).

## Checkpoint log (append-only)

- [2026-10-13] WO created. Lane issue #647 verified real BEFORE naming; one clean `Issue: #647` line. No source mutation yet.
