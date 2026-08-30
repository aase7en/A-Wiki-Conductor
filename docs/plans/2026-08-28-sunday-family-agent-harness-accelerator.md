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

### AHA-0 — C0 vocabulary gate [COMPLETE]
PR #110 merged as `6487cb2`; actor capability, runtime supply, and policy/authority are now explicitly distinct before provider behavior is added.

### AHA-1 — Provider/Harness contracts [COMPLETE]
PR #112 merged as `c3ca84c`; provider profile, harness strategy, trust/quota observations, typed failure vocabulary, credential references, and bounded dispatch schema are accepted.

### AHA-2 — Secure provider configuration [COMPLETE]
PR #114 merged as `ca4cd98`; non-secret provider configuration, safe endpoint validation, opaque credential references, same-control-DB persistence, and injected health/quota observation are accepted.

### AHA-3 — Claude Code harness adapter [COMPLETE]
PR #116 merged as `ab28dc7` after Windows/Ubuntu/macOS CI green. The adapter is injected-runner/read-only only, validates task packet path/size/SHA, requires fresh provider readiness, bounds output, and redacts evidence. No live provider call was required for acceptance.

### AHA-4 — Durable dispatch integration [COMPLETE]
GE-6 scheduler correctness merged via PR #104 (`023c7b65`), and durable graph-dispatch integration merged via PR #119 (`5cc417c9`) after 3-OS CI green. Stable execution identity, duplicate protection, transport-loss reconciliation, and bounded evidence now wrap the accepted durable job-control seams; AHA-4A extends this with worker leases/fallback rather than creating a second scheduler.

### AHA-4A — Worker lease broker + automatic fallback [ACTIVE / PROTECTED PR #131]
WO-P1-102 / draft PR #131 owns the current implementation in isolated worktree `A-Wiki-Conductor-aha4a-lease`. That worktree has protected local changes beyond the remote PR head, so other agents must not rebind, overwrite, or mutate its scope. Extend the existing worker registry/assignment authority with atomic leases, eligibility preflight, ownership/scope checks, and policy-driven fallback across eligible semantic workers. A busy/owned/dirty/incompatible worker is skipped, never rebound or interrupted. Eligible shell/read-only work may fall back to RDC; otherwise queue/wait. See `docs/plans/2026-08-28-worker-auto-fallback-and-glm-benchmark.md`.

### AHA-4B — Lease heartbeat + stale-owner recovery
Add heartbeat/expiry, quarantine for ambiguous dirty state, stale-owner reconciliation, fairness, and backpressure before broad autonomous parallelism. Recovery must reconcile actual runtime/worktree state before lease reuse.

### AHA-5 — GPT <-> GLM review/repair loop
One vertical repository slice: GPT plan/review, GLM implement/repair, deterministic verifier, durable checkpoints.

### AHA-6 — Parallel READY-task execution
Run two independent task packets concurrently in isolated scopes/worktrees through the lease broker; prove no ownership collision and bounded provider capacity/quota handling.

### AHA-6A - Automatic provider runtime assembly [COMPLETE - WO-P1-114 / PR #153]
Accepted provider SQLite state, A-Wiki Drive secret-reference boundary and supervised Claude backend assembly are merged. Exact-head and post-main CI are green; independent GLM review found zero P0/P1/P2 defects. This milestone does not yet authorize automatic live provider dispatch.

### AHA-6A.1 - Production provider admission/runtime wiring [COMPLETE - WO-P1-115 / PR #155]
Before elastic capacity or operator UI, wire the accepted WO-P1-114 resolver into an authorized runtime assembly that can locate the private Drive root without hardcoding, produce fresh provider health plus the complete required quota tuple, and serialize or atomically reserve same-provider admission across concurrent batches. Reuse existing authorities; do not add a second capacity store/semaphore, quota model, provider registry or secret system. Live dispatch stays fail-closed until all three gates are deterministic and tested.

### AHA-6B - Elastic worker capacity
Only after fixed-pool lease correctness and the provider execution assembly boundary are proven, allow policy-bounded creation of additional worker instances when all eligible workers are leased. New capacity must inherit the same health, ownership, scope, checkpoint, and release gates.

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

- PR #110 / AHA-0 is merged (`6487cb2`); new provider work must consume that accepted vocabulary contract rather than redefining it.
- PR #104 / GE-6 scheduler semantics merged as `023c7b65`; subsequent accelerator work must reuse that accepted scheduler and must not fork a substitute.
- PR #108 installer target-ownership safety merged as `bbb392b1`; its installer/release boundary remains separate from provider/harness feature scope.
- North Star work remains the integration home for runtime/execution-fabric concepts; new provider work should reconcile with it rather than duplicate it.

This priority switch changes what new feature work starts next. It does not invalidate safety gates or ownership.
