# Serena Full-Documentation Implications (from docs/SerenaDoc, 34 files)

Captured: 2026-08-21 · Purpose: durable engineering facts distilled from the complete engine documentation export, driving A-Conductor UI/config decisions.

## Key operational facts

- Install/run: `uv tool install -p 3.13 serena-agent`; `serena start-mcp-server`. HTTP mode: `--transport streamable-http --port <p>` (endpoint `http://localhost:<p>/mcp`, localhost-only by default); SSE discouraged.
- ChatGPT official path: `uvx mcpo --port 8000 --api-key <KEY> -- serena start-mcp-server --context chatgpt --project <path>` + cloudflared tunnel; ChatGPT Custom GPT uses Bearer auth + manually-added `servers` URL (no trailing slash).
- Contexts fixed at startup; single-project contexts (`ide`, `claude-code`, `grok`) REMOVE `activate_project` when `--project` is given. **`chatgpt` context is multi-project** — a connected chat agent can switch projects by prompting activation.
- Backend (LSP/JetBrains) fixed at startup; modes composable; languages/tools are live-changeable via dashboard.
- Project activation prompt (canonical): "Activate the current dir as project using serena". Activation is per-session friction; can deactivate unexpectedly.
- Onboarding fires exactly when a project has no memories; it floods context — start a NEW conversation afterwards.
- Memories: `<project>/.serena/memories/` + global `~/.serena/memories/global/`; name list given up-front (progressive disclosure). `initial_prompt` (Jinja2, `embed_memory()`) is delivered on every activation.
- Dashboard: `http://localhost:24282/dashboard/index.html` by default BUT silently picks a higher port when busy; every stdio spawn makes its own dashboard. Never hardcode.
- `serena-hooks` (activate/remind/cleanup/auto-approve) strongly recommended per client (`.claude/settings.json`, `~/.codex/hooks.json` + `[features] codex_hooks=true`, etc.).
- Trusted projects gate (`trusted_project_path_patterns`): new configs trust nothing; gates `activation_command` + project `ls_specific_settings`.
- Readiness is slow/language-specific: first symbolic query blocks on LS indexing (TS ~30s, Scala ≤180s, GDScript 30–60s first scan, C++ requires `compile_commands.json`).
- Git: JetBrains rename/move stage files in the index (verify staged+unstaged); Windows wants `core.autocrlf=true`. Known engine defects: move can create circular imports; `safe_delete` propagate unreliable on Python; inline causes formatting churn.

## Implications applied to A-Conductor

1. CONNECTORS instances using `--context chatgpt` can expose project switching to the chat agent (activation prompt) — document the copy-paste prompt in the UI hint/guide.
2. Config dialog marks context/backend/modes as restart-required (already done: "applies on next start").
3. Future: surface per-project memory presence + onboarding warning + "start new conversation" nudge; activation status; serena-hooks generator; MCPO/cloudflared flow generator; exposed-server security defaults (`excluded_tools: [execute_shell_command]`, `read_only: true` options).
4. Health checks must stay process/readyz-based (dashboard port unstable by design).
