# WO-P1-662 — allowlist-consuming read executor (strict at USE time)

Status: OPEN — implementation lane (SRM source; AWC docs only)
Issue: #662
Parent: #495 (overnight P4); predecessors: WO-P1-656 (strict validator), WO-P1-659 (canonical surface + the USE-time invariant).
Risk: R3 — the future real read-execution trust seam; offline/injected only.
Topology: EXECUTION_SUBSTRATE_ONLY. Compatibility: SRM `d1da117` + AWC `c5dbbf8` (re-pin on drift).

## Scope

`src/sunday/allowlist-executor.ts`: `createAllowlistReadExecutor({ allowlist, reader })` → `ExecutorOutcome`-shaped executor (drop-in for LocalAgentRuntime.executor). USE-time strict validation of every entry (legacy loose forms not usable); lexical containment under a strict-valid entry; typed denials `PATH_OUTSIDE_ALLOWLIST` / `ALLOWLIST_UNUSABLE` + reused path-denial semantics via the injected `DirectoryReader` seam ({ read, list } — NO fs import). Tests with a fake virtual-tree reader incl. one LocalAgent compose row. NOT wired to any live surface.

## Review assignment

Independent reviewer: GPT-6 Sol (gpt-6-sol codex exec read-only, exact-SHA, harness outside the worktree). JEV: SPENDING_GATED (recorded).

## Forbidden

Standard set; no fs import in the module; no live wiring (stdio adapter untouched); no weakening of shipped contracts.

## Checkpoint log (append-only)

- [2026-10-14] WO created. Lane issue #662 verified real BEFORE naming; one clean `Issue: #662` line. No source mutation yet.
