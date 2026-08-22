# HANDOFF — A-Sunday Conductor

Last updated: 2026-08-22 (GLM 5.3, post E2E + rename + reinstall)

## Current objective

E2E real-system suite, product rename to A-Sunday Conductor, and the local reinstall all shipped. Awaiting user trial of the installed app or next milestone pick.

## Status

`COMPLETE` for the authorized scope (E2E test per user request + naming + rebuild/reinstall).

## Resume authority

Do not trust chat memory as the task source of truth. Use: `actual repo/GitHub state -> CURRENT-WORK.md -> handoff.md -> active work order -> PROJECT-PLAN/contracts`

## Current repository state

- Branch: `main`, HEAD `22bc0e6` (merge of PR #36); PRs #35–#36 merged CI-green
- Full suite at close: 866 passed, 0 failed
- Working tree clean apart from this SSoT commit
- Local machine: fresh install at `%LOCALAPPDATA%\Programs\A-Sunday Conductor\` (Start Menu + Desktop + HKCU verified; smoke `A-CONDUCTOR_SMOKE_OK projects=4 workers=3`); user DB preserved at `%LOCALAPPDATA%\A-Conductor\control-center.sqlite`

## Completed this session

- PR #35 E2E real-system suite (24 tests) + 2 bug fixes (rebind regex escape, `open(instances_root=...)`).
- PR #36 rename: `a_conductor.branding.APP_NAME = "A-Sunday Conductor"` single-sources titles/installer/build; legacy names (package, CLI, data folder) intentionally kept for upgrade continuity.
- Reinstall on this machine: old install removed cleanly; new build installed and smoke-verified.
- New lessons: ESET can hold a freshly built exe read-locked for ~2 minutes (retry `shutil.copy2` in a loop); `py -V:Astral/CPython3.11.15 -m venv` works when the PATH `python` is itself a venv whose ensurepip fails.

## Next safe action

Read CURRENT-WORK.md "Next safe action": (a) trial installed app from Start Menu, (b) next §13 milestone with new work order + reuse gate, (c) MCP gateway backlog. 

## Do Not Do

- No MCP gateway hard enforcement (backlog / DECISION_REQUIRED).
- No A-Wiki primitive duplication; no target-project mutation for read-only features.
- No machine-wide env changes.
- Do not rename internal package/CLI/data folder without an explicit migration decision.

## Escalation

GLM 5.3 owns routine work. Escalate to **GPT-5.6 Sol UltraHigh** only for genuinely hard cross-cutting defects/architecture ambiguity, after checkpointing state.
