# WO-GE-006 — GE-6 / GE-7 scheduler + dispatch design gate

Created: 2026-08-26
Owner: GPT-5.6 Sol MAX — single integrator design lane
Status: DESIGN_ACCEPTED — implementation handoff pending ADR PR/CI/merge and GE-5 conflict fix
Branch: `docs/ge-scheduler-dispatch-design`
Base at design start: `be8a45d384b4679ff5c93230d06cbfc17a060b48`; reconciled to `4956760765caab60ae8efe1a48d6edf807cdecce` after GE-5 merged.
Parent: `docs/work-orders/WO-GE-001-graph-engineering-kickoff.md`

## Goal

Resolve the two architecture decisions that block Graph Engineering implementation:

- GE-6: how the scheduler reacts, respects the five-slot worker pool, matches capabilities, and prevents conflicts.
- GE-7: how scheduled graph nodes enter the existing durable job/execution system without creating a second lifecycle, store, dedup layer, or dispatch universe.

This work order is design-only. It authorizes ADR/documentation changes, not scheduler/dispatch production code.

## Repository / ownership gate

- Repository: `aase7en/A-Wiki-Conductor`
- Dedicated worktree: `A:\GitHub\A-Wiki-Conductor-ge-scheduler-design`
- Shared `A:\GitHub\A-Wiki-Conductor` main worktree is out of mutation scope.
- A-Wiki is HOLD/read-only for this work. No A-Wiki repository mutation is authorized.
- GLM GE-5 scope (`ready.py`, `test_graph_ready.py`, WO-GE-001 checkpoint) was independently owned until PR #96 merged.
- Allowed files for this design lane: this WO, ADR GE-0006, ADR GE-0007, bounded SSoT/coordination updates required to hand implementation off.
- Forbidden: `src/a_conductor/graph/scheduler.py`, scheduler implementation tests, dispatch production code, A-Wiki files, shared-main mutation.

## Reuse-before-build result

Authoritative A-Wiki GitHub `main` was inspected read-only at `f0c3a78e19afcb576e54d0370d41ef7f9c5cc371`.

- A-Wiki `conductor/` is the thin brain bridge: status/gate/plan/verify/recall/claim.
- `docs/architecture/brain-vs-conductor-division.md` explicitly assigns process management, worker scheduling/dispatch, and UI to A-Wiki-Conductor.
- A-Wiki `scripts/crew-dispatch.py` is model/subagent delegation, not control-plane worker scheduling.
- A-Wiki claim TTL/heartbeat is brain-side cross-agent coordination and must not become the owner of Conductor execution leases.
- GE-3 already ports the reusable DAG semantics from A-Wiki `dag_eval.py` with attribution.

Classification:

- GE-6 scheduler: **EXTEND / NEW bounded Conductor control-plane policy** over existing graph + worker/runtime state. It is not an A-Wiki duplicate.
- GE-7 dispatch: **REUSE + WRAP + EXTEND** existing `DurableJobControlService`, `SQLiteJobStore`, `DurableJobExecutionCoordinator`, supervised execution, and execution deduplication. A second lifecycle/store is forbidden.

## Decisions

### D6 — Event-driven scheduler core

**ACCEPTED.** GE-6 is a deterministic, re-entrant `schedule_once(...) -> SchedulePlan` style core invoked by state-change events and reconciliation boundaries. It is not a hot polling loop and owns no background thread.

Trigger classes:
- graph/node readiness transition;
- worker state/capability/assignment change;
- gate/provider/rate-limit eligibility change;
- dispatch completion/failure/lease release;
- startup/reconnect/explicit reconcile/rescan;
- targeted wake-up at the next known time-based eligibility boundary.

A low-frequency reconciliation tick may later exist at the orchestration edge as missed-event insurance, but it cannot become the source of scheduler semantics.

### D6-CAP — Five-slot capacity + deterministic worker pairing

**ACCEPTED.** Maximum concurrent graph dispatch is bounded by injected policy `max_parallel=5` for the current fleet, then reduced by actual eligible worker capacity and live reservations.

- One GE-6 task consumes one worker slot in the MVP.
- Eligible workers are READY and not already reserved/inflight.
- Scheduler never starts, stops, or rebinds workers as a side effect of selection.
- Explicit worker binding, when present, is authoritative; otherwise choose deterministically.
- `TaskNode.worker_requirement` must be a subset of the candidate worker/runtime capability snapshot.
- Mutating work requires project/workspace identity and mutation authority to match; ambiguity blocks instead of guessing.
- Worker capability/state data is injected through a scheduler-facing port/snapshot; scheduler must not import desktop UI or scrape UI rows.

Selection order for otherwise eligible nodes is deterministic:
1. greater `TaskNode.priority` first;
2. earlier DAG/topological rank;
3. lexical node ID tie-break.

No random scheduling. Fairness/aging beyond this deterministic policy is a future explicit extension.

### D6-CONFLICT — Resource conflict closure

**ACCEPTED.** GE-6 consumes the GE-4 conflict semantics as the authoritative conflict vocabulary/seam. It must reject conflicts against both:

1. already-running/inflight nodes; and
2. other nodes tentatively selected in the same scheduling batch.

Dynamic conflicts remain scheduler/readiness reasons, not persisted precedence edges unless a deterministic analyzer intentionally materializes a safe ordering under ADR GE-0003.

**Post-merge GE-5 defect:** PR #96's `compute_ready_set()` currently uses literal write-set equality instead of GE-4's glob-aware overlap semantics. Example: `src/**/*.py` vs `src/specific.py` can be incorrectly marked safe. GE-6 TDD may start after this ADR PR merges because scheduler safety independently consumes GE-4 conflicts; the GE-5 repair is a required merge gate before GE-6 is production-ready. No duplicate path-overlap implementation may be added in scheduler code.

### D6-GATE — Brain/safety gate seam

**ACCEPTED.** Pure scheduler logic consumes an injected gate snapshot/port. The concrete integration may call only the approved A-Wiki brain bridge (`python -m conductor` or importable `conductor/` package) per GE-0005. No scheduler module reads A-Wiki `.tmp` stores or imports `scripts.lib.*`.

Gate/provider/human-approval failure yields a typed blocked/deferred reason and no dispatch reservation.

### D7 — Dispatch extends existing durable job control

**ACCEPTED.** GE-7 must dispatch through the existing `DurableJobControlService` / job lifecycle rather than creating a graph-specific execution state machine or store.

Per selected graph node, the graph-dispatch adapter performs a bounded transaction through existing seams:

1. resolve a stable graph-run/node execution identity;
2. idempotently ensure/recover the corresponding durable job;
3. claim the exact selected worker using version/CAS semantics;
4. perform required gate checks before execution;
5. enter GATING through existing lifecycle APIs;
6. invoke exactly one allowlisted operation through `execute_operation()`;
7. let the existing coordinator own EXECUTING attempt accounting, durable checkpoint, recovery classification, and transition to VERIFYING;
8. reconcile/release the scheduler reservation based on durable outcome.

Gate refusal must occur before EXECUTING so it does not consume an execution attempt.

### D7-SURFACE — Tunnel/chat pull vs programmatic push

**ACCEPTED.** The scheduler must not confuse a tunnel with an invocation API.

- Current Sunday-Worker ChatGPT + Serena + Secure MCP Tunnel is `INTERACTIVE_PULL`: Conductor can persist/offer/reserve work; the AI in an active chat turn pulls/claims it through an approved task-inbox/application seam and then uses Serena/tools to perform the task. Conductor cannot assume it can inject a new turn into that chat merely because the MCP tunnel is connected.
- A local/headless/API agent with an explicit invocation interface is `PROGRAMMATIC_PUSH`: GE-7 may invoke its adapter after durable claim/gating and supervise the returned execution identity.
- Worker dispatch mode is declared metadata. Unknown mode blocks rather than guesses.
- A future MCP task-inbox transport wraps job-control/application contracts (`next/claim/heartbeat/checkpoint/result`); it is not a second lifecycle/store. General gateway work remains separately gated.

Direct answer to the product question: **the AI connected through the tunnel is the worker/actor during a ChatGPT turn; the tunnel itself does not press Run Node.** A-Sunday Conductor schedules and persists the node. For today's chat-backed workers, the model must pull the offered task when a turn is active. For true unattended push execution, use/integrate an execution surface that provides a documented programmatic run API.

### D7-IDENTITY — Stable graph dispatch identity

**ACCEPTED CONTRACT.** A graph node ID alone is not globally sufficient. Dispatch identity must include at least `{graph_id, graph_run_id, node_id}` and map deterministically to the durable job/execution identity. The exact encoding is implementation-local and must be validated for length/escaping; semantics are fixed by this ADR.

### D7-LEASE — Reservation lease != A-Wiki claim lease

**ACCEPTED.** Scheduler reservations are Conductor execution-control state. A-Wiki `.tmp/agent-claims.json` TTL leases remain cross-agent brain coordination only.

- Reservation/dispatch ownership must be bounded and heartbeat/reconciliation aware.
- Expiry or heartbeat loss means `RECONCILE`, not blind relaunch.
- Durable worker/job version state is checked before retry/reassignment.
- Exact lease duration is deliberately not fixed by this ADR; implementation must use one bounded, injectable policy and test expiry deterministically.

### D7-DEDUP — Existing execution dedup is mandatory

**ACCEPTED.** Existing fingerprint/dedup outcomes remain authoritative: attach to equivalent live execution, reuse verified completion, or block unknown/unsafe state. Transport failure never authorizes a blind duplicate launch.

`operator_dispatch.py` remains the external operator-protocol adapter; GE-7 should not route internal graph scheduling through it merely to reach job control.

## Verification / review evidence

Reviewed actual implementation seams:
- `graph/domain.py`, `graph/graph.py`, `graph/dag.py`, `graph/analyze.py`, GE-5 PR #96 `graph/ready.py`;
- `job_control.py`, `job_execution.py`, `job_store.py`, `job_state.py`;
- `execution_deduplication.py`, `operator_dispatch.py`;
- worker/control-center domain snapshots.

Post-merge GE-5 defect was recorded on PR #96: `https://github.com/aase7en/A-Wiki-Conductor/pull/96#issuecomment-5420827136`.

## Acceptance criteria

- [x] Polling vs event-driven resolved.
- [x] Five-slot capacity and worker matching contract resolved.
- [x] Same-batch and running-node conflict behavior resolved.
- [x] A-Wiki bridge/reuse boundary verified read-only.
- [x] Dispatch reuse vs new-store decision resolved.
- [x] Chat/tunnel pull-mode vs programmatic push-mode dispatch semantics resolved.
- [x] Stable graph-run/node dispatch identity semantics resolved.
- [x] Lease/heartbeat/dedup responsibilities resolved without duplicating A-Wiki claims.
- [x] GE-5 post-merge readiness defect identified and handed back to responsible stage.
- [ ] ADR GE-0006/0007 committed and PR CI green.
- [ ] ADR PR merged and `origin/main` verified.
- [ ] GE-5 glob-aware readiness regression repaired and green.
- [ ] GLM implementation handoff states GE-6 may start only after the two gates above.

## Next safe action

Re-audit the final ADR PR head against current `origin/main`, require green CI, merge, then hand GE-6 TDD to GLM immediately. GE-005A may land before or during that implementation but must be green/merged before GE-6 production merge.
