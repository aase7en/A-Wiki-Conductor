# WO-P1-653 — fs-backed agent state store + doctor runtime diagnostics

Status: OPEN — implementation lane (SRM source; AWC docs only)
Issue: #653
Parent: #495 (overnight Priority 4); lineage: LocalAgent runtime (B/B-2/647/650) + slice-A doctor + #646 stdio adapter.
Risk: R3 — persistence validity seam (a corrupt state must never be silently treated as fresh) + diagnostics adjacent to secrets (token presence only).
Topology: EXECUTION_SUBSTRATE_ONLY. Compatibility: SRM `4debd1b` + AWC `91c2e8a` (re-pin on drift).

## Scope

1. `createFsAgentStateStore(path)` — fs-backed AgentStateStore: typed fail-closed load validation (malformed → typed error, NEVER accepted as empty); atomic save (tmp+rename); deep-copy both directions.
2. `inspectAgentState(raw, now)` — pure diagnostics: executed count + malformed entries; refresh-token PRESENCE boolean (never the value); credentialExp verdict VALID/EXPIRED/ABSENT; typed fail-closed.
3. Doctor CLI extension: agent-state health from the Sunday config root + offline stdio test-gate posture (env booleans). Read-only, no secrets.
4. RED-first tests: fs roundtrip; LocalAgent.restart() over the REAL fs store (cold start); malformed-state typed rejection; inspector verdicts incl. expiry boundary; doctor rows via the pure inspector.

## Review assignment

Independent reviewer: **GPT-6 Sol** (`gpt-6-sol` codex exec, read-only, exact-SHA; harness files OUTSIDE the candidate worktree — WO-650 lesson). Author: GLM. JEV: SPENDING_GATED (route exists via #499 binding; new live calls need their own admission), advisory-only, non-blocking.

## Forbidden

Standard B-lineage set; no real enrollment; no secrets in any output; no store-validation weakening; no installer packaging (later slice).

## Checkpoint log (append-only)

- [2026-10-14] WO created. Lane issue #653 verified real BEFORE naming; one clean `Issue: #653` line. No source mutation yet.
