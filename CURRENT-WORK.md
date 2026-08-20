# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Phase 1 — Multi-Serena Control Center local MVP complete**

## Active work order

None.

Most recently completed:
- `WO-P1-030 — Runtime Setup Service + Desktop Dialog`
- `WO-P1-028R1 — Lifecycle Assembly Contract Regression Repair`
- `WO-C1-002 — A-Wiki ↔ A-Conductor Cross-Repo Integration Contract`

## Completed

- [x] Local process-manager/runtime safety stack through tunnel/preflight boundaries.
- [x] Control Center service + desktop shell.
- [x] Durable Serena config + lifecycle coordinator/assembly.
- [x] Desktop lifecycle Start/Stop/Restart through background executor.
- [x] Runtime Setup service with opaque Serena config bootstrap and tunnel-reference metadata.
- [x] Exact read-only Git project identity capture + explicit NO_GIT binding.
- [x] Readiness-aware Start gating and Setup dialog with no secret-value fields.
- [x] Cross-repo A-Wiki ↔ A-Conductor responsibility contract; A-Conductor remains a sibling repo.
- [x] Final verification: 34 targeted + 423 full-suite tests, compileall, diff check, UI secret-field scan, desktop smoke.
- [x] Active Conductor listener preserved at PID 25396 during smoke.

## External / deferred gate

- `DR-P1-003`: live Worker 3 Stage B remains `BLOCKED_EXTERNAL` until a unique transport binding is explicitly provisioned/authorized. Do not reuse Conductor/Phase6 transport.
- A-Wiki companion registration payload is prepared at `docs/contracts/a-wiki-companion-registration-payload.md` but has not yet been applied to the A-Wiki repo from an authorized A-Wiki execution surface.

## Repository state

- Branch: `main`
- Git remote: none

## Next safe action

Open the next bounded work order before implementation. The strongest unblocked North-Star-aligned candidate is a Native Execution Layer contract/first primitives for filesystem/safe subprocess/Git/test execution, classified against A-Wiki as execution-layer `NEW/EXTEND` rather than a second orchestrator. Alternatively, apply the prepared A-Wiki companion registration payload using an authorized A-Wiki execution surface. Do not start live Worker 3 provisioning without explicit authorization.
