# WO-P1-197 — ZRA-4 physical identity implementation gate

Status: BLOCKED_ZRA3_ACCEPTANCE / IMPLEMENTATION_PACKET_READY
Owner: GPT-5.6 Sol integrator
Parent: Issue #216 / GPT1-ZRA4-PREFLIGHT-001
Design input: WO-P1-196 exact SHA `10dca359568c216983199a6899b0af3863b5e9d7` / PR #271
Date: 2026-09-11 (Asia/Bangkok)
Risk: R3 when source mutation begins; this activation is docs-only R1/R2.
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo197-zra4-identity`
Branch: `docs/wo-p1-197-zra4-identity-implementation-gate`
Base: `origin/main@46f90b329d4991211f5c8a26406f3aca2162e9a7`

## Gate

Do not mutate product source until BOTH are true:

1. ZRA-3 parent composition is accepted in order (`PR #263` parent, then stacked `PR #269` exact accepted SHA); and
2. parent Issue #216 explicitly releases C1/C1b implementation from HOLD.

WO197 may be committed/pushed/opened as a documentation/claim packet now. Product implementation remains blocked.

## Objective

Implement the minimum physical-resource identity hardening required before ZRA-4 may fan out 2–3 mutation lanes. The implementation must make logically equivalent Windows workspace/scope aliases collide conservatively while preserving distinct proven resources as independent.

This work is not a new scheduler, lease system, path sandbox, or repository identity store. It strengthens the identity projection consumed by existing authorities.

## Accepted evidence inputs

Use WO196 as design/evidence authority, not as production code:

- physical root identity distinguishes logical repository, local worktree, physical write resource, and shared Git common directory;
- Windows junction / macOS symlink aliases can resolve to the same directory object while lexical paths differ;
- hardlinks can refer to the same file object while literal scopes appear disjoint;
- same synthetic physical resource can receive two leases under lexical alias identities today;
- dot-segment, alternate separator, case, junction/symlink, hardlink, 8.3/drive alias where available, nonexistent target, TOCTOU and unsupported filesystem cases require explicit dispositions;
- UNKNOWN must never become DISTINCT merely because strings differ.

Additional integrator reproducer on the current code:

```text
write_sets_overlap(('src\\a.py',), ('src/a.py',)) == False
write_sets_overlap(('SRC/a.py',), ('src/a.py',)) == False
```

On Windows these spellings may name the same write resource. ZRA-4 must not fan out mutation lanes while this remains possible.

## Authority boundaries

Reuse existing authorities:

- `registry.py::windows_worktree_key` (logical/lexical identity seam today);
- `graph/analyze.py::paths_overlap` and `write_sets_overlap` (single graph conflict seam today);
- `worker_lease.py` active lease acquisition/preflight transaction (atomic mutation reservation authority);
- existing task allowed/forbidden/mutable scope validation;
- existing GraphDispatch / ParallelReady / scheduler authorities.

Do not create a second conflict engine or a second lease registry.

## Expected implementation shape

The implementation should follow WO196's separation of concerns:

1. **Validated scope grammar** — reject absolute/drive-relative/NUL/traversal/ambiguous scope inputs before conflict projection.
2. **Canonical logical scope projection** — normalize Windows separators/case/dot segments in a deterministic, versioned representation without widening authorization.
3. **Physical root/resource identity observation** — resolve aliases only through OS-backed evidence when available; never guess cross-host equality.
4. **Atomic reservation integration** — ensure equivalent physical mutation resources contend inside the existing WorkerLeaseBroker/store transaction.
5. **Fail-closed unsupported/unknown** — ambiguous physical identity blocks concurrent mutation rather than being treated as disjoint.
6. **Legacy compatibility/migration** — old lease rows or unversioned identities cannot silently coexist with new identities in a way that permits double mutation.

Whole-root reservation is acceptable as a conservative first safety step only if it does not weaken existing allowed/forbidden authorization and the performance/concurrency trade-off is recorded. Finer resource classes may follow only with deterministic proofs.

## Initial mutable scope after release

The exact source scope must be re-pinned after ZRA-3 acceptance. Preferred minimal candidates:

- `src/a_conductor/registry.py`
- `src/a_conductor/graph/analyze.py`
- `src/a_conductor/worker_lease.py`
- focused tests for the touched seams

A new dedicated identity module is allowed only if it reduces duplicated OS-specific logic and all callers still flow through existing authorities.

Forbidden without explicit scope expansion:

- scheduler policy changes;
- GraphDispatch semantics;
- provider admission;
- ZCode configuration/credentials;
- live Worker/process/tunnel mutation;
- destructive Git operations;
- global continuity projections.

## RED-first acceptance matrix

Before GREEN, prove at least:

1. Windows case aliases (`SRC/a.py` vs `src/a.py`) collide.
2. Windows separator aliases (`src\\a.py` vs `src/a.py`) collide.
3. dot-segment aliases that resolve within allowed scope collide; traversal escaping scope is rejected.
4. trailing separators/case aliases of the same worktree remain one identity.
5. junction/symlink aliases of the same physical root cannot obtain two concurrent mutation leases.
6. distinct physical roots remain independent when positively proven distinct.
7. hard-linked existing write targets are not declared independent merely by different names.
8. 8.3/long-path or drive mapping aliases, when the platform can prove them, collide; unsupported cases fail closed/skip only in platform-specific proof tests.
9. nonexistent future write targets have a conservative parent/resource disposition and cannot create an alias bypass.
10. reparse/symlink escape below an allowed root cannot widen authorization.
11. shared Git common-dir hazards are represented separately from worktree data-root independence where mutation type requires it.
12. existing lexical positive controls continue to pass.
13. existing distinct scope patterns that are genuinely disjoint remain disjoint.
14. lease acquisition remains atomic under concurrent attempts; one winner for the same physical mutation resource.
15. legacy/unversioned lease identity cannot coexist optimistically with a new canonical identity.
16. UNKNOWN physical identity never returns DISTINCT solely from spelling.
17. no human relay is added to ZRA-4 scheduling/dispatch path.

## Verification floor

After implementation release, run at minimum:

- focused registry/project identity tests;
- graph analyze/ready/scheduler tests;
- worker lease + continuity guard tests;
- ParallelReady/worker-candidate tests;
- Windows-native alias/junction proof where available;
- macOS/Linux symlink proof where relevant;
- compile/import;
- `git diff --check`;
- strict UTF-8 / no U+FFFD;
- added-line secret scan;
- exact changed-scope audit;
- hosted CI on frozen exact SHA.

## ZRA-4 release condition

C1/C1b is necessary but not sufficient. Fan-out remains blocked until C2 deterministic batch identity is also accepted and the live 2–3 lane proof has explicit lease/provider/write-set isolation.

## Result contract

When implementation begins, write `runs/WO-P1-197/result.md` with:

- accepted parent SHA(s);
- accepted WO196 design SHA;
- release evidence from Issue #216;
- exact changed files;
- identity projection/version;
- OS evidence source and UNKNOWN policy;
- RED/GREEN tests and native alias proofs;
- atomic lease concurrency proof;
- legacy migration/fencing result;
- residual risks;
- exact frozen SHA and hosted CI;
- independent review verdict;
- exact next safe action.

Until the gate opens, final state is `BLOCKED_ZRA3_ACCEPTANCE`.
