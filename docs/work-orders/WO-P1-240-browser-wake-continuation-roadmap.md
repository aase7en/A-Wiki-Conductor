# WO-P1-240 — Browser Wake / Sunday-Family Extension roadmap

Status: ACTIVE / DOCS_ONLY / SOURCE_MUTATION_FORBIDDEN
Risk: R2 architecture/roadmap shaping
Owner: GPT-5.6 Sol integrator
Durable claim: GitHub Issue #320
Date: 2026-09-15

## Authority and exact state

Repo: `aase7en/A-Wiki-Conductor`
Docs worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo240-browser-wake-roadmap`
Branch: `docs/wo-p1-240-browser-wake-continuation-roadmap`
Base: `origin/main@67744e98e538b000579bff4a45616d3a178a824b`

Actual runtime/Git/GitHub/durable Issue state overrides this WO. Chat is not project authority.

Active WO223/RE2-A remains the source critical path and is explicitly non-overlapping. This lane must not edit its source/tests, PR #319 branch, `CURRENT-WORK.md`, `handoff.md`, `COLLAB.md`, provider/runtime DB, or live browser/provider configuration.

## Goal

Produce a binding-quality roadmap proposal for the missing reverse continuation path:

`external agent/CLI finishes -> A-Conductor durable event -> browser conversation wake -> browser AI reasons -> structured proposal -> A-Conductor revalidates -> safe next execution`

The desired operator outcome is one initial goal command, with no repeated human `continue` messages except real human-only approval/blocker gates.
## Reuse-before-build conclusions

A-Wiki remains the brain-side authority:
- A-Loop goal/continuation semantics;
- A-Suite/skill routing and model policy;
- hooks classification/policy;
- ReviewBus/review policy;
- durable knowledge/memory/work-order conventions.

A-Conductor remains execution authority:
- durable live job/execution state;
- worker/provider/runtime lease/admission;
- process supervision, evidence, dedup and recovery;
- mutation admission and runtime provider/model enforcement;
- Zero-Relay transport/results and GoalCloseout.

Sunday-Family Extension and any Native Messaging/broker layer are ADAPTERS only. No second planner, scheduler, claim store, review lifecycle, retry store, model-policy store, or project memory may be introduced.

## Allowed tracked scope

1. `docs/plans/2026-09-15-browser-wake-continuation-roadmap.md`
2. `docs/work-orders/WO-P1-240-browser-wake-continuation-roadmap.md`

No other tracked file is mutable under this claim.

`SAFE_TO_MUTATE_WO240_DOCS=YES`
`SAFE_TO_MUTATE_SOURCE=NO`
## Priority decision

The roadmap must optimize for leverage rather than feature novelty:

1. finish active WO223/RE2-A R3 repair and release;
2. complete Phase-D/WO205 and WO227/ZRA-3 continuation semantics;
3. implement Browser Wake Relay MVP before broad ZRA-4/ODP expansion;
4. normalize Kilo/Claude/ZCode/SundayWorker/CI lifecycle events into existing A-Conductor event/job authority;
5. add ZRA-4 bounded parallel fan-in using the wake channel;
6. expand provider adapters/council, packaging and embedded helper AI;
7. integrate browser reasoners into ODP capability-first selection;
8. add mobile/human approval UX and optional headless browser deployment later.

Reason: Browser Wake before ZRA-3 would merely automate typing `continue` without having a trustworthy definition of what may continue. ZRA-3 before Browser Wake gives safe semantics but still requires a human to trigger the next browser turn. The pair closes the loop.

## Acceptance criteria

- reconcile existing roadmap/current live critical path and explicitly flag stale projections;
- map A-Wiki hooks/skills to REUSE rather than duplicate them;
- audit `niawjunior/aipass-bridge` plus at least one multi-provider bridge and one Native Messaging bridge pattern;
- define Browser Wake authority/transport boundary and Sunday-Family package modules;
- define phased dependencies, success metrics, typed failure/security rules and implementation gates;
- preserve WO223 source ownership and make no source/runtime mutation;
- run markdown/text hygiene, UTF-8, `git diff --check`, exact-scope check;
- freeze/push docs candidate for independent review before any merge/project-plan fold.

## Continuity

Fresh session resume order:
`00-AGENT-ENTRY.md -> PROJECT-GRAPH.yaml -> AGENTS.md -> actual Git/GitHub -> Issue #320 -> this WO -> roadmap`.

Also re-read Issue #214 and PR #319 before assuming the current critical path, because WO223 may advance independently while this docs lane is under review.

Next safe action: verify the two-file docs diff, commit/push exact candidate, checkpoint Issue #320, then obtain independent read-only architecture/security review. Do not merge or edit source under this WO.
