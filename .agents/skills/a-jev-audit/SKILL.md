---
name: a-jev-audit
description: Evidence-based suitability audit for using the accepted TypeSafe-JEV semantic seam on one bounded question. Use before proposing JEV for skill suggestion, task/failure classification, evidence relevance, or escalation triage. Does not call a provider or grant task, claim, quota, routing, mutation, review, merge, or completion authority.
---

# A-JEV-Audit — bounded semantic suitability review

This skill answers one question: **is there evidence that an already-authorized
bounded semantic question benefits from the accepted JEV seam, and in which
currently accepted mode?** It does not dispatch JEV, select or create work,
change lane/WIP/quota state, or replace the deterministic A-FastTask and
A-Faster gates.

## Reuse and authority

- Reuse the family list, modes, eligibility, evidence validation, retry
  disposition, and telemetry contract in
  `../a-faster/references/jev-semantic-fast-path.md` and the existing
  `SemanticDecisionProvider` seam. Do not create another provider/router,
  task/claim store, scheduler, or decision authority.
- Read `docs/work-orders/WO-P1-508-jev4-heldout-confidence-cascade.md` and the
  current accepted JEV work order/issue for live mode and evidence status.
  Historical audit prose is not current admission proof.
- JEV is a System-One semantic adviser only. Deterministic tools own repository,
  task/claim, worktree/HEAD, scope, WIP, quota/readiness, security, arithmetic,
  and review facts. JEV output cannot authorize actions or override those facts.
- This audit is read-only and makes no provider call. A recommendation never
  substitutes for the separate per-invocation provider, credential, claim,
  hook/preflight, and mutation gates.

## Audit procedure

1. **State the remaining semantic uncertainty.** If a deterministic rule,
   repository/tool fact, exact comparison, security decision, or authority
   check can answer it, return `NO_FIT` for JEV.
2. **Name one allowlisted family and primitive.** Confirm it in the accepted
   JEV reference and current work order. `review_severity`, permission,
   ownership, claim, mutation, security, merge, and completion decisions are
   not JEV-authoritative families.
3. **Pin the mode from current durable evidence.** Distinguish `OFF`,
   `SHADOW`, and `ADVISORY`. A candidate allowlist, responsive service, skill
   mention, or old benchmark does not prove an effective live mode. If current
   mode/admission is missing or stale, do not recommend a live call.
4. **Classify and minimize the payload.** Record data class, redactions, and
   why each field is needed. Never send API keys, credentials, cookies, private
   customer/person data, unrestricted environment, raw logs, hidden reasoning,
   or irrelevant repository content. If the question cannot be answered from a
   safe minimal payload, return `NO_FIT`.
5. **Check evaluation evidence.** Use the deterministic baseline and a
   disjoint held-out set; record case count, split provenance, family-level
   errors, false-action risk, confidence/calibration, and fallback behavior.
   Tuning cases are not held-out evidence. Vendor benchmarks are not project
   acceptance evidence.
6. **Estimate the practical benefit.** Compare measured latency and cost with
   the baseline, including failures, escalations, and fallback. Do not claim
   savings from estimates or a fixture whose measurements are absent.
7. **Keep route gates separate.** Record TypeSafe/JEV mode, credential-rotation
   proof, route health, and freshness independently from GLM/CoinTH quota and
   Windows/Mac/device availability. For a GLM fallback, follow
   `docs/runbooks/cointh-glm-quota.md`: use its approved secret-safe resolver
   and `GET https://cointh.com/glm/api/quota` with `x-api-key`; preserve the
   five-hour tuple and classify a missing, stale, malformed, or
   provenance-free tuple as `UNKNOWN`. `window_source=stale` is not exhaustion
   and does not prove availability. Check upstream readiness separately.
   This skill and the lifecycle hook must never read or print the key.
8. **Choose exactly one audit disposition** from the rubric below, cite the
   evidence and its observation time, and name the deterministic fallback and
   final decision owner.

## Disposition rubric

| Disposition | Use when | Operational meaning |
|---|---|---|
| `FIT` | A supported family has a bounded semantic gap; sanitized input, current accepted mode/route, held-out evidence, useful measured benefit, confidence/error policy, and deterministic fallback all pass. | Recommend the named accepted mode for a separate preflight decision. This label does not itself authorize a call. |
| `SHADOW_ONLY` | The family is a plausible semantic fit, but production/advisory admission, credential rotation, evaluation strength, or route freshness is not proven; or observed evidence supports comparison only. | Keep output non-authoritative. Use offline fixtures when live admission is unavailable; live SHADOW still requires its own credential and provider gates. |
| `NO_FIT` | The question is deterministic/tool-owned, outside the allowlist, authority/security-sensitive, privacy-incompatible, or has no meaningful semantic benefit over the baseline. | Do not use JEV for this question; use the deterministic/frontier path. |
| `INSUFFICIENT_EVIDENCE` | Required facts such as family/mode, safe payload, held-out results, baseline, or measured benefit are missing, contradictory, or stale and no narrower SHADOW conclusion is supported. | Make no JEV recommendation. Name the smallest evidence gap; do not invent a provider call to fill it. |

`UNKNOWN` is not `AVAILABLE`, `EXHAUSTED`, `THROTTLED`, or proof that a machine
is offline. Device availability, execution liveness, JEV readiness, and GLM
quota are separate observations. An unavailable Windows surface blocks work
that requires that surface only; continue another already-authorized route when
its own task/claim/scope, collision, WIP, provider, and worktree gates pass.
A stale execution pulse requires recovery of process/session, result, Git and
claim evidence; it never grants cancellation, takeover, or duplicate dispatch.

## Credential and provider safety

- The TypeSafe credential previously exposed in chat remains unsafe until an
  authoritative rotation proof is recorded under the live JEV work order.
  Presence in an approved resolver is not rotation proof. While the gate says
  `LIVE_JEV_ALLOWED=NO`, return no live `FIT`; use `SHADOW_ONLY` only when the
  offline/accepted shadow evidence supports it, otherwise
  `INSUFFICIENT_EVIDENCE`.
- CoinTH proxy quota is only GLM account evidence, not TypeSafe-JEV quota or
  TypeSafe readiness. Positive numeric counters with stale provenance remain
  `UNKNOWN`; do not call that exhausted, and do not use it to admit GLM.
- A Windows machine or Worker becoming unavailable does not prove GLM quota,
  JEV health, or task termination. Recover existing delegated execution first;
  then route only to an already-authorized available surface. Never wait for an
  unrelated device when independent SAFE_READY work has a valid route.
- Provider errors, malformed output, low confidence, stale evidence, or
  unsupported mode fall back to deterministic/frontier handling. No blind
  retry, mode promotion, or model substitution.

## Required audit record

Return this compact record for one question:

```text
JEV_AUDIT_STATUS: FIT | SHADOW_ONLY | NO_FIT | INSUFFICIENT_EVIDENCE
QUESTION / TASK_REF:
FAMILY / PRIMITIVE:
CURRENT_ACCEPTED_MODE + EVIDENCE_REF + OBSERVED_AT:
PAYLOAD_CLASS / REQUIRED_FIELDS / REDACTIONS:
HELD_OUT_EVIDENCE: dataset + disjoint split + n + family errors
BASELINE / MEASURED_BENEFIT: accuracy-risk + latency + cost (or UNKNOWN)
ROUTE_GATES: JEV credential rotation / JEV route / GLM proxy quota / GLM upstream / device
FAILURE_AND_CONFIDENCE_POLICY:
DETERMINISTIC_FALLBACK:
FINAL_DECISION_OWNER:
NEXT_EVIDENCE_OR_ACTION:
```

Keep missing values `UNKNOWN`; cite durable evidence rather than copying
secrets or private payloads. The final owner is the existing deterministic
policy/integrator, never JEV.
