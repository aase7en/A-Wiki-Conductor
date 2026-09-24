# WO-P1-537 — Elastic borrowed lanes + Mission Control wait observability

Date: 2026-09-24
Issue: #537
Class: CONTROL_PLANE_ONLY
Risk: R3 concurrency policy + R2 read-only observability
Base: `1486e75484afa21a79810a7ebe0e92abb384c3b7`
Branch: `feat/wo-p1-537-elastic-mission-control`

## Goal

Replace the fixed operator interpretation of “3 mutable lanes total” with a
bounded elastic claimed-WIP policy that keeps safe work moving during CI,
external-provider and cooldown waits while preserving the normal three-lane
active mutation ceiling.

At the same time, extend the accepted Runtime Cockpit foundation so those waits
are visible as waits rather than generic RUNNING / apparent GPT inactivity.

## Authority boundary

A-Wiki/A-Conductor remains task, claim, lease, WIP, review and acceptance
authority. This WO creates no new scheduler, task store, claim store, monitor DB,
retry engine, completion authority or merge authority.

The new policy module and Cockpit additions are pure projections over structured
facts supplied by existing authorities. A verdict can require a borrow, resume or
park action, but cannot perform that action.

SunDayRemoteMCP is execution substrate only and is out of mutation scope.

## Frozen capacity contract

```text
ACTIVE_MUTATION_LIMIT = 3
BORROWED_LANE_LIMIT   = 2
MUTABLE_CLAIM_LIMIT   = 5
REVIEW_LANE_LIMIT     = 1
```

A mutable claim and active mutation compute are deliberately different counts.
Passive waiting and parked claims remain owned without consuming an
active-mutation slot; `WAITING_GLM` with an active delegated mutation child is
not passive and that child remains counted as active mutation.

## Borrowable wait states

Eligible passive wait states can create elastic capacity:

- `WAITING_APPROVAL`
- `WAITING_CI`
- `WAITING_GLM` only when no delegated mutation child remains active
- `WAITING_JEV`
- `WAITING_EXTERNAL`
- `COOLDOWN`

`BLOCKED`, `HUMAN_REQUIRED`, stale/unknown evidence and collision denial do
not create capacity. A wait label never overrides active-mutation evidence: an
active GLM mutation child remains counted against the three-lane compute ceiling.

## Borrow admission

A new borrowed claim requires all of:

1. a borrowable base wait;
2. real independent READY work;
3. free active-mutation capacity after reserving returning base lanes;
4. fewer than two borrowed claims;
5. exact scope/hotspot gate READY;
6. claim/lease admission READY;
7. runtime/provider admission READY.

Existing `PARKED_CAPACITY` work is resumed before a new borrowed claim is
created. This avoids claim churn and preserves continuity.

No work is manufactured merely to fill capacity.

## Contraction

When a base wait resolves, its return is reserved before new borrowed work.
If projected active mutations exceed three:

1. compute the exact borrowed lanes that must yield;
2. each yielding lane finishes only its current bounded micro-step;
3. checkpoint through existing durable authority;
4. transition the existing claim to `PARKED_CAPACITY`;
5. resume the base lane only after enough active capacity is free.

No reset, clean, stash, broad kill, duplicate claim or blind redispatch is a
valid contraction mechanism.

## Pure policy implementation

`src/a_conductor/elastic_wip_policy.py` classifies already-reconciled facts.

Stable outputs include:

- base / borrowed / review claimed counts;
- borrowable wait count;
- current active mutation count;
- `borrowed_to_park`;
- `borrowed_resume_target`;
- `new_borrow_target`;
- active count after contraction/refill;
- claimed count after refill;
- typed blockers.

It fails closed on overcommit, invalid counts, non-ready/unknown gates and
impossible contraction evidence.

It performs no I/O and imports no scheduler/runtime/store layer.

## Cockpit implementation

The existing COCKPIT-1 projection is extended, not replaced. New durable
activity vocabulary:

- `BORROWED_ACTIVE`
- `WAITING_CI`
- `WAITING_EXTERNAL`
- `COOLDOWN`
- `PARKED_CAPACITY`
- `BLOCKED`
- `HUMAN_REQUIRED`

A `CockpitActivityObservation` is accepted only with
`DURABLE_MONITOR_RECORD` provenance and exact WO/task identity. It may carry:

- capacity class;
- typed reason code;
- observed-at timestamp;
- next recheck timestamp;
- non-negative countdown seconds.

Untrusted activity provenance, foreign WO/task identity, invalid state/reason or
invalid countdown fails closed.

The desktop Cockpit renders wait reason, recheck and countdown and, when capacity
class evidence exists, an observed summary:

```text
base-active=N/3 borrowed-active=N/2 parked=N review=N/1 waits=N
```

This summary is a read model only. Missing capacity evidence is never filled from
guesswork.

## Roadmap fold

The canonical Mission Control roadmap now records this user-authorized MC-0/MC-1
elastic-wait slice. The Elastic Multi-Agent roadmap records the 3+2 claimed-WIP
override and contraction semantics.

## Ownership / collision fence

Allowed exact paths:

- `docs/plans/2026-09-07-elastic-multi-agent-leverage-roadmap.md`
- `docs/plans/2026-09-24-mission-control-agent-digital-twin.md`
- this WO
- `src/a_conductor/elastic_wip_policy.py`
- `tests/test_elastic_wip_policy.py`
- `src/a_conductor/cockpit_projection.py`
- `src/a_conductor/desktop_ui.py`
- `tests/test_cockpit_projection.py`

Forbidden in this WO: #529 NightShift paths, #530 A-Faster-owned paths, #531
resume-adapter paths, authority stores/schemas, CURRENT-WORK/HANDOFF/COLLAB,
SunDayRemoteMCP source, secrets and global Kilo config.

Executable A-Faster consumption is intentionally not wired while #530 owns its
hotspot. After #530 acceptance/release, a bounded successor may consume this
classifier without creating a second WIP authority.

## Acceptance

- RED-first elastic policy tests;
- borrow / no-work / gate / overcommit / park / resume adversarial cases;
- Cockpit wait-vs-running, identity/provenance, countdown and capacity rendering;
- focused and directly related deterministic suites;
- py_compile, diff-check, strict UTF-8, exact-scope and added-line secret scan;
- independent exact-SHA R3 review;
- exact-head hosted CI;
- expected-head merge and detached post-main verification.

## Bounded R3 review repair checkpoint — 2026-09-24

Repair authority: Issue #537 / PR #539 review at candidate
`7845d838d535cb92815f0e5b0773d2f0c265b884`; local composed base is
`ce1487ba6fb5e17b0eddabafc288f815a17997a8` and must be preserved. The
independent review reported P0=0, P1=3, P2=2. Repair scope additionally permits
`src/a_conductor/desktop_control.py` and `tests/test_desktop_control.py`.
Issue #540/A-Faster-owned paths and all authority stores/schemas remain out of
scope.

The bounded repair closes elastic wait-capacity contraction, execution-lifecycle
precedence over activity, injected read-only activity ingestion on both
first/recheck pins, exact execution identity and bounded freshness rejection
without detail leakage, and explicit active GLM-child capacity evidence. No
activity producer, store/schema, timer, thread, poller, or command authority is
added; MON-1 successor owns activity event production.

Verification is limited to directly relevant policy, projection, and desktop
control tests. The known unrelated Tk event-loop hang in the broad desktop UI
suite remains explicitly out of this repair.

## Independent review follow-up — 2026-09-24

Static review identified that direct lane projection without `generated_at`
could not prove activity freshness. Such activity now fails closed, with a
focused regression; the identity-mismatch test name now describes the asserted
behavior. This follow-up remains within the existing three-path repair scope.

## Independent R3 review follow-up — 2026-09-24

The independent MAX review of exact candidate
`e64b6692d38bd13ed7ab85bbc33591a5f14d0fea` returned `NEEDS_FIX`, P0=0,
P1=0, P2=3. Findings were: a stored countdown was rendered without adjusting
for snapshot time; the capacity line silently omitted lanes with no accepted
capacity class; and a parked borrowed claim without a matching execution or
worker row was lost by the composition builders.

Bounded repairs are implemented locally on this WO's existing feature branch
and exact allowed paths only:

- compute countdown seconds at `generated_at` from `next_recheck_at`, with an
  observed-countdown fallback; malformed/missing time evidence is omitted;
- include unclassified lanes in capacity coverage instead of implying a
  complete count;
- retain exact WO/task/lane identity from a durable parked-activity record and
  compose unmatched parked claims even without an execution/worker row.

RED-first regressions reproduced all three findings. Focused verification
passes: 155 passed, 1 deselected (known macOS-hosted Windows-path fixture).
`py_compile`, `git diff --check`, strict UTF-8, exact modified-path scope, and
added-line secret-pattern checks pass. The worktree is still dirty at the old
`e64b669` HEAD; the repaired candidate is not committed or pushed yet. Do not
accept or merge the prior `e64b669` review/CI evidence. Next: commit and push
one repaired candidate, obtain a fresh independent exact-SHA R3 review and
exact-head hosted CI, then repeat GPT acceptance against that SHA.
