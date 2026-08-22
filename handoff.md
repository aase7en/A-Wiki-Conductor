# HANDOFF — A-Sunday Conductor

Last updated: 2026-08-22 (GLM 5.3, post v0.2.0 public release)

## Current objective

Console-window retitling + public v0.2.0 release shipped. Awaiting user trial (window titles, Start Menu app, plugin rename in ChatGPT) or next milestone pick.

## Status

`COMPLETE` for the authorized scope (rename all CMD windows / installable + downloadable via GitHub / Serena credit).

## Resume authority

Do not trust chat memory as the task source of truth. Use: `actual repo/GitHub state -> CURRENT-WORK.md -> handoff.md -> active work order -> PROJECT-PLAN/contracts`

## Current repository state

- Branch: `main`, HEAD `2da3d01`; PRs #35–#40 merged CI-green
- Repo visibility: **public** (explicit user decision 2026-08-22; recorded in COLLAB.md)
- Release: https://github.com/aase7en/A-Wiki-Conductor/releases/tag/v0.2.0 (Setup + Portable + Notices; anonymous download verified)
- Full suite at close: 872 passed
- Local machine: real Setup.exe installed to `%LOCALAPPDATA%\Programs\A-Sunday Conductor\` (smoke OK, user DB preserved); window titles applied to all 13 instance `.cmd` files + `watchdog.ps1` (`.bak` backups beside each)

## Completed this session

- Window retitling: `Sunday-works 1/2/3 - <project>` across Start/Stop/Status/Configure/Provision/Watch scripts of conductor/phase6/wastewater instances; `Start-*.cmd` glob uniqueness verified intact; Status script re-run OK.
- Installer pipeline: `scripts/build_installer.py` (tested; shares AV-race hardening); real-run found + fixed the `icon` NameError with a regression test.
- Serena credit: `THIRD-PARTY-NOTICES.md` (full MIT text) in repo, in every install, and attached to the release.
- Version surface 0.2.0 (branding ↔ pyproject, test-enforced); tag `v0.2.0`.
- Lessons: ESET holds fresh exes ~2 min (retry open loop); phase6 `.cmd` files have mixed CR/LF line endings — insert `title` using each file's own first-line terminator.

## Next safe action

Read CURRENT-WORK.md "Next safe action": (a) double-click `Start-Serena-Phase6.cmd` to see the new title, (b) rename the ChatGPT plugin + reconnect (user task), (c) next §13 milestone with new work order + reuse gate.

## Do Not Do

- No MCP gateway hard enforcement (backlog / DECISION_REQUIRED).
- No A-Wiki primitive duplication; no target-project mutation for read-only features.
- No machine-wide env changes.
- Do not rename internal package/CLI/data folder without an explicit migration decision.
- Do not modify `C:\AI\serena-instances` scripts beyond this authorized retitling; `.bak` files allow rollback.

## Escalation

GLM 5.3 owns routine work. Escalate to **GPT-5.6 Sol UltraHigh** only for genuinely hard cross-cutting defects/architecture ambiguity, after checkpointing state.
