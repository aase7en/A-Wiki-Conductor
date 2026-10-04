# WO-P1-581 — SunDayRemoteMCP Darwin boot-identity liveness repair

Status: BOOTSTRAP_CLAIMED / SOURCE_BLOCKED
Issue: #581
Risk: R3
Topology: CROSS_REPO
Claim: `WO-P1-581-SRM-BOOT-IDENTITY-001`
Owner/integrator: A-Conductor GPT integrator
Bootstrap claim evidence: Issue #581 comment `5981994561`

## 1. Frozen compatibility binding

AUTHORITY_REPO:
- repository: `aase7en/A-Wiki-Conductor`
- bootstrap worktree: `/Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo581-srm-boot-identity-bootstrap`
- branch: `docs/wo-p1-581-srm-boot-identity-bootstrap`
- base HEAD: `100c94b0308ba33101e00929d7016443f3f7331f`

EXECUTION_REPO:
- repository: `aase7en/SunDayRemoteMCP`
- frozen remote main for bootstrap: `41a566c845c2629f9771becf68175d71cb7d1aaa`
- execution worktree: NOT_CREATED
- execution branch: NOT_CREATED

Any drift in either SHA invalidates this compatibility set until it is re-pinned and the mutation gate is rerun.

## 2. Bootstrap authority

The canonical new-task exception in `00-AGENT-ENTRY.md`, `docs/agent-collab/AGENT_ENTRY_PROTOCOL.md`, and `COLLAB_PROTOCOL.md` permits one clean isolated docs-only governance bootstrap when a genuinely new task has no Work Order/claim.

Bootstrap mutable scope is exactly this new file:
- `docs/work-orders/WO-P1-581-srm-darwin-boot-identity.md`

Everything else is read-only. This bootstrap grants no SunDayRemoteMCP source, test, runtime, process, claim-transfer, merge, or completion authority.

## 3. Defect evidence

Affected durable execution:
- `exec-murep77o-pa10qmf9`
- task: #575 exact-SHA read-only R3 review
- candidate: `5a8ffe10f5daf15c24ae6618894cc3d725f7acd9`

Observed divergence:
- durable observer classified the execution `INTERRUPTED` as stale-boot;
- exact supervisor/Kilo process tree was still alive;
- the detached review worktree remained clean at the exact candidate SHA;
- `sunday_cancel` refused cancellation because durable state was already terminal;
- after exact PID/PPID/command/worktree verification, only the stale review process tree was terminated; no broad kill and no repository mutation occurred.

Boot-identity values captured in the incident:
- recorded: `darwin-kern.boottime={ sec = 1790547593, usec = 491202 } Mon Sep 28 05:19:53 2026`
- later stable current samples: `darwin-kern.boottime={ sec = 1790547593, usec = 438805 } Mon Sep 28 05:19:53 2026`
- seconds match; microseconds differ.

Current SunDayRemoteMCP `origin/main@41a566c...` shows:
- `src/sunday/supervisor-io-probe.ts` obtains `sysctl -n kern.boottime` and stores the bounded full line as `darwin-kern.boottime`;
- `src/sunday/supervisor.ts` uses recorded/current boot identity for stale-boot decisions before trusting recorded PIDs;
- related existing tests are in `test/test-sunday-supervisor.js`.

These facts establish the failure path, not the final root cause.

## 4. Root-cause status

ROOT_CAUSE = TO_PROVE.

Current hypothesis: the Darwin boot-identity capture/normalization/comparison contract is too strict or not stable across all supported observations, allowing a same-boot representation mismatch to be treated as a reboot.

Do not claim that macOS itself changes `kern.boottime` microseconds. Repeated current samples were stable. The repair must first deterministically reproduce the recorded/current mismatch class and identify why equivalent-boot observations can differ.

## 5. Missing invariant

`TRANSPORT_OR_IDENTITY_UNCERTAINTY != EXECUTION_TERMINALITY`

A durable execution must not become terminal solely from an unstable/lossy boot-identity representation while exact runtime/process evidence contradicts that conclusion.

A true reboot must still fail closed: old PIDs must never be attached, signalled, or treated as current merely because a weaker comparison happens to match.

If durable state and exact runtime process identity disagree, the system must surface a typed reconciliation state such as `PROCESS_STATE_DIVERGENCE` (exact vocabulary to be frozen at the source gate) rather than silently presenting mutually incompatible truths.

## 6. Future source/test hypothesis — NOT YET MUTABLE

Candidate execution-repo scope to evaluate after this bootstrap is accepted and the full CROSS_REPO mutation gate passes:

- `src/sunday/supervisor-io-probe.ts`
- `src/sunday/supervisor.ts`
- `test/test-sunday-supervisor.js`

Read-only supporting surfaces unless new evidence proves they are required:
- `src/sunday/supervisor-evidence.ts`
- `src/sunday/recover.ts`
- `src/sunday/supervisor-io-shim.ts`

Any additional tracked path is `SCOPE_EXPANSION_REQUIRED`.

## 7. Required hard-bug loop

`REPRODUCE -> MINIMIZE -> ROOT_CAUSE -> RED REGRESSION -> REPAIR -> TARGETED+RELATED VERIFY -> FREEZE -> INDEPENDENT R3 REVIEW -> CI/POST-MAIN`

Before source mutation:
1. re-pin both repositories and prove the exact compatibility pair;
2. create one isolated SunDayRemoteMCP worktree/branch from the accepted execution SHA;
3. prove no mutable-hotspot collision and valid global WIP admission;
4. read applicable `DEFECT_LESSONS.md`;
5. freeze the smallest actual source/test scope;
6. run A-Audit on the SAFE_READY task;
7. perform exactly one task-bound `GLM_OFFLOAD_ASSESSMENT`;
8. immediately before a useful GLM-5.3 MAX material request, run the accepted fresh CoinTH fail-closed preflight.

GLM-5.3 MAX is preferred for bounded implementation/repair and the required independent exact-SHA R3 review. GPT-6.1 Sol is reserved for difficult architecture/root-cause/adjudication or a genuinely blocked eligible GLM route. GPT-6 Luna LOW remains Parent traffic control. JEV is advisory only.

## 8. RED regression matrix

At minimum the source lane must prove:
1. exact same boot identity -> not stale;
2. genuinely different boot -> stale and old PID is never trusted/killed;
3. incident-equivalent Darwin representations (same underlying boot, representation mismatch class) -> deterministic canonical result, never false terminalization;
4. malformed/unknown boot identity -> fail closed without fabricating liveness;
5. recorded/current boot disagreement plus matching exact process identity -> typed reconciliation path, not silent terminal/process divergence;
6. terminal durable state vs still-live exact owned process is observable/reconcilable and cancellation cannot silently disagree with process reality;
7. PID reuse / creation-identity protections remain intact;
8. no broad process termination or PID-only ownership inference is introduced.

The exact incident-equivalence rule must follow the proven root cause. Do not hard-code "ignore microseconds" merely to make this matrix green.

## 9. Deterministic verification

Required after repair:
- focused supervisor/liveness tests;
- related recovery/cancel/process-identity tests;
- TypeScript build/typecheck required by SunDayRemoteMCP policy;
- exact diff/scope check;
- secret scan and text hygiene;
- frozen exact candidate SHA;
- independent exact-SHA GLM-5.3 MAX R3 review;
- hosted CI on the frozen candidate when available/required;
- GPT integrator acceptance;
- merge only through the exact accepted authority;
- post-main verification.

Any production repair after freeze creates a new candidate SHA and requires rereview.

## 10. Durable defect-memory closeout

Before #581 can close, fold the proven facts into the existing canonical defect-memory path:
- symptom;
- impact;
- trigger;
- proven root cause;
- missing invariant;
- fix;
- executable regression/checker protection;
- future warning.

The durable prose fold belongs in the existing `DEFECT_LESSONS.md` authority, not a new memory store. The regression test/checker is the primary prevention mechanism. GitHub Issue #581 and exact CI/review evidence remain cross-session continuity.

## 11. Forbidden scope

- raw Codex SQLite/session/lock edits;
- broad-kill Node/Python/Kilo/Codex/ChatGPT;
- reset/clean/stash/force-push unknown work;
- weakening process-creation or boot/reboot safety to make the test pass;
- new task/claim/lease/retry/review/completion authority;
- SunDayRemoteMCP source/test/runtime mutation during this docs-only bootstrap;
- treating model prose as acceptance.

## 12. Bootstrap exit

Bootstrap is complete only when:
- this file is the sole tracked change;
- exact base/branch/worktree identity is verified;
- UTF-8/LF and `git diff --check` pass;
- the claim/bootstrap checkpoint is durable on Issue #581;
- the docs-only commit is frozen and, if policy permits, pushed to its branch;
- the full mutation/WIP/collision gate is rerun.

`SAFE_TO_MUTATE_BOOTSTRAP_DOC=YES`
`SAFE_TO_MUTATE_SOURCE=NO`
