# WO-P1-484 — JEV-1 shadow decision benchmark

Status: ACTIVE / SHADOW_ONLY / NO_PRODUCTION_ROUTING
Issue: #484
Task topology: CONTROL_PLANE_ONLY
Risk: R3 for any live external-provider/API/credential use; offline/docs-only benchmark slices may execute under lower local risk but remain non-authoritative.
Reuse classification: EXTEND existing ODP/A-FastTask provider-neutral decision architecture.

## Bound lane

- Authority repo: `A:\GitHub\A-Wiki-Conductor`
- Execution repo: same repo for JEV-1 benchmark-only code/docs
- Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo484-jev1`
- Branch: `docs/wo-p1-484-jev1-shadow-benchmark`
- Base/current at claim: `1bc617687dd931c537c569cdfa9d031b7a61b974`
- Owner/integrator: GPT-5.6 Sol
- Claim: Issue #484 comment #5779728199
- Global WIP at claim: #480 mutable + #482 mutable + #484 mutable = 3; MSP-3 shaping is read-only.

## Goal

Measure whether TypeSafe Jev/System One can remove a large fraction of narrow semantic decisions from frontier GPT/GLM paths while preserving A-Sunday Conductor authority, safety and evidence rules.

JEV-1 is a benchmark and shadow-evaluation slice. It does not authorize Jev to route, claim, mutate, merge, accept or complete work.

## Existing architecture reused

JEV-1 extends the existing Orchestration Decision Plane (ODP), especially the future decision-provider seam (ODP-2), capability-first candidate resolution (ODP-4), observability (ODP-7) and deterministic/fault E2E (ODP-8).

Canonical authority remains:

`MODEL/PROVIDER PROPOSES -> DETERMINISTIC POLICY/TOOLS VERIFY -> DURABLE STATE REMEMBERS`

Do not introduce a second:
- scheduler;
- task graph/store;
- claim/lease authority;
- provider registry/authority;
- review lifecycle;
- completion authority;
- long-term memory/SSoT.

## Phase A scope — benchmark contract + offline harness

1. Capture the JEV acceleration roadmap and threat/failure model.
2. Define a versioned benchmark-case schema and result schema.
3. Implement a deterministic offline benchmark runner with fixture/fake providers first.
4. Cover six initial decision families:
   - task classification;
   - skill/capability suggestion;
   - failure classification;
   - review severity;
   - evidence relevance/support;
   - escalation decision.
5. Measure accuracy, high-risk false action, abstention/escalation, p50/p95 latency, throughput, cost, retries/errors and typed/schema failures.
6. Preserve exact provider/model/version/usage metadata in benchmark results without storing credentials.
7. Add live Jev transport only behind the benchmark provider seam and only after the credential gate below passes.
8. Produce a GO / CONDITIONAL_GO / NO_GO report. No benchmark result directly changes production routing.

## Phase B — live Jev shadow gate

Live TypeSafe calls are permitted only when all are true:
- `TYPESAFE_API_KEY` resolves from an approved secret-safe binding;
- the credential is not known-compromised;
- the key value is never printed, persisted, passed in a visible command line, or committed;
- benchmark payloads are synthetic/public/sanitized only;
- no hospital, pharmacy, estate, personal, credential, or other private payload is sent;
- model ID and pricing assumptions are recorded with evidence date;
- transport retries are bounded and rate-limit/overload errors are typed.

The key previously pasted into chat is treated as exposed and must not be used as acceptance evidence.

## Benchmark design

### Baselines

At minimum compare:
1. deterministic heuristic/rule baseline when applicable;
2. current frontier semantic path (GPT/GLM) when a reproducible baseline exists;
3. Jev;
4. fixture/fake provider for harness determinism.

Do not invent a GPT/GLM baseline where no repeatable historical measurement exists; label it `NOT_MEASURED`.

### Metrics

Required:
- total cases;
- eligible cases;
- exact/categorical accuracy;
- high-risk false-action count/rate;
- abstention or escalation rate;
- schema/type failures;
- provider/transport errors;
- retries;
- p50 and p95 wall latency;
- throughput;
- input/output tokens where available;
- estimated cost per 1,000 eligible decisions;
- frontier-call avoidance rate under the candidate cascade policy.

### Proposed GO gates

These are A-Sunday evaluation gates, not TypeSafe guarantees:
- quality delta vs accepted baseline >= -2 percentage points;
- high-risk false-action rate no worse than baseline;
- typed/schema failures = 0 on accepted benchmark corpus;
- p50 latency >= 3x faster and p95 >= 2x faster than current semantic baseline when baseline exists;
- cost >= 10x lower for eligible semantic decisions when comparable cost evidence exists;
- target >= 60% of eligible decisions can avoid frontier GPT/GLM escalation without quality-gate regression;
- deterministic fallback succeeds for every injected Jev transport/provider failure.

If evidence is missing, result is `INCONCLUSIVE`, not GO.

## Initial cascade hypothesis

```text
deterministic facts/rules
        |
        v
bounded semantic decision
        |
        +--> Jev shadow assessment
                    |
               policy gate
              /           \
      eligible/high confidence   hard/uncertain/high risk
              |                         |
          candidate route          GPT-5.6 / GLM
```

Jev confidence/probability is input to policy only. It never overrides authority, ownership, exact-SHA, secret, mutation, review or completion gates.

## Failure/threat model

Must test:
- malformed response;
- missing answer;
- unexpected model/version;
- rate limit;
- provider overload;
- timeout/network error;
- retry exhaustion;
- contradictory semantic heads;
- low-confidence/ambiguous result;
- adversarial state text;
- irrelevant-context degradation;
- numeric/date question incorrectly routed to Jev;
- secret-shaped payload rejection/redaction;
- benchmark result attempting to imply production authority;
- provider unavailable -> safe deterministic/frontier fallback.

## Allowed initial files

- `PROJECT-PLAN.md` — bounded ODP/JEV pointer only.
- `docs/plans/2026-09-22-jev-system-one-acceleration-roadmap.md`
- `docs/work-orders/WO-P1-484-jev1-shadow-decision-benchmark.md`
- future offline harness/tests only after the post-bootstrap mutation gate is re-run and scope is frozen.

## Forbidden

- No production A-FastTask routing behavior change.
- No `src/a_conductor/**` mutation in the docs bootstrap slice.
- No mutation of #480/#482 scopes.
- No `CURRENT-WORK.md`, `handoff.md`, or `COLLAB.md` mutation from this lane while those remain shared hotspots.
- No plaintext API keys/tokens/cookies or secret-bearing command lines/logs.
- No private user/project payload in TypeSafe requests.
- No automatic model/provider substitution.
- No claim/mutation/merge/acceptance/completion authority from Jev output.

## Verification — docs bootstrap

- exact changed-file allowlist;
- `git diff --check`;
- UTF-8 decode and U+FFFD check;
- added-line credential-shaped scan;
- no source/test/runtime mutation;
- branch/worktree/HEAD identity check;
- remote issue/claim pointer present.

## Checkpoint

- [2026-09-22] User authorized execution of JEV-1.
- [2026-09-22] Recovered actual runtime/WIP: #480 and #482 have live mutable GLM executions; MSP-3 shaping is read-only. One mutable WIP slot was available.
- [2026-09-22] Issue #484 created; isolated worktree/branch created from then-current `origin/main@1bc617687dd931c537c569cdfa9d031b7a61b974`; claim comment recorded.
- [2026-09-22] Approved private global env file contains a `TYPESAFE_API_KEY` binding, but rotation status is not proven by presence alone. Live Jev calls remain gated until credential safety is established without exposing the value.

## Exact next safe action

Complete this docs-only bootstrap, run deterministic docs checks, freeze/commit/push/open the bootstrap PR, then re-run actual-state/WIP/ownership gates before creating the offline benchmark harness slice.