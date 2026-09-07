# WO-P1-164 — COLLAB Stale-Row Reconciliation (117/118/119/120/163)

Date: 2026-09-07
Owner: GLM-1 / GLM-A (ZCode) — docs-only single-writer
Status: IMPLEMENTED / READY_FOR_INDEPENDENT_REVIEW
Repository: `aase7en/A-Wiki-Conductor`
Base: `origin/main@a887e7a76184d8f5dc22446a159087b6f9cab78d` (post-PR #224)
Branch: `docs/wo-p1-164-collab-row-reconciliation`
Priority: P3 coordination hygiene (duplicate-work hazard removal)

## Problem

The COLLAB in-progress claims table contradicted the authoritative work-order docs on `origin/main`:

| Row said | WO doc says | Hazard |
|---|---|---|
| `WO-P1-117` READY_FOR_CLAIM | IMPLEMENTED / REVIEW_PENDING | A new agent could re-implement a frozen GPT-integrator lane |
| `WO-P1-118` QUEUED (blocked by 117) | COMPLETE — 118A+118B MERGED / POST_MAIN_GREEN / RELEASED | Lane wrongly held closed |
| `WO-P1-119` READY_FOR_CLAIM | SOURCE_FROZEN / REVIEW_PREP | A new agent could re-implement a frozen GPT-integrator lane |
| `WO-P1-120` READY_FOR_CLAIM | RELEASED | Duplicate hardening work on a released seam |
| `WO-P1-163` FOLD_CANDIDATE / CONDITIONAL_RELEASE | Fold merged via PR #224 on 2026-09-07 | Hotspot appeared still held |

## Evidence trail (read-only, verified before editing)

- WO docs on `origin/main`: `docs/work-orders/WO-P1-117-provider-dispatch-admission-safety.md` (`Status: IMPLEMENTED / REVIEW_PENDING`), `WO-P1-118-provider-config-generation-policy.md` (`COMPLETE - WO-P1-118A + WO-P1-118B MERGED / POST_MAIN_GREEN / RELEASED`), `WO-P1-119-provider-output-persistence-safety.md` (`SOURCE_FROZEN / REVIEW_PREP`), `WO-P1-120-elastic-capacity-fencing-recovery.md` (`RELEASED`).
- Main history: `beda832 docs: mark WO118 released`; `049894d docs(runtime): close WO120 release frontier`; `6f19c92 docs: refresh WO-P1-117 review evidence`.
- Implementation branches pushed: `fix/wo-p1-117-provider-dispatch-admission-safety` @ `6f19c924e8a75a3bacd6542ff949407ab6d86130`; `fix/wo-p1-119-provider-output-persistence-safety` @ `aad64cd837ba4cf01774900755b923bb59540d65`.
- PR #224 (WO163 fold): MERGED, head `45e4924ee706f7d6d3f2e3ae43ea355e53b9b43d`, merge `a887e7a76184d8f5dc22446a159087b6f9cab78d`.

## Change

`COLLAB.md` only (plus this WO doc):

1. Rows 117/118/119/120/163 corrected to match their WO-doc statuses verbatim, with evidence pointers. No lane ownership changed: 117/119 remain GPT-integrator lanes awaiting their review flow; 118/120 released; WO163 fold merged.
2. WO-P1-164 claim row added (this work order) — single-writer on the COLLAB hotspot; WO163 had released it.
3. Dated reconciliation note added under the table warning that a stale `READY_FOR_CLAIM` on an implemented/released lane is a duplicate-work hazard.

## Forbidden (unchanged)

No source/runtime/DB/credentials mutation; no A-Wiki Issue #54/P0-B/ZRA work; no takeover of GPT-owned frozen lanes (117/119); no live provider/tunnel/worker mutation; no self-merge.

## Acceptance

- Docs-only diff; CI green on the exact PR head.
- Independent review confirms each corrected row cites real WO-doc status and real merge/branch SHAs.
- GLM does not merge; acceptance/merge belongs to the independent gate per repo policy.
