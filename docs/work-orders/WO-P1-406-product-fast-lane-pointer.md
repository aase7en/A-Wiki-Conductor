# WO-P1-406 — Product Fast Lane pointer and legacy roadmap reconciliation

Status: ACTIVE / CLAIMED
Issue: #406
Risk: R2 — roadmap/authority documentation
Topology: CONTROL_PLANE_ONLY

## Binding
- Authority repo: `A:\GitHub\A-Wiki-Conductor`
- Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo406-product-fast-lane-pointer`
- Branch: `docs/wo-p1-406-product-fast-lane-pointer`
- Base: `c85484c23f6de86cf69edf1df6ab8b6e003cefd9`
- Claim: `WO-P1-406-PRODUCT-FAST-LANE-POINTER-001`
- Owner/integrator: GPT-5.6 Sol
- Evidence: `runs/WO-P1-406/`

## Goal

Make fresh-session “use A-Faster and continue the roadmap” resolution deterministic by reconciling the long-lived PROJECT-PLAN overlap first, preserving unique valid intent, then adding one concise Product Fast Lane pointer to the accepted 2026-09-20 DWB convergence roadmap / LOCAL-USABLE-1.

## Initial mutable scope
- `docs/work-orders/WO-P1-406-product-fast-lane-pointer.md`

`PROJECT-PLAN.md` remains READ_ONLY until PR #243 and stacked PR #244 are reconciled and the exact disposition is recorded in Issue #406.

After the overlap gate passes, mutable scope MAY expand exactly to:
- `PROJECT-PLAN.md`
- this WO file

No `CURRENT-WORK.md`, `handoff.md`, or `COLLAB.md` mutation is authorized in this lane.

## Reconciliation contract

For PR #243/#244:
- inspect exact diffs and current-main equivalent content;
- classify every unique roadmap intent as KEEP, DEFER or SUPERSEDED;
- preserve unique valid intent through an existing canonical roadmap pointer where possible;
- never discard unique work merely because the PR is old;
- closing/retargeting obsolete drafts is GitHub metadata only; never delete branches/worktrees as part of this WO;
- only after overlap is cleared may PROJECT-PLAN receive a concise pointer, not another duplicate full roadmap.

## Legacy roadmap overlap disposition — 2026-09-20

Read-only reconciliation against current `origin/main@c85484c23f6de86cf69edf1df6ab8b6e003cefd9`:

### PR #243 / WO-P1-170 — custom provider settings

Disposition: `KEEP_AS_DEFERRED_HISTORY`.

Still-valid unique intent:
- a future provider-neutral Settings/Advanced console for Base URL, protocol family, masked credential replacement, model-list management, Test and Enable/Disable;
- reuse existing provider/secret/readiness/admission authorities;
- never equate CONFIGURED with READY/AUTHORIZED/ADMITTED;
- do not create a second provider registry/router/secret store.

Why it does not remain an active PROJECT-PLAN writer:
- it was explicitly deferred behind the earlier Zero-Relay frontier;
- current product-fast-lane priority is LOCAL-USABLE-1;
- the detailed proposal remains fully preserved in PR #243 / its branch and commit history;
- current main already has provider/operator/runtime authorities that must be re-pinned when this UX is eventually promoted.

Action: close PR #243 as a preserved deferred historical proposal after stacked child #244 is closed. Do not delete its branch.

### PR #244 / WO-P1-171 — AEET

Disposition: `SUPERSEDED_AND_DEFERRED_HISTORY`.

Current-main mappings:
- minimality/YAGNI guidance -> accepted A-Faster Ponytail advisory layer;
- effective route/capability proof -> current provider/harness admission/readiness and A-Faster route gates;
- trace/operational observability -> accepted Hook/STM/Monitor roadmap;
- replay/operation identity -> DEX + durable A-Faster lane/run pointers;
- provenance/trust boundaries -> current claim/admission/review evidence rules;
- evaluator/adversarial/scoreboard/sanitized-feedback ideas remain future candidates, not current fast-lane authority.

The proposal is useful historical/research evidence but should not append another 134-line active roadmap block to PROJECT-PLAN now. Its exact content remains preserved in PR #244 / branch history plus existing Issue #233 / WO174 references on main.

Action: close PR #244 first as superseded/deferred historical proposal. Do not delete its branch.

### Scope release

After both draft PRs are closed with explanatory comments, `PROJECT-PLAN.md` overlap is considered released for this WO. The mutable scope then expands exactly to:
- `PROJECT-PLAN.md`
- this WO file.

No other roadmap/source/continuity file is authorized.

## Acceptance
- current accepted roadmap at `docs/plans/2026-09-20-dwb-convergence-product-acceleration-roadmap.md` is reachable from PROJECT-PLAN after the overlap gate;
- LOCAL-USABLE-1 and its fast-lane dependency order are summarized concisely;
- old roadmap history under `docs/plans/`, WOs, Issues/PRs/commits remains preserved;
- no duplicate task/roadmap authority;
- deterministic diff/UTF-8/reference/secret/scope checks;
- independent review per risk;
- exact-head CI;
- expected-head merge + post-main verification.

## Replay safety

A fresh session must re-read PR #243/#244 state before touching PROJECT-PLAN. If either overlapping branch has changed since the recorded disposition, fail closed and re-reconcile.
