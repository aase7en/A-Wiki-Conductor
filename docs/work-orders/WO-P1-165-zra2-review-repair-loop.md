# WO-P1-165 — ZRA-2 automatic review + bounded repair loop

Status: ACTIVATED / IMPLEMENTATION_READY
Parent: WO-P1-155 Zero-Relay Accelerator
Durable issue: GitHub Issue #214
Architecture claim: GPT1-ZRA2-PREFLIGHT-001
Implementation owner: bounded GLM5.3 MAX lane
Acceptance / merge authority: GPT1 integrator
Repository: A-Wiki-Conductor
Branch: feat/wo-p1-165-zra2-review-repair-loop
Worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo165-zra2
Baseline: main@a887e7a76184d8f5dc22446a159087b6f9cab78d

## Identity reconciliation

Historical ZRA-2 notes used WO-P1-159. That ID is now owned by
PR #222 loop-engineering adoption and MUST NOT be reused here.
WO-P1-165 is the canonical implementation identity for ZRA-2.
Issue #214 remains the architecture/preflight authority.

Activation evidence:
- ZRA-1 / PR #221 accepted + merged.
- A-Wiki #53 / PR #55 accepted + merged.
- A-Wiki #54 / PR #56 accepted + merged.
- A-Wiki #54 merge = 967e063cb9dc2e5b43b48a00deb575235f125a94.
- A-Wiki post-main Core CI 34133420008 = SUCCESS.
## Goal

Implement the thinnest production-safe loop:

accepted durable result
-> deterministic verification
-> independent review
-> if rejected, materialize exactly ONE bounded repair task
-> execute replacement task through existing authorities
-> verify + rereview
-> return typed accepted / rejected / recovery outcome

Human prompt/result copy-paste must not be an execution requirement.

## Reuse-before-build classification

REUSE:
- TaskPacketFile task authority.
- AgentResultPacket / durable result evidence.
- AgentRepairRequest + build_repair_task_markdown.
- Review mailbox / A-Wiki ReviewBridge boundary.
- GraphDispatch + DurableJobExecution authorities.
- provider admission and Worker lease authorities.

REFERENCE ONLY:
- feat/wo-p1-155-zero-relay@653eba9 zero_relay.py/tests.

Do NOT cherry-pick that preview. It uses raw prompt/response identity and
in-memory repair prompts, which are superseded by this contract.
## Core invariants

1. Task identity is TaskPacketFile ref/path/full SHA-256, not a free-form prompt.
2. Result identity is a durable result/evidence ref + digest, not response_text.
3. Reviewer output is never self-authorizing execution authority.
4. Author execution identity and reviewer execution identity must be distinct.
5. An addressed blocker remains blocking until independently verified upstream.
6. Exactly one repair task is permitted for this WO.
7. UNKNOWN/timeout/ambiguous execution is RECOVERY_REQUIRED; never blind retry.
8. Repair identity binds the exact rejected durable result + reason code.
9. Repair task materialization is deterministic and idempotent.
10. Existing file with same deterministic repair path + same SHA may be reused.
11. Existing file at repair path with different bytes/SHA is a typed collision.
12. No second scheduler, job store, provider store, lease store, ReviewBus, or retry engine.
13. Parent completion is not implied by provider exit 0 or reviewer prose.
14. No live provider/credentials/Worker/tunnel mutation in implementation tests.

## Initial mutable scope

Phase A is NEW-FILE-ONLY:
- src/a_conductor/zero_relay.py
- tests/test_zero_relay.py
- this work-order file

Shared source files are read-only until an explicit scope-expansion gate passes.
## Explicit forbidden scope

Until separately authorized:
- COLLAB.md
- CURRENT-WORK.md
- handoff.md
- PROJECT-PLAN.md
- PR #222 / WO-P1-159 files
- PR #225 / WO-P1-164 files
- Issue #210 / WO-P1-157 AIP-3 files
- PR #204 / WO-P1-152
- PR #202 / ODP-1
- provider DB/schema
- Worker lease store semantics
- scheduler semantics
- live A-Wiki state files
- credentials / secrets / tunnels

Protected root checkout is never an implementation lane.

## Phase A — durable-reference state machine

Create a pure bounded state machine that:
- accepts verified task/result references, not prompt text;
- validates exact task/result/attempt identity;
- accepts one independent review decision;
- returns ACCEPTED, REPAIR_REQUIRED, REJECTED, or RECOVERY_REQUIRED;
- never performs provider dispatch, Git mutation, review I/O, or file I/O itself;
- cannot request more than one repair generation.
Required Phase-A REDs:
- raw arbitrary prompt is not part of public task contract;
- response_text alone cannot satisfy result identity;
- missing result_ref/hash fails closed;
- foreign result_ref/hash fails closed;
- task-contract ref mismatch fails closed;
- attempt mismatch fails closed;
- same author/reviewer execution identity rejects independence;
- execution UNKNOWN never becomes repair or retry;
- one rejection requests one repair;
- second rejection ends REJECTED with no third execution;
- accepted first result requests zero repair.

## Later phases

Phase B: deterministic repair materializer using existing
AgentRepairRequest + build_repair_task_markdown + confined filesystem,
returning a verified TaskPacketFile.

Phase C: compose existing review adapter / trusted ReviewBridge evidence,
without importing A-Wiki internals or creating a second review lifecycle.

Phase D: bind the accepted ZRA-1 execution/result path and durable job state,
including REVIEW_PENDING -> COMPLETE guard only after exact-head review evidence.

Every phase requires a fresh scope/overlap gate before touching shared files.
## Verification

At each frozen candidate:
- git status is clean before and after tests;
- git diff --check;
- strict UTF-8 / no U+FFFD;
- focused tests for touched module;
- adjacent AgentResult/TaskPacket/Review adapter tests;
- negative identity/recovery tests;
- no secret-bearing output;
- exact-SHA independent review before merge.

Evidence hierarchy:
deterministic reproducer > automated tests > exact diff/state > runtime logs
> independent review > model claim.

## Stop / closeout

GLM implementation does not self-merge.
Freeze one exact SHA after each material phase and checkpoint Issue #214.
Any P0/P1 finding => CHANGES_REQUIRED and one bounded repair packet.
No live provider proof is part of source acceptance.
PROOF/live external execution requires separate GPT1/human authorization.

Next safe implementation action:
Phase A RED-first in the new-file-only scope above.
