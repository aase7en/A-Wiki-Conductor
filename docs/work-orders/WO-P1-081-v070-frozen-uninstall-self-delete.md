# WO-P1-081 — v0.7 frozen uninstaller self-delete repair

Status: COMPLETE / MERGED
Owner: GPT-5.6 Sol
Parent: WO-P1-075 release closeout
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-v070-uninstall-fix`
Branch: `fix/v070-frozen-uninstall-self-delete`
Base: `c72a550287a8c59d2361112b489e528639adeaa6`

## Defect

Exact v0.7 CI Setup artifact installed successfully into an isolated `--target`, and the installed Portable hash matched the CI Portable. Installed smoke passed. Running the frozen installed uninstaller then returned `UNINSTALL_PARTIAL` because Windows kept `Uninstall-A-Sunday Conductor.exe` locked while it was executing, so `shutil.rmtree(target)` could not remove the target directory.

Observed error:
`UNINSTALL_FILES_FAILED: [WinError 5] Access is denied: ...\Uninstall-A-Sunday Conductor.exe`

The verification harness restored the pre-test HKCU uninstall entry and confirmed the live Start Menu shortcut hash was unchanged. Live v0.6 installation state was preserved.
## Allowed mutable scope

- `scripts/installer_main.py`
- `tests/test_installer_uninstall_self_delete.py` (new)
- this work order
- `DEFECT_LESSONS.md` for the verified prevention lesson only

Everything else is read-only.

## Required behavior

1. A frozen executable running inside the install target must never call `rmtree(target)` on itself.
2. The registered Windows `UninstallString` must be a synchronous external wrapper: copy the frozen uninstaller to an isolated temp path, run that temp copy with the exact target, wait for its exit code, then delete the temp copy with a finite retry budget.
3. The temp-copy uninstaller runs outside the target and therefore keeps synchronous target cleanup; source-mode uninstall remains synchronous as well.
4. Direct frozen in-target `--uninstall` fails closed before removing shortcuts, registry state, or files, instead of entering a known self-lock partial uninstall.
5. Shortcut and registry failures remain visible and preserve `UNINSTALL_PARTIAL` semantics.
6. Wrapper payload uses encoded literal-path-safe PowerShell; no user-controlled raw shell interpolation and no orphan/background cleanup process.
7. Non-Windows behavior remains explicit/fail-safe.

### Evidence-driven design correction

The first attempted design moved the running frozen EXE aside and launched a detached cleanup helper. Real PyInstaller/RDM containment proved the child helper did not survive/start reliably; the target could disappear while the staged EXE remained. That design is rejected. The synchronous registered wrapper is now authoritative because the parent wrapper stays alive until both target cleanup and temp-exe cleanup finish.
## Acceptance / verification

- RED regression proves frozen self-delete path cannot use synchronous `rmtree(target)`.
- Unit tests cover registered-wrapper construction, path quoting/encoding, direct in-target fail-closed behavior, temp-copy/source-mode cleanup, and failure propagation.
- Existing installer/build tests remain green.
- `python -m compileall -q src/a_conductor scripts` passes.
- `git diff --check` passes.
- Clean Portable + Setup rebuild from this branch succeeds.
- Exact sandbox install using `--target` succeeds.
- Installed Portable hash equals rebuilt Portable hash; installed smoke passes.
- Registered frozen uninstall returns success; target directory and temporary uninstaller copy both disappear within the bounded verification window.
- Pre-test HKCU uninstall entry and live shortcut hashes are restored/unchanged.
- Windows CI + Ubuntu/macOS smoke pass before merge.

## Release consequence

v0.7.0 publication remains BLOCKED until this fix is merged and the release boundary is deliberately reconciled. Do not publish the known-broken `c72a550` Setup artifact.

## Checkpoint — implementation + real frozen acceptance (2026-08-27)

Status: COMPLETE / MERGED

Evidence:
- RED after isolated `--basetemp`: 5 failures because no self-delete-safe seam existed.
- Initial detached-helper prototype was rejected after real PyInstaller/RDM evidence showed the orphan child did not reliably start/survive; no such helper remains in production code.
- Final design uses registered synchronous `-EncodedCommand` wrapper: copy installed uninstaller to isolated temp, run temp copy synchronously, propagate exit code, finite-retry delete of temp copy.
- Frozen in-target `--uninstall` now fails closed with exit 4 before destructive cleanup; real E2E confirmed target + registry + shortcut remain intact at that point.
- Focused installer regression: `27 passed`.
- `python -m compileall -q src/a_conductor scripts`: PASS.
- `git diff --check`: PASS.
- Clean Setup rebuilt with PyInstaller 6.22.2 from this branch; Portable input SHA-256 `ffafc5b23f88ec4b9e149d3d878ededdbf3aef41556ec67fcaf6354b5062390c`; Setup SHA-256 `825480aed883a0d03b7cda3c7a9c70765d973723a1da681b92ecc75a6545aae4`.
- Real registered-uninstall E2E: Setup install exit 0; installed Portable hash exactly equals rebuilt Portable; installed smoke `A-CONDUCTOR_SMOKE_OK projects=0 workers=3`; direct in-target uninstall exit 4 with `UNINSTALL_REQUIRES_REGISTERED_COMMAND`; registered `UninstallString` present and encoded; registered uninstall exit 0.
- Post-uninstall independent checks: install target GONE; sandbox temp uninstaller GONE; live HKCU restored to v0.6.0 / original install path; live Start Menu shortcut SHA-256 unchanged at `86daf2eab98442b29ed5b159b936f693900b83ff6a0d2db62f8f5adbcf115cdb`.
- Live connector ports 18011-18015, live DB, and live install files were not used as test targets.

Remaining gate:
1. pre-PR diff/security review;
2. commit/push/open PR;
3. remote diff audit;
4. Windows + Ubuntu + macOS CI;
5. post-CI final HEAD re-audit;
6. merge/fetch exact main;
7. rebuild/download exact merged artifact and repeat sandbox installed/uninstall acceptance before v0.7 publication.

## Repo-health reconciliation - 2026-08-29

- Historical execution text above is preserved as evidence; the stale status is superseded by accepted GitHub state.
- PR #107 merged into main as `64bc628e233a6fb596a7dc6d188f7cdef35b3bbe`.
