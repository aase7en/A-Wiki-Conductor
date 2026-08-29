# WO-P1-085 — Capability Fabric upgrade plan

Status: COMPLETE / MERGED - PR #109 (`9106da2`); successor implementation moved to WO-P1-086+ / AHA lanes
Owner: GPT-5.6 Sol planning/integrator lane
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-capability-plan-main`
Branch: `docs/wo-p1-085-capability-upgrade-plan`
Base: `64bc628e233a6fb596a7dc6d188f7cdef35b3bbe`

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

- `docs/work-orders/WO-P1-085-capability-upgrade-plan.md`
- `docs/plans/2026-08-27-capability-upgrade-a-conductor-a-wiki.md`
- `docs/prompts/A-WIKI-BRAIN-CAPABILITY-UPGRADE-PROMPT.md`
- `docs/reviews/WO-P1-085-branch-defect-overlap-audit.md`

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
3. `docs/reviews/WO-P1-085-branch-defect-overlap-audit.md`
   - all-branch/worktree conflict and overlap archaeology;
   - deterministic defect proofs, GLM benchmark evidence, and anti-overlap integration order.

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

Changed paths must equal the four allowed additive docs above.

## Handoff / next safe action

Do not begin production implementation from this branch.

Next A-Conductor action after existing ownership gates reconcile: create a fresh bounded implementation WO for **C0 capability vocabulary reconciliation**.

Next A-Wiki action: copy the dedicated prompt into Project A-Wiki and let that project recover its own SSoT/claims before it creates any plan or mutation.

## Planning-time remote drift checkpoint

During this docs-only planning lane, `origin/main` advanced from `c72a550` to `64bc628` via merged PR #107 (`fix/v070-frozen-uninstall-self-delete`). Additional isolated v0.7 installer repair worktrees also appeared. This change was outside the original planning scope and did not justify merging unrelated release code into the superseded branch; the replacement main-based lane adds only its bounded review document as a fourth allowed file.

Before any future integration or implementation, fetch/reconcile current `origin/main` and all live claims/worktrees again. The superseded backup branch remains at the historical North Star lineage; this replacement planning branch is deliberately based on current `origin/main@64bc628` so its PR contains only planning/audit documentation.

## Branch-repair checkpoint — 2026-08-27

The first backup branch docs/wo-p1-083-capability-upgrade-plan was intentionally pushed but was discovered during branch archaeology to be based on the North Star feature lineage (88c7d5b) rather than current main, making a PR from it unsafe because it would carry unrelated North Star commits. A newer installer lane also already owns WO-P1-083. This clean replacement branch starts from origin/main@64bc628, renames this plan to WO-P1-085, and treats the earlier remote branch as backup/superseded only. No PR should be opened from the superseded branch.

## Branch archaeology / defect-audit checkpoint — 2026-08-27

Detailed evidence: `docs/reviews/WO-P1-085-branch-defect-overlap-audit.md`.

Key reconciliation results:
- current `origin/main = 64bc628`; no tested branch has a textual merge-tree conflict against it;
- old capability branch `docs/wo-p1-083-capability-upgrade-plan` is superseded because it carries unrelated North Star ancestry and collides with installer WO-P1-083 identity;
- replacement lane is this clean main-based WO-P1-085 branch;
- PR #102/#104/#108 are currently mergeable with green 3-OS CI, but green CI does not close the semantic/spec defects recorded in the review;
- P0 blockers found: GE glob/glob conflict false-negative, GE-6 accepted-contract omissions, installer empty-target uninstall authorization;
- current GLM evidence supports bounded deterministic TDD lanes for PR #102 then PR #104, with GPT final integration review;
- no SunDay Worker was reassigned or reused from another Project during this audit.

Next safe action: persist/push this docs-only review branch and open a Draft PR. Do not merge production branches from this planning lane.

## Remote checkpoint — 2026-08-27

- canonical planning branch pushed: `docs/wo-p1-085-capability-upgrade-plan`;
- Draft PR: #109 `docs: capability fabric upgrade plan and branch audit`;
- verified PR base: `main@64bc628`;
- verified PR head before this checkpoint: `172235904b7270b7ffa73ecc985a35f5c113e356`;
- GitHub final diff contained exactly the four allowed additive docs and was MERGEABLE; CI started automatically;
- old remote `docs/wo-p1-083-capability-upgrade-plan` remains superseded backup only, with no PR.
