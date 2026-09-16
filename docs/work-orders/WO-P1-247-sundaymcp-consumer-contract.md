# WO-P1-247 — SunDayMCP consumer contract and session-routing fold

Date: 2026-09-16
Status: ACTIVE / DOCS-ONLY / SOURCE MUTATION FORBIDDEN
Owner: GPT-5.6 Sol integrator
Risk: R2 architecture/governance documentation
Issue: #331
Base: `018779d0d2f5a7a7a21adb277e23a617692c36fd`
Classification: `REUSE + WRAP + EXTEND`; `NEW` only for a proven protocol gap.

## Goal

Fold the 2026-09-16 GPT-6 Astra SunDayMCP consumer-roadmap review into the
existing A-Sunday Conductor authorities without interrupting the Zero-Relay
critical path or creating a second orchestration universe.

The product North Star is one user-facing SunDayMCP connection backed by
A-Sunday Conductor. The user should not need to understand separate Serena
workers, RDC, Kilo/Claude harnesses, Python/Node prerequisites, ports, tunnels,
or worktree mechanics during ordinary operation.

This WO is architecture/routing documentation only. It does not authorize a
Worker Host, MCP facade, browser extension, service, installer, provider, or
runtime implementation.
## Current-state reconciliation

- Remote `main` at claim: `018779d0d2f5a7a7a21adb277e23a617692c36fd`.
- Protected root checkout remains stale/dirty and is not used for mutation.
- Issue #330 / WO246 is the active R3 author-attempt provenance blocker for
  WO205 / ZRA-2 Phase-D. This WO must not touch that source or its owned docs.
- Issue #320 / WO240 owns exactly its two Browser Wake roadmap/WO files. Its
  frozen candidate remains separate from this claim.
- PR #261 / WO189 is an older draft priority capture on a stale base. Its
  Zero-Relay-first intent is retained, but its branch is not the current
  SunDayMCP architecture authority.
- A-Wiki already owns the canonical global `a-fasttask` skill. The Conductor
  `.agents/skills/a-fasttask/` tree is a repo binding/projection, not a second
  global policy source.
- Current Kilo route `cointh-glm/glm-5.3` passed `kilo roll-call` during this
  session. No approved `COINTH_GLM_API_KEY` environment binding was available,
  so quota API evidence remains `UNKNOWN`, never unlimited.

## Binding dependency order

```text
WO246 provenance
-> WO205 / full ZRA-2 acceptance
-> ZRA-3 accepted NEXT READY continuation
-> ZRA-4 bounded parallel baseline
-> Worker Host / SunDayMCP implementation
-> consumer hardening and optional federation
```

Architecture/docs shaping may proceed in parallel when its claim does not
consume or overlap a critical mutable lane.
## Exact tracked scope

Allowed:
- this work order;
- `docs/adr/ADR-0001-mcp-gateway-deferred.md`;
- `docs/plans/2026-09-07-elastic-multi-agent-leverage-roadmap.md`;
- `.agents/skills/a-fasttask/SKILL.md`;
- `.agents/skills/a-fasttask/references/conductor.md`;
- `docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md`.

Forbidden:
- all `src/` and tests;
- runtime/provider/DB/credentials/install/browser implementation;
- `PROJECT-PLAN.md`, `CURRENT-WORK.md`, `handoff.md`, `COLLAB.md`;
- WO240's two claimed files;
- WO246/WO205/WO227 owned surfaces;
- A-Wiki repository mutation;
- live Worker/process mutation, merge, deploy, or destructive Git operations.

## Architecture decisions captured by this WO

1. Reopen ADR-0001 only for a **thin capability facade** because the reported
   multi-plugin UX now satisfies the original degraded-UX reopen condition.
2. Keep brain-enforcement deferred. A facade is not proof an agent read or
   obeyed policy.
3. SunDayMCP may authenticate, namespace typed tools, bind a request/session,
   translate schemas, and delegate into existing A-Conductor authorities. It
   may not own scheduling, claims, tasks, providers, review, retry, recovery,
   completion, or project memory.
4. Browser Companion/page content is untrusted transport/context. It cannot
   mint repository or execution authority.
5. Legacy Worker/RDC surfaces remain migration fallback until parity is proven;
   no configuration or credential is silently deleted.
## Session-routing decisions

For substantial project/engineering sessions, the existing A-FastTask route
should attempt a lightweight read-only discovery of RDC, GitHub, and exposed
SunDay Workers before mutable work. Unavailable surfaces receive typed failure
classification and block only dependent work. Trivial Q&A bypasses this path.

Every substantial multi-step task performs `GLM_OFFLOAD_ASSESSMENT`. Useful,
independent, bounded work should be routed to an eligible GLM-5.3 lane when the
exact harness/provider/model/readiness/authorization/quota evidence and
ownership gates permit it. GPT-5.6 Sol remains integrator and continues useful
non-overlapping work rather than becoming a passive dispatcher.

A-FastTask stays a router/binder. Actual dispatch remains owned by existing
A-Conductor execution/provider/Zero-Relay backends and existing claims/leases.

## Verification / acceptance

Required before merge consideration:
1. exact scope equals this WO's six paths;
2. `git diff --check` and strict UTF-8 pass;
3. local relative links/references resolve where applicable;
4. added-line credential/secret-pattern scan passes;
5. ADR history remains visible and only the thin-facade facet is reopened;
6. SMCP phases do not reorder `ZRA-2 -> ZRA-3 -> ZRA-4`;
7. no duplicated A-FastTask/global policy authority is introduced;
8. exact candidate SHA is reviewed independently by GLM-5.3 with P0/P1/P2=0,
   or confirmed findings are repaired and rereviewed;
9. exact-head hosted CI passes;
10. GPT-5.6 Sol performs final acceptance. The author lane does not self-merge.

`SAFE_TO_MUTATE_WO247_DOCS=YES` only in the isolated claimed worktree.
`SAFE_TO_MUTATE_SOURCE=NO`.
