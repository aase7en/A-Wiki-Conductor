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
acceptance, verification and result destination.

Agent then:
1. reads the task packet;
2. works only inside its lease/scope;
3. writes structured result/evidence to the declared destination;
4. does not edit coordination SSoT unless explicitly assigned;
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
the result back into another chat.

## 6. Parallelism

Only independent READY tasks may run in parallel. Each gets a distinct worktree/lease
or a proven non-overlapping mutable scope. AHA-5 intentionally allows one mutable file
per agent task; AHA-6 owns broader fan-out/fan-in scheduling and collision safety.

## 7. Provider selection gate

Before delegating to a named external model, record recent trustworthy evidence that the
model is suitable for the task class. Benchmark evidence informs routing; it never grants
mutation authority or overrides deterministic review.

## 8. Completion

A lane is complete only when acceptance evidence, diff, tests/CI as required, ownership
release and continuity checkpoint agree. `DONE` from an agent alone is insufficient.
