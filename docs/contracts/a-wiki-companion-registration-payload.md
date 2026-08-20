# A-Wiki Companion Registration Payload — A-Conductor

Status: READY_TO_APPLY_TO_A_WIKI
Prepared: 2026-08-20
Target repo: `A-Wiki`
Source repo: `A-Wiki-Conductor`

## Purpose

Register A-Conductor inside A-Wiki as a sibling companion project so future A-Wiki agents can discover that the execution-control-plane product already exists before implementing overlapping runtime/orchestration work.

This file is a payload/preparation artifact only. The current Sunday-Conducter instance is pinned to `A-Wiki-Conductor`; it must not mutate `A-Wiki` from here.

## Existing A-Wiki precedent verified read-only

A-Wiki currently documents `env-wastewater-webapp` as a sibling repo in `AGENTS.md` and keeps a durable project entity in `wiki/entities/env/env-webapp-project.md`. Therefore the preferred integration is to **reuse that companion-project pattern**, not invent a second registry format unless A-Wiki's current authoritative state changes.

## Proposed A-Wiki registration

### 1. Add a companion project entity

Preferred semantic location:

`wiki/entities/meta/a-conductor-project.md`

If A-Wiki has introduced a newer authoritative companion-project registry before application, use that current convention instead and record the migration. Do not create duplicate registries.

Suggested content:

```markdown
# A-Conductor (A-Wiki-Conductor sibling repo)

**Product**: A-Conductor
**Repository**: `A-Wiki-Conductor`
**Relationship**: sibling Git repository; separate Git history from A-Wiki
**Role**: durable local/hybrid execution control plane and Work-class agent tunnel
**Status**: active development

## North Star

Accept a high-level goal once and execute it through durable, checkpointed, resumable, cost-aware workers with native filesystem/shell/Git/test/build capabilities, semantic code specialists, external durable workers, and Discord/Desktop operator surfaces.

The objective is to use local/free/low-cost/deterministic workers whenever sufficient, reserving premium GPT/Claude-class workers for high-value reasoning/review. This reduces premium quota consumption; it does not bypass provider limits or access controls.

## Responsibility boundary

- **A-Wiki** owns durable brain/policy/knowledge, architectural decisions, skills, memory conventions, work-order/claim conventions, and reusable orchestration intelligence.
- **A-Conductor** owns durable execution/runtime state, worker pool, process/PID/port/tunnel supervision, filesystem/shell/Git/test/build execution, checkpoints/recovery/evidence, provider/runtime adapters, and Discord/Desktop operator surfaces.
- **A-Workers** perform bounded work through replaceable runtime/provider adapters.

## Do not duplicate

Before implementing a new execution-control capability in A-Wiki, inspect A-Conductor first for:
- worker/runtime lifecycle management;
- owned process supervision;
- PID/port/tunnel isolation;
- durable execution checkpoints/recovery;
- runtime evidence/journaling;
- native execution engine work;
- desktop/Discord execution-control surfaces;
- provider/runtime worker adapters.

Before A-Conductor implements orchestration/memory/claim/work-order/model-policy capabilities, inspect current A-Wiki first and classify `REUSE`, `WRAP`, `EXTEND`, `REPLACE`, or `NEW`.

## Integration contract

Authoritative A-Conductor-side boundary:
`docs/contracts/a-wiki-a-conductor-integration.md`

Expected logical interfaces:
- `ExecutionRequest` — A-Wiki/orchestrator -> A-Conductor
- `PolicySnapshot` — A-Wiki -> A-Conductor
- `EvidenceBundle` — A-Conductor -> A-Wiki/reviewer
- `ExecutionResult` — A-Conductor -> A-Wiki/orchestrator

## Continuity entry points in A-Conductor

- `PROJECT-PLAN.md`
- `COLLAB.md`
- `CURRENT-WORK.md`
- `handoff.md`
- `docs/work-orders/`
- `docs/contracts/a-wiki-a-conductor-integration.md`

## Repository rule

A-Conductor remains a separate sibling repo. It is not an A-Wiki worktree and should not be converted into one without an explicit architecture decision covering migration and compatibility.
```

### 2. Add a companion pointer to A-Wiki `AGENTS.md`

Preferred action: extend the existing sibling/companion-repository section/table that already mentions `env-wastewater-webapp`.

Suggested semantic row/content:

```text
A-Wiki-Conductor | sibling repo, separate Git history | companion execution-control-plane pointer | durable worker/runtime/execution/recovery/Discord/Desktop product; A-Wiki remains brain/policy/memory/orchestration knowledge
```

Do not hard-code an unverified local machine path as the only discovery mechanism. Prefer repo name + optional sibling resolution/environment configuration.

### 3. Link from appropriate A-Wiki context/index

Follow the same indexing/discovery convention used by the current A-Wiki entity system. If index files are generated, modify the source entity and run the documented generator rather than hand-editing generated output.

### 4. Record cross-repo work order / decision

Create or update an A-Wiki work order/decision entry that states:

- A-Conductor is an active sibling product, not a worktree.
- Cross-repo overlap gate is mandatory.
- New orchestration/coordination work must check both A-Wiki and A-Conductor ownership before implementation.
- Current authoritative boundary contract is `A-Wiki-Conductor/docs/contracts/a-wiki-a-conductor-integration.md`.

Use A-Wiki's current `docs/protocols/cross-agent-work-orders.md` convention at apply time.

## Suggested A-Wiki master work order

Use A-Wiki's current work-order convention at apply time; proposed content:

```markdown
# WO-AC-001: Register A-Conductor Companion Execution Plane
Status: open
Lane/files: A-Conductor project entity/pointer, AGENTS companion-repo pointer, applicable context/index source, handoff/current-work only as required
Branch: current authorized A-Wiki branch
Model tier: high

## Goal + Acceptance criteria
- Register `A-Wiki-Conductor` / A-Conductor as an active sibling companion repo.
- Record that A-Wiki owns brain/policy/memory/orchestration knowledge.
- Record that A-Conductor owns durable execution/runtime/recovery/operator surfaces.
- Link to `A-Wiki-Conductor/docs/contracts/a-wiki-a-conductor-integration.md`.
- Add the anti-duplication `REUSE / WRAP / EXTEND / REPLACE / NEW` gate.
- Do not duplicate existing A-Conductor runtime capabilities in A-Wiki.
- Verify current A-Wiki work orders/claims and current companion-project convention before editing.

## Forbidden
- Do not convert A-Conductor into an A-Wiki worktree/submodule as part of registration.
- Do not move production A-Conductor source into A-Wiki.
- Do not create a second work-order/claim/memory/orchestration protocol.
- Do not hard-code secrets or credential/tunnel values.

## Verify
- Existing companion pattern remains valid or migration is explicitly recorded.
- A-Conductor pointer is discoverable from A-Wiki agent/project context.
- No duplicate project entry exists.
- Generated indexes, if any, are updated through the documented generator.
- Resulting A-Wiki commit SHA is recorded back in A-Conductor handoff.
```

## Apply-time verification checklist

Before modifying A-Wiki:

- [ ] Inspect authoritative A-Wiki GitHub/current branch state.
- [ ] Inspect active work orders and claims relevant to coordination/orchestration/project registry.
- [ ] Confirm `env-wastewater-webapp` companion pattern is still current.
- [ ] Confirm no newer project registry supersedes the entity/pointer approach.
- [ ] Add/update A-Conductor entity/pointer without duplicating an existing entry.
- [ ] Link/index using current A-Wiki convention.
- [ ] Run A-Wiki documentation/index verification required by the repo.
- [ ] Commit in A-Wiki separately from A-Conductor.
- [ ] Record resulting A-Wiki commit SHA back in A-Conductor handoff/contract metadata.

## Do not claim complete yet

Cross-repo registration remains **prepared but not applied** until the A-Wiki repository is actually updated and verified through an authorized execution surface. The A-Conductor-side responsibility contract can be complete independently.
