# HANDOFF — A-Sunday Conductor

Last updated: 2026-08-24 (GLM 5.3, v0.5.0 compact-ready) (GPT-5.6 Sol + SunDay-Worker 1, WO-P1-062 design review)

## Current objective

Execute `WO-P1-063` from the clean v0.5.0 baseline: restyle/reorganize the native desktop application to the user-approved minimal terminal command-center design while preserving all existing control-plane behavior. Visual authority: `DESIGN.md`.

## WO-P1-063 resume state

- Branch: `feat/terminal-command-center-redesign`; base `main`/`origin/main` = `e131b8baffcd160d96b95db9e9380e6e2b4346c0`.
- Initial working tree was clean.
- SSoT/design gate complete; production source not yet changed at this checkpoint.
- Master brand asset: `assets/sunday-family-particle.png` (1448×1086).
- Preserve Add Brain, Add Connector, English buttons + localized help, copy logs, atomic assignment replacement, Donate, and lifecycle safety.
- Pointer motion must remain subtle: eyes ~2–3 px target; face/head parallax lower (~1–2 px), smooth return, no uncanny motion.
- Do not reintroduce periodic PowerShell/cmd subprocesses; read `DEFECT_LESSONS.md` before src edits.

## Previous objective (historical)

Finish `WO-P1-061` Sunday Family native GPU particle portrait with strict grayscale fidelity, then execute `WO-P1-062` responsive/global UI refresh. The repo plan was updated before WO-P1-062 implementation as explicitly required by the user.

## Status

`IN_PROGRESS / DESIGN_REVIEW` on branch `feat/gpu-sunday-family-particles-clean`.

- WO-P1-061 GPU path real smoke: previously PASS (`gpu-opengl`, ~9,360 particles, no GPU error).
- WO-P1-061 local implementation is verified: GPU + forced fallback E2E pass, grayscale-only contract enforced, portable build succeeds and bundles GPU/asset. Final frozen/full regression is deferred to GitHub CI because this workstation security layer returns `Access is denied` for freshly built PE files.
- Local Windows security/AV currently denies immediate reads of newly-created `.ps1` fixtures, so affected unrelated instance-management tests require CI confirmation rather than production-code changes.
- WO-P1-062 is `DESIGN_REVIEW / PARTIAL_IMPLEMENTATION`: requirements 1–10 have dirty partial code with focused test evidence; requirements 11–13 are planned but production work pauses for the explicitly-invoked brainstorming approval gate. Recommended design is bounded domain + UI extension (no rewrite).
- Connector inspection confirms desktop `Add Connector` already exists; GPT is not required. The Worker Connector column is the matching connector instance for the assigned project; `-` means no match. New connector creation requires a validated reference connector; Tunnel ID is optional/settable later.
- Model-routing research is durable at `docs/research/model-routing-2026-08-24.md`.

## Resume authority

Do not trust chat memory as the task source of truth. Use: `actual repo/GitHub state -> CURRENT-WORK.md -> handoff.md -> active work order -> PROJECT-PLAN/contracts`

## Current repository state

- Branch: `main` HEAD at UI redesign commit; v0.5.0 installed
 (PRs #35–#73 merged CI-green on 3 OS); v0.4.3 installed; repo health 100%; 5 connector instances all READY (see CURRENT-WORK fleet table); secrets + backups live in the A-Wiki-Data Drive layer
- Repo visibility: **public** (explicit user decision 2026-08-22; recorded in COLLAB.md)
- Release: https://github.com/aase7en/A-Wiki-Conductor/releases/tag/v0.2.0 (Setup + Portable + Notices; anonymous download verified)
- Full suite at close: 912 passed
- Local machine: real Setup.exe installed to `%LOCALAPPDATA%\Programs\A-Sunday Conductor\` (smoke OK, user DB preserved); window titles applied to all 13 instance `.cmd` files + `watchdog.ps1` (`.bak` backups beside each)

## Completed this session

- Window retitling: `Sunday-works 1/2/3 - <project>` across Start/Stop/Status/Configure/Provision/Watch scripts of conductor/phase6/wastewater instances; `Start-*.cmd` glob uniqueness verified intact; Status script re-run OK.
- Installer pipeline: `scripts/build_installer.py` (tested; shares AV-race hardening); real-run found + fixed the `icon` NameError with a regression test.
- Serena credit: `THIRD-PARTY-NOTICES.md` (full MIT text) in repo, in every install, and attached to the release.
- Version surface 0.2.0 (branding ↔ pyproject, test-enforced); tag `v0.2.0`.
- Lessons: ESET holds fresh exes ~2 min (retry open loop); phase6 `.cmd` files have mixed CR/LF line endings — insert `title` using each file's own first-line terminator.

## New this session (WO-P1-060)

- Worker slots: add (auto `a-worker-NN`), rename (display), delete (guarded) — PR #42.
- Connectors: create from a validated reference (port auto, `Sunday-works N` titles) — PR #43; alias rename + stop-first zip-backup delete — PR #44.
- Real-machine round trip verified (Serena-Smoketest create → discover → delete with zip; root restored to the original three).
- UI lesson: instance tree populates async (`refresh_instances` + `root.after`) — tests must call `refresh_instances()` then `root.update()` with an ImmediateExecutor.

## Next safe action

Read CURRENT-WORK.md "Next safe action": (a) trial `+ Worker` / `+ ตัวเชื่อม` in the real app, (b) user renames the ChatGPT plugin + reconnects, (c) rebuild+reinstall Start Menu build, (d) next §13 milestone.

## Do Not Do

- No MCP gateway work — deferred per ADR-0001 (docs/adr/).
- No A-Wiki primitive duplication; no target-project mutation for read-only features.
- No machine-wide env changes.
- Do not rename internal package/CLI/data folder without an explicit migration decision.
- Do not modify `C:\AI\serena-instances` scripts beyond this authorized retitling; `.bak` files allow rollback.

## Escalation

GLM 5.3 owns routine work. Escalate to **GPT-5.6 Sol UltraHigh** only for genuinely hard cross-cutting defects/architecture ambiguity, after checkpointing state.

## WO-P1-063 real-monitor extension

WO-P1-063 real-monitor extension: after the terminal-command-center visual slice, add factual CPU/RAM/app-uptime monitoring to SYSTEM OVERVIEW. Use a lightweight sampler with Windows native APIs / non-subprocess platform fallbacks. UI refresh target 2–5 seconds, bounded CPU history, clean `after_cancel` during close. Never fabricate metrics to match the visual reference.

## Resume checkpoint — WO-P1-063 real monitor implemented

Branch: `feat/terminal-command-center-redesign`. The native terminal-command-center redesign is implemented in the working tree and real CPU/RAM/app-uptime monitoring is now wired into SYSTEM OVERVIEW. New files: `src/a_conductor/system_metrics.py`, `tests/test_system_metrics.py`. Real UI smoke measured CPU 5%, RAM 9.2 / 15.9 GB, uptime 00:00:03; monitor timer cancelled cleanly. Focused redesign/GPU/monitor suite: 37 passed, 1 environment skip. Known local ESET fresh `.ps1` / fresh PE locks remain environment blockers; rely on GitHub CI for authoritative regression. Next safe action: commit implementation checkpoint, push/open PR, run 3-OS CI, fix real failures only, merge/fetch, rebuild/reinstall and visually compare with `DESIGN.md`.
