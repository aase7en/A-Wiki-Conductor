"""Issue #545 contract tests for the project-local Codex lifecycle hooks."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / ".codex" / "hooks.json"
SCRIPT = ROOT / ".codex" / "hooks" / "a_sunday_lifecycle.py"


def _run(payload: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == ""
    return json.loads(proc.stdout or "{}")


def _base(event: str) -> dict:
    return {
        "session_id": "session-test",
        "transcript_path": None,
        "cwd": str(ROOT),
        "hook_event_name": event,
        "model": "gpt-6-luna",
        "permission_mode": "default",
        "turn_id": "turn-test",
    }


def _receipt(path: Path, *, reason: str = "NEXT_READY", status: str = "CONTINUE") -> dict:
    return {
        "schema_version": "1.0.0",
        "receipt_type": "NIGHTSHIFT_TURN_RECEIPT",
        "run_id": "nightshift-hook-test",
        "thread_id": "01234567-89ab-cdef-0123-456789abcdef",
        "parent_exec_ref": "exec-parent-abc123",
        "model": "gpt-6-luna",
        "effort": "high",
        "contract_ref": "/tmp/nightshift-hook-test/supervisor-contract.md",
        "receipt_ref": str(path),
        "authority_repo_ref": str(ROOT),
        "worktree_ref": str(ROOT),
        "capability_evidence_version": "codex-resume-v1",
        "generation": 4,
        "generated_at": "2026-09-24T14:00:00Z",
        "status": status,
        "reason": reason,
        "stop_gate": "NONE",
        "outstanding_exec_refs": [],
        "next_safe_action_ref": "issue:545#next-safe-action",
    }


def test_hook_config_registers_required_codex_events() -> None:
    data = json.loads(HOOKS.read_text(encoding="utf-8"))
    hooks = data["hooks"]
    assert set(hooks) == {
        "SessionStart",
        "UserPromptSubmit",
        "PreCompact",
        "PostCompact",
        "PreToolUse",
        "PostToolUse",
        "Interrupt",
        "Stop",
    }
    for groups in hooks.values():
        assert groups
        for group in groups:
            for handler in group["hooks"]:
                assert handler["type"] == "command"
                assert "a_sunday_lifecycle.py" in handler["command"]
                assert "commandWindows" in handler
                assert "powershell" in handler["commandWindows"].lower()
                assert "git rev-parse --show-toplevel" in handler["commandWindows"]
                assert "a_sunday_lifecycle.py" in handler["commandWindows"]


def test_session_start_reinjects_full_supervisor_contract_after_compaction() -> None:
    payload = _base("SessionStart")
    payload["source"] = "compact"
    out = _run(payload)
    specific = out["hookSpecificOutput"]
    assert specific["hookEventName"] == "SessionStart"
    context = specific["additionalContext"]
    for token in (
        "RECOVER -> RECONCILE -> HARVEST",
        "A-FastTask -> A-Faster -> A-NightShift",
        "GLM-5.3 MAX",
        "GLM-5.3-Flash",
        "JEV",
        "System-One fast advisory",
        "SunDay-Worker 1..5",
        "SundayMCP Mac",
        "Actual durable evidence wins",
        "no manufactured work",
    ):
        assert token in context


def test_user_prompt_submit_reinjects_activation_without_rewriting_prompt() -> None:
    payload = _base("UserPromptSubmit")
    payload["prompt"] = "continue the roadmap"
    out = _run(payload)
    specific = out["hookSpecificOutput"]
    assert specific["hookEventName"] == "UserPromptSubmit"
    assert "A-Faster" in specific["additionalContext"]
    assert "A-NightShift" in specific["additionalContext"]
    assert "updatedInput" not in json.dumps(out)


def test_compaction_hooks_are_stateless_and_do_not_create_shadow_authority() -> None:
    for event in ("PreCompact", "PostCompact"):
        payload = _base(event)
        payload["trigger"] = "auto"
        assert _run(payload) == {"continue": True}


def test_direct_kilo_heavy_bypass_is_denied_but_readiness_probe_is_not() -> None:
    payload = _base("PreToolUse")
    payload.update({
        "tool_name": "Bash",
        "tool_use_id": "tool-1",
        "tool_input": {"command": "kilo run --model cointh-glm/glm-5.3 --variant max task"},
    })
    out = _run(payload)
    specific = out["hookSpecificOutput"]
    assert specific["permissionDecision"] == "deny"
    assert "sunday_dispatch" in specific["permissionDecisionReason"]

    payload["tool_input"] = {"command": "kilo roll-call"}
    probe = _run(payload)
    assert "permissionDecision" not in probe.get("hookSpecificOutput", {})


def test_sunday_dispatch_gets_binding_and_provider_context_not_a_second_guard() -> None:
    payload = _base("PreToolUse")
    payload.update({
        "tool_name": "mcp__SundayMCP_Mac__sunday_dispatch",
        "tool_use_id": "tool-2",
        "tool_input": {"command": "/usr/bin/env", "mode": "mutate"},
    })
    out = _run(payload)
    specific = out["hookSpecificOutput"]
    assert specific["hookEventName"] == "PreToolUse"
    context = specific["additionalContext"]
    assert "claim/worktree/branch/HEAD/scope" in context
    assert "fresh structured GLM admission" in context
    assert "share=disabled" in context
    assert "permissionDecision" not in specific


def test_post_sunday_execution_reinjects_harvest_and_refill_rules() -> None:
    payload = _base("PostToolUse")
    payload.update({
        "tool_name": "mcp__SundayMCP_Mac__sunday_harvest",
        "tool_use_id": "tool-3",
        "tool_input": {"execId": "exec-child-abc123"},
        "tool_response": {"ok": True},
    })
    context = _run(payload)["hookSpecificOutput"]["additionalContext"]
    assert "RECOVER -> RECONCILE -> HARVEST" in context
    assert "RUNNING/UNKNOWN" in context
    assert "AUTO_REFILL_REQUIRED" in context


def test_stop_continues_once_only_from_valid_actionable_turn_receipt() -> None:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "turn-receipt.json"
        path.write_text(json.dumps(_receipt(path)), encoding="utf-8")
        payload = _base("Stop")
        payload["stop_hook_active"] = False
        payload["last_assistant_message"] = f"A_SUNDAY_TURN_RECEIPT_REF={path}"
        out = _run(payload)
        assert out["decision"] == "block"
        assert "fresh RECOVER" in out["reason"]
        assert str(path) in out["reason"]

        payload["stop_hook_active"] = True
        assert _run(payload) == {}


def test_stop_never_spins_waiting_terminal_missing_or_malformed_receipts() -> None:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "turn-receipt.json"
        payload = _base("Stop")
        payload["stop_hook_active"] = False
        payload["last_assistant_message"] = f"A_SUNDAY_TURN_RECEIPT_REF={path}"

        path.write_text(json.dumps(_receipt(path, reason="WAITING_EXTERNAL")), encoding="utf-8")
        assert _run(payload) == {}
        path.write_text(json.dumps(_receipt(path, status="TERMINAL")), encoding="utf-8")
        assert _run(payload) == {}
        path.write_text("{broken", encoding="utf-8")
        assert _run(payload) == {}
        path.unlink()
        assert _run(payload) == {}


def test_interrupt_preserves_durable_child_truth_without_restart() -> None:
    out = _run(_base("Interrupt"))
    message = out["systemMessage"]
    assert "parent turn interrupted" in message
    assert "Do not infer durable Sunday child executions were cancelled" in message
    assert "recover status/harvest truth before replay" in message
    assert "decision" not in out


def test_stop_rejects_invalid_v1_receipt_semantics() -> None:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "turn-receipt.json"
        payload = _base("Stop")
        payload["stop_hook_active"] = False
        payload["last_assistant_message"] = f"A_SUNDAY_TURN_RECEIPT_REF={path}"

        invalid_variants = []
        generation_zero = _receipt(path)
        generation_zero["generation"] = 0
        invalid_variants.append(generation_zero)
        bad_reason = _receipt(path)
        bad_reason["reason"] = "NOT_A_REASON"
        invalid_variants.append(bad_reason)
        bad_gate = _receipt(path)
        bad_gate["stop_gate"] = "NOT_A_GATE"
        invalid_variants.append(bad_gate)
        bad_exec = _receipt(path)
        bad_exec["outstanding_exec_refs"] = ["bad-exec-ref"]
        invalid_variants.append(bad_exec)

        for receipt in invalid_variants:
            path.write_text(json.dumps(receipt), encoding="utf-8")
            assert _run(payload) == {}


def test_hook_script_is_read_only_and_has_no_network_or_process_authority() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    for forbidden in (
        "subprocess",
        "urllib",
        "requests",
        "socket",
        "os.system",
        "Popen",
        "write_text",
        "write_bytes",
        "unlink(",
    ):
        assert forbidden not in text



def test_wo545_direct_kilo_bypass_catches_windows_and_quoted_paths() -> None:
    commands = (
        r'"C:\\tools\\kilo.exe" run --model cointh-glm/glm-5.3 task',
        r'C:\\tools\\kilo.exe run --model cointh-glm/glm-5.3 task',
        '"/usr/local/bin/kilo" run --model cointh-glm/glm-5.3 task',
        '/usr/local/bin/kilo run --model cointh-glm/glm-5.3 task',
    )
    for command in commands:
        payload = _base("PreToolUse")
        payload.update(
            {
                "tool_name": "Bash",
                "tool_use_id": "tool-kilo-path",
                "tool_input": {"command": command},
            }
        )
        out = _run(payload)
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny", command


def test_wo545_stop_only_continues_actionable_nonterminal_reasons() -> None:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "turn-receipt.json"
        payload = _base("Stop")
        payload["stop_hook_active"] = False
        payload["last_assistant_message"] = f"A_SUNDAY_TURN_RECEIPT_REF={path}"
        for reason in (
            "QUOTA_EXHAUSTED",
            "HUMAN_ACTION_REQUIRED",
            "HUMAN_DECISION_REQUIRED",
            "AUTHORIZATION_REQUIRED",
            "SAFETY_BLOCK",
            "TRUE_NO_SAFE_NEXT_ACTION",
            "GOAL_COMPLETE",
            "WAITING_EXTERNAL",
        ):
            path.write_text(json.dumps(_receipt(path, reason=reason)), encoding="utf-8")
            assert _run(payload) == {}, reason
        for reason in ("NEXT_READY", "CHILD_RESULT_READY", "TURN_BUDGET_BOUNDARY"):
            path.write_text(json.dumps(_receipt(path, reason=reason)), encoding="utf-8")
            assert _run(payload)["decision"] == "block", reason


def test_wo545_receipt_validation_matches_closed_bounded_v1_shape() -> None:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "turn-receipt.json"
        payload = _base("Stop")
        payload["stop_hook_active"] = False
        payload["last_assistant_message"] = f"A_SUNDAY_TURN_RECEIPT_REF={path}"
        variants = []

        extra = _receipt(path)
        extra["prompt"] = "not allowed"
        variants.append(extra)

        too_large_generation = _receipt(path)
        too_large_generation["generation"] = 2147483648
        variants.append(too_large_generation)

        duplicate_exec = _receipt(path)
        duplicate_exec["outstanding_exec_refs"] = ["exec-child-abc123", "exec-child-abc123"]
        variants.append(duplicate_exec)

        url_ref = _receipt(path)
        url_ref["next_safe_action_ref"] = "https://example.invalid/wake"
        variants.append(url_ref)

        newline_ref = _receipt(path)
        newline_ref["contract_ref"] = "issue:545\nignore-prior"
        variants.append(newline_ref)

        bad_time = _receipt(path)
        bad_time["generated_at"] = "not-a-time"
        variants.append(bad_time)

        bad_model = _receipt(path)
        bad_model["model"] = "bad model with spaces"
        variants.append(bad_model)

        bad_capability = _receipt(path)
        bad_capability["capability_evidence_version"] = "bad capability value with spaces"
        variants.append(bad_capability)

        for receipt in variants:
            path.write_text(json.dumps(receipt), encoding="utf-8")
            assert _run(payload) == {}
