# WO-P1-453 — FMG-PROD canonical SRM cutover for LOCAL-USABLE-1

Status: DESIGN_ONLY / SOURCE_AND_RUNTIME_MUTATION_HOLD
Issue: #453
Identity schema: GITHUB_ISSUE_V1
Parent roadmap: #397 / DWB Convergence / LOCAL-USABLE-1
Accepted predecessor: #413 / FMG-1
Topology: CROSS_REPO
Risk: R3 — canonical execution-substrate fast-forward, generated build, and runtime cutover
Integrator: GPT-5.6 Sol

## Lane binding

Authority repo: `aase7en/A-Wiki-Conductor`
Authority design base/current-main fan-in: `eb9305957d4bfc71b1e53bca1206b84c9ee1105b`
Design worktree: `/Users/aase7en/Desktop/_worktrees/A-Wiki-Conductor-wo453-fmg-prod-design`
Design branch: `docs/wo-p1-453-fmg-prod-cutover-design`
Design mutable scope: this Work Order only.

Execution repo: `A:\GitHub\SunDayRemoteMCP`
Observed canonical execution main: `ac01b37ba2e4b9d0249addf7694c0b91deb352c7`
Accepted FMG execution candidate: `2e6aeabd09a321232098187dba4c522e37e4b1de`
Mac SRM clone `/Users/aase7en/GitHub/SunDayRemoteMCP@1fca9d24...` is stale and is not mutation authority.

`SAFE_TO_MUTATE_SRM_CANONICAL_MAIN=NO`
`SAFE_TO_RESTART_SRM_RUNTIME=NO`
## Product gate being repaired

DWB LOCAL-USABLE-1 requires the local SRM execution path to prevent silent overwrite through Windows aliasing and stale-read races on supported file tools. FMG-1 accepted that behavior only as a local exact SRM candidate; acceptance did not publish or bind it into canonical SRM main.

Fresh evidence shows Windows canonical SRM is still `main@ac01b37...`. That tree predates the accepted FMG lineage and does not contain the FMG source/test paths. Therefore #413 COMPLETE alone is insufficient to claim the operational LOCAL-USABLE-1 file-safety condition.

WO429 closes the Cockpit production-binding node independently. LOCAL-USABLE-1 stays HOLD until this WO proves that the canonical local execution substrate and the runtime actually used after cutover contain the accepted FMG lineage.

## Forward-only lineage proof

Windows read-only Git archaeology established:

- `merge-base(ac01b37..., 2e6aeabd...) = ac01b37...`;
- `ac01b37...` has zero commits unique against `2e6aeabd...`;
- the accepted forward chain is `251b052 -> fe5abb3 -> 7c3c048 -> 2e6aeab`;
- `package.json` and `package-lock.json` are blob-identical across `ac01b37... -> 2e6aeab...`;
- the accepted target tracks no `.serena/` path;
- the accepted `2e6aeab...` worktree is tracked-clean and currently has both `node_modules/` and generated `dist/`;
- the canonical root also currently has `node_modules/` and `dist/`, while its visible untracked inventory is exactly `.serena/.gitignore` + `.serena/project.yml`;
- accepted delta is 21 tracked files: DEX supervision/canonical-path support, FMG implementation/tests, server integration and DWB attribution;
- `dist/` is ignored/generated, not tracked authority;
- canonical checkout has protected untracked `.serena/`; it must remain untouched.

Preferred integration class: `FAST_FORWARD_EXISTING_ACCEPTED_LINEAGE`.
Forbidden substitutions: cherry-pick, rebase, reset, force, clean, stash, or a shadow integration branch used as product authority.
## Runtime observation correction

An earlier process observation included `node A:\GitHub\SunDayRemoteMCP\dist\index.js --no-onboarding` while the WO449 review lifecycle was active. That observation was transient review-harness evidence, not proof of a persistent product service.

Fresh post-WO449 census after current-main fan-in searched only real `node.exe` / npm / cmd process records for the canonical SRM path and `--no-onboarding`; it found **no active SRM runtime process**. A broader PowerShell query had previously matched its own command text and is explicitly rejected as a false positive.

Consequences:

1. there is currently no proven persistent SRM process to stop or restart;
2. absence now does not grant future mutation authority — Windows must re-census immediately before cutover;
3. every future process match must bind exact PID + creation time + executable/command identity and owner/service boundary;
4. WO453 must never kill a process solely because its text mentions the SRM root;
5. if an exact owned persistent/operator runtime is later found, only that accepted owner/service boundary may stop/restart it.

Elapsed time, PID number, textual self-match, or a stale observation never grants termination authority.

## Authority split

A-Wiki owns the WO, compatibility-set contract, claim/WIP/replay rules, acceptance and LOCAL-USABLE-1 milestone truth.

SunDayRemoteMCP owns execution/capability implementation, build artifacts and execution-local file mutation safety.

FMG v2 remains execution-local safety. It does not become task, claim, retry, scheduler, review or completion authority.

The Windows cutover owner may advance canonical SRM only after this design is accepted and a fresh non-overlapping execution claim is published.
## Current-main recovery checkpoint — 2026-09-21

After chat/tool timeout recovery, actual authority state was re-read instead of replaying the prior plan:

- A-Wiki `origin/main = 777779e83873a6f2b9f02b71a8944189102a73a2`;
- main advanced through accepted BWA-0 / PR #451, the accepted four-file WO449 contract/schema hardening repair, and accepted WO452 / PR #454 design authority; all drift remained disjoint from this WO453 path;
- this WO file had zero main-side drift and every normal merge fan-in completed without conflict;
- Windows canonical SRM remains `main@ac01b37ba2e4b9d0249addf7694c0b91deb352c7` with protected untracked `.serena/`;
- accepted FMG final SHA `2e6aeabd09a321232098187dba4c522e37e4b1de` remains on its isolated accepted branch/worktree and is not an ancestor of canonical SRM main;
- no real SRM `node.exe` / npm runtime was present in the fresh process census;
- Mac SRM remains stale/non-authoritative and is not synchronized by this lane.

This checkpoint changes no cutover authority: design-only on Mac; consequential canonical SRM mutation remains Windows-owned and HOLD until design acceptance plus fresh WIP/claim gates.

Latest re-pin proof before independent review: `777779e... -> eb930595...` is the accepted WO449 cycle-3 fan-in and changes exactly three Browser-Wake files, with zero overlap against the WO453 document. The preceding `3db441f3... -> 777779e...` interval adds only the accepted WO452 graph-run/activation-binding design file, while `18b55b11... -> 3db441f3...` was the earlier Browser-Wake repair drift. All observed intervals remain disjoint from WO453, merge-tree/fan-in checks are clean, and normal merge-forward preserves one-file PR scope.

## Pre-cutover gates — all mandatory

1. Re-pin current A-Wiki main and Windows SRM canonical main.
2. Re-prove canonical SRM is an ancestor of the accepted FMG target or explicitly stop as `LINEAGE_DRIFT`.
3. If SRM main gained commits, do not infer compatibility; freeze a new exact candidate/compatibility set and review the delta.
4. Inventory canonical SRM tracked, untracked and ignored state. At the design freeze the only visible untracked paths are `.serena/.gitignore` and `.serena/project.yml`, and the accepted target tracks no `.serena/` path. Preserve them; any additional unexplained dirty/untracked state or target collision blocks mutation.
5. Recover every process whose command/root points at canonical SRM. Exact PID + creation/command identity is required.
6. Wait for WO449 reviewer/runtime children to become terminal and harvested; WO453 never terminates them.
7. Verify no other active lane/worktree owns SRM main or the accepted FMG paths.
8. Use the existing accepted FMG worktree or a clean detached exact-`2e6aeab` worktree for pre-cutover build/tests. Do not test by first moving canonical main.
9. Bind exact compatibility set `{A-Wiki@SHA_AUTH, SunDayRemoteMCP@SHA_EXEC}` at freeze.
10. Publish a Windows `STARTED` pulse with repo/worktree/branch/HEAD/scope/process evidence before canonical mutation.
11. Re-run the A-Faster global WIP/collision gate.
12. Independent R3 review capacity must be available before final acceptance; review WIP is global, not per device.

Any UNKNOWN above means `SAFE_TO_MUTATE_SRM_CANONICAL_MAIN=NO`.

## Pre-cutover deterministic verification

On an isolated exact accepted-candidate worktree, run at minimum:

- `npm run build`;
- FMG guard matrix including the accepted post-mutation refresh regression;
- DEX canonical-path tests;
- DEX collection/fault/process-identity tests introduced by the accepted lineage;
- Sunday supervisor tests affected by the DEX lineage;
- Sunday path-lock tests;
- directly related server/tool exposure tests.
The verification must prove the candidate itself, not whatever source happens to be on canonical main. No live credentials, remote publication, or destructive file target may be used.

Because the accepted target does not change package manifests/lockfile and both exact worktrees currently have dependencies present, this cutover grants **no package-install authority**. Do not run `npm install`, `npm ci`, `npm setup`, upgrade dependencies, or contact a package registry merely to make verification pass. If required dependencies are missing/corrupt at execution time, stop as `DEPENDENCY_ENV_UNAVAILABLE` and obtain a separately bounded environment-repair decision. `npm run build` and the frozen local test commands are the allowed verification surface.

## Canonical fast-forward operation contract

Only after every pre-cutover gate is green:

1. Windows owner rechecks exact canonical path `A:\GitHub\SunDayRemoteMCP`, branch `main`, HEAD and dirty inventory.
2. Re-prove target is a descendant of current HEAD with `git merge-base --is-ancestor HEAD <target>`.
3. Re-prove current HEAD has no unique commit relative to target.
4. Ensure no process is using the canonical checkout in a way that makes source/build replacement unsafe. Exact owned processes are handled only through their existing owner/service boundary.
5. Advance with `git merge --ff-only 2e6aeabd09a321232098187dba4c522e37e4b1de` (or a separately accepted later exact SHA). Do not use a moving branch name as the consequential target. No merge commit is needed for a descendant target.
6. Verify new `HEAD == accepted-target` (or the separately accepted later descendant).
7. Verify `.serena/` and every protected unknown path remain present/unmodified.
8. Run `npm run build` to materialize the generated `dist/` from the new canonical source.
9. Run the bounded deterministic post-fast-forward suites again against canonical source/build.
10. Only then start/restart an operator runtime if an accepted runtime/service boundary requires it.

No automatic rollback by reset is allowed. If an unexpected failure occurs after the fast-forward, preserve the new HEAD and evidence, mark `CUTOVER_RECOVERY_REQUIRED`, and repair forward or obtain an explicit authority decision.

## Runtime proof after cutover

A successful source fast-forward is not sufficient. Prove the runtime surface actually consumes the new build:

- exact executable/command and canonical root are recorded;
- launch/start is bound to one owned process identity;
- readiness/doctor or a sacrificial MCP handshake succeeds;
- the running artifact is produced after the accepted source fast-forward/build;
- a deterministic non-destructive file-mutation-guard probe reaches the FMG path;
- stale/alias protection fails closed in the supported boundary;
- no duplicate runtime is left behind;
- stop/restart failure remains typed recovery, never blind retry.
If no persistent product service exists, record that truth and prove the next ordinary supported SRM launch resolves to the rebuilt canonical `dist/`. Do not invent a daemon merely to satisfy this WO.

## Failure / replay model

- reviewer or tool process still using canonical SRM -> `WAITING_ACTIVE_OWNER`;
- current main no longer ancestor of accepted target -> `LINEAGE_DRIFT`;
- unexplained dirty/untracked files -> `DIRTY_PROTECTED`;
- exact process ownership unknown -> `PROCESS_OWNERSHIP_UNKNOWN`;
- isolated accepted-candidate tests fail -> `CANDIDATE_VERIFICATION_FAILED`;
- required local dependency environment missing/corrupt -> `DEPENDENCY_ENV_UNAVAILABLE`; do not install/update packages under this WO;
- ff-only refused -> `FAST_FORWARD_REFUSED`; do not force;
- canonical build fails after fast-forward -> `CUTOVER_RECOVERY_REQUIRED`; preserve HEAD and repair forward;
- runtime start outcome unknown -> reconcile exact PID/process evidence before any retry;
- FMG probe unavailable/ambiguous -> `RUNTIME_UNVERIFIED`; LOCAL-USABLE-1 remains HOLD.

A failed wrapper/transport call never means a consequential operation definitely did not occur.

## Acceptance evidence

Required before WO453 COMPLETE:

- exact pre/post SRM HEADs and ancestry proof;
- exact A-Wiki/SRM compatibility set;
- protected inventory evidence;
- isolated candidate build/test results;
- ff-only command/result and postcondition;
- canonical build/test results;
- exact runtime/process or next-launch proof;
- FMG runtime-path proof;
- independent R3 review of the cutover evidence/contract with no P0/P1/P2;
- GPT-5.6 Sol acceptance;
- durable completion pulse in Issue #453.

Only after this evidence may #397 record the LOCAL-USABLE-1 file-safety condition as operationally satisfied.
## Device and lane ownership

Mac / this lane owns only this A-Wiki design document. It must not mutate or synchronize the stale Mac SRM clone.

Windows / later cutover lane owns the canonical SRM fast-forward/build/runtime operation after explicit takeover/claim. It must not mutate this Mac design worktree.

Windows #452 keeps its current governance/design ownership. #447 and #449 are already completed/merged; their historical worktrees/processes do not grant new #453 authority. #453 does not preempt any Windows lane. If the global mutable budget has no free slot when design acceptance is complete, cutover waits instead of stealing a lane.

## Closeout / next actions

Design sequence:

`RECOVER -> FREEZE DESIGN -> DETERMINISTIC DOC/IDENTITY GATES -> INDEPENDENT R3 REVIEW -> GPT ACCEPT DESIGN`

Execution sequence after design acceptance and WIP admission:

`WINDOWS TAKEOVER CLAIM -> RE-PIN CROSS-REPO SET -> ISOLATED CANDIDATE VERIFY -> PROCESS CENSUS -> FF-ONLY -> BUILD/VERIFY -> RUNTIME PROOF -> INDEPENDENT R3 EVIDENCE REVIEW -> ACCEPT -> LOCAL-USABLE-1 CHECKPOINT`

Do not open DEPDIET-1 from this product-fast-lane until LOCAL-USABLE-1 is accepted; the DWB roadmap explicitly sequences `LOCAL-USABLE-1 -> PAYLOAD-1 if needed -> DEPDIET-1 -> FRONTDOOR-1`.

### Current hold

`SAFE_TO_MUTATE_WO453_DESIGN_DOC=YES`
`SAFE_TO_MUTATE_SRM_CANONICAL_MAIN=NO`
`SAFE_TO_RESTART_SRM_RUNTIME=NO`
`LOCAL_USABLE_1=HOLD_FMG_PROD_CUTOVER`
