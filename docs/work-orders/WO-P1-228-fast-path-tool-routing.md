# WO-P1-228 — Fast-path tool routing governance

Status: PREPARED / DRAFT PR
Risk: R2 — binding workflow/tool-routing policy, docs-only
Owner: GPT integrator
Repository: `aase7en/A-Wiki-Conductor`
Base: `main@251df211afc1ee5452f3652675d7a2f38c526876`
Branch: `docs/wo-p1-228-fast-path-tool-routing`

## Goal

Reduce A-Sunday Conductor delivery latency while preserving durable authority, mutation safety, exact-SHA evidence, independent review and no-shadow-SSoT rules.

This WO captures the user's 2026-09-12 request:

- keep ChatGPT Project Instructions compact rather than appending more large policy;
- explicitly preserve the core surfaces that let ordinary GPT Chat operate on the real project:
  - `SunDay-Worker 1`..`SunDay-Worker 5`;
  - `Remote Desktop Commander`;
  - `GitHub`;
- move detailed plugin/process routing into repository markdown/YAML;
- improve speed by using coherent implementation batches, parallel independent review and CI fan-out/fan-in;
- avoid repeated loops that delay accepted outcomes.

## Scope

Allowed:

- create `docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md`;
- update `PROJECT-GRAPH.yaml` so tool/session/process-routing tasks load that file on demand;
- keep the work docs-only;
- open a draft PR for independent review.

Forbidden:

- production source or tests;
- `CURRENT-WORK.md`, `handoff.md`, `COLLAB.md` unless a later explicit reconciliation lane owns those hotspots;
- changing ZRA/WO214/WO226/WO227 authority;
- creating another task/claim/lease/scheduler/review authority;
- changing secrets, provider credentials, runtime state, or live devices.

## Non-overlap check

Known open work as observed during bootstrap includes ZRA/WO226/WO227 and other roadmap PRs. This WO avoids their source/runtime scopes and does not modify active ZRA work-order files.

`CURRENT-WORK.md` appears stale versus actual GitHub `main` and was intentionally not rewritten in this lane.

## Acceptance criteria

- Project Instructions replacement is compact and explicitly names SunDay Worker 1-5, RDC and GitHub.
- Repository policy gains a routed markdown node for tool and fast-path routing.
- The new routing doc explains core vs conditional tools.
- The workflow distinguishes normal fast path from high-risk R3 path.
- Anti-loop/anti-latency rules are recorded.
- No shadow SSoT is introduced.
- Remote diff is docs-only and exact-SHA reviewable.

## Verification

- YAML is parseable.
- New doc has no obvious unresolved placeholders.
- Changed paths are limited to:
  - `PROJECT-GRAPH.yaml`
  - `docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md`
  - `docs/work-orders/WO-P1-228-fast-path-tool-routing.md`
- No secrets or credentials are included.
- Draft PR remains unmerged until independent review/CI as policy requires.

## Checkpoint

Prepared via GitHub remote branch from exact `main@251df211afc1ee5452f3652675d7a2f38c526876`.

Next safe action: independent exact-SHA docs/policy review of the draft PR, then merge only if review/CI requirements are satisfied.
