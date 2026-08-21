"""Per-worker Serena configuration surface (WO-P1-048).

Typed, validated settings edited through the Conductor UI, rendered into a
complete ``serena_config.yml`` for the worker's isolated ``SERENA_HOME`` and
applied on worker restart. Serena remains the config consumer; Conductor owns
generation. No live worker is mutated by this module.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_WORKER_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_TOOL_NAME_RE = re.compile(r"^[a-z0-9_]+$")
_MODE_NAME_RE = re.compile(r"^[a-z0-9_-]+$")
_LANGUAGE_RE = re.compile(r"^[a-z0-9+#_-]+$")

KNOWN_LANGUAGES: tuple[str, ...] = (
    "python", "typescript", "javascript", "html", "css", "scss", "json",
    "yaml", "markdown", "toml", "rust", "go", "cpp", "c", "csharp", "java",
    "kotlin", "php", "ruby", "swift", "vue", "svelte", "solidity", "bash",
)

ENGINE_TOOLS: tuple[str, ...] = (
    "read_file", "write_file", "open_file", "get_dir_tree", "find_file",
    "search_for_pattern", "find_symbol", "get_symbols_overview",
    "get_references_overview", "find_referencing_symbols", "replace_regex",
    "insert_after_symbol", "replace_symbol_body", "execute_shell",
    "read_memory", "write_memory", "create_memory", "list_memories",
    "activate_project", "get_current_config", "restart_language_server",
)

_MIN_TOOL_TIMEOUT = 1
_MAX_TOOL_TIMEOUT = 86400


class LanguageBackend(str, Enum):
    LSP = "LSP"
    JETBRAINS = "JetBrains"


def _require_identifier_tuple(
    values: tuple[str, ...],
    field_name: str,
    pattern: re.Pattern[str],
) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValueError(f"{field_name} must be a tuple of strings")
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or pattern.fullmatch(value) is None:
            raise ValueError(f"{field_name} contains an invalid name: {value!r}")
        if value in seen:
            raise ValueError(f"{field_name} contains duplicates: {value!r}")
        seen.add(value)
    return values


@dataclass(frozen=True, slots=True)
class WorkerSerenaSettings:
    worker_id: str
    language_backend: LanguageBackend = LanguageBackend.LSP
    excluded_tools: tuple[str, ...] = ()
    included_optional_tools: tuple[str, ...] = ()
    fixed_tools: tuple[str, ...] = ()
    base_modes: tuple[str, ...] = ()
    tool_timeout: int = 240
    project_path: str | None = None
    enabled_languages: tuple[str, ...] = ()
    brain_folders: tuple[str, ...] = ()
    brain_entry_files: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.worker_id, str)
            or _WORKER_ID_RE.fullmatch(self.worker_id) is None
        ):
            raise ValueError("worker_id must match ^[a-z0-9][a-z0-9-]*$")
        if not isinstance(self.language_backend, LanguageBackend):
            raise ValueError("language_backend must be a LanguageBackend")
        _require_identifier_tuple(self.excluded_tools, "excluded_tools", _TOOL_NAME_RE)
        _require_identifier_tuple(
            self.included_optional_tools, "included_optional_tools", _TOOL_NAME_RE
        )
        _require_identifier_tuple(self.fixed_tools, "fixed_tools", _TOOL_NAME_RE)
        _require_identifier_tuple(self.base_modes, "base_modes", _MODE_NAME_RE)
        if self.project_path is not None and (
            not isinstance(self.project_path, str)
            or not self.project_path.strip()
            or "\x00" in self.project_path
        ):
            raise ValueError("project_path must be a non-blank string or None")
        known = set(KNOWN_LANGUAGES)
        _require_identifier_tuple(
            self.enabled_languages, "enabled_languages", _LANGUAGE_RE
        )
        for language in self.enabled_languages:
            if language not in known:
                raise ValueError(f"LANGUAGE_NOT_SUPPORTED: {language}")
        if not isinstance(self.brain_folders, tuple) or not isinstance(
            self.brain_entry_files, tuple
        ):
            raise ValueError("brain fields must be tuples of strings")
        if len(self.brain_folders) > 2 or len(self.brain_entry_files) > 2:
            raise ValueError("BRAIN_LIMIT: at most 2 brain folders and 2 entry files")
        seen_folders: set[str] = set()
        for folder in self.brain_folders:
            if (
                not isinstance(folder, str)
                or not folder.strip()
                or "\x00" in folder
                or not Path(folder).is_absolute()
            ):
                raise ValueError(f"brain_folders entry must be an absolute path: {folder!r}")
            if folder in seen_folders:
                raise ValueError(f"brain_folders contains duplicates: {folder!r}")
            seen_folders.add(folder)
        seen_entries: set[str] = set()
        for entry in self.brain_entry_files:
            if (
                not isinstance(entry, str)
                or not entry.strip()
                or "\x00" in entry
                or not Path(entry).is_absolute()
            ):
                raise ValueError(f"brain_entry_files entry must be an absolute path: {entry!r}")
            if entry in seen_entries:
                raise ValueError(f"brain_entry_files contains duplicates: {entry!r}")
            seen_entries.add(entry)
        if self.fixed_tools and (self.excluded_tools or self.included_optional_tools):
            raise ValueError("FIXED_TOOLS_EXCLUSIVE: fixed_tools cannot be combined with excluded/included tool lists")
        if (
            not isinstance(self.tool_timeout, int)
            or isinstance(self.tool_timeout, bool)
            or not _MIN_TOOL_TIMEOUT <= self.tool_timeout <= _MAX_TOOL_TIMEOUT
        ):
            raise ValueError(
                f"tool_timeout must be between {_MIN_TOOL_TIMEOUT} and {_MAX_TOOL_TIMEOUT}"
            )

    def render_serena_config(self, *, project_path: str | None = None) -> str:
        effective_project = project_path if project_path is not None else self.project_path
        if effective_project is not None and (
            not isinstance(effective_project, str)
            or not effective_project.strip()
            or "\x00" in effective_project
        ):
            raise ValueError("project_path must be a non-blank string or None")

        def yaml_list(values: tuple[str, ...]) -> str:
            if not values:
                return " []"
            return "\n" + "\n".join(f"- {value}" for value in values)

        if self.enabled_languages:
            disabled = tuple(
                language
                for language in KNOWN_LANGUAGES
                if language not in set(self.enabled_languages)
            )
            if disabled:
                ls_block = "ls_priorities:\n" + "\n".join(
                    f"  {language}: 0" for language in disabled
                )
            else:
                ls_block = "ls_priorities:"
        else:
            ls_block = "ls_priorities:"

        lines = [
            "# Generated by A-Conductor (WO-P1-048). Applied on worker restart.",
        ]
        if self.brain_folders:
            brain_lines = [
                "[A-CONDUCTOR SECOND BRAIN]",
                "Brain folders (source of truth; session memory is not):",
            ]
            for index, folder in enumerate(self.brain_folders, start=1):
                brain_lines.append(f"{index}) {folder}")
            if self.brain_entry_files:
                brain_lines.append("Must-read BEFORE starting the task (use read_file):")
                for entry in self.brain_entry_files:
                    brain_lines.append(f"- {entry}")
            brain_lines.extend(
                [
                    "Rules:",
                    "- Read every must-read file BEFORE starting the task.",
                    "- Before write_file/execute_shell or any mutation, state which rule or protocol you are following.",
                    "- Pull further brain content on demand (get_dir_tree/read_file); do not assume memory.",
                ]
            )
            lines.append("system_prompt: |")
            lines.extend(f"  {line}" for line in brain_lines)
        lines.extend(
            [
                f"language_backend: {self.language_backend.value}",
                "line_ending: native",
                "gui_log_window: false",
                "web_dashboard: false",
                "web_dashboard_open_on_launch: false",
                "web_dashboard_interface:",
                "web_dashboard_listen_address: 127.0.0.1",
                "web_dashboard_trusted_hosts:",
                "- 127.0.0.1",
                "- localhost",
                "log_level: 20",
                "trace_lsp_communication: false",
                "ls_specific_settings: {}",
                ls_block,
                "ignored_paths: []",
                "read_only_memory_patterns: []",
                "ignored_memory_patterns: []",
                f"tool_timeout: {self.tool_timeout}",
                f"excluded_tools:{yaml_list(self.excluded_tools)}",
                f"included_optional_tools:{yaml_list(self.included_optional_tools)}",
                f"fixed_tools:{yaml_list(self.fixed_tools)}",
                f"base_modes:{yaml_list(self.base_modes)}",
                "default_modes:",
                "default_max_tool_answer_chars: 150000",
                "token_count_estimator: CHAR_COUNT",
                "symbol_info_budget: 10",
                'project_serena_folder_location: "$projectDir/.serena"',
                "trusted_project_path_patterns: []",
            ]
        )
        if effective_project is None:
            lines.append("projects: []")
        else:
            lines.append("projects:")
            lines.append(f"- '{effective_project.replace(chr(39), '')}'")
        return "\n".join(lines) + "\n"


class WorkerSettingsApplyError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def apply_worker_serena_settings(
    settings: WorkerSerenaSettings,
    *,
    instances_root: Path | str,
    project_path: str,
    serena_home_subdir: str = "serena-home",
) -> Path:
    """Render and atomically write the worker's serena_config.yml.

    Writes are confined to ``<instances_root>/<worker_id>/<serena_home_subdir>``;
    any traversal outside the resolved root fails closed.
    """
    if not isinstance(settings, WorkerSerenaSettings):
        raise WorkerSettingsApplyError("SETTINGS_INVALID")
    if not isinstance(serena_home_subdir, str) or not re.fullmatch(
        r"[A-Za-z0-9_-]+", serena_home_subdir
    ):
        raise WorkerSettingsApplyError("SERENA_HOME_SUBDIR_INVALID")
    root = Path(instances_root).expanduser().resolve(strict=False)
    if not root.is_dir():
        raise WorkerSettingsApplyError("INSTANCES_ROOT_NOT_FOUND")
    target_dir = (root / settings.worker_id / serena_home_subdir).resolve(strict=False)
    if target_dir != root / settings.worker_id / serena_home_subdir or root not in target_dir.parents:
        raise WorkerSettingsApplyError("SETTINGS_TARGET_OUTSIDE_ROOT")
    target_dir.mkdir(parents=True, exist_ok=True)

    rendered = settings.render_serena_config(project_path=project_path)
    target = target_dir / "serena_config.yml"
    temp_path = target_dir / ".serena_config.yml.tmp"
    temp_path.write_text(rendered, encoding="utf-8", newline="\n")
    os.replace(temp_path, target)
    return target


_BRAIN_MARKER = "# A-CONDUCTOR SECOND BRAIN (managed by A-Conductor — do not edit by hand)"


def _brain_block_text(settings: WorkerSerenaSettings) -> str:
    lines = [
        _BRAIN_MARKER,
        "system_prompt: |",
        "  [A-CONDUCTOR SECOND BRAIN]",
        "  Brain folders (source of truth; session memory is not):",
    ]
    for index, folder in enumerate(settings.brain_folders, start=1):
        lines.append(f"  {index}) {folder}")
    if settings.brain_entry_files:
        lines.append("  Must-read BEFORE starting the task (use read_file):")
        for entry in settings.brain_entry_files:
            lines.append(f"  - {entry}")
    lines.extend(
        [
            "  Rules:",
            "  - Read every must-read file BEFORE starting the task.",
            "  - Before write_file/execute_shell or any mutation, state which rule or protocol you are following.",
            "  - Pull further brain content on demand (get_dir_tree/read_file); do not assume memory.",
        ]
    )
    return "\n".join(lines) + "\n"


def apply_brain_to_serena_home(
    settings: WorkerSerenaSettings, serena_home: Path | str
) -> str:
    """Append-only brain injection into an existing validated serena_config.yml.

    Never rewrites the whole file: strips a previously managed brain block
    (marker to EOF) and appends the current one. Refuses when the file is
    missing, when the profile has no brain configured, or when a foreign
    ``system_prompt`` already exists.
    """
    if not isinstance(settings, WorkerSerenaSettings):
        raise ValueError("settings must be a WorkerSerenaSettings")
    home = Path(serena_home).expanduser().resolve(strict=False)
    config_path = home / "serena_config.yml"
    if not config_path.is_file():
        return "SKIPPED_NO_CONFIG"
    if not settings.brain_folders and not settings.brain_entry_files:
        return "SKIPPED_NO_BRAIN"
    text = config_path.read_text(encoding="utf-8", errors="strict")

    marker_index = text.find(_BRAIN_MARKER)
    if marker_index != -1:
        text = text[:marker_index].rstrip("\r\n") + "\n"
    probe = text.split(_BRAIN_MARKER)[0]
    for line in probe.splitlines():
        if line.strip().startswith("system_prompt:"):
            return "SKIPPED_SYSTEM_PROMPT_PRESENT"

    if not text.endswith("\n"):
        text += "\n"
    text += "\n" + _brain_block_text(settings)
    temp_path = home / ".serena_config.brain.tmp"
    temp_path.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temp_path, config_path)
    return "APPLIED"
