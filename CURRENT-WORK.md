# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Phase 1 — Multi-Serena Control Center / repository safety baseline**

C1 core contracts are complete. Before production implementation, establish a local Git identity/checkpoint.

## Active work order

`docs/work-orders/WO-P1-000-repository-baseline.md`

Status: `IN_PROGRESS`

## Completed foundation

- [x] A-Wiki reuse-before-build gate checked.
- [x] A-Wiki cross-agent work-order system bootstrapped into this project.
- [x] `AGENTS.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md` continuity surfaces created.
- [x] WO-C1-001 canonical domain vocabulary + invariants completed.
- [x] Task Contract JSON Schema created and validated.
- [x] Repository Identity Gate JSON Schema created and validated.
- [x] Evidence Record JSON Schema created and validated.
- [x] Example instances validate against all three schemas.

## Active checklist — WO-P1-000

- [x] Create conservative root `.gitignore` for Serena/local runtime/secrets artifacts.
- [ ] Initialize local Git on `main`.
- [ ] Verify `.serena/` is ignored.
- [ ] Inspect untracked/staged project files.
- [ ] Create local bootstrap commit(s).
- [ ] Verify branch/HEAD/clean status.
- [ ] Verify no Git remote exists and no push occurred.
- [ ] Update work-order checkpoint + handoff.

## C1 verification evidence

- JSON parse: PASS (3 schemas).
- JSON Schema Draft 2020-12 `check_schema`: PASS (3 schemas).
- Example instance validation: PASS (3/3).
- Placeholder scan on contract/schema artifacts: clean.
- SHA256:
  - `docs/contracts/core-domain.md`: `4d0689dc29953aa54d128523ac6bf6e9008e63be21f97560d4a76b141ecadaf7`
  - `schemas/task-contract.schema.json`: `000355629887896e24fec94e61e44cb5b84ea7f1d616f789d9857f9748f9d1a6`
  - `schemas/repository-identity.schema.json`: `1acaef58c07f2499810d866a4327f37e385d193c37ba0e5be62552746972c12c`
  - `schemas/evidence-record.schema.json`: `57292f14c42829fd4676d01af400478ff7e9652670091f4b3931ec0efe266ac0`

## DECISION_REQUIRED

### DR-C1-001 — GitHub repository publication

A-Conductor needs durable GitHub history and an A-Wiki cross-repo pointer, but current planning material includes machine-specific deployment evidence/paths.

Recommended default: **private repository first**, then extract/promote public-safe reusable material later if desired.

This does not block local Git initialization or Phase 1 local implementation.

## Constraints

- Do not create/publish/configure a GitHub remote until DR-C1-001 is resolved.
- Do not modify A-Wiki or A-Wiki Phase 6.
- Do not start UI/process-manager implementation during WO-P1-000.
- Do not fork Serena.
- Do not duplicate A-Wiki claim/work-order/handoff primitives.

## Next safe action

Initialize **local-only Git** on `main`, inspect the exact baseline file set, and create a clean recovery checkpoint without configuring a remote.
