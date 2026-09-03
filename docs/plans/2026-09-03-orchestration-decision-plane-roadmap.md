# Orchestration Decision Plane Roadmap — 2026-09-03

Status: APPROVED ROADMAP CAPTURE / IMPLEMENTATION REQUIRES SEPARATE CLAIMS
Planning work order: `WO-P1-149`
Research basis: `docs/research/fable-orchestrator-adoption-2026-09-03.md`
Classification: `REUSE + WRAP + EXTEND`

## 1. Outcome

Make A-Sunday Conductor better at choosing **who should think, who should implement, what can run in parallel, and when evidence requires replanning** without creating a second orchestration universe.

Target loop:

```text
GOAL / EXECUTION REQUEST
        |
        v
A-Wiki policy + capability intent
        |
        v
ORCHESTRATION PACKET
        |
        v
PLANNER / ADJUDICATOR
proposal only; no workspace authority
        |
        v
GRAPH ADMISSION
        |
        v
EXISTING TASK GRAPH + ROUTER + SCHEDULER
        |
   READY frontier
   /     |      \
worker worker worker
   \     |      /
        v
EVIDENCE + VERIFY
        |
        +--> independent review when required
        |
        +--> bounded adjudication / repair / continue
        |
        v
COMPLETE / BLOCKED / RECOVERY_NEEDED
```

## 2. Authority boundary

This roadmap does **not** make A-Conductor the owner of high-level orchestration policy.

Reuse the existing split:
- **A-Wiki** — canonical capability intent, high-level orchestration intelligence, cost/model policy, reusable procedures, work-order/claim conventions, review policy.
- **A-Conductor** — durable execution state, TaskGraph validation/persistence, runtime/provider eligibility, worker scheduling, repository/runtime safety, evidence, recovery, operator state.
- **Decision provider** — proposes graph/next-step decisions from an explicit packet; no direct mutation authority.
- **Worker** — executes one bounded admitted task contract.
- **Independent reviewer** — reviews actual artifact/evidence under existing ReviewBus/review contracts.

Do not add a second:
- planner SSoT;
- task graph store;
- scheduler;
- provider registry;
- work-order/claim system;
- review lifecycle;
- long-term memory system.

## 3. Core design rules

### 3.1 Role first, model second

Canonical task semantics use role/capability requirements, not permanent vendor/model names.

Reuse A-Wiki routing roles where applicable:
- `deterministic-executor`
- `strong-reasoner`
- `strongest-independent`

Provider/model resolution occurs only after eligibility:

`CAPABLE ∧ READY ∧ AUTHORIZED ∧ ADMITTED ∧ POLICY_OK`

Eligible candidates may then be ranked using observed:
- execution durability / resume support;
- reliability / recent failure history;
- cost / quota headroom;
- latency / throughput;
- context fit;
- task-relevant benchmark/evidence freshness.

Unknown facts remain unknown.

### 3.2 Planner output is untrusted proposal data

No decision provider may directly become mutation authority by returning a graph.

Every proposal passes Graph Admission before dispatch.

### 3.3 Compact packets, not chat replay

Decision providers should receive bounded structured facts instead of whole-session transcripts whenever possible.

### 3.4 Evidence drives the next round

A worker saying `done` is not completion. Adjudication consumes verified outcomes, not worker confidence.

### 3.5 Budget every loop

Every task carries explicit limits for:
- planner/adjudication rounds;
- repair/retry attempts;
- parallelism;
- premium cost/quota where applicable;
- no-progress repetitions.

Proposed initial default: maximum **3 decision/adjudication rounds** per task unless policy or the user deliberately raises it.

### 3.6 Transport and execution remain separate

Preserve:

`TRANSPORT FAILURE != EXECUTION FAILURE`

A lost planner/worker transport cannot justify blind replay of an execution with unknown completion state.

## 4. Orchestration Packet v1 — target projection

Build on existing `ExecutionRequest`, TaskGraph, provider/runtime observations, and evidence. Do not create another durable task authority.

Minimum fields/semantics:
- request/task/graph identity;
- objective and acceptance criteria;
- current graph state + READY frontier;
- project/repository/worktree/branch/HEAD/dirty identity facts;
- allowed mutation scope + protected scope;
- relevant work-order/claim/policy/skill references;
- required actor/task/runtime capabilities;
- currently eligible callable candidates only;
- current concurrency/resource ceiling;
- retry/repair/adjudication budget;
- cost/quota/durability constraints;
- human approval requirements;
- existing evidence and unresolved blockers;
- user routing preferences that are relevant to this task.

Hard exclusions:
- plaintext credentials/API keys/tokens/cookies;
- unrestricted environment dumps;
- hidden reasoning/chain-of-thought;
- unrelated chat history;
- model/provider routes that are merely configured but not currently eligible.

## 5. Graph Proposal v1 — target output

Each proposed node should declare:
- stable node ID;
- purpose/outcome;
- dependencies;
- required actor capability/role;
- required runtime/tool capabilities;
- owned file/scope or non-file responsibility;
- mutation/read-only intent;
- expected output/evidence;
- verification contract;
- stop/block condition;
- parallel-safe flag only when justified.

Material graphs should end in an integration/final-verification step rather than equating the last implementation node with completion.

## 6. Graph Admission Gate

Validate proposals against current authoritative state before creating/dispatching executable work.

Required checks:
1. schema/version recognized;
2. DAG is acyclic and dependencies resolve;
3. capabilities are canonical/versioned;
4. mutable ownership does not overlap another active task/claim;
5. repository/worktree/branch/HEAD/dirty/authority constraints pass;
6. requested worker/provider routes are currently eligible;
7. concurrency/resource limits pass;
8. required verification and stop conditions exist;
9. destructive/high-impact actions retain approval gates;
10. proposed graph does not weaken acceptance criteria or protected scope;
11. retry/idempotency boundaries are explicit where replay risk exists.

Admission result should be typed and evidence-backed, e.g.:
- `ADMITTED`
- `REJECTED_INVALID_GRAPH`
- `BLOCKED_CAPABILITY`
- `BLOCKED_AUTHORITY`
- `BLOCKED_OWNERSHIP`
- `BLOCKED_PROVIDER`
- `BLOCKED_BUDGET`
- `DECISION_REQUIRED`

Do not silently repair a materially unsafe planner proposal and pretend the planner asked for the corrected graph.

## 7. Evidence-backed selection and fallback

Extend existing provider-selection evidence rather than inventing a second routing log.

Persist/project where available:
- required role/capability;
- selected worker/provider/model;
- candidate eligibility facts;
- selection reason;
- exclusion/fallback reason;
- evidence freshness/timestamp/reference;
- decision/adjudication round;
- whether selection was policy-preferred, cost-driven, durability-driven, independent-review-driven, or a safe fallback.

If the system did not evaluate a reason, keep existing truthful forms such as `UNKNOWN` / `NOT_EVALUATED`.

## 8. Bounded adjudication loop

After each meaningful execution wave:

```text
COLLECT -> VERIFY -> SUMMARIZE EVIDENCE -> ADJUDICATE
```

Allowed decisions:
- continue newly READY nodes;
- repair a failed node;
- add/remove/reorder proposed future nodes through normal Graph Admission;
- request independent review;
- return upstream for product/architecture decision;
- block on authorization/capability/resource;
- complete when acceptance + applicable assurance pass.

Stop or escalate when:
- adjudication budget exhausted;
- same material failure repeats without new evidence;
- no candidate route is eligible;
- execution state is ambiguous and unsafe to replay;
- a human decision/approval is genuinely required.

## 9. Independent review

The planner/adjudicator is not automatically an independent reviewer.

For security, architecture, high-blast-radius, protocol, release, or other risk-proportionate work:
- reuse the accepted A-Wiki ReviewBus / review-mailbox path;
- prefer `strongest-independent` capability;
- bind review to exact artifact/diff/SHA and actual tests/evidence;
- keep reviewer trusted-field stripping and current safety contracts;
- review failure loops to the earliest responsible repair stage.

## 10. Delivery roadmap

| Node | Priority | Goal | Dependencies / gates | Acceptance signal |
|---|---|---|---|---|
| ODP-0 | **P1 docs / this WO** | research + authority boundary + roadmap | current A-Wiki/A-Conductor SSoT | roadmap captured; no source mutation |
| ODP-1 | **P1** | Orchestration Packet v1 contract/projection | current `ExecutionRequest`, capability bridge | pure schema/projection tests; no secrets/transcript dump |
| ODP-2 | **P1** | decision-provider adapter seam | ODP-1; existing provider authority | fake provider returns graph proposal only; zero workspace mutation |
| ODP-3 | **P1** | Graph Admission validator | ODP-1/2; existing TaskGraph/claims/repo gates | invalid/overlapping/unauthorized graphs fail closed |
| ODP-4 | **P1** | capability-first candidate resolution | ODP-3; provider evidence/authority | no hard-coded model semantics; evidence-backed reasons |
| ODP-5 | **P1** | evidence/adjudication envelope + loop budget | ODP-3/4; durable evidence | bounded rounds; no-progress/retry stop proven |
| ODP-6 | **P1** | independent review integration | accepted WO147 ReviewBus adapter | exact-artifact independent review reused, not duplicated |
| ODP-7 | **P1/P2** | operator observability | ODP-4/5/6 | task timeline shows roles, selected route/reason, round, blocker |
| ODP-8 | **P1** | deterministic orchestration E2E/fault injection | ODP-1..6 | fake planner/workers/providers prove lifecycle and recovery |
| ODP-9 | **P2 / gated** | bounded real multi-provider pilot | authorized/admitted providers + stable ODP E2E | one real goal runs plan -> parallel work -> verify -> review/adjudicate without human relay |

## 11. Dependency and coexistence with current frontier

This roadmap does not steal active implementation scopes.

At capture time:
- PR #199 / WO148 owns the provider service-authorization contract and touches `COLLAB.md`; ODP capture does not edit that file or its source/test scope.
- PR #200 / WO147 owns the thin ReviewBus mailbox adapter; ODP-6 depends on its accepted outcome and does not implement a competing review bridge.
- WO096 remains the independent P0 v0.7.0 connector-runtime release blocker. ODP work does not weaken or bypass it.
- AiPASS remains subject to AIP authorization/admission gates; ODP cannot turn a blocked provider into an eligible candidate.

Implementation WOs should be claimed from then-current `origin/main` one slice at a time and must re-run the reuse/claim/ownership gate.

## 12. Deterministic verification matrix

ODP implementation is not accepted from happy-path model demos alone.

Minimum fake/fault-injection cases:
- valid serial graph;
- valid independent parallel READY nodes;
- cycle;
- missing dependency;
- overlapping mutable file scope;
- stale/dirty repo identity mismatch;
- configured but not READY provider;
- READY but not AUTHORIZED provider;
- authorized but not ADMITTED provider;
- missing required actor capability;
- no eligible route;
- stale quota/cost evidence;
- planner proposes invented provider/model;
- worker failure -> bounded repair;
- repeated same failure -> no-progress stop;
- planner/worker transport loss with execution unresolved;
- duplicate dispatch while original execution unresolved;
- reviewer changes-required -> repair -> exact-artifact rereview;
- restart/resume from durable graph/evidence without chat context;
- secret-shaped data rejected/redacted from packets and evidence.

## 13. Success criteria

The feature is successful when the user can submit one sufficiently specified goal and A-Sunday Conductor can, within existing authority:

1. obtain a bounded plan from the best eligible decision intelligence;
2. validate rather than blindly trust that plan;
3. route each node by capability and current evidence, not fixed model names;
4. execute independent work in parallel when safe;
5. preserve exact ownership, recovery, and retry semantics;
6. verify outputs deterministically;
7. obtain independent review where risk requires it;
8. re-adjudicate only when evidence warrants it and within a bounded budget;
9. expose truthful selection/fallback/blocker reasons;
10. resume after session/transport loss without the user carrying context.

The intended end-state is a stronger version of the useful Fable pattern:

> **strong decision intelligence proposes -> A-Conductor proves eligibility and safety -> specialized workers execute -> tools/evidence verify -> independent judgment closes the loop.**
