# WO-P1-110 — Frozen installer install/uninstall E2E CI gate

Created: 2026-08-29
Owner: GPT-5.6 Sol release verification lane
Status: COMPLETE / MERGED PR #145 / POST-MERGE MAIN CI GREEN
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
- additive `scripts/verify_frozen_installer_e2e.py`
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
- GREEN: workflow initially invoked a PowerShell verifier; exact-head CI exposed its output-stream bug and the accepted repair uses `scripts/verify_frozen_installer_e2e.py` after Portable smoke and before artifact upload.
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

## Merge / exact-main closeout — 2026-08-29

PR #145 final head `b7a2c77df4ba413df40d2fcdfdd0388615e899ab` passed exact-head CI run `33247761698` on Windows, Ubuntu, and macOS. Windows executed the real frozen Setup install/uninstall E2E successfully after Portable smoke. Remote scope was exactly four intended files and review/issue comments were zero.

PR #145 was SHA-guard squash-merged as `047326966ded5d2941d57411782f8a85b6d9121a`. Post-merge main CI run `33248070680` passed all three OS jobs and repeated the frozen Setup install/uninstall E2E successfully on that exact main SHA.

Exact-main Windows Actions artifact: ID `9713566612`, name `A-Sunday-Conductor-Windows-047326966ded5d2941d57411782f8a85b6d9121a`; artifact ZIP SHA-256 `1d52ace01664487566096461833099c8dbe40f2fed4ab75c8a0d0d972a4a702a`; Portable SHA-256 `6728ce75349b6975c9f774868ff47adb1793264abe30e3d194c1c376aa0c1675`; Setup SHA-256 `1c4a1166d2af4509df184bc41f839a0fabd7fb0d45e6e2772f01346b93a89d4a`.

Local live v0.6.0 was never mutated by this CI-based E2E. Re-check after acceptance proves installed exe and Start Menu shortcut remain byte-identical to their pre-test hashes; Desktop shortcut remains absent as before. WO-P1-110 is complete.
