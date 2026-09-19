# A-Conductor Deterministic Fault-Injection Contract

Status: Phase 1 test-support contract; extended for the DEX cross-repo boundary (DEX-ARCH-1 / Issue #348)
Work order: `WO-AC-RES-007` (Phase 1); DEX scenarios gate `WO-P1-259` / `WO-P1-260`
Boundary contract: `docs/contracts/execution-admission-receipt-v1.md`

## Purpose

Recovery reliability must be tested deterministically without repeatedly breaking real Serena/MCP/tunnels. A local fake executor simulates transport timing, process state, durable result availability, and output volume while production recovery logic remains unchanged.

## Boundary

The fake is test infrastructure. It may implement the supervised `inspect/collect` shape and write temp-repository evidence, but it is not a production execution backend and must not be wired into normal worker routing.

## Determinism

Scenarios advance only through explicit test actions. No background threads, random sleeps, wall-clock races, or real network failures are required.

## Scenarios

- `NORMAL_SUCCESS`
- `DISCONNECT_BEFORE_LAUNCH`
- `DISCONNECT_AFTER_LAUNCH`
- `DISCONNECT_MID_COMMAND`
- `DISCONNECT_AFTER_COMPLETION`
- `DELAYED_SUCCESS`
- `LARGE_STDOUT`
- `NONZERO_EXIT`
- `MALFORMED_RESULT`
- `UNKNOWN_PROCESS`

## Required observable facts

- whether target ever started;
- launch count;
- whether transport loss was simulated;
- whether process is still running;
- whether result is available;
- durable stdout/stderr/result refs;
- exit code when known;
- never-started vs unknown provenance must remain distinguishable.

## Integration expectations

Tests should combine the fake with production AC-RES primitives:

- AC-RES-003 transport loss/ownership preservation;
- AC-RES-004 recovery reconciliation;
- AC-RES-005 duplicate execution protection;
- AC-RES-006 output backpressure.

The fake itself must not encode the expected production recovery decision.

## Safety

- temp directories/databases only;
- no real Serena/PID/tunnel manipulation;
- no infinite loop/background daemon;
- no network access;
- no destructive Git.

## DEX boundary scenarios (deterministic expected invariants)

These scenarios gate the cross-repo admission/receipt seam defined by
`docs/contracts/execution-admission-receipt-v1.md` (ADR-0002) and are required
by `WO-P1-259` (substrate side) and `WO-P1-260` (control-plane side). They run
on fakes/temp fixtures only, advance only through explicit test actions, and
the fake itself must not encode the expected production decision.

- `ADMISSION_RESPONSE_LOSS` — admission decided, response lost: re-query by idempotency key returns the single original admission; exactly zero or one process exists; no second spawn.
- `SIMULTANEOUS_DISPATCH` — two dispatches for the same binding: exactly one `ACCEPTED`; the other fenced `REJECTED: DUPLICATE_LIVE_ATTEMPT` or attached as observer; at most one live child.
- `SHIM_CRASH_BEFORE_SPAWN` — supervisor/shim dies before child creation: attempt classifiable `NOT_STARTED` from durable evidence; retry still requires explicit Conductor authority, not automatic replay.
- `SHIM_CRASH_AFTER_SPAWN` — supervisor dies after child creation: state is `LAUNCH_AMBIGUOUS`; reconciliation recovers exact process creation identity; terminal classification requires descendant quiescence.
- `PID_REUSE` — PID re-observed with different creation identity or boot epoch: detected as a different process; never treated as the live child; no ownership action against the innocent process.
- `RESULT_BEFORE_RECEIPT` — terminal evidence exists substrate-side, no Conductor receipt: projected `TERMINAL_UNHARVESTED`; conflicting redispatch/mutation blocked until harvest/reconciliation completes.
- `RECEIPT_RESPONSE_LOSS` — receipt stored, response lost: substrate redelivery returns the same receipt idempotently; no double-apply of task effects; no attempt reopening.
- `NOTIFICATION_ACK_LOSS` (future boundary, DEX-3a) — durable receipt already exists; ack loss changes nothing about task/acceptance state; out of scope for v1 receipts.
- `REBOOT_AT_PERSISTENCE_BOUNDARY` — boot epoch changes with attempts in flight: prior live-process identity void; durable admission/evidence/receipt records survive; classification from durable evidence only (typically `UNKNOWN` or terminal); no replay.
- `PATH_ALIAS_JUNCTION_OVERLAP` — dispatch/collection paths alias the same store via junction/subst/8.3 forms: canonical path identity resolves the overlap; unresolved overlap fails closed (rejected scope/quarantine), never double-binds.
- `CLAIM_SESSION_LOSS_CHILD_ALIVE` — claiming session/lease looks stale while the child lives under valid identity: ownership not released; no second owner admitted; release only after verified terminal + descendant quiescence, authorized handoff, or explicit cancellation.
- `MALFORMED_FORGED_EVIDENCE` — evidence with digest mismatch, schema violation, or binding/identity mismatch: rejected with quarantine marker at ingest; never accepted, never repaired by guessing; acceptance state unchanged.
- `CROSS_REPO_SHA_MISMATCH` — substrate or authority head drifted from the pinned compatibility set: new admission/collection under the drifted set rejected; old terminal evidence remains advisory-collectable; set invalid until re-pin and focused review.
