# A-Sunday Conductor — session rollover checkpoint — 2026-09-21 17:55 +07

Purpose: durable session/context rotation only. This checkpoint is a factual snapshot, not project authority. A fresh session MUST recover actual Git/GitHub/runtime/durable state first; newer evidence outranks this file.

## 1. Project / authority binding

- Project: A-Sunday Conductor
- Task topology for this checkpoint: CONTROL_PLANE_ONLY continuity capture
- Authority repo: `A:\GitHub\A-Wiki-Conductor`
- Execution substrate: `A:\GitHub\SunDayRemoteMCP` (not mutated by this checkpoint)
- Parent continuity authority: Issue #215
- Current authoritative remote main at checkpoint:
  `a37746f67631c9ed8edd23fa20b80b8ef4d3dfd9`
- That main is merge PR #463 / WO-P1-461 GraphStore v2 run-authority.
- Checkpoint branch:
  `checkpoint/session-rollover-20260921-1755`
- Checkpoint worktree:
  `A:\GitHub\_worktrees\A-Wiki-Conductor-rollover-20260921-1755`
- Checkpoint file:
  `docs/checkpoints/2026-09-21-session-rollover-a-conductor-1755.md`

The earlier rollover PR #462 / SHA `e272f3d5...` is HISTORICAL and stale relative to the state below. Do not resume from it without reconciling this newer checkpoint and live state.

## 2. Protected root checkout

Do NOT mutate/reset/clean/stash/switch the root checkout merely to make it match remote main.

Observed root checkout:

- root: `A:\GitHub\A-Wiki-Conductor`
- local branch: `main`
- local HEAD: `1a5ea1b8574f783c002589ffe3fb51b30303e24c`
- remote `origin/main`: `a37746f67631c9ed8edd23fa20b80b8ef4d3dfd9`
- untracked/protected entries were observed, including:
  - `$null`
  - `0`
  - `docs/prompts/GLM-WO230-ZRA2-REVIEW-TASK-CONTRACT-AUTHORITY.md`

Use isolated worktrees. Root dirt/staleness is protected unknown work, not cleanup permission.

## 3. Global live execution / WIP snapshot

At the final recovery pulse:

- matching live Kilo/GLM/reviewer process count for WO453/458/459/461: **0**
- independent review slot: **FREE (0 live reviewer process observed)**
- default mutable WIP should be treated as **3/3 occupied** until claims are explicitly released:
  1. WO461 post-main repair
  2. WO458 frozen provider-selection candidate
  3. WO453 Mac-owned FMG-PROD design
- WO459 claim is RELEASED / PAUSED and does NOT consume a mutable slot.

Do not infer claim release from a terminal model process alone.

## 4. WO461 / Issue #461 — FIRST PRIORITY

Typed state:

`MERGED_WITH_POSTMAIN_DEFECT / REPAIR_REQUIRED`

Historical accepted/merged path:

- PR #463 merged
- reviewed candidate: `ae01abb73fc128acd9cdb27d272f7a95b79c0695`
- merge/current main: `a37746f67631c9ed8edd23fa20b80b8ef4d3dfd9`

Why repair is still required:

- cross-session Sol adjudication conflicted after merge;
- deterministic finding: schema DDL normalization lowercased quoted string literals, so CHECK literal case drift such as `'serena'` -> `'SERENA'` could be classified as canonical v2;
- no rollback/reset/revert/history rewrite is authorized;
- repair proceeds FORWARD from current main.

Active repair binding:

- issue: #461 OPEN
- claim remains: `WO-P1-461-GRAPHSTORE-V2-RUN-AUTHORITY-001`
- worktree:
  `A:\GitHub\_worktrees\A-Wiki-Conductor-wo461-postmain-schema-repair`
- branch:
  `fix/wo-p1-461-schema-literal-case-postmain`
- HEAD/base:
  `a37746f67631c9ed8edd23fa20b80b8ef4d3dfd9`
- no remote repair branch existed at final check
- tracked working-tree mutations currently exist:
  - `src/a_conductor/graph/store.py`
  - `tests/test_graph_run_authority.py`
- no bound executor was live at checkpoint.

Replay safety:

- classify existing repair work as PARTIAL_MUTATION / owner-preserved;
- DO NOT reset/clean/stash/restart from scratch;
- inspect the exact current diff before any edit;
- continue only inside existing #461 repair scope;
- RED/fix/test -> update WO repair evidence -> freeze SHA -> exact-head CI -> fresh independent GLM-5.3 MAX exact-SHA review -> Sol adjudication -> expected-head repair merge -> post-main verification -> explicit claim release.

This lane is the shortest path to stabilizing main and freeing one WIP slot.

## 5. WO458 / Issue #458 / PR #464 — FROZEN, BASE STALE

Current remote candidate:

- Issue #458 OPEN
- PR #464 OPEN / DRAFT / mergeable at final check
- branch: `feat/wo-p1-458-provider-fallback-policy`
- frozen remote/local candidate:
  `f14c657c6d760e0b72a003d5591e06d1cbb4652e`
- historical base:
  `eb9305957d4bfc71b1e53bca1206b84c9ee1105b`
- local worktree:
  `A:\GitHub\_worktrees\A-Wiki-Conductor-wo458-provider-fallback`
- local tree was clean and synchronized with the remote branch at final reconciliation.

Exact 3-file scope:

- `src/a_conductor/provider_fallback_policy.py`
- `tests/test_provider_fallback_policy.py`
- `docs/work-orders/WO-P1-458-provider-fallback-policy.md`

Frozen evidence already recorded:

- focused: 48 PASS
- focused + related provider + WO identity: 202 PASS
- py_compile: PASS
- diff-check: PASS

Historical author attempts are terminal/superseded. In particular attempt-0004 failed closed before child spawn due HEAD drift and MUST NOT be replayed.

Important current-main drift:

- current main is now `a37746f...` because WO461 PR #463 merged;
- WO458 scope is disjoint from WO461 paths, but the PR base is stale;
- DO NOT run final exact-SHA acceptance review against the stale base as if current-main binding were satisfied;
- preferred sequence: finish/release WO461 repair first, then re-pin #458 to then-current main, prove overlap/merge-tree, merge-forward normally if authorized/disjoint, freeze a new candidate SHA, rerun affected deterministic gates + exact-head CI, then one independent GLM-5.3 MAX review.

No new author mutation is needed unless fan-in or review finds a real issue.

## 6. WO453 / Issue #453 / PR #456 — MAC-OWNED, STALE BASE

Ownership:

- Mac-owned design lane
- Windows MUST NOT mutate the WO453 design document/branch or canonical SunDayRemoteMCP runtime under this checkpoint.

Remote state:

- Issue #453 OPEN
- PR #456 OPEN / DRAFT / mergeable at final check
- current remote head:
  `ce5d6a0278d4fcddfba3c4feaf9715b7f07062e4`
- PR base:
  `eb9305957d4bfc71b1e53bca1206b84c9ee1105b`
- scope remains exactly:
  `docs/work-orders/WO-P1-453-fmg-prod-canonical-srm-cutover.md`

Flash pre-review was harvested and is advisory only. Its P1 was rejected as an ignored-vs-visible-untracked category error; P3 notes remain advisory. Required independent GLM-5.3 MAX R3 review has not yet been accepted for the new current-main state.

Because current main advanced to `a37746f...` and WO461 repair may move main again:

- do not final-review/merge the stale-base WO453 candidate now;
- Mac owner should re-pin/fan-in after main stabilizes;
- then freeze new exact head, run exact-head CI and one qualified MAX R3 review;
- PR #456 remains DESIGN ONLY.

Still binding:

`SAFE_TO_MUTATE_SRM_CANONICAL_MAIN=NO`

`SAFE_TO_RESTART_SRM_RUNTIME=NO`

## 7. WO459 / Issue #459 — RELEASED / PAUSED

Current claim state:

`RELEASED / PAUSED`

Binding retained only for recovery:

- worktree:
  `A:\GitHub\_worktrees\A-Wiki-Conductor-wo459-awiki-secret-writer`
- branch:
  `feat/wo-p1-459-awiki-secret-writer`
- retained historical head/base:
  `eb9305957d4bfc71b1e53bca1206b84c9ee1105b`
- no remote branch at the release pulse
- no accepted tracked source/test/doc mutation from the author attempts.

Read-only GLM-5.3 MAX prep was harvested. Useful prep:
- reuse existing `awiki_environment_resolver` authority;
- explicit authorized-root writer API;
- RED matrix for validation, containment, atomic replace/read-back, non-disclosure, no subprocess/network and fixture confinement;
- round-trip warning for quote-looking/padded values;
- same-directory temp + fsync + os.replace + verification.

An ignored/untracked `.kilo/plans/...` advisory artifact was observed from prep. It is not authority and must not be blindly cleaned.

Do NOT resume mutation until:
1. a mutable WIP slot is legitimately free;
2. live main is re-pinned;
3. a fresh claim/worktree/base/non-overlap pulse is recorded.

## 8. WO457 / Issue #457 — HUMAN DECISION GATE

Status:

`HUMAN_DECISION_REQUIRED / SOURCE_HOLD`

No Browser Wake extension repository has been authorized/created.

Advisory preference from shaping:
- preferred: dedicated PRIVATE repo `aase7en/sunday-family-extension`
- fallback: bounded `extension/` subtree in A-Wiki-Conductor
- Native Messaging host advisory preference: Python 3.11 stdlib-only
- MV3 side: TypeScript

These are recommendations only, not authorization.

Do NOT create the repo or mutate BWA-1A source until the user explicitly chooses:
1. dedicated private repo vs A-Wiki `extension/` subtree;
2. Native Messaging host language if the project requires explicit selection.

Issue #215 still owns automatic NEXT_READY/successor authority. BWA-1A remains transport only.

## 9. Kilo / GLM security — Issue #342

Security incident is durable under Issue #342.

Critical rule:

**`kilo run --pure` alone is NOT sufficient evidence that external MCP subprocesses are disabled.**

Accepted mitigation probe:

- derive configured MCP NAMES ONLY; do not persist command/env/header/token values;
- provide `KILO_CONFIG_CONTENT` overlay with every configured MCP entry `enabled=false`;
- set `KILO_PURE=1`;
- run a harmless model probe;
- live-sample the exact delegated descendant tree;
- classify MCP-specific process/package signatures only;
- do not treat bare words such as `github` as an MCP signature because normal `git.exe` caused a false positive;
- if a genuine MCP-specific descendant appears, terminate only the exact bound delegated process tree and classify the run interrupted/security-invalid.

The successful isolation probe sampled the process tree 137 times and observed zero MCP-specific descendants.

Never persist raw secret-bearing process command lines, Kilo MCP config/status dumps, environment values, session/share URLs, tokens or headers.

Do not rotate/delete credentials automatically. Credential rotation remains explicit operator-approved work.

## 10. Review / GLM routing after rollover

At checkpoint no live reviewer was observed.

For every material GLM dispatch:

1. recover any outstanding run first;
2. refresh CoinTH quota via the approved secret-safe resolver;
3. exact model admission/roll-call;
4. use MCP-disable overlay + `KILO_PURE=1`;
5. live descendant census with refined MCP-specific signatures;
6. one mutable owner per hotspot;
7. one independent read-only review slot globally;
8. Worker/GLM DONE is a claim only; deterministic exact-SHA evidence wins.

Do not silently substitute another provider/model if CoinTH/GLM is unavailable.

## 11. Immediate continuation order in the next chat

RECOVER ACTUAL STATE FIRST. This order is the intended next path only if live evidence still matches.

### A. Finish WO461 post-main repair first

- recover #461 issue/comments, repair worktree, exact current diff and process liveness;
- no redispatch if an executor has appeared;
- preserve current partial mutation;
- RED -> repair -> deterministic graph/run-authority tests;
- freeze candidate on current main;
- exact-head CI;
- fresh independent GLM-5.3 MAX review;
- expected-head repair merge;
- post-main verification;
- release #461 claim.

### B. Re-pin WO458 after main stabilizes

- verify #458 PR #464 remote/local state;
- compare then-current main to historical base and prove disjointness;
- normal merge-forward only if authorized and conflict-free;
- freeze new exact SHA;
- rerun affected tests/CI;
- one independent MAX review;
- Sol acceptance/merge/post-main;
- release #458 claim.

### C. Let Mac owner re-pin WO453

- do not mutate from Windows;
- current main may have moved again after #461 repair;
- Mac owner performs its own merge-forward/freeze/CI/MAX review.
- canonical SunDayRemoteMCP mutation remains forbidden until WO453 design acceptance + fresh Windows CROSS_REPO claim.

### D. Re-claim WO459 only after a slot is free

- start from actual current main, not stale `eb930595...`;
- fresh claim and isolated worktree/branch binding;
- use harvested RED plan only as advisory;
- author with hardened GLM harness and exact scope.

### E. WO457 waits for human product decision

Do not create extension repo/source until the placement/visibility decision is explicit.

## 12. Session rollover instruction

A new ChatGPT session MUST NOT restart these tasks.

Use:

`RECOVER -> RECONCILE -> HARVEST -> CONTINUE`

not:

`NEW CHAT -> NEW TASK -> REDISPATCH`

The durable Issues, PRs, worktrees, SHAs and evidence above are the handoff surface. Actual newer Git/GitHub/runtime state outranks this checkpoint.
