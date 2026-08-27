# COLLAB — A-Conductor Multi-Agent Coordination

> Binding coordination standard: A-Wiki `docs/protocols/cross-agent-work-orders.md`.
> Every ChatGPT/GPT Work/A-Worker/Serena/Codex/external agent must read this file before non-trivial work.

## Lanes

| Lane | Theme | Owned scope | Must not touch without a separate claim |
|---|---|---|---|
| `WO-P1-022` | ChatGPT / Sunday-Conducter | 2026-08-20 | `src/a_conductor/tunnel_boundaries.py`, `src/a_conductor/owned_process.py`, `src/a_conductor/__init__.py`, `tests/test_tunnel_boundaries.py`, `tests/test_owned_process.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-022-tunnel-preflight-references.md` |
| ARCH | architecture, contracts, ADRs, plans | `PROJECT-PLAN.md`, `docs/contracts/**`, `schemas/**`, architecture ADRs | runtime/UI implementation |
| RUNTIME | worker/runtime/process/Serena adapters | future runtime/process source + runtime tests | UI and architecture hotspot files |
| VERIFY | deterministic verification, evidence, recovery tests | future verifier/test/evidence tooling | product UI and unrelated runtime internals |
| UI | desktop control center | future UI source/assets | runtime/process internals |
| DOCS | continuity, handoff, operator docs | `AGENTS.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/**`, operator docs | architecture decisions unless explicitly claimed |

A single work order may claim multiple lanes only when the scope is explicit and small. Prefer additive/new files over shared-file edits.

## Hotspot files

These are shared coordination surfaces and must be changed by only one active work order at a time:

- `PROJECT-PLAN.md`
- `AGENTS.md`
- `COLLAB.md`
- `CURRENT-WORK.md`
- `handoff.md`
- future dependency manifests / lockfiles
- future central worker/project registries
- future task-state transition tables
- future shared schema index/version registry

## In-progress claims

| Chunk/WO | Agent | Claimed | Scope (files) |
|---|---|---|---|
| `WO-P1-087` / Sunday Family Agent Harness accelerator | GPT-5.6 Sol via RDC | 2026-08-28 | Plan/SSoT only in isolated `A-Wiki-Conductor-agent-harness`: `PROJECT-PLAN.md`, `DESIGN.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, WO-P1-087 + accelerator plan. No production code/tests. |
| PR #104 / GE-6 | GLM 5.3 lane | 2026-08-26 | `feat/ge-6-scheduler` worktree/branch; scheduler/Graph scope remains separately owned. |
| PR #108 / installer target ownership | release/installer lane | 2026-08-27 | `fix/v070-installer-target-ownership`; destructive installer safety scope remains separately owned. |
| North Star integration | GPT integrator + bounded workers | 2026-08-27 | `feat/north-star-runtime-sunday-family`; runtime/execution integration lineage, preserved for later reconciliation. |

### Recently closed / released claims

- `WO-P1-086` / PR #110 capability vocabulary C0: merged as `6487cb2` on 2026-08-28; clean feature worktree/local/remote branch removed after ancestry verification; accepted contract remains on `main`.
- `WO-P1-063`: implementation/release complete; v0.6.0 published from `c870525`; future work leaves this WO.
- `WO-GE-001` decision fan-in: D1-D5 accepted via PR #86; decision claim released. GE-1a is the next implementation slice and must be claimed by its actual implementer before mutation.
- `docs/repo-health-sync`: merged/closed before release integration; no live claim remains.
- `fix/brain-restart-note` / PR #82: merged/closed; no live claim remains.
- `fix/gpu-context-ui-repaint`: superseded by corrective release PR #87; no live claim remains.

> Git remote `origin` = `https://github.com/aase7en/A-Wiki-Conductor.git` (public since 2026-08-22 by explicit user decision — originally created private 2026-08-20). Pull/reconcile before commit/push; record branch/HEAD in checkpoints.

## Rules

1. **Claim before work.** A chunk must have a work order and claim before touching shared scope.
2. Before significant work, run the **A-Wiki reuse-before-build gate** in `AGENTS.md`/`PROJECT-PLAN.md`; inspect GitHub/work orders/live claims when duplicate-work risk exists.
3. Once Git is initialized, pull/reconcile before commit/push and record branch/HEAD in checkpoints.
4. Never edit a file owned by another live claim.
5. Never use destructive Git (`reset --hard`, `checkout -- .`, `clean`) on shared user work; never delete another worktree/branch.
6. Every chunk uses `docs/work-orders/<id>.md`; append a checkpoint whenever stopping, delegating, or changing execution surface.
7. Scope belongs to the work order, not to a vendor/model. Another agent may resume the same WO after verifying state.
8. Additive-first: prefer new bounded files; shared hotspots require explicit ownership.

## Pause → Resume

Before pausing or delegating:

1. record actual state/evidence;
2. update active WO checkpoint;
3. update `CURRENT-WORK.md`;
4. update `handoff.md`;
5. release/transfer claim when the coordination backend supports it.

Resume sequence:

`AGENTS.md -> PROJECT-PLAN.md -> COLLAB.md -> CURRENT-WORK.md -> handoff.md -> active work order -> actual repository/runtime reconciliation`

Never blindly repeat a mutation merely because the previous agent/session disappeared.
