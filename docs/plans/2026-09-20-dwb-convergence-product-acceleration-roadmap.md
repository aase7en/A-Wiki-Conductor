# DWB Convergence / Product-Acceleration Roadmap — 2026-09-20

Status: ACTIVE ROADMAP CANDIDATE
Work Order: `WO-P1-397`
Issue: #397
Task topology: `CROSS_REPO`
Primary objective: shortest safe path to a genuinely usable A-Sunday Conductor product.

## 0. Executive decision

A-Sunday should **not** become DWB MCP Studio.

The convergence strategy is:

`KEEP OUR CONTROL-PLANE BRAIN + BORROW DWB'S SHARP EXECUTION-EDGE PATTERNS + REMOVE OUR DELIVERY DEBT`

The fastest product path is not a rewrite. It is a convergence program that:

1. wires existing A-Conductor continuity machinery into live generated truth;
2. adds DWB-grade file identity/stale-write protection to SunDayRemoteMCP by reusing and, where appropriate, directly adapting MIT-licensed DWB code;
3. exposes the truth we already hold through the existing A-Sunday desktop UI instead of building a second dashboard stack;
4. classifies and retires worktree/dependency/legacy-surface debt only after deterministic ownership/reachability proof;
5. keeps Zero-Relay, Hook/STM/observability, DEX and provider-neutral roadmaps as compatible upstream work rather than replacing them.

### Smallest usable-product gate

The first product gate is **LOCAL-USABLE-1**.

It is reached when all of the following are true:

- current task/execution/repo truth is generated from durable authority rather than hand-maintained status prose;
- the local SRM execution path cannot silently overwrite an observed file through Windows case/junction aliasing or a stale-read race on supported file tools;
- the existing A-Sunday desktop app shows one concise read-only runtime cockpit with task/lane/repo/HEAD/claim/execution/blocker/next-action truth;
- interruption/unknown-outcome states are operator-visible and never imply blind retry;
- a fresh session can recover the current task from durable state without asking the user to reconstruct chat history.

Full automatic worktree deletion, dependency slimming, tray polish, remote transport and broad tool-surface redesign are **not blockers** for LOCAL-USABLE-1.

## 1. Frozen baselines and authority

### Authority repo

`A:\GitHub\A-Wiki-Conductor`

Roadmap base:
`61315b71d510ce8ba88498018bb6c1d76dab144d`

### Execution substrate

`A:\GitHub\SunDayRemoteMCP`

Planning baseline:
`ac01b37ba2e4b9d0249addf7694c0b91deb352c7`

The execution repo is local-first and has no remote configured at this planning snapshot. Its root has only untracked `.serena/`; no source mutation is authorized by this roadmap WO.

### External benchmark

`sphakanin/dwb-mcp-studio-public@884fdc6a0d76779dc772842c8894d43d7c4ebd64`

Local read-only clone:
`A:\GitHub\_benchmarks\dwb-mcp-studio-public-884fdc6`

DWB license: MIT, copyright (c) 2026 Phakanin.

DWB's `THIRD-PARTY.md` explicitly separates DWB source from downloaded Desktop Commander, OpenAI tunnel-client and npm dependencies. Copying DWB source is allowed under MIT when the copyright + permission notice is retained with substantial copied portions. This roadmap does **not** treat third-party hosted-service access or external component rights as inherited from DWB.

## 2. Governing architecture that must survive convergence

### A-Wiki / A-Sunday Conductor owns

- Work Orders/tasks;
- claims/leases and mutable-scope authority;
- project/repository topology;
- admission/routing/WIP;
- retry/replay authorization;
- review/acceptance/merge/release;
- durable continuity and final completion truth.

### SunDayRemoteMCP owns

- execution/capability implementation;
- filesystem/search/edit;
- Git inspection;
- terminal/process/batch execution;
- durable dispatch/status/output/cancel/harvest/recover;
- execution-local safety;
- semantic/LSP capabilities.

### DWB-derived components may never become

- another task store;
- another scheduler;
- another claim/lease authority;
- another completion authority;
- another project-memory SSoT;
- another provider/secret authority.

`DWB PATTERN != DWB AUTHORITY MODEL`

## 3. Decision vocabulary

Every imported idea/code path is classified before implementation.

### COPY_VERBATIM

Use when:

- DWB code is MIT;
- implementation language fits directly;
- trust boundary is compatible;
- substantial copying is cheaper/safer than rewriting;
- attribution can be preserved;
- tests can bind exact behavior.

Required:
- copyright/MIT attribution in `THIRD-PARTY-NOTICES.md` or equivalent;
- file-level notice when a substantial file/function body is copied;
- exact upstream SHA and source path in the child WO.

### ADAPT_WITH_ATTRIBUTION

Use when the DWB implementation is useful but must be changed for SRM/A-Conductor contracts. Preserve attribution for substantial copied structure/body.

### CLEAN_ROOM_REIMPLEMENT

Use behavior/spec only when direct copying would import an incompatible authority model, runtime stack, hidden dependency or operational assumption.

### REUSE_EXISTING

Prefer an already-accepted A-Wiki/SRM seam and only add the missing adapter/wiring.

### CUT_OR_DEFER

Remove from default product path or postpone when it does not help LOCAL-USABLE-1 or when it duplicates existing authority.

## 4. Convergence matrix

| DWB capability / source | Decision | A-Sunday/SRM destination | Why |
|---|---|---|---|
| `src/file-observer.ts::canonicalPath` | **ADAPT_WITH_ATTRIBUTION** | SRM file identity seam adjacent to `src/sunday/path-lock.ts` / `workspace.ts` | Same TypeScript runtime; solves Windows case/junction alias identity |
| `src/file-observer.ts::fingerprint` + `sameFingerprint` | **COPY_VERBATIM** | SRM observed-file version state | Pure Node/TypeScript logic with no DWB session authority dependency; preserve DWB MIT attribution and exact upstream SHA; child WO may adapt only surrounding types/call sites while recording any changed copied body as attributed adaptation |
| `src/file-observer.ts::planTool` | **ADAPT_WITH_ATTRIBUTION** | SRM tool mutation planner | Tool names/contracts differ; pattern is valuable |
| DWB lock -> re-plan -> gate -> fingerprint -> dispatch sequence | **ADAPT_WITH_ATTRIBUTION** | SRM file mutation dispatch seam | Highest-value TOCTOU protection |
| `src/core-hardening-test.ts` Windows case/junction tests | **ADAPT_WITH_ATTRIBUTION** | SRM regression tests | High-signal portable regression cases; adapt harness/imports while retaining DWB provenance |
| DWB stale-write tests | **ADAPT_WITH_ATTRIBUTION** | SRM regression tests | Prevents silent overwrite regressions; SRM harness and mutation seams differ |
| `src/payload-guard.ts` | **ADAPT_WITH_ATTRIBUTION**, P1 unless evidence elevates | SRM MCP response boundary | Useful context/transport protection, but not needed before file-safety + cockpit |
| `src/payload-guard-test.ts` Thai/PII/retention cases | **ADAPT_WITH_ATTRIBUTION** | SRM tests | Strong reusable edge cases when PAYLOAD-1 starts |
| request outcome vocabulary: cancelled / pending / unknown | **CLEAN_ROOM REIMPLEMENT** | A-Sunday operator vocabulary over existing states | Semantics align, but map to our durable execution taxonomy |
| `src/request-lifetime.ts` cancellation ideas | **REUSE_EXISTING** | existing SRM AbortSignal/path-lock/supervisor paths | We already have bounded waits/cancel; use DWB only as comparison evidence and do not add duplicate lifetime authority |
| DWB worker/session pool | **REUSE_EXISTING** | A-Conductor/SRM existing worker/execution model | Reject the DWB pool as a new authority; reuse our existing worker/execution model |
| DWB session registry persistence | **REUSE_EXISTING** | existing A-Conductor durable jobs/execution evidence | Reject DWB session persistence as project authority; ours is stronger and cross-session/cross-repo aware |
| DWB broker event JSONL as project state | **REUSE_EXISTING** | existing durable authority + Hook projection | Keep existing authoritative stores; DWB event shape may inform observability only |
| Workspace aliases | **CUT_OR_DEFER** | SRM automatic workspace detection first | Nice UX, not a LOCAL-USABLE-1 blocker |
| Dashboard status cards / recent events | **CLEAN_ROOM_REIMPLEMENT** | existing `desktop_ui.py`, `ControlCenterService`, operator views | Borrow information architecture, not C#/XAML/PowerShell implementation |
| DWB `dashboard.ps1/.xaml` | **CUT_OR_DEFER** | none | We already have Tk/Ttk product UI; a second UI stack is out of the fast lane |
| DWB `launcher.cs`, `app.ps1` | **CUT_OR_DEFER** | existing A-Sunday launcher/desktop app | A second launcher stack slows product convergence |
| startup/tray preferences | **REUSE_EXISTING** | existing A-Sunday preferences/autostart | Reuse current settings + instance autostart; borrow only UX expectations, with tray optional polish |
| `doctor.mjs` behavior | **REUSE_EXISTING** | existing readiness/doctor seams | Consolidate current diagnostics; DWB is comparison evidence, not a second diagnostic authority |
| DPAPI API-key storage | **REUSE_EXISTING** | existing provider/secret resolver boundaries | Keep the existing secret authority; do not import DWB credential storage |
| Setup downloads external worker/tunnel | **CUT_OR_DEFER** | current installer/runtime setup | Different product boundary; avoid importing DWB's external-runtime coupling |
| broker circuit breaker/backoff | **REUSE_EXISTING** | existing supervised execution/recovery | No need for another worker supervisor |
| workspace mutation gate | **ADAPT_WITH_ATTRIBUTION** | SRM local safety | Adapt only execution-local file-boundary behavior; A-Conductor retains project mutation authority |
| DWB release ZIP verification idea | **CLEAN_ROOM_REIMPLEMENT** | existing release/installer CI | Reimplement the release-verification behavior in our existing CI; do not import the whole DWB release pipeline |

## 5. What we already have and must reuse

### 5.1 Generated Operational Truth foundations

Existing:
- `src/a_conductor/continuity_projection.py`
- `ContinuityProjectionFoldAdapter`
- deterministic renderers for `CURRENT-WORK.md`, `handoff.md`, `COLLAB.md`;
- candidate-SHA binding;
- lease-gated `AgentChangeApplier`;
- expected-content SHA preconditions;
- full read-back verification;
- `tests/test_continuity_projection.py`.

Observed gap:
- production references to `ContinuityProjectionFoldAdapter` are not established by the current symbol-reference audit; the adapter is heavily tested but appears primarily wired in tests.

Decision:
**REUSE_EXISTING. Wire it; do not design another projection store or renderer.**

### 5.2 SRM execution/safety foundations

Existing:
- `src/sunday/path-lock.ts`;
- non-empty path scope requirement for mutating lanes;
- bounded lock waits;
- `src/sunday/workspace.ts`;
- `src/sunday/repo-snapshot.ts`;
- durable `ExecutionSupervisor`;
- atomic dispatch manifests;
- output caps;
- harvest/recover/replay classification;
- `supervisor-evidence.ts`;
- compact tool policy;
- semantic/LSP foundation.

Decision:
**EXTEND these seams with DWB file identity/fingerprint behavior. Do not insert a second broker.**

### 5.3 Existing A-Sunday operator UI

Existing:
- `src/a_conductor/desktop_ui.py`;
- `ControlCenterService.snapshot()`;
- graph operator view;
- provider/operator views;
- settings/preferences;
- instance autostart;
- runtime readiness;
- connector recovery;
- doctor/readiness seams;
- current monitor windows.

Decision:
**Build Runtime Cockpit inside this UI. Do not copy DWB's C#/XAML dashboard.**

## 6. What should be cut, retired or moved out of the default path

"Cut" means evidence-backed removal from the default product path. It never authorizes broad delete.

### 6.1 Manual current-truth prose

Cut from the authoritative region after generated projection adoption:
- manually maintained current HEAD;
- manually maintained current task status;
- manually maintained active owner/claim;
- manually maintained current blocker;
- manually maintained next action.

Historical narrative may remain behind an explicit historical anchor.

Target:
`durable facts -> projection -> human-readable file`

not:
`human edits -> project truth`.

### 6.2 Worktree accumulation

Observed current machine inventory before this roadmap:
- A-Wiki had hundreds of worktrees in the prior audit;
- SRM had dozens;
- paths were real, not merely prunable Git metadata.

Do not broad-prune.

Cut only after ownership-aware classification proves:
`RELEASED_SAFE_TO_ARCHIVE`.

### 6.3 SRM default dependency surface

Current SRM carries a large inherited dependency/tool/UI surface while its compact default exposes only a small tool set plus `sunday_*`.

Direct dependency name reachability scan found no literal TypeScript reference in `src/` for at least:
- `@tiptap/pm`;
- `remark`;
- `remark-gfm`;
- `remark-parse`;
- `unified`.

This is **candidate evidence only**, not removal authority. Dynamic/build/runtime use must be checked before deletion.

Many other dependencies are used only outside `src/sunday` and the thin entry seam, including PDF/editor/UI/data/remote capabilities.

Decision:
- define **compact core** and **optional legacy/full-toolset feature packs**;
- remove a dependency only after AST/import/build/test/package reachability proof;
- do not break `SUNDAY_FULL_TOOLSET=1` accidentally;
- move remote/cloud/telemetry surfaces out of the local MVP dependency path where practical.

### 6.4 Duplicate UI/runtime stacks

Cut from the roadmap:
- DWB C#/XAML dashboard;
- DWB launcher implementation;
- a second web dashboard for LOCAL-USABLE-1;
- a new state DB solely for cockpit;
- a new tray framework before current app launch/close behavior is proven insufficient.

### 6.5 Stale roadmap prose / long-lived draft overlap

`PROJECT-PLAN.md` is currently protected by open draft PR #243 and stacked PR #244.

Do not overwrite them.

Reconciliation rule:
1. extract any still-unique accepted intent;
2. classify as KEEP / DEFER / SUPERSEDED;
3. retarget or close obsolete drafts only after evidence;
4. then add one concise "Product Fast Lane" section to PROJECT-PLAN rather than another large duplicate roadmap block.

## 7. Product Fast Lane

### Dependency shape

```text
WO397 ROADMAP FREEZE
    |
    +--> GOT-1 Generated Operational Truth wiring ------------------+
    |                                                               |
    +--> FMG-1 SRM File Mutation Guard v2 ----------------------+    |
    |                                                           |    |
    +--> WTL-0 Worktree inventory/classifier design (read-only) |    |
                                                                |    |
GOT-1 + FMG-1 --------------------------------------------------+--> COCKPIT-1
                                                                     |
                                                                     +--> LOCAL-USABLE-1

WTL-0 -> WTL-1 read-only lifecycle classifier -> WTL-2 bounded cleanup executor (later)
LOCAL-USABLE-1 -> PAYLOAD-1 if needed -> DEPDIET-1 -> FRONTDOOR-1 polish
```

### Parallel WIP after WO397

Preferred **fill order for free capacity** after recovering and reconciling all already-owned executions/claims:
- Mutable lane A: GOT-1 in A-Wiki.
- Mutable lane B: FMG-1 in SunDayRemoteMCP.
- Read-only lane C: WTL-0 inventory/classifier evidence when it does not consume the one independent-review slot needed by a frozen candidate.
- Independent reviewer: one frozen-candidate review at a time under the global 3+1 budget.

This list grants no right to evict, steal, or overlap an active Zero-Relay, Hook, DEX, release, or other accepted claim. Existing safe in-flight work is recovered/harvested first; newly READY fast-lane nodes fill only currently available global WIP unless a later explicit authority decision reprioritizes an owned lane.

Do not run two writers on `PROJECT-PLAN/CURRENT-WORK/COLLAB`.

## 8. Phase GOT-1 — Generated Operational Truth

Topology: `CONTROL_PLANE_ONLY`
Risk: at least R2; R3 if closeout/lease/retry authority changes.

### Reuse

- `ContinuityProjectionFoldAdapter`;
- `ProjectionFacts`;
- GoalCloseout fold port;
- `AgentChangeApplier`;
- existing claims/leases;
- existing projection tests.

### Work

1. locate the production closeout assembly seam;
2. inject the existing projection fold adapter rather than adding a new writer;
3. derive projection facts only from durable authority;
4. run first-adoption against current file shapes in an isolated fixture/copy;
5. keep historical text byte-preserved outside the machine sentinel;
6. make repeated fold idempotent;
7. surface typed failure when current bytes drift or candidate identity changes;
8. never parse the Markdown projection back as authority.

### Acceptance

- successful GoalCloseout writes machine-owned current sections through existing mutation authority;
- `CURRENT-WORK/handoff/COLLAB` current data matches durable state;
- second identical fold produces zero unnecessary writes;
- candidate SHA mismatch fails closed;
- stale content precondition produces no optimistic completion;
- fresh session recovery does not require a human to repair status prose;
- no second store or projection authority is introduced.

### Cut after acceptance

Stop manually editing live task/HEAD/blocker/next-action fields in the machine-owned region.

## 9. Phase WTL — Ownership-aware Worktree Lifecycle

Topology: `CONTROL_PLANE_ONLY` for classification authority; local Git cleanup executes only through the accepted repo-operation boundary.
Risk:
- WTL-0 read-only design: R1/R2;
- WTL-1 classifier: R2;
- WTL-2 delete/archive: R3 consequential operation.

### WTL-0 — read-only inventory first

Collect per worktree:
- absolute physical path;
- repo;
- branch/detached state;
- HEAD;
- dirty/untracked counts;
- active WO/task/claim/lease;
- open PR/remote branch;
- merge ancestry;
- accepted candidate pointer if known;
- active process/execution evidence;
- last durable task evidence;
- continuity fold state.

### Canonical classifier

Minimum states:
- `ACTIVE_OWNED`
- `REVIEW_FROZEN`
- `MERGED_NOT_FOLDED`
- `RELEASED_SAFE_TO_ARCHIVE`
- `DIRTY_PROTECTED`
- `CLAIM_CONFLICT`
- `PROCESS_OR_EXECUTION_ACTIVE`
- `REMOTE_UNMERGED`
- `UNOWNED_UNKNOWN`
- `EVIDENCE_INCOMPLETE`

Only `RELEASED_SAFE_TO_ARCHIVE` is cleanup-eligible.

### DWB pattern reused

Borrow the **active-work probe before restart/reclaim** idea, but map it to our stronger ownership/execution evidence. DWB's session/worker "busy" truth is not enough to delete a project worktree.

### WTL-2 cleanup rules

No broad `git worktree prune` as authority.

For each candidate:
1. re-pin physical path + HEAD;
2. verify clean or explicitly archived;
3. verify no claim/lease;
4. verify no active process/execution;
5. verify accepted merge ancestry or explicit abandonment authority;
6. verify continuity folded;
7. remove exactly one bound worktree;
8. verify Git metadata and filesystem postcondition;
9. write one durable cleanup event.

## 10. Phase FMG-1 — SunDayRemoteMCP File Mutation Guard v2

Topology: `CROSS_REPO`
Authority WO: A-Wiki.
Implementation repo: SunDayRemoteMCP.
Risk: R3 because it affects mutation concurrency, path identity and retry/stale-write semantics.

### Direct DWB reuse candidates

Upstream:
`dwb-mcp-studio-public@884fdc6`

Primary source:
`src/file-observer.ts`

Candidate functions:
- `canonicalPath`;
- `fingerprint`;
- `sameFingerprint`;
- `planTool`;
- `StaleFileConflictError`.

Primary regression source:
`src/core-hardening-test.ts`

### Required SRM adaptation

Do **not** copy DWB `LockManager` wholesale.

DEX/ADR-0002 already fixes canonical worktree/repository identity authority: A-Conductor admission owns the canonical physical worktree identity and immutable binding digest; SRM recomputes/verifies that admitted root at the physical execution seam. FMG-1 must reuse that exact root identity contract. DWB-derived `canonicalPath` logic may canonicalize **child file identities under the already verified root**, but must never redefine the worktree/repository root, admission digest, claim, or mutation authority.

Keep SRM:
- `acquireScopes`;
- read/mutate modes;
- bounded waits;
- lane manager;
- supervisor evidence.

Add:
1. physical/canonical file identity;
2. Windows case folding only through proven physical identity semantics;
3. junction/symlink-aware path resolution;
4. per-session/attempt observed fingerprint cache only as execution-local safety state;
5. tool mutation plan;
6. workspace boundary gate;
7. lock acquisition;
8. **re-plan after lock acquisition**;
9. workspace boundary gate again;
10. compare observed fingerprint immediately before mutation;
11. dispatch write only when still safe;
12. refresh observation after successful read/write.

### Mutation pipeline

```text
TOOL REQUEST
 -> resolve/bind workspace
 -> PLAN #1
 -> pre-gate
 -> acquire path scope(s)
 -> PLAN #2 after wait
 -> re-gate workspace/physical identity
 -> stale fingerprint check
 -> execute underlying tool
 -> update observations/evidence
 -> release scope
```

### Important boundary

This protects supported MCP file tools.

It is **not an OS sandbox** and does not magically serialize arbitrary shell edits or external applications.

Shell/process mutation continues to require task scope/claim/repo identity and must not be described as protected by file fingerprints unless the exact command path is brought under a proven mutation plan.

### Acceptance tests

At minimum adapt/copy:
- Windows case variants share identity;
- junction aliases share identity;
- junction that escapes workspace is rejected;
- ordinary dot-prefixed child remains valid;
- a read followed by external change then write fails stale;
- waiting writer re-plans after acquiring lock;
- cancellation while waiting never executes later;
- overlapping write paths serialize;
- non-overlapping paths may proceed;
- unknown mutation target fails closed;
- move locks source + destination;
- write/create operations cannot escape workspace through a late alias change.

### Attribution

If substantial DWB implementation/test bodies are copied, update SRM `THIRD-PARTY-NOTICES.md` with:
- DWB project;
- upstream repo;
- exact SHA;
- copied/adapted paths;
- MIT copyright + license notice.

## 11. Phase COCKPIT-1 — Runtime Cockpit MVP

Topology: primarily `CONTROL_PLANE_ONLY`.
Risk: R2 if read-only projection; R3 only if consequential commands are added.

### Reuse

- `desktop_ui.py`;
- `ControlCenterService.snapshot`;
- graph operator view;
- provider operator view;
- execution/job stores;
- Hook/STM projection when accepted;
- existing preferences/readiness/connector monitor.

### DWB lesson

DWB wins at operational legibility.

Borrow the information architecture, not its UI implementation.

### One-screen MVP

Show:
- Work Order / task;
- topology;
- lane / executor / provider/harness;
- authority repo;
- execution repo;
- active repo/worktree/branch/HEAD;
- claim/lease state;
- execution ID + exact process identity when available;
- derived execution state;
- last activity;
- last meaningful progress;
- verification/review/CI gate state;
- blocker code;
- replay safety;
- exact next safe action.

### Operator vocabulary

Map internal detail into concise states without losing underlying evidence:

- `NOT_DISPATCHED`
- `PENDING_SCOPE`
- `RUNNING`
- `WAITING_EXTERNAL`
- `STALLED_RECONCILE`
- `TERMINAL_UNHARVESTED`
- `OUTCOME_UNKNOWN`
- `FAILED_VERIFIED`
- `COMPLETED_VERIFIED`

Never show "retry" as safe merely because transport disconnected.

### No new store

Cockpit is a UI consumer/projection, not a new state plane. The accepted Hook/STM roadmap already requires Desktop/Web/Extension surfaces to consume the same normalized Monitor Projection. COCKPIT-1 must therefore extend or consume that shared projection contract when available. If COCKPIT-1 lands earlier, any temporary adapter must read existing durable/operator views directly, create no independent schema/store, and have an explicit convergence path into the shared Monitor Projection rather than becoming a permanent desktop-only truth model.

`DURABLE AUTHORITY -> SHARED MONITOR/OPERATOR PROJECTION -> COCKPIT`

not:
`COCKPIT DB -> TASK TRUTH`.

### Initial command scope

LOCAL-USABLE-1 is read-only for high-consequence actions.

Existing safe start/stop actions may remain where their authority already exists, but new retry/reassign/cleanup controls wait for the A-Conductor Command Gateway contract.

## 12. Phase PAYLOAD-1 — MCP Payload Guard

Default priority: P1, promoted only if oversized-result failures are materially blocking LOCAL-USABLE-1.

DWB source:
`src/payload-guard.ts`

DWB tests:
`src/payload-guard-test.ts`

### Why useful

- prevents multi-megabyte tool results from destabilizing chat/transport;
- keeps a bounded preview;
- can retain structured content only when safe;
- supports redacted/off archival;
- includes PII/secret-oriented regression cases;
- gives operator a clear next action.

### Adaptation constraints

- use SRM's existing output/evidence paths where possible;
- archive is optional and local;
- default to redacted or off;
- no raw secret retention;
- do not create a second execution result authority;
- guarded response must preserve typed error semantics when structured payload is truncated.

## 13. Phase DEPDIET-1 — SRM Dependency Diet

Topology: `EXECUTION_SUBSTRATE_ONLY` under A-Wiki Work Order when project-governed.
Risk: R2 because package/release behavior changes.

### Goal

Make the default local SRM install reflect the compact product rather than the full inherited Desktop Commander surface.

### Required audit

For every direct dependency:
- static import/reference;
- dynamic import;
- build-script use;
- test-only use;
- optional full-toolset use;
- postinstall/release use;
- transitive requirement;
- package/binary impact.

### Current candidate removals

The initial literal-reference scan found zero TypeScript references in `src/` for:
- `@tiptap/pm`;
- `remark`;
- `remark-gfm`;
- `remark-parse`;
- `unified`.

These are **investigation candidates only**.

### Feature-pack boundary

Default compact core should prioritize:
- MCP protocol;
- filesystem/read/edit;
- process/shell;
- search;
- workspace;
- repo snapshot;
- background execution;
- durable evidence;
- file mutation guard;
- semantic core.

Candidates for optional/later packs:
- rich file-preview UI;
- rich document editor;
- PDF conversion stack;
- remote-device/cloud path;
- telemetry/analytics;
- legacy publishing extras.

Do not delete a capability solely because it is outside `src/sunday`; prove the default product no longer needs it first.

### 13.1 Feature-pack boundary design — WO-P1-518 (2026-09-23)

Status: bounded design only. WO-P1-518 mutates no SunDayRemoteMCP package or source; every SRM fact below is READ_ONLY evidence from the exact clones cited. This design converts the parent #472 `NO_DIRECT_DELETE_CANDIDATE` audit into pack boundaries, coupling truth, acceptance contracts and successor packet conditions.

Evidence snapshot:

- Current accepted execution-substrate evidence is exact SRM SHA `2f033cfb1f61b6dff9c2e55264cca6f2a9125e95`: later accepted WO-P1-507 pins `A:\\GitHub\\SunDayRemoteMCP` at that SHA, and the current macOS clone is clean `main@2f033cfb...` at the same commit. The repository still has no configured Git remote, so this is accepted local-SHA execution-substrate evidence rather than a remotely verified repository identity.
- `e3ec2e06baf464e68c4166faae65f51c60fd5477` is the accepted first dependency-diet predecessor (#473) and direct parent of `2f033cfb...`; it is not the current execution-substrate HEAD.
- Post-slice direct graph: 27 production roots + 1 optional (`caffeinate`) + 14 dev roots.

#### Pack definitions and dependency ownership

`PACK-R` — remote-device/cloud transport (2 roots + 1 optional):

- Roots: `@supabase/supabase-js`, `open`; optional `caffeinate` (macOS no-sleep, used only by `npm-scripts/remote.ts`).
- Source surface: `src/remote-device/**` (device, authenticator, remote-channel, desktop-commander-integration, scripts) + `src/npm-scripts/remote.ts` CLI (`sunday-mcp remote` argv branch in `src/index.ts`).
- Function: a device/transport mode, not MCP tools; zero compact-tool-surface overlap.
- Tests: `test-remote-channel-reconnect.js`, `test-remote-channel-signed-out.js`, `test-remote-inflight-call-fast-fail.js`, `test-remote-transport.js`.

`PACK-D` — rich-document/editor (17 roots, two independently isolatable facets):

- Facet `D1` editor-preview (browser, 10 roots): `@tiptap/core`, `@tiptap/starter-kit`, `@tiptap/extension-image`, `@tiptap/extension-table`, `@tiptap/extension-table-row`, `@tiptap/extension-table-header`, `@tiptap/extension-table-cell`, `tiptap-markdown`, `markdown-it`, `highlight.js`.
  Source surface: `src/ui/file-preview/**` browser modules; served artifact is the esbuild bundle `dist/ui/file-preview/preview-runtime.js` produced by `scripts/build-ui-runtime.cjs`. Node-side reference is types-only (`shared/preview-file-types.js` used by `src/handlers/filesystem-handlers.ts`).
  Tests: `test-markdown-editor-edit-diff.js`, `test-markdown-editor-roundtrip.js`, `test-markdown-preview.js`, `test-file-preview-image-runtime.js`, `test-file-preview-directory-runtime.js` (jsdom-style tests mount the real compiled editor from `dist`).
- Facet `D2` document handlers (Node, 7 roots): `@opendocsg/pdf2md`, `md-to-pdf`, `pdf-lib`, `unpdf`, `exceljs`, `pizzip`, `sharp`.
  Source surface: `src/tools/pdf/**`, `src/utils/files/{pdf,docx,excel}.ts`, factory routing in `src/utils/files/factory.ts`, `src/tools/pdf/lib/pdf2md.ts` (CJS `require` of `@opendocsg/pdf2md/lib/util/pdf`), dynamic `sharp` in `src/tools/pdf/extract-images.ts`.
  Tests: `test-pdf-chrome-cache.js`, `test-pdf-creation.js`, `test-pdf-parsing.js`, `test-excel-files.js`.

Compact core retained roots (8): `@modelcontextprotocol/sdk`, `@vscode/ripgrep`, `cross-fetch`, `fastest-levenshtein`, `isbinaryfile`, `proper-lockfile`, `zod`, `zod-to-json-schema`.

#### Verified coupling truth (build/package/test/release)

1. TypeScript build: `tsconfig.json` compiles all of `src/**` — including `src/remote-device/**`, `src/ui/file-preview/**` and every D2 module — into `dist`. Any root removal without a compile seam breaks `tsc` before runtime.
2. Startup import chains (ESM, eagerly evaluated on every `sunday-mcp` invocation, compact included):
   - `src/index.ts` → `npm-scripts/remote.ts` → `remote-device/device.ts` → `remote-channel.ts` → `@supabase/supabase-js`; authenticator → `open`. PACK-R is import-chain coupled to the entrypoint.
   - `src/index.ts` imports `ensureChromeAvailable` from `tools/pdf/markdown.js` and calls it at server init: the compact default pre-checks/downloads Chrome for PDF generation. D2 is entrypoint-coupled.
3. Compact tool semantics: `read_file`, `write_file`, `get_file_info` all route through `getFileHandler`; the factory statically registers `PdfFileHandler`, `DocxFileHandler`, `ExcelFileHandler`; `src/tools/filesystem.ts` additionally imports `tools/pdf/index.js` statically. Compact `start_search` indexes `.docx` (static `pizzip`) and `.xlsx` (dynamic `exceljs`). D2 is semantically fused with four compact-allowlisted tools.
4. PACK-D1 editor has no Node-runtime import; its coupling is build-time only (tsc compile + esbuild bundle + tests against `dist`).
5. Package/publish: `files: ["dist", ...]` ships prebuilt `dist`; `scripts/build-mcpb.cjs` copies `package.json.dependencies` verbatim into the MCPB bundle and runs `npm install --omit=dev`, so every production root — both packs — ships in the default `.mcpb`. Dockerfile installs and builds from source (needs build-time availability of D1 roots).
6. Tests: `test/run-all-tests.js` auto-discovers every `test-*.js`; pack tests hard-fail when pack roots are absent. Test isolation needs pack-gated skips (dependency-presence probe or env), never test deletion.
7. Full-toolset compatibility: `SUNDAY_FULL_TOOLSET=1` (`src/sunday/tool-policy.ts`) exposes all tools. With both packs installed, full-toolset behavior must remain byte-equivalent; without a pack, full-toolset must degrade to the same typed fallbacks as compact for that pack's surfaces.
8. Successor-verify oddity: `device:install` runs `npm install` inside `src/remote-device/`, which contains no `package.json` at the audited SHAs — likely vestigial; the successor must classify it before touching PACK-R packaging.

#### Deterministic before/after acceptance matrix

Baseline `B` is the exact frozen SRM SHA before each successor slice; candidate `C` is the slice head. All checks are deterministic; no LLM assertion substitutes for them.

| # | Check | B (before) | C (after, per slice) |
|---|---|---|---|
| A1 | Static import scan of `dist/index.js` module graph for pack root specifiers | ≥1 hit for PACK-R and D2 chains (current truth) | 0 hits for the isolated pack; scan method and hit list recorded |
| A2 | `npm run build` (tsc + shx staging + UI runtime esbuild) | PASS | PASS |
| A3 | Compact facade (`SUNDAY_FULL_TOOLSET` unset): exposed tool set | = allowlist + `sunday_*` (19 + facade) | identical set, order-insensitive compare recorded |
| A4 | Full facade (`SUNDAY_FULL_TOOLSET=1`) with all packs installed | full tool list | byte-equivalent list |
| A5 | Full test run (`node test/run-all-tests.js`) | recorded PASS/fail counts (see #473: 70/78 base replay) | pack-gated skips replace pack-test failures; non-pack results identical to B; skipped set enumerated |
| A6 | `read_file`/`write_file`/`get_file_info` on `.txt`/`.md`/`.py` fixtures | PASS, byte-identical results | byte-identical to B |
| A7 | Same tools on `.pdf`/`.docx`/`.xlsx` without D2 installed | current rich parsing results (recorded) | typed `UNSUPPORTED_FORMAT_PACK` degradation with deterministic text; no silent wrong content; no crash |
| A8 | Same tools on `.pdf`/`.docx`/`.xlsx` with D2 installed | rich parsing results | byte-equivalent to B |
| A9 | `start_search` over mixed tree (txt+md+docx+xlsx) without D2 | content hits in office formats | text hits identical; office-format hits degrade to typed skip/filename-match per defined contract; enumerated diff |
| A10 | `sunday-mcp remote` without PACK-R installed | remote mode starts | typed `PACK_NOT_INSTALLED` error, exit ≠ 0, no partial state |
| A11 | `sunday-mcp remote` with PACK-R installed | current behavior | equivalent to B (4 remote tests PASS) |
| A12 | `ensureChromeAvailable` at init without D2 | Chrome pre-check/download runs | not invoked; no network probe; init log delta recorded |
| A13 | `npm pack` / tarball contents + `files` set | includes `dist` incl. `preview-runtime.js` | unchanged deliverable shape; D1 runtime still shipped prebuilt |
| A14 | `build:mcpb` bundle `dependencies` diff vs B | all 27 roots | exactly the slice's roots removed; ripgrep wrapper/binaries intact; bundle size delta recorded |
| A15 | Lock semantics (#473 style) | — | removed roots absent; unreachable transitives removed; 0 entries added; surviving entries unchanged; root metadata preserved; no version churn |
| A16 | Hygiene | — | `git diff --check` PASS; strict UTF-8/no BOM; no secrets; scope diff = declared paths only |

#### Successor mutation packet conditions

A successor slice may mutate SRM only as a separately claimed `EXECUTION_SUBSTRATE_ONLY` WO that: re-pins actual SRM state; if the execution-substrate HEAD remains `2f033cfb1f61b6dff9c2e55264cca6f2a9125e95`, uses that accepted local-SHA base, otherwise reconciles the drift before mutation; cites this section; and explicitly re-opens the exact source seams it will touch (a package-only ceiling like #473's cannot create seams). One pack slice per WO, cheapest-first order:

1. `D1` editor-preview roots to build-time-only dependency class (dev-style), shipping the prebuilt `preview-runtime.js`. Lowest risk: no Node import chain. Prove A1–A6, A13–A16 plus D1 tests still green in dev/CI where roots remain installed.
2. `PACK-R` remote-device/cloud: lazy `import()` seam at the `remote` argv branch in `src/index.ts`, typed `PACK_NOT_INSTALLED` failure, roots moved to an optional/meta-pack mechanism chosen and justified by that WO (optionalDependencies vs feature manifest consumed by `build-mcpb.cjs`); caffeinate classified with it. Prove A1–A5, A10, A11, A13–A16.
3. `D2` document handlers: lazy factory registration, lazy `tools/pdf` imports in `src/tools/filesystem.ts`, `search-manager` typed fallback, `ensureChromeAvailable` gating, and the A7/A8/A9 degradation contract. Highest coupling; requires the A7–A9 contract to be frozen in that WO's tests RED-first.

Hard fences for every slice: no capability deletion without its typed degradation; no break of `SUNDAY_FULL_TOOLSET=1` with packs present; isolation proof (A1) precedes any root removal; no `npm install/prune/update/audit-fix/publish` lifecycle runs — offline, no-script, no-churn lock rewriting only, proven in claim evidence first; no runtime restart; protected `.serena` state untouched; independent exact-SHA R2 review before acceptance because package/release behavior changes.

## 14. Phase FRONTDOOR-1 — Productized Windows Front Door

Priority: after LOCAL-USABLE-1 unless launch/setup friction blocks actual use.

### Reuse ours

Current A-Wiki already contains:
- desktop UI;
- preferences;
- app shutdown preference;
- instance autostart;
- readiness;
- connector monitoring/recovery;
- setup wizard;
- runtime setup;
- update checks;
- doctor-like tunnel diagnostics.

Therefore DWB's launcher/dashboard implementation is not the base.

### Borrow DWB UX rules

- one obvious app entry point;
- one obvious "ready / not ready" state;
- Start/Stop exposed without editing config;
- persisted safe preferences;
- close/minimize behavior explained;
- read-only Doctor that does not create workers/executions;
- runtime version shown from actual running process;
- update refused or staged safely while active work exists.

### Tray

Add only if:
- current app-close behavior causes real operator friction; and
- implementation does not require a disproportionate dependency/runtime stack.

Tray is polish, not architecture.

## 15. Relationship to active roadmaps

### Zero-Relay

Remains P0 execution-fabric accelerator.

This roadmap does not replace it and does not cancel any active Zero-Relay claim. After WO397 acceptance, GOT-1/FMG-1 enter the dependency queue as product-fast-lane work and may run in parallel only in free, non-overlapping global WIP. They reduce status drift and local mutation risk independently of provider dispatch automation; they do not justify blind lane preemption.

### Hook / STM / Observability

Remain valid.

Current active HOOK-1c / PR #395 is disjoint and should continue through its own gate.

HOOK-2b / Issue #396 retains its own canonical terminal-identity scope.

COCKPIT-1 should consume accepted hook/monitor projection when available; it must not wait for every future hook feature before showing existing durable task/execution truth.

### DEX

DEX exact process/retry/receipt boundaries remain stronger than DWB worker/session recovery.

Use DEX evidence for cockpit and worktree safety.

Do not replace DEX with DWB session persistence.

### Semantic/LSP roadmap

Unaffected.

Semantic tooling remains an execution capability and does not become a blocker for LOCAL-USABLE-1.

## 16. Child Work Order queue

Create only when dependency-ready.

### GOT-1

Title:
`Wire ContinuityProjectionFoldAdapter into production GoalCloseout`

Repo:
A-Wiki.

Files:
existing continuity/closeout assembly + focused tests only.

### WTL-0

Title:
`Read-only worktree lifecycle inventory and cleanup eligibility contract`

Repo:
A-Wiki.

No deletion.

### FMG-1

Title:
`SRM File Mutation Guard v2 — DWB physical identity + stale-write adaptation`

Authority:
A-Wiki.

Implementation:
SRM.

Must include DWB attribution plan.

### COCKPIT-1

Title:
`Runtime Cockpit MVP — durable truth projection in existing desktop UI`

Repo:
A-Wiki.

Read-only operator surface first.

### PAYLOAD-1

Title:
`SRM bounded MCP result/payload guard`

Only READY if evidence says oversized results are a current blocker or after LOCAL-USABLE-1.

### DEPDIET-1

Title:
`SRM compact-core dependency and feature-pack boundary`

No blind package deletion.

### FRONTDOOR-1

Title:
`A-Sunday Windows front-door polish without second UI stack`

Only after launch friction is measured.

## 17. Roadmap integration gate

`PROJECT-PLAN.md` is authoritative long-term roadmap but is currently an overlapping mutable hotspot.

Open draft overlaps observed:
- PR #243 — `PROJECT-PLAN.md` + deferred custom provider-settings roadmap;
- PR #244 — stacked on #243, `PROJECT-PLAN.md` + AEET roadmap.

This WO therefore creates the detailed plan first without violating ownership.

Before PROJECT-PLAN integration:
1. read #243/#244 exact current diffs;
2. identify unique still-valid content;
3. classify each block KEEP / DEFER / SUPERSEDED;
4. preserve unique accepted intent;
5. close/retarget only when evidence supports it;
6. re-pin `origin/main`;
7. create one clean integration branch;
8. add a concise Product Fast Lane pointer, not a second full copy of this document.

## 18. Verification strategy

### Roadmap WO

- scope diff;
- Markdown/UTF-8;
- internal path/link existence;
- no secrets;
- no accidental benchmark binary;
- exact benchmark SHA/license recorded;
- independent SunDay-Worker 5 review;
- hosted CI on frozen candidate when available.

### GOT-1

Targeted projection/closeout tests + exact-SHA independent review.

### FMG-1

Windows-specific hardening tests + concurrency/stale-write adversarial suite + exact-SHA compatibility set + hosted CI.

### COCKPIT-1

Projection/view tests + no-authority regression + UI smoke.

### WTL-2

Dry-run/classifier proof first; consequential cleanup receives R3 review and postcondition verification.

## 19. Metrics

Measure accepted outcomes, not activity.

### LOCAL-USABLE-1

- user can launch the existing A-Sunday app and see truthful current state without opening repository Markdown;
- supported SRM file mutations pass File Mutation Guard v2;
- operator can distinguish running, terminal-unharvested and outcome-unknown work;
- new chat can recover current execution pointers without user copy/paste.

### Generated truth

- manual current-state projection edits per accepted task -> target zero inside machine-owned sections;
- projection drift detected deterministically;
- repeated identical fold -> no unnecessary writes.

### Worktree lifecycle

- every worktree has a classification;
- unknown/dirty/active worktrees are never auto-deleted;
- eligible stale worktrees decrease only through per-path verified cleanup.

### SRM core

- default dependency surface decreases only with green build/tests and preserved compact-tool behavior;
- no feature loss hidden by package removal.

## 20. Explicit non-goals

Not part of the fastest usable-product slice:

- replacing Tk/Ttk with DWB XAML;
- cloning DWB broker/session architecture;
- new cloud backend;
- automatic public remote access;
- tray icon for its own sake;
- broad worktree deletion;
- full legacy dependency purge in one PR;
- moving claims/tasks/review into SRM;
- copying DWB secret handling;
- copying third-party components merely because DWB downloads them;
- waiting for every ODP/semantic/provider roadmap item before using the local product.

## 21. Final product principle

The product should become **simpler at the edge while remaining stronger at the core**.

DWB demonstrates that a user values:
- one entry point;
- clear runtime status;
- safe local file mutation;
- visible queue/worker state;
- predictable restart/update behavior.

A-Sunday already contains stronger durable orchestration and authority machinery.

The convergence therefore is:

```text
A-SUNDAY DURABLE AUTHORITY
        +
SRM DWB-GRADE FILE SAFETY
        +
EXISTING DESKTOP UI AS COCKPIT
        +
GENERATED OPERATIONAL TRUTH
        -
MANUAL STATUS DRIFT
        -
WORKTREE/DEPENDENCY DEBT
        -
DUPLICATE UI/AUTHORITY STACKS
        =
FASTEST SAFE USABLE PRODUCT
```
