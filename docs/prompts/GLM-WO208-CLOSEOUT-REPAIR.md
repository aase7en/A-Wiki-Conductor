# WO208 — bounded GLM evidence repair

Task: `WO208-GLM-CLOSEOUT-REPAIR-001` (same WO208, one repair cycle).
Status: PREPARED_NOT_STARTED / QUEUED_CAPACITY / EVIDENCE ONLY.
Owner when claimed: one eligible Windows ZCode / GLM session.
Reviewer: Poppy Javis / home Mac Astra. WO205/Sol retains Phase-D acceptance and release.

## Objective

Repair R1–R5 and retract false F1 from the independent review. Deliver executable,
truthful, portable crash/recovery evidence for WO205. Do not build the production fix.
Use this packet for the full supported goal loop without repeated human prompts.
This is the correction of an existing submission, not another broad research campaign.
Budget roughly 6–12 useful hours if needed; up to20 only for concrete unresolved proof
work. Finish early when acceptance is met. Actual provider limits apply; no padding,
keepalive, sleep-to-fill-time, endless stress or quota bypass.

## Immutable identity and startup

Repository: `https://github.com/aase7en/A-Wiki-Conductor.git`.
Worktree: `A:/GitHub/_worktrees/A-Wiki-Conductor-wo208-glm-closeout-repair`.
Branch: `codex/wo-p1-208-glm-closeout-repair`.
Frozen submission: `b3a553ca3bb51753daa84b5f6be0dc81f1d025d6`.
Original source: `02d39cbd9bca1ab3bb19b6e0cfbb0766c991f971`.
Review delivery: exact commit in the Issue214/233 delivery comment and human pointer.
Review: `docs/reviews/WO-P1-208-astra-lab-review.md`.
WO: `docs/work-orders/WO-P1-208-closeout-crash-contract.md`.
Original design: `docs/plans/2026-09-12-closeout-crash-boundary-contract.md`.
Original seed: `docs/reviews/WO-P1-208-closeout-crash-evidence.md`.

Follow 00-AGENT-ENTRY, PROJECT-GRAPH, AGENTS, actual repository/remote/branch/HEAD/dirty
state, CURRENT-WORK, this WO, relevant routed policies and latest Issue214/233. Read
the review before changing the lab. Fetch/read current WO205 and master authority
without switching/merging this pinned worktree. Re-pin claims and capacity. At packet
preparation Phase B was accepted and WO216 C0 separately released; those owners have
priority and are not transferred here. A new pointer must not preempt an active goal
or evade a controller's external gate. If busy, queue this task under the current owner.

Require HEAD == exact review delivery on initial start. On owned resumes, require
explained append-only candidate history and unchanged immutable inputs. Record packet,
review, seed and proposal hashes. Require all source/tests byte-identical to source base:

| Path | Git blob ID |
|---|---|
| src/a_conductor/goal_closeout.py | 0acdf8c99194818169239a2eaf4aeac7758e3f39 |
| src/a_conductor/job_store.py | bde34b6f4e1163caaa7b641a21dd741e14e5cda8 |
| src/a_conductor/job_state.py | 816784b431c4d03d9cfbe23a806525adc29645f4 |
| tests/test_goal_closeout.py | b4055cae6a79c2165aa20dd0c5172c4cf0736446 |

If another owner already claimed this repair, stop for coordination; a missing process
does not release a claim. Append claim here in the assigned WO, commit/push and publish
identity/scope/capacity to Issue214 before prototype changes. Do not write claims in
global SSoT. Keep the frozen lab worktree and branch untouched.

## Exact writable scope

Only on the repair branch:

1. Correct `docs/reviews/WO-P1-208-glm-closeout-lab.md`; retain original result provenance
   and explicitly supersede false/unsupported claims rather than erase history.
2. Append repair checkpoints to `docs/work-orders/WO-P1-208-closeout-crash-contract.md`.
3. NEW research bundle, exactly these allowed files under `docs/reviews/wo208-closeout-lab/`:
   `seed_probe.py`, `wo208_child.py`, `c02_cut_matrix.py`, `c03_c05_c06_suite.py`,
   `c07_model.py`, optional `lab_common.py`, `manifest.json`, `README.md`.

Ignored outputs/environment/probes: `runs/WO-P1-208/glm-repair/**`; owned recorded
temporary roots with `wo208-` prefix. No outputs or bytecode in the tracked bundle;
set PYTHONDONTWRITEBYTECODE=1 and explicit output paths. Do not add CI discovery/hooks.

Read-only: src/**, tests/**, .github/**, all other docs including this packet, Astra
review/proposal/original seed, global CURRENT-WORK/handoff/COLLAB, other WOs/branches,
A-Wiki, private Drive, installed ZCode/config, live jobs/leases/processes/providers.
No new production store/journal/controller, source mutation, schema migration, real
release/fold/merge, credentials/provider calls, power interruption, broad cleanup or
process kills. Work on synthetic SQLite stores and owned file effects only. Helpers
must have exact process identity and bounded cleanup. No Worker project rebinding.

## Recover the named artifacts once

Read only the five named files from the frozen worktree
`A:/GitHub/_worktrees/A-Wiki-Conductor-wo208-glm-closeout-lab/runs/WO-P1-208/glm/`.
Before copying, verify its HEAD/clean tracked state and each raw SHA-256 against the
review's table. Copy only those files into owned ignored repair storage; no recursive
copy/search of runs or ZCode. Record raw byte hashes and any explicit LF normalization.
If unavailable/mismatched, checkpoint ARTIFACT_RECOVERY_REQUIRED and stop dependent work;
do not silently recreate an alleged original result. Rehydrate original seed from its
fence and verify `bf1136e729cbe8676676031120a586610adeeb3dccca20addda6c1301a579aac`.
Original recorded hash is correct. Publish the seed with that canonical fence content;
keep invocation/root setup outside it if needed.

## Finite program sequence

Run one RED/repair/GREEN batch per program, checkpoint at each material boundary.
Use deterministic controls first, a few fixed-seed schedules only where scheduling
adds evidence. No automatic phase advancement or broad reruns on an external block.

### P0 — reproduction ledger and stable inputs

Pin the identities above and make a ledger mapping R1–R5/F1 to exact original evidence,
planned correction and pass predicate. Establish baseline 94 tests once in the pinned
source environment, or record a reproducible environment block. Never alter production
source to make the lab pass. Retain the four original seed observations.

### P1 — make the experiment fail when its claims are false (R2)

RED: demonstrate the original unsafe candidate policy returns zero with violations.
Demonstrate at least one wrong cut expectation/missing hook and a zero-CREATED or failed
child case that the old driver cannot certify. Use copied/synthetic fixtures only.
Repair all driver expectations as a batch: required cut reached marker, child exit,
JSON shape, exact case count, effect count, ordered checkpoint identity and final state.
Returning past a configured crash hook must fail distinctly. A missing result is failure.
For two-process receipt tests require two successful child exits, exactly
`[CREATED, REUSED_EXACT]` and one exact row. Assert negative controls were detected.
Use finally-based bounded cleanup for every owned helper, including timeout paths;
test a finite helper failure/timeout. Do not modify shared process utilities.

### P2 — reach both COMPLETE lost-ack boundaries (R1)

RED: reproduce both original C03 COMPLETE records as FOLD_CHECKPOINT_MISSING and show
the hooks were not entered. Repair prerequisites using actual ordered job-store writes
and truthful fold/lease observations. Assert planner stage and hook entry before
labeling the observation. Execute raise-before-COMPLETE-commit and commit-then-raise,
reopen each store and compare state/events/version. Include positive normal completion
and terminal repeat no-op. Count every effect before/after restart. Preserve the useful
fold-checkpoint lost-ack pair. Errors alone never establish commit or no-commit.

### P3 — bind each model claim to an observable transition (R3)

RED: reproduce the unsupported COMPLETE action escaping the checker, explicitly labeled
outside the old policy vocabulary. Reject unsupported actions. Model next effect count,
checkpoint knowledge and job state for the small bounded policy, or narrow the model's
claims and supply separate executable transition proofs for omitted obligations.
For each claimed invariant, include a named mutant and a deterministic violation trace:
duplicate UNKNOWN retry, stale-owner effect, fabricated checkpoint, contradictory
completion, terminal repeated effect and unjustified initial blocking. Candidate
violations or undetected mutants must make the top-level command nonzero. If ack does
not affect knowledge, document that equivalence instead of counting duplicate tuples
as extra assurance. State all exclusions and bounded liveness limits.

### P4 — distinguish operation identity, authority and effect truth (R4)

RED: same original authority prefix/payload with v8 and v9 creates two receipt rows.
Fix the synthetic contract so one operation retains its identity across a legitimate
checkpoint version advance; version/owner fence remains a separate admission input.
Prove same operation reuses one exact receipt, changed payload is refused, stale owner
cannot create a new effect, and a genuinely new authorized operation is distinguishable.
Define which identifiers make the same operation in this lab; do not choose WO205's API.

Preserve same-key two-process uniqueness with P1's strict predicates. Explain that the
existing receipt-row INSERT is the entire transactional effect. Add one small separate
file-effect/receipt cut to show why an intent or receipt in another transaction alone
does not prove atomicity. UNKNOWN remains recovery, never blanket permission to retry.
No design claim of general exactly-once execution, power-loss durability or cross-host
coordination. Production option A/B/C and migration decisions stay with WO205.

### P5 — honest lease and report corrections (R2, F1)

Retract false F1 without editing original seed. Retain F2 as a source-seam port contract
question. After the odd both-false outcome, feed truthful ACTIVE lease evidence against
the actual release checkpoint and record the refusal/contradiction. If using a synthetic
RELEASED fixture for a positive control, label it explicitly; do not present it as a
persisted release observation. Minimize the counterexample and separate actual source
behavior, fixture assumptions, candidate recommendations and parent decisions.

### P6 — portable replay bundle and final verification (R5)

Publish complete scripts in the exact bundle scope. Use explicit repository-root and
output-root arguments (or a documented launcher in lab_common.py); do not retain the
old HERE.parents assumption that changes when files move. All runtime imports must
resolve to the pinned checkout. README contains verbatim Windows and POSIX commands,
Python/dependency requirements, seed extraction, entrypoints, expected exits/summary,
and an honest OS verification matrix. No machine-specific absolute import paths.

Manifest: raw SHA-256 for each script/README, source Git blobs, original artifact hashes,
normalization rule, fixed seeds/timeouts, case identifiers and expected outcomes. Exclude
manifest itself from its hash list; candidate SHA belongs in the external result/comment
to avoid a self-referential commit hash. Existing baseline dependencies are sufficient.
No unapproved installation/global dependency mutation.

From a fresh owned export/checkout with no old ignored runs, replay every documented
entrypoint on native Windows using only tracked bundle + pinned source. Record source
provenance and clean input status. If native Mac is unavailable, leave MAC_REPLAY_PENDING
for Astra's exact-candidate verification; do not simulate an OS and claim native evidence.
Run corrected related lab programs and deterministic negative controls once after the
last relevant change. Repeat only for a failure or material evidence gap. Validate
source/test equality, allowed scope, UTF-8, links and git diff --check.

## Checkpoint, freeze, return

Append the WO checkpoint and update ignored `runs/WO-P1-208/glm-repair/checkpoint.json`
at completed programs, quota/blocker, or session rollover. Include current HEAD, owned
dirty files, immutable hashes, finished evidence, exact next action and forbidden scope.
Do not repeatedly rewrite global SSoT; Issue214/233 and the scoped WO supply its owner.

One final report must map each R1–R5/F1 to RED, correction, GREEN, command, outcome and
remaining limit. Include positive controls, model mutants, native OS evidence, parent
decision inputs and unresolved findings. Commit/push one frozen candidate, clean tracked
worktree, no force push. Publish exact candidate SHA and changed file list to Issue214
and Issue233; parent can read the result directly, no human copy-back required.

Write `runs/WO-P1-208/glm-repair/result.json` with STATUS, TASK, WORKTREE, BRANCH,
SOURCE_BASE_SHA, REVIEW_DELIVERY_SHA, CANDIDATE_SHA, INPUT_HASHES, CHANGED_SCOPE,
RED_EVIDENCE, GREEN_EVIDENCE, NATIVE_HOST_EVIDENCE, UNRESOLVED_FINDINGS,
KNOWN_LIMITATIONS, NEXT_SAFE_ACTION. Final status is COMPLETE_FOR_INDEPENDENT_REVIEW
only when all repair acceptance predicates are met on Windows; explicitly carry any
Mac replay dependency. It is never self-acceptance, Phase-D release or permission to merge.

Stop at unexplained dirty/ownership drift, unsafe replay, missing authority/artifacts,
quota/environment gate, or a second recurrence of the same unresolved repair failure.
Checkpoint the smallest reproducer and return for adjudication; do not create another
campaign/controller, alter immutable source or hop into another phase to stay busy.
