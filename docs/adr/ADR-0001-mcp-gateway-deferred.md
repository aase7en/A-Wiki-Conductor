# ADR-0001 — MCP Gateway: deferred (both facets)

Date: 2026-08-22 · Status: ACCEPTED (deferred with explicit reopen conditions) · Supersedes the standing `DECISION_REQUIRED` marker

## Context

Two related-but-distinct ideas have been parked under "MCP gateway":

1. **Multiplexer** — one local MCP server + one tunnel port routing tool calls to per-project Serena instances (any plugin connects to a single endpoint).
2. **Brain enforcement (Second Brain Phase 2)** — a gateway that hard-enforces "agent must prove it read the brain rules before write/execute", recording brain-read evidence in execution records (Phase 1 teaches via `system_prompt`; prompts teach but do not cage — `docs/plans/2026-08-21-second-brain-phase1.md:24`).

## Decision

**Defer both facets.** Do not build an MCP gateway in A-Sunday Conductor for now.

## Rationale

- **Serena already supports multi-project activation inside one instance** (`activate_project`), which covers most multi-project needs without a proxy.
- A multiplexer is a new MCP-protocol proxy subsystem (session state, tool-namespace collisions across instances) — a **second orchestration universe** that conflicts with the reuse-before-build gate (`docs/superpowers/specs/2026-08-21-one-app-orchestration-design.md:11`).
- The current one-tunnel-per-connector model is validated, working (5 live instances), and each extra chat is a few clicks via **+ ตัวเชื่อม**.
- Brain enforcement can be approached incrementally (execution-record evidence, preflight checks) without a gateway if the need becomes real.

## Reopen conditions (any one)

- Tunnel-per-connector stops scaling (hard limit on tunnels per account, or materially degraded UX when managing many chats).
- A concrete requirement that agents must be *forced* (not taught) to read brain rules before mutating — and lighter mechanisms (recorded evidence, supervised-mode gates) prove insufficient.
- An upstream (Serena/OpenAI) gateway primitive appears that we can wrap rather than build.

## Consequences

- The standing `DECISION_REQUIRED` markers are resolved: gateway work is **deferred per ADR-0001**, not pending an imminent decision.
- Multi-project needs are met by: per-connector instances + the เปลี่ยนโปรเจกต์ (rebind) button + Serena's own multi-project activation.
- Revisit this ADR when any reopen condition is met; that revisit starts with a new WO + updated ADR.
