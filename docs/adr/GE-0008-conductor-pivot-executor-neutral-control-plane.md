# GE-0008 — A-Sunday Conductor pivot: quota/cost-aware hybrid execution control plane

Status: PROPOSED / PHASE0_RECONCILED / GPT_SOL_ADJUDICATED_HYBRID_V2 / LIVENESS_AMENDMENT / R2_REREVIEW_REQUIRED
Date: 2026-09-14
Decider: GPT-5.6 Sol (integrator/authority)
Parent: `WO-P1-231` / Issue #317
Baseline: `origin/main@251df211afc1ee5452f3652675d7a2f38c526876`

## 1. Decision

A-Sunday Conductor is the **vendor-neutral, quota/cost-aware hybrid execution control plane**. It keeps durable authority for goals/jobs, claims/leases, worktree safety, provider admission, routing, recovery, deterministic verification, review/repair, exact-SHA acceptance, closeout, and continuation.

Executors are replaceable hands behind existing control-plane seams. The system routes each task to the **lowest-cost safe capable lane** using task class, risk, capability, readiness, authorization, quota, cost, availability, worktree ownership, latency, and autonomy requirements.

Canonical role split:

- **Sunday Worker / Serena** — first-class lightweight local semantic/tool lane, not a fallback and not the orchestrator.
- **Native Git/tests/RDC** — deterministic local/system lane where model reasoning is unnecessary.
- **Kilo + GLM 5.3** — default heavyweight autonomous lane once the Kilo adapter is accepted.
- **Claude Code/ZCode + GLM 5.3** — existing alternate heavyweight supervised lane.
- **Kilo + GPT-5.6 Sol** — premium escalation when quota is available and task value justifies it.
- **GPT-6 Astra** — exceptional architecture/adversarial review/debug escalation.
- **Codex/Cline/local models** — later replaceable executor lanes.

Strategy remains: `REUSE -> WRAP -> EXTEND -> REPLACE/NEW only by explicit decision`. No product rewrite and no second scheduler/task/claim/lease/review/recovery/SSoT system.

## 2. Adjudicated reuse decisions

### 2.1 Executor port

**REUSE `JobExecutionBackend`; do not build a second Executor Contract framework.**

`src/a_conductor/job_execution.py` already provides the canonical provider-neutral port:

`execute(operation_ref, JobExecutionContext) -> JobBackendResult`

`DurableJobExecutionCoordinator` already owns the durable execution lifecycle around that port. `AllowlistedNativeJobBackend` and `ClaudeCodeJobBackend` prove structurally different backends can conform without changing the protocol. The supervised ZCode path supplies reusable mutation/recovery/authority patterns even though it is not yet composed as a production `JobExecutionBackend`.

A future executor descriptor may be added only if a concrete adapter cannot express required identity/capability metadata through existing provider/runtime/worker structures. That is an EXTEND decision, not a new framework by default.

### 2.2 Mobile/operator protocol

**KEEP `operator.v1` canonical. WRAP/EXTEND it; do not create a broad new Mobile API.**

Reuse `operator_protocol.py`, `operator_dispatch.py`, `operator_wire.py`, durable job control, existing bounded execution-artifact evidence surfaces, and the existing Secure MCP tunnel/SundayWorker surface. The first mobile design candidate is a narrow Conductor MCP/operator wrapper over an existing authenticated tunnel/loopback boundary.

Never expose arbitrary shell, Kilo daemon, Claude terminal, credentials, SQLite files, unrestricted filesystem access, or unrestricted local services to the Internet.

### 2.3 Quota/cost routing

**EXTEND existing provider/scheduler evidence; do not build a second router or quota vocabulary.**

Reuse `ProviderHealth`, `QuotaSnapshot`, `ProviderObservation`, `ProviderExecutionAuthority`, provider admission, worker candidate assembly, READY/scheduler/ParallelReady execution, execution deduplication, recovery reconciliation, and ContinuityGuard.

Minimal additions after predecessor gates:

1. declared, generation-stamped `cost_class` (UNKNOWN allowed; advisory ordering only),
2. a pure derived quota tier over existing `QuotaSnapshot` (`AVAILABLE/LOW/EXHAUSTED/UNKNOWN` as a preference view, not a second stored authority),
3. deterministic candidate preference ranking after all hard gates,
4. thin **pre-attempt** provider re-selection when nothing was launched,
5. provider/operator quota evidence only where observable; unknown remains fail-closed when quota is required.

Mid-flight executor/provider switching never bypasses recovery classification, lease/worktree authority, execution fingerprints, or dedup/reconciliation.

### 2.4 Execution liveness / operator status

**EXTEND existing durable events/checkpoints and `operator.v1`; do not create a second status store.**

Long-running executors, reviews, CI, and provider calls must expose a recoverable operator liveness projection: task/execution identity, executor, authoritative job state, derived `STARTING/RUNNING/WAITING/STALLED/TERMINAL/UNKNOWN`, `last_activity_at`, `last_progress_at`, optional heartbeat, typed blocker/reason, evidence reference, and exact next safe action.

Heartbeat proves observability, not progress. `STALLED` is a derived warning only; it triggers runtime/log/durable-state reconciliation before any attach/retry/failover. Timeout alone never proves non-completion. The binding reporting/recovery contract is `docs/agent-collab/EXECUTION_LIVENESS_PROTOCOL.md`.
## 3. Target architecture

```text
User / ChatGPT Mobile
        |
        v
existing authenticated tunnel / bounded operator wrapper
        |
        v
A-Sunday Conductor durable control plane
  |-- Goal/Job/Graph/READY authority
  |-- WorkerLease + worktree/HEAD/scope authority
  |-- Provider policy/readiness/quota/admission authority
  |-- quota/cost-aware route selection
  |-- execution liveness/status projection + bounded watchdog
  |
  |-- LIGHTWEIGHT --> SundayWorker / Serena / native tools
  |-- HEAVY DEFAULT --> Kilo + GLM 5.3
  |-- HEAVY ALT --> Claude Code/ZCode + GLM 5.3
  |-- PREMIUM --> Kilo + GPT-5.6 Sol
  `-- CRITICAL REVIEW --> GPT-6 Astra
        |
        v
JobExecutionBackend / existing supervised execution seams
        |
        v
deterministic verify -> independent review -> bounded repair
        |
        v
GoalCloseout -> NEXT READY -> bounded result/evidence -> mobile
```

ChatGPT conversation remains an interactive/pull surface; Conductor must not assume it can wake or push a new turn into an arbitrary ChatGPT conversation. Push-style notification may use an accepted external channel such as Hermes/Telegram, while ChatGPT Mobile reads bounded status/results through its tool surface.

## 4. Existing assets that remain authority

KEEP/REUSE without reconstruction:

- `domain.py`, `job_store.py`, `job_state.py`, `job_control.py`, `job_execution.py`
- `graph/*`, READY/scheduler/dispatch lifecycle
- `worker_lease.py`, `worker_candidate_assembly.py`
- provider configuration/policy/execution authority/config store/runtime assembly
- `parallel_ready_execution.py`, elastic worker capacity
- supervised execution/command runner/owned process/native execution
- execution record/store/dedup/artifacts
- ZCode production assembly/runner/protocol/recovery/process truth
- Claude Code harness/backend/assembly as adapter patterns
- `zero_relay.py`, review task/execution, repair materializer
- `continuity_guard.py`, continuity projection, recovery reconciliation
- `goal_closeout.py`, agent change packets
- `operator_protocol.py`, `operator_dispatch.py`, `operator_wire.py`
- Serena/SundayWorker lifecycle/settings/transport assets

## 5. A-Wiki / A-Conductor boundary

- **A-Wiki** owns durable knowledge/policy: architecture rationale, provider/model research, reusable protocols, lessons, long-term cost/capability knowledge.
- **A-Conductor** owns live execution authority: jobs, READY state, provider observations, admission, attempts, worktrees/leases, routing choice, recovery, verification and acceptance evidence.

A-Wiki policy may seed declared configuration, but A-Wiki is never a live dispatch dependency and must not become a second runtime state store.

## 6. Dependency order and current frontier

The pivot does **not** bypass or strand the current Zero-Relay chain. Actual durable frontier remains controlled by Issue #214/GitHub evidence rather than stale `CURRENT-WORK.md` on main.

Required predecessor chain before broad pivot source implementation:

`WO226 reviewer-execution bridge repair/accept -> WO223/C1 semantic ReviewEvidence -> WO227/ZRA-3 production NEXT READY activation`

ZRA-4 bounded-parallel work remains dependency-gated where required for multi-lane mutation. Existing GoalCloseout/ContinuityGuard authority remains unchanged.

As of this adjudication, `main@251df211...`; WO226 source is not accepted into main and must pass its own independent exact-SHA review/CI/merge/post-main gates. This ADR grants no source mutation authority to WO226 or any pivot implementation lane.

## 7. Revised P0 sequence

Numbers after WO231 are provisional until explicit Work Orders are issued. Do not create duplicate WOs where an existing ZRA WO already owns the seam.

1. **P0-0 — WO231/GE-0008 adjudication**: this docs-only reconciliation; independent R2 review then merge/post-main checkpoint.
2. **P0-A — finish existing ZRA predecessor chain**: WO226 -> WO223/C1 -> WO227/ZRA-3; ZRA-4 only where required by bounded parallel acceptance.
3. **P0-B — canonical backend conformance proof**: prove new executors reuse `JobExecutionBackend`; no new executor framework.
4. **P0-C — SundayWorker first-class lightweight route**: bind capability/risk/cost selection to the existing Worker/Serena lane without duplicating scheduler or lease authority.
5. **P0-D — Kilo+GLM heavyweight adapter**: read-only/headless contract first, then mutation capability only through existing lease/admission/apply/recovery authorities.
6. **P0-E — quota/cost preference + pre-attempt failover**: extend existing provider/scheduler evidence; preserve `PROVIDER_QUOTA_UNKNOWN` fail-closed semantics.
7. **P0-F — execution liveness + operator status**: reuse durable events/checkpoints to expose activity/progress/heartbeat, derived stall/wait/terminal truth, reconcile-before-retry, and `operator.v1` status projection.
8. **P0-G — mobile control/result wrapper**: extend `operator.v1` through an existing authenticated SundayWorker/Serena/MCP or equivalent narrow loopback gateway.
9. **P0-H — hybrid E2E proof**: ChatGPT Mobile -> Conductor -> lightweight or heavyweight route -> observable liveness -> verify/review/repair -> GoalCloseout/NEXT READY -> bounded result, with `human relay actions per accepted external-agent task = 0`.

Fast-path implementation may reorder P0-C..P0-G only when dependencies and file scopes are proven independent; P0-H remains the terminal hybrid E2E acceptance proof. Default WIP remains <=3 mutable lanes + 1 independent read-only review lane.

## 8. Acceptance proofs for the pivot

The pivot is not complete until deterministic evidence proves at least:

- a lightweight task stays on SundayWorker/native tools even when premium models are available;
- a heavyweight task executes through a Kilo+GLM adapter without creating a second lifecycle/store;
- GPT/Codex quota unavailable/unknown cannot cause unsafe dispatch; eligible work can fall back only through a safe pre-attempt route;
- an ambiguous/mid-flight execution cannot be blindly relaunched on another provider;
- `operator.v1` mobile control can create/observe/control a durable job without arbitrary shell exposure;
- one real bounded end-to-end goal completes with zero manual prompt/result copy-paste;
- exact worktree/HEAD/lease/evidence identity survives verify, review, repair and closeout;
- a long-running executor distinguishes activity from progress, derives `STALLED` without blind replay, and can be recovered by a fresh session from durable/runtime evidence;
- `operator.v1` can expose bounded liveness/status without leaking secrets or creating a second status authority.

## 9. Non-decisions / blockers

- No paid plan, credit purchase, or material PAYG use is authorized by this ADR.
- Kilo CLI/headless argv/result/config-isolation contract must be pinned against the actual installed Kilo version before adapter grammar is frozen.
- Provider-specific quota must not be invented when the provider exposes no reliable API; operator/advisory evidence must be provenance-tagged and short-lived.
- Root checkout `A:\GitHub\A-Wiki-Conductor` remains stale/protected-dirty and is never a mutation surface.
- `CURRENT-WORK.md`/handoff reconciliation belongs to WO229 or its accepted successor, not this ADR lane.
- Open/legacy branches and PRs are not authority merely because they exist.

## 10. Consequences

- The earlier Phase-0 proposal to BUILD a standalone Executor Contract module is **superseded**. `JobExecutionBackend` is the canonical executor port unless future concrete evidence proves a minimal extension is necessary.
- SundayWorker/Serena is promoted from "specialized later executor" framing to a **first-class low-cost/lightweight route**.
- Kilo+GLM becomes the target default heavyweight autonomous route; Kilo+GPT is premium rather than default because quota/cost are routing inputs.
- `operator.v1` becomes the canonical mobile/control vocabulary; gateway work is a wrapper/extension problem.
- quota/cost work becomes a bounded extension of existing provider/scheduler evidence, not a new router.
- Existing WO226/WO223/WO227 work remains valuable and on the critical path.
- Execution liveness becomes an explicit P0 control-plane requirement: status is a derived projection over existing authority, never a shadow task/state system, and every new session can recover it without user relay.
