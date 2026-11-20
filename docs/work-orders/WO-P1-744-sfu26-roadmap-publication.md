# WO-P1-744 — SFU26 Master Roadmap Publication

Identity schema: GITHUB_ISSUE_V1
Issue: #744
Status: AUTHOR LANE — candidate for review/CI/merge gates
Risk: R0 (docs-only, two new files, no source/runtime/policy edits)
Topology: CONTROL_PLANE_ONLY

## Authority and Claim

- Authority repo: `aase7en/A-Wiki-Conductor`; base `38fb5d5708d60049b9f50e2a377e526b667b0d07` (local == origin/main verified before lane start; re-verify at merge).
- Worktree: `/Volumes/MAC_WORK/DevWorkspace/Github/AWC-wo744-roadmap`; branch `docs/wo744-sfu26-roadmap`.
- Owner: integrator-side docs lane under the operator goal-mode directive (2026-11-12T22:07Z); standing decision protocol = Jev (TypeSafe) + GPT-6.1 Terra advisory, human only when genuinely undecidable.
- Allowed scope (exact, both NEW files):
  - `docs/plans/2026-11-13-sunday-family-unified-dashboard-routing-roadmap.md`
  - `docs/work-orders/WO-P1-744-sfu26-roadmap-publication.md` (this file)
- No edits to any existing document (UX-1 packet, `CURRENT-WORK.md`, `handoff.md`, `AGENTS.md`, `PROJECT-GRAPH.yaml`, prior roadmaps), no `src/`, `tests/`, CI, web, or dependency changes. Untracked user inputs and `HUMAN_DECISION_REQUIRED` in the main checkout remain untouched.

## What this publishes

Card `CAND-SFU26-00` of the SFU26 program: the master implementation roadmap for the Sunday Family unified dashboard + intelligent routing over existing seams — 14 sections, 12 milestones, 22 candidate work-order cards (`CAND-SFU26-00..21`), dependency DAG, single-owner reuse map, benchmark/test strategy, acceptance gates `G-PLAN..G-RELEASE`, `OFF→SHADOW→ADVISORY→CANARY→PRODUCTION` rollout ladder, and rollback invariants.

Provenance (session inputs, untracked by design — digests recorded, contents not copied into this repo):

- Task packet `docs/prompts/KILOCODE-SUNDAY-FAMILY-UNIFIED-DASHBOARD-ROADMAP-2026-11-13.md` — sha256 `2ecd6fce22ab89b3e46c9be8f9dd068778ec312ab4e83de50d4c27c85ec12042`
- Research archive `docs/research/2026-11-13-intelligent-routing-evidence-roadmap.md` — sha256 `1eda13ae31312b3823edfb30e92260791ca993fb00711822475e37df112658a1`
- Harness-local draft `.kilo/plans/1793421406193-sunday-family-unified-dashboard-routing-roadmap.md` (main checkout, untracked)

Quality gate: an independent read-only adversarial plan review (2026-11-12) returned **PASS** with 0 P0/P1 and 3 P2 polish items, all folded into this published version:

1. Mermaid §7.3 now carries the card03→card05 dependency edge (graph matches card 05 text dependencies).
2. Frontend test inventory corrected: 7 test files plus fixtures/setup under `web/sunday-family/tests/`.
3. §9.1 names the sixth `SemanticDecisionFamily` enum member `review_severity` (frontier-only, excluded from admission per WO-P1-502).

## Boundaries honored

- UX-1 operator green-light (#743) remains open and blocks only card 04/UX-2; cards 01/06/10 offline preparation may be proposed independently without it.
- All `CAND-SFU26-*` IDs are planning IDs, not claims; every successor card requires its own WO, claim, and gates. This publication grants no implementation authority.
- No paid provider calls were made; no merge/deploy authority is exercised beyond this lane's own gate sequence (commit → push branch → PR → exact-head CI → merge expected head → post-main CI → checkpoint).

## Acceptance criteria

- `python3 -m pytest tests/test_work_order_identity.py -q` passes with this WO in the corpus (bare Issue header line matching this WO's numeric anchor; unique numeric id in filename).
- Added-file whitespace/UTF-8 checks clean; `git diff --check` clean; no tracked file outside the two allowed paths changed.
- Delivery gate sequence completed and checkpointed on Issue #744.

## Checkpoint

- 2026-11-13: lane bootstrapped (worktree + branch @ `38fb5d5`, base verified equal to origin/main); issue #744 created; input digests recorded; review verdict PASS folded. Authoring in progress.
