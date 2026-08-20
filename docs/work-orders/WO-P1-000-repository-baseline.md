# WO-P1-000: Local Repository Safety Baseline

Status: done
Lane/files: `.gitignore`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-000-repository-baseline.md`, existing C1 documentation/contracts for initial local commit
Branch: bootstrap -> `main`
Model tier: cheap-ok

## Goal + Acceptance criteria

Create a **local-only Git safety baseline** before production implementation, without creating/publishing a GitHub repository or changing A-Wiki.

Acceptance:
- root Git repository initialized on branch `main`;
- machine/runtime-local Serena state is ignored;
- secrets/local runtime artifacts have safe ignore defaults;
- all intended project planning/contract/coordination files are included in the first local commit;
- repository is clean after the initial commit;
- no Git remote exists and no push is performed;
- `CURRENT-WORK.md` and `handoff.md` record the resulting HEAD.

## Reference pattern

- `AGENTS.md` safety rules.
- `PROJECT-PLAN.md` repository safety + continuity requirements.
- A-Wiki cross-agent work-order protocol: coherent batches should be committed early; destructive Git is forbidden.

## Steps

1. Create conservative root `.gitignore` for local Serena/runtime/secrets artifacts.
2. Initialize local Git with branch `main`.
3. Inspect `git status --short` before staging.
4. Stage only project files intended for the baseline.
5. Review staged names/diff summary.
6. Commit one local bootstrap baseline.
7. Verify branch/HEAD/clean status/no remotes.
8. Update checkpoint, current work, and handoff.

## Forbidden

- No GitHub repository creation.
- No remote configuration.
- No push/fetch/pull.
- No A-Wiki mutation.
- No reset/clean/stash/rebase/merge.
- No secret/API-key material.
- No production runtime/UI code.

## Verify commands

- `git branch --show-current` -> `main`
- `git status --short` -> empty after commit
- `git rev-parse HEAD` -> valid SHA
- `git remote -v` -> empty
- `git check-ignore .serena/project.local.yml` -> ignored

## Checkpoint log

- [2026-08-20] ChatGPT/Sunday-Conducter: opened local-only Git baseline after WO-C1-001 completed. Remote publication remains blocked by `DR-C1-001`.

- [2026-08-20] ChatGPT/Sunday-Conducter: local Git initialized on `main`; `.serena/` confirmed ignored; no remotes configured; root baseline commit `3ed22df0d884cf15729167d923ec4a0e32593662`; worktree clean after commit. Git ownership guard requires exact per-command `-c safe.directory=A:/GitHub/A-Wiki-Conductor`; global config was intentionally not modified.
