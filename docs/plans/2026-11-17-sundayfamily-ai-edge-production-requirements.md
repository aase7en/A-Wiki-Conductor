# SundayFamily — Operator Requirements Addendum: AI Edge, Configurable Decision Routing & One-Command Production Install

**Date:** 2026-11-17 (Asia/Bangkok)
**Status:** OPERATOR PRODUCT INTENT / DESIGN CHECKPOINT — **NOT IMPLEMENTED, NOT RELEASE AUTHORITY**
**Governance:** A-Wiki-Conductor Issue [#771](https://github.com/aase7en/A-Wiki-Conductor/issues/771), WO-P1-771
**Baseline:** Existing [SFU26 roadmap](2026-11-13-sunday-family-unified-dashboard-routing-roadmap.md) (WO-P1-744/#744). This is an ADDENDUM to the plan, not a replacement.
**UX boundary:** SundayFamily Color E-Ink + manga direction is handled separately by the operator's Gemini Carbon chat-only session and current #769 / PR #770. This document does not select visual details or authorize UX-2 changes.

## 1. North star / single-product experience

SundayFamily should become the easiest production operator experience for the existing A-Sunday Conductor family. The operator should be able to install one package with one documented OS-appropriate command, configure providers and model-routing behavior in a safe Settings UI, see evidence-based state/cost/quality, and operate bounded workflows without being a manual GPT↔agent message bus.

**Retain authority boundaries:**
- **ChatGPT + SundayMCP plugin:** user-facing conversational planning and strongest reasoning/integration while an active conversation exists; **ChatGPT is not an always-on API supervisor** and cannot be treated as self-waking after an asynchronous job finishes.
- **A-Wiki:** existing knowledge, skills, canonical skill/model intelligence and routing sources; no copied second skill/model SSOT.
- **A-Wiki-Conductor / A-Conductor:** Work Orders, task/claim/lease state, semantic/provider admission, deterministic safety gates, execution/reconciliation, evidence, review and accepted completion.
- **SunDayRemoteMCP:** physical machine capability/transport and durable execution adapter, **not** scheduler/task/review/claim/authorization authority.
- **SundayFamily React/PWA:** existing authenticated operator UI and read models. Browser never owns a parallel task database or direct unguarded machine execution.

The visually themed user experience is an independently owned design track. The developer track supplies semantic functional requirements, not CSS, colors, layout or illustrations.

## 2. AI Edge & Cost-Aware Router — requirements

**Required:** reuse and extend existing A-FastTask/provider-admission/semantic seams; classify first using deterministic rules and existing A-Wiki shortlist/context compression, then optionally invoke a suitable small decision model. Do not recreate a generalized router, queue, Work Order or agent scheduler.

The admitted capability catalog must support:
- External **Free** models for approved non-sensitive bounded tasks (quotas, availability, retention/egress and limitations can change).
- **Batch** asynchronous models for independent, noninteractive requests with explicit provider handling/retention, durable job identity, status and harvest/replay safety.
- **Local/Edge** models for eligible offline/private tasks on hardware that actually supports them; unmet hardware capability returns typed unavailable, not fake success.
- Paid/frontier provider as **explicitly budgeted and authorized** fallback for tasks requiring capability/assurance unavailable in lower-cost lanes.
- Capability dimensions: `text`, `image`, `structured_decision`, `tools`, `coding`, `reasoning`, `batch`, `context`, locale/Thai, reliability, token/usage and privacy.
- Task constraints: class, risk tier, data sensitivity, OS/device readiness, latency target, provider availability, quota, evidence requirements, ownership, consent and WIP.
- Rule results: selected provider/model/version, candidates excluded and why, settings-policy revision, source/freshness, estimated vs actual cost, abstain/fallback/escalation reasons.

**Must not:** route confidential patient data, passwords or approved-secret values to an external model by default; let model confidence grant claims/mutation/merge/paid egress; blindly retry a possibly completed Batch/Agent run; silently substitute a different model when policies require explicit provider selection.

## 3. No-hardcode Settings — user/admin experience

Use **configuration-driven policy**. Runtime model IDs/prices are not stable architecture constants. Expose through the *existing* Settings/Models & Agents journey, with one authority and source/version/read-back. Store only reference handles and metadata in the frontend; secrets remain in approved encrypted/OS-backed storage.

| Settings area | Proposed editable controls | Guards |
|---|---|---|
| Provider Registry | enable/disable, adapter type, model ID/version, capability tags, allowed residency/egress | source/provenance and compatibility verification; provider names do not confer authority |
| Model Profiles | task-class preference, priority, context/latency/quality goals, local hardware eligibility | no arbitrary browser commands, no unvalidated model aliases |
| Routing Policies | Free / Local / Batch / Paid preferences, typed abstain/fallback | risk/ownership/permission gate enforced independently of editable settings |
| Budget & Quota | day/month/workflow caps, rate/concurrency limit, reserved budget and approval threshold | hard stop at unknown cost, no paid spending without approval |
| Batch Options | eligibility, deadline, polling/notification, result retention, recovery/retry | existing task identity, idempotency and storage policy; no separate queue authority |
| Decision Providers | typed decision adapter choice and thresholds, shadow/canary mode, evaluation dataset | conservative no-go when provider/schema/evaluation is unproven |
| Diagnostics | test connectivity, dry-run reason, config diff, draft/publish/rollback, policy revision | atomic validate/publish, restricted roles, audit/redaction |

**Separation of concerns:** (1) versioned immutable security invariants/schema in source; (2) editable validated app config in approved existing authority; (3) runtime observations/telemetry in existing durable evidence projections. Do not use Git, UI state or chat memory as a live secrets/config DB.

**UX acceptance:** A non-coding operator can add an approved provider and change a low-risk route preference through the UI *without editing source or re-deploying*. The UI clearly differentiates `DRAFT` vs `PUBLISHED`, `EFFECTIVE` vs `DESIRED`, `UNKNOWN/STALE` vs `HEALTHY`; every change has a rollback path and a source revision.

## 4. Fast typed Decision Engine

Reuse **existing** `SemanticDecisionProvider`, `SemanticDecisionRequest`/`SemanticEvidence`, Jev adapter, fixtures, SFU26 evaluation corpus and advisory/admission gates. No duplicate `DecisionRequest`, new policy authority or model-driven authorization engine.

Candidate adapters for subsequent verified feasibility, **not hard-coded binding vendors**:
- TypeSafe/Jev (existing code seam; verify currently supported decision families, model versions, prices and limits before calling live).
- Google small/fast decision model (model/API name, schema, pricing, privacy, availability and Terms are **UNVERIFIED until official docs plus actual connector conformance**).
- Other fast/cheap local/free decision-capable models if they pass typed-output, latency, calibration, cost and policy/evidence tests.

Decision output is **advice** such as score/classification/probabilities with provenance, not authoritative `APPROVE` for execution. Maintain `OFF -> SHADOW -> ADVISORY -> CANARY -> PRODUCTION` progression only via accepted risk, budget and privacy gates.

**Benchmark/evidence:** compare deterministic baseline vs each candidate on frozen representative bilingual/Thai holdout; verify false-negative impact on high-risk classes and class imbalance. Track p50/p95 latency, accuracy/F1 (by family), abstain/calibration, policy-override attempts, prompt-injection robustness, cost per *accepted* task, human rework, escalation, provider errors, quota and actual savings. Reject the apparent 'cheapest' model if failed validations/rework erase savings.

## 5. Async Batch and continuity

A Batch provider is a transport/cost option. Reuse A-Conductor's existing durable Work Order/task/attempt/event identity. Maintain exact input/result identity, privacy classification, approved retention, retry budget, deadline, failure type and result destination. Derived states `RUNNING`, `TERMINAL_UNHARVESTED`, `STALLED`, `INTERRUPTED`, `UNKNOWN` must reconcile against actual evidence before replay; no duplicate writer on ambiguous completion. ChatGPT reviews on a later user turn or another **explicitly authorized** supervisor surface; never promise the same chat will autonomously wake.

## 6. One-command production installer (Windows + macOS)

**Hard product acceptance criterion:** from a fresh supported Windows/macOS machine without manually installed Python/Node/Git/Docker, the user enters **one OS-appropriate documented command** and the installer installs required software, performs machine preflight, configures eligible services and verifies ready operation. Additional OS permission prompts, account pairing and explicit trust approvals remain legitimate where required; never bypass them.

**Installer responsibilities:**
1. Detect OS version/arch, disk, RAM/GPU (for optional Local AI), network/trust chain, ports, current user permissions, service conflicts and existing installation.
2. Download **pinned signed and verified artifacts** from authorized release channel; no unverified pipe-to-shell or silently running opaque remote scripts. Least privilege by default.
3. Install bundled/frozen UI/backend/runtime and approved dependencies *only if actually necessary*; do not force global Python/Node/Docker just to run a built frontend.
4. Use the existing Device Agent enrollment and A-Conductor authority. Pairing/credential consent are explicit and authenticated. No automatic exposure of LAN/public endpoints.
5. Provide `doctor`/health/readiness with actual API, identity, adapter and read/write-permission checks appropriate to accepted scope, including start-after-login behavior where chosen.
6. Repeat-safe idempotent re-run, interrupted-install detection, snapshot-before-upgrade, signed update, compatible migration and **tested rollback without loss of user data**. Uninstall never silently destroys user data/keys/Work Orders.
7. Launch/open existing SundayFamily Dashboard and bounded Setup Wizard, with truthful `READY`, `DEGRADED`, `BLOCKED`, `UNKNOWN` states and next safe action.

**Design candidates (not frozen):** minimal signed Rust/Go bootstrap, supported Windows package manager, macOS Homebrew/package workflow, embedded Python runtime, bundled static web/PWA and optional WebView. Choose based on **actual** Python/TS app and SRM substrate packaging reality; do NOT rewrite the stack to Rust for packaging convenience.

**Verification matrix:** clean/older supported Windows/macOS; with and without existing dependencies; offline/network/TLS failure; insufficient disk/permissions; port conflict; interruption and re-run; upgrade and rollback; OS restart/login recovery; uninstall preserving user data; malicious/tampered artifact rejection; provider unavailable and confidential-data defaults.

## 7. Explicit security, ownership and rollout gates

- Actual repo/worktree/branch/HEAD, claims, WIP, dirty work, ongoing execution and replay safety before any mutation.
- Scope guard/approval for paid API credit, outbound model data, autostart, credentials, firewall, installer privileges, Production and consequential changes.
- Typed config validation and atomic read-back. No unverified `success` from HTTP accepted or a model saying `DONE`.
- Security review of external inference privacy/retention and exact API/model IDs before provider admission.
- Exact frozen SHA per repo, independent review and CI by risk, post-main/release/live acceptance, no invented install/benchmark results.
- Protect separate visual design ownership #769/PR #770. A desired agent-entry link to this addendum must be made only after non-overlapping claim/review once PR #770 is resolved.

## 8. Map to existing SFU26 implementation sequence (not a new program)

| Existing seam / card | Effect of this addendum |
|---|---|
| #743 UX-1; card 04 UX-2 | UI functional/approval gate remains, visual design in separate Gemini Carbon session |
| Card 05 / #767 settings read models | reuse safe metadata projection; only later plan guarded editable config and write-through gate |
| Cards 07/08/09/10 | reuse evidence pack, skill/model shortlist, freshness and offline evaluation |
| Card 11 Gemini adapter; card 12 shadow | official API/privacy/security/egress proof before any live external invocation |
| Card 13 route/advice UX | expose explainability, provenance and config observability using accepted read models |
| Cards 17/18/19 | same-origin serving + launcher feasibility + tested production packaging/parity; add hard one-command fresh-install acceptance |
| Device Agent #607/#630 | reuse preflight/doctor/enrollment/autostart, not a second device bootstrap identity system |

Any missing implementation slice needs its own accepted WO and scope; **this addendum neither grants dispatch nor resolves the outstanding operator UX/security gates**.

## 9. Deferred decisions / next actions

1. Independently review this new-document PR; bind exact candidate head, CI and review evidence. Do not silently merge.
2. Re-check issue #769/PR #770 status, AGENTS/graph ownership and live repo state; **then** perform a separate scoped agent-entry/reference update so future agents discover this additive requirements document.
3. Audit current SFU26 cards, prior provider settings, SRM Device Agent installer and source of truth, then write small nonoverlapping implementation WOs for proven gaps only.
4. Invite **Gemini Carbon (chat-only)** to critique this architecture/sequence and identify security/cost/UX setup gaps. Return its analysis to integrator for evidence-based discussion; do not let model advice replace repo/runtime truth.
5. Run read-only feasibility/benchmark first; gated external provider use/paid credits and installer release remain later decisions.

**Definition of checkpoint success:** the product intent is durable, linked to #771 and the SFU26 program, traceable to exact GitHub revision, and isolated from concurrent UX/UI work. **Definition of project production success is separate and requires measured E2E proof.**
