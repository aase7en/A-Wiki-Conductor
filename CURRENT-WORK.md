# A-Sunday Conductor — Current Work

Last updated: 2026-08-29 (GPT-5.6 Sol — AHA-4A retry/scope hardening GREEN / PR #131 pending)

## Current phase

**PRIMARY NEW-FEATURE PRIORITY: Sunday Family Multi-Model Agent Harness Accelerator — WORKER LEASE + AUTOMATIC FALLBACK REVIEW GATE.**

Current exact lane:
- worktree: `A:\GitHub\A-Wiki-Conductor-aha4a-lease`;
- branch: `feat/wo-p1-102-aha4a-worker-lease-broker`;
- reconciled `origin/main`: `39f0253cc4f8896cffa78b6772ce6ffd2e229736`;
- Draft PR: #131.

## Active work order

`docs/work-orders/WO-P1-102-aha4a-worker-lease-broker.md`.

## Immediate execution frontier

1. AHA-4A core is local GREEN: atomic worker/scope leasing, ordered fallback, typed preflight, exact-owner release, RDC read-only fallback;
2. independent review found and fixed two P0/P1 correctness gaps: mutation scope could escape `allowed_scope`; same session/task retry could create a second lease after uncertain transport;
3. retries now attach the same active owner/task lease, contract drift fails `LEASE_REQUEST_CONFLICT`, and concurrent same-owner requests converge on one lease;
4. resumed verification found a P1 outcome-classification bug: the race loser could attach the existing lease but still report `LEASED`; `EXISTING` is now explicit for pre-existing/race-attached leases;
5. final local evidence: focused **35 passed**, relevant regression **219 passed**, race repeat **10/10 PASS**, compileall/diff-check PASS; final exact-head CI remains required;
6. next = checkpoint/commit/push -> merge latest accepted main -> remote PR #131 diff audit -> independent read-only review + GPT re-review -> exact-head 3-OS CI -> merge;
7. AHA-4B heartbeat/expiry/quarantine remains a separate work order; no stale lease is reclaimed here.

## Source-of-truth rule

Do **not** reconstruct task state from chat memory. Use actual repo/GitHub state → CURRENT-WORK.md → handoff.md → active work order → PROJECT-PLAN/contracts.

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

## v0.2.3: private Drive data layer (2026-08-22)

- Secrets now live in the A-Wiki-Data Drive layer: `L:\My Drive\A-Wiki-Data\secrets-conductor-tunnels.md` holds all five Tunnel IDs (mapping worker/port/plugin); the Drive layer's `LAYOUT.md` records the two new roles.
- Connector-deletion zip backups automatically target `L:\My Drive\A-Wiki-Dataackups-conductor-instances\` when it exists (`default_backup_dir()` in desktop_control, Drive-first with LOCALAPPDATA fallback); the existing smoketest zip was moved there.
- Repo AGENTS.md now points every agent at the Drive layer + its AGENTS/LAYOUT rules before touching important/secret files.

## v0.2.4: A-Doctor deep-audit fixes (2026-08-22)

- **P1 fixes**: Toggle Auto wrote the wrong column (clobbered TUNNEL, left AUTO stale); reaper used substring matching (could kill sibling instances' wrappers — now path-boundary + apostrophe-escaped); project paths with apostrophes broke PowerShell single-quoted lines (now escaped via `_ps_quote` in create/rename/rebind); MONITOR froze the UI thread every 5s (async + cached instances + 64KB tail reads).
- **P2 fixes**: create validates the whole reference before touching disk (no skeleton folders); delete uses the real stop result code; backup zips include empty dirs; rename rollback covers read/write IO; stop-failures at close surface via confirm; error tables extended + made symmetric (Thai/EN) with the duplicate TUNNEL_ID_INVALID removed; CI GUI list completed (test_instance_create, test_doctor_fixes).
- WO-P1-052 closed (code shipped long ago); WO-P1-023 marked superseded. Guide §3 diagram/§4.5 refreshed for the current toolbars + MONITOR + shutdown switch.

## v0.3.0: backlog loops shipped (2026-08-23, PRs #59-#63)

- **Loop A (deep i18n)**: all 64 config blurbs bilingual (PR #60) + full English user guide bundled with every install; Guide button follows the language; MODE_BLURBS finally wired as a checkbox grid.
- **Loop B-1 (cross-platform P1)**: `platform_support` (env-override roots, Win32 constant flags), POSIX launcher (`/bin/sh` + start_new_session), headless smoke fallback; **CI now runs on Windows + Ubuntu + macOS** — the matrix caught 3 real POSIX bugs (subprocess attr, hardcoded instance base, Tk-no-display) before any user ever hit them. Remaining: B-2 (.sh instance templates) + B-3 (mac/Linux packaging).
- **Loop C (signing)**: SignPath pipeline ready (`scripts/sign.py` no-op until `SIGNPATH_API_TOKEN`; sign workflow on release publish); **user action pending**: apply per `docs/signing/SIGNPATH-APPLY.md` (free for OSS; consider switching the license to MIT/Apache first).
- **Loop D**: ADR-0001 defers the MCP gateway with explicit reopen conditions; no DECISION_REQUIRED markers remain.
- v0.3.0 installed on this machine (smoke OK, both guides bundled); bug-hunt suite stable ×2 (24/24).

## v0.3.0 COMPLETE (2026-08-23, PRs #59-#65, GitHub Release published)

**Everything from the approved backlog-loop plan is shipped:**

- **Loop A (deep i18n)**: bilingual config blurbs + English user guide + MODE grid
- **Loop B (cross-platform)**: platform layer (B-1) + POSIX .sh templates (B-2) + 3-OS CI matrix (B-3)
- **Loop C (signing)**: SignPath pipeline ready; user applies per docs/signing/SIGNPATH-APPLY.md
- **Loop D**: ADR-0001 gateway deferred with reopen conditions
- **GitHub Release v0.3.0**: https://github.com/aase7en/A-Wiki-Conductor/releases/tag/v0.3.0 (Setup + Portable + both guides + notices)
- **README rewritten** (capabilities, quick-start, architecture) + **INSTALL.md** (Thai step-by-step)
- Bug-hunt stable ×2; no DECISION_REQUIRED markers remain anywhere

**Remaining (next milestone, not blocking):**
- macOS/Linux desktop builds (B-3 packaging — the groundwork + templates are in place)
- RPi (P3) + Umbrel headless (P4) per docs/plans/cross-platform-plan.md
- SignPath application (user action, guide provided)

## v0.4.0: Setup Wizard (2026-08-23, PRs #69-#70)

One-stop installer: new users download Setup.exe → open → wizard auto-opens → installs everything (uv, Python 3.13, Serena, tunnel-client) → creates first connector → saves credentials. No manual prerequisites.

- **PR-A (engine)**: setup_wizard.py — check_system, Installer (uv/Python/Serena/tunnel-client with injectable download/subprocess), FirstInstanceCreator (generates complete instance from embedded templates, no reference needed)
- **PR-B (UI)**: 7-step wizard dialog with first-run auto-open; i18n TH/EN; real-time install log; OpenAI Platform link

## v0.4.1-0.4.3: wizard backends + donate (2026-08-24, PRs #71-#73)

- v0.4.1: Node.js auto-install + backend selection (Filesystem / Serena)
- v0.4.2: Google Stitch backend (4th option)
- v0.4.3: Donate dialog (GitHub Sponsors + PromptPay QR) + DPAPI fix
- Final audit: repo health 100%, 1031 tests, zero DECISION_REQUIRED

## v0.5.0 UI Redesign + Session Summary (2026-08-24, PRs #74-#76+)

### Shipped this session:
- **PanedWindow layout** — all panels drag-resizable, no more disappearing panels
- **GPU particle logo** — 120px interactive canvas in header, eyes track mouse
- **Responsive button grids** — buttons auto-wrap at wide widths, stack at narrow
- **English button labels** — canonical_button_label forces English globally
- **Tri-lingual i18n** — Thai / 中文 / English with per-language tooltips
- **MONITOR + ACTIVITY side-by-side** — horizontal PanedWindow
- **Copy log** — Ctrl+C, right-click menu, Copy All buttons
- **Assign with confirmation** — popup when replacing existing assignment
- **Setup Wizard** — 4 backends (Filesystem, Serena, Google Stitch, custom)
- **Donate dialog** — GitHub Sponsors + PromptPay QR
- **DEFECT_LESSONS.md** — 3 documented lessons (PowerShell spawn, dialog destroy, Tk instance)
- **PowerShell spawn fix** — native ctypes API, 0 process spawns
- **+Worker dialog fix** — read entry before destroy
- **Splash screen fix** — Toplevel instead of second Tk()
- **Community files** — CODE_OF_CONDUCT, CONTRIBUTING, templates, FUNDING
- **CHANGELOG.md** — full version history
- **MIT License** + GitHub Sponsors + Privacy + Security policies
- **Repo health 100%**

### Current state:
- Version: v0.5.0
- Tests: ~1092 collected
- CI: Windows + Ubuntu + macOS
- GitHub Releases: v0.5.0
- Install: %LOCALAPPDATA%\Programs\A-Sunday Conductor
### Pending (backlog, non-blocking):
- GPT/GLM collaboration protocol (docs/agent-collab/)
- Connector column UX tooltip improvement
- macOS/Linux desktop packaging (B-3)
- RPi + Umbrel (P3/P4)
- SignPath application (user action)

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

957 passed (v0.2.4 A-Doctor fixes included).

## Next safe action (user picks)

(a) กด `+ Worker` / `+ ตัวเชื่อม` ในแอปจริงเพื่อเปิดแชทขนานเพิ่ม (Tunnel ID ยังต้องสร้างใน OpenAI Platform web); (b) ตั้งชื่อ plugin ใหม่ใน ChatGPT + reconnect (user's own task); (c) rebuild+reinstall เพื่อให้ Start Menu ได้ปุ่มใหม่; (d) next §13 milestone with new work order + reuse gate.

## Mandatory boundaries

- MCP gateway: deferred per `docs/adr/ADR-0001-mcp-gateway-deferred.md` (reopen conditions listed there).
- A-Wiki remains brain authority. No machine-wide env changes.
- Do not rename internal package/CLI/data folder without an explicit migration decision.
- Do not modify `C:\AI\serena-instances` scripts further without user authority (this session's retitling was explicitly authorized; `.bak` files allow rollback).

## Escalation rule

GLM 5.3 owns routine implementation, TDD, regression, docs, PR/CI, merge. Escalate to GPT-5.6 Sol UltraHigh only for genuinely hard cross-cutting defects/architecture ambiguity, after checkpointing state.

## WO-P1-063 real-monitor extension checkpoint

Real-monitor extension checkpoint: user requested real CPU/RAM/app-uptime monitoring in the command-center overview. This extends WO-P1-063; it does not create a second dashboard. The implementation must use native/file-based sampling, no periodic subprocesses, bounded CPU history, and `—` for unavailable metrics. Claimed files include `src/a_conductor/system_metrics.py` and `tests/test_system_metrics.py` in addition to the existing WO-P1-063 UI scope.

## WO-P1-063 implementation evidence — terminal command center + real monitor

Current branch `feat/terminal-command-center-redesign` contains the implemented terminal command-center visual slice plus a real system-monitor extension. `SYSTEM OVERVIEW` now uses measured CPU/RAM/app uptime, not mockup numbers. New collector is `src/a_conductor/system_metrics.py`; it uses native Windows APIs / Linux `/proc`, no periodic subprocess. UI refresh = 2.5s, CPU history = max 60 points, callback cancels on close. Real UI smoke: CPU 5%, RAM 9.2 / 15.9 GB, uptime 00:00:03. Combined focused suite: 37 passed, 1 environment skip. Release loop is not complete until PR/CI/merge/fresh-install visual verification.

## WO-P1-063 PR checkpoint

Draft PR #77 is open from `feat/terminal-command-center-redesign`; implementation commit `c42d174` is pushed. CI started with Windows test + Ubuntu/macOS cross-platform smoke pending. Next owner must review actual PR diff and checks first, then fix only evidence-backed failures, finish packaging/fresh-install visual E2E, update SSoT, convert from draft/merge only after acceptance.
