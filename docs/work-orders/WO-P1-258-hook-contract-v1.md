# WO-P1-258 — Hook Contract v1 (HOOK-0)

Status: IN_PROGRESS
Issue: #368
Risk: R3 — cross-surface event/protocol contract feeding the Hook/STM/Monitor stack
Task topology: CONTROL_PLANE_ONLY

## Binding

Authority repo: `A:\GitHub\A-Wiki-Conductor`

Authority worktree:
`A:\GitHub\_worktrees\A-Wiki-Conductor-hook-0`

Branch:
`feat/wo-p1-258-hook-contract-v1`

Base:
`A-Wiki-Conductor origin/main@fe1edad5dcce8b399fac1923a2c49e4f75c1b646`
(merge of PR #366 accepting the WO-P1-257 roadmap)

Owner: SunDay-Worker 2 / GLM-5.3 MAX under GPT-5.6 Sol integration.

Planning authority:
`docs/plans/2026-09-19-a-faster-hook-stm-observability-roadmap.md`
(P1 — HOOK-0 Contract + threat/failure model)

## Goal

Freeze the versioned Hook Contract v1 as contract artifacts only:

- normative contract document;
- machine-readable JSON Schema (Draft 2020-12);
- deterministic schema/invalid/oversized/redaction tests;
- this Work Order.

## Classification (reuse-before-build)

- REUSE: `src/a_conductor/control_events.py` event-id and typed-error
  precedent; existing `schemas/*.schema.json` Draft 2020-12 conventions;
  existing contract-test patterns in `tests/test_provider_harness_contract.py`.
- WRAP: harness/substrate adapters map native events into the normalized
  envelope without changing task semantics.
- EXTEND: later HOOK-1/HOOK-2 phases extend existing control/lifecycle event
  seams; this WO performs no runtime extension.
- REPLACE/NEW: none. No new task store, scheduler, claim/lease authority,
  review/completion system, or second control plane.

## Allowed authority-repo scope (exact)

- NEW `docs/contracts/hook-contract-v1.md`
- NEW `docs/contracts/hook-contract-v1.schema.json`
- NEW `tests/test_hook_contract_schema.py`
- NEW `docs/work-orders/WO-P1-258-hook-contract-v1.md`

Everything else is READ-ONLY.

## Forbidden

- Any `src/a_conductor/` mutation; any runtime, hook bus, STM, monitor, or UI
  implementation (contract-only boundary).
- Modification of PROJECT-PLAN, A-FastTask/A-Faster skills, CURRENT-WORK,
  handoff, COLLAB, other Work Orders, or SRM.
- Reset/clean/stash/switch/rebase/merge/force-push; push/merge/self-accept.
- Secrets inspection, environment dumps, MCP/web use, new authority/state
  stores, new dependencies or package changes.
- Git pre/post-commit hooks as orchestration authority.
- Exactly-once delivery promises (at-least-once + idempotent consumers +
  bounded dedupe only).

## Contract-only / no-runtime boundary

This WO delivers documents, a JSON Schema, and tests. It does not implement
adapters, a bus, STM, monitor endpoints, or any validation in production
runtime. Runtime validation seam decisions belong to HOOK-1 and later Work
Orders extending `control_events.py`-class seams.

## Invariants carried into the contract

- A-Sunday Conductor remains sole task/claim/routing/retry/review/acceptance/
  command authority; A-FastTask/A-Faster remain router/binder/profile; SRM
  remains execution substrate.
- Hook Bus, STM, Monitor are never SSoT; actual Git/GitHub/runtime/durable
  evidence outranks hook/STM projections.
- First monitor milestone is read-only.
- Security/authority GUARD hooks fail closed; ambiguous GUARD classification
  defaults fail closed.
- STM starts as derived in-memory TTL projection only.
- No raw secrets, credentials, cookies, share URLs, full prompts, or
  secret-bearing command lines in normal hook payloads.
- Browser-to-localhost requires origin validation + local token.
- Adapter capabilities are version-bound/discoverable.

## Replay safety

Artifacts are additive docs/schema/tests on a fresh branch from the accepted
base. Re-running the packet from the same base reproduces the same four-path
diff; tests are deterministic (no network, no MCP, no clocks beyond fixed
fixtures). A re-driven candidate replaces the branch tip only through normal
integrator flow; no history rewrite.

## Acceptance

1. Work Order records exact binding/base/branch/scope, R3 risk, forbidden
   scope, contract-only boundary, replay safety, and this acceptance list.
2. `docs/contracts/hook-contract-v1.md` gives normative MUST/SHOULD/MAY for a
   small required core plus bounded optional context groups and decides:
   globally unique `event_id`; source-local dedupe identity + bounded replay
   window; positive ordering (per-source sequence authoritative when present,
   producer order preserved per source, never global total order from wall
   clock, deterministic monitor merge/tie-break, correlation/causation as
   links not time order); event classes OBSERVE/ADVISORY/GUARD/COMMAND with
   class-scoped failure behavior; schema/version compatibility with typed
   reject/degrade; payload/string/array bounds without performance SLOs;
   privacy/redaction classification and shared fake-secret corpus; localhost
   browser origin+token boundary; backpressure/degradation; evidence
   pointers/digests not authority copies; STM read-model only; adapter
   capability/version discovery.
3. `docs/contracts/hook-contract-v1.schema.json` encodes core fields, enums,
   patterns, limits, conditional GUARD requirements, unknown-field policy,
   and security-invalid envelope rejection; Draft 2020-12 valid.
4. `tests/test_hook_contract_schema.py` covers all 15 packet cases, is
   table-driven where practical, and runs green offline.
5. Focused test + smallest relevant existing regressions pass
   (`test_control_events.py`, `test_provider_harness_contract.py`).
6. `git diff --check` clean; exact-scope check from BASE_SHA shows only the
   four allowed paths; UTF-8/JSON parse clean; fake-pattern secret scan clean.
7. Freeze: single commit on the branch records the exact candidate SHA;
   independent exact-SHA review is the required next step. No push/merge/
   self-accept.

## Checkpoint

- 2026-09-19: lane opened; Goals 0-1 verified (state matches binding; reuse
  inventory recorded above).
- 2026-09-19: contract doc, JSON Schema, and deterministic tests authored.
  Focused suite + `test_control_events.py` + `test_provider_harness_contract.py`
  green (93 passed). `git diff --check` clean; UTF-8/JSON parse clean;
  fake-pattern secret scan clean (only FAKE-marked corpus items).
- 2026-09-19: freeze commit on this branch; exact SHA recorded in the final
  packet response. Awaiting independent exact-SHA review. No push/merge/
  self-accept.
