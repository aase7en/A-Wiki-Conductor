# WO-P1-220 — independent review of WO219 Phase-C0 provenance repair

Status: PREPARED / WAIT FOR PR #299 TERMINAL CI
Parent: WO219 / PR #299
Parent of parent: WO216 / PR #296
Review target: `5f779dda10c70d20cfbbeb8925ed3e42c000ecee`
Independent finding source: WO218 `c5b04305154e229e3fd42d2092844ded6234a2ff`
Preferred reviewer: ZCode GLM-5.3, independent of GPT repair author
Risk: R3 identity / persisted provenance / anti-replay

## Objective

Attempt to falsify the repaired Phase-C0 provenance chain before integrator acceptance. This is a review lane only. Do not edit candidate source/tests and do not merge or release C1.

## Release gate

Before review execution, re-pin:

- PR #299 head is exactly `5f779dda10c70d20cfbbeb8925ed3e42c000ecee`;
- PR #299 hosted CI is terminal green on that exact head;
- parent PR #296 remains exact `ade1628247a4512fa879c10bfd093d14f51d487f` and unmerged as a standalone defective candidate;
- WO218 review evidence exists and still maps to the parent defects;
- no source drift or owner conflict changes the candidate;
- reviewer lane is read-only against source/tests.

If CI is non-terminal/failing or source drift exists, checkpoint and STOP. Do not poll.

## Mandatory attack matrix

Reproduce all four WO218 attacks independently:

1. fake successful write-result object with wrong path/size/hash;
2. forged caller-constructed `MaterializedReviewTask`;
3. packet path under a foreign worktree with matching suffix/hash/contract;
4. old review packet / new internally-consistent route HEAD replay.

All four must be refused by stable typed failures after repair.

Then attempt novel counterexamples around:

- post-create disappeared/divergent bytes;
- same path/same bytes idempotent reuse;
- same path/different bytes collision preservation;
- reviewed HEAD uppercase/lowercase canonicalization and malformed HEADs;
- 7-char and 64-char accepted HEAD boundaries;
- filesystem root mismatch;
- packet path normalization (`.`, `..`, slash direction, case on Windows semantics);
- task packet hash/ref mismatch;
- result destination mismatch;
- author identity drift while HEAD is fixed;
- HEAD drift while author identity is fixed;
- author/reviewer execution-id alias;
- READ_ONLY vs PROJECT_MUTATION;
- `ParallelReadyTask` worker/provider/project/worktree/branch/head cross-fences;
- caller object mutation/forgery through `dataclasses.replace`;
- missing/vanished persisted file before C0b;
- TOCTOU-shaped changes between materialization and route binding;
- symlink/root-confinement behavior through real `NativeFileSystem` where safe and temp-only;
- UTF-8 exact byte/hash behavior.

## Test-vacuity requirements

Do not merely rerun candidate tests. At least one novel independent probe must:

- fail against parent `ade1628...`, or otherwise demonstrate that it discriminates old vs repaired semantics;
- pass/refuse correctly on repaired `5f779dd...`;
- record exact inputs and observed typed result.

Inspect candidate tests for monkeypatch/fake assumptions that bypass real path/root semantics. Use real `NativeFileSystem` temp roots for at least one positive and one negative path when practical.

## Regression floor

After adversarial review run at least:

- `tests/test_zero_relay_review_task.py`;
- `tests/test_native_execution.py`;
- `tests/test_zero_relay_repair_materializer.py`;
- `tests/test_zero_relay.py`;
- `tests/test_claude_code_harness.py`;
- `tests/test_parallel_ready_execution.py`;
- `tests/test_agent_change_packets.py`;
- `tests/test_review_mailbox_adapter.py`;
- any additional route/harness test justified by a novel finding.

Also run compile/static/diff/UTF-8/scope checks on the frozen candidate without modifying it.

## Writable review evidence

Only review-lane evidence is writable:

- `docs/reviews/WO-P1-220-zra2-c0-repair-review.md`
- `runs/WO-P1-220/**` if ignored/authorized by repository convention
- append-only checkpoint to this WO if needed

Candidate source/tests are immutable.

## Verdict

Return exactly one:

- `PASS`
- `CHANGES_REQUIRED`
- `BLOCKED`
- `SOURCE_DRIFT`

Report exact candidate SHA, PR, CI state, P0/P1/P2/P3 counts, novel probes, regression evidence, and `merge_performed=false`.

If PASS: checkpoint `BLOCKED_EXTERNAL_GPT_ACCEPTANCE` and STOP.
If CHANGES_REQUIRED: checkpoint `BLOCKED_EXTERNAL_GPT_REPAIR_AUTHORITY` and STOP.

Never self-merge, never release C1, never switch to unrelated backlog to stay busy.
