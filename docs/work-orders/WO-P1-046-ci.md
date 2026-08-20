# WO-P1-046: GitHub Actions CI

Status: complete
Lane/files: `.github/workflows/ci.yml`, `docs/work-orders/WO-P1-046-ci.md`
Branch: chunk/p1-046-ci (PR)
Model tier: mid

## Goal

Make every push/PR verifiable on GitHub so bugs are easy to localize and fix (user requirement 2026-08-20: small chunks + PRs for easy bugfixing).

## Reuse classification

`NEW (infra)`: no existing CI in this repository; no A-Wiki CI overlap (per-repo pipeline).

## Design

- `windows-latest` — the product runtime targets Windows (owned-process control, PowerShell inspection, tunnel boundaries); tests already guard non-Windows where needed.
- Python 3.11, `pip install -e .` (also validates packaging), full pytest suite, then `python -m a_conductor --smoke` against a runner-temp database.
- Tests were audited for machine-specific paths before adding CI: all `tunnel-client.exe` references are dummy executables under temp dirs; `C:\Tools`-style strings are environment fixtures, not filesystem requirements.

## Completion evidence

- See the CI run on this PR (first run) and subsequent runs.
- Local pre-check: full suite 741 passed, 1 skipped; smoke OK.

## Forbidden

- No secrets; no deployment; no external side effects.
