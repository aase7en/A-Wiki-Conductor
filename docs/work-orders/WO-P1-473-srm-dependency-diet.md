# WO-P1-473 — DEPDIET-1 SRM compact-core direct dependency audit and first removal slice

Status: COMPLETE / POST_MAIN_VERIFIED / SSOT_FOLDED
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

## Final closeout — 2026-09-22

- Accepted execution candidate: `e3ec2e06baf464e68c4166faae65f51c60fd5477`, direct child of canonical SRM base `2e6aeabd09a321232098187dba4c522e37e4b1de`.
- Canonical `A:\GitHub\SunDayRemoteMCP` `main` was integrated by local `--ff-only` to that exact candidate. SunDayRemoteMCP has no configured Git remote, so no shadow repository or PR was created.
- Exact execution mutation remained `package.json` + `package-lock.json` only.
- Removed direct production roots exactly: `@tiptap/pm`, `remark`, `remark-gfm`, `remark-parse`, `unified`.
- Semantic lock proof: 67 unreachable entries removed, 0 entries added, no surviving package entry/version changes, inherited lock root metadata preserved except the five root dependency keys, and `@tiptap/pm` remains reachable transitively from retained Tiptap packages.
- Deterministic acceptance evidence: UTF-8/no-BOM PASS; `git diff --check` PASS; build PASS; compact facade PASS; full-toolset facade PASS; focused supervisor PASS; atomic-write alternating BASE/CANDIDATE replay 3/3 PASS on each side.
- Full-run differential was explicitly adjudicated rather than silently ignored: exact base replay 70/78 PASS and candidate replay 69/78 PASS, with seven common failures; candidate-only supervisor/atomic-write failures subsequently passed targeted/replay verification and no deterministic failure attributable to the two-manifest commit remained.
- Author run: GLM-5.3 MAX, terminal exit 0, bounded two-file scope, no accepted MCP/security violation.
- Accepted independent R2 review: `runs/WO-P1-473/r2-review/attempt-0005-static-e3ec2e0-v1/`; run `run:WO-P1-473:r2-static-review:a5:f05646ef0027`; exact candidate review PASS; P0/P1/P2/P3 = 0/0/0/3; exit 0; 2,620 process samples; no MCP descendant; no scope violation; review tree clean.
- Earlier review attempts are historical non-authority: attempt-0001 and attempt-0003 were security-invalid; attempt-0002 was provenance-collision-invalid; attempt-0004 was invalidated before dispatch by task/config identity drift.
- GPT-5.6 Sol adjudication: ACCEPT.
- Post-main proof: canonical SRM HEAD is exact accepted SHA; protected `.serena/.gitignore` and `.serena/project.yml` hashes were unchanged; existing live Node processes were not restarted.
- Claim `WO-P1-473-DEPDIET1-WINDOWS-001` is released by this closeout and Issue #473 closure.
- This first removal slice does not close parent Issue #472's broader DEPDIET-1 feature-pack boundary. Unknown or ambiguous dependencies remain retained.
- Issue #457 remains `HUMAN_DECISION_REQUIRED`; this lane does not change that gate.

## Next safe action

Keep parent #472 open. Reconcile the remaining DEPDIET-1 audit/read-only feature-pack boundary against actual SRM state before authorizing another package/source mutation. FRONTDOOR-1 remains gated on measured launch/setup friction; do not manufacture a source lane merely because this slice completed.
