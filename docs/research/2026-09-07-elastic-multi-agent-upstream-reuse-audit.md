# Elastic Multi-Agent — Upstream Reuse Audit

Date: 2026-09-07
Status: DEEP AUDIT COMPLETE / READ-ONLY SHAPING / NO IMPLEMENTATION AUTHORITY
Related plan: `docs/plans/2026-09-07-elastic-multi-agent-leverage-roadmap.md`
Final fold re-pinned on 2026-09-12 to `origin/main@cfcb369fe5ab3a50569defa822289f10f2f38aac`; Zero-Relay Phase B is accepted/post-main, Phase C0 is the active frontier, and this audit remains read-only shaping only.

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

## Original candidate queue (historical)

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


## 2026-09-12 verified deep audit results

### Scope / binding priority

This pass completes the read-only audit for the serious candidates in the original queue plus projects discovered during source-level research. The adoption unit is a **primitive**, not a whole framework.

Binding priority from the user:

> **Finish GPT <-> GLM Zero-Relay first.** The user must not copy prompts, results, review findings, repair tasks, or `continue` messages between the two sides.

Research may harden Zero-Relay requirements now, but Worker-Fleet/MCP production work must not preempt the accepted ZRA chain. Any upstream component that would become a second scheduler, task/claim/lease store, review authority, retry authority, provider authority, or durable execution authority is rejected as core.

Verified 2026-09-12 against GitHub repository metadata plus relevant README/docs/source. Stars are a dated maturity signal only.

### Verified source pins

| Project | Head | License | Stars | Primary lesson |
|---|---:|---|---:|---|
| AgentWrapper/agent-orchestrator | `55e13fcab017` | Apache-2.0 | 11,570 | fleet plugins, worktrees, Windows ConPTY, CI/review feedback |
| langchain-ai/open-swe | `9752b06c2bdf` | MIT | 10,699 | persistent sandbox, safe failure, CI/review continuation |
| microsoft/agent-framework | `14b9f1d7e9a4` | MIT | 13,479 | typed fan-out/fan-in, checkpoint identity |
| block/goose | `846cbeaf5157` | Apache-2.0 | 54,131 | heterogeneous local/MCP agent runtime |
| OpenHands/software-agent-sdk | `57f5cc9f4a67` | MIT | 1,091 | Agent Server REST/WebSocket/events/workspaces |
| OpenHands/OpenHands | `9120ff6cbbe2` | MIT | 87,486 | Agent Canvas: one UI can switch across multiple Agent Servers |
| docker/mcp-gateway | `a21c0ac1c1e7` | MIT | 1,562 | one gateway -> many MCPs; lifecycle/security/namespaces |
| IBM/mcp-context-forge | `b13ebe48c980` | Apache-2.0 | 4,458 | MCP/A2A federation + observability |
| adelost/agentmux | `09b8017a8998` | MIT | 0 | durable prompt receipt / at-most-once delivery |
| JinchengGao-Infty/agent-mux | `ce3b994bc8d5` | GitHub metadata NOASSERTION; README says MIT | 7 | one MCP server -> tmux-backed multi-agent pool |
| joaovictor3g/agents | `d315e24c4a4b` | MIT | 0 | worktree/tmux registry + live reconciliation |
| craigsc/cmux | `864d41d4b4fe` | MIT | 603 | minimal idempotent worktree lifecycle |
| gastownhall/gastown | `649b832b7672` | MIT | 18,013 | coordinator/worker/health/merge role separation |
| gastownhall/beads | `a690b0a8c4d1` | MIT | 27,062 | READY frontier / atomic claim ergonomics |
| pydantic/pydantic-ai | `f6afee204181` | MIT | 19,866 | typed delegation + durable-boundary discipline |
| openai/openai-agents-python | `1705dd62509e` | MIT | 29,364 | bounded handoff context + tracing |
| temporalio/temporal | `9ab3a9f770da` | MIT | 22,978 | mature durable workflow reference |
| crewAIInc/crewAI | `e1f3c4bdd4d3` | MIT | 58,372 | roles/flows only |
| ruvnet/ruflo | `005a0ed25e64` | MIT | 72,105 | swarm topology/federation/monitoring |
| rohansx/workz | `84b6688bee54` | MIT | 87 | port/DB/Compose/env/process isolation |
| sunduq-ai/falq | `32c39b5e2f1c` | MIT | 4 | deterministic runtime slots + hard pre-run gate |
| langchain-ai/langgraph | `e539ac122f41` | MIT | 41,472 | checkpoint/graph reference only |
| OpenBMB/ChatDev | `4fb2db0ea903` | Apache-2.0 | 34,271 | role/SOP decomposition |
| FoundationAgents/MetaGPT | `11cdf466d042` | MIT | 70,323 | SOP/task-role decomposition |
| camel-ai/camel | `8c791b7b9cf7` | Apache-2.0 | 17,704 | multi-agent research patterns |

Primary repositories are the corresponding `https://github.com/<owner>/<repo>` URLs above.

### Per-project decisions

| Candidate | Useful primitive | Authority conflict | Decision / priority |
|---|---|---|---|
| **agentmux** | persistent FIFO; `pending -> pasting -> drafted -> submitted -> acknowledged/delivered_unverified`; exact history receipt; never re-paste ambiguous submitted work | its queue must not become a second A-Conductor execution store | **EXTEND semantics into existing ZRA durable execution — P0 NOW** |
| **JinchengGao-Infty/agent-mux** | compact proof that one MCP endpoint can create/list/spawn/send/read/kill multiple interactive agents via a backend pool | project is tiny; tmux-only; default agent examples use unsafe permission-bypass flags; GitHub license metadata is not machine-verified | **REFERENCE MCP-to-many-worker API shape only; DO NOT vendor/runtime-adopt** |
| **OpenHands Agent Server** | execution/API/UI separation; REST + WebSocket events; explicit workspace/conversation identity; forward-compatible event variants | conversation store/automation must not replace jobs/scheduler | **REFERENCE now; EXTEND Worker Host after ZRA-4** |
| **OpenHands Agent Canvas** | one control UI can select among multiple Agent Servers/backends; UI does not execute agent actions directly | Canvas state must remain read model/UI, not task authority | **REFERENCE Fleet Dashboard / multi-host UX after ZRA-4** |
| **Agent Orchestrator** | worktree/branch/PR lanes; runtime/workspace plugins; Windows process/ConPTY; CI/review feedback routing; dashboard | owns tracker/lifecycle/merge in its own model | **REFERENCE + selective EXTEND after Zero-Relay** |
| **Docker MCP Gateway** | one endpoint to many servers; dynamic discovery; centralized lifecycle/trace; collision/security lessons | gateway auth must not override A-Conductor policy/provider authority | **EXTEND namespace/security invariants; gateway DEFER** |
| **ContextForge** | MCP/A2A federation, host registry, OTEL, admin/read model | full gateway would duplicate governance/persistence | **REFERENCE for P2 federation/observability** |
| **joaovictor3g/agents** | persisted identity but liveness reconciled from tmux/filesystem every read; detached sessions | none if copied as read-model rule | **EXTEND reconciliation tests — P1** |
| **workz / falq** | deterministic ports; per-worktree DB/Compose/env; hooks; liveness; precise reap; agent-context projection | allocation must remain subordinate to physical worktree + WorkerLease | **EXTEND runtime isolation — P2/P3** |
| **Gas Town** | Mayor/Polecat/Witness/Deacon/Refinery separation; persistent worker identity + ephemeral sessions | its task/merge authorities overlap ours | **REFERENCE fleet roles/health only** |
| **Beads** | dependency READY front; claims; machine-readable durable task UX | direct duplicate of jobs/tasks/claims/SSoT | **REJECT store adoption; REFERENCE ergonomics** |
| **Microsoft Agent Framework** | concurrent fan-out -> aggregator fan-in; stable participant IDs/checkpoint restore | duplicate graph/checkpoint authority | **REFERENCE ZRA-4 APIs/tests only** |
| **PydanticAI / Temporal** | explicit durable activity boundaries; stable IDs; replay/restart discipline | replacing jobs/execution is major duplicate/migration | **REFERENCE; no engine migration** |
| **OpenAI Agents SDK** | handoff input filters/history mapping; trace actual tools/handoffs | no conflict if used as packet-design reference | **REFERENCE bounded handoff/tracing** |
| **Open SWE** | persistent isolated sandbox; unreachable workspace is not silently replaced; CI/review continuation | LangGraph/thread state would duplicate durable graph | **REFERENCE failure semantics** |
| **LangGraph** | checkpoint/graph concepts | direct durable-graph duplication | **REJECT-AS-CORE** |
| **Goose** | provider/MCP-capable local execution | could become competing agent lifecycle | **WRAP only for a proven future capability gap** |
| **Ruflo** | health/monitor streams; worktrees; federation; 6–8 hierarchical and 10+ hierarchical-mesh guidance | own swarm state, memory, router, loops, consensus, huge MCP surface | **REFERENCE scale/topology; REJECT-AS-CORE** |
| **CrewAI / ChatDev / MetaGPT / CAMEL** | roles, SOPs, planner decomposition | insufficient exact Git/lease/replay/acceptance authority; duplicate orchestration | **REFERENCE task-contract ideas only** |
| **cmux** | minimal idempotent worktree lifecycle | A-Conductor already richer | **REFERENCE only** |

### P0 ideas admitted immediately

Only these research findings should change current Zero-Relay acceptance/RED tests:

1. **At-most-once submit/receipt fence (agentmux):**
   - distinguish `not submitted` from `submitted but receipt/result unverified`;
   - ambiguous post-submit => `RECOVERY_REQUIRED`, never resend;
   - exact receipt binds task bytes/hash + execution identity;
   - recovery is restart-stable.
   These are semantics for existing DurableExecutionRecord/supervised-execution/recovery authorities, not a new queue.

2. **Task-bound CI/review reactions (Agent Orchestrator/Open SWE):**
   - CI/review evidence routes to the exact task/result/review identity;
   - it can create only the bounded repair generation allowed by ZRA-2;
   - no generic "send feedback to whichever agent is running."

3. **Bounded handoff context (OpenAI Agents SDK / MAF):**
   - handoff payload is explicit and filtered;
   - full chat history is never implicit authority;
   - stable participant/execution IDs survive resume;
   - accepted output is distinguished from intermediate output.

4. **Unknown execution/workspace => hold/reconcile (OpenHands/Open SWE):**
   - never silently replace an unreachable workspace/process whose external effects are unknown.

5. **Capability collision fails closed (Docker MCP Gateway):**
   - aggregated tool/resource/prompt names cannot silently shadow each other.

### Primitive synthesis

| Primitive | Keep local authority | Upstream lesson | Action |
|---|---|---|---|
| tasks/claims/leases | jobs + WorkerLease + scopes | Beads/Gas Town comparison | **KEEP** |
| GPT->GLM dispatch/receipt | ZRA-1 + durable execution | agentmux | **EXTEND P0 tests/semantics** |
| review->repair | ZRA-2 + ReviewBridge | Agent Orchestrator/Open SWE | **EXTEND P0 through existing packet path** |
| trusted review evidence | WO201/existing review authority | OpenAI/MAF typed handoff | **REFERENCE P0** |
| NEXT READY | ZRA-3 jobs/graph | MAF stable restore identity | **KEEP + tests** |
| parallel fan-out/in | ZRA-4 scheduler/jobs/CAS | MAF/Ruflo | **KEEP + tests** |
| physical worktree identity | WO196/197 C1/C1b | worktree tools as negative comparison | **EXTEND local before live ZRA-4** |
| Worker Host | LocalInstance/runtime/registry | OpenHands + Agent Orchestrator | **EXTEND P1** |
| one endpoint -> many workers/tools | connector/MCP boundary | Docker/ContextForge | **EXTEND P1/P2** |
| host/fleet health | instance health/recovery | Gas Town + `agents` | **EXTEND P1** |
| cross-machine federation | no full accepted seam | ContextForge | **NEW thin adapter P2** |
| runtime port/DB/Compose isolation | partial conventions | workz/falq | **EXTEND P2/P3** |
| event stream/dashboard | desktop/read models | OpenHands + OTEL | **EXTEND P1/P2** |
| durable engine replacement | jobs/events/checkpoints | Temporal/Pydantic/LangGraph | **REJECT replacement** |
| second task/memory DB | current SSoT | Beads/Ruflo/CrewAI | **REJECT** |
| agent-runtime auto-merge | GPT/exact-SHA acceptance | AO/Gas Town | **REJECT as authority** |

### Copy-versus-build verdict

**Copy source code now: NONE.**

The highest-value discoveries are invariants and interface patterns. Copying an upstream scheduler, queue, gateway, graph engine, task DB, or worktree manager on the P0 path would increase authority count and integration risk.

Future narrow source reuse is permitted only after a dedicated license/provenance/API-stability gate. Plausible future reuse candidates are a small platform-neutral runtime-isolation helper, OpenTelemetry conventions, or generated protocol/client types—not a new control plane.

### Community evidence / operational warning

Recent multi-agent practitioner reports converge on the same failure modes:
- worktrees help only for genuinely independent scopes;
- worktrees do **not** isolate ports, DBs, Compose projects, untracked env, or process state;
- coordination/merge/review overhead can erase gains around 4–6 coding agents;
- cleanly separated audit/test/feature lanes can materially reduce elapsed time.

Therefore optimize **accepted throughput**, not number of busy workers.

### Audit conclusion

The research validates A-Conductor's control/trust-plane architecture. It identifies this implementation order:

1. **P0:** finish Zero-Relay, adding at-most-once delivery/receipt and task-bound repair invariants.
2. **P1:** Worker Host + live event/read model using OpenHands/AO patterns behind existing worker/lease authority.
3. **P1/P2:** gateway namespace/federation/observability using Docker/ContextForge patterns.
4. **P2/P3:** runtime isolation using workz/falq patterns.
5. **P4:** measured 2 -> 4 -> 6 -> 8 -> 10+ scale using Gas Town/Ruflo topology lessons.

The Stage-0 research prerequisite is complete for architecture shaping. Production adoption still requires a fresh work order, exact-main pin, non-overlap claim, RED-first acceptance tests, and risk-tier review.


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
