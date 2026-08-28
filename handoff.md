# HANDOFF — A-Sunday Conductor

Last updated: 2026-08-28 — WO-P1-091 / AHA-3

## Current Objective

Eliminate manual prompt copying by building the provider-neutral Sunday Family multi-model harness. Current slice is the bounded Claude Code harness adapter with an injected fake runner only.

## Current Task

`WO-P1-091` — translate the accepted AHA-1 harness dispatch + AHA-2 readiness evidence into a fixed non-interactive, read-only Claude Code invocation with explicit task packet, bounded timeout/output, environment-reference allowlist, and redacted structured evidence.

## Repository State

- Repository: `aase7en/A-Wiki-Conductor`
- Worktree: `A:\GitHub\A-Wiki-Conductor-claude-harness`
- Branch: `feat/wo-p1-091-claude-code-harness`
- Base at claim: `origin/main@ca4cd986c9d3ad0b9af833350f067ff9056df653`.
- Current accepted main/worktree HEAD after roadmap PR #115: `685029d8e367955ba7fb44a3d5449ddf75ca01eb`.
- Local AHA-3 source/tests are modified/untracked until the next bounded commit.
- Shared root remains protected/read-only.

## Accepted Harness Baseline

- PR #110 C0 vocabulary merged `6487cb2`.
- PR #111 priority/SSoT plan merged `457f974`.
- PR #112 AHA-1 contracts merged `c3ca84c`.
- PR #114 AHA-2 provider config/observation merged `ca4cd98` after Windows/Ubuntu/macOS exact-head CI green.
- PR #115 roadmap/worker fallback docs merged `685029d`; Windows hosted Tk `0x80000003` rerun passed, Ubuntu/macOS passed.

## Local Claude Interface Evidence

Read-only CLI inspection on this machine:
- Claude Code `2.1.178`;
- `-p/--print`, JSON output, no-session-persistence, safe mode, explicit permission/tools/model/effort controls;
- `--system-prompt-file <file>` is accepted by the installed CLI parser;
- current user config references a loopback gateway/apiKeyHelper, but no credential value was read/copied and no live provider call is authorized here.

## Protected Parallel Work

- PR #104 / `feat/ge-6-scheduler`: GE-6 owner lane (GLM 5.3 MAX); re-reconciled with `origin/main @ ab28dc7` (safe merge, no rebase/reset/force); fixing the four ADR GE-0006 review blockers this round; no scheduler mutation by non-Graph lanes.
- PR #108 installer safety: separate release owner; no installer mutation.
- `feat/north-star-runtime-sunday-family`: unique integration lineage; read-only reconciliation only.
- dirty/detached audit lanes remain protected.

## AHA-3 Safety Boundary

- fake/injected runner only; no subprocess/network client in production code;
- `READ_ONLY` only; `PROJECT_MUTATION` fails closed until AHA-4 durable gates;
- task packet file is explicit, worktree-contained, size/SHA verified;
- environment state carries only endpoint/credential references, never values;
- runner output must be bounded, JSON-structured, and redacted before evidence returns;
- provider/harness success is evidence, never task completion authority.

## Roadmap decision added 2026-08-28

User requested worker auto-fallback so new chats stop competing for a hard-coded SunDay-Worker. Roadmap now inserts AHA-4A atomic worker leases + eligibility/fallback and AHA-4B heartbeat/stale-owner recovery before broad parallel execution. README exposes released `v0.6.0`, development `0.7.0`, and the AHA checklist.

Repository benchmark evidence for GLM-5.3: its owned GE-6 branch/PR #104 remains a strong bounded implementation lane; independent graph recheck = `83 passed in 1.76s`, while the PR is currently non-mergeable against newer main and needs owner-led reconciliation.

## Verification Checkpoint

- AHA-3/AHA-2/AHA-1/domain: `52 passed in 0.87s`.
- Provider-store + supervised-runner regression: `9 passed in 3.39s`.
- compileall + `git diff --check`: PASS.
- Added a regression proving secret-like JSON keys are redacted before evidence return.

## Next Safe Action

1. commit/push only AHA-3 source/tests + continuity checkpoint;
2. open Draft AHA-3 PR and audit the remote diff;
3. require exact-head Windows/Ubuntu/macOS CI, repairing only evidence-backed failures;
4. merge/cleanup when green;
5. live read-only provider smoke remains separately gated on safe configured credentials/health;
6. AHA-4 remains blocked on accepted GE scheduler/durable-dispatch integration.
