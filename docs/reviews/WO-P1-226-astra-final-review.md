# WO226 independent exact-candidate review — CHANGES_REQUIRED

Reviewer: Poppy Javis / GPT Astra. Date: 2026-09-13.
Candidate: `78ec598b9830d802f54eb47642130693a038a39c`, PR #314.
Base: `251df211afc1ee5452f3652675d7a2f38c526876`.
Claim: [WO226-ASTRA-FINAL-REVIEW-001](https://github.com/aase7en/A-Wiki-Conductor/issues/214#issuecomment-5649387082).
This verdict supersedes neither Sol's acceptance authority nor the released WO.
It reviews the final repaired source, not the superseded 653d637 draft.

**3 P1 + 1 P2 remain. Do not accept this candidate.** The factory signature,
read-only recovery lookup, stale generation check, live-record timeout retention,
and missing-resource handoff guards have improved. Passing tests do not cover the
four counterexamples below.

| ID | Severity | Trigger and observed result | Required behavior |
|---|---|---|---|
| AF1 | P1 | Pause winning caller after lease/admission acquire, before runner factory returns. Concurrent identical dispatch sees EXECUTING + no runtime record; returns NOT_ATTEMPTED_CLEANED and changes both winner resources from ACTIVE to RELEASED. Winner resumes and reports EXECUTED. | Non-winner cannot infer crash/no effect from missing runtime record. Keep winner resources until canonical ownership/quiescence/terminal proof authorizes cleanup. |
| AF2 | P2 | Timeout leaves RUNNING + held resources; durable state later becomes FAILED. Replay returns EQUIVALENT_TERMINAL_NOT_USABLE before cleanup; admission and lease remain active. | Proven terminal failure performs exact cleanup once, without usable review handoff or relaunch. |
| AF3 | P1 | Inject one canonical terminal record with matching fingerprint but foreign worker during run. Backend returns EXECUTED with handoff worker a-worker-01 while stored record belongs to a-worker-99. | Apply complete identity classification after run, before cleanup/handoff; fingerprint/count/state alone are insufficient. |
| AF4 | P1 | Current task/profile/endpoint/generation agree, but task network_policy=DENIED for external first-party endpoint. Existing evaluate_provider_policy returns TASK_NETWORK_DENIED; bridge still calls runner and returns EXECUTED. | Consume canonical task provider policy/requirement before any resource/model effect; generation freshness alone does not authorize egress. |

## Source and proof detail

AF1: `src/a_conductor/zero_relay_review_execution.py:1325-1338` calls cleanup when
RECONCILE finds no record; `_cleanup_held_resources_without_record` at 1355-1397
reads exact keys and releases them without proving the original caller stopped.
The job CAS prevents duplicate launch, but does not authorize a loser to revoke
winner resources. The deterministic barrier uses a live winner thread, not a
simulated crash. It proves premature release; the model effect counter remains
one. The synthetic runner then accepts the stale acquired objects; no real model
or process is used. Real assembly also consumes the supplied resource evidence;
there is no live-owner proof in this cleanup branch. Do not claim a second model
launch was observed. Requiring schema/lock/lifecycle expansion invokes the existing
WO DESIGN_GAP stop; do not invent another ownership authority.

AF2: classification at lines 442-446 marks FAILED/PARTIAL/CANCELLED unusable.
Top-level lines 1223-1224 return before `reconcile_review_execution`, which itself
also returns immediately on RECOVERY_REQUIRED. The successful terminal path has a
cleanup path; failed terminal after timeout does not. The probe proves FAILED;
PARTIAL/CANCELLED share the branch by inspection, not separate experimental runs.
TTL expiry can bound retention; it does not satisfy exact terminal cleanup proof.

AF3: lines 882-899 replaced the post-run classifier with count/newness/state checks.
`worker_id` is not part of the fingerprint and the existing classifier correctly
rejects foreign workers before launch. Post-run now bypasses that invariant and
constructs worker identity from the plan instead of validating the record. This is
a fault-injection test at the supported runner/store seam; it does not claim the
normal real runner spontaneously changes its worker. Retain resources/recovery
truth for a foreign or ambiguous record; do not release based on that record.

AF4: lines 274-291 examine provider_security only for presence, compare generation
and endpoint, then compare requirement.provider_id only. The bridge never invokes
the canonical provider policy/authority decision. Compare the accepted authority
path in `parallel_ready_execution.py:818-838` and `provider_policy.py:103-169`.
The probe constructs a valid ParallelReadyTask with complete provider authority,
updates real SQLite config to the matching current generation, proves the existing
policy denies, then observes one synthetic effect. The `.invalid` URL is fixture
data; it is never contacted. The real default assembly has no task-security input,
so the fake does not bypass a downstream policy check that would save this case.
Reuse existing policy/requirement authorization; preserve readiness/quota and
store-authority bindings as required by the original WO, without a second engine.

## Reproduction and verification

From a worktree containing this evidence and candidate source:

```sh
python3 -m pytest -q -s docs/reviews/wo226-astra-final/test_adversarial.py
```

Expected on frozen 78ec598: **4 failed** assertion tests. These are deliberate RED
acceptance tests, not broken environment/import/setup tests. Assertions must turn
GREEN after bounded repair. See [test file](wo226-astra-final/test_adversarial.py)
and [captured output](wo226-astra-final/adversarial.log).

Independently run on macOS/Python 3.12:

- WO226 + production assembly + composition truth: **54 passed, 6 skipped**;
  skips are the platform-gated Windows real-helper tests. Command and output are
  recorded in `wo226-astra-final/baseline.txt`.
- GraphDispatch, JobExecution, provider execution authority, WorkerLease/recovery,
  ParallelReady, ZCode runner and authority-bound assembly: **220 passed**;
  see [regression log](wo226-astra-final/regression.log).
- Source and tests unchanged relative to candidate; source SHA256 manifest supplied.
- Full 2892 and hosted CI PASS are GLM's handback claims from Issue214 comment
  5648493827, not a full-battery rerun by Astra. They do not close these REDs.

No live provider, real process, secret read, source edit, merge or release occurred.
No semantic ACCEPTED/REJECTED parsing, universal sandbox claim, or new journal.

## Bounded handback

Sol: adjudicate AF1–AF4, fold accepted obligations into the existing WO226 packet,
and explicitly re-release the same GLM lane only after ownership is checked.
Prepared [repair supplement](wo226-astra-final/GLM-REPAIR.md) reuses the original
packet and freezes the four counterexamples. It is **HELD_FOR_SOL_RELEASE**, not an
automatic restart or authority to change schemas. The original GLM owner may repair
within its released source scope after that gate, then freeze a new exact SHA for
independent review. Do not advance WO223/C1, Phase D, or ZRA-3/4 on this verdict.
