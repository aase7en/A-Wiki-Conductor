# WO-P1-498 — A-Faster executable GUARD hook enforcement

Status: SHAPING / SOURCE BLOCKED ON HOOK-0
Issue: #498
Parent context: #483 A-Faster hardening; #365 Hook/STM roadmap; #368 HOOK-0
Topology: CONTROL_PLANE_ONLY
Risk: R3 — authority/security invocation gates
Reuse classification: EXTEND

## Binding

Authority repo: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo498-guard-shaping`
Branch: `docs/wo-p1-498-guard-shaping`
Base: `29183fed35188df4723593311ed2e0f86c3bb049`

Phase-0 mutable scope:
- `docs/work-orders/WO-P1-498-a-faster-executable-guard-enforcement.md`

Everything else is read-only until the dependency gate below is satisfied.

## Goal

Make A-Faster's accepted material-boundary sequence resistant to prompt/session
forgetfulness by enforcing accepted authority/safety policy at executable
invocation seams where a real centralized seam exists:

`ENTRY -> RECOVERY -> PRE_DISPATCH -> PRE_MUTATION -> PRE_FREEZE -> PRE_REVIEW -> PRE_MERGE -> POST_MAIN`

Hooks never become task/claim/lease/retry/review/acceptance authority. They
enforce existing authority at invocation boundaries and fold evidence into
existing WO/run-pointer/closeout evidence.

## Dependency gate

Source implementation is BLOCKED until HOOK-0 / Issue #368 / PR #385 is
accepted on then-current main and post-main verified.

Required dependency properties:
- Hook Contract v1 GUARD class accepted;
- security/authority/ambiguous GUARD fail closed;
- enforcement pinned to invocation/gate time, never eventual Hook Bus delivery;
- OBSERVE/ADVISORY remain non-authoritative;
- forward-compatible parsing/security rules accepted.

No #498 source mutation may pin a superseded HOOK-0 candidate.

## Actual seam inventory

### REUSE — PRE_DISPATCH

`src/a_conductor/supervised_run_coordinator.py` is the strongest current
centralized execution seam.

`SupervisedRunCoordinator.run_with_outcome()` already:
1. computes the execution fingerprint;
2. invokes `DuplicateExecutionGuard.assess(...)`;
3. returns BLOCKED/ATTACH/REUSE dispositions without blind relaunch;
4. creates the durable execution record only for a fresh safe launch;
5. constructs `SupervisedLaunchPlan`;
6. invokes the backend launch;
7. polls/collects using durable execution identity.

This is the first executable GUARD integration target. A guard MUST run after
binding/dedupe facts are known and before a new execution record/launch can
become consequential.

### REUSE — duplicate/replay safety

`src/a_conductor/execution_deduplication.py` already owns pure duplicate
assessment:
- SAFE_TO_LAUNCH;
- ATTACH_RUNNING;
- REUSE_COMPLETED;
- BLOCKED_UNKNOWN.

It explicitly owns no launch/retry/Git mutation authority. #498 must preserve
that boundary; GUARD consumes the assessment, never replaces it.

### REUSE/PATTERN — provider authority guard

`src/a_conductor/claude_code_supervised_runner.py` already supports an
injected `ProviderExecutionAuthorityGuard.check()` before consequential
provider execution. Reuse the injection/fail-closed pattern; do not fork a
second provider-specific policy engine.

### OBSERVE ONLY — current Hook adapter

`src/a_conductor/control_hook_adapter.py` normalizes authoritative
`ControlEvent` to Hook Contract v1 `OBSERVE` envelopes. It is not an
executable GUARD and cannot satisfy any #498 guard checkpoint.

### REUSE — closeout evidence

`src/a_conductor/production_closeout_observation.py` is read-only evidence
plumbing for exact PR head, merge ancestry and post-main CI. It owns no merge,
review, retry, completion or command authority. PRE_MERGE/POST_MAIN GUARD may
consume its accepted evidence later, but must not turn this provider into an
action gateway.

## Enforcement truth

A-Faster exposes exactly:
- `POLICY_ONLY` — skill/test/manual deterministic gate; executable GUARD not
  proven on the exact action path;
- `GUARD_ENFORCED` — accepted GUARD executed on the exact material action
  path and allowed it;
- `OBSERVE_ONLY` — telemetry only; never satisfies GUARD.

No path may be reported `GUARD_ENFORCED` merely because a hook event exists.

## Staged implementation

### GUARD-498A — PRE_DISPATCH executable guard

First source slice after HOOK-0 acceptance.

Target behavior:
- exact lane binding includes repo/worktree/branch/HEAD/task/claim/scope;
- consume existing duplicate-execution assessment and durable execution facts;
- missing/ambiguous authority/security evidence fails closed;
- RUNNING => attach/no new dispatch;
- terminal-unharvested/recovery-required => no blind launch;
- wrapper/session/UI ambiguity never grants dispatch;
- GUARD decision occurs before consequential fresh launch;
- no new store, scheduler, lease, retry or task authority;
- emit/fold Hook GUARD evidence without relying on Hook Bus delivery to enforce.

Expected minimal source family to validate during RED design:
- a small pure/injected A-Faster execution guard module OR an existing accepted
  authority-guard abstraction if one can be reused cleanly;
- `src/a_conductor/supervised_run_coordinator.py`;
- focused tests for coordinator/guard behavior;
- this WO.

The exact source path set is NOT yet authorized; it will be frozen only after
HOOK-0 post-main acceptance plus source-symbol impact analysis and
`DEFECT_LESSONS.md` read.

### GUARD-498B — PRE_MUTATION

Target: mutation must consume existing `SAFE_TO_MUTATE` truth; the hook does
not mint mutation authority.

Current limitation: A-Sunday still has raw shell/Git/tool mutation surfaces
that do not all pass through one accepted command/mutation gateway. Therefore
full unskippable PRE_MUTATION enforcement is NOT claimed in 498A.

498B requires an accepted centralized mutation/Command Gateway route or a
proven complete inventory of material mutation entry points. Until then it
remains `POLICY_ONLY` outside guarded execution surfaces.

### GUARD-498C — PRE_FREEZE / PRE_REVIEW

Consume existing deterministic verification, exact changed-scope, frozen SHA
and clean read-only reviewer binding. These checkpoints cannot create review
authority or accept their own evidence.

### GUARD-498D — PRE_MERGE / POST_MAIN

Consume accepted exact-head review/CI, current-main drift, expected-head merge,
merge ancestry and post-main CI evidence.

Current limitation: the accepted roadmaps explicitly state no production
Command Gateway source exists yet. Raw `gh pr merge` / Git shell paths can
bypass a hook. Therefore unskippable PRE_MERGE enforcement depends on ACT-1
Command Gateway or an equivalent accepted central action seam.

## Fail-closed rules

For security/authority GUARD:
- missing registration;
- malformed guard evidence;
- ambiguous scope classification;
- stale repo/worktree/branch/HEAD;
- unknown claim/owner;
- unsafe duplicate/replay state;
- required guard unavailable on a route declared GUARD-required

=> dependent material action does not proceed.

A route not yet wired for executable GUARD is `POLICY_ONLY`, not falsely
blocked as if the runtime gate existed and not falsely labeled GUARD_ENFORCED.

## No shadow authority

Forbidden:
- new task DB;
- new scheduler;
- new claim/lease registry;
- new retry state machine;
- new completion/review authority;
- Hook Bus/STM/Monitor as SSoT;
- event delivery as the enforcement point;
- provider/model identity as mutation authority.

## RED/adversarial matrix for 498A

Before GREEN implementation, tests must prove:
1. fresh safe binding + SAFE_TO_LAUNCH + GUARD allow => exactly one launch;
2. equivalent RUNNING => no new launch;
3. BLOCKED_UNKNOWN => no launch;
4. claim/scope/HEAD drift => fail closed;
5. malformed/missing authority GUARD evidence => fail closed;
6. Hook Bus delivery failure after invocation decision cannot reverse an
   already-enforced deny/allow;
7. OBSERVE event cannot satisfy GUARD;
8. timeout/UNKNOWN/session loss cannot authorize retry;
9. exact guard evidence binds task/claim/repo/worktree/branch/HEAD/scope;
10. no guard path can call launch/retry/merge/mutate directly;
11. no second durable store is introduced;
12. existing supervised-run attach/reuse/collect behavior remains compatible.

Later phases add adversarial bypass tests for mutation/merge gateways.

## Acceptance path

Phase 0:
- docs-only freeze;
- HOOK-0 dependency reaches accepted/post-main state.

498A:
- read `DEFECT_LESSONS.md`;
- freeze exact source/test scope;
- RED-first tests;
- GLM-5.3 MAX bounded implementation;
- targeted + related deterministic suites;
- exact frozen SHA;
- independent GLM-5.3 MAX R3 review;
- hosted CI;
- expected-head merge;
- post-main verification.

Then continue 498B/C/D only when each centralized action seam is proven.
