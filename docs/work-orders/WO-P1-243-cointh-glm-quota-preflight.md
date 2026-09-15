# WO-P1-243 — CoinTH GLM quota preflight runbook

Status: ACTIVE / DOCS-ONLY / R1
Owner: GPT-5.6 Sol integrator
Base: `origin/main@82d3aabe352d071a676db5bb6b9cbfeb5dcda05b`
Branch: `docs/wo243-cointh-glm-quota`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo243-glm-quota`

## Purpose
Record the user-provided CoinTH GLM quota-check method as durable project guidance so GLM availability can be checked without relying on chat memory or wasteful model probes.

## Source classification
- Endpoint, header, returned field names, and the statement that this quota check does not consume GLM quota are **USER_PROVIDED** on 2026-09-15.
- No live credentialed call is required for this docs task.
- Runtime use remains `LIVE_PROOF_PENDING` until an authorized secret resolver performs a redacted live preflight.

## Claimed scope
- `docs/work-orders/WO-P1-243-cointh-glm-quota-preflight.md`
- `docs/runbooks/cointh-glm-quota.md`

Forbidden scope: source/runtime code, secrets, provider credentials, existing shared routing docs, scheduler/router/store/lifecycle authority.

## Mutation gate
Target project/repo/worktree/branch/HEAD are proven above; worktree was clean at claim time; scope is new-file-only and non-overlapping. `SAFE_TO_MUTATE_DOCS=YES`.