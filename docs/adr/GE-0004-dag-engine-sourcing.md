# GE-0004 — D1: DAG engine sourcing (port A-Wiki dag_eval semantics with credit)

Status: ACCEPTED — GPT-5.6 Sol MAX integrator decision, 2026-08-26
Date: 2026-08-25
Evidence: A-Wiki `scripts/eval/dag_eval.py` — proven parse → Kahn topological sort + cycle detection → parallel-within-level execution → merge fan-in with `{id.output}` substitution (+ `evals/subagents/pipeline-council.json`, `pipeline_graph.py` visualizer).

## Recommendation

**Port, don't link.** Vendor the algorithm semantics into a Conductor-owned module (e.g. `a_conductor/graph/dag.py`) with a NOTICE crediting A-Wiki's dag_eval as lineage (same pattern as `conductor/NOTICE` credits Serena). Do NOT add a runtime cross-repo dependency (A-Wiki is the brain under user HOLD; Conductor must stay executable standalone) and do NOT reimplement from scratch (proven prior art exists — blind reimplementation violates the reuse gate).

## Scope of the port for GE-3

parse/validate, Kahn topo sort with cycle error naming the cycle, ready-level computation. Execution/fan-in stays Conductor-side (scheduler + completeness barriers per GE-0001) — dag_eval's executor is eval-scoped.

## Alternatives

- WRAP via import from A-Wiki checkout: fragile path coupling, violates standalone.
- NEW from scratch: duplicate proven code, gate says prefer reuse.
