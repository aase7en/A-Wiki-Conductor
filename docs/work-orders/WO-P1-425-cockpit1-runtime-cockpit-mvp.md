# WO-P1-425 — COCKPIT-1: Runtime Cockpit MVP durable truth projection

Identity schema: GITHUB_ISSUE_V1
Issue: #425
Status: CLAIMED / READY_FOR_IMPLEMENTATION
Parent roadmap: #397 / `docs/plans/2026-09-20-dwb-convergence-product-acceleration-roadmap.md`
Topology: CONTROL_PLANE_ONLY
Risk: R2 — read-only projection and existing desktop UI only; no consequential commands
Owner / integrator: GPT-5.6 Sol

## Repository binding

Authority repo: `A:\GitHub\A-Wiki-Conductor`
Execution repo: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo425-cockpit1`
Branch: `feat/wo-p1-425-cockpit1-runtime-cockpit`
Base / accepted main at claim: `bd4892185195d8c6a7c3a8652a75ec4db7f003b4`
Claim: `WO-P1-425-COCKPIT1-RUNTIME-COCKPIT-MVP-001`

## Dependency gate satisfied

- GOT-1 / GOT-1b-B is accepted, merged and post-main verified; `production_closeout_observation.py` is accepted read-only evidence composition.
- DEX-2b identity/receipt foundation is accepted and post-main verified.
- FMG-1 is ACCEPTED_LOCAL_ONLY / COMPLETE at SunDayRemoteMCP `7c3c048d3d21291e842a944e50ecf0ca5d71f475` against A-Wiki main `bd4892185195d8c6a7c3a8652a75ec4db7f003b4`.
- COCKPIT-0 current-main Flash refresh `run:WO-P1-421:refresh:1:a3:5b362ddf247f` completed exit 0 at exact `bd489218` and classified READY_AFTER_FMG.
- WTL-1 remains parallel/unmerged at claim time. WTL-derived lifecycle/ownership fields MUST remain UNKNOWN until an accepted source exists.
- Durable desktop Hook read-back remains absent. Hook-derived fields MUST remain UNKNOWN; this WO does not create a hook store.

## Goal

Add one concise read-only Runtime Cockpit to the existing A-Sunday desktop UI so an operator can see durable task/execution/repository/gate truth without opening Markdown or relying on chat history.

The cockpit is a projection/consumer only:

`DURABLE AUTHORITY -> EXISTING OPERATOR/READ VIEWS -> COCKPIT`

never:

`COCKPIT DB -> TASK TRUTH`.

## Exact mutable scope

- NEW `src/a_conductor/cockpit_projection.py`
- MODIFY `src/a_conductor/desktop_control.py`
- MODIFY `src/a_conductor/desktop_ui.py`
- NEW `tests/test_cockpit_projection.py`
- MODIFY `docs/work-orders/WO-P1-425-cockpit1-runtime-cockpit-mvp.md`

Everything else is READ ONLY. Any required edit outside these five paths is `SCOPE_EXPANSION_REQUIRED`.

## Reuse requirements

REUSE / WRAP accepted read-only authority and projection seams; do not redefine them:

- `ControlCenterService.snapshot` and immutable control-center screen DTO precedent.
- `DesktopControlService` existing read-only facade pattern.
- `graph.operator_view.read_graph_operator_snapshot` and graph-monitor rendering precedent.
- `provider_operator_view.build_provider_operator_rows`.
- `SQLiteExecutionStore.get/list_events/get_receipt` read surfaces and `DurableExecutionRecord` / `DurableExecutionReceipt`.
- Existing job/checkpoint readers and `completed_closeout_checkpoint_refs` as applicable.
- `SQLiteWorkerLeaseStore` read/health surfaces as applicable.
- `worker_status.evaluate_worker_status` and provenance-aware process observation only when a full observation can be built from existing accepted sources.
- Production-closeout accepted underlying read primitives; do NOT instantiate `ProductionCloseoutEvidenceProvider` on every UI refresh.
- Existing desktop UI monitor cadence / background single-flight / Tk-thread publish seam.
- Accepted DEX identity/binding helpers only as evidence provenance; no new identity authority.

## Explicitly unknown / unavailable sources

- No accepted durable desktop Hook-envelope read-back exists; Hook fields render explicit UNKNOWN.
- WTL-1 is not accepted on main at claim time; worktree lifecycle/cleanup ownership fields render explicit UNKNOWN.
- Missing/unreadable evidence is UNKNOWN or EVIDENCE_INCOMPLETE, never silently false/healthy/absent.
- PID existence alone is not process identity and MUST NOT imply RUNNING.

## Projection contract

Add immutable read-only presentation DTOs in `cockpit_projection.py`. Each material displayed fact must carry or preserve a bounded source/provenance reference sufficient to explain its origin. The frame must distinguish at minimum FRESH, STALE and EVIDENCE_INCOMPLETE.

Required operator information when accepted evidence exists:

- Work Order/task reference;
- topology;
- lane/executor/provider/harness;
- authority and execution repository;
- active repo/worktree/branch/HEAD;
- claim/lease state;
- execution id and exact process identity when provenance is known;
- derived execution/outcome state;
- last activity / meaningful progress when supported;
- verification/review/CI gate state;
- blocker code;
- replay-safety status;
- descriptive next safe action.

Required concise outcome vocabulary includes `RUNNING`, `TERMINAL_UNHARVESTED`, `OUTCOME_UNKNOWN`, `RECOVERY_NEEDED` / `STALLED_RECONCILE`, `REVIEW_BLOCKED`, `CI_BLOCKED`, `READY_FOR_NEXT_STAGE`, `COMPLETE` / `COMPLETED_VERIFIED`, `OBSERVABILITY_DEGRADED` and `EVIDENCE_INCOMPLETE`. Mapping is presentation-only and never grants retry authority.

## Frame / re-pin model

- One projection build represents one bounded frame.
- Use existing immutable/read-only witnesses where available.
- If source witnesses drift during collection, perform at most one bounded re-collection; if still mixed, mark STALE rather than publishing blended facts as FRESH.
- Source absence/failure marks the relevant field UNKNOWN and the frame EVIDENCE_INCOMPLETE as appropriate.
- The cockpit owns no persistent cache of truth.

## Desktop integration

- `DesktopControlService` gains only the smallest read-only cockpit facade/composer method.
- `desktop_ui.py` adds one cockpit read-only monitor surface in the existing UI stack.
- Reuse the existing 15-second `_monitor_tick` / background-executor / poll-to-Tk-thread pattern. Do not create a second timer/scheduler.
- No retry/reassign/cleanup/merge/accept/restart buttons or new consequential command paths.
- Existing safe start/stop UI authority outside the cockpit remains unchanged.

## RED-first acceptance matrix

1. Provenance mismatch: wrong repo/head/receipt/gate binding renders blocker/UNKNOWN; never silently rebind.
2. UNKNOWN versus absent: missing Hook/WTL/lease/post-main/review sources remain explicit UNKNOWN; observed empty/absent evidence remains distinguishable.
3. Stale frame: witness drift across collection causes bounded retry then STALE, never a mixed FRESH frame.
4. Process provenance: PID without creation/executable/provenance match never renders RUNNING.
5. Execution outcome: terminal process without durable harvested result renders TERMINAL_UNHARVESTED / OUTCOME_UNKNOWN rather than success.
6. Closeout/review/CI gates: pending/missing/failed/wrong-head evidence is not rendered accepted/complete.
7. Replay safety: only evidence-backed replay-safe state may render safe; otherwise UNKNOWN / insufficient evidence.
8. Zero command authority: cockpit projection/UI exposes no new mutation/retry/reassign/cleanup/merge/accept controls.
9. UI cadence: cockpit refresh reuses existing monitor single-flight/timer path; no second recurring scheduler.
10. Real-service smoke: existing desktop smoke still constructs; cockpit rendering tolerates empty databases/unavailable sources.
11. No-new-store/static audit: `cockpit_projection` creates no SQLite schema/table/store and contains no authority writes.
12. Determinism: identical immutable source snapshots produce identical semantic projection apart from an explicitly non-authoritative collection token/time field.

## Forbidden

- New DB/table/schema or cockpit-specific persistent truth store.
- New task/claim/lease/review/retry/completion/scheduler authority.
- New filesystem/process mutation or cleanup action.
- Inferring truth from Markdown, Issue prose, branch names, filenames, directory age, PID existence or log keywords.
- Registering a Hook sink or inventing durable Hook storage.
- Treating WTL-1 branch bytes as accepted authority before merge/acceptance.
- Calling network/Git mutation from projection or UI.
- Broad desktop UI rewrite or a second UI framework.

## Verification

At candidate freeze run at minimum:

- `tests/test_cockpit_projection.py`
- `tests/test_desktop_control.py`
- `tests/test_desktop_ui.py`
- `tests/test_control_center.py`
- `tests/test_graph_operator_view.py`
- `tests/test_provider_operator_view.py`
- relevant execution/job/lease/continuity/closeout tests exercised by the projection;
- `py_compile` on changed Python;
- `git diff --check`, exact five-path scope, strict UTF-8/no U+FFFD, added-line secret scan.

Hosted exact-head CI is mandatory. Independent exact-SHA GLM-5.3 MAX R2 review is mandatory after candidate freeze. PASS requires P0=P1=P2=0.

## Replay / recovery

Every delegated attempt must leave a durable execution pointer under ignored `runs/WO-P1-425/`. Before redispatch recover pointer/process/result/Git. RUNNING is never duplicated; terminal-unharvested work is harvested first; ambiguous dirty state fails closed.

## Closeout

COCKPIT-1 is complete only when the exact candidate is independently R2-accepted, exact-head hosted CI is green, merged to current main, and post-main CI succeeds. LOCAL-USABLE-1 is evaluated only after that verified merge; this WO alone does not declare LOCAL-USABLE-1.
