# WO-P2-554 — Restore post-merge work-order identity CI

Status: CLAIMED / IMPLEMENTATION
Issue: #553
Risk / topology: R1 / CONTROL_PLANE_ONLY
Authority repo: aase7en/A-Wiki-Conductor
Worktree: /Users/aase7en/.codex/worktrees/wo-p2-554-identity-fixture/A-Wiki-Conductor-codex-supervisor
Branch: codex/wo-p2-554-identity-fixture
Starting HEAD: 8d2aae705a6d2180fd36abaf7f1ed545355d554c
Claim: WO-P2-554-IDENTITY-FIXTURE-001 (Issue #553 comment 5844315737)

## Goal and evidence

Restore the failing post-merge Windows test job from CI run 36220243248.
The failure is two assertions in tests/test_work_order_identity.py caused by
one corpus/fixture mismatch: current main contains the legacy-shaped file
WO-P1-191-zra3-next-ready.md but the frozen exception fixture omits it.
Issue #270's separate WO-P1-553 read-only plan explicitly excludes this repair.

## Exact mutable scope

- tests/fixtures/work_order_identity/legacy_identity_filenames.txt:
  add WO-P1-191-zra3-next-ready.md once at its lexicographically sorted position.
- This work-order file: append checkpoints for this lane only.

CURRENT-WORK.md and handoff.md remain excluded because the active #498
integrator claim owns those shared continuity paths. Keep this lane's durable
checkpoint here and in Issue #553 until #498 releases them. All other paths,
including A-Wiki, production source, test logic, and PR #269/#550/#552 are
read-only.

## Acceptance criteria

- Exact candidate has only the two claimed paths changed.
- Fixture is UTF-8, newline-terminated, lexicographically sorted and unique;
  the target filename appears exactly once.
- python -m pytest tests/test_work_order_identity.py passes.
- git diff --check, exact-scope, encoding and added-line secret checks pass.
- Exact-head PR CI and required post-main verification pass before closeout.

## Reference pattern

Follow the frozen legacy exception-set tests in
tests/test_work_order_identity.py and the WO-TEMPLATE.md checkpoint format.
Do not change the exception rule or tests.

## Steps

1. Re-pin remote main and preserve the exact claim binding.
2. Add the one legacy filename at its sorted position.
3. Run the focused suite and deterministic scope/format checks.
4. Freeze the exact SHA; open a draft PR and await exact-head CI.
5. Integrator reviews, accepts, merges with expected-head protection, then
   verifies post-main CI and records the final result here/Issue #553.

## Checkpoint log (append-only)

- [2026-09-26] Poppy Javis: Issue #553 and exact R1 claim established at
  main@8d2aae705a6d2180fd36abaf7f1ed545355d554c. No file edits before claim.
  Shared CURRENT-WORK.md/handoff.md are excluded under the active #498 claim.
- [2026-09-26] Poppy Javis: exact claimed edit complete. Focused suite:
  33 passed. Exact two-path scope, strict UTF-8, terminal newlines,
  lexicographic order, uniqueness, target count, added-line secret scan and
  git diff --check all PASS. Candidate is ready to freeze for exact-head CI.
