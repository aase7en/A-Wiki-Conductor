# WO-P1-190 — GLM Wave 10 / 10-hour deep engineering shift

Status: READY / DOCS-ONLY ORCHESTRATION PACKET
Risk: R0 parent transport; child work retains its own R0/R1/R2/R3 risk
Parent: WO-P1-155 Zero-Relay Accelerator
Durable coordination: GitHub Issue #233
Packet owner: GPT-5.6 Sol integrator
Execution engine: GLM-5.3 MAX through ZCode/manual pointer execution
Architecture / trust / exact-SHA acceptance / merge / release: GPT-5.6 Sol
Repository: A-Wiki-Conductor
Branch: `docs/wo-p1-190-glm-wave10-10h-deep-shift`
Bootstrap main: `f964afced5fbe0905c3667b1a6552a6fdafc09cb`

## Purpose

Use a long GLM-5.3 MAX session for work that benefits from sustained repository context, iterative debugging, code archaeology, adversarial testing, exact-SHA review, recovery/replay analysis, cross-platform reasoning, and bounded implementation.

This packet is designed as a **roughly ten-hour useful-work capacity envelope**, not a wall-clock timer and not a token-burning quota. GLM must never idle merely to reach ten hours. If a critical dependency is blocked, it moves to another safe READY program and returns automatically when the gate changes.

Wave 10 continues the accepted project priority:

`Zero-Relay correctness/reliability -> ZRA-2 -> ZRA-3 -> ZRA-4 -> later ODP/SundayFamily expansion`

SundayFamily MCP/capability expansion is deliberately deferred by WO189/PR #261 and is `DO_NOT_BUILD` in this wave except for read-only dependency notes needed to avoid future conflict.

## Bootstrap truth at publication

At packet creation:

- `origin/main = f964afced5fbe0905c3667b1a6552a6fdafc09cb`;
- Wave 9 / WO188 is predecessor transport and must not be restarted without material-state change;
- canonical ZRA-2 remains WO165 / PR #258;
- PR #258 head at bootstrap = `5f95fe16e95c90faaa4a36686e286515e4641708`;
- independent GPT review found one blocking P1: `ReviewEvidence` did not bind exact `task_sha256` + `result_sha256`;
- GPT-5.6 Sol currently owns the narrowly bounded Phase-A P1 repair claim from Issue #214 comment `5630372514`;
- Wave 10 must not mutate that active repair scope while GPT owns it;
- when a NEW repair candidate freezes, a genuinely independent GLM session is the preferred exact-SHA rereviewer;
- ZRA-3 Issue #215 is implementation-blocked on ZRA-2 acceptance;
- ZRA-4 Issue #216 is implementation-blocked on ZRA-3 acceptance;
- automatic ZCode app-server transport used by ChatGPT is intentionally READ_ONLY; a user-started ZCode/GLM workspace may have mutation tools, but the agent must prove its actual mutation capability and claim state before editing;
- packet publication itself grants no product/source/runtime/provider authority.

All of the above are bootstrap hints only. Actual Git/GitHub/runtime/claim state at execution time overrides stale details.

## Why this work suits GLM-5.3

Prefer GLM for:

- multi-hour repository archaeology while retaining long context;
- tracing cross-module identity/authority paths;
- RED-first implementation from an exact contract;
- iterative test/debug/repair loops;
- large adversarial matrices;
- race/replay/recovery hypothesis generation plus deterministic verification;
- exact-SHA read-only review of another author's candidate;
- Windows/POSIX behavior comparison;
- broad but bounded test generation and failure clustering;
- mechanical refactor/hardening after authority is settled;
- evidence synthesis into concise checkpoints.

Do not spend GLM capacity on:

- final architecture/trust-boundary adjudication owned by GPT;
- self-approval/self-merge;
- repetitive reruns with no changed hypothesis;
- broad speculative features;
- new schedulers/stores/retry engines where authority already exists;
- SundayFamily MCP work deferred by WO189;
- live credential handling or secret discovery;
- destructive repository cleanup.

## Parent mutable scope

Exactly two additive docs files:

- `docs/work-orders/WO-P1-190-glm-wave10-10h-deep-shift.md`
- `docs/prompts/GLM-MARATHON-WAVE10-10H-DEEP-SHIFT.md`

This parent grants no mutation authority outside those two files.

## Child mutation gate

Every mutable child must independently establish:

1. canonical existing WO or explicitly permitted new bounded WO;
2. repository + remote + exact worktree;
3. branch + HEAD + origin/main;
4. clean/known dirty and untracked state;
5. owner/claim/lease identity;
6. allowed mutable scope;
7. forbidden scope;
8. open-PR/worktree overlap proof;
9. risk tier R0/R1/R2/R3;
10. dependency gate;
11. deterministic verification ladder;
12. result/checkpoint destination;
13. `SAFE_TO_MUTATE=YES`.

Unknown/conflicting state means no mutation.

## Ten-hour operating model

Wave 10 has twelve programs. The recommended budget is approximately 45–70 minutes of useful work per high-value active program, with shorter programs when evidence is already settled. These are priority budgets, not timers.

The executor must use preemption and replenishment rather than waiting on one blocked lane.

### P00 — Critical-path watcher / exact-SHA review preemption

Re-pin PR #258 and Issue #214 frequently enough to catch a newly frozen Phase-A repair candidate.

If a NEW candidate exists and this GLM session did not author/mutate it:

- preempt lower-value work;
- independently review exact SHA;
- adversarially test digest substitution, stale review reuse, author/reviewer identity, UNKNOWN recovery, exactly-one repair, no-I/O purity and typed errors;
- publish P0/P1/P2/P3 verdict;
- do not mutate or merge the reviewed candidate;
- resume saved queue.

If no new candidate exists, continue other programs.

### P01 — IR1 duplicate-physical-execution / stable replay identity

Use the recovered IR1 incident as a concrete failure case.

Goal: trace why one logical review authorization could produce multiple physical executions when outer tool/invocation boundaries timed out and ephemeral stores did not share replay authority.

Deliver:

- exact identity map from logical review task -> job -> execution -> provider admission -> WorkerLease -> process;
- deterministic reproducer or proof that current production path already prevents it;
- distinction between harness misuse and product invariant gap;
- smallest executable prevention candidate;
- R3 repair WO shape only if source mutation is justified.

No blind retry and no live provider requirement.

### P02 — ZRA-2 Phase B repair materializer

Until Phase A is accepted: read-only shaping, source archaeology, RED design and task-packet preparation only.

After Phase A acceptance and a fresh child claim:

- reuse `AgentRepairRequest`, `build_repair_task_markdown`, `TaskPacketFile`, existing confined filesystem authority;
- bind exact rejected task digest + result digest + finding/reason identity;
- deterministic path and bytes;
- same path/same bytes -> reuse;
- same path/different bytes -> typed collision;
- generation exactly one;
- no free-form prompt as authority;
- no provider/review/job/lease/scheduler authority in the materializer.

### P03 — ZRA-2 Phase C trusted review composition

Trace and, only when claim-gated, compose the existing review path:

`review task -> ReviewMailboxResultReader -> ReviewResultForwarder -> accepted A-Wiki ReviewBridge/ReviewBus`

Falsify:

- self-review;
- stale reviewed HEAD;
- task digest substitution;
- result digest substitution;
- task/result ref substitution;
- provider/model/reviewer drift;
- task-hash drift;
- oversized/truncated review output;
- truthy prose acceptance;
- addressed-but-not-verified findings;
- duplicate review lifecycle/store.

Do not import A-Wiki internals or create another ReviewBus.

### P04 — ZRA-2 Phase D durable lifecycle composition

After B/C acceptance, compose existing lifecycle authorities only.

Challenge:

- `REVIEW_PENDING` prematurely becoming COMPLETE;
- provider exit 0 without accepted exact review evidence;
- UNKNOWN/timeout ambiguity;
- stale HEAD;
- second repair generation;
- lease rollover after candidate commit;
- reviewed-SHA mismatch;
- completion from model prose;
- crash/restart at every transition.

No second scheduler/job store/retry authority.

### P05 — ZRA-3 automatic NEXT READY deep preparation / implementation

Issue #215 is canonical.

Before ZRA-2 acceptance: read-only archaeology, exact seam selection, failure matrix, RED packet.

After ZRA-2 acceptance and an explicit claim:

prove:

- accepted/verified parent advances exactly one newly READY successor automatically;
- duplicate tick is a no-op;
- completed identity never respawns;
- restart preserves durable identity;
- UNKNOWN never blind-replays;
- dirty worktree/lease/provider/admission drift fails closed;
- foreign completion cannot release a successor;
- no human prompt/result relay.

Reuse TaskGraph/scheduler/job/lease authorities.

### P06 — ZRA-4 bounded 2–3 lane fan-out/fan-in

Issue #216 is canonical.

Before ZRA-3 acceptance: read-only concurrency archaeology and RED/fault packet only.

After ZRA-3 acceptance and explicit claim:

prove bounded parallel execution using existing WIP/provider capacity/lease/scheduler authorities:

- 2–3 independent READY lanes;
- no overlapping mutable paths;
- sibling failure preserves successful sibling evidence;
- partial fan-in deterministic;
- malformed one-lane result does not erase valid siblings;
- provider capacity uncertainty blocks launch;
- stale lease fails closed;
- duplicate execution is prevented/reconciled;
- no global barrier/new scheduler.

### P07 — Process / PID / Windows recovery hardening

Deep-dive recurring high-risk process boundaries:

- PID + creation-time identity;
- exact executable/argv fingerprint;
- idempotent start observation race;
- process-gone-before-release;
- orphan prevention;
- supervisor/result missing;
- output budget exhaustion;
- Windows `SYSTEMROOT` minimality;
- permission/observer failure classes;
- exact-PID-only cleanup;
- restart attach/reconcile;
- no broad kill.

Use positive controls before interpreting adversarial failures.

### P08 — Security / prompt injection / exfiltration adversarial pack

Fake-first / synthetic-only.

Build or shape executable fixtures for:

- repository-content prompt injection;
- malicious tool output;
- malicious metadata;
- authority-escalation text;
- review spoofing;
- task/result digest substitution;
- provider/endpoint confusion;
- fake secret exfiltration strings;
- task/result/log/exception/argv/env/artifact leak paths.

Every malicious case needs a valid positive semantic twin.

Never use real credentials.

### P09 — Exact-SHA review/hardening queue

When genuinely independent, use idle capacity to review frozen candidates authored by other lanes.

Priority:

1. Zero-Relay R3 critical path;
2. P0/P1 repairs;
3. R2/R3 delivery-path candidates;
4. process/recovery/security fixes;
5. older PRs only when still materially relevant.

Candidate movement invalidates review. Never self-review.

### P10 — CI/test economy + cross-platform fault isolation

Use current and historical CI evidence to reduce wasted reruns without weakening assurance.

Deliver:

- focused -> related -> adversarial -> hosted ladder recommendations backed by data;
- deterministic isolation for flaky Windows process tests;
- failure clustering by authority boundary;
- tests that catch material defects earlier;
- no broad full-suite reruns merely because time remains.

### P11 — Continuity / hygiene / successor shaping

Read-only unless a single-writer claim exists.

Compare actual Git/GitHub/runtime with CURRENT-WORK/handoff/COLLAB/Issues.

Deliver changed-state-only reconciliation candidates, stale-claim hazards, safe PR/worktree cleanup candidates, and the next bounded queue.

Do not edit shared continuity hotspots from this parent wave.

## Standard program loop

Every selected work item follows:

`RECOVER -> REUSE -> TRACE -> POSITIVE CONTROL -> FALSIFY -> DELIVER/SHAPE -> VERIFY -> DEFECT MEMORY -> CHECKPOINT -> ROUTE`

Use the shortest truthful verification ladder appropriate to risk.

## Preemption

Preempt current work when:

- a new PR #258 repair candidate freezes for independent review;
- a frozen R2/R3 candidate from another author becomes critical-path READY;
- a P0/P1 finding appears;
- claim/ownership drift invalidates planned mutation;
- exact CI/merge/post-main result unblocks ZRA-2/3/4;
- GPT publishes a new child task/claim.

Before preemption, checkpoint queue position. After preemption, automatically resume.

## Replenishment

When the initial programs are truthfully dispositioned and useful capacity remains, derive `X001..X500` only from proven current evidence:

- newly unblocked ZRA critical-path work;
- new exact-SHA independent review;
- P0/P1/P2 reproducer or bounded repair packet;
- missing executable defect memory;
- concrete recovery/replay defect;
- process/cross-platform proof gap;
- security fixture gap;
- SSoT/claim duplication hazard;
- measurable CI/test throughput improvement;
- duplicate-authority simplification;
- deterministic cleanup candidate.

No token padding and no speculative feature expansion.

## Multi-session continuity

Ten-hour work may exceed one model context/session. Before provider/context limit approaches, publish a durable checkpoint to Issue #233 with:

- exact main/ref/SHA;
- active PR/issue/WO;
- completed programs/subgoals;
- current candidate SHAs;
- review verdicts;
- claims acquired/released;
- tests/probes and results;
- active findings P0/P1/P2/P3;
- blocked owner/dependency items;
- current queue + skip/consumed set;
- evidence paths;
- exactly one resume pointer / NEXT_SAFE_ACTION.

The next GLM session must re-pin actual state and resume the first unresolved item. Do not restart settled programs unless material state changed or a new falsification hypothesis justifies reopening them.

## Stop conditions

Stop the campaign only when one is true:

- useful safe work frontier is exhausted;
- every remaining item has a real owner/authority/dependency blocker;
- `HUMAN_DECISION_REQUIRED`;
- `HUMAN_ACTION_REQUIRED`;
- `AUTHORIZATION_REQUIRED`;
- `SAFETY_BLOCK`;
- provider/session limit is near and a durable resumable checkpoint has been published.

Do not stop because one child is blocked while independent safe work exists.

## Completion report

Publish to Issue #233:

`## GLM-WAVE10-10H-DEEP-SHIFT RESULT`

Include:

- start/final main and material SHAs;
- elapsed useful-work estimate if known, but do not fabricate wall-clock precision;
- program dispositions;
- implementations/frozen candidates;
- independent reviews;
- P0/P1/P2/P3 findings and closures;
- deterministic test/CI evidence;
- recovery/replay/process/security/cross-platform findings;
- ZRA-2/3/4 maturity delta;
- claims acquired/released;
- consumed/no-repeat evidence;
- `DO_NOT_BUILD` list;
- top next READY queue;
- exactly one `NEXT_SAFE_ACTION` for GPT/integrator.

Evidence, not model confidence, is completion authority.
