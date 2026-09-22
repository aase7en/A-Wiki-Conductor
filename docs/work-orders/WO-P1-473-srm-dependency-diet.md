# WO-P1-473 — DEPDIET-1 SRM compact-core direct dependency audit and first removal slice

Status: GOVERNANCE_BOOTSTRAP / EXECUTION_SOURCE_HOLD
Issue: #473
Identity schema: GITHUB_ISSUE_V1
Parent roadmap: #397 / DWB convergence / DEPDIET-1
Accepted predecessor: #453 / LOCAL-USABLE-1 file-safety completion
Topology: EXECUTION_SUBSTRATE_ONLY under A-Wiki authority
Risk: R2 — package graph, build, test and release behavior
Integrator: GPT-5.6 Sol

## Lane binding

Authority repo: `aase7en/A-Wiki-Conductor`
Authority base: `5bec993c525fef104a2890e7656ed1b3331bde32`
Authority worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo473-depdiet1`
Authority branch: `docs/wo-p1-473-depdiet1`
Authority mutable bootstrap scope: this Work Order only.

Execution repo: `A:\GitHub\SunDayRemoteMCP`
Accepted canonical execution base: `2e6aeabd09a321232098187dba4c522e37e4b1de`
Canonical branch: `main`
Configured Git remotes at bootstrap: none.
Protected local execution state: visible untracked `.serena/.gitignore` + `.serena/project.yml`; this lane must not clean, stage or mutate them.

Claim: `WO-P1-473-DEPDIET1-WINDOWS-001`

`SAFE_TO_MUTATE_SRM_PACKAGE_GRAPH=NO` until the audit/re-pin gate below is complete.

## Goal

Make the default local SunDayRemoteMCP install reflect the compact product rather than the full inherited Desktop Commander dependency surface, without deleting capability by intuition and without creating a second product or package authority.

This Work Order implements the accepted roadmap sequence after:
- LOCAL-USABLE-1 file-safety became operationally satisfied through #453;
- PAYLOAD-1 was explicitly assessed as `PAYLOAD_NOT_NEEDED_NOW` and deferred until a concrete reopen trigger occurs.

## Authority and product fences

A-Wiki owns this Work Order, claim/WIP/review/acceptance truth and roadmap progression.

SunDayRemoteMCP owns package/build/runtime implementation. This lane may change only the accepted package graph after an exact audit proves a dependency unnecessary.

This lane MUST NOT:
- delete or edit production TypeScript source merely to justify a dependency removal;
- remove a capability solely because it is outside `src/sunday`;
- add a replacement package;
- update package versions unrelated to the accepted removal set;
- run package publication, release, setup, registry, native-host or global-install actions;
- mutate canonical runtime/process state;
- mutate `.serena`, credentials, provider state, external data or network accounts;
- create scheduler/task/job/claim/retry/review/completion authority;
- reopen PAYLOAD-1 without one of its accepted concrete triggers.

## Required direct-dependency audit

Every direct dependency in `package.json` must be classified against actual exact-base evidence for:
1. static imports/references;
2. dynamic imports;
3. build-script use;
4. test-only use;
5. optional/full-toolset use;
6. postinstall/release use;
7. transitive requirement;
8. package/binary impact;
9. default compact-core capability impact;
10. retain/remove/defer disposition with source evidence.

The audit is repository-wide and must include `src/`, `test/`, `scripts/`, setup/uninstall files, build scripts, UI runtime generation, release/MCPB tooling and package metadata. Literal absence in `src/sunday` is insufficient.

## First investigation candidates

The accepted roadmap names these only as candidates:
- `@tiptap/pm`;
- `remark`;
- `remark-gfm`;
- `remark-parse`;
- `unified`.

No candidate is authorized for removal merely by appearing in this list.

## Compact-core retention priority

Default compact core must preserve:
- MCP protocol;
- filesystem/read/edit;
- process/shell;
- search;
- workspace;
- repository snapshot;
- background execution;
- durable evidence;
- file mutation guard;
- semantic core.

Optional/later feature-pack candidates may include rich preview/editor, rich document/PDF conversion, remote-device/cloud, telemetry/analytics and legacy publishing extras only after dependency-to-capability ownership is proven.

## Source release gate

Before any package mutation:
1. re-pin actual canonical SRM branch/HEAD/dirty/untracked/ignored state and process census;
2. prove no overlapping active SRM package/build/release claim;
3. produce the complete direct-dependency audit table as durable ignored run evidence;
4. for each proposed removal, prove zero direct/dynamic/build/test/full-tool/postinstall/release requirement OR prove that any remaining references are unreachable optional tooling explicitly outside the default product and preserved through a separate dependency;
5. identify lockfile direct-root entries and transitive packages that would become unreachable;
6. prove the removal can be represented without unrelated version churn;
7. freeze an exact removal set and exact mutable paths.

If any candidate remains required or ambiguous, retain it. Unknown is not removable.

## First mutation ceiling

After the source release gate, the first removal cycle may mutate at most:
- `package.json`;
- `package-lock.json`.

No production/test/tooling source path is implicitly authorized.

No `npm install`, `npm update`, `npm audit fix`, `npm prune`, package publication or lifecycle script may be run merely to rewrite the lockfile. Any package-manager operation requires a separately proven offline/no-script/no-version-churn method in the claim evidence first.

## Verification floor

A frozen removal candidate must prove:
- package JSON/lockfile structural consistency;
- removed direct roots are absent and retained roots unchanged except lockfile reachability effects;
- no unrelated package version churn;
- `npm run build` against the existing dependency environment;
- existing full deterministic test runner or a justified superset of all affected build/package/tool tests;
- compact and full-toolset MCP facade smoke where relevant;
- packaging/release scripts parse and retain their required imports;
- diff-check and strict UTF-8/no BOM for changed manifests;
- protected local state preserved;
- exact candidate SHA frozen before review.

Independent review: GLM-5.3 MAX exact-SHA review is required because package/release behavior is R2. Acceptance requires P0/P1/P2=0 plus GPT-5.6 Sol adjudication.

## Current state

At bootstrap:
- A-Wiki authority main is `5bec993c...`;
- canonical SRM is `main@2e6aeabd...`;
- `package.json` and `package-lock.json` are the same accepted manifests carried through the #453 cutover;
- the accepted roadmap's initial literal scan found zero TypeScript references in `src/` for the five investigation candidates, but this is not sufficient for removal;
- no DEPDIET-1 Issue existed before #473;
- no execution-source mutation has been authorized or performed by this Work Order.

## Next safe action

Freeze/push this governance bootstrap, then run an exact-base repository-wide direct-dependency audit. Only if that audit produces a bounded, non-ambiguous removal set may a fresh source-release pulse authorize the two package manifest paths.
