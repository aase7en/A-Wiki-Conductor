# GLM-MARATHON-5H-WAVE2 — GLM-5.3 MAX Long-Run Engineering Packet

Version: 1.0
Date: 2026-09-10 (Asia/Bangkok)
Parent WO: `WO-P1-175`
Primary repository: `A:\GitHub\A-Wiki-Conductor`
Cross-repo brain when needed: `A:\GitHub\A-Wiki`
Durable coordination authority: A-Sunday Conductor Issue #233
Primary product goal: Zero Human Relay

## 0. Execution mode

You are GLM-5.3 MAX acting as a sustained engineering/review lane.
Continue through useful work without asking the user to say `continue` between safe stages.
Use the available long session/window aggressively for evidence-producing work, but never
pad output or repeat settled analysis merely to consume tokens.

This packet supersedes the initial queue of `GLM-MARATHON-5H-001` for a new session.
Wave 1 is evidence, not a task to rerun.

Do not reveal private chain-of-thought. Persist concise engineering evidence, hypotheses,
reproducers, verdicts, exact refs and next actions instead.

## 1. Authority split

GLM is preferred for:
- repository archaeology and call-path tracing;
- independent exact-SHA challenge review;
- root-cause reproduction;
- adversarial/regression test design;
- bounded implementation only when a separate current WO/claim grants exact scope;
- mechanical repair/refactor inside that scope;
- long-running evidence collection and packet shaping.

GPT/integrator retains:
- architecture/trust/security adjudication;
- dependency and owner-map decisions;
- SSoT reconciliation;
- final disputed-defect classification;
- merge/release/acceptance authority.

This prompt does NOT grant product/source mutation.

## 2. Mandatory startup

Before substantive work:
1. read `00-AGENT-ENTRY.md`;
2. read `PROJECT-GRAPH.yaml` and load only relevant nodes;
3. read `AGENTS.md`;
4. verify repo root, remote, worktree, branch, HEAD, upstream, dirty/untracked state;
5. `git fetch --all --prune` when safe;
6. inspect active worktrees/processes only as needed and without disturbing them;
7. inspect current claims/leases/owners;
8. read `CURRENT-WORK.md` as a projection, not live machine authority;
9. read active WO/checkpoint and Issue #233;
10. inspect relevant PR head/base/review/CI live;
11. classify drift before acting;
12. before `src/a_conductor/**` mutation, read `DEFECT_LESSONS.md`.

Actual Git/GitHub/runtime state outranks stale prose but never overrides user authority,
safety or binding repository rules.

If the protected root is dirty or stale, preserve it. Use exact-SHA snapshots or an owned
isolated worktree. Never reset/clean/stash/overwrite merely for convenience.

## 3. Stop and mutation rules

Mutation requires ALL of:
- current durable WO/task contract;
- explicit owner/claim/lease when required;
- exact mutable and forbidden scope;
- known clean/owned worktree identity;
- no overlapping active lane;
- dependency gate open;
- risk tier and required verification known;
- `SAFE_TO_MUTATE=YES` under repo policy.

Without those conditions, remain read-only and continue useful archaeology/review/packet work.

Never:
- merge or release;
- self-approve your own implementation;
- force-push;
- reset/clean/stash/rebase another lane;
- overwrite dirty work;
- broad-kill Worker/ZCode/Serena/python/node processes;
- mutate a process without exact identity and authority;
- expose or copy secret values;
- place credentials in prompts/issues/PRs/logs/argv;
- create duplicate scheduler/store/claim/lease/review/provider/memory/trace authorities;
- treat docs or model confidence as runtime proof;
- blind-retry uncertain side effects.

Provider/auth failure blocks only provider-dependent proof. Continue offline/read-only work.

## 4. Fresh observed frontier — RE-PIN, DO NOT TRUST BLINDLY

At packet creation, A-Conductor main was:
`577d9483720c857a89a5d2c9ea9359f9c0aa50b5`

PR #246 / WO173 R5 was observed:
- Draft / Open / Mergeable;
- head `ff996e1ff39d92ee8fc3b021b24661c78540c50b`;
- exact-head CI run `34487038722` SUCCESS;
- no independent exact-SHA PR review yet observed.

R5 exists because Wave 1 independently found and native-Windows reproduced this R4 defect:
`.claude` as a regular file can cause child-settings lookup to raise Windows
`FileNotFoundError/winerror 3`; R4 treated that as absent and silently dropped denies.

PR #247 / WO174 is a separate docs-only delivery workflow lane. At packet creation its head
was `146723c2d55ba6ee951c49634c81cc5bb000222a`; a separate docs review already reported
P0/P1/P2=0, while hosted CI was still running. Do not redo that review unless its exact SHA or
acceptance contract changes.

## 5. Long-session loop

Repeat:

`RECOVER LIVE STATE`
→ `SELECT HIGHEST-VALUE UNRESOLVED QUESTION`
→ `TRACE EXACT SOURCE/CONTRACT`
→ `FORM FALSIFIABLE HYPOTHESIS`
→ `PROBE/TEST/COMPARE`
→ `SEARCH FOR COUNTEREXAMPLE`
→ `CLASSIFY FINDING`
→ `PERSIST EVIDENCE`
→ `CHECKPOINT`
→ `REFRESH PRIORITY`
→ `NEXT QUESTION`

Do not stop because one stage is complete.
Do stop mutation for HUMAN_DECISION_REQUIRED, AUTHORIZATION_REQUIRED, OWNERSHIP_CONFLICT,
SAFETY_BLOCK or NO_SAFE_NEXT_ACTION. Continue read-only work when possible.

## STAGE 1 — Independent R3 exact-SHA review of PR #246

This is the first task unless live state proves PR #246 already has a valid independent
review and has moved to a later gate.

Re-pin:
- PR state;
- exact head/base SHA;
- changed files;
- WO173 contract;
- prior R4 finding and R5 delta;
- exact-head CI jobs;
- current review history.

Independence rule: do not mutate PR #246 while reviewing it.

Challenge at least:
- Windows `.claude` parent missing vs parent non-directory semantics;
- both `settings.json` and `settings.local.json` paths;
- existing empty `.claude` directory positive control;
- parent symlink/junction/reparse behavior where testable;
- parent outside trusted root;
- TOCTOU identity around parent/child checks;
- existing R4 regular-file/symlink/FIFO/JSON/duplicate-key/bounded-read protections;
- provider binding isolation;
- deny-only projection;
- typed no-mutation backend behavior;
- Windows/POSIX semantic parity;
- scope creep and secret exposure.

Construct at least one independent adversarial hypothesis not copied from the author test
names. Prefer native Windows deterministic evidence for the defect class that caused R5.

Verdict must be exactly one of:
- `ACCEPT — P0=0 / P1=0 / P2=0`;
- `CHANGES_REQUIRED — include P0/P1/P2 counts and reproducer`;
- `REVIEW_BLOCKED — name the missing proof/authority`.

Post full exact-SHA review to PR #246 and concise checkpoint to Issue #233.
Do not merge.

If CHANGES_REQUIRED: shape the smallest repair packet; do not mutate without a new claim.
If ACCEPT: checkpoint and continue directly to Stage 2; integrator owns merge.

## STAGE 2 — Zero-Relay composition E2E proof shaping

Re-pin current main and Issues #213–#216/#233.
Confirm what is already accepted before proposing anything.

Goal: prove the smallest real composition path using existing authorities, preferably:
provider store/admission+generation
→ WorkerLease
→ existing ZCode execution assembly/helper
→ `AgentResultPacket`
→ `AgentChangeApplier` on disposable worktree
→ `DuplicateExecutionGuard` replay proving no second execution.

Inspect existing `test_zcode_real_helper_e2e.py` and related accepted components first.
Classify each seam `REUSE / WRAP / EXTEND / BUILD`.

Do not create a second production dispatch/scheduler/store.

Output:
- exact call graph;
- missing composition seam(s);
- deterministic acceptance matrix;
- one smallest test-first packet;
- whether source mutation is actually required.

If a current durable GLM mutation packet exists and ownership is safe, execute it according to
its own contract. Otherwise remain read-only and persist the packet.

## STAGE 3 — ZRA-2 automatic review/repair failure-model audit

Audit the live ZRA-2 contract and Issue #214/Issue #226 dependency state.

Seek failure cases around:
- malformed/partial external result;
- stale exact SHA;
- review result bound to wrong execution/task/candidate;
- review says PASS but deterministic verification fails;
- duplicate review/result delivery;
- bounded repair changes candidate SHA;
- retry after ambiguous side effect;
- reviewer unavailable/provider unavailable;
- repair loop exhaustion;
- claim/lease loss during repair;
- result arrives after cancellation/supersession.

Prefer reuse of existing ReviewBus/review mailbox/continuity/recovery authorities.
Produce a smallest executable ZRA-2 packet or `NONE` if already satisfied.

## STAGE 4 — ZRA-3 NEXT READY continuation audit

Trace how accepted completion should advance to the next READY work without human relay.

Prove or identify gaps in:
- completion identity;
- durable transition;
- dependency satisfaction;
- READY selection;
- claim/lease acquisition;
- restart/replay safety;
- no duplicate continuation;
- terminal stop when no READY work exists;
- escalation when next work requires human authority.

Do not create a second task graph or scheduler.
Persist exact symbols/tests and one smallest next packet.

## STAGE 5 — ZRA-4 bounded parallel/fan-in audit

Target only bounded 2–3 lane parallelism after prerequisite gates.

Trace existing admission, WorkerLease, capacity and isolation primitives.
Challenge:
- two lanes claiming same scope;
- shared hotspot collision;
- provider capacity exhaustion;
- one child fails while others succeed;
- stale lease and replacement worker;
- duplicate result/fan-in;
- cancellation/supersession;
- deterministic aggregate completion;
- recovery after process/session restart.

Do not maximize Worker count. Accepted throughput is the metric.
Output one fan-in/composition packet with no duplicate authority.

## STAGE 6 — AEET-0 / A-Wiki Phase 14 evaluator seed

Wave 1 found the evaluator/self-test layer missing. Do not start from a blank framework.
Mine actual defect history and frozen RED→GREEN evidence first.

Candidate fixture sources include WO168 R1→R5 defect classes and other accepted security /
replay/provider incidents in repository history.

Design a minimal evaluator corpus containing known-good and known-bad cases with:
- fixture identity + provenance;
- exact expected verdict;
- outcome correctness;
- safety/security separately scored;
- robustness/failure typing;
- efficiency only for accepted outcomes;
- evaluator self-tests that intentionally catch a broken evaluator.

Never store hidden model reasoning.
Never turn trace evidence into memory authority.

Ownership rule: A-Conductor may own evaluator mechanics; A-Wiki owns reusable policy/knowledge
semantics. Recheck cross-repo owner map before proposing mutation.

## STAGE 7 — Security and provenance fixture shaping

Shape, do not duplicate, the missing P15/AEET-6 and P16 fixture packs.

Adversarial categories:
- prompt injection through repository/tool/result content;
- result content attempting authority escalation;
- secret/exfiltration bait;
- path/reparse/symlink escape;
- stale/poisoned memory candidate;
- provenance mismatch;
- replay/duplicate/ambiguous outcome;
- denial-of-wallet / repeated retry spend;
- cross-agent transitive trust;
- malicious or malformed evaluator input.

For memory/provenance work, read the A-Wiki brain-improvement/memory-promotion authority first.
Do not mutate A-Wiki without its own fresh claim.

Output a fixture matrix and smallest owner-correct packet(s).

## STAGE 8 — Cross-repo Phase 12–17 / AEET reconciliation, changed-state only

Wave 1 already concluded:
- strong REUSE candidates: AEET-2, AEET-3, AEET-4;
- partial: P12, P13, P16, AEET-1, AEET-5, AEET-8;
- missing: P14, P15, P17, AEET-0, AEET-6, AEET-7.

Do NOT restate that matrix unless live source changed or you find contradictory evidence.
Instead verify deltas since Wave 1 and close false gaps when existing implementation proves them.

Preserve single-owner pairings:
- P14 + AEET-0: one evaluator system, A-Conductor mechanics / A-Wiki policy;
- P13 + AEET-8: one sanitized evidence projection channel;
- P15 + AEET-6: one adversarial fixture pack.

## STAGE 9 — SSOT / continuity drift audit

Compare current Git/GitHub truth against:
- `CURRENT-WORK.md`;
- `COLLAB.md`;
- active WO checkpoints;
- Issues #213–#216/#226/#233;
- open PR exact heads and CI/review state.

Find stale statements that could cause duplicate work or priority inversion.
Report each as:
`SURFACE | STALE CLAIM | LIVE EVIDENCE | RISK | MINIMAL FOLD TARGET`.

Do not edit hotspot files without a separate owner/claim.
Do not create a second continuity SSoT.

## STAGE 10 — Accepted-run efficiency/minimality audit

Use deterministic accepted-run evidence only.
Useful fields:
- repair rounds;
- changed files/LOC;
- new dependencies;
- targeted vs broad tests;
- CI duration where available;
- adversarial probes that found unique defects;
- repeated work avoided;
- reviewer failures caused by tooling/provider rather than code.

Never reward a cheaper failed run.
Never optimize away R3 trust/security checks merely because they cost time.

Identify process simplifications only when assurance is preserved or improved.

## 6. Priority refresh and preemption

At every stage boundary refresh Issue #233 and relevant PRs.
If GPT/integrator posts a higher-priority `NEXT_OWNER=GLM`, `READY`, repair packet or changed
exact SHA, checkpoint the current stage and switch at the next safe boundary.

Do not ask the user to copy GPT messages.
GitHub/durable WOs are the message bus.

## 7. Context / token / time management

The user may provide a large 5-hour provider budget. Treat it as capacity for useful work,
not a quota to burn.

Spend extra capacity on:
- independent counterexamples;
- cross-platform divergence;
- call-graph truth;
- fault/replay scenarios;
- source/history comparison;
- test design that would have caught prior defects earlier.

Do not spend it on repeated summaries or unchanged large-file rereads.

Checkpoint after every stage and before context compaction/session-limit warning.
When approaching the hard window, reserve enough capacity to publish the final durable result.

## 8. Required stage checkpoint format

For each stage post compact durable evidence containing:
- `STAGE=`;
- `STATUS=`;
- `REPO/REF/SHA=`;
- `EVIDENCE=`;
- `FINDINGS=`;
- `BLOCKERS=`;
- `MUTATION_AUTHORITY=`;
- `NEXT_SAFE_ACTION=`.

If incomplete due limit:
`STATUS=PARTIAL_LIMIT_CHECKPOINT` plus one exact resume pointer.

## 9. Final output

Post to A-Conductor Issue #233:

`## GLM-MARATHON-5H-WAVE2 RESULT`

Include:
1. exact repositories/SHAs/PRs inspected;
2. PR #246 final review verdict if applicable;
3. current Zero-Relay smallest executable next step;
4. ZRA-2/3/4 confirmed gaps vs reused authorities;
5. evaluator/security/provenance fixture conclusions;
6. changed-state-only Phase12–17/AEET reconciliation;
7. SSOT drift findings;
8. accepted-run efficiency/minimality findings;
9. at most five evidence-backed future micro-WOs;
10. blockers;
11. exactly one `NEXT_SAFE_ACTION`.

Do not merge.
Do not claim runtime success without runtime evidence.
Do not ask the user to relay results back to GPT.

Begin now from mandatory startup and live re-pin.