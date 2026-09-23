# JEV semantic fast path — A-Faster reference

Status: advisory routing contract for JEV-3A. This reference does not grant
provider, task, claim, mutation, review, merge, completion, or SSoT authority.

## Purpose

Use a provider-neutral semantic decision seam to remove narrow classification
and triage work from frontier GPT/GLM paths when project-local benchmark evidence
supports it. A-FastTask remains the canonical router/binder; A-Faster remains an
acceleration overlay; deterministic policy remains authoritative.

The fast path is:

```text
deterministic facts
      |
      v
JEV-eligible semantic question?
   /               \
 no                 yes
 |                   |
frontier/default   SemanticDecisionProvider
                     |
              validate normalized evidence
                     |
               deterministic policy
                /             \
        advisory candidate     escalate
                |                |
                v                v
          A-Faster route      GPT/GLM
```

## Deterministic-first boundary

Never send work to a semantic provider to determine facts that tools/code already
own. Resolve these before semantic assessment:

- repository/worktree/branch/HEAD/dirty identity;
- task/claim/lease/ownership and mutable-scope overlap;
- WIP occupancy and exact lane binding;
- quota/readiness/authentication state;
- exact-SHA ancestry/diff/CI status;
- arithmetic, counting, date/time comparison, schema validation;
- security/secret policy and permission/authorization facts.

Semantic provider output is evidence only and cannot override any of these facts.

## Initial eligible decision families

Project-local JEV-1 live evidence supports advisory use for:

1. `task_classification`
2. `skill_suggestion`
3. `failure_classification`
4. `evidence_relevance`
5. `escalation_decision`

`review_severity` remains **frontier-only** until a later held-out benchmark
proves a separate admission gate. Authority, security, ownership, mutation,
merge, completion and acceptance decisions are never JEV-authoritative families.

## Modes

### OFF

Do not call a semantic provider. Continue with the existing deterministic /
frontier routing path.

### SHADOW

Call the provider only after normal deterministic admission. Record normalized
semantic evidence for comparison. The result MUST NOT change routing, WIP,
ownership, mutation, review, merge or completion behavior.

### ADVISORY

Expose a validated provider recommendation to the deterministic policy/integrator.
It may reduce unnecessary frontier classification work, but the surrounding lane
and existing A-FastTask/A-Faster gates remain authoritative.

JEV-5 production admission is required before adding any mode with automatic
product consequence.

## Advisory eligibility gate

A semantic provider may be consulted only when all are true:

- decision family is allowlisted;
- state is bounded, sanitized and contains no secrets/private operational payload;
- answer space/rubric is explicit and typed;
- provider route/model is admitted for this semantic service;
- surrounding task/lane already passed its normal authority and collision gates;
- the call is replay-safe or its duplicate effect is evidence-only;
- failure has a deterministic frontier fallback.

No separate mutable or review WIP slot is created for a semantic call. The
surrounding admitted engineering lane remains the owner.

## Evidence validation

Consume only the normalized provider-neutral evidence contract. Fail closed when
any of these occurs:

- provider/transport error;
- missing or mismatched primitive;
- malformed answer;
- non-finite score/probability/latency/cost;
- probability/confidence outside the accepted range;
- unexpected model/provider identity where pinned identity is required;
- missing required answer-space probability data;
- high-risk uncertainty;
- low confidence below the family-specific validated threshold;
- policy cannot prove eligibility.

Failure disposition is `ESCALATE`, not blind retry.

## Routing examples

### Task classification

Use semantic evidence to distinguish a bounded task family after Git/task facts
are known. The result may help choose a workflow or executor class, but does not
create a claim or mutation authority.

### Skill suggestion

Use semantic evidence to shortlist an existing skill/capability. The selected
skill still performs its own trigger/authority checks.

### Failure classification

Use semantic evidence to suggest a typed failure family. Runtime/log facts and
the retry taxonomy remain authoritative. A transport failure never proves
execution failure.

### Evidence relevance

Use semantic evidence to prioritize which already-available evidence deserves
frontier attention. It cannot mark a candidate accepted.

### Escalation decision

Use semantic evidence as a low-cost signal for whether frontier reasoning is
likely useful. Deterministic R3/security/authority rules always force escalation
regardless of semantic confidence.

## GPT / GLM responsibilities after the fast path

- GPT-5.6 Sol: architecture, DAG, trust/security boundary, ownership conflict,
  integration, difficult defect adjudication, exact-SHA acceptance, merge/release.
- GLM-5.3 MAX: bounded R2/R3 implementation, repair, tests and required qualified
  independent reviews when its route is admitted.
- GLM-5.3-Flash: bounded read-only reconnaissance/shaping where policy permits.
- deterministic tools/tests/CI: verification authority.

Semantic evidence is used to avoid wasting frontier reasoning on easy bounded
classification, not to replace engineering reasoning.

## Telemetry

Record only safe normalized fields needed to evaluate routing quality:

- decision family;
- provider/model version;
- mode;
- validated answer/disposition;
- confidence/probability summary where allowed;
- latency and safe token/cost usage;
- escalation/fallback reason;
- semantic failure type.

Never record plaintext credentials, auth headers, private payloads, unrestricted
state text, session/share URLs, or hidden reasoning.

## Retry and recovery

Semantic calls are ordinary provider executions for liveness/retry purposes:

- unambiguous provider rejection/error may use the existing bounded retry policy;
- ambiguous transport outcome must be reconciled before replay;
- repeated material failure without new evidence enters root-cause mode;
- provider unavailable => use deterministic/frontier fallback without changing
  the underlying Work Order/claim/scope.

## Roadmap relationship

- JEV-2 supplies the provider-neutral `SemanticDecisionProvider` seam.
- JEV-3 uses this reference for OFF/SHADOW/ADVISORY routing.
- JEV-4 validates confidence/fallback cascades on held-out workload.
- JEV-5 is required for production admission and rollback/fault evidence.
- ODP Graph Admission remains the enforceable policy boundary.
