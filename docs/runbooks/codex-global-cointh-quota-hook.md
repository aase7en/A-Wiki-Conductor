# Codex-global CoinTH quota hook

Status: USER-LOCAL MAC CONFIGURATION / DETERMINISTIC PRETOOL GUARD
Work order: WO-P1-564 / Issue #564
Related: `docs/runbooks/cointh-glm-quota.md`

## What it covers

The user's Codex-global `PreToolUse` hook on this Mac checks explicit GLM-5.3 model requests made from Codex tool calls. Supported paths are `Bash`, the current Mac tool `mcp__codex_apps__sundaymcp_mac_sunday_dispatch`, and the legacy-compatible `mcp__sunday_mcp__sunday_dispatch`, including explicit Kilo/Claude CLI model selectors carried in their command/argv (the Mac dispatcher may wrap the CLI with `/usr/bin/env`). It performs one fresh CoinTH quota GET immediately before the matching tool call. It makes no model call and consumes no GLM inference tokens.

The matcher must be narrow: check the command's executable arguments or a structured model field for an explicit GLM-5.3 selector such as `cointh-glm/glm-5.3`; a mention of GLM in the task prompt, source text, or a filename is not a dispatch. Delegated and direct Codex calls use the same quota semantics. The hook cannot see CLI processes launched outside Codex, and cannot infer an unreported CLI default model; callers must specify the selected model explicitly.

## Decision behavior

The hook delegates classification to `docs/runbooks/cointh-glm-quota.md`:

- `AVAILABLE`: return without a permission decision so Codex's normal approval rules still apply.
- `EXHAUSTED`: return a `PreToolUse` deny for this matching GLM request only.
- `UNKNOWN`: return a `PreToolUse` deny for this matching GLM request only and identify a safe typed reason; never claim exhaustion or provider throttling.
- Non-GLM tool calls: return without changing them.

It must never return `allow`, silently rewrite the user's command, auto-select another model, authorize paid fallback, or bypass task/claim/WIP/scope/tool permissions. An upstream 429 is visible only after a real GLM request; the quota hook does not pre-probe upstream.

## Implementation requirements

- Config location: `~/.codex/hooks.json`; global handler: `~/.codex/hooks/cointh_quota_pretool.py`.
- Keep the repository implementation at `scripts/codex_hooks/cointh_quota_pretool.py`; the installed handler must match that reviewed source.
- Register only `PreToolUse` with a narrow matcher for the supported tool names. Do not alter or replace other global hooks.
- Read only the already-bound `COINTH_GLM_AUTH_TOKEN` environment variable. Missing binding is `UNKNOWN`.
- Make one verified-HTTPS, no-cache GET with bounded timeout. Use system `curl --config -` and send the config through stdin so the key is absent from argv. Never scan files/Drive, print or log the key, save the quota response, or cache state.
- Emit a valid hook JSON deny result on `EXHAUSTED`/`UNKNOWN`; catch handler errors and fail closed for a recognized GLM request. For `AVAILABLE`, emit no permission override.
- Do not change `~/.codex/hooks.state` or fabricate trust hashes. After the concrete config and script exist, the user reviews/trusts them with Codex `/hooks`.

Codex documents `PreToolUse` as able to block supported shell and MCP tools with `hookSpecificOutput.permissionDecision="deny"`. Hook commands run synchronously for blocking decisions. Hook errors, unavailable tool paths, or timeouts are not a complete enforcement boundary and may let a call continue, so keep the handler small, bounded, and deterministic. See the [official Codex Hooks documentation](https://learn.chatgpt.com/docs/hooks).

The local setup is Codex-global for this Mac user. It does not install into the repository's `.codex/hooks.json`, affect another user or machine, or govern standalone Kilo/Claude processes launched outside Codex.

## JEV boundary

Do not call JEV from this quota hook. Quota arithmetic, provider authentication, and permission decisions are deterministic facts; JEV cannot adjudicate them. Current project JEV mode defaults to `OFF`, and a dedicated executor/model-selection family is not admitted by this hook.

If a future accepted JEV `ADVISORY` family covers route suggestions, place it in the task-routing layer before dispatch, after deterministic filtering has produced a safe eligible-model shortlist. Send only sanitized typed task features, let JEV rank or abstain among that shortlist, and let the deterministic router make the final selection. JEV failure or low confidence falls back to deterministic routing. It never changes quota state, claims, WIP, mutation/review authority, or permissions.

## Incident lessons

- Treat a fresh valid positive CoinTH tuple as `AVAILABLE` even if `window_source=stale`; preserve that value as metadata instead of blocking work.
- For Kilo, use `kilo run "<task prompt>" --model cointh-glm/glm-5.3 --variant max --dir <claimed-worktree> ...`; prompt comes before flags. Kilo's [CLI reference](https://kilo.ai/docs/code-with-ai/platforms/cli-reference) lists `message` as the `kilo run` positional and `--model`/`--file`/`--dir`/`--variant` as options. A prompt after repeated `--file` options can be parsed as a path and fail before inference.
- The Mac execution route is independent of Windows. Discover Windows as optional capacity when filling multiple lanes; never make its availability a precondition for the Mac route.

## Activation and verification boundary

First reconcile the exact source/config contents and run static syntax/JSON/scope/secret checks. A human must then review the registered command in `/hooks`; trust is not written by editing internal Codex state. The hook remains inactive until Codex accepts that trust decision. Exact-SHA hosted CI and an independent R3 review are still required for repository acceptance; local activation is not a substitute.
