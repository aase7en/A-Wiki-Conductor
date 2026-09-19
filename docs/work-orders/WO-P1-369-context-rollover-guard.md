# WO-P1-369 — Context Rollover Guard + Durable Recovery Pointer MVP

Date: 2026-09-19
Owner: GPT-5.6 Sol integrator / mutation owner
Status: CLAIMED / RED_FIRST
Issue: #369
Identity schema: GITHUB_ISSUE_V1
Risk: R3 — continuity / authority-adjacent
Task topology: CONTROL_PLANE_ONLY

## Binding

Authority repo: `aase7en/A-Wiki-Conductor`

Worktree:
`/Users/aase7en/GitHub/_worktrees/awiki-wo258-context-rollover`

The physical worktree directory retained its pre-rebind `wo258` pathname
after the branch-name collision reconciliation; the directory name is
historical only and does NOT represent WO-P1-258 task authority.

Branch:
`feat/wo-p1-259-context-rollover-guard`

This is a retained historical transport branch name only (the remote PR
transport branch); branch naming grants no task authority. Canonical task
identity is WO-P1-369 / Issue #369 (GITHUB_ISSUE_V1).

Base:
`origin/main@95c4b9e78003c4b61083650d1698c6661f9bb545`

Owner:
GPT-5.6 Sol

Claim:
`WO-P1-369-CONTEXT-ROLLOVER-001`
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

Binding factual repair (2026-09-19, claim
`WO-P1-259-BINDING-FACT-REPAIR-001`, lane `fix/wo-p1-259-binding-fact`):
independent exact-SHA review returned PASS with P0/P1/P2=0 but flagged the
Binding block's pre-collision names. Docs-only correction at dispatch HEAD
`e4d9fa30d453510c2df7026499ee7ae8e079d73c`: the branch of record is now
truthfully `feat/wo-p1-259-context-rollover-guard` (remote head at that SHA),
and the Binding note above explains the retained worktree pathname. No
behavioral acceptance criteria or implementation claims were changed.


## 2026-09-19 current-main re-pin checkpoint

- Re-pin worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo259-repin-20260919`.
- Re-pin baseline: `origin/main@2a461ae22ab28ad3b48f15660ab818f700faab30` (accepted DEX-ARCH-1 + WO-P1-260 durable-lane overlay + accepted WO-P1-258 Hook Contract v1).
- Merge-forward checkpoint before this docs note: `53fcace634a0d6fbc96140684e834e91fb684c93`.
- The four WO259 scoped blobs at that merge-forward checkpoint are byte-identical to reviewed candidate `a2e149352ad3ba1a4fcb8b3045169541ab5cfd04`; no source/test/entry behavior changed during re-pin.
- Re-pinned continuity battery: 245 passed (`context_rollover_guard`, `continuity_guard`, `continuity_projection`, `goal_closeout`).
- This checkpoint changes factual binding only. Exact-head review and hosted CI must bind the new frozen SHA; prior review remains semantic evidence only.

## 2026-09-19 identity rebind checkpoint — WO-P1-369

Identity-only rebind (claim `WO-P1-369-CONTEXT-ROLLOVER-REBIND-001`, lane
`fix/wo-p1-369-context-rollover-rebind`, worktree
`A:\GitHub\_worktrees\A-Wiki-Conductor-wo369-context-rebind`, dispatch HEAD
`95c87ab8aa7027eabc462a888e93c8428665a768`): this lane is GitHub Issue #369,
so canonical task identity is now WO-P1-369 (identity schema GITHUB_ISSUE_V1)
and the current canonical claim is `WO-P1-369-CONTEXT-ROLLOVER-001`.

All prior WO-P1-258/WO-P1-259 identities recorded in earlier checkpoints,
binding notes, branches, worktree names, review evidence, and SHAs above are
historical only and retain no task authority; they are preserved unchanged as
truthful historical record. The remote PR transport branch remains named
`feat/wo-p1-259-context-rollover-guard`; that name is retained historical
transport naming only.

This rebind changed identity references only: the module docstring of
`src/a_conductor/context_rollover_guard.py`, the single context-rollover WO
reference in `00-AGENT-ENTRY.md`, and this work order's header/binding
identity plus this checkpoint. Behavioral code, tests, and all historical
checkpoint facts are unchanged. Behavioral semantics are frozen per the
prior exact-SHA review of `95c87ab` (PASS, P0/P1/P2/P3=0).