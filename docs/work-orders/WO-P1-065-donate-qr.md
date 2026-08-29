# WO-P1-065 — Donate PromptPay QR asset

Created: 2026-08-25
Owner: GLM 5.3 Max (user-authorized substitution while GPT-5.6 Sol is on weekly limit)
Status: COMPLETE / MERGED
Base: `origin/main` `acd77b4c9fb04101557a12657779db50d5d543dd`
Branch: `assets/donate-promptpay-qr`

## Scope (all files touched)

- `assets/donate-promptpay-qr.png` (new, 253,458 bytes, PNG magic verified)
- `.github/DONATE.md` (filled the PromptPay/TrueWallet number; source: decoded locally from the user's own QR image via opencv-headless — EMVCo payload `0066992654265` → domestic `099-265-4265`, currency THB, static QR; TrueWallet is listed with the same number per the dialog's combined "PromptPay / TrueWallet" flow — owner should confirm TrueWallet uses the same number)
- `docs/work-orders/WO-P1-065-donate-qr.md` (this file)
- `docs/agent-collab/AGENT_TASKS.md` (one GLM row — small known merge-conflict surface with the same file's edit on `fix/gpu-context-ui-repaint`; trivial resolution, both are additive rows)

No product code changes: `desktop_ui.open_donate_dialog` / `_find_donate_qr` already expected exactly `assets/donate-promptpay-qr.png` (dev layout `repo/assets/`, frozen layout bundled `assets/`), and `scripts/build_portable.py` already bundles the whole `assets/` directory, so no build-script change is required.

## Problem

The user placed the PromptPay QR at `assets/donate-promptpay-qr.png.png` (double extension) on 2026-08-25, so the Donate dialog could not find it and kept showing the "add a QR code" placeholder text.

## Fix

Rename to the expected filename. That is the entire functional change.

## Overlap check for GPT-5.6 Sol (recorded per user instruction)

- `fix/gpu-context-ui-repaint` (GPT's open branch, tip `ffff853`) touches: `src/a_conductor/gpu_particle_logo.py`, `tests/test_gpu_particle_logo.py`, `docs/work-orders/WO-P1-063-...md`, `docs/agent-collab/AGENT_TASKS.md`.
- This branch touches: `assets/donate-promptpay-qr.png` (new), this WO, and one row in `AGENT_TASKS.md`.
- **File-level overlap: none** except the additive `AGENT_TASKS.md` row noted above. No code overlap. Safe to merge in either order.

## Evidence

- PNG magic bytes verified (`89 50 4E 47 0D 0A 1A 0A`).
- Tests with existing tolerance for the QR being present or absent: `tests/test_wizard_ui.py::test_donate_qr_finder_returns_none_when_missing` asserts `result is None or result.is_file()`; `test_donate_dialog_opens` and `tests/test_e2e_all_buttons.py::test_donate_button_opens_dialog` only assert the dialog opens. Run results recorded in the PR.
- Frozen bundling: `--add-data assets;assets` already ships the whole folder (same mechanism as `sunday-family-particle.png`, enforced by the CI archive gate).

## For GPT to review later (visual authority stays with you)

1. Open Donate in a real window: QR image renders (not the placeholder text), reasonable size/position next to the GitHub Sponsors button.
2. Confirm the QR scans to the intended PromptPay account (owner-provided image; GLM cannot verify content).
3. If you want a Setup-payload copy (installer also embedding the QR directly), that is a `build_installer.py` change in your lane — not attempted here.

## Checklist

- [x] Asset renamed in user's main worktree (dev builds show QR immediately)
- [x] Committed on clean branch from acd77b4
- [x] Work order + AGENT_TASKS record for GPT
- [ ] CI green on PR
- [ ] GPT visual acceptance after weekly limit resets

## Repo-health reconciliation - 2026-08-29

- Historical execution/checklist text above is preserved as evidence; stale status is superseded by accepted GitHub state.
- PR #80 merged into main as `f4ecf9a8e5a3aa9f92e3cd4ee4c16125f45e43e2`.
