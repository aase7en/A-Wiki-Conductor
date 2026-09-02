# AiPASS Provider Integration Roadmap — 2026-09-02

Status: APPROVED ROADMAP CAPTURE / IMPLEMENTATION NOT YET AUTHORIZED
Owner boundary: A-Conductor provider/execution fabric; A-Wiki remains brain/policy authority
Planning work order: `WO-P1-132`

## 1. Decision

Evaluate AiPASS as an optional **reasoning / research / review provider lane** behind the existing A-Conductor provider contracts. Do not import a second orchestration system and do not give AiPASS direct Git/filesystem mutation authority.

Classification: `WRAP + EXTEND` existing provider/runtime/recovery seams.

Reference implementation refreshed: `niawjunior/aipass-bridge@a24a5bb6218559e9a66b9e6644c2be1e87885bca`.

Useful reference properties:
- local OpenAI-compatible chat/model surface;
- browser-held AiPASS session rather than copying the cookie into the bridge;
- streaming responses and model discovery, including free-credit metadata;
- server-owned conversation history;
- extension/transport disappearance is not automatically treated as execution failure.

No `LICENSE` file was visible at the inspected repository root. This roadmap therefore permits **concept/reference study only**; source copying requires an explicit license/permission check first.
## 2. External authorization gate

Official AiPASS terms currently effective from **2026-08-19** state in section 3.4 that, unless explicitly authorized in writing, users must not access the platform/account with bot-emulation or unapproved software and must not directly access/connect/use system API, API Key, or Token outside the provider-defined UI.

Therefore A-Conductor must fail closed:

`CONFIGURED != READY != AUTHORIZED != ADMITTED`

For AiPASS:
- `CONFIGURED`: provider/reference configuration exists locally.
- `READY`: local observation says the approved integration surface is reachable.
- `AUTHORIZED`: policy has evidence that this automation/integration mode is permitted.
- `ADMITTED`: authorized + enabled + healthy + route/quota policy permits this execution.

Default roadmap state: `AUTHORIZED = NO / BLOCKED_EXTERNAL`.

No live automated message execution is permitted by this roadmap merely because a bridge is technically reachable. Production enablement requires an official supported integration/API path or explicit written authorization covering the intended automation mode.

Terms are changeable; re-check the official AiPASS terms immediately before any live-authorization decision.
## 3. Target architecture

```text
A-Wiki policy / skills / memory
            |
            v
A-Sunday Conductor
Provider Policy + Execution Authority + Router
            |
      AiPASS adapter
            |
  approved local integration surface
            |
     browser-held session
            |
        AiPASS models
```

AiPASS returns reasoning/results. Any proposed code/file change must re-enter the existing Conductor proposal/materialization, repository-identity, lease, scope, test, evidence, and review gates before mutation.

Reuse these existing authorities instead of recreating them:
- `provider_config_store.py` / `provider_configuration.py`;
- `provider_execution_authority.py` / `provider_policy.py`;
- `provider_operator_view.py` / `provider_runtime_assembly.py`;
- durable execution, deduplication, transport recovery, and evidence services;
- `MODELS & AGENTS` UI and existing truthful readiness/quota projections.
## 4. Priority order

| Order | Node | Priority | Dependency / gate | Outcome |
|---|---|---|---|---|
| 0 | WO096 connector resilience | **P0 release blocker** | existing maintenance/hosted proof gate | v0.7.0 stability; independent of AiPASS |
| 1 | WO127 provider actions | **P1 released** | accepted / merged | stable Edit/Disable/Enable/Test control seam |
| 2 | WO128 T0+T1 evidence core + truthful projection | **P1 released** | accepted / merged | routing/admission evidence without invented reasons |
| 3 | WO134 Provider Evidence Detail | **P1 active** | exact-SHA review -> CI -> merge -> post-main | truthful operator evidence + explicit graph correlation |
| 4 | AIP-1 authorization + adapter contract | **P1 next** | WO134 accepted | exact provider boundary; no live traffic |
| 5 | AIP-2 fake/read-only discovery | **P1** | AIP-1 | health/models/free-credit projection without sending prompts |
| 6 | AIP-3 resilient message adapter | **P1** | AIP-2 + deterministic fake backend | streaming/recovery semantics; live path still gated |
| 7 | AIP-4 authorized live pilot | **P1 / BLOCKED_EXTERNAL** | written/official authorization | research/review-only live evidence |
| 8 | AIP-5 cost/quota routing | **P1** | accepted live pilot + truthful quota observations | cheap/free model candidate routing |
| 9 | AIP-6 UI/operator integration | **P1/P2** | stable adapter semantics | AiPASS truth in MODELS & AGENTS |
| 10 | AIP-7 browser-provider generalization | **P2 optional** | second real provider proves reuse | generic abstraction only when justified |

Future WO numbers are intentionally allocated **at claim time**, not reserved here, to avoid collision with parallel roadmap work.
## 5. Execution nodes

### AIP-1 — Authorization + adapter contract

Goal: define the minimum AiPASS provider contract without live automation.

Required:
- re-check official terms and record authorization evidence/state;
- decide whether the future implementation uses an official supported API/integration or remains blocked;
- define provider capabilities such as streaming, model discovery, reasoning visibility, conversation affinity, and cost/credit observation;
- define safe endpoint/reference configuration without storing browser cookies;
- explicitly map disconnect/reconnect behavior onto the existing resilient-execution contract;
- perform source-license review before any implementation reuses code rather than concepts.

Acceptance: typed contract + fake fixtures exist; `AUTHORIZED=NO` cannot dispatch.

### AIP-2 — Fake/read-only discovery

Goal: prove integration shape with zero prompt execution.

Required:
- deterministic fake AiPASS bridge fixture;
- read-only health/status observation;
- model list projection and optional `free_credit` observation;
- stale/error/empty/unsupported states;
- generation-bound observation; no secret/cookie/endpoint-value exposure.
Acceptance: CI uses fake fixtures only; no browser/login required; no message is sent upstream.

### AIP-3 — Resilient message adapter

Goal: implement provider-neutral execution semantics before any live enablement.

Required deterministic cases:
- streaming success and bounded output;
- disconnect before dispatch;
- disconnect after dispatch while execution may still be running;
- completion after observer/extension loss;
- timeout / malformed response / non-success result;
- duplicate execution request while the original is unresolved;
- model-list refresh racing provider configuration generation;
- conversation affinity treated as cache/context, never Conductor SSoT.

Core invariant remains `TRANSPORT FAILURE != EXECUTION FAILURE`. Never blind-retry an unknown AiPASS generation.

Acceptance: fake/fault-injection matrix passes through existing durable execution/evidence authorities; production authorization remains disabled.

### AIP-4 — Authorized live pilot

Gate: `BLOCKED_EXTERNAL` until official support or explicit written authorization covers the exact automation mode.

First live role: **research / reasoning / independent review only**. No direct `RUN`, file write, Git mutation, deployment, or credential access.
Pilot evidence must record:
- authorization basis/version;
- provider/model selected;
- safe observation timestamps and route identity;
- execution/evidence IDs;
- disconnect/recovery behavior;
- result verification by Conductor or an independent reviewer.

Acceptance: bounded live pilot succeeds without secrets in logs/state and without bypassing provider policy or user-account restrictions.

### AIP-5 — Cost/quota routing

Goal: make AiPASS an optional low-cost candidate, never an automatic loophole around provider limits.

Routing inputs may include:
- observed model readiness;
- current free-credit/credit metadata when legitimately available;
- task capability fit;
- recent reliability/latency evidence;
- user/provider policy and authorization;
- need for independent-provider review.

Unknown or stale cost/quota data must remain `UNKNOWN`; never invent remaining credit or fallback reason.

Acceptance: deterministic router tests show unauthorized/unready/stale AiPASS candidates are excluded and selection reasons are evidence-backed.
### AIP-6 — MODELS & AGENTS integration

Expose only operator-useful truth:
- configured / enabled;
- ready / degraded / unavailable;
- authorized / blocked reason;
- model inventory and safe free-credit indicator when current;
- last observation age;
- Test/Refresh through the existing async provider-action path.

Never display cookies, raw credentials, authorization headers, or unrestricted browser/session identifiers.

### AIP-7 — Generalize only after proof

Do not create `BrowserBackedProvider` merely because AiPASS uses a browser-backed session. Generalize only if a second provider needs materially the same lifecycle/auth/transport contract and the shared abstraction reduces real duplication.

## 6. Hard non-goals

- no wholesale import/fork of `aipass-bridge`;
- no reverse-engineering escalation or security-filter bypass work;
- no extracting/copying AiPASS cookies, API keys, tokens, or hidden credentials;
- no bypass of AiPASS/model-provider quotas, access controls, or terms;
- no AiPASS conversation history as project/task source of truth;
- no second provider registry, scheduler, evidence store, or retry engine;
- no direct AiPASS filesystem/Git authority.
## 7. Verification strategy

Every implementation node must use RED-first deterministic tests and preserve the accepted provider/recovery semantics.

Minimum regression matrix:
- unauthorized provider cannot dispatch;
- configured-but-not-ready cannot dispatch;
- ready-but-not-authorized cannot dispatch;
- disabled/in-use/CAS fences remain intact;
- no cookie/token/credential value reaches DB, logs, UI, task packets, or evidence;
- transport loss preserves unresolved execution ownership;
- no blind replay after ambiguous completion;
- stale observations cannot overwrite a newer provider generation;
- AiPASS-originated change suggestions require normal Conductor mutation authority and verification;
- fake backend covers all CI paths; live tests are separately gated and opt-in.

## 8. Next development sequence

1. Finish WO134 Provider Evidence Detail through exact-SHA independent review, exact-head CI, merge, and post-main evidence.
2. Open a bounded implementation WO for **AIP-1** from then-current main; re-run the reuse/claim/license/terms gate and keep live traffic disabled.
3. Implement **AIP-2** fake/read-only discovery before any chat execution.
4. Implement **AIP-3** resilient transport behavior entirely against deterministic fixtures first.
5. Keep **AIP-4** blocked until external authorization is explicitly satisfied.
6. Only after an accepted live pilot, add cost/quota routing and richer operator UI.

WO096 remains the independent P0 release blocker throughout this sequence and must not be delayed or weakened by AiPASS work.
## 9. Reference evidence

- A-Conductor planning base: `aase7en/A-Wiki-Conductor@9118a289b9fcd87e0bae4e4eb601cc585062856d`.
- AiPASS bridge reference: `https://github.com/niawjunior/aipass-bridge`, refreshed at `a24a5bb6218559e9a66b9e6644c2be1e87885bca`; repository license metadata remains null and no root `LICENSE` was found.
- Official AiPASS terms: `https://www.aipass.go.th/term-and-cond-th`, effective 2026-08-19; section 3.4 is the current automation/API authorization gate used by this roadmap.

These external references are evidence inputs, not A-Conductor runtime dependencies.