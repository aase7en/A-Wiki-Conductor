# WO-P1-630 — INSTALL-ENROLL slice A: offline enrollment contract + RDC separation

Status: IN_PROGRESS (claimed 2026-10-12 by the GLM-5.3 MAX wake lane; implementation pending)
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
