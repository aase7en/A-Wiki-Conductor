# Elastic Multi-Agent Leverage Roadmap

Date: 2026-09-07
Status: SHAPING / P0 ZERO-RELAY PRIORITY FENCE / NO FLEET IMPLEMENTATION AUTHORITY
Repository: `aase7en/A-Wiki-Conductor`
Baseline at creation: `origin/main@df5a25f1f9949e6938ea4bbcf0150515e6e5fa85` (PR #221 / ZRA-1 merged)
Final shaping fold re-pinned on 2026-09-12 to `origin/main@cfcb369fe5ab3a50569defa822289f10f2f38aac`. The dependency order remains `ZRA-2 -> ZRA-3 -> ZRA-4`; Phase B is accepted/post-main and Phase C0 / WO216 is the current ZRA-2 implementation frontier.

## Purpose

Evolve A-Sunday Conductor from a fixed small set of parallel lanes into a provider-neutral, asynchronous, conflict-aware **Elastic Multi-Agent execution fabric** that can use 1, 2, 4, 6, 8, 10+ agents when independent READY work actually exists.

This document does not authorize implementation or reorder the accepted Zero-Relay roadmap. It records the target architecture and acceptance principles so future sessions do not depend on chat memory.


## 2026-09-12 priority fence and deep-audit fold

### Binding product priority

The latest user instruction reaffirms the highest project priority:

> **Complete GPT <-> GLM Zero-Relay before expanding Sunday Worker/Fleet/MCP production scope.**

Completion means the user no longer copies prompts, results, review findings, repair instructions, or `continue` messages between ChatGPT/GPT and GLM/ZCode for the accepted path. Research/docs may proceed without consuming a critical mutable lane; Worker Host/Fleet implementation may not preempt the ZRA dependency chain.

This is consistent with WO189 / PR #261 (pending priority capture) and does not transfer or supersede any active ZRA ownership.

### Actual-state critical path at final fold

This roadmap was re-pinned on 2026-09-12 against `origin/main@cfcb369fe5ab3a50569defa822289f10f2f38aac`.

Durable Zero-Relay state observed from Git/GitHub/Issue #214:

- **ZRA-2 Phase B is COMPLETE / POST-MAIN VERIFIED / ACCEPTED.** The reviewed no-clobber repair was accepted and folded through PR #291; merge `8700d21887500965ffc33bcbffa1f33602d9c2f6` preserved all six accepted Phase-B paths byte-for-byte and post-main verification reported `321 passed, 1 expected platform skip`.
- **ZRA-2 Phase C0 is the active implementation frontier.** WO216 was explicitly released `NEXT_READY` on the accepted Phase-B base. A later durable coordination checkpoint detected two GLM sessions entering the same WO216 worktree; one session stood down without mutation. Treat that event as evidence that logical claim publication alone is insufficient runtime fencing; do not dispatch another WO216 writer until the current owner is reconciled.
- **ZRA-2 Phase C1 remains blocked** until C0 is independently accepted, merged, post-main verified, and a fresh C1 claim is released.
- **WO208 crash/effect lab is CHANGES_REQUIRED.** Independent review found five P2 evidence defects and published bounded repair packet PR #294. The original lab is not accepted as the WO205 Phase-D prerequisite.
- **ZRA-2 Phase D remains blocked** until C0+C1 are accepted and the repaired WO208 crash/effect evidence is accepted and consumed.
- **ZRA-3 remains dependency-blocked by full ZRA-2 acceptance.**
- **ZRA-4 remains dependency-blocked by ZRA-3 acceptance and Issue #216 release.**

These are dated observations, not permanent projections. Every dependent mutation must re-pin actual state.

### Required execution order

```text
P0-A  ZRA-2 Phase C0 — CURRENT ACTIVE FRONTIER
      WO216 review-task binding/materialization
      -> deterministic exact ResultIdentity -> review TaskPacketFile
      -> trusted route binding; READ_ONLY reviewer contract
      -> no invented mailbox agent_id
      -> no-clobber/replay/collision/identity-drift tests
      -> reconcile duplicate-mutator event before further dispatch
      -> freeze exact SHA -> independent review -> merge -> post-main verify

P0-B  ZRA-2 Phase C1
      WO201 trusted review-evidence composition
      -> reviewer payload cannot mint author/result/attempt/generation authority
      -> bind exact independent reviewer execution
      -> exact author-result/task assignment cross-binding

P0-C  WO208 repair + ZRA-2 Phase D prerequisite
      repair the independent lab findings from PR #294
      -> prove real crash/effect/restart evidence truthfully
      -> accept repaired evidence before Phase-D source release

P0-D  ZRA-2 Phase D
      bind accepted ZRA-1 execution/result/review path + GoalCloseout/durable job state
      -> at-most-once external effect / receipt / reconciliation
      -> UNKNOWN or lost acknowledgement => reconcile, never resend
      -> one review failure => exactly one bounded repair generation
      -> repaired result ingested/verified automatically

P0-E  Full ZRA-2 acceptance E2E
      GPT task -> GLM -> exact result -> verify -> independent review
      -> automatic repair -> GLM -> exact repaired result -> acceptance
      -> human relay actions = 0

P0-F  ZRA-3 acceptance
      automatic NEXT READY
      -> reconcile current WO191/WO195/WO199 stack on accepted ZRA-2
      -> timeout/UNKNOWN never blind-replays

P0-G  ZRA-4 bounded baseline
      first ceiling = 2 mutable lanes
      -> C1 physical workspace identity
      -> C1b write-set canonicalization
      -> C2 deterministic parallel batch identity
      -> two-lane race/restart/partial-failure/fan-in proof
      -> raise toward 3 only from evidence

ONLY AFTER P0-G:
P1    Worker Host / Fleet supervisor
P2    second-machine federation
P3    runtime isolation
P4    evidence-gated 4/6/8/10+ scaling
```

### Open-source lessons admitted into the current Zero-Relay path

The companion deep audit permits only bounded invariant/test adoption on the current critical path:

1. **agentmux delivery receipt:** submitted-but-unverified is an at-most-once recovery fence, never a resend signal.
2. **Agent Orchestrator/Open SWE CI-review reaction:** feedback is bound to exact task/result/reviewer identity and enters the existing ZRA-2 repair path.
3. **OpenAI/MAF handoff discipline:** explicit filtered task context, stable participant/execution identity, accepted vs intermediate output separation.
4. **OpenHands/Open SWE unknown-state rule:** unknown/unreachable workspace/process is recovery/hold, not silent replacement.
5. **Docker gateway collision rule:** dynamic capability names cannot silently shadow one another.
6. **Multi-agent runtime fencing lesson from the live WO216 duplicate-mutator incident:** logical task/claim identity must be composed with exact physical worktree/process ownership before dispatch; duplicate entry is a coordination defect to reconcile, not permission for concurrent mutation.

No new scheduler, queue, graph store, retry store, or review authority is authorized.

### P1 — single-machine Worker Host MVP (Windows first)

After ZRA-4 baseline acceptance, consolidate logical workers behind one background host/supervisor while preserving old endpoints as migration fallback:

```text
ChatGPT / A-Sunday Conductor
           |
      Worker Host API
           |
    +------+------+------+------+
    W1     W2     W3     W4     W5
```

Required:
- stable host identity + authenticated endpoint;
- list/get/health/events for logical workers;
- start/stop/restart/drain through existing LocalInstanceOrchestrator/recovery;
- live reconciliation of process/project/worktree/branch/HEAD/dirty/task/claim/lease;
- background/no-console startup;
- request/response plus streaming event/read model;
- namespace collision rejection;
- **no Worker Host scheduler/task/claim/merge authority**.

Primary references: OpenHands Agent Server, Agent Orchestrator, Docker MCP Gateway, `agents`.

### P2 — Windows + Mac federation

```text
A-Conductor
   +-- Windows Host -> W1..W5
   +-- Mac Host     -> W6..W10
```

Required:
- host identity separate from worker identity;
- OS/capability/resource/latency/last-seen projection;
- `HOST_OFFLINE` distinct from `WORKER_UNHEALTHY`;
- heartbeat/event reconciliation;
- cross-host auth/secret isolation;
- cross-platform exact-SHA verification roles;
- no assumption RDC identity == Worker Host identity.

References: ContextForge federation/OTEL, OpenHands multi-server pattern, Gas Town Witness/Deacon separation.

### P3 — runtime isolation profile

Before high-concurrency mutable lanes that run services/tests:
- deterministic per-lane port ranges;
- per-lane DB/schema and Compose namespace where required;
- env projection without secrets in Git;
- dependency/cache policy;
- exact owned background-process identity;
- setup/teardown hooks;
- stale-allocation reconciliation/doctor.

Allocation is subordinate to physical worktree identity + WorkerLease, never a second scheduler/claim system.

References: workz and falq.

### P4 — evidence-gated fleet scale

- **2 mutable lanes:** ZRA-4 first acceptance target.
- **3 mutable + 1 read-only review:** normal ceiling after 2-lane proof.
- **4–6 lanes:** require READY demand, runtime isolation, review capacity, provider capacity, and measured throughput gain.
- **8 lanes:** additionally require host resource backpressure + restart/partial-failure evidence.
- **10+ registered workers:** allowed as a pool; active mutation remains dynamic and recovery capacity stays free.

Ten registered workers are capacity, not a concurrency target.

### Adoption verdict

| Area | Adopt | Reject |
|---|---|---|
| Zero-Relay transport | agentmux at-most-once receipt invariants | second prompt queue |
| worker host | OpenHands/AO interface patterns | their schedulers/task stores |
| MCP gateway | Docker namespace/lifecycle/security | gateway-owned authority |
| federation/observability | ContextForge/OTEL patterns | ContextForge control plane |
| liveness | `agents` live reconciliation | persisted liveness as truth |
| runtime isolation | workz/falq allocation patterns | unowned global cleanup |
| fleet health | Gas Town Witness/Deacon roles | Beads/Gas Town task DB |
| fan-out/in | MAF API/test patterns | MAF graph/checkpoint store |
| durable semantics | Pydantic/Temporal invariants | durable-engine migration |
| handoff context | OpenAI explicit filters/traces | implicit full-chat handoff |
| swarm scale | Ruflo topology benchmarks | Ruflo memory/router/scheduler |

### Fleet acceptance metrics

A Fleet change is rejected if it increases busyness without accepted delivery:
- human relay actions / accepted external-agent task (**0 after Zero-Relay**);
- accepted work/hour;
- median/p95 lead time and READY->claim latency;
- first-review pass rate and repair loops/task;
- merge/conflict rate and review queue wait;
- CPU/RAM/disk/LSP/process count per host;
- duplicate execution count;
- ambiguous-submit blind replay count (**0**);
- runtime port/DB/Compose collision count;
- recovery success + orphan process/worktree count;
- cost / accepted task.

### Activation rule

The deep audit is complete enough to close the research prerequisite for architecture shaping. It does **not** activate Worker Host/Fleet product work. The next production mutation remains the current Zero-Relay critical path. Worker Host/Fleet becomes `NEXT_READY` only after ZRA-4 baseline acceptance or an explicit future user decision that reorders the roadmap after fresh conflict/authority analysis.


## Existing foundations to reuse

Do not rebuild these authorities:

- `WO-P1-116` Production Worker Supply + Elastic Capacity — RELEASED.
- `WO-P1-120` Elastic Capacity Fencing + Recovery Hardening — RELEASED.
- PR #211 four-lane coordination SSoT — existing lane/ownership shaping; do not duplicate its mutable scope.
- Issue #216 / ZRA-4 bounded parallel Zero-Relay preflight — existing parallel execution/fan-in authority shaping.
- existing TaskGraph / ReadySet / scheduler / WorkerLease / provider admission / durable job / supervised execution / review / recovery primitives.
- ZRA-1 accepted production execution path from PR #221.
- `WO-P1-162` Universal Agent Entry (PR #219, BINDING) + `WO-P1-163` continuity fold (PR #224) — every fabric participant starts from `00-AGENT-ENTRY.md` -> `PROJECT-GRAPH.yaml` -> actual-state verification; no lane may bypass the entry/claim gate.
- A-Wiki ReviewBus accepted review gates — Issue #53 / PR #55 (exact-head verdict/CI invalidation on HEAD rollover) and Issue #54 / PR #56 (blocker findings stay blocking through `open` AND `addressed`; only `verified` releases PASS/READY). These are the acceptance authorities any fabric review/fan-in semantics must reuse; no second review bus.

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

### Stage 0 — external reuse audit — COMPLETE FOR SHAPING (2026-09-12)

Deep source/license/trust-boundary audit is complete in the companion research document. Production adoption remains separately gated; no upstream framework becomes authority by completing this research.

### Stage 1 — bounded parallel baseline

Use existing ZRA-4 scope: 2–3 independent READY lanes with exact conflict/admission/fan-in proof.

### Stage 2 — dynamic 4–6 lanes

Only after Stage 1 acceptance. Add adaptive capacity and demonstrate that accepted throughput improves without increasing duplicate/ownership violations.

### Stage 3 — dynamic 8 lanes

Require restart/concurrency/partial-failure/CI-review-backpressure tests plus measured benefit over Stage 2.

### Stage 4 — dynamic 10+ lanes

Only if READY frontier, provider capacity, conflict topology, review capacity, and measured accepted throughput justify it. No architectural constant should require exactly ten workers.

This scale progression must not silently reorder the authoritative ZRA-0 -> ZRA-1 -> ZRA-2 -> ZRA-3 -> ZRA-4 -> ZRA-5 dependency chain. Shaping/research may proceed read-only; production mutation obeys current roadmap/claims.

## Issue #216 ZRA-4 findings this roadmap must reconcile

Classified against the accepted durable record in Issue #216 (GPT1 review verdict + GPT2 gate refresh + Q59 host validation). Nothing in this section authorizes implementation.

### CURRENT ACCEPTED (design verdicts already recorded in #216; reuse, do not reinvent)

- **Two-coordinator convergence** — deterministic per-node job identity + store CAS closes the concurrent-coordinator window; no global lock, no second scheduler.
- **Partial-batch preservation** — `ParallelReadyExecutor` returns one typed `ParallelReadyOutcome` per selected node; there is NO batch transaction/rollback semantic, and that absence is correct. Lane A success + lane B UNKNOWN preserves A, retains B's admission/lease, and never blindly replays B.
- **Fan-in by per-node durable state** — successor node C becomes READY only when every required predecessor reaches canonical `DONE`/`SKIPPED`; mid-batch crash preserves already-committed lanes across restart.
- **Lease never auto-released by elapsed time alone**; UNKNOWN external effect routes to reconcile, never replay.
- **First ZRA-4 acceptance ceiling** — `SchedulePolicy.max_parallel = 2`, raised toward 3 only after 2-lane chaos/restart/fan-in proof; independent read-only review lane accounted separately under WO154's `3 mutable + 1 review` ceiling.

### FUTURE SHAPING (mutation-ready packets; NOT implemented — gated on the ZRA chain + a fresh WO161 activation claim)

- **C1 — physical Windows worktree identity** (GPT1 P1-1): `windows_worktree_key` (normcase+normpath only) does not resolve junctions/symlinks or expand 8.3 short paths; the same physical worktree expressed via alias currently yields two lease identities => double mutation lease + mutable-scope-overlap bypass. Accepted repair direction (Q59-validated on the real Windows host): resolve + explicit `\\?\`/UNC-prefix stripping + normcase/normpath, with an alias-matrix RED (case change + trailing separator + `~1` short path => `WORKTREE_PARALLEL_CONFLICT`; genuinely distinct worktrees still pass).
- **P1-2 — mutable-scope alias overlap**: `write_sets_overlap` matching raw scope strings can miss alias-spelled overlap; scope paths must normalize through the same normalized root (same future commit as C1).
- **C2 — deterministic batch identity**: `zb1:<sha256(canonical graph_run_id + sorted selected job_ids)>`; the pure re-form design is validated, deterministic across restart, and creates no new batch store/authority.
- Required REDs before any ZRA-4 implementation: alias-key matrix; deterministic batch_id re-form; executor-level two-coordinator race; mid-batch generation-drop; one-lane TTL expiry.

### EXPERIMENTAL / NOT ACCEPTED

- `WO-P1-161` remains a **reservation only** — no dedicated worktree/branch, no activation claim, `SAFE_TO_MUTATE_WO161 = NO` until the ZRA predecessor chain and the fresh main/worktree/HEAD/dirty/claim/overlap gate pass.
- Every upstream framework candidate in the companion audit is unverified until its per-candidate audit passes; popularity is not evidence.

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

The companion upstream reuse audit is complete for architecture shaping. Continue the existing Zero-Relay critical path from the current frontier: reconcile and finish WO216 Phase C0; independently accept/merge/post-main C0; release and complete WO201 Phase C1; repair and accept the WO208 crash/effect evidence; complete ZRA-2 Phase D plus the full no-human-relay review/repair E2E; reconcile/accept ZRA-3; then execute the already-gated ZRA-4 C1/C1b/C2 work and two-lane proof.

Worker Host/Fleet product work remains deferred until that ZRA-4 baseline is accepted. Research-derived P0 invariants may be folded into the existing ZRA contracts/tests only through their current owners and claims; this document grants no source mutation authority. Any future Worker Host/Fleet implementation requires a fresh work order, exact-main re-pin, ownership/non-overlap gate, RED-first acceptance criteria, and independent exact-SHA review.
