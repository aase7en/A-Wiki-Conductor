# Kilo CLI vs Claude Code CLI harness decision for A-Sunday Conductor

Status: DECISION REFERENCE / WO-P1-244 / DOCS-ONLY
Date: 2026-09-15
Issue: #325
Baseline: origin/main@82d3aabe352d071a676db5bb6b9cbfeb5dcda05b
Owner: GPT-5.6 Sol integrator

## Decision

Use an executor-neutral A-Sunday Conductor control plane. Do not choose one CLI as the project authority.

Current operational default:

1. Use Kilo CLI + CoinTH GLM-5.3 for high-token GLM labor when the route is healthy.
2. Keep the existing Claude Code path as an alternate heavyweight harness, but only promote it to production lanes after route/auth/liveness is proven on this Windows runtime.
3. Implement future Kilo support as a thin `KiloJobBackend` conforming to the existing `JobExecutionBackend`/durable supervised execution authority.
4. Never create a second job store, scheduler, provider registry, claim/lease authority, review authority, or lifecycle engine for either harness.

Rationale: local runtime evidence shows Kilo CLI already executed CoinTH GLM-5.3 lanes and produced useful write/review work, while the direct Claude Code + CoinTH/GLM route remained unverified because current Claude Code configuration routes through a local gateway/helper that did not complete smoke tests. Claude Code has stronger documented structured/headless primitives, but those primitives are not acceptance evidence until the local route is proven.

## Sources and evidence classes

### Repo authority

- `00-AGENT-ENTRY.md` requires actual Git/runtime/claim verification before mutation.
- `docs/adr/GE-0008-conductor-pivot-executor-neutral-control-plane.md` makes A-Sunday Conductor the vendor-neutral quota/cost-aware execution control plane.
- `docs/contracts/provider-harness.md` says provider/model/harness identity is configuration/observation shape, not execution authority.
- `docs/agent-collab/CAPABILITY_MATRIX.md` already records GPT-5.6 Sol as integrator and GLM-5.3 via accepted CLI routes as labor.

### Current Windows runtime observations

- Kilo executable used during this session: `kilocode.kilo-code-7.6.2-win32-x64\bin\kilo.exe`.
- Proven Kilo route: `cointh-glm/glm-5.3` produced previous WO223/RE2-A implementation and review evidence.
- Kilo quota/liveness evidence: `kilo roll-call` returned `[1308] Usage limit reached for 5 hour` with reset `2026-09-15 19:26:26`.
- CoinTH quota endpoint evidence: `GET https://cointh.com/glm/api/quota` returned `HTTP 403` for currently discovered A-Wiki/Kilo credential refs; classify as `AUTH_REQUIRED / ENTITLEMENT_MISMATCH`, not as quota proof.
- Claude Code installed version observed earlier: `2.1.178`; direct Claude Code + GLM proxy smoke was not accepted because no JSON result/sentinel returned before timeout.

### Public source evidence

- Kilo supports CLI configuration and custom providers using `provider-id/model-id`; its docs describe provider config, model choice, MCP, permissions, and environment overrides. Sources: https://kilo.ai/docs/code-with-ai/platforms/cli and https://kilo.ai/docs/code-with-ai/agents/custom-models
- Kilo supports OpenAI-compatible custom providers and endpoint URLs; an issue response says the CLI bundles `@ai-sdk/openai-compatible` as fallback. Sources: https://github.com/Kilo-Org/kilocode/blob/main/packages/kilo-docs/pages/ai-providers/openai-compatible.md and https://github.com/Kilo-Org/kilocode/issues/6315
- Kilo MCP tools are automatically available once configured, and large MCP servers can add context pressure. Source: https://kilo.ai/docs/automate/mcp/using-in-cli
- Kilo permissions support allow/ask/deny rules. Source: https://kilo.ai/docs/customize/agent-permissions
- Claude Code CLI supports `-p/--print`, `--output-format json|stream-json`, `--model`, `--permission-mode`, `--allowedTools`, `--disallowedTools`, `--permission-prompt-tool`, `--resume`, and `--continue`. Source: https://docs.anthropic.com/en/docs/claude-code/cli-usage
- Claude Code MCP usage requires explicitly allowed MCP tools and can use a permission-prompt MCP tool. Source: https://docs.anthropic.com/ja/docs/claude-code/sdk
- Claude Code LLM gateway docs describe centralized auth, usage tracking, cost controls, audit logging, and model routing through gateway/proxy configuration. Source: https://docs.anthropic.com/en/docs/claude-code/llm-gateway
- Claude Code issue tracker contains reports that headless runs can return exit 0/success-like envelopes despite permission denial or API rate-limit prose; treat those as external reports, not project truth, but design A-Conductor to never rely on exit code alone. Sources: https://github.com/anthropics/claude-code/issues/76867 and https://github.com/anthropics/claude-code/issues/79500

## Decision matrix

| Criterion | Kilo CLI + GLM | Claude Code CLI + GLM proxy | A-Conductor decision |
|---|---|---|---|
| Current local proof | Proven enough for GLM work; also exposed rate-limit and permission-friction modes | Protocol-compatible in principle but local route unverified | Prefer Kilo now; keep Claude gated |
| Model/provider neutrality | Strong with custom provider config and `provider/model` naming | Strong if Anthropic-compatible gateway/helper is healthy | Both are adapters, not authority |
| Headless reliability | Worked, but sessions can stall or hit memory/board permission requests | Rich headless flags, but public issues report misleading success/permission behavior | Require sentinel + artifact + Git/test verification for both |
| Structured output | Mostly prompt/sentinel discipline unless wrapper adds schema | Better documented JSON/stream-json surfaces | Add A-Conductor result schema outside harness |
| Permissions | Allow/ask/deny exists; MCP can add unwanted tools/context | Fine-grained CLI flags and permission-prompt tool exist | Generate deny-first profiles per lane |
| Worktree isolation | A-Conductor should create/pin worktrees itself | Do not delegate worktree authority to CLI | Conductor owns worktree/HEAD/claim |
| Quota/cost | Kilo roll-call gives practical liveness; CoinTH quota API still auth-blocked | Depends on gateway/helper route; not proven | Route only after quota/health proof |
| Resume/recovery | Needs Conductor process/session capture | Claude has session resume primitives | Store Conductor execution_id independently |
| Security | Custom providers/MCP/remote mode need strict fences | Gateway/helper and permissions need strict fences | Never expose shell/credentials/browser to internet |
| Best use now | High-token implementation/review labor | Future structured reviewer/writer once route proven | Backend capability router |

## Harness policy

A-Sunday Conductor owns the lifecycle:

`Goal -> claim -> worktree -> provider admission -> harness execution -> result artifact -> deterministic verify -> independent review -> repair/accept -> CI -> merge/post-main -> next-ready continuation`

Kilo CLI and Claude Code CLI may only implement the `harness execution` substep. Their output is a claim until verified.

### Kilo lane profile

Use for:
- high-volume implementation in one mutable worktree;
- broad read-only archaeology/review lanes;
- repetitive test repair loops;
- GLM-heavy tasks where token budget is abundant.

Hard gates:
- use exact executable path, not ambient PATH;
- preflight `kilo roll-call` or quota endpoint when available;
- disable board/memory/MCP/plugin tools unless explicitly required;
- require final sentinel and result artifact under `runs/**`;
- never trust process exit 0 alone;
- record PID/session/model/agent/worktree/HEAD/result path.

### Claude Code lane profile

Use after route proof for:
- structured JSON reviewer lanes;
- tasks benefiting from `--output-format json|stream-json` and permission-prompt tooling;
- alternate harness comparison/A-B tests;
- future provider gateway work.

Hard gates:
- prove actual model route (`glm-5.3`, not paid Claude/Astra) before use;
- prove credential helper/gateway does not stall;
- bound `--max-turns`, output capture, and wall-clock timeout;
- parse result text for permission/rate-limit failure markers, not only JSON subtype/exit code;
- do not rely on `.claude/**` writes in headless paths.

## Required A-Conductor implementation shape

```text
ExecutionBackend
├── existing ClaudeCodeJobBackend
├── NEW KiloJobBackend
└── future BrowserWake/ProviderWebBackend

CapabilityRouter
├── health/quota/cost/readiness
├── claim/worktree/scope gates
├── deny-first permission profile selection
└── exact completion classifier
```

The Kilo adapter should be thin:

- construct an approved argv list from a typed operation, never from task text;
- launch via durable supervised execution;
- record stdout/stderr/session files with byte counts and hashes;
- classify outcomes into `COMPLETED_CLAIM`, `RATE_LIMITED`, `PERMISSION_BLOCKED`, `TRANSPORT_FAILURE`, `NO_PROGRESS`, `AUTH_REQUIRED`, `RUNTIME_UNVERIFIED`;
- require downstream deterministic verification before acceptance.

## Completion classifier

A harness task is not done until all required evidence exists:

1. expected worktree and HEAD match;
2. process terminated or bounded stop captured;
3. result artifact exists under allowed `runs/**` path;
4. final sentinel/schema is present and well-formed;
5. tracked diff is clean for read-only lanes or exactly scoped for writer lanes;
6. targeted tests and requested probes ran;
7. no secret-shaped output or unauthorized path mutation;
8. GPT/Sol integrator adjudicates findings against exact SHA.

## Recommendation

Default now: **Kilo CLI for GLM labor, GPT-5.6 Sol for integration/acceptance, Astra/paid premium models only for hard R3 conflicts.**

Target architecture: **executor-neutral routing with both Kilo and Claude Code backends.** Claude Code is not rejected; it is gated until local model/credential/transport proof is available. Kilo is not trusted as authority; it is a productive transport that must be wrapped by A-Conductor's durable verification and completion classifier.
