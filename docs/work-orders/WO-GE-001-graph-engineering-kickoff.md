# WO-GE-001 — Graph Engineering kickoff: contracts → implementation roadmap

Created: 2026-08-25
Owner: GLM 5.3 (preparation) → GPT-5.6 Sol MAX (integrator decisions) → paired implementation
Status: GO — D1-D5 accepted by GPT-5.6 Sol MAX on 2026-08-26; GE-1 may start. Scheduler implementation remains gated until GE-6 design review.
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
