# Cost-First Delivery Runbook

Status: OPERATING RECIPE / applies existing authority
Owner: active work-order owner and GPT/integrator
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

## 2. Work the dependency path in this order

| Rank | Phase | Exit evidence |
|---:|---|---|
| 1 | Close WO173/R5 Windows harness repair through integrator acceptance | owner publishes a frozen exact candidate; Windows reproducer passes; targeted and related tests, scope/secret checks, independent exact-SHA review, and required CI are green; integrator acceptance and required post-main proof close the gate |
| 2 | Reconcile actual P0-B and authority gates, then prove the smallest ZRA-1 production composition | current main, claims, and accepted authority are pinned; one bounded task uses an authorized proven host through production dispatch, exact result ingestion, and change-apply seams; identity, admission, recovery, and no-secret evidence pass |
| 3 | ZRA-2 automatic one-repair loop | one forced review failure produces exactly one bounded repair, re-verifies the result, and returns a frozen candidate with no human result copyback |
| 4 | ZRA-3 accepted NEXT READY continuation | acceptance advances exactly one eligible dependency node; duplicate, timeout, or ambiguous execution fails closed without blind replay |
| 5 | ZRA-4 bounded parallelism | two or three disjoint READY lanes keep separate claims/worktrees/results; fan-in verifies exact identities and respects the existing WIP cap |

ZRA-2 is the first major throughput milestone because it removes the repeated
result-review-repair relay. ZRA-3 and ZRA-4 matter after that loop is accepted.

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

At the 2026-09-10 [R5 freeze checkpoint](https://github.com/aase7en/A-Wiki-Conductor/issues/233#issuecomment-5620087669),
WO173 source mutation is complete and its claim released; [PR #246](https://github.com/aase7en/A-Wiki-Conductor/pull/246)
awaits independent review and exact-head CI. The next safe action is integrator closure of
that candidate, then re-pin prerequisites for composition. This runbook claims no source
lane and lifts no P0-B, provider, platform, review, merge, or release gate.
