# WO208 independent GLM lab review

Date: 2026-09-12. Reviewer: Poppy Javis / GPT-6 Astra / home macOS.
Claim: `WO208-ASTRA-LAB-REVIEW-001`.
Reviewed lab: `b3a553ca3bb51753daa84b5f6be0dc81f1d025d6` on
`codex/wo-p1-208-glm-closeout-lab`.
Verdict: **CHANGES_REQUIRED — LAB EVIDENCE**. This does not revoke Sol's
`ACCEPT_DESIGN_ONLY` of original design `b1d52d0c03100f0bfffd9a4adca0c6240f43ac2c`.
The lab is not yet accepted as WO205's Phase-D prerequisite. No production fix,
source release, merge, or live failure is asserted by this review.

## Disposition

The fold/checkpoint lost-acknowledgment pair is useful: the same caller-visible error
can follow either a committed or an uncommitted write. The original seed's four
composition-seam observations remain valid. The GLM process-cut results, stale gate,
and receipt-row concurrency experiment are useful bounded inputs, subject to the
oracle and replay repairs below. Preserve these results rather than repeat a broad audit.

Five P2 lab acceptance findings and one P3 report correction remain. P2 here describes
the evidence deliverable's acceptance impact, not production vulnerability severity.
The original source has no discovered production `GoalCloseoutExecutor` instantiation
at the pinned base; synthetic fixtures do not establish production reachability.

| ID | Finding | Required correction |
|---|---|---|
| R1 / P2 | C03 COMPLETE fault hooks are not reached | Establish truthful prerequisite checkpoints, prove hook entry, reopen both outcomes |
| R2 / P2 | Drivers can report failed expectations and return success | Enforce assertions, child exits/schema, hook reachability and negative controls |
| R3 / P2 | C07 claims exceed the modeled state transitions | Model observable transitions or narrow claims and supply missing executable proofs |
| R4 / P2 | C05 does not cover replay across changing job versions | Separate stable operation identity from version/fencing evidence; limit atomicity claim |
| R5 / P2 | Handback cannot be replayed from a clean checkout | Commit exact research scripts, manifest and commands within the repair scope |
| F1 / P3 | Claimed original seed hash typo is false | Retract F1; preserve the correct immutable seed |

## R1 — COMPLETE lost-ack experiment stops before transition

In `c03_c05_c06_suite.py`, `c03()` (line 111 onward) supplies `fold.completed=True`
but retains only the verification checkpoint from `make_store()`. Both variants
return `RECOVERY_REQUIRED / FOLD_CHECKPOINT_MISSING`; both reopened jobs remain
`REVIEW_PENDING`, with one checkpoint reference and zero fold calls. Neither
`CommitThenRaiseStore.transition` nor `RaiseBeforeCommitStore.transition` is exercised.

Independent targeted reruns on native Mac and Windows reproduced that result.
C02's after-COMPLETE-commit exit is a different experiment and does not establish
the before-commit versus commit-then-raise pair. Repair the fixture with real ordered
prerequisite writes and assert the selected plan/hook before attributing results to it.
Observe both the final job state and ordered journal after reopening; do not invent
expected exception types when the actual executor returns a bounded recovery result.

## R2 — a successful process exit does not certify the experiment

`c02_cut_matrix.py:55-66` records `exit_matches` without enforcing it; several
branches emit `UNEXPECTED`, but `main()` still returns zero (line 153).
`wo208_child.py` also has fallbacks after `execute_next` that use the same exit code
as the intended fault hook (for example lines 148, 158, 171 and 194). A hook that was
never entered can therefore appear to have reached its cut. Require a cut marker
written at the actual boundary and a distinct failure when execution returns past it.

`c03_c05_c06_suite.py` mostly records observations without enforcing the expected
outcomes. Its C05 two-process predicate `not(count(CREATED) == 2)` permits zero
CREATED results; validate both child exits, the exact outcome multiset and row count.
Own and bound both child lifetimes on all exits, including a first child's timeout.
This is confined to lab helpers, not WO202's production process-cleanup scope.

Independent Mac mutation control: replacing only the candidate assignment
`check_invariants(decide_conservative)` with `check_invariants(decide_unsafe)` in an
ignored copy of C07 produces **I1=8, I3=8, process exit=0**. A driver must fail if its
candidate violates the contract, and separately assert that each deliberately unsafe
negative control is detected. Expected negative controls are not candidate passes.

Also correct C06's evidentiary boundary: after the odd port returns both flags false,
the script injects a fixture claiming `LeaseEvidence(RELEASED)` before COMPLETE.
That is not evidence the lease changed. Preserve F2 as a port-contract question and
add a truthful ACTIVE-lease control against the release checkpoint; never describe
the injected RELEASED fixture as observed runtime truth or a production bypass.

## R3 — finite policy table is not a completion/journal transition proof

C07 enumerates 96 input tuples, but only `next_effect` is modeled. It does not model
next checkpoint or next job state; the acknowledgment axis is unused by the policy.
I2 primarily checks CONSUME/NOOP labels, I3 filters actions on divergent checkpoints,
and I5 checks two initial tuples. This supports a small decision-table check, not the
full stated no-fabrication, completion-safety or recovery-liveness claims.

Independent probe inserts action `COMPLETE` for
`(CURRENT, ATTEMPTED_UNKNOWN, LOST, ABSENT, NONTERMINAL)`; all reported invariant
counts remain zero. This action is outside the original policy vocabulary: the
counterexample demonstrates missing action validation and unmodeled completion,
**not** a production COMPLETE bypass or an execution of the original conservative policy.

For each retained invariant, define its observable state change and a mutant that
violates it and is rejected. Include stale-owner effects, fabricated checkpoint,
contradictory completion, terminal repeated effect and unjustified blocking. Explicitly
reject unknown actions. A small bounded transition model is sufficient; do not inflate
state counts or claim unbounded liveness/power-loss safety.

## R4 — receipt uniqueness has a narrower contract than crash-safe effects

C05 builds an identity containing `|v=8` (suite line 205). Independently applying the
same authority prefix and payload using `|v=8`, then `|v=9`, returns CREATED twice,
with two receipt rows. This is a lab key-namespace counterexample, not two observed
production effects. A job version can change during checkpoint/recovery while the
intended operation remains the same. An unchanged-key test alone cannot prove replay
suppression under that lifecycle.

Use a stable identity for the same authorized operation, distinct from changing
version/owner-fence evidence. Show exact replay across a checkpoint version advance,
divergent payload refusal, and stale authority rejection before any new effect.
Keep genuinely new operations distinct under an explicit synthetic contract.

The current destination's entire effect is an INSERT of an APPLIED receipt row.
SQLite uniqueness proves one such row for one exact key; it does not prove atomic
coupling with a separate file/fold/network effect. State this limit and demonstrate
the ambiguity with a small sacrificial separate-effect cut if making that comparison.
Neither a pre-effect intent nor a pre-effect version check alone closes the window
after authorization and before an external effect. WO205 retains the A/B/C choice;
this review does not select a new production store, API or migration.

## R5 — ignored scripts are unavailable to a cold-start reviewer

The tracked report has three pseudocode snippets, including `super().checkpoint(...)`,
and points to five ignored Windows scripts. It does not contain their full bytes,
content manifest or complete replay commands. A reviewer with only the candidate
checkout cannot recreate the evidence. Publish the named research bundle under
`docs/reviews/wo208-closeout-lab/` using the bounded repair packet. No CI discovery,
source integration or new tests under `tests/` are authorized.

## F1 correction and provenance

The original fenced probe's recorded and computed SHA-256 are both:
`bf1136e729cbe8676676031120a586610adeeb3dccca20addda6c1301a579aac`.
Verified independently from the original document on Mac and Windows. F1's alleged
`6a1301` transcription typo is falsified. The correct original seed must not be edited.

Frozen Windows raw artifact receipts (not Git blob IDs):

| File under `runs/WO-P1-208/glm/` | Bytes | Raw SHA-256 |
|---|---:|---|
| seed_probe.py | 5601 | d0f76a5a0e6214a33f9e3dfd389b58f58af6373b81c7e6370e06dc9c8ecd3fb3 |
| wo208_child.py | 16828 | f17bb11e4c07f0881c68ee2c0d7908749fb0b5a6ab7491cfe43e9d8dec04461c |
| c02_cut_matrix.py | 7086 | cc4cdb6fb5ad91769fd8928e1b14c90d32d8a057083eb8cadffe7d0b654ead9f |
| c03_c05_c06_suite.py | 15347 | 1bac4caa4ed01ffd5aa1f6eb75d55a72d67d4c9f5bc571b9a963e6a7d1c73f6d |
| c07_model.py | 6280 | 5394a9364630370f7587ecb10a89029746dab8a378f479418ea4b0a997934fbd |

Mac review copies were transferred as decoded text, normalized CRLF to LF, and gained
one trailing LF during patch creation. They are not raw-byte-identical copies. After
removing that transfer-added LF, normalized hashes matched the Windows decoded text:

| File | Normalized SHA-256 |
|---|---|
| wo208_child.py | 32881a48eea1fe5ef72415fc9f406dabd36fabed7afcdaf0a6ad27f565e2b8b0 |
| c02_cut_matrix.py | 62ea8d048485b15cba0b5be8bdd229573676a2fff9fe7ade08b09cecafd554d7 |
| c03_c05_c06_suite.py | 0451be89d05bedaed4a2b8942c2b3527a9d4e66cb691da618105e3244f130d47 |
| c07_model.py | 1ff3b56c99891a4d3d5d4f173be826d04015b7680ee14aea858e4dcfed8f39fa |

Local reviewer artifacts: `runs/WO-P1-208/review/adjudicate.py`, `adjudication.json`,
`key-version-proof.json`, and `windows/`. The decisive observations and exact mutation
recipes are recorded above so these ignored files are not the only durable findings.
For C03, import the frozen suite with pinned repository root and `src` on `sys.path`,
call only `c03()` using an owned `TemporaryDirectory(prefix="wo208-review-c03-")`, then
inspect its two COMPLETE records. For R4, use the frozen `ReceiptDestination` on a
sacrificial DB and call `apply` twice with the two version-suffixed keys and same payload.

## Verification boundary and handoff

Independent executions: targeted C03 on Mac and Windows, original seed hash checks on
both hosts, Mac C07 candidate/unsupported-action/unsafe-policy controls, and Mac C05
version-key probe. Full Windows C02 is source-inspected and GLM-reported here, not
independently rerun as a whole. The 94-test baseline is inherited GLM/seed evidence;
this docs-only review does not claim a new full baseline run. No power loss, cross-host
effect coordination, provider, real lease or production workspace mutation was tested.

Next: [same-WO bounded repair packet](../prompts/GLM-WO208-CLOSEOUT-REPAIR.md), one
eligible GLM session, then independent review of its exact pushed candidate. Do not
repair the frozen lab branch or activate WO205 source from this verdict. At refresh,
Issue214 records Phase-B post-main acceptance and separate WO216 C0 release; those
lanes and the current master remain owned by Sol/GLM. No preemption or controller edit.
Global CURRENT-WORK/handoff projection remains with its single writer, supplied by
this WO's scoped checkpoint and Issue214/233 delivery notice.
