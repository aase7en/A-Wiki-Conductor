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
- [x] Cross-repo boundary contract established: A-Conductor stays a sibling repo; A-Wiki companion registration payload prepared in `docs/contracts/a-wiki-companion-registration-payload.md`.

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

Resume the existing uncommitted P1-030 implementation without resetting it: inspect actual `runtime_setup.py`, `desktop_control.py`, `desktop_ui.py`, and targeted tests; fix the known atomic Serena-config copy portability issue and stale UI/test wiring; then run unique targeted tests before the full suite. The cross-repo contract checkpoint is complete on the A-Conductor side; A-Wiki registration remains an explicit apply-later step.
