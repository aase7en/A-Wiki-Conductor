# WO-P1-686: DEPDIET-2A Opt-In Headless-UI Build Artifact

Identity schema: GITHUB_ISSUE_V1
Issue: #686
Date: 2026-10-20
Status: DRAFT_BOOTSTRAP / EXPERIMENT_NOT_ADMITTED / RELEASE_BLOCKED
Risk: R0 docs-only bootstrap; intended R2 offline experiment, subject to admission and escalation below.
Topology: EXECUTION_SUBSTRATE_ONLY implementation; CROSS_REPO authority/compatibility binding (AWC authority, SRM execution).

## 1. Authority, Identity and Pins

Parent authority: AWC issue #472, audit comment c5798905431, independently fetched during bootstrap: NO_DIRECT_DELETE_CANDIDATE. Compact-hidden is not removable; the successor must prove a separately bounded compile/package/test/release boundary, not delete root dependencies.

Design input, read fully: `A:\GitHub\_worktrees\AWC-wo683-config-root\runs\WO-P1-472\build-boundary-20261019\result.md` (137 lines). Adopt Option A only, not Option B packs. It remains OPTIONAL AFTER PILOT absent a measured blocker; this packet does not assert one.

GitHub `gh api` verified the following main heads on 2026-10-20:

| Role | Repository | Exact main SHA |
| --- | --- | --- |
| Authority | aase7en/A-Wiki-Conductor | 7cb757d79f97bb0442565c93575e23d47039c806 |
| Execution | aase7en/SunDayRemoteMCP | 1e95b013144a7980a26337a4e8e3a80c08ea37ab |

The design packet used SRM `241160bb93945302b12a6497e5aebe0c85eb895d`, NOT current SRM main. Before implementation, re-verify every source/test/build path and re-pin the compatibility set at the NEW SRM main above, with a focused delta review of `sunday-config-root`, agent-entry, installer and doctor changes versus the packet's assumptions (config-root unification #683 merged). Do not reuse old config assumptions or modify these surfaces. Any later member-head drift invalidates the set until re-pin/focused review.

Driving title: `DEPDIET-2A: opt-in headless-ui build artifact (offline experiment)`. At bootstrap, title search returned no issue. The identity line above is the explicitly requested placeholder for root binding, NOT proof of a live driving issue. Number 685 already identifies the merged lesson-fold PR; root must resolve the GitHub identity collision and correct/bind the packet before implementation admission. The offline identity suite does not validate GitHub issue existence/type. No lane may execute on a fabricated issue binding.

Bootstrap tuple: AWC -> `A:\GitHub\_worktrees\AWC-wo685-depdiet` -> `docs/wo685-depdiet-headless` -> `7cb757d79f97bb0442565c93575e23d47039c806` -> explicit one-file author assignment -> this WO only. Initial worktree clean. Owner: bootstrap author session `ses_ea92574fbffe6uOkuQA8ylBTn0`; integrator/root owns issue binding, review, commit/push and subsequent admission. No SRM worktree/claim is acquired by this bootstrap. Shared continuity docs remain reserved to PR550; no edits to CURRENT-WORK.md, handoff.md, COLLAB.md or other files.

## 2. Goal and Compatibility Contract

Produce one explicit, opt-in HEADLESS-UI distribution in isolated `artifacts/headless-ui/`, WITHOUT the file-preview/config-editor browser widgets or their heavy editor dependency closure. Never overwrite ordinary `dist` or replace the full package. Preserve the default full output byte-compatible under the same pinned toolchain, inputs and platform; preserve all current full-package capabilities, scripts, bin, metadata and dependency/version graph.

The alternate artifact retains text/image/PDF/Excel/DOCX operations, compact facade and full toolset, remote-device compatibility and backend shared preview types. No tool capability is removed. `SUNDAY_FULL_TOOLSET` remains exposure policy, not feature installation or authorization. PDF imports/Chrome prewarm and Supabase/backend graphs remain; this is not a startup/lazy-loading optimization. Backend configuration tools keep normal semantics; only their browser widgets are omitted.

One immutable build descriptor identifies `profile=headless-ui`, `features.ui=false`; normal full source defaults to `ui=true`. This is not live config, a permission, enrollment state, plugin registry or request-triggered installation. Headless tool advertisements omit widget metadata even when `showMcpUiPreviews=true`; resources/list omits both widgets. Known widget reads return typed `FEATURE_NOT_INCLUDED` with `feature=ui`, `profile=headless-ui` through the existing MCP error envelope, before file access; unknown URI behavior remains unknown-resource, not feature-absence. Ordinary non-widget tool results are unchanged. Identify the profile through initialization instructions or an existing read-only status surface, not a new tool/authority.

## 3. Prospective SRM Allowlist (Not Mutation Authority)

Revalidate at the admitted SRM pin. Any extra path requires checkpoint/re-scope BEFORE mutation.

| Path | Bounded intended change |
| --- | --- |
| `package.json` | Add `build:headless-ui` and `test:build-boundary` scripts only; no default script/dependency/version/name changes. |
| `scripts/build-headless-ui.cjs` (new) | Isolated source/staging projection, explicit asset inventory, immutable descriptor, manifest/import/closure assertions. Reject root/dist aliases, traversal and foreign pre-existing output; no implicit install, lifecycle children, publish or deletion outside proven owned temporary output. |
| `tsconfig.headless-ui.json` (new) | Extend compile options with isolated staging rootDir/outDir; exclude browser source roots, retain shared contracts; verify no transitive re-entry or browser declarations. Exclude alone is not proof. |
| `src/build-profile.ts` (new) | One statically imported full default descriptor; stage headless literal in experimental tree, not tracked-source rewrites during build. |
| `src/ui/contracts.ts` | Suppress widget metadata for headless, preserve full metadata. |
| `src/ui/resources.ts` | Profile-aware listing/reads and typed known-widget absence; preserve full HTML inlining bytes/semantics. |
| `src/server.ts` | Narrow resource error translation/profile instructions only; preserve all tool definitions/dispatch and remote metadata. |
| `test/test-build-boundary.js` (new) | RED-first profile, isolated output, manifest, transitive import/declaration, absence/error and full-baseline assertions. |

`scripts/build-ui-runtime.cjs` requires NO change in the first candidate: headless orchestrator does not invoke it; full continues building both targets. Root lockfile changes are not admitted speculatively. If genuinely required, stop/re-scope rather than silently churn it.

Generate a separate `private=true` staged manifest with no `publishConfig`, projecting the pinned root dependency versions exactly and subtracting ONLY browser-only `@tiptap/*`, `tiptap-markdown`, `markdown-it`, `highlight.js` AFTER emitted JS/declarations and resolved transitive closure prove no remaining use. If those packages remain transitively reachable, record failure/stop; do not claim absence from a direct-manifest subtraction. Keep SDK, media, remote, ripgrep and all staged-entrypoint assets/scripts and notices. Record source SHA, profile hash, manifest digest and sorted inventory. No new dependencies, peers or independent ranges.

Forbidden: default dependency deletion/version changes; `src/index.ts`, tool policy/registry, handler/factory/PDF/remote behavior changes; config-root/agent-entry/installer/doctor edits; real HOME/config/credentials; runtime activation, onboarding, enrollment, network/provider calls, Chrome downloads; AWC product changes; release scripts/manifests/workflows; package identity fixes, publish/release/tag/cleanup. Existing identity/version drift in package/server/manifest remains a SEPARATE publication blocker, not work in this lane.

## 4. Failure Model and RED-First Acceptance

| Failure / RED probe | Required GREEN evidence |
| --- | --- |
| Existing all-src compiler graph with browser packages denied | Headless compile succeeds with exit 0, browser roots/runtime/declarations absent, shared backend types present; deny-resolver trace catches transitive re-entry. Emitted JS after nonzero tsc is FAILURE. |
| Existing build has no isolated profile/output | Dist and candidate cannot overwrite one another; stale widget contamination refused; repeat identical-input builds yield deterministic inventories. |
| Missing-widget route advertises a nonexistent template or leaks ENOENT | Headless listTools metadata and resources/list coherent; both known URIs return typed absence before fs; unknown URI retains ordinary error; full widgets inline with no relative external assets. |
| Direct-only removal masks transitive browser dependencies | Headless JS/declaration and resolved production dependency closure contain no omitted browser editor/highlighter packages; no undeclared peers or imports. No install is implied to prove this. |
| Reduced build accidentally becomes full/default | Default package/bin/scripts/dependency graph, setup/onboarding/remote assets, notices and compiled/bundled output inventory/bytes match pinned full baseline on same toolchain/platform. Full MCPB inventory is statically checked, NOT built via networked helper. |
| UI absence accidentally removes tools/media/remote capabilities | Both profile outputs retain compact/full tool names, schemas, stable descriptions, dispatch/denials and sunday_* facade; all media/document/image/cancellation and synthetic remote tests remain compatible. Existing passing tests are guards, not invented RED failures. |
| Cleanup/lifecycle/network escape or real state reads | Owned temporary/staging containment proven; network, child side effects and real HOME/runtime denied; reject attempts rather than let hooks/native download proceed. |
| Live profile switch or altered config-root resolution | Immutable build descriptor only; focused new-main config delta reviewed; no config preference, migration, foreign-state adoption or installer/doctor change. |

Full acceptance also requires existing full UI regressions, not skipping/weaking them because headless omits assets. Any default-package behavior/byte/dependency graph change is STOP, not a tradeoff to accept silently. Unavailable fixtures or baseline failures must be explicit, reproducible and integrator-adjudicated; no parity claim with unrun tests.

## 5. Admission and Verification Commands

These are FUTURE commands/contracts, NOT executed in docs bootstrap. Root first resolves issue identity, claims a clean SRM-only execution lane at the verified pin and reruns entry/ownership/risk gates. Reuse/EXTEND the packet's existing UI/build seams; no new coordination primitive.

Gate 1: verify known local Node/npm/tsc/esbuild versions and dependency provenance WITHOUT install. Capture source pin and RED assertions before implementation. Missing/unknown toolchain or node_modules provenance => `BUILD_ENV_UNAVAILABLE`, not permission to install. Review exact scripts/test fixtures and sandbox wrappers first; no blind npm lifecycle execution.

Gate 2: separately admit offline compiler/esbuild executions, writes confined to isolated full-baseline/full-candidate/headless outputs. Snapshot baseline ordinary dist before candidate changes; compare same source/toolchain/platform/lockfile. Existing full build command after script/side-effect review is `npm run build`; new explicit candidate command is `npm run build:headless-ui` (maps to `node scripts/build-headless-ui.cjs`). Never run both against a shared output. Fail immediately on any nonzero build exit. Full script default remains unchanged; sandbox isolation belongs to the harness/worktree, not default script rewrites.

Gate 3: `npm run test:build-boundary` maps to `node test/test-build-boundary.js`; run profile assertions against both isolated outputs. Existing suites below need staged/synthetic harness binding rather than assuming a nonexistent profile CLI flag:

```text
node test/test-sunday-tool-policy.js
node test/test-sunday-mcp-tools.js
node test/test-pdf-parsing.js
node test/test-pdf-creation.js
node test/test-pdf-chrome-cache.js
node test/test-markdown-preview.js
node test/test-file-preview-directory-runtime.js
node test/test-file-preview-image-runtime.js
node test/test-remote-channel-reconnect.js
node test/test-remote-channel-signed-out.js
node test/test-remote-inflight-call-fast-fail.js
node test/test-remote-transport.js
node test/run-all-tests.js
```

Re-verify filenames/fixture requirements at the NEW SRM pin. Run media/remote/facade coverage on both profiles, full UI runtime regressions on full; include read_file/read_multiple_files, PDF pages/images/write_pdf, DOCX/Excel, ordinary image base64 and cancellation fixtures. Use fake transport/auth, synthetic credentials and pre-provisioned local/synthetic browser engines only; prevent automatic Chrome downloads. Pin remote command entrypoint, child env/stdio and `_meta.remote/client`. Full-package regression is mandatory after targeted tests, with sandboxed HOME/USERPROFILE and denied network/real state. `npm test` includes a rebuild; prefer admitted direct runner after controlled builds rather than accidentally rerunning lifecycle work. No build or suite result is preclaimed here.

Gate 4 (separate explicit admission after compile/runtime GREEN): verify exact installed npm CLI details offline, then local `npm pack --ignore-scripts --json` ONLY in staged private tree, network denied. Inspect archive entries, imports, declarations, bin/postinstall/assets/notices. An install/native platform matrix needs another explicit sandbox/lifecycle admission; neither pack nor install is authorized by this bootstrap. Never use `build:mcpb`, `release:dry`, `release:rehearsal`, `release:alpha` or publication helpers as offline probes: they can download/install/publish/push tags. Release behavior proof here is preserved static default contract plus fail-closed non-publication; actual release verification remains blocked and separate.

## 6. Measurements, Rollback and Stop Gates

No invented MB, percentages, token, startup, install, RSS or elapsed savings. Deterministic sorted file/emitted-source/declared-dependency counts and hashes are allowed once computed; counts are not performance savings. Measure archive bytes ONLY after admitted pack; installed/transitive size ONLY after admitted controlled install; elapsed/RSS ONLY with explicit instrumentation, same toolchain/platform/lockfile and cold/warm conditions stated. Root development install/build is not made lighter. Accept maintenance of a second artifact only if measured benefit justifies it; otherwise park after pilot, not another manifest deletion audit.

Rollback: do not ship/use the optional artifact; select unchanged full artifact/entrypoint. No live activation occurs, so no config migration, cache deletion, credential conversion, pack installation or source revert is needed to recover settings. Candidate output cleanup, if ever needed, is separately bounded to proven owned output; no worktree/foreign-state deletion here.

STOP on default behavior/bytes/capability/dependency/version changes; unresolved issue identity/ownership; main drift without review/re-pin; unknown local dependency provenance; extra source path; browser dependency transitive residue; mismatched name/version/manifest or missing required asset; lifecycle/network/download/publish attempt; access to real config/credentials/runtime. Escalate/re-scope to R3 BEFORE any release/installer/trust/protocol-authority change: intended R2 experiment does not downgrade the packet's R3 framing requirement for eventual packaging/release or broaden absence semantics beyond this offline UI boundary.

## 7. Routing, Evidence and Bootstrap Closeout

Current work is one R0 docs-bootstrap author lane only, native deterministic checks; no product/source authority. Future implementation routing follows CAPABILITY_MATRIX/FAST_EXECUTION: GLM preferred only if ready/admitted. If approved env-bound `COINTH_GLM_AUTH_TOKEN` remains absent, `GLM_OFFLOAD=BLOCKED:SECRET_SOURCE_UNAVAILABLE`, quota UNKNOWN (not exhausted); no disk/keychain/env-file search or provider call. Eligible GPT fallback may author the separately admitted R2 lane; independent exact-SHA review remains a DIFFERENT lane/session, never author self-approval. Root retains final admission/acceptance/merge authority. No executor is dispatched by this packet.

Future evidence: `runs/WO-P1-686/` in the claimed execution worktree, folded/pointer-bound to this authority WO by root, with exact repo/worktree/branch/SHA/tool versions/profile/manifest/inventory hashes, commands/exits, RED/GREEN and unrun/baseline limits. CROSS_REPO evidence and compatibility acceptance fold to AWC; WIP counted globally, one mutation owner per hotspot. Shared continuity reservation unchanged.

Bootstrap verification contract: sole new file exactly this path; `git diff --check`; added-file whitespace check (untracked files are not covered by ordinary diff); strict UTF-8/no replacement characters; exactly one issue identity matching filename; identity corpus includes this untracked WO. Run from this clean docs worktree:

```text
python -B -m pytest tests/test_work_order_identity.py -q -p no:cacheprovider --basetemp C:\Users\aase7en\AppData\Local\Temp\kilo\wo685-identity-20261020-bootstrap
```

Use a fresh absent basetemp (do not reuse/delete unrelated temp paths). Expected baseline is 33 tests, but report actual output, not expectation. No commit/push, SRM code/build/install/test, shared-doc edit or issue/claim post by bootstrap author. Root reviews draft/checks, resolves/binds issue, commits/pushes and separately admits implementation. Until those gates pass: `SAFE_TO_MUTATE_SRM=NO`.
