# WO-P1-429 — COCKPIT-1B Production Authority Binding

Status: SHAPING / DOCS_ONLY_BOOTSTRAP
Issue: #429
Parent: #424 / PR #428 / roadmap #397
Topology: CONTROL_PLANE_ONLY
Risk: R2 shaping; implementation escalates if durable-state/trust authority changes.
Claim: WO-P1-429-COCKPIT1B-SHAPING-001
Owner: GPT-5.6 Sol integrator.

## Exact binding

- authority/execution repo: `A:\\GitHub\\A-Wiki-Conductor`
- shaping worktree: `A:\\GitHub\\_worktrees\\A-Wiki-Conductor-wo429-cockpit1b-shaping`
- branch: `docs/wo-p1-429-cockpit1b-shaping`
- base/current HEAD: `946cf036a57c813852060ab65264fe4e155e37e0`
- evidence destination: `runs/WO-P1-429/`
- current mutable scope: this Work Order only
- source mutation: FORBIDDEN until shaping is accepted and the mutation gate is rerun
- predecessor candidate: `e624728d420d187f0b4ef9be604e9dd0948c50fb`

## Trigger

PR #428 is a useful projection/provenance foundation but does not satisfy the
LOCAL-USABLE-1 production path. Normal desktop startup does not bind its
optional cockpit durable authority. Read-only inspection of the installed
default `control-center.sqlite` shows no `execution_records` or
`worker_leases` tables, so treating that file as execution authority would
be an unsupported identity guess.
## Goal

Identify and bind one accepted production execution/lease observation source
to ordinary desktop startup so Runtime Cockpit can truthfully reach RUNNING,
TERMINAL_UNHARVESTED, OUTCOME_UNKNOWN, and PENDING_SCOPE when evidence exists.

The binding must be a read-only consumer of existing authority. It must not
create, migrate, initialize, mirror, or infer a second state store.

## Reuse-before-build gate

Audit and classify REUSE / WRAP / EXTEND only:
- DurableJobControlService / SQLiteJobStore;
- SQLiteExecutionStore durable execution records;
- SQLiteWorkerLeaseStore canonical lease authority;
- accepted GOT / ProductionGoalCloseoutFacade / continuity projection;
- operator.v1 bounded status vocabulary;
- Hook/STM shared Monitor Projection when accepted;
- existing DesktopControlService + desktop bootstrap composition.

Reject NEW/REPLACE authority unless a separate architecture decision proves
all accepted seams insufficient.

## Shaping questions

1. What exact production component owns the execution/lease authority path?
2. How can normal desktop startup obtain that identity explicitly?
3. Is one shared control database an accepted invariant or only a test/composition option?
4. Can the existing service factory bind the source without touching desktop_app.py?
5. If a new startup/config seam is required, what is the smallest tracked scope?
6. How does this temporary adapter converge into the shared Monitor Projection?
## Hard boundaries

Forbidden during shaping and implementation unless a later accepted contract says otherwise:
- guessing a DB from filename, branch, PID, age, prose, or table presence;
- initializing/migrating execution or lease schemas from a cockpit read path;
- a new DB/store/task/job/claim/lease/review/completion state machine;
- subprocess/network work on the Tk main thread;
- a second timer or scheduler;
- retry/reassign/cleanup/merge/accept/restart cockpit commands;
- parsing human prose as execution authority;
- weakening explicit UNKNOWN / EVIDENCE_INCOMPLETE behavior;
- mutating PR #428 while its exact-SHA reviewer is live.

## Required shaping evidence

- production call graph for desktop startup;
- production call graph for durable job/execution/lease composition;
- actual installed default DB schema inspected read-only;
- exact accepted ADR/WO/contract statements about database identity;
- current #424 independent rereview result when terminal;
- no-live-authority conclusion stated explicitly if no accepted locator exists.

## Implementation entry gate

No source mutation until this WO records:
- accepted authority source/locator;
- exact implementation worktree/branch/HEAD;
- exact claim + non-overlapping scope;
- allowed/forbidden files;
- RED-first production-startup test;
- targeted + related verification;
- independent exact-SHA R2 review and exact-head CI requirements.

If no accepted production locator exists, implementation state is
`DEPENDENCY_REQUIRED`, not permission to invent one.
## Acceptance target

A normal existing desktop launch must be capable of reading accepted durable
execution truth when that authority exists, through a deterministic production
composition path.

Required proof:
- production-startup test reaches RUNNING from accepted durable evidence;
- equivalent tests reach TERMINAL_UNHARVESTED and OUTCOME_UNKNOWN;
- absent/unreadable authority remains explicit UNKNOWN;
- cockpit reads create no table/file and perform no durable write;
- exact authority identity/provenance is inspectable;
- no new lifecycle/store/command authority;
- existing monitor background cadence remains the only refresh path.

## Current evidence checkpoint

- #424 exact candidate `e624728d...`: focused 44 PASS; large related battery green.
- CI #1083 / run `35518020142`: SUCCESS.
- PR #428 remains DO NOT MERGE for LOCAL-USABLE-1.
- live default DB has Control Center/provider/config tables only; execution/lease tables absent.
- production symbol search finds no alternative default execution/lease DB locator.
- WO401 proves SQLiteExecutionStore callers may share one control database, but does not
  establish the installed desktop DB as execution authority by itself.
- GOT closeout projection is production-wired for closeout facts, but is explicitly not
  an authority database and is not a live execution-status source.

## Next safe action

Harvest canonical #424 exact-SHA R2 rereview when terminal, fold any new evidence
into this shaping decision, then freeze the smallest production-binding design.
Do not start implementation merely because a free mutable slot exists.

## Shaping disposition — dependency required

Classification: `DEPENDENCY_REQUIRED`.

Read-only archaeology found no accepted production locator that ordinary desktop
startup can use today:
- supervised execution persistence is explicitly opt-in (WO-P1-047/049);
- `DurableJobControlService.open(database_path, ...)` requires an explicit path
  and has no top-level desktop production caller;
- elastic worker lease composition likewise requires an explicit path and has no
  top-level desktop production caller;
- `operator.v1` is a protocol/dispatcher over an injected job-control service,
  not a bound production status backend;
- graph operator view reads job/runtime facts only from a caller-supplied DB;
- A-Faster `execution-pointer.json` files have no accepted production reader;
- GOT continuity projection is a closeout projection, explicitly not an authority
  database or general live-execution store;
- the installed default Control Center DB contains none of `job_records`,
  `execution_records`, or `worker_leases`.

Therefore COCKPIT-1B must not invent a locator, scan `runs/` as a new UI
authority, or initialize execution/lease tables merely to make the screen look
complete.

Required predecessor: an R3 production-runtime authority composition/locator
slice that binds existing job/execution/lease authorities to one explicit,
inspectable product composition boundary. COCKPIT-1B resumes only after that
predecessor is accepted and can consume its read-only identity without mutation.
