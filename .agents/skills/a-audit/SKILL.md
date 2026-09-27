---
name: a-audit
description: "A-Sunday Conductor task-suitability adviser. Use after deterministic task eligibility is established and before A-FastTask/A-Faster selects among eligible routes. Recommends one handling class with evidence and fallback; never grants task, claim, model, provider, mutation, review, merge, or completion authority."
---

# A-Audit — task suitability adviser

## Purpose and boundary

Inspect one already-authorized, deterministically eligible task and recommend
exactly one handling class. Reduce unnecessary frontier-model work by matching
the task to deterministic logic, an admitted JEV mode, cheap read-only
reconnaissance, a strong implementation/repair/review route, frontier
architecture reasoning, or a human decision.

A-Audit is advisory. It is called from the Conductor-local A-FastTask binding
after recovery and deterministic eligibility/ownership checks, before selecting
an executor/workflow. It does not select new work, split or claim tasks, create
lanes, check out worktrees, call providers, dispatch, change WIP, or accept
results. A-FastTask/A-Faster and existing deterministic authorities decide
whether any recommended route is actually eligible.

## Required inputs

Use facts already established by repository/runtime tools and the active task
packet:

- exact repo, worktree, branch, HEAD and dirty-state ownership;
- task/work-order, owner/claim, allowed/forbidden paths and dependency state;
- risk tier, acceptance criteria and deterministic verification available;
- active global WIP and mutable-hotspot ownership;
- data sensitivity and any security/authorization boundary;
- candidate harness/model routes with current availability, readiness,
  authorization and cost evidence when a provider route is being considered;
- semantic ambiguity, repeatability, expected latency/cost benefit and
  evidence destination.

Do not infer missing facts from task prose, model familiarity, an installed CLI,
a stale pulse, a quota counter, or another device's status. If a required fact
is absent or conflicts with authoritative evidence, return `HUMAN_REQUIRED`
with the typed blocker and the smallest evidence needed to resolve it. Do not
call JEV or another provider to discover deterministic facts.

## Deterministic-first checks

Before making the recommendation, confirm from existing authorities:

1. The task itself is authorized and its current claim, repo/worktree/branch/
   HEAD, mutable scope and ownership are known.
2. Dependencies are satisfied, the task is READY, and global WIP has a valid
   slot. A recommendation cannot make blocked work READY.
3. Repository/runtime facts, exact diffs/SHAs, quota/readiness, permissions,
   arithmetic, schemas and acceptance results come from their deterministic
   owners, never a semantic model.
4. Provider and device availability are separate facts. An offline device has
   zero current capacity and blocks only work that requires it. A missing
   Windows Worker/RDC surface does not block an independent authorized Mac
   route. Installed Kilo/Claude/Codex binaries alone do not prove a live model
   route.
5. Device count never multiplies the canonical project/global WIP budget.
   Use discovered per-device resources to rule routes in or out within that
   budget; do not invent extra task or review slots.

If these preconditions have not been proven, A-FastTask must not treat this
recommendation as a route admission.

## Keep evidence dimensions separate

| Evidence | Meaning | What it does not mean |
|---|---|---|
| Fresh CoinTH GET has a complete valid tuple, `remaining_5h > 0`, and no positive expiry flag (including `window_source=stale`) | `PROXY_QUOTA_STATE=AVAILABLE`; retain source metadata with the counters/reset evidence | It does not prove upstream success, but the useful real request may test that route |
| Fresh CoinTH GET has a complete valid tuple and `remaining_5h == 0` | `PROXY_QUOTA_STATE=EXHAUSTED` | It does not prove upstream throttling or device unavailability |
| CoinTH GET is missing, malformed, inconsistent, expired, non-200, or has transport/TLS/credential failure | `PROXY_QUOTA_STATE=UNKNOWN` | It does not prove exhaustion or upstream throttling |
| Positive proxy quota without an actual request result | It establishes proxy capacity only; deterministic route/model/claim/scope/WIP/authorization gates still apply | It does not prove that the upstream model request will succeed |
| A useful GLM request returns explicit provider throttle/reset evidence | Block only that provider/model route until the stated reset unless material evidence changes | It does not block independently eligible Codex/native/other-device work |
| A device pulse is stale or its session/process state is unknown | Reconcile that exact lane's process/session, result, Git state, claim and replay safety | It does not mark every device or every project lane unavailable |
| A device is actually offline/unreachable | That device contributes zero current capacity | It does not block work on another ready device or create extra WIP there |

For material GLM work, the existing deterministic pre-dispatch guard owns the
quota check. It uses `GET https://cointh.com/glm/api/quota` with the approved
`COINTH_GLM_AUTH_TOKEN` sent only as `x-api-key`; never expose or store the
credential. Make one fresh GET immediately before each material GLM dispatch.
The user-directed current interpretation is recorded in Issue #564: a complete
valid positive five-hour tuple is proxy
`AVAILABLE`, including when `window_source=stale`; a complete valid
zero-balance tuple is `EXHAUSTED`; missing, malformed, inconsistent, expired,
transport/TLS, or non-200 evidence is `UNKNOWN`. That policy correction
supersedes the legacy stale-window and upstream-READY clauses in
`docs/runbooks/cointh-glm-quota.md` until its owner reconciles the runbook.
Use the runbook for request mechanics and secret handling during that bounded
reconciliation. Do not make an upstream smoke/readiness call before useful
work. The real GLM request tests its route; if it returns explicit provider
throttle/reset evidence, block only that provider/model route until reset.
Existing route/model/cost/authorization/claim/scope/WIP gates still apply.
A-Audit does not perform the request or replace the deterministic guard. An
`UNKNOWN` or `EXHAUSTED` quota blocks only GLM; continue safe work through
other already eligible routes.

## Recommendation classes

Return exactly one primary class:

| Class | Recommend when | Do not use when |
|---|---|---|
| `KEEP_DETERMINISTIC` | The task is exact, repeatable, mechanical or has facts/acceptance owned by tools, scripts, tests, schemas, Git or policy code | A bounded semantic judgment is material to the next safe action |
| `JEV_SHADOW` | A bounded, sanitized, typed semantic decision belongs to a currently allowlisted JEV family and would benefit from shadow comparison | Do not invoke JEV unless SHADOW mode and route are accepted; do not send sensitive/unbounded data, unadmitted families, or outputs that trigger product consequences |
| `JEV_ADVISORY` | A bounded, allowlisted semantic decision could benefit from advisory input while deterministic fallback remains explicit | Do not invoke JEV unless ADVISORY mode, provider-neutral seam and route are accepted; never use it for authority/security/ownership/mutation/review/merge/completion |
| `CHEAP_RECON` | A bounded read-only inventory, scope scan, dependency census, compatibility precheck or task-packet shaping can reduce latency/cost | Work needs writes, broad private-data ingestion, frontier judgment, or a qualified independent review |
| `STRONG_IMPLEMENTATION` | A bounded READY implementation has clear inputs, file ownership and deterministic acceptance | Architecture/authority is unresolved, scope is ambiguous, or route is not admitted |
| `STRONG_REPAIR` | A reproducible defect has a bounded repair surface and a deterministic regression check | Root cause/replay safety/owner is unknown, or repair crosses unclaimed paths |
| `STRONG_REVIEW` | A frozen exact-SHA candidate needs an independent review by a qualified reviewer | Reviewer is not independent/qualified, SHA is mutable, or deterministic checks are being delegated to model judgment |
| `FRONTIER_ARCHITECTURE` | Novel design, trust boundaries, conflicting high-impact evidence, dependency ordering or difficult unresolved system reasoning needs integrator-level judgment | The answer is already deterministic or the remaining choice belongs to a human authority |
| `HUMAN_REQUIRED` | Approval, external intent, policy choice, private-data decision or unresolved authority/ownership is required | The blocker can be resolved safely from existing deterministic evidence without a human decision |

### JEV restrictions

JEV is a System-One structured-decision adviser, not an engineering executor.
Use only the accepted provider-neutral seam, admitted route, supported JEV
mode and allowlisted decision family described by
`.agents/skills/a-faster/references/jev-semantic-fast-path.md`. That reference
is the source of truth for the current effective mode and must be checked for
each relevant task because accepted mode can change. When it reports `OFF` or
the route/admission prerequisites are not accepted:

- A-Audit may identify `JEV_SHADOW` or `JEV_ADVISORY` as the best *semantic
  fit*, but must report `route_status=BLOCKED` when the corresponding mode or
  route is not accepted and must not make a direct TypeSafe call.
- In `SHADOW`, output cannot change routing or behavior. In `ADVISORY`, it may
  inform the deterministic integrator only; the integrator may disregard it.
- Authority, security, ownership, scope, task/claim creation, lane allocation,
  quota/provider admission, mutation, independent review, merge and completion
  decisions are never JEV-authoritative.
- Malformed output, transport/auth/schema error, uncertainty or missing
  freshness evidence escalates to the recorded deterministic/frontier fallback;
  do not retry unless a later accepted adapter contract explicitly permits it.

## Selection procedure

1. Summarize the task in one sentence from its authorized packet.
2. List the decisive evidence references and distinguish facts from
   interpretation. Do not restate secrets or private payloads.
3. Compare the task with the class table. Prefer deterministic handling when
   it can deliver the same accepted result; use semantic judgment only for a
   bounded, explicit answer space; reserve strong/frontier routes for the
   justified risk and complexity.
4. Recommend exactly one class. Record blocked candidate routes separately;
   never upgrade a blocked route because its model is preferred or quota looks
   plentiful.
5. State a safe fallback that can proceed with already eligible routes. A
   provider/device blocker must not serialize independent work.
6. Return the structured result below. Do not dispatch or claim the lane.

## Required result

```yaml
recommendation: KEEP_DETERMINISTIC
basis: "one sentence tying the class to task evidence"
evidence:
  - "repo-relative file, durable issue/work-order, exact SHA, or runtime fact"
confidence: MEDIUM
ambiguity_risk: "material ambiguity/risk and the evidence behind it"
data_sensitivity: INTERNAL # PUBLIC_SAFE | INTERNAL | SENSITIVE_RESTRICTED
semantic_brittleness: LOW # LOW | MEDIUM | HIGH, with a short basis
latency_cost_value: "expected benefit or NOT_BENEFICIAL, with reason"
route_status: NOT_REQUIRED # ELIGIBLE | BLOCKED | UNKNOWN | NOT_REQUIRED
route_evidence:
  - "exact current route/readiness evidence, or typed blocker"
fallback: "deterministic or frontier path that is already authorized"
deterministic_authority: "existing owner of task, route, mutation, review, and acceptance"
```

The example value is illustrative; choose the actual class and values from
evidence. `confidence` is qualitative (`HIGH|MEDIUM|LOW`) with a short basis,
not a made-up probability. Use the listed sensitivity categories and state the
basis for sensitivity and semantic brittleness. State material ambiguity/risk
explicitly. There must be exactly one `recommendation` and one safe
`fallback`.

## Existing authorities to reuse

- A-FastTask repo binding: `.agents/skills/a-fasttask/SKILL.md`
- Risk-tier delivery: `docs/agent-collab/FAST_EXECUTION_PROTOCOL.md`
- Executor capability: `docs/agent-collab/CAPABILITY_MATRIX.md`
- Device and route projection: `.agents/skills/a-faster/references/multidevice.md`
- JEV eligibility/modes: `.agents/skills/a-faster/references/jev-semantic-fast-path.md`
- CoinTH request mechanics and secret handling: `docs/runbooks/cointh-glm-quota.md`
- Current quota classification correction during runbook reconciliation:
  Issue #564; it supersedes only the legacy stale-window and
  upstream-READY clauses until the runbook owner aligns that file.

Do not fork their task, claim, WIP, quota/provider, execution, review or
completion authority into this skill.
