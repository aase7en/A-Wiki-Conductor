# WO-P1-424 — COCKPIT-1 Runtime Cockpit MVP durable truth projection

Status: CLAIMED / READY_FOR_IMPLEMENTATION
Issue: #424
Identity schema: GITHUB_ISSUE_V1
Topology: CONTROL_PLANE_ONLY
Risk: R2 — read-only shared operator projection + desktop integration

## Binding

- authority/execution repo: `A:\\GitHub\\A-Wiki-Conductor`
- isolated worktree: `A:\\GitHub\\_worktrees\\A-Wiki-Conductor-wo424-cockpit1`
- branch: `feat/wo-p1-424-cockpit1-runtime-cockpit`
- bootstrap base SHA: `bd4892185195d8c6a7c3a8652a75ec4db7f003b4`
- current-main re-pin accepted: `7394322f14b6878c0c7fef61c618b9ae31898a72`
- post-fan-in branch anchor before source mutation: `2013145f352945bfd1c71cc962d5d906db219bae`
- claim: `WO-P1-424-COCKPIT1-RUNTIME-COCKPIT-001`
- owner: bounded implementation lane selected by A-Faster; GPT-5.6 Sol remains integrator/acceptance authority.
- evidence destination: `runs/WO-P1-424/`
- replay safety: recover pointer/process/result/Git before any redispatch; RUNNING is never duplicated.

## Dependency gates

Satisfied:
- GOT chain accepted, including WO-P1-419 post-main verification.
- FMG-1 accepted local-only at exact compatibility set:
  `{A-Wiki-Conductor@bd4892185195d8c6a7c3a8652a75ec4db7f003b4, SunDayRemoteMCP@7c3c048d3d21291e842a944e50ecf0ca5d71f475}`.
- COCKPIT-0 shaping #421 re-pinned on `bd489218...` and classified `READY_AFTER_FMG`.

Still intentionally UNKNOWN at bootstrap:
- durable desktop Hook read-back is not accepted; Hook-derived cockpit fields MUST render UNKNOWN.
- WTL-1 is not accepted on main; WTL-derived cockpit fields MUST render UNKNOWN until a later accepted re-pin.

## Goal

Deliver the smallest usable read-only Runtime Cockpit inside the existing desktop stack. The cockpit is a projection/consumer of accepted durable/operator truth; it is never a new task database, monitor store, scheduler, claim/review/completion authority, retry engine, or command gateway.

`DURABLE AUTHORITY -> READ-ONLY COCKPIT PROJECTION -> EXISTING DESKTOP UI`

not:

`COCKPIT DB -> TASK TRUTH`

## Exact mutable scope

Only:
- `src/a_conductor/cockpit_projection.py` — NEW pure/read-only immutable projection composer.
- `src/a_conductor/desktop_control.py` — MODIFY only for one bounded read-only facade/composer seam.
- `src/a_conductor/desktop_ui.py` — MODIFY only for one compact Runtime Cockpit surface on the existing monitor refresh cadence.
- `tests/test_cockpit_projection.py` — NEW focused projection/service/UI-boundary tests.
- `docs/work-orders/WO-P1-424-cockpit1-runtime-cockpit.md` — this contract/checkpoint.

Any required tracked path outside this set => `SCOPE_EXPANSION_REQUIRED` and source mutation stops.

## Reuse / no-new-authority boundary

Prefer REUSE/WRAP:
- `ControlCenterService.snapshot()`;
- `DesktopControlService` existing read facade patterns;
- graph operator view;
- provider operator view;
- existing job/execution/lease/process observation surfaces;
- accepted DEX identity/digest and execution receipt semantics;
- accepted production-closeout observation DTO/ports as provenance vocabulary where applicable;
- existing desktop monitor tick/scheduling.

Forbidden:
- new DB/store/schema or migration;
- new task/job/claim/lease/review/completion state machine;
- new scheduler/thread/timer;
- new retry/reassign/cleanup/merge/accept/restart command;
- subprocess spawn from periodic UI paths;
- PID existence as process authority;
- inference of truth from branch names, filenames, prose, age, labels, or missing data;
- DWB C#/XAML/dashboard code copying;
- changes to `PROJECT-PLAN.md`, `CURRENT-WORK.md`, `handoff.md`, or `COLLAB.md`;
- WTL-2 cleanup implementation;
- Hook/STM store or read-back invention.

## Immutable projection contract

Create one immutable cockpit snapshot/DTO with explicit provenance for displayed facts. At minimum project the roadmap one-screen fields when authority exists:
- Work Order/task;
- topology;
- lane/executor/provider/harness;
- authority repo;
- execution repo;
- active repo/worktree/branch/HEAD;
- claim/lease state;
- execution ID + exact process identity when proven;
- derived execution state;
- last activity;
- last meaningful progress;
- verification/review/CI gate state;
- blocker code;
- replay safety;
- exact next safe action (descriptive only).

Missing/unavailable/unaccepted evidence is `UNKNOWN` or `EVIDENCE_INCOMPLETE`, never false/zero/absent by implication.

One rendered snapshot must be internally consistent. If a bounded re-pin detects source drift, emit `STALE` / `EVIDENCE_INCOMPLETE` instead of mixing observations from different identities.

## Operator vocabulary

Use/normalize without inventing a new lifecycle:
- `NOT_DISPATCHED`
- `PENDING_SCOPE`
- `RUNNING`
- `WAITING_EXTERNAL`
- `STALLED_RECONCILE`
- `TERMINAL_UNHARVESTED`
- `OUTCOME_UNKNOWN`
- `FAILED_VERIFIED`
- `COMPLETED_VERIFIED`

Explicit `UNKNOWN`, `STALE`, and degraded-observability markers may accompany the state.

Never label retry safe merely because transport disconnected.

## Desktop integration

- extend the existing desktop monitor refresh cadence; do not add a second timer;
- render a compact/readable Runtime Cockpit section;
- no consequential cockpit buttons;
- existing safe Start/Stop controls remain where they already exist and retain their existing authority;
- UI render must be passive over the injected/read-only projection;
- avoid subprocess/network work on the Tk main thread.

## RED-first acceptance matrix

Before/with implementation prove:
1. provenance mismatch cannot render `RUNNING` or `COMPLETED_VERIFIED`;
2. re-pin/source drift returns `STALE`/typed blocker, never a mixed snapshot;
3. unavailable Hook/WTL/review/remote/process evidence stays explicit UNKNOWN/EVIDENCE_INCOMPLETE;
4. PID without exact process provenance is not displayed as authoritative running identity;
5. transport-exited/ambiguous result maps to `OUTCOME_UNKNOWN` or `STALLED_RECONCILE`, not success;
6. missing verify/review/merge/post-main proof cannot become complete;
7. exact accepted evidence can render `COMPLETED_VERIFIED`;
8. deterministic identical inputs yield identical snapshot/fingerprint/render data;
9. cockpit adds no command authority and no new timer;
10. real-service smoke through existing DesktopControlService/read-only authorities returns a coherent snapshot without writing durable state.

## Verification

- RED-first focused tests;
- `python -m pytest tests/test_cockpit_projection.py -q`;
- directly related desktop-control / control-center / graph-operator / provider-operator / continuity / execution observation tests selected by changed seam;
- source compile/import checks;
- exact-path scope;
- `git diff --check`;
- strict UTF-8 / no U+FFFD;
- added-line fake-secret scan;
- independent exact-SHA R2 review;
- exact-head hosted CI;
- expected-head merge and post-main verification.

## Completion

Agent/GLM DONE is only a claim. Completion requires frozen exact SHA, deterministic evidence, independent exact-SHA R2 review with P0/P1/P2=0, exact-head CI, GPT acceptance/merge, post-main verification, and durable checkpoint.

