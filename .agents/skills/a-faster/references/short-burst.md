# SHORT_BURST — frozen bounded-loop execution policy (WO-P1-483)

This reference is the skill-policy carrier for the WO-P1-483 short-burst
contract: budgets, staged escalation, timeout semantics, foreground/background
threshold, pre-model transport taxonomy, and user-visible checkpoint cadence.
It binds every A-Faster executor of this work-order family. It adds budgets
and ordering rules only — it creates no scheduler, retry engine, lease,
registry, or second execution state machine, and it never weakens
claim/lease/ownership/secret/destructive-operation gates. Liveness classes and
census dispositions come from `EXECUTION_LIVENESS_PROTOCOL.md` and
`durable-lanes.md` §5 as reused by `SKILL.md`; nothing here redefines them.

## The frozen loop

Every burst follows exactly:

```
RECOVER EXACT EVIDENCE -> ONE BOUNDED ACTION/DISPATCH -> USER CHECKPOINT -> NEXT BURST
```

One burst = one bounded action (or one bounded dispatch), then a checkpoint,
then the next burst. No burst may contain a second material action after an
UNKNOWN/RECOVER outcome.

## Exact-path first

Prefer exact-path/pointer reads (a known file, a known `runs/` pointer, a
known LANE_REF/DELEGATED_RUN_ID) before any broad scan. Broad recursive scans
are forbidden in the critical path. Escalation is allowed only when a bounded
exact query FAILS (not-found or ambiguous): at most one escalation step per
burst, widening exactly one dimension (e.g. one glob family or one
include-set), still bounded (≤ 3 directory levels or ≤ 200 candidate paths),
and recorded in the burst checkpoint. A second failed escalation ends the
burst: checkpoint the typed blocker and plan the next burst; do not scan
harder.

## Default budgets (frozen in WO-P1-483)

| Budget | Default value | Notes |
|---|---|---|
| Single command output | ≤ 200 lines or ≤ 8 KiB (head+tail slice), never full dump | applies to shell/build/test output folding |
| Exact-file read | ≤ 400 lines per read by default | targeted single-file reads |
| Glob/query result set | ≤ 50 paths or ≤ 40 matches, ≤ 5 context lines | broad result sets are truncated and reported as truncated |
| Bounded exact queries per burst | ≤ 2 before escalation | not-found/ambiguous counts as a failed query |
| Foreground command time | ≤ 120 s | longer => background-first |
| Background polling | ≤ 1 poll per 30 s, ≤ 10 polls per burst, then yield turn with checkpoint | bounded polling only; no busy wait |

## Timeout semantics

- Wrapper/harness/tool timeout => classify `UNKNOWN/RECOVER`, never automatic
  FAILURE, and never redispatch permission.
- `UNKNOWN/RECOVER` blocks redispatch until reconciliation proves one of: the
  exact recorded PID is dead (matched creation/command identity) AND
  `result_ref`/`exit_ref`/`log_ref` are reconciled AND git/worktree/HEAD/dirty
  state is compared against the dispatch pointer's `dispatch_head`/mutable
  scope.
- If the exact PID is still live with matching identity => `RUNNING`: attach
  or wait; never kill broadly, never redispatch.
- Terminal detail (COMPLETED_ACCEPT / FAILED / ABNORMAL_EXIT, etc.) comes only
  from result/exit artifacts, never from wrapper behavior or exit code alone.

## Foreground/background threshold

- Any dispatch with an expected duration > 120 s MUST be background-first:
  write the durable pointer (existing `pointer.md` fields) before or at
  launch, recording PID + verified command identity when observable, plus
  `log_ref`/`exit_ref` destinations.
- A foreground command crossing the 120 s boundary without completing is
  treated exactly as a wrapper timeout: `UNKNOWN/RECOVER`, reconcile before
  any further action in that hotspot.
- Background lanes are observed only by bounded polling (budget table) plus
  event-style re-entry per the collision-pulse refresh boundaries in
  `SKILL.md`; a fresh turn never assumes background state without re-deriving
  it from pointer + process + artifacts.

## Pre-model transport failure taxonomy

Typed classes; each proves only that the dispatch did not produce model
execution evidence:

| Class | Meaning | Evidence status |
|---|---|---|
| `DISPATCH_POINTER_MISSING` | no durable pointer written before/at launch | dispatch invalid; retry requires fresh pointer first |
| `HARNESS_ROUTE_FAILURE` | harness/model route rejected or never launched | proves nothing about child outcome; quota/route gates re-run before any redispatch |
| `QUOTA_EXHAUSTED` / `QUOTA_UNKNOWN` | provider quota gate | routing evidence only |
| `AUTH_OR_ENTITLEMENT` | credential/entitlement failure | routing evidence only |
| `TRANSPORT_CONNECTIVITY` | network/relay failure pre-model | proves nothing about any prior child process |
| `WRAPPER_TIMEOUT_UNKNOWN` | timeout with child state unproven | => `UNKNOWN/RECOVER` per timeout semantics |

None of these classes may become acceptance evidence, completion evidence, or
failure-of-record for the underlying task. The only acceptance path remains:
pointer → result/exit artifacts → deterministic verification → review/merge
gates.

## Mandatory material-boundary hook sequence

A-Faster's material-boundary sequence is fixed:

`ENTRY -> RECOVERY -> PRE_DISPATCH -> PRE_MUTATION -> PRE_FREEZE -> PRE_REVIEW -> PRE_MERGE -> POST_MAIN`

The minimum evidence required at each boundary reuses existing authorities:

| Checkpoint | Minimum evidence before PASS |
|---|---|
| `ENTRY` | repo/worktree/branch/HEAD/task/claim/scope + dirty state known |
| `RECOVERY` | outstanding delegated runs classified; RUNNING not redispatched; terminal-unharvested harvested first |
| `PRE_DISPATCH` | WIP slot + no-overlap + dedupe gate + fresh provider/model readiness/quota where GLM is used |
| `PRE_MUTATION` | `SAFE_TO_MUTATE=YES` for the exact lane and mutable scope |
| `PRE_FREEZE` | deterministic verification + exact changed-path/scope evidence |
| `PRE_REVIEW` | frozen exact candidate SHA + clean read-only review binding |
| `PRE_MERGE` | exact-head review/CI/risk-floor evidence + current-main drift reconciliation |
| `POST_MAIN` | merged SHA + required post-main CI/runtime proof + durable closeout/checkpoint |

Disposition:

- accepted executable `GUARD` returns allow => checkpoint may be
  `GUARD_ENFORCED/PASS`;
- `DENY`, malformed/ambiguous guard evidence, or required authority/security
  guard unavailable => fail closed for the dependent material action;
- `OBSERVE` / `ADVISORY` telemetry can explain state but never satisfies a
  GUARD requirement;
- if executable GUARD wiring is not yet accepted on that action path, record
  `POLICY_ONLY` and perform the same deterministic gate manually; never claim
  runtime enforcement that does not exist.

No hook verdict creates task/claim/lease/retry/review/acceptance authority.
Hooks enforce accepted policy at invocation boundaries; they do not become a
second control plane.

## User-visible checkpoint cadence

Independent of opaque tool cards (a missing tool card is never progress or
liveness evidence), checkpoints are written to the active WO/Issue checkpoint
or the lane result destination:

- one line before each burst (what/where/why);
- one line after each terminal/harvest outcome;
- immediately at any escalation, any `UNKNOWN/RECOVER`, and any
  `WAITING`/`STOPPED`;
- at least every ~10 minutes of wall time inside one material lane;
- content reuses the existing lifecycle pulse minimum fields
  (`durable-lanes.md` §3.1); no new format.
