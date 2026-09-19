# Browser Wake / Continuation Relay Roadmap — 2026-09-15

Status: RECONCILED ROADMAP CANDIDATE / DOCS-ONLY / SOURCE MUTATION FORBIDDEN
Work order: `WO-P1-240`
Durable issue: GitHub #320
Classification: `REUSE + WRAP + EXTEND`; `NEW` only for a proven browser-transport/provider-adapter gap.

## 0. 2026-09-19 reconciliation against current authority

This roadmap was originally frozen on 2026-09-15. It is now reconciled against
`origin/main@95c4b9e78003c4b61083650d1698c6661f9bb545` and the newer accepted/open authorities:

- WO-P1-257 / Issue #365 is merged and owns the Hook/STM/Monitor/Web+Extension/Command-Gateway architecture. Browser Wake consumes that architecture; it does not create a second extension state model or command channel.
- WO-P1-258 / Issue #368 / PR #371 is the open HOOK-0 Hook Contract v1 lane. Browser Wake must re-pin the final accepted contract before implementation and extend it only through a bounded follow-up if browser adapters need additional source/capability vocabulary.
- WO-P1-259 / Issue #369 / PR #373 is the open context-rollover guard lane. New-chat/session resume belongs to that continuity contract; browser code must consume its verdict/pointers rather than invent another resume state machine.
- WO223 / PR #319 is merged. ZRA-3 remains the continuation-semantics dependency and is not accepted merely because browser wake transport exists.
- Ordinary ChatGPT/Gemini web chat does not need or provide a native `/goal`. The durable goal/task graph remains A-Sunday Conductor/A-Wiki authority; the browser adapter receives only bounded task/continuation turns and returns untrusted proposals/results.
- Scheduled goals are a control-plane feature, not Chrome-alarm authority. An Extension UI may request/show schedules only after a canonical scheduler contract exists; a browser alarm may at most provide a non-authoritative wake hint.

The current delta therefore narrows WO240 from a broad new extension protocol into the missing **Browser Chat Harness Adapter** layered on the accepted Hook/Monitor/Command-Gateway/continuity authorities.

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

Therefore Browser Wake is a missing **transport adapter + conversation binding + response ingestion seam**, not a new orchestrator.

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
privacy, causation and adapter capability discovery reuse the accepted WO257/HOOK-0
contract family. Consequential operator commands reuse the later A-Conductor
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

### P0-A — Finish current continuation/contract gates

Run these as independent accepted-authority lanes; WO240 does not mutate them:

1. ZRA-3 / NEXT_READY continuation must reach accepted exact-SHA state.
2. HOOK-0 / WO258 must freeze and be accepted; Browser Wake then binds to the
   final Hook Contract rather than inventing its own event vocabulary.
3. Context rollover / WO259 must be accepted for safe ordinary-chat rotation and
   new-chat recovery.

Browser Wake implementation may be designed in parallel, but live automation
must not claim these open candidates as accepted contracts.

### P0-B — BWA-0 Browser Chat Harness Contract

Create a bounded follow-up Work Order after the relevant contracts are pinned.

Define only the missing browser execution/harness semantics:

- exact provider + adapter version/capability discovery;
- exact conversation binding and non-authoritative locator;
- bounded task/continuation input;
- stable response-completion/result capture;
- proposal/result envelope back to A-Conductor;
- DOM/selector/session/version drift classification;
- event/dedupe mapping to Hook Contract;
- context-rollover handoff mapping;
- no goal store, scheduler, claim store, retry engine or completion authority.

If HOOK-0 source/capability enums cannot represent browser adapters, extend that
contract through a separate reviewed contract delta; do not fork it inside the
extension.

### P0-C — BWA-1 Native Messaging + fake-provider transport

Implement the narrow transport before touching live provider DOMs:

- authenticated Native Messaging host;
- MV3 extension core;
- fake browser provider fixture;
- exact request/result correlation and replay rejection;
- restart/reconnect reconciliation;
- doctor diagnostics;
- no direct Git/process/filesystem authority.

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
using the accepted rollover contract. No human `continue` message is allowed
in the successful path.

### P1-A — UI-1 Extension cockpit integration

Reuse WO257 P6/P7 Monitor projection/API for:

- goal/task progress display;
- current/next step;
- provider/harness health;
- evidence pointers;
- Play/Pause/Resume/Stop controls as requests only.

The Extension keeps no authoritative task or schedule state.

### P1-B — ACT-1 Command Gateway controls

Pause/cancel/retry/recover/reassign and later Play/Resume requests go through the
A-Conductor Command Gateway with task/claim/replay/ownership/authorization
checks. No content script or popup directly mutates a process, Git state, claim
or durable task state.

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
- Never export cookies/session tokens from the browser unless a provider explicitly requires an accepted supported mechanism.
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

Browser Wake source mutation is not authorized by this roadmap alone. Before each implementation node:
1. re-pin current `origin/main`, active Issue/WO/claims and provider terms;
2. re-pin final accepted WO257/HOOK-0/context-rollover contracts and the relevant ZRA continuation predecessor;
3. run A-Wiki reuse/owner-map gate;
4. create a bounded work order and isolated worktree;
5. define provider-specific permission/DOM failure model;
6. RED-first deterministic fake extension/native-host tests before live browser use;
7. use sacrificial browser conversation/project and non-destructive task first;
8. exact-SHA independent review + hosted CI for R2/R3 nodes;
9. checkpoint durable state so a new session never needs chat reconstruction.

## 13. Exact next safe actions — reconciled 2026-09-19

1. Keep WO240 docs-only. Do not implement browser/extension source under this claim.
2. Freeze this reconciled two-file candidate on top of
   `origin/main@95c4b9e78003c4b61083650d1698c6661f9bb545`; verify exact scope,
   UTF-8, references and `git diff --check`.
3. Obtain independent exact-SHA architecture/security/reuse review and hosted CI
   appropriate to this docs-only R2 candidate.
4. After acceptance, fold only the minimal Browser Chat Harness dependency into
   global roadmap authority; do not duplicate WO257.
5. When ZRA-3, HOOK-0 and context-rollover contracts are accepted, open **BWA-0**
   as the next bounded implementation contract. It owns browser-harness semantics
   only, not Goal/Task/Scheduler/Monitor/Command authority.
6. Follow with BWA-1 fake-provider Native Messaging transport, then BWA-2
   ChatGPT/Gemini adapters, then BWA-3 zero-human-continuation E2E.
7. Add Extension cockpit controls only through WO257 Monitor/Command Gateway.
   Add scheduled goals only through an accepted canonical scheduler contract.

This ordering now explicitly separates **goal semantics**, **continuation
semantics**, **browser execution transport**, **operator UI**, and **schedule
authority**, so ordinary ChatGPT/Gemini web chat can participate without native
`/goal` support and without creating a shadow control plane.
