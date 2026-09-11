# GLM MARATHON WAVE 10 — 10-HOUR DEEP ENGINEERING SHIFT

## MASTER `/goal`

Run this file as one sustained GLM-5.3 MAX / ZCode engineering campaign.

Target: roughly **ten hours of useful engineering capacity**, potentially across multiple GLM/ZCode sessions.

This is NOT a timer and NOT a token quota.

Do not idle to reach ten hours.
Do not manufacture work.
Do not repeatedly rerun unchanged tests without a new hypothesis.
Do not ask the user to type `continue` between safe goals.
Do not use the user as a GPT↔GLM result relay when durable GitHub/repo evidence can carry state.

Evidence production and accepted progress are the objective.

---

# 0. COLD START — MANDATORY EVERY SESSION

Before material work:

1. Read actual `origin/main:00-AGENT-ENTRY.md`.
2. Read `PROJECT-GRAPH.yaml` and select only relevant nodes.
3. Read `AGENTS.md`.
4. Re-pin actual repo, remote, origin/main, worktrees, branches, HEADs, dirty/untracked state.
5. Re-pin relevant open PRs, Issues, exact-head CI, claims, leases and ownership.
6. Read the active child WO/task packet before any mutation.
7. Before any `src/a_conductor/**` mutation, read current `DEFECT_LESSONS.md`.
8. Recompute risk tier and `SAFE_TO_MUTATE` for every mutable child.
9. Treat chat/history/this packet's bootstrap SHA as hints only. Actual state wins.
10. Unknown owner/claim/dirty/overlap/replay safety => fail closed.

Never reset, clean, stash, rebase, force-push or delete another lane's work for convenience.
Never broad-kill processes.
Never expose real credentials.

---

# 1. WAVE IDENTITY

Parent WO:
`WO-P1-190`

Parent packet:
`docs/work-orders/WO-P1-190-glm-wave10-10h-deep-shift.md`

This file:
`docs/prompts/GLM-MARATHON-WAVE10-10H-DEEP-SHIFT.md`

Durable coordination:
GitHub Issue #233

Bootstrap main at packet publication:
`f964afced5fbe0905c3667b1a6552a6fdafc09cb`

Parent packet grants NO product/source/test/runtime/provider/A-Wiki/merge authority.

Every mutable child needs its own current WO/claim/non-overlap gate.

GPT-5.6 Sol retains:

- architecture;
- trust/security boundary decisions;
- conflict adjudication;
- exact-SHA acceptance;
- merge;
- release.

GLM-5.3 MAX is the preferred long-horizon executor for:

- repository archaeology;
- RED-first implementation;
- debugging;
- adversarial testing;
- exact-SHA read-only review;
- race/replay/recovery analysis;
- cross-platform failure analysis;
- bounded hardening/refactor;
- test generation;
- evidence synthesis.

---

# 2. CURRENT PRIORITY POLICY

Current priority is:

`Zero-Relay correctness/reliability -> ZRA-2 -> ZRA-3 -> ZRA-4 -> later ODP/SundayFamily expansion`

WO189 / PR #261 defers SundayFamily MCP/capability expansion to the late roadmap.

Therefore this Wave MUST NOT spend material capacity implementing SundayFamily MCP, broad new integrations, or unrelated feature expansion.

Security/recovery/test work that directly protects Zero-Relay remains in scope when separately authorized.

---

# 3. BOOTSTRAP FRONTIER — RE-PIN BEFORE USE

At publication:

- canonical ZRA-2 = WO165 / PR #258;
- old PR #258 candidate = `5f95fe16e95c90faaa4a36686e286515e4641708`;
- independent review found a blocking P1 digest-binding defect;
- GPT-5.6 Sol currently owns the narrowly bounded repair claim from Issue #214 comment `5630372514`;
- Wave 10 MUST NOT mutate that exact repair scope while GPT owns it;
- when GPT freezes a NEW repair candidate and releases mutation ownership, this GLM session may independently rereview it if it did not author/mutate that candidate;
- ZRA-3 = Issue #215, implementation blocked until ZRA-2 acceptance;
- ZRA-4 = Issue #216, implementation blocked until ZRA-3 acceptance;
- automatic app-server transport used by ChatGPT may be READ_ONLY; a user-launched ZCode workspace may expose write tools. Detect actual capability instead of assuming.

If these facts changed, follow the new facts.

---

# 4. TEN-HOUR OPERATING MODEL

Use a sustained queue with twelve major programs.

Suggested useful-work budget per high-value active program: roughly 45–70 minutes.

These are prioritization budgets, NOT timers.

A program may finish faster if evidence is already settled.
A blocked program must yield to another safe program.
Return automatically when its dependency changes.

For every work item use:

`RECOVER -> REUSE -> TRACE -> POSITIVE CONTROL -> FALSIFY -> DELIVER/SHAPE -> VERIFY -> DEFECT MEMORY -> CHECKPOINT -> ROUTE`

Do not skip positive control for adversarial probes.

---

# P00 — CRITICAL-PATH WATCHER / PR #258 REREVIEW

This program has preemption priority over all lower-value work.

At every meaningful boundary, re-pin:

- PR #258 exact head;
- Issue #214 latest checkpoint;
- CI for the exact candidate;
- active owner/claim state.

## If PR #258 is still old candidate `5f95fe16...`

Do NOT rereview it again.
The P1 finding is already durable.
Continue P01+.

## If a NEW Phase-A repair candidate freezes

First prove this GLM session did NOT author or mutate it.

Then preempt immediately into independent R3 exact-SHA rereview.

Mandatory attack matrix:

1. `ReviewEvidence.task_sha256` exact binding.
2. `ReviewEvidence.result_sha256` exact binding.
3. same task ref / different task bytes.
4. same result ref / different result bytes.
5. malformed SHA values.
6. task/result digest cross-substitution.
7. attempt mismatch.
8. generation mismatch.
9. author == reviewer.
10. UNKNOWN/TIMEOUT/AMBIGUOUS => RECOVERY_REQUIRED.
11. verification failure + ACCEPT contradiction.
12. no-review implicit acceptance attempt.
13. generation 0 reject -> exactly generation 1 repair.
14. generation 1 reject -> terminal reject.
15. truthy arbitrary object cannot forge review.
16. exception messages do not leak attacker text.
17. module remains pure/no provider/file/network/process/Git I/O.
18. no second scheduler/store/retry/review authority.
19. exact-head CI matches reviewed SHA.
20. changed scope remains bounded.

Publish verdict:

`P0 / P1 / P2 / P3`

R3 acceptability requires:

`P0=0 / P1=0 / P2=0`

Reviewer does not mutate or merge candidate.

Checkpoint result to PR #258 + Issue #214 + Issue #233 as appropriate.

Resume saved queue immediately after review.

---

# P01 — IR1 DUPLICATE PHYSICAL EXECUTION / STABLE REPLAY IDENTITY

Treat IR1 as a real recovery incident, not a review verdict.

Known class:

one logical review authorization
→ outer caller/tool timeout
→ replay across ephemeral invocation stores
→ multiple physical executions possible
→ both reconciled RECOVERY_REQUIRED

Goal: establish whether this is harness misuse only or a missing production invariant.

## A — Recover

Read current IR1/IR2 evidence and production replay/idempotency authorities.

## B — Reuse

Map existing:

- JobStore/job ID;
- ExecutionStore/execution ID;
- GraphDispatch identity;
- provider admission identity;
- WorkerLease identity;
- supervised process identity;
- task hash;
- durable result identity.

Do not invent a new replay store before proving existing authorities cannot solve it.

## C — Trace

Trace one logical review from task authorization to process spawn.
Mark where identity becomes ephemeral.

## D — Positive control

Prove a normal single invocation launches/reuses exactly one physical execution.

## E — Falsify

Try:

- outer timeout before durable result;
- caller retry with same logical identity;
- process still running;
- process completed but caller lost response;
- new local wrapper process;
- restart with same task digest;
- provider admission released/active edge;
- lease active/expired edge;
- stale transient DB/control store.

## F — Deliver

Read-only first.

Deliver:

- deterministic reproducer or non-reproducer;
- identity-loss point;
- existing authority that should fence it;
- smallest executable prevention candidate;
- exact owner/scope/risk.

If source repair is genuinely needed, shape a new R3 child WO/claim. Do not silently mutate runtime code from this parent.

## G–J

Verify, convert the defect to executable memory, checkpoint, route.

---

# P02 — ZRA-2 PHASE B DETERMINISTIC REPAIR MATERIALIZER

Dependency:
Phase-A accepted exact SHA.

Before dependency clears:

- source archaeology only;
- reuse map;
- API/RED contract;
- task packet preparation;
- collision/adversarial matrix.

After dependency clears and an explicit child mutation claim exists:

reuse:

- `AgentRepairRequest`;
- `build_repair_task_markdown`;
- `TaskPacketFile`;
- existing confined filesystem/path authority.

Required invariants:

- bind exact rejected task digest;
- bind exact rejected result digest;
- bind exact review finding/reason identity;
- generation must be exactly 1;
- same deterministic path + same bytes => REUSE;
- same path + different bytes => typed COLLISION;
- no raw prompt text as authority;
- no reviewer prose as mutation authority;
- no provider dispatch;
- no ReviewBus ownership;
- no JobStore/lease/scheduler ownership;
- deterministic output bytes;
- restart-safe/idempotent materialization.

RED first.
Freeze exact SHA after accepted slice.
Stop mutation for independent review.
Continue non-overlapping queue.

---

# P03 — ZRA-2 PHASE C TRUSTED REVIEW COMPOSITION

Dependency:
Phase A/B acceptance as required by current WO.

Reuse the existing path:

`review task -> ReviewMailboxResultReader -> ReviewResultForwarder -> A-Wiki ReviewBridge/ReviewBus`

Never create another ReviewBus.
Never import A-Wiki internals as hidden state authority.

Adversarial matrix:

- self-review;
- stale reviewed SHA;
- foreign task;
- foreign result;
- task digest substitution;
- result digest substitution;
- task/result ref substitution;
- provider mismatch;
- model mismatch;
- reviewer identity drift;
- task hash drift;
- oversized result;
- truncated result;
- malformed UTF-8/JSON;
- duplicate/conflicting review result;
- truthy prose acceptance;
- addressed blocker without independent verification;
- clean-HEAD lost after review;
- review for H1 applied to H2.

Read-only until explicit child claim exists.

---

# P04 — ZRA-2 PHASE D DURABLE LIFECYCLE

Dependency:
accepted Phase A/B/C slices.

Compose existing authorities only.

Trace parent lifecycle:

`EXECUTING -> VERIFYING -> REVIEW_PENDING -> COMPLETE`

or

`REVIEW_PENDING -> CHANGES_REQUIRED -> REPAIRING -> VERIFYING -> REVIEW_PENDING`

Challenge every transition:

- provider exit 0 but result not verified;
- verification green but review missing;
- review PASS but exact SHA changed;
- UNKNOWN reviewer execution;
- repair child timeout;
- candidate commit invalidates old mutation lease;
- stale expected version/CAS;
- generation 2 attempt;
- foreign child execution;
- restart mid-transition;
- conflicting durable evidence;
- model prose says DONE;
- CI stale to prior SHA.

Parent COMPLETE only from trusted exact evidence.

No second state machine authority.

---

# P05 — ZRA-3 AUTOMATIC NEXT READY

Canonical issue:
#215

Before ZRA-2 acceptance:

READ_ONLY SHAPING ONLY.

Do:

- graph/scheduler/job archaeology;
- exact continuation seam;
- failure model;
- RED test plan;
- restart/replay matrix;
- smallest mutable future scope.

After ZRA-2 acceptance and explicit GPT-framed child claim:

prove:

1. accepted/verified parent releases exactly correct successor READY set;
2. one automatic continuation tick occurs without human prompt relay;
3. duplicate tick no-op;
4. completed task never respawns;
5. restart preserves identity;
6. foreign completion does not release successor;
7. UNKNOWN does not blind replay;
8. dirty worktree blocks mutation;
9. lease drift blocks launch;
10. provider/admission uncertainty blocks launch;
11. stale graph/version fails closed;
12. no second scheduler/task lifecycle.

Use current scheduler/TaskGraph/GraphDispatch authorities.

---

# P06 — ZRA-4 BOUNDED PARALLEL 2–3 LANE FAN-IN

Canonical issue:
#216

Before ZRA-3 acceptance:

READ_ONLY SHAPING ONLY.

Deep-trace:

- ReadySet;
- write-set conflict detection;
- WorkerCandidateAssembler;
- WorkerLeaseBroker;
- provider max concurrency/admission;
- ParallelReadyExecutor;
- durable per-task results;
- GraphDispatch/fan-in state.

After ZRA-3 acceptance and explicit claim:

prove with 2–3 independent READY lanes:

- non-overlapping mutable scope;
- independent worktrees;
- provider capacity fence;
- worker lease fence;
- one sibling failure preserves valid siblings;
- one malformed result does not erase good evidence;
- partial fan-in deterministic;
- no batch rollback of successful siblings;
- duplicate execution prevented/reconciled;
- stale lease fails closed;
- provider capacity uncertainty blocks launch;
- restart preserves child identities;
- no global barrier/new scheduler.

---

# P07 — PROCESS / PID / WINDOWS RECOVERY HARDENING

Use long-context debugging strength here.

Focus recurring process-risk boundaries:

- PID + creation-time identity;
- executable fingerprint;
- argv fingerprint;
- idempotent start observation;
- PID reuse;
- observer permission/error classes;
- process gone before release;
- child exit before result;
- result before terminal exit;
- orphan prevention;
- exact supervisor/child relation;
- stdout/stderr budget;
- delayed exit;
- restart attach;
- cleanup locks;
- Windows `SYSTEMROOT` minimality;
- POSIX parity;
- no broad kill.

Always build a positive control before interpreting a failure as product defect.

When a flaky test appears:

1. reproduce deterministically if possible;
2. identify race window;
3. separate environment/tool failure from source defect;
4. add executable prevention only if defect is real;
5. do not blind-rerun until green and call that proof.

---

# P08 — SECURITY / PROMPT INJECTION / EXFILTRATION PACK

Fake-first only.

Use synthetic secrets.

Adversarial fixtures:

- malicious repository text telling agent to bypass policy;
- malicious task/result text;
- malicious tool output;
- malicious tool metadata;
- authority escalation language;
- reviewer spoofing;
- task digest substitution;
- result digest substitution;
- endpoint confusion;
- provider confusion;
- secret-looking strings in logs/errors;
- env/argv/artifact leakage;
- redirect/foreign endpoint attempt;
- hidden instruction in generated evidence.

Every malicious fixture needs a valid positive semantic twin.

Prefer executable tests/checkers over prose warnings.

No real secrets.
No live external provider call unless separately authorized.

---

# P09 — INDEPENDENT EXACT-SHA REVIEW QUEUE

When this session is genuinely independent from candidate author:

review frozen candidates from other lanes.

Priority:

1. ZRA-2/3/4 R3 critical path;
2. P0/P1 repair;
3. R2/R3 delivery-path candidate;
4. process/recovery/security candidate;
5. older PR only if still materially valuable.

For each review:

- re-pin immutable SHA;
- re-pin exact-head CI;
- read candidate WO/acceptance contract;
- inspect exact diff;
- attack trust boundaries;
- classify P0/P1/P2/P3;
- publish exact symbols/tests/evidence;
- do not mutate reviewed candidate;
- do not merge.

Candidate movement invalidates review.

Never count this session as independent reviewer of anything it authored/mutated.

---

# P10 — CI / TEST ECONOMY / CROSS-PLATFORM FAULT ISOLATION

Use historical accepted/rejected lanes to quantify which tests catch real defects earliest.

Goal:
maintain R3 assurance while shortening repair cycles.

Analyze:

- targeted test yield;
- related-suite yield;
- adversarial-batch yield;
- hosted CI-only failures;
- Windows-only failures;
- flaky process tests;
- expensive duplicate full runs;
- tests that repeatedly miss material defects.

Deliver:

- focused-first ladders;
- deterministic flake isolation;
- candidate test subsets by changed authority;
- earlier executable guards;
- no assurance downgrade.

Do not rewrite CI broadly without explicit child claim.

---

# P11 — CONTINUITY / CLAIM / PR / WORKTREE HYGIENE + SUCCESSOR SHAPING

Read-only unless a dedicated single-writer claim exists.

Compare:

- actual Git/GitHub/runtime;
- Issue #233;
- Issues #214–#216;
- CURRENT-WORK;
- COLLAB;
- handoff;
- open PRs;
- known worktrees/branches.

Find:

- stale claims;
- duplicate-work risk;
- consumed docs packet PRs;
- superseded branches;
- clean abandoned worktrees;
- stale acceptance language;
- mismatched dependency ordering;
- forgotten frozen candidates.

Do NOT close/delete/reset unknown work from this parent.

Produce safe cleanup candidates with proof.

Maintain a small successor queue:

`item | dependency | owner | risk | smallest scope | proof required | blocker | next action`

---

# 5. PREEMPTION RULES

Checkpoint current goal, then preempt when:

1. NEW PR #258 repair candidate freezes for independent review;
2. a P0/P1 trust/security/recovery defect appears;
3. exact CI/merge/post-main result unblocks ZRA-2/3/4;
4. claim/ownership drift makes mutation unsafe;
5. ambiguous execution requires recovery reconciliation;
6. a frozen R2/R3 candidate from another author becomes critical-path READY;
7. GPT posts a new bounded child task/claim.

After preemption, automatically resume previous safe queue.

Do not ask user to type continue.

---

# 6. MUTATION RULE

This Wave is NOT blanket permission.

Before every edit:

- canonical WO exists;
- owner known;
- fresh claim active;
- repo/worktree/remote verified;
- branch/HEAD verified;
- dirty/untracked state known;
- mutable paths explicit;
- forbidden paths explicit;
- overlap checked;
- dependency satisfied;
- risk classified;
- RED/acceptance plan exists;
- result destination exists;
- `SAFE_TO_MUTATE=YES`.

If one condition fails, do not mutate.

If this GLM environment lacks write tools, do not pretend mutation happened.
Mark the child `GLM_MUTATION_TRANSPORT_UNAVAILABLE` and continue read-only programs/reviews/testing that are genuinely possible.

---

# 7. DEFECT MEMORY RULE

For every material defect, prefer prevention in this order:

1. regression test;
2. deterministic checker;
3. type/schema/invariant;
4. fail-closed runtime guard;
5. CI/lint gate;
6. monitoring/diagnostic evidence;
7. docs/runbook;
8. prose lesson only when nothing executable fits.

Prove whether prevention already exists before adding another mechanism.

---

# 8. NO-REPEAT RULE

Consume Waves 1–9 evidence.

Do NOT rerun a completed program merely because this is a new Wave.

A completed prior item may be reopened only if:

- main/candidate materially changed;
- a new failure contradicts prior evidence;
- a new adversarial hypothesis exists;
- dependency semantics changed;
- prior evidence was invalid/ambiguous.

Record the reason for reopening.

---

# 9. REPLENISHMENT X001..X500

After P00..P11 are truthfully dispositioned, continue useful work by minting only evidence-backed X goals.

Priority:

1. newly unblocked Zero-Relay critical path;
2. independent exact-SHA review of another author's candidate;
3. P0/P1/P2 reproducer/repair packet;
4. IR1/recovery/replay follow-up;
5. process/PID/cross-platform proof gap;
6. executable security fixture;
7. missing defect-memory mechanism;
8. claim/SSoT duplication hazard;
9. measurable test/CI throughput improvement;
10. duplicate-authority simplification;
11. deterministic cleanup candidate.

Every X goal records:

- parent evidence;
- owner;
- risk;
- exact scope;
- dependency;
- falsifiable hypothesis;
- exit condition.

No speculative features.
No token padding.
No SundayFamily MCP implementation.

---

# 10. MULTI-SESSION CONTINUITY

A ten-hour shift may span multiple model contexts/sessions.

Before context/provider limit approaches, publish:

`## GLM-WAVE10-10H PARTIAL CHECKPOINT`

to Issue #233.

Include:

- actual main/ref/SHA;
- active worktree/branch/HEAD where relevant;
- active PR/Issue/WO;
- completed programs/subgoals;
- exact frozen candidate SHAs;
- exact review verdicts;
- active findings P0/P1/P2/P3;
- claims acquired/released;
- tests/probes and deterministic results;
- blocked owner/dependency items;
- consumed/no-repeat set;
- current queue head;
- evidence paths;
- exactly one `NEXT_SAFE_ACTION` / resume pointer.

Next session:

1. cold-start again;
2. re-pin actual state;
3. resume first unresolved goal;
4. do not restart P00 unless state changed.

---

# 11. DO NOT BUILD / DO NOT DO

Do NOT build:

- second scheduler;
- second task graph;
- second JobStore;
- second execution store;
- second provider authority;
- second WorkerLease authority;
- second ReviewBus;
- second retry/replay engine;
- second memory/trace authority;
- SundayFamily MCP/capability expansion in this Wave;
- broad ODP feature work before ZRA dependency gates;
- speculative new framework merely to organize tests.

Do NOT:

- expose credentials;
- inspect broad secret/config trees;
- blind retry UNKNOWN external effects;
- self-review R2/R3 candidate;
- self-merge;
- force push;
- reset/clean unknown work;
- broad-kill processes;
- call flaky rerun a fix;
- treat provider exit 0 as completion;
- treat reviewer prose as acceptance;
- report work that did not happen.

---

# 12. STOP CONDITIONS

Continue while a truthful safe goal exists.

Stop only for:

- `HUMAN_DECISION_REQUIRED`;
- `HUMAN_ACTION_REQUIRED`;
- `AUTHORIZATION_REQUIRED`;
- `SAFETY_BLOCK`;
- `OWNERSHIP_CONFLICT` with no alternative safe queue;
- `NO_SAFE_NEXT_ACTION`;
- provider/context limit near after durable checkpoint.

One blocked child is NOT a reason to stop if another safe program is READY.

---

# 13. FINAL RESULT CONTRACT

At end publish to Issue #233:

`## GLM-WAVE10-10H-DEEP-SHIFT RESULT`

Report:

1. actual start/final main;
2. actual useful-work duration estimate if known — never fabricate precision;
3. programs P00..P11 disposition;
4. X goals completed;
5. implementations/frozen candidates + exact SHAs;
6. independent reviews + exact SHAs;
7. P0/P1/P2/P3 findings;
8. repaired/closed findings;
9. tests/probes/CI evidence;
10. recovery/replay findings;
11. process/PID/cross-platform findings;
12. security/exfiltration findings;
13. ZRA-2 maturity delta;
14. ZRA-3 maturity delta;
15. ZRA-4 maturity delta;
16. claims acquired/released;
17. blocked owners/dependencies;
18. consumed/no-repeat evidence;
19. `DO_NOT_BUILD` updates;
20. top next READY queue;
21. exactly ONE `NEXT_SAFE_ACTION` for GPT/integrator.

Do not claim DONE because time elapsed.
DONE means the useful safe frontier was honestly worked and every selected item has evidence or a truthful blocked/deferred/consumed disposition.

Begin now.
