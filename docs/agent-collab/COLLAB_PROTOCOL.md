# Provider-Neutral Agent Collaboration Protocol

Purpose: let GPT, GLM, Claude, Codex, local models, and future agents work on one project without relying on chat memory or human result copy/paste.

## 1. Entry sequence

Before non-trivial work, read:
1. `00-AGENT-ENTRY.md`
2. `PROJECT-PLAN.md` + `DESIGN.md`
3. `COLLAB.md`
4. `CURRENT-WORK.md`
5. `handoff.md`
6. active `docs/work-orders/<id>.md`
7. `DEFECT_LESSONS.md` before `src/` mutation
8. this lane index only when multi-agent work is active

Actual repo/runtime state overrides stale summaries.

## 2. Safety gate

Mutation requires all of:
- exact repository/worktree/remote/branch/HEAD;
- known dirty-state ownership;
- task owner and active bounded claim/lease;
- non-overlapping mutable scope;
- explicit allowed + forbidden scope;
- acceptance criteria and verification;
- durable result/evidence destination.

If any item is uncertain: `SAFE_TO_MUTATE = NO`.

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

## 7. Provider selection gate

Before delegating to a named external model, record recent trustworthy evidence that the
model is suitable for the task class. Benchmark evidence informs routing; it never grants
mutation authority or overrides deterministic review.

## 8. One-goal orchestration + loop-engineer cycle

A human may state the goal once. The integrator owns decomposition, model routing, task packets, result ingestion and SSoT fold-back. For material work use this ordered loop:

`recover SSoT/actual Git -> Grill Me with docs -> brainstorm -> explicit plan/task gate -> implement -> independent exact-SHA review -> root-cause debug -> targeted + realistic E2E/adversarial tests -> evidence report -> defect-prevention memory -> audit -> active-WO branch/PR -> exact-head CI/CD -> re-audit -> authorized merge/fetch proof -> cleanup proof`.

Rules:
- verify the local `grill-with-docs` against its upstream GitHub source when materially planning; record date/ref or mark `UPSTREAM_UNVERIFIED`;
- grilling/brainstorming never authorizes mutation by itself: an explicit bounded plan/task/claim gate must exist first;
- subagents are advisory or separately leased lanes, never hidden shared writers;
- branch names come from the active WO; never hard-code a generic health branch over unrelated work;
- provider/model benchmarks route work only after freshness/task-fit review; provider readiness/auth/quota remains a separate gate;
- review and CI evidence are pinned to exact SHA; transport/tool failures are not product failures or passes.

## 9. Completion

A lane is complete only when acceptance evidence, diff, tests/CI as required, ownership
release and continuity checkpoint agree. `DONE` from an agent alone is insufficient.
