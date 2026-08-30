import json

import pytest

from a_conductor.agent_change_packets import AgentProposalDecoder, AgentChangeError
from a_conductor.claude_code_harness import ClaudeCodeHarnessResult, HarnessExecutionStatus


def harness(payload: dict, status=HarnessExecutionStatus.SUCCESS):
    return ClaudeCodeHarnessResult(status=status, payload=payload, stderr="", exit_code=0)


def proposal() -> dict:
    return {
        "task_id": "task-1", "provider_id": "zai", "model_id": "glm-5.3",
        "status": "CHANGES_PROPOSED", "base_head": "a" * 40,
        "changes": [{"path": "src/a.py", "content": "NEW\n"}],
        "evidence_refs": ["agent-report:1"],
    }


def test_decodes_result_json_string() -> None:
    packet = AgentProposalDecoder().decode(harness({"result": json.dumps(proposal())}))
    assert packet.task_id == "task-1"
    assert packet.changes[0].path == "src/a.py"


def test_decodes_structured_output_when_present() -> None:
    packet = AgentProposalDecoder().decode(harness({"structured_output": proposal()}))
    assert packet.provider_id == "zai"

def test_rejects_failed_harness_invalid_json_and_mismatched_identity() -> None:
    decoder = AgentProposalDecoder()
    with pytest.raises(AgentChangeError, match="AGENT_EXECUTION_NOT_SUCCESSFUL"):
        decoder.decode(harness({}, HarnessExecutionStatus.FAILED))
    with pytest.raises(AgentChangeError, match="AGENT_RESULT_INVALID"):
        decoder.decode(harness({"result": "not-json"}))
    bad = proposal(); bad["task_id"] = "other"
    with pytest.raises(AgentChangeError, match="TASK_MISMATCH"):
        decoder.decode(
            harness({"result": json.dumps(bad)}), expected_task_id="task-1",
            expected_provider_id="zai", expected_model_id="glm-5.3",
        )


def test_expected_identity_is_checked_at_decode_boundary() -> None:
    decoder = AgentProposalDecoder()
    for field, value, code in (
        ("provider_id", "other", "PROVIDER_MISMATCH"),
        ("model_id", "other", "MODEL_MISMATCH"),
    ):
        data = proposal(); data[field] = value
        with pytest.raises(AgentChangeError, match=code):
            decoder.decode(
                harness({"structured_output": data}), expected_task_id="task-1",
                expected_provider_id="zai", expected_model_id="glm-5.3",
            )
