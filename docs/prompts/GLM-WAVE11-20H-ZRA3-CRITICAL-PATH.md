# GLM WAVE 11 — 20-HOUR ZRA-3 CRITICAL-PATH `/goal`

## MASTER `/goal`

Drive WO-P1-191 from current durable truth to the strongest safely frozen ZRA-3 candidate possible without human prompt relay.

Primary objective:

`durably accepted task -> reconcile authoritative completion -> expose/select newly READY successor -> dispatch exactly once -> persist/reconcile result -> continue without human copy/paste`

This is a **useful-work capacity envelope up to roughly 20 hours**, not a wall-clock requirement and not a token-burning target. Finish earlier if the bounded task is genuinely complete. Never generate filler, repeat unchanged work, or remain active merely to consume time.

Your implementation authority is ONLY the current WO/task packet and current durable repo/claim state. `/goal`, large context, long runtime, tool access, or provider quota do not grant additional repository, runtime, secret, merge, replay, or ownership authority.

---

# 0. COLD START — MANDATORY

Before any mutation:

1. Read `00-AGENT-ENTRY.md`.
2. Read `PROJECT-GRAPH.yaml` and only the routed nodes needed for this task.
3. Read `AGENTS.md`.
4. Read `docs/work-orders/WO-P1-191-zra3-next-ready.md` in full.
5. Read the relevant parts of:
   - `docs/plans/2026-09-04-zero-relay-accelerator-roadmap.md`
   - `docs/work-orders/WO-P1-165-zra2-review-repair-loop.md`
   - `docs/contracts/a-wiki-a-conductor-integration.md`
   - `docs/agent-collab/FAST_EXECUTION_PROTOCOL.md`
   - `docs/agent-collab/CAPABILITY_MATRIX.md`
6. Read `DEFECT_LESSONS.md` before touching `src/a_conductor/**`.
7. Re-pin actual:
   - repository identity and remote;
   - worktree path;
   - branch;
   - HEAD;
   - `origin/main`;
   - dirty/untracked state;
   - Issue #215 state/claim;
   - PR #258 merge truth;
   - open PR file overlap;
   - relevant worktrees/claims/leases;
   - provider/runtime facts only when materially needed.
8. Confirm the execution worktree is exactly:
   `A:\GitHub\_worktrees\A-Wiki-Conductor-wo191-zra3`
9. Confirm branch is exactly:
   `feat/wo-p1-191-zra3-next-ready`
10. Treat the bootstrap SHA embedded in the WO as an observation, never as current authority.
11. If the worktree/claim/scope is unknown or conflicting, fail closed and continue only safe read-only investigation.
12. Write the recovered state and `SAFE_TO_MUTATE=YES/NO` to `runs/WO-P1-191/checkpoint.md`.

Do not ask the user to repeat context that Git/GitHub/repo/runtime can provide.

---

# 1. ROLE SPLIT

You are the **GLM-5.3 MAX implementation/debug/test lane**.

You own:

- deep repository archaeology inside this task;
- bounded implementation;
- RED-first test creation;
- iterative debugging/repair;
- adversarial identity/replay/restart testing;
- evidence collection;
- commit/push of the bounded candidate branch;
- durable result/checkpoint writing.

You do NOT own:

- architecture/trust-boundary overrides when the packet is ambiguous;
- final acceptance;
- independent review of your own implementation;
- merge/release;
- live credentials/secrets;
- destructive repository cleanup;
- mutation outside the exact task scope;
- weakening existing scheduler/lease/provider/review/continuity authority.

GPT-5.6 Sol is the integrator/reviewer and final merge authority.

---

# 2. PRIORITY

The current delivery priority is:

`ZRA-3 automatic NEXT READY -> GPT exact-SHA review/acceptance -> ZRA-4 bounded parallel continuation -> later roadmap`

Do not divert into unrelated SundayFamily MCP, ODP, AiPASS, UI, or general refactor work.

Worker/PowerShell resilience may be inspected read-only only after the ZRA-3 candidate is frozen, because it has a separate operational work order and authority boundary.

---

# 3. SUCCESS DEFINITION

The successful ZRA-3 path must prove:

1. a parent task is durably accepted/verified/closed under existing authority;
2. its graph transition exposes the correct newly READY successor;
3. ZRA-3 chooses at most one successor in this phase;
4. existing lease/provider/admission/dispatch gates remain authoritative;
5. the successor is dispatched automatically without human prompt copy/paste;
6. duplicate observations/ticks/restarts do not create duplicate physical work;
7. UNKNOWN/timeout/ambiguous side effects never blind-replay;
8. foreign identity cannot advance the graph;
9. dirty/HEAD-drift/claim-conflict/provider-stale cases fail closed;
10. durable restart/recovery reconstructs the same identity;
11. no second scheduler/job store/lease store/retry engine/review lifecycle is created;
12. a frozen exact SHA and deterministic evidence are produced for GPT review.

Primary metric: `human relay actions per accepted external-agent task = 0`.

---

# 4. OPERATING LOOP

Repeat this loop for each material stage:

`RECOVER -> REUSE -> TRACE -> POSITIVE CONTROL -> RED/FALSIFY -> IMPLEMENT -> GREEN -> RELATED VERIFY -> ADVERSARIAL VERIFY -> SELF-REVIEW -> CHECKPOINT -> ROUTE`

Rules:

- Never patch symptoms before tracing the authority/identity defect.
- Never repeat a test on unchanged code unless the run exercises a distinct environment/failure hypothesis.
- Prefer deterministic evidence over prose reasoning.
- When a defect recurs, turn it into executable prevention in this bounded scope.
- When blocked on mutation, continue read-only archaeology, test design, failure-model work, or result/checkpoint preparation that is still useful.
- Do not stop merely because one sub-step is blocked if another safe in-scope step remains.

---

# 5. PHASE A — AUTHORITY TRACE

Before coding, write a concise authority map to the checkpoint:

`durable result/review -> GoalCloseout completion truth -> graph lifecycle -> READY/frontier truth -> successor selection -> lease/admission -> GraphDispatch identity -> execution/reconcile`

For each arrow identify:

- current owner module/class/function;
- durable identity used;
- side effect, if any;
- idempotency/replay boundary;
- recovery behavior;
- why ZRA-3 can compose instead of duplicating it.

Explicitly verify that `next_ready_continuation` is owned by A-Conductor and that A-Wiki is not a second continuation engine.

If the correct design would require a new scheduler/store/lease/retry authority, STOP that design and reframe around existing authority.

---

# 6. PHASE B — RED-FIRST CORE MATRIX

Create `tests/test_next_ready_continuation.py` before implementation and prove the intended RED state.

Minimum cases:

- incomplete parent -> no dispatch;
- review PASS but closeout incomplete -> no dispatch;
- parent identity mismatch -> typed fail closed;
- no successor READY -> no-op;
- one successor READY -> one dispatch;
- >1 successor READY -> no accidental ZRA-4 fan-out;
- duplicate tick -> no duplicate;
- restart -> same durable identity/no duplicate;
- prior execution UNKNOWN -> reconcile/recovery, no blind replay;
- successor already represented -> no respawn;
- foreign completion -> no advancement;
- dependency/barrier blocked -> no dispatch;
- dirty worktree -> fail closed;
- HEAD drift -> fail closed;
- lease conflict -> fail closed;
- stale/missing provider admission -> fail closed;
- malformed/stale digest identity -> fail closed;
- crash after durable dispatch record -> restart reconciles;
- crash before durable dispatch record -> retry decision remains explicit/evidence-backed;
- valid success path requires no human relay.

Every negative case must have a valid positive twin when meaningful.

Record exact RED command/output summary in the checkpoint.

---

# 7. PHASE C — IMPLEMENT NEW-FILE CORE

Preferred source:

`src/a_conductor/next_ready_continuation.py`

Design constraints:

- deterministic and explicit types/enums/dataclasses where appropriate;
- injected existing authorities;
- no secrets;
- no global mutable process memory as replay authority;
- no scheduler implementation;
- no direct provider credential logic;
- no GitHub/network/subprocess/filesystem I/O in the pure decision core;
- typed reason/error codes;
- exact identity binding;
- bounded one-successor semantics for ZRA-3;
- restart/idempotency behavior derived from durable facts.

Use existing names/contracts where available. Do not invent near-duplicate vocabulary without a concrete need.

Run the focused test repeatedly only when code/hypothesis changes.

---

# 8. PHASE D — PRODUCTION COMPOSITION SEAM

After the new-file core is green, decide whether production already has a caller seam that can use it without editing another file.

If production wiring genuinely needs one existing file, choose **exactly one** from the whitelist in WO191 and write `runs/WO-P1-191/scope-selection.json` BEFORE the first edit.

The evidence file must include:

- chosen production file;
- chosen matching test file;
- why it is the smallest seam;
- exact current HEAD;
- open PR overlap recheck;
- active claim overlap recheck;
- call path before/after;
- why no second authority is introduced;
- expected rollback.

Then edit only that chosen existing production file and its matching test.

If more than one existing production file is truly required:

- do not widen silently;
- preserve the Phase-C candidate;
- write the required scope expansion as a bounded successor proposal in the result;
- continue other safe verification/read-only work.

---

# 9. PHASE E — FAULT / REPLAY / RESTART CAMPAIGN

Attack the candidate systematically.

## Identity attacks

- task ref same / task bytes changed;
- result ref same / result bytes changed;
- graph-run substitution;
- node substitution;
- attempt/generation substitution where applicable;
- stale completion from previous run;
- foreign provider/model/worker identity where applicable.

## Replay attacks

- duplicate caller invocation;
- duplicate scheduler/observer tick;
- caller timeout after durable effect;
- caller timeout before durable effect;
- stale process-local cache;
- process restart;
- store/service reconstruction;
- previous execution still alive/UNKNOWN.

## Authority attacks

- reviewer prose says accept but durable closeout not complete;
- dirty worktree;
- HEAD drift;
- lease ownership conflict;
- stale admission;
- blocked graph dependency;
- missing result destination;
- wrong graph/run/task ownership.

## Crash boundaries

Inject/reason about crash points around:

- completion observation;
- READY selection;
- durable dispatch identity creation;
- lease acquisition;
- provider admission;
- physical launch;
- result persistence;
- caller response.

For each crash boundary classify:

`SAFE_NOOP / RECONCILE / RECOVERY_REQUIRED / SAFE_RETRY / BLOCKED`

Never convert ambiguity into blind retry.

---

# 10. PHASE F — PROGRESSIVE VERIFICATION

Use the narrowest truthful ladder:

1. focused `test_next_ready_continuation.py`;
2. chosen composition-seam test if any;
3. GoalCloseout tests;
4. graph ready/scheduler/dispatch/lifecycle tests that share the call path;
5. parallel-ready tests only where ZRA-3 reuses its gate/dispatch behavior;
6. adversarial/restart tests;
7. compile/import check;
8. diff/scope/encoding/secret checks.

Do not repeatedly run the broad full suite merely because capacity remains.

If a related test fails:

- classify source defect vs stale expectation vs unrelated baseline failure;
- reproduce/minimize;
- repair only inside scope;
- add regression protection when material.

---

# 11. PHASE G — SELF-AUDIT, NOT SELF-ACCEPTANCE

Perform a hard self-audit of the exact diff:

- duplicated authority?
- hidden process-memory replay state?
- second scheduler/store/retry loop?
- ambiguous truthy/prose acceptance?
- stale SHA/ref reuse?
- missing recovery state?
- unsafe default?
- exception text leaking sensitive details?
- unbounded buffers/collections?
- platform-specific hidden assumptions?
- unnecessary changed files?
- test that passes without proving production behavior?

Fix deterministic findings in scope and rerun the affected verification.

This self-audit is implementation quality work only. It is NOT the independent R3 review.

---

# 12. PHASE H — FREEZE CANDIDATE

Before freezing:

- verify changed tracked files are only allowed scope;
- strict UTF-8 / no U+FFFD;
- `git diff --check`;
- credential/secret-like added-line scan;
- focused + required related tests green;
- exact branch/worktree identity correct;
- no unexplained untracked files;
- result/checkpoint current.

Then:

1. commit the bounded candidate;
2. push `feat/wo-p1-191-zra3-next-ready`;
3. record exact final SHA in `runs/WO-P1-191/result.md`;
4. record commands/results and unresolved findings;
5. set final status `CANDIDATE_FROZEN_FOR_GPT_REVIEW`;
6. STOP source mutation unless a new deterministic defect is found before review and the candidate is explicitly unfrozen/re-frozen with a new SHA;
7. never merge.

---

# 13. REMAINING CAPACITY AFTER FREEZE

If meaningful session capacity remains after a valid frozen candidate:

Priority order:

1. read-only independent-review preparation for GPT;
2. re-read exact frozen diff and create adversarial checklist;
3. shape ZRA-4 Issue #216 failure matrix/read-only implementation seam;
4. inspect WO156 Worker/PowerShell resilience read-only for reusable evidence;
5. inspect CI/test-economy opportunities directly relevant to ZRA-3/ZRA-4;
6. checkpoint everything needed for a fresh session to continue without chat memory.

Do not start unrelated feature work.

Do not mutate the frozen candidate merely to stay busy.

---

# 14. 20-HOUR CONTINUITY / CONTEXT ROLLOVER

Treat long execution as multiple resumable evidence windows, not one fragile context.

At each meaningful boundary update `runs/WO-P1-191/checkpoint.md` with:

- timestamp;
- exact HEAD;
- dirty state;
- current phase;
- completed evidence;
- current hypothesis;
- current blockers;
- claims/leases relevant to the task;
- exact next safe action;
- files currently mutable;
- files explicitly forbidden;
- commands/tests that should NOT be repeated without a changed hypothesis.

Before context compression/session rollover/provider limit:

- stop starting new destructive/non-idempotent actions;
- finish or classify in-flight actions;
- checkpoint exact state;
- make the next session resume from files, not memory.

Never fabricate token or time accounting.

---

# 15. PREEMPTION RULES

Checkpoint and preempt lower-value work when:

- Issue #215 claim/authority changes;
- origin/main changes in a way that affects this scope;
- an overlapping PR/claim appears;
- a deterministic P0/P1 defect invalidates current design;
- a required dependency becomes newly satisfied/unsatisfied;
- GPT/integrator posts a new bounded instruction to the durable WO/Issue;
- provider/runtime failure makes mutation evidence unreliable.

If preemption invalidates `SAFE_TO_MUTATE`, stop mutation immediately and continue only safe read-only work until reconciled.

---

# 16. STOP CONDITIONS

Stop mutation only for:

- `HUMAN_DECISION_REQUIRED`
- `AUTHORIZATION_REQUIRED`
- `OWNERSHIP_CONFLICT`
- `SAFETY_BLOCK`
- `RECOVERY_REQUIRED` with no safe recovery action
- `NO_SAFE_NEXT_ACTION`
- provider/context cutoff after durable checkpoint
- `CANDIDATE_FROZEN_FOR_GPT_REVIEW`

Ordinary debugging difficulty is not a stop condition.
A single blocked subtask is not a stop condition when useful read-only/in-scope work remains.

---

# 17. FINAL RESULT CONTRACT

Write `runs/WO-P1-191/result.md` with:

1. final status;
2. repo/worktree/branch/base/final SHA;
3. current origin/main at finish;
4. actual changed files;
5. authority/call-path map;
6. selected composition seam or `NEW_FILE_ONLY`;
7. RED evidence;
8. GREEN evidence;
9. related/adversarial verification;
10. duplicate/replay/restart verdicts;
11. crash-boundary classifications;
12. defects found and repaired;
13. unresolved P0/P1/P2/P3 findings;
14. scope/overlap/secret/encoding/diff audit;
15. claims acquired/released;
16. exact GPT independent-review checklist;
17. ZRA-4 readiness delta;
18. exact next safe action.

Allowed final statuses:

- `CANDIDATE_FROZEN_FOR_GPT_REVIEW`
- `BLOCKED_AUTHORITY`
- `BLOCKED_DEPENDENCY`
- `RECOVERY_REQUIRED`
- `NO_SAFE_NEXT_ACTION`

Do not report DONE merely because the session was long.

---

# 18. REMINDER

The goal is not to consume 20 hours.
The goal is to remove the human from the GPT↔GLM relay path safely and leave a deterministic, reviewable candidate that GPT-5.6 Sol can accept or reject by exact SHA.

Evidence beats confidence.
Durable state beats session memory.
One bounded authority path beats a second clever orchestration system.
