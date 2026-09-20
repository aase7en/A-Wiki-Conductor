# WO-P1-397 — DWB convergence and product-acceleration roadmap

Status: ACTIVE / ROADMAP AUTHORING
Issue: #397
Risk: R2 — binding architecture/roadmap and cross-repo delivery reprioritization
Task topology: CROSS_REPO

## Binding

Project: A-Sunday Conductor

Authority repo:
`A:\GitHub\A-Wiki-Conductor`

Execution repo:
`A:\GitHub\SunDayRemoteMCP`

Authority worktree:
`A:\GitHub\_worktrees\A-Wiki-Conductor-wo397-dwb-convergence`

Branch:
`docs/wo-p1-397-dwb-convergence-roadmap`

Base / current HEAD at claim:
`A-Wiki-Conductor origin/main@61315b71d510ce8ba88498018bb6c1d76dab144d`

Execution-substrate planning baseline:
`SunDayRemoteMCP main@ac01b37ba2e4b9d0249addf7694c0b91deb352c7`

External benchmark:
`sphakanin/dwb-mcp-studio-public@884fdc6a0d76779dc772842c8894d43d7c4ebd64`

External benchmark license:
MIT, copyright (c) 2026 Phakanin. Verbatim/substantial copying requires preservation of the DWB copyright and MIT permission notice.

Owner / integrator:
GPT-5.6 Sol

Mutable author lane:
SunDay-Worker 1, docs-only in the authority worktree above.

Read-only evidence lanes:
- SunDay-Worker 2 — DWB source/provenance and copy/adapt inventory.
- SunDay-Worker 3 — SunDayRemoteMCP reuse seams and execution-substrate fit.
- SunDay-Worker 4 — dependency/cut/defer audit and synced-Drive fallback policy read.
- SunDay-Worker 5 — independent exact-SHA roadmap review after freeze.

## Goal

Produce the implementation-ready convergence plan that gets a usable A-Sunday product sooner by:

1. copying DWB implementation where license, language, trust boundary and architecture fit;
2. adapting DWB behavior where direct copying would create a second authority or incompatible stack;
3. reusing existing A-Sunday/A-Wiki/SRM primitives before building anything new;
4. cutting or deferring duplicate, stale, legacy or non-MVP surfaces;
5. preserving A-Wiki as governance/control authority and SunDayRemoteMCP as execution/capability substrate;
6. turning the resulting decisions into an explicit dependency-ordered roadmap with child Work Orders and acceptance gates.

## Allowed mutation scope

- NEW `docs/work-orders/WO-P1-397-dwb-convergence-roadmap.md`
- NEW `docs/plans/2026-09-20-dwb-convergence-product-acceleration-roadmap.md`
- Git branch/commit/PR metadata required to review this roadmap.
- `PROJECT-PLAN.md` only after all currently open overlapping PR ownership is reconciled and a fresh mutation gate proves no overlap.

## Forbidden in this WO

- no A-Conductor production source mutation;
- no SunDayRemoteMCP source mutation;
- no worktree deletion or broad cleanup;
- no dependency removal;
- no launcher/UI implementation;
- no external executable launch from the benchmark;
- no new scheduler/task/claim/review/completion authority;
- no copying of third-party code whose license/provenance is not established;
- no secret/config/token migration;
- no mutation of `CURRENT-WORK.md`, `handoff.md`, or `COLLAB.md`;
- no overwrite of `PROJECT-PLAN.md` while PR #243/#244 ownership overlap remains unresolved.

## Reuse-before-build classification

Default policy:

`REUSE_EXISTING -> COPY_VERBATIM_IF_FIT -> ADAPT_WITH_ATTRIBUTION -> CLEAN_ROOM_REIMPLEMENT -> NEW`

A DWB feature is not copied merely because it exists. It must pass all of:

- license/provenance;
- same or compatible language/runtime;
- same trust/authority boundary;
- no duplicate state authority;
- no unnecessary UI/runtime stack;
- lower implementation/maintenance cost than extending an existing seam;
- deterministic tests can bind the adopted behavior.

## Roadmap priorities to resolve

The roadmap must explicitly disposition:

1. Generated Operational Truth / single-writer continuity projection.
2. Ownership-aware Worktree Lifecycle and cleanup eligibility.
3. SunDayRemoteMCP File Mutation Guard v2.
4. Runtime Cockpit / concise operator state and outcome vocabulary.
5. Payload/result guard where it reduces context and transport failures.
6. SunDayRemoteMCP dependency diet and optional feature-pack boundary.
7. Windows front-door polish: launch/startup/tray/doctor only where it reuses the current product shell.
8. Stale roadmap/PR and manual-projection debt that slows delivery.

## Current overlap / continuity facts

At task start:

- A-Wiki canonical root checkout is protected, dirty and 802 commits behind remote main; this WO does not use it for mutation.
- PR #395 is an active draft on a disjoint source/work-order scope and has green hosted CI.
- Issue #396 is open for HOOK-2b; this roadmap must not steal its source scope.
- PR #243 and stacked PR #244 remain open and both touch `PROJECT-PLAN.md`; therefore the shared roadmap file is protected until those branches are reconciled.
- DWB benchmark is cloned read-only under `A:\GitHub\_benchmarks\dwb-mcp-studio-public-884fdc6`.
- Google Drive connector and Remote Desktop Commander/GitHub connector calls are policy-blocked in this chat; GitHub truth is accessed through authenticated `gh` CLI and Windows access through SunDay Workers. The synced private Drive layer was read only after its `AGENTS.md` and `LAYOUT.md` contract; it remains non-authoritative.

## Acceptance criteria

1. A detailed convergence roadmap exists under `docs/plans/`.
2. Every DWB-derived capability is classified as one of:
   - `COPY_VERBATIM`
   - `ADAPT_WITH_ATTRIBUTION`
   - `CLEAN_ROOM_REIMPLEMENT`
   - `REUSE_EXISTING`
   - `CUT_OR_DEFER`
3. Direct-copy candidates name exact DWB source file/function/test seams and required attribution.
4. Existing A-Sunday/SRM seams are named so child WOs do not rebuild solved infrastructure.
5. The roadmap defines the smallest usable-product slice and separates it from later polish.
6. Worktree cleanup is split into read-only classification and consequential cleanup; no broad delete is implied.
7. Dependency cuts require reachability/behavior proof and do not remove full-toolset capability accidentally.
8. The plan does not create a second broker/session/task authority.
9. Child work is dependency ordered and risk classified; R3 boundaries are explicit.
10. Open roadmap overlap (#243/#244) has a documented reconciliation path before `PROJECT-PLAN.md` integration.
11. Exact candidate SHA receives independent read-only review by SunDay-Worker 5.
12. Deterministic scope, link, UTF-8 and secret checks pass.
13. Hosted CI is run on the frozen roadmap candidate when available.
14. Issue #397 receives the candidate/PR/evidence pointer so a fresh session can resume without chat memory.

## Replay safety

This WO is docs-only. Re-execution is safe only after re-reading Issue #397, branch/HEAD, dirty state and open roadmap-overlap PRs. Never overwrite a moving shared roadmap hotspot.

## Next safe action

Author the convergence roadmap in the isolated branch, then freeze exact SHA and run an independent read-only review before any shared-roadmap integration.
