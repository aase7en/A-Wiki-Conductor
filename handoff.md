# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Current objective

Phase 1 local Control Center MVP is complete. Preserve the validated runtime/lifecycle/setup foundation and continue toward the Work-class durable agent tunnel North Star without duplicating A-Wiki orchestration.

## Current task

No active work order.

Most recently completed: `WO-P1-030 — Runtime Setup Service + Desktop Dialog`.

## Completed / evidence

- Local process-manager/runtime safety stack complete.
- Control Center service + desktop shell complete.
- Desktop Start/Stop/Restart runs through background lifecycle execution and code-only error logging.
- Runtime Setup persists only non-secret runtime metadata, atomically bootstraps worker-owned `SERENA_HOME/serena_config.yml`, and never exposes tunnel/reference file contents.
- Exact Git identity capture is fixed/read-only; NO_GIT binding exists.
- Start is readiness-gated; Setup dialog exposes paths/ports/reference IDs only.
- Targeted P1-030 verification: 34 passed.
- Final full suite after separate lifecycle-assembly baseline repair: 423 passed.
- compileall: PASS; git diff check: PASS; UI secret-value-field scan: PASS.
- Desktop smoke: `A-CONDUCTOR_SMOKE_OK projects=0 workers=3`.
- Active Conductor listener preserved: `127.0.0.1:18011`, PID `25396` before/after smoke.
- P1-028 baseline regression repaired separately in commit `4f4b943`.
- A-Wiki ↔ A-Conductor responsibility contract is binding at `docs/contracts/a-wiki-a-conductor-integration.md`; A-Conductor remains a separate sibling repo.
- A-Wiki companion registration/master-work-order payload is prepared in `docs/contracts/a-wiki-companion-registration-payload.md` but is not yet applied to A-Wiki.

## External / deferred gate

`DR-P1-003 / BLOCKED_EXTERNAL`: Worker 3 live Stage B requires a unique authorized transport binding. Never reuse the active Conductor or Phase6 tunnel/profile and never auto-run credential-bearing provisioning.

## Repository state before final P1-030 commit

- branch: `main`
- no Git remote
- expected remaining worktree delta: P1-030 source/tests/docs only

## Next safe action

After verifying a clean post-commit worktree, open a new bounded work order. Preferred unblocked direction: Native Execution Layer (filesystem/safe subprocess/Git/tests/artifacts) while Serena stays the semantic code specialist and A-Wiki remains brain/policy/orchestration knowledge. A separate valid next action is applying the prepared A-Wiki companion registration payload through an authorized A-Wiki execution surface.

## Resume instructions

Read `AGENTS.md` -> `PROJECT-PLAN.md` -> `docs/contracts/a-wiki-a-conductor-integration.md` -> `COLLAB.md` -> `CURRENT-WORK.md` -> this file; verify branch/HEAD/status before mutation and run the A-Wiki reuse-before-build gate before architecture overlap.
