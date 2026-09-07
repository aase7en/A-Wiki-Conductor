# WO-P1-166 — P0-B Continuity Guard / GoalCloseout Authority

Date: 2026-09-08
Owner: GPT1 architecture / exact-SHA acceptance; GLM-5.3 MAX bounded implementation after activation
Status: ACTIVATION_FOLD_CANDIDATE / CONDITIONAL_RELEASE
Durable issue: GitHub Issue #226
Risk: R3 CRITICAL
Repository: `aase7en/A-Wiki-Conductor`
Activation branch: `docs/wo-p1-166-p0b-activation`
Activation base: `origin/main@8ffd12f8de3cada79f1f463f3c6f7ee7a35082b9`

## Goal

Add one fail-closed continuity authority layer over existing A-Conductor factual authorities so mutation and goal completion cannot rely on stale chat/projection state.

Target order:

`P0-B1 classification -> P0-B2 mutation gate -> P0-B3 GoalCloseout -> P0-B4 single-writer projections -> P0-B5 vendor adapters -> P0-B6 GPT/Codex CI backstop -> ZRA-2 WO165`

## Reuse-before-build classification

REUSE / EXTEND only:
- `TaskState` and `RecoveryClassification`;
- `SQLiteJobStore` ordered CREATED / TRANSITION / CHECKPOINT evidence;
- `WorkerLeaseBroker` / `SQLiteWorkerLeaseStore`;
- `AgentResultPacket` / `AgentChangeApplier`;
- actual Git/GitHub repository evidence;
- existing review/provider/execution authorities.

FORBIDDEN: second scheduler, job store, work-order system, claim store, lease store, retry engine, ReviewBus/review authority, or shadow live-state database.

## P0-B1 contract — pure classification

Phase A creates a pure module with no Git/process/network/file/provider mutation. It consumes an immutable factual projection and returns deterministic continuity findings.

Required classifications:
- `FRESH`
- `STALE_LOCAL_CHECKOUT`
- `HEAD_DRIFT`
- `WORKTREE_DIRTY_OR_UNKNOWN`
- `CLAIM_CONFLICT`
- `SSOT_DRIFT`
- `MERGED_NOT_FOLDED`
- `RECONCILE_REQUIRED`
- `UNKNOWN`

Decision contract:
- `FRESH` only when every required factual invariant is proven compatible;
- any non-FRESH finding yields `safe_to_mutate = False`;
- `UNKNOWN` always fails closed;
- output includes ordered findings, primary classification, typed reasons, and required reconciliation actions;
- factual Git/runtime/job/lease authority outranks `CURRENT-WORK.md`, `handoff.md`, and `COLLAB.md` projections;
- classification does not itself acquire/release leases, fetch Git, dispatch providers, or write projections.

## Phase-A mutable scope after activation merge

NEW-FILE-ONLY:
- `src/a_conductor/continuity_guard.py`
- `tests/test_continuity_guard.py`
- this WO checkpoint file

Read-only until explicit scope expansion:
- `job_state.py` / `job_store.py`
- `worker_lease.py`
- `agent_change_packets.py`
- provider/execution authorities
- `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`
- WO165 / ZRA-2 source scope

## Phase-A RED acceptance matrix

1. fully complete/consistent/clean snapshot -> `FRESH`, safe true;
2. missing critical factual field -> `UNKNOWN`, safe false;
3. expected/local/remote head mismatch -> `STALE_LOCAL_CHECKOUT` or `HEAD_DRIFT`, safe false;
4. dirty or unknown protected worktree -> `WORKTREE_DIRTY_OR_UNKNOWN`, safe false;
5. lease owner or mutable-scope conflict -> `CLAIM_CONFLICT`, safe false;
6. human-readable projection contradicts factual authority -> `SSOT_DRIFT`, safe false;
7. accepted merge exists but required fold/release is incomplete -> `MERGED_NOT_FOLDED`, safe false;
8. deterministic reconciliation is required before work -> `RECONCILE_REQUIRED`, safe false;
9. multiple simultaneous defects return deterministic ordered findings and a stable primary classification;
10. repeated classification of the same snapshot is idempotent.

## R3 assurance

RED first -> bounded implementation -> targeted/related tests -> adversarial matrix -> frozen exact SHA -> independent review -> exact-head hosted CI -> GPT1 acceptance/merge -> post-main verification. GLM does not self-merge.

## ZRA-2 dependency correction

WO-P1-165 / Issue #214 remains queued and source-blocked until P0-B is accepted/merged/post-main reconciled. Preserve its existing activation branch; do not rebind or duplicate it.

## Activation self-closing invariant

This docs activation owns only the four activation documents. Once this exact activation projection is present on `origin/main` and required exact-head review/CI succeed, the activation hotspot claim has no remaining mutable scope and is RELEASED without another global-file rewrite. P0-B1 source work then requires a fresh isolated worktree/claim from the new main.
