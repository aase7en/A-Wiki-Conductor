---
name: a-fasttask
description: A-Sunday Conductor repo-scoped session ROUTER for substantial multi-step work only — routing a non-trivial session through entry/classify/claim/workflow selection, filling or recycling a parallel WIP lane, cross-executor continuation/takeover of a stalled lane, or explicit closeout of a temporary lane. Binds to existing 00-AGENT-ENTRY / PROJECT-GRAPH / FAST_EXECUTION / routing / claim authorities, then hands control to the selected existing workflow. NOT for trivial Q&A, single obvious mechanical edits, or work needing no claim/workflow/lane selection. Grants no mutation, transfer, cleanup, or acceptance authority.
---

# A-FastTask — repo-scoped progressive-disclosure router/binder

Router ONLY (WO-P1-245 / Issue #327; session-routing fold WO-P1-247). This skill
binds the reading agent to the repository's existing execution authorities and
returns one routing decision. It is not, and must not become: a scheduler, task
store, claim/lease system, reviewer, handoff SSoT, completion state machine,
daemon, background cleanup queue, provider registry, or source/runtime adapter.

The generic/global A-FastTask policy is owned by the canonical A-Wiki skill
registry. This Conductor copy is the repo binding/projection and may add only
Conductor-specific authority paths, routing references, and constraints. Do not
fork the generic policy into another global skill or hand-copy divergent full
instructions into every repository.

## Accelerated profile

For substantial **A-Sunday Conductor engineering work**, use **A-Faster** as
the default acceleration overlay after loading this canonical A-FastTask base.
Also use it whenever the user explicitly asks for A-Faster, coordinated
multi-device work, parallel Kilo + Claude Code GLM lanes, or accelerated lane
recycle/cleanup. Trivial Q&A, single obvious mechanical edits, and already-bound
mid-lane execution remain excluded by the negative triggers below.

Read `../a-faster/SKILL.md` after this file. A-Faster may add only
device/harness/WIP/readiness/cleanup routing constraints; it must not redefine
task, claim, provider, review, merge, completion, or memory authority.

## Trigger (use this skill)

- Substantial repo/session routing: a multi-step task that needs entry
  recovery, risk classification, core-surface readiness discovery, and a
  claimed non-overlapping lane before mutable work starts.
- Safe parallel-lane fill or recycle: choosing work for a free WIP lane within
  the existing `3 mutable + 1 read-only review` limit.
- Cross-executor continuation or takeover of a stalled/lane-lost session.
- Explicit closeout of a temporary lane/worktree at end of lane.

## Negative trigger (bypass this skill)

- Trivial Q&A about the repository.
- A single obvious mechanical edit with no claim/branch/workflow decision.
- Mid-lane execution of an already-claimed work-order packet (follow the
  packet as written; do not re-route mid-lane).
- Anything requiring no selection among executors, workflows, or lanes.

## Routing loop

1. RECOVER — run the `00-AGENT-ENTRY.md` start sequence; recover actual
   repository/worktree/remote/branch/HEAD/dirty/claim state, plus task and
   execution liveness per `docs/agent-collab/EXECUTION_LIVENESS_PROTOCOL.md`.
   Before selecting new READY work, reconcile every known outstanding delegated
   execution pointer for the current task/claim from existing job/events/
   checkpoints/evidence plus actual process/session/log/result/Git state.
   The census scope is the current project: its active/open work orders and
   Issues plus material recent lane pointers, including GLM assignments from
   prior invocations and from sessions other than this one whenever they are
   discoverable from that durable evidence. Do not scan arbitrary ancient
   unrelated projects. Derive `RUNNING`, `TERMINAL_UNHARVESTED`, `STALLED`,
   `INTERRUPTED`, `UNKNOWN`, or `TERMINAL`. Never infer `RUNNING` from a
   stale PID number alone: a PID is live evidence only when it matches the
   recorded creation/command/boot identity where available. Harvest and
   verify `TERMINAL_UNHARVESTED` results before redispatch or
   conflicting mutation. `STALLED`, timeout, transport loss, or session loss
   never grants replay authority; route them through existing recovery/takeover
   rules, and reconcile side effects/replay safety before any takeover of an
   ambiguous state. A fresh chat/session never means a fresh task. This is
   recovery/harvest routing only — A-FastTask creates no new
   execution store or lifecycle state.
2. BOOTSTRAP — for a substantial project/engineering session, attempt the
   lightweight READ-ONLY core-surface discovery defined by
   `docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md`: RDC exact device/runtime,
   GitHub remote truth, and exposed SunDay lane readiness. A missing or
   failed surface receives a typed blocker and blocks only dependent work.
   LANE CONTEXT BIND: each lane is bound to exactly one repo by the full
   tuple `repo -> worktree -> branch -> HEAD -> task/claim -> scope`,
   verified against its executor process/context. There is no mutable
   global Active Project to bind to; Worker 1..N is lane naming only. A
   context mismatch fails closed as `CONTEXT_DRIFT`, blocks only that lane,
   and is reconciled before resume. Bound never implies mutation authority.
   Topology (`CONTROL_PLANE_ONLY` / `EXECUTION_SUBSTRATE_ONLY` /
   `CROSS_REPO`) is defined only in
   `docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md`; projected here
   without redefining: a `CROSS_REPO` freeze pins one exact-SHA
   compatibility set `{AUTHORITY_REPO@SHA_AUTH, EXECUTION_REPO@SHA_EXEC}`
   and any member head drift invalidates the set until re-pin and focused
   review of the affected delta; WIP stays one global budget across set
   members; and CROSS_REPO evidence/results fold to the AUTHORITY_REPO.
   Windows process routing follows the durable no-console rule from the
   same home: exact installed executable invoked directly; hidden
   PowerShell only when unavoidable; background children launched with
   `CREATE_NO_WINDOW`/`windowsHide`; exact-PID-only termination with
   verified command identity; never change global shell settings.
3. CLASSIFY — classify R0/R1/R2/R3 per
   `docs/agent-collab/FAST_EXECUTION_PROTOCOL.md`; inventory candidate
   executors per `docs/agent-collab/CAPABILITY_MATRIX.md` and
   `docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md`; check WIP capacity per
   `PROJECT-GRAPH.yaml` `rules.default_wip`, counted once across all
   compatibility-set members (`CROSS_REPO` never multiplies WIP per
   repository). For every substantial multi-step task, perform
   `GLM_OFFLOAD_ASSESSMENT` after A-Audit as part of final eligible-route
   selection. Before each material GLM
   dispatch, refresh the approved quota evidence. Resolve the CoinTH
   credential through an approved secret source: environment binding first,
   then an approved global secret file/resolver when available. The current
   proven CoinTH secret name is `COINTH_GLM_AUTH_TOKEN`; send its value only as
   `x-api-key` to `GET https://cointh.com/glm/api/quota`, never print/persist it.
   Treat that five-hour tuple as proxy/account evidence only:
   `PROXY_QUOTA_STATE = AVAILABLE | EXHAUSTED | UNKNOWN`. Do not require a
   separate upstream admission/smoke probe before useful authorized work. A
   successful fresh HTTP 200 with a complete, valid tuple, `remaining_5h > 0`,
   and no positive expiry flag is `AVAILABLE`, even when
   `window_source=stale`; preserve that field as metadata. A complete valid
   tuple with `remaining_5h == 0` is `EXHAUSTED`; missing credentials,
   transport/TLS/non-200 errors, malformed or inconsistent fields, and an
   expired tuple are `UNKNOWN`. Refresh the GET immediately before each
   material GLM dispatch. The real request then establishes or blocks that
   exact route: only explicit provider throttle/reset evidence suppresses that
   provider/model route until reset; diagnose other concrete errors only after
   they occur, without looping probes. HTTP 401/403 remains
   auth/entitlement evidence, not quota exhaustion. The current user-directed
   interpretation is recorded in Issue #564; until its owner
   reconciles the runbook, that correction supersedes only the legacy
   stale-window and upstream-READY clauses. This rule does not bypass
   model/route/claim/scope/authorization/WIP/cost gates or create provider
   authority.
   Provider guidance says this quota GET does not consume GLM quota; a 2026-09-16
   back-to-back live check observed zero change in `used_5h` and `remaining_5h`.
   Treat that as operational supporting evidence, not a billing guarantee.
   `QUOTA_UNKNOWN` is not `RATE_LIMITED` and is never treated as unlimited.
   Legacy `QUOTA_AVAILABLE` here means proxy/account capacity only. When
   `PROXY_QUOTA_STATE=AVAILABLE`, refresh proxy quota before EACH material GLM
   dispatch and keep filling eligible independent GLM lanes up to WIP; do not
   serialize them merely to conserve quota. A separate upstream READY
   assertion is not a precondition: the useful real request tests that route.
   Proxy `QUOTA_EXHAUSTED` or `QUOTA_UNKNOWN` blocks only GLM dispatch without
   blocking independently eligible GPT/Codex lanes. Keep the
   A-Faster benchmark guidance as candidate-fit evidence for the post-A-Audit
   selection (GLM-5.3 MAX for R2/R3 implementation and required independent
   review; GLM-5.3-Flash for bounded read-only assist). Do not rank or select
   a model before A-Audit; the deterministic selector chooses only from
   currently eligible routes. A cheaper or faster model never silently
   satisfies a required independent R3/qualified review, and no model identity
   grants authority.
   If the exact upstream GLM admission is observed `RATE_LIMITED`, record the
   provider-reported reset evidence, set GLM offload blocked for that window,
   and do not repeat quota/credential root-cause work or live admission probes
   before the reset unless material evidence changes. Harvest any terminal GLM
   execution first, then let GPT-5.6 Sol take over eligible READY
   implementation/analysis work within the verified claim/scope so throughput
   continues. Independent-review requirements do not transfer to the authoring
   Sol lane: a separate qualified reviewer is still required where policy says
   independent review. At/after reset, refresh quota once immediately before
   the next useful authorized GLM task; let that real request establish whether
   the exact route has recovered, then refill other eligible GLM lanes up to WIP.
   After deterministic task eligibility, dependency, authorization, claim,
   scope, hotspot, WIP and route-evidence checks, read
   `.agents/skills/a-audit/SKILL.md` and produce exactly one advisory handling
   class with cited evidence and a safe fallback. Scope each recommendation to
   the exact task/work-order/claim/scope tuple. When one pipeline handles
   multiple independent eligible tasks, invoke A-Audit separately for each
   task after that task passes its deterministic eligibility, dependency,
   authorization, claim, scope, hotspot, WIP and route-evidence checks, and
   before selecting that task's executor/workflow. Never reuse a parent,
   aggregate, or sibling recommendation for another task. Any child work item
   must first be created/authorized/bound by the existing task and claim
   authorities; if it is not independently READY and bound, retain the existing
   blocked/unknown fallback and do not select or dispatch it. A-Audit does not
   create, split, or claim work. Select only among routes that remain eligible
   under the existing capability, quota, provider, cost, claim, scope and WIP
   authorities. JEV is considered only in its accepted mode through its
   admitted provider-neutral seam; A-Audit never makes a direct TypeSafe or
   other provider call and never dispatches work.
   Keep quota provenance separate from device liveness:
   `window_source=stale` is retained as CoinTH response metadata and does not
   change a complete valid positive fresh GET from `PROXY_QUOTA_STATE=AVAILABLE`;
   it does not prove exhaustion, upstream throttling, or that Windows is
   offline. Reconcile a stale device pulse
   against that exact lane's runtime/session/Git/claim evidence. A missing or
   offline Windows surface blocks only work that requires it; independently
   eligible Mac-local Kilo/Claude/Codex routes may proceed after their own
   exact harness/model/authorization/quota checks. Device availability
   never multiplies the project-wide WIP budget.
4. PIPELINE FILL — decompose independent READY work, then use the existing
   claim/lease + execution authorities to dispatch every eligible bounded GLM
   lane up to the current WIP/provider-capacity limits. Sol also assigns
   non-overlapping lane roles: implementation where claimed, GLM
   task-packet/dispatch assistance, deterministic verification, adversarial
   read-only review, and recovery/reserve. Lanes may help prepare or operate
   an accepted Kilo/Claude GLM route only within explicit scope and provider
   authority. Transitional Serena use, if any, is private per lane/worktree
   and optional. Prefer dispatch-first / harvest-later: Sol must not
   serialize independent work merely to wait for an earlier GLM report. GLM
   outputs should be challenged by an independent read-only lane when
   available; under default WIP only one such review lane runs at a time
   while other lanes remain standby or work inside already-owned lanes. Sol
   reconciles all findings and remains final acceptance authority.
   Harness-native helpers such as `/goal`, `/plan`, `/init`, and equivalents are
   conveniences only. Optimize accepted throughput while obeying quota, cost,
   WIP, scope, claims, and `1 MUTABLE HOTSPOT = 1 MUTATION OWNER`.
5. BRANCH — choose the one existing workflow that fits (normal fast path, R3
   high-risk path, continuation, takeover, or closeout) and read only the
   matching reference below:
   - roles / WIP / executor fallbacks / session bootstrap → `references/conductor.md`
   - continuation / takeover / checkpoint → `references/material-boundary.md`
   - temporary-lane closeout → `references/closeout.md`
6. BIND, then HAND OFF — record/report exactly these routing fields:
   - existing task/claim reference (work order + claim identity; never
     invented here);
   - chosen existing workflow (named file/risk tier);
   - evidence destination (ignored `runs/<work-item>/<lane>/` path);
   - current blocker (typed failure code or `NONE`);
   - outstanding delegated-execution reconciliation (`NONE`, or exact execution
     identities + derived states + harvest/recovery disposition from existing
     authorities);
   - GLM offload disposition (`DISPATCHED`, `NOT_BENEFICIAL`, or `BLOCKED`)
     with bounded reason and safe harness/model/quota-readiness facts when
     material; never include secrets;
   - cleanup state (`NOT_NEEDED`, `PENDING`, `BLOCKED`, or `COMPLETE`), plus
     exact path/reason/evidence when applicable;
   - exact next action (one bounded command or step).
   The A-FastTask routing role ends after this decision, but the user-facing
   session does NOT stop merely because routing finished. If this agent is the
   authorized selected executor/integrator and a safe next micro-step exists,
   continue immediately under the chosen existing workflow. Stop only for a
   real blocker/approval gate/terminal state, or when the route hands work to
   a different executor that must run on another execution surface.

## Authority floor

Selection of this skill grants NO mutation, transfer, cleanup, dispatch,
provider, or acceptance authority. If any required authority item is missing or
ambiguous, the routing decision is `SAFE_TO_MUTATE = NO` plus the typed blocker
and exact next action. No new authority path may be created to work around a
missing one. GLM/SunDayWorker/RDC/GitHub availability changes routing options,
never claims, leases, task semantics, or acceptance authority.
