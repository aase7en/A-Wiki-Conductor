# WO-P1-251 — CROSS_REPO binding contract

Status: IN_PROGRESS
Issue: #349
Risk: R2 NORMAL — binding coordination / SSoT policy
Owner/integrator: GPT-5.6 Sol
Topology: CROSS_REPO

AUTHORITY_REPO: `A:\GitHub\A-Wiki-Conductor`
AUTHORITY_BASE: `7c0ff0d68c816a3f307fa39851129bcbab7c9f16`

EXECUTION_REPO: `A:\GitHub\SunDayRemoteMCP`
EXECUTION_BASE: `2b7996ced0ceaff5b97c7bef3f601765213de5ec`

## Goal

Define the first repo-native CROSS_REPO binding contract for A-Sunday Conductor: repo-role classification, per-lane execution-context binding, exact-SHA compatibility set, global WIP accounting, set-level completion, and a durable Windows no-console rule.

This work must not create a second scheduler, task store, claim authority, reviewer authority, completion authority, mutable global Active Project, or copy Project Sources into repo roots.

## Normative vocabulary

- `CONTROL_PLANE_ONLY` — all mutation lanes are in the authority repo.
- `EXECUTION_SUBSTRATE_ONLY` — mutation lanes are in execution repo(s), while task/claim/WIP/review/acceptance remain governed by the authority repo.
- `CROSS_REPO` — mutation spans both repo roles and is accepted as one exact-SHA compatibility set.

Per-lane binding:

`repo -> worktree -> branch -> HEAD -> task/claim -> scope`

Compatibility set at freeze:

`{AUTHORITY_REPO@SHA_AUTH, EXECUTION_REPO@SHA_EXEC}`

Any member head drift invalidates the set until re-pin and focused review of affected delta.

## Global WIP

One global budget across the compatibility set:

- mutable lanes: 3
- independent read-only review lanes: 1
- `1 MUTABLE HOTSPOT = 1 MUTATION OWNER`

CROSS_REPO never multiplies WIP per repository.

## Durable Windows no-console rule

Invoke the exact installed executable directly wherever possible. When PowerShell is unavoidable, launch it hidden with no new console window. Background child processes use `CREATE_NO_WINDOW` / `windowsHide` on Windows. Never change global shell settings or profiles. Process termination targets an exact PID with verified command identity only; broad process kill remains forbidden.

## Claims / mutation lanes

### Lane A — authority routing contract
Repo: A-Wiki-Conductor
Scope:
- `docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md`
- `PROJECT-GRAPH.yaml`

Task:
- define the three topology values at one authoritative routing definition home;
- define full per-lane tuple;
- define global-cross-repo WIP accounting;
- define exact-SHA compatibility pair/set and set-level completion pointer;
- project the Windows no-console rule;
- preserve existing A-FastTask router/binder-only authority floor.

### Lane B — authority entry / A-FastTask projection
Repo: A-Wiki-Conductor
Scope:
- `00-AGENT-ENTRY.md`
- `.agents/skills/a-fasttask/SKILL.md`
- `.agents/skills/a-fasttask/references/conductor.md`
- `.agents/skills/a-fasttask/references/closeout.md`

Task:
- project, but do not redefine, topology semantics;
- align the pre-existing derived-liveness enumeration with `EXECUTION_LIVENESS_PROTOCOL.md`;
- project the full lane-binding tuple and exact-SHA set;
- make WIP accounting global across set members;
- make CROSS_REPO evidence fold target the authority repo;
- project the durable no-console rule where execution routing is described.

### Lane C — execution-substrate mirror
Repo: SunDayRemoteMCP
Scope:
- `AGENTS.md`

Task:
- declare SunDayRemoteMCP as `EXECUTION_SUBSTRATE_ONLY` for A-Wiki-governed CROSS_REPO work;
- require authority WO/claim reference plus exact compatibility pair before mutation;
- preserve SRM-owned WO-SRM self-governance for SRM-owned tasks;
- add the durable no-console rule;
- bind cross-repo references by exact SHA, never by copied control-plane source.

## Forbidden

- no `src/`, test, runtime, provider, DB, credentials, or secret mutation in this WO;
- no mutation of dirty/stale canonical A-Wiki root;
- no broad reset/clean/stash/checkout/rebase/force;
- no broad process kill;
- no Project Sources copied into either repo root;
- no second task/claim/scheduler/review/completion authority.

## Dispatch invariants

Before every material GLM dispatch:
1. fresh CoinTH quota/readiness preflight through the approved secret-safe resolver;
2. exact lane binding and claimed scope;
3. no overlapping writer;
4. durable result destination under ignored `runs/WO-P1-251/<lane>/`;
5. no secrets in prompt/logs.

Worker/GLM DONE is a claim only. Deterministic exact-SHA evidence wins.

## Verification / acceptance

Per repo:
- exact claimed path scope;
- `git diff --check`;
- strict UTF-8;
- added-line secret scan;
- referenced relative paths resolve;
- no runtime/source/schema change;
- classification vocabulary has one definition home and projections do not fork it.

Set-level:
- freeze one exact candidate head per repo;
- independent read-only review of the compatibility pair must return `P0=0 P1=0 P2=0`;
- A-Wiki exact-head hosted CI required;
- SunDayRemoteMCP exact-head deterministic fallback allowed only if hosted CI is absent and must be explicitly recorded;
- merge expected heads only, authority repo first then execution repo;
- post-main verification both repos;
- Issue #349 records final merged SHA pair, CI/fallback evidence, independent-review reference, and global WIP ledger before closure.

## Current checkpoint

Bootstrap pair:
- A-Wiki main: `7c0ff0d68c816a3f307fa39851129bcbab7c9f16`
- SunDayRemoteMCP main: `2b7996ced0ceaff5b97c7bef3f601765213de5ec`

WO250 / PR #345 is merged and post-main CI run `35313602575` succeeded on A-Wiki merge SHA `7c0ff0d...`.

Next safe action: commit/push this governance bootstrap, rerun mutation gate, create isolated lane worktrees from the bootstrap authority SHA / execution base, then dispatch Lane A/B/C in parallel within global WIP.
