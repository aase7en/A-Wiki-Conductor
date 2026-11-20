# Cost-First Delivery Runbook

Status: OPERATING RECIPE / applies existing authority
Owner: active work-order owner and GPT/integrator
Updated: 2026-09-15 / [WO241](../work-orders/WO-P1-241-sunday-delivery-priorities.md)
Source policies: [Fast Execution Protocol](../agent-collab/FAST_EXECUTION_PROTOCOL.md),
[Capability Matrix](../agent-collab/CAPABILITY_MATRIX.md), and
[Zero-Relay roadmap](../plans/2026-09-04-zero-relay-accelerator-roadmap.md)

## 1. Purpose and limits

Use this recipe to move accepted work through the critical path while using premium
reasoning only where it changes a high-value decision. It wraps existing work-order,
claim, routing, review, and acceptance rules. It creates no scheduler, model router,
claim authority, evaluator, pricing registry, or scoreboard.

Optimize accepted outcomes, not agent activity. Current evidence shows repeated
boundary repairs, unfinished production composition, human relay, and model-role
confusion. These are observed delivery risks. Faster delivery or lower model cost is
an inference to test; do not report a speedup or saving until the measurement below
supports it.

One dated example illustrates the measurement need: PR #242 CI recorded success on
2026-09-10 at 05:31:45Z, while the independent finding was published at 13:18:15Z,
7h46m30s later. Review start time and competing workload are unknown, so this is not
reviewer work time or measured waste. It is a reason to capture queue and review delay.

## 2. Current delivery sequence — 2026-09-15

This section replaces the old WO173-first operating queue. It applies the user's
leverage-first development direction; it does not grant source/runtime mutation,
reassign active claims, or accept an outstanding candidate. Use actual GitHub,
runtime and WO evidence at every dependency release, not this dated snapshot alone.

### Verified planning baseline, not live readiness

- A-Conductor remote main: `67744e98e538b000579bff4a45616d3a178a824b`;
  A-Wiki remote main: `3a4e0fba4676f0ba9425733933d5a217eb5cdd7c`.
- [Issue #214](https://github.com/aase7en/A-Wiki-Conductor/issues/214) is the active
  Zero-Relay coordination record. WO223 RE2-A is in bounded repair after independent
  rejection of `1d755b6d5de5ebf5e357c5348f2e1b2544641b09`. The
  [latest inspected checkpoint](https://github.com/aase7en/A-Wiki-Conductor/issues/214#issuecomment-5675435129)
  adds typed identity validation to the recovery/concurrency repair set.
- [PR #319](https://github.com/aase7en/A-Wiki-Conductor/pull/319) remains at
  `42221020c02c507decfb396ac8c3b9da54d523bc`; its previous green CI does not
  accept the later repair candidate. Re-pin a new exact SHA/review/CI before merge.
- WO226 / [PR #314](https://github.com/aase7en/A-Wiki-Conductor/pull/314) is merged.
  WO208 crash/effect evidence is
  [accepted](https://github.com/aase7en/A-Wiki-Conductor/issues/233#issuecomment-5649401039);
  reuse it without treating it as complete Phase-D production acceptance.
- Main's WO166-era CURRENT-WORK/handoff and some older roadmap tables are stale.
  WO229/its successor owns their fold; do not resume WO166 or overwrite WO223's
  continuity because an old summary says it is the frontier.

### Ordered outcomes

| Priority | Existing node / next outcome | Why first / acceptance gate |
|---|---|---|
| P0, current owner | WO223 RE2-A repair -> C1 acceptance -> WO205 Phase D -> full ZRA-2 | close automatic review/repair and durable lost-handoff recovery; forced failure repairs once, exact result survives restart, no duplicate model effect or foreign cleanup |
| P0, after ZRA-2 | WO227 / ZRA-3 production NEXT READY | accepted predecessor advances the correct eligible successor without human relay; unknown execution reconciles before retry |
| P0, after ZRA-3 | ZRA-4 bounded two-lane proof | physical worktree/scope aliases, two-coordinator race, restart, partial success and exact fan-in pass before raising concurrency |
| P0, independent release lane | WO096 and its owned resilience successors | retain installed exact-PID recovery, explicit Stop suppression and required soak/release acceptance; do not declare fleet readiness from source/CI alone |
| P1, preparation beside P0 | Brain skill/hook capability inventory + GE-0008 executor conformance/preflight | disjoint read-only or narrowly claimed fixtures may remove a named blocker; do not consume the critical writer's scope or budget |
| P1, gated integration | Brain binding/enforcement + thin Kilo adapter / existing Claude reuse | follow Sections 9–10 and GE-0008 predecessor gates; no new backend framework or brain authority |
| P1, after accepted ZRA-4 for broad expansion | ODP remaining gaps and Sunday Dev/Research operator MVP | use accepted orchestration packet, Graph Admission, ReviewBus and operator.v1; no requirement to finish all ODP features before a bounded read-only shell |
| P2 | Waste OCR migration, optional local AI, Teach Sunday | verified live baseline/corpus parity, permission and exact-payload approval, submit recovery, reviewed workflow/version and rollback |
| P3 | Broader Social/Finance/Office write actions, mobile/multi-device, larger fleets | explicit use-case, policy/recovery/release gates and measured accepted-throughput benefit |

This is an outcome order, not a second runtime DAG. A prepared document is not a
READY source lane. Do not reissue an existing WO under a new number. A serial
Kilo conformance/adapter slice may run after its GE-0008 predecessors if already
released and disjoint; only multi-lane mutation requires ZRA-4 acceptance. Broad
ODP/Fleet expansion still follows the Zero-Relay fence.

### Browser Wake proposal: explicit pending sequencing decision

[WO240 / Issue #320](https://github.com/aase7en/A-Wiki-Conductor/issues/320)
owns the browser-wake roadmap at candidate
`1fa4b880506eaf5d38331da6ba908d5adbd0383e`. It proposes a reverse path:
external executor completion -> durable Core event -> bound browser-AI
conversation -> untrusted structured proposal -> Core revalidation.

Its proposed insertion **after ZRA-3 but before broad ZRA-4/ODP expansion** differs
from the default ZRA-2 -> ZRA-3 -> ZRA-4 sequence above. It remains pending
independent review/adjudication; this runbook does not silently accept or reject
that insertion. Sol must reconcile the accepted WO240 outcome at the ZRA-3 exit
and record the chosen successor in the existing WO/Issue. Until then, retain the
accepted ZRA order; do not dispatch browser-wake production work. Research and
read-only UI fixtures may proceed independently without live browser/provider effects.

Browser wake is a transport capability, distinct from Core NEXT READY scheduling.
Neither a page message nor a browser model response grants execution authority.

Do not force an unproven macOS supervision route onto an already valid Windows path.
Choose a currently authorized and proven host for the production proof, while retaining
the cross-platform acceptance and hosted-CI requirements of the owning work order.

Tiny AEET-0 or defect fixtures may run beside the critical path only when they are
bounded, disjoint, and remove a specific repeated review. Do not place the entire
AEET roadmap ahead of Zero-Relay. Treat [WO171 / PR #244](https://github.com/aase7en/A-Wiki-Conductor/pull/244)
and [WO172 / PR #245](https://github.com/aase7en/A-Wiki-Conductor/pull/245) as pending
inputs until accepted on main.

Current evidence anchors are
[Issue #233 marathon findings](https://github.com/aase7en/A-Wiki-Conductor/issues/233#issuecomment-5619553261),
[the independent Windows finding](https://github.com/aase7en/A-Wiki-Conductor/pull/242#issuecomment-5619318241),
[its follow-up](https://github.com/aase7en/A-Wiki-Conductor/pull/242#issuecomment-5619862174),
and [AEET reuse/gap findings](https://github.com/aase7en/A-Wiki-Conductor/issues/233#issuecomment-5619490874).
They are evidence, not acceptance or authority to take another owner's lane.
A later `READY` packet is evidence of readiness only; it grants no source authority and
does not revoke or transfer an existing claim.

## 3. Start one delivery lane

1. Select the first dependency node whose prerequisites are satisfied.
2. Verify repository, remote, worktree, branch, HEAD, dirty-state ownership, live claim,
   and result destination. If any identity or ownership fact is unknown, stop mutation.
3. Use one current owner and one durable WO/task-packet pointer. Do not rewrite a long
   prompt from chat and do not create another task form.
4. Run the full repository entry sequence at every new session or scope. Within that
   continuing scope, re-pin only facts that can drift at later boundaries: HEAD, diff,
   claim/lease, provider readiness, authorization/admission, dependency state, and
   result identity.
5. Classify the risk tier and record a compact routing entry in the same WO/checkpoint.
   Reserve a qualified reviewer while shaping the WO so the frozen candidate is not
   left waiting for a particular named model.
6. For R2/R3 boundary changes, complete the first-pass matrix below, including supported
   platforms and exceptions. For R0/R1, use the existing tier checks and only affected rows.
7. Implement RED-first where behavior changes. Use the smallest reproducer during
   edits, then targeted and directly related verification after the batch.
8. Batch confirmed boundary defects into the allowed repair budget. The same material
   failure twice without new evidence triggers root-cause reset and adjudication.
9. Before freeze, run the adversarial boundary batch plus scope, diff, secret, static,
   encoding, and link checks that apply.
10. Freeze one exact candidate and produce one bounded evidence packet. Reuse it for
    review; do not make reviewers reconstruct evidence or rerun unchanged broad audits.
11. Send the frozen identity to a qualified independent reviewer. Run independent review
    and required CI concurrently against the same SHA when both are ready; acceptance
    waits for both, with no duplicate CI or early approval. The author cannot be the sole
    independent reviewer. Apply the risk-tier review budget and adjudicate blockers together.
12. Repair within budget, re-freeze, and focus rereview on changed trust/behavior
    boundaries plus prior blockers unless blast radius requires full rereview.
13. After review and the same-SHA CI both finish, run only any additional release proof
    required by the risk tier. The integrator accepts or rejects from the combined
    evidence, then performs the authorized merge/release.
14. Checkpoint the WO and shared continuity only at a meaningful boundary: claim,
    blocker, frozen candidate, acceptance, handoff, or session rollover.
15. Continue to the next READY node only after the current result is accepted and its
    dependency/ownership facts are re-pinned. No manual result copyback is required.

## 4. First-pass boundary matrix

For R2/R3 boundary changes, complete this in the existing task packet before implementation;
mark irrelevant rows `N/A` with a reason. R0/R1 uses existing tier checks plus only affected
rows. This matrix never lowers the truthful risk tier or adds a full ceremony to small edits.

| Boundary | Required question/evidence |
|---|---|
| Repository and ownership | exact repo/worktree/branch/base HEAD; clean or explained dirty state; one claim; allowed and forbidden paths |
| Authority and trust | who may frame, mutate, review, accept, merge, release, and access secrets; fail-closed conditions |
| Task/result identity | task, execution, provider/model, base/candidate SHA, schema, hashes, and destination bind end to end |
| Lifecycle and recovery | start, attach, timeout, cancellation, retry, duplicate, ambiguous outcome, and terminal transition behavior |
| Composition | production entrypoint reaches dispatch, supervised execution, ingestion, verification, and apply seams without a test-only shortcut |
| Data and limits | stdout/result/context bounds, encoding, malformed/extreme input, persistence, redaction, and no-secret proof |
| Platform | Windows/macOS/Linux behavior, supported host chosen for proof, explicit exceptions, and cross-platform CI expectation |
| Verification | RED reproducer, targeted/related tests, adversarial cases, exact-head review/CI, and post-main/live proof when required |

## 5. Route by role and evidence

The [Capability Matrix](../agent-collab/CAPABILITY_MATRIX.md#user-routing-preference--2026-09-15--wo241)
records the user's current operating preference: **Sol integrates; GLM-5.3 through
accepted Kilo/Claude CLI routes implements; Astra resolves exceptional high-value
uncertainty**. The CLI name never proves the selected model, provider, quota,
permission coverage or recovery capability. Reuse supported ZCode routes as
eligible alternatives, not a second authority.

| Work | First route | Escalate when |
|---|---|---|
| Git identity, search, hashes, formatting, tests, builds, schema checks | deterministic/native tools | a result needs architectural or trust judgment |
| Bounded lookup, implementation, test mechanics, debugging, and batched repair | a currently capable, READY, authorized, admitted, policy-valid workhorse with a bound result destination | scope becomes ambiguous, high blast radius, or the same root cause fails twice |
| R2/R3 candidate review | qualified independent reviewer, separate from the author and bound to exact SHA | trust/security ambiguity remains or reviewer capability is insufficient |
| Architecture, authority, dependency, cross-lane conflict, acceptance, merge, release | integrator | strongest qualified specialist is needed to resolve an unresolved decision |

GPT-6 Astra is an escalation candidate, not a hardcoded gate or automatic R3 choice.
R3 still requires integrator authority/failure-model framing before mutation and the
strongest qualified independent review available before acceptance. Escalate for
unresolved architecture/trust questions, large blast radius, or repeated same-cause
failure. After the decision is written into the packet, de-escalate implementation,
test, and repair mechanics to the lowest currently qualified route.

Do not encode permanent provider rankings or unverified prices. A provider/model name
does not prove capability, readiness, authorization, quota, admission, or ownership.
Quota exhaustion blocks or selects an authorized fallback; it never transfers a claim.

Record routing once per lane or material route change in the same WO/checkpoint:

```text
ROUTE: role=<role>; reason=<task need>; evidence=<capability/readiness/cost source+date>;
effort=<requested effort>; escalate=<trigger>; fallback=<authorized route or BLOCKED>
```

If price or usage is unavailable, record `UNKNOWN`, never zero. Do not add one routing
record for every tool call.

## 6. WIP and review discipline

Remain within the existing maximum of three mutable lanes plus one independent read-only
review lane. Begin with:

- one critical-path implementation lane;
- one disjoint fixture or composition slice only if it removes a named blocker;
- one independent reviewer for the frozen candidate.

Keep spare capacity for recovery or adjudication. A packet marked `COMPLETE` receives no
busy audit rerun. Reopen it only for new evidence, a new hypothesis, base drift, a repair,
or a risk-tier-required independent rerun.

## 7. Measure the next 10 accepted WOs

Use existing WO, Git, CI, review, and evidence timestamps. Compare 10 accepted WOs before
adoption with the next 10 accepted WOs after adoption. Missing data stays `UNKNOWN`; do
not infer it or build a new scoreboard service. AEET7 may consume the evidence later.

Capture per WO:

| Metric | Definition |
|---|---|
| READY-to-accept lead time | first authoritative `READY_FOR_CLAIM` to integrator acceptance |
| Queue/blocked/review delay | separately observed intervals; unknown start/end stays `UNKNOWN` |
| Astra participation | actual framing, implementation, review, repair, or acceptance actions; do not infer from ownership labels |
| Repair rounds | frozen-candidate repair/rereview cycles |
| CI runs | exact runs used before acceptance, distinguishing reruns and post-main proof |
| Manual relay count | human prompt/result copy actions per accepted external-agent task |
| Escaped defects | blocking defects found within a declared observation window after acceptance/integration |

Report medians and counts with sample size and missingness. This runbook promises no
2–3x gain. Keep it only if accepted lead time and Astra dependence improve without worse
escaped defects or safety incidents.

## 8. Stop and hand off

At each phase exit, record the frozen identity, evidence packet, review result, CI state,
remaining authority/platform/release gates, and exactly one next safe action. Do not mark
preview, fixture, state-machine, or review evidence as production acceptance.

Historical evidence only: at the 2026-09-10 [R5 freeze checkpoint](https://github.com/aase7en/A-Wiki-Conductor/issues/233#issuecomment-5620087669),
WO173 source mutation was complete and its claim released; [PR #246](https://github.com/aase7en/A-Wiki-Conductor/pull/246)
subsequently merged on 2026-09-10. Do not reopen its old queue. Section 2 supplies
the newer dated frontier. This runbook claims no source lane and lifts no provider,
platform, review, merge, or release gate.

## 9. A-Wiki as shared development infrastructure

Extend Phase 4 of [PROJECT-PLAN](../../PROJECT-PLAN.md) through the existing
[integration contract](../contracts/a-wiki-a-conductor-integration.md), not a new
brain implementation. The three slices below are planning labels, not reserved WOs.

| Slice | Reuse / work | Acceptance |
|---|---|---|
| 4A: discover and bind | BRAIN-ENTRY Index+Pull, skills-registry, existing task/policy references; select only relevant skills/context | record brain source commit, skill version/digest, applicable policy/verification and context budget in the existing task packet; stale/unknown facts visible |
| 4B: enforce and prove | canonical hook registry/runner and provider normalization, wrapped through the approved brain boundary | matrix distinguishes AVAILABLE, WIRED, ENFORCED and E2E_VERIFIED per runtime; real denied-operation probes prove hard gates cannot be bypassed |
| 4C: evidence to learning | existing EvidenceBundle, ReviewBus and privacy/provenance/promotion pipeline | accepted result produces a bounded reviewable lesson candidate; no raw secrets/private content or unreviewed policy rewrite |

4A inventory and bounded gap tests can run beside ZRA without taking its scope.
Broad integration follows the dependency fence; a gate necessary to make the active
ZRA path safe must be incorporated by its existing owner before acceptance, not deferred.

Start 4B with claim/scope, secret leakage, destructive Git and raw immutability;
add external-editor drift for userscript migration. Preserve hard/soft classification:
an advisory hook is not enforcement. Parent-process hooks do not automatically
intercept an external CLI's internal tools. Require verified native hooks or a
wrapper/sandbox that actually controls the operation; otherwise deny that mutable
capability. Skills in prompts alone do not establish enforcement.

[GE-0005](../adr/GE-0005-brain-bridge-access.md) keeps Graph Runtime access through
`python -m conductor` / the importable brain bridge; do not import brain internals,
read `.tmp` stores, or copy registry policy into Conductor. If skill/hook discovery
or execution needs an absent facade, prepare an A-Wiki-owned bridge extension under
a separate authorized claim. A-Wiki policy versions can be cached as provenance-bound
snapshots; do not make every local task depend on a fresh network read of the brain.

Use [A-Wiki PR #59](https://github.com/aase7en/A-Wiki/pull/59) and existing
WO171/AEET work as pending evidence/evaluation inputs for 4C; do not implement their
unaccepted phases implicitly or create another memory/evaluation roadmap.

## 10. Sunday-Family surfaces and upstream reuse

### Shared authority and first useful modules

Keep A-Wiki as knowledge/skill/policy owner and Core as durable execution authority.
Sunday-Family browser modules are clients and bounded browser executors. Reuse
`operator_protocol.py`, `operator_dispatch.py`, `operator_wire.py`, existing events,
job state and artifact services. Browser intent passes authentication, context and
admission checks; do not expose every internal claim/gate/execute action directly.

Prepare protocol compatibility, capability handshake, request deduplication,
event cursor/reconnect, task-bound approvals and bounded artifact access before
task submission. Evaluate Native Messaging versus authenticated loopback using the
WO240 threat model; neither transport choice nor an extension ID proves all trust.
This work does not reopen ADR-0001's generic MCP gateway by another name.

Development order for user modules:
1. **Sunday Dev + Inbox**: PR context -> one canonical review task -> evidence and
   decisions; read-only first so the tool helps build Conductor itself.
2. **Sunday Research**: selected page/text -> source URL/time/raw provenance ->
   reviewed A-Wiki ingestion; private material stays in approved private storage.
3. **Sunday Hospital / Waste OCR**: reconcile live Tampermonkey version and
   `USERSCRIPT_SYNC_OK`, freeze corpus, test staff/department/correction/fill parity,
   exact-payload approval, navigation and ambiguous-submit recovery; retain rollback.
4. **Teach Sunday**: recorder emits a reviewable versioned workflow; deterministic
   replay verifies outcomes. AI selector repair is a proposal, not permission to act.
5. Other Office/Social/Finance modules after concrete use-case and effect gates;
   autonomous trading is outside this initial scope.

### Reuse shortlist and intake gate

These are candidates from the 2026-09-15 source/document review, not accepted
dependencies or measured integration successes. Pin the exact commit/version and
license when a bounded proof-of-fit WO is claimed.

| Candidate | Intended reuse | Boundary |
|---|---|---|
| [WXT](https://github.com/wxt-dev/wxt) | TypeScript extension shell/build/shared modules | first framework proof-of-fit; target-browser/permission tests |
| [Obsidian Web Clipper](https://github.com/obsidianmd/obsidian-clipper) | capture/highlight/Markdown extraction patterns | preserve source/private-data policy; source license does not include branding assets |
| [Nanobrowser](https://github.com/nanobrowser/nanobrowser) | side-panel UX and bounded browser adapters | do not import its planner as another task/scheduler authority |
| [WebLLM](https://github.com/mlc-ai/web-llm) | optional browser-local inference | device/Thai/model-license/memory/worker-restart evaluation first |
| [Stagehand](https://github.com/browserbase/stagehand) | optional Core-side browser action/extraction/QA adapter | SDK, not a drop-in extension; pin current API/provider/browser requirements |
| [aipass-bridge](https://github.com/niawjunior/aipass-bridge) | browser-held-session/provider transport pattern | existing AIP roadmap, authentication/result-trust and service-authorization gates |
| [Automa](https://github.com/AutomaApp/automa) / [BrowserOS](https://github.com/browseros-ai/BrowserOS) | workflow/browser-agent use-case references | inspect exact AGPL/commercial/file-level license before copying; avoid wholesale product fork |

Intake output uses the existing WO: exact source/license, REUSE/WRAP/EXTEND rationale,
smallest component, owner, permissions/data flow, maintenance/update/rollback cost,
compatibility, fixture proof and residual risks. Start with a small shell + capture
proof; choose one browser executor after comparison, not every framework at once.

AiPASS already has an [integration roadmap](../plans/2026-09-02-aipass-provider-integration-roadmap.md).
The inspected upstream main was `5e19e78605f000f392e3fac5b5da6c5514468925`, newer than
that roadmap's reference. Refresh its security/source diff rather than duplicating
AIP work. Upstream documents unauthenticated loopback access; current official
[terms](https://www.aipass.go.th/term-and-cond-th) retain the automation authorization
gate. Keep live AiPASS optional/gated; it is not a prerequisite for Sunday release.

### Embedded AI and package boundary

Offer optional browser-local AI for bounded summarize/classify/draft work; route
heavy or durable work through accepted Core local/cloud providers. Show execution
location and material data egress; never silently fall back from local to cloud.
Core-offline local drafts may remain usable, but cannot claim canonical Core task
completion. Browser-local write actions still require their own accepted effect,
approval, recovery and privacy contract; standalone write automation is not enabled
by this plan.

Test WebLLM/model choices on Thai tasks, target hardware, download/storage cost,
latency, memory and browser lifecycle. As inspected on 2026-09-15, the
[Chrome Prompt API](https://developer.chrome.com/docs/ai/prompt-api) documents
en/ja/es/de/fr rather than Thai; recheck before selection and do not promise
universal local-Thai capability. Library and model-weight licenses are separate.

Use **Sunday-Family** as the umbrella brand. Start with a coherent **Sunday Work**
package (Dev/Research/Inbox); allow Hospital and unrelated domains to be separately
installed packages sharing SDK/protocol/UI/AI adapters. A single package remains
possible when its purpose and permissions are coherent; no store acceptance is
assumed. Evaluate the [single-purpose policy](https://developer.chrome.com/docs/webstore/program-policies/quality-guidelines)
and [MV3 remote-code rules](https://developer.chrome.com/docs/webstore/program-policies/mv3-requirements).
Bundle reviewed executable modules with releases; do not download arbitrary skill
code or a complex remote command interpreter and call it configuration.

## 11. Next-session handoff and measurement

Sol resumes through the normal entry chain, re-pins Issue #214/#317/#320, main,
current candidate, claims and runtime evidence, then selects the first accepted
dependency frontier. At this snapshot the next source action belongs to the
existing WO223 RE2-A owner, not a new parallel writer. Reuse prepared backend and
browser packets; never infer live CLI/model readiness from their presence.

Each worker gets one existing WO/task packet: exact identity, allowed/forbidden
scope, skill/policy refs, acceptance, verification, result destination and stop
conditions. Workers write bounded results; Sol reads them, verifies/folds evidence,
and continues. Prefer native tools, then qualified GLM; use Astra only under the
matrix's narrow escalation/return contract. Source changes restart exact-SHA review
where required. No repeated human `continue` between safe steps; real authority,
provider, ambiguous-effect and required-approval gates remain explicit stops.

Keep Section 7's before/after accepted-WO measurement; additionally track context
tokens/cost when observed, recovery time, duplicate effects and ownership violations.
For browser pilots track intent-to-accepted-task latency, provenance quality and
verified skill success. Do not claim speedup from agent count or number of skills.

This operating-plan update is discoverable through the existing Fast Execution
Protocol and Capability Matrix. Do not overwrite active global continuity or
PROJECT-PLAN/PROJECT-GRAPH claims to duplicate it. Their integrator-owned folds
should reference this plan and the accepted WO240 result when those scopes release.
