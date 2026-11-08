# WO-P1-736 Prepared-Run Reconstruction

Issue: [#736](https://github.com/aase7en/A-Wiki-Conductor/issues/736)
Status: CANDIDATE_FROZEN / REVIEW_PASS_R2R3 / CI_PENDING
Frozen candidate hashes (sha256): src `37ca2e8c0563f24c0afb70fee33089ff3a7001111f558e344f85a79492945527` / tests `52889772bba48249bae357944d6321e8f358a94b930b57c894a3a804e21b09bd`; review verdict R3 PASS 0 findings (0/0/0/0)
Classification: R2 with R3-adjacent durable-state read boundary (read-only reconstruction of prepared runs; no writes, no dispatch). Reclassify if the full gate identifies an R3 boundary.
Base: `722c4a516bc9ca27e6bb7c5260fc85a72002293f`
Worktree: `/Volumes/MAC_WORK/DevWorkspace/Github/A-Wiki-Conductor-wo736-bootstrap`
Branch: `docs/wo736-prepared-run-recon`
Mutable bootstrap scope: this document + `CURRENT-WORK.md` + `handoff.md` only.
Implementation reservation (future, gated): NEW `src/a_conductor/prepared_run_reconstruction.py` + `tests/test_prepared_run_reconstruction.py` ONLY; no existing source file edits. This reservation is not a claim or authorization.

## 1. Objective

Provide a read-only prepared-run successor reconstruction seam per #736: given an EXPLICIT graph-run identity and planner-selected node, reconstruct the existing activation request only after validating durable run/node binding and current contract/packet identity. Reuse `GraphStore.load_graph_run` (`src/a_conductor/graph/store.py:1061`), `GraphStore.load_graph_run_bindings` (`src/a_conductor/graph/store.py:1084`), and existing preparation reconstruction logic (`PreparationApplication._reconstruct_activation_request`, `src/a_conductor/graph/preparation_application.py:396`). Verify exact symbols, accessibility, semantics and file:line anchors at the implementation base before implementation; record the verified anchors in evidence.

## 2. Failure Model

Ambiguity, drift, missing or duplicate binding must yield a typed recovery blocker, fail-closed. NEVER prepare a new run, select "latest", dispatch, add a store or scheduler, or write durable state. This seam must not bypass the ORCH-1/7 HOLD in [#709 comment 6719134323](https://github.com/aase7en/A-Wiki-Conductor/issues/709#issuecomment-6719134323): C1 durable claim release, C2 hydrated claim history, and C3 canonical reader rerun are all required before that hold can be reconsidered.

## 3. Acceptance Criteria

Offline deterministic verification only: fixture-owned stores, no network, live runtime or credentials. Write RED-first tests covering:

- Valid reconstruction happy path.
- Foreign or wrong run identity.
- Wrong or non-selected node.
- Changed packet or contract identity (drift).
- Duplicate bindings.
- Missing binding.
- Restart and re-read stability.

Assert all typed blockers with exact reason codes. Define and document the codes in the gated implementation contract before writing tests; do not treat exceptions or generic failures as sufficient evidence.

## 4. Reuse-Before-Build Audit

Before implementation reconcile `next_ready_continuation.py` execution path, `graph/preparation_application.py` prepare path, and `parallel_ready_execution.py` identity checks against the exact base. Prove whether any accepted external caller already provides this reconstruction, including the adviser risk note in #736; record evidence and stop for adjudication if overlap or authority is uncertain. Prefer reuse over a new seam.

## 5. Delivery Gates

Immediately after bootstrap rerun the full entry and mutation gates in `AGENTS.md`, including actual ownership and non-overlap; obtain a claim on #736 before implementation. Freeze the exact candidate SHA, obtain independent review and exact-head CI, and permit merge only by acceptance authority. Evidence destination: `runs/WO-P1-736/`. This packet alone authorizes no implementation, dispatch, merge or runtime action.

## 6. Out Of Scope

ZRA-3G loop composition, parallel fan-in, any /7 mutable-refill surface, and live/runtime activation.
