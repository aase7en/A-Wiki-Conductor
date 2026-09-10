# GLM-MARATHON-5H-WAVE3 — Runtime Binding First, Then Read-Only Continuation

Use this file as the execution pointer for a sustained GLM-5.3/ZCode session.

Do not ask the user to repeatedly type `continue`. Continue through every safe stage until a real stop condition is reached. Durable repository/issue evidence is authority; chat memory is not.

## 0. Universal startup — mandatory before mutation

1. Read `00-AGENT-ENTRY.md`.
2. Read `PROJECT-GRAPH.yaml` and select only task-relevant nodes.
3. Read `AGENTS.md`.
4. Verify actual repository/worktree/remote/current branch/HEAD/dirty+untracked state.
5. Read `CURRENT-WORK.md`, but treat its stale sections as subordinate to newer exact Git/Issue/PR evidence.
6. Read current claims/ownership from `COLLAB.md` plus current Issues/PRs.
7. Read `docs/agent-collab/FAST_EXECUTION_PROTOCOL.md`.
8. Read `docs/plans/2026-09-04-zero-relay-accelerator-roadmap.md`.
9. Read `DEFECT_LESSONS.md` before any `src/a_conductor/` mutation.
10. Read `docs/work-orders/WO-P1-176-zcode-runtime-model-binding.md` and `docs/work-orders/WO-P1-177-glm-marathon-wave3.md` from the exact task-packet ref supplied by the operator.
11. Re-read current Issue #213 and #233 evidence newer than this packet.
12. Inspect open PRs/branches/worktrees/claims for overlap.

If repo identity, dirty-state ownership, branch base, claim owner, or mutable scope is ambiguous: `SAFE_TO_MUTATE = NO`.

Bootstrap facts in this file are dated evidence only. Re-pin them before use.

## 1. Consume Wave 2; do not repeat it

Wave-2 final result is Issue #233 comment `5620813258`.

Treat these Wave-2 conclusions as hypotheses already independently supported unless current state changed:

- PR #246 / WO173 R5 was merged and post-main verified.
- current Wave-2 main was `1e2d193db2e7db7763d52cb337e9a3f130d0808e`.
- the critical Zero-Relay blocker became runtime provider/model materialization.
- ZRA-2 has primitives but lacks final composition and is ordered after honest runtime binding.
- ZRA-3 has reusable closeout/ready-set/scheduler/lease primitives but lacks one composition seam and is ordered after ZRA-2.
- ZRA-4 has reusable conflict/capacity/parallel/recovery primitives and is ordered after ZRA-3.
- AEET-0 corpus seed and security fixtures were shaped read-only.
- `CURRENT-WORK.md` was identified as stale and must not be claimlessly rewritten.

Do not rerun old broad archaeology merely to rediscover these findings. Re-check only changed state and facts needed for the current stage.

## 2. Critical finding to repair first

Read Issue #213 comment `5620725176` in full.

The independent GLM audit reproduced one root trust-boundary defect:

- A-Conductor authorized/hashed provider+model identity;
- `session/create` omitted the authorized model/provider;
- the installed ZCode app-server selected ambient machine-default provider state;
- with a synthetic canary credential, the child attempted the ambient endpoint instead of the authorized loopback endpoint;
- create-time model selection is supported but resolves against the provider catalog;
- therefore cosmetic model-ref injection alone is insufficient if ambient catalog dependence remains;
- actual selected session model/provider was not compared against durable authorized identity before prompt send.

Treat this as R3. P0/P1 classification belongs to the integrator, but implementation must close the demonstrated failure mode rather than only the narrower earlier hypothesis.

## 3. Stage A — claim WO176 correctly

Before editing source:

- re-pin `origin/main`;
- verify this task-packet branch exact SHA;
- inspect all open PR heads and current claims touching:
  - `zcode_protocol.py`
  - `zcode_supervised_helper.py`
  - `zcode_runner.py`
  - `zcode_production_assembly.py`
  - `owned_process.py`
  - directly related ZCode tests;
- verify no unexplained dirty work in the chosen isolated worktree;
- use a dedicated source branch/worktree; never edit another lane's worktree;
- record an explicit GLM implementation claim for WO176 before source mutation;
- if an earlier GPT-framing claim still appears active, do not silently steal it: reconcile/transfer it through the current coordination mechanism first.

The desired owner split is:

`GPT/integrator = architecture + authority + final acceptance/merge/release`

`GLM implementation lane = bounded WO176 RED-first implementation + deterministic/adversarial verification + candidate freeze`

Do not count this same GLM lane as the independent R3 reviewer later.

## 4. Stage B — RED first

Read the complete behavioral matrix in WO176. Produce the smallest failing tests that prove the present defect before production repair.

At minimum RED must prove:

1. current A-Conductor-shaped create can omit authorized model/provider;
2. conflicting ambient default can be selected instead;
3. prompt send is not gated on exact actual-vs-authorized model identity;
4. synthetic credential routing is not proven isolated to the authorized endpoint under ambient-default drift.

Prefer fake transport + loopback/synthetic-provider fixtures. Do not use a real provider credential.

Keep every canary obviously synthetic and scan final artifacts for it.

## 5. Stage C — implement the isolation-complete repair

Implement the smallest REUSE-shaped flow satisfying WO176.

Target behavior:

`canonical admitted provider snapshot/binding`
`-> bounded helper metadata (non-secret facts + credential ENV KEY NAME)`
`-> ephemeral authorized provider/model materialization in supported ZCode workspace/provider registry`
`-> session/create with exact authorized {providerId,modelId}`
`-> deterministic actual-session identity read-back`
`-> exact compare`
`-> session/send only on match`

Rules:

- reuse existing provider snapshot/model/endpoint/generation/secret-ref authority;
- actual credential value remains only in the explicit child environment;
- protocol/task/log/result metadata must never contain the credential value;
- one new explicit helper metadata env key may be added to the existing owned-process allowlist only if necessary and only for non-secret serialized runtime binding metadata;
- unknown env override keys must remain rejected;
- no ambient default fallback for an authorized execution;
- no new provider store/policy/model authority;
- no live ZCode config mutation;
- no new dependency unless absolutely unavoidable and separately justified.

If installed protocol behavior differs from this packet, stop source expansion, capture exact evidence, and request integrator adjudication. Do not invent protocol fields.

## 6. Stage D — adversarial batch

After basic GREEN, test the trust boundary as one batch.

Required adversarial cases:

- authorized provider/model A while ambient default is B;
- authorized endpoint loopback A while ambient endpoint B is externally addressable in test harness;
- missing provider id;
- missing model id;
- malformed serialized runtime metadata;
- unsupported provider/model;
- provider materialization rejected;
- session create ignores/changes requested model;
- read-back returns different provider/model;
- read-back unavailable/ambiguous;
- duplicate/restart path does not rebind to the wrong model;
- same packet with two authorized models remains distinct in durable execution identity;
- timeout/output budget remains bounded;
- result/log/redaction output contains zero synthetic secret canary;
- owned-process allowlist accepts only the one intended new metadata key, if added.

A test that merely checks a field was passed is not enough. At least one deterministic or loopback-shaped proof must demonstrate that conflicting ambient state cannot receive the synthetic secret canary.

## 7. Stage E — progressive verification and freeze

Run, in cost-first order:

1. targeted new RED/GREEN tests;
2. directly related protocol/helper/runner/assembly tests;
3. owned-process focused tests if changed;
4. relevant provider/admission/selection tests;
5. adversarial batch;
6. compile/static checks appropriate to changed Python files;
7. `git diff --check`;
8. strict UTF-8 check;
9. added-line secret scan;
10. bounded related regression;
11. broader suite only when R3 boundary coupling or repository policy requires it.

Then verify:

- exact changed-file set matches the claim;
- no secret/config/live DB artifact entered Git;
- no global SSoT hotspot changed without separate claim;
- branch is pushed;
- one exact candidate SHA is frozen.

Create the assurance packet requested by WO176 under ignored `runs/WO-P1-176/assurance/<sha>/`.

Publish a concise WO176 checkpoint to Issue #213 and pointer to Issue #233.

Stop mutable implementation with:

`STATUS=READY_FOR_INDEPENDENT_EXACT_SHA_R3_REVIEW`

Do not self-approve. Do not merge.

## 8. Stage F — switch to read-only continuation instead of waiting

Once WO176 candidate is frozen, immediately set:

`MUTATION_AUTHORITY=NONE_FOR_SUCCESSOR_STAGES`

Continue the following stages read-only while an independent lane reviews WO176.

Do not modify the frozen candidate during these stages. If you discover a blocking WO176 defect, report it against the frozen SHA and wait for the integrator to reopen/assign a repair slice.

## 9. Stage G — shape ZRA-COMP-1

Goal: create the smallest future test-only composition packet proving the already-existing production ZRA-1 pieces compose honestly after WO176 acceptance.

Read current source/tests and the Wave-2 Stage-2 evidence referenced by comment `5620813258`.

Shape, but do not implement unless a fresh work order/claim is separately granted:

- exact entry symbol to exercise;
- real-helper/fake-provider or loopback path to reuse;
- task/provider/model/base-HEAD identities to assert;
- zero production delta target;
- exact failure cases: wrong result identity, wrong provider/model, duplicate execution, timeout/ambiguous completion;
- acceptance that no human prompt/result relay occurs inside the composition proof.

Output one bounded packet proposal, not a new framework.

## 10. Stage H — reconcile ZRA-2 from changed state only

Read current Issue #214 and source at current main.

Do not trust its old baseline or old blocker wording if main has advanced.

Confirm or falsify Wave-2's composition claim:

`accepted exact AgentResultPacket`
`-> deterministic verify`
`-> A-Wiki review adapter / existing review authority`
`-> blocking findings`
`-> exactly one bounded repair task`
`-> replacement exact result`
`-> reverify/rereview`

Questions to answer:

- which exact production symbols already exist for each step?
- where is the single missing composition seam?
- what identity binds original result, review, repair request and replacement result?
- what prevents same-agent self-review being treated as independent?
- what prevents duplicate repair creation after restart/replay?
- what happens on UNKNOWN/ambiguous external-agent outcome?
- what is the smallest RED-first implementation packet after WO176/ZRA-1 acceptance?

No source mutation.

## 11. Stage I — reconcile ZRA-3 next-READY continuation

Read current Issue #215.

Revalidate existing primitives instead of inventing a scheduler:

- `CloseoutDecision` / closeout checkpoint identity;
- `compute_ready_set`;
- graph scheduler/dispatch coordinator;
- worker lease authority;
- duplicate execution/recovery semantics;
- natural terminal stop when READY frontier is empty.

Shape exactly one future composition seam:

`accepted closeout -> refresh READY set -> deterministic selection -> claim/lease -> dispatch next task`

Required fail-closed cases:

- dependency not satisfied;
- candidate/base/head drift;
- stale/unknown lease;
- ambiguous prior execution;
- duplicate continuation after restart;
- no READY nodes.

No second scheduler/lifecycle/state store.

## 12. Stage J — reconcile ZRA-4 bounded parallel/fan-in

Read current Issue #216.

Revalidate these existing authorities:

- write-set conflict detection;
- running write sets;
- provider admission/capacity;
- per-lane lease and runtime binding;
- bounded parallel executor;
- stale reservation reconciliation;
- per-task result identity and closeout;
- duplicate/replay protection.

Shape the smallest future 2–3 lane proof with:

- two independent READY tasks that may execute concurrently;
- one same-scope conflicting task that must not co-run;
- provider-capacity exhaustion case;
- one lane failure while another succeeds;
- fan-in only accepts exact task-bound results;
- restart cannot duplicate accepted work.

No new concurrency authority.

## 13. Stage K — AEET-0 evaluator seed

Consume Wave-2's corpus proposal instead of redesigning it.

Re-pin the real historical tests/evidence for:

Known good examples:
- deny-only projection behaves correctly;
- allowed empty `.claude` directory;
- junction-parent/reparse boundary remains inside trusted root when appropriate.

Known bad examples should include classes such as:
- `.claude` regular file instead of directory;
- duplicate/escaped JSON keys;
- oversized Windows quoting/settings payload;
- symlink/reparse escape;
- hostile parser payload;
- packet tamper after intake;
- restart replay of completed execution;
- mismatched VerificationEvidence identity.

Evaluator self-tests must prove the evaluator itself can fail:

- remove security dimension -> suite fails;
- invert known expectation -> suite fails;
- cheap/fast failed run never outscores accepted run;
- unredacted canary in a nominally green run -> security dimension fails.

Output an exact candidate file/symbol/test map for a future AEET-0 implementation WO. Do not implement without a separate claim.

## 14. Stage L — security fixture packets

Shape two tiny test-only future packets with positive twins:

### SEC-INJECT-1

Repository/tool/result content contains instruction-like escape text. The system must preserve fixed task authority, fixed allowed tool set, scope gates and prompt/task identity. Malicious content remains data, never mutation authority.

### SEC-EXFIL-1

A fake model/result returns a synthetic secret canary. Redaction/security dimension must fail or strip it according to existing policy, and the canary must not be promoted into task/review/memory evidence.

For both:

- reuse existing fake runner/loopback/fault-injection primitives;
- no network to real providers;
- no real secrets;
- include benign positive twins so a blocks-everything implementation cannot pass.

## 15. Stage M — changed-state SSoT drift only

Compare only facts that changed after Wave 2.

Check:

- `CURRENT-WORK.md` frontier wording vs actual merged/current frontier;
- `COLLAB.md` claims vs actual branch/PR/WO status;
- Issue #213 wording that may still imply merged ZRA-1 equals accepted live proof;
- Issues #214–#216 dependency wording after WO176 state changes;
- PR #248/Wave-2 status;
- new WO176/WO177 packet refs.

Do not edit shared hotspot files without a dedicated single-writer claim. Produce a fold candidate list ranked by duplication/priority-inversion risk.

## 16. Stage N — efficiency evidence

Measure only accepted-run/process evidence; do not reward failed cheap runs.

Capture where data exists:

- changed files/LOC/concepts introduced;
- new dependencies;
- targeted/adversarial test counts;
- candidate repair rounds;
- CI duration;
- independent-review defect yield;
- duplicate work avoided by consuming Wave-2 evidence;
- whether bounded adversarial probes found defects earlier than broad CI.

Do not turn LOC minimization into a safety objective. Correctness/security/recovery gates dominate efficiency.

## 17. Checkpoint cadence

Post durable checkpoints to Issue #233 only at meaningful stage boundaries, for example:

- WO176 claim + RED established;
- WO176 GREEN/adversarial candidate frozen;
- ZRA-COMP + ZRA-2/3/4 shaping complete;
- evaluator/security shaping complete;
- final Wave-3 result.

WO176-specific details should primarily go to Issue #213 / its Draft PR.

Every checkpoint must state:

`STAGE`
`STATUS`
`REPO/BRANCH/SHA`
`MUTATION_AUTHORITY`
`OWNED_SCOPE`
`EVIDENCE`
`FINDINGS`
`BLOCKERS`
`NEXT_SAFE_ACTION`

Do not post hidden reasoning or chain-of-thought.

## 18. Final Wave-3 result format

Publish one final comment titled:

`GLM-MARATHON-5H-WAVE3 RESULT`

Include exactly these sections:

1. exact repos/SHAs/PRs inspected;
2. WO176 implementation/frozen-candidate state;
3. deterministic + adversarial evidence;
4. unresolved findings by P0/P1/P2;
5. independent-review state for WO176;
6. ZRA-COMP-1 shaped packet;
7. ZRA-2/3/4 changed-state reconciliation;
8. AEET-0 / SEC-INJECT-1 / SEC-EXFIL-1 conclusions;
9. changed-state SSoT drift findings;
10. accepted-run efficiency findings;
11. at most five ranked future executable micro-WOs;
12. blockers requiring human/GPT authority;
13. exactly one `NEXT_SAFE_ACTION`.

The result must allow a new agent with zero chat history to resume safely.

## 19. Stop conditions

Stop only for:

- `HUMAN_DECISION_REQUIRED`
- `HUMAN_ACTION_REQUIRED`
- `AUTHORIZATION_REQUIRED`
- `SAFETY_BLOCK`
- `OWNERSHIP_CONFLICT`
- `NO_SAFE_NEXT_ACTION`
- or completion of the entire Wave-3 packet.

An independent-review wait is NOT a reason to sit idle; after freezing WO176, continue the explicitly read-only successor stages.

If a mutable dependency is not accepted yet, shape its next packet read-only and continue to the next independent read-only stage.
