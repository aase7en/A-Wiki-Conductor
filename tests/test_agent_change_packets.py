from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from a_conductor.agent_change_packets import (
    AgentChangeApplier,
    AgentChangeError,
    AgentFileChange,
    AgentResultPacket,
    AgentResultFileReader,
    AgentRepairRequest,
    agent_result_from_claude_payload,
    build_human_bridge_prompt,
    build_repair_task_markdown,
)
from a_conductor.native_execution import NativeExecutionScope, NativeFileSystem
from a_conductor.worker_lease import LeaseHealth, LeaseHealthKind, LeaseMutationIntent, WorkerLease


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


class StaticLeaseStore:
    def __init__(self, value: WorkerLease) -> None:
        self.value = value

    def inspect_health(self, lease_id: str, *, now: object) -> LeaseHealth:
        assert lease_id == self.value.lease_id
        kind = LeaseHealthKind.ACTIVE
        if self.value.released_at is not None:
            kind = LeaseHealthKind.RELEASED
        elif self.value.quarantined_at is not None:
            kind = LeaseHealthKind.QUARANTINED
        return LeaseHealth(kind, self.value)


def applier(root: Path, value: WorkerLease) -> AgentChangeApplier:
    fs = NativeFileSystem(NativeExecutionScope(root=root, mutation_allowed=True))
    return AgentChangeApplier(filesystem=fs, lease_store=StaticLeaseStore(value), clock=lambda: "2026-08-29T15:05:00.000000Z")


def test_applies_leased_exact_scope_change(tmp_path: Path) -> None:
    target = tmp_path / "src/a_conductor/demo.py"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"OLD\n")
    result = applier(tmp_path, lease(tmp_path)).apply(
        packet(AgentFileChange("src/a_conductor/demo.py", "NEW\n", digest("OLD\n"))),
        "lease-1", session_id="session-1", task_id="task-1", actual_head="a" * 40,
    )
    assert target.read_text(encoding="utf-8") == "NEW\n"
    assert result.changed_paths == ("src/a_conductor/demo.py",)


def test_rejects_change_outside_lease_scope_before_write(tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("KEEP\n", encoding="utf-8")
    with pytest.raises(AgentChangeError, match="CHANGE_SCOPE_DENIED"):
        applier(tmp_path, lease(tmp_path)).apply(
            packet(AgentFileChange("README.md", "BAD\n", digest("KEEP\n"))), "lease-1",
            session_id="session-1", task_id="task-1", actual_head="a" * 40,
        )
    assert target.read_text(encoding="utf-8") == "KEEP\n"


def test_rejects_wrong_owner_or_head_before_write(tmp_path: Path) -> None:
    target = tmp_path / "src/a_conductor/demo.py"
    target.parent.mkdir(parents=True)
    target.write_text("KEEP\n", encoding="utf-8")
    proposed = packet(AgentFileChange("src/a_conductor/demo.py", "BAD\n", digest("KEEP\n")))
    with pytest.raises(AgentChangeError, match="LEASE_OWNER_MISMATCH"):
        applier(tmp_path, lease(tmp_path)).apply(
            proposed, "lease-1", session_id="other", task_id="task-1", actual_head="a" * 40,
        )
    with pytest.raises(AgentChangeError, match="HEAD_MISMATCH"):
        applier(tmp_path, lease(tmp_path)).apply(
            proposed, "lease-1", session_id="session-1", task_id="task-1", actual_head="b" * 40,
        )
    assert target.read_text(encoding="utf-8") == "KEEP\n"


def test_rejects_released_or_quarantined_lease(tmp_path: Path) -> None:
    base = lease(tmp_path)
    released = replace(base, released_at="2026-08-29T15:01:00.000000Z")
    quarantined = replace(base, quarantined_at="2026-08-29T15:01:00.000000Z", quarantine_code="TEST")
    change = AgentFileChange("src/a_conductor/demo.py", "X\n", digest("OLD\n"))
    for blocked in (released, quarantined):
        with pytest.raises(AgentChangeError, match="LEASE_NOT_ACTIVE"):
            applier(tmp_path, blocked).apply(
                packet(change), blocked.lease_id, session_id="session-1", task_id="task-1", actual_head="a" * 40,
            )


def test_requires_content_precondition_for_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "src/a_conductor/demo.py"
    target.parent.mkdir(parents=True)
    target.write_text("KEEP\n", encoding="utf-8")
    with pytest.raises(AgentChangeError, match="CHANGE_PRECONDITION_REQUIRED"):
        applier(tmp_path, lease(tmp_path)).apply(
            packet(AgentFileChange("src/a_conductor/demo.py", "BAD\n")), "lease-1",
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


def test_rejects_multi_file_packet_until_parallel_lane_phase() -> None:
    with pytest.raises(ValueError, match="one file change per task"):
        packet(
            AgentFileChange("src/a_conductor/demo.py", "A\n"),
            AgentFileChange("src/a_conductor/other.py", "B\n"),
        )


def test_human_bridge_prompt_points_to_durable_files_only() -> None:
    prompt = build_human_bridge_prompt(
        "runs/task-1.md", "runs/result-1.json"
    )
    assert "runs/task-1.md" in prompt
    assert "runs/result-1.json" in prompt
    assert "Do not return the result to the human" in prompt
    assert len(prompt) < 260


def test_result_file_reader_rehydrates_and_checks_identity(tmp_path: Path) -> None:
    payload = packet(
        AgentFileChange("src/a_conductor/demo.py", "NEW\n", digest("OLD\n"))
    )
    result_path = tmp_path / "runs/result-1.json"
    result_path.parent.mkdir(parents=True)
    import json
    result_path.write_text(json.dumps(payload.as_dict()), encoding="utf-8")
    reader = AgentResultFileReader(
        filesystem=NativeFileSystem(NativeExecutionScope(root=tmp_path))
    )
    restored = reader.read(
        "runs/result-1.json", expected_task_id="task-1",
        expected_provider_id="zai", expected_model_id="glm-5.3",
    )
    assert restored == payload
    with pytest.raises(AgentChangeError, match="PROVIDER_MISMATCH"):
        reader.read(
            "runs/result-1.json", expected_task_id="task-1",
            expected_provider_id="other", expected_model_id="glm-5.3",
        )


def test_repair_task_is_durable_and_bounded() -> None:
    request = AgentRepairRequest(
        task_id="task-1-repair-1", provider_id="zai", model_id="glm-5.3",
        base_head="a" * 40, source_result_ref="runs/result-1.json",
        result_destination_ref="runs/result-1-repair.json",
        review_findings=("as_dict omits expected_sha256",),
    )
    text = build_repair_task_markdown(request)
    assert "runs/result-1.json" in text
    assert "runs/result-1-repair.json" in text
    assert "as_dict omits expected_sha256" in text
    assert "Do not broaden scope" in text


def test_repair_task_requires_review_evidence() -> None:
    with pytest.raises(ValueError, match="review_findings"):
        AgentRepairRequest(
            task_id="repair", provider_id="zai", model_id="glm-5.3",
            base_head="a" * 40, source_result_ref="runs/result.json",
            result_destination_ref="runs/repair.json", review_findings=(),
        )


def test_file_bridge_supports_one_review_repair_round(tmp_path: Path) -> None:
    import json
    target = tmp_path / "src/a_conductor/demo.py"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"OLD\n")
    results = tmp_path / "runs"
    results.mkdir()
    first = packet(AgentFileChange(target.relative_to(tmp_path).as_posix(), "BAD\n", digest("OLD\n")))
    (results / "result.json").write_text(json.dumps(first.as_dict()), encoding="utf-8")
    reader = AgentResultFileReader(filesystem=NativeFileSystem(NativeExecutionScope(root=tmp_path)))
    parsed = reader.read("runs/result.json", expected_task_id="task-1", expected_provider_id="zai", expected_model_id="glm-5.3")
    applier(tmp_path, lease(tmp_path)).apply(parsed, "lease-1", session_id="session-1", task_id="task-1", actual_head="a" * 40)
    assert target.read_text(encoding="utf-8") == "BAD\n"

    repair = AgentRepairRequest(
        task_id="task-1", provider_id="zai", model_id="glm-5.3", base_head="a" * 40,
        source_result_ref="runs/result.json", result_destination_ref="runs/repair.json",
        review_findings=("expected GOOD output",),
    )
    assert "expected GOOD output" in build_repair_task_markdown(repair)
    repaired = packet(AgentFileChange(
        target.relative_to(tmp_path).as_posix(), "GOOD\n", digest("BAD\n")
    ))
    (results / "repair.json").write_text(json.dumps(repaired.as_dict()), encoding="utf-8")
    parsed_repair = reader.read(
        "runs/repair.json", expected_task_id="task-1",
        expected_provider_id="zai", expected_model_id="glm-5.3",
    )
    applier(tmp_path, lease(tmp_path)).apply(
        parsed_repair, "lease-1", session_id="session-1",
        task_id="task-1", actual_head="a" * 40,
    )
    assert target.read_text(encoding="utf-8") == "GOOD\n"


def test_rejects_lease_for_different_worktree(tmp_path: Path) -> None:
    target = tmp_path / "src/a_conductor/demo.py"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"OLD\n")
    wrong_root = tmp_path / "other"
    wrong_root.mkdir()
    wrong = replace(lease(wrong_root), worktree_key=str(wrong_root))
    with pytest.raises(AgentChangeError, match="WORKTREE_MISMATCH"):
        applier(tmp_path, wrong).apply(
            packet(AgentFileChange("src/a_conductor/demo.py", "NEW\n", digest("OLD\n"))),
            wrong.lease_id, session_id="session-1", task_id="task-1", actual_head="a" * 40,
        )
    assert target.read_text(encoding="utf-8") == "OLD\n"
