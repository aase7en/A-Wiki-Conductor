# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Native Execution Foundation — Work-class execution plane**

## Active work order

`docs/work-orders/WO-P1-032-native-git-verification-adapters.md`

Status: `IN_PROGRESS`

## Completed foundation

- [x] Phase 1 local Multi-Serena Control Center MVP.
- [x] A-Wiki ↔ A-Conductor sibling-repo responsibility contract.
- [x] P1-031 Native Execution Core: confined filesystem + authorized `shell=False` subprocess.
- [x] P1-031 verification: 16 targeted + 439 full-suite tests.

## Active checklist — WO-P1-032

- [x] Open bounded work order + adapter contract.
- [ ] Commit coordination checkpoint.
- [ ] Write RED Git/verification adapter tests.
- [ ] Implement fixed-method adapters.
- [ ] Run targeted/full/compile/diff/static verification.
- [ ] Close and commit work order.

## Safety boundary

- Git: read-only status/diff/cached-diff only in P1-032.
- Verification: fixed pytest/compileall shapes; requires mutation authority because tooling may create artifacts.
- No generic shell or model-supplied arbitrary argv adapter.
- Git stage/commit requires a later precondition/approval design.

## External / deferred gate

- `DR-P1-003`: live Worker 3 Stage B remains `BLOCKED_EXTERNAL` until a unique transport binding is explicitly provisioned/authorized.
- A-Wiki companion registration payload remains prepared and unapplied from this Conductor-pinned surface.

## Repository state

- Branch: `main`
- Base HEAD for P1-032: `24f4e33`
- Git remote: none

## Next safe action

Commit the P1-032 docs/claim checkpoint, then write RED tests proving fixed argv shapes, root-confined pathspecs, no Git mutation commands, and verification mutation gating.
