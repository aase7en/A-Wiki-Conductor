# WO-GE-006 — GE-6 / GE-7 scheduler + dispatch design gate

Created: 2026-08-26
Owner: GPT-5.6 Sol MAX — single integrator design lane
Status: COMPLETE / MERGED
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

## Checkpoint — GE-6 implementation lane reconcile (2026-08-28, GLM 5.3 MAX)

Status: COMPLETE / MERGED

- Worktree `A:\GitHub\A-Wiki-Conductor-glm-ge6`, branch `feat/ge-6-scheduler`, clean before and after.
- Implementation commit `43cd20f` (pure deterministic `schedule_once → SchedulePlan`, 176-line scheduler + 202-line tests) was already green in isolation: scheduler 14 passed, graph suite 74 passed pre-reconcile.
- Reconciled with `origin/main @ ca4cd98` via clean merge `d377dbe` — zero conflicts, no rebase/reset/force. The merge carries in: the merged GE-005A deterministic glob∩glob overlap seam (`2378b9c` — satisfying the D6-CONFLICT merge gate for the seam itself) and the PR #113 Windows CI test-isolation repairs, which address the Windows-only CI failure class previously blocking this PR.
- Verified on the merged state: scheduler consumes the single `write_sets_overlap` seam from `graph/analyze.py` for both running-node and same-batch conflicts (no third matcher; D6-CONFLICT compliant).
- Full graph suite on merged state: **92 passed** (`test_graph_scheduler`, `test_graph_analyze`, `test_graph_ready`, `test_graph_dag`, `test_graph_domain`, `test_graph_assembly`, `test_graph_store`, `test_ge005a_glob_conflict`); `python -m compileall -q src/a_conductor` PASS; `git diff --check` PASS.
- Scope held: only this WO checkpoint, `handoff.md` PR-#104 line, and the merge commit itself; no AHA-3/README/worker-auto-fallback/installer/North-Star file was edited.

Next safe action: push `feat/ge-6-scheduler`, require the exact PR head Windows/Ubuntu/macOS CI green, then GPT-5.6 Sol re-audits the final PR head before any merge.

## Checkpoint — GE-6 review round 2 (2026-08-28, GLM 5.3 MAX)

Status: COMPLETE / MERGED

Reconcile: merged `origin/main @ ab28dc7` (safe merge `09753c6`, no rebase/reset/force); the only conflict was `handoff.md` "Protected Parallel Work", resolved preserving both sides' continuity (main's AHA-3 narrative + GE-6 lane status line).

TDD RED→GREEN for the four ADR GE-0006 review blockers (10 new failing tests first, then the fix; scheduler file 14 old tests unchanged-green):

1. **Ordering now priority → topological rank → lexical ID.** `_topological_rank()` derives deterministic Kahn ranks via the existing GE-3 `topological_sort`; same-priority nodes order by earlier rank before the lexical tiebreak. Regression: `test_same_priority_orders_by_topological_rank_before_lexical_id` (c-early rank 1 beats b-later rank 2 despite lexical order).
2. **Equivalent worker selection is input-order independent.** Available workers are sorted by stable `worker_id` before assignment; no explicit binding/policy override exists yet (noted in the docstring as the future exception). Regression: `test_equivalent_worker_selection_is_stable_by_worker_id` (w-alpha before w-bravo regardless of input order).
3. **Mutating identity enforcement, fail closed; read-only exempt.** A node with non-empty write_set reuses the single GE-4 binding parser (`_parse_binding`, `ws:`/`project:` convention — no second parser) and requires the selected worker's project/workspace identity to match plus `mutation_authorized=True`; a mutating node without any identity binding blocks itself before worker selection (missing identity fail closed), and worker identity mismatch/absence is not eligible (ambiguous fail closed). Read-only nodes (empty write_set) are NOT blocked by `mutation_authorized=False` — the old blanket `mutation_authorized` gate was removed. Regressions: matching/mismatching workspace, missing-binding fail-closed, unauthorized-worker fail-closed, read-only-not-blocked.
4. **Injected `NodeEligibility` gate/provider seam.** `schedule_once(..., eligibility={node_id: NodeEligibility})` is a deterministic injected input; `gate_refused` / `provider_unavailable` / `rate_limited` each block the node with a typed reason BEFORE any worker is considered or reserved — no reservation, no dispatch, no GE-7 expansion, no probing. Regressions: parametrized three-refusal test + default-eligible-still-selects.

D6-CONFLICT held: all conflict checks still route through the single `write_sets_overlap` seam from `graph/analyze.py` (now imported at module level along with `_parse_binding`); the running-conflict regression was restructured to exercise the scheduler's external-reservation path (`running_write_sets`), since in-graph DOING conflicts are already surfaced by `compute_ready_set`.

Verification (worktree `A:\GitHub\A-Wiki-Conductor-glm-ge6`, merged state `09753c6` + fix commit):
- full directive graph suite: **102 passed** (scheduler 24 = 14 original + 10 new; analyze/ready/dag/domain/assembly/store/ge005a 78).
- `python -m compileall -q src/a_conductor` PASS; `git diff --check` PASS.
- Changed files confined to GE-6 scope: `src/a_conductor/graph/scheduler.py`, `tests/test_graph_scheduler.py`, plus this WO checkpoint and the handoff PR-#104 status line. AHA/README/installer/North-Star untouched.

Remaining blockers: none known locally — PR #104 exact-head CI (Windows/Ubuntu/macOS) and GPT-5.6 Sol re-audit are the outstanding gates before merge.

## Checkpoint — GE-6 final round (2026-08-28, GLM 5.3 MAX)

Status: COMPLETE / MERGED

TDD RED→GREEN (12 new failing tests first; all 24 prior scheduler tests stayed green):

1. **Explicit worker binding is authoritative (ADR §4/§5).** `_node_bindings()` now returns project/workspace/worker from ONE `_parse_binding` call (the single GE-4 parser — no second parser). A node bound `worker:<id>` restricts candidates to exactly that worker: bound worker wins over stable worker-ID order; a bound worker that is missing / not READY / reserved / capability-mismatched / identity-unauthorized / already assigned this batch BLOCKS with `BINDING` kind — the scheduler never silently falls back to another worker; mutating bound workers still satisfy project/workspace identity + mutation authority (verified match→select, mismatch→block).
2. **Human approval + stable typed block reasons (ADR §7).** `NodeEligibility` gains deterministic `human_approval_pending`; `BlockedReason` gains a required stable `kind: BlockedReasonKind` (str-Enum output vocabulary, not a lifecycle/store): `GATE_NO_GO`, `HUMAN_APPROVAL_WAIT`, `PROVIDER_WAIT`, `RATE_LIMIT_WAIT`, `CAPACITY`, `CAPABILITY`, `NO_WORKERS`, `IDENTITY`, `CONFLICT`, `BINDING`. All four §7 wait/refusal states are distinct kinds; pending human approval blocks BEFORE worker selection/reservation, same as other eligibility refusals. Human-readable reason strings from earlier rounds are unchanged, so existing fragment assertions remain valid.

Verification (worktree `A:\GitHub\A-Wiki-Conductor-glm-ge6`, base `383ff1a` + this round):
- full directive graph suite: **114 passed** (scheduler 36 = 24 prior + 12 new; analyze/ready/dag/domain/assembly/store/ge005a 78).
- `python -m compileall -q src/a_conductor` PASS; `git diff --check` PASS.
- Changed files: `src/a_conductor/graph/scheduler.py`, `tests/test_graph_scheduler.py`, this WO checkpoint, handoff PR-#104 line. No AHA changes, no GE-7 dispatch, no new scheduler/parser/store; `write_sets_overlap` remains the sole conflict seam.

Remaining blockers: none known locally — exact-head PR #104 CI and GPT-5.6 Sol re-audit remain the gates before merge.

## Repo-health reconciliation - 2026-08-29

- Historical execution/checklist text above is preserved as evidence; stale status is superseded by accepted GitHub state.
- PR #97 merged into main as `15d2b26d959965ff7b32347326e02bbab1f60a8a`.
