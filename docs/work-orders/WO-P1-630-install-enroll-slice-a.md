# WO-P1-630 — INSTALL-ENROLL slice A: offline enrollment contract + RDC separation

Status: DONE — SRM PR #21 merged 2026-10-12 at `cdb669e` (pinned-head `da1d727`); review chain SRM PR #21 comment 6126638338; claim released #630 comment 6126647821
Issue: #630
Parent: #607 (INSTALL-1 / CUTOVER-RO); operator steer 2026-10-12 "Native Windows Enrollment Unblock"; audit evidence #607 comment 6122338729.
Risk: R3 — authentication, enrollment, trust and remote access.
Topology: CROSS_REPO architecture; EXECUTION_SUBSTRATE_ONLY implementation (SRM source; AWC untouched except this doc).
Compatibility gate: SRM `f4bdd57465e79874eb3c371b4b0602729a241467` + AWC `061e8eb30a9c08465bb23c2407020206ac609b50` (read-only references). Drift before merge → re-pin + focused review.

## Scope (slice A — offline; proceeds regardless of the issuer decision)

1. Config-root separation (Sunday-owned root; zero foreign-root writes; RDC installs preserved).
2. Upstream health seam (allowlisted, fail-closed UNKNOWN; never unconditional true; DC target only as documented transitional default).
3. `sunday enroll` / `sunday doctor` CLI scaffolding (no PAIRED without a verified real enrollment session; secrets never echoed).
4. Pure token-verification contract module + the steer §7 RED-first matrix.

Full detail: issue #630 body and the audit (#607 c6122338729).

## Gated on the operator trust decision (options 1/2/3 in the audit)

Any DC-token→PAIRED wiring (transitional approval) or any Sunday-owned issuer implementation. Until decided: no minting, no RDC reuse, no PAIRED claims.

## Forbidden

Identity-provider invention; credential minting; RDC token reuse as PAIRED; security-boundary bypass; patient/hospital data; ESET/FortiGate changes; new public/LAN endpoints; second claim store/scheduler; live mutation canary.

## Stop conditions

- If the issuer decision lands mid-slice and changes the contract shape → park slice A remainder, re-scope.
- If SRM source requires cross-repo authority changes → separate admission.

## Checkpoint log (append-only)

- [2026-10-12] WO created after the R3 source audit (#607 c6122338729); lane issue #630 verified as a real issue BEFORE naming. Audit-only so far; no source mutation. SRM worktree for implementation TBD next iteration (wo607 worktree's `.serena/`/`.tmp/` preserved untouched).
- [2026-10-12] Operator decided OPTION 1 (Sunday-owned issuer; #630 c6122489537) — Option 2 transitional DC trust explicitly NOT approved; slice A scope unchanged (offline).
- [2026-10-12] COMPLETE — SRM PR #21 merged at `cdb669e` (pinned-head `da1d727`; worktree `A:\GitHub\_worktrees\SRM-install-enroll-a` off SRM `f4bdd57`). Delivered: `enroll-contract.ts` (pure token-verification contract; 3-arg signature seam, hasOwn key pinning, strict nbf, full typed fail-closed matrix), `sunday-config-root.ts` (`~/.sunday-device` isolation, both-direction containment refusal, foreign RDC state never touched), `upstream-health.ts` (allowlisted fail-closed probe; single-upstream posture documented), `sunday:enroll` (refuses until the Option-1 issuer exists; no PAIRED path) + `sunday:doctor` (read-only) CLIs, 3 adversarial suites. Review: 2 exact-SHA rounds on the repo-accepted separate-session GLM read-only lane (Codex Sol unavailable — typed blocker CODEX_MODEL_UNAVAILABLE_ON_ACCOUNT; r1 CHANGES_REQUIRED P1 signature-seam/P2 inherited-key-pinning + P3s → repaired → r2 PASS with behavioral evidence; chain: SRM PR #21 c6126638338). CI: codespell SUCCESS, CLEAN. Post-main verify on merged main: 3/3 new suites + agent-gate + pairing-state green; full-suite local baseline 89/97 with 8 failures reproduced identically on clean f4bdd57 (environment only). NO PAIRED state ever created; no issuer invented; no credentials minted. Slice-B follow-ups recorded by review: drive-root trailing-separator CONTAINS edge; multi-origin failover; lexical-alias isolation note. NEXT: Milestone 2 — the bounded read-only Option-1 issuer architecture/threat-model proposal (authorized by c6122489537 item 2).
