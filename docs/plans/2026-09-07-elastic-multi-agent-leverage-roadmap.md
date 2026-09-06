# Elastic Multi-Agent Leverage Roadmap

Date: 2026-09-07
Status: SHAPING / NO IMPLEMENTATION AUTHORITY
Repository: `aase7en/A-Wiki-Conductor`
Baseline at creation: `origin/main@df5a25f1f9949e6938ea4bbcf0150515e6e5fa85` (PR #221 / ZRA-1 merged)

## Purpose

Evolve A-Sunday Conductor from a fixed small set of parallel lanes into a provider-neutral, asynchronous, conflict-aware **Elastic Multi-Agent execution fabric** that can use 1, 2, 4, 6, 8, 10+ agents when independent READY work actually exists.

This document does not authorize implementation or reorder the accepted Zero-Relay roadmap. It records the target architecture and acceptance principles so future sessions do not depend on chat memory.

## Existing foundations to reuse

Do not rebuild these authorities:

- `WO-P1-116` Production Worker Supply + Elastic Capacity — RELEASED.
- `WO-P1-120` Elastic Capacity Fencing + Recovery Hardening — RELEASED.
- PR #211 four-lane coordination SSoT — existing lane/ownership shaping; do not duplicate its mutable scope.
- Issue #216 / ZRA-4 bounded parallel Zero-Relay preflight — existing parallel execution/fan-in authority shaping.
- existing TaskGraph / ReadySet / scheduler / WorkerLease / provider admission / durable job / supervised execution / review / recovery primitives.
- ZRA-1 accepted production execution path from PR #221.

Classification for this roadmap: `REUSE -> WRAP -> EXTEND`; `NEW` only for a proven gap. No second scheduler, lease store, provider store, task store, review authority, recovery authority, or SSoT.

## Core architecture

```text
USER GOAL
   |
   v
Planning / Control Pool
   |
   v
Durable Task DAG
   |
   v
READY Frontier
   |
   +--> Capability Router
   |
   +--> Conflict / Ownership / Policy / Admission Gates
   |
   v
Elastic Heterogeneous Agent Pool
   |       |       |       |       |       |
  GPT     GLM    Claude  Gemini   Local   Tools ...
   |       |       |       |       |       |
   +-------+-------+-------+-------+-------+
                           |
                    Frozen Candidate
                           |
                  Independent Review
                     /            \
                  ACCEPT         REPAIR
                    |              |
                    v              +--> READY
             Incremental Fan-in
                    |
                    v
               NEXT READY
```

A-Sunday Conductor remains the **control / trust / authority plane**. External models are bounded workers, planners, reviewers, or specialists; they are not authority merely because of vendor or model identity.

## Non-negotiable concurrency rule

```text
1 MUTABLE HOTSPOT = 1 MUTATION OWNER
```

Parallelism is allowed across independent mutable scopes. The same hotspot may have multiple read-only reviewers/verifiers, but never multiple unsynchronized writers.

Examples:

- 10 independent safe scopes may permit up to 10 mutation lanes.
- 10 available agents but only 2 safe independent scopes means at most 2 mutation lanes; remaining capacity may review, test, research, or stay spare.
- equivalent physical worktrees or alias-equivalent write sets must be treated as the same conflict domain.

## Asynchronous DAG — no global barrier

The system must not wait for all lanes to finish before making progress.

If task D depends only on B:

```text
B ACCEPTED -> D READY
```

D may start even while unrelated C is still running.

Synchronization occurs only at real dependency or authority barriers, not at a global "all agents finished" barrier.

## Incremental fan-out / fan-in

- READY independent nodes may fan out immediately subject to lease/provider/policy/capacity gates.
- each lane freezes an exact candidate/result independently.
- independent review runs against a stable exact candidate.
- accepted independent outputs may merge/fold independently where graph semantics allow.
- a successor becomes READY only when its required predecessors reach accepted terminal state.
- partial batch success is preserved; UNKNOWN lanes are not blindly replayed and do not roll back unrelated successful lanes.

## Work stealing

A free agent may claim another independent READY task only after a fresh admission/ownership gate.

A worker in `REVIEW_WAIT`, `CI_WAIT`, or blocked on an unrelated dependency should not reserve mutation capacity unnecessarily when its claim can be safely released/frozen.

Work stealing must never bypass:

- task ownership;
- worktree/write-set conflict checks;
- WorkerLease;
- provider admission;
- capability/policy requirements;
- exact HEAD/task/result identity.

## Capability-first heterogeneous routing

Do not hard-code architecture such as `coding -> GLM` or `planning -> GPT`.

Route from task requirements to an **eligible capability profile**, then choose among currently authorized/ready providers/models.

Candidate dimensions include:

- task/role capabilities;
- long-horizon coding quality;
- architecture/reasoning quality;
- review/adversarial quality;
- multimodal/visual quality;
- Thai-language/Thai-in-image quality where relevant;
- research/retrieval speed;
- context capacity;
- tool/MCP/plugin availability;
- latency;
- cost;
- current provider capacity;
- recent first-review acceptance rate;
- repair-loop rate;
- deterministic tool reliability;
- observed unsupported-claim / hallucination rate;
- privacy/locality/policy constraints.

Capability scores must come from evidence/benchmark/accepted task history where practical, not permanent vendor stereotypes.

High-risk trust/authority decisions remain independently verified and are never delegated solely because a model has a high capability score.

## Elastic capacity policy

The target is not `LANES = 10`. Active parallelism is bounded by actual safe capacity.

Conceptually:

```text
safe_mutation_parallelism <= min(
  independent_READY_nodes,
  non_overlapping_mutable_scopes,
  eligible_worker_leases,
  provider_admission_capacity,
  policy_limit,
  verification/review_capacity
)
```

Reserve recovery capacity where required. Do not saturate every available provider/worker slot if doing so prevents recovery or creates an unbounded review queue.

## Frozen-candidate review barrier

A reviewer evaluates an immutable candidate/result identity, not a branch that continues changing under review.

Typical flow:

```text
CLAIM -> IMPLEMENT -> VERIFY -> FROZEN SHA/RESULT
      -> INDEPENDENT REVIEW
      -> ACCEPT or bounded REPAIR
```

The builder may return to the pool after a safe freeze/release boundary if durable state allows another worker to perform any later repair.

## Model/provider independence

The architecture must permit future combinations such as:

- GPT planner + GLM long-horizon implementer + Claude reviewer;
- Claude planner + Gemini fast research worker + GLM builder;
- GPT multimodal/visual specialist + local model classifier + deterministic verifier;
- any future MCP/plugin-capable provider satisfying the same contracts.

Provider substitution is never silent. A route is eligible only when required facts equivalent to the existing fail-closed contract are true:

`CAPABLE ∧ READY ∧ AUTHORIZED ∧ ADMITTED ∧ POLICY_OK ∧ RESULT_DESTINATION_BOUND`

UNKNOWN blocks or routes to an explicitly authorized fallback; it never means "try another model and hope".

## Scale progression

Scaling is evidence-gated, not a one-step jump.

### Stage 0 — external reuse audit

Study current upstream orchestration projects before adding new primitives. Produce `REUSE / WRAP / EXTEND / REJECT / NEW` decisions with license/provenance and trust-boundary analysis.

### Stage 1 — bounded parallel baseline

Use existing ZRA-4 scope: 2–3 independent READY lanes with exact conflict/admission/fan-in proof.

### Stage 2 — dynamic 4–6 lanes

Only after Stage 1 acceptance. Add adaptive capacity and demonstrate that accepted throughput improves without increasing duplicate/ownership violations.

### Stage 3 — dynamic 8 lanes

Require restart/concurrency/partial-failure/CI-review-backpressure tests plus measured benefit over Stage 2.

### Stage 4 — dynamic 10+ lanes

Only if READY frontier, provider capacity, conflict topology, review capacity, and measured accepted throughput justify it. No architectural constant should require exactly ten workers.

This scale progression must not silently reorder the authoritative ZRA-0 -> ZRA-1 -> ZRA-2 -> ZRA-3 -> ZRA-4 -> ZRA-5 dependency chain. Shaping/research may proceed read-only; production mutation obeys current roadmap/claims.

## SSoT / state projection requirement

The fabric must operate from canonical actual state, not session memory or manually synchronized Markdown.

Desired direction:

```text
Git / GitHub / runtime / lease / provider / durable job state
                    |
                    v
          canonical actual-state projection
                    |
        +-----------+-----------+
        v                       v
 operator/read model      drift detection
                                |
                         reconcile before
                         dependent mutation
```

Markdown remains durable human-readable continuity, not a competing runtime database.

## Test-integrity requirement

A lesson from WO158/PR221 is binding:

```text
CANONICAL AUTHORITY -> REAL RECORD -> PRODUCTION CONSUMER
```

Trust-boundary tests must include records created by the real canonical store/broker where feasible. Hand-written mocks alone are insufficient if they can represent impossible production states.

## Required failure semantics

- transport failure != execution failure;
- UNKNOWN external effect -> reconcile, never blind replay;
- no broad process kill;
- no duplicate execution authority;
- no global batch rollback for independent successful lanes;
- no implicit ownership release from elapsed time alone;
- provider/capacity ambiguity remains fail-closed;
- stale HEAD/lease/provider-generation/result identity blocks acceptance.

## Performance metrics

Optimize **accepted throughput**, not raw agent count.

Track at least:

- accepted work / hour;
- first-review pass rate;
- repair loops / accepted task;
- human relay actions / accepted external-agent task;
- review latency;
- queue wait time;
- lane utilization;
- provider utilization;
- conflict rejection rate;
- duplicate execution count;
- blind replay count;
- escaped blocking defect rate;
- cost / accepted task;
- median and p95 task lead time.

A higher lane count is rejected if coordination/review overhead makes accepted throughput worse.

## Acceptance vision

The long-term architecture is accepted only when a user can submit a goal and A-Sunday Conductor can safely:

1. decompose it into durable dependency-aware work;
2. discover the READY frontier;
3. route each independent task to the best eligible currently authorized agent/tool;
4. execute multiple non-conflicting lanes asynchronously;
5. freeze and independently verify exact results;
6. repair bounded failures without human prompt/result relay;
7. incrementally release successors as dependencies accept;
8. recover across restart/transport ambiguity without duplicate external effects;
9. scale active concurrency up or down from evidence rather than a fixed lane count;
10. leave durable SSoT/evidence so a new session can resume with zero chat history.

## Immediate next design action

Do not implement a new orchestration subsystem from this document.

First complete the companion upstream reuse audit, then map its findings against the already-accepted WO116/WO120 primitives and Issue #216 ZRA-4 design. Any future implementation requires a fresh work order, exact-main re-pin, ownership gate, RED-first acceptance criteria, and independent exact-SHA review.
