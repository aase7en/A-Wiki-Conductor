# WO-P3-135 — Provider Evidence Defect Lessons

Date: 2026-09-02
Owner: GPT-5.6 Sol
Status: VERIFIED / READY_FOR_PR
Priority: P3 reliability memory
Base: `b6d50921035ae6ec6d32b6c05b3f723530b8c68d`
Worktree: `A:\GitHub\A-Wiki-Conductor-wo135-defect-lessons`
Branch: `docs/wo-p3-135-evidence-lessons`

## Goal
Persist two already-proven WO128 lessons so future bounded evidence reads cannot regress chronology or persisted-corruption handling.

## Allowed scope
- `DEFECT_LESSONS.md`
- this work order only

## Forbidden
- all `src/**` and `tests/**`
- CURRENT-WORK / handoff / COLLAB / AGENT_TASKS
- WO134 mutable scope
- PR183/AiPASS scope
- live Workers/tunnels, WO096, release/version state

## Acceptance
- Defect Memory numbering remains monotonic from #46 to #47/#48.
- #47 records semantic instant normalization before bounded LIMIT.
- #48 records persisted read-decoder revalidation of writer invariants.
- Evidence is historical and names only verified WO128 review/CI/merge facts.
- No source/test/shared-continuity/live-runtime/release mutation.

## Verification
- `git diff --check`
- UTF-8 decode for both changed files
- heading uniqueness / monotonic numbering check
- changed-path allowlist
- added-line secret/private-key/token scan

## Checkpoint — 2026-09-02
- WO128 reviewed exact head: `a9f4fe6a92367650e7c22caaa9df9e8c148cf3ad`.
- GLM review `wo128-glm-review-002`: PASS, P0/P1/P2=0.
- exact-head CI `33586307363`: SUCCESS.
- PR #184 merge: `b6d50921035ae6ec6d32b6c05b3f723530b8c68d`.
- post-main CI `33591789871`: SUCCESS.
- Next: deterministic docs audits -> commit -> push -> docs-only PR.

### Verification result
- `git diff --check`: PASS.
- UTF-8 strict decode: PASS.
- Defect headings end `45, 46, 47, 48`; unique: PASS.
- Changed-path allowlist: exactly `DEFECT_LESSONS.md` + this WO: PASS.
- Added-content secret/private-key/API-key scan: PASS.
- Base still equals `origin/main` at `b6d50921035ae6ec6d32b6c05b3f723530b8c68d` before commit.
