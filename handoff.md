# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Project

A-Wiki Conductor / product name **A-Conductor**.

## Current objective

Establish a local Git recovery/safety baseline before starting Phase 1 production implementation.

## Current phase

`Phase 1 — Multi-Serena Control Center / repository safety baseline`

## Current task

`WO-P1-000 — Local Repository Safety Baseline`

Status: `IN_PROGRESS`

## Completed

- A-Wiki reuse-before-build gate checked before architecture work.
- A-Wiki cross-agent work-order templates bootstrapped into this project.
- Continuity surfaces created: `AGENTS.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`.
- `WO-C1-001` completed: provider-neutral domain vocabulary and invariants documented.
- C1 schemas created: Task Contract, Repository Identity Gate, Evidence Record.
- All three schemas passed Draft 2020-12 schema validation and all three example instances passed instance validation.
- Root `.gitignore` created for Serena/local runtime/secrets/build artifacts.

## Evidence

C1 deterministic results:

- schema JSON parse: PASS (3)
- Draft 2020-12 `check_schema`: PASS (3)
- example validation: PASS (3/3)
- placeholder scan: clean

Contract SHA256:

- core domain: `4d0689dc29953aa54d128523ac6bf6e9008e63be21f97560d4a76b141ecadaf7`
- task contract: `000355629887896e24fec94e61e44cb5b84ea7f1d616f789d9857f9748f9d1a6`
- repository identity: `1acaef58c07f2499810d866a4327f37e385d193c37ba0e5be62552746972c12c`
- evidence record: `57292f14c42829fd4676d01af400478ff7e9652670091f4b3931ec0efe266ac0`

## Current repository state

At this checkpoint the project has **not yet been Git-initialized**. WO-P1-000 is specifically responsible for creating the local-only `main` baseline.

## Files/areas created or updated in the current project sequence

- `.gitignore`
- `AGENTS.md`
- `COLLAB.md`
- `CURRENT-WORK.md`
- `handoff.md`
- `PROJECT-PLAN.md` (prior approved planning work)
- `docs/contracts/core-domain.md`
- `docs/work-orders/README.md`
- `docs/work-orders/WO-TEMPLATE.md`
- `docs/work-orders/WO-C1-001-core-contracts.md`
- `docs/work-orders/WO-P1-000-repository-baseline.md`
- `schemas/task-contract.schema.json`
- `schemas/repository-identity.schema.json`
- `schemas/evidence-record.schema.json`
- `schemas/examples/*.example.json`

## Decisions made

- Product name: `A-Conductor`.
- Initial reusable slots: `A-Worker 1`, `A-Worker 2`, `A-Worker 3`.
- Serena is the first runtime implementation; `Worker` remains runtime-neutral.
- Reuse A-Wiki coordination primitives before building equivalents.
- Session memory is not durable project truth.
- C1 contracts precede production runtime/UI implementation.

## DECISION_REQUIRED

### DR-C1-001 — GitHub repository publication

Need explicit visibility/public-safety resolution before GitHub repo creation or remote configuration. Recommended default: private-first because current planning material includes machine-specific deployment evidence.

## Known problems / warnings

- Prior GitHub connector path returned `FORBIDDEN`; public A-Wiki GitHub remained inspectable read-only through the web.
- Local A-Wiki has unrelated dirty work and must remain untouched by A-Conductor tasks.
- Cross-machine claim visibility remains incomplete until A-Conductor has a Git remote/A-Wiki cross-repo pointer.

## Do not do

- Do not create/configure/push a GitHub remote during WO-P1-000.
- Do not modify A-Wiki or Phase 6.
- Do not reset/clean/stash/rebase/merge user work.
- Do not start UI/process-manager code before the local Git safety baseline is complete.

## TODO

See `CURRENT-WORK.md` and `docs/work-orders/WO-P1-000-repository-baseline.md`.

## Next safe action

Run local `git init -b main`, verify `.serena/` is ignored, inspect baseline files, then create a local-only bootstrap commit.

## Resume instructions

Read `AGENTS.md` -> `PROJECT-PLAN.md` -> `COLLAB.md` -> `CURRENT-WORK.md` -> this file -> active work order. Re-run the A-Wiki duplicate-work/claim gate if resuming in a new session or after a significant time gap.
