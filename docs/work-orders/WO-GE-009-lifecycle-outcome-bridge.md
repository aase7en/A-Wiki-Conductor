# WO-GE-009 — Read-only lifecycle outcome bridge

Created: 2026-08-29
Owner: GPT-5.6 Sol Graph Engineering lane
Status: REVIEW_READY / LOCAL_GREEN
Parent: `docs/work-orders/WO-GE-001-graph-engineering-kickoff.md` (GE-9)
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-ge9-lifecycle`
Branch: `feat/wo-ge-009-lifecycle-bridge`
Base: `origin/main@76a7b55a1b4b8cde32173a7446741db9975c485b`

## Goal

Project durable job lifecycle truth into graph `TaskNodeStatus` without creating a second lifecycle or writing either store. The bridge exists only so GE readiness/barriers/operator views can consume current execution truth.

## Reuse-before-build

Classification: **REUSE + WRAP**.

- durable authority remains `JobRuntimeState` / `TaskState` from `job_state.py`;
- stable graph-run/node job identity reuses `GraphDispatchKey.job_id` from GE-7;
- graph planning/execution projection reuses `TaskNodeStatus`; no enum expansion;
- missing job identity is projected as graph TODO, while non-`JOB_NOT_FOUND` store errors propagate fail-closed;
- A-Wiki remains read-only; no brain schema/store mutation.

## Accepted projection design

| Durable `TaskState` | Graph `TaskNodeStatus` | Reason |
|---|---|---|
| NEW / PLANNING / READY | TODO | durable work has not entered an owned execution attempt |
| CLAIMED / GATING / EXECUTING | DOING | worker/execution ownership is active; scheduler must not select again |
| VERIFYING / REVIEW_PENDING | DOING | execution is still unresolved for downstream dependencies |
| CHANGES_REQUIRED / REPAIRING | DOING | repair stays lifecycle-owned; graph must wait, not create a retry edge |
| BLOCKED / RECOVERY_NEEDED | BLOCKED | fail closed while lifecycle requires intervention/reconciliation |
| COMPLETE | DONE | downstream graph dependencies may proceed |
| FAILED | BLOCKED | terminal failure must not satisfy downstream dependency |
| CANCELLED | SKIPPED | matches existing GE-5 skipped-dependency semantics |

The table is exhaustive over the current `TaskState` enum. Future enum additions must fail tests until explicitly classified.

## API boundary

`project_job_state(job) -> TaskNodeStatus` is pure.

`project_graph_node_states(graph, graph_id, graph_run_id, jobs)`:
- derives one `GraphDispatchKey` per graph node;
- calls read-only `jobs.get_job(job_id)` only;
- returns a node-id -> TaskNodeStatus mapping;
- `JOB_NOT_FOUND` => TODO;
- validates returned durable identity matches the requested stable job id;
- performs no transition/checkpoint/create/dispatch/retry/store write.

## Allowed mutable scope

- `src/a_conductor/graph/lifecycle_bridge.py` (new)
- `tests/test_graph_lifecycle_bridge.py` (new)
- this WO
- GE-8 closeout evidence in `WO-GE-008-fan-in-completeness-barriers.md`
- bounded GE-9 checkpoint in parent WO-GE-001

## Forbidden

- `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, WO-P1-102, worker lease source/tests (active PR #131 ownership)
- job state machine/store/control mutation
- graph store/scheduler/dispatch mutation
- UI files
- A-Wiki/live connector/process/secret mutation

## Acceptance

- [ ] every current TaskState has an explicit pinned projection;
- [ ] repair/review states remain unresolved/DOING rather than satisfying dependencies;
- [ ] FAILED and RECOVERY_NEEDED cannot become DONE/SKIPPED;
- [ ] missing durable job => TODO; unrelated store errors fail closed;
- [ ] stable identity reuses GraphDispatchKey and mismatched durable job identity fails closed;
- [ ] bridge port exposes read only `get_job`;
- [ ] focused + graph regression + compile/diff/secret/scope gates green;
- [ ] exact-head 3-OS CI green, final review clean, PR merged and main verified.

## Next

RED exhaustive state mapping and graph projection tests -> implement pure/read-only bridge -> regressions -> PR/CI/re-audit/merge.


## Local verification checkpoint — 2026-08-29

- RED: focused suite failed collection because `a_conductor.graph.lifecycle_bridge` did not exist.
- GREEN: exhaustive state/identity/store tests reached 6/6, then staff review added 7 ReadySet composition cases for **13/13 focused green**.
- Mapping is exhaustive over every current `TaskState`; future enum additions remain unclassified until tests/design are updated.
- `GraphDispatchKey` is the only graph-run/node -> durable job identity seam; missing job projects TODO, other store failures propagate.
- Review/repair states remain DOING so downstream graph dependencies cannot proceed before lifecycle resolution.
- COMPLETE projects DONE; CANCELLED projects SKIPPED; BLOCKED/RECOVERY_NEEDED/FAILED project BLOCKED.
- The bridge has a read-only `get_job` port only and contains no mutation operation.
