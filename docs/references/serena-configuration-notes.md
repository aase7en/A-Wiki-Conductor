# Serena Configuration — Reference Notes for A-Conductor

Source: https://oraios.github.io/serena/02-usage/050_configuration.html
Captured: 2026-08-20
Purpose: durable reference for future fork/copy-and-develop decisions (see `PROJECT-PLAN.md` §2, §11) and for programmatic multi-instance management.

## Configuration layers (later overrides earlier)

1. **Global** — `serena_config.yml`
2. **Project** — `project.yml` (+ `project.local.yml` for local overrides)
3. **Contexts & modes** — composable, selected case-by-case
4. **CLI parameters** to `start-mcp-server`

## Global configuration

- Auto-created on first run:
  - Linux/macOS/Git-Bash: `~/.serena/serena_config.yml`
  - Windows: `%USERPROFILE%\.serena\serena_config.yml`
- Editable via the Dashboard while running, a text editor, or `serena config edit`.
- Configures: default language backend (JetBrains plugin vs language servers, per-project overridable), Dashboard/UI settings, default enabled/disabled tools, default modes, tool execution params (timeout, max answer length), global ignore rules, logging, trusted project paths, language-server advanced settings, language server priorities (drive auto-detection).
- Full parameter reference lives in the Serena repo template: `src/serena/resources/serena_config.template.yml`.

## Contexts

- Define the operating environment; influence system prompt and toolset; **fixed at startup** — cannot change mid-session.
- Selected at launch with `--context <name>` (Claude-Desktop-style parameter lists need two parameters).
- Built-ins: `desktop-app` (default, full toolset), `claude-code`, `codex`, `grok`, `ide`, `agent` (autonomous), `oaicompat-agent` (local OpenAI-compatible servers).
- `ide`, `claude-code`, `grok` are **single-project contexts** (`single_project: true`): toolset restricted to project config, explicitly disabled tools unavailable, project-activation tool disabled — effectively pins one project. This is the upstream mechanism behind A-Conductor's project pinning.
- Management: `serena context list|create|edit|delete <name>`.

## Modes

- Refine behavior per task/interaction style; multiple may be active; can alter prompt and exclude tools.
- Built-ins: `planning`, `editing`, `interactive`, `one-shot`, `no-onboarding`, `onboarding`, `no-memories`, `query-projects` (query other projects without activating).
- Active modes = union of `base_modes` (global, always active) + `default_modes` (global, overridable by project or CLI `--mode`) + `added_modes` (project config or CLI `--add-mode`).
- Guidance: always-wanted → `base_modes`; typically-wanted-but-overridable → `default_modes`; per-project/session → `added_modes`.
- Incompatible combinations (e.g. `interactive` + `one-shot`) are not blocked — caller's responsibility.
- Management: `serena mode list|create|edit|delete <name>`.

## Prompt templates (Jinja2)

- Apply to `system_prompt`, context/mode `prompt` fields, project `initial_prompt`.
- Variables (all templates): `available_tools`, `available_markers` (tool categories with ≥1 exposed tool), `tool_names` (canonical → effective mapping).
- Function (context/mode/project prompts only): `embed_memory(name)` — inlines a memory wrapped in a tag; errors are logged, nothing rendered on failure.

## Advanced configuration relevant to A-Conductor

- **`SERENA_HOME`** env var relocates the entire Serena data directory (config, language-server files, logs); default `~/.serena`. This is the isolation primitive A-Conductor already uses per worker instance.
- **`project_serena_folder_location`** (global): customizes the per-project `.serena` folder; supports `$projectDir` and `$projectFolderName` placeholders. Fallback order: configured path → project root (legacy) → create at configured path (backward compatible).
- Trusted-project paths (global) gate which projects may apply project-level settings.

## Language-server settings (`ls_specific_settings`)

- Global per-language config; the same key in `project.yml` / `project.local.yml` overrides per language (top-level merge); project-level settings apply **only to trusted projects**.
- Launch-command customization (servers deriving from `LanguageServerDependencyProviderBaseCommand`):
  - `ls_path` (string) — override core dependency path; bypasses managed download/install and version/registry settings
  - `ls_base_cmd` (list) — override base command, e.g. `["npx", "-y", "/my/local/package"]`
  - `ls_args` (list) — replaces internal command construction entirely
  - `ls_extra_args` (list) — always appended
  - Supported by: ansible, bash, bsl, clojure, cpp, cpp_ccls, hlsl, html, kotlin, lean4, luau, markdown, php, nix, php_phpactor, python, rust, scss, solidity, systemverilog, toml, typescript, yaml

## Implications for fork / copy-and-develop

- The multi-layer config + `SERENA_HOME` + single-project contexts mean A-Conductor's per-worker isolation and project pinning can be driven entirely through public config surfaces — no fork required for current needs (consistent with `PROJECT-PLAN.md` §2 escalation order).
- A future fork would primarily target: lifecycle hooks, structured telemetry, and startup orchestration — all gated behind `DECISION-SERENA-FORK` with maintenance/licensing/update/security cost analysis.
- `ls_specific_settings` override chains are the sanctioned path for pinning/custom language-server binaries per project without touching Serena core.
