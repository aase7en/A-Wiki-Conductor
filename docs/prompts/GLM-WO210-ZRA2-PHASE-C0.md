# GLM / WO-P1-210 — ZRA-2 Phase C0 deterministic review-task + trusted route binding

STATUS: HOLD — DO NOT IMPLEMENT UNTIL RELEASED

You are ZCode GLM-5.3 acting as a bounded implementation worker. This packet is intentionally prepared before release so you can work deeply without rediscovering the architecture after Phase B is accepted.

Read first:

1. `docs/work-orders/WO-P1-210-zra2-phase-c0-review-task-binding-gate.md`
2. `docs/work-orders/WO-P1-201-zra2-phase-c-review-evidence-gate.md`
3. `docs/work-orders/WO-P1-165-zra2-review-repair-loop.md`
4. current Issue #214 durable state
5. current repository entry/governance routing and `DEFECT_LESSONS.md`

## 1. Release gate

Before any source/test mutation, prove from durable Git/GitHub state that:

- repaired Phase B received independent WO204 PASS;
- GPT/integrator accepted that exact reviewed tree;
- WO209 fold landed Phase B on current main with post-main byte + CI verification;
- Issue #214 explicitly says `PHASE_C0_NEXT_READY`;
- fresh C0 implementation claim names owner, worktree, branch, base SHA, mutable paths and forbidden paths;
- worktree is isolated and clean except explained owned changes;
- no overlapping mutable lane exists.

If any item is false/unknown:

`BLOCKED_EXTERNAL_AUTHORIZATION`

Write a durable checkpoint and STOP. Do not create source WIP and do not jump to Phase C1/Phase D/backlog.

## 2. Mission

Implement only the missing production provenance seam between exact author ResultIdentity and a trusted independent review route.

Do NOT implement a new review lifecycle.

The intended flow is:

```text
ResultIdentity
  -> C0a deterministic review TaskPacketFile
  -> existing scheduler/provider/lease route
  -> C0b exact route binding
  -> reviewer execution
  -> existing review result reader / ReviewBridge forward
  -> later WO201 C1 ReviewEvidence composition
```

## 3. Mandatory fresh archaeology

At the released base, inspect symbolically before designing API:

- `zero_relay.ResultIdentity`
- `zero_relay.ReviewEvidence`
- `claude_code_harness.TaskPacketFile`
- accepted `NativeFileSystem.create_text_if_absent`
- `HarnessDispatch`
- `SelectedAssignment`
- `WorkerLeaseCandidate` / canonical WorkerLease used by production route
- provider execution/admission authority used by the selected route
- `AgentMailboxAssignment`
- `ReviewMailboxResult`
- `ReviewMailboxResultReader`
- `ReviewResultForwarder`
- actual production callers of scheduler/dispatch/provider/lease composition

Re-run call-site searches. Do not trust this packet if source drift changed the architecture.

Important historical finding to verify fresh:

- mailbox assignment publisher had no production caller;
- review forwarder had no production caller;
- generic `domain.Agent` had no production construction and was not accepted as mailbox identity authority.

If these facts changed, record exact new evidence and adapt only within released scope.

## 4. C0a exact review task materializer

Implement a deterministic packet generated solely from exact `ResultIdentity` + fixed protocol text.

The task bytes must bind:

- author task_contract_ref
- author task_sha256
- author result_ref
- author result_sha256
- attempt_id
- generation
- author_execution_id
- fixed independent-review requirements
- fixed result schema expectations

No arbitrary caller review prompt may alter the packet outside an explicitly versioned bounded field.

Use a versioned domain separator such as `zra2-review-task-v1` and canonical serialization before hashing.

Prefer one digest that deterministically drives:

- review task contract ref
- review task path
- review result destination path

Paths must be fixed-parent/root-confined and never include raw author/user text.

Publication MUST reuse accepted `NativeFileSystem.create_text_if_absent()` semantics:

- exact same bytes => reuse
- divergent bytes => typed collision
- race same bytes => converge
- race different bytes => preserve other bytes and fail collision
- unknown/vanished state => fail closed

Do not reimplement temp-file/hard-link/no-clobber behavior in this module.

## 5. C0b route binding

After the exact review packet exists, consume existing route authorities.

Do not let the caller freely provide provider/model/worktree/branch/head/worker facts.

Cross-bind the exact review packet with trusted values from the released production composition, such as:

- HarnessDispatch
- SelectedAssignment
- Worker lease/candidate
- provider profile/admission/config generation

Required failures include:

- task-contract mismatch
- worker mismatch
- provider mismatch
- model mismatch
- worktree mismatch
- branch mismatch
- HEAD mismatch
- project mismatch
- expired/released/unknown lease where relevant
- provider generation/admission drift where relevant
- result destination mismatch
- stale current HEAD

Use fixed role `independent-review` if a role string is required. Do not use caller prose as authority.

## 6. Mailbox-agent rule

External mailbox publication is NOT automatically authorized.

At packet creation there was no proven production worker->mailbox-agent mapping.

If implementation requires `publish_agent_mailbox_assignment()` and no accepted mapping now exists, return:

`MAILBOX_AGENT_ID_AUTHORITY_MISSING`

and STOP for integrator scope decision.

Do not set agent_id to worker_id/provider/model/plugin label merely because convenient.

A direct programmatic ZCode review route should not publish a mailbox solely to fabricate authority.

For direct routing, an `AgentMailboxAssignment`-shaped binding may be constructed only if every authority-relevant field is derived from trusted route facts and `agent_id` is not used as filesystem route authority.

If existing adapter API makes that impossible without unsafe semantics, report a bounded design gap rather than broad-refactor the adapter.

## 7. RED-first campaign

Before implementation, write failing tests proving the missing C0 seam.

At minimum cover:

### Deterministic packet

- valid ResultIdentity -> deterministic exact packet
- same input repeated -> same ref/path/bytes/hash
- author task SHA change -> different identity
- author result SHA change -> different identity
- result ref change -> different identity
- attempt change -> different identity
- generation change -> different identity
- author execution ID change -> different identity
- raw path-like/prose input cannot escape root
- exact bytes returned by TaskPacketFile match disk

### Publication

- same persisted bytes reused without rewrite
- different persisted bytes typed collision
- barrier-driven concurrent same input converges
- deterministic injected divergent race preserves conflict
- mutation forbidden
- missing parent
- UTF-8 exact bytes/hash
- unsupported primitive fails closed

### Route binding

- exact positive route
- task contract mismatch
- worker mismatch
- provider mismatch
- model mismatch
- worktree mismatch
- branch mismatch
- head mismatch
- project mismatch
- stale lease / wrong mutation intent where applicable
- provider generation/admission mismatch where applicable
- review result destination mismatch
- current HEAD drift
- caller cannot override fixed role into authority
- no mailbox agent mapping => external publish blocked typed

### Anti replay

- review packet for author result A cannot bind author result B
- same head/provider/model but different result SHA cannot reuse
- stale attempt/generation cannot reuse
- old packet cannot authorize new candidate HEAD

### Authority fence

AST/import or direct review must prove the new module does not create:

- scheduler
- provider store
- lease store
- retry loop
- ReviewBus/ReviewBridge clone
- second filesystem implementation
- A-Wiki internal import

## 8. Implementation constraints

- Prefer a small new module + focused tests.
- Reuse existing typed dataclasses and validators.
- Use stable typed error codes.
- No live Worker/provider/credential/network mutation in tests.
- No sleeps for concurrency when barrier/fault injection can be deterministic.
- No hidden retry loop.
- No source changes outside explicit released scope.
- Do not weaken existing tests.
- Do not modify Phase-A relay decision semantics.
- Do not modify generic mailbox/forwarder semantics unless a deterministic RED proves the accepted C0 contract cannot be implemented without a narrow extension; checkpoint before expanding scope.

## 9. Verification ladder

After GREEN, run:

1. focused C0 tests
2. accepted Phase-B no-clobber filesystem tests
3. `tests/test_zero_relay.py`
4. `tests/test_agent_change_packets.py`
5. `tests/test_review_mailbox_adapter.py`
6. only scheduler/lease/provider tests justified by actual imports/call paths
7. compile/import
8. diagnostics
9. `git diff --check`
10. strict UTF-8 / no U+FFFD
11. exact changed-path + untracked audit
12. secret-like added-line audit
13. adversarial self-review with at least one novel counterexample beyond authored tests

When green:

- update released C0 work order truthfully
- write durable result/checkpoint
- commit only allowed scope
- push exact candidate
- open/update Draft PR
- STOP at hosted CI if non-terminal
- after CI success STOP at independent GPT/GLM review gate

Do not self-accept or self-merge.

## 10. Durable handback

Result must include:

- base SHA
- exact candidate SHA
- worktree/branch/claim
- changed paths
- RED evidence
- GREEN tests
- adversarial tests
- authority map actually reused
- whether mailbox publication was used
- if used, exact accepted source of mailbox agent_id authority
- findings P0/P1/P2/P3
- any `DESIGN_GAP_*`
- PR URL
- merge_performed=false
- next safe action

## 11. Long-run behavior

Work deeply inside C0 and execute every READY micro-step without asking the human to relay messages.

But stop at the first external gate:

- missing Phase-B acceptance
- missing C0 release
- ownership/scope conflict
- missing mailbox-agent authority when external mailbox is required
- need for unapproved source-scope expansion
- source drift
- non-terminal CI
- independent acceptance
- merge/post-main verification

Checkpoint before stopping. On the next invocation resume from durable C0 state; do not restart completed work.