# WO-P1-424 — COCKPIT-1 Runtime Cockpit MVP durable truth projection

Status: FOUNDATION_RESCOPED / READY_FOR_FOUNDATION_EXACT_SHA_R2_REVIEW
Issue: #424
Identity schema: GITHUB_ISSUE_V1
Topology: CONTROL_PLANE_ONLY
Risk: R2 — read-only shared operator projection + desktop integration

## Binding

- authority/execution repo: `A:\\GitHub\\A-Wiki-Conductor`
- isolated worktree: `A:\\GitHub\\_worktrees\\A-Wiki-Conductor-wo424-cockpit1`
- branch: `feat/wo-p1-424-cockpit1-runtime-cockpit`
- bootstrap base SHA: `bd4892185195d8c6a7c3a8652a75ec4db7f003b4`
- current-main re-pin accepted: `27d644405f008e50771599d08669893e5caa80f6`
- post-fan-in branch anchor before source mutation: `2013145f352945bfd1c71cc962d5d906db219bae`
- claim: `WO-P1-424-COCKPIT1-RUNTIME-COCKPIT-001`
- owner: bounded implementation lane selected by A-Faster; GPT-5.6 Sol remains integrator/acceptance authority.
- evidence destination: `runs/WO-P1-424/`
- replay safety: recover pointer/process/result/Git before any redispatch; RUNNING is never duplicated.

## Dependency gates

Satisfied:
- GOT chain accepted, including WO-P1-419 post-main verification.
- FMG-1 repaired acceptance is current and local-only at exact compatibility set:
  `{A-Wiki-Conductor@27d644405f008e50771599d08669893e5caa80f6, SunDayRemoteMCP@2e6aeabd09a321232098187dba4c522e37e4b1de}`.
  The authority re-pin from `7394322...` to `27d6444...` adds only accepted WTL-1 paths and does not alter the FMG/DEX authority blobs.
  The earlier `7c3c048...` completion marker is superseded by the post-mutation outcome-integrity repair and focused independent R3 rereview.
- COCKPIT-0 shaping #421 re-pinned on `bd489218...` and classified `READY_AFTER_FMG`.

Still intentionally UNKNOWN at this candidate:
- durable desktop Hook read-back is not accepted; Hook-derived cockpit fields MUST render UNKNOWN.
- WTL-1 is accepted on main at `27d6444...`, but COCKPIT-1 does not add a WTL read-back adapter in this slice; WTL-derived cockpit fields remain UNKNOWN unless an already-accepted read seam is reused without widening authority.

## Recovery checkpoint after interrupted author attempt

- `run:WO-P1-424:author:1:a1:948e2e42538f` terminated with harness exit `0xffffffff` after writing only `tests/test_cockpit_projection.py`; no production source file was modified.
- The preserved test file is syntactically valid and is intentional RED-first evidence: focused pytest currently fails during collection because the not-yet-implemented `cockpit_monitor_lines` symbol is absent.
- Git ownership is reconciled: the untracked test is inside this WO's allowed scope and belongs to the interrupted author attempt; no live runner/child remains.
- Classification: `PARTIAL / SAFE_TO_CONTINUE_FROM_RED`. Do not delete/recreate the test blindly; a continuation attempt may refine it only within the claimed scope.
- FMG dependency is re-accepted at SRM `2e6aeabd...` against A-Wiki main `7394322...`; source mutation is unblocked subject to the normal mutation/collision/quota gate.

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

## Candidate checkpoint after A-Faster recovery

- author continuation `run:WO-P1-424:author:1:a2:4662b50f92e6` completed terminal-success and froze local implementation commit `f0c046387886e51009d416cec6cf8f64a21b5204` over dispatch head `94e4a25...`;
- exact implementation delta is the four claimed product/test paths only;
- current-main fan-in is `27d644405f008e50771599d08669893e5caa80f6` (WTL-1), with zero overlap against the four implementation paths;
- post-fan-in candidate before this documentation checkpoint is `e446b537511d4d0970647bf25f460e450bf407f7`;
- integrator verification at `e446b53...`: focused cockpit **32 passed**, related desktop/control-center/graph/provider/continuity/WTL **355 passed**, py_compile PASS, strict UTF-8 PASS, exact path scope PASS;
- independent R2 review must explicitly audit whether the real `DesktopControlService.cockpit_projection()` wiring satisfies the Work Order/LOCAL-USABLE operator-truth requirement. The current implementation composes ControlCenter worker rows while execution/lease/git/gate observations remain unavailable in the real facade. Pure projection tests prove those states when injected, but reviewer must decide whether leaving accepted durable execution truth unwired is a blocking product-acceptance gap rather than truthful UNKNOWN behavior;
- no merge/acceptance is permitted until that focused product-truth question and ordinary R2 safety review both pass.

## Canonical R2 harvest and explicit foundation re-scope

Canonical repaired-candidate review:
- run `run:WO-P1-424:r2-rereview:1:a1:b6d13ae09610`;
- reviewed exact SHA `e624728d420d187f0b4ef9be604e9dd0948c50fb`;
- terminal exit 0;
- verdict `CHANGES_REQUIRED`, severity P0/P1/P2/P3 = 0/1/0/4;
- focused 44 PASS; related 438 PASS + 1 environment skip; compile/diff/UTF-8/secret/read-only adversarial probes PASS;
- prior P2 gate-provenance defect is resolved;
- explicit durable execution/lease facade binding is correct and fail-closed;
- blocking P1 remains only at ordinary product composition: normal desktop startup has no accepted durable runtime authority binding, so LOCAL-USABLE-1 is not met by this slice.

Integrator disposition: **foundation re-scope**.
- This Work Order / PR #428 is COCKPIT-1A: a safe read-only projection/provenance/UI foundation only.
- It does **not** claim LOCAL-USABLE-1 completion and does not own production runtime authority composition.
- R3 successor #431 `RUNTIME-AUTH-1` owns production durable job/execution/lease authority composition/locator.
- #429 `COCKPIT-1B` consumes the accepted #431 identity read-only in ordinary desktop startup.
- Refined critical path: `accepted GOT/FMG -> COCKPIT-1A (#424 foundation) + RUNTIME-AUTH-1 (#431) -> COCKPIT-1B (#429) -> LOCAL-USABLE-1`.
- Product/test bytes from `e624728d...` remain the foundation candidate; only this Work Order semantics change in the re-scope commit.
- Because the re-scope creates a new exact SHA, merge remains blocked until fresh exact-head CI and independent exact-SHA R2 review accept the narrowed foundation contract.

Foundation acceptance requires:
1. read-only projection/provenance behavior remains fail-closed and deterministic;
2. operator-declared gate evidence cannot yield `COMPLETED_VERIFIED`;
3. injected accepted durable execution/lease evidence reaches the bounded projection states without writing durable state;
4. unbound/unreadable authority remains explicit UNKNOWN/EVIDENCE_INCOMPLETE;
5. no new DB/store/schema/scheduler/task/claim/lease/review/completion authority;
6. no claim that ordinary desktop startup has production durable authority binding;
7. #431/#429 remain the explicit owners of that missing product path.

## Completion

Agent/GLM DONE is only a claim. Completion requires frozen exact SHA, deterministic evidence, independent exact-SHA R2 review with P0/P1/P2=0, exact-head CI, GPT acceptance/merge, post-main verification, and durable checkpoint.
