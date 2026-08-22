# HANDOFF — A-Sunday Conductor

Last updated: 2026-08-22 (GLM 5.3, post 5-connector rollout)

## Current objective

v0.2.4: A-Doctor deep audit fixed (AUTO column, reaper boundary, PS quoting, async MONITOR, symmetric error tables). Ready for the next A-Wiki session to plug in.

## Status

`COMPLETE` for the authorized scope (rename all CMD windows / installable + downloadable via GitHub / Serena credit).

## Resume authority

Do not trust chat memory as the task source of truth. Use: `actual repo/GitHub state -> CURRENT-WORK.md -> handoff.md -> active work order -> PROJECT-PLAN/contracts`

## Current repository state

- Branch: `main` (PRs #35–#58 merged CI-green); 5 connector instances all READY (see CURRENT-WORK fleet table); secrets + backups live in the A-Wiki-Data Drive layer
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
