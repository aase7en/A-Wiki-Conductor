# WO-P1-259 — Context Rollover Guard + Durable Recovery Pointer MVP

Date: 2026-09-19
Owner: GPT-5.6 Sol integrator / mutation owner
Status: CLAIMED / RED_FIRST
Issue: #369
Risk: R3 — continuity / authority-adjacent
Task topology: CONTROL_PLANE_ONLY

## Binding

Authority repo: `aase7en/A-Wiki-Conductor`

Worktree:
`/Users/aase7en/GitHub/_worktrees/awiki-wo258-context-rollover`

Branch:
`feat/wo-p1-258-context-rollover-guard`

Base:
`origin/main@95c4b9e78003c4b61083650d1698c6661f9bb545`

Owner:
GPT-5.6 Sol

Claim:
`WO-P1-259-CONTEXT-ROLLOVER-001`
## Goal

Add the smallest deterministic session/context rollover guard that lets an
ordinary ChatGPT/agent session decide when to continue, checkpoint, or rotate
without pretending it can read an exact context-window percentage and without
making chat memory project authority.

The guard consumes existing ContinuityGuard truth plus explicit session facts.
It creates no durable store and performs no side effects.

## Reuse-before-build classification

`REUSE + EXTEND`.

Reuse:
- `ContinuityVerdict` / ContinuityGuard;
- existing durable Work Order / task / job / checkpoint / claim / lease facts;
- existing Git/GitHub evidence and delegated-run recovery pointers;
- existing checkpoint/handoff projections;
- future Hook/STM roadmap as an adapter consumer, not an authority.

Forbidden:
- second task/job/checkpoint/claim/lease store;
- new scheduler/retry/review/completion authority;
- STM subsystem or chat-memory database;
- token-count fabrication;
- parsing Markdown back into project authority;
- hidden network/process/filesystem mutation.
## Mutable scope

New:
- `src/a_conductor/context_rollover_guard.py`
- `tests/test_context_rollover_guard.py`

Modify:
- `00-AGENT-ENTRY.md`
- this Work Order

Read-only:
- `src/a_conductor/continuity_guard.py`
- `src/a_conductor/goal_closeout.py`
- `src/a_conductor/continuity_projection.py`
- durable stores / lease / job / provider / execution modules
- `CURRENT-WORK.md`, `handoff.md`, `COLLAB.md`
- Hook/STM runtime roadmap implementation

## Contract

Inputs are explicit immutable facts:

- `context_pressure = NORMAL | CROWDED | NEAR_LIMIT | UNKNOWN`;
- existing `ContinuityVerdict`;
- checkpoint state `CURRENT | STALE | UNKNOWN`;
- whether mutation happened after the checkpoint;
- active task recovery pointer state;
- outstanding delegated execution count;
- whether every outstanding execution is recoverable by durable identity/evidence.
Outputs:

- `GREEN` — safe to continue under current continuity facts;
- `YELLOW` — checkpoint/recovery refresh recommended before more substantial
  work or before rotation;
- `RED` — stop new non-trivial mutation; checkpoint/reconcile/recover before
  session rotation or continuation.

The output is advisory/session-safety policy only. It never grants mutation
authority. `ContinuityVerdict.safe_to_mutate=False` always dominates.

No exact context percentage is produced.

## RED acceptance matrix

1. NORMAL + FRESH + current checkpoint + no post-checkpoint mutation + ready
   recovery pointer + no outstanding executions -> GREEN.
2. CROWDED with otherwise-good facts -> YELLOW / checkpoint recommended.
3. NEAR_LIMIT with stale/unknown checkpoint or post-checkpoint mutation -> RED.
4. UNKNOWN context pressure -> at least YELLOW; never optimistic GREEN.
5. non-FRESH ContinuityVerdict -> RED regardless of context pressure.
6. missing/unknown active-task recovery pointer -> RED at NEAR_LIMIT and at
   least YELLOW otherwise.
7. outstanding executions with missing/unknown durable recovery evidence -> RED.
8. outstanding executions proven recoverable may remain GREEN only when all
   other facts are current and pressure NORMAL.
9. same immutable snapshot -> value-stable idempotent verdict.
10. invalid enum/count/bool inputs fail closed by validation, not coercion.
11. output includes deterministic reason codes and ordered required actions.
12. `rotation_ready=True` only when checkpoint is current, no mutation occurred
    after it, active-task recovery pointer is ready, and outstanding executions
    are recoverable. A non-FRESH ContinuityVerdict still forces RED and blocks
    mutation, but may be handed to a new session when that unsafe state itself
    is durably checkpointed; rotation never upgrades mutation authority.

## Ordinary-chat behavioral fallback

`00-AGENT-ENTRY.md` will state that ordinary ChatGPT cannot claim an exact
remaining-context percentage. When the session is materially crowded,
near practical rollover, or uncertainty rises, agents use this contract
conceptually: checkpoint existing durable authority first, preserve execution
pointers, then rotate. A new session recovers actual state instead of asking
the user to paste old chat history.

Future native Hook/PreCompact adapters may feed this contract, but they must
not redefine its authority rules.

## Verification

RED-first targeted tests -> GREEN -> deterministic idempotence/adversarial
matrix -> related ContinuityGuard tests -> compileall -> diff/scope/UTF-8/
secret checks -> frozen exact SHA -> independent exact-SHA R3 review -> hosted
CI -> GPT acceptance.

No merge before all R3 gates pass.

## Implementation checkpoint — 2026-09-19

RED proof:
- commit `f12a1b027fd166d26e710fd1c87e6ac92ecccdd3`;
- focused collection failed with `ModuleNotFoundError` because the production
  module did not yet exist.

GREEN implementation:
- pure `context_rollover_guard.py`; no filesystem/network/process/store I/O;
- existing ContinuityGuard verdict remains mutation authority;
- rotation readiness is deliberately separate from mutation readiness: a
  durably checkpointed non-FRESH state may rotate, but the next session remains
  fail-closed until reconciliation;
- ordinary-chat fallback is projected through `00-AGENT-ENTRY.md`.

Deterministic local evidence before freeze:
- WO259 focused matrix: 22 passed;
- Context/Continuity/GoalCloseout/Projection battery: 245 passed;
- compileall: PASS;
- `git diff --check`: PASS;
- strict UTF-8 / no replacement bytes: PASS;
- bounded secret-pattern scan: PASS.

Next gate: commit/freeze exact candidate SHA, independent exact-SHA R3 review,
hosted exact-head CI, then GPT acceptance. No self-review merge.
