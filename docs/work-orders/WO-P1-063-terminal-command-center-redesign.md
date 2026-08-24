# WO-P1-063 — Terminal Command-Center Redesign

Created: 2026-08-24
Owner: Codex / GPT-5.6 Sol (one implementation owner; PR #79)
Status: RELEASE_VALIDATION — PR #79 candidate; source/package/installed green, final documentation CI/merge/main gates pending
Depends on: v0.5.0 UI baseline; WO-P1-061/062 capabilities already present on `main`

## Goal

Restyle and reorganize the A-Sunday Conductor desktop application to match the user-approved dark professional terminal/CMD/CLI command-center reference as closely as practical while remaining a lightweight native desktop app and preserving existing safe behavior.

Design authority: `DESIGN.md`.

## Repository basis at start

- repo: `A:\GitHub\A-Wiki-Conductor`
- branch base: `main`
- base HEAD: `e131b8baffcd160d96b95db9e9380e6e2b4346c0`
- `origin/main`: same HEAD at gate time
- working tree: clean before branch creation
- implementation branch: `feat/terminal-command-center-redesign`
- latest base CI for HEAD was still in progress at branch creation; preceding main runs were green.

## Reuse-before-build classification

- Desktop framework: REUSE Tk/Ttk.
- Existing responsive helpers / PanedWindow: EXTEND.
- Existing Sunday Family GPU renderer: EXTEND, not replace.
- Existing `assets/sunday-family-particle.png`: REUSE as master logo source.
- Existing Add Brain / Add Connector / i18n / copy log / assignment replacement: REUSE and preserve.
- Command-center visual hierarchy: NEW presentation layer over existing capabilities; no orchestration rewrite.
- Graphs/metrics: EXTEND only from real existing data; do not invent operational metrics.

## Grill / brainstorm conclusion

The user has already resolved the design decisions that would otherwise require questions:
- visual target = supplied terminal command-center mockup;
- desktop native/lightweight = required;
- Sunday Family portrait = master brand asset;
- Add Brain = primary header capability;
- logo pointer response = gentle eye + face movement, explicitly not exaggerated;
- full repo SSoT + engineer loop through PR/CI/merge = required.

Upstream `mattpocock/skills` freshness checked 2026-08-24: current `grill-with-docs` delegates to grilling/domain-modeling; the grilling rule is to explore facts from the codebase rather than asking the user. No unresolved user-only design decision blocks implementation.

## Planned slices

### 063-A — SSoT + design system
- create `DESIGN.md`;
- update AGENTS read order;
- update PROJECT-PLAN UI direction;
- reconcile CURRENT-WORK/handoff drift;
- claim redesign scope in COLLAB.

### 063-B — Header + brand motion
- compact Sunday Family portrait sourced from the master asset;
- title/tagline/status composition matching reference;
- Add Brain remains first-class;
- gentle eye movement and subtler face/head parallax;
- no layout movement; clean shutdown/fallback.

### 063-C — Command-center workspace layout
- Projects sidebar on wide layouts;
- compact System Overview from factual existing state;
- Worker and Connector/Instance tables use horizontal width efficiently;
- recent-events / diagnostic placement based on available width;
- bottom terminal-style diagnostics area while preserving copyable logs/monitor behavior.

### 063-D — Theme / density / real system monitor
- thin borders and compact terminal typography;
- restrained semantic colors;
- add real CPU %, RAM used/total, and A-Sunday Conductor process uptime to SYSTEM OVERVIEW;
- collect metrics through a lightweight native/file-based sampler with no periodic subprocesses;
- use a thin bounded CPU sparkline from real samples only; unavailable metrics render as `—`;
- cancel the monitor callback cleanly during application shutdown.

### 063-E — Compatibility regression
Preserve and test:
- responsive narrow/wide behavior;
- global English action labels;
- localized TH/zh-CN/EN help;
- Add Connector discoverability;
- confirmed atomic assignment replacement;
- copyable read-only diagnostics;
- Donate/Check Update;
- worker/connector lifecycle safety.

### 063-F — Realistic E2E / release loop
- compact/standard/wide/maximized;
- pointer motion + pointer leave + app close;
- GPU-disabled fallback;
- language switching during resize/animation;
- copy logs;
- assign replacement;
- connector operation smoke;
- package/portable/installer graph;
- fresh installed application visual verification;
- report + DEFECT_LESSONS if a user-relevant recurring defect is found;
- commit → PR → CI → fix real failures → merge → fetch main.

## Acceptance criteria

- [x] `DESIGN.md` is in the mandatory agent read path.
- [x] Main screen visually follows the approved minimal terminal command-center reference.
- [x] UI remains native Tk/Ttk; no browser/web rewrite.
- [x] Master family asset remains `assets/sunday-family-particle.png`.
- [x] Header logo is recognisable at actual small size using fine white/gray particles.
- [x] Interactive eyes use only restrained amber highlights; eye motion <= ~3 px target at normal header size.
- [x] Face/head parallax is subtler than eyes (<= ~2 px target) and smoothly returns to neutral.
- [x] Add Brain is clearly visible near product identity.
- [x] Wide window uses horizontal information hierarchy; compact window remains reachable.
- [x] Existing English buttons + tri-lingual help behavior remains intact.
- [x] Add Connector remains visible/discoverable.
- [x] MONITOR/ACTIVITY/diagnostics remain copyable and read-only.
- [x] Assign replacement still confirms and preserves atomic safety.
- [x] No new repeating subprocess-based monitor/render path.
- [x] Real CPU/RAM/app-uptime values are measured, never invented; unavailable values show `—`.
- [x] System metric refresh uses no subprocess and stops cleanly on app shutdown.
- [x] Tests cover design contracts and regressions.
- [x] Realistic E2E passes on source build.
- [x] Packaging includes the logo/GPU requirements and build succeeds.
- [x] Fresh installed/relaunched app is visually checked.
- [ ] PR CI is green before merge.
- [ ] Main is fetched after merge and continuity files say DONE with evidence.

## Known environment caveats

- Local ESET/security can temporarily deny access to fresh `.ps1` fixtures and fresh PE files.
- Pytest assertions may pass before Windows temp cleanup returns WinError 5. Use repo-local `--basetemp` and CI evidence; do not change unrelated production code to satisfy antivirus races.

## Checkpoint — 2026-08-24 / start

Design direction approved by user. Repository identity gate passed. `DESIGN.md` created. No production `src/` mutation has occurred in WO-P1-063 yet.

## Checkpoint — 2026-08-24 / real monitor extension

User explicitly requested that the CPU/RAM/uptime surfaces become real monitoring rather than mockup-only placeholders. SSoT was updated before production mutation. Planned implementation is a bounded `system_metrics.py` collector plus UI labels/sparkline; no PowerShell/cmd subprocess is permitted in the periodic path.

## Checkpoint — 2026-08-24 / real monitor implemented

Implemented factual system monitoring as part of the command-center overview:
- new `src/a_conductor/system_metrics.py` with Windows native `GetSystemTimes` + `GlobalMemoryStatusEx`, Linux `/proc` fallbacks, and honest `None` on unsupported metrics;
- no `subprocess`, PowerShell, or cmd dependency in the periodic collector;
- real CPU %, RAM used/total, and current A-Sunday Conductor session uptime shown in SYSTEM OVERVIEW;
- 2.5-second low-frequency UI refresh, bounded 60-sample CPU history, thin 1px sparkline;
- monitor callback starts from `start_background_operations()` and is cancelled before close/shutdown work;
- deterministic collector tests: 5 passed;
- combined redesign/GPU/monitor focused suite: 37 passed, 1 environment skip;
- real Tk/UI smoke on this workstation: CPU 5%, RAM 9.2 / 15.9 GB, uptime 00:00:03, two real CPU samples, callback cancelled cleanly;
- previous real OpenGL smoke remains: `gpu-opengl`, ~9,360 particles, `GPU_ERROR=None`;
- non-AV GUI regression previously: 142 passed; core suite previously: 890 passed with only known local ESET `.ps1` PermissionErrors;
- Portable build previously completed at ~24.3 MB and included Sunday Family/GPU assets, but fresh-PE ESET lock still blocks immediate frozen/Setup continuation locally.

Next release loop: final staff review -> broader CI-equivalent regression -> commit/push -> PR -> GitHub 3-OS CI -> fix real failures only -> merge -> fetch main -> rebuild Setup/Portable -> fresh install/relaunch -> visual acceptance against `DESIGN.md`.

## Historical checkpoint — 2026-08-24 / PR #77

Implementation checkpoint committed as `c42d174` (`feat(ui): build terminal command center monitor`) and pushed to `origin/feat/terminal-command-center-redesign`. GitHub later marked Draft PR #77 merged indirectly through PR #78 while it still had no reviews. Its Windows/Ubuntu/macOS checks were green, but those checks do not cover the forward-only completion fixes below. Do not resume work by mutating PR #77.

## Checkpoint — 2026-08-25 / Draft PR #79 release validation

- current branch: `fix/terminal-command-center-completion`; pushed source HEAD before this checkpoint: `8abf2bfcb62dc435a39765d7c0e8552f50578290`; base `origin/main`: `9782f933426bbd5970e9e571545da89402c6a9ed`;
- exact master portrait renders through a real framebuffer-verified WGL path at ~9,360 particles; forced GPU-disabled fallback renders the same portrait as one raster plus six optional eye-core accents (seven Canvas items, zero particle ovals);
- actual pointer sweep returns to neutral; 12 repeated real WGL create/destroy cycles reported successful native unbind/delete, stable GDI/USER resources after warm-up, zero callback errors;
- responsive real windows verified at 700, 900, 1280, 1600, and maximized; the 700px System Overview uses compact one-row labels so no value or selectable Worker row is clipped;
- real UI sample: CPU 29–30%, RAM 12.3 / 15.9 GB, uptime 00:00:03, bounded history populated; these are sample evidence only and are not hard-coded;
- full repository regression: **1166 passed**; real-system sandbox E2E: **23 passed**, one network-only case deselected;
- fresh Portable: 24,282,484 bytes, SHA-256 `DB4921146FABA1E774B56F342EDE8178EADA3782DC59F669BB513D570206B0CA`;
- fresh Setup: 31,219,212 bytes, SHA-256 `F5C676406C36E265EE293721FB977DFB8C740B52E076BD58AC71A0A851D67574`;
- frozen smoke exit 0; recursive archive check contains Sunday master/compact assets, GPU/metrics, ModernGL/OpenGL, Pillow, and Tcl/Tk; a Windows path-separator false-failure in the new archive CI gate was found locally, covered by test, and fixed before final CI;
- first PR #79 run `32783280486`: Ubuntu/macOS green; Windows failed when the hosted virtual WGL driver access-violated inside `moderngl.create_context()` before Python could activate fallback. Classified as platform/test-environment incompatibility. Generic Windows CI now forces the deterministic Canvas path; real WGL remains a workstation/installed-app gate;
- Draft PR #79 is the sole forward completion PR. Remaining gates are current-HEAD CI, safe installed upgrade/E2E, ready review, merge, fetch main, rebuild/reinstall from main, and final COMPLETE continuity update.

## Checkpoint — 2026-08-25 / installed release candidate

- pushed implementation HEAD `e3d4babb78859b9d5e218354b0ea0b5d14129484`; PR #79 run `32789507743` passed Windows test/package plus Ubuntu/macOS smoke;
- full local repository regression before the bounded final shutdown optimization: **1175 passed**, with one transient local Tcl/Tk skip rerun successfully in focused coverage; final shutdown-focused regression passed and GitHub reran the full three-job matrix green;
- a real installed close during connector autostart exposed redundant synchronous health polling. A failing regression proved the forced pending-launch path still probed once; the fix skips only that pre-force probe while retaining post-stop verification. Skeptical review verdict: GO;
- source-process shutdown E2E improved from 8,091 ms to 4,361 ms in the same sandbox. The freshly installed one-file executable also created the stop marker and removed both frozen processes; the observed bounded close was 9,235 ms on the security-filtered workstation because cancellation, post-stop verification, wrapper reaping, and bootloader cleanup still complete before process exit;
- final pre-merge Portable: 24,285,453 bytes, SHA-256 `FF55C476BF4FFA852CB78545EFA12EC69399F2E70D28432B303CB69EEE98BD15`;
- final pre-merge Setup: 31,222,411 bytes, SHA-256 `26CEE072C2FFDAF934B11C47CB1D5D5D4CFE67D4CAD1032988E34BE2FA2D2D7D`;
- recursive archive gate passed all 12 Portable requirements and all 6 Setup requirements, rejected duplicate full-app modules in Setup, and frozen smoke exited 0;
- Setup exited 0 on its first attempt. Installed executable exactly matches the Portable hash; registered product is A-Sunday Conductor v0.6.0; the user database physical hash stayed unchanged and its logical contents remain identical to the consistent pre-test backup;
- installed visual acceptance directly compared the real 1096×719 window with the user-reconfirmed wide near-black reference: detailed Sunday Family portrait visible, terminal hierarchy/density retained, Add Brain/Guide/Settings reachable, English actions preserved, and real CPU/RAM/uptime populated;
- all five live connectors remained `STOPPED`; installed sandbox actions used only the temporary Sunday-Worker-Test instance.

Remaining gates: commit this release evidence, require the resulting PR checks green, mark PR #79 ready, final diff review/merge, fetch merged `main`, rebuild/reinstall from `main`, repeat installed acceptance, and publish the final COMPLETE continuity checkpoint.
