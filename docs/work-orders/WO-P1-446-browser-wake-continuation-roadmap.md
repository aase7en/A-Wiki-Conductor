# WO-P1-446 — Browser Wake / Sunday-Family Extension roadmap

Status: ACTIVE / DOCS_ONLY / RECONCILED_CANDIDATE / SOURCE_MUTATION_FORBIDDEN
Issue: #446
Identity schema: GITHUB_ISSUE_V1
Canonical authority: Issue #446 / WO-P1-446
Historical authority alias: Issue #320 / WO-P1-240
Risk: R2 architecture/roadmap shaping
Topology: CONTROL_PLANE_ONLY
Owner: GPT-5.6 Sol integrator
Durable claim: GitHub Issue #446
Date: 2026-09-15

## Canonical identity migration — 2026-09-21

This roadmap was minted as WO-P1-240 / Issue #320 before WO-P1-381 and
WO-P1-386 established and froze the current GitHub-backed Work Order identity
policy. It remained unmerged when the frozen legacy exception corpus was
captured, so the deterministic guard correctly rejects introducing the old
low-number filename now. Issue #320 is also below the frozen current-identity
threshold; Issue #446 / WO-P1-446 is therefore the canonical live identity.

The frozen legacy exception fixture is intentionally unchanged. The historical
branch/worktree names, Issue #320 thread, prior WO-P1-240 candidate SHAs,
review evidence, run/claim identifiers and prose references remain immutable
historical evidence aliases. They are not rewritten merely for cosmetics and
do not create a second live Browser Wake authority. This rebind changes no
product/source/runtime semantics.

## Authority and exact state

Repo: `aase7en/A-Wiki-Conductor`
Docs worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo240-browser-wake-roadmap`
Branch: `docs/wo-p1-240-browser-wake-continuation-roadmap`
Original base: `origin/main@67744e98e538b000579bff4a45616d3a178a824b`
Prior reconciled main baseline: `origin/main@3656fb386911b5bf9e3457e8e11c67d6b11da8e6`
Current re-pin baseline (2026-09-21): `origin/main@9a37e02ba833004ddf4317fd39cbf5927cf26d58`
Pre-edit reconciliation merge: `c4d24ff2ad6e8a6df96d61ff7db81423dbed5957`
Prior current-main re-pin merges: `264dbab26cf88fd5115f91c3c3187e710995b25d`, `c3a012633b26e8785f94738b8fb5e386d99c20da`
Latest current-main re-pin merge: `51122ebbf06fc1e0238b0243f887f59fe905305e`

Actual runtime/Git/GitHub/durable Issue state overrides this WO. Chat is not project authority.

WO223/PR #319 is merged historical evidence, not the current blocker. This lane remains docs-only and must not edit Issue #215 automatic-continuation authority, the current Hook-contract family / Issue #368, DEX authority lanes, WO369/context-rollover, WO374 durable-lane authority, `CURRENT-WORK.md`, `handoff.md`, `COLLAB.md`, product source/tests, provider/runtime DB, or live browser/provider configuration.

## Goal

Produce a binding-quality roadmap proposal for the missing reverse continuation path:

`external agent/CLI finishes -> A-Conductor durable event -> browser conversation wake -> browser AI reasons -> structured proposal -> A-Conductor revalidates -> safe next execution`

The desired operator outcome is one initial goal command, with no repeated human `continue` messages except real human-only approval/blocker gates.

## 2026-09-19 authority reconciliation

Current GitHub truth materially advanced after the original freeze:

- WO223/PR #319 merged; the old "finish WO223" dependency is historical.
- WO257 is merged and owns Hook Contract -> Hook Bus/STM -> Monitor API ->
  Web/Extension UI -> Command Gateway architecture.
- WO-P1-374 / Issue #374 / PR #377 is now the canonical durable delegated-lane
  identity/recovery overlay. Historical pre-remediation WO260 pointers remain
  evidence aliases only; Browser Wake consumes those pointers without gaining
  task/retry authority.
- WO258/PR #371 established HOOK-0. Main has since accepted HOOK-1 / HOOK-1B /
  HOOK-1C / HOOK-2A / HOOK-2B successors, while forward-compatibility repair
  PR #385 remains open. WO446 must bind implementation to the latest accepted
  Hook-contract family at freeze time rather than fork its event vocabulary.
- WO-P1-369 / Issue #369 / PR #373 is merged and is the canonical context/session
  rollover contract; browser new-chat resume consumes it unchanged.
- DEX-ARCH-1 / Issue #348 / PR #372 is merged and defines DEX-3a completion
  notification plus DEX-3b supported resume adapter. Browser Wake is a DEX-3b
  provider/browser realization, not a new continuation control plane.
- WO-P1-381 / Issue #381 / PR #382 is merged and establishes current atomic
  Work Order identity rules for future browser implementation lanes.
- Issue #215 exclusively owns automatic accepted-completion -> NEXT_READY
  continuation. Historical PR #263/#269/#274 and WO191/195/227 remain
  unaccepted evidence only and must not be revived as Browser Wake authority.
- Ordinary ChatGPT/Gemini web chat has no required native `/goal` contract.
  Goal/task semantics stay external in A-Sunday Conductor/A-Wiki.
- Schedule ownership remains outside the extension. A future schedule UI sends
  requests to a canonical A-Conductor scheduler/trigger authority only.

Result: WO446 is narrowed to the browser/provider realization of **DEX-3b
supported resume**. Extension monitor/control UI is reused from WO257; session
rollover is reused from WO369; delegated-lane recovery pointers are reused from
canonical WO374 (with historical WO260 aliases preserved as evidence); completion
notification/reconciliation follows DEX-3a/DEX-2a/DEX-2b; automatic NEXT_READY
is consumed only from the accepted successor of Issue #215 authority.

## 2026-09-21 acceleration reconciliation

Latest user priority makes Browser Wake / Sunday-Family Extension a P0 delivery
accelerator because ordinary browser ChatGPT still needs a human to create the
next turn after delegated work or a tool turn becomes idle.

Current authority after re-pin:
- COCKPIT-1A / WO424 and RUNTIME-AUTH-1 / WO431 are merged; `main@9a37e02...`
  includes merged WO433 / PR #441 with the accepted explicit/manual bounded
  runtime activation primitive. #429 COCKPIT-1B is the current product-binding
  frontier. Browser Wake reuses these seams and creates no second runtime producer.
- Issue #215 still exclusively owns automatic accepted-completion -> NEXT_READY
  continuation. Historical PR #263/#269/#274 and WO191/195/227 are unaccepted
  evidence only; WO446/BWA work must not implement successor-selection policy.
- Main has accepted HOOK-1 / HOOK-1B / HOOK-1C / HOOK-2A / HOOK-2B successors.
  HOOK-0 forward-compatibility repair PR #385 remains open; each browser freeze
  binds the latest accepted Hook-contract family and never forks stale vocabulary.
- DEX-2b identity/receipt foundation is merged (PR #403); DEX-2a substrate
  supervision and production DEX-3a completion-event delivery remain open.
- WO205 Phase-D is an active separate mutable lane and is not part of WO446 scope.

To reduce idle dependency time without weakening authority, after WO446 itself is
accepted:
1. **BWA-0 contract shaping may start immediately** against explicit open/accepted
   dependency references. It remains docs/contracts only.
2. While BWA-0 is under review, **BWA-1 source-layout/test-harness shaping may
   proceed read-only**. Tracked BWA-1 source mutation starts only after BWA-0
   acceptance and a free mutable WIP slot. Its fake ingress is test-only and
   defined by BWA-0; it must not invent or impersonate the production DEX-3a
   completion producer. Passing BWA-1 proves transport, binding, restart and
   dedupe mechanics only; it does not claim live autonomous continuation.
3. **BWA-2 live browser adapters and BWA-3 zero-human continuation remain gated**
   on the then-current accepted Hook/DEX/continuation authorities and provider
   authorization.

`Play` / `Pause` in the first extension slice means arm/disarm **automatic browser
wake delivery only**. `Pause` never kills, suspends, retries or cancels an
underlying execution. Any consequential execution pause/cancel/retry/reassign
request remains Command-Gateway-mediated.

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
2. `docs/work-orders/WO-P1-446-browser-wake-continuation-roadmap.md`

No other tracked file is mutable under this claim.

`SAFE_TO_MUTATE_WO446_DOCS=YES`
`SAFE_TO_MUTATE_SOURCE=NO`
## Priority decision — accelerated 2026-09-21

The roadmap must optimize for leverage and preserve the newer accepted
architecture:

1. accept/merge WO446 itself after current-main exact-SHA review and CI;
2. start BWA-0 contract shaping immediately after WO446 acceptance while open
   continuation/Hook/DEX dependencies continue in their existing owner lanes;
3. shape BWA-1 source/test layout read-only while BWA-0 is reviewed; begin
   tracked Native Messaging + MV3 fake-provider implementation only after BWA-0
   acceptance + WIP admission, using test-only ingress and no live NEXT_READY;
4. consume the automatic NEXT_READY semantics only from the accepted successor
   of Issue #215 rather than implementing "continue" logic in JavaScript, and
   re-pin the latest accepted Hook/DEX predecessors before any live-browser
   autonomy claim;
5. BWA-2: ChatGPT Web and Gemini Web adapters after the live-provider gates pass;
6. BWA-3: zero-human-continuation E2E with restart + context rollover;
7. integrate cockpit/status with WO257 Monitor API/Extension UI;
8. expose adapter-local Play/Pause for automatic wake arming; no production
   Command Gateway source exists on current main, so consequential execution
   pause/cancel/retry/reassign remains future Command-Gateway-only scope;
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
- explicitly reconcile with WO257, the current accepted Hook-contract family, WO369, WO374, DEX-ARCH-1/DEX-3b and Issue #215 automatic-continuation authority rather than duplicating them;
- specify that ChatGPT/Gemini web adapters require no native `/goal`;
- keep scheduled-goal authority outside Chrome/Extension state;
- define phased dependencies, success metrics, typed failure/security rules and implementation gates;
- preserve active #215 / WO205 / Hook / DEX lane ownership and make no source/runtime mutation;
- run markdown/text hygiene, UTF-8, `git diff --check`, exact-scope check;
- freeze/push docs candidate for independent review before any merge/project-plan fold.

## Continuity

Fresh session resume order:
`00-AGENT-ENTRY.md -> PROJECT-GRAPH.yaml -> AGENTS.md -> actual Git/GitHub -> Issue #446 -> this WO -> roadmap`.

Before implementation planning, re-read Issue #446, historical Issue #320 as
evidence only, Issue #215 automatic
continuation authority, WO257 plus the current Hook-contract family / Issue #368,
accepted WO369 context rollover, canonical WO374 durable-lane overlay,
DEX-ARCH-1, merged DEX-2b identity/receipt foundation, and the still-open
DEX-2a / production DEX-3a seams. Treat PR #263/#269/#274 and WO191/195/227 as
historical/unaccepted evidence, not current automatic-continuation authority.

Next safe action: verify the reconciled two-file diff against current main,
freeze/push a new exact candidate, checkpoint canonical Issue #446 and historical
Issue #320, then obtain a qualified
independent GLM-5.3 MAX exact-SHA architecture/security/reuse review plus exact-head
CI. Do not edit product source under this WO. After WO446 acceptance, open BWA-0
immediately as a bounded DEX-3b contract lane. Shape BWA-1 read-only while BWA-0
is reviewed; begin tracked fake-provider Native-Messaging/MV3 transport only after
BWA-0 acceptance and WIP admission. Open ZRA/Hook/DEX
predecessors continue in their existing owner lanes and gate BWA-2/BWA-3 live
autonomy rather than forcing BWA-0/BWA-1 to idle.
