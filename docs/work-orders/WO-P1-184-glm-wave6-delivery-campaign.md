# WO-P1-184 — GLM Wave 6 Autonomous Delivery Campaign

Status: `DOCS_PACKET_READY / TASK_TRANSPORT_ONLY / NO_PRODUCT_AUTHORITY`
Date: 2026-09-11
Owner: GPT-5.6 Sol integrator (architecture/acceptance/merge authority)
Execution candidate: GLM-5.3 MAX / ZCode
Repository: `aase7en/A-Wiki-Conductor`
Bootstrap base: `5f36fe0ae59b6b3d4aadfd5465e817761d59ff09`
Parent authority: `WO-P1-155` Zero-Relay Accelerator + Issues #213–#216 + Issue #233
Predecessor evidence: `GLM-MARATHON-WAVE5-320 RESULT` / Issue #233 comment `5626978376`

## 1. Purpose

Use one sustained ZCode `/goal` program to consume substantially more useful GLM capacity without turning token consumption into a goal by itself.

Wave 6 is a delivery-oriented successor to Wave 5:

- 8 programs;
- 8 goal families per program;
- 12 mandatory child steps per family;
- **64 families × 12 steps = 768 base goal units**;
- evidence-triggered recursive sub-goals may extend a family to depth 5;
- blocked mutable work yields to independent useful work instead of asking the user to type `continue`.

The campaign prefers accepted delivery, defect prevention, deterministic evidence and reusable implementation over prose volume.

## 2. Bootstrap live state — must be re-pinned at execution time

At packet authoring:

- `main = 5f36fe0ae59b6b3d4aadfd5465e817761d59ff09` after WO181 / PR #254 merge;
- WO181 frozen source candidate `ccb2346a14efcf59fef8e1f994d2d272fd089e94` received independent GLM ACCEPT P0=0/P1=0/P2=0 and exact-head CI SUCCESS before merge;
- post-main CI run `34543995776` is still in progress at packet bootstrap and remains a gate before a new real WO179 attempt;
- PR #255 / WO183 exists as a separate R1 duplicate-runtime-model-JSON hardening candidate at `efe2618e08f91152570410cc3a2f17ce9f98fa50`; its hosted CI is in progress at packet authoring;
- Wave 5 task-transport PR #253 is consumed and closed without merge;
- WO179 ZRA-1 live proof remains owner-gated; a new real-provider attempt is forbidden until WO181 post-main verification is successful and GPT/integrator records a fresh bounded live-attempt authorization;
- ZRA-2 -> ZRA-3 -> ZRA-4 remain dependency-gated behind accepted ZRA-1;
- A-Wiki remains a separate authority/repository and may not be mutated from this A-Conductor packet.

These are bootstrap facts only. Actual state always wins; re-pin before relying on any SHA, CI, PR, worktree or claim.

## 3. Role split

### GPT/integrator retains

- architecture and trust-boundary framing;
- cross-repo authority adjudication;
- R3 live-provider authorization;
- defect severity arbitration when evidence conflicts;
- final exact-SHA acceptance;
- merge/release/post-main authority.

### GLM/ZCode is encouraged to do heavily

- deep source archaeology;
- exact-SHA independent review when genuinely independent;
- adversarial challenge and deterministic probes;
- bounded low-risk/test-only implementation after a valid WO/claim gate;
- test generation and fault-injection fixture work;
- failure reproduction/root-cause isolation;
- compatibility/recovery/security analysis;
- work-order shaping for future R2/R3 slices;
- cross-session checkpointed long-horizon execution.

### Deterministic evidence remains completion authority

Tests, exact hashes, actual Git/PR/CI/runtime state and reproducible probes beat model confidence or a `DONE` statement.

## 4. Mutation authority

This Wave-6 packet itself grants **NO product/source mutation authority**.

Every tracked mutation requires:

1. live entry/graph/AGENTS/claim recovery;
2. exact repo/worktree/remote/branch/HEAD/dirty identity;
3. no overlapping active claim/PR implementation;
4. an active bounded WO for that chunk;
5. explicit mutable/forbidden scope;
6. risk classification;
7. `SAFE_TO_MUTATE = YES` for that exact chunk.

For new low-risk/test-only work with no existing WO, the repo's bounded docs-only governance bootstrap may create the WO/claim first. Re-run the full mutation gate immediately afterwards. This exception never grants broader source authority.

## 5. Explicit Wave-6 implementation slots

These slots are allowed to progress beyond shaping **only when their individual gate passes**. If any slot would require production-source change, shared hotspot mutation, live credential/provider action, or scope expansion beyond the slot, STOP that slot and checkpoint the evidence instead.

### I1 — PR #255 / WO183 independent review

Mode: `READ_ONLY_REVIEW_ONLY`.

If the GLM Wave-6 session did not author/mutate the candidate and PR #255 is still review-eligible:

- re-pin exact head;
- rerun focused deterministic tests as justified;
- challenge duplicate-key rejection at top-level and nested object depth;
- test benign unique JSON positive controls;
- verify no parser authority duplication;
- publish one exact-SHA verdict: `ACCEPT`, `CHANGES_REQUIRED`, or `REVIEW_BLOCKED`.

Do not mutate PR #255 in the independent-review role.

### I2 — ZCode bundle compatibility guard

Mode: `R2_TEST_ONLY_MAY_BOOTSTRAP`.

Goal: prove the installed/supported ZCode bundle/protocol schema used for real turns matches the assumptions required by the accepted runtime-model materialization path.

Before implementation, discover whether an equivalent guard/test already exists. REUSE it if so. Otherwise a new bounded WO may be bootstrapped for a test-only guard. Production source is forbidden in this slot.

Minimum evidence:

- exact bundle/version/hash observation where available without touching user config;
- fake/fixture protocol positive control;
- schema-drift negative that fails before a real turn;
- no live provider call;
- no user config mutation;
- cross-platform skip semantics explicit.

### I3 — PID reuse / creation-time fixture

Mode: `R2_TEST_ONLY_MAY_BOOTSTRAP`.

Goal: challenge child identity/recovery against same-PID/different-creation-time evidence and prove no unsafe attach/reuse.

Prefer existing process-truth/recovery test surfaces. Production source is forbidden unless a RED proves a material defect, in which case checkpoint and request a separate repair WO rather than expanding this slot.

### I4 — Review positive-control enforcement fixture

Mode: `R2_TEST_ONLY_MAY_BOOTSTRAP`.

Goal: prevent malformed adversarial probes from being counted as security wins merely because all useful work is blocked. A security/review fixture must pair attack rejection with a benign positive task that still succeeds.

Reuse existing review/loop/evaluator test surfaces. No new review lifecycle authority.

### I5 — AEET-0 evaluator seed

Mode: `READ_ONLY_SHAPE + NEW-FILE TEST/EVAL SEED MAY_BOOTSTRAP ONLY IF LIVE ROADMAP GATE ALLOWS`.

The evaluator must self-test against known-good and deliberately bad fixtures before its output can affect routing or policy. It may not become a scheduler, reviewer, policy authority or trace SSoT. If PR #244/WO171 or the current A-Wiki brain gate still blocks implementation, shape exact fixtures/acceptance only and continue elsewhere.

### I6 — Agent-security fake-first fixture seed

Mode: `R2_TEST_ONLY_MAY_BOOTSTRAP` only when no overlapping security/evaluator claim exists.

Initial classes: indirect repo/tool injection, secret-exfiltration attempt, authority escalation, malicious metadata, review spoofing, duplicate/replay ambiguity and denial-of-wallet/loop exhaustion. Every attack fixture needs a benign positive control. No real secrets or live provider calls.

## 6. R3 successor boundary

ZRA-2, ZRA-3 and ZRA-4 are R3 control-plane work. Wave 6 may perform deep archaeology, failure-model design, RED/test-plan shaping, exact symbol maps and docs-only WO bootstrap after dependencies are proven.

It may not silently mutate R3 production source merely because the previous node completed. A fresh source claim with the exact GPT-framed authority/failure model is required.

Required ordering remains:

`WO181 post-main verified -> WO179 ZRA-1 live proof accepted -> ZRA-2 -> ZRA-3 -> ZRA-4 -> later ODP/ZRA-5 expansion`.

## 7. No-real-provider rule

Wave 6 does not itself authorize a real CoinTH/ZCode provider call.

A real attempt requires a fresh durable GPT/integrator authorization naming:

- task/attempt identity;
- provider/model/endpoint authority references;
- credential reference only, never the value;
- replay rule;
- terminal/recovery reconciliation;
- maximum number of attempts.

Absent that record, use fake/loopback/synthetic evidence only.

## 8. Preemption policy

At every family boundary, re-check for a newly frozen high-value candidate.

Priority:

1. R3/R2 exact-SHA independent review needed to unblock the critical path and reviewer independence is genuine;
2. Zero-Relay dependency gate/evidence;
3. explicit Wave-6 implementation slots with valid claims;
4. failure reproduction/root-cause work;
5. security/recovery/evaluator evidence;
6. continuity/SSOT drift;
7. efficiency/hygiene.

After a preemption, resume the saved family/child pointer. Do not restart the whole Wave.

## 9. Recursive finding rule

Spawn `Fxx.R<n>` only when a falsifiable probe confirms a material new gap or a high-value untested hypothesis.

Each recursive goal must contain:

- parent family;
- exact evidence;
- severity/risk;
- existing owner/reuse candidate;
- positive control;
- RED/reproducer where applicable;
- bounded repair or next packet;
- deterministic verification;
- durable checkpoint;
- return pointer to the parent queue.

Maximum recursive depth: 5. Beyond that, consolidate into a separate WO instead of recursively expanding without bound.

## 10. Anti-token-waste rule

Large token budget is permission for deeper useful work, not permission to repeat.

Do not spend budget on:

- rereading unchanged files with no hypothesis;
- restating settled architecture;
- producing dozens of speculative WOs;
- cosmetic prose expansion;
- repeatedly rerunning broad test suites without a new reason;
- repeatedly polling a blocked CI/provider when independent work exists.

Spend budget on source tracing, counterexamples, reproducible probes, fixture generation, failure matrices, focused implementation, verification and high-quality checkpoints.

## 11. Cross-session continuity

Wave 6 is explicitly allowed to span multiple ZCode sessions.

Before context/usage limits approach, publish `STATUS=PARTIAL_LIMIT_CHECKPOINT` to Issue #233 containing:

- exact repo/main/branch/PR SHAs inspected;
- completed `Pxx/Fxx/A..L` nodes;
- active/preempted work;
- blocked nodes + owner/dependency;
- recursive findings;
- frozen candidates/review verdicts;
- created WO/claim IDs and exact scopes;
- next queue;
- exactly one `NEXT_SAFE_ACTION`.

The next GLM session resumes from the latest checkpoint. It must not redo completed nodes unless a material state change or explicit new falsification hypothesis justifies it.

## 12. Result contract

Final Issue #233 heading:

`## GLM-MARATHON-WAVE6-768 RESULT`

Include:

1. exact repos/SHAs/PRs/CI inspected;
2. start vs final frontier;
3. 64-family completion matrix;
4. count of completed base child units;
5. recursive findings and dispositions;
6. independent review verdicts;
7. implementation candidates created/frozen, with exact SHAs and ownership;
8. ZRA-1..5 maturity delta;
9. security/evaluator/recovery findings;
10. cross-platform compatibility findings;
11. continuity/SSOT drift findings;
12. efficiency/test-economy findings;
13. `REUSE/WRAP/EXTEND/BUILD/DROP` decisions;
14. blockers requiring GPT/human/external action;
15. max 15 ranked next micro-WOs/candidates;
16. explicit `DO_NOT_BUILD` list;
17. exactly one `NEXT_SAFE_ACTION`.

## 13. Stop conditions

Stop the whole campaign only for:

- `HUMAN_DECISION_REQUIRED` affecting all remaining useful work;
- `HUMAN_ACTION_REQUIRED` affecting all remaining useful work;
- `AUTHORIZATION_REQUIRED` affecting all remaining useful work;
- `SAFETY_BLOCK`;
- `OWNERSHIP_CONFLICT` that cannot be avoided by another independent family;
- `NO_SAFE_NEXT_ACTION`;
- practical session limit after a durable partial checkpoint.

A single blocked family is not a campaign stop.

## 14. Completion definition

Wave 6 is complete when all useful families are either `DONE`, `PROVEN_NO_GAP`, `FROZEN_FOR_REVIEW`, or `BLOCKED_WITH_OWNER`, all evidence-triggered recursive findings are resolved/owned, and one exact resume/action pointer exists.

The objective is not to consume a fixed number of tokens. The objective is to turn a large GLM budget into accepted engineering evidence and a deeper executable frontier with minimal human relay.
