# Provider-Neutral Agent Collaboration Protocol

Purpose: let GPT, GLM, Claude, Codex, local models, and future agents work on one project without relying on chat memory or human result copy/paste.

## 1. Entry sequence

All execution surfaces use the same startup core:

1. `00-AGENT-ENTRY.md`
2. `PROJECT-GRAPH.yaml`
3. `AGENTS.md`
4. actual repository/worktree/remote/branch/HEAD/dirty/claim state
5. `CURRENT-WORK.md`
6. active work order under `docs/work-orders/` when one exists or has already been claimed
7. `handoff.md` only for resume/transfer work, unclear continuity, or when `CURRENT-WORK.md` points to it for material context
8. task-relevant nodes selected by `PROJECT-GRAPH.yaml`
9. `DEFECT_LESSONS.md` before `src/a_conductor/` mutation

Actual repo/runtime state overrides stale summaries and chat memory about state; it never overrides user authority, safety constraints, or binding repository policy.

Do not mechanically require the full `PROJECT-PLAN.md` + `DESIGN.md` corpus for every task. The project graph makes them mandatory only when architecture/roadmap/trust-policy or UI/UX scope requires them.

Default delivery ownership is `GPT governance -> capability-selected bounded execution -> deterministic evidence -> independent review as required -> GPT acceptance/merge`. The capability matrix currently prefers GLM/ZCode for many bounded READY implementation tasks; provider identity is a routing preference, not an architectural dependency or authority bypass.

## 2. Safety gate

Product/source mutation requires all of:
- exact repository/worktree/remote/branch/HEAD;
- known dirty-state ownership;
- task owner and active bounded claim/lease;
- non-overlapping mutable scope;
- explicit allowed + forbidden scope;
- acceptance criteria and verification;
- durable result/evidence destination.

If any item is uncertain: `SAFE_TO_MUTATE = NO`.

Bootstrap exception: when a genuinely new task has no work order/claim yet, a clean isolated docs-only governance lane may create the initial WO/claim and nothing else. Product/source/runtime mutation remains blocked until the full gate is rerun and passes.

## 3. Task → result protocol

Integrator writes or selects one task packet containing identity, goal, scope,
acceptance, verification and result destination. After generation, the integrator must
re-read the packet and verify literal worktree/branch/HEAD, unresolved-placeholder absence,
content/SHA preconditions and result destination before any provider/human relay dispatch.

Agent then:
1. reads the task packet;
2. works only inside its lease/scope;
3. writes structured result/evidence to the declared destination;
4. never edits tracked coordination SSoT (`CURRENT-WORK.md`, `handoff.md`, `COLLAB.md`, active WO) unless a docs-only task explicitly assigns that exact file and proves no overlap; the integrator is the default single writer;
5. does not merge, publish, retry ownership, or broaden scope.

Integrator then:
1. reads the result directly;
2. checks task/provider/model identity;
3. checks exact base HEAD and file SHA256 precondition;
4. applies one-file replacement through the deterministic lease boundary;
5. runs review/tests;
6. accepts or emits a bounded repair task.

Agent claims are descriptive; deterministic evidence is authoritative.

## 4. Repair loop

On review failure, persist findings and create a repair packet referencing the prior result.
Use the same provider/task lifecycle and lease authority; do not invent a second retry system.
A transport timeout or ownership uncertainty becomes `RECOVERY_REQUIRED`, never blind replay.

## 5. Human bridge fallback

Use only when automatic provider execution is unavailable because of auth, quota,
entitlement, tool packaging, or another external condition.

The integrator gives the human one short prompt:
`Read <task-ref>. Do only that authorized lane; write the required JSON result to <result-ref>. Do not return the result to the human or edit coordination files.`

The human relays that direction once. The external agent reads the task and writes the
result file. The integrator resumes by reading that file itself; the human never copies
the result back into another chat. The human should relay only the task pointer/direction,
not duplicate task content, status, findings, or result payload.

Runtime task/result artifacts belong in the existing ignored `runs/` surface. Do not create
per-agent roadmap/handoff/memory clones. The integrator folds accepted status/evidence back
into the canonical WO + `CURRENT-WORK.md` + `handoff.md`, and reusable defects into
`DEFECT_LESSONS.md`.

## 6. Parallelism

Only independent READY tasks may run in parallel. Each gets a distinct worktree/lease
or a proven non-overlapping mutable scope. AHA-5 intentionally allows one mutable file
per agent task; AHA-6 owns broader fan-out/fan-in scheduling and collision safety.

Default WIP limit from `FAST_EXECUTION_PROTOCOL.md`: at most **3 mutable implementation lanes + 1 independent read-only review lane**. Extra worker capacity should remain available for recovery/blocker work rather than maximizing active worktree count. Throughput is measured at accepted merge/release, not number of busy workers.

## 7. Provider selection gate

Route by task class and risk first, then choose the cheapest capable authorized executor using current evidence in `CAPABILITY_MATRIX.md`. Evaluate capability, readiness, authorization, cost, availability, ownership and result-destination fit separately.

Before delegating to a named external model, record recent trustworthy evidence that the
model is suitable for the task class. Benchmark evidence informs routing; it never grants
mutation authority or overrides deterministic review. A provider preference may change without changing lifecycle semantics.

## 8. One-goal orchestration + loop-engineer cycle

A human may state the goal once. The integrator owns decomposition, model routing, task packets, result ingestion and SSoT fold-back. Delivery is risk-tiered by `FAST_EXECUTION_PROTOCOL.md`; do **not** mechanically run the maximum-assurance path for every material task.

Common front door:

`recover minimum SSoT/actual Git -> resolve only material ambiguity -> explicit bounded task/claim -> classify R0/R1/R2/R3 -> run the tier-specific loop -> checkpoint accepted evidence -> select next READY node`.

R2/R3 retain frozen exact-SHA independent review, bounded repair/rereview, exact-head CI and realistic E2E/fault/release verification where applicable. R0/R1 may use shorter deterministic paths when their actual blast radius remains low.

Rules:
- verify the local `grill-with-docs` against its upstream GitHub source when materially planning; record date/ref or mark `UPSTREAM_UNVERIFIED`;
- grilling/brainstorming never authorizes mutation by itself: an explicit bounded plan/task/claim gate must exist first;
- subagents are advisory or separately leased lanes, never hidden shared writers;
- branch names come from the active WO; never hard-code a generic health branch over unrelated work;
- provider/model benchmarks route work only after freshness/task-fit review; provider readiness/auth/quota remains a separate gate;
- review and CI evidence are pinned to exact SHA; transport/tool failures are not product failures or passes.
- prefer one adversarial batch before external independent review; do not create a PR per defect by default.
- freeze one candidate SHA after targeted/related verification and known adversarial repairs; independent review should target that candidate rather than each intermediate commit.
- repeat broad/full verification only when the risk tier, changed boundary, new failure evidence, or release gate requires it.
- canonical SSoT is checkpointed at claim transfer, material blocker/decision, frozen candidate, merge/release, and handoff/session rollover rather than after every trivial edit.

## 9. Completion

A lane is complete only when acceptance evidence, diff, tests/CI as required, ownership
release and continuity checkpoint agree. `DONE` from an agent alone is insufficient.


## 10. Stable external-agent mailbox fallback

When automatic provider dispatch is unavailable, prefer one stable machine-local mailbox path per external agent over changing human-visible task pointers every round.

The mailbox is an **addressing shim only**, not task authority. Default Windows location is `%LOCALAPPDATA%\A-Conductor\agent-bridge\<agent>\task.md`; an explicit bridge-root override and cross-platform user-state fallback are supported. The internal `A-Conductor` data-folder name remains unchanged.

Before publishing a mailbox assignment, the integrator must first generate the exact task packet, re-read it, verify literal identity/HEAD/result destination, and verify its SHA-256 per `DEFECT_LESSONS.md #24`. The mailbox then points to that exact packet + hash and its exact result destination. Publishing replaces the same stable `task.md` atomically.

Human fallback prompt therefore stays constant for that agent: `Read <stable-mailbox>/task.md. Follow only the exact task packet referenced there; write the result to its declared destination. Do not return the result to the human.`
The mailbox may be overwritten for the next assignment only after ownership/state gates prove the prior lane is terminal or explicitly superseded. A result from an older task remains non-authoritative because task/provider/model/base-HEAD identity and exact packet hashes are still checked by the accepted bridge.

Do not create per-agent roadmap, handoff, memory, scheduler or retry files beside the mailbox. Canonical history stays in the active work order, `CURRENT-WORK.md`, `handoff.md`, `DEFECT_LESSONS.md`, Git/PR/CI and deterministic evidence.

Ignored exact task/result artifacts may be retained while a lane is active or under review. After accepted evidence is folded into tracked SSoT and post-merge verification is green, superseded ignored runtime artifacts may be pruned deliberately; never broad-clean worktrees or delete tracked evidence.

The stable mailbox does not claim automatic model invocation. It is the low-friction human bridge until provider readiness/auth/quota and WO118B production enforcement permit no-relay dispatch.
