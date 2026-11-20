# WO208 — GLM closeout crash/recovery evidence campaign

Task: WO208-GLM-CLOSEOUT-LAB-001
Status: QUEUED / EVIDENCE ONLY / NO PRODUCT IMPLEMENTATION
Design owner: Poppy Javis / home Mac Astra
Parent: Issue214 / WO205; existing parent integrator retains acceptance and source release
Executor: one eligible Windows ZCode / GLM session after current goals/capacity gates

## Goal and effort

Make the existing closeout crash/restart requirements concrete enough for WO205 to implement
without discovering fundamental effect/journal ambiguity during final review. Extend the
four Astra seam probes with reproducible child-process crash cuts, native Windows store
behavior, exact effect reconciliation and a finite model. Produce implementation decision
inputs and reusable tests as research artifacts, not production code.

Plan for 10–18 hours of useful bounded work; up to 24 only while new evidence justifies it.
Finish early when acceptance is met. Hours/test counts are not completion authority.
Provider limits still apply; checkpoint and stop on quota/entitlement/environment gates.
No keepalive, rate-limit bypass, sleep-to-fill-time or endless random stress.

## Exact identity

Repo: https://github.com/aase7en/A-Wiki-Conductor.git
Source base: 02d39cbd9bca1ab3bb19b6e0cfbb0766c991f971
Delivery branch: codex/wo-p1-208-closeout-crash-contract
Lab branch: codex/wo-p1-208-glm-closeout-lab
Prepared Windows path: A:/GitHub/_worktrees/A-Wiki-Conductor-wo208-glm-closeout-lab
Work order: docs/work-orders/WO-P1-208-closeout-crash-contract.md
Proposal: docs/plans/2026-09-12-closeout-crash-boundary-contract.md
Seed evidence + exact executable: docs/reviews/WO-P1-208-closeout-crash-evidence.md
Output: docs/reviews/WO-P1-208-glm-closeout-lab.md plus runs/WO-P1-208/glm/result.json

Pin the exact delivery commit from the Issue214/233 handoff or human pointer. Never use
an unverified branch tip. Record packet/proposal/seed SHA-256. Source blob IDs must match:
- goal_closeout.py: 0acdf8c99194818169239a2eaf4aeac7758e3f39
- job_store.py: bde34b6f4e1163caaa7b641a21dd741e14e5cda8
- job_state.py: 816784b431c4d03d9cfbe23a806525adc29645f4
- tests/test_goal_closeout.py: b4055cae6a79c2165aa20dd0c5172c4cf0736446
These are Git blob IDs, not SHA-256. Verify source/tests unchanged against base.
On owned later checkpoint resumes, verify immutable packet/source hashes and the explained
child diff rather than requiring HEAD still equal initial delivery.

## Startup and anti-duplication

Follow 00-AGENT-ENTRY, graph-selected nodes, AGENTS, actual Git/dirty/claim state, CURRENT-WORK,
this WO, latest Issue214/233, WO205, and the active controller checkpoint where applicable.
WO205 was a separate docs branch at preparation, so its file may not exist in this
checkout. Read it without switching/merging this worktree:
`git show origin/docs/wo-p1-205-zra2-phase-d-gate:docs/work-orders/WO-P1-205-zra2-phase-d-closeout-binding-gate.md`
Pinned preparation commit: 06764f646ee307bdf92b459fd471f6fd787788b7. Fetch the named ref
if absent, and prefer newer explicit parent authority from Issue214 without modifying it.
Read the proposal and seed before inventing experiments. Re-read current parent gates;
WO201/205 source remains HOLD unless its owner separately releases a source lane.

The human pointer selects this evidence task only for an eligible session. It never cancels
WO196 or WO206/master work. If already running another goal, finish/checkpoint under that
owner; queue this packet. Do not use this lab to escape a master CI/review/authority gate.
Default WIP and independent-review capacity limits still apply. No hidden subagents.

Before writing prototypes, append the child claim in THIS WO on the lab branch, commit/push
and publish branch/HEAD/owner/scope/capacity to Issue214. If another session already owns
WO208-GLM-CLOSEOUT-LAB-001, STOP_COLLISION. A missing process is not proof a claim is free.
Do not edit the original Astra delivery branch or any other lane. Resume owned artifacts;
never reset/clean/stash/rebase/force-push unexplained state.

## Writable scope

Tracked, on the GLM branch only:
- NEW docs/reviews/WO-P1-208-glm-closeout-lab.md
- append child checkpoints to docs/work-orders/WO-P1-208-closeout-crash-contract.md

Ignored: runs/WO-P1-208/glm/** for prototypes, finite model, fixtures, captured output,
result/checkpoint and task-local environment if needed. Temp roots created by the lab
must use wo208- prefix and be recorded. Retain portable replay code/excerpts in the report.

Read-only: all src/**, existing tests/**, .github/**, other docs/WOs, packet/proposal/seed,
CURRENT-WORK/handoff/COLLAB, A-Wiki, private Drive, real Git branches/workspaces beyond this
lane, live databases, Worker/process/provider configuration and installed ZCode state.
No credentials/provider calls, live release/merge/fold effects, new scheduler/store/controller
or production recovery implementation. Synthetic SQLite copies and owned file effects only.
No actual power interruption, reboot, unmount, disk corruption, global dependency install,
or arbitrary process kill. Do not touch WO202 process-cleanup or WO204 candidate/review work.

## Program sequence

| Program | Useful effort | Deliverable |
|---|---:|---|
| C00 source/owner/previous evidence | 0.5h | manifest and no-repeat ledger |
| C01 native Windows seed controls | 1h | four minimized baseline probes |
| C02 real child-process cut matrix | 2–3h | reopen-after-exit durable observations |
| C03 lost acknowledgment / store errors | 1–2h | commit-vs-return truth matrix |
| C04 stale-owner / two-process effect ordering | 1–2h | deterministic event trace |
| C05 exact receipt and idempotency prototypes | 1.5–2.5h | supported/unsupported port contract |
| C06 lease/fold/current-evidence contradictions | 1–2h | existing-authority reconciliation cases |
| C07 finite model with negative controls | 1–2h | bounded safety/liveness oracle |
| C08 WO205 implementation readiness + handback | 1–2h | decisions, exact consumers, replayable report |

Estimates overlap and are not a runtime quota. Stop a settled program after one adequate
native proof plus required controls. Add cases only for an invariant, not to hit a count.

### C00 — pinned manifest

Record host, Python/SQLite versions, delivery/source SHA, packet/proposal/seed hashes,
claim/capacity, exact branch/path and existing evidence consumed. Inspect relevant source
for production GoalCloseout consumers. Report absence honestly. Read existing P0-B3 tests
and WO205 matrix; mark covered cases so the campaign adds proof rather than retelling them.

One existing baseline:
`python -m pytest -q tests/test_goal_closeout.py tests/test_job_store.py`

### C01 — reproduce and validate the harness

Extract the exact Python fence from Astra seed into ignored lab storage; verify its hash.
Run on Windows with only synthetic fixture data. Preserve real SQLiteJobStore/executor,
real valid job transitions and truthfully recorded verification checkpoint versions.
Confirm concurrent two-effects/one-checkpoint, stale-facts effect, UNKNOWN reentry, and
positive one-effect/COMPLETE/no-op. Thread return ordering may differ. Add a negative
control demonstrating the harness fails if the claimed effect count is wrong.

This seed is a reopened-store test, NOT actual process crash evidence. Use that distinction
in every report. Do not classify a deliberately unsafe caller as a reachable production bug.

### C02 — actual child-process exit and reopen

Each helper is a short owned Python process, not ZCode/Worker/provider. Parent records
exact executable, PID/creation identity, fixture root and command; finite timeout <=60s.
Prefer helper self-termination at an explicit barrier (os._exit in the helper) to killing
an external process. Parent waits for the owned child to exit and reopens its sacrificial DB.
No sleep-based hope that a particular boundary was reached.

Instrument only lab adapters/ports. Cover before effect, effect committed before response,
response before job checkpoint, job checkpoint committed before response, COMPLETE committed
before response, and restart reconciliation before any second effect. For persisted file
receipts use explicit close/flush semantics and report them. Process exit is not power-loss
proof; do not claim fsync makes every external operation transactional.

For each cut capture effect count/identity, journal refs+sequence, job state/version,
recovery disposition and whether a second effect was attempted. A deliberately unsafe
baseline may duplicate; a proposed safe composition must suppress ambiguous replay or
return typed RECOVERY_REQUIRED. Never hide UNKNOWN by creating fresh all-green facts.

### C03 — acknowledgment ambiguity

Wrap the real sacrificial job store with a lab port that commits then raises a bounded
JobStoreError to model lost acknowledgment. Contrast a raise-before-commit control.
Show why returning an error cannot alone tell whether an event committed. Reopen/read
ordered events and exact identities before deciding. Cover fold checkpoint and final
transition separately; preserve existing terminal idempotent no-op.

Inject failures in synthetic effect-port response and query. Generic catch-and-retry is
invalid. Missing receipt, divergent receipt and unqueryable effect remain distinct from
proven not executed. Do not introduce a production outbox or second completion journal.

### C04 — ordering and owner validity

Advance real job state/version after a facts snapshot but before effect; demonstrate
which part rejects and whether any effect already occurred. Then model an accepted-owner
precondition at the effect boundary in a lab-only adapter and test its exact limits.
A Python thread lock proves no cross-process safety: use two helper processes for that claim.

Enumerate deterministic schedules: both observe same version, one owner becomes stale,
first effect succeeds, competing checkpoint wins, stale caller resumes. Record each actor
and boundary. Do not invent authority by adding arbitrary trusted=True/host_id fields.
If existing APIs cannot carry the needed fence, report DESIGN_DECISION_REQUIRED with source
symbols. No source patch even when the defect seems easy.

### C05 — idempotent/queryable effect prototype

Prototype only against a sacrificial effect destination. Derive a stable identity from
existing stage/task/candidate and relevant merge/fold/lease fields, with identical request
reuse and divergent-payload refusal. The destination must actually enforce idempotency;
a digest in a request alone proves nothing. Demonstrate two competing processes, lost
response, stale receipt and reopen. Record which evidence could be reused in the existing
effect owner and which capability is absent.

These temporary receipts are a lab oracle, NOT a proposed second production store. Compare
at most the minimal alternatives in the Astra proposal. Do not implement all options as
new production frameworks. Query UNKNOWN remains recovery. Absence counts as negative proof
only under a stated trustworthy, complete query contract and accepted exclusion.

### C06 — leases and conflicting observations

Reuse existing lease release semantics and test fixtures; do not operate live leases.
Test actual release then missing checkpoint, already_released, active despite release ref,
old lease ref, released=False/already_released=False, and typed/raised failures. Keep exact
current lease identity and occupancy; no forced release merely because timeout elapsed.

For folds test current merge/task contradiction, effect complete with no checkpoint, and
checkpoint present with current evidence UNKNOWN. Preserve existing refusal semantics.
Separate a malformed port contract from a demonstrated reachable completion bypass.

### C07 — finite state model

Enumerate small states for current ownership/version, effect state, acknowledgment state,
checkpoint presence/identity, current observation and job terminality. Clearly bound the
state space and map every transition to a source/adapter assumption. Verify:
- no unsupported/unknown effect is retried;
- completed checkpoint is not fabricated from intent/error;
- contradictory current identity never completes;
- same completed exact job is a no-op;
- known eligible operations can progress (record unavoidable recovery stops separately).

Include a deliberately unsafe mutation of the model and show the oracle catches the
seed counterexample. This is finite reasoning, not proof of the whole OS or future code.
Do not reproduce existing glob/physical identity work from WO196.

### C08 — implementation decision packet

Hand WO205 a compact table: invariant, actual consumer/port, native evidence, gap, minimal
accepted-authority extension if needed, source owner and dependency. Do not create a new
Phase-D WO or pick its source scope. Parent decides whether to restrict initial support,
use an existing idempotent adapter or extend existing durable intent/recovery semantics.

Source changes require Phase B/C acceptance, Issue214 explicit release, a fresh R3 claim
and exact-SHA review. This lab never transitions into implementation automatically.

## Evidence, checkpoint and stop rules

After each program or blocker update ignored checkpoint.json and append a concise scoped
WO checkpoint; push meaningful doc milestones. Keep commands bounded, check exit codes
individually, capture exact byte evidence without implicit PowerShell encoding rewrites.
Retain minimized counterexample seeds and cleanup outcome. No raw environment dump or
unrelated logs. Never delete another task's temp roots or processes.

Same failure twice without new evidence -> STOP_NO_PROGRESS with root cause, not endless
repair. Genuine quota/provider/environment/ownership ambiguity -> checkpoint and stop.
Completion is COMPLETE_FOR_PARENT_REVIEW or DESIGN_GAPS. Neither is source acceptance.
Do not poll CI/review repeatedly or switch to another backlog item to avoid a gate.

Result JSON fields: task_id, claim, source_sha, delivery_sha, packet_sha256, proposal_sha256,
seed_sha256, host, runtime_versions, completed_programs, cases, native_vs_model, findings,
decisions_pending, modified_paths, cleanup, elapsed_hours, independent_review_status,
merge_performed=false, next_safe_action. Record final candidate SHA after commit in the
public handoff/result; do not make a file hash refer circularly to its own containing commit.

Tracked report must include replayable reduced code/commands, source/probe identities,
controls, observed counts, evidence limits and missing native Mac cases. Ignored files
alone are not a cross-machine handoff. Commit/push allowed docs; publish exact SHA/report
pointer to Issue214/233. The integrator reads results directly; no human copy-back.

## Capability and continuity note

Official ZCode Agent documentation checked 2026-09-12 supports agent coding/testing workflows:
https://zcode.z.ai/en/docs/agents . Existing WO193 GLM evidence demonstrates repository/test
execution on this Windows host; its unresolved B07 result also demonstrates why deterministic
barriers and truthful limits matter. Neither evidence promises unlimited quota or a 24h run.
Reuse current supported Goal/checkpoint behavior; do not build a new controller here.
