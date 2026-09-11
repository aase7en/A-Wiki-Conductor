# MASTER /goal — WO-P1-203 ZRA-2 Phase-B no-clobber publication repair

Use only after GPT/integrator explicitly releases WO203 from HOLD.

## Primary pointer

Read first and treat as the durable task contract:

`docs/work-orders/WO-P1-203-zra2-phase-b-no-clobber-publication.md`

Parent authority:

- WO-P1-165 / Issue #214
- WO-P1-195 Phase-B materializer candidate, exact SHA supplied by GPT at release time

## Goal

Repair the proven Phase-B collision/TOCTOU defect without creating a second filesystem authority.

The accepted architecture is:

1. extend the existing `NativeFileSystem` with one narrow atomic no-clobber text-publication primitive;
2. use that primitive from the repair materializer;
3. reconcile already-exists through exact re-read;
4. same bytes => reuse;
5. different bytes => stable `REPAIR_TASK_COLLISION`;
6. never overwrite another actor's artifact;
7. no retry loop, no scheduler/reviewer/provider/lease changes.

## Startup

Before mutation:

1. read `00-AGENT-ENTRY.md`, routed repo rules, local `AGENTS.md`/`AGENT.md`, and `DEFECT_LESSONS.md`;
2. read WO203 fully;
3. read parent WO195 + Issue #214 latest checkpoint;
4. re-pin repo/remote/worktree/branch/HEAD/origin-main/dirty state;
5. verify the exact released Phase-B parent candidate SHA;
6. inspect open PRs/worktrees/process ownership for overlap on:
   - `src/a_conductor/native_execution.py`
   - `src/a_conductor/zero_relay_repair_materializer.py`
   - `tests/test_native_execution.py`
   - `tests/test_zero_relay_repair_materializer.py`
7. verify GPT has changed `SAFE_TO_MUTATE_WO203` to YES in durable authority.

If any material fact is unknown/conflicting, write checkpoint and STOP. Do not guess.

## Required work style

You are the bounded implementation labor lane, not acceptance authority.

Work RED-first and continue autonomously through every READY micro-step in this one lane.

Do not ask the human to carry evidence between tools. Use Git/GitHub/durable files directly.

Do not self-accept, self-merge, mutate live runtime/provider credentials, or switch to unrelated backlog work when blocked.

## RED program

First reproduce the exact defect deterministically.

Required initial RED:

- materializer pre-read observes deterministic path absent;
- before final publication, inject a different-byte file at that exact target;
- current behavior overwrites it and returns success;
- record the RED result before production repair.

Then add native filesystem REDs for atomic no-clobber behavior, including concurrent creators.

Do not use SHA collision tricks. The conflict is an external artifact at the same final path between observation and publication.

Prefer barriers/hooks to sleeps.

## Implementation constraints

### NativeFileSystem

Add a narrow additive primitive. Do not silently change existing `write_text()` semantics unless exhaustive archaeology proves it safe and GPT explicitly approves.

The primitive must:

- remain confined by `NativeExecutionScope`;
- require mutation authority;
- enforce existing size/UTF-8 rules;
- never overwrite an existing final target;
- report target-already-exists through stable typed evidence/error;
- work correctly on Windows and hosted Linux/macOS;
- never degrade to clobbering behavior on unsupported filesystems;
- clean temporary files best-effort without touching another actor's target.

Choose the actual OS primitive only after proving semantics on supported platforms. Do not assume POSIX rename behavior equals Windows behavior.

### Materializer

Use only the existing filesystem authority plus the new narrow primitive.

On already-exists:

- read exact target through `NativeFileSystem`;
- matching bytes/hash/path => reuse;
- divergent bytes/hash => `REPAIR_TASK_COLLISION`;
- disappearance/unknown state => typed verification/recovery failure;
- no blind retry.

Do not use raw `Path.open`, `os.open`, `os.replace`, or direct root-path mutation from the materializer as a shortcut around NativeFileSystem.

## Tests

Minimum required:

- target absent success;
- existing same bytes no overwrite;
- existing different bytes no overwrite;
- injected create between observation and publish preserves conflict;
- concurrent same-path creators: at most one physical publication winner;
- loser reconciles safely;
- mutation disabled;
- parent missing;
- non-file target;
- file too large;
- UTF-8 byte/hash identity;
- materializer same-input replay;
- materializer collision;
- materializer TOCTOU collision;
- no second repair generation;
- no second authority import surface;
- no retry loop;
- returned TaskPacketFile hash equals persisted bytes.

Run positive controls beside negative cases.

## Verification ladder

Run progressively:

1. focused new/changed tests;
2. `tests/test_native_execution.py`;
3. `tests/test_zero_relay_repair_materializer.py`;
4. related agent-change/task-packet tests;
5. justified native execution regressions;
6. compile/import;
7. diagnostics;
8. `git diff --check`;
9. UTF-8/U+FFFD scan;
10. secret-like added-line scan;
11. exact scope audit.

Do not weaken existing tests.

## Freeze / handback

When implementation and local verification are complete:

1. update WO203 checkpoint/result with exact commands/outcomes;
2. write `runs/WO-P1-203/result.md` and machine-readable result/checkpoint if repo pattern requires;
3. commit only authorized paths;
4. push the exact branch;
5. create/update Draft PR;
6. record exact candidate SHA;
7. re-pin clean worktree + remote SHA;
8. STOP at hosted CI / GPT independent acceptance gate.

Do not poll CI in a loop.

## Resume behavior

If invoked again:

- read durable checkpoint/result first;
- re-pin actual state;
- continue only unfinished READY steps;
- never restart completed experiments without drift/evidence reason.

## Mandatory stop gates

STOP immediately after checkpoint if any of these appears:

- GPT release absent;
- parent candidate changed unexpectedly;
- another owner overlaps mutable scope;
- source contract requires scope outside WO203;
- no-clobber semantics cannot be proven on a supported platform;
- CI non-terminal;
- independent review required;
- merge/post-merge acceptance required;
- authorization/provider/runtime external dependency appears.

At a stop gate, report exact blocker, branch/SHA/PR, completed evidence, and next safe action. Then stop.