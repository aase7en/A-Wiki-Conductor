# Elastic Multi-Agent — Upstream Reuse Audit

Date: 2026-09-07
Status: RESEARCH QUEUE / READ-ONLY UPSTREAM STUDY
Related plan: `docs/plans/2026-09-07-elastic-multi-agent-leverage-roadmap.md`
Recomposed onto current accepted main: `origin/main@a887e7a76184d8f5dc22446a159087b6f9cab78d` (WO162 Universal Agent Entry + WO163 fold included; A-Wiki #54 review-gate dependency merged at `967e063c`)

## Purpose

Avoid rebuilding mature agent-orchestration primitives from zero. Before extending A-Sunday Conductor for heterogeneous 4/6/8/10+ lane operation, inspect current upstream implementations and decide per primitive:

`REUSE -> WRAP -> EXTEND -> REJECT -> NEW`

This file records the audit protocol and candidate set. It does **not** claim that any candidate is approved, compatible, secure, or current. Re-verify upstream source, releases, licenses, and documentation at audit time.

## A-Conductor boundary

A-Sunday Conductor should remain primarily the **control / trust / authority plane**:

- durable task/graph state;
- exact repo/worktree/HEAD/task/result identity;
- ownership/lease/mutation-scope authority;
- provider authorization/admission/policy;
- supervised execution/recovery;
- evidence ingestion;
- deterministic verification;
- independent acceptance;
- bounded repair/continuation.

External frameworks may supply useful runtime/workspace/DAG/agent abstractions, but they must not silently become competing authorities.

## Existing local primitives that upstream work must be compared against

- WO-P1-116 elastic worker supply/capacity;
- WO-P1-120 elastic capacity fencing/recovery;
- WorkerCandidateAssembler / WorkerLeaseBroker;
- provider configuration/admission/generation authority;
- TaskGraph / ReadySet / scheduler / ParallelReadyExecutor;
- GraphDispatchCoordinator / durable jobs;
- supervised execution + recovery;
- ZRA-1 exact execution/result identity;
- Issue #216 ZRA-4 bounded parallel shaping — including its accepted findings (CAS two-coordinator convergence, per-node typed outcome folding, fan-in on canonical predecessor `DONE`/`SKIPPED`, `max_parallel=2` first ceiling) and its mutation-ready packets (C1 physical Windows worktree identity with junction/symlink/8.3/`\\?\` resolution, P1-2 write-set alias-overlap normalization, C2 deterministic `zb1:` batch identity) held in the WO161 reservation;
- PR #211 four-lane coordination document;
- WO162 Universal Agent Entry / WO163 continuity fold — entry/claim gate every participant must pass;
- A-Wiki ReviewBus accepted gates (#53 exact-head verdict/CI invalidation; #54 blockers stay blocking through `open`/`addressed` until `verified`) — the review authority audit candidates are compared against, never duplicated.

An upstream library is useful only if integration reduces complexity without weakening these trust boundaries.

## Candidate projects to audit

Candidate list captured from project shaping; current facts must be re-verified before adoption.

| Candidate | Repository | Primary audit question |
|---|---|---|
| Agent Orchestrator | `github.com/AgentWrapper/agent-orchestrator` | Can its agent/runtime/workspace abstractions or CI/review reaction patterns be wrapped without replacing Conductor ownership/lease authority? |
| Open SWE | `github.com/langchain-ai/open-swe` | What can be reused from persistent asynchronous software-task/sandbox execution and CI follow-up? |
| LangGraph | `github.com/langchain-ai/langgraph` | Are checkpoint/durable graph semantics reusable or only conceptual given Conductor's existing durable job authority? |
| Microsoft Agent Framework | `github.com/microsoft/agent-framework` | Which concurrent/handoff/group orchestration patterns fit a provider-neutral capability router? |
| Goose | `github.com/block/goose` | Which local/MCP/provider abstractions can be wrapped for heterogeneous worker execution without granting authority to the agent runtime? |
| OpenHands | `github.com/All-Hands-AI/OpenHands` | Can sandbox/runtime/event patterns improve isolation while preserving exact Conductor identity and recovery? |
| ChatDev | `github.com/OpenBMB/ChatDev` | Which graph/role decomposition ideas are useful for SDLC shaping without copying its authority model? |
| MetaGPT | `github.com/FoundationAgents/MetaGPT` | Which SOP/task-role decomposition patterns improve task contracts and planner output? |
| CAMEL | `github.com/camel-ai/camel` | What empirical multi-agent scaling/coordination patterns can inform 2/4/6/8/10+ lane benchmarks? |

Add/remove candidates only from current evidence. Do not select a framework because it is popular.

## Audit dimensions

For every candidate inspect:

1. **License / provenance**
   - license compatibility;
   - copied/generated dependency obligations;
   - project activity/release health;
   - security advisories where applicable.

2. **Execution model**
   - local process, container, VM, remote sandbox;
   - lifecycle ownership;
   - cancellation/timeout behavior;
   - crash/restart behavior.

3. **Workspace isolation**
   - worktree/branch/sandbox model;
   - handling of concurrent writers;
   - conflict detection;
   - exact repository/HEAD identity.

4. **Task orchestration**
   - DAG/queue/state-machine semantics;
   - asynchronous fan-out/fan-in;
   - work stealing;
   - backpressure/WIP limits;
   - idempotency/retry behavior.

5. **Durability**
   - persistent checkpoints;
   - restart/resume;
   - ambiguous external effects;
   - duplicate-execution prevention.

6. **Provider / model abstraction**
   - heterogeneous provider support;
   - capability routing;
   - quotas/capacity;
   - fallback semantics;
   - secret handling.

7. **MCP / tool integration**
   - tool authorization;
   - filesystem/shell execution;
   - plugin lifecycle;
   - result/evidence contracts.

8. **Review / repair / CI**
   - exact-candidate review;
   - automated CI feedback;
   - bounded repair;
   - reviewer independence;
   - stale-result rejection.

9. **Trust boundary**
   - who is authoritative for task, ownership, workspace, provider, execution, result, retry, and merge;
   - whether caller/model assertions are trusted;
   - fail-open vs fail-closed behavior.

10. **Operational cost**
    - dependency weight;
    - platform support, especially Windows;
    - process/resource overhead;
    - observability;
    - maintenance burden.

## Required output per candidate

Use this template:

```text
PROJECT:
VERSION / COMMIT / DATE VERIFIED:
LICENSE:

USEFUL PRIMITIVES:
- ...

AUTHORITY CONFLICTS:
- ...

WINDOWS / LOCAL FIT:
- ...

SECURITY / RECOVERY RISKS:
- ...

DECISION:
REUSE | WRAP | EXTEND | REJECT | NEW-GAP

EXACT INTEGRATION SEAM:
- ...

CODE TO IMPORT/COPY:
NONE | candidate paths after license review

RED TESTS REQUIRED BEFORE ADOPTION:
- ...
```

## Primitive-by-primitive synthesis

After individual audits, produce a single matrix rather than choosing one winning framework.

| Primitive | Best existing A-Conductor authority | Best upstream reference | Decision | Reason |
|---|---|---|---|---|
| Worker/lease ownership | existing WorkerLease | TBD | KEEP / WRAP | authority must remain local/durable |
| Worktree/sandbox isolation | existing worktree gate | TBD | EXTEND | only if upstream improves isolation without duplicate ownership |
| Physical worktree identity (Windows aliases) | C1 packet: resolve + `\\?\`/UNC strip + normcase/normpath in `windows_worktree_key` (#216 P1-1) | TBD | EXTEND (local) | alias-spelled same physical worktree must be one conflict domain; upstream cannot own this |
| Mutable-scope overlap normalization | same normalized root for scope paths (#216 P1-2) | TBD | EXTEND (local) | raw-string overlap matching misses alias-spelled scopes |
| Batch/graph-run identity | C2 packet: `zb1:<sha256(canonical graph_run_id + sorted selected job_ids)>` | TBD | KEEP local deterministic | deterministic across restart; no new batch store |
| Two-coordinator convergence | deterministic node job-id + store CAS (#216 accepted) | TBD | KEEP local | no global lock, no second scheduler |
| Partial-batch folding | per-node typed `ParallelReadyOutcome`, no batch rollback (#216 accepted) | TBD | KEEP local | preserve successful peers; UNKNOWN reconciles, never replays |
| Fan-in readiness | canonical predecessor `DONE`/`SKIPPED` per-node durable state (#216 accepted) | TBD | KEEP local | successors gated on real terminal state, not barriers |
| Async task graph | existing TaskGraph/jobs | TBD | REUSE local + borrow patterns | avoid second durable graph |
| Runtime plugin abstraction | existing provider/runtime seams | TBD | WRAP/EXTEND | provider-neutral target |
| CI -> repair routing | existing review/repair path + A-Wiki ReviewBus gates (#53/#54) | TBD | EXTEND | preserve exact result identity + blocker-until-verified semantics |
| Checkpoint/resume | existing durable jobs/recovery | TBD | KEEP / compare | upstream cannot replace ambiguity rules silently |
| MCP/tool surface | current plugin/MCP boundary | TBD | WRAP | maintain authorization |

The objective is a **composed architecture**, not framework replacement.

## Research safety rules

- Read upstream before coding locally.
- Prefer official repository/docs and exact version/commit evidence.
- Do not execute untrusted upstream installer/scripts on the production workstation merely for inspection.
- Do not copy source until license/provenance review passes.
- Do not import a framework that becomes a second scheduler/store/lease/retry/review authority.
- Do not weaken Conductor's UNKNOWN/no-blind-replay semantics to fit an upstream API.
- Do not send credentials/private repository content to an external service during research.
- Record unsupported or unclear behavior as `UNKNOWN`, not inference.

## Benchmark questions

The audit must answer whether upstream reuse can improve **accepted throughput**, not just launch more agents.

Measure or plan to measure:

- 1 vs 2 vs 4 vs 6 vs 8 vs 10 active lanes;
- independent-task throughput;
- merge/conflict rate;
- first-review acceptance;
- repair loops;
- review queue latency;
- restart recovery;
- partial UNKNOWN batch behavior;
- provider saturation/backpressure;
- CPU/RAM/process overhead;
- cost per accepted task;
- human relay actions.

## Exit criteria for research phase

Research is complete when:

1. each serious candidate has an exact current source/license review;
2. each useful primitive has one of `REUSE/WRAP/EXTEND/REJECT/NEW-GAP`;
3. no selected integration creates a second authority;
4. Windows/local operation and crash/restart behavior are understood;
5. a minimal implementation proposal maps changes onto existing WO116/WO120/ZRA-4 seams;
6. required RED/concurrency/chaos tests are specified before production mutation;
7. the implementation proposal demonstrates why it should improve accepted throughput over the current bounded parallel baseline.

Only then create/activate an implementation work order.
