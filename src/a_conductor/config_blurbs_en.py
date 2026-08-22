"""English variants of the config blurbs (mirrors config_blurbs)."""

from __future__ import annotations

LANGUAGE_BACKEND_BLURBS: dict[str, str] = {
    "LSP": "Free · auto-installed · covers most languages (recommended)",
    "JetBrains": "Needs a JetBrains IDE + plugin · stronger rename/move · some languages only",
}

TOOL_BLURBS: dict[str, str] = {
    "read_file": "Read a file — agent inspects code/docs in the project",
    "write_file": "Write a file — agent edits code / creates files (disable if worried)",
    "open_file": "Open a file in the editor connected to the agent",
    "get_dir_tree": "See the folder structure — agent understands the layout",
    "find_file": "Find files by name — faster than a full search",
    "search_for_pattern": "Search text/regex across the whole project",
    "find_symbol": "Find classes/functions/variables language-aware (not just text)",
    "get_symbols_overview": "Symbol outline of a file — faster structure reading",
    "get_references_overview": "See who uses this symbol",
    "find_referencing_symbols": "Trace every call site — crucial when refactoring",
    "replace_regex": "Regex replace across the project — handle with care",
    "insert_after_symbol": "Insert code right after the chosen symbol",
    "replace_symbol_body": "Overwrite an entire function/class body",
    "execute_shell": "Run shell commands — the most dangerous; disable if unneeded",
    "read_memory": "Read the project's stored memories",
    "write_memory": "Save a memory — agent remembers across sessions",
    "create_memory": "Create a new memory file",
    "list_memories": "List all stored memories",
    "activate_project": "Switch the active project — needed for multi-project use",
    "get_current_config": "View the engine's current config",
    "restart_language_server": "Restart the language server — use when the index breaks",
}

MODE_BLURBS: dict[str, str] = {
    "planning": "Planning mode — agent thinks before acting; good for big tasks",
    "editing": "Editing mode — enables the code-writing tools",
    "interactive": "Interactive mode — agent asks back when unclear",
    "one-shot": "Single-shot task — no questions, just do it",
    "onboarding": "Teach the project to the agent on first entry",
    "no-onboarding": "Skip project onboarding entirely",
    "no-memories": "Disable memories — agent neither reads nor writes them",
    "query-projects": "Cross-project read — search other projects read-only",
}

LANGUAGE_BLURBS: dict[str, str] = {
    "python": "Python — fully supported, auto-installed",
    "typescript": "TypeScript/JavaScript — auto-installed",
    "javascript": "JavaScript — auto-installed",
    "html": "HTML — enable when working on web pages",
    "css": "CSS — needed when editing styles",
    "scss": "SCSS/Sass — only if the project uses Sass",
    "json": "JSON — config files",
    "yaml": "YAML — config/Docker/K8s files",
    "markdown": "Markdown — docs/README",
    "toml": "TOML — Python config",
    "rust": "Rust — install rust-analyzer yourself",
    "go": "Go — install gopls yourself",
    "cpp": "C/C++ — requires compile_commands.json",
    "c": "C — requires compile_commands.json",
    "csharp": "C# — requires .NET 10+",
    "java": "Java — install Eclipse JDT LS yourself",
    "kotlin": "Kotlin — requires a Kotlin LS",
    "php": "PHP — auto-installed",
    "ruby": "Ruby — requires a Ruby LS",
    "swift": "Swift — requires Xcode/LLVM",
    "vue": "Vue.js — auto-installed",
    "svelte": "Svelte — auto-installed",
    "solidity": "Solidity — smart contracts",
    "bash": "Bash/Shell scripts",
}

FIELD_BLURBS: dict[str, str] = {
    "tool_timeout": "Max seconds per tool call — higher is calmer but can hang longer",
    "project_path": "Project the engine works on — blank = use the Assigned project",
    "included_optional_tools": "Extra optional tools to enable (CSV) — usually untouched",
    "fixed_tools": "Lock to ONLY these tools (CSV) — maximum control · never combine with exclusions above",
    "base_modes": "Base modes (CSV) — usually interactive + editing",
    "brain_folder_1": "Primary brain folder — every agent must read its rules first",
    "brain_folder_2": "Secondary brain (optional) — e.g. org/team rules",
    "brain_entry_1": "First file to read — e.g. AGENTS.md",
    "brain_entry_2": "Second file to read — e.g. wiki-overview.md",
}
