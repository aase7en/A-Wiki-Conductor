# A-Sunday Conductor — Current Work

Last updated: 2026-08-22 (GLM 5.3, post v0.2.0 public release)

## Current phase

**No open work orders.** Latest: E2E suite (PR #35), rename (PR #36), installer/notices/version (PR #38–#39), public release **v0.2.0**, and console-window retitling are all complete.

## Source-of-truth rule

Do **not** reconstruct task state from chat memory. Use: actual repo/GitHub state → CURRENT-WORK.md → handoff.md → active work order → PROJECT-PLAN/contracts.

## Verified completed work (this session, main `2da3d01`)

- **PR #35**: E2E real-system suite (24 tests) + rebind regex fix + `open(instances_root=...)`.
- **PR #36**: display name → **A-Sunday Conductor** (branding.APP_NAME single source).
- **PR #38–#39**: `scripts/build_installer.py` (payload assembly + PyInstaller Setup build, shares the cosmetic-PE AV hardening), `THIRD-PARTY-NOTICES.md` (full Serena MIT text, bundled into every install), `branding.APP_VERSION` 0.2.0 synced with pyproject, `_install_files` extraction + icon regression fix found by the real Setup run.
- **Public release v0.2.0**: repo flipped public (explicit user decision 2026-08-22, recorded in COLLAB.md); https://github.com/aase7en/A-Wiki-Conductor/releases/tag/v0.2.0 with `A-Sunday-Conductor-Setup.exe`, `A-Sunday-Conductor-Portable.exe`, `THIRD-PARTY-NOTICES.md`; anonymous download verified (HTTP 200). Secret scan clean before flipping.
- **Local machine**: real `A-Sunday-Conductor-Setup.exe` ran end-to-end (files + shortcuts + HKCU + frozen uninstaller); smoke `A-CONDUCTOR_SMOKE_OK projects=4 workers=3` — user DB preserved.
- **Console window retitling (local files outside repo, user-authorized, `.bak` backups)**: all 13 `.cmd` launchers under `C:\AI\serena-instances\{conductor,phase6,wastewater}\` now set `title` — `Sunday-works 1 - Conductor`, `Sunday-works 2 - Phase6`, `Sunday-works 3 - Wastewater` (+ `- Stop/Status/Configure/Provision`, watchdog = `Sunday-works 3 - Wastewater Watchdog`); `watchdog.ps1` embedded title aligned. `Start-*.cmd`/`Stop-*.cmd` glob uniqueness preserved; Status script re-run OK after edit.

## Full suite at close

872 passed (test_build_installer grew to 9 after the icon regression test).

## Next safe action (user picks)

(a) ทดลองเปิดหน้าต่างจริง: ดับเบิลคลิก `Start-Serena-Phase6.cmd` → หน้าต่างต้องขึ้นชื่อ "Sunday-works 2 - Phase6"; (b) ตั้งชื่อ plugin ใหม่ใน ChatGPT + reconnect (user's own task — tunnel IDs untouched); (c) next §13 milestone with new work order + reuse gate.

## Mandatory boundaries

- MCP gateway enforcement stays `DECISION_REQUIRED` (backlog).
- A-Wiki remains brain authority. No machine-wide env changes.
- Do not rename internal package/CLI/data folder without an explicit migration decision.
- Do not modify `C:\AI\serena-instances` scripts further without user authority (this session's retitling was explicitly authorized; `.bak` files allow rollback).

## Escalation rule

GLM 5.3 owns routine implementation, TDD, regression, docs, PR/CI, merge. Escalate to GPT-5.6 Sol UltraHigh only for genuinely hard cross-cutting defects/architecture ambiguity, after checkpointing state.
