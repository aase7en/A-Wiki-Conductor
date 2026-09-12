/goal

Execute independent exact-SHA adversarial review WO-P1-220 only.

PRIMARY WORK ORDER:
A:\GitHub\_worktrees\A-Wiki-Conductor-wo220-zra2-c0-rereview\docs\work-orders\WO-P1-220-zra2-c0-repair-independent-review.md

REVIEW TARGET:
- PR #299
- exact SHA `5f779dda10c70d20cfbbeb8925ed3e42c000ecee`
- parent exact SHA `ade1628247a4512fa879c10bfd093d14f51d487f` / PR #296
- WO218 independent rejection evidence `c5b04305154e229e3fd42d2092844ded6234a2ff`

ROLE:
You are ZCode GLM-5.3 acting as an independent R3 reviewer of GPT-authored WO219 repair. You are NOT the implementation author of the repair. Candidate source/tests are immutable during this invocation.

LONG-SHIFT CONTRACT:
Use the full useful work budget. Do not optimize for chat/context length. Keep durable rolling notes/checkpoints/evidence under WO220 so later context compression or a later invocation can resume without restarting. Read checkpoint first on every resumed invocation.

STARTUP / GATE:
1. Read current repository entry/governance routing, AGENTS.md and DEFECT_LESSONS.md as required.
2. Re-pin repo/worktree/branch/current origin/main/PR #299 exact head/base/CI.
3. Verify PR #299 head is exactly `5f779dda10c70d20cfbbeb8925ed3e42c000ecee`.
4. Verify hosted CI is terminal green for that exact head.
5. Verify parent #296 is exact `ade1628247a4512fa879c10bfd093d14f51d487f` and WO218 evidence still maps to it.
6. Verify review source/test paths are read-only and no ownership conflict exists.

If CI is non-terminal/failing, SHA drift exists, or authority is unknown: write durable checkpoint and STOP. Do not poll/wait and do not jump to other work.

MISSION:
Try to falsify the entire repaired provenance chain:

(ResultIdentity + exact reviewed HEAD)
 -> canonical review identity
 -> deterministic refs/markdown bytes/hash
 -> collision-safe NativeFileSystem persistence
 -> verified post-write reread
 -> exact selected review worktree/path
 -> second persisted-byte verification at C0b
 -> DirectReviewRoute

MANDATORY REPLAY OF WO218 BLOCKERS:
A. successful create returning fabricated wrong path/size/hash;
B. caller-forged MaterializedReviewTask/persisted SHA;
C. task packet in foreign worktree with matching suffix/hash/contract;
D. old packet rebound to a new internally-consistent route HEAD.

All must now fail closed with appropriate typed outcomes.

ADVERSARIAL CAMPAIGN:
- persisted file vanishes after create;
- persisted file diverges after create;
- same identity/same HEAD deterministic bytes/refs;
- different HEAD changes contract/task/result identity;
- invalid HEAD and 7/40/64-char boundary forms;
- mixed-case hexadecimal HEAD canonicalization;
- author ResultIdentity field-by-field replay matrix;
- filesystem root vs selected worktree mismatch;
- exact path vs suffix-only path, dot segments, parent segments, slash direction and Windows case semantics;
- symlink/junction/root escape with temp-only real NativeFileSystem where supported;
- packet hash/ref mismatch;
- result destination mismatch;
- author/reviewer execution alias;
- READ_ONLY/mutation mismatch;
- worker/provider/model/project/worktree/branch/head authority mismatch through ParallelReadyTask;
- forged dataclass objects using dataclasses.replace;
- missing persisted bytes before bind;
- TOCTOU-style persisted change between C0a and C0b;
- exact UTF-8/Thai/emoji bytes and digest behavior;
- unsupported filesystem primitive/error paths fail closed;
- no duplicate filesystem/scheduler/provider/lease/review lifecycle introduced.

TEST VACUITY:
Do not simply rerun candidate tests. Create at least one novel independent counterexample/probe. Prefer deterministic fault injection, barriers, controlled temp directories and state transitions over sleeps. Where useful, run a probe against parent `ade1628...` to prove it catches old behavior, then against repair `5f779dd...`.

Use real NativeFileSystem temp roots for at least one positive and one negative root/path verification when practical. Do not touch live Worker/provider/credential/runtime state.

REGRESSION:
Run the exact WO220 floor after adversarial probes. Expand only when a hypothesis justifies it. Compile/static/diff/UTF-8/scope checks must be recorded.

WRITE SCOPE:
You may write only review evidence/checkpoint files authorized by WO220. Do NOT edit candidate source/tests, parent branches, C1, Phase D, A-Wiki, scheduler/provider/lease/mailbox code, live runtime, credentials or secrets.

VERDICT:
Return exactly one of PASS / CHANGES_REQUIRED / BLOCKED / SOURCE_DRIFT.
Record:
- exact target SHA/PR/base;
- exact CI state;
- P0/P1/P2/P3 counts;
- reproduced WO218 attacks;
- novel probes and whether they are discriminating/non-vacuous;
- regression/static evidence;
- exact next safe action;
- `merge_performed=false`.

If PASS:
checkpoint `BLOCKED_EXTERNAL_GPT_ACCEPTANCE` and STOP.

If CHANGES_REQUIRED:
checkpoint `BLOCKED_EXTERNAL_GPT_REPAIR_AUTHORITY` and STOP.

At the FIRST external gate, finish only the current atomic safe step, persist durable state, and STOP. Never poll/wait at gates. Never self-accept, self-merge, release C1, or switch to unrelated backlog.
