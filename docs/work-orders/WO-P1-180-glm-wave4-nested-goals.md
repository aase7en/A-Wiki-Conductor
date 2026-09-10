# WO-P1-180 — GLM Wave 4 Nested-Goal Marathon

Status: DRAFT / DOCS-ONLY ORCHESTRATION PACKET
Risk: R2 coordination; individual child work keeps its own risk tier and authority.
Owner: GPT-5.6 Sol integrator for architecture/acceptance; GLM/ZCode is the preferred sustained execution/review engine when its child gate permits.
Bootstrap main: `680566d25e105630b321127c1a9b3e9e61af4bd4` (must be re-pinned at execution time).
Parent accelerator: `WO-P1-155` Zero-Relay Accelerator.
Prompt: `docs/prompts/GLM-MARATHON-WAVE4-NESTED-GOALS.md`.

## Purpose

Exploit ZCode's long-horizon `/goal` workflow as a nested goal tree rather than short one-task prompts.
The operator should send one pointer, then GLM should continue through useful dependent work for as long as the execution surface remains available.

This packet does **not** create a second scheduler, task store, claim system, review lifecycle, or authority layer. The repo's existing WO/claim/PR/Issue contracts remain authoritative. The nested `/goal` tree is an execution convenience only.

## Operator outcome

One manual pointer should launch a sustained queue shaped approximately as:

`RECOVER -> CURRENT FRONTIER -> REVIEW/PREP -> ZERO-RELAY CRITICAL PATH -> EVALUATOR/SECURITY -> CROSS-REPO EVIDENCE -> DRIFT/EFFICIENCY -> NEXT QUEUE`

Do not return to the user after each child goal. Continue automatically unless a binding STOP condition is reached.

## Current durable frontier captured for bootstrap

Evidence available before this packet was authored:

- WO176 / PR #250 merged and post-main verified; runtime provider/model materialization P0/P1 defect closed.
- WO178 / PR #251 merged as `680566d25e105630b321127c1a9b3e9e61af4bd4`; independent review ACCEPT P0/P1/P2=0.
- Post-main CI run `34509004680` on `680566d25...` completed SUCCESS.
- WO179 was opened as the next R3 lane for one real authorized no-relay provider proof, but its live/local state must be re-pinned before relying on this snapshot.
- Wave 3 identified next reusable seams: ZRA-2 activation, ZRA-3 thin continuation composition, ZRA-4 bounded fan-in, AEET-0 evaluator seed, SEC-INJECT-1 / SEC-EXFIL-1, plus three WO176 P3 hardening advisories.

Actual Git/runtime/claim state always overrides this dated snapshot.

## Nested-goal execution contract

Treat `GLM-MARATHON-WAVE4-NESTED-GOALS.md` as one top-level `/goal`.
Inside it, maintain child `/goal`s and, where useful, grandchild `/goal`s for evidence gathering, falsification, implementation, verification, and packetization.

Recommended depth:

- Level 0: Wave 4 master objective.
- Level 1: durable delivery goals (`G0`..`G15`).
- Level 2: evidence / falsification / implementation / verification sub-goals.
- Level 3 only when a difficult defect or failure model needs a bounded deep dive.

Do not nest merely to consume tokens. Every active goal must name a concrete unresolved question or deliverable.

## Mutation rule

This WO/prompt itself grants **no product/source mutation authority**.
For each child goal:

1. re-pin repo/worktree/remote/branch/HEAD/dirty/untracked state;
2. inspect current claims, work orders, PRs, processes and overlap;
3. read the child task's authoritative WO/Issue/contract;
4. mutate only if a fresh explicit claim covers the exact scope and risk;
5. otherwise continue in READ_ONLY mode and prepare evidence/packet for the owner.

`SAFE_TO_MUTATE = NO` by default.

## Role split

GPT/integrator retains:
- architecture and trust-boundary decisions;
- dependency ordering and cross-lane conflict adjudication;
- work-order/claim authority framing;
- final defect severity adjudication;
- exact-SHA acceptance, merge, release, post-main closeout.

GLM/ZCode is preferred for:
- long source archaeology;
- exact-SHA independent review when it did not author the candidate;
- bounded implementation under an explicit GLM claim;
- adversarial/fault test generation;
- root-cause reproduction;
- repeated repair/retest loops;
- read-only shaping while another mutable lane is active.

## Independence rule

A GLM session that authored a candidate must not count itself as the independent reviewer of that candidate.
After freeze it should:

`FREEZE -> PUBLISH ASSURANCE -> SWITCH READ_ONLY -> CONTINUE OTHER CHILD GOALS`

An independent lane/model/session performs exact-SHA review.

## Long-run continuity

At every meaningful transition persist a compact durable checkpoint to the existing Issue/PR/WO surface. Do not create another SSoT.

Before context/token/session exhaustion publish:

`STATUS=PARTIAL_LIMIT_CHECKPOINT`

with:
- exact repos/SHAs;
- completed goal IDs;
- current goal and hypothesis;
- deterministic evidence;
- mutation/claim state;
- blockers;
- one resume pointer;
- exactly one `NEXT_SAFE_ACTION`.

A new GLM session must be able to resume from the checkpoint without the human reconstructing prior chat.

## Useful-work rule

The user explicitly prefers long GLM utilization. Spend available reasoning/context budget aggressively on **useful unresolved engineering work**:
- tracing source/call paths;
- building falsifiable hypotheses;
- adversarial probes;
- boundary/failure matrices;
- dependency/authority mapping;
- targeted tests;
- replay/idempotency analysis;
- cross-platform cases;
- privacy/security cases;
- evidence-backed simplification;
- packet preparation for the next READY lane.

Never waste budget by repeating conclusions, rereading unchanged files without a question, restating the prompt, or generating speculative architecture without evidence.

## STOP conditions

Stop the whole Wave only for:
- AUTHORIZATION_REQUIRED;
- OWNERSHIP_CONFLICT;
- SAFETY_BLOCK;
- destructive/live action requiring human approval not already granted;
- no safe useful read-only work remains;
- session/context limit after durable checkpoint.

A single child goal being blocked is **not** a Wave stop. Mark it BLOCKED, record the dependency, and continue the next independent read-only child.

## Completion

Final result destination: A-Wiki-Conductor Issue #233 unless a more specific active WO/Issue owns that child result.

Final heading:

`## GLM-MARATHON-WAVE4-NESTED-GOALS RESULT`

Required summary:
1. exact repos/SHAs inspected;
2. goal tree with DONE/BLOCKED/DEFERRED states;
3. accepted/reviewed candidates and verdicts;
4. Zero-Relay critical-path result;
5. confirmed defects + severity + evidence;
6. evaluator/security/provenance outcomes;
7. SSOT/ownership drift findings;
8. efficiency/minimality findings;
9. at most five READY or near-READY micro-WOs;
10. exactly one `NEXT_SAFE_ACTION`.

Do not merge from this orchestration lane unless a separate active child WO explicitly assigns merge authority (normally GPT/integrator retains it).
