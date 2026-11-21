# WO-P1-782 — SundayFamily SDLC Virtual Flow Roadmap & Agent-Visible Design Routing

Identity schema: GITHUB_ISSUE_V1  
Issue: #782  
Status: DOCS-ONLY CANDIDATE / REVIEW REQUIRED / NOT MERGED  
Topology: CONTROL_PLANE_ONLY  
Risk: R2 (shared design/agent-routing docs, no source/runtime authority)  
Authority repo: `aase7en/A-Wiki-Conductor`  
Owner: ChatGPT integrator — bounded GitHub-only docs lane

## Goal / operator authority
2026-11-21: Operator explicitly requested publishing the prepared SDLC Virtual Flow Roadmap to GitHub and making relevant design/plan/agent documents consistently point to it. The attached screenshots are reference designs, not verified deployed UI.

This work **publishes a proposed, additive SFU26 feature roadmap**; it does not implement the UI, alter live policy/security/claim/route, schedule tasks, or supersede the accepted SFU26 master roadmap.

## Exact lane & claim
- Issue/claim anchor: https://github.com/aase7en/A-Wiki-Conductor/issues/782
- Remote baseline: `main@6a137273a6caa2edfa6912942c20b3dc0aab2902` (reverify before merge)
- Isolated remote branch: `docs/wo-p1-782-sdlc-virtual-flow-docs`
- Physical Windows/macOS main checkouts remain untouched: their HEADs are stale and contain unrelated dirty/untracked work.
- This Work Order and issue are the **existing authority**. No second registry/scheduler/claim or status database.
- Mutation verdict applies only to this branch and enumerated docs files; not to other repos or local worktrees.
- Previous UX-2 claim: Issue #774 / PR #776 owns `web/sunday-family/`; no overlap permitted.

## Allowed docs-only scope
1. `docs/work-orders/WO-P1-782-sdlc-virtual-flow-docs.md` (this contract).
2. NEW `docs/plans/2026-11-21-sundayfamily-sdlc-virtual-flow-roadmap.md` (publish original draft).
3. Bounded, **additive** references only in existing:
   - `docs/design/sunday-family-design-system.md`
   - `docs/plans/2026-11-13-sunday-family-unified-dashboard-routing-roadmap.md`
   - `PROJECT-GRAPH.yaml` `ui_design` node
   - `AGENTS.md` SundayFamily UI section
   - `00-AGENT-ENTRY.md` only if gap exists, otherwise avoid it.
4. Independent issue/PR descriptions and checkpoint comments.

## Forbidden
- `web/`, `src/`, `tests/`, `DESIGN.md` Tk requirements, deployed runtime, Command Gateway, security/claims/providers, SunDayRemoteMCP, A-Wiki, external skill installation.
- Shared mutable coordination hotspots `CURRENT-WORK.md`, `handoff.md`, `COLLAB.md` without independently proven single-writer ownership. Fold via existing integrator/continuity owner **after** accepted merge.
- No direct push to `main`; no self-merge, auto-approval or synthetic status claims.

## Integration rules
- Roadmap status must remain `PROPOSED / NON-BINDING` until a separate implementation WO is accepted.
- Scope is `Work & Lanes > SDLC Virtual Flow` secondary read-only tab (no eighth top-level nav).
- Keep the Color E-Ink pencil/manga, Thai-first, reduced-motion, evidence-first Design System; don't turn reference screenshots into runtime evidence.
- Reuse A-Wiki skill policy, A-Conductor task/claims/CI/Review/Continuity, and existing React/API/SSE contracts. No duplicate control plane.
- Do not begin frontend mutation until UX-2 PR #776 current ownership and merge/acceptance gate are reconciled.

## Validation / acceptance
- Confirm the 334-line ChatGPT roadmap is published intact with correct PROPOSED warnings.
- Verify new roadmap link/path is real and navigation/graph pointers resolve.
- Read GitHub actual remote PR diff at frozen head: only allowlisted docs; no accidental secret or runtime edits.
- Check YAML, Markdown anchors/UTF-8/trailing newlines; run `tests/test_work_order_identity.py` and CI as possible.
- Because this touches agent-read routing, require independent R2 documentation review and exact-head hosted CI before merge.
- After accepted merge: verify `main` and fold continuity through **one verified writer**; release claim only after that, not now.
- Replay safety: before repeating writes, inspect issue, remote branch, PR and each path's SHA; never blind-repeat.

## Context / evidence
- Operator request 2026-11-21; drafted file `SundayFamily_SDLC_Virtual_Flow_Roadmap_2026-11-21.md`.
- SFU26 master `docs/plans/2026-11-13-sunday-family-unified-dashboard-routing-roadmap.md`.
- Design System `docs/design/sunday-family-design-system.md`, existing repo agent entry and UX-1 acceptance Issue #743.
- Existing UX-2 issue #774 / PR #776 (open during preflight).
- Local Windows main dirty `CURRENT-WORK.md`, `handoff.md`, `src/a_conductor/memory_presence.py`, `.kilo/`; macOS main has unrelated untracked files.

## Exact next safe action
Bind non-overlapping docs-only claim on #782; publish the unchanged roadmap on this branch; add only approved bounded pointers after re-reading current file SHAs; inspect remote diff, review/CI; keep PR open for independent approval.
