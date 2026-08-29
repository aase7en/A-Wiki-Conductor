# WO-P1-110 — Frozen installer install/uninstall E2E CI gate

Created: 2026-08-29
Owner: GPT-5.6 Sol release verification lane
Status: ACTIVE / TDD
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-installer-e2e`
Branch: `test/wo-p1-110-frozen-installer-e2e`
Base: `origin/main@c37925850cb5f096844b4e38d3b9dbdbedde6cd6`

## Trigger

The Windows CI builds and inspects both frozen executables and smokes the Portable, but it does not execute the frozen Setup through install -> registered uninstall. Local exact-main artifact E2E is currently blocked by host AV: fresh unsigned Portable and Setup files are denied for read/execute even outside the repository, while the artifact ZIP and member hashes are valid.

## Classification / scope

`EXTEND` existing release verification. Do not change installer product behavior.

Allowed:
- `.github/workflows/ci.yml`
- additive `scripts/verify_frozen_installer_e2e.ps1`
- `tests/test_build_installer.py` workflow-contract assertion only
- this work order

Forbidden: `scripts/installer_main.py`, live install, live connectors/tunnels, PR #131 scope, coordination hotspots, North Star.

## Acceptance

1. Frozen Setup rejects an unknown non-empty target with exit 5; sentinel remains byte-identical.
2. Empty sandbox target installs successfully.
3. Install marker, Start Menu/Desktop shortcuts, and HKCU uninstall entry identify the sandbox target and current app version.
4. Installed Portable SHA-256 equals the just-built Portable; frozen smoke exits 0 and creates its database.
5. Direct in-target frozen uninstall exits 4 and leaves managed state intact.
6. The registered `UninstallString` runs synchronously and exits 0.
7. Sandbox target, shortcuts, HKCU entry, and `A-Sunday-Conductor-Uninstall-*.exe` temp residue are gone after registered uninstall.
8. The verification script is reusable on a clean Windows host and performs no live-fleet operation.
9. Focused contract test, diff/compile checks, exact-head 3-OS CI, remote diff audit, merge, and post-merge main CI pass.

## Safety gate

`SAFE_TO_MUTATE = YES` in this isolated worktree for the allowed scope only. The active PR #131 worktree remains dirty/protected and its files are forbidden.

## First TDD step

RED: workflow contract must require the reusable frozen installer E2E script before the workflow is changed.

## Local TDD / verification checkpoint

- RED: workflow contract failed because no frozen Setup E2E step/script existed.
- GREEN: workflow now invokes `scripts/verify_frozen_installer_e2e.ps1` after Portable smoke and before artifact upload.
- Verifier is clean-host only and exercises unknown-target refusal, install identity, installed hash/smoke, direct-uninstall fail-closed, registered uninstall, and zero managed residue.
- On this workstation the verifier parsed/bound successfully and stopped at `HOST_REGISTRY_NOT_CLEAN` before mutation because live v0.6.0 is installed; this is the intended safety behavior.
- Local exact-main artifact PE files are independently blocked by host AV with `Access is denied`; artifact ZIP/member hashes remain valid. AV was not disabled or bypassed.
- Installer regression: **41 passed**.
- `python -m compileall -q scripts src/a_conductor`: PASS.
- `git diff --check`: PASS.

Next: scope audit -> commit/push/PR -> exact-head Windows runner executes the real frozen install/uninstall E2E -> remote diff/review audit -> merge -> post-merge main CI.

## Exact-head CI RED / harness repair — 2026-08-29

PR #145 head `a3fc38e3790cf5e4ce5296ca5fadbd85599653b2` ran CI `33244718525`.
Ubuntu/macOS passed; Windows build, archive verification, and Portable smoke passed.
The new frozen Setup E2E failed before product assertions because the PowerShell helper leaked native stdout into the function return stream, producing `System.Object[]` where a Boolean assertion was expected.
Classification: verifier-harness defect, not installer behavior.
Repair: replace the PowerShell verifier with a Python clean-host Windows verifier that captures native stdout/stderr explicitly and returns only process exit codes.
Post-repair local evidence: installer regression `41 passed`; `compileall scripts` PASS; `git diff --check` PASS; local invocation fails closed at `HOST_REGISTRY_NOT_CLEAN` before mutating the installed v0.6 state.
Next: commit/push follow-up, rerun exact-head CI, inspect the real Setup E2E result, then re-audit/merge only on green.