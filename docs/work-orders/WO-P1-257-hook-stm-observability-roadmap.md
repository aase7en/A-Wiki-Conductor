# WO-P1-257 — Hook, STM, and Observability architecture roadmap

Status: IN_PROGRESS
Issue: #365
Risk: R3 — cross-repo architecture/protocol roadmap
Task topology: CROSS_REPO

## Binding

Authority repo: `A:\GitHub\A-Wiki-Conductor`
Execution repo: `A:\GitHub\SunDayRemoteMCP`

Authority worktree:
`A:\GitHub\_worktrees\A-Wiki-Conductor-wo257-hook-stm-roadmap`

Branch:
`docs/wo-p1-257-hook-stm-roadmap`

Base:
`A-Wiki origin/main@4f93005d20feb5781b5febb8f963ccd224d29e25`

Read-only execution-substrate baseline:
`SunDayRemoteMCP main@70046f0a46f74c1655020ef272cd9c00e41737cd`

Owner/integrator: GPT-5.6 Sol / SunDay-Worker 4 documentation lane.

## Goal

Capture the canonical architecture and priority roadmap for:

- A-Faster/A-FastTask accelerated routing;
- versioned Hook Contract;
- A-Conductor control-plane events;
- SRM execution hooks;
- Claude/Kilo harness adapters;
- Ponytail/Caveman/Grill-me advisory integration;
- STM operational working memory;
- Hook Bus/event pipeline;
- shared Hook Monitor backend;
- Desktop/Web/Extension monitor UI;
- later A-Conductor Command Gateway;
- Windows/macOS/Linux/Pi/Umbrel rollout;
- semantic/ODP/provider roadmap integration.

## Classification

`REUSE + WRAP + EXTEND`.

Do not create:

- another task store;
- another scheduler;
- another claim/lease authority;
- another review/completion system;
- another project memory SSoT;
- another per-UI state authority.

## Allowed authority-repo scope

- NEW `docs/plans/2026-09-19-a-faster-hook-stm-observability-roadmap.md`
- MODIFY `PROJECT-PLAN.md`
- MODIFY `docs/plans/cross-platform-plan.md`
- MODIFY `.agents/skills/a-faster/SKILL.md` for the two accepted P2 wording hardenings only
- this Work Order

SunDayRemoteMCP is READ_ONLY in this WO.

## Forbidden

- runtime/source/provider/DB implementation;
- hook bus implementation;
- monitor server/UI implementation;
- SRM source changes;
- external network/remote monitor exposure;
- secrets;
- raw prompt/credential logging;
- claim/task authority changes.

## Dependencies

Accepted A-Faster merge:
`4f93005d20feb5781b5febb8f963ccd224d29e25`

Accepted SEM-1a:
`70046f0a46f74c1655020ef272cd9c00e41737cd`

Parallel roadmaps:

- Issue #341 semantic/LSP;
- Issue #340 provider-neutral executor/model portability;
- DEX resilient execution continuity;
- ODP orchestration decision plane.

## Acceptance

1. Dedicated roadmap exists and is linked from PROJECT-PLAN.
2. Cross-platform plan reuses the same monitor backend/Web UI rather than a
   separate Umbrel state stack.
3. A-Faster WIP wording explicitly covers devices/harnesses/repos/CROSS_REPO
   compatibility sets.
4. A-Faster recovery capacity is explicitly inside the same 3+1 WIP budget.
5. STM is defined as bounded/rebuildable/non-authoritative.
6. Hook Bus/Monitor UI cannot mutate task truth.
7. Consequential UI actions are deferred to an A-Conductor Command Gateway.
8. Hook adapters are version/capability bound.
9. Security/redaction, ordering/dedupe/backpressure and failure semantics are
   explicit.
10. Priority/dependency sequence is implementation-ready but does not claim
    runtime implementation occurred.
11. YAML/UTF-8/diff/reference/secret/scope checks pass.
12. Frozen exact SHA receives independent R3 review + CI before merge.

## Next safe action

Author the bounded roadmap/docs delta, run deterministic checks, freeze exact
SHA, dispatch one independent read-only review lane, run hosted CI in parallel,
then reconcile/repair/merge only the reviewed exact candidate.
