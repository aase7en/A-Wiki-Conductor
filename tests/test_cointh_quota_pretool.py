"""WO-P1-564 / Issue #564 focused offline tests + WO-P1-787 / Issue #787 G2.

The WO-P1-564 layers cover the GLM-command detection repaired in
``scripts/codex_hooks/cointh_quota_pretool.py``: newline-separated explicit
GLM commands, quoted multiline prompt non-matches, recognized here-document
body non-matches, and preserved separator / env-wrapped selector behavior.

The WO-P1-787 G2 layers pin the offline quota classification seam
(``_quota_state``) to its current truth: AVAILABLE/EXHAUSTED vs the exact
UNKNOWN reason-code vocabulary, HTTP 401/403 mapping, ``window_source``
pass-through, and credential stripping from the child curl environment.

The tests exercise pure helpers directly and the quota seam only through a
recorded ``subprocess.run`` stand-in with DUMMY tokens. They never read real
credentials, open sockets, spawn processes, or touch the network.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

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


# --- WO-P1-787 G2: offline quota classification fixtures (current-code truth) ---

_DUMMY_TOKEN = "wo787-dummy-token-not-a-real-credential"


def _quota_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "remaining_5h": 40,
        "used_5h": 10,
        "limit_5h": 50,
        "window_reset_at": 1795767600,
        "window_reset_in_sec": 600,
        "is_expired": False,
        "window_source": "quota_window_fresh",
    }
    payload.update(overrides)
    return payload


def _quota_output(payload: Any, *, status: int = 200) -> bytes:
    if isinstance(payload, bytes):
        body = payload
    elif isinstance(payload, str):
        body = payload.encode("utf-8")
    else:
        body = json.dumps(payload).encode("utf-8")
    return body + f"\nCOINTH_HTTP_STATUS:{status}".encode("ascii")


class _FakeCurl:
    """Recording ``subprocess.run`` stand-in; never spawns a process."""

    def __init__(
        self,
        *,
        stdout: bytes = b"",
        returncode: int = 0,
        error: Exception | None = None,
    ) -> None:
        self.stdout = stdout
        self.returncode = returncode
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def __call__(self, args: Any, **kwargs: Any) -> SimpleNamespace:
        self.calls.append({"args": list(args), **kwargs})
        if self.error is not None:
            raise self.error
        return SimpleNamespace(stdout=self.stdout, returncode=self.returncode)


def _run_quota_state(
    monkeypatch: pytest.MonkeyPatch, fake: _FakeCurl
) -> tuple[str, dict[str, Any]]:
    monkeypatch.setenv(HOOK._CREDENTIAL_ENV, _DUMMY_TOKEN)
    monkeypatch.setattr(subprocess, "run", fake)
    return HOOK._quota_state()


@pytest.mark.parametrize(
    ("overrides", "expected_state"),
    [
        pytest.param({"remaining_5h": 40, "used_5h": 10}, "AVAILABLE", id="positive-remaining"),
        pytest.param({"remaining_5h": 0, "used_5h": 50}, "EXHAUSTED", id="valid-zero"),
    ],
)
def test_quota_state_consistent_tuple_classifies_available_or_exhausted(
    monkeypatch: pytest.MonkeyPatch,
    overrides: dict[str, Any],
    expected_state: str,
) -> None:
    fake = _FakeCurl(stdout=_quota_output(_quota_payload(**overrides)))
    state, evidence = _run_quota_state(monkeypatch, fake)
    assert state == expected_state
    assert state != "UNKNOWN"
    assert evidence["remaining_5h"] == overrides["remaining_5h"]
    assert evidence["used_5h"] == overrides["used_5h"]
    assert evidence["limit_5h"] == 50
    assert evidence["window_reset_in_sec"] == 600
    assert evidence["http_status"] == 200
    assert evidence["is_expired"] is False
    assert "reason" not in evidence


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"remaining_5h": 10, "used_5h": 10}, id="sum-mismatch"),
        pytest.param({"remaining_5h": -1, "used_5h": 51}, id="negative-remaining"),
    ],
)
def test_quota_state_inconsistent_tuple_is_unknown_without_false_exhaustion(
    monkeypatch: pytest.MonkeyPatch, overrides: dict[str, Any]
) -> None:
    fake = _FakeCurl(stdout=_quota_output(_quota_payload(**overrides)))
    state, evidence = _run_quota_state(monkeypatch, fake)
    assert state == "UNKNOWN"
    assert evidence == {"reason": "quota_inconsistent_tuple", "http_status": 200}


@pytest.mark.parametrize(
    "body",
    [
        pytest.param('{"remaining_5h": 40,', id="invalid-json"),
        pytest.param("[40, 10, 50]", id="json-array-not-object"),
    ],
)
def test_quota_state_malformed_body_is_unknown(
    monkeypatch: pytest.MonkeyPatch, body: str
) -> None:
    fake = _FakeCurl(stdout=_quota_output(body))
    state, evidence = _run_quota_state(monkeypatch, fake)
    assert state == "UNKNOWN"
    assert evidence == {"reason": "quota_malformed_json", "http_status": 200}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("remaining_5h", "40", id="string-remaining"),
        pytest.param("used_5h", 10.0, id="float-used"),
        pytest.param("limit_5h", True, id="boolean-limit"),
        pytest.param("window_reset_in_sec", None, id="null-reset-in"),
    ],
)
def test_quota_state_non_integer_counter_is_unknown(
    monkeypatch: pytest.MonkeyPatch, field: str, value: Any
) -> None:
    fake = _FakeCurl(stdout=_quota_output(_quota_payload(**{field: value})))
    state, evidence = _run_quota_state(monkeypatch, fake)
    assert state == "UNKNOWN"
    assert evidence == {"reason": "quota_invalid_counter_type", "http_status": 200}


@pytest.mark.parametrize(
    ("flag", "expected_reason"),
    [
        pytest.param(True, "quota_expired", id="expired-true"),
        pytest.param("false", "quota_invalid_expiry_flag", id="non-bool-flag"),
    ],
)
def test_quota_state_expiry_flag_gate_is_unknown(
    monkeypatch: pytest.MonkeyPatch, flag: Any, expected_reason: str
) -> None:
    fake = _FakeCurl(stdout=_quota_output(_quota_payload(is_expired=flag)))
    state, evidence = _run_quota_state(monkeypatch, fake)
    assert state == "UNKNOWN"
    assert evidence == {"reason": expected_reason, "http_status": 200}


@pytest.mark.parametrize(
    ("stdout", "returncode"),
    [
        pytest.param(b"", 6, id="curl-nonzero-exit"),
        pytest.param(b'{"remaining_5h": 40}', 0, id="missing-status-marker"),
        pytest.param(
            b'{"remaining_5h": 40}\nCOINTH_HTTP_STATUS:2OO',
            0,
            id="non-digit-status",
        ),
    ],
)
def test_quota_state_transport_failure_is_unknown(
    monkeypatch: pytest.MonkeyPatch, stdout: bytes, returncode: int
) -> None:
    fake = _FakeCurl(stdout=stdout, returncode=returncode)
    state, evidence = _run_quota_state(monkeypatch, fake)
    assert state == "UNKNOWN"
    assert evidence == {"reason": "quota_transport_error"}


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(subprocess.TimeoutExpired(cmd="/usr/bin/curl", timeout=10), id="timeout"),
        pytest.param(OSError("curl binary unavailable"), id="os-error"),
    ],
)
def test_quota_state_request_failure_is_unknown(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    fake = _FakeCurl(error=error)
    state, evidence = _run_quota_state(monkeypatch, fake)
    assert state == "UNKNOWN"
    assert evidence == {"reason": "quota_request_failed"}


@pytest.mark.parametrize("http_status", [401, 403])
def test_quota_state_http_error_is_unknown_with_quota_http_error_reason(
    monkeypatch: pytest.MonkeyPatch, http_status: int
) -> None:
    fake = _FakeCurl(stdout=_quota_output(_quota_payload(), status=http_status))
    state, evidence = _run_quota_state(monkeypatch, fake)
    # current seam has no separate AUTH state/reason: HTTP errors stay UNKNOWN
    assert state == "UNKNOWN"
    assert evidence == {"reason": "quota_http_error", "http_status": http_status}


def test_quota_state_missing_credential_is_unknown_without_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(HOOK._CREDENTIAL_ENV, raising=False)
    fake = _FakeCurl()
    monkeypatch.setattr(subprocess, "run", fake)
    state, evidence = HOOK._quota_state()
    assert state == "UNKNOWN"
    assert evidence == {"reason": "missing_credential"}
    assert fake.calls == []


@pytest.mark.parametrize(
    "window_source",
    ["quota_window_fresh", "quota_window_stale", "stale-cache-2026", None],
)
def test_quota_state_window_source_passes_through_verbatim(
    monkeypatch: pytest.MonkeyPatch, window_source: Any
) -> None:
    fake = _FakeCurl(stdout=_quota_output(_quota_payload(window_source=window_source)))
    state, evidence = _run_quota_state(monkeypatch, fake)
    assert state == "AVAILABLE"
    assert evidence["window_source"] == window_source


def test_quota_state_stale_window_source_is_never_promoted_to_fresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeCurl(
        stdout=_quota_output(_quota_payload(window_source="quota_window_stale"))
    )
    state, evidence = _run_quota_state(monkeypatch, fake)
    assert state == "AVAILABLE"
    assert evidence["window_source"] == "quota_window_stale"
    assert evidence["window_source"] != "quota_window_fresh"


def test_quota_state_child_process_keeps_credential_out_of_env_and_argv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeCurl(stdout=_quota_output(_quota_payload()))
    state, _evidence = _run_quota_state(monkeypatch, fake)
    assert state == "AVAILABLE"
    assert len(fake.calls) == 1
    call = fake.calls[0]
    child_env = call["env"]
    assert isinstance(child_env, dict)
    assert HOOK._CREDENTIAL_ENV not in child_env
    assert not any(_DUMMY_TOKEN in str(value) for value in child_env.values())
    assert not any(_DUMMY_TOKEN in str(arg) for arg in call["args"])
    assert _DUMMY_TOKEN.encode("utf-8") in call["input"]


def test_quota_state_oversized_response_is_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bloated = _quota_output(_quota_payload()) + b"#" * (HOOK._MAX_QUOTA_BYTES + 65)
    fake = _FakeCurl(stdout=bloated)
    state, evidence = _run_quota_state(monkeypatch, fake)
    assert state == "UNKNOWN"
    assert evidence == {"reason": "quota_response_too_large"}


@pytest.mark.parametrize(
    "missing_field",
    ["remaining_5h", "used_5h", "limit_5h", "window_reset_at", "window_reset_in_sec"],
)
def test_quota_state_incomplete_tuple_is_unknown(
    monkeypatch: pytest.MonkeyPatch, missing_field: str
) -> None:
    payload = _quota_payload()
    del payload[missing_field]
    fake = _FakeCurl(stdout=_quota_output(payload))
    state, evidence = _run_quota_state(monkeypatch, fake)
    assert state == "UNKNOWN"
    assert evidence == {"reason": "quota_incomplete_tuple", "http_status": 200}


@pytest.mark.parametrize(
    ("reset_at", "expected_state"),
    [
        pytest.param(1795767600, "AVAILABLE", id="epoch-int"),
        pytest.param(1795767600.0, "AVAILABLE", id="finite-float"),
        pytest.param("2026-11-23T10:00:00+00:00", "AVAILABLE", id="tz-aware-iso"),
        pytest.param("2026-11-23T10:00:00", "UNKNOWN", id="naive-iso"),
        pytest.param("1795767600", "UNKNOWN", id="numeric-string"),
    ],
)
def test_quota_state_window_reset_at_validity_as_presently_defined(
    monkeypatch: pytest.MonkeyPatch, reset_at: Any, expected_state: str
) -> None:
    fake = _FakeCurl(stdout=_quota_output(_quota_payload(window_reset_at=reset_at)))
    state, evidence = _run_quota_state(monkeypatch, fake)
    if expected_state == "AVAILABLE":
        assert state == "AVAILABLE"
        assert evidence["window_reset_in_sec"] == 600
    else:
        assert state == "UNKNOWN"
        assert evidence == {"reason": "quota_inconsistent_tuple", "http_status": 200}
