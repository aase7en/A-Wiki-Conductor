# WO-P1-101 โ€” Tunnel-client checksum required before install

Date: 2026-08-28
Owner: GPT-5.6 Sol
Status: REVIEW_READY / LOCAL GREEN
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-tunnel-checksum`
Branch: `fix/wo-p1-101-tunnel-checksum-required`
Base: `origin/main@fd6df8cca3aa8b455d5cc1acc30e13709774c664`
Parent: `WO-P1-096` CR-1 release hardening

## Goal

Fail closed when installing/upgrading unsigned tunnel-client release artifacts. A downloaded Windows ZIP must have a matching entry in the release `SHA256SUMS.txt` before extraction or replacement of the installed binary.

## Proven gap

`install_tunnel_client()` currently verifies SHA256 only when the checksum asset downloads successfully and contains a matching entry. Missing checksum asset, download/parse failure, or missing entry silently skips verification and continues installation. Upstream v0.0.13 Windows executable is not Authenticode-signed, so this fail-open path violates the WO-P1-096 checksum/provenance release gate.

## Reuse classification

**EXTEND** the existing GitHub release asset selection, `_download`, `_find_checksum`, SHA256 calculation, version floor, and atomic `os.replace`. Do not add a second updater or trust store.

## Allowed scope

- `src/a_conductor/setup_wizard.py`
- `tests/test_setup_wizard.py`
- this work order

Forbidden: PR #108 installer files, PR #125 recovery files, coordination SSoT, AHA/North-Star scopes, live connector fleet.

## Acceptance

1. latest release without `SHA256SUMS.txt` -> fail before ZIP install;
2. checksum download/read failure -> fail closed;
3. checksum file without the selected asset entry -> fail closed;
4. SHA256 mismatch -> existing mismatch error, no replacement;
5. matching checksum -> version verification then atomic replacement succeeds;
6. failed verification leaves an existing binary byte-for-byte unchanged;
7. downloaded ZIP/checksum scratch files are cleaned;
8. focused setup tests and relevant broader setup/instance tests pass;
9. exact-head 3-OS CI green before merge.

## Verification checkpoint

- baseline: `tests/test_setup_wizard.py` 22 passed;
- RED: three fail-open cases failed on the old implementation (missing checksum asset, checksum download failure, missing checksum entry);
- GREEN: focused setup suite 26 passed;
- broader setup/instance/control regression: 106 passed, one pre-existing invalid-escape DeprecationWarning;
- `git diff --check`: PASS;
- secret-like added-line scan: PASS;
- behavior now downloads and validates `SHA256SUMS.txt` before the ZIP, requires a valid 64-hex entry for the selected asset, rejects mismatch before extraction/replacement, and removes both checksum/ZIP scratch files in `finally`.

Next: compile/scope audit -> commit/push PR -> exact-head 3-OS CI -> merge/cleanup if green.
