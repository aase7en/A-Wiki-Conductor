# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Phase 1 — Multi-Serena Control Center / runtime setup**

## Active work order

`docs/work-orders/WO-P1-030-runtime-setup.md`

Status: `IN_PROGRESS`

## Completed

- [x] Local process-manager/runtime safety stack through tunnel/preflight boundaries.
- [x] Control Center service + desktop shell.
- [x] Durable Serena config + lifecycle coordinator/assembly.
- [x] Desktop lifecycle wiring.
- [x] Stage B transport gate `DR-P1-003` remains isolated.

## Active checklist — WO-P1-030

- [x] Open work order.
- [ ] Claim + commit coordination checkpoint.
- [ ] Write RED setup-service/UI tests.
- [ ] Implement worker setup/readiness + exact Git capture.
- [ ] Add desktop Setup dialog and readiness-aware Start enablement.
- [ ] Run targeted/full/smoke verification.
- [ ] Close/commit work order.

## Repository state

- Branch: `main`
- Git remote: none

## Next safe action

Claim/commit P1-030, then write failing runtime setup/readiness/Git capture tests before implementation.
