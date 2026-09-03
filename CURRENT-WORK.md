# A-Sunday Conductor — Current Work

Last updated: 2026-09-03 (GPT-5.6 Sol MAX - WO144 post-reliability actual-state closeout)

## Actual-state reconciliation — 2026-09-03

**Actual GitHub/repo/runtime evidence supersedes older frontier text below. WO140 and WO143 are released; PR #183/AiPASS is the next bounded product-planning lane, while WO096 remains the independent P0 operational release gate.**

- `origin/main = cf2a4e7a57bfd22ec55de79c700ec3e4931dc475`: WO144 / PR #195 merged from exact docs head `f2d33ed2d63454e6b7f547a016abb07f058d89be`; post-main CI `33704062299` SUCCESS. WO144 coordination claim is released by this final closeout; PR #183 / WO132 is next.
- WO140 / PR #193 is RELEASED. GLM diagnosis candidate was independently reviewed by GPT; GPT found and repaired one P2 bounded-memory defect with `deque(maxlen=64)`. Final head `2238259e264991e1249d1439b206dc9b252c3051`; exact-head CI `33678036552` SUCCESS; merge `787e9be2f108ce3f323bebc20127eb03c2958bfc`; post-main CI `33679432865` SUCCESS.
- WO143 / WO134-R1 is RELEASED. Original reviewed feature head `9c41da768713e3ad1c6d948f420b1110ea49afe6`; after WO140 main drift, merge-composed exact head `720d0328c02f7068d34cc3a5ae31418a9b1ede4b` preserved all 7 reviewed feature blobs byte-identically. GLM exact-head rereview PASS P0/P1/P2/P3=0; exact-head CI `33680012267` SUCCESS; PR #194 merged as `272953a366f93a7f7dbd8e1e8060fc0f1bacdb88`; post-main CI `33681115738` SUCCESS, completing the release verification gate.
- PR #183 / WO132 AiPASS is next after WO144. Draft head `085a06cf6d2d1d1e4a3b5085ad51ad3444a8b337`; prior CI `33662059825` green. Fresh audit confirms `niawjunior/aipass-bridge@b1b8bab757d91c266410d58f505aeeaa218da102` and MIT LICENSE blob `17ddd0b8425c523d029917a1027d7e40a0916100`; official AiPASS Terms effective 2026-08-19 section 3.4 prohibit bot-emulation/unapproved software and direct API/API Key/Token access outside the provider-defined UI **unless explicitly authorized in writing by the project**. Live automation remains fail-closed until an official supported path or explicit written authorization covers the intended mode. Current PR #183 conflict is confined to `COLLAB.md`; roadmap text needs WO143/current-main reconciliation.
- WO096 remains the P0 v0.7.0 operational release blocker. Read-only fleet refresh: 18011/18013/18014 listening; 18012/18015 stopped; shared live tunnel-client remains 0.0.11. Stopped does not mean available: Worker2 retains pharmacy cycle `PO-2026-08-26-001` / `RECONCILE_RECEIPT`; Worker5 retains sunday-estate worktree/branch continuity. No live maintenance authority is inferred.
- A-Wiki Review Bridge remains dependency-blocked on independent acceptance only. Current candidate `b04761d580ddcdc7eb682e3a6036078b3b346953` / PR #50 is Draft, mergeable CLEAN; Core CI `33682384067`, Loop Gate `33682383989`, and py38 smoke are SUCCESS. The bridge repairs were GPT-authored, so a fresh independent exact-SHA rereview with P0/P1/P2=0 is still mandatory before Ready/Merge. Do not implement a parallel ReviewBus or bind to the Draft API as accepted authority.
- Protected root checkout remains stale/dirty; use isolated worktrees only.

### Immediate execution order

1. Reconcile PR #183 against current main `cf2a4e7a57bfd22ec55de79c700ec3e4931dc475`, preserve released WO140/WO143/WO144 history, and refresh current AiPASS evidence before new exact-head CI.
2. After PR #183 acceptance, claim AIP-1 from then-current main with a fresh reuse/authorization gate and no live traffic.
3. Continue read-only A-Wiki Review Bridge polling; implement adapter only after accepted exact A-Wiki SHA/API.
4. Keep WO096 fail-closed until explicit maintenance authority exists; do not publish stable v0.7.0.

## Current phase

**AHA-7 Models & Agents remains the active product frontier. WO127 and WO128 are accepted/released. WO134 historical T2-T4 evidence detail merged, but post-merge WO134-R1 is now the active dependency-blocking product defect and requires a fresh bounded remediation SHA; historical review/CI cannot close it. GPT remains integrator/merge authority. P0 WO-P1-096 remains the v0.7.0 operational release blocker.**

Accepted / active frontier state:
- PR #174 / WO124 reviewed exact head `be97d313c748fe5fcce0e57ecf5dc304b863e230`; GLM review002 PASS with P0/P1/P2 = 0; task SHA-256 `abe750450dda09dbf423681811efd0110ecfa26914cc55828b133db48a9fcf2b`; exact-head CI `33497483113` attempt 2 SUCCESS; merged as `c1cfbe780e76d3a64fb692e91dde851824bd8033`; post-main CI `33504441646` attempt 2 SUCCESS.
- WO124 establishes the truthful read-only operator model: `CONFIGURED != READY`, `READY != AUTHORIZED`, existing readiness/quota authority is reused, invalid generations fail closed, and secret/endpoint values are excluded.
- PR #176 / WO129 reviewed exact head `661c86f9a30433006a01e996ed1ea46fde4a7e52`; GLM review001 PASS with P0/P1/P2 = 0; task SHA-256 `b211091c4bfdc6c063da1ad037dc2a340750a90a47d813443e27c0bfa9c26481`; exact-head CI `33503763313` SUCCESS; merged as `fae5c0d8a36a41eb172e2acb8dc88ca04658c4e9`; post-main CI `33509029840` SUCCESS including Windows Portable/Setup and Frozen install/uninstall E2E.
- WO129 permits bounded post-termination UNKNOWN re-observation only after exact-PID termination succeeds; it never retries termination, never tolerates MISMATCH, and preserves PID metadata when exit ownership remains uncertain.
- PR #178 / WO125 reviewed exact head `91f77731d472d23c624bef22891b9cd400e6c090`; GLM long-goal review PASS with P0/P1/P2=0; exact-head CI `33528331266` SUCCESS; merged as `23b988764a3529f0721375f5d0a0c885b715ad46`; post-main CI `33534118110` SUCCESS including Windows Portable/Setup/Frozen E2E. Ultra final review exhausted quota before writing a result and was not used as merge authority.
- PR #179 / WO126 reviewed exact head `eee3e0e202b27c685f63c222ff10646ae667987e`; GLM task `wo126-glm-review-001` (task SHA `5d5ce849018f42db9adb6043ae0457230abbaa4d0ee8ddab4684927fc877644f`) PASS with P0/P1/P2=0; exact-head CI `33540512066` SUCCESS; merged as `010ab4bdefbe54725388a5cea936117b8eb93b6b`; post-main CI `33544097620` SUCCESS including Windows packaging/Frozen Setup E2E.
- WO126 preserves `CONFIGURED != READY != AUTHORIZED`, async/single-flight Settings reads, typed empty/error truth, stale-dialog guards, safe provenance only, and zero endpoint/credential/raw-secret UI exposure.
- PR #182 / WO127 exact head `e91647a7ccaefe522b11ba867719b3186ed5b96d` passed GLM rereview002 with P0/P1/P2=0 and CI `33582451656`; merged as `b0eed29656cc54031b7442348449d57cf55d23be`; post-main `33585602021` SUCCESS.
- PR #184 / WO128 core exact head `a9f4fe6a92367650e7c22caaa9df9e8c148cf3ad` passed GLM review002 with P0/P1/P2=0 and CI `33586307363`; merged as `b6d50921035ae6ec6d32b6c05b3f723530b8c68d`; post-main `33591789871` SUCCESS. Truth remains `SELECTION_REASON=UNKNOWN`, `FALLBACK_REASON=NOT_EVALUATED`.
- PR #186 / WO135 defect-memory exact head `a3f51ca6a403724a1b7228a239d4965ced28bfad` passed CI `33607169866`; merged as `0ac30eb3a452327e01e9a6bad18ce0676aadf1f3`; post-main `33608067520` SUCCESS.
- WO134 T2-T4 Provider Evidence Detail is CLAIMED in `A:\GitHub\A-Wiki-Conductor-wo134-provider-evidence-detail`, branch `feat/wo-p1-134-provider-evidence-detail`; GLM owns its declared UI/control/test scope and GPT must not overlap it.
- PR #180 / WO131 exact head `554c2b1003d12cd211712393ecf61c034b1a8003` passed exact-head CI `33543935682` and merged externally as `af7a933fe27d2a3e3f29360abf9214df1e5478c5` before the planned GLM review result existed; post-main CI `33545560617` is SUCCESS. This is accepted runtime evidence with an explicit process deviation, not retrospective independent-review evidence.
- P0 WO096 remains operationally open: no live Worker/tunnel mutation is authorized by this roadmap work; public v0.7.0 remains blocked pending the required hosted remote MCP-after-TTL proof.

## Active work orders

1. `WO-P1-134` - ACTIVE / GLM OWNED: T2-T4 Provider Evidence Detail in isolated worktree; GPT remains integrator/merge authority and must not overlap mutable UI/control/test scope.
2. `WO-P1-096` - P0 operational release gate; live Worker/tunnel mutation remains unauthorized; v0.7.0 publication blocked.
3. `PR #183 / WO-P1-132` - separate draft AiPASS roadmap lane; semantic reconcile required before merge, no overlap from WO136.
4. `WO-P3-136` - GPT docs-only shared SSoT closeout for accepted WO127/WO128/WO135 state.

## Immediate execution frontier

1. Complete WO136 docs-only reconciliation, exact-head CI, merge, and post-main verification.
2. Preserve WO134 ownership; consume its declared result only after GLM finishes and then independently review exact candidate identity, tests, secret/UI truth, CI and merge gates.
3. Reconcile PR #183 against current main and fresh AiPASS authorization/source evidence in its own separate claimed lane before any merge or AIP-1 implementation.
4. Keep WO096 fail-closed until explicit maintenance authority permits the isolated v0.0.13 hosted-after-TTL proof; do not publish v0.7.0.

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

- AHA-5 audit evidence: related suite 122 passed; CI-equivalent full suite 1687 passed, 1 environment skip, 0 failed; compileall/diff-check/secret-pattern scan PASS.


## WO-P1-114 implementation checkpoint — 2026-08-30

- New provider runtime seams implemented in `awiki_environment_resolver.py` and `provider_runtime_assembly.py`; no scheduler/lease/job-store/UI mutation.
- RED collection proved both modules absent before implementation; GREEN focused suite now `15 passed`.
- Related provider/harness/AHA-6 regression: `211 passed`; compileall PASS.
- Full local suite: `1714 passed, 5 skipped, 2 known GPU dependency failures` outside WO-P1-114.
- Adversarial `.drive-path` decode defect repaired and recorded as `DEFECT_LESSONS.md #26`.
- Automatic GLM is still fail-closed: desktop runtime has no current `A_WIKI_DRIVE_PATH` binding, and AHA-6 cross-batch provider admission remains unsupported without serialized/atomic capacity authority.
- Next gate: scope/secret/encoding audit → implementation commit/push → exact-SHA GLM-5.3 MAX read-only review packet → bounded repair if valid → PR/CI.

### WO-P1-114 trust-boundary repair update

- Pre-external GPT review found 2 real fail-closed defects: invalid explicit Drive override fallback and corrupt SQLite provider row decode escape.
- Both have RED tests and bounded repairs; focused suite is now `17 passed`, related regression `224 passed`.
- `DEFECT_LESSONS.md #27` added.
- The first ignored GLM packet at `c94abfc755a279f873cd0745eb8cdb131103ef84` was never dispatched and is superseded.
- Next: exact-state full suite → audit/commit/push repair → regenerate exact-SHA GLM review packet.

### WO-P1-114 exact repaired full-suite evidence

Exact repaired snapshot: focused `17 passed`; related `224 passed`; full local `1716 passed, 5 skipped, 2 known GPU dependency failures`. No provider/runtime assembly regression. Next gate remains audit → repair commit/push → fresh exact-SHA GLM review.

### WO-P1-114 external review handoff

- Repaired implementation head `d914915e5a1b2f179ce1315b13633cc4aa5f7b7e` is pushed and clean.
- Exact local gates: focused `17 passed`, related `224 passed`, full local `1716 passed / 5 skipped / 2 known GPU dependency failures`; compile/diff/scope/secret/encoding additions audit PASS.
- Independent review task ID is `wo114-glm-review-002`; task/result live only under ignored `runs/wo114-glm-review-002/`.
- GLM-5.3 MAX is assigned read-only trust-boundary review only; GPT retains acceptance/repair/merge authority.
- Automatic GLM dispatch is still fail-closed; use one-way human pointer relay only if the packet cannot be dispatched automatically.
- Next: commit/push this handoff checkpoint, generate and re-read exact-SHA task packet, then dispatch review.

### WO-P1-114 independent review accepted

GLM-5.3 MAX task `wo114-glm-review-002` returned `PASS` at exact HEAD `75c8e21da3d47ffb2fff6f8e37f6240b537f2522`. GPT independently validated task/provider/model/HEAD/task SHA and all four source/test hashes. P0/P1/P2 findings: 0. Four P3 hardening notes are deferred without source mutation. Next gate: final branch audit, Draft PR, exact-head CI, re-audit, merge, post-main proof.
