# GLM MARATHON WAVE 7 — 1,536-UNIT SUSTAINED DELIVERY GOAL TREE

## ROOT `/goal`

Operate as a sustained bounded GLM-5.3/ZCode execution lane for A-Sunday Conductor. This is a long-horizon delivery campaign, not a single review or archaeology task.

Run the matrix below as nested `/goal`s. Continue automatically across families and programs for several hours if capacity permits. Do not ask the human to type `continue` between safe goals. Do not require the human to relay results to GPT; checkpoint durable results to the declared repository/Issue/PR surfaces.

The purpose is productive accepted evidence and delivery. **Never burn tokens by repeating unchanged reads/tests or padding output.** When a unit is already proven by exact current evidence, mark it `CONSUMED_PROVEN` and route forward.

### Mandatory cold start

Before substantive work:
1. Read `00-AGENT-ENTRY.md`.
2. Read `PROJECT-GRAPH.yaml` and only routed task-relevant policy nodes.
3. Read `AGENTS.md`.
4. Re-pin actual repo/remote/worktree/branch/HEAD/dirty state.
5. Read `CURRENT-WORK.md` as a projection, not machine authority.
6. Read the current WO/claim for any mutable child before mutation.
7. For source mutation, read `DEFECT_LESSONS.md` first.
8. Re-pin Issue #233 plus relevant #213/#214/#215/#216 and open PR/CI state.
9. Compare actual state with this packet's bootstrap facts. Actual current state wins where the packet is stale, subject to user/safety/binding policy.

## CURRENT BOOTSTRAP FRONTIER — RE-PIN, DO NOT TRUST BLINDLY

Packet base: `f964afced5fbe0905c3667b1a6552a6fdafc09cb`.

At packet authoring time:
- WO181 / PR #254 was merged and post-main CI `34543995776` was SUCCESS.
- WO183 / PR #255 was independently ACCEPTED, CI green, then expected-head merged as `f964afced5fbe0905c3667b1a6552a6fdafc09cb`.
- post-main CI for `f964afc...` may still be running; verify it before treating the new main as release-verified.
- WO179 `ZRA-1-LIVE-3` is GPT/integrator-owned live execution. GLM may independently audit its artifacts/result after it occurs but MUST NOT issue/retry the live provider turn.
- existing WO165 / Issue #214 is the canonical ZRA-2 implementation lane. Reuse/resume it after its dependency gate is actually satisfied; do not create another ZRA-2.
- Wave 6 / WO184 / PR #256 is a consumed transport packet when `STATUS=WAVE6_COMPLETE` is durable; do not rerun it.

## GLOBAL AUTHORITY INVARIANTS

- `SAFE_TO_MUTATE=YES` is required for every mutable child.
- A root `/goal` never grants blanket source/test/runtime mutation authority.
- Never steal/rebind/reset/overwrite another active lane.
- Preserve dirty work; no silent reset/clean/stash/rebase/force-push.
- No broad process kill.
- No real secret values in output, argv, GitHub, task packets, result packets, logs, or committed files.
- Do not broad-search live `%USERPROFILE%\.zcode\v2`.
- UNKNOWN/timeout/ambiguous external effects never trigger blind redispatch.
- Review result is evidence, not mutation/merge authority.
- R2/R3 authors cannot be their own sole independent reviewer.
- GLM does not merge or release its own candidate.
- Reuse authorities before WRAP; WRAP before EXTEND; EXTEND before NEW.
- Do not create a second scheduler, job store, lease store, provider store, ReviewBus, retry engine, memory authority, or trace authority.

## STANDARD FAMILY PROTOCOL — 8 CHILD `/goal`s

For every family `Pxx-Fyy`, execute these children unless current exact evidence proves one is unnecessary. A skipped child must carry a reason and evidence reference.

### A — RECOVER / DELTA FILTER
Re-pin exact current state, prior Wave-6 evidence and relevant claims. State what materially changed. Do not repeat unchanged archaeology.

### B — REUSE + AUTHORITY MAP
Locate existing production/test/policy authorities and classify the intended action `REUSE | WRAP | EXTEND | REPLACE | NEW`. Identify owner/claim and mutable overlap before suggesting build work.

### C — FALSIFY + POSITIVE CONTROL
Write the strongest plausible failure hypothesis for this family and define a benign positive twin. Try to falsify the current claim with deterministic evidence before proposing a fix.

### D — TRACE / PROBE
Run the cheapest safe deterministic trace/probe/test that can change the decision. Prefer existing fixtures, fake providers, loopback endpoints, disposable DB/worktree and exact-SHA snapshots. Never use a real credential merely to gain confidence.

### E — DELIVER
Produce useful durable output. If mutation is both necessary and authorized, use a separate bounded WO/claim and implement RED-first. Otherwise deliver a review verdict, task packet, fault matrix, fixture spec, reuse decision, or `PROVEN_NO_GAP` evidence. Do not manufacture code changes merely to count a unit.

### F — VERIFY / ADVERSARIAL
Run focused + related verification proportional to risk. For frozen R2/R3 candidates, challenge exact SHA independently; for R0/R1 use the shortest truthful assurance ladder. Include secret/diff/UTF-8/scope checks when relevant.

### G — CHECKPOINT
Persist changed-state-only result to the WO/result path and/or relevant Issue/PR. Include exact repo/ref/SHA, owner/claim, evidence, unresolved blockers and status. Do not paste large repetitive logs.

### H — ROUTE / REPLENISH
Choose `DONE_PROVEN | ACCEPT | CHANGES_REQUIRED | READY_FOR_CLAIM | BLOCKED_WITH_OWNER | RECOVERY_REQUIRED | DEFERRED | DROP`. Queue the next dependency-safe family. A newly proven material finding may spawn `R1..R8` recursive subgoals using the same A-H protocol. Do not recurse on speculation.

## PREEMPTION ORDER

At every family boundary, preempt the queue for:
1. newly frozen R3 candidate needing independent exact-SHA review;
2. P0/P1 security/credential/process/durable-state finding;
3. Zero-Relay critical-path state change;
4. ambiguous execution requiring recovery reconciliation;
5. only then return to normal family order.

After preemption, checkpoint and return to the previous queue automatically.

# PROGRAM P00 — LIVE ZERO-RELAY ACCEPTANCE FRONTIER

P00-F00 current-main/post-main closure and ancestry truth
P00-F01 WO179 LIVE-3 authorization boundary audit — GLM must not execute it
P00-F02 LIVE-3 result/job/execution/admission/lease reconciliation after owner run
P00-F03 LIVE-3 process/PID/orphan truth
P00-F04 LIVE-3 provider/model/baseURL materialization and attestation evidence
P00-F05 LIVE-3 secret confinement and ambient-provider exclusion
P00-F06 LIVE-3 task/result/digest identity proof
P00-F07 LIVE-3 same-identity replay/dedup proof without second provider call
P00-F08 ZRA-1 acceptance matrix adjudication
P00-F09 ZRA-1 failure classification and recovery-only path if non-positive
P00-F10 ZCode bundle version drift at live-proof time
P00-F11 provider readiness/quota/health evidence freshness
P00-F12 consumed Wave-6/WO184 closeout classification
P00-F13 consumed packet PR hygiene without deleting evidence
P00-F14 Zero-Relay durable checkpoint completeness
P00-F15 dependency handoff from ZRA-1 to canonical WO165/ZRA-2

# PROGRAM P01 — WO165 / ZRA-2 AUTOMATIC REVIEW + EXACTLY-ONE REPAIR

P01-F00 resume existing WO165 identity and refresh stale baseline without duplicating lane
P01-F01 Phase-A pure state-machine RED matrix
P01-F02 durable TaskPacketFile identity fence
P01-F03 durable result ref/hash/evidence identity fence
P01-F04 author execution vs reviewer execution independence fence
P01-F05 review timeout/truncation/identity mismatch -> recovery behavior
P01-F06 accepted-first-result path with zero repair generations
P01-F07 first rejection -> exactly one deterministic repair request
P01-F08 AgentRepairRequest + build_repair_task_markdown reuse/materialization
P01-F09 deterministic repair packet path collision/idempotence
P01-F10 replacement-result destination distinctness and source-result binding
P01-F11 repaired result verification and rereview path
P01-F12 second rejection -> terminal rejected, no third execution
P01-F13 UNKNOWN execution -> RECOVERY_REQUIRED, no repair/no retry
P01-F14 ReviewMailboxResultReader/Forwarder composition without second review lifecycle
P01-F15 GoalCloseout handoff only after identity-fenced exact-head review PASS

# PROGRAM P02 — ZRA-3 NEXT READY + ZRA-4 PARALLEL/FAN-IN

P02-F00 ZRA-3 canonical dependency-graph input reuse
P02-F01 NEXT READY deterministic selection contract
P02-F02 blocked dependency exclusion
P02-F03 stale claim/lease exclusion
P02-F04 dirty worktree exclusion
P02-F05 provider readiness/admission exclusion
P02-F06 deterministic tie-breaking and replay stability
P02-F07 zero-human transition from one completed goal to next task packet
P02-F08 ZRA-3 crash/restart continuation
P02-F09 ZRA-4 bounded 2-agent split contract
P02-F10 ZRA-4 bounded 3-agent split contract
P02-F11 mutable-scope disjointness proof
P02-F12 fan-in result identity + completion barrier
P02-F13 fan-in partial-write ambiguity and recovery
P02-F14 one-child failure while sibling succeeds
P02-F15 fan-in acceptance/closeout without implicit parent completion

# PROGRAM P03 — AGENT SECURITY / PROMPT INJECTION / EXFILTRATION

P03-F00 repository-content indirect prompt injection fixture
P03-F01 README/comment malicious instruction fixture + benign twin
P03-F02 tool-output injection fixture
P03-F03 changed/malicious tool metadata fixture
P03-F04 authority-escalation text from untrusted artifact
P03-F05 request to reveal secret through stdout/result artifact
P03-F06 request to copy secret into GitHub/comment/task packet
P03-F07 argv/environment secret exfiltration boundary
P03-F08 denial-of-wallet/runaway nested-goal attack
P03-F09 infinite self-replenishment protection
P03-F10 memory poisoning / false durable-state assertion
P03-F11 inter-agent taint propagation
P03-F12 forged reviewer identity
P03-F13 forged task/result SHA identity
P03-F14 forged claim/lease/owner evidence
P03-F15 consolidated fake-first agent-security fixture pack with positive controls

# PROGRAM P04 — ZCODE / PROVIDER / MODEL / PROTOCOL TRUST

P04-F00 installed ZCode bundle identity and upgrade contract
P04-F01 runtimeModel provider/model/baseURL exact binding
P04-F02 runtimeModel duplicate-key hardening regression
P04-F03 decoded unicode key alias/duplicate regression
P04-F04 session/create attestation missing/mismatch behavior
P04-F05 ambient provider/default model fallback exclusion
P04-F06 credential env-reference-only materialization
P04-F07 credential delivery-key consistency
P04-F08 provider snapshot generation drift before spawn
P04-F09 provider observation freshness and readiness semantics
P04-F10 admission provider/generation/batch/execution identity
P04-F11 custom/unsupported protocol fail-closed semantics
P04-F12 loopback HTTP vs external HTTPS endpoint policy
P04-F13 protocol frame/output size and malformed message handling
P04-F14 thought-level/model-variant compatibility
P04-F15 bundle compatibility guard design using behavior probe, not hash-only authority

# PROGRAM P05 — PROCESS OWNERSHIP / FAILURE / RECOVERY

P05-F00 child identity PID/executable/parent/creation-time binding
P05-F01 PID reuse rejection
P05-F02 supervisor PID reuse rejection
P05-F03 child exits before durable result
P05-F04 supervisor exits before durable result
P05-F05 result exists but process status is ambiguous
P05-F06 process alive but timeout transport lost
P05-F07 result missing -> RecoveryReconciliationService behavior
P05-F08 exact UNKNOWN -> job BLOCKED/RECOVERY_REQUIRED semantics
P05-F09 no broad-kill invariant under failure
P05-F10 natural shutdown and terminal-exit ordering
P05-F11 restart dedup/no-respawn after terminal success
P05-F12 output flood/backpressure/truncation
P05-F13 process ownership release only after terminal truth
P05-F14 admission + lease release idempotence
P05-F15 crash/failure path with SYSTEMROOT-only Windows environment

# PROGRAM P06 — SQLITE / CAS / LEASE / CONCURRENCY DURABILITY

P06-F00 SQLiteJobStore transition/version CAS
P06-F01 execution-store terminal-state monotonicity
P06-F02 ordered event/checkpoint durability
P06-F03 concurrent provider admission max-concurrency race
P06-F04 admission release/expiry race
P06-F05 WorkerLeaseBroker acquisition conflict
P06-F06 lease expiry/reconcile_stale fencing
P06-F07 session/task/worker mismatch release refusal
P06-F08 mutable scope vs allowed/forbidden scope validation
P06-F09 dirty/head/project mismatch before execution
P06-F10 DB reopen/restart idempotence
P06-F11 partial transaction failure and recovery classification
P06-F12 duplicate execution identity collision
P06-F13 duplicate job/task identity collision
P06-F14 concurrent fan-in write ordering
P06-F15 disposable live-schema-copy compatibility without mutating installed DB

# PROGRAM P07 — REVIEW / EVIDENCE / EVALUATOR / DEFECT MEMORY

P07-F00 exact-SHA review packet integrity
P07-F01 reviewer independence proof and masquerade challenge
P07-F02 positive-control-first adversarial probe rule
P07-F03 malformed/no-op probe self-detection fixture
P07-F04 review result task/provider/model/head/hash binding
P07-F05 review response spoof/invalid-schema handling
P07-F06 review transport timeout/truncation recovery
P07-F07 blocker finding addressed-vs-verified semantics
P07-F08 evaluator known-good corpus
P07-F09 evaluator known-bad corpus
P07-F10 evaluator self-tests ES-1..ES-4
P07-F11 executable defect-memory promotion criteria
P07-F12 duplicate-key/parser-class reusable fixture policy
P07-F13 defect recurrence scoreboard by executable guard
P07-F14 evidence packet minimality and secret scan
P07-F15 review latency/repair-round/defect-yield measurement without fake precision

# PROGRAM P08 — WINDOWS / POSIX / FILESYSTEM / VERSION COMPATIBILITY

P08-F00 SYSTEMROOT minimal Windows child environment invariant
P08-F01 Windows environment case-insensitive aliasing
P08-F02 Windows long-path behavior
P08-F03 junction/reparse tracked regression port
P08-F04 symlink path-boundary behavior
P08-F05 file-vs-directory parent boundary
P08-F06 descriptor identity change between stat/read
P08-F07 Unicode/UTF-8 strict decoding
P08-F08 POSIX parity for Windows-only branch behavior
P08-F09 executable path normalization/casefold
P08-F10 argv/command-line budget on Windows
P08-F11 temp-file lifecycle and cleanup semantics
P08-F12 crashpad/TEMP dependency challenge without widening environment blindly
P08-F13 ZCode bundle upgrade schema/behavior probe
P08-F14 Python/Node/Electron version compatibility
P08-F15 clean host vs dirty host deterministic test parity

# PROGRAM P09 — CONTINUITY / SSOT / CLAIM / CROSS-REPO GOVERNANCE

P09-F00 CURRENT-WORK staleness changed-state audit
P09-F01 Issue #213 ZRA-1 claim aging/closeout
P09-F02 Issue #214 WO165/ZRA-2 claim refresh
P09-F03 Issues #215/#216 dependency status refresh
P09-F04 consumed Wave packet PR closeout classification
P09-F05 stale branches/worktrees evidence-preserving cleanup candidates
P09-F06 cold-start GPT integrator drill
P09-F07 cold-start GLM executor drill
P09-F08 deterministic operator drill without chat history
P09-F09 handoff/COLLAB projection drift
P09-F10 claim lease owner overlap detector evidence
P09-F11 A-Wiki/A-Conductor owner-map revalidation
P09-F12 cross-repo task/result/review authority duplication audit
P09-F13 private Drive/secrets boundary audit
P09-F14 memory/provenance quarantine boundary
P09-F15 single-writer SSoT fold packet with exact current facts

# PROGRAM P10 — CI / RELEASE / TEST ECONOMY / OBSERVABILITY

P10-F00 focused-first test ladder correctness
P10-F01 hosted Windows critical-path duration
P10-F02 Ubuntu/macOS smoke signal quality
P10-F03 full-CI-only defect yield measurement
P10-F04 flaky/ambiguous test classification
P10-F05 test process ownership on timeout
P10-F06 packaging/install smoke relation to changed scope
P10-F07 exact-head CI vs base-drift handling
P10-F08 expected-head merge fencing
P10-F09 post-main ancestry/tree verification
P10-F10 post-main CI release gate
P10-F11 observability event identity completeness
P10-F12 secret/redaction telemetry checks
P10-F13 run artifact retention/minimality
P10-F14 accepted-merge lead-time scoreboard
P10-F15 WIP/parallelism throughput based on accepted output, not active-agent count

# PROGRAM P11 — ARCHITECTURE SIMPLIFICATION / ROADMAP / REPLENISHMENT

P11-F00 reuse-before-build audit of next Zero-Relay seam
P11-F01 second-authority detector for scheduler/store/lease/review/provider/memory/trace
P11-F02 dead preview/obsolete branch code vs current production authority
P11-F03 old packet supersession/closeout map
P11-F04 ZRA-5/ODP gate after ZRA-4 only
P11-F05 provider settings roadmap relevance after current runtime binding
P11-F06 AEET roadmap gate and smallest executable seed
P11-F07 security-fixture pack delivery packet readiness
P11-F08 bundle compatibility guard delivery packet readiness
P11-F09 tracked junction/reparse fixture delivery packet readiness
P11-F10 cross-platform next-risk forecast
P11-F11 top recurring defect classes ranked by recurrence × blast radius
P11-F12 architecture simplifications that delete process/authority rather than add layers
P11-F13 maximum 20 dependency-safe micro-WOs
P11-F14 explicit DO_NOT_BUILD / DROP list
P11-F15 final Wave-8 replenishment queue derived only from proven unresolved work

## RECURSIVE FINDING GOALS — R1..R8

A family may spawn `Pxx-Fyy-R1` through `R8` only after a material finding is proven. Each recursive goal repeats A-H with narrower scope. Stop recursion when:
- evidence falsifies the finding;
- existing coverage already closes it;
- owner/dependency blocks mutation;
- a bounded successor WO is ready;
- or depth 8 is reached.

Never recursively restate the same finding with different wording.

## MUTABLE DELIVERY SLOT RULE

When a family proves an implementation/test/docs change is both useful and dependency-ready:
1. search actual Issues/PRs/branches/worktrees for existing ownership;
2. reuse compatible existing WO if present;
3. otherwise allocate an unused WO identity;
4. create fresh isolated worktree/branch from current authoritative base;
5. checkpoint owner/claim/allowed+forbidden scope;
6. rerun overlap/mutation gate;
7. RED-first for behavior changes;
8. run focused/related/adversarial verification;
9. freeze exact SHA and release implementation claim;
10. R2/R3: independent reviewer must be a different lane/session/author;
11. no GLM self-merge; GPT/integrator accepts/merges/releases.

If the task cannot satisfy this sequence, deliver a shaped packet instead of mutating.

## QUEUE REPLENISHMENT AFTER 1,536 BASE UNITS

If all base families are dispositioned and provider/session capacity remains, do NOT idle and do NOT restart completed families. Build a replenishment queue from only:
- unresolved P0/P1/P2 findings;
- newly frozen independent-review candidates;
- READY bounded WOs whose owners/dependencies permit work;
- executable defect-memory gaps with deterministic reproducer;
- current SSoT/claim drift capable of causing duplicate/unsafe work;
- cross-platform/runtime incompatibilities proven by fresh evidence;
- ZRA-2/3/4 successor work made READY during this Wave.

Assign replenishment IDs `X001..X999`. Each uses A-H and may recurse to depth 8. If no such productive work exists, stop with `NO_SAFE_NEXT_ACTION`; do not create speculative chores to consume token budget.

## MULTI-SESSION CHECKPOINT CONTRACT

Before context/session limit:
- checkpoint `STATUS=PARTIAL_LIMIT_CHECKPOINT`;
- exact repo/ref/SHA/main;
- completed family/replenishment IDs;
- current mutable claims and owners;
- exact evidence/result paths;
- blockers/dependencies;
- next safe family ID;
- one exact resume pointer.

A new session must cold-start from that checkpoint and skip completed families unless actual material state changed.

## FINAL RESULT CONTRACT

Publish one durable Wave-7 result containing:
1. exact repos/branches/SHAs/PRs/CI inspected;
2. base families dispositioned / 192;
3. base actions dispositioned / 1,536;
4. recursive/replenishment goals completed;
5. implementation/test/docs candidates created and frozen;
6. independent exact-SHA reviews performed with P0/P1/P2/P3 counts;
7. merges explicitly **not** performed by GLM;
8. ZRA-1/ZRA-2/ZRA-3/ZRA-4 maturity delta;
9. security/exfil/injection delta;
10. process/recovery/durability/concurrency delta;
11. Windows/POSIX/filesystem/version delta;
12. evaluator/defect-memory delta;
13. SSoT/claim/PR hygiene delta;
14. throughput/test-economy measurements supported by evidence;
15. REUSE/WRAP/EXTEND/REPLACE/NEW classifications;
16. maximum 20 ranked next micro-WOs;
17. DO_NOT_BUILD / DROP list;
18. unresolved blockers needing GPT/human authorization;
19. exact resume pointer if limit-interrupted;
20. exactly one `NEXT_SAFE_ACTION`.

`DONE` is evidence-based. GLM confidence, token usage, or number of goals visited is never completion authority.
