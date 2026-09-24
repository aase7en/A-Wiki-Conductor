# WO-P1-529 — A-NightShift one-shot quota continuation

Issue: #529
Class: CONTROL_PLANE_ONLY
Risk: R3
Claim: WO-P1-529-NIGHTSHIFT-ONE-SHOT-MAC-001
Base: 1486e75484afa21a79810a7ebe0e92abb384c3b7
Worktree: /Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo529-nightshift-one-shot
Branch: fix/wo-p1-529-nightshift-one-shot

## Goal

Repair A-NightShift so one parent `/goal` can continue safely across ChatGPT turn loss and repeated roadmap transitions until either:
1. a fresh approved CoinTH preflight proves `QUOTA_EXHAUSTED`; or
2. a genuine frozen stop gate remains after all independent SAFE READY work is exhausted.

## Reproduced defects

Run `nightshift-WO-P1-526-20260924T070716Z-qq_o5o2q` proved:
- the parent survives ordinary chat/tool-turn loss and can merge/verify work;
- it falsely classified #495 as `HUMAN_DECISION_REQUIRED` even though #348 already accepted a local-only SRM compatibility anchor and explicitly stated that no SRM publication is implied;
- it terminated and cleaned up while quota remained available;
- integrator availability can be misclassified when default PATH omits the bundled Codex binary.

## Required semantics

- Accepted durable local-only execution-repo identity evidence may satisfy a local-only execution binding. It MUST NOT silently grant remote publication or cross-device authority.
- A blocker on one frontier item is not a terminal human gate while another dependency-unblocked SAFE READY item exists.
- `INTEGRATOR_ACTION_REQUIRED + route AVAILABLE => WAITING_INTEGRATOR`, never a manufactured human gate.
- Integrator route discovery must allow an exact configured `CODEX_BIN`/capability probe, not PATH alone.
- Parent lifecycle remains `RECOVER -> RECONCILE -> HARVEST -> REFILL -> WAIT`.
- `WAITING_EXTERNAL` uses blocking wait/no model spin only when no independent SAFE READY work exists.
- Fresh `QUOTA_EXHAUSTED` is a legitimate run terminal after children are harvested/checkpointed.
- No work may be manufactured merely to consume quota.
- Cleanup stays PRE/delete/POST under the existing durable authority.

## Allowed tracked scope

- `.agents/skills/a-nightshift/SKILL.md`
- `.agents/skills/a-nightshift/references/overnight-supervisor.md`
- `tests/test_a_nightshift_skill_contract.py`
- this WO

## Forbidden

A-Faster files/tests, `src/a_conductor/**`, CURRENT-WORK, handoff, COLLAB, SRM mutation, secrets, scheduler/task/claim/lease/review/completion authority, protected root dirt.

## Verification

- focused NightShift contract tests;
- adjacent A-Faster invocation/utilization tests;
- mutation probes for false-human-gate regressions;
- UTF-8, diff-check, secret scan, exact scope;
- independent R3 review on frozen exact SHA;
- exact-head CI;
- Sol exact-SHA acceptance and post-main verification.


## Implementation checkpoint — Sol takeover after Kilo transport stall

Initial GLM-5.3 MAX execution `exec-muf9ban1-6m70ucph` was launched through
Sunday durable execution with sharing disabled. The Kilo session/process
remained alive but produced zero durable output and no tracked mutation for
more than ten minutes; the same failure mode occurred concurrently on an
independent Flash probe and another MAX lane. It was classified as a common
Kilo/provider transport stall, cooperatively cancelled by exact execution id,
harvested and collected. No blind redispatch was performed.

Sol then applied the bounded repair inside this WO's exact scope:
- local-only accepted execution-repo evidence is `LOCAL_ONLY_CANONICAL` for
  local-only work and does not imply remote/cross-device publication authority;
- a blocked frontier item is not parent-terminal while another SAFE READY item
  exists;
- fresh quota exhaustion after child reconciliation is the quota terminal;
- a verified exact `CODEX_BIN` capability can establish integrator
  availability even when PATH lookup fails;
- Codex turn completion is separated from durable Goal completion:
  nonterminal turn boundary => `TURN_RECEIPT_STATUS=CONTINUE`,
  `GOAL_TERMINAL=NO`, `CLEANUP_ALLOWED=NO`.

Verification: NightShift + adjacent A-Faster contract suite 113/113 PASS;
git diff --check PASS. Independent R3 review and hosted CI remain required
before acceptance.

## Independent R3 repair checkpoint — 2026-09-24

Independent exact-SHA review of 1e4cd0a3575577bc572b132c447690f29f9b8fd0
returned CHANGES_REQUIRED / P0=0 P1=1 P2=1 P3=0.

Accepted repairs:
- local-only compatibility/provenance evidence is no longer treated as mutation
  admission; EXECUTION_REPO_COMPATIBILITY=LOCAL_ONLY_CANONICAL remains
  observational until the exact lane proves its claim/lease/guard mutation
  admission, while remote absence alone does not manufacture a human gate;
- the SAFE_READY frontier vector now proves only GOAL_TERMINAL=NO; NightShift
  consumes AUTO_REFILL_REQUIRED from accepted A-Faster truth verbatim and
  never derives TRUE from SAFE_READY alone. Quota/route/WIP gates may keep the
  marker FALSE or UNKNOWN.

Operator decision B separately established canonical private SRM remote identity
at aase7en/SunDayRemoteMCP with remote/local main pinned to
2f033cfb1f61b6dff9c2e55264cca6f2a9125e95; that publication decision does not
retroactively turn historical compatibility evidence into mutation admission.

The repaired candidate requires a new exact SHA, focused deterministic
verification, fresh independent R3 review, and exact-head hosted CI before merge.

## Independent R3 mutation-probe repair — 2026-09-24

Rereview of 7ae2eb1db15ec9a46302c2f54dadf4c4c7a86161 closed prior F1/P1
and F2/P2 but found one new P2 test-assurance gap: the WO529 assertions did
not reject an injected contradictory
REMOTE_CONFIGURED=NO => HUMAN_DECISION_REQUIRED rule.

The repair adds a structural no-false-human-gate validator and an adversarial
mutation probe over all three copies: SKILL, canonical reference, and embedded
supervisor template. The injected contradiction must fail the validator in
every copy. No production/contract semantics change in this slice.

A new exact SHA, deterministic verification, fresh exact-SHA independent R3
review, and exact-head hosted CI remain required before merge.
