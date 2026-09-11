# WO-P1-206 — GLM-5.3 20h durable continuation controller v2

Status: ACTIVE CONTROLLER / Q2 READY
Owner: GPT-5.6 Sol integrator for routing; GLM-5.3 is bounded execution/review worker
Base: `02d39cbd9bca1ab3bb19b6e0cfbb0766c991f971`
Branch: `docs/wo-p1-206-glm-master-v2`
Repository: `A:\GitHub\A-Wiki-Conductor`
Primary issue: #214 (ZRA-2)

## Purpose

Provide one durable MASTER controller that lets ZCode GLM-5.3 work deeply for long sessions without depending on chat memory, while preserving external authority gates and multi-lane ownership.

The controller is deliberately not a license to work on every backlog item. It selects exactly one current queue item, drives every READY micro-step inside that item, checkpoints durable state, and stops at the first external gate.

## Supersedes / migrates

WO-P1-200 MASTER remains historical evidence. Its Q1 checkpoint is stale after GPT independent review discovered a P1 publication race and created a bounded repair child.

Historical checkpoint facts:
- GLM Phase-B parent candidate: `865ef3c18ebc5f4fb0f34f40dcee6851295baee4` / PR #280.
- WO200 stopped at `BLOCKED_EXTERNAL_CI` as instructed.
- GPT exact-SHA review later found a deterministic no-clobber race.
- GPT bounded repair candidate: `1c8c159bba74346dce60e6abb7d01ecbd1c17b4e` / PR #281.
- PR #280 and PR #281 CI are now all terminal SUCCESS.

Therefore WO206 starts at Q2. Do not resume WO200 Q1 as active work.

## Controller loop

Within one invocation and one active queue item:

1. REFRESH actual Git/GitHub/runtime/task authority.
2. SELECT only the queue item explicitly READY under durable gates.
3. EXECUTE all safe micro-steps in that item.
4. VERIFY with deterministic/adversarial evidence.
5. CHECKPOINT after material milestones.
6. If more steps in the same item are READY, repeat.
7. At the first external gate, checkpoint and STOP.

Do not switch to a different queue item merely because the current one hit a gate.

## Queue

### Q2 — READY now — independent review of repaired ZRA-2 Phase B

Review lane:
`A:\GitHub\_worktrees\A-Wiki-Conductor-wo204-zra2-review`

Review branch:
`review/wo-p1-204-zra2-phaseb-no-clobber`

Mandatory pointer:
`docs/prompts/GLM-WO204-INDEPENDENT-REVIEW.md`

Work order:
`docs/work-orders/WO-P1-204-zra2-phaseb-no-clobber-independent-review.md`

Read-only candidate worktree:
`A:\GitHub\_worktrees\A-Wiki-Conductor-wo203-zra2-phaseb-no-clobber`

Exact target:
`1c8c159bba74346dce60e6abb7d01ecbd1c17b4e`

Parent candidate:
`865ef3c18ebc5f4fb0f34f40dcee6851295baee4`

PRs:
- #280 parent
- #281 repair
- #282 review packet

At WO206 activation, #280/#281/#282 hosted CI are terminal SUCCESS and PR heads are unchanged. Re-pin again before review.

Q2 is review-only. GLM must not edit candidate source/tests or merge. It may write only WO204 review evidence/checkpoint scope.

Q2 terminal outcomes:
- `PASS` -> checkpoint `BLOCKED_EXTERNAL_GPT_ACCEPTANCE` and STOP.
- `CHANGES_REQUIRED` -> checkpoint `BLOCKED_EXTERNAL_GPT_REPAIR_AUTHORITY` and STOP.
- `SOURCE_DRIFT` / `BLOCKED` -> checkpoint exact blocker and STOP.

No Phase C in the same invocation after Q2 review result. GPT/integrator must adjudicate first.

### Q3 — HOLD — ZRA-2 Phase C trusted review-evidence composition

Preparation packet:
- Draft PR #277
- `docs/work-orders/WO-P1-201-zra2-phase-c-review-evidence-gate.md`
- `docs/prompts/GLM-WO201-ZRA2-PHASE-C.md`

Q3 becomes READY only after ALL:
- Phase B final tree independently accepted;
- required Phase-B merge/post-main verification complete;
- Issue #214 explicitly says Phase C `NEXT_READY`;
- fresh implementation claim/worktree/base/mutable scope exists.

If any missing: `BLOCKED_EXTERNAL_AUTHORIZATION` and STOP.

If GLM authors Phase C, GLM must stop after candidate freeze/CI and cannot self-review or self-accept it.

### Q4 — HOLD — ZRA-2 Phase D execution/result → GoalCloseout composition

Preparation packet:
- Draft PR #283
- `docs/work-orders/WO-P1-205-zra2-phase-d-closeout-binding-gate.md`
- `docs/prompts/GLM-WO205-ZRA2-PHASE-D.md`

Q4 becomes READY only after Phase B + Phase C are accepted/merged/post-main verified and Issue #214 explicitly says Phase D `NEXT_READY`, followed by a fresh scope/claim gate.

Phase D must reuse GoalCloseout and must never create a second direct COMPLETE path.

### Q5 — HOLD — ZRA-3 acceptance/integration

Preserved stack:
- PR #263 parent `e13155b9947c7b42f00853cc5583480741119531`
- PR #269 production child `0bf8f1ed088d234ec51e855cf4e067add5552da0`

The original Phase-A implementation was GLM-authored. This GLM may not claim independent acceptance of its own authored tree. Q5 is therefore an external-review/merge gate unless a future bounded repair task is explicitly assigned.

Do not mutate or merge #263/#269 from this controller without fresh authority.

### Q6 — HOLD — ZRA-4 parallelism hardening

Existing preparation:
- accepted WO196 design
- PR #272 / WO197 physical workspace/scope identity gate
- PR #273 / WO198 deterministic batch identity gate

Q6 becomes READY only after ZRA-3 is accepted/merged/post-main verified and Issue #216 explicitly releases a child implementation scope.

No fan-out/live Worker parallel mutation before C1/C1b/C2 gates are accepted.

## Separate lanes not to steal

- Worker 3 currently belongs to ENV-webapp work.
- Worker 5 currently belongs to Sunday-Estate work.
- Worker 4 being pointed at A-Conductor root does not imply it is free; readiness/claim must be proven before use.
- Worker 2 was the Phase-B implementation lane; frozen candidate must be preserved.
- GPT Phase-D preparation and other integrator docs run on isolated worktrees.
- WO194/PR #266 Worker launcher repair is separate from ZRA-2 critical path.

## External gates

Stop immediately when any applies:
- non-terminal CI;
- GPT/integrator acceptance required;
- merge or post-merge verification required;
- independent review required and current GLM is the author;
- missing/ambiguous claim, owner, scope, branch, worktree, HEAD, or dirty-state provenance;
- source/base SHA drift;
- provider credential/entitlement/quota problem;
- another active lane overlaps mutable files;
- live runtime/process mutation would be needed without a fresh process/claim gate;
- UNKNOWN evidence would need to be guessed into SAFE.

## Checkpoint

Use:
`A:\GitHub\_worktrees\A-Wiki-Conductor-wo206-glm-master-v2\runs\WO-P1-206\checkpoint.json`

Minimum schema fields:
- schema = `wo206-glm-master-checkpoint/1`
- timestamp
- queue_item
- status
- repo/worktree/branch/head
- target/base/candidate SHA where relevant
- claim
- dirty_paths
- completed_steps
- tests/evidence
- PRs
- blocker
- next_safe_action
- previous_checkpoint_migrated_from if applicable

Never store secrets.

## Acceptance of this controller

WO206 itself is docs/control-plane routing only. It never authorizes product source mutation beyond the active child work order's explicit gate.
