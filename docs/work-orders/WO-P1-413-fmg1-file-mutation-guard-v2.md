# WO-P1-413 — FMG-1: SunDayRemoteMCP File Mutation Guard v2

Status: ACCEPTED / LOCAL_ONLY_EXECUTION_CLOSEOUT
Issue: #413
Parent roadmap: #397 / `docs/plans/2026-09-20-dwb-convergence-product-acceleration-roadmap.md`
Topology: CROSS_REPO
Risk: R3 — mutation concurrency, physical path identity, stale-write and cancellation safety
Owner/integrator: GPT-5.6 Sol

## Repository binding

Authority repo: `A:\GitHub\A-Wiki-Conductor`
Authority accepted main: `dfe09e8817e6679433444f18292e295cb2f6a6d5`

Execution repo: `A:\GitHub\SunDayRemoteMCP`
Accepted local-only DEX-2a compatibility anchor: `fe5abb3eb51ec712a970ec3a8cdcd5402619e992`
Execution branch to create: `feat/wo-p1-413-fmg1-file-mutation-guard`
Claim: `WO-P1-413-FMG1-FILE-MUTATION-GUARD-001`

Exact compatibility set:
`{A-Wiki-Conductor@dfe09e8817e6679433444f18292e295cb2f6a6d5, SunDayRemoteMCP@fe5abb3eb51ec712a970ec3a8cdcd5402619e992}`

SRM remains local-first. No remote creation, push or publication is authorized by this WO.

## Gate already satisfied

- WO-P1-259 DEX-2a P2-2 repair accepted as the local-only SRM anchor after independent exact-SHA R3 rereviews.
- WO-P1-260 repaired A-Wiki candidate passed independent exact-SHA R3 with P0/P1/P2/P3 = 0/0/0/0 and exact-head CI #1063.
- PR #403 merged as A-Wiki main `dfe09e8817e6679433444f18292e295cb2f6a6d5`.
- Fresh detached post-main A-Wiki verification at that merge SHA: 136 DEX/evidence/receipt/work-order/project-identity tests passed, diff-check clean, tree clean.
- SRM anchor `fe5abb3...`: build and canonical-path tests pass; tracked tree clean, with only known protected untracked `.serena/`.
- Cross-repo root-digest vectors remain exact:
  - `win32 + c:\repo\work` -> `aa2a21e52e96d0188faca668dcbeda48d6c0c454859ab32caee8cd325ad4c786`
  - `posix + /srv/repo` -> `e316d7049a2dcb0ae2be546a7fedb07d537ac769735d567e96985a2e0a73084f`
  - `win32 + \\server\share\repo` -> `b4f5a4a7b27cc64a7e11dff32f2412e63c279e11e5150b7bf3f97a8c6893c2ba`
  - `win32 + c:\repo\straße` -> `364893ee1c50f5c718bdaab1598cfee477a2659312ed41e7d045628dd87e996a`

## Goal

Wrap the first bounded set of supported in-process MCP file mutations with a physical-child-identity + stale-write guard while reusing the accepted DEX canonical-root authority and existing SRM path-lock authority.

Target sequence:

`verified admitted root -> PLAN #1 -> physical pre-gate -> capture observation fingerprint -> atomic multi-scope lock -> PLAN #2 -> root/child re-gate -> stale fingerprint check -> cancellation check -> existing tool mutation -> refresh observation -> release`

FMG is execution-local safety only. It is not a task store, claim system, scheduler, completion authority, OS sandbox, or replacement for A-Conductor admission.

## Root versus child authority

REUSE without redefining:
- `src/sunday/canonical-path.ts`
  - `resolveCanonicalRoot`
  - `verifyCanonicalBinding`
  - `normalizeForPlatform`
  - `canonicalDigest`
  - `PROJECT_IDENTITY_FAILED`
- A-Conductor remains the canonical root/binding authority.
- SRM independently recomputes/verifies the admitted root.
- Null admission remains the DEX seam's explicit self-observed degraded mode; FMG must not silently elevate it to verified admission.

FMG owns only:
- physical child identity under the verified root;
- execution-local file fingerprints;
- stale-write/canonical-drift/cancellation guard logic;
- mapping supported mutation tools into the guard pipeline.

No parallel root/worktree/digest/claim identity implementation is permitted.

## Exact execution-repo mutable scope

NEW:
- `src/sunday/fmg/child-identity.ts`
- `src/sunday/fmg/fingerprint.ts`
- `src/sunday/fmg/errors.ts`
- `src/sunday/fmg/plan.ts`
- `src/sunday/fmg/pipeline.ts`
- `test/test-fmg-guard.js`
- `licenses/DWB-LICENSE.txt`

MODIFY:
- `src/server.ts` — only the existing `write_file`, `create_directory`, `move_file`, and `edit_block` CallTool cases may be wrapped.
- `THIRD-PARTY-NOTICES.md` — DWB provenance notice only.

Everything else is READ ONLY.

Any required edit outside this list is `SCOPE_EXPANSION_REQUIRED` and must stop for integrator reconciliation.

## First bounded tool coverage

Guard:
- `write_file`
- `edit_block`
- `move_file`
- `create_directory` as the strictly necessary helper for fresh-tree writes

Explicitly NOT covered in FMG-1:
- `write_pdf` (FMG-2 follow-up)
- `set_config_value`
- terminal/process/shell/external-app writes
- `sunday_batch_exec` / `sunday_dispatch`
- any claim that arbitrary external writers are serialized by the in-process guard

The fingerprint guard may detect external change; it does not sandbox or lock external applications.

## Child identity contract

For every path-bearing argument:

1. expand/normalize the user spelling lexically;
2. reject lexical parent escape before filesystem access;
3. resolve physical identity using the deepest existing ancestor plus missing tail for create targets;
4. an existing broken symlink/reparse component fails closed; never fall back through it lexically;
5. normalize the resulting physical child representation with the accepted DEX `normalizeForPlatform`;
6. require separator-bounded containment under the verified canonical root;
7. feed the resulting physical child key into existing `acquireScopes`;
8. re-resolve after lock acquisition and reject key drift.

Existing `path-lock.ts` semantics are reused unchanged. FMG must not create a second lock manager.

## Pipeline contract

PLAN #1:
- pure tool/arg mapping, no filesystem effects.
- `write_file`: lock target.
- `edit_block`: lock + observe `file_path`.
- `move_file`: atomically lock source + destination; observe source.
- `create_directory`: lock target; existence-shape check only.

Physical pre-gate:
- verify root via DEX seam;
- canonicalize every child;
- reject outside-root/alias escape;
- capture ephemeral observation fingerprints before waiting.

Lock:
- one existing `acquireScopes` call over all physical keys;
- bounded wait;
- cancellation signal must flow into lock acquisition.

PLAN #2 / re-gate:
- recompute root + child physical identities after lock wait;
- any key change => typed canonical-drift failure;
- no silent re-acquire in this MVP.

Stale/cancel:
- compare pre-lock observation against current observation immediately before mutation;
- stale => fail before first mutation;
- final cancellation check immediately precedes first mutation;
- release always in `finally`.

Mutation:
- call the unchanged existing handler/tool body;
- preserve existing response/structuredContent behavior.

Refresh:
- update only execution-local observation data;
- never persist a project/task/claim truth store.

## Typed guard failures

At minimum:
- `EADMISSION`
- `EOUTSIDEROOT`
- `ESTALEFILE`
- `ECANONICALDRIFT`
- `EPATHSWAPPED`
- `EDESTEXISTS`
- `ESOURCEGONE`
- `EEXDEV`
- `ELOCKTIMEOUT`
- `ECANCELLED`
- `EINTERNAL`

Guard-origin failures render a bounded MCP error result. They grant no retry authority by themselves.

## RED-first acceptance matrix

Before implementation, write deterministic tests that fail on the unmodified accepted SRM anchor. At minimum:

1. Windows case variants converge to one child identity / one lock scope.
2. Junction alias path and real path converge.
3. Junction inside root escaping outside root => `EOUTSIDEROOT`, zero mutation.
4. Wrong admission binding => `EADMISSION`, zero mutation.
5. Null admission preserves explicit degraded self-observed behavior.
6. Ordinary dot-prefixed children remain valid; real parent escape fails.
7. Non-existing create target resolves through deepest existing parent.
8. External change after PLAN #1 => `ESTALEFILE`.
9. Cancel while waiting => `ECANCELLED`, no later mutation.
10. Cancel after acquire before write => no mutation; lock released.
11. Move source+destination scopes are acquired atomically.
12. Move source gone / destination exists / EXDEV => typed failures, no unsafe fallback.
13. Junction/symlink target changes between PLAN #1 and #2 => `ECANONICALDRIFT` or typed path-swap failure.
14. Existing `write_file`, `edit_block`, `move_file`, `create_directory` responses remain byte/shape compatible when allowed.
15. Existing file-handler/edit/path-lock/symlink-security/supervisor tests remain green.
16. Cross-repo canonical digest vectors above remain exact.

No sleep-based correctness proof where injected realpath/stat/clock hooks can make the scenario deterministic.

## DWB provenance / license freeze

Benchmark:
`sphakanin/dwb-mcp-studio-public@884fdc6a0d76779dc772842c8894d43d7c4ebd64`
License: MIT.

Accepted reuse decisions:
- `src/file-observer.ts::fingerprint`, `FileFingerprint`, `sameFingerprint`: COPY_VERBATIM where the exact body fits SRM.
- physical/canonical child path logic: ADAPT_WITH_ATTRIBUTION.
- `StaleFileConflictError`: ADAPT_WITH_ATTRIBUTION into FMG typed error.
- `planTool`: ADAPT_WITH_ATTRIBUTION to only the bounded SRM tools/arg names.
- DWB LockManager/session/core/workspace/broker: REJECT — existing SRM `acquireScopes` is reused.
- DWB test bodies are not copied wholesale; test ideas may be adapted with attribution.

Requirements:
- `licenses/DWB-LICENSE.txt` is the pinned MIT license text.
- `THIRD-PARTY-NOTICES.md` cites repository + exact upstream SHA.
- copied/adapted FMG source carries concise provenance headers sufficient to identify upstream source/SHA and adaptation status.

## Forbidden

- no second scheduler/task/claim/lease/review/completion authority
- no second root/worktree identity authority
- no new lock manager/session registry/store/broker
- no `path-lock.ts` semantic change
- no `workspace.ts` authority change
- no `mcp-tools.ts` error-union expansion
- no `schemas.ts` contract change
- no supervisor/lane-manager/bootstrap mutation
- no package/lock/tsconfig mutation
- no broad shell/external-write safety claim
- no reset/clean/stash/rebase/force-push
- no SRM remote creation/push/publication
- never touch protected untracked `.serena/`

## Verification

Required before candidate freeze:
- `npm run build`
- `node test/test-fmg-guard.js`
- directly related existing file-handler/edit/path-lock/symlink-security/supervisor suites
- cross-repo root-digest compatibility proof against A-Wiki merged main `dfe09e8...`
- `git diff --check`
- exact mutable-scope audit
- strict UTF-8 / no U+FFFD
- added-line secret/credential scan
- tracked worktree clean after commit

R3 acceptance:
1. freeze exact local-only SRM candidate SHA;
2. independent read-only GLM-5.3 MAX exact-SHA review;
3. deterministic Windows case/junction/symlink/stale-write/cancel/move tests;
4. exact compatibility set re-pinned to A-Wiki main;
5. GPT-5.6 Sol acceptance;
6. no SRM push/merge unless a later explicit task contract supersedes local-only policy.

## Replay / recovery

Every material delegated execution must leave a durable pointer under the implementation worktree's ignored `runs/WO-P1-413/` lane.

Before redispatch:
- recover pointer/process/result/Git;
- RUNNING is never duplicated;
- TERMINAL_UNHARVESTED is harvested first;
- interrupted mutation is reconciled by exact Git bytes/tests before retry;
- unknown dirty state fails closed.

## Closeout

FMG-1 is complete only when the exact local SRM candidate is independently R3-accepted against the exact A-Wiki compatibility main and all acceptance families above are green.

COCKPIT-1 remains blocked until FMG-1 acceptance.

## Acceptance checkpoint — 2026-09-20

FMG-1 satisfied the R3 acceptance gate and is accepted as a **local-only**
SunDayRemoteMCP execution candidate.

Accepted exact compatibility set:
`{A-Wiki-Conductor@bd4892185195d8c6a7c3a8652a75ec4db7f003b4, SunDayRemoteMCP@7c3c048d3d21291e842a944e50ecf0ca5d71f475}`.

Execution candidate:
- SRM parent / accepted DEX-2a anchor:
  `fe5abb3eb51ec712a970ec3a8cdcd5402619e992`;
- frozen FMG-1 candidate:
  `7c3c048d3d21291e842a944e50ecf0ca5d71f475`;
- exact changed tracked paths: 9, matching this Work Order;
- SRM remains local-only with no accepted remote, push, or publication.

Independent exact-SHA R3 review:
- durable run:
  `run:WO-P1-413:r3-review:1:a1:c509c9d84b7f`;
- verdict: PASS;
- severities: P0=0 / P1=0 / P2=0 / P3=4 nonblocking;
- pipeline ordering, DEX/root authority reuse, physical child identity,
  stale/cancel/drift, atomic move/error semantics, server first-slice
  integration, degraded admission and DWB provenance/license all passed.

Deterministic evidence:
- `npm run build`: PASS;
- live Windows FMG M1-M14 / U1-U6 guard suite: PASS;
- directly related file/path/symlink/edit suites: PASS;
- current-main DEX identity/evidence/execution tests: 85 PASS;
- authority PR #423 merged to
  `bd4892185195d8c6a7c3a8652a75ec4db7f003b4`;
- post-main CI run `35501688689`: SUCCESS at that exact SHA.

Nonblocking P3 residuals remain outside FMG-1:
- dedicated EINTERNAL / non-EXDEV generic handler-throw tests are absent;
- Windows trailing-dot/space alias policy remains a DEX/platform policy gap,
  not an FMG-local normalization authority;
- one supervisor-suite failure was not reproducible and touched no FMG source;
- `THIRD-PARTY-NOTICES.md` UTF-8 BOM pre-existed the candidate.

Acceptance consequences:
- FMG-1 is **ACCEPTED_LOCAL_ONLY**;
- this does not authorize SRM remote creation, push, merge or publication;
- the COCKPIT-1 dependency gate is satisfied together with the accepted GOT
  chain;
- subsequent A-Wiki main movement requires ordinary consumer re-pin but does
  not rewrite the accepted FMG candidate bytes.
