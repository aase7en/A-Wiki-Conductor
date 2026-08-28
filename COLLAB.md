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
| `WO-P1-100` / AHA-4 supervised durable backend assembly | GPT-5.6 Sol integrator | 2026-08-28 | Isolated `A-Wiki-Conductor-aha4-assembly`: per-job durable Claude backend -> accepted supervised Claude runner assembly, focused tests, SSoT. No connector-stability, installer, North-Star, live-provider, worker-lease mutation. |
| PR #108 / installer target ownership | release/installer lane | 2026-08-27 | `fix/v070-installer-target-ownership`; destructive installer safety scope remains separately owned. |
| North Star integration | GPT integrator + bounded workers | 2026-08-27 | `feat/north-star-runtime-sunday-family`; runtime/execution integration lineage, preserved for later reconciliation. |

### Recently closed / released claims

- `WO-P1-098` / PR #124 supervised Claude runner: final head `25cc69478f73a8cfc154de721ae1c48bb8db7fd2` passed exact-head Windows/Ubuntu/macOS CI run `33176757259` including Windows packaging/frozen/Portable smoke and merged as `e933a53c3c32bf0f8126f1602c913c08765d9a8a`; claim released to WO-P1-100.
- `WO-P1-097` / PR #122 connector CR-1 + CR-3: tunnel-client >=0.0.12 floor + forensic launcher hardening merged as `ceee9bb7aa361aef6d0ecfc210c25b564578d552`; WO-P1-096 still blocks v0.7.0 on CR-2/CR-4 + isolated E2E/soak.
- `WO-P1-095` / PR #121 Claude durable backend: exact head `69fffe7aba40f74ac23ea7c04f9b875c76d7f030` passed GPT re-audit + 3-OS CI run `33164201872` and merged as `0e9b93a7c08cb7b284f2234af61ec6a96b16a2ea`.
- `WO-P1-094` / PR #119 durable graph-dispatch core: final head `70e80c1d958b08137bf5c70a44cca369ac4aadac` passed Windows/Ubuntu/macOS CI run `33159443742` including Windows packaging/frozen smoke and merged as `5cc417c92450eba796fa9af1cf3da037663b1eea`.
- PR #104 / GE-6 deterministic scheduler: exact head `694b8dee053e48d805596b527525cada875848a4` passed GPT re-audit + 3-OS CI and merged as `023c7b65026b0ff536cd1d802d6010e381a4447a`; worktree/local/remote branch removed after ancestry proof.
- `WO-P1-092` / PR #117 harness phase transition: merged as `8db32269f3b1e55a7a551a5a98f6c93b8a30158d`; claim released to AHA-4.
- `WO-P1-091` / PR #116 AHA-3 Claude Code harness adapter: merged as `ab28dc7` on 2026-08-28 after exact-head Windows/Ubuntu/macOS CI green; clean worktree/local/remote branch removed after ancestry verification.
- `WO-P1-090` / PR #114 AHA-2 provider configuration + observation: merged as `ca4cd98` on 2026-08-28 after exact-head Windows/Ubuntu/macOS CI green; clean worktree/local/remote branch removed after ancestry verification.
- `WO-P1-087` / PR #111 priority plan: merged as `457f974` on 2026-08-28; worktree/branch removed after ancestry verification.
- `WO-P1-088` / PR #112 AHA-1 provider/harness contracts: merged as `c3ca84c` on 2026-08-28; AHA-2 consumes this accepted contract.
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
