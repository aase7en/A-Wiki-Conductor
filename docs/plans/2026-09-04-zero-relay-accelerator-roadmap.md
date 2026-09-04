# Zero-Relay Accelerator Roadmap — 2026-09-04

Status: P0 ACCELERATOR / USER-PRIORITIZED
Planning work order: `WO-P1-155`
Classification: `REUSE + WRAP + EXTEND`

## Current maturity checkpoint - 2026-09-04

Zero-Relay has an advanced preview but is **not production-ready**.

Current preview evidence on the stacked WO155 branch demonstrates:
- one real installed ZCode app-server callability pilot;
- deterministic exactly-one repair behavior;
- deterministic continuation to the next READY task;
- focused and related regression tests around the preview adapter/state machine.

This is prototype/fabric evidence, not final ZRA-1..3 production acceptance. R3 review has unresolved boundaries including supervised process ownership/reaping truth, bounded stdout/result memory, repair-context truncation, exact provider/model/credential identity binding, and use of production authorization/admission/policy/secret-resolution assembly rather than synthetic pilot observations.

Therefore:
- label the existing real pilot as `LIVE_CALLABILITY_PROOF` until production authority is exercised;
- do not treat deterministic ZRA-2/ZRA-3 state-machine tests as live scheduler/lease integration;
- do not block the GLM-first delivery workflow on Zero-Relay completion;
- use the one-pointer human bridge immediately: GPT/integrator writes the durable task packet, the user sends one short pointer to ZCode/GLM, and the integrator reads the declared result directly;
- when Zero-Relay passes R3 gates, replace only that transport step with automatic dispatch/result ingestion.

The workflow authority and safety gates are identical before and after Zero-Relay. Zero-Relay is a latency accelerator, not a new scheduler, task authority, secret authority, or acceptance authority.

## 1. Product outcome

Remove the human from the message-bus role between GPT/A-Conductor and GLM/ZCode.

Target operator experience:

```text
USER GOAL
   -> A-Conductor creates bounded task packet
   -> eligibility / authority / quota / policy gate
   -> GLM-capable execution route is invoked automatically
   -> result + evidence are ingested automatically
   -> deterministic verification
   -> GPT/integrator review
   -> repair task dispatched automatically when required
   -> continue to next READY node
```

The user must not need to copy a prompt to another program, copy results back, or repeatedly type `continue` merely to move a valid task between accepted execution surfaces.

## 2. Why this is P0 now

This is an accelerator dependency, not feature creep. Every later ODP/AHA/roadmap node benefits from eliminating manual relay. Completing it first should reduce coordination latency, context-transfer mistakes, operator fatigue, and premium-model time spent on repetitive implementation routing.

The optimization is accepted only if it preserves current repository ownership, provider authorization, secret isolation, retry/idempotency, exact-result identity, and deterministic acceptance rules.

## 3. Reuse-before-build boundary

Reuse existing accepted components; do not create a second scheduler/router/provider store/mailbox:

- AHA-4/4A/4B durable dispatch + worker lease/recovery;
- AHA-5 task/result/review-repair bridge;
- AHA-6 parallel READY execution and provider runtime assembly;
- WO118 provider generation/trust/egress/admission enforcement;
- WO122 stable external-agent mailbox as fallback addressing shim;
- WO123 loop-engineer task/status/result protocol;
- existing Claude Code supervised harness/backend;
- existing provider configuration/admission authority.

The stable mailbox remains the fallback when no callable provider route is eligible. It must not become a second task authority.

## 4. Current actual-state evidence — 2026-09-04

Read-only host inspection from WO154 found:

- current source contains provider configuration/admission/runtime assembly and supervised Claude Code harness paths;
- `Claude Code 2.1.178` is installed and callable on this host;
- `ZCode` is not currently exposed as a CLI on PATH;
- the current shell exposes no GLM/Anthropic provider route variables;
- live `%LOCALAPPDATA%\A-Conductor\control-center.sqlite` is schema version 1 and currently contains the older Control Center tables only; provider tables are absent in that live DB;
- therefore current installed/live runtime is not yet exercising the accepted provider execution stack even though current source contains it.

No credential/config contents were read and no live provider or runtime mutation was performed.

## 5. Preferred execution path

Preferred supported route:

```text
A-Conductor
  -> existing provider authority
  -> supervised Claude Code CLI harness
  -> authorized Anthropic-compatible GLM-5.3 provider route
  -> bounded task
  -> result/evidence destination
```

Do not automate ZCode UI clicks by default. UI automation is brittle and must not bypass provider terms, authentication, quota or authority. If the user's ZCode entitlement exposes no supported non-interactive invocation path, real zero-relay GLM dispatch is `BLOCKED_EXTERNAL`; all local plumbing should still be completed and proven with fake/sacrificial providers while the stable mailbox remains the fallback.

## 6. Delivery nodes

| Node | Risk | Goal | Acceptance |
|---|---|---|---|
| `ZRA-0` | R3 | Live-stack migration/activation proof without touching live credentials | copied/sacrificial DB migrates to current provider schema; existing data preserved; rollback proven; no live DB mutation |
| `ZRA-1` | R3 | One-shot no-relay dispatch | A-Conductor submits one bounded synthetic task to a callable authorized GLM route and receives exact task-bound result without human copy/paste |
| `ZRA-2` | R3 | Automatic result ingestion + verify/repair | result identity/evidence validated; one forced review failure creates one bounded repair task and receives repaired result automatically |
| `ZRA-3` | R3 | Safe autonomous continuation | accepted result advances to next READY task without human relay; duplicate/timeout/ambiguous state never blind-replays |
| `ZRA-4` | R3 | Parallel accelerator | up to 2–3 independent GLM-capable READY lanes dispatch under existing lease/WIP/ownership limits; fan-in verifies exact results |
| `ZRA-5` | R2/R3 | ODP integration seam | ODP capability-first selection can choose this accepted execution route; mailbox remains fallback, not authority |

## 7. P0 execution order

```text
WO154 fast workflow accepted
  -> WO153 ZCode lock closeout releases shared SSoT hotspots
  -> ZRA-0 migration/activation proof
  -> ZRA-1 single real no-relay task
  -> ZRA-2 repair loop
  -> ZRA-3 automatic continuation
  -> ZRA-4 bounded parallel dispatch
  -> resume ODP roadmap using zero-relay execution fabric
  -> ZRA-5 ODP integration as the routing seam becomes ready
```

ODP-1 may be reconciled/readied in parallel only when it does not consume a mutable lane needed by this P0 accelerator. Do not continue broad ODP feature expansion ahead of ZRA-1..3.

## 8. Fail-closed conditions

Automatic GLM execution must not occur when any required fact is unknown or false:

`CAPABLE ∧ READY ∧ AUTHORIZED ∧ ADMITTED ∧ POLICY_OK ∧ RESULT_DESTINATION_BOUND`

Also block when:
- provider route/entitlement is not callable non-interactively;
- required quota/readiness evidence is stale or unavailable;
- task trust/egress policy denies the route;
- repository/worktree ownership is ambiguous;
- an earlier execution may still be running or its outcome is unknown;
- result task/provider/model/base-HEAD identity does not match;
- secret resolution would cross an unapproved boundary.

## 9. Verification

Because this path touches provider authority, credentials boundary, process execution, retries and durable task state, ZRA-0..4 are R3 unless a later bounded sub-slice is proven lower risk.

Required evidence includes:
- copied/sacrificial DB migration and rollback proof;
- fake-provider deterministic lifecycle tests before live use;
- exact task/result identity and hash binding;
- timeout/transport-loss/duplicate-dispatch fault injection;
- no secret leakage in logs/task/result packets;
- exact-SHA independent review;
- hosted CI;
- real one-task pilot only through an authorized supported route;
- post-pilot state reconciliation proving no orphan execution/lease.

## 10. Success metric

Primary metric: **human relay actions per accepted external-agent task = 0**.

Secondary metrics:
- prompt copy/paste actions = 0;
- result copy/paste actions = 0;
- blind replay after ambiguous transport = 0;
- duplicate mutable ownership = 0;
- median task handoff latency materially lower than stable-mailbox manual-trigger baseline;
- later roadmap throughput improves without higher blocking-defect escape rate.
