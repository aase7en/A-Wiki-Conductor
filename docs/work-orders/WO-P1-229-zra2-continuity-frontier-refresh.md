# WO-P1-229 — ZRA-2 continuity frontier refresh

Status: PREPARED / FROZEN FOR INDEPENDENT R2 REVIEW
Risk: R2 — root continuity / workflow authority, docs-only
Owner: GPT-5.6 Sol integrator
Repository: `aase7en/A-Wiki-Conductor`
Base: `origin/main@251df211afc1ee5452f3652675d7a2f38c526876`
Branch: `docs/wo-p1-229-zra2-continuity-frontier`
Authority issue: GitHub Issue #214

## Goal

Replace the stale WO166 top-authority blocks in `CURRENT-WORK.md` and `handoff.md` with the actual ZRA-2 frontier so a fresh session can recover without chat memory.

## Scope

Allowed paths only:

- `CURRENT-WORK.md`
- `handoff.md`
- this work-order file

Forbidden:

- product/source/tests/runtime state;
- `COLLAB.md`;
- active WO226 source/test paths;
- claims/leases/provider state;
- merge/release of WO226, WO223, WO205, WO227 or WO228.

## Pinned facts folded into continuity

- `origin/main@251df211afc1ee5452f3652675d7a2f38c526876`.
- WO225 and WO224 accepted/merged/post-main verified.
- WO208 evidence prerequisite satisfied for `23e701fa879bece6f46e5f66372ebb459f21a1db` by independent Windows plus native macOS replay.
- WO226 remains the active critical path and is not accepted. PR #314 candidate `cc398d6b1bff329d7145d0a98662add108b423ab` is `CHANGES_REQUIRED / DO_NOT_MERGE` for two deterministic trust gaps: terminal-unusable cleanup can release an admission/lease despite provider configuration-generation mismatch, and an all-None direct-review provider authority triple can be silently upgraded from the current snapshot and execute.
- Current WO226 repair packet is `origin/docs/wo-p1-226-repair-r1@a5ea7938a7a273b2a9554c5e434b2a4673e25229`, `docs/prompts/GLM-WO226-REPAIR-R1.md`; it now includes both remaining blockers inside the same bounded two-file source scope.
- WO223/C1 remains HOLD; prepared PR #305 head `5f2a91a48d695f25429290bb41e1f21415a70d9f`.
- WO205 Phase D remains HOLD; prepared PR #309 head `52fe1159c9ff94f49f4cd92d25148980d8561214` and WO208 is no longer a blocker.
- WO227/ZRA-3 remains HOLD behind full ZRA-2 + Issue #215 release.
- WO228/PR #313 head `02832d548405a4224313a770c079efcd90e8824f` is CI-green but still needs independent R2 exact-SHA review.

## Acceptance

- Only the authoritative top blocks of `CURRENT-WORK.md` and `handoff.md` change; historical evidence remains byte-preserved below the existing separator.
- Facts are bounded to exact durable Git/GitHub/evidence state and explicitly instruct new sessions to re-pin before mutation.
- No source/runtime/claim authority is created or transferred.
- Changed paths stay within the three-file scope.
- `git diff --check` and strict UTF-8 pass.
- Freeze one exact SHA, push a draft PR, and require independent exact-SHA R2 review + exact-head CI before merge.

## Stop state

`FROZEN_FOR_INDEPENDENT_R2_REVIEW`; no self-merge by the authoring Sol lane.
