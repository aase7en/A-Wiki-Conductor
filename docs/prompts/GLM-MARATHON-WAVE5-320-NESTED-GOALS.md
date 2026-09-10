# GLM-MARATHON-WAVE5-320-NESTED-GOALS

Status: LONG-HORIZON EXECUTION PACKET / RESUMABLE / GOAL-TREE
Parent WO: `WO-P1-182-glm-wave5-320-goals`
Primary repo: `A:\GitHub\A-Wiki-Conductor`
Cross-repo read-only target when selected: `A:\GitHub\A-Wiki`
Default durable result surface: A-Wiki-Conductor Issue #233
Zero-Relay task surfaces: Issues #213, #214, #215, #216

---

## MASTER `/goal`

Execute the largest useful evidence-backed engineering program that can be completed safely from the current A-Sunday Conductor frontier.

Create and maintain nested ZCode `/goal` work under this MASTER goal. Do not stop after one task. Do not ask the human to type `continue` between safe stages.

This packet defines:

- 32 Level-1 goal families `F00..F31`;
- ten standard child goals `A..J` for every family;
- therefore **320 base goal units**;
- optional bounded recursive finding goals `<Fxx>.R<n>` to depth 4;
- preemption for newly frozen exact-SHA review candidates;
- cross-session resume without rerunning completed work.

The purpose is to use GLM/ZCode long-context capacity heavily on useful work, not to consume tokens for their own sake.

### MASTER success condition

Produce durable evidence that advances the project, closes real gaps, disproves false gaps, prepares owner-correct implementation packets, or independently verifies exact candidates. Leave the repository easier to resume and safer than at start.

### MASTER failure condition

Do not count repeated summaries, repeated unchanged grep, speculative architecture, hidden reasoning, self-review of authored candidates, claimless mutation, or duplicate control-plane designs as progress.

---

# 0. Mandatory startup

Before opening child goals:

1. Read `00-AGENT-ENTRY.md`.
2. Read `PROJECT-GRAPH.yaml`.
3. Read `AGENTS.md`.
4. Verify actual repo/worktree/remote/branch/HEAD/dirty/untracked state.
5. Re-pin `origin/main`.
6. Inspect open PRs/Issues/branches/current claims and any active local worktrees visible to your lane.
7. Read `CURRENT-WORK.md`, but explicitly reconcile it against actual state because Wave 4 already proved it stale.
8. Read `docs/agent-collab/FAST_EXECUTION_PROTOCOL.md`.
9. Read `docs/agent-collab/CAPABILITY_MATRIX.md`.
10. Read `docs/plans/2026-09-04-zero-relay-accelerator-roadmap.md`.
11. Read Issue #233 latest comments.
12. Read Issue #213 latest comments before ZRA-1 work.
13. Read Issues #214/#215/#216 before ZRA-2/3/4 work.
14. For any `src/a_conductor/**` mutation, read `DEFECT_LESSONS.md` first.
15. If A-Wiki becomes relevant, read A-Wiki `BRAIN-ENTRY.md -> PROJECT-GRAPH.yaml -> COLLAB.md`, then only the selected protocol nodes.

Record a START checkpoint with exact SHAs and active ownership.

---

# 1. Global authority rules

These rules bind every nested goal.

1. Durable repo/runtime evidence > agent claim.
2. Chat history is not authority.
3. Prompt file is task transport, not mutation authority.
4. `REUSE -> WRAP -> EXTEND -> BUILD`.
5. No duplicate scheduler, job store, TaskGraph, claim/lease authority, review lifecycle, provider/model policy store, retry/recovery authority, trace authority, or memory authority.
6. Unknown dirty/ownership state means `SAFE_TO_MUTATE=NO`.
7. Existing active local/remote claim wins; never steal it.
8. Frozen candidate author cannot be its required independent reviewer.
9. Exact-SHA review means immutable exact SHA, not moving worktree.
10. R3 means fail closed on ambiguity.
11. Real credential values are never printed, copied, hashed into public evidence, committed or pasted.
12. Synthetic credentials are preferred for adversarial provider probes.
13. No broad ZCode state scan while ZCode is running.
14. No broad process kill. Exact PID + command identity only when explicitly authorized.
15. A failed tool/tunnel/provider transport is not automatically a code defect.
16. A blocked child yields to another safe child; it does not stop MASTER.
17. A finding is not a defect until source/runtime evidence proves it.
18. Positive controls are required for security tests so a block-everything implementation cannot pass.
19. Efficiency is measured only on accepted outcomes.
20. Do not remove tests/security/privacy/auth/recovery gates merely to improve speed.

---

# 2. Standard ten-child protocol — run for EVERY family

For every `Fxx`, create nested children in this logical order. Parallelize read-only children only where independence is clear.

## `<Fxx>.A RECOVER`

- re-pin relevant repo/ref/SHA;
- identify dependency state;
- identify task/WO/claim owner;
- identify active worktree/branch/PR if any;
- classify `READ_ONLY`, `MUTATION_ELIGIBLE`, `REVIEW_ELIGIBLE`, or `BLOCKED`.

## `<Fxx>.B REUSE-MAP`

- enumerate exact existing owner primitives;
- cite path/symbol/test/Issue/PR evidence;
- classify each proposed component `REUSE`, `WRAP`, `EXTEND`, `BUILD`, `DROP`;
- explicitly prove absence before `BUILD`.

## `<Fxx>.C TRACE`

- trace call path/data path/state path end-to-end;
- find all boundary conversions and authority handoffs;
- note dead/unreachable/preview-only paths separately from production paths;
- identify version/platform-dependent seams.

## `<Fxx>.D EVIDENCE-MAP`

Create a compact matrix:

`claim | evidence | exact SHA/version | status PROVEN/UNPROVEN/STALE/CONTRADICTED | owner`

Do not convert docs statements into runtime proof.

## `<Fxx>.E FALSIFY`

Attempt at least three meaningful counterexamples when the family has a behavioral/security claim.

Examples:
- wrong provider/model;
- stale generation/head/lease;
- duplicate/replay;
- timeout/ambiguous result;
- malformed input;
- Windows/POSIX semantic divergence;
- positive allowed case beside blocked case.

## `<Fxx>.F PROBE`

Run deterministic safe probes when possible.

Preference:
1. pure unit/reproducer;
2. disposable DB/worktree;
3. fake child/provider;
4. loopback synthetic provider;
5. installed runtime with synthetic credential;
6. real provider only under explicit task-specific live authorization.

Record observable evidence only. Never record hidden chain-of-thought.

## `<Fxx>.G DELIVER`

If a live WO+claim gives mutation authority:

`RED -> minimum repair/implementation -> targeted GREEN -> related regression -> adversarial batch -> freeze SHA`.

If no mutation authority:

- do not mutate;
- shape the smallest future WO packet;
- include exact owner, scope ceiling, acceptance, dependencies and stop conditions.

## `<Fxx>.H VERIFY`

Verify proportionally to risk:

- exact scope/diff;
- targeted tests;
- related tests;
- positive/negative controls;
- secret/path/identity checks;
- cross-platform/host evidence where relevant;
- hosted CI only when a frozen candidate exists and policy requires it.

Distinguish author verification from independent review.

## `<Fxx>.I CHECKPOINT`

Persist a durable concise checkpoint to the existing Issue/PR/WO surface:

```text
WAVE=GLM-WAVE5-320
FAMILY=Fxx
STATUS=
REPO/REF/SHA=
MODE=
OWNER/CLAIM=
PROVEN=
FALSIFIED=
FINDINGS=
BLOCKERS=
DEPENDENCIES=
NEXT_QUEUE=
```

Do not create a parallel SSoT.

## `<Fxx>.J ROUTE`

Choose one:

- `DONE_PROVEN`
- `DONE_NO_GAP`
- `BLOCKED_WITH_OWNER`
- `DEFERRED_BY_AUTHORITY`
- `PREEMPT_TO_EXACT_SHA_REVIEW`
- `SPAWN_RECURSIVE_FINDING`

Then continue automatically to the highest-value eligible family. Do not ask the human to continue.

---

# 3. Recursive finding protocol

When a family proves a new material finding, spawn `<Fxx>.R<n>`.

Each recursive finding runs:

1. reproduce independently;
2. root-cause to exact seam;
3. severity `P0/P1/P2/P3` or non-defect;
4. existing-owner/WO search;
5. duplicate-authority check;
6. minimum prevention level: test/assertion/helper/contract/runtime guard;
7. mutation gate;
8. repair only when authorized;
9. freeze/review separation;
10. durable checkpoint and return to parent.

Maximum automatic depth = 4. This bounds speculative recursion; it does not limit the number of separately proven findings.

---

# 4. Preemption protocol

At any time, if a high-priority R2/R3 exact candidate becomes frozen and this GLM session did NOT author it:

1. checkpoint current child;
2. re-pin candidate/base/PR/CI/assurance identity;
3. preempt into independent exact-SHA review;
4. use adversarial probes, not only test reruns;
5. publish verdict;
6. do not merge unless separately assigned;
7. return automatically to the saved Wave-5 queue.

If this GLM session authored the candidate, it may not satisfy the independent-review requirement. Freeze it and continue another family.

---

# 5. Goal families F00..F31

Every family below runs children A..J.

## F00 — Global actual-state and ownership reconstruction

Goal: establish a cold-start truthful operating picture before any other conclusion.

Must cover:
- A-Conductor main/branches/open PRs/issues/claims/worktrees/processes visible to lane;
- A-Wiki main/claims only where cross-repo decisions require it;
- stale `CURRENT-WORK.md` versus actual state;
- active WO181/WO179 ownership;
- Wave-4 result and consumed PR #252 status.

Exit: one dependency graph with exact current refs and no unresolved ownership ambiguity for read-only Wave work.

## F01 — Wave-4 result reconciliation and no-repeat filter

Goal: classify every G0..G15 result from Wave 4 as `CLOSED`, `CARRY`, `SUPERSEDED`, or `NEEDS_FALSIFICATION`.

Do not rerun a Wave-4 conclusion unless:
- code/state changed materially;
- previous evidence was incomplete;
- a new counterexample exists.

Exit: explicit skip list preventing token waste.

## F02 — WO181 Windows child-environment critical-path watch/review

Goal: handle WO181 without stealing its active GPT/Sol source lane.

If WO181 is moving/unpublished:
- READ_ONLY only;
- map Windows explicit-environment DNS dependency;
- design adversarial env-minimization tests;
- identify positive controls and platform behavior.

If WO181 becomes frozen and this GLM session is independent:
- preempt and conduct exact-SHA R3 review;
- challenge `SYSTEMROOT`, DNS, TLS/cert, temp/profile, PATH assumptions;
- verify only the minimum non-secret inherited environment is allowed;
- prove no broad environment inheritance/secret leakage.

Exit: review verdict or owner-correct blocker checkpoint.

## F03 — WO179 Attempt-1/Attempt-2 recovery truth

Goal: ensure the live-proof failure cannot leave stale `RUNNING`, orphan processes, ambiguous retry or duplicate execution.

Trace/reuse:
- SQLiteJobStore;
- ExecutionTransportService;
- RecoveryReconciliationService;
- StrictRecoveryRepositoryObserver;
- provider admission;
- WorkerLease;
- durable execution store/dedup.

Attempt-1 is historical and must never be replayed blindly.

Exit: exact recovery state and retry preconditions for the next distinct live identity.

## F04 — ZRA-1 live authorized proof readiness

Goal: prove every prerequisite for one harmless real provider turn after WO181/post-main gate.

Checklist:
- canonical provider route current and authorized;
- exact runtime/provider/model materialization from WO176;
- post-WO181 Windows behavior verified;
- provider admission + WorkerLease + durable execution + recovery composed;
- one new identity only;
- success marker/result destination bound;
- no ambient fallback;
- no secret in artifacts;
- no retry on ambiguity.

No real provider call without task-specific owner authorization.

Exit: READY_FOR_OWNER_LIVE_PROOF or precise blocker.

## F05 — ZRA-1 independent result adjudication

Goal: when a new live proof result exists, independently classify it.

Positive acceptance requires:
- authorized provider/model endpoint actually used;
- exact task/result identity;
- expected harmless marker/result;
- durable terminal execution state;
- job terminal state;
- lease/admission released;
- no orphan child/supervisor;
- no secret leakage;
- replay identity would not duplicate.

Failure must be classified provider/runtime/transport/code/authorization/recovery without guesswork.

Exit: ACCEPT / CHANGES_REQUIRED / BLOCKED_EXTERNAL / RECOVERY_REQUIRED.

## F06 — ZRA-2 automatic result -> verify -> review -> bounded repair

Goal: close Issue #214 using existing authorities only.

Map existing pieces:
- AgentResultPacket / AgentChangeApplier;
- A-Wiki ReviewBus via adapter;
- AHA-5 review/repair bridge;
- repair task builder;
- durable task/result identity;
- lease/admission/recovery.

Prove one forced blocking review creates exactly one bounded repair task and one replacement result, never a new review/task authority.

If implementation gate not open, shape exact smallest composition WO.

Exit: production gap proven or no-gap proof.

## F07 — ZRA-2 adversarial failure matrix

Goal: attack the ZRA-2 loop before/after implementation.

Minimum cases:
- duplicate review result;
- stale candidate SHA;
- wrong task/result provider/model identity;
- repair scope expansion;
- same-agent review masquerading as independent;
- repair result arrives after supersession;
- timeout before outcome known;
- review transport duplicate;
- repair task duplicate;
- reviewer says PASS while deterministic verify fails.

Exit: executable matrix + positive controls.

## F08 — ZRA-3 NEXT READY continuation composition

Goal: close Issue #215 without creating another scheduler.

Reuse:
- GoalCloseout / CloseoutDecision;
- compute_ready_set;
- existing scheduler;
- GraphDispatchCoordinator;
- WorkerLeaseBroker;
- dedup/recovery.

Prove accepted completion advances exactly once to deterministic next READY task and natural empty frontier stops cleanly.

Exit: thinnest composition seam + E2E proof plan or implementation if separately claimed.

## F09 — ZRA-4 bounded parallel/fan-in composition

Goal: close Issue #216 using existing concurrency authorities.

Challenge:
- same-write-set conflict;
- max provider concurrency;
- lease collisions;
- one child fail, siblings succeed;
- stale/replaced worker;
- duplicate result;
- cancel/supersede;
- restart recovery;
- deterministic fan-in completion.

No new concurrency scheduler.

Exit: 2–3 lane proof shape and acceptance matrix.

## F10 — ZRA-5 ODP routing seam readiness

Goal: prove what remains before ODP can select Zero-Relay as an accepted capability route.

Separate:
- A-Wiki high-level policy/planning authority;
- A-Conductor runtime capability/eligibility/selection;
- mailbox fallback;
- provider readiness/admission;
- accepted Zero-Relay route.

Do not implement broad ODP ahead of ZRA-4 unless dependency graph permits a read-only preparation slice.

Exit: exact prerequisite list, no duplicate router.

## F11 — AEET-0 evaluator corpus implementation readiness

Goal: turn real defect history into project-native evaluator fixtures.

Start from Wave-2/3 corpus evidence:
- known-good positives;
- known-bad settings/path/parser/identity/replay cases;
- evaluator-bites self-tests ES-1..ES-4.

Prove evaluator itself can fail when security dimension is removed or expectations are inverted.

No external framework dependency until native corpus mechanics are proven insufficient.

Exit: smallest owner-correct evaluator WO.

## F12 — Security injection fixture pack

Goal: shape/implement `SEC-INJECT` only under a dedicated claim.

Attacks:
- repo file contains instruction to escape scope;
- tool output contains instruction to mutate forbidden path;
- review content claims authority;
- result payload requests broader permissions;
- malicious markdown/code block tries to alter task contract.

Assertions:
- fixed task packet unchanged;
- tool set/authority unchanged;
- no transitive privilege;
- positive benign-content twin succeeds.

Exit: executable test-only packet or verified coverage reuse.

## F13 — Secret/exfiltration fixture pack

Goal: prove secrets cannot transit task/result/protocol/log surfaces.

Use synthetic token markers only.

Attack surfaces:
- model returns secret-like value;
- child stderr/stdout;
- protocol receipt;
- result packet;
- review packet;
- trace/event telemetry;
- retry/recovery diagnostics;
- crash traceback.

Positive control must allow non-secret metadata required for debugging.

Exit: coverage map + smallest missing fixtures.

## F14 — WO176 duplicate-key decoder hardening advisory

Goal: independently verify Wave-4 P3 duplicate-key finding and classify whether it deserves an R1 hardening WO.

Probe nested/top-level duplicate JSON keys and semantic aliases.

Reuse existing unique-object parsing pattern if repair becomes authorized.

Do not relabel the already accepted WO176 as failed unless a production exploit path is proven.

Exit: DROP / R1_HARDENING_READY / ESCALATE with evidence.

## F15 — WO176 delivery-key parameterization advisory

Goal: investigate hardcoded credential env-key assumptions versus authorized runtime metadata.

Prove whether mismatch:
- fails closed;
- misroutes credential;
- only affects future provider kinds;
- is unreachable under current canonical assembly.

No new secret-delivery authority.

Exit: exact compatibility boundary and smallest future fix if needed.

## F16 — ZCode bundle/version compatibility guard

Goal: ensure accepted runtime materialization does not silently drift on ZCode upgrade.

Map:
- installed bundle version/hash evidence;
- session/create model/runtimeModel schema;
- generatedAt/version semantics;
- attestation response shape;
- capability differences by bundle version.

Design a deterministic compatibility probe that gates live turns and fails closed on unsupported schema.

Do not pin forever to one hash if a schema/capability test can prove compatibility more robustly.

Exit: compatibility guard proposal/test packet.

## F17 — Windows child environment minimality matrix

Goal: determine the minimum explicit environment required for installed ZCode child correctness without inheriting unrelated user secrets/state.

Dimensions:
- SYSTEMROOT/SystemRoot;
- WINDIR;
- TEMP/TMP;
- PATH only if required;
- USERPROFILE/HOME isolation implications;
- TLS certificate/runtime dependencies;
- DNS/Winsock dependencies;
- locale/encoding;
- architecture-specific variables.

Use synthetic/disposable tests. Never dump full environment.

Exit: minimal allowlist evidence and platform-specific positive/negative matrix.

## F18 — Process ownership / orphan / shutdown truth

Goal: challenge helper/app-server process lifecycle across success/failure/timeout/restart.

Cases:
- child exits before supervisor;
- supervisor exits first;
- result exists but child identity stale;
- timeout with process still alive;
- PID reuse;
- creation-time mismatch;
- attach-running after restart;
- natural exit vs kill ladder.

Reuse existing process-truth primitives; no second process manager.

Exit: proven coverage + missing cases.

## F19 — Recovery/replay/ambiguity fault-injection campaign

Goal: systematically test ambiguous external execution boundaries.

Faults:
- network fail before send;
- network fail after server may have accepted;
- child output truncated;
- durable result write succeeds but job transition fails;
- job transition succeeds but caller loses response;
- process dies between report/result;
- admission release fails;
- lease release fails;
- duplicate transport delivery;
- restart at every checkpoint.

Outcome must never blind-replay unsafe work.

Exit: recovery classification matrix tied to existing authorities.

## F20 — Provider/admission/credential provenance audit

Goal: prove one execution's provider identity from policy through runtime and result.

Trace:
- provider config snapshot;
- generation;
- endpoint/baseURL;
- model;
- trust/egress policy;
- credential_ref;
- credential delivery key;
- admission record;
- runtime model materialization;
- result/attestation identity.

Challenge stale generation, conflicting refs and ambient defaults.

Exit: end-to-end provenance proof or exact gap.

## F21 — Observability / trace privacy audit

Goal: define privacy-safe evidence needed to debug autonomous loops without storing prompts/secrets/hidden reasoning.

Review existing logs/events/traces for:
- task/execution ids;
- stage timestamps;
- provider/model refs;
- byte/count/duration metadata;
- error classifications;
- redaction behavior;
- retention surfaces.

Prefer local metadata-first telemetry. Raw prompt/tool payloads off/redacted by default.

Exit: REUSE map + minimal missing metadata proposal.

## F22 — A-Wiki cross-repo owner-map revalidation

Goal: revalidate Issue #233 owner map against current A-Wiki and A-Conductor source, only for capabilities touched by post-Wave-1 work.

Capabilities:
- model policy vs runtime selection;
- work order vs runtime task;
- claim/lease;
- review lifecycle;
- scheduler/ready-set;
- retry/recovery;
- next-ready continuation;
- memory/defect learning.

No broad rewrite if owner map still holds.

Exit: changed-state-only reconciliation.

## F23 — A-Wiki memory provenance / quarantine threat model

READ-ONLY unless a separate A-Wiki brain-gate claim exists.

Goal: shape malicious/stale memory-candidate fixtures:
- poisoned source candidate;
- stale fact attempting overwrite;
- low-confidence source promotion;
- provenance mismatch;
- private/sensitive data candidate;
- cross-agent untrusted summary;
- rollback/drift shadow.

A-Wiki policy remains owner. A-Conductor must not become memory authority.

Exit: A-Wiki-side packet recommendation or proof existing gates suffice.

## F24 — Defect-memory executable-prevention audit

Goal: mine accepted P0/P1/P2 history for recurring classes that still lack executable prevention.

For each candidate:
- original defect;
- root-cause class;
- current regression test/guard;
- prevention tier;
- whether docs-only memory can be upgraded to executable memory.

Prioritize classes hit repeatedly across Waves 1–4.

Exit: maximum 10 prevention candidates ranked by defect recurrence × blast radius.

## F25 — CURRENT-WORK / COLLAB / handoff drift audit

Goal: compare live GitHub/Issue/claim state against continuity files.

Do not edit hotspots claimlessly.

Classify every mismatch:
- dangerous duplicate-work risk;
- priority inversion risk;
- stale historical-only text;
- harmless documentation lag.

Shape one bounded fold packet for the actual hotspot owner rather than scattered edits.

Exit: exact fold target list.

## F26 — Open PR/branch/Issue hygiene and successor graph

Goal: reduce risk of agents selecting stale candidates.

Classify open/old items:
- KEEP;
- RETARGET;
- CLOSE_SUPERSEDED;
- FOLD_LATER;
- REVIEW_REQUIRED;
- OWNER_REQUIRED.

Do not delete branches/evidence owned by other lanes.

Explicitly revisit roadmap docs PRs #243/#244 and consumed Wave packets only from current evidence.

Exit: hygiene actions safe for integrator, no destructive cleanup.

## F27 — Cold-start resume drill

Goal: simulate a new agent with no chat history and verify it can find the correct frontier using only durable state.

Run three personas:
- GPT integrator;
- GLM implementation/review lane;
- deterministic operator/tool lane.

For each, record:
- files read;
- wrong/stale paths encountered;
- whether owner/next action is unambiguous;
- whether secret/private boundaries remain clear.

Exit: continuity gaps ranked by real cold-start failure risk.

## F28 — Test-suite economy and coverage topology

Goal: improve delivery speed without reducing assurance.

Analyze:
- which targeted suites predict full CI failures;
- redundant expensive suites;
- platform-only tests;
- flaky/slow tests;
- security tests missing positive controls;
- repeated fixture setup that can be reused safely;
- tests whose name/coverage overclaims production reality.

Do not delete tests from analysis alone.

Exit: evidence-backed test-routing recommendations with estimated time savings only where measured.

## F29 — Accepted-run efficiency scoreboard

Goal: build the evidence model for AEET-7 without rewarding failed cheap runs.

Candidate metrics:
- accepted lead time;
- review rounds;
- changed files/LOC only as secondary metrics;
- deterministic test duration;
- independent-review defect yield;
- adversarial-probe yield;
- CI retries/flakes;
- human relay actions;
- duplicate-work incidents;
- rollback/recovery incidents.

Use durable historical runs only. Unknown values remain UNKNOWN.

Exit: scoreboard schema proposal + sample from known accepted WOs, no fake precision.

## F30 — Failure forecasting / next-boundary attack plan

Goal: predict the next likely defects from architecture boundaries, then try to falsify them before implementation reaches production.

Focus:
- cross-platform environment inheritance;
- runtime upgrade/schema drift;
- provider route drift;
- stale claim/lease reuse;
- task/result identity mismatch;
- independent-review spoofing;
- fan-in ambiguity;
- recovery after partial durable writes;
- memory/provenance poisoning;
- stale SSoT causing duplicate work.

Each forecast must name the boundary, evidence basis and executable probe.

Exit: top 12 attack probes by expected risk-reduction value.

## F31 — Final synthesis + executable next-work queue

Goal: finish the Wave with an owner-correct dependency-aware queue, not a wish list.

Required output:
- F00..F31 status matrix;
- recursive finding list;
- exact current main/PRs/claims;
- Zero-Relay maturity `ZRA-1..5`;
- P0/P1/P2/P3 findings;
- owner/reuse decisions;
- maximum 12 future micro-WOs with risk/dependency/scope;
- list of work that should explicitly NOT be built;
- exactly one `NEXT_SAFE_ACTION`.

The final queue must preserve current P0 Zero-Relay priority unless live authority says it has completed.

---

# 6. Automatic routing priorities

When multiple families are eligible, choose in this order:

1. safety/security P0/P1 exact candidate review;
2. current user-prioritized Zero-Relay critical path;
3. recovery/ambiguity defects that block safe retries;
4. independent exact-SHA R2/R3 review;
5. executable security/evaluator prevention;
6. cross-platform/runtime compatibility;
7. SSoT/claim duplicate-work prevention;
8. efficiency/test-economy analysis;
9. roadmap/hygiene/read-only research.

Do not let lower priority read-only work consume an available critical review window.

---

# 7. Mutation handoff contract

When a family identifies a mutation candidate but lacks authority, write a compact packet with:

```text
TASK_ID=
OWNER_REPO=
RISK=
DEPENDENCY=
TRIGGER_EVIDENCE=
EXISTING_AUTHORITY_TO_REUSE=
MUTABLE_SCOPE_CEILING=
FORBIDDEN_SCOPE=
RED_TEST_OR_REPRODUCER=
MINIMUM_REPAIR_SHAPE=
TARGETED_VERIFY=
ADVERSARIAL_VERIFY=
INDEPENDENT_REVIEW_REQUIREMENT=
MERGE/RELEASE_OWNER=GPT_INTEGRATOR
```

Do not create a new branch/worktree/claim unless the repository's live mutation gate authorizes this GLM session as owner.

---

# 8. Review result format

For exact-SHA review:

```text
TASK/WO=
REPO=
BASE_SHA=
CANDIDATE_SHA=
CHANGED_SCOPE=
REVIEWER_INDEPENDENCE=
DETERMINISTIC_RERUNS=
ADVERSARIAL_PROBES=
P0=
P1=
P2=
P3=
VERDICT=ACCEPT|CHANGES_REQUIRED|REVIEW_BLOCKED
LIMITATIONS=
NEXT_SAFE_ACTION=
```

`ACCEPT` for R2/R3 requires no unresolved P0/P1/P2 unless the binding task explicitly defines a different threshold.

---

# 9. Long-session / cross-session policy

This Wave is intended to outlive one context window.

When nearing limit:

1. stop opening new mutation;
2. finish/checkpoint current bounded child;
3. write `PARTIAL_LIMIT_CHECKPOINT` to Issue #233;
4. record DONE family/child ids;
5. record BLOCKED family/owner/dependency ids;
6. record recursive findings and their state;
7. record exact repo/branch/SHA/PR state;
8. record active claims and forbidden scopes;
9. serialize next queue in deterministic priority order;
10. leave exactly one `NEXT_SAFE_ACTION`.

A fresh GLM session must read the last Wave-5 checkpoint and resume only unfinished work. It must not restart F00.. from scratch unless live state materially changed and it explains why re-recovery is needed.

---

# 10. Token/compute use policy

Use available model capacity aggressively for useful tasks:

Good uses:
- deeper call-path tracing;
- independent source cross-checks;
- adversarial/fuzz-like bounded test design;
- cross-platform reasoning backed by probes;
- historical defect mining;
- version compatibility analysis;
- negative + positive control matrices;
- replay/recovery state exploration;
- owner/reuse archaeology;
- exact-SHA code review;
- test-economy measurement.

Bad uses:
- restating the same conclusion;
- rereading unchanged files without a new question;
- generating speculative components with no gap evidence;
- producing prose when a deterministic probe can answer;
- creating duplicate planning/task/memory authorities;
- re-running a full suite after every tiny thought with no evidence benefit.

If useful queue remains, continue. If useful queue is exhausted, stop truthfully rather than manufacture work.

---

# 11. Whole-Wave STOP conditions

The MASTER `/goal` stops only for:

- `HUMAN_DECISION_REQUIRED`
- `HUMAN_ACTION_REQUIRED`
- `AUTHORIZATION_REQUIRED`
- `SAFETY_BLOCK`
- `OWNERSHIP_CONFLICT`
- `NO_SAFE_NEXT_ACTION`
- useful goal tree fully exhausted
- context/session limit after checkpoint

One blocked family is not a whole-Wave stop.

---

# 12. Final result

Post to A-Wiki-Conductor Issue #233:

`## GLM-MARATHON-WAVE5-320 RESULT`

Include:

1. exact repositories/SHAs inspected;
2. start vs final state;
3. family matrix F00..F31;
4. count of child goals completed/blocked/deferred;
5. recursive finding tree;
6. Zero-Relay ZRA-1..5 status;
7. P0/P1/P2/P3 findings and exact evidence;
8. REUSE/WRAP/EXTEND/BUILD/DROP matrix;
9. evaluator/security/provenance conclusions;
10. Windows/process/runtime compatibility conclusions;
11. recovery/replay/ambiguity conclusions;
12. A-Wiki cross-repo conclusions;
13. continuity/SSoT/PR/claim hygiene conclusions;
14. accepted-run efficiency/test-economy evidence;
15. maximum 12 ranked future micro-WOs;
16. explicit `DO_NOT_BUILD` list;
17. blockers requiring human action, if any;
18. exactly one `NEXT_SAFE_ACTION`.

End with:

`STATUS=WAVE5_COMPLETE` or `STATUS=PARTIAL_LIMIT_CHECKPOINT`.

---

# 13. One-line execution intent

**Run this file as one MASTER ZCode `/goal`; recursively execute F00..F31 using child protocol A..J, preempt for higher-value exact-SHA reviews, checkpoint instead of waiting, resume across sessions, and continue until every useful safe goal is completed or a true global stop condition occurs.**
