"""WO-P1-564 / Issue #564 (scope addendum 5865895184) focused offline tests.

These tests cover only the GLM-command detection repaired in
``scripts/codex_hooks/cointh_quota_pretool.py``: newline-separated explicit
GLM commands, quoted multiline prompt non-matches, recognized here-document
body non-matches, and preserved separator / env-wrapped selector behavior.

The tests exercise the hook's pure parsing helpers directly. They never read
credentials, open sockets, spawn subprocesses, or enter the quota path.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "codex_hooks" / "cointh_quota_pretool.py"


def _load_hook() -> Any:
    spec = importlib.util.spec_from_file_location(
        "cointh_quota_pretool_under_test", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


HOOK = _load_hook()


def _detect(command: str) -> bool:
    return HOOK._cli_model_selector(command)


def _segments(command: str) -> list[str]:
    return HOOK._split_shell_command_segments(command)


def test_newline_separated_kilo_run_model_option_is_detected() -> None:
    command = 'printf \'preparing\'\nkilo run "finish the report" --model glm-5.3'
    assert _detect(command)


def test_newline_separated_claude_model_equals_form_is_detected() -> None:
    command = "cd /tmp\nclaude --model=glm-5.3 -p 'check'"
    assert _detect(command)


def test_newline_separated_path_qualified_kilo_short_flag_is_detected() -> None:
    command = 'ls -la\n/usr/local/bin/kilo run "task" -m GLM-5.3'
    assert _detect(command)


def test_prose_and_blank_lines_before_glm_command_still_detected() -> None:
    command = 'echo one\n\necho two\nkilo run "task" --model glm-5.3'
    assert _detect(command)


def test_quoted_multiline_prompt_mention_is_not_a_selector() -> None:
    command = 'kilo run "step one: draft\nstep two: mention glm-5.3 in notes"'
    assert not _detect(command)


def test_quoted_prompt_token_containing_model_text_is_positional() -> None:
    command = 'kilo run "instructions: pass --model glm-5.3"'
    assert not _detect(command)


def test_quoted_multiline_text_stays_one_segment() -> None:
    command = 'echo "line one\nkilo run \'x\' --model glm-5.3\nline three"'
    assert _segments(command) == [command]
    assert not _detect(command)


def test_inline_shell_comment_selector_is_ignored() -> None:
    command = 'kilo run "task" # example: --model glm-5.3'
    assert not _detect(command)


def test_comment_ignored_but_later_newline_glm_command_detected() -> None:
    command = 'kilo run "task" # example: --model glm-5.3\nkilo run "real task" --model glm-5.3'
    assert _detect(command)


def test_leading_comment_line_selector_is_ignored() -> None:
    command = '# kilo run "docs example" --model glm-5.3\necho done'
    assert not _detect(command)


def test_midword_hash_is_not_a_comment() -> None:
    command = 'kilo run task#note --model glm-5.3'
    assert _detect(command)


def test_quoted_delimiter_heredoc_body_is_skipped() -> None:
    command = (
        "cat <<'EOF'\nExample dispatch:\nkilo run \"task\" --model glm-5.3\nEOF"
    )
    assert not _detect(command)


def test_unquoted_delimiter_heredoc_body_is_skipped() -> None:
    command = 'cat <<EOF\nkilo run "work" -m glm-5.3\nEOF'
    assert not _detect(command)


def test_dash_heredoc_with_tab_indented_terminator_is_skipped() -> None:
    command = "cat <<-EOF\n\tclaude --model glm-5.3\n\tEOF"
    assert not _detect(command)


def test_unterminated_heredoc_consumes_remaining_lines() -> None:
    command = 'cat <<EOF\nkilo run "x" --model glm-5.3'
    assert not _detect(command)


def test_command_after_heredoc_terminator_is_detected() -> None:
    command = (
        'cat <<\'EOF\'\ndocumentation only\nEOF\n'
        'kilo run "real task" --model glm-5.3'
    )
    assert _detect(command)


def test_semicolon_separated_selector_is_detected() -> None:
    command = 'echo prepare; kilo run "task" --model glm-5.3'
    assert _detect(command)


def test_double_ampersand_chain_selector_is_detected() -> None:
    command = "cd /tmp && claude --model=glm-5.3 -p 'check'"
    assert _detect(command)


def test_pipe_separated_selector_is_detected() -> None:
    command = "printf 'notes' | kilo run \"task\" -m glm-5.3"
    assert _detect(command)


def test_env_assignment_prefix_selector_is_detected() -> None:
    command = "ANTHROPIC_MODEL=glm-5.3 claude -p 'hello'"
    assert _detect(command)


def test_usr_bin_env_wrapped_cli_option_is_detected() -> None:
    command = '/usr/bin/env kilo run "task" --model glm-5.3'
    assert _detect(command)


def test_usr_bin_env_wrapped_model_assignment_is_detected() -> None:
    command = "/usr/bin/env ANTHROPIC_MODEL=glm-5.3 claude -p 'hello'"
    assert _detect(command)


def test_env_ignore_environment_assignment_is_detected() -> None:
    command = "env -i ANTHROPIC_MODEL=glm-5.3 claude -p 'hi'"
    assert _detect(command)


def test_git_commit_message_mention_is_not_matched() -> None:
    command = 'git commit -m "notes about glm-5.3"'
    assert not _detect(command)


def test_bash_event_routing_for_newline_command() -> None:
    matched = {
        "tool_name": "Bash",
        "tool_input": {"command": 'echo prep\nkilo run "t" --model glm-5.3'},
    }
    assert HOOK._explicit_glm_request(matched)
    unmatched = {
        "tool_name": "Bash",
        "tool_input": {"command": 'echo "glm-5.3 docs"'},
    }
    assert not HOOK._explicit_glm_request(unmatched)


def test_sunday_dispatch_argv_env_wrapped_selector_is_detected() -> None:
    matched = {
        "tool_name": "mcp__codex_apps__sundaymcp_mac_sunday_dispatch",
        "tool_input": {"args": ["ANTHROPIC_MODEL=glm-5.3", "claude", "-p", "hi"]},
    }
    assert HOOK._explicit_glm_request(matched)
    unmatched = {
        "tool_name": "mcp__codex_apps__sundaymcp_mac_sunday_dispatch",
        "tool_input": {"args": ["claude", "-p", "hi"]},
    }
    assert not HOOK._explicit_glm_request(unmatched)
