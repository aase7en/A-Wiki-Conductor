# WO-P1-562 — A-Audit task suitability skill

Status: ACTIVE / R3 / CLAIMED / IMPLEMENTED_PENDING_VERIFICATION
Issue: #562
Authority: GitHub Issue #562
Repository: `aase7en/A-Wiki-Conductor` (`CONTROL_PLANE_ONLY`)
Base: `origin/main@0f0a5f17b33e82516e39ff00f482887728810e87`
Branch: `codex/wo-p1-562-a-audit-suitability`
Worktree: `/Users/aase7en/.codex/worktrees/a-audit-skill/A-Wiki-Conductor-codex-supervisor`

## Goal

Add a reusable Conductor-local `A-Audit` task-suitability skill, then add one
bounded call site to the repository-local `A-FastTask` router. The audit
recommends one executor/workflow class for an already-authorized, deterministically
eligible task. It cites observable task evidence and leaves every task, claim,
scope, route, provider, mutation, review, merge, and completion decision with
the existing deterministic owners.

## Authority and failure model

- Risk is R3 because this changes a binding router projection and could steer
  downstream model/workflow selection.
- The integrator frames the trust and failure boundary and accepts the final
  result. A-Audit/JEV output is advisory and cannot grant authority.
- A-Audit accepts only an existing task packet plus facts collected by existing
  deterministic tools/policies. It runs after deterministic eligibility and
  before A-FastTask/A-Faster route selection.
- Missing, stale, conflicting, sensitive, or malformed input fails closed to
  a deterministic/frontier fallback or `HUMAN_REQUIRED`; no provider call or
  mutation follows from the recommendation alone.
- JEV is only considered in a currently accepted mode, through an accepted
  provider-neutral seam and admitted route. The current A-Faster reference
  says its effective executable mode is OFF until those prerequisites are
  accepted. A-Audit must not improvise a direct TypeSafe call.
- Before each material GLM dispatch, use one fresh GET to
  `https://cointh.com/glm/api/quota` with the approved token as `x-api-key`;
  never log the credential. A complete valid positive tuple is
  `PROXY_QUOTA_STATE=AVAILABLE`, even when `window_source=stale`; a complete
  valid zero-balance tuple is `EXHAUSTED`; malformed, inconsistent, expired,
  non-200, credential, or transport/TLS failures are `UNKNOWN`. Do not require
  a separate upstream smoke/readiness call before useful authorized work: the
  actual request tests that route, and an explicit provider throttle/reset
  blocks only that provider/model route. Existing route, cost, authorization,
  claim, scope, WIP, and other gates remain binding.
- Device/harness availability affects only routes that require that surface.
  An offline Windows surface is zero current capacity and must not block an
  independent authorized Mac route. Device count never multiplies the current
  canonical project/global WIP budget. This WO does not change that budget.

## Exact claimed file scope

- NEW `.agents/skills/a-audit/SKILL.md`
- MODIFY `.agents/skills/a-fasttask/SKILL.md` only to invoke A-Audit after
  deterministic eligibility and before eligible route selection.
- NEW `docs/work-orders/WO-P1-562-a-audit-task-suitability-skill.md`

No hooks, runtime/source code, tests, A-Wiki files, or other skill paths are in
scope. No `CURRENT-WORK.md` or `handoff.md` edits are included because this is
a bounded child lane and those shared continuity paths are owned by other
active work.

## Recommendation classes

The skill must return exactly one primary class:

- `KEEP_DETERMINISTIC`
- `JEV_SHADOW`
- `JEV_ADVISORY`
- `CHEAP_RECON`
- `STRONG_IMPLEMENTATION`
- `STRONG_REPAIR`
- `STRONG_REVIEW`
- `FRONTIER_ARCHITECTURE`
- `HUMAN_REQUIRED`

For every recommendation, include evidence, uncertainty/confidence, data
sensitivity, semantic brittleness, expected latency/cost value, deterministic
owner of the decision, eligibility/readiness notes, and a safe fallback. The
class is not an exact model selection. A-FastTask/A-Faster selects only among
already eligible routes. If the recommended JEV mode/route is not admitted,
report that as blocked and retain the fallback without calling JEV.

## Explicitly forbidden

- No JEV, GLM, Codex, or other provider inference call from this skill-authoring
  lane.
- No new task/claim/WIP/quota/provider registry, scheduler, hook, policy store,
  execution store, automatic dispatch, or route/model authority.
- No per-device WIP expansion or worker-count-based parallelism.
- No changes to A-Faster, A-NightShift, `.codex/hooks/**`, A-Wiki, or
  SunDayRemoteMCP. Do not edit paths owned by active issues #498, #508/#561,
  #549/#550, #551/#552, or #560.
- No secret values, secret paths, private payloads, or credentials in the skill,
  work order, issue, or verification output.

## Acceptance

1. The skill returns exactly one class from the list above and cites concrete
   evidence for it.
2. Every class has inclusion/exclusion guidance, required evidence, a typed
   uncertainty/failure fallback, and explicit deterministic authority owner.
3. JEV modes remain advisory and fail closed while OFF/unadmitted; no direct
   TypeSafe/provider calls are authorized.
4. A-FastTask invokes A-Audit separately for each already-authorized task after
   that task's eligibility/claim/scope/WIP gates and before its route choice;
   parent/aggregate/sibling recommendations are never reused. Any child item
   must first be bound and made READY by existing authorities. A-FastTask and
   A-Faster remain route owners.
5. Offline devices block only routes that depend on them; device availability
   never changes canonical WIP or the set of eligible READY tasks.
6. Exact diff contains only the three claimed files. Skill frontmatter and
   structure pass the repository's skill validator; UTF-8, `git diff --check`,
   recommendation coverage, authority boundaries, and exact-scope checks pass.
7. Freeze one exact candidate SHA. Obtain the required independent exact-SHA
   review and exact-head hosted CI before acceptance/merge.

## Execution and evidence

- Claim tuple: `A-Wiki-Conductor -> isolated worktree above -> branch above ->
  base HEAD 0f0a5f17b33e82516e39ff00f482887728810e87 -> Issue #562 / WO-P1-562
  -> exact three-file scope`.
- Provider offload assessment: `NOT_BENEFICIAL` for writing this docs-only
  control-plane contract; no inference is necessary. Deterministic validation
  and independent review supply the needed evidence.
- No automated behavior/unit tests are added or run; this WO changes no
  executable code. Use the prescribed skill validator and targeted structural,
  authority, UTF-8, diff, and scope checks.
- The worktree started clean and detached at the exact base. Re-run the full
  mutation gate now that this bootstrap WO exists and after every ownership or
  HEAD change.

## Checkpoint

- Initial bootstrap: created from a clean isolated worktree at the base SHA
  above. The issue claim comment and post-bootstrap mutation verdict must be
  recorded before editing either skill.
- Claim: Issue #562 comment `5857078408`; exact worktree, branch, base HEAD,
  three-file scope, R3 classification and forbidden surfaces are recorded.
- Reuse-before-build: inspected A-Wiki's canonical
  `skills/awiki/a-fasttask/SKILL.md` and Issue #60. The universal FastTask is
  already the thin cross-harness router and explicitly defers to this repo's
  local binding. Issue #60 remains open for registry cross-harness exposure;
  it does not claim this Conductor file scope. No A-Wiki `A-Audit` skill or
  active A-Audit issue was found. Decision: `REUSE` the canonical/global
  FastTask and existing Conductor-local binding, then `EXTEND` only the local
  binding with one A-Audit pointer. Do not change A-Wiki or create a generic
  A-Wiki authority in this lane.
- Collision/WIP pulse: SundayMCP recovery at 2026-09-27 15:06 UTC found no
  RUNNING/UNKNOWN/INTERRUPTED/STALLED executions and no active Sunday lane.
  Latest accepted #498 marker, observed 2026-09-27 10:30:45 UTC, recorded
  `UNUSED_SAFE_CAPACITY=1`; this #562 claim consumes that one global mutable
  slot. No extra per-device slot is inferred. Open-PR path search found no
  other PR touching `.agents/skills/a-fasttask/SKILL.md`; current #550 owns
  A-Faster/hook paths and #552 owns the A-Wiki claim-reader contract.
- Post-bootstrap gate (2026-09-27 15:15 UTC): remote is
  `https://github.com/aase7en/A-Wiki-Conductor.git`; branch is
  `codex/wo-p1-562-a-audit-suitability`; HEAD remains exact base
  `0f0a5f17b33e82516e39ff00f482887728810e87`; initial tree was clean and the
  only dirty path is this claimed new work order. Issue #562 is OPEN and the
  exact claim is live. No material GLM/JEV delegated run will be started by
  this docs lane, so quota/provider freshness is not a dispatch precondition
  for authoring.
- `SAFE_TO_MUTATE = YES` for the three exact Issue #562 paths only, under the
  single existing global mutable WIP slot. Re-run the gate if HEAD, claim,
  scope, WIP occupancy, remote state, or ownership changes.
- Implemented within the claim: new `.agents/skills/a-audit/SKILL.md` defines
  the nine required classes, evidence schema, JEV OFF/admission fallback,
  secret-safe quota boundaries, and independent device liveness/capacity rules.
  `.agents/skills/a-fasttask/SKILL.md` now calls A-Audit only after
  deterministic eligibility and before executor/workflow selection; it
  treats `window_source=stale` as response metadata when a fresh positive quota
  tuple is otherwise valid, and permits eligible independent Mac routes under
  the unchanged project-wide WIP cap.
- No hook/A-Faster/A-NightShift/runtime/A-Wiki/SRM files or tests were changed.
- Historical policy checkpoint (superseded 2026-09-28): the first
  implementation treated `window_source=stale` as UNKNOWN and required
  upstream READY before dispatch. This contradicted the user's explicit
  instruction to use a fresh positive proxy quota and diagnose upstream from
  the real request. WO-P1-564 now records the corrected policy; these three
  #562 files are being reconciled within their existing claim.
- Review-route preflight at 2026-09-27 15:19:24 UTC used the user-specified
  CoinTH quota endpoint with the approved environment binding held in memory;
  the first urllib transport attempt failed before receiving an HTTP response,
  then the documented cURL client returned HTTP 200. The response contained
  non-exhausted counters and `window_source=stale`; exact live counters are
  deliberately not retained in this public repository. The prior conclusion
  that stale provenance made quota UNKNOWN is superseded by the corrected
  policy above. No GLM/JEV call was made during that historical preflight.
  Other eligible routes remain independent.
- Routing order: executor/model preference and `GLM_OFFLOAD_ASSESSMENT` are
  explicitly after A-Audit; deterministic eligibility, route evidence, WIP and
  provider guards stay authoritative. A-Audit reports sensitivity,
  semantic-brittleness, ambiguity/risk, qualitative confidence, latency/cost
  value, route status and fallback.
- Final validation on the implemented bytes at 2026-09-27 15:20 UTC: skill
  validator `Skill is valid!`; `git diff --check` PASS; strict UTF-8 and no
  trailing whitespace on all three files; exact changed paths equal the claim;
  all five referenced policy/runbook files exist. No tests were run.
- Next safe action: commit the exact three-file candidate, post its SHA to
  Issue #562, and obtain the required independent exact-SHA review and
  exact-head CI before acceptance or merge.

### Hosted CI repair checkpoint — 2026-09-27

- Exact candidate `9888b3797ef1db4e0ce13ffa0df49895924eadbc` passed Ubuntu and macOS smoke but its hosted `test` job failed in `test_work_order_identity.py`: GitHub-backed WOs at this ID require exactly one literal `Issue: #562` line.
- Added that required identity line to this work order within the original three-file claim. The failed candidate is not accepted; the next pushed head requires fresh exact-head CI and independent review.
- No local automated tests were run. The reviewer attempts produced no findings because both Codex review agents terminated at the account usage limit.
- The historical candidate's stale-window/upstream-READY gate has been removed
  per the explicit operator correction and the corrected semantics in WO-P1-564.
  Before the next actual GLM review dispatch, make one fresh quota GET and
  satisfy the existing claim, WIP, exact-SHA binding, and harness gates; no
  separate upstream probe is required.

### Independent exact-SHA review and bounded repair — 2026-09-27

- Read-only R3 review of candidate `b89f0275a9954afba8d493e7bd90197ccc6bf559` found one P2 ambiguity: A-FastTask could appear to apply one audit recommendation across multiple pipeline tasks or decomposed children.
- The candidate remains unaccepted despite green exact-head CI. The repair stays within the original three-file claim and clarifies that every task is audited independently only after its own existing authorization, READY, claim, scope, hotspot, WIP, and route-evidence gates pass. Parent, aggregate, and sibling recommendations cannot be reused; unbound children are not selected or dispatched.
- No runtime, hook, provider, task-store, A-Wiki, or SunDayRemoteMCP change is introduced. No tests were added or run.
- Static validation at 2026-09-27 16:21 UTC: strict UTF-8 and trailing-whitespace checks passed for all three claimed files; the work-order identity has exactly one `Issue: #562` line; per-task routing boundaries passed; the candidate remains exactly the original three-path scope; `git diff --check` passed. No tests were added or run.
- Next: publish the repaired exact candidate without force, then obtain exact-head CI and a fresh independent R3 review before acceptance.

### CoinTH policy reconciliation — 2026-09-28

- Recovered Mac and Windows SundayMCP execution ledgers: each reported 160
  executions (106 completed, 14 failed, 40 cancelled), no open execution, and
  no active lane. The completed Kilo review remains for prior candidate
  `b89f0275...`; it does not review current candidate `3c27bfe...`.
- Reconciled the three claimed paths with WO-P1-564's user-directed live quota
  semantics: a fresh complete positive tuple is AVAILABLE regardless of
  `window_source`; no separate upstream smoke/READY gate; a real explicit
  provider throttle blocks only that route. Deterministic claim/scope/WIP,
  route, cost, authorization, and review gates remain.
- PR #563 remains draft/open. Current exact-head checks on `3c27bfe...` are
  green, but it has no review request/review for that SHA. These policy edits
  create a replacement candidate requiring fresh exact-SHA review and hosted
  checks. No acceptance or merge is claimed.
