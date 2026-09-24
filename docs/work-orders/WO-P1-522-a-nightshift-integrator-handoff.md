# WO-P1-522 — A-NightShift Sol integrator handoff and stale terminal-pointer guard

Status: ACTIVE / RED-FIRST
Issue: #522
Topology: CONTROL_PLANE_ONLY
Risk: R3 coordination / protocol authority
Claim: WO-P1-522-NIGHTSHIFT-HANDOFF-MAC-001
Repo: A-Wiki-Conductor
Worktree: /Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo522-a-nightshift-handoff
Branch: fix/wo-p1-522-a-nightshift-handoff
Exact base: 7672d704bdd51d58b45eb34b42629c8bb0a83565

## Goal

Repair the real post-#520 NightShift terminal/handoff failure without creating a
second scheduler, task database, claim/lease system, review authority, completion
authority, or durable state store.

Observed production sequence:
1. NightShift recovered #517 and PR #519 correctly.
2. A Sol acceptance boundary was collapsed directly into HUMAN_ACTION_REQUIRED.
3. The run directory was then cleaned up by exact path.
4. The same /goal auto-continuation later re-entered using the deleted contract.
5. CONTRACT_ABSENT was repeatedly reported as SAFETY_BLOCK.

## Failure model

### F1 — integrator requirement collapsed into human action

INTEGRATOR_ACTION_REQUIRED is not itself a stop gate. First classify the actual
integrator route as AVAILABLE, UNAVAILABLE, or UNKNOWN.

- AVAILABLE: route/handoff through the existing accepted authority; classify
  WAITING_INTEGRATOR, GOAL_TERMINAL=NO, CLEANUP_ALLOWED=NO,
  HUMAN_ACTION_REQUIRED=FALSE.
- UNKNOWN: recover/probe the route; do not invent HUMAN_ACTION_REQUIRED.
- PROVEN_UNAVAILABLE and a human must actually invoke the integrator:
  HUMAN_ACTION_REQUIRED is allowed.

No model/provider name grants authority; GPT-5.6 Sol remains the accepted
integrator/acceptance authority.

### F2 — ephemeral cleanup erased the only local receipt

The ephemeral receipt may be deleted with its run directory. Before any terminal
cleanup, fold a compact final run record into an existing durable task authority
(Issue / accepted WO checkpoint / existing durable checkpoint): run id, terminal
classification, evidence pointer(s), exact next safe action, and cleanup intent.
This is continuity folding, not a new status store.

### F3 — expected post-cleanup absence misclassified as safety incident

A later /goal entry that finds CONTRACT_ABSENT must first recover durable
closeout by exact run id.

- Exact durable terminal+cleanup proof => STALE_TERMINAL_POINTER /
  GOAL_ALREADY_TERMINAL. No SAFETY_BLOCK, no rematerialization, no redispatch,
  no repeated user-visible reply, no new authority.
- No matching durable terminal proof => CONTRACT_ABSENT_UNKNOWN may fail closed
  as SAFETY_BLOCK.

## Frozen mutation scope

Only:
1. .agents/skills/a-nightshift/SKILL.md
2. .agents/skills/a-nightshift/references/overnight-supervisor.md
3. tests/test_a_nightshift_skill_contract.py
4. docs/work-orders/WO-P1-522-a-nightshift-integrator-handoff.md

Forbidden:
- .agents/skills/a-faster/**
- DEFECT_LESSONS.md
- #517 guard/tests/roadmap/WO
- #498 paths
- src/a_conductor/**
- CURRENT-WORK.md / handoff.md / COLLAB.md
- scheduler/task/claim/lease/provider/review/merge/completion authority
- secrets
- destructive Git
- broad process termination

## Required RED regressions

Pin semantically:
1. INTEGRATOR_ACTION_REQUIRED requires route classification first.
2. AVAILABLE => WAITING_INTEGRATOR + non-terminal + no cleanup + no human gate.
3. UNKNOWN => recover/probe, not invented human gate.
4. PROVEN_UNAVAILABLE may derive HUMAN_ACTION_REQUIRED only when human invocation
   is actually necessary.
5. terminal cleanup requires durable fold into existing authority first.
6. ephemeral receipt alone is explicitly insufficient durable closeout.
7. CONTRACT_ABSENT entry performs run-id durable recovery before classification.
8. proven terminal cleanup => STALE_TERMINAL_POINTER / GOAL_ALREADY_TERMINAL,
   SAFETY_BLOCK=FALSE, REMATERIALIZE=FORBIDDEN, REDISPATCH=FORBIDDEN,
   USER_VISIBLE_REPEAT_REPLY=FORBIDDEN.
9. unproven contract absence remains fail-closed CONTRACT_ABSENT_UNKNOWN /
   SAFETY_BLOCK.
10. existing WAITING_EXTERNAL / WAIT_TOOL_TIMEOUT_RECHECK / no-model-spin
    semantics remain unchanged.

## Verification

- prove RED on new regression tests before production contract edits;
- existing NightShift contract tests remain green after repair;
- A-Faster invocation contract remains green;
- git diff --check;
- strict UTF-8;
- added-content secret scan;
- exact frozen scope check;
- freeze exact candidate SHA;
- independent GLM-5.3 MAX R3 review on frozen SHA;
- exact-head hosted CI;
- GPT-5.6 Sol expected-head acceptance/merge;
- post-main verification.

## Ownership / replay

Owner: GPT-5.6 Sol integrator; bounded implementation may be delegated to
GLM-5.3 MAX after fresh CoinTH quota/readiness proof.

Replay safety: no blind redispatch. Existing #517 dirty candidate and #498 scope
are separate owners and must remain untouched.

## Stop conditions

Only a real HUMAN_DECISION_REQUIRED / HUMAN_ACTION_REQUIRED /
AUTHORIZATION_REQUIRED / SAFETY_BLOCK / TRUE_NO_SAFE_NEXT_ACTION or material
ownership ambiguity. An integrator requirement with an available or unknown
route is not automatically terminal.

## Checkpoint — attempt-0001 (author lane, 2026-09-24)

- Executor: Kilo / GLM-5.3 under claim `WO-P1-522-NIGHTSHIFT-HANDOFF-MAC-001`,
  in the exact pinned worktree/branch at base HEAD
  `f6cf976cd2ad9f76f63b5fb00644bde569983d69`; pwd/branch/HEAD and initial
  clean `git status --porcelain` proven before mutation.
- RED proof: 11 new WO-P1-522 semantic regressions added to
  `tests/test_a_nightshift_skill_contract.py` (F1 route-classification pins,
  F2 durable-fold pins, F3 stale-pointer pins, incident-522 vector, and one
  unchanged-wait-semantics control) failed on the unrepaired contract
  (focused run: 11 failed / 44 passed) before any SKILL/reference edit.
- Repair implemented: `INTEGRATOR_ACTION_REQUIRED` route classification
  (AVAILABLE/UNKNOWN/PROVEN_UNAVAILABLE), durable final-run-record fold into
  existing task authority before terminal cleanup with explicit
  ephemeral-receipt insufficiency, and CONTRACT_ABSENT run-id durable
  recovery with STALE_TERMINAL_POINTER / GOAL_ALREADY_TERMINAL outcome
  vector — added to `.agents/skills/a-nightshift/SKILL.md` (new sections +
  cleanup/stop-gate clarification) and
  `.agents/skills/a-nightshift/references/overnight-supervisor.md`
  (canonical sections + incident regression + in-template contract body).
- Verification: focused NightShift contract tests 55/55 PASS;
  A-Faster control `tests/test_a_faster_invocation_contract.py` 11/11 PASS;
  `git diff --check` clean; strict UTF-8 decode of all four mutated files
  PASS; added-content secret scan 0 hits; scope check = exactly the four
  frozen paths, no forbidden path touched.
- Stop state: `READY_FOR_INTEGRATOR_VERIFICATION`. No commit, no merge, no
  push; GPT-5.6 Sol owns frozen-SHA review, acceptance, and merge. Compact
  evidence: `runs/WO-P1-522/author/attempt-0001/result.md`.

## Sol CHANGES_REQUIRED addition — attempt-0002 repair requirement

Sol integrator finding (Issue #522, 2026-09-24): attempt-0001 requires a
durable PRE-cleanup fold carrying cleanup intent, but no POST-delete
durable confirmation; intent alone cannot prove that exact-path deletion
actually completed, so a later CONTRACT_ABSENT cannot deterministically
distinguish expected completed cleanup from unexpected loss. Required
bounded repair, same frozen scope:

1. Two-phase closeout: `PRE_CLEANUP_FOLDED` before deletion; exact-path
   delete; `POST_CLEANUP_CONFIRMED` in the SAME existing durable authority
   after successful deletion.
2. `POST_CLEANUP_CONFIRMED` records at minimum run id + exact deleted
   path + terminal classification + cleanup result; no secret/log dump.
3. `STALE_TERMINAL_POINTER` / `GOAL_ALREADY_TERMINAL` requires
   `POST_CLEANUP_CONFIRMED`; cleanup intent alone is insufficient.
4. Delete failure / missing post-confirmation remains
   fail-closed/recoverable, never fabricated success.
5. No new store/authority; reuse Issue/WO/existing checkpoint.
6. Preserve all attempt-0001 F1/F2/F3 + WAITING_EXTERNAL/no-model-spin
   semantics.

## Checkpoint — attempt-0002 (author lane, 2026-09-24)

- Executor: Kilo / GLM-5.3 under claim `WO-P1-522-NIGHTSHIFT-HANDOFF-MAC-001`,
  resumed in the exact pinned worktree/branch at unchanged HEAD
  `f6cf976cd2ad9f76f63b5fb00644bde569983d69`; attempt-0001 dirty candidate
  preserved (no reset/clean/stash/discard); initial dirty patch SHA256
  `f5164889d5a0b5624413376ec24854ebc33937c0a2cbe19520789a87657d9c33` over
  exactly the four frozen WO paths, proven before mutation.
- RED proof: 6 new attempt-0002 semantic regressions (two-phase ordering,
  POST field set, stale-pointer requires POST_CONFIRMED, delete-failure
  fail-closed, same-authority reuse, incident vector) failed on the
  unrepaired attempt-0001 contract (focused run: 6 failed / 56 passed,
  the 56 including the new preservation control) before any
  SKILL/reference edit.
- Repair implemented: two-phase durable closeout
  (`PRE_CLEANUP_FOLDED` -> exact-path deletion -> `POST_CLEANUP_CONFIRMED`
  in the SAME existing durable authority), POST confirmation field set
  (run id, exact deleted path, terminal classification, cleanup result;
  no secrets, no log dumps), stale-pointer proof upgraded to require
  `POST_CLEANUP_CONFIRMED` with cleanup-intent insufficiency explicit,
  and delete-failure/missing-post-confirmation fail-closed/recoverable
  semantics — added to `.agents/skills/a-nightshift/SKILL.md` (cleanup +
  stale-pointer sections), `.agents/skills/a-nightshift/references/overnight-supervisor.md`
  (canonical stale-pointer + cleanup rules, incident-regression two-phase
  pin, in-template `## Cleanup` and `## Stale terminal-pointer` bodies),
  and `tests/test_a_nightshift_skill_contract.py` (docstring + 7 new
  tests: 6 RED regressions + 1 preservation control).
- Verification: focused NightShift contract tests 62/62 PASS; A-Faster
  control `tests/test_a_faster_invocation_contract.py` 11/11 PASS;
  `git diff --check` clean; strict UTF-8 decode of all four mutated files
  PASS; added-content secret scan 0 hits (single value-pattern match is
  the documented public HEAD SHA, not a credential); scope check = exactly
  the four frozen paths, no forbidden path touched.
- Stop state: `READY_FOR_INTEGRATOR_VERIFICATION`. No commit, no merge, no
  push; GPT-5.6 Sol owns frozen-SHA review, acceptance, and merge. Compact
  evidence: `runs/WO-P1-522/author/attempt-0002/result.md`.
