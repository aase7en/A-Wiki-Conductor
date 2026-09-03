# Fable Orchestrator Adoption Research — 2026-09-03

Status: RESEARCH COMPLETE / CONCEPT ADOPTION ONLY
Work order: `WO-P1-149`
Reference: `codejunkie99/fable-orchestrator@3b653701d48095a488c350f7a9d5b1fca4d37183`

## Question

Which ideas from Fable Orchestrator materially improve A-Sunday Conductor without importing a second planner, scheduler, provider registry, review lifecycle, task store, claim system, or memory authority?

## FACT — upstream design

Primary sources inspected:
- `README.md`
- `skill/fable/SKILL.md`
- `skill/fable/scripts/ask_fable.sh`
- `skill/fable/agents/openai.yaml`
- `install.sh`
- `tests/test_skill.sh`

Observed properties:

1. Fable separates **orchestration judgment** from **workspace implementation**. Claude Fable 5.1 plans/adjudicates; Codex owns the workspace, dispatch, tools, verification, and final runtime responsibility.
2. The planner receives a compact packet containing objective, acceptance criteria, workspace facts, constraints/protected files, existing evidence, callable workers, concurrency limit, and user preferences.
3. Planner output is a bounded task graph. Nodes carry purpose, dependencies, worker/model choice, ownership, expected output, verification, and a stop condition. Independent READY nodes may run in parallel.
4. Codex validates the returned graph before execution instead of treating planner output as authority.
5. Workers report results/evidence; Codex inspects artifacts and verifies before completion. A complex task may return a compact result packet for another adjudication round.
6. The planner helper is deliberately non-mutating: no tools, no persistent Claude session, and no credentials in the orchestration packet.
7. The repository is intentionally small and prompt/policy driven. It does not implement a durable DAG scheduler, task database, lease system, crash recovery engine, execution deduplication, durable checkpoints, or production recovery supervisor.
8. Implementation routing is hard-coded to two named model routes. This is useful as an example of specialization but is not provider-neutral.
9. Static tests cover shell/install/config/safety properties, but there is no full execution-lifecycle E2E proving planner -> dispatch -> failure/recovery -> adjudication -> completion.
10. Some documentation/tests contain a creator-specific absolute path, so the current package is not a portability reference for A-Conductor.

Upstream URL: https://github.com/codejunkie99/fable-orchestrator

## FACT — A-Wiki / A-Conductor authority already exists

A-Wiki's binding cross-agent protocol already defines capability-first routing roles before vendor/model identity:
- `deterministic-executor`
- `strong-reasoner`
- `strongest-independent`

A-Conductor already has durable `TaskGraph`, READY calculation, scheduler/dispatch, worker/runtime state, provider configuration and execution-authority seams, selection/fallback evidence, resilient execution, and repository safety gates.

The binding `docs/contracts/a-wiki-a-conductor-integration.md` explicitly assigns:
- high-level orchestration intelligence and cost/model policy to A-Wiki;
- operational routing, worker/runtime execution, recovery, evidence, and provider adapters to A-Conductor;
- no incompatible second planner/model-router/review/task-state universe.

Therefore this proposal is classified:

`REUSE + WRAP + EXTEND`

not `NEW` and not `REPLACE`.

## INFERENCE — transferable strengths

The strongest reusable pattern is not the named Fable/Luna/DeepSeek combination. It is the control boundary:

```text
Decision intelligence proposes
        -> Conductor validates
        -> eligible workers execute bounded nodes
        -> deterministic evidence verifies
        -> independent review/adjudication decides what happens next
```

This fits A-Conductor particularly well because the durable runtime pieces that Fable delegates to Codex already exist as first-class product concepts here.

A second useful pattern is a **small, explicit decision packet**. It reduces context waste and makes provider/model substitution easier because the decision provider receives facts and contracts rather than an entire chat history.

A third useful pattern is **budgeted adjudication**. Re-planning should happen only when evidence changes the decision frontier, not after every worker message.

## RECOMMENDATION — adopt

### 1. Orchestration Packet projection

Project a bounded packet from existing `ExecutionRequest`, task graph, repository/runtime state, provider eligibility, and evidence. Include only:
- objective + acceptance criteria;
- task/graph identity and current READY frontier;
- repo/worktree/branch/HEAD/dirty/authority facts;
- allowed/protected scope;
- relevant policy/skill/work-order/claim references;
- evidence already gathered;
- currently eligible/callable worker/provider choices;
- concurrency, retry, cost/quota, durability, and approval constraints;
- user preferences relevant to the decision.

Exclude secrets, raw credentials, hidden chain-of-thought, and unnecessary transcripts.

### 2. Decision-role separation

A planner/adjudicator role may propose graph changes or next actions but must never gain direct mutation authority merely because it is a strong model.

A-Conductor remains execution authority. Repository mutation still requires normal identity, claim, scope, policy, test, and evidence gates.

### 3. Capability-first routing

Use A-Wiki canonical role/capability requirements first. Resolve vendor/model only from current observed candidates that are:

`CAPABLE ∧ READY ∧ AUTHORIZED ∧ ADMITTED ∧ within policy/budget`

Then rank eligible candidates using evidence such as durability/resume support, reliability, quota/cost, latency/throughput, and recent task-relevant performance.

Do not hard-code permanent model names into task semantics.

### 4. Graph admission before dispatch

Treat an LLM-generated graph as a proposal. Validate:
- acyclic structure;
- known capability vocabulary;
- dependency correctness;
- exclusive mutable ownership / no unsafe overlap;
- repository and authority constraints;
- eligible provider/worker supply;
- concurrency/resource limits;
- verification and stop conditions;
- integration/final-verification node where material.

Reject unavailable or invented routes. Do not silently substitute a model/provider when the substitution changes risk or capability.

### 5. Evidence-backed adjudication

After a bounded execution wave, feed only compact structured outcomes/evidence to the decision provider. The next decision may be:
- continue with newly READY nodes;
- repair a failed node;
- revise the graph;
- request independent review;
- block on a real decision/authorization;
- complete.

Default decision/adjudication rounds should be bounded (proposed default: 3) and terminate on repeated no-progress evidence or exhausted retry/decision budgets.

### 6. Independent review remains independent

Planner/adjudicator is not automatically the reviewer. High-risk changes should reuse the accepted A-Wiki ReviewBus path and prefer a `strongest-independent` reviewer that did not author the implementation.

### 7. Truthful routing evidence

Persist/project:
- requested role/capability;
- selected worker/provider/model identity;
- observed eligibility evidence;
- selection reason;
- fallback/exclusion reason;
- adjudication round and decision reason.

Unknown evidence remains `UNKNOWN`; never fabricate why a provider was selected or skipped.

### 8. Fail closed when no route exists

If there is no eligible worker/provider, return a typed blocker with the missing capability/authority/readiness/quota condition. Never invent a model or bypass admission merely to keep the loop moving.

## RECOMMENDATION — reject / do not copy

- Hard-coded implementation model names.
- Creator-specific filesystem paths.
- A second planner/task graph store/scheduler/provider registry/review lifecycle.
- Planner direct filesystem/Git mutation authority.
- Model configuration treated as proof that a model is callable or authorized.
- Static-only verification as proof of orchestration correctness.
- Whole-chat transfer when a compact decision/evidence packet is sufficient.

## DECISION

Adopt the useful Fable concepts as an **Orchestration Decision Plane (ODP)** layered over current A-Wiki policy/orchestration authority and A-Conductor durable graph/provider/execution machinery.

The ODP is a contract and validation/adjudication loop, **not a second orchestrator**:

```text
A-Wiki policy / orchestration intelligence
                |
                v
       Orchestration Packet
                |
                v
 Planner / Adjudicator provider
        (proposal only)
                |
                v
       Graph Admission Gate
                |
                v
 Existing TaskGraph + Scheduler + Provider Authority
                |
        parallel bounded workers
                |
                v
     Evidence + deterministic verify
                |
     independent review when required
                |
                +------> bounded adjudication round
```

Implementation sequencing and gates are defined in `docs/plans/2026-09-03-orchestration-decision-plane-roadmap.md`.
