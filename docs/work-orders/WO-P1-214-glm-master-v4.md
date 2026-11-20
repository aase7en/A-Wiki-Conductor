# WO-P1-214 — GLM durable continuation MASTER v4

Status: PREPARED / SUCCESSOR CONTROLLER / DO NOT PREEMPT ACTIVE WO212
Owner: GPT-5.6 Sol integrator
Preferred executor: ZCode GLM-5.3
Risk: orchestration R3; this packet itself is docs-only
Base at creation: `a23149640750579c94369eb5a6730bba757ff772`
Parent roadmap: `docs/plans/2026-09-04-zero-relay-accelerator-roadmap.md`
Primary authority issue: GitHub Issue #214

## 1. Purpose

Provide a durable, resumable long-shift controller for GLM-5.3 that can work deeply for many hours inside one authorized queue item without depending on chat context or model context length.

The controller must never convert available compute time into permission to cross an external authority gate.

Correct behavior is:

`re-pin actual state -> choose exactly one READY authorized queue item -> work deeply -> verify/adversarially falsify -> checkpoint -> STOP at first external gate -> resume from durable state on next invocation`.

A 20-hour budget is capacity, not a requirement to manufacture work.

## 2. Creation-time durable snapshot

This snapshot is provenance only. Every invocation must re-pin actual Git/GitHub/runtime state before relying on it.

- `origin/main = a23149640750579c94369eb5a6730bba757ff772` after accepted docs-only WO208 merge.
- ZRA-2 Phase-B repaired source `1c8c159bba74346dce60e6abb7d01ecbd1c17b4e` was independently reviewed by WO204 and accepted by GPT/integrator.
- WO204 review commit `4a63d912bb269f44e2c685d296cd5823218907c5` records PASS, P0/P1/P2=0.
- PR #282 review-evidence branch had one unrelated Windows real-process stop failure in `tests/test_owned_process.py`; this does not invalidate exact candidate #281, whose own CI is terminal green.
- WO213 fresh-main fold candidate: PR #291, head `1badb95d2e226b150cf8d14cf70d2ac8addf57b8`, base `a231496...`; at MASTER creation hosted CI was non-terminal.
- WO213 preserves six reviewed Phase-B paths byte-for-byte from `1c8c159...` and locally passed 321 tests + 1 POSIX-only skip.
- WO210 Phase-C0 design/prompt: PR #288; implementation remains HOLD until Phase-B fold accepted+merged+post-main verified and Issue #214 explicitly releases C0 with a fresh claim.
- WO201 Phase-C1 trusted review-evidence composition: PR #277; HOLD until C0 accepted+merged+post-main and explicit release.
- WO208 crash-boundary design is accepted+merged; it proved external fold/release effects can occur before job checkpoint CAS. Its GLM crash lab/recovery contract evidence remains a Phase-D prerequisite when explicitly released.
- WO205 Phase-D gate: PR #283; source implementation remains HOLD.
- WO212 launcher-stack independent review is a separate Worker-resilience lane. The user invoked GLM on WO212 before this MASTER was created. Do not preempt or co-own that review.
- ZRA-3 stack remains dependency-blocked by full ZRA-2 acceptance. GLM authored original ZRA-3 Phase-A and must not self-accept the whole ZRA-3 stack.
- ZRA-4 remains blocked by ZRA-3 acceptance and Issue #216 release.

## 3. Long-shift design

GLM may use a large execution budget, but durable state must make context length irrelevant.

Use:

- `runs/WO-P1-214/checkpoint.json` — machine-readable current state;
- `runs/WO-P1-214/notes.md` — compact rolling discoveries/decisions, not raw logs;
- queue-item-specific `runs/<WO>/...` evidence required by that WO;
- tracked review/result docs only when the active WO authorizes them.

After each meaningful milestone, update checkpoint. Do not wait for context pressure.

When output/logs are large:

1. save them under the active WO's allowed evidence path;
2. record command, exit code, artifact path, concise finding in notes/checkpoint;
3. do not paste full logs repeatedly into prompts or result docs;
4. on resume, read the compact checkpoint first, then only evidence needed for the next unresolved question.

Never use chat history or model recollection as authority.

## 4. Queue selection invariant

Exactly one queue item may be ACTIVE per invocation.

Do not hit an external gate in one item and then switch to another backlog item to remain busy.

At startup, select the first item whose dependencies are durably satisfied and whose scope/claim is explicitly released.

If an earlier critical-path item is blocked by an external gate, report that gate and STOP.

## 5. Q0 — active-owner / previous-invocation gate

Before choosing new work:

- inspect current claims/worktrees/processes/branches;
- inspect WO212 branch/PR if it is the current GLM assignment;
- inspect prior WO214 checkpoint if present;
- treat WO200/WO206/WO211 checkpoints as historical migration input only.

If WO212 or another GLM task is still active/dirty/uncheckpointed and this invocation would overlap it:

`BLOCKED_EXTERNAL_OWNER`

and STOP.

Do not run two GLM mutation/review goals in one worktree or branch.

## 6. Q1 — ZRA-2 Phase-B fresh-main fold gate

Authority: WO209 + WO213 / PR #291.

### If PR #291 CI is non-terminal

Checkpoint:

`BLOCKED_EXTERNAL_CI`

STOP. No polling loop.

### If PR #291 CI fails

Read the exact failed job once.

- if the failure is clearly unrelated infrastructure/flaky and source bytes are unchanged, checkpoint `BLOCKED_EXTERNAL_GPT_ACCEPTANCE` with evidence;
- if it exposes an owned deterministic defect, do not edit reviewed source under this MASTER. Checkpoint `BLOCKED_EXTERNAL_GPT_REPAIR_AUTHORITY` and STOP;
- if ambiguous, `RECOVERY_REQUIRED` and STOP.

### If PR #291 CI is terminal SUCCESS but PR is not merged

Checkpoint:

`BLOCKED_EXTERNAL_GPT_ACCEPTANCE`

STOP. GLM must not merge WO213.

### If WO213 is merged

Re-pin `origin/main` and verify:

- merge contains exact WO213 accepted tree;
- six accepted Phase-B paths still match reviewed bytes or the accepted post-merge fold identity;
- no later commit changed those paths unexpectedly;
- run only the post-main focused verification requested by the integrator/Issue #214.

Then STOP unless Issue #214 explicitly publishes Phase-C0 `NEXT_READY` with a fresh implementation claim.

## 7. Q2 — ZRA-2 Phase C0 review-task binding/materialization

Only READY when all are true:

1. Phase-B WO213 accepted+merged;
2. required post-main verification green;
3. Issue #214 explicitly says C0/NEXT_READY;
4. fresh child WO/claim names executor, base SHA, branch, worktree, mutable paths, forbidden paths;
5. no overlapping mutable lane.

Pointer:

`docs/prompts/GLM-WO210-ZRA2-PHASE-C0.md`

Canonical objective:

- C0a: deterministically bind exact `zero_relay.ResultIdentity` into an exact review `TaskPacketFile`;
- C0b: bind that packet to trusted scheduler/provider/lease/dispatch route facts without caller-forged provider/model/head/worktree authority;
- preserve generic mailbox/review authorities rather than inventing a ZRA-specific review bus;
- direct ZCode review route does not require invented external mailbox `agent_id`;
- external mailbox publication must fail closed if no authoritative worker->mailbox-agent identity mapping exists.

Do RED-first work, adversarial identity drift tests, deterministic packet/path tests, route mismatch tests, replay/collision tests, no-authority-import tests, compile/diff/scope/secret checks, freeze exact candidate, Draft PR, then STOP at hosted CI.

Do not self-accept or self-merge.

## 8. Q3 — ZRA-2 Phase C1 trusted review-evidence composition

Only READY after C0 exact candidate is independently accepted, merged, post-main verified, and Issue #214 publishes a new C1 claim.

Pointer:

`docs/prompts/GLM-WO201-ZRA2-PHASE-C.md`

Canonical objective:

compose trusted review result + exact assignment/task + durable reviewer execution + exact author `ResultIdentity` into existing `zero_relay.ReviewEvidence`.

Do not let reviewer prose mint:

- author result ref/hash;
- attempt;
- generation;
- task contract ref;
- reviewer execution identity;
- merge/ready authority.

If exact author-result binding cannot be proven from accepted C0/C1 inputs, return `DESIGN_GAP_RESULT_BINDING` and STOP.

## 9. Q4 — WO208 crash/effect recovery lab

This is not automatically READY merely because WO208 design is merged.

Only run the WO208 GLM lab when its owner/Issue #214 explicitly releases it and no earlier ZRA-2 external gate blocks the critical path.

Pointer in accepted WO208 docs:

`docs/prompts/GLM-WO208-CLOSEOUT-CRASH-LAB.md`

The lab may legitimately consume a long compute/reasoning budget. Required spirit:

- preserve the four accepted seed counterexamples;
- add real child-process exit/lost-ack/process-ordering experiments;
- Windows SQLite behavior where useful;
- two-process effect ordering;
- explicit false-positive controls;
- finite-state/model reasoning where productive;
- distinguish synthetic seam evidence from production reachability;
- no production source mutation;
- no live provider/worker mutation;
- checkpoint durable evidence frequently.

External gate after evidence handback: parent GPT/WO205 design adjudication.

## 10. Q5 — ZRA-2 Phase D execution/result/review -> GoalCloseout composition

Only READY after:

- Phase B accepted+merged+post-main;
- C0+C1 accepted+merged+post-main;
- accepted WO208 crash/effect evidence is consumed into a parent decision;
- Issue #214 publishes Phase D `NEXT_READY`;
- fresh R3 scope/claim exists.

Pointer:

`docs/prompts/GLM-WO205-ZRA2-PHASE-D.md`

Phase D must NOT create a second completion state machine.

It must preserve:

`exact task/result/execution identity -> accepted independent review -> current durable job/candidate -> existing GoalCloseoutExecutor`.

It must not call `JobStore.transition(COMPLETE)` directly.

External fold/release effects may not be treated as safe merely because later JobStore CAS exists. Effect eligibility, exact operation identity and durable reconcile/UNKNOWN behavior must follow the accepted WO208 parent decision.

UNKNOWN never grants replay permission.

## 11. Q6 — ZRA-3 gate

Do not start automatically from this MASTER unless Issue #214 / relevant ZRA-3 authority explicitly releases a precise child scope.

Known preserved stack includes PR #263/#269 and review packet #274.

Because GLM authored original WO191 Phase-A, GLM may not be the independent final accepter of the entire repaired ZRA-3 stack.

At an acceptance gate, STOP for an independent reviewer/integrator.

## 12. Q7 — ZRA-4 gate

No ZRA-4 source implementation until:

- ZRA-3 accepted/merged/post-main;
- Issue #216 releases child scope;
- fresh physical-identity/batch-identity scope is reconciled with WO196/197/198 and any newer evidence.

Do not infer Windows path identity from string normalization alone.

## 13. Separate Worker-resilience lane

WO212 reviews PR #266 + #285. It is not part of the ZRA-2 queue and must not be used to escape a ZRA external gate.

If WO212 review returns PASS, final acceptance/merge/deployment remains GPT/integrator authority.

Do not restart/deploy live Workers merely because source review passes.

## 14. Checkpoint schema

Path:

`runs/WO-P1-214/checkpoint.json`

Minimum structure:

```json
{
  "schema": "wo214-glm-master-checkpoint/1",
  "timestamp": "ISO-8601",
  "queue_item": "Q1|Q2|Q3|Q4|Q5|Q6|Q7",
  "status": "WORKING|BLOCKED_EXTERNAL_CI|BLOCKED_EXTERNAL_GPT_ACCEPTANCE|BLOCKED_EXTERNAL_GPT_REPAIR_AUTHORITY|BLOCKED_EXTERNAL_MERGE|BLOCKED_EXTERNAL_AUTHORIZATION|BLOCKED_EXTERNAL_OWNER|BLOCKED_EXTERNAL_PROVIDER|RECOVERY_REQUIRED|DONE_LOCAL",
  "repo": "A-Wiki-Conductor",
  "base_sha": "...",
  "worktree": "...",
  "branch": "...",
  "head": "...",
  "candidate_sha": null,
  "claim": null,
  "dirty_paths": [],
  "tests": [],
  "findings": [],
  "evidence_refs": [],
  "pr": null,
  "blocker": null,
  "next_safe_action": "..."
}
```

Never write secrets/tokens/credential values.

## 15. Long-run anti-waste rules

A large budget does not justify repeated identical commands.

For each hypothesis:

1. state what invariant is being challenged;
2. create the smallest deterministic reproducer;
3. include a positive control;
4. record whether evidence is new or duplicate;
5. stop repeating once the invariant is sufficiently characterized.

Prefer barriers/fault injection/state models over sleep-based races.

Prefer targeted tests first, justified regression expansion second, full suite/hosted CI at freeze.

Do not spend hours polling CI, waiting for providers, or rerunning a passing test without a falsification purpose.

## 16. Repository safety

Never use reset/clean/stash/rebase/force-push to obtain cleanliness.

Never overwrite unexplained dirty files.

Never switch another agent's active branch/worktree.

Never modify live credentials, provider secrets, live databases, or active Worker processes unless a future exact work order explicitly authorizes that operation.

A visible plugin or worktree does not mean it is free.

## 17. Final stop rule

At the first external gate:

- finish only the current atomic safe step;
- update durable checkpoint;
- write the active WO result/evidence required by its packet;
- commit/push only if the active WO explicitly authorizes freeze;
- print concise handback with exact SHA/PR/verdict/blocker/next safe action;
- STOP.

Do not ask the human to relay information that Git/GitHub/durable files can provide.

Do not start another queue item during the same invocation after an external gate.
