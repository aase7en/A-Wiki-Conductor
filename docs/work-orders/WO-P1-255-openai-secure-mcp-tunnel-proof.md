# WO-P1-255 — OpenAI Secure MCP Tunnel + SRM stdio proof

Status: CLAIMED / CROSS_REPO IMPLEMENTATION
Issue: #357
Parent roadmap: #340
Risk: R3 CRITICAL — external transport / capability entitlement / MCP trust boundary
Topology: CROSS_REPO
Owner/integrator: GPT-5.6 Sol

## Exact lane bindings

Authority lane:
- repo: `A:\GitHub\A-Wiki-Conductor`
- worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo255-openai-mcp`
- branch: `docs/wo-p1-255-openai-secure-mcp-tunnel-proof`
- bootstrap base SHA: `8dd659df635b50988757414d3eae2f1cf923ba52`
- note: `origin/main` advanced independently to `6ca84a7f2a3f48d4e1fd100f6064f6436e627025`
  after WO-P1-254 merged. This docs lane remains bound to its branch; the final
  CROSS_REPO compatibility set must be re-pinned and reviewed before fan-in.

Execution lane:
- repo: `A:\GitHub\SunDayRemoteMCP`
- worktree: `A:\GitHub\_worktrees\SunDayRemoteMCP-wo255-openai-mcp`
- branch: `feat/srm-openai-mcp-stdio-proof`
- base SHA: `1fca9d24c37e49762ea6fbce8b2927726d94e0b7`

## Architecture decision

Classify this slice as `REUSE -> EXTEND`.

First transport proof reuses the existing SRM stdio server and the existing stdio end-to-end test
harness. Do **not** build Streamable HTTP first. Do not use the inherited Desktop Commander/Supabase
remote mode as the Sunday production transport path.

The intended external topology is:

`supported OpenAI surface -> Secure MCP Tunnel -> existing SRM stdio -> sunday_* tools`

The tunnel/client is transport only.

`TRANSPORT_READY != CHATGPT_WRITE_AUTHORITY`

Tunnel connectivity grants no task, claim, scheduler, retry, review, completion, project, provider,
or write/mutation authority. It does not prove that ChatGPT can start a new turn or push work into
an inactive conversation.

A-Conductor remains control-plane authority. SunDayRemoteMCP remains execution substrate.

## Current reusable SRM seams

At SRM base `1fca9d24...`:

- `src/index.ts` already starts the local MCP endpoint through stdio and supports
  `--no-onboarding`.
- `src/sunday/mcp-tools.ts` already exposes the typed `sunday_*` namespace and resolves
  workspace/path per request rather than through a mutable global Active Project.
- `test/test-sunday-mcp-tools.js` already contains an end-to-end stdio client that:
  - spawns `dist/index.js --no-onboarding`;
  - performs MCP `initialize` + `notifications/initialized`;
  - exercises `tools/list` and `tools/call`;
  - checks typed bad-argument and unknown-tool failures.

Therefore this WO extends that harness rather than introducing a second MCP conformance framework.

## Goal

Prove two independent facts without conflating them:

1. **Tier 0 transport/protocol conformance** — existing SRM stdio can behave as a clean private MCP
   server suitable for a tunnel/client adapter.
2. **Entitlement evidence** — the consuming OpenAI product/account surface has a separately observed
   capability level. This evidence gates what may be claimed, not what the tunnel transports.

The first slice must be independently verifiable without OpenAI credentials, ChatGPT UI access,
network access, or a live Secure MCP Tunnel session.

## Entitlement model

Add a declaration/evidence-only typed model with exactly these capability states:

- `UNKNOWN` — default; fail closed; no write/modify claim.
- `READ_ONLY` — read/fetch/tool-observation capability only.
- `WRITE_MODIFY` — write/modify capability explicitly observed and supported by current evidence.
- `UNSUPPORTED` — target product surface does not support the custom MCP/app path being claimed.

Rules:

1. UNKNOWN is never promoted to READ_ONLY or WRITE_MODIFY.
2. READ_ONLY is never promoted to WRITE_MODIFY.
3. TRANSPORT_READY alone changes no entitlement state.
4. WRITE_MODIFY must require explicit bounded evidence and may not be inferred from plan name,
   tool annotations, successful read calls, or tunnel connectivity.
5. Entitlement records must contain bounded non-secret provenance only.
6. No raw auth headers, cookies, tokens, tunnel IDs, share/session URLs, commands, full config, or
   environment maps.
7. Stale/invalid/missing evidence degrades to UNKNOWN rather than optimistic capability.
8. This model owns no authorization or MCP execution authority. It is safe capability evidence only.

## Claimed authority scope

A-Wiki lane may modify exactly:

- NEW `docs/work-orders/WO-P1-255-openai-secure-mcp-tunnel-proof.md`

No other A-Wiki tracked file is mutable in this slice.

## Claimed execution scope

SRM lane may modify exactly:

- NEW `src/sunday/openai-mcp-entitlement.ts`
- NEW `test/test-sunday-openai-mcp-entitlement.js`
- MODIFY `test/test-sunday-mcp-tools.js`

No `package.json` change is required because `test/run-all-tests.js` auto-discovers top-level
`test*.js` files.

Forbidden execution changes include:
- `src/index.ts`
- `src/sunday/mcp-tools.ts`
- `src/remote.ts` / inherited remote transport
- Supabase/remote channel code
- task/job/claim/scheduler/lease/retry/review/completion authority
- provider/admission code
- secrets/config/credential resolution
- production HTTP/Streamable HTTP transport
- process restart/kill behavior

## Tier 0 deterministic proof

Extend the existing `test/test-sunday-mcp-tools.js` stdio client/harness to prove:

1. clean MCP initialize/initialized handshake;
2. exact `sunday_*` inventory remains present;
3. existing typed bad-args / unknown-tool envelopes remain intact;
4. stdout purity:
   - every non-empty stdout line from the MCP server must be valid JSON-RPC;
   - test harness must not silently discard non-JSON stdout noise;
5. two-workspace / one-session:
   - create two distinct temporary workspaces/repositories;
   - call `sunday_workspace_info` for each in the same MCP session;
   - each call must resolve its explicit path independently;
   - no previous path may become mutable global project/session authority;
6. no tunnel/OpenAI/network dependency is required.

Windows process invocation must obey the repo no-console rule where applicable; tests should use
the exact Node executable path and bounded child cleanup.

## Entitlement deterministic tests

The new entitlement module/tests must prove at least:

- default/absent evidence => UNKNOWN;
- exact valid READ_ONLY / WRITE_MODIFY / UNSUPPORTED construction;
- invalid/blank/oversized provenance rejects;
- naive/non-date or stale evidence fails closed to UNKNOWN or rejects according to one documented
  deterministic rule;
- tunnel-ready=true with UNKNOWN remains UNKNOWN;
- tunnel-ready=true with READ_ONLY remains READ_ONLY;
- READ_ONLY cannot satisfy a WRITE_MODIFY capability requirement;
- WRITE_MODIFY can satisfy a WRITE_MODIFY capability requirement only with valid current evidence;
- safe projection is a fixed allowlist and carries no raw command/config/env/header/token/secret/url
  fields;
- no provider/network/process/filesystem side effects in the production entitlement module.

## Live Secure MCP Tunnel evidence — separate conditional tier

A later operator/live evidence step may run the supported OpenAI Secure MCP Tunnel against the
accepted SRM stdio launch surface and exercise only the capability allowed by observed entitlement.

Live evidence must record only bounded, redacted facts such as:
- exact SRM SHA;
- tunnel/client version or documented surface identifier;
- observed transport result;
- observed entitlement state and evidence timestamp;
- safe tool names / bounded result codes.

If no supported OpenAI account/product entitlement is available, record
`LIVE_ENTITLEMENT_BLOCKED`. Tier 0 may still be accepted as stdio transport/protocol proof.
Never convert that into a claim of ChatGPT WRITE_MODIFY capability.

## Compatibility / fan-in

Freeze one exact candidate SHA per repo:

`{A-Wiki-Conductor@SHA_AUTH, SunDayRemoteMCP@SHA_EXEC}`

Any member drift invalidates the set until re-pin and focused review.

Required order:
1. freeze authority doc candidate;
2. freeze SRM execution candidate;
3. deterministic verification;
4. independent exact-SHA CROSS_REPO review;
5. authority repo PR/merge first;
6. re-pin merged authority SHA with unchanged execution candidate and verify the affected delta;
7. execution repo fan-in according to its local delivery policy;
8. post-main verification of both repos;
9. fold final accepted SHA pair to this authority WO before completion.

## Verification floor

Authority lane:
- exact one-file scope;
- `git diff --check`.

Execution lane:
- focused entitlement test;
- focused Sunday MCP stdio test;
- TypeScript build;
- directly related Sunday MCP tests;
- `git diff --check`;
- exact three-file tracked scope;
- secret/share/session URL scan;
- no production I/O/import expansion in the entitlement module.

R3 independent review must explicitly challenge:
- transport vs entitlement separation;
- no write-authority inference;
- no global Active Project;
- stdout purity;
- tool inventory stability;
- entitlement evidence freshness/provenance;
- no shadow control plane;
- exact-SHA pair.

## Deferred

Not authorized in WO-P1-255:
- Streamable HTTP transport;
- ChatGPT push/turn-trigger implementation;
- exposing or authorizing write-capable `sunday_*` operations from an OpenAI surface;
- mobile/operator UI;
- authentication redesign beyond the supported tunnel boundary;
- inherited Desktop Commander/Supabase remote mode as Sunday production transport;
- automatic provider/model routing;
- any Serena GPL application code copy.

## Exit

This WO is complete only when the exact cross-repo SHA pair has deterministic evidence and
independent R3 review. A successful local stdio proof may establish TRANSPORT_PROTOCOL_READY but
must never be worded as CHATGPT_WRITE_AUTHORITY without separate valid entitlement evidence.
