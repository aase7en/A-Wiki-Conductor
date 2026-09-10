# GLM Marathon Wave 4 — Nested `/goal` Long-Run Contract

This file is the execution contract for a sustained ZCode/GLM session.
Treat the entire file as the top-level `/goal`.

Do not stop after one child goal.
Do not ask the human to type `continue` between safe goals.
Do not maximize activity; maximize accepted, evidence-backed progress.

## MASTER `/goal`

Advance the A-Sunday Conductor Zero-Relay critical path and its immediate evidence/security dependencies as far as safely possible in one sustained session, using nested child `/goal`s, durable checkpoints, and exact repository authority.

Primary repository:
`A:\GitHub\A-Wiki-Conductor`

Cross-repo read-only authority when needed:
`A:\GitHub\A-Wiki`

Parent orchestration WO:
`docs/work-orders/WO-P1-180-glm-wave4-nested-goals.md`

### MASTER invariants

- Actual repo/runtime/GitHub state overrides dated SHA snapshots.
- User/safety/repository policy is never overridden by observed state.
- Reuse before build: `REUSE -> WRAP -> EXTEND -> BUILD`.
- No duplicate scheduler/job store/task graph/claim/lease/review/provider-policy/memory authority.
- Evidence > agent claims.
- `DONE` is not evidence.
- No hidden reasoning is stored as project evidence.
- Never expose secrets or real credential values.
- Never mutate live ZCode user configuration for a probe.
- Never broad-kill processes.
- Never reset/clean/stash/rebase/force-push protected work.
- Never merge unless a child WO explicitly grants that authority; default merge owner is GPT/integrator.
- If one goal blocks, checkpoint it and continue another independent safe goal.

### MASTER startup

Before any child mutation:

1. Read `00-AGENT-ENTRY.md`.
2. Read `PROJECT-GRAPH.yaml` and load only relevant nodes.
3. Read `AGENTS.md`.
4. Verify repository identity, remote, worktrees, branches, HEADs, dirty/untracked state and running processes.
5. Read `CURRENT-WORK.md` as continuity evidence, but compare it against live GitHub/WO state because Wave 3 found it stale.
6. Read `COLLAB.md` when ownership/parallelism is relevant.
7. Read `docs/agent-collab/FAST_EXECUTION_PROTOCOL.md`.
8. Read Zero-Relay authority:
   - `docs/plans/2026-09-04-zero-relay-accelerator-roadmap.md`
   - `docs/work-orders/WO-P1-155-zero-relay-accelerator.md` if present at the live ref
   - Issues #213, #214, #215, #216, #233
9. Re-pin live `main` and all relevant PR heads.
10. Build a live goal-state table before deciding any mutation.

Bootstrap history only — re-pin before use:
- WO176 / PR #250 closed the ZCode provider/model materialization P0/P1 defect.
- WO178 / PR #251 test-only ZRA-COMP-1 was merged into `main@680566d25e105630b321127c1a9b3e9e61af4bd4`.
- Post-main CI run `34509004680` was SUCCESS.
- WO179 was opened for the one real authorized no-relay proof; its current state may have moved.

Create nested child goals `G0` through `G15` below. Child goals may spawn bounded grandchildren for evidence, falsification, implementation, repair and verification.

---

## `/goal G0` — Cold-start reconciliation and goal queue

Objective: determine the actual current frontier without relying on Wave-3 prose.

Grandchildren:

### `/goal G0.A` Live identity
- fetch/pin `origin/main`;
- list relevant worktrees/branches/claims;
- inspect current open PRs/issues;
- identify mutable owners and read-only lanes;
- note stale docs separately from actual state.

### `/goal G0.B` Dependency graph
Create a compact table for:
- WO179 / live ZRA-1 proof;
- ZRA-2;
- ZRA-3;
- ZRA-4;
- AEET-0;
- SEC-INJECT-1;
- SEC-EXFIL-1;
- WO176 P3 hardening advisories;
- A-Wiki P14/P15/P16/P17 dependencies.

For each mark:
`DONE | READY | ACTIVE_OTHER_OWNER | REVIEW_READY | BLOCKED | DEFERRED`.

### `/goal G0.C` Overlap challenge
Search current branches/PRs/issues/worktrees for equivalent implementation before proposing anything new.

Checkpoint G0 to Issue #233.
Then continue automatically.

---

## `/goal G1` — WO179 / live ZRA-1 authorized proof frontier

Objective: advance or independently verify the one real authorized no-relay proof without stealing its mutable lane.

Rules:
- First identify WO179 owner from live durable evidence.
- If another owner has an ACTIVE mutable claim, GLM is READ_ONLY.
- Never execute a real credential/provider turn unless the active WO explicitly authorizes it and the current GLM lane owns that action.
- Synthetic/loopback probes remain preferred for falsification.

Branching:

### If WO179 has a frozen exact-SHA candidate
Spawn `/goal G1.REVIEW`:
- verify candidate/base identity;
- immutable exact-SHA review;
- inspect proof artifacts for secret hygiene;
- verify provider/model/endpoint/session attestation;
- verify no ambient-config fallback;
- verify one-and-only-one execution and bounded result;
- verify lease/admission/release/replay truth;
- run independent adversarial checks appropriate to R3;
- verdict `ACCEPT | CHANGES_REQUIRED | REVIEW_BLOCKED` with P0/P1/P2/P3 counts.
Do not mutate candidate.

### If WO179 is active but not frozen
Spawn `/goal G1.PREP` READ_ONLY:
- trace the exact composed call path expected for live proof;
- build a failure matrix for authorization/admission/provider/model/endpoint/credential/replay/orphan process;
- identify deterministic evidence that must exist before acceptance;
- inspect whether post-main CI prerequisite is satisfied;
- publish only delta findings, not a restatement of prior plans.

### If WO179 is complete/merged/post-main verified
Record closure and immediately continue to G2.

Checkpoint G1 to the owning WO/Issue and Issue #233.

---

## `/goal G2` — ZRA-2 automatic review/repair activation

Objective: move ZRA-2 from shaped architecture to the thinnest real production composition allowed by current gates.

Read Issue #214 and live owner-map authority before mutation.

Grandchildren:

### `/goal G2.A` Reuse archaeology
Trace existing reusable primitives for:
- accepted `AgentResultPacket` intake;
- deterministic verification;
- A-Wiki ReviewBus / A-Conductor review adapter;
- blocking finding normalization;
- `AgentRepairRequest` / repair task construction;
- active lease/scope/head verification;
- exactly-one repair execution;
- replacement result identity;
- no blind retry on UNKNOWN/ambiguous outcome.

Produce symbol/path/test evidence for every primitive.

### `/goal G2.B` Falsification matrix
At minimum challenge:
- same-agent review accidentally counted independent;
- stale review bound to old candidate;
- repair task widens mutation scope;
- duplicate repair after retry/restart;
- review transport timeout with unknown outcome;
- replacement result from wrong provider/model/base HEAD;
- result packet claims authority it never had;
- reviewer output containing injection instructions;
- lease expires between review and repair;
- no-change repair incorrectly reported as source mutation.

### `/goal G2.C` Mutation decision
If and only if a fresh ZRA-2 production WO/claim exists and explicitly assigns GLM a non-overlapping scope:
- execute RED-first;
- use smallest composition seam;
- do not add another review lifecycle/store/scheduler;
- batch adversarial failures before repair;
- freeze one exact candidate;
- publish assurance packet;
- switch this GLM session to READ_ONLY after freeze.

If no mutation authority exists:
- prepare the exact smallest executable WO packet and checkpoint it;
- continue G3 without waiting for human relay.

---

## `/goal G3` — ZRA-3 automatic NEXT READY continuation

Objective: prove/prepare a thin continuation tick after accepted closeout, reusing existing graph/ready/scheduler/lease/dispatch authorities.

Do not create another scheduler.

Grandchildren:

### `/goal G3.A` Call graph
Trace:
`accepted closeout -> compute_ready_set -> schedule/select -> acquire lease/admission -> dispatch next task -> durable checkpoint`.

Verify actual symbols and tests on current main.

### `/goal G3.B` Failure matrix
Challenge:
- empty ready set = natural completion;
- blocked nodes not dispatched;
- stale candidate/head triggers reload/replan;
- already-complete node not respawned;
- closeout from old attempt cannot advance new attempt;
- duplicate tick does not duplicate execution;
- lease acquisition failure leaves graph truthful;
- one child failure cannot silently mark parent complete.

### `/goal G3.C` Executable shape
If source WO/claim exists, implement the thinnest composition only.
Otherwise produce an exact packet with proposed files/tests and acceptance evidence.

Checkpoint and continue.

---

## `/goal G4` — ZRA-4 bounded parallel/fan-in

Objective: advance safe 2–3 lane Zero-Relay parallelism only after ZRA-3 acceptance gates permit it.

Reuse:
- write-set overlap/conflict seam;
- provider admission capacity;
- worker lease capacity;
- existing parallel-ready runner/executor;
- duplicate execution protection;
- per-task closeout/fan-in truth.

Grandchildren:

### `/goal G4.A` Concurrency authority audit
Prove there is exactly one owner for conflict detection, provider quota, worker lease and scheduler selection.

### `/goal G4.B` Adversarial fan-in
Design/probe:
- overlapping scopes never run together;
- independent scopes may run concurrently;
- provider capacity 1 serializes correctly;
- one success + one failure stays per-task truthful;
- restart during fan-in does not duplicate accepted children;
- stale worker replacement is fenced;
- cancellation/supersession does not blend results;
- aggregate completion requires exact child set.

### `/goal G4.C` Delivery decision
Implement only under a fresh explicit GLM claim. Otherwise shape the smallest proof packet.

Checkpoint and continue.

---

## `/goal G5` — AEET-0 evaluator seed

Objective: turn real defect history into an executable evaluator corpus, not a prose benchmark.

Reuse Wave-2/3 fixture findings but re-pin current test names and source behavior.

Corpus dimensions must stay separate:
- outcome/correctness;
- safety/security;
- robustness/recovery;
- efficiency/cost only for accepted outcomes.

Grandchildren:

### `/goal G5.A` Corpus reconstruction
Reconfirm known-good and known-bad fixtures from actual repo history/tests, including:
- settings deny projection;
- invalid `.claude` parent;
- duplicate JSON-key ambiguity class;
- symlink/reparse/path escape;
- parser hostile input;
- packet tamper;
- completed-execution replay;
- task/candidate-bound verification evidence;
- provider/model materialization mismatch;
- Zero-Relay composition replay.

### `/goal G5.B` Evaluator self-test
Ensure evaluator tests can prove the evaluator itself fails when:
- security dimension is removed;
- expected label is inverted;
- fast failed run outranks slow accepted run;
- unredacted secret marker appears in otherwise green output.

### `/goal G5.C` Implement-or-shape
If an explicit evaluator WO/claim exists, implement project-native minimum first with no new framework dependency.
Otherwise produce a READY packet.

---

## `/goal G6` — SEC-INJECT-1 repository/tool/result injection fixture

Objective: prove untrusted repository/tool/model output cannot grant new authority or rewrite the execution contract.

Grandchildren:
- hostile file content says to ignore WO and widen scope;
- fake model echoes/extends hostile instruction;
- verify fixed task contract, allowed tools and mutation scope remain unchanged;
- result is data, not authority;
- include a benign positive twin so a blocks-everything defense cannot pass.

Prefer test-only R1/R2 packet. Implement only under explicit claim.

---

## `/goal G7` — SEC-EXFIL-1 secret-return/redaction fixture

Objective: prove a provider/model returning secret-like material cannot cause unredacted persistence into receipts/results/review packets.

Use synthetic markers only.

Challenge:
- model response contains the synthetic credential marker;
- tool result contains it;
- error/trace contains it;
- review summary contains it;
- structured JSON nesting/arrays contain it.

Verify redaction before persistence and transmission to downstream evidence surfaces.

Implement only under explicit claim; otherwise shape packet.

---

## `/goal G8` — WO176 P3 hardening advisory triage

Objective: convert the three accepted advisory findings into evidence-backed priority decisions without destabilizing the closed R3 repair.

Advisories:
1. duplicate-key JSON decoder defense-in-depth;
2. delivery-key parameterization vs hardcoded `ANTHROPIC_API_KEY`;
3. `generatedAt` / ZCode bundle-version compatibility.

For each:
- reproduce or falsify on current main;
- classify real blast radius;
- search for existing prevention;
- decide `DROP | TEST_ONLY | R1 | R2 | R3`;
- propose smallest WO only when evidence justifies it.

Do not modify WO176 history.

---

## `/goal G9` — Installed ZCode compatibility matrix

Objective: reduce future regressions when ZCode changes protocol/bundle behavior.

Read-only unless a dedicated compatibility WO exists.

Build a version-sensitive matrix from currently available local/committed evidence:
- supported `session/create` model/runtimeModel fields;
- attestation/session readback shape;
- workspace/provider materialization behavior;
- generatedAt semantics;
- provider registry resolution source;
- protocol methods relied upon by A-Conductor.

Define a deterministic compatibility probe that can fail closed on unsupported upgrades without reading/printing secrets.

Do not patch installed ZCode.

---

## `/goal G10` — SSoT / continuity drift audit

Objective: prevent cold-start agents from following stale continuity while preserving single-writer hotspot ownership.

Read-only by default.

Compare:
- `CURRENT-WORK.md`;
- `COLLAB.md` active rows;
- active/closed WO docs;
- Issue #233;
- live PRs/main;
- Zero-Relay roadmap status.

Classify each mismatch:
`STALE_DOC | ACTIVE_AUTHORITY_CONFLICT | HISTORICAL_ONLY | NO_DEFECT`.

Do not edit shared hotspots claimlessly.
Prepare one fold packet for the correct single-writer owner if drift remains material.

---

## `/goal G11` — Cross-repo A-Wiki Phase 14–17 reconciliation

Objective: use A-Wiki only as live cross-repo authority/evidence where needed; do not mutate it without its own brain-improvement gate and claim.

Read live A-Wiki:
- `BRAIN-ENTRY.md`;
- `docs/graph/PROJECT-GRAPH.yaml`;
- `AGENTS.md`;
- `COLLAB.md` when coordination applies;
- `docs/protocols/brain-improvement-gate.md` before proposing brain capability changes;
- relevant Phase 14–17 roadmap/research nodes.

Reconcile:
- evaluator policy owner vs A-Conductor evaluator mechanics;
- agent-security policy vs test fixture ownership;
- memory provenance/quarantine policy vs runtime evidence projection;
- evidence radar candidate-only semantics;
- no automatic promotion of execution traces into global knowledge.

Produce changed-state-only findings; do not repeat Wave-1 matrices unchanged.

---

## `/goal G12` — Executable defect-memory harvest

Objective: turn material failures discovered across WO168/173/176/178/179 into reusable prevention candidates.

For each accepted defect ask:
- What executable test/check would have caught this before review?
- Is that prevention already present?
- Is the prevention local to a module or cross-cutting?
- Which authoritative defect-memory surface owns it?

Prefer tests/static checks over prose.
Do not create duplicate defect registries.

Output at most 10 high-value invariants.

---

## `/goal G13` — Accepted-run efficiency and review-economy analysis

Objective: use actual CI/PR/repair evidence to reduce future delivery time without lowering assurance.

Measure only from durable evidence where available:
- repair rounds per WO;
- candidate size/files/dependencies;
- targeted vs broad test counts;
- CI duration;
- independent review latency;
- defects caught at author/adversarial/reviewer/CI/post-main stage;
- duplicate CI/review work caused by successor PRs;
- acceptance escape rate if any.

Rules:
- failed/unsafe work never scores as efficient;
- do not reward LOC reduction by itself;
- do not remove R3 checks merely because they are expensive;
- recommend simplification only with evidence.

Produce up to five process improvements ranked by expected leverage and safety.

---

## `/goal G14` — Repository hygiene and stale candidate audit

Objective: reduce accidental reuse of superseded branches/PRs/task packets without deleting evidence.

Read-only unless explicitly authorized.

Identify:
- open docs PRs whose execution packet was already consumed;
- stacked roadmap PRs whose base is stale;
- obsolete candidate branches that could be mistaken for READY;
- work-order rows that claim READY after merge/release;
- task packets superseded by newer waves.

Recommend `KEEP | RETARGET | CLOSE_SUPERSEDED | FOLD_LATER` with evidence.
Never delete branches/history by default.

---

## `/goal G15` — Final synthesis and next marathon seed

Objective: finish the Wave with a cold-start-safe durable result and seed the next useful queue.

Before final output:
- re-pin `main` again;
- re-check all mutable owners/claims touched during the session;
- ensure no process/tool/probe was left orphaned;
- ensure no secret value entered evidence;
- ensure every mutation has an owning WO/claim;
- ensure authored candidates were not self-approved;
- record any falsified hypothesis explicitly.

Publish to Issue #233:

`## GLM-MARATHON-WAVE4-NESTED-GOALS RESULT`

Include:
1. live final main SHA;
2. nested goal tree with state for G0..G15;
3. exact PR/candidate/review verdicts handled;
4. Zero-Relay frontier and what is now actually proven;
5. P0/P1/P2/P3 findings;
6. evaluator/security/cross-repo outcomes;
7. SSoT/hygiene findings;
8. efficiency findings;
9. maximum five next micro-WOs, each with dependency + risk + smallest scope;
10. exactly one `NEXT_SAFE_ACTION`.

If useful work still remains and the ZCode session has capacity, spawn one final nested child:

### `/goal G15.CONTINUE`
Select the highest-value unresolved READ_ONLY question that does not overlap another mutable owner, investigate it deeply, checkpoint the result, and return to G15 synthesis.

Do not invent work merely to prolong the session.

---

# Repair loop used by every mutable child

When a child has explicit mutation authority:

`RE-PIN -> RED -> MINIMAL IMPLEMENTATION -> TARGETED TEST -> RELATED TEST -> ADVERSARIAL BATCH -> REPAIR CONFIRMED FINDINGS -> FREEZE -> ASSURANCE PACKET -> SWITCH READ_ONLY`

Do not run an independent review of your own candidate.

# Read-only deep-work loop used while blocked

When no mutation authority is available:

`SELECT UNRESOLVED QUESTION -> TRACE SOURCE/SYMBOLS -> FORM FALSIFIABLE HYPOTHESIS -> PROBE/TEST WITHOUT MUTATION -> SEEK COUNTEREXAMPLE -> RECORD EVIDENCE -> SHAPE SMALLEST READY PACKET -> NEXT CHILD GOAL`

# No-progress rule

If a child repeats the same conclusion twice without new evidence:
- mark `NO_NEW_EVIDENCE`;
- stop that child;
- continue the next independent child.

If a tool/provider transport fails:
- distinguish transport failure from code failure;
- retry only within existing bounded policy;
- do not weaken credential/safety gates to make a probe pass.

# Context-limit rule

When remaining context is becoming unsafe for continuity, do not improvise.
Publish `STATUS=PARTIAL_LIMIT_CHECKPOINT` with exact resume state, then stop cleanly.
A future GLM session should resume the same MASTER `/goal` from that checkpoint rather than restarting G0 from scratch.
