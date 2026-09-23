---
name: a-nightshift
description: Overnight/operator-away continuation overlay for substantial A-Sunday Conductor work — keeps the accepted A-FastTask/A-Faster stack progressing unattended through RECOVER -> RECONCILE -> HARVEST, a low-cost Codex traffic-controller supervisor, GLM-5.3 MAX heavy lanes, quiet event-driven waiting, and strict stop gates. Activation requires an explicit invocation clause ("use A-NightShift" / "ใช้ A-NightShift" / "A-NightShift ตาม Roadmap"); explanatory mentions never activate. MUST load and obey ../a-faster/SKILL.md first. Adds overnight routing constraints only; grants no task, claim, cleanup, provider, review, merge, or acceptance authority.
---

# A-NightShift — overnight operator-away continuation overlay

A-NightShift is a **thin overlay on the accepted A-FastTask + A-Faster
stack**, not a second control plane. It keeps already-authorized work
progressing overnight while the operator is away, and it stops the moment a
human gate or safety boundary appears.

Before using this overlay, read and obey:

`../a-faster/SKILL.md` (which itself must load `../a-fasttask/SKILL.md`)

If either base skill is missing, unreadable, or conflicts with this file,
fail closed as `A_NIGHTSHIFT_BASE_MISSING_OR_CONFLICT` and stop with
`NO_SAFE_NEXT_ACTION`. The bases own recovery, classification, claim, WIP,
collision, evidence, cleanup, and authority rules; A-NightShift adds only
overnight continuation constraints. This overlay grants no task, claim,
cleanup, provider, review, merge, or acceptance authority, and it never
becomes a scheduler, task store, claim/lease system, reviewer, or
completion authority.

Activation is strictly layered: after base activation succeeds, an active
A-NightShift session implies `A_FASTER_ACTIVE=YES`. The overlay runs only
on top of an active A-Faster routing and never sets, clears, or fabricates
that base marker itself.

## Invocation contract (activation)

One explicit clause is enough to route the full overnight profile for that
session:

- **"use A-NightShift"**
- **"ใช้ A-NightShift"**
- **"A-NightShift ตาม Roadmap"**

Any equivalent explicit overnight/operator-away continuation intent — the
operator asks that work continue unattended overnight or while away, naming
this overlay — routes the same profile. The routed profile never exceeds
what the accepted bases already allow: verbose or emphatic forms add
emphasis only and grant no extra WIP, authority, quota, or collision
tolerance.

Explanatory mentions do not activate work: asking what A-NightShift is,
discussing it, quoting it, or documenting the name (including this file)
activates nothing unless an explicit overnight/operator-away continuation
intent is also present. After activation, the normal A-FastTask binding and
authority gates still apply before anything runs.

## Overnight loop

Every entry and every continuation follows this ordering strictly:

```
RECOVER -> RECONCILE -> HARVEST before any new dispatch
```

1. **RECOVER** the delegated-run census and lifecycle truth exactly as
   A-Faster defines it: durable lane pointers, exact process identity,
   result/exit/log evidence, actual Git/worktree/branch/HEAD/dirty state.
2. **RECONCILE** ambiguous states (`STALLED` / `INTERRUPTED` / `UNKNOWN`):
   side effects and replay safety first; fold material lifecycle pulses.
3. **HARVEST** and verify every `TERMINAL_UNHARVESTED` result before it can
   block or duplicate anything.

Only after that loop completes may new dispatch happen, through the normal
A-FastTask pipeline fill under the same authorities.

## Global WIP

The inherited A-Faster global budget is unchanged and never multiplied by
device, harness, session, or model: **max 3 mutable + 1 independent review
lanes**, and `1 MUTABLE HOTSPOT = 1 MUTATION OWNER`. A-NightShift never
adds WIP slots, never relaxes the collision gate, and never creates an
independent review lane of its own.

## Model roles

- **GLM-5.3 MAX** (effort max) is the heavy lane for R2/R3 authoring,
  repair, and any required independent review, exactly per the A-Faster
  routing rules.
- **GLM-5.3-Flash** is bounded read-only assistance only
  (reconnaissance, census, shaping, precheck, advisory); it never holds
  mutation authority and never satisfies a required independent review.
- **TypeSafe-JEV** is advisory only: its output is evidence, never
  task/claim/mutation/review/merge/completion authority. Provider failure,
  malformed evidence, or low confidence fails closed to the normal path.
- Maximum normal nesting is **Codex -> GLM -> JEV**; JEV results return to
  the GLM lane that asked, never to another JEV call. No deeper nesting is
  introduced.

## Low-cost Codex supervisor

The overnight supervisor is a **low-cost Codex lane acting as traffic
controller** — routing, waiting, harvesting, checkpointing — and is never
the primary engineer. At activation, select the
smallest/cheapest currently available capable supervisor profile from what
the harness actually exposes, defaulting to LOW effort for routing and
harvest steps. Escalate effort or profile only for genuinely ambiguous
recovery, collision, authority, or acceptance questions; never escalate
just to speed up routine waiting.

Do not permanently pin a Codex product model name in this skill: selection
is per-invocation from the currently available profiles, and a cheaper
capable profile is always preferred when available. If the selected
supervisor's model or effort cannot change mid-goal when escalation is
required, fail closed and escalate to a human or to a stronger preselected
profile rather than inventing capability or silently continuing under the
wrong profile.

## Quiet waiting

Waiting must be quiet and event-driven: prefer compact receipts and
event-driven wakeups; when events are unavailable, fall back to bounded
infrequent polling on a declared low-frequency interval instead of busy
polling or chatty narration. Compact receipts record state transitions and
evidence references only — no secrets, no log dumps.

## Fanout and refill

Follow dispatch-first / harvest-later: fill every free safe READY slot up
to the inherited WIP budget, then refill as lanes go terminal; never
manufacture work to keep lanes busy and never burn quota for its own sake —
an idle safe state with no READY work is truthful, not a failure.

Utilization markers are consumed, never recomputed: when the accepted
A-Faster semantics expose `FANOUT_TARGET`, `UNUSED_SAFE_CAPACITY`,
`A_FASTER_UNDERUTILIZED`, or `AUTO_REFILL_REQUIRED`, preserve and forward
them verbatim in NightShift routing/receipt output. A-NightShift computes
no second utilization authority and no parallel refill state machine;
refill decisions stay with the accepted A-Faster semantics that emitted
the markers. Until the accepted base exposes a marker, its value is
recorded as `UNKNOWN`, never invented.

## Quota gates

Refresh approved quota/readiness evidence before every material GLM
dispatch — not once per night. `QUOTA_UNKNOWN` is not `RATE_LIMITED` and is
never treated as unlimited; never collapse unlike failures, and obey actual
`QUOTA_EXHAUSTED`/auth/transport/cost gates exactly as the bases define
them.

## No blind redispatch

Never blindly redispatch a lane whose census-derived state is `RUNNING`,
`UNKNOWN`, `INTERRUPTED`, or `TERMINAL_UNHARVESTED`. A wrapper timeout, a
missing UI card, session loss, or a stale PID number is a recovery signal,
never redispatch permission; apply the A-Faster PRE-DISPATCH DEDUPE GATE
before every material launch.

## Ephemeral per-run supervisor contract

Each activation creates exactly one collision-safe per-run supervisor
contract **outside Git, under the OS temp dir** — never inside any repo or
worktree, and never hard-code one operator machine (macOS uses `$TMPDIR`,
Windows uses `%TEMP%`/`%TMP%`; the canonical cross-platform rules live in
`references/overnight-supervisor.md`):

1. materialize an ephemeral per-run copy of that canonical template, which
   is the canonical tracked source, substituting exact recovered run
   facts/paths per its substitution rules;
2. emit a compact `/goal` pointer that tells the Codex supervisor to read
   that exact ephemeral contract path and operate it verbatim — the pointer
   carries the path, not a copy of the contract, and never secrets;
3. record the exact ephemeral path (plus run id, selected supervisor
   profile, and stop state) in an A_NIGHTSHIFT receipt.

Never commit the ephemeral copy; it is a runtime artifact outside Git.

## Cleanup of the ephemeral run

Cleanup happens only at terminal state, after every child run is harvested
or durably checkpointed. Delete by exact path only — the one run directory
created for this activation; never wildcard or glob deletion, and never the
temp root itself. Record the deletion in the `A_NIGHTSHIFT` receipt. If any
child run is unharvested and not durably checkpointed, cleanup stays
blocked with its typed blocker.

## Stop gates

Stop only on `HUMAN_ACTION_REQUIRED`, `HUMAN_DECISION_REQUIRED`,
`AUTHORIZATION_REQUIRED`, `SAFETY_BLOCK`, or `NO_SAFE_NEXT_ACTION`. On any
stop, checkpoint durable state, publish a truthful lifecycle pulse, clean
up per the cleanup rules when eligible, and record the stop gate in the
`A_NIGHTSHIFT` receipt. Any other overnight pause is a WAITING state, not a
stop.

## Routing output additions

In addition to normal A-Faster output, report the `A_NIGHTSHIFT` receipt:
run id, exact ephemeral contract path, the compact `/goal` pointer used,
selected supervisor profile (model + effort, per-invocation), current loop
position, harvested/unharvested counts, quota freshness, stop gate (or
`NONE`), cleanup state, and the exact next safe action. When the accepted
base exposes them, the receipt also carries the A-Faster utilization
markers compactly and verbatim — `A_FASTER_ACTIVE` (implied `YES` after
base activation succeeds), `FANOUT_TARGET`, `UNUSED_SAFE_CAPACITY`,
`A_FASTER_UNDERUTILIZED`, `AUTO_REFILL_REQUIRED` — passed through from
A-Faster, never recomputed by this overlay.

A-NightShift ends where its bases end: after routing/binding and overnight
continuation state is durably checkpointed.
