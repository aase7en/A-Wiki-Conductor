# WO-GE-001 — Graph Engineering kickoff: contracts → implementation roadmap

Created: 2026-08-25
Owner: GLM 5.3 (preparation) → GPT-5.6 Sol MAX (integrator decisions) → paired implementation
Status: AWAITING GPT FAN-IN (GE-0 complete; nothing here is approved until GPT marks the ADRs accepted)
Inputs: GE-0 status report + A-Wiki reuse gate (session records 2026-08-25); ADR drafts GE-0001..0005 in this branch.

## Decision briefs (answer these and GE-1 can start)

- **D1 (GE-0004):** DAG engine = port dag_eval semantics with credit? [GLM recommends YES]
- **D2 (GE-0002):** graph fields live Conductor-side, awiki-task/v1 untouched? [GLM recommends YES]
- **D3 (GE-0005):** A-Wiki access conductor-bridge-only + CI grep gate? [GLM recommends YES]
- **D4:** accept GE-0003's 12 DependencyTypes as the initial vocabulary?
- **D5:** GE-1 first implementation node = `a_conductor/graph/` package (domain + DAG) with tests only, no scheduler yet?

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
