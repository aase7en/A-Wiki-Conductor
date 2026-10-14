# WO-P1-656 — allowlist directory configuration + doctor row

Status: DONE — SRM PR #30 merged 2026-10-14 at `660ad00` (pinned-head `eb91eba`); review chain: GPT-6 Sol 3 rounds (r1 CHANGES_REQUIRED P1 path-forms + P2 control-char spoofing → `525c0b3`; r2 CHANGES_REQUIRED 2xP1 normalized-prefix + mid-segment → `eb91eba`; r3 PASS zero findings); claim released #656 comment 6164346276
Issue: #656
Parent: #495 (overnight Priority 4 continuation); predecessor WO-P1-653 (fs state store + doctor rows, `86ab83c`).
Risk: R3 — path-validation seam (future executor consent surface); offline/test-only.
Topology: EXECUTION_SUBSTRATE_ONLY. Compatibility: SRM `86ab83c` + AWC `30d8cbd` (re-pin on drift).

## Scope

1. `src/sunday/allowlist-config.ts` — typed allowlist: validated absolute Windows/UNC directory paths (normalize; reject `..` segments, NUL, non-strings, length > 1024; dedupe post-normalization; cap 64); fail-closed load (missing → null; corrupt/wrong-shape/null-file → typed ALLOWLIST_CORRUPT — never silently empty); validated atomic save; pure `inspectAllowlist` (count + first-entry preview only).
2. Doctor CLI row (ABSENT / N directories + preview / CORRUPT typed).
3. RED-first `test/test-sunday-allowlist-config.js` (validation matrix, fs roundtrip, typed corrupt rows incl. null-file, cap/dedupe, atomicity, CLI subprocess rows).

## Review assignment

Independent reviewer: GPT-6 Sol (`gpt-6-sol` codex exec read-only HIGH, exact-SHA, harness OUTSIDE the worktree). JEV: SPENDING_GATED (recorded).

## Forbidden

Standard B-lineage set; no real executor wiring (later slice); no filesystem mutation beyond the config file under the Sunday/test root; no secrets.

## Checkpoint log (append-only)

- [2026-10-14] WO created. Lane issue #656 verified real BEFORE naming; one clean `Issue: #656` line. No source mutation yet.
