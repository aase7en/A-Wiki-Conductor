# WO-P1-518 — DEPDIET Feature-Pack Boundary Design

Status: ACTIVE / CANDIDATE_FROZEN_FOR_REVIEW (attempt-0003)
Issue: #518
Parent: #472
Risk: R2 — architecture/docs
Topology: CONTROL_PLANE_ONLY shaping for an EXECUTION_SUBSTRATE_ONLY successor
Claim: WO-P1-518-DEPDIET-FEATUREPACK-MAC-001
Base: 84696b2360197c981d6f9fa2f33fb065b7b8ef07
Worktree: /Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo518-depdiet-featurepack
Branch: docs/wo-p1-518-depdiet-featurepack

## Goal
Convert the parent #472 NO_DIRECT_DELETE_CANDIDATE audit into a bounded feature-pack/build-boundary design before any SunDayRemoteMCP package or source mutation.

## Exact mutable scope
- docs/plans/2026-09-20-dwb-convergence-product-acceleration-roadmap.md
- this work order

## Required design
Preserve the compact core. Evaluate remote-device/cloud and rich-document/editor as separate optional feature-pack candidates. Map TypeScript build, package graph, tests, packaging and full-toolset compatibility. Define deterministic before/after acceptance and a bounded successor mutation packet only when isolation is proven.

## Forbidden
No SRM mutation; no package.json/package-lock edits; no npm install/prune/update/publish; no remote creation; no runtime restart; no blind dependency deletion.

## Acceptance
Diff/UTF-8/link/scope checks, frozen SHA, independent R2 review as required, exact-head CI, GPT acceptance. No self-merge.

## Attempt-0003 checkpoint — 2026-09-23

- Context proof passed before mutation: pwd/worktree, branch, HEAD `84696b2...`, WO present; initial dirty state exactly this untracked WO bootstrap.
- READ_ONLY evidence: accepted first-slice predecessor `e3ec2e0` (#473) is the direct parent of current accepted execution-substrate SHA `2f033cfb1f61b6dff9c2e55264cca6f2a9125e95`; later accepted WO-P1-507 pins the Windows SRM execution substrate at `2f033cfb...`, and the current macOS SRM clone is clean `main@2f033cfb...`. The repository remote remains unverified/absent.
- Design delivered in roadmap §13.1: PACK-R (remote-device/cloud: `@supabase/supabase-js`, `open`, `caffeinate`) and PACK-D (rich-document/editor, facets D1 browser editor 10 roots / D2 Node document handlers 7 roots) with compact-core retained set (8 roots); verified build/package/test/release coupling (tsc whole-`src` compile, ESM entrypoint import chains, `getFileHandler` fusion with compact tools, MCPB dependency copy, test auto-discovery, `SUNDAY_FULL_TOOLSET` compatibility); 16-row deterministic before/after acceptance matrix (A1–A16); successor mutation packet conditions with slice order D1 → PACK-R → D2 and hard fences.
- Mutable scope used: roadmap §13.1 insertion + this WO only. No SRM mutation; no npm operations; no remote creation; no runtime restart.
- Result evidence: `runs/WO-P1-518/author/attempt-0003/result.md`.
- Next safe action: independent R2 review of the frozen docs candidate, then GPT acceptance; successor slice WOs may be authored only after acceptance and must re-pin actual SRM state, using `2f033cfb1f61b6dff9c2e55264cca6f2a9125e95` as the accepted local-SHA base only if it remains the execution-substrate HEAD.
