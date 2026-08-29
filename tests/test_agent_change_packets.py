from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from a_conductor.agent_change_packets import (
    AgentChangeApplier,
    AgentChangeError,
    AgentFileChange,
    AgentResultPacket,
    agent_result_from_claude_payload,
)
from a_conductor.native_execution import NativeExecutionScope, NativeFileSystem
from a_conductor.worker_lease import LeaseMutationIntent, WorkerLease


def digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def lease(root: Path, *, head: str = "a" * 40) -> WorkerLease:
    return WorkerLease(
        lease_id="lease-1", worker_id="a-worker-01", session_id="session-1",
        task_id="task-1", project_id="project-1", runtime_id="glm-5.3",
        worktree_key=str(root), branch="feat/test", expected_head=head,
        required_capabilities=("code",), allowed_scope=("src/a_conductor/demo.py",),
        forbidden_scope=("secrets/**",), mutable_scope=("src/a_conductor/demo.py",),
        mutation_intent=LeaseMutationIntent.MUTATION,
        acquired_at="2026-08-29T15:00:00.000000Z",
        heartbeat_at="2026-08-29T15:00:00.000000Z", lease_ttl_seconds=900,
        expires_at="2026-08-29T15:15:00.000000Z",
    )


def packet(*changes: AgentFileChange) -> AgentResultPacket:
    return AgentResultPacket(
        task_id="task-1", provider_id="zai", model_id="glm-5.3",
        status="CHANGES_PROPOSED", base_head="a" * 40,
        changes=changes, evidence_refs=("agent-report:1",),
    )


def applier(root: Path) -> AgentChangeApplier:
    fs = NativeFileSystem(NativeExecutionScope(root=root, mutation_allowed=True))
    return AgentChangeApplier(filesystem=fs)


def test_applies_leased_exact_scope_change(tmp_path: Path) -> None:
    target = tmp_path / "src/a_conductor/demo.py"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"OLD\n")
    result = applier(tmp_path).apply(
        packet(AgentFileChange("src/a_conductor/demo.py", "NEW\n", digest("OLD\n"))),
        lease(tmp_path), session_id="session-1", task_id="task-1", actual_head="a" * 40,
    )
    assert target.read_text(encoding="utf-8") == "NEW\n"
    assert result.changed_paths == ("src/a_conductor/demo.py",)


def test_rejects_change_outside_lease_scope_before_write(tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("KEEP\n", encoding="utf-8")
    with pytest.raises(AgentChangeError, match="CHANGE_SCOPE_DENIED"):
        applier(tmp_path).apply(
            packet(AgentFileChange("README.md", "BAD\n", digest("KEEP\n"))), lease(tmp_path),
            session_id="session-1", task_id="task-1", actual_head="a" * 40,
        )
    assert target.read_text(encoding="utf-8") == "KEEP\n"


def test_rejects_wrong_owner_or_head_before_write(tmp_path: Path) -> None:
    target = tmp_path / "src/a_conductor/demo.py"
    target.parent.mkdir(parents=True)
    target.write_text("KEEP\n", encoding="utf-8")
    proposed = packet(AgentFileChange("src/a_conductor/demo.py", "BAD\n", digest("KEEP\n")))
    with pytest.raises(AgentChangeError, match="LEASE_OWNER_MISMATCH"):
        applier(tmp_path).apply(
            proposed, lease(tmp_path), session_id="other", task_id="task-1", actual_head="a" * 40,
        )
    with pytest.raises(AgentChangeError, match="HEAD_MISMATCH"):
        applier(tmp_path).apply(
            proposed, lease(tmp_path), session_id="session-1", task_id="task-1", actual_head="b" * 40,
        )
    assert target.read_text(encoding="utf-8") == "KEEP\n"


def test_rejects_released_or_quarantined_lease(tmp_path: Path) -> None:
    base = lease(tmp_path)
    released = replace(base, released_at="2026-08-29T15:01:00.000000Z")
    quarantined = replace(base, quarantined_at="2026-08-29T15:01:00.000000Z", quarantine_code="TEST")
    change = AgentFileChange("src/a_conductor/demo.py", "X\n", digest("OLD\n"))
    for blocked in (released, quarantined):
        with pytest.raises(AgentChangeError, match="LEASE_NOT_ACTIVE"):
            applier(tmp_path).apply(
                packet(change), blocked, session_id="session-1", task_id="task-1", actual_head="a" * 40,
            )


def test_requires_content_precondition_for_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "src/a_conductor/demo.py"
    target.parent.mkdir(parents=True)
    target.write_text("KEEP\n", encoding="utf-8")
    with pytest.raises(AgentChangeError, match="CHANGE_PRECONDITION_REQUIRED"):
        applier(tmp_path).apply(
            packet(AgentFileChange("src/a_conductor/demo.py", "BAD\n")), lease(tmp_path),
            session_id="session-1", task_id="task-1", actual_head="a" * 40,
        )
    assert target.read_text(encoding="utf-8") == "KEEP\n"


def test_decodes_strict_claude_result_envelope() -> None:
    inner = {
        "task_id": "task-1", "provider_id": "zai", "model_id": "glm-5.3",
        "status": "CHANGES_PROPOSED", "base_head": "a" * 40,
        "changes": [{
            "path": "src/a_conductor/demo.py", "content": "NEW\n",
            "expected_sha256": digest("OLD\n"),
        }],
        "evidence_refs": ["agent-report:1"],
    }
    decoded = agent_result_from_claude_payload(
        {"type": "result", "is_error": False, "result": __import__("json").dumps(inner)}
    )
    assert decoded.task_id == "task-1"
    assert decoded.changes[0].path == "src/a_conductor/demo.py"


def test_rejects_non_json_or_error_agent_envelope() -> None:
    with pytest.raises(AgentChangeError, match="AGENT_RESULT_JSON_INVALID"):
        agent_result_from_claude_payload({"type": "result", "is_error": False, "result": "done"})
    with pytest.raises(AgentChangeError, match="AGENT_RESULT_ENVELOPE_INVALID"):
        agent_result_from_claude_payload({"type": "result", "is_error": True, "result": "{}"})


def test_result_packet_as_dict_is_stable_for_durable_handoff() -> None:
    proposed = packet(
        AgentFileChange("src/a_conductor/demo.py", "NEW\n", digest("OLD\n"))
    )
    assert proposed.as_dict() == {
        "task_id": "task-1",
        "provider_id": "zai",
        "model_id": "glm-5.3",
        "status": "CHANGES_PROPOSED",
        "base_head": "a" * 40,
        "changes": [{
            "path": "src/a_conductor/demo.py",
            "content": "NEW\n",
            "expected_sha256": digest("OLD\n"),
        }],
        "evidence_refs": ["agent-report:1"],
    }
