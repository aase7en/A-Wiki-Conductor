# JEV System One Acceleration Roadmap — 2026-09-22

Status: EXPERIMENTAL / SHADOW-FIRST / EVIDENCE-GATED
Authority issue: #484 / WO-P1-484
Parent architecture: Orchestration Decision Plane (ODP)
Classification: EXTEND, not a new control plane

## 1. Why this exists

TypeSafe Jev is a System One model for bounded structured judgments: Choice, Score and Noul. It does not replace GPT-5.6 Sol, GLM, Workers, deterministic tools, A-FastTask, TaskGraph, claims, review or completion authority.

The opportunity is narrower and potentially high leverage:

`use cheap/fast typed semantic judgments for easy bounded decisions -> escalate only difficult/uncertain/high-risk cases to frontier reasoning`.

The roadmap therefore asks one question:

> Can Jev remove a material share of semantic routing/triage/verification calls from frontier GPT/GLM paths without reducing accepted reliability?

Vendor benchmark claims are hypotheses only. A-Sunday adoption depends on project-local evidence.

## 2. Placement in A-Sunday Conductor

```text
actual state / deterministic evidence
              |
              v
        A-FastTask / ODP
              |
              v
   SemanticDecisionProvider
      /       |        \
deterministic Jev   frontier reasoning
      \       |        /
              v
       deterministic policy
              |
     route / escalate / review
              |
              v
    normal authority + verification
```

Rules:
- TypeSafe/Jev is an optional decision provider, never authority.
- A-FastTask remains canonical router/binder.
- ODP/Graph Admission owns enforceable routing/admission policy.
- deterministic facts are computed before model judgment;
- arithmetic, date comparison, counting, Git identity, claims, quotas and exact-SHA checks remain code/tool work;
- Jev is used only for bounded semantic judgments with an explicit answer space;
- unsupported/ambiguous/high-risk cases escalate.

## 3. Documentation basis

Primary TypeSafe docs reviewed for this evaluation include:
- Introduction and Quickstart;
- System One concepts;
- How to build with System One;
- State;
- Choice / Score / Noul primitives;
- Confidence;
- Models;
- HTTP API;
- Python and JavaScript SDK documentation;
- Coding Agents;
- Agent Skill;
- Jev 1.13 jaggedness;
- Cookbooks index and all 18 current cookbook recipes discovered through `https://docs.typesafe.ai/llms.txt` on 2026-09-22.

Important vendor-documented constraints:
- Jev is for structured decisions, not chat/code/text generation.
- math/counting/date ordering should remain in code.
- large irrelevant state reduces accuracy.
- adversarial state can steer outputs; state is not a security boundary.
- Jev can read literally and can struggle with multi-hop indirection.
- Choice and Noul answer different questions; do not assume arithmetic invariants between separate heads.
- English is the primary/best-supported language; Thai/domain usage requires separate local benchmarking.

## 4. Roadmap

### JEV-0 — documentation + threat model

Outcome:
- current docs inventory complete enough to design the experiment;
- limitations and authority boundary captured;
- exposed-key rule captured;
- no implementation dependency created.

Gate:
- COMPLETE for benchmark planning;
- documentation must be refreshed at live-provider admission time because model/pricing/limits can change.

### JEV-1 — shadow benchmark

Outcome:
- versioned benchmark schema;
- deterministic offline runner;
- fixture/fake provider;
- sanitized/public corpus;
- comparable latency/cost/quality report;
- GO / CONDITIONAL_GO / NO_GO.

No production routing.

Initial decision families:
1. task classification;
2. skill/capability suggestion;
3. failure classification;
4. review severity;
5. evidence relevance/support;
6. escalation decision.

### JEV-2 — provider-neutral semantic decision seam

Start only if JEV-1 is GO/CONDITIONAL_GO.

Target:
`SemanticDecisionProvider` interface with:
- deterministic/fake provider;
- Jev provider;
- optional frontier provider adapter;
- normalized answer/probability/confidence/usage/latency/error envelope.

This seam must not become provider authority or a second routing system.

### JEV-3 — A-FastTask advisory pilot

Modes:
1. `OFF`
2. `SHADOW` — record comparison only;
3. `ADVISORY` — recommendation visible to deterministic policy/integrator;
4. production eligibility remains forbidden until JEV-5.

First use case should be skill/capability suggestion because it is bounded and directly supported by TypeSafe cookbook evidence.

Second use case:
- failure taxonomy classification.

### JEV-4 — confidence cascade

Candidate flow:

```text
deterministic prefilter
       |
       v
      Jev
       |
  policy/threshold
   /          \
accept candidate   escalate
                     |
                GPT-5.6 / GLM
```

Tune thresholds using held-out data, not cookbook defaults.

Required comparison:
- quality;
- false automatic actions;
- escalation rate;
- p50/p95 latency;
- end-to-end cost;
- frontier-call avoidance.

### JEV-5 — production admission

Requires:
- stable provider-neutral seam;
- sanitized telemetry;
- timeout/rate-limit/overload circuit handling;
- deterministic fallback;
- security/privacy review;
- exact-SHA review/CI;
- rollback to Jev `OFF` without task-state migration;
- proven policy thresholds on held-out workload.

No provider output can grant mutation/claim/review/merge/completion authority.

### JEV-6 — Thai/domain pilots

Separate domain benchmark gates:
1. Pharmacy SKU candidate selection;
2. ENV operator-note classification;
3. Sunday Estate document classification;
4. optional AI-content quality/risk triage.

Never carry A-Sunday English thresholds into Thai domains without evidence.

### JEV-7 — scale/optimization

Only after production admission:
- batch parallel questions that share state;
- compact/retrieve state before Jev;
- two-stage shortlist/rerank patterns;
- caching only where replay semantics permit;
- per-decision telemetry and drift detection;
- model-version revalidation when `jev-latest` changes.

## 5. JEV-1 benchmark corpus

### Case shape

Every accepted case needs:
- stable case ID;
- decision family;
- sanitized state;
- question/primitives definition;
- allowed answer space;
- expected answer or expected policy disposition;
- truth/evidence provenance;
- risk class;
- whether abstention/escalation is acceptable;
- baseline route and version when measured.

Cases without defensible expected truth are excluded from accuracy calculations and may be used only for latency/shape diagnostics.

### Corpus strategy

Phase 1:
- synthetic/public/repository-safe cases only;
- derive taxonomies from accepted A-Sunday contracts where possible;
- no private operational payloads.

Phase 2:
- historical A-Sunday cases only after sanitization/provenance review.

Phase 3:
- Thai/domain datasets as separate pilots.

## 6. Metrics and decision gates

Required report:
- accuracy and confusion matrix by family;
- high-risk false automatic action rate;
- abstention/escalation;
- typed/schema failure;
- retries/provider errors;
- latency p50/p95;
- throughput;
- token usage;
- estimated cost per 1,000 eligible decisions;
- frontier-call avoidance under candidate cascade;
- results by model version and benchmark revision.

Proposed adoption gates:
- quality delta >= -2 percentage points vs accepted baseline;
- high-risk false-action rate <= baseline;
- schema/type failures = 0 on accepted corpus;
- p50 >=3x and p95 >=2x faster where a comparable semantic baseline exists;
- >=10x lower comparable cost;
- target >=60% eligible frontier-call avoidance;
- every injected provider failure reaches a safe fallback.

Any missing critical metric produces `INCONCLUSIVE`, not GO.

## 7. Benchmark result status

One of:
- `GO` — gates met, eligible for JEV-2;
- `CONDITIONAL_GO` — narrow families meet gates; limit scope to those families;
- `NO_GO` — material gate fails;
- `INCONCLUSIVE` — evidence insufficient.

A GO result is permission to propose the next bounded WO, not production admission.

## 8. Data/privacy and secrets

- Resolve `TYPESAFE_API_KEY` only from approved secret-safe binding.
- Never print/store the value or put it on a process command line.
- Treat the API key pasted into chat as exposed.
- Never send repository secrets, hospital data, pharmacy order data, estate/private documents, user identity data or arbitrary chat history in JEV-1.
- Store only sanitized benchmark inputs and safe metadata.
- Provider responses are untrusted semantic evidence.
- Add credential-shaped scanning to committed fixtures/results.

## 9. Failure injection

Offline harness must deterministically cover:
- HTTP/auth/rate-limit/overload/timeout classes without a real secret;
- malformed payload;
- missing answer;
- wrong answer type;
- unexpected model ID;
- retry exhaustion;
- low-confidence and contradictory judgments;
- policy threshold edge cases;
- safe fallback;
- result serialization without secret leakage.

## 10. Relationship to current roadmap

JEV-ACCEL is a child experimental track of ODP, not a new numbered project phase.

Mapping:
- JEV-1 informs ODP-2/4;
- JEV-2 implements the reusable semantic decision seam only after evidence;
- JEV-3/4 exercise capability routing/adjudication;
- JEV-5 shares ODP-7 observability and ODP-8 fault evidence;
- JEV-6 remains outside the A-Sunday control-plane critical path.

JEV work must not block LOCAL-USABLE-1 or active MSP scopes. Under the default global WIP limit it may use at most one mutable lane while two other mutable lanes are occupied.

## 11. Why shadow-first

Shadow mode yields evidence with minimal product risk:
- no routing side effects;
- no authority transfer;
- baseline and Jev see the same bounded case;
- thresholds can be tuned offline;
- vendor failure has no production blast radius;
- NO_GO leaves the architecture clean.

The success criterion is not reproducing a vendor headline. It is proving that A-Sunday can safely avoid expensive reasoning on a large fraction of bounded semantic decisions.

## 12. Next action

Finish the JEV-1 docs bootstrap, then implement the smallest offline benchmark harness and fixtures under the same WO after a fresh mutation/WIP gate. Live TypeSafe execution remains separately gated by credential safety and sanitized-payload policy.