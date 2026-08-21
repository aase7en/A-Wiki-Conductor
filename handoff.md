# HANDOFF — A-Conductor

Last updated: 2026-08-21 (session 4 end)

## Current objective

Own-brand product delivered and installed on this machine. Awaiting user trial + next milestone.

## Status

`COMPLETE` for the authorized scope (setup.exe + icon + Start Menu; de-brand with credits-only reference; minimal no-shortcut UI with guide button; toggle settings for project/tools/languages; CLI-styled).

## Baseline

- branch `main` at merge `ec16587` (PR #17); PRs #13-#17 CI-green
- installed app at `%LOCALAPPDATA%\Programs\A-Conductor` (Start Menu + Desktop shortcuts, HKCU uninstall entry); installed `--smoke` PASS
- artifacts in repo (gitignored dist/): `dist\A-Conductor.exe`, `dist\A-Conductor-Setup.exe`
- final suite 787 passed, 0 failed

## What the next agent must know

- WO-P1-051 closed with evidence; build entry points: `scripts/build_portable.py` (hardened vs Defender PE races), `scripts/installer_main.py` (per-user install/uninstall).
- Settings v2 fields (`project_path`, `enabled_languages`) round-trip through the store and render into engine config; dialog v2 exposes them as toggles.
- Unsigned-exe reality: automated execution of fresh builds may be Defender-blocked; interactive SmartScreen click-through is the expected first-run flow (documented in USER-GUIDE).
- Wastewater connector instance remains live (port 18013).

## Safety state

- No admin actions taken; install is per-user only (HKCU + user profile paths). Uninstaller registered.
- No real connector instance start/stop by automated tests tonight; the one real install was the user-requested deliverable and is reversible via Add or remove programs.

## Next safe action

Read CURRENT-WORK.md "Next safe action"; open a new work order + reuse gate before implementation.
