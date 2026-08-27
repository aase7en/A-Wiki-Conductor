# WO-P1-083 — Capability Fabric upgrade plan

Status: PLANNING_COMPLETE / IMPLEMENTATION_BLOCKED_ON_EXISTING_OWNERSHIP_GATES
Owner: GPT-5.6 Sol planning/integrator lane
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-capability-plan`
Branch: `docs/wo-p1-083-capability-upgrade-plan`
Base: `88c7d5bf0d23d719d56b80b45fc5c07da513b1a7`

## Goal

Create a durable, evidence-backed plan for adding high-value external skills/MCP/providers to A-Sunday Conductor and A-Wiki without duplicating existing brain, scheduler, runtime catalog, durable execution, or skill-registry authority.

Also create a **separate self-contained prompt for Project A-Wiki** so A-Wiki brain mutations occur in the correct project/session and do not get mixed with this A-Conductor work.

## Worker preflight / execution-surface decision

Actual SunDay worker/runtime evidence was inspected before delegation.

- Worker 3 is actively executing `env-wastewater-webapp` work and is unavailable.
- Worker 2 recently operated the v0.7 release worktree; ownership/session state is nontrivial, so it is not reassigned.
- Worker 5 is bound to `sunday-estate-webapp` with an unfinished feature branch; not assumed free.
- Worker 1 has a freshly initialized A-Conductor Serena session on the unsafe shared stale/dirty main worktree; not used.
- Worker 4 has only recent read-only A-Conductor inspection evidence and no repository mutation claim found, making it the safest candidate for a future bounded **read-only review**, but an established live connection means this lane does not rebind or mutate through it without stronger ownership proof.
Per repository safety rules, planning therefore uses Remote Desktop Commander in a new isolated docs-only worktree rather than stealing a live Worker/worktree.

## SAFE_TO_MUTATE gate

`SAFE_TO_MUTATE = YES` only for the new docs-only worktree and these additive files:

- `docs/work-orders/WO-P1-083-capability-upgrade-plan.md`
- `docs/plans/2026-08-27-capability-upgrade-a-conductor-a-wiki.md`
- `docs/prompts/A-WIKI-BRAIN-CAPABILITY-UPGRADE-PROMPT.md`

Forbidden:
- production code/tests/schemas;
- `PROJECT-PLAN.md`, `AGENTS.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md` hotspots;
- PR #102 / #104 worktrees;
- North Star N2/N3 mutable scopes;
- v0.7 release/uninstall/audit worktrees;
- A-Wiki mutation;
- live connectors/processes/ports.

## Sources / authority

Read/reconciled:
- repository `AGENTS.md`, `PROJECT-PLAN.md`, `DESIGN.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`;
- North Star `WO-P1-078` and implemented runtime-catalog/domain seams;
- GE-0005 brain bridge and GE-0007 durable-dispatch decisions;
- actual Git worktrees, remote main, open PR #102/#104, and SunDay worker runtime/log evidence;
- A-Wiki current Brain Improvement Gate / skill-registry architecture from authoritative GitHub state;
- external add-on research from the Charlie Hills capability survey, subject to upstream freshness re-verification before adoption.
## Deliverables

1. `docs/plans/2026-08-27-capability-upgrade-a-conductor-a-wiki.md`
   - target architecture;
   - reuse/extend boundaries;
   - P0/P1/P2 external capability priorities;
   - phased dependency graph and acceptance criteria.
2. `docs/prompts/A-WIKI-BRAIN-CAPABILITY-UPGRADE-PROMPT.md`
   - self-contained prompt to run only inside Project A-Wiki;
   - requires fresh repo/claim/upstream verification before mutation;
   - forbids bulk skill installation and A-Conductor mutation.

## Acceptance criteria

- plan extends existing Conductor capability/runtime/job-control seams instead of inventing parallel authority;
- A-Wiki remains brain/skill/memory authority;
- A-Wiki prompt follows Brain Improvement Gate and delta-adoption policy;
- external candidates are prioritized with security/cost/context/maintenance considerations;
- implementation dependencies on North Star/GE ownership are explicit;
- work is resumable without chat history;
- docs-only diff passes `git diff --check` and contains no secret material.

## Verification

Run:

```text
git status --short --branch
git diff --check
git diff --name-only
```

Changed paths must equal the three allowed additive docs above.

## Handoff / next safe action

Do not begin production implementation from this branch.

Next A-Conductor action after existing ownership gates reconcile: create a fresh bounded implementation WO for **C0 capability vocabulary reconciliation**.

Next A-Wiki action: copy the dedicated prompt into Project A-Wiki and let that project recover its own SSoT/claims before it creates any plan or mutation.

## Planning-time remote drift checkpoint

During this docs-only planning lane, `origin/main` advanced from `c72a550` to `64bc628` via merged PR #107 (`fix/v070-frozen-uninstall-self-delete`). Additional isolated v0.7 installer repair worktrees also appeared. This change is outside the three allowed planning files and does not justify rebasing/merging unrelated release code into this branch.

Before any future integration or implementation, fetch/reconcile current `origin/main` and all live claims/worktrees again. This plan branch intentionally remains based on the North Star integration point `88c7d5b` so its runtime-catalog context is preserved.
