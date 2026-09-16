# ADR-0001 — MCP Gateway: thin facade reopened; brain enforcement deferred

Original decision: 2026-08-22
Reopened: 2026-09-16 via WO-P1-247 / Issue #331
Status: ACCEPTED ARCHITECTURE DIRECTION / IMPLEMENTATION GATED AFTER ZRA-4

## Context

The original ADR separated two related ideas under "MCP gateway":

1. **Multiplexer** — one local MCP server + one tunnel port routing tool calls
   to per-project Serena instances.
2. **Brain enforcement (Second Brain Phase 2)** — a gateway that hard-enforces
   proof that an agent read brain rules before write/execute.

The 2026-08-22 decision deferred both facets. At that time Serena multi-project
activation plus one tunnel per connector was validated and manageable, while a
new proxy risked becoming a second orchestration universe.

The original reopen conditions were:
- tunnel-per-connector stops scaling or materially degrades UX;
- hard brain enforcement becomes necessary and lighter gates are insufficient;
- an upstream gateway primitive appears that can be wrapped rather than built.

## 2026-09-16 reopen evidence

The user now explicitly reports that separately connecting RDC plus SunDay
Workers 1–5 is too difficult and wants one user-facing SunDayMCP connection.
That is direct evidence that the original degraded-UX reopen condition is met.
The desired product also now includes a planned Worker Host, provider-neutral
execution, persistent background lifecycle, and a Browser Companion, making a
single capability facade a product-boundary concern rather than a Serena-only
multiplexer.
## Decision

Reopen **only the multiplexer/facade facet** as a thin SunDayMCP capability
facade over existing A-Sunday Conductor authority.

Architecture shaping, contracts, threat modeling, conformance design, and
migration planning may proceed under bounded docs claims. Product/source
implementation of the unified Host/facade remains gated after the accepted
ZRA-4 bounded-parallel baseline unless a later explicit user decision reorders
that dependency after fresh authority/conflict analysis.

The brain-enforcement facet remains **DEFERRED**. A single endpoint does not
prove an agent read, understood, or followed A-Wiki policy; existing recorded
evidence, admission, claim/lease, review and mutation gates remain responsible
for that boundary.

## Thin-facade boundary

The facade MAY:
- authenticate a client/device/session;
- expose a collision-free typed capability namespace;
- bind logical Worker/project/worktree/session identity;
- translate schemas/protocol envelopes;
- delegate typed operations to existing semantic/native/Git/provider adapters;
- project bounded status/events and capability availability;
- preserve legacy endpoints during migration.

The facade MUST NOT become:
- a scheduler, task graph/store, claim/lease system or READY authority;
- a provider registry/quota/admission authority;
- a review, retry, recovery, deduplication or completion state machine;
- durable project memory or a second SSoT;
- an opaque `execute(anything)` remote shell that bypasses typed authorization.

A-Conductor remains the control/trust/authority plane. Serena, native-device
operations, Git/GitHub, Kilo/Claude/provider harnesses, and future browser or
remote-host surfaces remain adapters/capabilities.
## Security and recovery constraints

One endpoint is a UX boundary, not a security boundary. Every privileged
operation still requires current capability/authorization/project/worktree/task
and ownership checks. Transport reconnect may restore observation/session
state, but it must never blindly replay an ambiguous model/process/mutation
effect; existing execution identity, deduplication and recovery truth decide
whether the outcome is complete, partial, running, or UNKNOWN.

Dynamic/lazy capability exposure is permitted only when client conformance
proves tool-list/change behavior. A static curated tool set remains the fallback.
Capability names must reject collisions rather than silently shadow backends.

Browser/page content remains untrusted input. A future Browser Companion or
Native Messaging bridge is an adapter only and cannot mint claim, execution,
provider, merge, or completion authority.

## Migration and rollback

Legacy SunDay Worker connectors and RDC remain available while SunDayMCP parity
is proven. Migration is additive first: map stable logical Worker identities to
existing runtimes, prove read-only parity, then bounded write/action parity
through the same admission/dedup authorities. Do not shadow-run the same
external or mutable effect through both legacy and facade paths.

Do not silently delete legacy connector configuration, credential references,
or user project state. Rollback disables facade routing and restores the
previous endpoint selection without replaying unfinished work.

## Consequences

- The original 2026-08-22 defer decision remains part of ADR history; its UX
  reopen condition is now satisfied for the thin-facade facet.
- Worker Host / SunDayMCP implementation is refined in the Elastic Multi-Agent
  roadmap and remains behind the accepted Zero-Relay/ZRA-4 dependency fence.
- Brain enforcement remains deferred until its separate reopen condition is met.
- No new orchestration/control-plane authority is created by this ADR.
