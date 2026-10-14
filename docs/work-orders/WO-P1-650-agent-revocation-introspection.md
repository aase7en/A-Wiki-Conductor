# WO-P1-650 — agent-side revocation introspection (offline)

Status: OPEN — implementation lane (SRM source; AWC docs only)
Issue: #650
Parent: #495 (overnight Priority 2); lineage B/B-2/647 runtime + #646 adapter (router-side veto shipped there).
Risk: R3 — revocation semantics adjacent to the at-most-once anchor; offline/test-only.
Topology: EXECUTION_SUBSTRATE_ONLY. Compatibility: SRM `96f0c8b` + AWC `cfb916f` (re-pin on drift).

## Scope

Injectable `introspect?: (deviceId, thumbprint) => boolean` on `LocalAgentRuntime`; `receive()` checks it for NEW executions AFTER dedup (dedup contract preserved across revocation) and BEFORE execution; fail-closed (false OR throw) → typed `{ agentAck: false, denied: 'AGENT_REVOKED' }`, nothing recorded (retryable once revocation lifts, mirroring expiry semantics); absent → previous behavior exactly.

## Deterministic matrix (RED first)

revoked→refused+unrecorded · throw→fail-closed · prior duplicate still served · no-introspect back-compat · revocation lifts→executes.

## Review assignment (operator steer)

Author GLM; INDEPENDENT reviewer **GPT-6 Sol** (`gpt-6-sol` Codex exec, read-only sandbox, exact-SHA bound; preflight verified `PREFLIGHT_OK`). GLM separate-session lane is the fallback if the Codex route fails mid-review.

## Forbidden

Standard B-lineage set; no weakening of the dedup anchor, expiry guard, or #646 adapter gates.

## Checkpoint log (append-only)

- [2026-10-13] WO created. Lane issue #650 verified real BEFORE naming; one clean `Issue: #650` line. JEV route recorded unavailable this session (advisory-only, non-blocking). No source mutation yet.
