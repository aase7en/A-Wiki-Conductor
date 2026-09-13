# GE-0008 — A-Sunday Conductor pivot: executor-neutral durable control plane

Status: PROPOSED / PHASE0_RECONCILED / AWAITING_GPT_SOL_ADJICATION + RAW_ROADMAP_INGESTION
Date: 2026-09-13
Decider: GPT-5.6 Sol (integrator/authority) — this ADR is a PROPOSAL authored by the GLM Phase-0 lane
Input pointer: Issue #317 (raw roadmap `A-CONDUCTOR-PIVOT-ROADMAP-2026-09-13.md`, Drive id `1PhXDwcD9RhPALG_fm03bDWC-XaXenwfx`) — see WO-P1-231 §Blockers: the raw file is NOT present in the locally synced Drive at Phase-0 time; its details are NON-BINDING until ingested and reconciled.
Companion: `docs/work-orders/WO-P1-231-pivot-phase0-reconciliation.md` (the 14-item Phase-0 report this ADR is derived from).

## 1. Decision

Reposition A-Sunday Conductor as the **vendor-neutral durable control plane** for coding-agent execution, with ChatGPT Mobile as the primary human command surface. Conductor keeps ALL durable authority (goals/WOs, state, claims/leases, routing, continuity/recovery, worktree safety, deterministic verification, exact-SHA evidence, review/repair/acceptance, Zero-Human-Relay). External coding agents (Kilo+GPT-5.6, Claude Code/ZCode+GLM-5.3, later Codex/Cline) become **replaceable executors** behind one minimal Executor Contract. Sunday Worker/Serena remains a specialized local semantic/deterministic executor, not the orchestrator.

Strategy: `REUSE → WRAP → EXTEND → REPLACE/NEW only by explicit decision`. No product rewrite.

## 2. Evidence basis (verified 2026-09-13, read-only)

- origin/main = `251df211afc1ee5452f3652675d7a2f38c526876` (114 modules in `src/a_conductor/` + `graph/` subpackage).
- The full durable-authority stack ALREADY EXISTS and is review-hardened through the WO158–WO226 arcs: SQLiteJobStore + GraphDispatch durable lifecycle + version-CAS single-winner; WorkerLease broker/store (READ_ONLY/MUTATION intents, mutable-scope fencing, canonical release truth); provider config store with generation CAS + admission authority + policy evaluation; supervised ZCode execution (owned process, protocol permission-denial, child truth); execution fingerprint/dedup with all-equivalent multiplicity; zero-relay review pipeline (review task → reviewer execution bridge → C1); continuity guard/projection + goal closeout + agent change packets; recovery reconciliation.
- CURRENT-WORK.md on main is STALE (authoritative section dated 2026-09-08, WO166 era) — actual frontier lives in Issue #214: WO226 reviewer-execution bridge on PR #314 @ `fa85dce` awaiting GPT rereview (external CR1 round), WO227–WO230 docs lanes open, WO230 "review task-contract authority / architecture split" in flight.
- Root checkout `A:\GitHub\A-Wiki-Conductor` is ~230 merges behind origin/main (at `f4ecf9a`, PR-#80 era) and protected-dirty — it must never be used as authority; all lanes branch from origin/main.

## 3. Target architecture (smallest viable)

```
User / ChatGPT Mobile
   ↓ (operator channel — EXTEND existing operator wire / tunnel boundaries)
A-Conductor control plane (authority)
   ├─ durable goals/WOs → GraphDispatch jobs → claims/leases → routing
   ├─ Executor Contract (thin, executor-neutral)
   │    ├─ Lane A: Kilo + GPT-5.6 Sol (adapter; architecture-sensitive work)
   │    ├─ Lane B: Claude Code/ZCode + GLM-5.3 (existing supervised path; bounded work)
   │    ├─ later: Codex, Cline adapters
   │    └─ Sunday Worker / Serena (specialized local executor)
   ├─ isolated worktree per lane → tests/build/Git/CI
   ├─ deterministic verify + independent review + repair + exact-SHA acceptance
   └─ checkpoint → next READY → mobile status/report
```

## 4. Smallest Executor Contract (proposal)

Only what Conductor truly needs; provider UI concepts stay OUT of the durable contract:

1. **executor identity** — stable executor descriptor (kind + version) ≠ worker identity (WorkerLease `worker_id`).
2. **capability declaration** — reuse `WorkerLeaseCandidate.capabilities` / `required_capabilities` + CAPABILITY_MATRIX routing policy.
3. **readiness** — worker health (`inspect_health`, `health_fresh`, READY) + provider snapshot/admission where model-backed.
4. **task dispatch** — reuse `ParallelReadyTask`-shaped validated packet (exact task contract ref + sha + HarnessDispatch facts).
5. **execution identity** — the PROVEN three-identity model: dispatch-context id (= GraphDispatch job id = admission execution id) ≠ supervised runtime job id ≠ `DurableExecutionRecord.execution_id`, cross-bound by fingerprint (never equated).
6. **binding** — lease (worker/worktree/branch/HEAD/task) + packet hash + `verify_execution_context` drift fences.
7. **status observation** — execution-store states + `SupervisedLauncher.inspect` equivalent + attach/reuse classifications (all-equivalent, never newest-row).
8. **result collection** — typed artifact refs (stdout/report/result) + `AgentResultPacket`/`AgentChangeApplier` for change application.
9. **cancellation** — owned-process graceful-first stop semantics where the executor runtime supports it; otherwise REFUSED/UNSUPPORTED.
10. **recovery/attach** — ATTACH_RUNNING / REUSE_COMPLETED / RECOVERY_REQUIRED semantics + `recovery_reconciliation`; fail-closed on UNKNOWN.
11. **evidence identity** — exact-SHA discipline: candidate SHA, fingerprint, packet sha, artifact hashes.
12. **failure classification** — `RecoveryClassification` + typed error codes; no blind retry.

Existing satisfaction: items 2–12 are substantially satisfied TODAY by the ZCode/GLM lane (WO226 proved the deepest parts). The BUILD surface is one executor-neutral descriptor/port module + per-executor adapters; nothing else new.

## 5. What this ADR does NOT decide

- Binding the raw roadmap's specific claims (unread locally) — gated on ingestion (WO-P1-231 Blocker B1).
- Reconciliation with WO230 "architecture split" and the WO223/C1 → Phase-D chain — Sol must adjudicate how the pivot re-scopes that chain (the reviewer-execution bridge built in WO226 is exactly the kind of asset the pivot reuses; do not strand it).
- Any DEPRECATE/REMOVE of shipped product surfaces (Phase-6 challenge concluded: no generic editor/terminal/chat-UI/MCP duplication exists in `src/` to remove; candidates list recorded in WO-P1-231 §7).
- Mobile gateway mechanism choice (operator wire EXTEND vs new minimal API) — WO proposes EXTEND-first with a gateway decision gate.

## 6. P0 roadmap (work-order sequence; numbers provisional)

P0-0 reconcile (this WO-P1-231) → P0-1 ADR adjudication (this doc) → P0-2 Executor Contract module (WO-232) → P0-3 Kilo thin adapter (WO-233) → P0-4 ZCode/GLM lane conforms to contract (WO-234, mostly WRAP) → P0-5 dual-executor parallel + cross-review proof (WO-235) → P0-6 recovery/fail-closed proof matrix (WO-236) → P0-7 minimal control/status/approval API for ChatGPT Mobile (WO-237) → P0-8 end-to-end Zero-Relay proof, metric `human relay actions per accepted external-agent task = 0` (WO-238).

Priority driver: remove AnyDesk/manual-relay dependence as early as possible (P0-7 may pull earlier if the operator-channel EXTEND path proves cheap).

## 7. Consequences

- Executor/provider/model names become routing choices; swapping executors must not touch durable semantics.
- The WO22x chain's review/repair discipline carries over unchanged (RED-first, exact-SHA, cross-review, GPT merge authority).
- Parallel mutation allowed only under: both lanes READY + separate owned worktrees + valid claims + disjoint mutable scopes + fan-in plan; default WIP = 3 mutable lanes + 1 read-only review lane; cross-review pairing GLM↔GPT.
