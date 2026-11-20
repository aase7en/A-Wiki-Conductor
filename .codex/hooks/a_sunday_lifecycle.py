#!/usr/bin/env python3
"""Thin Codex lifecycle adapter for A-Faster + A-NightShift.

The hook is intentionally stateless. It injects policy context and consumes an
accepted NightShift turn receipt; it owns no scheduler, claim, quota, or task state.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional

_MAX_STDIN_BYTES = 262_144
_MAX_RECEIPT_BYTES = 65_536
_RECEIPT_MARKER = re.compile(r"(?m)^A_SUNDAY_TURN_RECEIPT_REF=(.+?)\s*$")
_KILO_RUN = re.compile(
    r"""(?ix)(?:^|[\s;&|])(?:
        "(?:[^"\r\n]*[\\/])?kilo(?:\.(?:exe|cmd|bat))?"
        |'(?:[^'\r\n]*[\\/])?kilo(?:\.(?:exe|cmd|bat))?'
        |(?:[A-Za-z]:)?(?:[^\s"';&|]+[\\/])+kilo(?:\.(?:exe|cmd|bat))?
        |kilo(?:\.(?:exe|cmd|bat))?
    )\s+run\b"""
)

_BASE_CONTEXT = """A-SUNDAY CODEX SUPERVISOR CONTRACT:
Actual durable evidence wins over chat/session memory. Before material work run
RECOVER -> RECONCILE -> HARVEST, then A-FastTask -> A-Faster -> A-NightShift.
Recover outstanding delegated executions before any redispatch. GLM-5.3 MAX is
preferred eligible R2/R3 heavy labor; GLM-5.3-Flash is bounded read-only assist.
Use JEV only in its currently accepted mode as a System-One fast advisory for
condition checks, scoring, route suggestions, and guardrail confidence; JEV never
grants mutation/review/merge/completion authority. Before fanout, discover the
actual Windows SunDay-Worker 1..5 and SundayMCP Mac surfaces; ONLINE is capacity
evidence, never extra task or WIP authority. Enforce no manufactured work and no
quota burning. A GLM 5-hour throttle blocks only that provider route when an
authorized Codex fallback exists. The Codex/Luna supervisor remains low-cost
routing/decomposition/harvest traffic control, not the default heavy engineer.
Preserve global WIP, one-hotspot-one-owner, claims, exact worktree/HEAD, and real
stop gates. Do not infer quota/readiness/model authority from prose."""

_DISPATCH_CONTEXT = """Before Sunday dispatch: prove current task authority and
claim/worktree/branch/HEAD/scope, run the normal collision/WIP gate, and require
fresh structured GLM admission before material GLM work. For Kilo, use explicit
--dir plus per-run share=disabled/--no-share. Never infer quota from command text.
This hook is not the #498 mutation guard and grants no mutation authority."""

_POST_EXEC_CONTEXT = """After delegated execution activity: RECOVER -> RECONCILE -> HARVEST
terminal-unharvested evidence before refill. RUNNING/UNKNOWN executions
never authorize duplicate replay. Consume accepted A-Faster FANOUT_TARGET and
AUTO_REFILL_REQUIRED markers; do not recompute a second utilization authority."""

_ACTIONABLE_CONTINUE_REASONS = {"NEXT_READY", "CHILD_RESULT_READY", "TURN_BUDGET_BOUNDARY"}
_RECEIPT_REASONS = {
    "NEXT_READY",
    "WAITING_EXTERNAL",
    "CHILD_RESULT_READY",
    "TURN_BUDGET_BOUNDARY",
    "QUOTA_EXHAUSTED",
    "HUMAN_ACTION_REQUIRED",
    "HUMAN_DECISION_REQUIRED",
    "AUTHORIZATION_REQUIRED",
    "SAFETY_BLOCK",
    "TRUE_NO_SAFE_NEXT_ACTION",
    "GOAL_COMPLETE",
}
_STOP_GATES = {
    "NONE",
    "HUMAN_ACTION_REQUIRED",
    "HUMAN_DECISION_REQUIRED",
    "AUTHORIZATION_REQUIRED",
    "SAFETY_BLOCK",
    "TRUE_NO_SAFE_NEXT_ACTION",
}
_RUN_ID = re.compile(r"^nightshift-[A-Za-z0-9._-]{1,120}$")
_THREAD_ID = re.compile(r"^[0-9a-fA-F-]{36}$")
_EXEC_REF = re.compile(r"^exec-[a-z0-9-]{6,64}$")
_MODEL = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_CAPABILITY = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
_GENERATED_AT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z$")
_URL_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
_MAX_GENERATION = 2_147_483_647
_REQUIRED_RECEIPT_FIELDS = {
    "schema_version",
    "receipt_type",
    "run_id",
    "thread_id",
    "parent_exec_ref",
    "model",
    "effort",
    "contract_ref",
    "receipt_ref",
    "authority_repo_ref",
    "worktree_ref",
    "capability_evidence_version",
    "generation",
    "generated_at",
    "status",
    "reason",
    "stop_gate",
    "outstanding_exec_refs",
    "next_safe_action_ref",
}


def _emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def _read_event() -> dict[str, Any]:
    raw = sys.stdin.buffer.read(_MAX_STDIN_BYTES + 1)
    if len(raw) > _MAX_STDIN_BYTES:
        return {}
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _context_output(event: str, context: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": context,
        }
    }


def _is_sunday_execution_tool(name: object) -> bool:
    if not isinstance(name, str):
        return False
    return any(
        token in name
        for token in (
            "sunday_dispatch",
            "sunday_recover",
            "sunday_status",
            "sunday_output",
            "sunday_harvest",
            "sunday_collect",
        )
    )


def _pre_tool(event: dict[str, Any]) -> dict[str, Any]:
    tool_name = event.get("tool_name")
    tool_input = event.get("tool_input")
    if tool_name == "Bash" and isinstance(tool_input, dict):
        command = tool_input.get("command")
        if isinstance(command, str) and _KILO_RUN.search(command):
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "Direct Kilo run bypasses A-Sunday durable transport. "
                        "Use sunday_dispatch with fresh admission and exact binding."
                    ),
                }
            }
    if _is_sunday_execution_tool(tool_name):
        return _context_output("PreToolUse", _DISPATCH_CONTEXT)
    return {}


def _receipt_pointer(message: object) -> Optional[Path]:
    if not isinstance(message, str) or len(message) > 100_000:
        return None
    matches = list(_RECEIPT_MARKER.finditer(message))
    if len(matches) != 1:
        return None
    raw = matches[0].group(1).strip()
    if not raw or "\x00" in raw:
        return None
    path = Path(raw).expanduser()
    return path if path.is_absolute() else None


def _valid_ref(value: object) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= 1024
        and "\r" not in value
        and "\n" not in value
        and _URL_SCHEME.match(value) is None
    )


def _load_receipt(path: Path) -> Optional[dict[str, Any]]:
    try:
        resolved = path.resolve(strict=True)
        temp_root = Path(tempfile.gettempdir()).resolve(strict=True)
        resolved.relative_to(temp_root)
        if not resolved.is_file() or resolved.stat().st_size > _MAX_RECEIPT_BYTES:
            return None
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, RuntimeError, ValueError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or set(value) != _REQUIRED_RECEIPT_FIELDS:
        return None
    if value.get("schema_version") != "1.0.0":
        return None
    if value.get("receipt_type") != "NIGHTSHIFT_TURN_RECEIPT":
        return None
    status = value.get("status")
    effort = value.get("effort")
    reason = value.get("reason")
    stop_gate = value.get("stop_gate")
    if not isinstance(status, str) or status not in {"CONTINUE", "TERMINAL"}:
        return None
    if not isinstance(effort, str) or effort not in {"low", "medium", "high"}:
        return None
    if not isinstance(reason, str) or reason not in _RECEIPT_REASONS:
        return None
    if not isinstance(stop_gate, str) or stop_gate not in _STOP_GATES:
        return None
    run_id = value.get("run_id")
    thread_id = value.get("thread_id")
    parent_exec_ref = value.get("parent_exec_ref")
    model = value.get("model")
    capability = value.get("capability_evidence_version")
    generated_at = value.get("generated_at")
    if (
        not isinstance(run_id, str)
        or len(run_id) > 128
        or _RUN_ID.fullmatch(run_id) is None
    ):
        return None
    if resolved.name != "turn-receipt.json" or resolved.parent.name != run_id:
        return None
    if not isinstance(thread_id, str) or _THREAD_ID.fullmatch(thread_id) is None:
        return None
    if not isinstance(parent_exec_ref, str) or _EXEC_REF.fullmatch(parent_exec_ref) is None:
        return None
    if not isinstance(model, str) or _MODEL.fullmatch(model) is None:
        return None
    if not isinstance(capability, str) or _CAPABILITY.fullmatch(capability) is None:
        return None
    if not isinstance(generated_at, str) or _GENERATED_AT.fullmatch(generated_at) is None:
        return None
    generation = value.get("generation")
    if (
        isinstance(generation, bool)
        or not isinstance(generation, int)
        or not 1 <= generation <= _MAX_GENERATION
    ):
        return None
    outstanding = value.get("outstanding_exec_refs")
    if not isinstance(outstanding, list) or len(outstanding) > 16:
        return None
    if any(not isinstance(ref, str) or _EXEC_REF.fullmatch(ref) is None for ref in outstanding):
        return None
    if len(set(outstanding)) != len(outstanding):
        return None
    for field in (
        "contract_ref",
        "receipt_ref",
        "authority_repo_ref",
        "worktree_ref",
        "next_safe_action_ref",
    ):
        if not _valid_ref(value.get(field)):
            return None
    receipt_ref = value["receipt_ref"]
    try:
        if Path(receipt_ref).expanduser().resolve(strict=False) != resolved:
            return None
    except (OSError, RuntimeError, ValueError):
        return None
    return value


def _stop(event: dict[str, Any]) -> dict[str, Any]:
    if event.get("stop_hook_active") is True:
        return {}
    pointer = _receipt_pointer(event.get("last_assistant_message"))
    if pointer is None:
        return {}
    receipt = _load_receipt(pointer)
    if receipt is None or receipt.get("status") != "CONTINUE":
        return {}
    if receipt.get("stop_gate") != "NONE":
        return {}
    reason = receipt.get("reason")
    if reason not in _ACTIONABLE_CONTINUE_REASONS:
        return {}
    contract_ref = receipt.get("contract_ref")
    next_ref = receipt.get("next_safe_action_ref")
    if not isinstance(contract_ref, str) or not isinstance(next_ref, str):
        return {}
    return {
        "decision": "block",
        "reason": (
            f"Continue the SAME A-NightShift parent from receipt {pointer} and "
            f"contract {contract_ref}. Start with fresh RECOVER, then follow "
            f"next_safe_action_ref={next_ref}. Do not duplicate live executions."
        ),
    }


def main() -> int:
    event = _read_event()
    name = event.get("hook_event_name")
    if name in {"SessionStart", "UserPromptSubmit"}:
        _emit(_context_output(str(name), _BASE_CONTEXT))
    elif name in {"PreCompact", "PostCompact"}:
        _emit({"continue": True})
    elif name == "PreToolUse":
        _emit(_pre_tool(event))
    elif name == "PostToolUse":
        if _is_sunday_execution_tool(event.get("tool_name")):
            _emit(_context_output("PostToolUse", _POST_EXEC_CONTEXT))
        else:
            _emit({})
    elif name == "Interrupt":
        _emit({
            "systemMessage": (
                "A-Sunday parent turn interrupted. Do not infer durable Sunday child "
                "executions were cancelled; recover status/harvest truth before replay."
            )
        })
    elif name == "Stop":
        _emit(_stop(event))
    else:
        _emit({})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
