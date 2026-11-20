# ADR-0001 — MCP Gateway: thin facade reopened; brain enforcement deferred

Original decision: 2026-08-22
Reopened: 2026-09-16 via WO-P1-247 / Issue #331
Recomposed: 2026-09-17 via WO-P1-247 / PR #332 (accepted controlled pivot)
Status: ACCEPTED ARCHITECTURE DIRECTION / IMPLEMENTATION GATED BEHIND THE RECOMPOSED RUNTIME/ZRA-4 ORDER

## Context

The original ADR separated two related ideas under "MCP gateway":

1. **Multiplexer** — one local MCP server + one tunnel port routing tool calls
   to per-project Serena instances.
2. **Brain enforcement (Second Brain Phase 2)** — a gateway that hard-enforces
   proof that an agent read brain rules before write/execute.

The 2026-08-22 decision deferred both facets. At that time Serena multi-project
activation plus one tunnel per connector was validated and manageable, while a
new proxy risked becoming a second orchestration universe.

### Superseded 2026-08-22 rationale (preserved for history)

- Serena already supported multi-project activation through `activate_project`,
  covering most multi-project needs without another proxy.
- A multiplexer would add MCP proxy/session/tool-namespace complexity and risk a
  second orchestration universe, contrary to the reuse-before-build gate in
  `docs/superpowers/specs/2026-08-21-one-app-orchestration-design.md:11`.
- The then-current one-tunnel-per-connector model had been validated with five
  live instances and was considered manageable at that time.
- Brain enforcement could be approached incrementally through execution-record
  evidence and preflight checks; Phase 1 explicitly noted that prompts teach but
  do not cage (`docs/plans/2026-08-21-second-brain-phase1.md:24`).

The original reopen conditions were:
- tunnel-per-connector stops scaling or materially degrades UX;
- hard brain enforcement becomes necessary and lighter gates are insufficient;
- an upstream gateway primitive appears that can be wrapped rather than built.

## 2026-09-16 reopen evidence

The user now explicitly reports that separately connecting RDC plus SunDay
Workers 1–5 is too difficult and wants one user-facing SunDayMCP connection.
That is direct evidence that the original degraded-UX reopen condition is met.
The desired product also now includes a planned execution substrate (recomposed
from the earlier Worker Host concept into the SunDay Runtime Supervisor),
provider-neutral execution, persistent background lifecycle, and a Browser
Companion, making a single capability facade a product-boundary concern rather
than a Serena-only multiplexer.

## 2026-09-17 recomposition — SunDay Runtime substrate

The accepted controlled pivot splits the planes explicitly:

- A-Sunday Conductor remains the **sole control plane** (authority, admission,
  claims/leases, review, acceptance, recovery, evidence).
- The new **SunDay Runtime** is an **execution substrate only**: `execute /
  observe / cancel / collect evidence`. It owns no scheduling, claims, tasks,
  providers, review, retry, recovery, completion, merge, or project-memory
  authority.
- **One Runtime Supervisor per device** supervises separate isolated executor
  processes/contexts per lane.
- There is **no mutable global Active Project authority**. Logical Worker
  `1..N` is lane naming only, not a fleet identity.
- Per-lane **explicit execution-context binding** (repo/worktree/branch/HEAD/
  claim) with fail-closed `CONTEXT_DRIFT` replaces the standing rule that every
  exposed Worker binds to the same Active Project.

### Supersede — shared mutable Serena Active Project

The shared mutable Serena Active Project model (including reliance on Serena
global `activate_project` as a cross-lane authority) is SUPERSEDED. Corrected
defect analysis: a request timeout alone does not prove a Serena deadlock;
project-context drift caused by global project activation is the architectural
defect. Transitional Serena use is private per lane/worktree and optional
through a lane-local compatibility adapter. The long-term semantic direction is
a small semantic interface over LSP + Tree-sitter + bounded ripgrep; language
servers and global indexes are not rebuilt initially.

### Adapter dependency strategy

DesktopCommanderMCP is adopted as a pinned upstream dependency/adapter for
useful filesystem/search/remote-device mechanics — not a whole-repo fork
initially. Existing Conductor supervised execution/process ownership remains
the authority, and the DesktopCommanderMCP hosted relay remains an optional
external dependency.

### Security P0 — mutation surface

Autonomous mutation must NOT default to unrestricted raw shell, because a
same-user shell can bypass scope. Until stronger isolation exists, prefer typed
file edits, a patch-apply broker, and allowlisted build/test commands. This
binds the Runtime executors, the facade, and any adapter-backed operation
alike.

## Decision

Reopen **only the multiplexer/facade facet** as a thin SunDayMCP capability
facade over existing A-Sunday Conductor authority.

Architecture shaping, contracts, threat modeling, conformance design, and
migration planning may proceed under bounded docs claims. Product/source
implementation of the Runtime and unified facade remains gated behind the
recomposed order — SunDay Runtime single-device MVP, two-lane multi-project
isolation/recovery proof, then ZRA-4 recomposed acceptance — unless a later
explicit user decision reorders that dependency after fresh authority/conflict
analysis. Federation is additionally deferred until the isolation/recovery
proof is accepted.

The brain-enforcement facet remains **DEFERRED**. A single endpoint does not
prove an agent read, understood, or followed A-Wiki policy; existing recorded
evidence, admission, claim/lease, review and mutation gates remain responsible
for that boundary.

## Thin-facade boundary

The facade MAY:
- authenticate a client/device/session;
- expose a collision-free typed capability namespace;
- bind logical lane/project/worktree/session identity;
- translate schemas/protocol envelopes;
- delegate typed operations to existing semantic/native/Git/provider adapters;
- project bounded status/events and capability availability;
- preserve legacy endpoints during migration.

The facade MUST NOT become:
- a scheduler, task graph/store, claim/lease system or READY authority;
- a provider registry/quota/admission authority;
- a review, retry, recovery, deduplication or completion state machine;
- durable project memory or a second SSoT;
- an opaque `execute(anything)` remote shell that bypasses typed authorization
  (see Security P0 above).

A-Conductor remains the control/trust/authority plane. The SunDay Runtime is
its execution substrate. Serena (lane-local compatibility adapter), native-device
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
is proven. Migration is additive first: map stable logical lane identities to
existing runtimes, prove read-only parity, then bounded write/action parity
through the same admission/dedup authorities. Do not shadow-run the same
external or mutable effect through both legacy and facade paths.

Do not silently delete legacy connector configuration, credential references,
or user project state. Rollback disables facade routing and restores the
previous endpoint selection without replaying unfinished work.

## Consequences

- The original 2026-08-22 defer decision remains part of ADR history; its UX
  reopen condition is now satisfied for the thin-facade facet.
- The Worker Host concept is recomposed into the SunDay Runtime Supervisor
  (one supervisor per device, isolated per-lane executors) and is refined in
  the Elastic Multi-Agent roadmap behind the recomposed
  Runtime/isolation/ZRA-4 dependency fence.
- The shared mutable Serena Active Project model is superseded; transitional
  Serena use is lane-local and optional.
- Federation is deferred until the two-lane multi-project isolation/recovery
  proof is accepted.
- Brain enforcement remains deferred until its separate reopen condition is met.
- No new orchestration/control-plane authority is created by this ADR.
