# Provider + Harness Contract

Status: AHA-1 binding contract / WO-P1-088
Version: `provider-harness/v1`

## Purpose

Define how A-Sunday Conductor describes a model/provider and a coding-agent harness without making any vendor, model, proxy, CLI, or GUI the task authority.

The first intended real configuration is a Claude Code CLI / Anthropic-style harness backed by a user-configured Anthropic-compatible provider for GLM-5.3. **GLM-5.3 is the first provider configuration, not an architectural dependency**.

This contract is configuration/observation/dispatch shape only. It does not implement network calls, subprocess launch, scheduler dispatch, retries, credential storage, or model routing.

## Existing authority reused

- A-Wiki owns canonical task/actor intent and durable brain policy.
- `capability-vocabulary-bridge/v1` separates task/actor requirement, execution supply, and policy/authority.
- A-Conductor `task-contract/v1` owns bounded target/scope/security/budget/verification requirements.
- Durable job/execution/recovery contracts own execution identity, claims, retry/recovery, checkpoints, and evidence.
- Runtime/tool adapters are replaceable hands.

Therefore:

> **CAPABLE != AUTHORIZED**

A capable model/provider is not eligible until project identity, mutation authority, privacy/egress policy, health and task gates also pass.

## Configuration is not readiness

`provider-profile/v1` is static/non-secret configuration. It may say which protocol, harness strategies, models and trust class are configured.

`provider-observation/v1` is separately observed evidence.

> **CONFIGURED != READY**

A configured provider with missing/stale/failed observation must not be promoted to AVAILABLE by assumption.

## Provider profile

A profile contains:
- stable `provider_id` and display metadata;
- `protocol_family` such as `ANTHROPIC_MESSAGES`, `OPENAI_COMPATIBLE`, or `LOCAL`;
- non-secret `endpoint_ref`;
- opaque `credential_ref` only;
- explicit trust class and egress boundary classification;
- allowed fixed harness strategies;
- model profiles and actor-capability evidence metadata;
- bounded concurrency metadata;
- enabled/disabled configuration.

The schema intentionally has no API-key, token, password, secret-value, raw authorization header, or credential-value field. It also has no arbitrary metadata catch-all that could smuggle secret-bearing payloads. Secret resolution happens outside tracked configuration at execution time.

Actor/model capability evidence is not execution supply. A model being marked capable of `deep-reasoning` does not imply shell, repository, tests, semantic-code, or mutation access.

## Provider observation and quota

Health is evidence with freshness and provenance. Supported typed states include `UNKNOWN`, `AVAILABLE`, `DEGRADED`, `UNAVAILABLE`, `AUTH_FAILED`, `RATE_LIMITED`, and `QUOTA_EXHAUSTED`.

Quota is optional evidence. When supported, it may carry window type, limit, used, remaining and reset timing. Missing quota stays unknown; it must never be treated as unlimited or zero. Quota-aware routing may preserve headroom or select an eligible fallback, but it must not bypass provider limits or access controls.

Trust, egress boundary, health, and task authority remain independent: a technically AVAILABLE external provider can still be policy-ineligible for the task. The provider profile describes where data would cross, not permission to cross it.

## Harness strategy

A harness strategy is a fixed adapter class, not arbitrary command text. Initial enum values are:
- `CLAUDE_CODE_CLI`
- `DIRECT_API`
- `LOCAL_CLI`

For the first coding lane, `CLAUDE_CODE_CLI` is preferred because it preserves the Anthropic/Claude Code agent harness while allowing the provider endpoint/model configuration to be replaceable.

The future adapter owns the exact approved executable/arguments/environment allowlist. A task/model cannot inject executable, argv, shell, or arbitrary environment fields through `harness-dispatch/v1`.

## Harness dispatch

A dispatch references existing authority rather than embedding a conversation:
- stable `execution_id`;
- `task_contract_ref`;
- exact project/worktree/branch/HEAD identity;
- provider/model/harness identity;
- explicit `READ_ONLY` or `PROJECT_MUTATION` intent;
- bounded timeout and output budget;
- evidence destination reference.

**No raw prompt or transcript** is part of the dispatch contract. The adapter resolves the authorized task contract/checkpoint packet through a bounded internal seam.

There is also no raw command, argv, shell, executable, arbitrary environment field, or generic metadata payload.

## Reliability and completion

This provider layer inherits the resilient execution invariant:

> **TRANSPORT FAILURE != EXECUTION FAILURE**

A CLI/API/proxy disconnect does not prove the underlying execution failed. Reconciliation must inspect durable execution identity/evidence before any retry.

A **provider reporting DONE is evidence, not completion authority**. Conductor verification and applicable review gates remain authoritative.

## No orchestration duplication

**No second scheduler** is created here. This contract also creates no second task state machine, retry authority, worker registry, model router, memory store, claim system, or provider-specific work-order format.

GE scheduler/dispatch and durable execution integration remain separate owned work. A future live adapter must enter through those accepted seams rather than bypassing them.

## Third-party proxy boundary

An Anthropic-compatible proxy is a protocol-compatible provider, not necessarily Anthropic-operated. The profile must expose trust class and egress boundary so policy can deny a healthy provider when task privacy does not permit that boundary. Boundary metadata never grants permission by itself.

Do not place private sensitive data, repository secrets, credential files, auth tokens, or screenshots containing credentials into provider task context merely because the provider is inexpensive or has available quota.

## UI consequence

The Sunday Family `MODELS & AGENTS` surface may display configured provider/model/harness metadata plus fresh health/quota/trust evidence. Full credentials are never displayed or copied. `CONFIGURED`, `AVAILABLE`, and `AUTHORIZED` remain visually/conceptually distinct.

## Next implementation seam

AHA-2 may implement secure local provider configuration/secret references and fake provider health/quota normalization. Live provider calls and Claude Code process execution remain gated until those pieces are verified and the durable dispatch integration seam is ready.
