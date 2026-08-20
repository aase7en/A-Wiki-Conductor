# WO-C1-002: A-Wiki ↔ A-Conductor Cross-Repo Integration Contract

Status: completed
Lane/files: `docs/contracts/a-wiki-a-conductor-integration.md`, `docs/contracts/a-wiki-companion-registration-payload.md`, `PROJECT-PLAN.md`, `CURRENT-WORK.md`, `handoff.md`, `COLLAB.md`, `docs/work-orders/WO-C1-002-cross-repo-integration.md`
Branch: main
Model tier: high

## Goal + Acceptance criteria

- Establish a durable responsibility boundary between A-Wiki and A-Conductor.
- Keep A-Conductor as a separate sibling Git repo, not an A-Wiki worktree by default.
- Reuse A-Wiki's existing sibling-companion pattern rather than inventing a parallel registry.
- Define anti-duplication classification: `REUSE`, `WRAP`, `EXTEND`, `REPLACE`, `NEW`.
- Define logical cross-repo interfaces: `ExecutionRequest`, `PolicySnapshot`, `EvidenceBundle`, `ExecutionResult`.
- Prepare an apply-ready A-Wiki companion registration payload without mutating A-Wiki from the pinned A-Conductor execution surface.
- Preserve all existing uncommitted `WO-P1-030` implementation work untouched and resumable.
- Stage/commit docs and continuity only; no `src/**` or `tests/**` from P1-030.

## Reference pattern

- A-Wiki `AGENTS.md` sibling-repo entry for `env-wastewater-webapp`.
- A-Wiki `wiki/entities/env/env-webapp-project.md` companion project entity.
- A-Wiki `docs/protocols/cross-agent-work-orders.md`.
- A-Conductor `PROJECT-PLAN.md` §16 reuse-before-build gate.

## Steps

1. Verify A-Conductor project identity/status and existing P1-030 uncommitted work.
2. Inspect A-Wiki companion-project precedent read-only.
3. Add responsibility/integration contract.
4. Add A-Wiki apply-ready registration payload.
5. Reference the contract from `PROJECT-PLAN.md`.
6. Update continuity to record this completed architecture checkpoint and immediately resume P1-030 as active work.
7. Verify diff/staging boundaries and commit docs-only.

## Forbidden

- No modification to `A:\GitHub\A-Wiki` from the pinned Sunday-Conducter instance.
- No source/test mutation for P1-030 as part of this work order.
- No reset/clean/stash/checkout/switch/rebase/merge.
- No remote creation/push.
- No broad process operations.
- No claim that A-Wiki registration is applied until an authorized A-Wiki mutation actually occurs.

## Verify commands

- `git diff --check`
- inspect `git status --short`
- inspect staged file list before commit
- verify staged list contains no `src/**` or `tests/**`
- scan contract/payload for `REUSE`, `WRAP`, `EXTEND`, `ExecutionRequest`, `PolicySnapshot`, `EvidenceBundle`, `ExecutionResult`, and sibling-repo rule

## Checkpoint log

- [2026-08-20] ChatGPT / Sunday-Conducter: verified A-Wiki read-only precedent for sibling repo + companion entity; created integration contract and registration payload; P1-030 source remains untouched.
- [2026-08-20] ChatGPT / Sunday-Conducter: work order completed on A-Conductor side; A-Wiki apply step remains explicitly pending until authorized execution against the A-Wiki repo.