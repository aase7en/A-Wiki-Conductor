# WO-P1-155 — Zero-Relay Accelerator

Date: 2026-09-04
Owner: GPT-5.6 Sol integrator (gate authority); GLM preview/repair evidence exists (see First implementation claim status truth below)
Status: PREVIEW / REVIEW-REPAIR EVIDENCE EXISTS — NOT ACCEPTED (ZRA-0 prerequisite migration mechanism/evidence pre-proven, but formal ZRA-0 node acceptance remains PENDING after PR208 accepted/merged; ZRA-1 full production acceptance PENDING)
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

Historical claim gate (kept as chronology): `ZRA-0` required (1) WO154 acceptance, (2) WO153 hotspot release, (3) fresh repo/ownership gate, (4) installed/runtime reconciliation, (5) no credential contents for sacrificial-DB proof.

**Status truth (review repair 2026-09-04):** condition (2) is satisfied (WO153 merged+RELEASED in `68079e3`); condition (1) remains open — PR #208 is in REVIEW_REPAIR, and tracked production acceptance stays gated on PR208 accepted/merged; preparatory preview work does not bypass that dependency. **ZRA-0 prerequisite migration mechanism/evidence is pre-proven** on sacrificial/valid-registry DBs with live DB untouched, but the formal ZRA-0 node is **NOT yet accepted/closed** under Issue #212 and must be reconciled against the post-PR208 main before closure. **ZRA-1 = preview/transport-harness evidence exists** (one-shot app-server session proof); FULL authorized/admitted production ZRA-1 acceptance remains PENDING, with unresolved review blockers (session-event identity, process-reap evidence, task-packet TOCTOU, streaming-output bounds, overclaimed ZRA-1/ZRA-3 authority) — `653eba9` is NOT accepted. **ZRA-2** only to the level actually proven. **ZRA-3** and **ZRA-4** production acceptance remain PENDING.

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

The accelerator is useful after ZRA-1 proves one real authorized no-relay task, but broad ODP resumes only after ZRA-4 proves automatic result ingestion, bounded repair, continuation, and bounded parallel lane isolation with no human relay. ZRA-5 remains the later ODP integration seam.
