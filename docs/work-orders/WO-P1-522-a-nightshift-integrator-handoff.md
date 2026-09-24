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
