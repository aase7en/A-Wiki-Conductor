# WO-P1-154 — Fast Execution / Risk-Tier Workflow

Date: 2026-09-04
Owner: GPT-5.6 Sol integrator
Status: READY_FOR_INDEPENDENT_REVIEW / R2 BINDING PROCESS CHANGE
Priority: P1 delivery throughput
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo154-fast-workflow`
Branch: `docs/wo-p1-154-fast-execution-workflow`
Base: `origin/main@1ae477f05e597c5027d22fdb2ca4f1496c070db7`
Classification: `REUSE + WRAP + EXTEND`

## Goal

Increase roadmap delivery throughput toward roughly 2–3x current effective pace without weakening repository safety, evidence quality, truthful state, independent review where risk requires it, or recovery after session/transport loss.

## Problem observed

Recent delivery history shows strong implementation velocity but excessive coordination/verification ceremony around intermediate states:
- full or broad verification repeated before the candidate is stable;
- review repeated on multiple intermediate SHAs;
- temporary RED/adversarial branches or PRs proliferate around one logical work item;
- too many simultaneously open mutable lanes/worktrees increase reconciliation cost;
- SSoT closeout can lag actual Git/GitHub state;
- premium reasoning can be consumed on repetitive implementation/test mechanics better handled by GLM/ZCode or deterministic tools.

The target optimization is **remove repeated ceremony, not assurance**.

## Mutable scope

- `COLLAB.md`
- `PROJECT-PLAN.md`
- `docs/agent-collab/COLLAB_PROTOCOL.md`
- `docs/agent-collab/CAPABILITY_MATRIX.md`
- `docs/agent-collab/FAST_EXECUTION_PROTOCOL.md` (new)
- `docs/plans/2026-09-03-orchestration-decision-plane-roadmap.md`
- `docs/plans/2026-09-04-zero-relay-accelerator-roadmap.md` (new)
- `docs/work-orders/WO-P1-155-zero-relay-accelerator.md` (new queued P0 accelerator)
- this work order

## Protected / deferred scope

Do not edit the following from WO154 because open WO153 already owns them:
- `AGENTS.md`
- `CURRENT-WORK.md`
- `handoff.md`
- `DEFECT_LESSONS.md`

Do not touch WO150/WO152 product source/tests or any live Worker/tunnel/provider state.

## Binding design decisions

1. Classify every task as R0/R1/R2/R3 and run the shortest workflow that preserves the required assurance.
2. Keep repository/ownership/secret/destructive-operation gates mandatory at every tier.
3. During implementation run targeted/relevant verification first; defer full-suite, hosted CI and release E2E to the frozen candidate/release gates unless early broad verification is specifically justified.
4. Batch adversarial cases before independent review instead of opening one review cycle per defect.
5. Independent review binds to a **Frozen Candidate SHA**, not every intermediate SHA.
6. Default to one feature PR per WO. Temporary RED/adversarial branches stay local/ephemeral unless remote CI or independent collaboration genuinely requires a remote branch.
7. Limit active work to **3 mutable implementation lanes + 1 independent read-only review lane**. Keep a fifth worker/spare capacity for recovery/blockers rather than filling every slot.
8. GPT integrator retains architecture, trust-boundary, cross-lane adjudication, SSoT, merge/release and final acceptance authority.
9. GLM-5.3/ZCode is preferred for bounded repository implementation, mechanical refactor, test generation, debugging, repair batches, code archaeology and adversarial review when current provider/tool readiness allows it.
10. Deterministic tools remain acceptance authority; model confidence or `DONE` is never enough.
11. Same material failure twice without new evidence triggers root-cause/no-progress handling instead of another blind retry.
12. SSoT checkpoints are required at meaningful boundaries (claim/ownership change, blocker, frozen candidate, merge/release, handoff/session rollover), not after every trivial edit.
13. User-prioritized accelerator dependencies may supersede lower-leverage roadmap feature order when they demonstrably reduce repeated human relay/coordination cost without weakening safety. `WO-P1-155` Zero-Relay Accelerator is therefore P0 ahead of broad ODP continuation.

## Acceptance

- A binding fast-execution protocol defines R0–R3 loops, escalation conditions, WIP limits, frozen-candidate review, batch verification, role routing and no-progress handling.
- Existing collaboration protocol points to the new risk-tier flow instead of requiring the heaviest path for every material task.
- ODP roadmap explicitly preserves risk-tier assurance and safe parallelism.
- Capability routing documents current official ZCode evidence without turning a provider/model name into authority.
- Zero-Relay Accelerator is captured as a bounded P0 prerequisite with explicit reuse boundary, R3 gates, fail-closed behavior and an exit back to ODP; it does not silently broaden WO154 into source/runtime mutation.
- No source/runtime behavior changes.
- Diff is confined to the declared docs scope and contains no secrets.
- Markdown/UTF-8 and repository diff checks pass.

## Verification plan

- `git diff --check`
- inspect `git diff --name-only` against mutable scope
- search for accidental weakening of mandatory safety/acceptance language
- verify no overlap with currently fetched WO150/WO152/WO153 changed-file sets
- because this changes binding delivery/assurance policy, classify WO154 as `R2`; freeze an exact candidate SHA and require an independent read-only policy review before merge.

## Verification checkpoint — pre-freeze 2026-09-04

- `git diff --check`: PASS.
- UTF-8 decode across all 7 WO154 files: PASS.
- secret-pattern scan: PASS.
- changed-file overlap against fetched WO150/WO152/WO153 branches: `NO_OVERLAP` for every compared branch.
- ZCode CLI is not available on this host (`ZCODE_CLI_NOT_AVAILABLE`), so an automatic independent GLM review cannot be invoked from this execution surface. R2 merge therefore remains blocked until a separate read-only reviewer examines the frozen candidate.

## Checkpoint

WO154 is intentionally disjoint from WO153. `CURRENT-WORK.md` and `handoff.md` fold-back are deferred until WO153 releases those hotspot files; this work order is the authoritative checkpoint for WO154 meanwhile. The exact frozen commit SHA is recorded in the assurance packet/PR after commit, avoiding a self-referential SHA edit.
