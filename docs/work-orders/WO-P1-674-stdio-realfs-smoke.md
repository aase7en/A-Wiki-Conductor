# WO-P1-674 — real-chain stdio smoke (fs reader + allowlist executor)

Status: OPEN — implementation lane (SRM test-only; AWC docs only)
Issue: #674
Parent: #495 (operator steer 2026-10-15); predecessors: #646 adapter (injected-agent seam), #662 executor, #671 fs reader.
Risk: R2 — test-only composition over shipped, reviewed components; zero production files.
Topology: EXECUTION_SUBSTRATE_ONLY. Compatibility: SRM `a03bd4a` + AWC `168338f` (re-pin on drift).

## Scope

1. `test/fixtures/local-agent-stdio-server-realfs.js` (new): env-driven (SUNDAY_TEST_FS_ALLOWLIST JSON validated via validateAllowlist, SUNDAY_TEST_STATE_DIR) LocalAgent over createAllowlistReadExecutor + createFsDirectoryReader + fs agent store, launched via startOfflineLocalAgentStdio behind the same double gates.
2. `test/test-sunday-stdio-realfs.js` (new, RED-first): real stdio subprocess over a temp tree — initialize / tools-list / real-file read through the WHOLE chain / outside-allowlist + traversal denials / dedup across a SECOND subprocess over the same state dir / invalid-allowlist fail-closed exit.

## Review assignment

Independent reviewer: GPT-6 Sol (exact-SHA, harness outside the worktree). JEV: SPENDING_GATED (recorded; no paid calls).

## Forbidden

Standard set; ZERO production-file changes (everything under test/); existing fixture + gates untouched; temp trees only.

## Checkpoint log (append-only)

- [2026-10-15] WO created. Lane issue #674 verified real BEFORE naming; one clean `Issue: #674` line. No source mutation yet.
