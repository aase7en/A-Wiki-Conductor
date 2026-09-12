/goal

Execute independent exact-SHA adversarial review WO-P1-220 only.

PRIMARY WORK ORDER:
A:\GitHub\_worktrees\A-Wiki-Conductor-wo220-zra2-c0-rereview\docs\work-orders\WO-P1-220-zra2-c0-repair-independent-review.md

REVIEW TARGET:
- PR #299
- exact SHA `a2cb571d33e528840f47660d98fcdec80cad889b`
- parent exact SHA `ade1628247a4512fa879c10bfd093d14f51d487f` / PR #296
- WO218 independent rejection evidence `063e8afe93db1b0468951e61472ec711d436fdba`

ROLE:
You are ZCode GLM-5.3 acting as an independent R3 reviewer of GPT-authored WO219 repair. You are NOT the implementation author of the repair. Candidate source/tests are immutable during this invocation.

LONG-SHIFT CONTRACT:
Use the full useful work budget. Do not optimize for chat/context length. Keep durable rolling notes/checkpoints/evidence under WO220 so later context compression or a later invocation can resume without restarting. Read checkpoint first on every resumed invocation.

STARTUP / GATE:
1. Read current repository entry/governance routing, AGENTS.md and DEFECT_LESSONS.md as required.
2. Re-pin repo/worktree/branch/current origin/main/PR #299 exact head/base/CI.
3. Verify PR #299 head is exactly `a2cb571d33e528840f47660d98fcdec80cad889b`.
4. Verify hosted CI is terminal green for that exact head.
5. Verify parent #296 is exact `ade1628247a4512fa879c10bfd093d14f51d487f` and WO218 evidence still maps to it.
6. Verify review source/test paths are read-only and no ownership conflict exists.

If CI is non-terminal/failing, SHA drift exists, or authority is unknown: write durable checkpoint and STOP. Do not poll/wait and do not jump to other work.

Overlap decision: PR #298 / `41ba9f5ede1827af7a24d5a6be0835a287d4c591` is a partial predecessor, fails full Windows CI with a path-construction SyntaxError, and is `SUPERSEDED_DO_NOT_MERGE`. Do not review, repair, or merge #298 in this lane. The only review target is PR #299 exact `a2cb571d33e528840f47660d98fcdec80cad889b`.

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
E. duck-typed/non-NativeFileSystem object presented as persistence authority to either C0a or C0b.

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
- `dispatch_gate.allowed=False` presented as a supposedly selected/authorized review route;
- `dispatch.model_id` absent from `provider_profile.models`, unsupported harness strategy, unsupported effort, and provider readiness/admission/generation drift — determine explicitly whether C0 is allowed to delegate each fact downstream or whether minting `DirectReviewRoute` would violate WO210 trusted-route semantics;
- direct-review result contract: `HarnessDispatch.evidence_destination_ref` is currently metadata-only; ZCode durable `result.json` contains process-exit metadata, while the exact reviewer response is in `stdout.log` and is hash-bound by `report.json`. Prove the C0 task defines enough fixed machine-readable output schema/provenance for C1 to validate the review without inventing a new payload contract. If not, return `CHANGES_REQUIRED` with a bounded `DIRECT_REVIEW_RESULT_CONTRACT_MISSING`-class finding;
- forged dataclass objects using dataclasses.replace;
- missing persisted bytes before bind;
- TOCTOU-style persisted change between C0a and C0b;
- exact UTF-8/Thai/emoji bytes and digest behavior;
- unsupported filesystem primitive/error paths fail closed;
- no duplicate filesystem/scheduler/provider/lease/review lifecycle introduced.

TEST VACUITY:
Do not simply rerun candidate tests. Create at least one novel independent counterexample/probe. Prefer deterministic fault injection, barriers, controlled temp directories and state transitions over sleeps. Where useful, run a probe against parent `ade1628...` to prove it catches old behavior, then against repair `a2cb571...`.

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
