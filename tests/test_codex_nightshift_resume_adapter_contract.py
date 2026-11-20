"""WO-P1-531 deterministic contract tests for the Codex NightShift resume adapter."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "contracts" / "codex-nightshift-resume-adapter-v1.md"
SCHEMA_PATH = ROOT / "docs" / "contracts" / "codex-nightshift-resume-adapter-v1.schema.json"


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _valid(status: str = "CONTINUE") -> dict:
    reason = "NEXT_READY" if status == "CONTINUE" else "GOAL_COMPLETE"
    gate = "NONE"
    return {
        "schema_version": "1.0.0",
        "receipt_type": "NIGHTSHIFT_TURN_RECEIPT",
        "run_id": "nightshift-test-001",
        "thread_id": "01234567-89ab-cdef-0123-456789abcdef",
        "parent_exec_ref": "exec-parent-abc123",
        "model": "gpt-6-luna",
        "effort": "medium",
        "contract_ref": "/tmp/a-nightshift/run/supervisor-contract.md",
        "receipt_ref": "/tmp/a-nightshift/run/turn-receipt.json",
        "authority_repo_ref": "/Users/example/GitHub/A-Wiki-Conductor",
        "worktree_ref": "/Users/example/GitHub/_worktrees/A-Wiki-Conductor-task",
        "capability_evidence_version": "codex-0.116.0-resume-probe-v1",
        "generation": 3,
        "generated_at": "2026-09-24T08:00:00Z",
        "status": status,
        "reason": reason,
        "stop_gate": gate,
        "outstanding_exec_refs": ["exec-child-abc123"],
        "next_safe_action_ref": "issue:529#checkpoint-next-safe-action",
    }


def _errors(payload: dict) -> list:
    return list(Draft202012Validator(_schema()).iter_errors(payload))


def _resume_decision(
    payload: dict,
    *,
    expected_generation: int,
    parent_live: bool,
    capability_verified: bool,
    delivery_ambiguous: bool = False,
) -> str:
    if _errors(payload):
        return "RECEIPT_INVALID"
    if payload["status"] == "TERMINAL":
        return "TERMINAL_NO_RESUME"
    if payload["stop_gate"] != "NONE":
        return "FROZEN_GATE_NO_RESUME"
    if not capability_verified:
        return "CAPABILITY_UNVERIFIED"
    if payload["generation"] != expected_generation:
        return "STALE_WAKE_GENERATION"
    if parent_live:
        return "LIVE_PARENT_OWNS_THREAD"
    if delivery_ambiguous:
        return "WAKE_DELIVERY_UNKNOWN"
    return "RESUME_SAME_THREAD"


def test_schema_is_closed_draft_202012_and_valid_examples_pass() -> None:
    schema = _schema()
    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False
    assert not _errors(_valid("CONTINUE"))
    assert not _errors(_valid("TERMINAL"))


@pytest.mark.parametrize(
    "field",
    (
        "prompt",
        "messages",
        "token",
        "api_key",
        "secret",
        "password",
        "cookie",
        "session_token",
        "share_url",
        "argv",
        "command_line",
        "shell_command",
        "git_operation",
        "pid",
    ),
)
def test_sensitive_or_executable_fields_are_structurally_rejected(field: str) -> None:
    payload = _valid()
    payload[field] = "forbidden"
    assert _errors(payload)


@pytest.mark.parametrize("field", ("contract_ref", "receipt_ref", "authority_repo_ref", "worktree_ref", "next_safe_action_ref"))
def test_refs_reject_url_schemes(field: str) -> None:
    payload = _valid()
    payload[field] = "https://example.invalid/not-allowed"
    assert _errors(payload)


def test_resume_only_for_nonterminal_exact_generation_without_live_owner() -> None:
    payload = _valid()
    assert _resume_decision(
        payload,
        expected_generation=3,
        parent_live=False,
        capability_verified=True,
    ) == "RESUME_SAME_THREAD"
    assert _resume_decision(
        payload,
        expected_generation=2,
        parent_live=False,
        capability_verified=True,
    ) == "STALE_WAKE_GENERATION"
    assert _resume_decision(
        payload,
        expected_generation=3,
        parent_live=True,
        capability_verified=True,
    ) == "LIVE_PARENT_OWNS_THREAD"


def test_terminal_and_frozen_gate_never_resume() -> None:
    terminal = _valid("TERMINAL")
    assert _resume_decision(
        terminal,
        expected_generation=3,
        parent_live=False,
        capability_verified=True,
    ) == "TERMINAL_NO_RESUME"

    frozen = _valid()
    frozen["stop_gate"] = "HUMAN_DECISION_REQUIRED"
    assert _resume_decision(
        frozen,
        expected_generation=3,
        parent_live=False,
        capability_verified=True,
    ) == "FROZEN_GATE_NO_RESUME"


def test_unverified_capability_and_ambiguous_delivery_fail_closed() -> None:
    payload = _valid()
    assert _resume_decision(
        payload,
        expected_generation=3,
        parent_live=False,
        capability_verified=False,
    ) == "CAPABILITY_UNVERIFIED"
    assert _resume_decision(
        payload,
        expected_generation=3,
        parent_live=False,
        capability_verified=True,
        delivery_ambiguous=True,
    ) == "WAKE_DELIVERY_UNKNOWN"


def test_contract_pins_live_proven_exec_resume_shape_and_no_shadow_authority() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "exec resume --json --ignore-user-config" in text
    assert "RESUME_SEED_OK" in text
    assert "RESUME_CONTINUE_OK" in text
    assert "does not accept -s or -C" in text
    assert "SAME persisted Codex thread" in text
    assert "Issue #215 remains NEXT_READY continuation authority" in text
    for phrase in (
        "scheduler or roadmap owner",
        "task database",
        "claim or lease system",
        "retry authority",
        "review or merge authority",
        "completion authority",
    ):
        assert phrase in text


def test_wake_payload_is_pointer_only_and_queue_is_not_resume_substitute() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "pointer-only and bounded" in text
    assert "MUST NOT reconstruct or embed roadmap state" in text
    assert "codex queue MUST NOT be used as a resume substitute" in text


def test_generation_is_fenced_and_duplicate_wake_forbidden() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "expected_generation != receipt.generation" in text
    assert "STALE_WAKE_GENERATION" in text
    assert "Duplicate wake of the same generation is forbidden" in text
    assert "MUST NOT be blindly retried" in text


def test_receipt_missing_required_identity_fails_schema() -> None:
    for field in ("run_id", "thread_id", "parent_exec_ref", "contract_ref", "receipt_ref", "generation"):
        payload = _valid()
        payload.pop(field)
        assert _errors(payload), field
