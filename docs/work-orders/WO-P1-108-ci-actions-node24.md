# WO-P1-108 — GitHub Actions Node 24 runtime refresh

Created: 2026-08-29
Owner: GPT-5.6 Sol CI maintenance lane
Status: ACTIVE / BOUNDED MAINTENANCE
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-ci-actions-v7`
Branch: `fix/wo-p1-108-ci-actions-node24`
Base: `origin/main@392047a0395f30cc1d6ed7d8c2c3f7c0457a5e37`

## Trigger

Hosted CI repeatedly warns that `actions/checkout@v4`, `actions/setup-python@v5`, and `actions/upload-artifact@v4` are Node 20 actions being forced onto Node 24.

Official GitHub release check on 2026-08-29:
- `actions/checkout` latest `v7.0.1`;
- `actions/setup-python` latest `v7.0.0`;
- `actions/upload-artifact` latest `v7.0.1`.

## Scope

Allowed:
- `.github/workflows/ci.yml`
- `.github/workflows/sign.yml`
- `tests/test_build_installer.py` (workflow contract expectation only)
- this work order

Forbidden:
- source/tests outside CI configuration;
- PR #131 coordination/worker-lease files;
- live connector/runtime mutation;
- release publication.

## Acceptance

- every targeted old action reference is replaced with the current Node-24-compatible major `@v7`;
- no unrelated workflow logic changes;
- YAML parses successfully;
- `git diff --check` passes;
- exact-head CI passes Windows/Ubuntu/macOS;
- Windows packaging/frozen smoke still passes;
- CI run no longer emits Node-20 forced-runtime warnings for these actions;
- remote diff/review and accepted-main verification pass before closeout.

## CI RED repair — 2026-08-29

Exact-head Windows CI exposed one stale contract assertion in `tests/test_build_installer.py` that required `actions/upload-artifact@v4`. Local RED reproduced the same single failure; repo-wide grep found no other old action assertions. The test expectation is updated to `@v7`; workflow behavior is unchanged.
