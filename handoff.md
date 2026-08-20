# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Project

A-Wiki Conductor / product name **A-Conductor**.

## Current objective

Extract a product-grade Serena runtime-manager contract from the validated manual multi-instance deployment before implementing any process manager.

## Current phase

`Phase 1 — Multi-Serena Control Center / runtime-manager contract extraction`

## Current task

`WO-P1-002 — Serena Runtime Manager Contract from Validated Prototype`

Status: `IN_PROGRESS`

## Completed

- C1 provider-neutral domain/invariant contract complete.
- Task/RepositoryIdentity/Evidence JSON Schemas complete and mechanically validated.
- Local Git safety baseline complete on `main`.
- WO-P1-001 typed core domain implemented test-first; `17 passed`.
- Implementation commit: `dbf5b34c44a3a10d70bf994a78739324c43bfe7a`.
- WO-P1-002 opened and claimed for docs-only/read-only runtime contract extraction.

## Evidence

- `pytest -q`: 17 passed for typed domain.
- `python -m compileall -q src`: PASS.
- provider/product leakage scan in `src/a_conductor/domain.py`: clean.
- Git current HEAD before WO-P1-002 coordination commit: `dbf5b34c44a3a10d70bf994a78739324c43bfe7a`.

## Repository state

- branch: `main`
- Git remote: none
- Git safe-directory guard is handled per-command only; global Git config was not modified.

## Decisions made

- Worker remains runtime-neutral; Serena is first runtime implementation only.
- External multi-Serena launcher/runbook is implementation evidence, not product source to copy blindly.
- WO-P1-002 is docs-only/read-only; process code begins only after this contract is reviewed.

## DECISION_REQUIRED

### DR-C1-001 — GitHub repository publication

Need explicit visibility/public-safety decision before creating/configuring a GitHub remote. Recommended default: private-first.

## Known problems / warnings

- No GitHub remote/cross-machine A-Conductor claim visibility yet.
- External runtime prototype may contain machine-specific or secret-adjacent configuration. Only stable concepts may be recorded; credentials/tunnel IDs must not be copied.
- Local A-Wiki has unrelated dirty work and remains read-only.

## Do not do

- Do not modify `C:/AI/serena-instances/` during WO-P1-002.
- Do not start/stop runtime processes or tunnels.
- Do not modify A-Wiki/Phase6.
- Do not create Git remote/push.

## TODO

See `CURRENT-WORK.md` and `docs/work-orders/WO-P1-002-serena-runtime-contract.md`.

## Next safe action

Commit the WO-P1-002 coordination checkpoint, then inspect the external runbook and representative runtime scripts read-only.

## Resume instructions

Read `AGENTS.md` -> `PROJECT-PLAN.md` -> `COLLAB.md` -> `CURRENT-WORK.md` -> this file -> active WO. Re-run duplicate-work/claim checks when resuming in a new session or after significant time.
