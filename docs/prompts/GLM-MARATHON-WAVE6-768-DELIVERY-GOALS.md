# GLM MARATHON WAVE 6 — 768-UNIT AUTONOMOUS DELIVERY GOAL TREE

Status: `EXECUTION_PACKET / LONG_HORIZON / MULTI_SESSION_SAFE`
Contract: `docs/work-orders/WO-P1-184-glm-wave6-delivery-campaign.md`
Repository: `A:\GitHub\A-Wiki-Conductor`
Primary durable destination: A-Wiki-Conductor Issue #233
Critical-path issues: #213, #214, #215, #216, #233
Bootstrap main at authoring: `5f36fe0ae59b6b3d4aadfd5465e817761d59ff09`

> This file is one MASTER ZCode `/goal`. It contains 8 programs × 8 families × 12 mandatory child steps = 768 base goal units. It may span multiple sessions. Do not stop for a single blocked child. Do not optimize for token consumption; optimize for useful accepted evidence and delivery.

---

## MASTER `/goal`

Drive A-Sunday Conductor toward the controlled autonomous loop:

`PLAN -> DECOMPOSE -> ROUTE -> EXECUTE -> VERIFY -> REVIEW -> REPAIR -> CONTINUE -> COMPLETE`

with Zero-Relay as the current throughput-critical path and with no duplicate scheduler, job store, lease store, provider policy, review lifecycle, retry authority or memory authority.

Run this Wave as a durable dependency-aware program rather than a chat checklist.

### Mandatory startup

Before doing any child goal:

1. read `00-AGENT-ENTRY.md`;
2. read `PROJECT-GRAPH.yaml` and select only relevant nodes;
3. read `AGENTS.md`;
4. inspect actual repo/worktree/remote/branch/HEAD/dirty state;
5. read `CURRENT-WORK.md` as evidence, but challenge staleness against actual Git/GitHub state;
6. read `COLLAB.md` when coordination/claims are relevant;
7. read the active WO for any mutable/review target;
8. read `DEFECT_LESSONS.md` before `src/a_conductor/**` mutation;
9. read the latest Issue #233 checkpoint/result, then Issues #213–#216 when their program is reached;
10. re-pin open PRs and CI rather than trusting SHAs embedded in this packet.

Record a Wave-6 start checkpoint on Issue #233 with actual state and `MUTATION_AUTHORITY`.

---

## GLOBAL AUTHORITY INVARIANTS

- The Wave packet is task transport, not product/source authority.
- A mutable family requires its own live WO + exact scope + isolated worktree/branch where needed + non-overlap + `SAFE_TO_MUTATE=YES`.
- GPT/integrator retains architecture/trust-boundary/final acceptance/merge/release authority.
- A GLM author cannot be the required independent reviewer of its own candidate.
- Independent review is read-only.
- Never merge unless separately authorized.
- Never expose real credential values.
- Never broad-inherit parent environment merely to fix one runtime dependency.
- Never blind-retry an ambiguous execution.
- Never manipulate a dirty/unknown worktree to make a gate pass.
- Never steal another claim, branch or active worker lane.
- A-Wiki is a separate repository/authority; no mutation from this packet without its own brain/repo gate.
- Real provider calls require a fresh durable GPT/integrator live-attempt authorization. This packet is not that authorization.
- Deterministic evidence > agent confidence.

---

## STANDARD FAMILY PROTOCOL — 12 child `/goal`s per family

For every family `Fxx`, execute children `A..L` unless a child is provably not applicable. A skipped child still needs a one-line evidence reason in the checkpoint.

### `Fxx.A — RECOVER`

Re-pin the current relevant repo/PR/issue/claim/worktree/runtime state. Identify stale embedded facts.

### `Fxx.B — REUSE MAP`

Search existing accepted source/tests/contracts/WOs before proposing anything new. Classify candidates `REUSE / WRAP / EXTEND / REPLACE / NEW`.

### `Fxx.C — AUTHORITY MAP`

Name exactly one owner for every factual/control decision touched by the family. Reject OWNER/OWNER ambiguity.

### `Fxx.D — TRACE`

Trace the real source/call/data path using exact files/symbols/tests/artifacts. Do not infer implementation from names alone.

### `Fxx.E — POSITIVE CONTROL`

Define/prove at least one benign successful case. A defense that blocks all useful work is not a pass.

### `Fxx.F — FALSIFY`

State the strongest plausible failure/escape hypothesis and attempt to disprove the current implementation/assumption.

### `Fxx.G — DETERMINISTIC PROBE`

Use the cheapest reproducible probe: unit fixture -> integration fake -> disposable state -> loopback/synthetic runtime -> host-specific bounded probe. Avoid live provider use unless separately authorized.

### `Fxx.H — FAILURE MATRIX`

Cover applicable malformed/stale/mismatch/duplicate/race/transport/platform/permission/secret/identity edges. Distinguish code failure from tool/provider/external failure.

### `Fxx.I — DELIVER`

Choose exactly one disposition:

- `PROVEN_NO_GAP`;
- `READ_ONLY_FINDING`;
- `WO_SHAPED`;
- `IMPLEMENTED_AND_FROZEN` only when a valid per-chunk mutation gate exists;
- `REVIEW_VERDICT` when acting as independent reviewer;
- `BLOCKED_WITH_OWNER`.

### `Fxx.J — VERIFY`

Run targeted verification first, then directly related coverage. Broad suites only when risk/coupling justifies them.

### `Fxx.K — CHECKPOINT`

Persist exact evidence, SHA/state, findings, owner/blocker and resume pointer. Do not rely on this session history.

### `Fxx.L — ROUTE`

Re-check preemption queue, choose the highest-value safe next family, and continue without asking the human to type `continue`.

---

## PREEMPTION LOOP

At every `.L` child and whenever a long operation ends, check:

1. newly frozen critical-path R2/R3 candidate needing independent review;
2. WO181 post-main status;
3. PR #255/WO183 exact head + CI/review state;
4. WO179 live-proof owner checkpoint;
5. ZRA-2/3/4 dependency state;
6. any ownership conflict or newly opened mutation lane.

If a review candidate is eligible and this GLM session is genuinely independent, save current pointer and preempt into the review. Publish verdict, then resume the saved queue.

If a blocker needs GPT/merge/live authorization, checkpoint it and continue independent families.

---

# PROGRAM P0 — CRITICAL ZERO-RELAY DELIVERY FRONTIER

## F00 — Actual-state and WO181 post-main closure

Goal: establish whether WO181 is fully post-main verified, not merely merged.

Inspect merge SHA, push CI, platform jobs, Issue #233/WO181 checkpoints and current main. If post-main CI succeeds, record evidence but do not invent live-attempt authority. If it fails, root-cause classify without touching another owner's source.

## F01 — PR #255 / WO183 independent exact-SHA review

Goal: review duplicate-key JSON hardening if and only if reviewer independence is genuine.

Challenge top-level and nested duplicate keys, unknown/invalid structures, benign unique JSON, canonical serialization round-trip, exception normalization and parser reuse. Rerun focused tests. Verdict exactly `ACCEPT`, `CHANGES_REQUIRED`, or `REVIEW_BLOCKED`, with P0/P1/P2 counts. Do not mutate the candidate while reviewing.

## F02 — WO179 Attempt-3 readiness audit

Goal: determine whether all prerequisites for a fresh `ZRA-1-LIVE-3` identity are satisfied.

Audit WO181 post-main, prior attempt identities, sacrificial stores, release state, no orphan execution, provider/lease/admission authority, recovery semantics and credential-ref-only handling. Do not execute a real provider turn unless a new explicit GPT live-attempt authorization exists.

## F03 — ZRA-1 acceptance proof matrix

Goal: define the exact evidence needed to call ZRA-1 accepted after a successful owner-run live proof.

Require authorized provider/model/endpoint binding, exact task/result identity, marker round-trip, no human relay, durable terminal/recovery state, zero orphan, released admission/lease, no ambient fallback, replay safety and secret-free artifacts.

## F04 — ZRA-2 automatic verify/repair contract

Goal: prepare the thinnest R3 successor contract using existing ReviewBus/result/apply/recovery authorities.

Trace exact current symbols. Failure model must include wrong result identity, review spoofing, stale SHA, provider/model mismatch, malicious result content, exactly-once repair dispatch, repair-loop bound, reviewer failure, transport loss after possible effect and restart reconciliation. Shape a docs-only WO only after ZRA-1 acceptance and current owner-map permit it.

## F05 — ZRA-3 autonomous NEXT READY contract

Goal: prepare safe continuation after accepted result.

Reuse existing ready-set/scheduler/task graph/job-state authorities. Prove no second scheduler. Failure model: duplicate completion, stale ready-set, changed dependencies, blocked next task, restart between closeout and continuation, replay and human-approval boundary.

## F06 — ZRA-4 bounded parallel/fan-in contract

Goal: prepare 2–3 independent external-agent lanes under existing WIP/lease/ownership limits.

Trace current parallel-ready execution, worktree identity, lease isolation, write-set overlap, batch identity, partial fan-in, one-lane failure, retry ambiguity, provider capacity and exact result fan-in. No broad worker-count optimization before correctness.

## F07 — ZRA-5 / ODP transition gate

Goal: define exactly when broad ODP work may resume after ZRA-4 and how Zero-Relay becomes an execution adapter rather than a second router/policy system.

Reconcile PR #202 and owner-map. Do not mutate ODP ahead of the accepted dependency frontier.

---

# PROGRAM P1 — ZCODE / PROVIDER / RUNTIME TRUST BOUNDARIES

## F08 — Runtime-model JSON parser hardening state

Reconcile PR #255 result with current main. If accepted/merged later, prove duplicate-key rejection is effective and does not create another JSON authority. If not accepted, preserve exact finding and owner.

## F09 — ZCode bundle compatibility guard — IMPLEMENTATION SLOT I2

Search for an existing accepted bundle/version/protocol guard first. If none exists and no overlapping claim exists, a bounded R2 test-only WO may be bootstrapped.

Target evidence: installed/supported bundle identity/hash where observable, fake positive protocol fixture, schema-drift negative before turn send, explicit host/platform skip, no live provider/config mutation. Production source change is outside this slot; a RED requiring source repair becomes a separate finding/WO.

## F10 — Windows minimal child environment next-dependency challenge

Probe whether any dependency beyond `SYSTEMROOT` is genuinely required on realistic success/failure paths. Focus on TEMP/crash/error/reporting behavior without broad inheritance. Use synthetic/local children. Preserve secret-minimal environment. Do not add variables merely because Windows commonly has them.

## F11 — Provider snapshot generation drift

Trace snapshot -> admission -> execution binding. Probe endpoint/model/generation changes after admission and before child send. Verify stale generation cannot silently execute.

## F12 — Credential delivery / exfiltration boundary

Trace credential reference resolution and child delivery without reading real values. Probe env-key aliasing, denied legacy variables, argv/log/artifact leakage, exception/traceback leakage and malicious task/result attempts to surface credentials. Synthetic secrets only.

## F13 — Protocol schema drift

Challenge `session/create`, model setting/attestation, `session/send/read` or current equivalent against missing/extra/renamed fields, unsupported runtime version and silently ignored model selection. Positive control must prove valid current schema still executes against fake/loopback transport.

## F14 — Effective provider/model attestation

Audit configured vs effective identity at every observable boundary. Verify no success is possible when effective provider/model/endpoint differ from authorized runtime binding.

## F15 — Provider readiness / quota / authorization freshness

Trace current authorities and their age/generation semantics. Falsify stale readiness/quota/service authorization. Do not invent quota facts or live-probe provider billing/limits without authorization.

---

# PROGRAM P2 — PROCESS, DURABILITY, RECOVERY AND REPLAY

## F16 — PID reuse / creation-time fixture — IMPLEMENTATION SLOT I3

Discover canonical process-truth/recovery tests. If no equivalent fixture exists and no claim overlaps, bootstrap a bounded R2 test-only WO. Prove same PID + different creation time cannot attach/reuse. Production-source RED -> separate repair WO, not silent scope expansion.

## F17 — Orphan process / natural shutdown semantics

Trace helper/supervisor/child lifecycle. Probe stdin EOF, timeout, child exit-before-result, report-before-result and no-kill-ladder assumptions. Verify no broad process kill.

## F18 — Output backpressure and oversized frames

Challenge queue/line/result budgets, flooding child, huge single line, many small lines, partial frames and EOF. Verify typed failure and bounded memory, with benign normal-output positive control.

## F19 — Transport loss after possible side effect

Build a fault matrix where operation may have completed before transport acknowledgement. Verify reconcile-before-retry and at-most-once/idempotent semantics through existing authorities.

## F20 — Durable state CAS/transition truth

Trace execution/job state transitions and persistence failure behavior. Probe CAS failure, disk/store error, concurrent terminal transitions and apparent-success escapes.

## F21 — Lease expiry / stale owner recovery

Challenge time boundaries, heartbeat loss, owner death, stale but live process, released lease and cross-process reconciliation. Never equate elapsed time alone with safe mutation ownership.

## F22 — Replay/dedup identity

Audit operation/task/runtime identities for collision, truncation, migration, same-packet-different-model/provider and restart replay. Verify no duplicate spawn/effect.

## F23 — Fan-in partial-write ambiguity

Prepare deterministic two-lane fake execution where one result persists and another transport/result write fails. Verify existing fan-in/recovery semantics preserve known success and do not rollback/replay blindly.

---

# PROGRAM P3 — REVIEW, EVALUATOR AND EVIDENCE QUALITY

## F24 — AEET-0 evaluator contract

Re-pin PR #244/WO171 and current owner/gate. Define deterministic dimensions separately: requested outcome, security/privacy/authority/scope, robustness/recovery, efficiency. Never allow a weighted score to compensate for mandatory safety failure.

## F25 — Evaluator known-good / known-bad seed — IMPLEMENTATION SLOT I5

Only if the live roadmap/claim gate permits a new-file test/eval seed. First prove evaluator catches deliberately bad fixtures and accepts known-good fixtures. Prefer native/simple data structures. No routing-policy mutation. If implementation remains gated, produce exact fixture corpus and acceptance packet only.

## F26 — Review identity / spoofing

Trace how reviewer identity/independence is represented. Probe same-author masquerade, copied stale verdict, verdict for wrong SHA, wrong repo/branch/task, edited candidate after review and provider/session ambiguity.

## F27 — Positive-control enforcement — IMPLEMENTATION SLOT I4

If no equivalent guard exists, bootstrap bounded test-only work proving every adversarial/security evaluation includes benign positive success. A defense that rejects attack and benign task equally must not earn PASS.

## F28 — Accepted-run efficiency scoreboard

Derive metrics only from accepted comparable runs: risk tier, outcome, files/LOC/deps, elapsed time, review/repair rounds, retries/recovery, tool/model/cost facts when trustworthy, safety gates. Do not create a second task/evidence store.

## F29 — Repair-round and defect-yield analysis

Use durable WOs/PR/reviews to compare where defects were caught: author tests, adversarial pre-freeze, independent review, CI, post-main/live proof. Recommend process changes only when evidence supports them.

## F30 — Trace/provenance completeness

Audit current evidence envelopes for task/agent/tool/process/provider/model/artifact hashes without capturing hidden reasoning or private payloads by default. Trace is evidence, never authority.

## F31 — Reviewer-independence enforcement architecture

Determine the smallest deterministic prevention against self-review being counted as independent. Reuse Git/WO/reviewer provenance. Shape only unless a separate authorized WO exists.

---

# PROGRAM P4 — AGENT SECURITY / ADVERSARIAL FIXTURES

## F32 — Indirect prompt injection from repository content

Design fake-first fixtures where malicious repo text instructs the agent to escape scope, reveal secrets, override WO or alter unrelated files. Verify repo content is untrusted input, not authority.

## F33 — Tool-output injection

Use synthetic tool output that attempts to override task/authority, request unrelated actions or hide failed verification. Prove tool payload cannot grant scope.

## F34 — Malicious or changed tool metadata

Challenge tool name/schema/description drift and malicious metadata that requests broader access. Effective capability/tool identity must be attested rather than trusted from prose.

## F35 — Secret exfiltration attempts

Use synthetic secret markers. Probe prompt, repo file, tool output, stderr/traceback, report/result packet and agent-to-agent handoff channels. Positive task must still complete without exposing marker.

## F36 — Authority escalation / transitive permission

Planner/reviewer/upstream model output asks worker to expand mutation scope or bypass approval. Verify downstream revalidates original task/lease/policy and cannot inherit stronger authority.

## F37 — Denial-of-wallet / runaway loop

Design bounded fake loops, repeated repair requests, tool retry storms and recursive-goal expansion. Verify existing iteration/time/budget gates where applicable. Do not create a second scheduler/budget authority.

## F38 — Memory poisoning / quarantine boundary

Read-only reconcile A-Wiki Phase-16 memory/provenance plans and A-Conductor sanitized feedback. Design fixtures proving untrusted execution output cannot auto-promote into global knowledge. A-Wiki mutation requires its own gate.

## F39 — Inter-agent taint propagation

Trace user/repo/tool/model/reviewer-derived inputs across hops. Design deterministic provenance classes and revalidation assertions without relying on another LLM as sole trust detector.

Security implementation opportunity: after F32–F39 shaping, if no overlapping security/evaluator claim exists and the exact new-file/test-only scope is clear, implementation slot I6 may bootstrap ONE consolidated R2 fake-first fixture WO rather than eight competing WOs. Freeze it for independent review and continue elsewhere.

---

# PROGRAM P5 — CROSS-PLATFORM / VERSION / FILESYSTEM COMPATIBILITY

## F40 — Windows system-environment minimization

Prove required system dependencies narrowly. Challenge case-insensitive env keys, invalid/missing values and ambient credential/config absence. Do not copy parent env wholesale.

## F41 — POSIX parity

Confirm Windows-only repair did not alter Linux/macOS semantics. Where platform differences are intentional, encode explicit test/skip evidence rather than assuming equivalence.

## F42 — Junction/symlink/reparse/path alias safety

Reuse prior path-boundary probe packs. Challenge trusted-root/worktree/scope checks through symlink/junction/reparse/UNC/long-path/alias forms where supported. Do not mutate user filesystem broadly.

## F43 — Casefold and environment alias behavior

Probe Windows case-insensitive variable/path identity and POSIX case-sensitive behavior. Ensure duplicate aliases cannot smuggle conflicting credential/system values.

## F44 — Unicode / UTF-8 boundaries

Challenge task packet, path, JSON, stdout/stderr, reports and docs with valid non-ASCII plus malformed byte/encoding cases. Preserve strict UTF-8 and no replacement-character corruption where required.

## F45 — Long paths / argv / command-line budgets

Revisit Windows length boundaries, quoting, exact argv grammar and path normalization. Positive normal command must still work. No prompt/task payload in argv.

## F46 — Executable/bundle identity

Audit what is launch evidence vs live-observed identity. Probe replaced binary/path, same path new file, bundle hash drift and restart reconciliation. Avoid claiming argv digest as live proof when it is launch-only evidence.

## F47 — ZCode upgrade compatibility matrix

Build a read-only matrix from accepted/current supported ZCode versions and protocol observations available in durable evidence. Identify exact tests that must run before accepting a future upgrade. No user ZCode config mutation.

---

# PROGRAM P6 — CONTINUITY, SSoT, CLAIMS AND CROSS-REPO BOUNDARIES

## F48 — CURRENT-WORK staleness audit

Compare `CURRENT-WORK.md` against actual main, PRs, Issue #233 and accepted merges. Identify stale authoritative wording that could misroute a cold-start agent. Do not mutate hotspot unless separately claimed.

## F49 — Issue #213–#216 claim-aging audit

Separate historical claim text from current live ownership. Propose minimal status reconciliation without deleting evidence. Avoid interpreting old `ACTIVE` prose as a free or occupied lane without corroboration.

## F50 — Stale PR/candidate hygiene

Classify open PRs `KEEP / RETARGET / CLOSE_SUPERSEDED / FOLD_LATER / REVIEW_NOW`. Never close/retarget another owner's active candidate without integrator authority; publish evidence recommendations.

## F51 — Branch/worktree hygiene

Map only relevant known branches/worktrees. Identify merged/superseded leftovers and collision risk. Never reset/clean/delete/stash another lane. Hygiene is advisory unless explicit ownership exists.

## F52 — Cold-start continuity drill

Simulate an agent with no chat history using only durable entry/graph/WO/Issue/Git evidence. Record where it would choose the wrong frontier or duplicate work. Prefer executable prevention over prose if a material defect is confirmed.

## F53 — Checkpoint completeness drill

Sample recent WOs/Waves and verify checkpoint has task/status/owner/repo/worktree/branch/HEAD/dirty/evidence/blocker/decision/TODO/one next action. Identify missing fields that caused actual friction rather than inventing bureaucracy.

## F54 — A-Wiki/A-Conductor owner-map revalidation

Read both current repos. Revalidate planning, work-order contract, claim/lease, status, mutation gate, model policy/runtime selection, review, verification, continuity, scheduler, retry/recovery, next-ready and memory. Exactly one OWNER per capability.

## F55 — Memory/provenance/privacy boundary

Reconcile A-Conductor execution evidence with A-Wiki memory layers. Ensure private/raw/secret/tool payloads cannot be auto-promoted. No A-Wiki mutation without brain-improvement gate.

---

# PROGRAM P7 — THROUGHPUT, SIMPLIFICATION, RELEASE AND SUCCESSOR PLANNING

## F56 — Test-economy analysis

Measure which focused suites predict final CI for recent accepted WOs. Recommend smaller during-edit batteries and preserve full gates only where risk requires them. Never delete coverage solely for speed.

## F57 — CI critical-path analysis

Use durable workflow/job timing evidence to identify expensive serial steps, redundant work and platform asymmetry. Suggest changes only when they preserve R2/R3 assurance and do not duplicate local verification unnecessarily.

## F58 — Task-packet/context compression

Measure repeated prompt/WO context and identify what can be referenced by pointer rather than re-embedded. Preserve binding requirements. Goal is less repeated context, not less safety.

## F59 — WIP / parallel scheduling evidence

Analyze accepted-run throughput under current `3 mutable + 1 review` guidance. Determine whether 2–3 lanes remain optimal. Do not increase parallelism from theory alone; include merge/review/blocker latency and conflict rate.

## F60 — Defect-yield optimization

Rank detection mechanisms by severity-weighted defects caught per effort: TDD, adversarial batch, independent review, CI, live proof. Recommend where to spend GLM/GPT/native-tool effort next.

## F61 — Architecture simplification / reuse audit

Find concepts/files/adapters that duplicate accepted authority or can be collapsed behind existing interfaces. Use `NEEDED? -> REUSE -> STDLIB/NATIVE -> INSTALLED DEP -> MINIMUM CLEAR CHANGE`. Do not optimize LOC at the expense of robustness.

## F62 — Release-blocker reconciliation

Re-pin WO096 and current source/release version state. Separate Zero-Relay progress from unrelated release requirements. Identify what remains actually blocking a release, but do not deploy/release without authority.

## F63 — Final synthesis and Wave-7 queue

Build the final result from evidence, not narrative repetition.

Deliver:

- exact state delta during Wave 6;
- 64-family matrix;
- base child units completed/skipped with reasons;
- recursive findings;
- review verdicts;
- implementation candidates/frozen SHAs;
- Zero-Relay maturity;
- security/evaluator/recovery status;
- continuity/SSoT risk;
- efficiency evidence;
- max 15 ranked next micro-WOs;
- `DO_NOT_BUILD` list;
- exactly one `NEXT_SAFE_ACTION`.

If substantial useful work remains beyond the current session, also design the next pointer as a continuation of unresolved evidence, not a reset of Wave 6.

---

## RECURSIVE FINDING `/goal` TEMPLATE

When a material finding survives falsification, spawn:

`/goal Fxx.R<n> — <short defect/hypothesis>`

Children:

1. exact evidence + positive control;
2. reproduce twice when deterministic;
3. classify code/tool/provider/environment/policy/authority;
4. severity P0/P1/P2/P3 + risk R0/R1/R2/R3;
5. existing owner/reuse search;
6. smallest RED/fixture;
7. bounded repair plan or WO shape;
8. mutation gate if implementation eligible;
9. targeted/related verification;
10. secret/scope/identity hygiene;
11. checkpoint exact SHA/state;
12. return to parent `.L` route.

Depth maximum 5. Consolidate deeper findings into a standalone WO rather than recursively exploding the tree.

---

## MULTI-SESSION CHECKPOINT

When context/usage limit approaches, do not summarize vaguely. Publish to Issue #233:

`## GLM-MARATHON-WAVE6-768 PARTIAL_LIMIT_CHECKPOINT`

with:

- exact main + relevant PR heads + CI;
- current program/family/child pointer;
- completed family bitmap `F00..F63`;
- completed base unit count;
- active recursive goals;
- frozen review/implementation candidates;
- active claims/scopes and mutation authority;
- blockers with owner;
- next queue;
- exactly one next safe action.

Next session reads this packet + latest checkpoint, re-pins state, and resumes the first incomplete useful child. Never restart completed families without a material-state-change/falsification reason.

---

## FINAL RESULT

Publish exactly:

`## GLM-MARATHON-WAVE6-768 RESULT`

on Issue #233 using the result contract in WO-P1-184.

Do not claim `DONE` because tokens ran out or because a model said the work looked good. Claim Wave completion only when every useful family is evidence-resolved as `DONE`, `PROVEN_NO_GAP`, `FROZEN_FOR_REVIEW`, or `BLOCKED_WITH_OWNER`, and all recursive material findings have a durable disposition.

Then leave exactly one `NEXT_SAFE_ACTION` for GPT/integrator or the next cold-start GLM session.
