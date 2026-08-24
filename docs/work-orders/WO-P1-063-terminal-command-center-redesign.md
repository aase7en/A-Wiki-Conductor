# WO-P1-063 — Terminal Command-Center Redesign

Created: 2026-08-24
Owner: GPT-5.6 Sol + SunDay-Worker 1
Status: IN_PROGRESS — DESIGN/PLAN APPROVED, implementation pending gates
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

- [ ] `DESIGN.md` is in the mandatory agent read path.
- [ ] Main screen visually follows the approved minimal terminal command-center reference.
- [ ] UI remains native Tk/Ttk; no browser/web rewrite.
- [ ] Master family asset remains `assets/sunday-family-particle.png`.
- [ ] Header logo is recognisable at actual small size using fine white/gray particles.
- [ ] Interactive eyes use only restrained amber highlights; eye motion <= ~3 px target at normal header size.
- [ ] Face/head parallax is subtler than eyes (<= ~2 px target) and smoothly returns to neutral.
- [ ] Add Brain is clearly visible near product identity.
- [ ] Wide window uses horizontal information hierarchy; compact window remains reachable.
- [ ] Existing English buttons + tri-lingual help behavior remains intact.
- [ ] Add Connector remains visible/discoverable.
- [ ] MONITOR/ACTIVITY/diagnostics remain copyable and read-only.
- [ ] Assign replacement still confirms and preserves atomic safety.
- [ ] No new repeating subprocess-based monitor/render path.
- [ ] Real CPU/RAM/app-uptime values are measured, never invented; unavailable values show `—`.
- [ ] System metric refresh uses no subprocess and stops cleanly on app shutdown.
- [ ] Tests cover design contracts and regressions.
- [ ] Realistic E2E passes on source build.
- [ ] Packaging includes the logo/GPU requirements and build succeeds.
- [ ] Fresh installed/relaunched app is visually checked.
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

## Checkpoint — 2026-08-24 / Draft PR #77

Implementation checkpoint committed as `c42d174` (`feat(ui): build terminal command center monitor`) and pushed to `origin/feat/terminal-command-center-redesign`. Draft PR: #77 `feat(ui): terminal command-center redesign with real monitor`. Initial CI state: Windows `test`, Ubuntu `cross-platform-smoke`, and macOS `cross-platform-smoke` all pending. Do not merge until CI is green and final installer/fresh-install visual acceptance against `DESIGN.md` is complete.
