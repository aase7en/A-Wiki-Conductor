# WO208 — GLM sustained evidence finalization

Task: WO208-GLM-CLOSEOUT-FINALIZATION-001, same WO208.
Status: PREPARED_NOT_STARTED / QUEUED_CAPACITY / EVIDENCE ONLY.
Executor: one eligible ZCode GLM-5.3 session. Reviewer: Astra on home Mac.
Parent: WO205 / Issue214; Sol retains architecture, source release, acceptance and merge.

## Goal and execution style

Close N1–N4 from the exact repair review and make the research bundle verify its own
identity, validators and bounded transition claims. The previous repair ended at
independent review; this packet authorizes one specific next pass requested by the user.
No production fix. Preserve successful R1/R4 evidence instead of restarting archaeology.

Use one supported ZCode /goal invocation with the ten subgoals below as a durable
checklist. Complete RED -> correction -> GREEN -> adversarial verification -> checkpoint
for one subgoal at a time. Nested goals mean logical subgoals in that same session,
not multiple concurrent sessions writing this worktree. No hidden agents or duplicate
goal dispatch. Native commands perform deterministic work; GLM handles the bounded
implementation/testing/reporting. Astra is needed only for a specific new design gap
or independent final adjudication.

Plan 10–16 useful hours, up to20 if unresolved counterexamples justify it. Finish early
when the predicates below are met. Duration, test count and tokens are not acceptance.
No sleep-to-fill-time, endless fuzzing, keepalive or quota bypass; actual limits apply.
Continue safe substeps without asking the human to type continue or relay results.

## Identity and owner gate

Repo: https://github.com/aase7en/A-Wiki-Conductor.git
Worktree: A:/GitHub/_worktrees/A-Wiki-Conductor-wo208-glm-finalization
Branch: codex/wo-p1-208-glm-finalization
Input candidate: 2482998e19ee439e04adf321cd5d74c1feb94243
Source base: 02d39cbd9bca1ab3bb19b6e0cfbb0766c991f971
Delivery: exact commit in the Issue214/233 handoff and user pointer; require it at first start.
Review: docs/reviews/WO-P1-208-astra-repair-review.md
WO: docs/work-orders/WO-P1-208-closeout-crash-contract.md
Result: runs/WO-P1-208/glm-finalization/result.json

Follow 00-AGENT-ENTRY/graph/AGENTS and routed policies; verify actual device/repo/remote,
branch/HEAD/dirty/claims, CURRENT-WORK, this WO, review and latest Issue214/233. Read
current WO205/master authority without switching or merging this source-pinned worktree.
Record immutable packet/review/design/seed hashes and the four source blobs in the
prior repair packet. Require zero source/test delta against source base. On resumes,
require explained owned history and unchanged immutable inputs rather than initial HEAD.

At preparation WO220 reviews the C0 repair; WO219/221/222 are separate Sol-owned work.
Do not duplicate those reviews or preempt a current goal. If capacity/ownership is
ambiguous, checkpoint BLOCKED_EXTERNAL_OWNER. A branch or absent process is not a lease.
Publish one receiving session's claim ID/branch/HEAD/scope to Issue214 before mutation,
append the claim to this WO, commit/push it. If a claim already exists, resume only as
its known owner or stop for adjudication; never use first file creation as authority.

## Exact mutable scope

On the finalization branch only:

- Correct docs/reviews/WO-P1-208-glm-closeout-lab.md with explicit supersession/provenance.
- Append checkpoints to docs/work-orders/WO-P1-208-closeout-crash-contract.md.
- Existing bundle files in docs/reviews/wo208-closeout-lab/: seed_probe.py,
  wo208_child.py, c02_cut_matrix.py, c03_c05_c06_suite.py, c07_model.py,
  lab_common.py, manifest.json, README.md.
- NEW, optional research-only replay_suite.py and test_lab_contract.py in that same
  bundle. These supply a single batch command and the validator/mutation test suite;
  do not scatter additional runners, stores or registries elsewhere.

Ignored: runs/WO-P1-208/glm-finalization/** and newly created recorded wo208- temp roots.
Outputs/bytecode stay outside the bundle; set PYTHONDONTWRITEBYTECODE=1 before Python.
Keep immutable: src/**, tests/**, .github/**, original seed/design and all Astra reviews
and packets, other docs/WOs/global SSoT, A-Wiki, private Drive, installed/runtime config,
all other worktrees and frozen candidate branches. No production implementation,
new controller/store/lease authority, credentials/provider calls, real fold/release,
deployment, merge, force-push, broad process kill or global dependency install.
No Worker project rebinding; Windows operations use explicit cwd. Own exact helper
handles/PIDs and commands; cleanup only helpers created by this experiment.

## Subgoal S0 — pin, recover and minimize (about 0.5–1h)

Read the tracked candidate bundle; no ignored Windows artifact recovery is needed now.
Record N1–N4 reproductions from the review, expected evidence and disposition of every
prior R1–R5. Baseline once: pytest -q tests/test_goal_closeout.py tests/test_job_store.py
(94 tests on the pinned source). Document environment failures separately. Reproduce
the manifest mismatch, substituted seed, malformed transition, escaped authority
mutants, disabled C02 validator and missing post-release reload before fixes.
Do not change production to match a mistaken lab expectation.

## S1 — executable identity and manifest gate (1–2h)

Bind the exact bytes executed by seed_probe to the verified canonical fence. Cover both
ignored-original and existing-output locations. Prefer executing the verified canonical
input in owned fresh storage; if reusing files, reject mismatch before import. Record
the hash of the actual executable bytes and the explicit normalization rule. A fake
run() returning the five expected numbers must never substitute for the seed experiment.
Include a harmless sentinel to prove rejected mismatched code was never executed.

Add a fail-closed preflight checking every listed bundle hash and source blob against
the selected checkout before any experiment. A missing/changed script, unexpected
manifest omission, or wrong source pin must fail. Exclude the manifest from its own
hashes and record final candidate SHA externally. This gate is for the lab only.
No public security claim that a self-authored manifest authenticates an attacker-controlled
checkout; the trust root is the independently pinned candidate SHA.

## S2 — repair closed transition semantics (1–2h)

Use a fixed state shape. Every supported transition returns a valid state and an exact
new-effect count. First execution adds one effect; non-effect actions add zero; duplicate
effects must be observable. Preserve job state instead of dropping its axis. Invalid
action/state tuples fail explicitly. Validate next_state rather than discard it.
RED-first cases: the review's three-element result, first-effect zero count and failure
when feeding one step's output into the next. Keep the model bounded and explicit.

## S3 — authority and bounded traces (2–3h)

Prove execution and completion require the model's current authorization and eligible
job state. Reject blocked-job EXECUTE_ONCE and stale-owner COMPLETE counterexamples.
Distinguish legal COMPLETE from unsupported COMPLETE_UNMODELED. Use traces of 2–4 steps
to exercise effects, knowledge reconciliation, checkpoint and completion; enumerate a
small documented reachable state space. Retain counterexample traces in summaries.
Do not add arbitrary state axes to inflate assurance. Identify synthetic oracle
assumptions versus actual executor behavior. Any proposed production contract change
goes to WO205 as DESIGN_DECISION_REQUIRED, not into src.

Availability checks must prove exactly what is claimed. If completion progress is
outside the chosen policy, say so and point to the real-store C03 positive proof;
do not claim full lifecycle liveness from the initial execute decision. Each safety
predicate needs a mutant that crosses its boundary and is detected for that reason.

## S4 — validate the validators through their real entrypoints (1–2h)

Extract only the minimal shared C02 observation validation so positive and malformed
observations use the same path. Negative controls must invoke that validator and assert
rejection; include process-level nonzero exit evidence. Merely asserting code!=99 or
marker absence is not proof the experiment would fail. Preserve all positive cuts.

Mutation batch: disable exit, marker, effect count, checkpoint identity/count, job state
and child cardinality checks one at a time in ignored copies; deliberately bad inputs
must make the contract suite fail. Catch the review's combined wrong-exit99 + disabled
predicate mutant. Missing result, unexpected schema, non-boolean/missing expected
fields and zero-created receipt race must not silently become success. Reject unknown
cases or missing required cases when aggregating. Keep observation data (which may
legitimately contain false) separate from acceptance predicates. Do not introduce a
generic validation framework beyond this small research bundle.

## S5 — real bounded helper failure/timeout (1–1.5h)

Use a finite owned helper that remains alive past a short test timeout and a bounded
sibling helper; verify timeout yields nonzero and both owned processes are reaped on
every exit. Invalid argparse mode is a separate control, not a timeout proof. Exercise
early first-child failure and missing-output cases. Validate exact identity of any
helper you terminate. No live Worker, ZCode, Python service or unrelated PID operation.
Record limits; direct-child cleanup does not imply arbitrary process-tree containment.

## S6 — lease truth and exact journal reload (0.5–1h)

After the odd both-false port response, assert the actual release checkpoint is present.
Reopen the store; reload state/version/refs; retain truthful ACTIVE lease evidence;
execute again. Require RECOVERY_REQUIRED / LEASE_RELEASE_CONTRADICTION, total release
calls one, and REVIEW_PENDING. The report must agree with observed booleans. Rename
called/released indicators accurately. Keep the explicitly synthetic RELEASED positive
control distinct; do not fabricate refs and label them observed. F2 remains a limited
port-contract question, not a production COMPLETE bypass.

## S7 — differential and metamorphic batch (1–2h)

After repairs, batch meaningful variations: ordering/permutation of independent cases,
fresh output directories, source-root relocation including spaces, missing/corrupt
summary, identical replay key across version advances, divergent payload, and each
documented unsafe policy mutant. Compare typed outcome/identity/effect/journal facts,
not timing or path strings. Reuse existing valid C03/R4 controls; no new broad audit.
Use fixed deterministic inputs/barriers; any randomized extension must have a fixed
seed and finite bound with a minimized retained failure. A failure must never be
hidden by a final unconditional zero exit or a top-level expected=true field.

## S8 — portable cold-start batch and evidence ledger (1–2h)

Provide one documented batch command (optional replay_suite.py) using explicit
--repo-root/--output-root. It must run manifest preflight, contract/negative controls
and all lab entrypoints, preserve each exit, and produce one bounded summary. Existing
documented entrypoints remain usable. README gives literal Windows and POSIX examples,
required environment, fresh output policy and exact expected observations. Existing
output directories must be handled explicitly without deleting unexplained evidence.

From a fresh owned export of the candidate with no prior ignored runs, execute the
batch on native Windows and verify it can run using tracked contents only. Regenerate
manifest after final edits; replay that exact bundle and ensure no generated tracked
changes. Archive the commands/exits/summary and normalized platform facts. Native Mac
remains pending for Astra when unavailable; never label simulation as native replay.
No need to copy raw logs to the user; reports and result paths are directly readable.

## S9 — adversarial freeze and handback (0.5–1h)

Map every N1–N4 and S0–S8 item to RED, correction, GREEN, negative control, artifact and
limit. Avoid prose assertions contradicted by JSON. Validate that all script hashes,
source pins, manifest cases, README counts and actual emitted cases agree. One final
focused/related regression batch after the last relevant change; broaden only for a
specific failure. Preserve successful seed/C03/receipt facts and the original reports'
provenance. Compile, diff/UTF8/link/scope checks; all src/tests unchanged.

Freeze one exact clean candidate, commit/push without force, publish changed paths,
candidate SHA, branch and report/result pointer to Issue214/233, then STOP for independent
review. Do not merge or advance to C1/D/ZRA3. This packet closes the evidence pass only;
it does not assert whole-roadmap completion or parent design acceptance.

## Checkpoint and stop rules

At each subgoal completion, material finding or context pressure: append a compact WO
checkpoint and update runs/WO-P1-208/glm-finalization/checkpoint.json. Include current
SHA, owned dirty paths, immutable hashes, completed subgoals, next command, blocker and
forbidden scope. Resume from that checkpoint in the same owned lane. No new private
controller/handoff files outside the assigned surface; global SSoT is integrator-owned.

Result JSON must contain STATUS, TASK, WORKTREE, BRANCH, INPUT_CANDIDATE_SHA,
REVIEW_DELIVERY_SHA, CANDIDATE_SHA, INPUT_HASHES, CHANGED_SCOPE, FINDING_DISPOSITIONS,
RED_EVIDENCE, GREEN_EVIDENCE, MUTANT_RESULTS, NATIVE_HOST_EVIDENCE, KNOWN_LIMITATIONS,
UNRESOLVED_FINDINGS and NEXT_SAFE_ACTION. Status COMPLETE_FOR_INDEPENDENT_REVIEW only
when all required predicates pass; carry MAC_REPLAY_PENDING explicitly when applicable.

Stop for unknown ownership, unexplained bytes, unsafe process/storage action, missing
authority, quota/environment gate, new production design dependency, or two consecutive
failed attempts at the same minimized hypothesis. Preserve the reproducer; no third
blind repair/research wave. The independent review decides any next action. Hours of
available compute never authorize crossing a gate or taking another owner's work.
