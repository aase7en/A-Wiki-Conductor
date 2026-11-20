# WO-P1-774 — SFU26 Card 04 UX-2 Read-Only React Build-Out: WO Bootstrap

Identity schema: GITHUB_ISSUE_V1
Issue: #774
Status: R0 DOCS-ONLY WO BOOTSTRAP — AWAITING INTEGRATOR DEPENDENCY-ORDER ACCEPTANCE; NOT IMPLEMENTATION AUTHORIZATION
Risk: R0 (this docs lane charters an R2 implementation card)
Topology: CONTROL_PLANE_ONLY

## Goal and source

Charter the SFU26 roadmap card 04 implementation ("Read-Only UX-2 In Existing React Shell", `docs/plans/2026-11-13-sunday-family-unified-dashboard-routing-roadmap.md` §04) now that the operator UX-1 gate is fully closed. This WO creates the durable work-order contract only; the implementation lane re-runs the full mutation gate after integrator acceptance.

Operator authority chain (2026-11-17, Asia/Bangkok):

- UX-1 five-decision record: [#743 c6949730135](https://github.com/aase7en/A-Wiki-Conductor/issues/743#issuecomment-6949730135)
- Decision 5 acceptance + gate closure (5/5): [#743 c6950258083](https://github.com/aase7en/A-Wiki-Conductor/issues/743#issuecomment-6950258083)

Binding operator decisions carried into card 04 scope:

1. Visual baseline = accepted Color E-Ink design system (`docs/design/sunday-family-design-system.md` + root AGENTS.md direction). The "family kitchen" artwork refinement is design-track input (#769 lineage); this lane never restyles. If the visual outcome is weak, record `UX_VISUAL_REVIEW_REQUIRED` with screenshots/viewport/SHA — never redesign from the implementation lane.
2. Seven-section IA with Projects/Claims/Roadmap grouped under **Work & Lanes**.
3. Models & Agents = read-only panel in v1 (card 05 read models are the data source).
4. Popup WebView is the window direction but its feasibility/security review belongs to cards 17/18 — NOT this card.
5. Fleet v1 = **monitor-only** (status/evidence/provenance; no Start/Stop/Pair/Rebind/Delete buttons). Control actions arrive later via card 15, one action per accepted WO.

## Claim / scope / exact base

- Issue: #774 (this WO's numeric identity).
- Branch: `docs/wo-p1-774-sfu26-card04-ux2`; worktree `A:\GitHub\_worktrees\AWC-wo774-card04`.
- Exact base: `origin/main@789ee650b7723bcca7a986f569ef3b47962debc4` (post PR #770 merge, verified 2026-11-17).
- Owner: Kilo Code / GLM-5.3 bounded docs-only lane (operator-approved continuation plan, `.kilo/plans/1794914556048-sundayfamily2-continuation-plan.md`).
- Allowed in THIS lane: exactly one NEW file — this WO.
- Forbidden in THIS lane: `CURRENT-WORK.md` / `handoff.md` (root worktree carries another session's intentionally-uncommitted checkpoint — never touch), `AGENTS.md`, `PROJECT-GRAPH.yaml`, `DESIGN.md`, SFU26 roadmap, UX docs, `src/`, `web/`, `tests/` (identity suite runs read-only as verification), infrastructure, secrets.
- Replay safety: issue #774, branch, and PR state must be inspected before any retry; no blind duplicate writes.
- Non-overlap: PR #772 (WO-P1-771 requirements docs) is a disjoint docs candidate owned by the ChatGPT integrator lane; no shared files.

## Deliverable

This WO file plus the driving issue #774 charter. The chartered implementation scope (executed only after acceptance, by a claimed implementation lane):

- Families: existing `web/sunday-family/src/` (App/API/components/styles) + `web/sunday-family/tests/` ONLY. No new router/store dependency, no backend/claims mutations, no design-system rewrite, no Tk changes.
- DoD: accepted seven-nav grouping; Overview/Work/Tools/Fleet read views consuming existing delivered read models (inspector card 02, fleet projection card 03, settings read models card 05, snapshot/cockpit projection); source/time/reason/truncation truth display; MC-1 2D waits; absent settings/advice/usage visibly unavailable; UNKNOWN/STALE never rendered healthy.
- Tests (from roadmap card 04): unknown enum, optional-source failure, source-empty vs missing, stale READY removal, disconnect-while-running, viewports 390/900/1280px, keyboard/zoom/Thai wrapping, zero API mutation from this slice.
- Rollback: previously accepted React shell remains usable; keep sample banner for fixtures; no Tk launch or deletion.

## Acceptance / review

- Exactly one new file in the PR diff; identity suite green (`tests/test_work_order_identity.py`).
- Exact-head CI run ID recorded on #774; this docs candidate is NOT self-merged — integrator merges the expected head only.
- Integrator records dependency-order acceptance on #774 before any implementation claim; the implementation lane then branches fresh from accepted `main` under its own claim.

## Verified snapshot (2026-11-17, not timeless)

- `origin/main@789ee65`; local root worktree `main@6ccc341` behind, with protected foreign dirty `src/a_conductor/memory_presence.py`, untracked `.kilo/`, and another session's uncommitted `CURRENT-WORK.md`/`handoff.md` checkpoint — all preserved untouched.
- SFU26 program: 10/22 cards delivered (00–03, 05–10); card 04 is the next lineage head (04 → 13 → 14 → 15 → 17 → 18 → 19).
- PR #772 OPEN @ `2f79388` with independent review CHANGES_REQUIRED pending author correction — disjoint from this lane.

## Exact next safe action

1. This bootstrap PR: exact-head CI → integrator review/merge of expected head → post-main CI → checkpoint on #774.
2. Integrator records card-04 dependency-order acceptance on #774.
3. Implementation lane claims on #774 from accepted main: `web/sunday-family/` read-only UX-2 build-out per this WO's chartered scope, TDD-first, gate chain (exact-head CI → independent UI/truth/a11y review → integrator merge → post-main CI → checkpoint). No implementation may start before step 2.
