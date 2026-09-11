# WO-P1-211 — GLM durable continuation MASTER v3

Status: PREPARED / FUTURE CONTROLLER
Owner: GPT-5.6 Sol integrator
Base at packet creation: `02d39cbd9bca1ab3bb19b6e0cfbb0766c991f971`
Branch: `docs/wo-p1-211-glm-master-v3`
Purpose: durable queue/state machine for long ZCode GLM-5.3 execution without chat-memory dependence

## 1. Why v3 exists

WO200/v1 and WO206/v2 established the stop-at-external-gate pattern. Subsequent durable evidence changed the critical path:

- Phase-B parent PR #280 is not directly mergeable because independent GPT review found a P1 no-clobber race.
- repaired Phase-B tree is PR #281 at `1c8c159bba74346dce60e6abb7d01ecbd1c17b4e`.
- independent review is WO204 / PR #282.
- WO209 now defines a fresh-main fold gate so the defective parent is never landed on main as an accepted standalone state.
- fresh Phase-C archaeology proved mailbox assignment publication and ReviewResultForwarder still have no production callers.
- WO210 therefore splits Phase C into C0 review-task/route provenance before WO201/C1 ReviewEvidence composition.
- WO208 / PR #286 proved closeout external-effect crash/concurrency hazards that WO205 Phase D must consume before effect initiation can be released.
- WO205 was updated to depend on an accepted WO208 effect/recovery contract.

MASTER v3 encodes this queue explicitly so a later GLM invocation resumes from durable state instead of rediscovering or skipping the new gates.

## 2. Controller principle

The controller is a state machine, not a request to stay busy indefinitely.

Loop:

```text
REFRESH durable state
  -> SELECT the single highest-priority READY queue item
  -> VERIFY ownership/scope/dependencies
  -> EXECUTE all READY micro-steps inside that queue item
  -> adversarial VERIFY
  -> CHECKPOINT
  -> if external gate: STOP
  -> otherwise continue same queue item
```

Do not switch to an unrelated queue item merely because the active item hits CI, acceptance, merge, provider or authorization gate.

## 3. Queue

### Q2 — WO204 independent review of repaired Phase B

Review only exact repaired candidate:

`1c8c159bba74346dce60e6abb7d01ecbd1c17b4e`

Parent known-defective candidate:

`865ef3c18ebc5f4fb0f34f40dcee6851295baee4`

Review packet:

`A:\GitHub\_worktrees\A-Wiki-Conductor-wo204-zra2-review\docs\prompts\GLM-WO204-INDEPENDENT-REVIEW.md`

If another active GLM already owns Q2, do not duplicate it. Observe durable owner/checkpoint and return `BLOCKED_EXTERNAL_OWNER`.

Successful Q2 ends at `BLOCKED_EXTERNAL_GPT_ACCEPTANCE`. GLM does not fold/merge Phase B from the reviewer role.

### Q2F — Phase-B fresh-main fold

Owner: GPT/integrator, not GLM by default.

Authority:

`WO-P1-209-zra2-phase-b-fold-gate.md`

GLM does not perform this fold unless a future explicit implementation/integration claim assigns it. It is an external gate for the normal MASTER.

Required completion before Phase C:

- WO204 exact review accepted;
- fold from fresh main preserves exact reviewed path bytes;
- fold candidate CI green;
- merge/post-main path-byte proof green;
- Issue #214 records Phase B `ACCEPTED + MERGED + POST_MAIN_VERIFIED`.

### Q3 — Phase C0 review-task + trusted-route provenance

Only after Issue #214 says `PHASE_C0_NEXT_READY`.

Future implementation packet:

`docs/prompts/GLM-WO210-ZRA2-PHASE-C0.md`

C0 sequence:

```text
C0a ResultIdentity -> deterministic review TaskPacketFile
C0b exact packet + scheduler/provider/lease route -> trusted review binding
```

C0 must not invent mailbox agent identity. External mailbox publication is blocked unless an authoritative mapping exists. Direct programmatic ZCode review is the preferred initial production route.

If GLM authors C0 source, it stops after freeze/CI at independent acceptance. It cannot self-review/merge Q3.

### Q4 — Phase C1 trusted ReviewEvidence composition

Only after C0 accepted, merged and post-main verified and Issue #214 releases C1.

Packet:

`docs/prompts/GLM-WO201-ZRA2-PHASE-C.md`

C1 consumes exact C0 provenance + trusted review result + durable reviewer execution and produces existing `zero_relay.ReviewEvidence` without creating a second review lifecycle.

If GLM authors C1, stop after freeze/CI at independent acceptance.

### Q5 — Phase D durable result/review -> GoalCloseout composition

Only after Phase B and all Phase C stages are accepted/merged/post-main and Issue #214 releases Phase D.

Packet:

`docs/prompts/GLM-WO205-ZRA2-PHASE-D.md`

Additional prerequisite:

WO208 closeout crash-boundary lab + parent/integrator decision must be accepted first.

Phase D must:

- bind exact durable author result;
- bind exact accepted independent review;
- re-read current job/candidate authority;
- preserve `GoalCloseoutExecutor` as sole final COMPLETE authority;
- obey accepted WO208 external-effect idempotency/query/recovery contract;
- keep UNKNOWN effects in RECOVERY_REQUIRED rather than blind replay.

If GLM authors Phase D, stop after freeze/CI for independent review.

### Q6 — ZRA-3 acceptance/release

Existing stack:

- PR #263 repaired Phase-A parent: `e13155b9947c7b42f00853cc5583480741119531`
- PR #269 production composition: latest known stack SHA `0bf8f1ed088d234ec51e855cf4e067add5552da0`
- WO199 / PR #274 independent review packet

Do not mutate or self-accept this stack merely because ZRA-2 completed. Re-pin exact SHAs, ownership and independent review status. GLM authorship history means the same author model must not claim independent acceptance of code it authored.

### Q7 — ZRA-4

Only after ZRA-3 accepted and Issue #216 explicitly releases implementation.

Prepared gates:

- merged WO196 physical workspace identity design;
- WO197 / PR #272 C1/C1b implementation gate;
- WO198 / PR #273 deterministic batch identity gate.

No fan-out until physical identity + deterministic batch identity + live claim/lease/provider capacity gates are accepted.

## 4. Parallel lanes not to steal

The following may be active independently and are not escape work when the zero-relay queue is blocked:

- WO208 closeout crash-boundary design/lab (`PR #286`, Codex/Astra owner at packet creation);
- WO207 / PR #285 Worker launcher marker guard;
- WO194 / PR #266 launcher forensics stack;
- WO202 helper post-spawn cleanup backlog;
- ZRA-4 preparation lanes;
- ENV / Sunday-Estate Workers.

Observe them for dependency evidence but do not mutate their scope without an explicit transfer.

## 5. Checkpoint migration

Older checkpoints are provenance, not automatic current authority.

At startup read, in order if present:

- WO211 checkpoint;
- WO206 checkpoint;
- WO200 checkpoint;
- active queue-item result/checkpoint;
- actual Git/GitHub/runtime state.

If they conflict, actual durable current state wins and the new checkpoint must record the migration.

Examples:

- WO200 Q1 at parent `865ef3c...` is historical; do not resume parent implementation.
- WO206 Q2 remains current only until WO204 handback is accepted.
- after Phase-B fold/post-main, Q2/Q2F become DONE and Q3 may become eligible only with explicit Issue #214 release.

## 6. Checkpoint schema

Preferred path in the WO211 controller worktree:

`runs/WO-P1-211/checkpoint.json`

Minimum fields:

```json
{
  "schema": "wo211-glm-master-checkpoint/1",
  "timestamp": "ISO-8601",
  "queue_item": "Q2|Q2F|Q3|Q4|Q5|Q6|Q7",
  "status": "WORKING|BLOCKED_EXTERNAL_CI|BLOCKED_EXTERNAL_GPT_ACCEPTANCE|BLOCKED_EXTERNAL_MERGE|BLOCKED_EXTERNAL_AUTHORIZATION|BLOCKED_EXTERNAL_OWNER|BLOCKED_EXTERNAL_PROVIDER|RECOVERY_REQUIRED|DONE",
  "repo": "A-Wiki-Conductor",
  "worktree": "...",
  "branch": "...",
  "head": "...",
  "candidate_sha": null,
  "pr": null,
  "claim": null,
  "dirty_paths": [],
  "tests": [],
  "blocker": null,
  "dependencies": [],
  "next_safe_action": "..."
}
```

Never store secrets.

## 7. Stop rules

Stop immediately after the current atomic safe step on:

- non-terminal hosted CI;
- GPT/integrator acceptance;
- independent review owned by another model/agent;
- merge/post-main verification;
- missing Issue release;
- missing claim/scope;
- overlapping active owner;
- provider/credential/entitlement/quota gate;
- source/base drift invalidating packet;
- UNKNOWN execution/effect/review/ownership state;
- need to widen mutable source scope.

Checkpoint, hand back exact SHA/PR/blocker/next safe action, then STOP. Do not sleep/poll repeatedly and do not start unrelated backlog work.

## 8. Author/reviewer separation

Track author identity by queue item.

A model/agent that authored source may run self-audit but cannot supply final independent acceptance for that exact candidate.

Reviewer lanes are read-only against candidate source. If reviewer finds P0/P1/P2, return `CHANGES_REQUIRED`; do not repair in the reviewer branch.

Any repair gets a fresh bounded child scope and then a new independent exact-SHA review.

## 9. Mutation safety

Every mutation invocation must re-pin:

- repo/remote;
- worktree/branch/HEAD;
- origin/main;
- dirty/untracked state;
- issue/work order;
- owner/claim/lease;
- mutable/forbidden paths;
- overlapping open PR/worktrees;
- required provider/runtime state if relevant.

Unknown material state means `SAFE_TO_MUTATE=NO`.

No reset/clean/stash/rebase/force-push merely to obtain cleanliness.

## 10. Long-run intent

This controller is sized for long GLM work sessions, but useful duration is determined by READY work, not a target number of hours.

Inside an authorized queue item, GLM should work deeply: archaeology, RED-first tests, implementation, adversarial campaigns, related regression ladders, durable result/checkpoint, exact candidate freeze and Draft PR.

At an external gate it must stop even if substantial token/quota remains. The next invocation resumes from durable state.