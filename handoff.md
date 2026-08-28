# HANDOFF — A-Sunday Conductor

Last updated: 2026-08-28 — WO-P1-090 / AHA-2

## Current Objective

Eliminate manual prompt copying by building the provider-neutral Sunday Family multi-model harness. Current slice is secure non-secret provider configuration plus observed health/quota evidence.

## Current Task

`WO-P1-090` — implement AHA-2 provider configuration, endpoint validation, opaque credential references, same-control-DB persistence, and fake/injected observation normalization.

## Repository State

- Repository: `aase7en/A-Wiki-Conductor`
- Worktree: `A:\GitHub\A-Wiki-Conductor-provider-config`
- Branch: `feat/wo-p1-090-provider-config-observation`
- Base/HEAD at claim: `origin/main@c3ca84c81d901ae844ee40780619a41b46307049`
- Working tree clean before AHA-2 claim.
- Shared root remains protected/read-only.

## Accepted Harness Baseline

- PR #110 C0 vocabulary merged `6487cb2`.
- PR #111 priority/SSoT plan merged `457f974`.
- PR #112 AHA-1 provider/harness contracts merged `c3ca84c`.
- PR #113 Windows CI isolation repair merged `e2de499`; exact-main CI passed Windows/Ubuntu/macOS including packaging/frozen smoke.

First intended provider lane remains:

`Conductor -> Claude Code CLI / Anthropic-style harness -> configurable Anthropic-compatible provider -> GLM-5.3`

GLM is replaceable provider/model metadata. `CAPABLE != AUTHORIZED`; `CONFIGURED != READY`; provider `DONE` remains evidence only.

## Protected Parallel Work

- PR #104 / `feat/ge-6-scheduler`: GE-6 owner lane (GLM 5.3 MAX); reconciled with `origin/main @ ca4cd98` via clean merge `d377dbe` (no rebase/reset/force); full graph suite 92 passed locally on Windows on the merged state; awaiting PR CI + review. No scheduler mutation by non-Graph lanes.
- PR #108 / installer target ownership: separate release owner; no installer mutation.
- `feat/north-star-runtime-sunday-family`: unique integration lineage; reconcile, do not overwrite.
- Unknown dirty/detached audit lanes remain protected.

## Local Claude Harness Evidence (read-only)

- Claude Code installed: `2.1.178`.
- Non-interactive `-p` plus JSON/stream-json output is available.
- Current Claude user settings point to a loopback gateway and an `apiKeyHelper`; no credential value was read or copied.
- Gateway was not listening when observed; this is not yet a readiness signal.
- No live Claude/provider call is authorized in AHA-2.

## Next Safe Action

1. write AHA-2 failing tests;
2. implement only the bounded configuration/store/observation seams;
3. run focused + contract regressions, compileall, diff/secret/scope checks;
4. checkpoint, push, Draft PR, require CI;
5. start AHA-3 only after AHA-2 merges.
