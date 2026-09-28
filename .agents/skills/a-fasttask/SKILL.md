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
   `docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md`; check global WIP once
   across all repositories in a compatibility set. Device count never
   multiplies that budget.

   For each individual `SAFE_READY` R2/R3 task, only after its task, dependency,
   authorization, claim, exact-scope, hotspot, WIP, permission and provider
   eligibility gates pass, read `.agents/skills/a-audit/SKILL.md` and produce
   exactly one task-bound recommendation. Then perform exactly one
   `GLM_OFFLOAD_ASSESSMENT` for that task before route selection. Record
   `DISPATCHED`, `NOT_BENEFICIAL` with a concrete reason, or `BLOCKED` with a
   typed reason. Never reuse a result across parent, sibling or child tasks;
   each child must first be independently authorized, bound and `SAFE_READY`.
   A-Audit does not create, split, claim, dispatch or accept work.

   Select only among routes that remain eligible under existing capability,
   quota, provider, cost, claim, scope, permission and WIP authorities. Try
   GLM-5.3 MAX first for useful bounded R2/R3 implementation, repair and
   qualified independent review; GLM-5.3-Flash is bounded read-only assist.
   Keep the benchmark guidance as candidate-fit evidence, not authority. Do
   not rank or select a model before A-Audit. GPT/Luna retains supervision,
   architecture/trust decisions, integration, final adjudication and merge;
   no model identity grants authority. A separate qualified reviewer is still
   required wherever policy requires independent review.

   The existing deterministic pre-dispatch guard owns CoinTH request
   mechanics and classification; use
   `docs/runbooks/cointh-glm-quota.md` for request/secret mechanics and the
   current operator interpretation in Issue #564 for quota-state semantics.
   Until the runbook owner reconciles it, Issue #564's correction supersedes
   only the runbook's legacy stale-window and upstream-READY clauses. Resolve
   credentials only through the approved secret source,
   send them only as `x-api-key`, and never print or persist them. Make one
   fresh quota GET immediately before each actual material GLM invocation.
   The guard result is proxy/account evidence, not model selection or route
   authorization. A complete valid positive tuple is `AVAILABLE` even when
   `window_source=stale`; a valid zero balance is `EXHAUSTED`; malformed,
   inconsistent, expired, transport/TLS, credential or non-200 results are
   `UNKNOWN`. Do not add a separate upstream smoke probe before useful work;
   the useful real request tests the exact route. Only explicit provider
   throttle/reset evidence blocks that provider/model route until reset; do
   not repeat quota/root-cause probes before reset absent material evidence.
   HTTP 401/403 is auth/entitlement evidence, not quota exhaustion. Unknown or
   exhausted GLM blocks only that route; continue independently eligible work.
   A quota GET's observed token-counter behavior is not a billing guarantee.

   A-Audit results must reproduce the exact topology and repository bindings
   from deterministic task/claim/Git authorities. For `CONTROL_PLANE_ONLY`,
   require only `AUTHORITY_REPO`; for `EXECUTION_SUBSTRATE_ONLY`, only
   `EXECUTION_REPO`; for `CROSS_REPO`, require exactly both roles and the
   exact `{AUTHORITY_REPO@SHA_AUTH, EXECUTION_REPO@SHA_EXEC}` compatibility
   set. Each repository entry binds its exact worktree, branch, full HEAD and
   scope; a missing, extra, stale or mismatched member makes the result
   `HUMAN_REQUIRED`. The task, work order and claim must also match exactly.
   The recommendation must be exactly one non-empty class from A-Audit's
   nine-value enum; missing, empty, multiple or out-of-enum values are
   malformed. Discard malformed or mismatched results as `HUMAN_REQUIRED`;
   never use them to select or dispatch a route. A-FastTask/A-Faster remain
   the route owners. JEV is considered only in its currently accepted mode
   through the admitted provider-neutral seam; A-Audit never makes a direct
   TypeSafe or other provider call.

   Keep quota provenance separate from device liveness. A stale
   `window_source` does not prove exhaustion, provider throttling or Windows
   unavailability. Reconcile a stale device pulse against that lane's runtime,
   session, Git, claim and replay evidence. An offline Windows surface blocks
   only work that requires it; independently eligible routes on another
   verified surface remain available subject to their own gates.
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
