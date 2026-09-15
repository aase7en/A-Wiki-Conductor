# Browser Wake / Continuation Relay Roadmap — 2026-09-15

Status: PROPOSED / P0 ACCELERATOR / DOCS-ONLY SHAPING
Work order: `WO-P1-240`
Durable issue: GitHub #320
Classification: `REUSE + WRAP + EXTEND`; `NEW` only for the minimal missing transport seam.

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
sunday-family-protocol        # schemas only; event/action envelopes
sunday-family-native-host     # authenticated Native Messaging <-> Conductor adapter
sunday-family-extension-core  # MV3 lifecycle, tab/session binding, popup/cockpit
provider-chatgpt-web          # DOM/message adapter
provider-gemini-web           # DOM/message adapter
provider-claude-web           # later after MVP
provider-aipass-web           # reuse/wrap aipass-bridge patterns subject to authorization
wake-relay                    # consumes Conductor continuation events; sends compact turn
conversation-index            # non-authoritative provider conversation locators
sunday-family-doctor          # connectivity/selector/session/capability diagnostics
embedded-helper-ai            # optional UX/diagnostic classifier; never privileged authority
```

`embedded-helper-ai` may summarize diagnostics, classify a broken selector, suggest a provider, or explain operator state. It must never bypass A-Conductor claim/mutation/cost/authorization gates or decide project completion.
## 6. Continuation protocol

The Browser Wake path consumes existing durable truth and emits a compact synthetic continuation turn. Example conceptual envelope:

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

## 7. Priority order — optimize for leverage

The guiding rule is: finish the smallest prerequisite that makes every later roadmap node faster, then immediately exploit it.
### P0-A — Finish the current WO223 RE2-A critical repair

Do not abandon a nearly-complete R3 lane. Close the remaining typed parser defect, freeze/review/CI, update PR #319 by accepted non-force ancestry only, merge and post-main verify.

Why first: every continuation layer depends on trustworthy exact result/review identity. Building Browser Wake on top of a still-open duplicate-effect/recovery defect would automate unsafe continuation.

### P0-B — Release Phase-D / WO205 and WO227 / ZRA-3

Complete the accepted-result -> existing GoalCloseout composition, then safe `NEXT_READY` continuation under existing lifecycle authority.

Why second: **ZRA-3 is the semantic continuation engine.** Browser Wake should transport a continuation decision to/from a browser reasoner; it must not invent its own definition of NEXT_READY, retry or COMPLETE.

### P0-C — Browser Wake Relay MVP

Immediately after the relevant ZRA-3 contract is accepted, implement the smallest browser wake path before broad ZRA-4/ODP expansion:

1. one normalized continuation-event projection from existing A-Conductor job/execution events;
2. Sunday-Family Native Messaging host;
3. one MV3 extension core;
4. ChatGPT Web adapter + Gemini Web adapter as the first two independent providers;
5. exact conversation binding, wake/send, stable-response capture;
6. structured proposal return to A-Conductor;
7. `doctor` diagnostics and fail-closed selector/session detection.

Acceptance pilot: **one initial user goal** -> browser reasoner -> one CLI/Worker task -> result -> automatic browser wake -> browser review/next decision -> next execution -> deterministic COMPLETE, with zero human `continue` messages.

### P0-D — Normalize lifecycle hooks into the existing event fabric

REUSE A-Wiki hook classifications and provider lifecycle events. Add thin adapters only:
- Kilo session idle/error/permission/result;
- Claude Code Stop/Notification/PermissionRequest where supported;
- ZCode/A-Loop SessionStart/Stop continuation signals;
- SundayWorker/RDC process/result transitions;
- CI completion events.

These become observations feeding existing A-Conductor durable jobs/events. Do not create a generic second event-store authority.
### P0-E — ZRA-4 bounded parallelism on top of Browser Wake

After the one-goal/one-lane wake E2E is accepted, enable existing ZRA-4 bounded parallel dispatch and fan-in. Browser AI can act as planner/adjudicator, but A-Conductor remains the READY/WIP/lease authority.

This ordering makes parallelism useful immediately: multiple CLI lanes can finish independently, fan in, wake the browser reasoner once with bounded evidence, and receive the next decision without human relay.

### P1 — Expand provider adapters and council/fan-out

Add adapters only after two-provider MVP proves the abstraction:
- Claude Web;
- AiPASS / ThAI PASS where current terms/authorization permit;
- other consumer browser providers when a concrete use case exists.

Support bounded fan-out/council use: one event may ask several browser reasoners independently, then return a normalized result set to A-Wiki/A-Conductor adjudication. Partial provider failure must not erase successful results.

### P1 — Package and embedded helper AI

Ship Sunday-Family Extension as a versioned package with module capability discovery. Embedded helper AI may provide local diagnostics, selector-repair suggestions, summary/compression and operator UX. Prefer small/local/free models for these non-authoritative tasks.

### P2 — ODP integration

Treat eligible browser AI surfaces as decision-provider candidates in the existing capability-first ODP model. Keep role/capability first, provider/model second. Runtime selection remains A-Conductor; model-policy intent remains A-Wiki.

### P2 — Remote human approvals and mobile cockpit

Extend `operator.v1` and Sunday-Family UI for genuine `AUTH_REQUIRED` / `COST_APPROVAL_REQUIRED` / destructive-operation approvals. Reuse Web Push/ntfy-style patterns where useful; do not wake humans for deterministic safe continuation.

### P3 — Headless/browser-farm operation

Only after desktop signed-in browser MVP is stable: evaluate dedicated profiles, Docker/noVNC/offscreen keepalive and remote hosts. Multi-account/account-rotation mechanisms must never be used to bypass provider quotas, restrictions or terms.
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
2. prove the relevant ZRA predecessor is accepted;
3. run A-Wiki reuse/owner-map gate;
4. create a bounded work order and isolated worktree;
5. define provider-specific permission/DOM failure model;
6. RED-first deterministic fake extension/native-host tests before live browser use;
7. use sacrificial browser conversation/project and non-destructive task first;
8. exact-SHA independent review + hosted CI for R2/R3 nodes;
9. checkpoint durable state so a new session never needs chat reconstruction.

## 13. Exact next safe actions

1. **Critical path remains WO223 RE2-A.** Close its remaining in-scope typed parser defect, verify, freeze, independent R3 rereview, CI, PR #319 update/merge/post-main.
2. In parallel, review this WO240 docs candidate only; do not let it take a mutable source lane from WO223.
3. After WO223 acceptance, release/execute Phase-D WO205, then WO227/ZRA-3 according to live Issue #214 authority.
4. At ZRA-3 acceptance, open the Browser Wake MVP implementation WO: Native Messaging host + MV3 core + ChatGPT/Gemini adapters + doctor + one-goal E2E.
5. Only after that E2E passes, accelerate ZRA-4/ODP/provider expansion using the new wake channel.

This ordering deliberately builds the **continuation semantics first, wake transport second, parallel scale third**. It maximizes leverage while preserving one authority for each responsibility.
