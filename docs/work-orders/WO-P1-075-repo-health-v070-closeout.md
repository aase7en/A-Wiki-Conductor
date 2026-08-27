# WO-P1-075 — Repo health 100 + v0.7.0 closeout

Status: REVIEW
Owner: GPT-5.6 Sol
Branch: `docs/repo-health-100`
Base: `f9dff0b1ad169af376d102018eb859cdbea36777`

## Objective

Reconcile stale repository continuity after the merged v0.7 UI/release line, then publish v0.7.0 only from an exact post-reconciliation main SHA whose CI, frozen artifacts, and sandbox installation acceptance are verified.

## Verified merged release line

- PR #99 `PROJECT DISK` async release blocker — merge `e8195b1d16799140068abb09297198df4a725149`.
- PR #100 worker display-name repair — merge `12a4c56db5704706ef3b2b25e291f2639627c05c`.
- PR #101 live AI Execution Slots — merge `4ad0b8e48ecd07686d1c090aa8153215cbf4632f`.
- PR #103 PROJECT DISK monochrome particle magnitude — merge `f85ee4763215bbf7c5bf7050f779ec5c48810727`.
- PR #105 interactive offline HTML Guide — merge `f9dff0b1ad169af376d102018eb859cdbea36777`.
- Exact-main CI run `33005521278` for `f9dff0b1` passed Windows + Ubuntu + macOS. Windows passed GUI, core, clean Portable/Setup build, frozen archive verification, Portable smoke, and artifact upload.

## Release boundary decision

The historical `be8a45d` v0.7.0 candidate pin is superseded by later user-authorized release work that intentionally added/fixed P1 release blockers and UI acceptance items. v0.7.0 now targets the exact merge SHA of this repo-health PR after its own CI passes. It must not absorb later unrelated work merely because `main` moves.

Explicitly excluded until separately green/merged:
- PR #102 `fix/ge-005a-glob-conflict` — OPEN; Windows CI failing.
- PR #104 `feat/ge-6-scheduler` — OPEN; Windows CI failing.

## SSoT reconciliation scope

- `CURRENT-WORK.md`
- `handoff.md`
- `COLLAB.md`
- `CHANGELOG.md`
- WO-P1-073 and WO-P1-074 closeout evidence
- branch/worktree inventory and cleanup evidence

## Branch/worktree cleanup contract

Delete only branches/worktrees proven merged or superseded and clean. Preserve:
- shared `A:\GitHub\A-Wiki-Conductor` main worktree (do not mutate it);
- GLM GE-005A and GE-6 worktrees while PR #102/#104 are OPEN;
- any worktree with protected user/uncommitted work.

Merged P4/P5 worktrees/branches may be removed after ancestry + PR merge verification.

## Release acceptance

1. Repo-health remote diff audited.
2. Repo-health PR CI green Windows/Ubuntu/macOS.
3. Merge/fetch exact resulting `origin/main` SHA.
4. Download Windows artifact produced by CI for that exact SHA.
5. Verify artifact hashes and frozen archive contents.
6. Sandbox install using `--target` into an isolated directory; do not operate on live ports 18011–18015.
7. Installed/frozen smoke green; uninstall/cleanup preserves user DB and live connector fleet.
8. Publish GitHub Release `v0.7.0` from the exact verified SHA with Setup/Portable/notices.
9. Verify release assets/public download.
10. Cleanup obsolete release worktree/branches and report remaining active GLM branches only.

## Current evidence

- `origin/main = f9dff0b1ad169af376d102018eb859cdbea36777` before this docs branch.
- Open PRs are #102 and #104 only; both remain Windows-red and are excluded from v0.7.0.
- P5 worktree/branch `feat/interactive-html-guide` was verified merged via PR #105 and removed locally/remotely.

## Acceptance checklist

- [x] Continuity files reconciled.
- [x] WO-P1-073 / WO-P1-074 closed with merge/CI evidence.
- [x] CHANGELOG reflects v0.7.0 shipped UI/release work.
- [x] `git diff --check` clean.
- [ ] Remote PR diff audited.
- [ ] Repo-health CI green on 3 OS.
- [ ] Repo-health merged and exact main fetched.
- [ ] Exact-main Windows artifact downloaded and hashes recorded.
- [ ] Sandbox install/frozen acceptance green.
- [ ] GitHub Release v0.7.0 published and verified.
- [ ] Obsolete branches/worktrees removed; active GLM branches preserved.
