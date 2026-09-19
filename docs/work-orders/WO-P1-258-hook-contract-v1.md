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
   globally unique `event_id`; dedupe identity = explicit `dedupe_key` when
   deliberately supplied, else the global `event_id` (never `source` +
   `sequence`; distinct `event_id`s are never dropped for a source/sequence
   collision) inside a bounded replay window; ordering stream domain
   `(source, device_id, observed transport/adapter session)` — never bare
   source, no project-wide epoch store — with per-stream sequence authority
   (sequence authoritative among buffered events when present, producer
   order preserved per stream, never global total order from wall clock,
   deterministic monitor merge/tie-break, append-only emitted history with
   late-arrival inversion/gap surfacing and no waiting for unseen events,
   correlation/causation as links not time order); event classes
   OBSERVE/ADVISORY/GUARD/COMMAND with class-scoped failure behavior and
   GUARD fail-closed enforcement pinned to invocation/gate authority,
   never eventual stream delivery; schema/version compatibility with typed
   reject/degrade; payload/string/array bounds without performance SLOs;
   privacy/redaction classification and shared fake-secret corpus; localhost
   browser origin+token boundary; backpressure/degradation; evidence
   pointers/digests not authority copies; STM read-model only; adapter
   capability/version discovery with the adapter payload constrained to
   the capability-discovery event.
3. `docs/contracts/hook-contract-v1.schema.json` encodes core fields, enums,
   patterns, limits, conditional GUARD requirements, the adapter
   capability-payload constraint on the `transport.adapter_capabilities`
   OBSERVE event, unknown-field policy, and security-invalid envelope
   rejection; Draft 2020-12 valid.
4. `tests/test_hook_contract_schema.py` covers all 15 packet cases plus the
   review-001 repair regressions (dedupe identity proofs, stream-domain
   ordering, late-arrival append-only history, `event_type` semantic pin,
   adapter capability constraint), is table-driven where practical, and
   runs green offline.
5. Focused test + smallest relevant existing regressions pass
   (`test_control_events.py`, `test_provider_harness_contract.py`).
6. `git diff --check` clean; exact-scope check from BASE_SHA shows only the
   four allowed paths; UTF-8/JSON parse clean; fake-pattern secret scan clean.
7. Candidate re-pin: the review candidate is the exact branch head after
   the recorded freeze → §5 ordering repair → review-001 repair history
   (see Checkpoint); each bounded repair re-pins the exact candidate SHA
   without history rewrite. Independent exact-SHA R3 review is the
   required next step after each re-pin. No merge/self-accept; a repair
   lane pushes only its own repair branch.

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
- 2026-09-19: integrator found a §5 contract contradiction before
  independent review: source-local `sequence` authority conflicted with a
  timestamp-first global monitor sort that could place sequence N+1 before
  N for one source under inverted/skewed `occurred_at`. Bounded repair per
  integrator task packet: §5 rewritten to per-source ordered queues plus a
  stable k-way head-only merge ranked by `(occurred_at, source, event_id)`
  among eligible heads; conservative gap/mixed-availability rules (no
  invented events, no sentinel `sequence`, observed arrival slots kept);
  envelope/schema fields unchanged; 3 focused ordering-consistency tests
  added (96 passed; all 93 original tests preserved). The repair commit is
  the new review candidate SHA. Still no push/merge/self-accept.
- 2026-09-19: independent review 001 returned P0/P2/P3 findings; repair
  lane `fix/wo-p1-258-hook-contract-review001` opened from dispatch HEAD
  f20fff0 (claim WO-P1-258-HOOK0-REVIEW001-REPAIR-001, R3,
  CONTROL_PLANE_ONLY). Repairs, RED-first: P0 — duplicate identity is now
  explicit `dedupe_key` when deliberately supplied else the globally
  unique `event_id`; `source` + `sequence` fallback removed (distinct
  `event_id`s survive a source/sequence collision, including across
  devices); ordering stream domain pinned to (source, device_id, observed
  transport/adapter session) — never bare source; a new observed session
  may restart sequence; no project-wide epoch store. P2 — sequence
  constrains only currently buffered events; emitted history is
  append-only; a late lower sequence appends at observed arrival position
  with inversion/gap metadata; deterministic late-arrival regression
  added. P3 — §3.2 cross-references fixed (compatibility matrix §7.2,
  dedupe §4); `event_type` = `domain.action` semantic mismatch pinned in
  a deterministic contract test; schema `adapter` payload constrained to
  the `transport.adapter_capabilities` OBSERVE event; GUARD FAIL_CLOSED
  enforcement point stated (invocation/gate authority, never eventual
  stream delivery); acceptance/checkpoint wording updated for the actual
  re-pin/repair history. 15 tests added (RED set of 5 verified before
  repair); focused suite + `test_control_events.py` +
  `test_provider_harness_contract.py` green (111 passed).
  `git diff --check` clean; exact-scope check from f20fff0 shows only the
  four allowed paths; UTF-8/JSON parse clean; fake-pattern secret scan
  clean. Repair commit is the new review candidate SHA; repair branch
  pushed. No merge/self-accept.
