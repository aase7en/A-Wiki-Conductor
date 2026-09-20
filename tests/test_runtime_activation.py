from __future__ import annotations

from dataclasses import dataclass

import pytest

from a_conductor.elastic_worker_capacity import ElasticCapacityPolicy
from a_conductor.graph.domain import TaskNode, TaskNodeStatus
from a_conductor.graph.graph import TaskGraphBuilder
from a_conductor.graph.scheduler import NodeEligibility, SchedulePolicy
from a_conductor.runtime_activation import (
    RuntimeActivationError,
    RuntimeActivationRequest,
    RuntimeActivationService,
)


@dataclass(frozen=True)
class _Contract:
    node_id: str


class _Executor:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def execute_once(self, graph, ready, contracts_by_node, **kwargs):
        self.calls.append(
            {
                "graph": graph,
                "ready": ready,
                "contracts": contracts_by_node,
                **kwargs,
            }
        )
        return "EXECUTED"


def _graph(*nodes: TaskNode):
    builder = TaskGraphBuilder()
    for node in nodes:
        builder.add_node(node)
    return builder.build()


def _request(node_id: str = "n1") -> RuntimeActivationRequest:
    return RuntimeActivationRequest(
        graph_id="graph-1",
        graph_run_id="run-1",
        node_id=node_id,
        runtime_kind="serena",
        project_root="/repo",
        task_contract_ref="tasks/task.json",
        task_packet_path="/repo/task.md",
        provider_id="provider-1",
        model_id="model-1",
    )


def _service(graph, states, executor: _Executor, built: list[str]):
    return RuntimeActivationService(
        graph_loader=lambda graph_id: graph,
        state_projector=lambda graph, graph_id, graph_run_id: states,
        contract_builder=lambda request, node: (
            built.append(node.id) or _Contract(node.id)
        ),
        executor=executor,
    )


def test_manual_activation_executes_only_exact_ready_node():
    graph = _graph(
        TaskNode("n1", "first"),
        TaskNode("n2", "second"),
    )
    executor = _Executor()
    built: list[str] = []
    service = _service(
        graph,
        {"n1": TaskNodeStatus.TODO, "n2": TaskNodeStatus.TODO},
        executor,
        built,
    )

    result = service.activate(_request("n2"))

    assert result == "EXECUTED"
    assert built == ["n2"]
    assert len(executor.calls) == 1
    call = executor.calls[0]
    assert call["ready"].ready_ids == {"n2"}
    assert set(call["contracts"]) == {"n2"}
    assert call["schedule_policy"] == SchedulePolicy(max_parallel=1)
    assert call["elastic_policy"] == ElasticCapacityPolicy(
        enabled=False,
        max_extra_workers=0,
        permitted_runtime_kinds=(),
    )
    assert call["eligibility"] == {"n2": NodeEligibility()}
    assert call["provider_inflight"] == {}
    assert call["batch_id"].startswith("runtime-act-v1:")


def test_manual_activation_refuses_non_ready_exact_node():
    graph = _graph(TaskNode("n1", "first"))
    executor = _Executor()
    built: list[str] = []
    service = _service(
        graph,
        {"n1": TaskNodeStatus.DOING},
        executor,
        built,
    )

    with pytest.raises(RuntimeActivationError, match="ACTIVATION_NODE_NOT_READY"):
        service.activate(_request())

    assert built == []
    assert executor.calls == []


def test_manual_activation_fails_closed_on_unproven_worker_capability():
    graph = _graph(
        TaskNode(
            "n1",
            "requires capability",
            worker_requirement=("repository-write",),
        )
    )
    executor = _Executor()
    built: list[str] = []
    service = _service(
        graph,
        {"n1": TaskNodeStatus.TODO},
        executor,
        built,
    )

    with pytest.raises(
        RuntimeActivationError,
        match="RUNTIME_CAPABILITY_AUTHORITY_UNAVAILABLE",
    ):
        service.activate(_request())

    assert built == []
    assert executor.calls == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("graph_id", ""),
        ("graph_run_id", "bad" + chr(10) + "run"),
        ("node_id", " "),
        ("runtime_kind", ""),
    ],
)
def test_activation_request_rejects_unsafe_identity_text(field: str, value: str):
    values = {
        "graph_id": "graph-1",
        "graph_run_id": "run-1",
        "node_id": "n1",
        "runtime_kind": "serena",
        "project_root": "/repo",
        "task_contract_ref": "tasks/task.json",
        "task_packet_path": "/repo/task.md",
        "provider_id": "provider-1",
        "model_id": "model-1",
    }
    values[field] = value

    with pytest.raises(ValueError):
        RuntimeActivationRequest(**values)


def _write_activation_authority(
    root, *, approval_required=False, worktree=None, mutation_allowed=False,
    allowed_files=None, dispatch_mode="PROGRAMMATIC_PUSH", worker_id=None,
    worker_ids=("a-worker-01", "a-worker-02"),
):
    import json

    contract_ref = "tasks/task-1.json"
    packet_path = root / "packets" / "task-1.md"
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text("# bounded task\n", encoding="utf-8")
    contract_path = root / contract_ref
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0.0",
        "task_id": "task-activation-1",
        "goal": "bounded activation",
        "risk_class": "HIGH",
        "authority": {
            "requested_by": "test",
            "mutation_allowed": mutation_allowed,
            "human_approval_required": approval_required,
        },
        "target": {
            "project_id": "project-1",
            "expected_worktree_path": str(root if worktree is None else worktree),
            "expected_branch": "feat/task-1",
            "expected_head": "a" * 40,
            "identity_policy": "EXACT",
        },
        "scope": {
            "allowed_files": list(allowed_files or []),
            "forbidden_files": ["secrets/**"],
            "allowed_commands": [],
            "forbidden_commands": [],
        },
        "acceptance": {
            "criteria": ["bounded result"],
            "verify_commands": [],
            "review_required": True,
        },
        "security": {
            "privacy_class": "INTERNAL",
            "network_policy": "DENIED",
            "network_allowlist": [],
            "secret_access": False,
        },
        "budget": {"max_elapsed_seconds": 300},
        "retry_policy": {
            "max_attempts": 2,
            "max_identical_failures": 1,
            "on_lease_expiry": "RECOVERY_REQUIRED",
        },
        "escalation": {"conditions": ["UNKNOWN_RECOVERY_STATE"]},
        "required_evidence": ["TEST_RESULT"],
        "metadata": {
            "dispatch_mode": dispatch_mode,
            **({"worker_id": worker_id} if worker_id is not None else {}),
            **({"worker_ids": list(worker_ids)} if worker_ids is not None else {}),
        },
    }
    contract_path.write_text(json.dumps(payload), encoding="utf-8")
    return contract_ref, packet_path


def test_load_activation_authority_consumes_exact_existing_contract_and_packet(tmp_path):
    import hashlib

    from a_conductor.runtime_activation import load_activation_authority

    contract_ref, packet_path = _write_activation_authority(tmp_path)
    request = RuntimeActivationRequest(
        graph_id="graph-1",
        graph_run_id="run-1",
        node_id="n1",
        runtime_kind="serena",
        project_root=str(tmp_path),
        task_contract_ref=contract_ref,
        task_packet_path=str(packet_path),
        provider_id="provider-1",
        model_id="model-1",
    )

    authority = load_activation_authority(request)

    assert authority.task_id == "task-activation-1"
    assert authority.project_id == "project-1"
    assert authority.worktree == str(tmp_path.resolve())
    assert authority.branch == "feat/task-1"
    assert authority.head == "a" * 40
    assert authority.max_attempts == 2
    assert authority.timeout_seconds == 300
    assert authority.dispatch_mode == "PROGRAMMATIC_PUSH"
    assert authority.task_packet.sha256 == hashlib.sha256(
        packet_path.read_bytes()
    ).hexdigest()


def test_load_activation_authority_refuses_worktree_identity_mismatch(tmp_path):
    from a_conductor.runtime_activation import (
        RuntimeActivationError,
        load_activation_authority,
    )

    other = tmp_path / "other"
    other.mkdir()
    contract_ref, packet_path = _write_activation_authority(
        tmp_path,
        worktree=other,
    )
    request = RuntimeActivationRequest(
        graph_id="graph-1",
        graph_run_id="run-1",
        node_id="n1",
        runtime_kind="serena",
        project_root=str(tmp_path),
        task_contract_ref=contract_ref,
        task_packet_path=str(packet_path),
        provider_id="provider-1",
        model_id="model-1",
    )

    with pytest.raises(
        RuntimeActivationError,
        match="ACTIVATION_WORKTREE_IDENTITY_MISMATCH",
    ):
        load_activation_authority(request)


def test_load_activation_authority_refuses_pending_human_approval(tmp_path):
    from a_conductor.runtime_activation import (
        RuntimeActivationError,
        load_activation_authority,
    )

    contract_ref, packet_path = _write_activation_authority(
        tmp_path,
        approval_required=True,
    )
    request = RuntimeActivationRequest(
        graph_id="graph-1",
        graph_run_id="run-1",
        node_id="n1",
        runtime_kind="serena",
        project_root=str(tmp_path),
        task_contract_ref=contract_ref,
        task_packet_path=str(packet_path),
        provider_id="provider-1",
        model_id="model-1",
    )

    with pytest.raises(RuntimeActivationError, match="HUMAN_APPROVAL_REQUIRED"):
        load_activation_authority(request)


def _provider_snapshot():
    from datetime import datetime, timezone

    from a_conductor.provider_config_store import ProviderConfigurationSnapshot
    from a_conductor.provider_configuration import (
        EgressBoundary,
        HarnessStrategy,
        ProviderConfiguration,
        ProviderEndpointConfig,
        ProviderHealth,
        ProviderModelConfiguration,
        ProviderObservation,
        ProviderTrustClass,
        ProtocolFamily,
    )

    profile = ProviderConfiguration(
        provider_id="provider-1",
        display_name="Provider One",
        provider_type="cloud-proxy",
        protocol_family=ProtocolFamily.ANTHROPIC_MESSAGES,
        endpoint_ref="provider-config:one/base-url",
        credential_ref="secret-ref:provider-one",
        trust_class=ProviderTrustClass.TRUSTED_THIRD_PARTY,
        egress_boundary=EgressBoundary.EXTERNAL_THIRD_PARTY,
        harness_strategies=(HarnessStrategy.CLAUDE_CODE_CLI,),
        max_concurrency=1,
        models=(
            ProviderModelConfiguration(
                model_id="model-1",
                display_name="Model One",
                supported_effort_levels=("MAX",),
            ),
        ),
        enabled=True,
    )
    endpoint = ProviderEndpointConfig(
        profile.endpoint_ref,
        "https://provider.example/v1",
    )
    observation = ProviderObservation(
        provider_id=profile.provider_id,
        health=ProviderHealth.AVAILABLE,
        observed_at=datetime(2026, 9, 21, tzinfo=timezone.utc),
        provenance="test:runtime-activation",
        configuration_generation=7,
    )
    return ProviderConfigurationSnapshot(
        profile=profile,
        endpoint=endpoint,
        generation=7,
        observation=observation,
    )


def _contract_request(root, contract_ref, packet_path):
    return RuntimeActivationRequest(
        graph_id="graph-1",
        graph_run_id="run-1",
        node_id="n1",
        runtime_kind="serena",
        project_root=str(root),
        task_contract_ref=contract_ref,
        task_packet_path=str(packet_path),
        provider_id="provider-1",
        model_id="model-1",
    )


def test_build_activation_contract_derives_read_only_authorities(tmp_path):
    from a_conductor.claude_code_harness import MutationIntent
    from a_conductor.graph.dispatch import GraphDispatchKey
    from a_conductor.runtime_activation import build_activation_contract
    from a_conductor.worker_lease import LeaseMutationIntent

    contract_ref, packet_path = _write_activation_authority(tmp_path)
    request = _contract_request(tmp_path, contract_ref, packet_path)
    node = TaskNode("n1", "bounded activation")

    contract = build_activation_contract(
        request,
        node,
        database_path=tmp_path / "control.sqlite",
        provider_snapshot=_provider_snapshot(),
        ordered_worker_ids=("a-worker-01", "a-worker-02"),
    )

    key = GraphDispatchKey("graph-1", "run-1", "n1")
    assert contract.dispatch_key == key
    assert contract.project_id == "project-1"
    assert contract.work_order_ref == contract_ref
    assert contract.operation_ref == contract.provider_requirement.operation_ref
    assert contract.provider_requirement.matches_provider_authority_path(
        tmp_path / "control.sqlite"
    )
    assert contract.provider_security == contract.provider_requirement.provider_security
    assert contract.expected_configuration_generation == 7
    assert contract.harness_dispatch.execution_id == key.job_id
    assert contract.harness_dispatch.mutation_intent is MutationIntent.READ_ONLY
    assert contract.lease_request.session_id == key.job_id
    assert contract.lease_request.task_id == "task-activation-1"
    assert contract.lease_request.ordered_worker_ids == (
        "a-worker-01",
        "a-worker-02",
    )
    assert contract.lease_request.mutation_intent is LeaseMutationIntent.READ_ONLY
    assert contract.lease_request.mutable_scope == ()
    assert contract.lease_request.lease_ttl_seconds > contract.harness_dispatch.timeout_seconds
    assert contract.task_packet.task_contract_ref == contract_ref
    assert contract.max_attempts == 2


def test_build_activation_contract_derives_mutation_scope_from_task_authority(tmp_path):
    from a_conductor.claude_code_harness import MutationIntent
    from a_conductor.runtime_activation import build_activation_contract
    from a_conductor.worker_lease import LeaseMutationIntent

    contract_ref, packet_path = _write_activation_authority(
        tmp_path,
        mutation_allowed=True,
        allowed_files=("src/a.py", "tests/test_a.py"),        worker_ids=("a-worker-01",),
    )
    request = _contract_request(tmp_path, contract_ref, packet_path)

    contract = build_activation_contract(
        request,
        TaskNode("n1", "mutating activation"),
        database_path=tmp_path / "control.sqlite",
        provider_snapshot=_provider_snapshot(),
        ordered_worker_ids=("a-worker-01",),
    )

    assert contract.harness_dispatch.mutation_intent is MutationIntent.PROJECT_MUTATION
    assert contract.lease_request.mutation_intent is LeaseMutationIntent.MUTATION
    assert contract.lease_request.allowed_scope == ("src/a.py", "tests/test_a.py")
    assert contract.lease_request.mutable_scope == ("src/a.py", "tests/test_a.py")
    assert contract.lease_request.forbidden_scope == ("secrets/**",)


def test_build_activation_contract_refuses_mutation_without_explicit_scope(tmp_path):
    from a_conductor.runtime_activation import (
        RuntimeActivationError,
        build_activation_contract,
    )

    contract_ref, packet_path = _write_activation_authority(
        tmp_path,
        mutation_allowed=True,        worker_ids=("a-worker-01",),
    )
    request = _contract_request(tmp_path, contract_ref, packet_path)

    with pytest.raises(
        RuntimeActivationError,
        match="ACTIVATION_MUTABLE_SCOPE_REQUIRED",
    ):
        build_activation_contract(
            request,
            TaskNode("n1", "mutating activation"),
            database_path=tmp_path / "control.sqlite",
            provider_snapshot=_provider_snapshot(),
            ordered_worker_ids=("a-worker-01",),
        )


def test_build_activation_contract_refuses_missing_worker_authority(tmp_path):
    from a_conductor.runtime_activation import (
        RuntimeActivationError,
        build_activation_contract,
    )

    contract_ref, packet_path = _write_activation_authority(tmp_path)
    request = _contract_request(tmp_path, contract_ref, packet_path)

    with pytest.raises(
        RuntimeActivationError,
        match="WORKER_CANDIDATE_AUTHORITY_MISSING",
    ):
        build_activation_contract(
            request,
            TaskNode("n1", "bounded activation"),
            database_path=tmp_path / "control.sqlite",
            provider_snapshot=_provider_snapshot(),
            ordered_worker_ids=(),
        )


def test_runtime_activation_batch_identity_is_deterministic():
    from a_conductor.runtime_activation import derive_runtime_activation_batch_id

    request = RuntimeActivationRequest(
        graph_id="graph-1",
        graph_run_id="run-1",
        node_id="n1",
        runtime_kind="serena",
        project_root="/repo",
        task_contract_ref="tasks/task.json",
        task_packet_path="/repo/task.md",
        provider_id="provider-1",
        model_id="model-1",
    )
    same = RuntimeActivationRequest(
        graph_id="graph-1",
        graph_run_id="run-1",
        node_id="n1",
        runtime_kind="other-runtime-kind",
        project_root="/different-local-spelling",
        task_contract_ref="tasks/task.json",
        task_packet_path="/different/packet-path",
        provider_id="other-provider",
        model_id="other-model",
    )
    other = RuntimeActivationRequest(
        graph_id="graph-1",
        graph_run_id="run-1",
        node_id="n2",
        runtime_kind="serena",
        project_root="/repo",
        task_contract_ref="tasks/task.json",
        task_packet_path="/repo/task.md",
        provider_id="provider-1",
        model_id="model-1",
    )

    first = derive_runtime_activation_batch_id(request)
    assert first == derive_runtime_activation_batch_id(same)
    assert first != derive_runtime_activation_batch_id(other)


def test_load_activation_authority_refuses_unknown_dispatch_mode(tmp_path):
    from a_conductor.runtime_activation import (
        RuntimeActivationError,
        load_activation_authority,
    )

    contract_ref, packet_path = _write_activation_authority(
        tmp_path,
        dispatch_mode="UNKNOWN",
    )
    request = _contract_request(tmp_path, contract_ref, packet_path)

    with pytest.raises(RuntimeActivationError, match="DISPATCH_MODE_INVALID"):
        load_activation_authority(request)


def test_build_activation_contract_refuses_interactive_pull_launch_contract(tmp_path):
    from a_conductor.runtime_activation import (
        RuntimeActivationError,
        build_activation_contract,
    )

    contract_ref, packet_path = _write_activation_authority(
        tmp_path,
        dispatch_mode="INTERACTIVE_PULL",
        worker_id="a-worker-01",
        worker_ids=None,
    )
    request = _contract_request(tmp_path, contract_ref, packet_path)

    with pytest.raises(
        RuntimeActivationError,
        match="INTERACTIVE_PULL_REQUIRES_OFFER_PATH",
    ):
        build_activation_contract(
            request,
            TaskNode("n1", "pull-mode activation"),
            database_path=tmp_path / "control.sqlite",
            provider_snapshot=_provider_snapshot(),
            ordered_worker_ids=("a-worker-01",),
        )


def _control_center_for_pull(root):
    from a_conductor.control_center import ControlCenterSnapshot, WorkerScreenRow
    from a_conductor.domain import Project, WorkerState

    class _ControlCenter:
        def snapshot(self):
            return ControlCenterSnapshot(
                projects=(
                    Project(
                        project_id="project-1",
                        display_name="Project One",
                        root_path=str(root),
                    ),
                ),
                workers=(
                    WorkerScreenRow(
                        worker_id="a-worker-01",
                        display_name="Worker One",
                        state=WorkerState.STOPPED,
                        runtime_id="runtime-a-worker-01",
                        assignment_id="assignment-1",
                        project_id="project-1",
                        project_display_name="Project One",
                        project_root_path=str(root),
                        mutation_allowed=True,
                    ),
                ),
            )

    return _ControlCenter()


def test_interactive_pull_offer_is_durable_and_never_executes_backend(tmp_path):
    import sqlite3

    from a_conductor.graph.dispatch import GraphDispatchAction
    from a_conductor.graph.store import GraphStore
    from a_conductor.runtime_activation import offer_interactive_runtime

    database = tmp_path / "control.sqlite"
    graph = _graph(TaskNode("n1", "pull task"))
    GraphStore(database).save_graph(graph, "graph-1")
    contract_ref, packet_path = _write_activation_authority(
        tmp_path,
        dispatch_mode="INTERACTIVE_PULL",
        worker_id="a-worker-01",
        worker_ids=None,
    )
    request = _contract_request(tmp_path, contract_ref, packet_path)

    first = offer_interactive_runtime(
        database_path=database,
        request=request,
        control_center=_control_center_for_pull(tmp_path),
    )
    second = offer_interactive_runtime(
        database_path=database,
        request=request,
        control_center=_control_center_for_pull(tmp_path),
    )

    assert first.action is GraphDispatchAction.OFFERED
    assert first.reason_code == "INTERACTIVE_PULL_OFFERED"
    assert second.action is GraphDispatchAction.OFFERED
    assert second.job.job_id == first.job.job_id
    assert second.job.worker_id == "a-worker-01"
    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "job_records" in tables
    assert "execution_records" not in tables
    assert "worker_leases" not in tables
    assert "provider_admissions" not in tables


def test_interactive_pull_requires_exact_authoritative_worker(tmp_path):
    from a_conductor.graph.store import GraphStore
    from a_conductor.runtime_activation import (
        RuntimeActivationError,
        offer_interactive_runtime,
    )

    database = tmp_path / "control.sqlite"
    GraphStore(database).save_graph(
        _graph(TaskNode("n1", "pull task")),
        "graph-1",
    )
    contract_ref, packet_path = _write_activation_authority(
        tmp_path,
        dispatch_mode="INTERACTIVE_PULL",
        worker_id="missing-worker",
        worker_ids=None,
    )
    request = _contract_request(tmp_path, contract_ref, packet_path)

    with pytest.raises(
        RuntimeActivationError,
        match="INTERACTIVE_PULL_WORKER_UNAVAILABLE",
    ):
        offer_interactive_runtime(
            database_path=database,
            request=request,
            control_center=_control_center_for_pull(tmp_path),
        )
