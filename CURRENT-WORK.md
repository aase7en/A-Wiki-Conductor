# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Phase 1 — Multi-Serena Control Center / typed domain foundation**

C1 contracts and the local Git safety baseline are complete. Production implementation begins with a dependency-light typed domain layer only.

## Active work order

`docs/work-orders/WO-P1-001-domain-models.md`

Status: `IN_PROGRESS`

## Completed foundation

- [x] A-Wiki reuse-before-build gate checked.
- [x] A-Wiki work-order/claim/handoff primitives reused and bootstrapped.
- [x] C1 canonical vocabulary/invariants completed.
- [x] Task/RepositoryIdentity/Evidence schemas created and mechanically validated.
- [x] Local Git repository initialized on `main`.
- [x] `.serena/` and local runtime/secrets artifacts ignored.
- [x] Local architecture baseline commit created: `3ed22df0d884cf15729167d923ec4a0e32593662`.
- [x] No Git remote configured; no push performed.

## Active checklist — WO-P1-001

- [x] Confirm Python 3.11+ and pytest availability.
- [x] Define stdlib-first implementation strategy; no runtime framework lock-in.
- [x] Open/claim WO-P1-001.
- [ ] Commit work-order/claim checkpoint before source changes.
- [ ] Add minimal pytest config for `src/` layout.
- [ ] Write failing domain contract tests first.
- [ ] Capture expected red test result.
- [ ] Implement minimal typed domain models.
- [ ] Run pytest green.
- [ ] Run compileall + provider/runtime leakage review.
- [ ] Update checkpoint + handoff and commit coherent implementation batch.

## C1 verification evidence

- JSON parse: PASS (3 schemas).
- Draft 2020-12 `check_schema`: PASS (3 schemas).
- Example validation: PASS (3/3).
- Placeholder scan: clean.

## Repository state

- Branch: `main`
- Baseline content commit: `3ed22df0d884cf15729167d923ec4a0e32593662`
- Git remote: none
- Git ownership note: this filesystem triggers Git's dubious-ownership guard; commands in this session use exact per-command `-c safe.directory=A:/GitHub/A-Wiki-Conductor`. Global Git config has not been modified.

## DECISION_REQUIRED

### DR-C1-001 — GitHub repository publication

Need explicit visibility/public-safety decision before GitHub repo creation/remote configuration. Recommended default: **private-first** because planning material contains machine-specific deployment evidence.

This does not block local Phase 1 implementation.

## Constraints

- No GitHub remote/push until DR-C1-001 is resolved.
- No A-Wiki or Phase 6 mutation.
- No Serena/tunnel/process-manager implementation in WO-P1-001.
- No UI, broker, network, or provider SDK integration in WO-P1-001.
- No duplicate A-Wiki coordination engine.

## Next safe action

Commit the WO-P1-001 claim/checkpoint, then create the failing domain-model tests before writing `src/a_conductor/domain.py`.
