# WO-P1-155 — Zero-Relay Accelerator

Date: 2026-09-04
Owner: unassigned until WO154/WO153 release and fresh repo/ownership gate
Status: QUEUED / P0 ACCELERATOR
Priority: P0 delivery accelerator
Repository: `A:\GitHub\A-Wiki-Conductor`
Roadmap: `docs/plans/2026-09-04-zero-relay-accelerator-roadmap.md`
Classification: `REUSE + WRAP + EXTEND`

## Goal

Make GPT/A-Conductor -> GLM task dispatch -> result ingestion -> verify/review -> bounded repair/continue operate without the user copying prompts or results between programs.

## Why before ODP

This capability reduces the cost of implementing every later roadmap node. It is explicitly user-prioritized ahead of broad ODP continuation.

## Existing authority to reuse

AHA-4..6, WO118, WO122, WO123, provider configuration/admission, worker leasing, supervised Claude Code harness/backend, and stable task/result destinations.

Do not create a second provider registry, scheduler, task authority, retry system, or review lifecycle.

## First implementation claim

`ZRA-0` only after:
1. WO154 fast-execution policy is accepted/merged;
2. WO153 releases shared SSoT hotspots;
3. fresh `origin/main`, worktree/branch/HEAD/dirty/claim/overlap gate passes;
4. current live installed/runtime version is reconciled against source;
5. no credential contents are required for copied/sacrificial DB migration proof.

## Initial mutable scope

To be pinned by the ZRA-0 claim after current-main archaeology. Do not infer a broad source scope from this planning WO.

## Forbidden

- no live Control Center DB mutation during ZRA-0 proof;
- no ZCode config search/edit;
- no UI-click automation as a substitute for a supported provider invocation path;
- no secret/API key/token logging or source control;
- no automatic provider launch until readiness/auth/quota/policy/admission gates are satisfied;
- no blind retry when execution outcome is ambiguous;
- no ODP scope stealing.

## Acceptance frontier

The accelerator is useful after ZRA-1 proves one real authorized no-relay task, but the P0 slice is not complete until ZRA-3 proves automatic result ingestion, bounded repair and continuation with no human relay.
