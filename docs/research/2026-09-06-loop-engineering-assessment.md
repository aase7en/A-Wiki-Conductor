# loop-engineering Adoption Assessment — 2026-09-06

Upstream: `cobusgreyling/loop-engineering`
Pinned upstream main: `e1c9d5f5e23655b65d04c5617aff77ab3ad58c16`
License: MIT — Copyright (c) 2026 Cobus Greyling and contributors

Purpose: identify what A-Sunday Conductor should reuse, adapt, extend, or
reject without creating duplicate control-plane authorities.

## FACT — upstream strengths inspected

The pinned upstream exposes dedicated tools for loop context, cost, safety
gates, readiness audit, worktree isolation, swarm execution, metrics, sync,
MCP, and pattern initialization.

`loop-context` uses a deterministic run ledger and circuit breaker. It
tracks iteration count, repeated identical failure, consecutive no-progress,
token spend, and optional daily budget. It can prune/inject compact context
without an LLM call.

`loop-gate` separates static proposed-change policy from run-history policy.
Its basic checks are path denylist, changed-file count, and an auto-merge
allowlist.

`loop-audit` scores Loop Readiness from 0–100 and maps capability to L0–L3.
Signals include durable state, verifier separation, safety, worktree
isolation, cost observability, no-progress detection, human escalation, and
evidence of actual loop activity.

`loop-cost` models no-op, report, action, realistic, and caching scenarios.
It also applies orchestration multipliers such as maker-checker and parallel
fan-out.

The upstream pattern registry carries goal, cadence, risk, phases, human
gates, state, readiness mode, and token/cost metadata. Example patterns
include PR Babysitter, CI Sweeper, Daily Triage, Dependency Sweeper,
Post-Merge Cleanup, Changelog Drafter, Issue Triage, and Thin Loop.

## FACT — A-Conductor already has stronger overlapping authorities

A-Conductor already has:
- versioned Task Contract with per-task budget and retry policy;
- durable job state, attempts, graph dispatch, scheduler, worker leases;
- provider readiness/authorization/admission and parallel READY execution;
- explicit repository/worktree/identity gates and fail-closed recovery;
- independent review/repair and durable result/evidence contracts;
- A-Wiki reuse-before-build rules for claims, handoff, memory and procedures.

Therefore copying upstream scheduler, worktree, swarm, state files, or MCP
authority would create a competing system rather than accelerate this one.

## Decision matrix

| Upstream capability | Decision | A-Conductor treatment |
|---|---|---|
| pattern registry schema | ADAPT NOW | provider-neutral `Loop Recipe` schema layered above Task Contract |
| loop-context breaker | ADAPT NOW | dependency-free Python `loop_guard` pure decision primitive |
| loop-cost | EXTEND | feed existing task/provider cost + quota authorities; no second ledger |
| loop-audit/readiness-core | EXTEND | add Loop Readiness to A-Doctor |
| loop-gate | EXTEND | machine-enforce through existing repository/task/provider gates |

| named loop patterns | ADAPT | convert proven patterns into A-Wiki/A-Conductor recipes after recipe runtime exists |
| loop-worktree | REUSE EXISTING | keep A-Conductor worktree/lease/ownership controls |
| loop-swarm | REUSE EXISTING | keep dependency-graph + bounded parallel READY execution |
| loop state files | REJECT DUPLICATION | existing durable job/task/SSoT remains authority |
| Node/TypeScript runtime | REJECT AS DEPENDENCY | avoid a second runtime stack for core orchestration |

## INFERENCE

The highest-value missing primitive is not another scheduler. It is a
deterministic policy seam between an attempt result and permission to run the
next attempt. That seam lets existing ZRA/graph/job authorities enforce
stagnation and aggregate resource caps without interpreting prose.

The second high-value gap is reusable loop metadata. A Loop Recipe should
describe trigger, phases, autonomy ceiling, assurance tier, human gates,
aggregate loop limits, and references to existing Task Contract/state
authorities. It must not own task execution or persistence semantics itself.

## RECOMMENDATION

Adopt upstream ideas in layers:
1. pure guard + schema + license/credit;
2. integrate guard into the accepted continuation seam after current ZRA
   ownership releases it;
3. add A0–A3 autonomy policy and readiness scoring;
4. materialize a small recipe catalog;
5. add cost/telemetry and scheduled/event triggers;
6. promote to unattended mode only with observed evidence, not config alone.
