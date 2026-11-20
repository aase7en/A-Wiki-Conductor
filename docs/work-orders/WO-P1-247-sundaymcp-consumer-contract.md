# WO-P1-247 — SunDayMCP consumer contract and session-routing fold

Date: 2026-09-16
Recomposition: 2026-09-17 — accepted controlled pivot (carried by PR #332)
Status: ACTIVE / DOCS-ONLY / SOURCE MUTATION FORBIDDEN
Owner: GPT-5.6 Sol integrator
Risk: R2 architecture/governance documentation
Issue: #331
Base: `018779d0d2f5a7a7a21adb277e23a617692c36fd`
Classification: `REUSE + WRAP + EXTEND`; `NEW` only for a proven protocol gap.

## Goal

Fold the 2026-09-16 GPT-6 Astra SunDayMCP consumer-roadmap review and the
2026-09-17 accepted controlled pivot into the existing A-Sunday Conductor
authorities without interrupting the Zero-Relay critical path or creating a
second orchestration universe.

The product North Star is one user-facing SunDayMCP connection backed by
A-Sunday Conductor. The user should not need to understand separate Serena
workers, RDC, Kilo/Claude harnesses, Python/Node prerequisites, ports, tunnels,
or worktree mechanics during ordinary operation.

This WO is architecture/routing documentation only. It does not authorize a
SunDay Runtime supervisor/executor, MCP facade, browser extension, service,
installer, provider, or runtime implementation.

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
- PR #332 is the docs-only carrier of this WO recomposition. No merge,
  acceptance, or merge readiness is claimed by this file.
- A-Wiki already owns the canonical global `a-fasttask` skill. The Conductor
  `.agents/skills/a-fasttask/` tree is a repo binding/projection, not a second
  global policy source.
- Current Kilo route `cointh-glm/glm-5.3` passed `kilo roll-call` during this
  session. The environment binding was empty, but the approved global secret
  resolver exposed `COINTH_GLM_AUTH_TOKEN`; using it only as the CoinTH
  `x-api-key` returned HTTP 200 with the full five-hour quota tuple. Two
  back-to-back quota GETs with no model call between them observed zero change
  in `used_5h` and `remaining_5h`, supporting the provider's non-consuming
  guidance without treating it as a billing guarantee. The secret value and
  machine-local secret-file path are not tracked or logged.

## Accepted controlled pivot — architecture recomposition (2026-09-17)

Control-plane split:

1. A-Sunday Conductor remains the **sole control plane**. The new SunDay
   Runtime is an **execution substrate only**: `execute / observe / cancel /
   collect evidence`. It owns no scheduling, claims, tasks, providers,
   review, retry, recovery, completion, merge, or project-memory authority.
2. **One Runtime Supervisor per device** supervises separate isolated
   executor processes/contexts per lane. Isolation of process, working
   context, and working set across lanes is a Runtime obligation.
3. There is **no mutable global Active Project authority**. Project/repo
   context is bound explicitly per lane.
4. Logical Worker `1..N` is **lane naming only** — not a bound fleet identity
   and not an obligation that lanes share one project.
5. Transitional Serena use is **private per lane/worktree and optional**. The
   shared mutable Serena Active Project model is SUPERSEDED; ADR-0001 records
   the supersede and the corrected defect analysis.
6. The standing rule that every exposed Worker binds to the same Active
   Project is **replaced** by per-lane explicit execution-context binding
   (repo/worktree/branch/HEAD/claim) with fail-closed `CONTEXT_DRIFT` when
   the executor process/context does not match the declared binding.
7. Default WIP is preserved: `3 mutable + 1 independent read-only review`
   lanes, spare recovery capacity, and `1 MUTABLE HOTSPOT = 1 MUTATION OWNER`.

Strategy decisions:

8. **DesktopCommanderMCP**: adopt as a pinned upstream dependency/adapter for
   its useful filesystem/search/remote-device mechanics — not a whole-repo
   fork initially. Existing Conductor supervised execution/process ownership
   remains the authority; the hosted relay remains an optional external
   dependency.
9. **Security P0**: autonomous mutation must NOT default to unrestricted raw
   shell, because a same-user shell can bypass scope. Prefer typed file
   edits, a patch-apply broker, and allowlisted build/test commands until
   stronger isolation exists.
10. **Semantic transition**: a Serena compatibility adapter is lane-local
    only; the long-term direction is a small semantic interface over LSP +
    Tree-sitter + bounded ripgrep. Do not rebuild language servers or a
    global index initially.
11. **Evidence correction**: a request timeout alone does not prove a Serena
    deadlock; project-context drift from global activation is the
    architectural defect. Per-lane isolated contexts remove that defect class
    instead of papering over it with timeouts.

Recomposition ledger:

| Action | Item |
|---|---|
| KEEP | WO246, WO205 / full ZRA-2, ZRA-3, SunDayMCP thin facade |
| RECOMPOSE | ZRA-4, WO247 / PR #332, Worker Host -> Runtime Supervisor |
| SUPERSEDE | shared mutable Serena Active Project binding |
| DEFER | federation until two-lane multi-project isolation/recovery proof |

## Binding dependency order (recomposed)

```text
WO246 provenance design + implementation
-> WO205 / full ZRA-2 acceptance
-> ZRA-3 accepted NEXT READY continuation
-> SunDay Runtime single-device MVP
   (Runtime Supervisor + isolated per-lane executors; substrate only)
-> two-lane multi-project isolation/recovery proof
-> ZRA-4 recomposed bounded-parallel acceptance
-> thin SunDayMCP facade
-> consumer hardening / optional federation
```

The relative `ZRA-2 -> ZRA-3 -> ZRA-4` order is unchanged; the Runtime MVP and
its isolation/recovery proof are inserted before ZRA-4 recomposed acceptance
because the bounded-parallel proof now runs on the Runtime's isolated two-lane
substrate. Federation stays deferred until the isolation/recovery proof is
accepted.

Architecture/docs/research shaping for the Runtime may proceed in parallel
when its claim does not consume or overlap a critical mutable production
lane.

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

## Facade decisions captured by this WO (2026-09-16 fold)

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
SunDay lanes before mutable work. Unavailable surfaces receive typed failure
classification and block only dependent work. Trivial Q&A bypasses this path.

Every substantial multi-step task performs `GLM_OFFLOAD_ASSESSMENT`. Useful,
independent, bounded work should be routed to an eligible GLM-5.3 lane when the
exact harness/provider/model/readiness/authorization/quota evidence and
ownership gates permit it. GPT-5.6 Sol remains integrator and continues useful
non-overlapping work rather than becoming a passive dispatcher.

A-FastTask stays a router/binder. Actual dispatch remains owned by existing
A-Conductor execution/provider/Zero-Relay backends and existing claims/leases.

Standing lane-context rule (recomposed 2026-09-17; replaces the 2026-09-16
fleet-bind-to-one-Active-Project rule): every mutable or review lane receives
an explicit execution-context binding — repo/worktree/branch/HEAD/claim — and
its executor process/context is verified against that binding. There is no
mutable global Active Project to bind to. A mismatch fails closed as
`CONTEXT_DRIFT`, blocks only that lane, and is reconciled before the lane
resumes. Sol assigns non-overlapping lane roles dynamically: bounded
implementation, GLM task-packet or dispatch assistance, deterministic
verification, adversarial read-only review, and recovery/reserve. Material GLM
results should receive independent challenge where capacity permits, but
default WIP allows only one independent read-only review lane at a time; other
lanes remain standby or work inside already-owned lanes. Sol reconciles all
evidence and retains final acceptance. Lane assignment never grants mutation
authority, and this rule never overrides WIP or
`1 MUTABLE HOTSPOT = 1 MUTATION OWNER`.

User throughput refinement (2026-09-16): substantial sessions should use a
`dispatch-first / harvest-later` pipeline. Sol decomposes independent READY work,
fills eligible GLM lanes early within WIP/provider/quota gates, continues its own
non-overlapping integration work without waiting for each report, and harvests
GLM results at material fan-in points. Before each material GLM dispatch, refresh
approved quota/readiness evidence. Live proof on 2026-09-16 showed the CoinTH
quota endpoint returns the full five-hour tuple with HTTP 200 when the approved
`COINTH_GLM_AUTH_TOKEN` secret is loaded from the user's authorized global
secret source and sent only as the `x-api-key` header. Never print/persist the
secret or copy the local secret-file path into tracked policy. Harness-native
`/goal`, `/plan`, `/init` or similar commands are allowed only when the exact
harness supports them and never replace durable authority. Optimize for accepted
throughput rather than token minimization, without bypassing quota/cost/ownership
limits.

## Verification / acceptance

Required before merge consideration:
1. exact scope equals this WO's six paths;
2. `git diff --check` and strict UTF-8 pass;
3. local relative links/references resolve where applicable;
4. added-line credential/secret-pattern scan passes;
5. ADR history remains visible and only the thin-facade facet is reopened;
6. phases do not reorder `ZRA-2 -> ZRA-3 -> ZRA-4` (the Runtime MVP and its
   isolation/recovery proof insert between ZRA-3 and ZRA-4 without reordering
   the ZRA chain);
7. no duplicated A-FastTask/global policy authority is introduced;
8. recomposition invariants hold: no mutable global Active Project authority;
   per-lane execution-context binding fails closed on `CONTEXT_DRIFT`; default
   WIP `3 mutable + 1 independent read-only review` and `1 MUTABLE HOTSPOT =
   1 MUTATION OWNER` are preserved; federation stays deferred until the
   isolation/recovery proof; A-FastTask remains router/binder only;
9. exact candidate SHA is reviewed independently by GLM-5.3 with P0/P1/P2=0,
   or confirmed findings are repaired and rereviewed;
10. exact-head hosted CI passes;
11. GPT-5.6 Sol performs final acceptance. The author lane does not self-merge.

`SAFE_TO_MUTATE_WO247_DOCS=YES` only in the isolated claimed worktree.
`SAFE_TO_MUTATE_SOURCE=NO`.
