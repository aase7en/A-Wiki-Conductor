# WO-GE-005A — ReadySet must reuse GE-4 glob-aware conflict semantics

Created: 2026-08-26
Owner: GLM 5.3 implementation lane (claim required before mutation)
Status: READY — blocking GE-6 implementation
Parent: `WO-GE-001`
Found by: GPT-5.6 Sol MAX GE-6 design review after PR #96 merged

## Defect

Merged GE-5 `compute_ready_set()` checks running write conflicts by literal path-string equality. GE-4's accepted analyzer is glob-aware. Therefore a running node writing `src/**/*.py` and a TODO node writing `src/specific.py` may be incorrectly considered conflict-free/READY.

This violates ADR GE-0003/GE-0006 resource-conflict semantics and can let GE-6 select overlapping mutations concurrently.

## Required repair

- Reuse/extract **one authoritative GE-4 path-overlap/conflict seam**; do not maintain a second weaker write-conflict algorithm in `ready.py`.
- `compute_ready_set()` must treat the same FILE_WRITE overlaps as GE-4 for conflicts with currently DOING nodes.
- Add a regression proving `src/**/*.py` conflicts with `src/specific.py` (and the reverse orientation if the seam is directional internally).
- Preserve GE-5's worker-neutral boundary: do not add worker-capacity selection, scheduler dispatch, bridge network calls, or GE-6 code here.

## Allowed scope

- `src/a_conductor/graph/analyze.py` only if a small pure overlap helper must become a reusable public/internal seam;
- `src/a_conductor/graph/ready.py`;
- `tests/test_graph_analyze.py` / `tests/test_graph_ready.py`;
- this WO / parent WO checkpoint.

## Forbidden

- `scheduler.py` or dispatch implementation;
- A-Wiki mutation;
- new conflict algorithm duplicated from GE-4;
- changes to job lifecycle/dedup stores.

## Acceptance

- [ ] Regression is RED against merged PR #96 behavior.
- [ ] ReadySet and GE-4 use one authoritative glob-overlap semantic seam.
- [ ] Glob-vs-specific overlap blocks READY while disjoint paths stay ready.
- [ ] Focused graph suites pass.
- [ ] PR CI passes Windows + Ubuntu + macOS.
- [ ] PR merged and `origin/main` verified.

## Evidence reference

Integrator post-merge finding: https://github.com/aase7en/A-Wiki-Conductor/pull/96#issuecomment-5420827136

## Next

After this repair is merged green, GE-6 implementation is unblocked and must follow ADR GE-0006. GE-7 follows ADR GE-0007 after GE-6.
