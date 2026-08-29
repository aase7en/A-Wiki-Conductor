# WO-GE-008 — Fan-out / fan-in completeness barriers

Created: 2026-08-29
Owner: bounded Graph Engineering implementation lane
Status: COMPLETE / MERGED — PR #137 (`76a7b55`)
Parent: `docs/work-orders/WO-GE-001-graph-engineering-kickoff.md` (GE-8)
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-ge8-barriers`
Branch: `feat/wo-ge-008-fan-in-barriers`
Base: `origin/main@7722374b0e28f3943037c48e7a7463a4e4370ad2`

## Goal

Implement the pure graph-owned completeness barrier required by ADR GE-0001 without creating a second lifecycle, store, scheduler, executor, retry loop, or A-Wiki runtime dependency.

A join node must be able to distinguish expected predecessor children that are missing, observed-but-pending, terminal-successful, terminal-failed, intentionally skipped, or terminal-but-silent because declared `expected_outputs` are absent.

## Reuse-before-build

Classification: **EXTEND + REUSE**.

- dependency membership reuses the same `TaskGraph.edges_to(target)` relation consumed by GE-5 readiness; no second dependency list;
- expected output declarations reuse `TaskNode.expected_outputs` from ADR GE-0002;
- A-Wiki `main@290626ba16272f54742b6ebac8981629b04b3131` `scripts/eval/dag_eval.py` was checked read-only: its merge stage waits for all `depends_on` and consumes predecessor outputs. Only that fan-in semantic is reused; its eval executor/thread pool is not copied;
- lifecycle terminal/success/failure truth is injected as an observation and is not inferred from planning `TaskNodeStatus`; GE-9 will own the later read-only lifecycle projection.

## Allowed mutable scope

- `src/a_conductor/graph/barriers.py` (new)
- `tests/test_graph_barriers.py` (new)
- this WO
- bounded GE-8 checkpoint in `docs/work-orders/WO-GE-001-graph-engineering-kickoff.md`

## Forbidden

- `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, WO-P1-102, `worker_lease.py` and its tests (active Draft PR #131 ownership);
- `ready.py`, `scheduler.py`, `store.py`, dispatch/job lifecycle source;
- UI files;
- A-Wiki mutation;
- live connectors/processes/secrets.

## Contract

`FanInChildObservation` is explicit evidence for one predecessor:
- `terminal=False` => pending;
- `terminal=True, successful=True` => successful terminal child;
- `terminal=True, skipped=True` => intentionally skipped terminal child;
- `terminal=True` with neither success nor skip => failed terminal child;
- successful/skipped children that declared `expected_outputs` must present those exact output refs or they are `silent`.

Barrier result separates:
- `is_complete`: no missing, pending, or silent-output child remains;
- `is_satisfied`: complete AND no failed child.

A terminal failure is therefore complete-but-unsatisfied. Missing evidence is never silently treated as TODO/success. Duplicate incoming edge types from the same predecessor count as one expected child.

## Acceptance

- [ ] RED tests prove module/behavior absent before implementation.
- [ ] Root/no-predecessor barrier is vacuously complete+satisfied.
- [ ] Missing, pending, success, failure, skip and silent-output cases are distinct and deterministic.
- [ ] GE-5 compatibility: all incoming graph predecessors are barrier children; skipped can satisfy only when no declared output is missing.
- [ ] Duplicate predecessor edges count once; extra valid global observations do not become dependencies.
- [ ] Invalid observation invariants and unknown target fail closed.
- [ ] Existing graph suite plus new tests pass.
- [ ] `compileall`, `git diff --check`, scope and secret gates pass.
- [ ] Exact-head 3-OS CI green; final diff re-audited; PR merged and `origin/main` verified.

## Verification baseline

Before mutation, accepted main graph suite: **123 passed**.

## Next

TDD: add focused RED tests -> implement pure `barriers.py` -> focused + full graph regression -> review/debug -> PR/CI/re-audit/merge.


## Local verification checkpoint — 2026-08-29

- RED #1: initial focused suite failed collection because `a_conductor.graph.barriers` did not exist.
- GREEN #1: initial fan-in contract reached 14/14 focused tests.
- Staff review found the ADR/roadmap requires both fan-out parent completeness and fan-in join completeness, not only incoming join predecessors.
- RED #2: 4 regressions proved missing fan-out API, unnormalized observed output refs, and blank declared output fail-open behavior.
- GREEN #2: focused suite **18 passed**; graph-related regression **141 passed** (accepted-main baseline before GE-8: 123).
- API remains pure/read-only: no scheduler/store/lifecycle/retry/execution/UI authority was added.
- `evaluate_fan_in_barrier()` derives expected predecessors from `edges_to(join)`; `evaluate_fan_out_barrier()` derives expected children from `edges_from(parent)`; duplicate edge types count one node.
- Output refs are normalized; blank declared output refs fail closed; terminal failure is complete-but-unsatisfied; skipped/successful terminal nodes with missing declared outputs remain silent/incomplete.


## Accepted-main closeout — 2026-08-29

- implementation commit `b627ffafe0a7073fa6e19fbf2ce697b1db7efa8b` opened PR #137;
- exact-head CI run `33233102964` passed Windows test/build/frozen/Portable archive plus Ubuntu/macOS smoke;
- final PR state was CLEAN / MERGEABLE with exactly 4 scoped files and no review threads;
- PR #137 squash-merged as `76a7b55a1b4b8cde32173a7446741db9975c485b` and ancestry was verified on `origin/main`;
- clean feature worktree/local/remote branch were removed after ancestry proof.

GE-8 is complete. GE-9 consumes this accepted main and does not reopen barrier semantics unless new deterministic evidence requires a repair WO.
