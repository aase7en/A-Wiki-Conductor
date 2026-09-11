import json

import pytest

from a_conductor.graph.domain import DependencyType, TaskEdge, TaskGraph, TaskNode, TaskNodeStatus
from a_conductor.orchestration_packet import (
    EligibleRouteCandidate,
    RepositoryFacts,
    build_orchestration_packet,
)


def _task_contract() -> dict:
    return {
        "schema_version": "1.0.0",
        "task_id": "TASK-ODP-001",
        "work_order_ref": "WO-P1-150",
        "goal": "Implement one bounded orchestration packet projection.",
        "risk_class": "NORMAL",
        "authority": {
            "requested_by": "PRIVATE_REQUESTER",
            "approved_by": "PRIVATE_APPROVER",
            "approval_ref": "PRIVATE_APPROVAL_REF",
            "mutation_allowed": True,
            "human_approval_required": False,
        },
        "target": {
            "project_id": "A-Wiki-Conductor",
            "repository_identity_ref": "repo:a-wiki-conductor",
            "expected_worktree_path": "PRIVATE_WORKTREE_PATH",
            "expected_branch": "feat/example",
            "expected_head": "0123456789abcdef",
            "identity_policy": "EXACT",
        },
        "scope": {
            "allowed_files": ["src/example.py"],
            "forbidden_files": ["secrets/**"],
            "allowed_commands": ["echo PRIVATE_COMMAND_SECRET"],
            "forbidden_commands": ["PRIVATE_FORBIDDEN_COMMAND"],
            "max_changed_files": 2,
            "max_diff_bytes": 4096,
            "scope_growth": "FORBIDDEN",
        },
        "acceptance": {
            "criteria": ["Focused tests pass."],
            "verify_commands": ["echo PRIVATE_VERIFY_COMMAND"],
            "review_required": True,
            "required_review_class": "independent",
        },
        "security": {
            "privacy_class": "INTERNAL",
            "network_policy": "DENIED",
            "network_allowlist": ["PRIVATE_NETWORK_TARGET"],
            "secret_access": False,
        },
        "routing": {
            "required_capabilities": ["repository-read", "tests"],
            "preferred_surface_traits": {
                "supports_long_running": False,
                "supports_resume": True,
                "supports_background_execution": False,
                "supports_repo_tools": True,
                "requires_human_presence": False,
                "max_safe_transaction_scope": "one bounded task",
            },
        },
        "budget": {
            "max_elapsed_seconds": 600,
            "max_input_tokens": 10000,
            "max_output_tokens": 5000,
            "max_estimated_cost_usd": 1.0,
        },
        "retry_policy": {
            "max_attempts": 2,
            "max_identical_failures": 1,
            "on_lease_expiry": "RECOVERY_REQUIRED",
        },
        "escalation": {"conditions": ["REPEATED_FAILURE"]},
        "required_evidence": ["TEST_RESULT", "REVIEW_RESULT"],
        "metadata": {
            "api_key": "PRIVATE_API_KEY_VALUE",
            "chat_transcript": "PRIVATE_CHAT_TRANSCRIPT",
        },
    }


def _graph() -> tuple[TaskGraph, dict[str, TaskNodeStatus]]:
    graph = TaskGraph()
    graph.add_node(TaskNode(id="plan", objective="Establish settled contract.", expected_outputs=("contract",)))
    graph.add_node(
        TaskNode(
            id="implement",
            objective="Implement the bounded slice.",
            expected_outputs=("source", "tests"),
            read_set=("src/**",),
            write_set=("src/example.py",),
            worker_requirement=("repository-write", "tests"),
            model_requirement="vendor-specific-model-must-not-project",
            priority=10,
            timeout_seconds=300,
        )
    )
    graph.add_node(
        TaskNode(
            id="verify",
            objective="Verify the exact artifact.",
            worker_requirement=("code-review", "independent-judgement"),
        )
    )
    graph.add_edge(TaskEdge("plan", "implement", DependencyType.ORDERING))
    graph.add_edge(TaskEdge("implement", "verify", DependencyType.VERIFICATION))
    states = {
        "plan": TaskNodeStatus.DONE,
        "implement": TaskNodeStatus.TODO,
        "verify": TaskNodeStatus.TODO,
    }
    return graph, states


def _repo_facts() -> RepositoryFacts:
    return RepositoryFacts(
        project_id="A-Wiki-Conductor",
        repository_ref="github:aase7en/A-Wiki-Conductor",
        worktree_ref="worktree:wo150",
        branch="feat/wo-p1-150-orchestration-packet-v1",
        head_sha="0123456789abcdef",
        dirty=False,
        identity_verified=True,
        mutation_authorized=True,
    )


def _candidate(candidate_id: str = "route-b") -> EligibleRouteCandidate:
    return EligibleRouteCandidate(
        candidate_id=candidate_id,
        actor_role="deterministic-executor",
        provider_id="provider-safe",
        model_id="model-safe",
        capabilities=("repository-write", "tests"),
        supports_long_running=False,
        supports_resume=True,
        supports_background_execution=False,
        supports_repo_tools=True,
        requires_human_presence=False,
        max_concurrency=2,
        cost_class="LOW",
        quota_state="AVAILABLE",
        evidence_refs=("provider-observation:42",),
    )


def test_packet_projects_allowlisted_task_graph_and_ready_frontier_without_secret_fields() -> None:
    graph, states = _graph()
    before_nodes = graph.nodes()
    before_edges = graph.edges()

    packet = build_orchestration_packet(
        task_contract=_task_contract(),
        graph=graph,
        node_states=states,
        graph_id="graph-odp-001",
        repository=_repo_facts(),
        eligible_candidates=(_candidate(),),
        policy_refs=("awiki-policy:v1",),
        evidence_refs=("test:baseline",),
        blockers=("REVIEW_PENDING",),
        max_parallelism=2,
    )
    payload = packet.to_dict()

    assert payload["schema_version"] == "orchestration-packet/v1"
    assert payload["task"]["task_id"] == "TASK-ODP-001"
    assert payload["task"]["authority"] == {
        "mutation_allowed": True,
        "human_approval_required": False,
    }
    assert payload["task"]["scope"] == {
        "allowed_files": ["src/example.py"],
        "forbidden_files": ["secrets/**"],
        "max_changed_files": 2,
        "max_diff_bytes": 4096,
        "scope_growth": "FORBIDDEN",
    }
    assert payload["task"]["security"] == {
        "privacy_class": "INTERNAL",
        "network_policy": "DENIED",
        "secret_access": False,
    }
    assert payload["graph"]["ready_frontier"] == ["implement"]
    implement = next(node for node in payload["graph"]["nodes"] if node["id"] == "implement")
    assert implement["worker_requirement"] == ["repository-write", "tests"]
    assert "model_requirement" not in implement
    assert payload["limits"] == {"max_parallelism": 2, "max_adjudication_rounds": 3}

    encoded = json.dumps(payload, sort_keys=True)
    for forbidden in (
        "PRIVATE_REQUESTER",
        "PRIVATE_APPROVER",
        "PRIVATE_APPROVAL_REF",
        "PRIVATE_WORKTREE_PATH",
        "PRIVATE_COMMAND_SECRET",
        "PRIVATE_FORBIDDEN_COMMAND",
        "PRIVATE_VERIFY_COMMAND",
        "PRIVATE_NETWORK_TARGET",
        "PRIVATE_CHAT_TRANSCRIPT",
        "PRIVATE_API_KEY_VALUE",
        "vendor-specific-model-must-not-project",
    ):
        assert forbidden not in encoded

    assert graph.nodes() == before_nodes
    assert graph.edges() == before_edges


def test_packet_sorts_preeligible_candidates_by_stable_candidate_id() -> None:
    graph, states = _graph()
    packet = build_orchestration_packet(
        task_contract=_task_contract(),
        graph=graph,
        node_states=states,
        graph_id="graph-odp-002",
        repository=_repo_facts(),
        eligible_candidates=(_candidate("route-z"), _candidate("route-a")),
    )
    assert [item["candidate_id"] for item in packet.to_dict()["eligible_candidates"]] == ["route-a", "route-z"]


def test_duplicate_candidate_id_fails_closed() -> None:
    graph, states = _graph()
    with pytest.raises(ValueError, match="duplicate eligible candidate_id"):
        build_orchestration_packet(
            task_contract=_task_contract(),
            graph=graph,
            node_states=states,
            graph_id="graph-odp-003",
            repository=_repo_facts(),
            eligible_candidates=(_candidate("same"), _candidate("same")),
        )


@pytest.mark.parametrize(
    "field,value",
    [("max_parallelism", 0), ("max_parallelism", True), ("max_adjudication_rounds", 0), ("max_adjudication_rounds", True)],
)
def test_loop_limits_require_positive_non_boolean_integers(field: str, value: object) -> None:
    graph, states = _graph()
    kwargs = {"max_parallelism": 1, "max_adjudication_rounds": 3}
    kwargs[field] = value
    with pytest.raises(ValueError, match=field):
        build_orchestration_packet(
            task_contract=_task_contract(),
            graph=graph,
            node_states=states,
            graph_id="graph-odp-004",
            repository=_repo_facts(),
            eligible_candidates=(),
            **kwargs,
        )


def test_missing_required_task_contract_field_fails_closed() -> None:
    task = _task_contract()
    del task["acceptance"]
    graph, states = _graph()
    with pytest.raises(ValueError, match="task_contract.acceptance"):
        build_orchestration_packet(
            task_contract=task,
            graph=graph,
            node_states=states,
            graph_id="graph-odp-005",
            repository=_repo_facts(),
            eligible_candidates=(),
        )


def test_candidate_rejects_blank_or_nonpositive_control_fields() -> None:
    with pytest.raises(ValueError, match="candidate_id"):
        EligibleRouteCandidate(candidate_id=" ", actor_role="deterministic-executor", provider_id="p", model_id="m")
    with pytest.raises(ValueError, match="max_concurrency"):
        EligibleRouteCandidate(candidate_id="c", actor_role="deterministic-executor", provider_id="p", model_id="m", max_concurrency=0)
    with pytest.raises(ValueError, match="capabilities"):
        EligibleRouteCandidate(candidate_id="c", actor_role="deterministic-executor", provider_id="p", model_id="m", capabilities=("tests", ""))


def test_repository_facts_reject_unverified_mutation_authority_combination() -> None:
    with pytest.raises(ValueError, match="mutation_authorized requires identity_verified"):
        RepositoryFacts(
            project_id="p",
            repository_ref="repo:test",
            worktree_ref="worktree:test",
            branch="b",
            head_sha="0123456",
            dirty=False,
            identity_verified=False,
            mutation_authorized=True,
        )


def test_nested_routing_extras_fail_closed_as_invalid_task_contract_v1() -> None:
    task = _task_contract()
    task["routing"]["preferred_surface_traits"]["private_nested"] = "PRIVATE_NESTED_TRAIT"
    graph, states = _graph()
    with pytest.raises(ValueError, match="private_nested"):
        build_orchestration_packet(
            task_contract=task,
            graph=graph,
            node_states=states,
            graph_id="graph-odp-006",
            repository=_repo_facts(),
            eligible_candidates=(),
        )


def test_graph_summary_uses_same_missing_state_default_as_ready_authority() -> None:
    graph = TaskGraph()
    graph.add_node(TaskNode(id="legacy-done-metadata", objective="Runtime state is absent.", status=TaskNodeStatus.DONE))
    payload = build_orchestration_packet(
        task_contract=_task_contract(),
        graph=graph,
        node_states={},
        graph_id="graph-odp-007",
        repository=_repo_facts(),
        eligible_candidates=(),
    ).to_dict()
    assert payload["graph"]["ready_frontier"] == ["legacy-done-metadata"]
    assert payload["graph"]["nodes"][0]["status"] == "todo"


def test_malformed_required_evidence_fails_with_typed_value_error() -> None:
    task = _task_contract()
    task["required_evidence"] = 123
    graph, states = _graph()
    with pytest.raises(ValueError, match="task_contract.required_evidence"):
        build_orchestration_packet(
            task_contract=task,
            graph=graph,
            node_states=states,
            graph_id="graph-odp-008",
            repository=_repo_facts(),
            eligible_candidates=(),
        )


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda task: task.__setitem__("schema_version", "9.9.9"), "schema_version"),
        (lambda task: task.__setitem__("risk_class", "NOT_A_RISK"), "risk_class"),
        (lambda task: task["authority"].__setitem__("mutation_allowed", "false"), "mutation_allowed"),
        (lambda task: task["security"].__setitem__("secret_access", "false"), "secret_access"),
        (lambda task: task["budget"].__setitem__("max_elapsed_seconds", -5), "max_elapsed_seconds"),
        (lambda task: task.__setitem__("required_evidence", ["NOT_REAL"]), "required_evidence"),
        (lambda task: task["scope"].__setitem__("scope_growth", "ALLOW_ANY"), "scope_growth"),
    ],
)
def test_packet_rejects_task_contract_v1_authority_drift(mutate, match: str) -> None:
    task = _task_contract()
    mutate(task)
    graph, states = _graph()
    with pytest.raises(ValueError, match=match):
        build_orchestration_packet(
            task_contract=task,
            graph=graph,
            node_states=states,
            graph_id="graph-odp-authority-drift",
            repository=_repo_facts(),
            eligible_candidates=(),
        )


def test_reference_fields_reject_raw_paths_and_secret_bearing_values() -> None:
    graph, states = _graph()
    with pytest.raises(ValueError, match="repository_ref"):
        RepositoryFacts(project_id="p", repository_ref="C:/Users/private/repo", worktree_ref="worktree:wo", branch="b", head_sha="0123456", dirty=False, identity_verified=True, mutation_authorized=False)
    with pytest.raises(ValueError, match="worktree_ref"):
        RepositoryFacts(project_id="p", repository_ref="github:aase7en/A-Wiki-Conductor", worktree_ref="secret-ref:API_TOKEN", branch="b", head_sha="0123456", dirty=False, identity_verified=True, mutation_authorized=False)
    with pytest.raises(ValueError, match="evidence_refs"):
        EligibleRouteCandidate(candidate_id="c", actor_role="r", evidence_refs=("secret-ref:opaque-value",))
    with pytest.raises(ValueError, match="evidence_refs"):
        build_orchestration_packet(task_contract=_task_contract(), graph=graph, node_states=states, graph_id="g", repository=_repo_facts(), eligible_candidates=(), evidence_refs=("raw credential text",))
    with pytest.raises(ValueError, match="policy_refs"):
        build_orchestration_packet(task_contract=_task_contract(), graph=graph, node_states=states, graph_id="g", repository=_repo_facts(), eligible_candidates=(), policy_refs=("C:/Users/private/policy",))
    task = _task_contract()
    task["target"]["repository_identity_ref"] = "C:/Users/private/repo"
    with pytest.raises(ValueError, match="repository_identity_ref"):
        build_orchestration_packet(task_contract=task, graph=graph, node_states=states, graph_id="g", repository=_repo_facts(), eligible_candidates=())


def test_routing_surface_traits_reject_non_boolean_authority_drift() -> None:
    task = _task_contract()
    task["routing"]["preferred_surface_traits"]["supports_repo_tools"] = "false"
    graph, states = _graph()
    with pytest.raises(ValueError, match="supports_repo_tools"):
        build_orchestration_packet(task_contract=task, graph=graph, node_states=states, graph_id="g", repository=_repo_facts(), eligible_candidates=())


@pytest.mark.parametrize(
    "unsafe_ref",
    [
        "file:C:/Users/private/repo",
        "path:C:/Users/private/repo",
        "https:example.com/private",
        "url:example.com/private",
        "env:API_KEY",
        "evidence:Bearer_SECRET",
        "evidence:ghp_FAKE",
    ],
)
def test_reference_fields_reject_nonsemantic_or_credential_shaped_refs(unsafe_ref: str) -> None:
    graph, states = _graph()
    with pytest.raises(ValueError, match="safe namespaced reference"):
        build_orchestration_packet(
            task_contract=_task_contract(),
            graph=graph,
            node_states=states,
            graph_id="g",
            repository=_repo_facts(),
            eligible_candidates=(),
            evidence_refs=(unsafe_ref,),
        )


def test_reference_fields_accept_declared_semantic_namespaces() -> None:
    graph, states = _graph()
    packet = build_orchestration_packet(
        task_contract=_task_contract(),
        graph=graph,
        node_states=states,
        graph_id="g",
        repository=_repo_facts(),
        eligible_candidates=(EligibleRouteCandidate(
            candidate_id="c", actor_role="r", evidence_refs=("provider-observation:42",)
        ),),
        policy_refs=("awiki-policy:v1",),
        evidence_refs=("test:baseline", "evidence:transport-502"),
    )
    assert packet.to_dict()["evidence_refs"] == ["test:baseline", "evidence:transport-502"]


def test_reference_namespaces_are_field_specific() -> None:
    graph, states = _graph()
    with pytest.raises(ValueError, match="repository_ref"):
        RepositoryFacts(
            project_id="p", repository_ref="evidence:repo-1", worktree_ref="worktree:w",
            branch="b", head_sha="0123456", dirty=False, identity_verified=True, mutation_authorized=False,
        )
    with pytest.raises(ValueError, match="worktree_ref"):
        RepositoryFacts(
            project_id="p", repository_ref="repo:r", worktree_ref="repo:w",
            branch="b", head_sha="0123456", dirty=False, identity_verified=True, mutation_authorized=False,
        )
    with pytest.raises(ValueError, match="policy_refs"):
        build_orchestration_packet(
            task_contract=_task_contract(), graph=graph, node_states=states, graph_id="g",
            repository=_repo_facts(), eligible_candidates=(), policy_refs=("test:policy",),
        )
    with pytest.raises(ValueError, match="evidence_refs"):
        build_orchestration_packet(
            task_contract=_task_contract(), graph=graph, node_states=states, graph_id="g",
            repository=_repo_facts(), eligible_candidates=(), evidence_refs=("policy:e1",),
        )


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda task: task["target"].__setitem__("expected_branch", ["not", "a", "branch"]), "expected_branch"),
        (lambda task: task["acceptance"].__setitem__("required_review_class", {"forged": True}), "required_review_class"),
    ],
)
def test_packet_rejects_projected_optional_field_type_drift(mutate, match: str) -> None:
    task = _task_contract()
    mutate(task)
    graph, states = _graph()
    with pytest.raises(ValueError, match=match):
        build_orchestration_packet(
            task_contract=task, graph=graph, node_states=states, graph_id="g",
            repository=_repo_facts(), eligible_candidates=(),
        )

def test_allowed_evidence_namespace_rejects_credential_bearing_payload():
    with pytest.raises(ValueError, match="evidence_refs"):
        EligibleRouteCandidate(
            candidate_id="c",
            actor_role="reviewer",
            evidence_refs=("evidence:AuthorizationBearerSECRET",),
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("objective", "AuthorizationBearerFAKE"),
        ("expected_outputs", ("secret-ref:FAKE",)),
        ("read_set", ("C:/Users/private/.ssh/id_rsa",)),
        ("write_set", ("../outside.txt",)),
        ("retry_policy_ref", "Authorization:BearerSECRET"),
        ("artifacts", ("C:/Users/private/.ssh/id_rsa",)),
    ],
)
def test_graph_projection_rejects_secret_or_private_path_shapes(field, value):
    kwargs = {"id": "unsafe", "objective": "Safe objective."}
    kwargs[field] = value
    graph = TaskGraph()
    graph.add_node(TaskNode(**kwargs))
    with pytest.raises(ValueError, match="graph_nodes|decision-safe|repo-relative|retry_policy_ref"):
        build_orchestration_packet(
            task_contract=_task_contract(),
            graph=graph,
            node_states={"unsafe": TaskNodeStatus.TODO},
            graph_id="graph-unsafe",
            repository=_repo_facts(),
            eligible_candidates=(),
        )

def test_task_projection_rejects_secret_or_private_path_shapes():
    graph, states = _graph()
    cases = []
    task = _task_contract(); task["goal"] = "AuthorizationBearerFAKE"; cases.append(task)
    task = _task_contract(); task["scope"]["allowed_files"] = ["C:/Users/private/.ssh/id_rsa"]; cases.append(task)
    task = _task_contract(); task["acceptance"]["criteria"] = ["token=FAKE"]; cases.append(task)
    task = _task_contract(); task["routing"]["preferred_surface_traits"]["max_safe_transaction_scope"] = "secret-ref:awiki/API_TOKEN"; cases.append(task)
    for unsafe_task in cases:
        with pytest.raises(ValueError, match="decision-safe|repo-relative"):
            build_orchestration_packet(
                task_contract=unsafe_task,
                graph=graph,
                node_states=states,
                graph_id="graph-safe",
                repository=_repo_facts(),
                eligible_candidates=(),
            )


def test_repository_and_candidate_labels_reject_credential_shapes():
    with pytest.raises(ValueError, match="project_id"):
        RepositoryFacts(
            project_id="ghp_FAKE",
            repository_ref="repo:test",
            worktree_ref="worktree:test",
            branch="main",
            head_sha="0123456",
            dirty=False,
            identity_verified=True,
            mutation_authorized=False,
        )
    with pytest.raises(ValueError, match="provider_id"):
        EligibleRouteCandidate(
            candidate_id="route",
            actor_role="executor",
            provider_id="AuthorizationBearerSECRET",
        )


def test_graph_id_and_blockers_reject_credential_shapes():
    graph, states = _graph()
    with pytest.raises(ValueError, match="graph_id"):
        build_orchestration_packet(
            task_contract=_task_contract(), graph=graph, node_states=states,
            graph_id="ghp_FAKE", repository=_repo_facts(),
            eligible_candidates=(),
        )
    with pytest.raises(ValueError, match="blockers"):
        build_orchestration_packet(
            task_contract=_task_contract(), graph=graph, node_states=states,
            graph_id="graph-safe", repository=_repo_facts(), eligible_candidates=(),
            blockers=("AuthorizationBearerFAKE",),
        )


@pytest.mark.parametrize(
    "unsafe_ref",
    (
        "evidence:incident-ghp_FAKE",
        "evidence:incident-sk-ant-FAKE",
        "evidence:proof-Bearer_FAKE",
    ),
)
def test_allowed_evidence_namespace_rejects_embedded_credential_markers(unsafe_ref: str) -> None:
    with pytest.raises(ValueError, match="evidence_refs"):
        EligibleRouteCandidate(
            candidate_id="c",
            actor_role="reviewer",
            evidence_refs=(unsafe_ref,),
        )


def test_allowed_evidence_namespace_preserves_semantic_token_budget_ref() -> None:
    route = EligibleRouteCandidate(
        candidate_id="c",
        actor_role="reviewer",
        evidence_refs=("evidence:token-budget",),
    )
    assert route.evidence_refs == ("evidence:token-budget",)


@pytest.mark.parametrize(
    "unsafe_scope",
    ("https://x/y", "file?x=1", "file#frag", "file=x", "file&x"),
)
def test_repo_scope_rejects_url_and_query_marked_values(unsafe_scope: str) -> None:
    graph, states = _graph()
    task = _task_contract()
    task["scope"]["allowed_files"] = [unsafe_scope]
    with pytest.raises(ValueError, match="repo-relative"):
        build_orchestration_packet(
            task_contract=task, graph=graph, node_states=states,
            graph_id="graph-safe", repository=_repo_facts(), eligible_candidates=(),
        )

    unsafe_graph = TaskGraph()
    unsafe_graph.add_node(TaskNode(id="n", objective="safe", read_set=(unsafe_scope,)))
    with pytest.raises(ValueError, match="repo-relative"):
        build_orchestration_packet(
            task_contract=_task_contract(), graph=unsafe_graph,
            node_states={"n": TaskNodeStatus.TODO}, graph_id="graph-safe",
            repository=_repo_facts(), eligible_candidates=(),
        )

def test_allowed_evidence_namespace_rejects_secret_ref_slash_separator() -> None:
    with pytest.raises(ValueError, match="evidence_refs"):
        EligibleRouteCandidate(
            candidate_id="c",
            actor_role="reviewer",
            evidence_refs=("evidence:secret-ref/x",),
        )


def test_allowed_evidence_namespace_preserves_semantic_bearer_capacity_ref() -> None:
    route = EligibleRouteCandidate(
        candidate_id="c",
        actor_role="reviewer",
        evidence_refs=("evidence:bearer-capacity",),
    )
    assert route.evidence_refs == ("evidence:bearer-capacity",)
