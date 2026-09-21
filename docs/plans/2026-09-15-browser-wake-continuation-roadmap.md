# Browser Wake / Continuation Relay Roadmap — 2026-09-15

Status: RECONCILED ROADMAP CANDIDATE / DOCS-ONLY / SOURCE MUTATION FORBIDDEN
Work order: `WO-P1-446`
Durable issue: GitHub #446
Historical authority alias: Issue #320 / WO-P1-240
Identity schema: `GITHUB_ISSUE_V1`
Classification: `REUSE + WRAP + EXTEND`; `NEW` only for a proven browser-transport/provider-adapter gap.

## 0. 2026-09-19 reconciliation against current authority

This roadmap was originally frozen on 2026-09-15. It was first reconciled against
`origin/main@3656fb386911b5bf9e3457e8e11c67d6b11da8e6` and is now re-pinned on
2026-09-21 against `origin/main@0ce82be15355bf3af782cd488b54d77c475d285b` plus the newer accepted/open authorities:

- WO-P1-257 / Issue #365 is merged and owns the Hook/STM/Monitor/Web+Extension/Command-Gateway architecture. Browser Wake consumes that architecture; it does not create a second extension state model or command channel.
- WO-P1-258 / Issue #368 / PR #371 established Hook Contract v1. Main has since advanced through accepted HOOK-1 / HOOK-1B / HOOK-1C / HOOK-2A / HOOK-2B successors, while the forward-compatibility repair PR #385 remains open. Browser Wake must bind to the latest accepted Hook-contract family at each implementation freeze and must not pin or fork a stale pre-repair schema.
- WO-P1-369 / Issue #369 / PR #373 is merged and is the canonical context-rollover guard. New-chat/session resume consumes that accepted contract rather than storing another resume truth.
- WO-P1-374 / Issue #374 / PR #377 is the canonical A-Faster durable delegated-lane identity/recovery overlay (LANE_REF, DELEGATED_RUN_ID, ATTEMPT, BINDING_DIGEST). Historical pre-remediation WO-P1-260 pointers remain valid evidence aliases only; Browser Wake never treats them as task/retry authority.
- DEX-ARCH-1 / Issue #348 / PR #372 is merged. It freezes DEX-3a as supported completion notification and DEX-3b as the capability-proven supported resume adapter. DEX-2b identity/receipt foundation is now merged (PR #403); DEX-2a substrate supervision and the production DEX-3a completion-event seam remain open. Browser Wake is therefore a provider/browser realization of **DEX-3b**, not a parallel continuation control plane.
- WO-P1-381 / Issue #381 / PR #382 is merged and protects atomic Work Order identity. The pre-policy WO-P1-240 / Issue #320 lane remains a historical evidence alias; Issue #446 / WO-P1-446 is the canonical live Browser Wake roadmap identity.
- WO223 / PR #319 is merged. Issue #215 is the current exclusive owner of automatic accepted-completion -> NEXT_READY continuation. Historical ZRA-3 PR #263/#269/#274 and WO191/195/227 remain unaccepted evidence and are not the implementation authority Browser Wake should revive.
- Ordinary ChatGPT/Gemini web chat does not need or provide a native `/goal`. The durable goal/task graph remains A-Sunday Conductor/A-Wiki authority; the browser adapter receives only bounded task/continuation turns and returns untrusted proposals/results.
- Scheduled goals are a control-plane feature, not Chrome-alarm authority. An Extension UI may request/show schedules only after a canonical scheduler contract exists; a browser alarm may at most provide a non-authoritative wake hint.

The current delta therefore narrows WO446 into the browser/provider implementation roadmap for **DEX-3b supported resume**, reusing Hook/Monitor/Command-Gateway/WO369/WO374 authorities rather than inventing another Goal, continuation, recovery, or schedule system.

### 2026-09-21 acceleration update

- COCKPIT-1A / WO424 and RUNTIME-AUTH-1 / WO431 are merged, and WO433 / PR #441
  is in current main with the accepted explicit/manual bounded
  runtime activation primitive. #429 COCKPIT-1B is the current product-binding
  frontier. Browser Wake consumes these seams; it does not create a second runtime
  producer or a parallel operator truth.
- Issue #215 still exclusively owns automatic accepted-completion -> NEXT_READY
  continuation and remains an open prerequisite for live autonomous continuation.
- HOOK-0 forward-compatibility repair PR #385 is still open. Any browser
  implementation freeze must bind the latest accepted Hook successor rather than
  the older pre-repair contract.
- WO205 Phase-D advanced independently into current main via PR #445. Browser Wake
  consumes current-main truth and does not own or reopen that source scope.

User priority is now to minimize the human `continue` relay as early as safely
possible. Therefore the dependency strategy changes from **wait-then-build** to
**contract/transport-first**:

1. after WO446 acceptance, BWA-0 contract shaping may proceed while #215/Hook/DEX
   owners continue independently;
2. while BWA-0 is under review, BWA-1 source-layout/test-harness shaping may run
   read-only; tracked BWA-1 source mutation starts only after the BWA-0 contract
   is accepted and a mutable WIP slot is free;
3. BWA-1 then uses a deterministic fake provider plus a **test-only fake ingress**
   defined by BWA-0. It must not invent or impersonate the production DEX-3a
   completion producer; success proves only transport/binding/restart/dedupe mechanics;
4. BWA-2 live ChatGPT/Gemini wake and BWA-3 zero-human continuation remain
   fail-closed on current accepted continuation/Hook/DEX/provider-authorization gates.

This keeps the extension moving without allowing fake-provider success to
masquerade as accepted live NEXT_READY autonomy.

## 1. Product problem

A-Conductor already removes much of the first human relay bottleneck: browser AI can reach the local machine through RDC, SundayWorker/Serena MCP, and accepted execution surfaces; A-Conductor can dispatch CLI/external agents and read durable results.

The remaining bottleneck is the reverse direction. When Kilo/Claude/ZCode/SundayWorker finishes or blocks, an ordinary consumer browser-AI conversation (ChatGPT/Gemini/Claude/AiPASS or another supported web AI) does not automatically receive a new turn. The human still has to type "continue" even when the next action is recoverable from durable state.

Target operator experience:

```text
ONE USER GOAL
  -> browser AI reasons / delegates
  -> A-Conductor executes / supervises / verifies
  -> external CLI or Worker finishes
  -> A-Conductor emits a durable continuation event
  -> bound browser conversation is woken automatically
  -> browser AI reads durable evidence and proposes next action
  -> A-Conductor validates and executes it
  -> repeat until COMPLETE or a real human-only gate
```
## 2. Authority split — do not create a second control plane

This roadmap extends the accepted A-Wiki/A-Conductor owner map from Issue #233.

| Capability | Owner | Browser-Wake role |
|---|---|---|
| Planning/decomposition policy, skills, model policy | A-Wiki | REUSE |
| A-Loop long-horizon semantics / completion policy | A-Wiki | REUSE / project into runtime |
| Review lifecycle / ReviewBus | A-Wiki | REUSE through existing adapter |
| Durable knowledge / memory / defect learning | A-Wiki | REUSE |
| Live job/execution state, worker/provider/runtime lease | A-Conductor | OWNER |
| Process supervision, dedup, recovery, mutation admission | A-Conductor | OWNER |
| Runtime provider/model enforcement and evidence | A-Conductor | OWNER |
| Browser extension / provider DOM adapter | Sunday-Family Extension | ADAPTER only |
| Native Messaging host / browser broker | Sunday-Family Extension | ADAPTER only |
| Consumer browser AI response | Browser AI | UNTRUSTED proposal until validated |

Hard rule: the extension must not own a scheduler, goal store, claim store, review lifecycle, retry engine, model-policy store, or durable project memory.

A browser-AI turn ending is not task completion. A CLI process exiting is not task completion. Existing A-Conductor deterministic evidence and accepted A-Wiki review policy remain completion authority.

## 3. Reuse-first findings

A-Wiki already has the brain-side continuation machinery that this feature needs. Do not recreate it in A-Conductor or JavaScript:

- `scripts/hooks_runner.py`: canonical provider-neutral lifecycle hook dispatcher; registry-driven, hard/soft classification, deterministic order, bounded timeouts, sanitized diagnostics and fail-closed hard gates.
- `a-loop`: autonomous decompose -> execute -> verify/review -> continue loop with disk checkpoints and bounded no-progress handling.
- ZCode A-Loop hooks: SessionStart SSoT injection + Stop continuation + PreToolUse gates. This proves the "wake/continue from lifecycle event" pattern already exists on the CLI side.
- `a-claim`: canonical coordination policy and collision-prevention pattern; Browser Wake must respect the cross-repo owner map and must not add another claim database.
- `handoff-auto-export.sh`: debounced/locked continuity projection after edits; reuse the pattern for projections, not as a new runtime authority.
- A-Router / A-Suite: progressive-disclosure routing. Browser wake messages should inject a compact pointer/event, not replay whole chat history.

A-Conductor already has the execution-side machinery:

- durable job/execution events and checkpoints;
- `JobExecutionBackend` as the canonical executor port;
- worker/provider admission and lease authority;
- execution fingerprint/dedup/recovery;
- Zero-Relay result/review/repair path;
- execution liveness projection;
- `operator.v1` as the canonical operator/control protocol.

Therefore Browser Wake is a missing **transport adapter + conversation binding + response ingestion seam** under DEX-3b, not a new orchestrator. DEX-3a supplies the supported completion-notification side; DEX-3b owns the supported resume-adapter slot; Browser Wake only realizes that slot for consumer browser AI surfaces.

## 4. External projects — what to reuse

### `niawjunior/aipass-bridge` — primary reference

Reference: https://github.com/niawjunior/aipass-bridge
License: MIT on the inspected current main.

Useful transferable patterns:
- MV3 extension connected to a real signed-in browser tab;
- browser-held authentication: page JavaScript executes inside the signed-in session instead of exporting cookies/credentials;
- localhost bridge exposing a stable programmatic protocol;
- OpenAI-compatible projection over a browser-only provider;
- streaming and server-side conversation affinity;
- file/media attachment and asynchronous upstream job normalization;
- model/credit discovery and a `doctor` command;
- offscreen/service-worker keepalive and headless deployment patterns.

Do **not** adopt its local file-edit agent as A-Conductor mutation authority, and do not inherit a no-auth localhost boundary unchanged. Sunday-Family must bind every privileged call to A-Conductor identity/authorization and use a narrower IPC surface.
### Other reusable bridge patterns

| Reference | Reuse classification | Valuable pattern | Do not inherit blindly |
|---|---|---|---|
| `YosefHayim/ai-browser-bridge` | WRAP / EXTEND | provider adapters for ChatGPT/Gemini/Claude, stable non-interactive ask/result contract, fan-out, conversation reuse/search | its own repo state/checkpoint authority; CDP/shared-profile assumptions |
| Chrome Native Messaging bridge projects (`chrome-agent-bridge`, Browser/MCP bridges) | REUSE pattern | extension <-> native host authenticated IPC, restart isolation, narrow tool surface | broad cookie/CDP access or unrestricted browser control |
| Claude/Kilo lifecycle hooks and community notification hooks | REUSE event pattern | Stop/idle/error/permission events as deterministic wake inputs | human notification as the final loop; Browser Wake must continue autonomously when policy permits |
| ntfy/Web Push remote-approval tools | EXTEND later | HUMAN_REQUIRED notification/approval channel, fail-closed timeout | using human approval for steps A-Conductor can deterministically continue |

The adapter layer must be provider-specific because consumer web DOMs drift independently. Provider adapter failure is `TRANSPORT_FAILURE` / `RUNTIME_UNVERIFIED`, not proof that the underlying A-Conductor task failed.

## 5. Sunday-Family Extension package boundary

Use **Sunday-Family Extension** as an umbrella brand, but keep privilege and failure domains modular rather than shipping one giant extension.

Proposed modules:

```text
browser-harness-contract       # adapter/conversation capability contract over accepted Hook Contract
sunday-family-native-host      # authenticated Native Messaging <-> Conductor adapter
sunday-family-extension-core   # MV3 lifecycle, provider binding, thin cockpit shell
provider-chatgpt-web           # bounded ChatGPT Web task/result adapter
provider-gemini-web            # bounded Gemini Web task/result adapter
provider-claude-web            # later after two-provider conformance
provider-aipass-web            # later, subject to terms/authorization
browser-wake-relay             # consumes eligible continuation events; sends bounded turn
conversation-index             # non-authoritative provider conversation locators
sunday-family-doctor           # selector/session/version/capability diagnostics
embedded-helper-ai             # optional diagnostics only; never privileged authority
```

Do **not** create a separate `sunday-family-protocol`. Event envelopes, dedupe,
privacy, causation and adapter capability discovery reuse the accepted WO257
Hook-contract family current at implementation freeze. Consequential operator commands reuse the later A-Conductor
Command Gateway. Session/new-chat resume consumes the context-rollover contract.

`embedded-helper-ai` may summarize diagnostics, classify a broken selector,
suggest a provider, or explain operator state. It must never bypass A-Conductor
claim/mutation/cost/authorization gates or decide project completion.
## 6. Continuation protocol

The Browser Wake path consumes existing durable truth. The wire/event identity MUST map to the accepted Hook Contract family plus existing durable execution/task references; the human-readable block below is only the bounded text rendered into a provider conversation, not a second protocol or SSoT. Example conceptual turn:

```text
[A-CONDUCTOR CONTINUE v1]
event_id=<durable id>
goal_ref=<durable goal/work-order ref>
reason=AGENT_RESULT_READY|REVIEW_REQUIRED|NEXT_READY|RECOVERY_REQUIRED
candidate_sha=<exact SHA when applicable>
evidence_refs=<bounded durable refs>
next_decision=<what the browser reasoner must decide>
```

The extension sends this to the exact bound provider/conversation only after A-Conductor says wake is eligible. It must never reconstruct project state from old page text.

Browser-AI output returns as a **proposal envelope**, for example:

```text
A_CONDUCTOR_ACTION_V1
intent=REVIEW_RESULT|DISPATCH_TASK|CONTINUE_NEXT_READY|REQUEST_HUMAN
work_order_ref=...
expected_head=...
requested_capability=...
```

A-Conductor then re-reads current durable state and validates the proposal. Raw web text never becomes shell/Git/mutation authority directly.

Required dedupe semantics:
- every wake has an A-Conductor event/execution identity;
- repeated extension delivery of the same event is safe;
- a second browser response for an already-consumed exact event cannot cause a second mutation/model effect;
- tab/extension/browser crash is transport loss and must reconcile before resend;
- ambiguity remains UNKNOWN/RECOVERY_REQUIRED rather than blind replay.

## 7. Priority order — reconciled 2026-09-19

The leverage rule remains: continuation semantics first, browser transport second,
operator UI/control third, workflow scale last. Current dependencies are now
split so Browser Wake can progress without duplicating WO257.

### P0-A — Parallel predecessor + Browser-Wake preparation

Run the continuation/execution dependencies in their existing owner lanes while
Browser-Wake contract/transport preparation proceeds independently:

1. Issue #215 retains exclusive automatic NEXT_READY policy and must reach an
   accepted exact-SHA successor before live autonomous continuation is claimed.
2. The Hook family has accepted HOOK-1 / HOOK-1B / HOOK-1C / HOOK-2A / HOOK-2B
   successors; open PR #385 remains a forward-compatibility repair. Every live
   browser freeze binds the latest accepted Hook-contract family.
3. Context rollover is accepted as WO-P1-369 and is consumed unchanged.
4. DEX-2b identity/receipt foundation is merged. The still-open DEX-2a substrate
   supervision and production DEX-3a completion-event seam must reach the
   acceptance required by BWA-3 before end-to-end DEX-3b autonomy is claimed.
5. Merged WO433 provides the generic explicit/manual activation primitive;
   Browser Wake must reuse it and must not implement another runtime producer.

Open predecessors block **live autonomy claims**, not all useful browser work.
BWA-0 may shape the adapter contract after WO446 acceptance. BWA-1 read-only
layout/test shaping may overlap BWA-0 review, but tracked BWA-1 implementation
waits for BWA-0 acceptance and WIP admission. Neither lane may reinterpret a
fake/synthetic event as accepted NEXT_READY or production DEX-3a authority.

### P0-B — DEX-3b / BWA-0 Browser Chat Resume Adapter Contract

Create a bounded follow-up Work Order immediately after WO446 acceptance. Open
predecessors are recorded as explicit contract dependencies rather than reasons
to idle this docs/contracts lane.

Define only the missing browser execution/harness semantics:

- exact provider + adapter version/capability discovery;
- exact conversation binding and non-authoritative locator;
- bounded task/continuation input;
- stable response-completion/result capture;
- proposal/result envelope back to A-Conductor;
- DOM/selector/session/version drift classification;
- event/dedupe mapping to Hook Contract;
- WO-P1-369 context-rollover handoff mapping;
- delegated-lane evidence mapping to canonical WO-P1-374 LANE_REF / DELEGATED_RUN_ID pointers when applicable, while preserving historical WO260 aliases as evidence only;
- DEX-3a completion-event -> DEX-3b browser-resume correlation without creating another event or execution authority;
- no goal store, scheduler, claim store, retry engine or completion authority.

BWA-0 freezes three fail-closed fences:
- explicit/manual activation consumes the accepted WO433 primitive first; it does not
  create a new runtime producer;
- automatic NEXT_READY remains Issue #215-owned and is unavailable to BWA until an
  accepted #215 successor exists;
- production DEX-3a correlation stays TBD/unavailable until its accepted producer
  seam exists. BWA-1 may use only the separately labeled test-only fake ingress.

If the current accepted Hook-contract family cannot represent browser adapters,
extend that contract through a separate reviewed contract delta; do not fork it
inside the extension.

### P0-C — BWA-1 Native Messaging + fake-provider transport

Implement the narrow transport before touching live provider DOMs:

- authenticated Native Messaging host;
- MV3 extension core;
- fake browser provider fixture;
- adapter-local `Play` / `Pause` that arms/disarms automatic wake delivery only;
- exact request/result correlation and replay rejection;
- restart/reconnect reconciliation;
- doctor diagnostics;
- no direct Git/process/filesystem authority;
- no task/execution pause, cancel, retry or successor-selection authority.

Gating: tracked BWA-1 source mutation requires an accepted BWA-0 contract and a
free mutable WIP slot. Its fake ingress is test-only and must not define or
impersonate the still-open production DEX-3a producer vocabulary.

Acceptance: deterministic fake-provider E2E proves duplicate delivery causes
zero duplicate model/mutation effect and transport loss remains distinct from
task failure.

### P0-D — BWA-2 ChatGPT Web + Gemini Web adapters

After BWA-1 conformance, implement two independent provider adapters in parallel
when WIP permits:

- ChatGPT ordinary web conversation;
- Gemini ordinary web conversation.

They do not call `/goal`. A-Conductor sends bounded task/continuation turns.
Each adapter must fail closed on unknown DOM/session/conversation identity and
must use a sacrificial/non-destructive conversation for first live proof.

### P0-E — BWA-3 zero-human-continuation acceptance

Prove the actual product outcome:

```text
one initial user goal
-> A-Conductor task/continuation authority
-> browser reasoner
-> CLI/Worker execution
-> durable result
-> automatic browser wake
-> bounded browser proposal/result
-> A-Conductor revalidation
-> NEXT_READY
-> repeat until COMPLETE or real human-only gate
```

Acceptance includes browser/extension restart and one context/session rotation
using the accepted rollover contract. When a wake follows delegated lane work,
recover the canonical WO-P1-374 pointer/process/result/Git evidence (including
historical WO260 aliases where they are the truthful original evidence) before
any redispatch. No human `continue` message is allowed in the successful path.

### P1-A — UI-1 Extension cockpit integration

Reuse WO257 P6/P7 Monitor projection/API for a **read-only first milestone**:

- goal/task progress display;
- current/next step;
- provider/harness health;
- evidence pointers.

UI-1 exposes no consequential control channel. The Extension keeps no
authoritative task or schedule state.

### P1-B — ACT-1 Command Gateway controls

Adapter-local `Play` / `Pause` for **automatic wake delivery** is transport
configuration and may ship in BWA-1 because it neither mutates task truth nor
controls the underlying execution.

No production Command Gateway source exists on current main; ACT-1 therefore
remains an architecture-gated future control seam. Only after that Gateway is
accepted may the Extension expose execution pause/resume/stop,
cancel/retry/recover/reassign or other consequential
typed command requests. Every such request goes through A-Conductor
task/claim/replay/ownership/authorization checks. No content script or popup
directly mutates a process, Git state, claim or durable task state.

### P1-C — SCH-1 scheduled Goal Trigger

Schedule UX is added only after the canonical A-Conductor scheduler/trigger
contract is accepted.

```text
Extension/Desktop schedule request
-> A-Conductor authorization + canonical schedule authority
-> durable goal trigger
-> router/executor
-> Browser Wake when a browser reasoner is selected
```

Chrome alarms/service-worker timers may be used only as best-effort UI wake
signals; they never become the durable scheduler or source of truth.

### P2 — Provider/council expansion and workflow packs

After two-provider Browser Wake conformance:

- Claude Web and other authorized browser providers;
- bounded multi-reasoner fan-out/council;
- optional helper AI for diagnostics;
- domain workflow packs.

The first reference workflow may be a content-commerce pipeline:

`trend research -> opportunity -> script -> assets -> video/subtitles -> QA ->
approval/publish -> analytics -> next cycle`.

That workflow is a task graph on top of A-Conductor. It does not change the
control-plane architecture or grant an extension authority to publish, price,
spend money or perform other consequential actions without the applicable
policy/approval gate.

### P3 — Headless/browser-farm operation

Only after desktop signed-in browser MVP is stable: evaluate dedicated profiles,
offscreen/headless operation and remote hosts. Multi-account/account-rotation
mechanisms must never be used to bypass provider quotas, restrictions or terms.

## 8. Success metrics

Primary product metric:

`human relay actions per accepted end-to-end goal = 0` for steps that are not explicitly human-only.

Supporting metrics:
- CLI-finished -> browser-wake latency p50/p95;
- browser-wake -> validated next-action latency;
- human `continue` messages per goal;
- duplicate wake delivery causing duplicate effect = 0;
- browser transport ambiguity causing blind retry = 0;
- invalid/stale browser proposal accepted = 0;
- recovery after browser/extension/native-host restart without user context reconstruction;
- provider adapter breakage detected by `doctor` before privileged action;
- roadmap throughput after Browser Wake compared with the pre-wake Zero-Relay baseline.
- scheduled goal fires exactly once under canonical scheduler authority; browser/Chrome restart does not erase the schedule.
- ordinary ChatGPT/Gemini adapter completes the reference flow without requiring provider-native `/goal` support.

Target acceptance for the first production-capable loop: three consecutive sacrificial goals complete from one initial command across at least two browser providers and one CLI executor, including one forced transport restart, with deterministic evidence and zero duplicate mutation/model effect.

## 9. Security / policy boundaries

- Native Messaging is preferred for privileged browser-to-local IPC; localhost HTTP/WebSocket is acceptable only for bounded prototypes and must bind loopback + authentication/capability token.
- Pin extension/native-host identity; never trust arbitrary web-page messages as privileged commands.
- Browser DOM/content is hostile/untrusted input. Validate schemas, size, event identity, goal/task/head and allowed action before execution.
- Never export, scrape, persist or relay browser cookies/session tokens. Authentication remains browser-held inside the signed-in session; any provider requiring exported session secrets is unsupported by this adapter design.
- Provider adapter capability does not imply authorization. `CAPABLE != READY != AUTHORIZED != ADMITTED` remains binding.
- Consumer/free plans must not be automated to evade quota, account or provider restrictions.
- Paid/API/PAYG executor use still requires the existing cost/approval policy.
- Extension or provider loss is transport loss; durable A-Conductor execution state remains authoritative.

## 10. Failure classes

Use existing project taxonomy where possible:
`NOT_EXPOSED`, `AUTH_REQUIRED`, `RATE_LIMITED`, `TRANSPORT_FAILURE`, `PERMISSION_FAILURE`, `RUNTIME_UNVERIFIED`, `COST_UNKNOWN` plus existing durable recovery classifications.

Browser-specific typed observations should remain adapters, for example:
`TAB_NOT_BOUND`, `DOM_CONTRACT_UNVERIFIED`, `CONVERSATION_MISMATCH`, `WAKE_DELIVERY_UNKNOWN`, `RESPONSE_CAPTURE_UNKNOWN`.
They must map into existing recovery/transport truth rather than create a new job state machine.
## 11. Research references / adoption status

- A-Wiki current hook system: `.claude/settings.json`, `scripts/hooks_runner.py`, `skills/awiki/a-loop/SKILL.md`, `skills/awiki/a-claim/SKILL.md`, `.claude/hooks/handoff-auto-export.sh` — **REUSE** semantics/policy.
- https://github.com/niawjunior/aipass-bridge — **WRAP/EXTEND patterns**: signed-in browser execution, MV3 bridge, stable local API, streaming, model/credit discovery, diagnostics, offscreen/headless operation.
- https://github.com/YosefHayim/ai-browser-bridge — **WRAP/EXTEND patterns**: multi-provider browser adapters, non-interactive request/result, conversation reuse and fan-out.
- https://github.com/escapeWu/chrome-agent-bridge — **REUSE design patterns**: Chrome Native Messaging + local agent bridge, local authentication and user-approved browser automation.
- Chrome Native Messaging / MV3 lifecycle documentation — **REUSE platform primitive**, not a custom socket framework by default.
- Community Stop/PermissionRequest notification and remote-approval hooks — **REUSE event and fail-closed approval patterns**, but replace human-notification-only flows with A-Conductor continuation where policy permits.

All copied source, if any is later selected, requires a fresh license/security/version audit and third-party notice treatment. This roadmap approves patterns, not source copying.

## 12. Implementation gates

Browser Wake source mutation is not authorized by this roadmap alone. Every node
must re-pin current `origin/main`, active Issue/WO/claims, reuse/owner-map truth
and its exact dependency class before mutation.

Node-specific gates:
1. **BWA-0 (docs/contracts only):** may start after WO446 acceptance. Open
   #215/Hook/DEX items are explicit dependency references, not silent assumptions.
2. **BWA-1 (fake-provider transport):** read-only shaping may run while BWA-0 is
   under review; tracked source mutation requires accepted BWA-0 plus a free
   mutable WIP slot. It uses BWA-0's test-only fake ingress and has no live
   provider, production DEX-3a producer, NEXT_READY, Git or filesystem authority.
3. **BWA-2 (live browser adapters):** additionally requires per-provider
   authorization/terms verdict, the latest accepted Hook contract, and the
   accepted DEX capabilities it actually consumes.
4. **BWA-3 (zero-human autonomous continuation):** requires an accepted #215
   automatic NEXT_READY successor plus accepted DEX-2a substrate supervision,
   production DEX-3a completion delivery, and the current DEX-2b receipt contract.
5. All source nodes use bounded work orders + isolated worktrees; RED-first fake
   extension/native-host tests precede live browser use; first live proof uses a
   sacrificial conversation/project and non-destructive task.
6. R2/R3 nodes require exact-SHA independent review + hosted CI, and every
   material boundary checkpoints durable state for session-independent recovery.

## 13. Exact next safe actions — accelerated 2026-09-21

1. Keep WO446 source-forbidden; finish only this two-file roadmap lane.
2. Freeze the reconciled candidate on top of
   `origin/main@0ce82be15355bf3af782cd488b54d77c475d285b`; verify exact two-file
   scope, UTF-8, references, secret hygiene and `git diff --check`.
3. Obtain a fresh qualified GLM-5.3 MAX independent exact-SHA
   architecture/security/reuse review plus exact-head hosted CI.
4. After WO446 acceptance, open **BWA-0 immediately** as a bounded DEX-3b
   browser-harness contract lane; do not wait idly for unrelated source lanes.
5. While BWA-0 is under review, shape the BWA-1 source layout/test matrix read-only.
   After BWA-0 acceptance and WIP admission, open **BWA-1** Native Messaging + MV3
   + fake-provider transport in a non-overlapping lane. Ship adapter-local
   Play/Pause as wake arm/disarm only; use test-only fake ingress and do not
   invent the production DEX-3a producer vocabulary or underlying task control.
6. Continue #215 / Hook repair / DEX predecessor work in their existing owners in
   parallel. Their acceptance gates BWA-2/BWA-3 live autonomy, not BWA-0/BWA-1.
7. After live gates pass, run BWA-2 ChatGPT/Gemini adapters and BWA-3
   zero-human-continuation E2E. Consequential controls use Command Gateway;
   scheduled goals use only an accepted canonical scheduler authority.

This ordering now explicitly separates **goal semantics**, **continuation
semantics**, **browser execution transport**, **operator UI**, and **schedule
authority**, while making Browser Wake a DEX-3b implementation family. Ordinary
ChatGPT/Gemini web chat can therefore participate without native `/goal`
support and without creating a shadow control plane.
