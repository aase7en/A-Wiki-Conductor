# WO-P1-198 — ZRA-4 deterministic batch identity gate

Status: BLOCKED_ZRA3_AND_C1_ACCEPTANCE / IMPLEMENTATION_PACKET_READY
Owner: GPT-5.6 Sol integrator
Parent: Issue #216 / GPT1-ZRA4-PREFLIGHT-001
Date: 2026-09-11 (Asia/Bangkok)
Risk: R3 when source mutation begins; activation is docs-only.
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo198-zra4-batch`
Branch: `docs/wo-p1-198-zra4-batch-identity-gate`
Base: `origin/main@46f90b329d4991211f5c8a26406f3aca2162e9a7`

## Gate

Do not mutate product source until:

1. ZRA-3 is accepted;
2. C1/C1b physical identity hardening is accepted (WO196 design + released WO197 implementation); and
3. Issue #216 explicitly releases C2 implementation.

## Objective

Remove caller-chosen provider batch identity from ZRA-4 fan-out. For a selected parallel set, derive one deterministic, restart-stable batch identity from durable graph/dispatch identity so retries/restarts/reordered inputs cannot acquire unrelated provider-admission batches for the same logical dispatch set.

This does not add a provider admission store or scheduler. Existing provider/ParallelReady authorities remain owners.

## Existing authority

`GraphDispatchKey.job_id` is already deterministic SHA-256 over canonical JSON of:

- `graph_id`
- `graph_run_id`
- `node_id`

C2 should reuse those job IDs rather than inventing a second node identity.

## Required identity rule

Preferred versioned shape:

```text
selected_job_ids = sorted(unique(GraphDispatchKey(...).job_id for selected nodes))
material = b"zra4-batch-v1\0" + canonical_graph_run_id + b"\0" + b"\0".join(selected_job_ids)
batch_id = "zra4b1:" + sha256(material).hexdigest()
```

Including `graph_id` explicitly is allowed if the final contract is versioned and documented; selected job IDs already bind graph_id/run/node.

The caller must not be allowed to supply an arbitrary competing batch ID for the same ZRA-4 execution path.

## Initial mutable scope after release

Re-pin after dependencies are accepted. Preferred seams:

- `src/a_conductor/parallel_ready_execution.py`
- `src/a_conductor/elastic_worker_capacity.py` only if that is the production composition caller
- a small new identity helper module if it prevents duplicated hashing logic
- focused tests only

Do not change provider admission semantics, GraphDispatch identity, or scheduler ordering.

## RED-first matrix

Before GREEN prove at least:

1. same selected set in different input order -> same batch ID;
2. restart/re-observation -> same batch ID;
3. duplicate selected node IDs are rejected or canonicalized exactly once by a documented rule;
4. empty selection cannot create a mutation batch;
5. different graph_run_id -> different batch ID;
6. different selected GraphDispatch job set -> different batch ID;
7. foreign graph/run job identity is rejected before hashing;
8. arbitrary caller batch ID cannot override derived identity on ZRA-4 path;
9. 2-lane and 3-lane sets are deterministic;
10. partial selection after scheduler block has a distinct identity from the larger set and only represents the set actually admitted for that tick;
11. provider generation drift continues to fail closed through existing admission authority;
12. duplicate/restart attempts reconcile to existing admission/dispatch rather than open a second logical batch;
13. human relay count remains zero.

## Verification floor

- focused batch identity tests;
- ParallelReady execution tests;
- provider configuration/admission tests;
- elastic worker capacity tests if touched;
- graph dispatch/scheduler tests;
- compile/import;
- `git diff --check`;
- strict UTF-8/no U+FFFD;
- added-line secret scan;
- exact changed-scope audit;
- hosted CI on frozen exact SHA.

## ZRA-4 release condition

C2 completion still does not authorize live fan-out by itself. Live 2–3 lane proof requires C1/C1b + C2 accepted, compatible Worker claims/leases, non-overlapping physical mutation resources, provider capacity, exact task packets and bounded recovery semantics.

Until released, final state is `BLOCKED_ZRA3_AND_C1_ACCEPTANCE`.
