# Sunday Family Multi-Model Agent Harness Accelerator

Date: 2026-08-28
Status: ACTIVE PRIORITY PLAN
Parent: `docs/work-orders/WO-P1-087-sunday-family-agent-harness-accelerator.md`
Brand: **A-Sunday Conductor / Sunday Family**

## 1. Why this moves first

The largest current operator friction is not another UI feature: it is the human acting as the message bus between models. Repeatedly copying a prompt from GPT to GLM/Claude Code/ZCode, waiting, copying results back, and reconstructing state wastes time and makes continuity depend on chat context.

This accelerator therefore moves ahead of other new feature work. It should make every later engineering loop faster by turning models into selectable execution workers behind A-Sunday Conductor.

Safety fixes, open release correctness work, and already-owned Graph implementation remain independent P0 lanes and may continue without sharing mutable scope.

## 2. Sunday Family operating model

The existing Sunday Family brand remains the product identity. The new capability is represented as a family of coordinated roles, not as a separate product or vendor-branded shell.

```text
                         A-SUNDAY CONDUCTOR
                      Sunday Family Control Plane
                                  |
                    Goal / SSoT / Task Graph / Policy
                                  |
             +--------------------+--------------------+
             |                    |                    |
       Lead / Integrator     Implementation       Specialist / Review
           GPT-class          GLM/Claude-Code        future provider
             |                    |                    |
             +--------------------+--------------------+
                                  |
                        Evidence + Verification
                                  |
                       Repair / Continue / Done
```

Roles are capabilities, not permanent vendor assignments. GPT may lead today; a future provider may become eligible for the same role if evidence and policy allow it.

## 3. First harness: Claude Code style + GLM-5.3

The first coding execution lane should preserve the Anthropic/Claude Code harness the user likes while using a configurable Anthropic-compatible provider.

Preferred path:

```text
Conductor Task Packet
        |
        v
Claude Code CLI / agent harness
        |
        v
Anthropic-compatible Provider Adapter
        |
        v
GLM-5.3 (first configured provider)
        |
        v
repo edits / tests / structured result
        |
        v
Conductor verifies actual diff + tests + evidence
```

Why this path first:
- harness already provides an effective coding-agent interaction loop;
- Conductor does not need to recreate tool-use behavior immediately;
- non-interactive CLI execution is more robust and automatable than GUI copy/paste;
- the model endpoint remains swappable behind a provider profile;
- it is compatible with future quota-aware and failover routing.

Do not make ZCode Desktop or Claude Desktop GUI automation the core path. Desktop UI automation may be a last-resort/manual compatibility surface only.

## 4. Provider-neutral domain extension

Extend existing `Provider`, `Runtime`, `Agent`, `Capability`, and runtime-catalog seams with typed optional metadata. Do not create a parallel registry.

Target conceptual provider profile:

```text
ProviderProfile
- provider_id / display_name
- protocol_family            # anthropic_messages, openai_compatible, local, ...
- endpoint_ref               # non-secret configuration
- credential_ref             # secret reference only
- model profiles
- harness/runtime strategy   # claude_code_cli, direct_api, local_cli, ...
- capability evidence
- health observation + observed_at
- quota observation + reset window when supported
- trust/data-egress class
- cost class
- concurrency/capacity
- retry/fallback policy
- enabled
```

Model names are implementation metadata, never stable task capability IDs.

## 5. Secure configuration

The Settings surface may let the operator enter/change an endpoint and secret, but tracked configuration stores only safe metadata and a credential reference.

Required properties:
- secrets resolved at runtime from a private/OS-backed store;
- masked UI display;
- no secret echo to logs/task packets/diagnostics;
- explicit Test Connection action with bounded timeout;
- redaction before durable evidence;
- credential rotation does not require repository mutation.

The previously shared proxy credential must not be copied into any project file.

## 6. Third-party proxy policy

A proxy can be economically useful while still being a separate trust boundary.

Provider policy must distinguish at least:
- `FIRST_PARTY`
- `TRUSTED_THIRD_PARTY`
- `LOCAL`
- `UNKNOWN`

Task eligibility additionally checks data-egress sensitivity. A provider can be technically healthy and capable yet policy-ineligible for a task containing secrets/private sensitive material.

`CAPABLE != AUTHORIZED`.

## 7. Quota-aware routing

If the provider exposes a quota monitor, ingest it as an observation, not as scheduler truth.

Suggested normalized snapshot:

```text
QuotaSnapshot
- window_type
- limit
- used
- remaining
- reset_at / reset_in_seconds
- observed_at
- provenance
```

Routing can then prefer the cheapest/safest sufficient worker while preserving headroom for harder tasks. Unknown quota never becomes an invented numeric value.

Example policy direction:
- healthy + high headroom -> implementation/research allowed;
- lower headroom -> reserve provider for higher-value tasks;
- exhausted/rate-limited -> route eligible fallback or wait according to policy;
- auth/transport failure -> typed provider failure, not code failure.

No design may attempt to bypass upstream limits or access controls.

## 8. Task packet contract

Conductor must generate a bounded packet from durable state rather than paste a raw chat transcript.

Minimum packet:
- task/work-order ID;
- goal and why;
- repo/worktree/branch/HEAD/dirty state;
- authoritative files to read first;
- exact allowed and forbidden scope;
- dependencies/blockers;
- acceptance criteria;
- verification commands/scenarios;
- evidence required;
- checkpoint/handoff destination;
- retry/stop conditions.

The receiving harness should need no hidden chat context.

## 9. Parallel execution rule

Parallelism comes only from independent READY tasks.

```text
Task Graph
  |
  +-- READY-A -> Worker/Provider A -> isolated worktree/scope
  +-- READY-B -> Worker/Provider B -> isolated worktree/scope
  +-- BLOCKED-C waits for A
```

Never launch two sub-agents into the same mutable files/worktree without explicit coordination. Provider capacity and quota are additional constraints, not permission to ignore file ownership.

## 10. Verification / review-repair loop

A provider reporting `DONE` remains a claim.

```text
DISPATCH
  -> collect result
  -> inspect actual repo state
  -> deterministic tests/checks
  -> independent review where material
  -> PASS ? checkpoint/continue : repair task
```

The preferred early pairing is:
- GPT-class lead: architecture, synthesis, integration review, difficult trust-boundary decisions;
- GLM through Claude Code harness: bounded implementation, tests, deterministic repair, repository archaeology;
- deterministic tools: authoritative verification.

This is a default policy, not a permanent vendor rule.

## 11. Failure model / circuit breaker

Provider/harness failures should be typed separately from task/code failures:
- `PROVIDER_UNAVAILABLE`
- `AUTH_FAILED`
- `RATE_LIMITED`
- `QUOTA_EXHAUSTED`
- `TRANSPORT_LOST`
- `HARNESS_FAILED`
- `EXECUTION_STATE_UNKNOWN`
- `POLICY_DENIED`

Retries reconcile durable execution state first. A lost transport must never blindly launch a duplicate side effect.

## 12. UI — Sunday Family Models & Agents

Extend the existing command-center UI. Do not create a second dashboard.

Proposed Settings/Advanced section:

```text
MODELS & AGENTS

LEAD / ORCHESTRATOR
  GPT / current lead surface

SUB-AGENT PROVIDERS
  GLM Shared Proxy        READY     Claude Code Harness
    model                 GLM-5.3
    effort                Max
    quota                 observed / reset countdown
    trust                 Trusted Third Party
    concurrency           1
    [Edit] [Test] [Disable]

  + Add Provider
```

Display rules:
- use Sunday Family visual language: near-black, compact mono data, thin borders, restrained semantic accents;
- never show a full secret;
- configured != READY;
- quota/health must include observation freshness/provenance;
- selection reason should be inspectable (`why this provider?`);
- keep normal main screen uncluttered; detailed provider configuration belongs in Settings/Advanced.

## 13. Delivery sequence

### AHA-0 — C0 vocabulary gate
Accept/reconcile PR #110 so actor capability, runtime supply, and policy/authority are distinct before adding provider behavior.

### AHA-1 — Provider/Harness contracts
Docs/schema/domain design only. Define provider profile, harness strategy, trust class, health/quota observations, typed failures, and credential references. No live network execution.

### AHA-2 — Secure provider configuration
Local storage/credential-reference seam, masked UI/service API, validation, health/quota normalizer. Use fake providers in tests first.

### AHA-3 — Claude Code harness adapter
Injectable runner with non-interactive structured output, bounded timeout/output, explicit working directory/task packet, environment allowlist, redaction, and fake-backend tests. GLM Anthropic-compatible profile is first real configuration.

### AHA-4 — Durable dispatch integration
After compatible GE-6/GE-7/durable-execution gates: stable execution identity, claim/gate, duplicate protection, transport-loss reconciliation, evidence storage.

### AHA-5 — GPT <-> GLM review/repair loop
One vertical repository slice: GPT plan/review, GLM implement/repair, deterministic verifier, durable checkpoints.

### AHA-6 — Parallel READY-task execution
Run two independent task packets concurrently in isolated scopes/worktrees; prove no ownership collision and bounded provider capacity/quota handling.

### AHA-7 — Operator UI
Sunday Family Models & Agents configuration/status, selection reason, quota/health/trust, disable/fallback controls.

### AHA-8 — Additional providers
OpenAI-compatible, Anthropic first-party, Gemini, local/Ollama/llama.cpp, and other adapters only after the provider contract proves stable.

## 14. Acceptance milestone

The accelerator proves value when the user can issue one repository goal and observe a complete bounded loop where:

1. Conductor recovers SSoT and creates the task packet;
2. Conductor selects the GLM/Claude-Code harness from policy/capability/health;
3. the harness works in an isolated authorized scope;
4. result/diff/tests return without human copy/paste;
5. GPT/integrator reviews evidence;
6. failures produce a bounded repair dispatch rather than a new manual prompt;
7. task/checkpoint state survives session/model rotation;
8. no secret appears in tracked files/logs;
9. another provider could replace GLM without redesigning the task model.

## 15. Interaction with current open work

- PR #110 is a direct prerequisite for the provider capability vocabulary and should be reviewed first.
- PR #104 remains the owner of GE-6 scheduler semantics; the accelerator must not fork a substitute scheduler.
- PR #108 remains an installer/release safety lane and must not be deleted or mixed into this feature.
- North Star work remains the integration home for runtime/execution-fabric concepts; new provider work should reconcile with it rather than duplicate it.

This priority switch changes what new feature work starts next. It does not invalidate safety gates or ownership.
