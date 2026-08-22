# A-Sunday Conductor — Current Work

Last updated: 2026-08-22 (GLM 5.3, v0.2.2 monitor + shutdown + cross-platform plan)

## Current phase

**No open work orders.** Latest: WO-P1-060 complete — workers and connectors are now fully manageable from the UI (PRs #42–#44, CI-green; real-machine create/delete round trip verified).

## Source-of-truth rule

Do **not** reconstruct task state from chat memory. Use: actual repo/GitHub state → CURRENT-WORK.md → handoff.md → active work order → PROJECT-PLAN/contracts.

## Verified completed work (this session, main `2da3d01`)

- **PR #35**: E2E real-system suite (24 tests) + rebind regex fix + `open(instances_root=...)`.
- **PR #36**: display name → **A-Sunday Conductor** (branding.APP_NAME single source).
- **PR #38–#39**: `scripts/build_installer.py` (payload assembly + PyInstaller Setup build, shares the cosmetic-PE AV hardening), `THIRD-PARTY-NOTICES.md` (full Serena MIT text, bundled into every install), `branding.APP_VERSION` 0.2.0 synced with pyproject, `_install_files` extraction + icon regression fix found by the real Setup run.
- **Public release v0.2.0**: repo flipped public (explicit user decision 2026-08-22, recorded in COLLAB.md); https://github.com/aase7en/A-Wiki-Conductor/releases/tag/v0.2.0 with `A-Sunday-Conductor-Setup.exe`, `A-Sunday-Conductor-Portable.exe`, `THIRD-PARTY-NOTICES.md`; anonymous download verified (HTTP 200). Secret scan clean before flipping.
- **Local machine**: real `A-Sunday-Conductor-Setup.exe` ran end-to-end (files + shortcuts + HKCU + frozen uninstaller); smoke `A-CONDUCTOR_SMOKE_OK projects=4 workers=3` — user DB preserved.
- **Console window retitling (local files outside repo, user-authorized, `.bak` backups)**: all 13 `.cmd` launchers under `C:\AI\serena-instances\{conductor,phase6,wastewater}\` now set `title` — `Sunday-works 1 - Conductor`, `Sunday-works 2 - Phase6`, `Sunday-works 3 - Wastewater` (+ `- Stop/Status/Configure/Provision`, watchdog = `Sunday-works 3 - Wastewater Watchdog`); `watchdog.ps1` embedded title aligned. `Start-*.cmd`/`Stop-*.cmd` glob uniqueness preserved; Status script re-run OK after edit.

## Verified completed work (WO-P1-060, main `f7911db`)

- **PR #42 Worker CRUD**: `+ Worker` / `Rename` / `Delete` buttons (WORKERS bar). Add auto-picks the next free `a-worker-NN` (max+1, no reuse), rename touches display name only, delete requires unassigned + STOPPED.
- **PR #43 Connector create**: `+ ตัวเชื่อม` button + dialog (name / project / optional Tunnel ID). Materializes the validated layout from a live reference instance (shared tunnel paths parsed from its `instance.ps1`), port auto-allocated, Start/Stop windows titled `Sunday-works N - <Name>`.
- **PR #44 Connector manage**: `แก้ชื่อ` (alias in `instance_display_names`, folder untouched) and `ลบ` (stop-first via orchestrator → zip to `%LOCALAPPDATA%\A-Conductor\instance-backups\` → remove → flags/alias cleanup; refuses while it cannot stop).
- Real-machine evidence: `Serena-Smoketest` created from the real conductor reference on 18014, discovered, then deleted with `smoketest-20260822-140647.zip` — instances root returned to exactly the original three.
- Note: instance names normalize to a lowercase slug (`SmokeTest` → `serena-smoketest` folder, `Serena-Smoketest` display), matching the existing conductor/phase6/wastewater convention.

## v0.2.2 shipped (PRs #54-#55, CI-green; GUI/core suites now run in separate CI processes)

- **App close = clean machine (PR #54)**: WM_DELETE_WINDOW stops every running connector (failure-tolerant), reaps stale wrappers, then exits; toggle ปิดโปรแกรมแล้วหยุดทุกตัวเชื่อม in Settings (default ON). Includes `docs/plans/cross-platform-plan.md` (macOS/Linux/Pi feasible; Umbrel needs headless web milestone; GATE-0 = non-Windows tunnel-client builds).
- **MONITOR panel (PR #55)**: selected connector shows STATE/PID/MEM/log path/error count/last-12 log lines, 5s auto-refresh (real entrypoint only); `instance_monitor.py` is cross-platform-ready (/proc path for Linux). Replaces the need to keep CMD windows open.
- CI lesson: Tk tests + subprocess-heavy tests in one process deterministically tripped a Windows faulthandler 0x80000003 breakpoint on runners — suites now run in separate steps.

## v0.2.1 shipped (PRs #50-#52, all CI-green; installed on this machine)

- **Usability (PR #50)**: horizontal scrollbars on WORKERS/CONNECTORS; hover any row -> dark floating tooltip with the FULL path; right-click -> Copy path (logged); window title carries the version (`A-Sunday Conductor v0.2.1`).
- **Thai/English switch (PR #51)**: `i18n.py` string table + English variants for all 50 teaching error codes; `language` preference (Settings switch) applied at startup; known gap: config blurbs + Thai guide stay Thai (backlog).
- **Guide (PR #52)**: §4.3 refreshed for the new toolbar; §4.3.1 documents that ONE API key can own MANY tunnels (each = one parallel chat) with steps; §4.3.2 documents one chat using several workers (with trade-offs); §4.5 language switch + version note.
- Full suite at close: 932 passed. Installed build reinstalled + smoke OK (projects=4 workers=3 preserved).

## Live connector fleet (2026-08-22 night — backend renamed to one pattern, all READY)

| Folder / $InstanceName | Port | Display alias (matches ChatGPT plugin) | Project |
|---|---|---|---|
| sunday-worker-1 / Sunday-Worker-1 | 18011 | SunDay-Worker 1-Conduct (18011) | A-Wiki-Conductor |
| sunday-worker-2 / Sunday-Worker-2 | 18012 | SunDay-Worker 2-Conduct (18012) | L:\My Drive\A-Wiki-Data\personal-business\pharmacy |
| sunday-worker-3 / Sunday-Worker-3 | 18013 | SunDay-Worker 3-Conduct (18013) | env-wastewater-webapp |
| sunday-worker-4 / Sunday-Worker-4 | 18014 | SunDay-Worker 4-Conduct (18014) | A-Wiki-Conductor |
| sunday-worker-5 / Sunday-Worker-5 | 18015 | SunDay-Worker 5-Conduct (18015) | A:\GitHub\sunday-estate-webapp |

- Backend rename executed via `instance_rename.rename_instance_backend` (PR #48): folders, identity lines, profile/log literals, template filenames, and every cmd wrapper renamed; window titles now `Sunday-works N - <Action>`.
- Migration lesson: an app-started instance keeps a detached `cmd.exe` wrapper whose CWD is the instance folder — folder renames require stopping the instance AND reaping that wrapper by exact PID (command-line match) first.
- Projects are NOT locked to names: any connector can switch projects via the เปลี่ยนโปรเจกต์ button (this rename was done precisely to stop implying otherwise).

## Full suite at close

912 passed (WO-P1-060 added 38 tests).

## Next safe action (user picks)

(a) กด `+ Worker` / `+ ตัวเชื่อม` ในแอปจริงเพื่อเปิดแชทขนานเพิ่ม (Tunnel ID ยังต้องสร้างใน OpenAI Platform web); (b) ตั้งชื่อ plugin ใหม่ใน ChatGPT + reconnect (user's own task); (c) rebuild+reinstall เพื่อให้ Start Menu ได้ปุ่มใหม่; (d) next §13 milestone with new work order + reuse gate.

## Mandatory boundaries

- MCP gateway enforcement stays `DECISION_REQUIRED` (backlog).
- A-Wiki remains brain authority. No machine-wide env changes.
- Do not rename internal package/CLI/data folder without an explicit migration decision.
- Do not modify `C:\AI\serena-instances` scripts further without user authority (this session's retitling was explicitly authorized; `.bak` files allow rollback).

## Escalation rule

GLM 5.3 owns routine implementation, TDD, regression, docs, PR/CI, merge. Escalate to GPT-5.6 Sol UltraHigh only for genuinely hard cross-cutting defects/architecture ambiguity, after checkpointing state.
