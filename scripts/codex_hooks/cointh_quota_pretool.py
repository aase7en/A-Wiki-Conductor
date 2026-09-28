#!/usr/bin/env python3
"""Fresh CoinTH quota guard for explicit GLM-5.3 Codex tool requests.

This hook is deliberately model-free and stateless. It never grants tool
permission; a positive quota result simply leaves Codex's normal permission
flow untouched.
"""

from __future__ import annotations

import json
import math
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime
from typing import Any

_MAX_STDIN_BYTES = 262_144
_MAX_QUOTA_BYTES = 32_768
_CREDENTIAL_ENV = "COINTH_GLM_AUTH_TOKEN"
_QUOTA_URL = "https://cointh.com/glm/api/quota"
_GLM_53 = re.compile(r"(?i)(?:^|[^a-z0-9])glm[ ._/-]*5[ ._/-]*3(?:$|[^0-9])")
_CLI_NAMES = {"kilo", "kilo.exe", "kilo.cmd", "claude", "claude.exe", "claude.cmd"}


def _emit_deny(reason: str) -> None:
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            },
            separators=(",", ":"),
        )
    )


def _read_event() -> dict[str, Any]:
    raw = sys.stdin.buffer.read(_MAX_STDIN_BYTES + 1)
    if len(raw) > _MAX_STDIN_BYTES:
        return {}
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _is_glm_53(value: object) -> bool:
    return isinstance(value, str) and _GLM_53.search(value) is not None


def _model_option_is_glm(tokens: list[str], *, kilo: bool) -> bool:
    """Read explicit --model/-m option values, never natural-language prompt text."""
    start = 0
    if kilo:
        try:
            start = tokens.index("run") + 1
        except ValueError:
            return False
        # Kilo's documented syntax places its positional message after `run`.
        # Skip that whole shlex token so text inside the prompt is not an option.
        if start < len(tokens):
            start += 1

    i = start
    while i < len(tokens):
        token = tokens[i]
        if token in {"--model", "-m"}:
            if i + 1 < len(tokens) and _is_glm_53(tokens[i + 1]):
                return True
            i += 2
            continue
        if token.startswith("--model=") and _is_glm_53(token.partition("=")[2]):
            return True
        i += 1
    return False


_MODEL_ENV_NAMES = {
    "ANTHROPIC_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
}
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def _argv_has_cli_model_selector(tokens: list[str], assignments: list[str]) -> bool:
    """Inspect one shell command whose first executable is a supported CLI."""
    index = 0
    while index < len(tokens) and _ASSIGNMENT.match(tokens[index]):
        assignments.append(tokens[index])
        index += 1
    if index < len(tokens) and tokens[index].replace("\\", "/").rsplit("/", 1)[-1].lower() == "env":
        index += 1
        while index < len(tokens):
            if tokens[index] in {"-i", "--ignore-environment"}:
                index += 1
            elif tokens[index] in {"-u", "--unset"} and index + 1 < len(tokens):
                index += 2
            elif tokens[index].startswith("--unset="):
                index += 1
            elif tokens[index] == "--":
                index += 1
                break
            elif _ASSIGNMENT.match(tokens[index]):
                assignments.append(tokens[index])
                index += 1
            else:
                break
    if index < len(tokens) and tokens[index] in {"command", "exec"}:
        index += 1
    if index >= len(tokens):
        return False

    executable = tokens[index].rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
    if executable not in _CLI_NAMES:
        return False
    if _model_option_is_glm(tokens[index + 1 :], kilo=executable.startswith("kilo")):
        return True
    for assignment in assignments:
        name, _, value = assignment.partition("=")
        if name in _MODEL_ENV_NAMES and _is_glm_53(value):
            return True
    return False


def _argv_tokens_have_cli_model_selector(tokens: list[str]) -> bool:
    return _argv_has_cli_model_selector(tokens, [])


def _read_heredoc_delimiter(command: str, index: int) -> tuple[str | None, int]:
    """Read one heredoc delimiter word, honoring a single quoting level."""
    length = len(command)
    if index >= length:
        return None, index
    quote = command[index]
    if quote in {"'", '"'}:
        end = command.find(quote, index + 1)
        if end == -1:
            return None, index
        return command[index + 1 : end], end + 1
    end = index
    while end < length and command[end] not in " \t\r\n;&|":
        end += 1
    if end == index:
        return None, index
    return command[index:end], end


def _skip_heredoc_body(command: str, index: int, delimiter: str, strip_tabs: bool) -> int:
    """Skip raw heredoc body lines through the terminating delimiter line."""
    length = len(command)
    while index < length:
        line_end = command.find("\n", index)
        if line_end == -1:
            return length
        line = command[index:line_end]
        if (line.lstrip("\t") if strip_tabs else line) == delimiter:
            return line_end + 1
        index = line_end + 1
    return index


def _split_shell_command_segments(command: str) -> list[str]:
    """Split on unquoted separators and newlines; quoted text stays whole."""
    segments: list[str] = []
    current: list[str] = []
    pending: list[tuple[str, bool]] = []
    index = 0
    length = len(command)

    def flush() -> None:
        segments.append("".join(current))
        current.clear()

    while index < length:
        char = command[index]
        if char in ";&|\n":
            flush()
            index += 1
            if char == "\n" and pending:
                for delimiter, strip_tabs in pending:
                    index = _skip_heredoc_body(command, index, delimiter, strip_tabs)
                pending.clear()
            continue
        if char == "\\":
            current.append(char)
            if index + 1 < length:
                current.append(command[index + 1])
                index += 2
            else:
                index += 1
            continue
        if char == "'":
            end = command.find("'", index + 1)
            if end == -1:
                current.append(command[index:])
                index = length
            else:
                current.append(command[index : end + 1])
                index = end + 1
            continue
        if char == '"':
            end = index + 1
            while end < length and command[end] != '"':
                if command[end] == "\\" and end + 1 < length:
                    end += 2
                else:
                    end += 1
            if end < length:
                current.append(command[index : end + 1])
                index = end + 1
            else:
                current.append(command[index:])
                index = length
            continue
        if char == "<" and command.startswith("<<", index):
            if index + 2 < length and command[index + 2] == "<":
                current.append(command[index : index + 3])
                index += 3
                continue
            index += 2
            strip_tabs = index < length and command[index] == "-"
            if strip_tabs:
                index += 1
            while index < length and command[index] in " \t":
                index += 1
            delimiter, index = _read_heredoc_delimiter(command, index)
            if delimiter is None:
                current.append("<<")
                continue
            pending.append((delimiter, strip_tabs))
            current.append("<<")
            current.append(delimiter)
            continue
        if char == "#" and (not current or current[-1] in " \t"):
            # Unquoted word-start '#' opens a shell comment through end of
            # line; quoted or mid-word '#' stays literal text.
            newline = command.find("\n", index)
            index = length if newline == -1 else newline
            continue
        current.append(char)
        index += 1

    segments.append("".join(current))
    return segments


def _shell_command_has_cli_model_selector(command: str) -> bool:
    """Parse command segments without treating quoted prompt text as a CLI."""
    for segment in _split_shell_command_segments(command):
        try:
            lexer = shlex.shlex(segment, posix=True, punctuation_chars=";&|")
            lexer.whitespace_split = True
            lexer.commenters = ""
            tokens = list(lexer)
        except ValueError:
            continue
        if _argv_has_cli_model_selector(tokens, []):
            return True
    return False


def _cli_model_selector(command: object) -> bool:
    if not isinstance(command, str) or len(command) > _MAX_STDIN_BYTES:
        return False
    return _shell_command_has_cli_model_selector(command)


def _explicit_glm_request(event: dict[str, Any]) -> bool:
    tool_name = event.get("tool_name")
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return False

    if tool_name == "Bash":
        return _cli_model_selector(tool_input.get("command"))

    if tool_name in {
        "mcp__sunday_mcp__sunday_dispatch",
        "mcp__codex_apps__sundaymcp_mac_sunday_dispatch",
    }:
        model = tool_input.get("model")
        if _is_glm_53(model):
            return True
        command = tool_input.get("command")
        args = tool_input.get("args")
        if isinstance(args, list) and all(isinstance(arg, str) for arg in args):
            argv = ([command] if isinstance(command, str) else []) + args
            return _argv_tokens_have_cli_model_selector(argv)
        else:
            return _cli_model_selector(command)
    return False


def _curl_config_value(value: str) -> str:
    if "\r" in value or "\n" in value:
        raise ValueError("credential contains a forbidden line break")
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _quota_state() -> tuple[str, dict[str, Any]]:
    token = os.environ.get(_CREDENTIAL_ENV)
    if not token:
        return "UNKNOWN", {"reason": "missing_credential"}

    try:
        token = _curl_config_value(token)
        config = (
            f'url = "{_QUOTA_URL}"\n'
            f'header = "x-api-key: {token}"\n'
            'header = "Cache-Control: no-cache"\n'
            'header = "Pragma: no-cache"\n'
            f'max-filesize = "{_MAX_QUOTA_BYTES}"\n'
            'connect-timeout = "2"\n'
            'max-time = "8"\n'
            'write-out = "\\nCOINTH_HTTP_STATUS:%{http_code}"\n'
        )
        child_env = os.environ.copy()
        child_env.pop(_CREDENTIAL_ENV, None)
        completed = subprocess.run(
            ["/usr/bin/curl", "--config", "-", "--silent", "--show-error"],
            input=config.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
            env=child_env,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
        return "UNKNOWN", {"reason": "quota_request_failed"}

    output = completed.stdout.decode("utf-8", "replace")
    if len(completed.stdout) > _MAX_QUOTA_BYTES + 64:
        return "UNKNOWN", {"reason": "quota_response_too_large"}
    body, separator, status_text = output.rpartition("\nCOINTH_HTTP_STATUS:")
    if completed.returncode != 0 or not separator or not status_text.strip().isdigit():
        return "UNKNOWN", {"reason": "quota_transport_error"}
    status = int(status_text.strip())
    if status != 200:
        return "UNKNOWN", {"reason": "quota_http_error", "http_status": status}

    try:
        payload = json.loads(body)
    except (UnicodeError, json.JSONDecodeError):
        return "UNKNOWN", {"reason": "quota_malformed_json", "http_status": status}
    if not isinstance(payload, dict):
        return "UNKNOWN", {"reason": "quota_malformed_json", "http_status": status}

    fields = ("remaining_5h", "used_5h", "limit_5h", "window_reset_at", "window_reset_in_sec")
    if any(field not in payload for field in fields):
        return "UNKNOWN", {"reason": "quota_incomplete_tuple", "http_status": status}
    if "is_expired" in payload and not isinstance(payload["is_expired"], bool):
        return "UNKNOWN", {"reason": "quota_invalid_expiry_flag", "http_status": status}
    if payload.get("is_expired") is True:
        return "UNKNOWN", {"reason": "quota_expired", "http_status": status}

    counters = (payload["remaining_5h"], payload["used_5h"], payload["limit_5h"], payload["window_reset_in_sec"])
    if any(type(value) is not int for value in counters):
        return "UNKNOWN", {"reason": "quota_invalid_counter_type", "http_status": status}
    remaining, used, limit, reset_in = counters
    reset_at = payload["window_reset_at"]
    reset_at_valid = (
        type(reset_at) is int and 0 < reset_at <= (2**63 - 1)
    ) or (
        type(reset_at) is float and math.isfinite(reset_at) and reset_at > 0
    )
    if isinstance(reset_at, str):
        try:
            parsed_reset = datetime.fromisoformat(reset_at.replace("Z", "+00:00"))
            reset_at_valid = parsed_reset.tzinfo is not None
        except ValueError:
            reset_at_valid = False
    if (
        remaining < 0
        or used < 0
        or limit < 0
        or reset_in < 0
        or remaining + used != limit
        or not reset_at_valid
    ):
        return "UNKNOWN", {"reason": "quota_inconsistent_tuple", "http_status": status}

    safe = {
        "http_status": status,
        "remaining_5h": remaining,
        "used_5h": used,
        "limit_5h": limit,
        "window_reset_in_sec": reset_in,
        "window_source": payload.get("window_source"),
        "is_expired": payload.get("is_expired"),
    }
    return ("AVAILABLE" if remaining > 0 else "EXHAUSTED"), safe


def main() -> int:
    event = _read_event()
    if not _explicit_glm_request(event):
        return 0
    try:
        state, evidence = _quota_state()
    except Exception:
        state, evidence = "UNKNOWN", {"reason": "quota_internal_error"}
    if state == "AVAILABLE":
        # No permission override: continue under Codex's ordinary policy.
        return 0
    if state == "EXHAUSTED":
        _emit_deny("CoinTH proxy quota is exhausted (valid remaining_5h is zero).")
    else:
        reason = evidence.get("reason", "quota_evidence_unavailable")
        _emit_deny(f"CoinTH quota could not be verified ({reason}); GLM request blocked fail-closed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
