# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Phase 1 — Multi-Serena Control Center / runtime-manager contract extraction**

## Active work order

`docs/work-orders/WO-P1-002-serena-runtime-contract.md`

Status: `IN_PROGRESS`

## Completed foundation

- [x] A-Wiki reuse/work-order/claim gate checked and reused.
- [x] C1 domain contract + Task/RepositoryIdentity/Evidence schemas complete and validated.
- [x] Local Git safety baseline complete on `main`.
- [x] Typed provider-neutral core domain implemented test-first.
- [x] `pytest -q`: 17 passed for WO-P1-001.
- [x] Typed domain implementation commit: `dbf5b34c44a3a10d70bf994a78739324c43bfe7a`.

## Active checklist — WO-P1-002

- [x] Open/claim runtime-contract work order.
- [ ] Commit the WO-P1-002 coordination checkpoint.
- [ ] Inspect external multi-Serena runbook read-only.
- [ ] Inspect representative instance/start/stop/status scripts read-only.
- [ ] Extract stable product concepts vs machine-specific/private details.
- [ ] Define runtime profile + ownership + health + tunnel binding contract.
- [ ] Define lifecycle, collision, stale PID, identity-failure, and recovery semantics.
- [ ] Secret/tunnel-credential leakage scan.
- [ ] `git diff --check`.
- [ ] Update checkpoint + handoff and commit docs batch.

## Repository state

- Branch: `main`
- Current HEAD before WO-P1-002 docs checkpoint: `dbf5b34c44a3a10d70bf994a78739324c43bfe7a`
- Git remote: none
- Git dubious-ownership guard: use exact per-command `-c safe.directory=A:/GitHub/A-Wiki-Conductor`; global config remains untouched.

## DECISION_REQUIRED

### DR-C1-001 — GitHub repository publication

Need explicit visibility/public-safety decision before GitHub repo creation/remote configuration. Recommended default: **private-first** because current planning material contains machine-specific deployment evidence.

This does not block local Phase 1 work.

## Constraints

- External prototype under `C:/AI/serena-instances/` is read-only evidence.
- No process start/stop/tunnel provisioning in WO-P1-002.
- No process-manager source code yet.
- No secrets/tunnel credentials copied into tracked files.
- No A-Wiki or Phase 6 mutation.
- No Git remote/push.

## Next safe action

Commit the WO-P1-002 claim/checkpoint, then inspect the external validated multi-Serena runbook and scripts read-only.
