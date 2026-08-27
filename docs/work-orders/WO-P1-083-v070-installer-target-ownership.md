# WO-P1-083 — v0.7 installer target ownership guard

Status: IN_PROGRESS
Owner: GPT-5.6 Sol
Parent: WO-P1-075 release closeout
Depends on: WO-P1-081 / PR #107
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-v070-target-guard`
Branch: `fix/v070-installer-target-ownership`
Base: `1a1a707c0521984aa0c41e130d3ba0f901ecb3c5`

## Defect / risk

`--target` may name an existing non-empty directory. Current install copies product files into it, and uninstall later calls `shutil.rmtree(target)`. Without durable install ownership evidence, an accidental/custom target can cause unrelated user files to be deleted during uninstall.

This is a destructive-boundary release blocker discovered during WO-P1-081 security review. v0.7 must fail closed on unknown targets.

## Allowed mutable scope

- `scripts/installer_main.py`
- `tests/test_installer_target_ownership.py` (new)
- this work order

Everything else is read-only.
## Required behavior

1. New/nonexistent or empty target is allowed.
2. Successful install writes a small product-owned marker inside the target.
3. Reinstall/upgrade into a target with a valid marker is allowed.
4. Legacy pre-marker installs are allowed only when Windows HKCU `InstallLocation` exactly matches the target and expected A-Sunday Conductor executable/uninstaller identity exists.
5. Non-empty unknown target is rejected before copying or overwriting files.
6. Uninstall validates managed ownership before deleting shortcuts, registry, or target files.
7. Marker alone is not enough for Windows frozen uninstall; current HKCU install-location identity must also match, preventing an accidentally copied marker from authorizing arbitrary deletion.
8. Invalid/corrupt/missing ownership evidence fails closed with an explicit code/message.
9. No live DB, connector tree, or unrelated files are used as test targets.

## Compatibility

- Existing v0.6 installs have no marker; the exact legacy registry + expected-file path is the migration bridge.
- After first successful v0.7 install/reinstall, the marker becomes durable ownership evidence.
- Source-mode/non-Windows tests may use marker ownership without Windows registry, but production Windows frozen uninstall remains registry-bound.

## Acceptance

- TDD RED proves non-empty unknown install target is rejected and unmanaged uninstall cannot reach `rmtree`.
- Tests cover new/empty target, valid marker, corrupt marker, legacy exact registry target, mismatched registry target, and marker-copy attack case.
- Existing `tests/test_build_installer.py` + WO-P1-081 regressions stay green.
- `compileall` and `git diff --check` pass.
- Real Setup sandbox test proves: unknown non-empty target remains byte-identical after refusal; empty target installs; marker exists; installed smoke passes; registered uninstall succeeds; target disappears; temp uninstaller disappears; live HKCU/shortcut state is restored/unchanged.
- PR/3-OS CI/final-head review required before merge.

## Non-goals

- no general filesystem sandbox;
- no installer framework rewrite;
- no live connector mutation;
- no changes to release version or North Star features in this slice.

## Release consequence

v0.7 publication remains blocked until both PR #107 and this ownership guard are merged and exact-main Setup acceptance passes.

## Checkpoint — local verification + destructive-boundary E2E (2026-08-27)

Status: `LOCAL_VERIFIED / PRE_PR_REVIEW`.

Evidence:
- RED: `8 failed, 1 passed` before ownership seams existed.
- GREEN combined installer regression: `36 passed` covering WO-P1-083 + WO-P1-081 + existing installer tests.
- `python -m compileall -q src/a_conductor scripts`: PASS.
- `git diff --check`: PASS.
- Rebuilt Setup SHA-256: `ff3034166478c8b3b027869fa94950a44746b8fe7ac3737d64ed8ec3c1935403`.
- Unknown non-empty sandbox target returned exit 5 with `INSTALL_TARGET_NOT_MANAGED`; sentinel content/hash remained unchanged; no product file or marker was created; pre-test registry state remained unchanged.
- Empty sandbox target installed successfully and contained marker `{app_name: A-Sunday Conductor, format: 1}`.
- Installed Portable hash matched payload; smoke `A-CONDUCTOR_SMOKE_OK projects=0 workers=3` passed.
- Direct frozen in-target `--uninstall` still failed closed with exit 4 and preserved target/registry/shortcut state.
- Registered uninstall wrapper returned exit 0; install target and sandbox temp uninstaller both disappeared.
- Independent post-run check: unknown target GONE; install target GONE; temp copy GONE; live HKCU restored to v0.6.0 + original install path; live Start Menu SHA-256 unchanged at `86daf2eab98442b29ed5b159b936f693900b83ff6a0d2db62f8f5adbcf115cdb`.
- PR #107 / WO-P1-081 merged as `64bc628e233a6fb596a7dc6d188f7cdef35b3bbe`; this branch base commit `1a1a707` is verified ancestor of current `origin/main`.

Remaining gate:
1. commit/push/open stacked PR;
2. remote diff audit confirms only WO-P1-083 delta vs current main;
3. Windows/Ubuntu/macOS CI;
4. final HEAD re-audit + merge;
5. exact-main release artifact rebuild/download and final sandbox install/uninstall acceptance before v0.7 publication.
