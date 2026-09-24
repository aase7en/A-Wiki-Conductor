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
recovery, collision, authority, acceptance, or terminal-classification
questions; never escalate just to speed up routine waiting.

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

## External liveness and WAITING_EXTERNAL

A recheckable external dependency — CI job, provider/device run, external
review, tunnel — whose authoritative state is non-terminal (`RUNNING`,
`WAITING`, or derived `STALLED`) is `WAITING_EXTERNAL`, never a terminal
Goal state and never a stop. `STALLED` means expected runtime remains
non-terminal but progress age exceeded the declared bound: it is a warning
that triggers reconciliation against the authoritative source, never
automatic replay or termination.

`RECHECK_ACTION_EXISTS => NO_SAFE_NEXT_ACTION = FALSE`: when a bounded
authorized observation/re-poll/reconcile action exists — including a
checkpoint's already-declared exact next safe action — the terminal gate
`NO_SAFE_NEXT_ACTION` is forbidden. `NO_MUTATION_AVAILABLE` is not
`NO_SAFE_NEXT_ACTION`: an empty mutable READY lane never stops the night
while read-only recovery/reconciliation, `TERMINAL_UNHARVESTED` harvest,
independent review, authorized external observation/recheck, or bounded
monitoring work remains.

Before any terminal `NO_SAFE_NEXT_ACTION`, prove ALL of these absent:
mutable READY work; read-only recovery/reconciliation;
`TERMINAL_UNHARVESTED` harvest; independent review action; authorized
external observation/recheck; bounded monitoring action; any
already-declared exact next safe action. If any exists,
`NO_SAFE_NEXT_ACTION=FALSE`; only this exhaustive proof is
`TRUE_NO_SAFE_NEXT_ACTION`.

While `WAITING_EXTERNAL`, the Goal remains alive: preserve ownership,
context, and the exact dependency/job identity; prefer event-driven wake,
with bounded infrequent polling/recheck as the fallback per the
quiet-waiting rules. Unchanged polls are not progress and must not consume
turns by busy polling. On dependency state change, run
`RECOVER -> RECONCILE -> HARVEST` as needed, recompute the DAG, then
continue/refill under the same authorities.

Escalation guard: before converting an ambiguous `STALLED` or
`WAITING_EXTERNAL` state into terminal blocked/`NO_SAFE_NEXT_ACTION`, the
low-cost supervisor must escalate the classification to the configured
stronger/integrator path or fail closed as `WAITING_EXTERNAL`. Never
terminate merely because the low-cost model is uncertain.

### No-model-spin blocking wait (issue #520 reply-spin repair)

The quiet-waiting rules are not a timer by themselves: a prose polling
interval never bounds model turns. When `WAITING_EXTERNAL` holds with an
unchanged authoritative state, waiting must not spin the supervisor or
the model:

- `USE_BLOCKING_WAIT=YES`: when `blocking_wait_capable=YES` and
  `independent_ready_work=NO`, the wait is ONE foreground read-only
  blocking wait bound to the exact dependency identity. Before blocking,
  dispatch and harvest any independent SAFE READY work first. For
  GitHub Actions CI the preferred foreground primitive is the canonical
  `gh run watch` form pinned in `references/overnight-supervisor.md`.
- `MODEL_TURN_MUST_NOT_COMPLETE_ON_UNCHANGED_WAIT=YES`: the supervisor
  must not complete the model turn solely to report an unchanged
  waiting state; the open tool call holds the turn while the wait
  blocks.
- `USER_VISIBLE_REPEAT_REPLY=FORBIDDEN` and
  `AUTO_CONTINUATION_REPOLL=FORBIDDEN`: never emit a repeated
  user-visible WAITING_EXTERNAL reply solely because a `/goal`
  auto-continuation fired, and never repoll merely because the model
  turn ended; a seconds-scale goal response loop is forbidden.
- `UNCHANGED_WAIT_OUTPUT=SILENT`: suppress or redirect repetitive
  unchanged watch output out of model context; only compact
  transition/terminal/error/timeout evidence returns.
- `WAIT_TOOL_TIMEOUT_RECHECK`: a bounded tool timeout is not progress,
  not a stop gate, and not cleanup authority — fresh-read the
  authoritative state, then re-enter the blocking wait while the
  dependency remains recheckable and no independent SAFE READY work
  exists.
- The wait is never detached or unowned: no detached watcher, timer,
  scheduler, task store, or new state store is created. When no native
  blocking watcher exists, the generic fallback is ONE foreground
  bounded silent loop inside a tool call that sleeps/polls internally
  and returns output only on transition, terminal state, real error, or
  bounded tool timeout.
- On `state_changed=YES`: watcher return, then run
  RECOVER -> RECONCILE -> HARVEST as needed, recompute the DAG, then
  continue/refill. Unchanged polls are not progress and never append
  repeated receipts to the `A_NIGHTSHIFT` receipt; record at most the
  watcher start plus one transition/timeout summary.

## Integrator handoff classification (INTEGRATOR_ACTION_REQUIRED)

`INTEGRATOR_ACTION_REQUIRED` is not itself a stop gate and never collapses
directly into `HUMAN_ACTION_REQUIRED`. An integrator requirement with an
available or unknown route is not automatically terminal. First classify
the actual integrator route from durable evidence:

- **AVAILABLE**: route/handoff through the existing accepted authority.
  Classify `WAITING_INTEGRATOR`, `GOAL_TERMINAL=NO`, `CLEANUP_ALLOWED=NO`,
  `HUMAN_ACTION_REQUIRED=FALSE`; the Goal stays alive exactly like
  `WAITING_EXTERNAL`.
- **UNKNOWN**: recover/probe the route from durable task authority,
  configured channels, and actual runtime evidence; do not invent
  `HUMAN_ACTION_REQUIRED` while the route is merely unproven.
- **PROVEN_UNAVAILABLE**: `HUMAN_ACTION_REQUIRED` is allowed only when the
  route is proven unavailable and a human must actually invoke the
  integrator.

No model/provider name grants authority: GPT-5.6 Sol remains the accepted
integrator/acceptance authority, and this overlay adds no second review,
acceptance, or completion authority.

## Stale terminal-pointer recovery (CONTRACT_ABSENT)

A later `/goal` entry that finds the ephemeral contract missing
(`CONTRACT_ABSENT`) must first recover durable closeout by exact run id
before any classification:

- Exact durable terminal+cleanup proof — `PRE_CLEANUP_FOLDED` plus
  `POST_CLEANUP_CONFIRMED` folded into the same existing durable task
  authority — classifies the entry as
  `STALE_TERMINAL_POINTER` / `GOAL_ALREADY_TERMINAL`:
  `SAFETY_BLOCK=FALSE`, `REMATERIALIZE=FORBIDDEN`, `REDISPATCH=FORBIDDEN`,
  `USER_VISIBLE_REPEAT_REPLY=FORBIDDEN`, and no new authority. Do not
  rematerialize the deleted contract, redispatch the finished run, or emit
  a repeated user-visible reply; expected post-cleanup absence is not a
  safety incident.
- No matching durable terminal proof: classify `CONTRACT_ABSENT_UNKNOWN`,
  which may fail closed as `SAFETY_BLOCK`. Cleanup intent alone is
  insufficient — `PRE_CLEANUP_FOLDED` without `POST_CLEANUP_CONFIRMED`, a
  failed deletion, or a missing post-confirmation is not cleanup proof;
  never fabricate success and keep the state fail-closed and recoverable.

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

Before any terminal cleanup, fold a compact final run record into an
existing durable task authority (Issue / accepted WO checkpoint / existing
durable checkpoint): run id, terminal classification, evidence pointer(s),
exact next safe action, and cleanup intent. This fold is the
`PRE_CLEANUP_FOLDED` phase. The ephemeral receipt alone is explicitly
insufficient durable closeout — it may be deleted with its run directory.
After the exact-path deletion of the one run directory succeeds, append a
`POST_CLEANUP_CONFIRMED` record to the SAME existing durable authority:
run id, exact deleted path, terminal classification, and cleanup result —
no secrets, no log dumps. Cleanup intent alone is not cleanup proof: only
`PRE_CLEANUP_FOLDED` plus `POST_CLEANUP_CONFIRMED` in the same authority
prove completed durable closeout. If deletion fails or the
post-confirmation cannot be recorded, closeout stays fail-closed and
recoverable — record the typed blocker and keep the run recoverable; never
fabricate cleanup success. This two-phase fold is continuity folding into
existing authority, not a new status store.

Cleanup happens only at terminal state, after every child run is harvested
or durably checkpointed, and never while any lane or external dependency
is `RUNNING`, `WAITING`, `WAITING_EXTERNAL`, `STALLED`,
INTERRUPTED-recoverable, UNKNOWN-recoverable, or otherwise holds a valid
recheck or exact next safe action. Cleanup is eligible only after
`GOAL_COMPLETE`, or a TRUE terminal human/safety/authorization gate, or
`TRUE_NO_SAFE_NEXT_ACTION` proven by the exhaustive predicate; a
"blocked" label alone is never cleanup authority. Delete by exact path
only — the one run directory created for this activation; never wildcard
or glob deletion, and never the temp root itself. Record the deletion in
the `A_NIGHTSHIFT` receipt. If any child run is unharvested and not durably
checkpointed, cleanup stays blocked with its typed blocker.

## Stop gates

Stop only on `HUMAN_ACTION_REQUIRED`, `HUMAN_DECISION_REQUIRED`,
`AUTHORIZATION_REQUIRED`, `SAFETY_BLOCK`, or `NO_SAFE_NEXT_ACTION` — and
that last gate only as `TRUE_NO_SAFE_NEXT_ACTION` proven by the exhaustive
absence predicate under "External liveness and WAITING_EXTERNAL";
`WAITING_EXTERNAL` and `STALLED` are waiting states, never stop gates.
`INTEGRATOR_ACTION_REQUIRED` is not itself a stop gate: classify the
integrator route first per "Integrator handoff classification" — an
integrator requirement with an available or unknown route is not
automatically terminal. On
any stop, checkpoint durable state, publish a truthful lifecycle pulse,
clean up per the cleanup rules when eligible, and record the stop gate in
the `A_NIGHTSHIFT` receipt. Any other overnight pause is a WAITING state,
not a stop.

## Routing output additions

In addition to normal A-Faster output, report the `A_NIGHTSHIFT` receipt:
run id, exact ephemeral contract path, the compact `/goal` pointer used,
selected supervisor profile (model + effort, per-invocation), current loop
position, harvested/unharvested counts, quota freshness, stop gate (or
`NONE`), cleanup state, and the exact next safe action — plus the active
external-liveness classification when a dependency is non-terminal
(`NIGHTSHIFT_STATE=WAITING_EXTERNAL` with `GOAL_TERMINAL=NO`,
`CLEANUP_ALLOWED=NO`). When the accepted
base exposes them, the receipt also carries the A-Faster utilization
markers compactly and verbatim — `A_FASTER_ACTIVE` (implied `YES` after
base activation succeeds), `FANOUT_TARGET`, `UNUSED_SAFE_CAPACITY`,
`A_FASTER_UNDERUTILIZED`, `AUTO_REFILL_REQUIRED` — passed through from
A-Faster, never recomputed by this overlay.

A-NightShift ends where its bases end: after routing/binding and overnight
continuation state is durably checkpointed.
