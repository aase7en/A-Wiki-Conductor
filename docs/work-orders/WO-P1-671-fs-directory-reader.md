# WO-P1-671 — fs-backed DirectoryReader library module (unwired)

Status: OPEN — implementation lane (SRM source; AWC docs only)
Issue: #671
Parent: #495 (operator steer 2026-10-15); predecessor WO-P1-662 (the DirectoryReader seam).
Risk: R2 — library-only fs reads; no trust-surface change (unwired).
Topology: EXECUTION_SUBSTRATE_ONLY. Compatibility: SRM `998a028` + AWC `1b92394` (re-pin on drift).

## Scope

`src/sunday/fs-directory-reader.ts`: `createFsDirectoryReader(): DirectoryReader` — `{read, list, isFile}` per the WO-662 seam; fail-closed nulls (never throws); sorted deterministic listing; stat-based isFile (symlinks followed, documented — lexical containment stays the executor's contract). NOT imported by any entrypoint/adapter/script in this slice. RED-first suite (temp trees; no writes — tree hash before/after).

## Review assignment

Independent reviewer: GPT-6 Sol (gpt-6-sol codex exec, exact-SHA, harness outside the worktree). JEV: SPENDING_GATED (recorded; no paid calls).

## Forbidden

Standard set; no live wiring; no realpath containment changes; no secrets.

## Checkpoint log (append-only)

- [2026-10-15] WO created. Lane issue #671 verified real BEFORE naming; one clean `Issue: #671` line. No source mutation yet.
