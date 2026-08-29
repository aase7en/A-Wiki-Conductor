# WO-GE-001 — Graph Engineering kickoff: contracts → implementation roadmap

Created: 2026-08-25
Owner: GLM 5.3 (preparation) → GPT-5.6 Sol MAX (integrator decisions) → paired implementation
Status: COMPLETE / GE-1..GE-11 MERGED; GE-11R1 READ-ONLY HARDENING MERGED
Inputs: GE-0 status report + A-Wiki reuse gate (session records 2026-08-25); ADR drafts GE-0001..0005 in this branch.

## Decision briefs — integrator fan-in (2026-08-26)

| ID | ADR | DECISION | Reason / guardrail |
|---|---|---|---|
| D1 | GE-0004 | **ACCEPTED** — port A-Wiki `dag_eval` semantics with attribution. | Reuse proven Kahn/cycle/ready-level behavior without a runtime dependency on the A-Wiki checkout. GE-3 is limited to parse/validate, topo/cycle naming, and ready levels; scheduler/execution stays Conductor-side. |
| D2 | GE-0002 | **ACCEPTED WITH CLARIFICATION** — graph fields are Conductor-owned; `awiki-task/v1` stays untouched. | A-Wiki is under HOLD and remains the brain contract. `TaskEdge`/`TaskGraph` own dependency relations so TaskNode must not keep a second nested dependency source of truth. A-Wiki task status is planning/source metadata only; retry/repair/execution state stays in the existing Conductor lifecycle state machine. |
| D3 | GE-0005 | **ACCEPTED** — A-Wiki access is bridge-only, enforced by CI grep/static gate. | Current A-Wiki GitHub confirms `conductor/` is the thin brain-side API; direct `.tmp/*` or `scripts.lib.*` coupling would violate the reuse boundary and standalone Conductor requirement. |
| D4 | GE-0003 | **ACCEPTED WITH SEMANTIC GUARDRAIL** — keep the 12-value initial vocabulary. | The enum vocabulary is useful, but dynamic/resource relations (for example worker/runtime/provider/rate-limit conflicts) must not be blindly materialized as precedence edges or exempted from cycle detection. Only true predecessor relations participate in Kahn ordering; dynamic constraints remain readiness/scheduler reasons unless a deterministic analyzer explicitly materializes a safe ordering. Human approval is a readiness gate, never a repair back-edge. |
| D5 | GE-0001 + roadmap | **ACCEPTED** — start with `a_conductor/graph/` and tests only; no scheduler. | First implementation PR is **GE-1a only** (`domain.py` + `test_graph_domain.py`), then GE-1b; GE-3 ports DAG semantics after the graph contract exists. GE-6/GE-7 remain blocked until their GPT design gate. |

**GO signal:** GLM may begin GE-1a from this accepted contract. No scheduler, dispatch, brain-schema mutation, or UI work is authorized by this decision PR.

### Integrator verification evidence (2026-08-26)

- A-Wiki GitHub `main` verified at `2b6dda1ff9e5ff17ef04d509a05048814d546129`; `docs/protocols/cross-agent-work-orders.md`, `skills/awiki/a-claim/SKILL.md`, `scripts/eval/dag_eval.py`, `schemas/awiki-task/v1.schema.json`, and `docs/architecture/brain-vs-conductor-division.md` were checked read-only.
- Live local A-Wiki claim store `.tmp/agent-claims.json` contained `{"claims": []}` at the decision gate; no overlapping Graph Engineering claim blocked GE-1.
- A-Wiki `dag_eval.py` still exposes Kahn topological sort with cycle detection and parallel dependency levels, supporting D1 reuse lineage.
- A-Wiki brain HOLD phases 8–11 remains unchanged; these decisions authorize no A-Wiki mutation.
- Conductor `origin/main` baseline for this decision PR: `6e8f2820423ae9bb80219e973f4ecbe09ac016d5`. The shared local `main` worktree was intentionally not switched or fast-forwarded.

## Roadmap (micro-step nodes; owner G=GLM, P=GPT; every node = WO + TDD + CI + PR)

| Node | Deliverable | Files (new unless noted) | Owner |
|---|---|---|---|
| GE-1a | TaskNode/TaskEdge/DependencyType dataclasses + validation | a_conductor/graph/domain.py, tests/test_graph_domain.py | G |
| GE-1b | TaskGraph assembly + invariants (acyclic via GE-3, unique ids) | a_conductor/graph/graph.py + tests | G |
| GE-2 | SQLite graph store (nodes/edges/runs/node_events) beside existing stores | a_conductor/graph/store.py + tests | G |
| GE-3 | DAG port (Kahn + cycle naming + ready levels) per GE-0004 | a_conductor/graph/dag.py + NOTICE + tests | G |
| GE-4 | Dependency analyzer: derive FILE_WRITE/GIT/WORKER/RUNTIME conflicts from write_sets/bindings | a_conductor/graph/analyze.py + tests | G |
| GE-5 | ReadySet computation (deps ∧ resources ∧ capability ∧ gates) | a_conductor/graph/ready.py + tests | G |
| GE-6 | Scheduler skeleton: bounded 5-slot capacity, capability match, bridge gate calls | a_conductor/graph/scheduler.py + tests | P design → G implement |
| GE-7 | Dispatch integration: leases/heartbeat/idempotency on existing dedup/job store | integrate with job_control.py (modified) | P design → G implement |
| GE-8 | Fan-out/fan-in completeness barriers (expected/missing/silent children) | a_conductor/graph/barriers.py + tests | G |
| GE-9 | Wire verify/review outcomes from lifecycle into node status (read-only adapter) | a_conductor/graph/lifecycle_bridge.py | P |
| GE-10 | Chaos/E2E scenarios on fault_injection.py (13 program scenarios) | tests/test_graph_chaos.py | G |
| GE-11 | Operator visualization (graph timeline/queues) — UI lane | desktop_ui.py (modified) | P |

Sequencing: 1a→1b→{2,3}→4→5→8 ; 6,7 after GPT design; 9 parallel; 10 last before 11. All Conductor-side; brain untouched (GE-0005).

## Out of scope / forbidden

- No modification of brain schemas/stores; no UI work before GE-11; no weakening of durability invariants; no new worker processes (5-slot topology only).

## Checkpoint — 2026-08-26 / GE-1a + GE-1b implemented (GLM 5.3, GO signal honored)

Branch `feat/ge-1a-graph-domain` from main `a24db2c`, per D5 scope:
- **GE-1a** `a_conductor/graph/domain.py`: `TaskNode` (frozen, NO dependency field per D2 — `dependencies`/`depends_on` deliberately absent, tests assert this), `TaskEdge`, `TaskGraph` invariants (unique ids, endpoint existence, self-edge + duplicate-edge rejection), `DependencyType` exactly the accepted 12 (D4), `TaskNodeStatus` = planning vocabulary only, `CAPABILITY_VOCABULARY` = the 20 awiki-task/v1 values, capability/priority/timeout validation.
- **GE-1b** `a_conductor/graph/graph.py`: `TaskGraphBuilder` (fail-fast, rolls back a cycle-creating edge before raising) + `build_graph` convenience + `_find_cycle` (Kahn + cycle reconstruction; semantics credited to A-Wiki dag_eval per GE-0004/D1 — full DAG engine remains GE-3).
- Tests: `tests/test_graph_domain.py` (14) + `tests/test_graph_assembly.py` (6) = **20 passed**. No scheduler/dispatch/persistence/UI (D5 gate).
- Next node per roadmap: **GE-2** SQLite graph store (`a_conductor/graph/store.py`), then GE-3 DAG port.

## Checkpoint — 2026-08-26 / GE-2 implemented (GLM 5.3)

`a_conductor/graph/store.py` — `GraphStore` with SQLite tables:
`graph_nodes` (JSON per-node dataclass), `graph_edges`, `graph_runs`,
`node_events` (append-only event log per node). Schema version tracked in
`graph_meta`. Per-call connection pattern (same as existing stores).
Full round-trip: save/load/list/delete + node events + enum status
preservation + cycle-rejection survives load. 6 tests in
`tests/test_graph_store.py`. Combined GE suite: 26 passed.

## Checkpoint — 2026-08-26 / GE-3 implemented (GLM 5.3)

`a_conductor/graph/dag.py` — full DAG engine per D1 (dag_eval semantics port):
- `topological_sort(graph) -> DagResult` with Kahn's algorithm, returning
  order + parallel-ready levels + cycle path (if any)
- `compute_ready_levels(graph)` — nodes grouped by execution wave
- `validate_acyclic(graph)` — cycle path or None
- Cycle reconstruction walks the remaining subgraph to name the actual
  cycle, not just flag "cyclic"
- Credit to A-Wiki scripts/eval/dag_eval.py for the algorithmic core
  (ADR GE-0004 decision D1)
- 14 tests in tests/test_graph_dag.py; combined GE suite: 40 passed

Also noted for GPT design lane: project-folder-size monitor with
monochrome gradient particle display (user request, WO-P1-070).

## Checkpoint — 2026-08-26 / GE-4 implemented (GLM 5.3)

`a_conductor/graph/analyze.py` — dependency analyzer:
- `analyze_conflicts(graph) -> ConflictsReport` with derived edges:
  FILE_WRITE (overlapping write_sets, glob-aware), WORKSPACE_WRITE
  (same workspace binding), WORKER (same physical worker binding)
- `_parse_binding` extracts pipe-separated bindings from model_requirement
  (`ws:A:/repo|worker:sunday-worker-1`)
- `_paths_overlap` handles recursive `**` globs (normalized for fnmatch)
- `ConflictsReport` provides `conflict_count(type)` + `already_sequenced`
  (pairs where the planner already declared an edge)
- 12 tests in tests/test_graph_analyze.py; combined GE suite: 52 passed

Design note: bindings in `model_requirement` are a pragmatic carrier
until GE-1a domain gains dedicated fields (future EXTEND per D2).

## Checkpoint — 2026-08-26 / GE-5 implemented (GLM 5.3)

`a_conductor/graph/ready.py` — ReadySet computation:
- `compute_ready_set(graph, node_states) -> ReadySetResult`
- A node is READY when: deps satisfied (preds done/skipped) ∧ no
  write-conflict with running nodes ∧ status == TODO
- `ReadyCheck` per node with typed `Blocker(kind, detail)` list
- `BlockerKind`: DEPENDENCY / RESOURCE / WORKER / GATE
- `ReadySetResult`: checks dict + ready_ids set + blocked_count
- 17 tests in tests/test_graph_ready.py; combined GE suite: 69 passed
- Readiness != execution: scheduler (GE-6) picks from ReadySet by
  capacity/policy — GPT design gate is resolved by ADR GE-0006/0007.

## Checkpoint — 2026-08-26 / GE-6 + GE-7 design accepted (GPT-5.6 Sol MAX)

Design authority is now `docs/adr/GE-0006-event-driven-bounded-scheduler.md` and
`docs/adr/GE-0007-dispatch-through-durable-job-control.md`:
- GE-6 = deterministic event-driven/re-entrant scheduling pass, no hot polling
  loop or background scheduler thread; startup/reconnect/reconcile call the same
  pure scheduling core.
- Current fleet capacity is bounded by injected `max_parallel=5`, actual READY
  worker availability, capability/project/mutation-authority match, existing
  inflight reservations, and resource/gate/provider constraints.
- GE-4 conflict semantics are authoritative and must close conflicts against
  running nodes AND nodes selected in the same scheduling batch.
- GE-7 reuses/wraps the existing durable `job_control.py` / SQLite job store /
  execution coordinator / supervised dedup path. No second graph lifecycle or
  execution store is authorized.
- Stable dispatch identity includes `{graph_id, graph_run_id, node_id}`;
  transport/lease loss triggers durable reconciliation, never blind relaunch.
- A-Wiki remains bridge-only/read-only per GE-0005; its agent-claim TTL is not a
  Conductor execution reservation lease.

**Blocking upstream repair before GE-6 production merge:** merged GE-5 PR #96 uses
literal equality for write-set conflict checks, weaker than GE-4's glob-aware
semantics. `src/**/*.py` vs `src/specific.py` can therefore be marked safe.
GE-6 TDD may begin after the ADR gate because GE-6 independently consumes the
authoritative GE-4 conflict report. Before GE-6 is merged as production-ready,
repair GE-5 by reusing one authoritative GE-4 overlap/conflict seam and add the
regression; do not create duplicate path-overlap logic in `scheduler.py`.
Integrator evidence/comment: PR #96 issue comment `5420827136`.

After the ADR PR is merged, GLM may start GE-6 TDD immediately from ADR GE-0006. GE-005A may land before or during GE-6 implementation but must be green/merged before GE-6 production merge. GE-7 follows GE-6 and must preserve ADR GE-0007's existing-job-control reuse boundary.
## Repo-health reconciliation - 2026-08-29

The original GO/gating text is historical. Accepted main now contains the graph foundation, glob-aware readiness repair and deterministic scheduler, and AHA-4 durable graph dispatch has consumed the accepted GE-7 boundary.

Completed milestones:
- GE-1..GE-5 graph domain/store/DAG/analyze/ready line is merged;
- GE-6/GE-7 design gate merged via PR #97;
- GE-005A glob-conflict repair merged via PR #102;
- GE-6 deterministic scheduler merged via PR #104;
- GE-7 durable graph-dispatch integration is accepted in the AHA-4 line via PR #119.

Still genuinely open from this roadmap:
- GE-8 fan-out/fan-in completeness barriers (barriers.py not present);
- GE-9 lifecycle outcome bridge (lifecycle_bridge.py not present);
- GE-10 graph chaos/E2E program scenarios (test_graph_chaos.py not present);
- GE-11 graph operator visualization/timeline/queues.

Do not mark the parent COMPLETE until GE-8..GE-11 have their own bounded work orders, tests/E2E, PRs and accepted-main evidence.


## GE-8 implementation checkpoint — 2026-08-29

WO-GE-008 implements pure fan-out/fan-in completeness barriers on isolated branch `feat/wo-ge-008-fan-in-barriers` from accepted main `7722374b`.

- fan-in joins derive expected predecessors from TaskGraph incoming edges;
- fan-out parents derive expected children from TaskGraph outgoing edges;
- missing, pending, successful, failed, skipped, and terminal-silent/output-gap states remain distinct;
- completeness is separate from satisfaction: terminal failures can complete a barrier without satisfying it;
- duplicate edge types do not double-count a node; expected output refs are validated/normalized;
- no lifecycle/store/scheduler/dispatch/UI authority is duplicated.

Local evidence at checkpoint: focused 18/18 green; graph-related suite 141/141 green versus pre-GE-8 accepted-main baseline 123. GE-8 remains REVIEW_READY until compile/diff/secret/scope gates, exact-head 3-OS CI, final review, merge, and accepted-main verification complete.


## GE-9 implementation checkpoint — 2026-08-29

WO-GE-009 adds a read-only durable lifecycle projection on isolated branch `feat/wo-ge-009-lifecycle-bridge` from accepted GE-8 main `76a7b55`.

- stable job identity reuses `GraphDispatchKey`;
- durable NEW/PLANNING/READY -> graph TODO;
- claimed/executing/verifying/review/repair states -> graph DOING;
- BLOCKED/RECOVERY_NEEDED/FAILED -> graph BLOCKED;
- COMPLETE -> DONE; CANCELLED -> SKIPPED;
- missing durable jobs -> TODO; non-not-found store failures and identity mismatches fail closed;
- no lifecycle/store/scheduler/dispatch mutation authority was added.

Focused bridge + ReadySet composition evidence is 13/13 green. GE-9 remains REVIEW_READY pending exact graph regression, local gates, exact-head CI, final review, merge and accepted-main verification.

## GE-10 tests-only checkpoint - 2026-08-29

WO-GE-010 composes all 10 existing deterministic FaultScenario cases with GE durable identity/lifecycle semantics plus three graph-specific cases: wrong-repo recovery blocking, durable reopen same-key replay prevention, and fan-in recovery/output completeness.

Focused chaos matrix is 13/13 green; broader graph + fault/recovery/transport regression is 200/200 green. No production source change was needed. GE-10 is REVIEW_READY pending exact-head CI, remote diff re-audit, merge and accepted-main verification.

## GE-8..GE-11 reconciliation — 2026-08-29

Accepted-main evidence now closes GE-8..GE-10:

- GE-8 PR #137 merged as `76a7b55a1b4b8cde32173a7446741db9975c485b` after exact-head 3-OS CI;
- GE-9 PR #138 merged as `da50305961536cc68b072ca99769a9c8e3048ffd` after exact-head 3-OS CI;
- GE-10 PR #139 merged as `1fea5cfffbe9bb8a9093e67dfa1065559e324ab2` after 13-case chaos, broader regression, remote re-audit and 3-OS CI.

GE-11 is the only remaining Graph Engineering roadmap node. Its isolated UI lane is `feat/wo-ge-011-graph-operator-ui` from accepted main `1fea5cf`; local deterministic/UI/E2E gates are green and PR/CI/merge remain outstanding.

## GE-11 accepted-source checkpoint — 2026-08-29

GE-11 operator visualization merged via PR #140 as `392047a0395f30cc1d6ed7d8c2c3f7c0457a5e37`. GE-8/9/10/11 source milestones are now merged; post-merge CI plus GE-11R1 read-only-store hardening remain before graph-lane closeout is declared fully verified.

## Final Graph Engineering closeout - 2026-08-29

Accepted main now contains the complete GE-1..GE-11 roadmap plus the GE-11R1 read-only hardening follow-up. Final slices: GE-8 PR #137 (`76a7b55`), GE-9 PR #138 (`da50305`), GE-10 PR #139 (`1fea5cf`), GE-11 PR #140 (`392047a`), and GE-11R1 PR #142 (`7acb102`). Post-merge main CI remained green through the later accepted main line. Graph Engineering is therefore closed as an implementation roadmap; later graph work requires a new bounded work order rather than reopening this kickoff.
