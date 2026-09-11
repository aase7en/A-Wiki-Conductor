# WO-P1-165 — ZRA-2 automatic review + bounded repair loop

Status: PHASE-A P1 REPAIR FROZEN / INDEPENDENT REREVIEW REQUIRED (2026-09-11)
Parent: WO-P1-155 Zero-Relay Accelerator
Durable issue: GitHub Issue #214
Architecture claim: GPT1-ZRA2-PREFLIGHT-001
Implementation owner: bounded GLM5.3 MAX lane
Acceptance / merge authority: GPT1 integrator
Repository: A-Wiki-Conductor
Branch: feat/wo-p1-165-zra2-review-repair-loop-r2
Worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo165-zra2-r2
Baseline: main@f964afced5fbe0905c3667b1a6552a6fdafc09cb
Historical activation preserved: feat/wo-p1-165-zra2-review-repair-loop@3d7209e0683afc3d1c9daf4d8db75052220ec782

## Identity reconciliation

Historical ZRA-2 notes used WO-P1-159. That ID is now owned by
PR #222 loop-engineering adoption and MUST NOT be reused here.
WO-P1-165 is the canonical implementation identity for ZRA-2.
Issue #214 remains the architecture/preflight authority.

Historical activation evidence:
- ZRA-1 / PR #221 accepted + merged as the earlier test/transport milestone.
- A-Wiki #53 / PR #55 accepted + merged.
- A-Wiki #54 / PR #56 accepted + merged.
- A-Wiki #54 merge = 967e063cb9dc2e5b43b48a00deb575235f125a94.
- A-Wiki post-main Core CI 34133420008 = SUCCESS.

## 2026-09-11 current-main refresh checkpoint

Actual Git/GitHub/runtime evidence supersedes the older activation baseline and the stale
`CURRENT-WORK.md` projection for dependency decisions:

- current A-Conductor `origin/main` at refresh = `f964afced5fbe0905c3667b1a6552a6fdafc09cb`;
- the historical WO165 activation branch/worktree is preserved untouched at
  `feat/wo-p1-165-zra2-review-repair-loop@3d7209e0683afc3d1c9daf4d8db75052220ec782`;
- this refresh uses a fresh isolated worktree/branch from current main; no reset/rebase of the
  historical activation evidence is permitted;
- WO166/P0-B component work and the later cross-repo authority-dedup prevention work are present
  in current-main history; current source includes the accepted continuity guard/closeout
  authorities that WO165 must reuse rather than replace;
- WO179 `ZRA-1-LIVE-3` is ACCEPTED on current main after one real authorized
  `cointh-glm / GLM-5.3` turn with exact task-bound response, zero human relay, no orphan,
  released provider admission/WorkerLease, and same-identity `REUSE_COMPLETED` replay proof;
- independent GLM Wave-7 adjudication also returned `ZRA1_VERDICT=ACCEPT` and
  `ZERO_RELAY_REAL_PROVIDER_PROVEN=YES`;
- therefore the predecessor gate that held WO165 is satisfied. The next critical-path node is
  this existing WO165; do not create a duplicate ZRA-2 coordinator lane;
- `CURRENT-WORK.md` still reflects the older P0-B frontier and is a stale human projection at
  this checkpoint. It must not re-block a successor that actual Git/Issues have already proven
  ready; a later single-writer continuity fold remains separate work.

Implementation ownership remains the original contract: bounded GLM-5.3 MAX owns Phase-A
implementation; GPT-5.6 Sol owns architecture, conflict adjudication, exact-SHA acceptance, merge,
and release. This refresh itself does not transfer acceptance authority.

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

## Phase A evidence (GLM implementation lane, 2026-09-11)

- Lane: worktree `A-Wiki-Conductor-wo165-zra2-r2` @ branch `feat/wo-p1-165-zra2-review-repair-loop-r2`, base refresh `1dda36d6` (= PR #258 head at task start; TASK.md SHA256 verified `ef982d8e...`).
- RED first: full 38-case matrix written before implementation; captured `ModuleNotFoundError: No module named 'a_conductor.zero_relay'`.
- GREEN: focused `tests/test_zero_relay.py` **38 passed / 0 failed**; related `test_agent_change_packets` + `test_goal_closeout` **136 passed / 0 failed** (read-only reuse vocabulary: `TaskPacketFile` sha256 semantics, `AgentResultPacket` identity vocabulary).
- Adversarial matrix included: raw-string disposition, truthy spoof object, control-char identities, hash malformation (63-hex/non-hex/blank), generation (<class 'bool'>, -1, 2, 5, '0'), cross-binding mismatches (task/result/attempt/generation), author==reviewer independence, UNKNOWN/TIMEOUT/AMBIGUOUS -> RECOVERY_REQUIRED, FAILED -> REJECTED, verification-failure + review-ACCEPT contradiction, no-review fail-closed, exactly-one repair generation (0->1), second rejection -> REJECTED, determinism, no-IO import surface, exception-text non-echo. Positive controls: first-accept, repaired-accept, repair-transition.
- Checks: compileall OK; `git diff --check` OK; strict UTF-8/no-U+FFFD OK; secret scan of changed lines 0 hits (only deliberate non-credential test marker); changed tracked scope exactly the 3 allowed paths.
- Implementation: pure frozen dataclasses + enums; zero I/O imports; no clock; stable `ZeroRelayError(code)` vocabulary; `RelayOutcome(decision, next_repair_generation)` carries next generation exactly 1 only for REPAIR_REQUIRED.
- Module SHA256 `2c05f6605ebfda01…`; tests SHA256 `2175089eba4a9115…` (full digests in run evidence).
- STATUS=PHASE_A_FROZEN / INDEPENDENT_REVIEW_REQUIRED — GLM authored this candidate and is NOT its independent reviewer.

## Phase A P1 exact-digest repair evidence (GPT bounded author lane, 2026-09-11)

Independent exact-SHA review of candidate `5f95fe16e95c90faaa4a36686e286515e4641708` returned `CHANGES_REQUIRED` with P0=0 / P1=1 / P2=0 / P3=0: `ReviewEvidence` did not carry the exact task/result SHA-256 digests, so an accepted review for older bytes could be reused when refs/attempt/generation stayed unchanged.

Fresh repair gate re-pinned this worktree/branch at that exact PR head, `origin/main=f964afced5fbe0905c3667b1a6552a6fdafc09cb`, CLEAN, with no competing remote branch owning `src/a_conductor/zero_relay.py` or `tests/test_zero_relay.py`. The automatic ZCode app-server path was also re-audited and is read-only by design because permission requests are denied; GPT integrator therefore became the bounded repair author to avoid human relay. The repaired candidate must use a genuinely independent GLM/ZCode read-only exact-SHA rereview before acceptance/merge.

RED-first repair evidence:
- added exact contract-shape/hash-validation checks for `ReviewEvidence.task_sha256` + `ReviewEvidence.result_sha256`;
- added stale-review attacks where task digest or result digest changes while refs/attempt/generation remain identical;
- before repair: `5 failed, 38 passed`; both stale-digest attacks incorrectly produced no `REVIEW_IDENTITY_MISMATCH`.

GREEN repair:
- `ReviewEvidence` now requires and validates full task/result SHA-256 values using the existing hash validator;
- `classify_relay_decision()` cross-binds both digests before any decision;
- focused `tests/test_zero_relay.py`: `43 passed`;
- related `tests/test_agent_change_packets.py` + `tests/test_goal_closeout.py`: `136 passed`;
- all prior UNKNOWN=>RECOVERY_REQUIRED, reviewer independence, exactly-one-repair, pure/no-I/O, and typed-error semantics remain unchanged.

Final pre-freeze verification: combined focused+related matrix `179 passed`; compileall PASS; `git diff --check` PASS; strict UTF-8/no-U+FFFD PASS; added-line credential-assignment scan `0` hits; changed tracked scope exactly the three allowed paths; production source LSP diagnostics empty; repository Python consumer audit found no external `zero_relay` consumer beyond this focused test module. The exact new candidate SHA is recorded in the durable PR/Issue checkpoint after commit/push.

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

The implementation author does not self-review or self-merge.
Freeze one exact SHA after each material phase and checkpoint Issue #214.
Any P0/P1 finding => CHANGES_REQUIRED and one bounded repair packet.
No live provider proof is part of source acceptance.
PROOF/live external execution requires separate GPT1/human authorization.

Next safe implementation action:
complete final pre-freeze hygiene -> commit/push the repaired exact SHA -> release the repair mutation claim -> independent GLM/ZCode read-only exact-SHA rereview -> GPT acceptance/merge only if all R3 gates pass.
