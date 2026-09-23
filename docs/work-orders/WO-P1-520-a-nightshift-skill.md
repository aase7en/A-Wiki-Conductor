# WO-P1-520 — A-NightShift overnight-supervisor skill

Status: ACTIVE / AUTHORING — attempt-0002 bounded semantic-alignment
repair (successor to attempt-0001, RED-first)
Issue: #520
Topology: CONTROL_PLANE_ONLY
Risk: R3 coordination policy
Claim: WO-P1-520-NIGHTSHIFT-MAC-001
Repo: A-Wiki-Conductor
Worktree: /Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo520-a-nightshift
Branch: feat/wo-p1-520-a-nightshift
Exact base: 84696b2360197c981d6f9fa2f33fb065b7b8ef07

## Goal

Create the reusable thin overlay skill **A-NightShift**: an
overnight/operator-away continuation profile over the accepted
A-FastTask + A-Faster stack. Invocation tasking forms: "use A-NightShift",
"ใช้ A-NightShift", "A-NightShift ตาม Roadmap", and equivalent explicit
overnight/operator-away continuation intent. Explanatory mentions must not
activate work.

## Frozen mutation scope (exactly four NEW files)

1. `.agents/skills/a-nightshift/SKILL.md`
2. `.agents/skills/a-nightshift/references/overnight-supervisor.md`
3. `tests/test_a_nightshift_skill_contract.py`
4. `docs/work-orders/WO-P1-520-a-nightshift-skill.md`

Forbidden: every existing tracked file (especially `.agents/skills/a-faster/**`,
`.agents/skills/a-fasttask/**`, #498 files, #517 files); any
scheduler/task/claim/lease/provider/review/merge/completion authority;
secrets; destructive Git; commit/push/merge.

## Required semantics (pinned by tests)

- overlay on accepted A-FastTask + A-Faster; fail closed if bases
  missing/conflicting; never a second control plane;
- RECOVER -> RECONCILE -> HARVEST before any new dispatch;
- global WIP max 3 mutable + 1 independent review; one mutable hotspot per
  mutation owner; never multiplied;
- GLM-5.3 MAX heavy R2/R3 author/repair/review; GLM-5.3-Flash bounded
  read-only; TypeSafe-JEV advisory only; max normal nesting
  Codex -> GLM -> JEV;
- low-cost Codex traffic-controller/supervisor, never the primary
  engineer; smallest/cheapest currently available capable profile; LOW
  effort default; escalate only for ambiguous recovery/collision/
  authority/acceptance; no permanent product-model pin; fail closed when
  model/effort cannot change mid-goal;
- quiet event-driven waiting with compact receipts; bounded infrequent
  polling only when events are unavailable;
- dispatch-first / harvest-later; refill safe READY capacity; never
  manufacture work; never burn quota for its own sake;
- refresh approved quota/readiness before every material GLM dispatch;
  QUOTA_UNKNOWN is not RATE_LIMITED and never unlimited;
- no blind redispatch of RUNNING/UNKNOWN/INTERRUPTED/TERMINAL_UNHARVESTED;
- one collision-safe per-run ephemeral supervisor contract outside Git
  under the OS temp dir; compact /goal pointer that tells Codex to read
  that exact ephemeral contract; exact ephemeral path recorded in an
  A_NIGHTSHIFT receipt;
- cleanup only at terminal state after child runs are harvested or durably
  checkpointed; exact-path deletion only, no wildcard/glob;
- macOS and Windows temp-root semantics without hard-coding one operator
  machine;
- stop only on HUMAN_ACTION_REQUIRED / HUMAN_DECISION_REQUIRED /
  AUTHORIZATION_REQUIRED / SAFETY_BLOCK / NO_SAFE_NEXT_ACTION;
- successor alignment with #517 A-Faster utilization enforcement:
  active NightShift implies `A_FASTER_ACTIVE=YES` after base activation
  succeeds; routing/receipt output preserves/consumes `FANOUT_TARGET`,
  `UNUSED_SAFE_CAPACITY`, `A_FASTER_UNDERUTILIZED`,
  `AUTO_REFILL_REQUIRED` verbatim from accepted A-Faster semantics —
  no second utilization authority, no parallel refill state machine;
  unexposed markers are recorded as `UNKNOWN`, never invented.

Reference split: `SKILL.md` stays concise; the long reusable supervisor
contract/template lives in `references/overnight-supervisor.md` as the
canonical tracked source. Each invocation materializes an ephemeral
per-run copy and substitutes exact recovered run facts/paths; the template
never instructs committing the ephemeral copy.

## Tests

Semantic RED-first tests in `tests/test_a_nightshift_skill_contract.py`
(not full-file snapshots), pinning: invocation-vs-explanation, base
overlay fail-closed, recover-before-dispatch ordering, WIP, model roles,
JEV advisory, low-cost supervisor without permanent model pin, quiet
waiting, fanout/refill, quota, no blind redispatch, per-run temp path +
collision safety, compact /goal pointer, exact-path cleanup / no wildcard,
stop gates, no second authority, and the never-committed canonical
template. Attempt-0002 adds semantic pins for the five A-Faster
utilization receipt markers (`A_FASTER_ACTIVE` / `FANOUT_TARGET` /
`UNUSED_SAFE_CAPACITY` / `A_FASTER_UNDERUTILIZED` /
`AUTO_REFILL_REQUIRED`), the `A_FASTER_ACTIVE=YES` implication, and the
no-second-authority boundary.

## Attempt-0002 — successor alignment with #517

Read-only fan-in against #517 showed A-Faster utilization enforcement
introduces machine-visible receipt markers: `A_FASTER_ACTIVE`,
`FANOUT_TARGET`, `UNUSED_SAFE_CAPACITY`, `A_FASTER_UNDERUTILIZED`,
`AUTO_REFILL_REQUIRED`. This repair adds them to the overlay so
A-NightShift cleanly consumes/preserves accepted A-Faster semantics once
#517 is accepted, without duplicating authority: active NightShift
implies `A_FASTER_ACTIVE=YES` after base activation succeeds; the
markers are passed through verbatim in routing/receipt output and as
pass-through placeholders in the supervisor template; the overlay
computes no second utilization authority or refill state machine. The
#517 worktree was not inspected; existing A-Faster/A-FastTask files are
untouched; the four-file mutation scope is unchanged.

## Verification matrix

- run `tests/test_a_nightshift_skill_contract.py` (RED observed at
  attempt-0001 before GREEN);
- run `tests/test_a_faster_invocation_contract.py`;
- strict UTF-8 on all four files;
- `git diff --check`;
- exact scope: no tracked changes and no new paths outside the four files
  plus the run result artifact;
- added-line secret scan (0 hits);
- no tracked changes outside the four paths.

## Result

Compact result at `runs/WO-P1-520/author/attempt-0002/result.md`
(attempt-0001 result retained at `runs/WO-P1-520/author/attempt-0001/result.md`).
Do not commit/push/merge.
