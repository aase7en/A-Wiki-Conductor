# A-Sunday Conductor — Current Work

Last updated: 2026-08-22 (GLM 5.3, post E2E + rename + reinstall)

## Current phase

**No open work orders.** Latest: E2E real-system suite (PR #35), product rename to A-Sunday Conductor (PR #36), and the local machine reinstall are all complete.

## Source-of-truth rule

Do **not** reconstruct task state from chat memory. Use: actual repo/GitHub state → CURRENT-WORK.md → handoff.md → active work order → PROJECT-PLAN/contracts.

## Verified completed work (this session, main `22bc0e6`)

- **PR #35**: `tests/test_e2e_real_system.py` — 24 tests through `DesktopControlService` against the real DB, real connector discovery, a sandbox copy of the live wastewater instance, and the real GitHub upstream API. Fixed 2 bugs found by the suite: `re.sub` regex-escape crash in `instance_rebind.py` for backslash paths, and `DesktopControlService.open()` missing `instances_root`. Module auto-skips on machines without the local instances/projects (CI).
- **PR #36**: product display name → **A-Sunday Conductor**. New single-source `src/a_conductor/branding.py` (`APP_NAME`) drives all window titles; installer (target dir, Start Menu/Desktop shortcuts, HKCU entry) and the PyInstaller exe name follow it. Docs updated; PROJECT-PLAN records the naming decision; contracts keep the internal codename "A-Conductor". Deliberately unchanged: package `a_conductor`, CLI `a-conductor`, smoke markers, and the data folder `%LOCALAPPDATA%\A-Conductor\` (guarded by `test_data_directory_keeps_legacy_name_for_upgrade_continuity`).
- **Local reinstall (evidence)**: old pre-PR#18 install fully removed (files, shortcuts, old HKCU key). New build installed at `%LOCALAPPDATA%\Programs\A-Sunday Conductor\`; Start Menu + Desktop shortcuts and HKCU `DisplayName` verified. Installed exe smoke: `A-CONDUCTOR_SMOKE_OK projects=4 workers=3` — the preserved user database loads with all 4 projects.
- Naming rationale (user decision 2026-08-22): "A" = the user's AI co-developer, "Sunday" = น้องซันเดย์ (user's son) + matches the company name, "Conductor" = founding codename.

## Full suite at close

866 passed, 0 failed (841 prior + 24 E2E + 3 branding − overlap; E2E runs only on machines with the real instance roots).

## Next safe action (user picks)

(a) Trial the installed app from Start Menu ("A-Sunday Conductor") and exercise the new surfaces (ตั้งค่า / เปลี่ยนโปรเจกต์ / เช็คอัปเดท / Config tooltips); (b) next §13 milestone — open a new work order + reuse gate before implementation; (c) backlog item: MCP gateway (DECISION_REQUIRED).

## Mandatory boundaries

- MCP gateway enforcement stays `DECISION_REQUIRED` (backlog).
- A-Wiki remains brain authority. No machine-wide env changes.
- Do not rename the internal package/CLI/data folder without an explicit migration decision.

## Escalation rule

GLM 5.3 owns routine implementation, TDD, regression, docs, PR/CI, merge. Escalate to GPT-5.6 Sol UltraHigh only for genuinely hard cross-cutting defects/architecture ambiguity, after checkpointing state.
