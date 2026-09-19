# WO-P1-240 — Browser Wake / Sunday-Family Extension roadmap

Status: ACTIVE / DOCS_ONLY / RECONCILED_CANDIDATE / SOURCE_MUTATION_FORBIDDEN
Risk: R2 architecture/roadmap shaping
Owner: GPT-5.6 Sol integrator
Durable claim: GitHub Issue #320
Date: 2026-09-15

## Authority and exact state

Repo: `aase7en/A-Wiki-Conductor`
Docs worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo240-browser-wake-roadmap`
Branch: `docs/wo-p1-240-browser-wake-continuation-roadmap`
Original base: `origin/main@67744e98e538b000579bff4a45616d3a178a824b`
Reconciled main baseline: `origin/main@cbd47608346e7510dcf5946cc8b1974b8564f31b`
Pre-edit reconciliation merge: `c4d24ff2ad6e8a6df96d61ff7db81423dbed5957`
Current-main re-pin merge: `264dbab26cf88fd5115f91c3c3187e710995b25d`

Actual runtime/Git/GitHub/durable Issue state overrides this WO. Chat is not project authority.

WO223/PR #319 is merged historical evidence, not the current blocker. This lane remains docs-only and must not edit ZRA-3, WO258/HOOK-0, WO259/context-rollover, `CURRENT-WORK.md`, `handoff.md`, `COLLAB.md`, product source/tests, provider/runtime DB, or live browser/provider configuration.

## Goal

Produce a binding-quality roadmap proposal for the missing reverse continuation path:

`external agent/CLI finishes -> A-Conductor durable event -> browser conversation wake -> browser AI reasons -> structured proposal -> A-Conductor revalidates -> safe next execution`

The desired operator outcome is one initial goal command, with no repeated human `continue` messages except real human-only approval/blocker gates.

## 2026-09-19 authority reconciliation

Current GitHub truth materially advanced after the original freeze:

- WO223/PR #319 merged; the old "finish WO223" dependency is historical.
- WO257 is merged and now owns Hook Contract -> Hook Bus/STM -> Monitor API ->
  Web/Extension UI -> Command Gateway architecture.
- WO260/PR #377 is merged and supplies durable delegated-lane identity/recovery
  pointers (LANE_REF / DELEGATED_RUN_ID / BINDING_DIGEST) as a non-authoritative
  routing/evidence overlay. Browser Wake consumes those pointers when relevant.
- WO258/PR #371 is the open HOOK-0 contract lane; WO240 must consume its final
  accepted form rather than introduce a Sunday-Family protocol.
- WO259/PR #373 is the open context/session rollover lane; browser new-chat
  resume consumes that contract rather than storing its own resume truth.
- ZRA-3 PR #263 and its production-composition successors remain continuation
  dependencies until accepted.
- Ordinary ChatGPT/Gemini web chat has no required native `/goal` contract.
  Goal/task semantics stay external in A-Sunday Conductor/A-Wiki.
- Schedule ownership remains outside the extension. A future schedule UI sends
  requests to a canonical A-Conductor scheduler/trigger authority only.

Result: WO240 is narrowed to the missing **Browser Chat Harness Adapter** and
its Native Messaging/provider transport. Extension monitor/control UI is reused
from WO257; session rollover is reused from WO259; delegated-lane recovery pointers
are reused from WO260; NEXT_READY is reused from ZRA-3.

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
## Priority decision — reconciled 2026-09-19

The roadmap must optimize for leverage and preserve the newer accepted
architecture:

1. accept the existing ZRA-3 continuation semantics rather than implementing
   "continue" logic in JavaScript;
2. accept/re-pin HOOK-0 and context-rollover contracts;
3. BWA-0: define the browser harness/conversation contract only;
4. BWA-1: Native Messaging + MV3 core + fake-provider deterministic E2E;
5. BWA-2: ChatGPT Web and Gemini Web adapters;
6. BWA-3: zero-human-continuation E2E with restart + context rollover;
7. integrate cockpit/status with WO257 Monitor API/Extension UI;
8. route pause/resume/cancel/retry through WO257 Command Gateway;
9. add scheduled Goal Trigger only after a canonical scheduler contract exists;
10. expand provider/council/workflow packs after the two-provider MVP is stable.

This separates five authorities that must not be collapsed:
`GOAL/TASK != CONTINUATION != BROWSER TRANSPORT != OPERATOR UI != SCHEDULE`.

Reason: ordinary browser chat does not need native `/goal`; the adapter is an
execution surface for bounded turns, while durable goal/task/schedule truth
remains in A-Sunday Conductor/A-Wiki.

## Acceptance criteria

- reconcile existing roadmap/current live critical path and explicitly flag stale projections;
- map A-Wiki hooks/skills to REUSE rather than duplicate them;
- audit `niawjunior/aipass-bridge` plus at least one multi-provider bridge and one Native Messaging bridge pattern;
- define Browser Wake authority/transport boundary and Sunday-Family package modules;
- explicitly reconcile with WO257, HOOK-0, context-rollover and ZRA-3 rather than duplicating them;
- specify that ChatGPT/Gemini web adapters require no native `/goal`;
- keep scheduled-goal authority outside Chrome/Extension state;
- define phased dependencies, success metrics, typed failure/security rules and implementation gates;
- preserve WO223 source ownership and make no source/runtime mutation;
- run markdown/text hygiene, UTF-8, `git diff --check`, exact-scope check;
- freeze/push docs candidate for independent review before any merge/project-plan fold.

## Continuity

Fresh session resume order:
`00-AGENT-ENTRY.md -> PROJECT-GRAPH.yaml -> AGENTS.md -> actual Git/GitHub -> Issue #320 -> this WO -> roadmap`.

Before implementation planning, re-read Issue #320 plus current ZRA-3, WO257, WO258/HOOK-0 and WO259/context-rollover authority. Treat PR #319 only as merged historical evidence; do not infer current dependencies from the original 2026-09-15 sequence.

Next safe action: verify the reconciled two-file diff against current main, freeze/push a new exact candidate, checkpoint Issue #320, then obtain independent exact-SHA architecture/security/reuse review plus required CI. Do not edit product source under this WO. After acceptance, open BWA-0 only when the live ZRA-3/HOOK-0/context-rollover dependency gates permit it.
