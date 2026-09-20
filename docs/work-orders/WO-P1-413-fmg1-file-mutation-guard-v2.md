# WO-P1-413 — FMG-1: SunDayRemoteMCP File Mutation Guard v2

Status: OPEN — durable contract created; SRM source mutation is
BLOCKED_PENDING_WO260_POST_MAIN (see Dependencies). This docs lane granted no
execution-repo mutation authority.
Identity schema: GITHUB_ISSUE_V1
Issue: #413
Risk: R3 — mutation concurrency, path identity, retry/stale-write semantics
Topology: CROSS_REPO (label home: `docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md`)
Authority repo: A-Wiki-Conductor (this repo; durable WO/evidence fan-in home)
Execution repo: SunDayRemoteMCP (SRM)
Owner/integrator: GPT integrator (trust framing, acceptance, merge authority)
Docs-lane claim: `WO-P1-413-FMG1-CONTRACT-001` on branch
`docs/wo-p1-413-fmg1-contract` from dispatch head
`dfe09e8817e6679433444f18292e295cb2f6a6d5`
Roadmap source: `docs/plans/2026-09-20-dwb-convergence-product-acceleration-roadmap.md` §10 (Phase FMG-1)

## Goal

Convert the already-harvested FMG shaping decision into a durable Work
Order/task contract before any SRM source mutation: a fail-closed File
Mutation Guard around SRM MCP file-mutation tools, reusing the accepted DEX
canonical-root authority and existing path-lock authority — never creating a
second root, binding, task, claim, session, or store authority.

## Dependencies (current truth at dispatch, 2026-09-20)

1. A-Wiki WO-P1-260 / PR #403 merged at
   `dfe09e8817e6679433444f18292e295cb2f6a6d5`.
2. Exact repaired/accepted pre-merge candidate:
   `a170368ea3dbaf4193d7372b7b004931a0f6f5a7`.
3. Exact-head CI `35498004777` SUCCESS and focused independent R3 rereview
   PASS P0=P1=P2=P3=0.
4. Post-main CI run `35499727319` was still PENDING/RUNNING at dispatch.
   Therefore SRM product mutation stays BLOCKED until it completes SUCCESS
   (`BLOCKED_PENDING_WO260_POST_MAIN`).
5. Accepted SRM DEX-2a local-only anchor:
   `fe5abb3eb51ec712a970ec3a8cdcd5402619e992`. SRM main `ac01b37` is behind
   and must NOT be used as the FMG base.
6. Final compatibility input set after post-main success is
   `{A-Wiki-Conductor@dfe09e8817e6679433444f18292e295cb2f6a6d5,
   SunDayRemoteMCP@fe5abb3eb51ec712a970ec3a8cdcd5402619e992}`; the final FMG
   candidate later replaces the SRM member with its descendant SHA and
   requires exact-set verification.

## Authority and binding

- REUSE the accepted DEX canonical-root authority/seam from SRM
  `canonical-path.ts`: A-Conductor authors the canonical root + immutable
  binding; SRM verifies it. FMG must not create a second
  root/binding/task/claim/session/store authority.
- FMG owns only: child physical identity below the verified root,
  call-scoped file fingerprints / stale-write guard, and narrow wrappers
  around existing file mutation dispatches.
- Reuse existing `acquireScopes` lock authority fed with physical child
  keys; do not alter path-lock semantics.
- Any member head drift in the CROSS_REPO compatibility set invalidates the
  set until re-pin and focused review of the affected delta.

## Exact mutable scope

This docs lane (already executed by this WO file's creation): only
`docs/work-orders/WO-P1-413-fmg1-file-mutation-guard-v2.md`. Everything else
read-only; no merge by the author.

Proposed SRM implementation scope (BLOCKED until the closeout gate below
passes; no other SRM path may mutate without explicit scope expansion):

- NEW `src/sunday/fmg/child-identity.ts`
- NEW `src/sunday/fmg/fingerprint.ts`
- NEW `src/sunday/fmg/errors.ts`
- NEW `src/sunday/fmg/plan.ts`
- NEW `src/sunday/fmg/pipeline.ts`
- NEW `test/test-fmg-guard.js`
- NEW `licenses/DWB-LICENSE.txt`
- MODIFY `src/server.ts` (only the four CallTool cases: `write_file`,
  `create_directory`, `move_file`, `edit_block`)
- MODIFY `THIRD-PARTY-NOTICES.md`

## Forbidden scope

- No product/source/test/runtime file outside the exact scopes above; this
  docs bootstrap never grants product/source/runtime mutation authority.
- No new scheduler, store, broker, session, claim, review, or completion
  authority.
- No DWB LockManager/SessionRegistry/CoreStore/WorkspaceStore/broker
  import or reimplementation.
- No OS sandbox claim; shell/process/external-app edits remain outside the
  safety claim.
- No SRM remote invention: SRM has no accepted remote at present; do not
  invent hosted CI or push. The local candidate remains local-only unless
  authority changes.

## Architecture contract (frozen)

1. REUSE accepted DEX canonical-root authority/seam from SRM
   `canonical-path.ts`; A-Conductor authors canonical root + immutable
   binding, SRM verifies. No second root/binding/task/claim/session/store
   authority.
2. FMG owns only child physical identity below the verified root,
   call-scoped file fingerprints/stale-write guard, and narrow wrappers
   around existing file mutation dispatches.
3. Reuse existing `acquireScopes` lock authority fed with physical child
   keys; path-lock semantics unchanged.
4. Required pipeline:
   `PLAN #1 -> verify DEX root/admission -> physical child pre-gate ->
   capture fingerprints -> atomic multi-scope lock -> PLAN #2/re-resolve ->
   re-gate/canonical drift check -> stale fingerprint -> final cancellation
   check -> unchanged inner mutation -> refresh observation -> finally
   release`.
5. `move_file` locks source + destination atomically.
6. First slice covers `write_file`, `edit_block`, `move_file`,
   `create_directory`. `write_pdf` remains an explicit FMG-2/later gap.
   Shell/process/external-app edits are out of the safety claim; no OS
   sandbox claim.
7. No new scheduler/store/broker/session/claim/review/completion authority.
8. No `bootstrap.ts` admission wiring in this slice; default no-admission
   behavior is the accepted DEX self-observed/degraded local mode. Future
   provider wiring is separate work.
9. No changes to filesystem/edit internals except narrow server dispatch
   wrapping if required. Preserve UI `structuredContent` behavior.

## Provenance and license (DWB freeze)

Benchmark repo `sphakanin/dwb-mcp-studio-public` at exact SHA
`884fdc6a0d76779dc772842c8894d43d7c4ebd64`, MIT, Copyright (c) 2026
Phakanin.

- COPY_VERBATIM_WITH_NOTICE: `FileFingerprint` + `fingerprint` +
  `sameFingerprint` from benchmark `file-observer.ts`; preserve the 16 MiB
  SHA-256 cap and ENOENT `exists:false` behavior.
- ADAPT_WITH_ATTRIBUTION: `physicalPath`/`canonicalPath` ideas,
  `StaleFileConflictError` shape into `FmgError(ESTALEFILE)`, and `planTool`
  reduced to bounded SRM tool/arg names.
- REUSE_EXISTING: SRM DEX canonical-root seam + `acquireScopes`.
- REJECT/CUT: DWB `LockManager`/`SessionRegistry`/`CoreStore`/
  `WorkspaceStore`/broker as authority; no duplicate lock/session/store.

Required notices:

- `licenses/DWB-LICENSE.txt`: verbatim MIT license text.
- `THIRD-PARTY-NOTICES.md`: DWB section with repo + exact SHA.
- Provenance/attribution header in copied/adapted FMG source files as
  appropriate.

## Failure model (fail-closed typed codes)

`EADMISSION`, `EOUTSIDEROOT`, `ESTALEFILE`, `ECANONICALDRIFT`,
`EPATHSWAPPED`, `EDESTEXISTS`, `ESOURCEGONE`, `EEXDEV`, `ELOCKTIMEOUT`,
`ECANCELLED`, `EINTERNAL`.

Every typed guard failure must occur before the first mutation wherever
replay-safe behavior is claimed.

## RED-first acceptance matrix

1. Windows case aliases contend on one physical identity.
2. Junction alias same-key contention.
3. Junction/symlink escape outside the verified root => `EOUTSIDEROOT`,
   zero writes.
4. Wrong admission binding => `EADMISSION`; null admission preserves the
   documented degraded self-observed mode.
5. `.hidden` and `..notes` normal child names allowed; actual `..`
   traversal rejected.
6. Missing target resolves via deepest existing ancestor + missing tail.
7. Stale external write between plan and mutate => `ESTALEFILE`.
8. Cancel while waiting and after acquire => no later mutation /
   `ECANCELLED`.
9. Move source+destination atomic locking; source-gone/dest-exists/EXDEV
   typed failures.
10. Re-resolve/canonical drift => `ECANONICALDRIFT`.
11. Alias/symlink retarget late => `EPATHSWAPPED` or a documented explicit
    residual.
12. `write_file`/`edit_block`/`move_file`/`create_directory` pass-through
    behavior preserved when the guard allows.
13. Cross-repo root digest conformance includes ASCII/UNC and the
    non-ASCII `Straße` vector from accepted WO-P1-260.
14. `write_pdf`/shell remain explicitly ungated/out-of-scope, never implied
    covered.

## Verification and review

- RED proof before implementation (new suite fails on unmodified SRM base).
- `npm run build`.
- `test/test-fmg-guard.js`.
- Related file-handler/edit/path-lock/symlink/supervisor suites.
- Exact-path scope check.
- `git diff --check`.
- Strict UTF-8 / no U+FFFD.
- Added-line secret scan.
- License/notice verification.
- Exact compatibility proof against A-Wiki merged authority
  `dfe09e8817e6679433444f18292e295cb2f6a6d5` and SRM base
  `fe5abb3eb51ec712a970ec3a8cdcd5402619e992`.
- Independent exact-SHA GLM-5.3 MAX R3 review before acceptance.
- SRM has no accepted remote at present; do not invent hosted CI/push. The
  local candidate remains local-only unless authority changes.

## Compatibility and merge policy

- CROSS_REPO freeze per `00-AGENT-ENTRY.md`: one exact-SHA compatibility
  set `{AUTHORITY_REPO@SHA_AUTH, EXECUTION_REPO@SHA_EXEC}`; member drift
  invalidates until re-pin; global WIP budget is never multiplied per repo.
- Authority repo (A-Wiki) merges first; SRM candidate stays local-only
  (no accepted remote); no merge by the bounded author; GPT integrator owns
  acceptance/merge.

## Recovery and replay safety

- All typed guards fire before the first mutation wherever replay-safe is
  claimed; after any typed failure the on-disk state is the pre-mutation
  state or the explicitly documented residual.
- Cancellation (while waiting or after acquire) must never execute a later
  mutation (`ECANCELLED`).
- Interrupted implementation attempts reconcile from actual Git/runtime
  evidence before retry; unknown state fails closed.
- The guard is execution-local safety state only: per-session/attempt
  observed fingerprints never become durable cross-session authority.

## Closeout / dependency rule (next action)

SRM source mutation stays BLOCKED_PENDING_WO260_POST_MAIN until post-main CI
run `35499727319` completes SUCCESS. After that:

1. Re-pin A-Wiki main and post-main evidence.
2. Prove SRM `fe5abb3` worktree/base and no active conflicting claim.
3. Create an isolated local SRM worktree/branch from `fe5abb3`.
4. Re-run the mutation gate.
5. Dispatch the MAX author on the exact scope.
6. Freeze the SRM candidate + exact pair/set (SRM member replaced by the
   candidate descendant SHA; exact-set verification).
7. Deterministic verify + independent R3 review.
8. GPT acceptance.
9. Reconcile durable continuity and expose the FMG-2/`write_pdf` or
   COCKPIT-1 dependency as the roadmap dictates; checkpoint on Issue #413.

## Checkpoint log (append-only)

- [2026-09-20] WO-P1-413-FMG1-CONTRACT-001 docs-only governance bootstrap:
  this WO created on branch `docs/wo-p1-413-fmg1-contract` from dispatch
  head `dfe09e8817e6679433444f18292e295cb2f6a6d5`, converting the harvested
  FMG shaping decision (roadmap §10 + task packet) into the durable
  contract above. SRM implementation remains
  BLOCKED_PENDING_WO260_POST_MAIN (post-main CI `35499727319` PENDING at
  dispatch). No product/source/test/runtime file touched; no merge.
