from __future__ import annotations

import pytest

from a_conductor.graph.barriers import (
    FanInChildObservation,
    evaluate_fan_in_barrier,
)
from a_conductor.graph.domain import DependencyType, TaskEdge, TaskNode
from a_conductor.graph.graph import build_graph


def _node(node_id: str, *, outputs: tuple[str, ...] = ()) -> TaskNode:
    return TaskNode(id=node_id, objective=f"objective {node_id}", expected_outputs=outputs)


def _graph(*, child_outputs: tuple[str, ...] = (), duplicate_edge: bool = False):
    edges = [TaskEdge("child", "join", DependencyType.DATA)]
    if duplicate_edge:
        edges.append(TaskEdge("child", "join", DependencyType.VERIFICATION))
    return build_graph([_node("child", outputs=child_outputs), _node("join")], edges)


def test_root_barrier_is_vacuously_complete_and_satisfied() -> None:
    graph = build_graph([_node("root")], [])
    result = evaluate_fan_in_barrier(graph, "root", {})
    assert result.expected_ids == ()
    assert result.is_complete
    assert result.is_satisfied


def test_unknown_target_fails_closed() -> None:
    graph = build_graph([_node("root")], [])
    with pytest.raises(ValueError, match="unknown target"):
        evaluate_fan_in_barrier(graph, "ghost", {})


def test_missing_predecessor_observation_is_not_pending_or_success() -> None:
    result = evaluate_fan_in_barrier(_graph(), "join", {})
    assert result.expected_ids == ("child",)
    assert result.missing_ids == ("child",)
    assert result.pending_ids == ()
    assert not result.is_complete
    assert not result.is_satisfied


def test_observed_nonterminal_child_is_pending() -> None:
    obs = FanInChildObservation("child", terminal=False)
    result = evaluate_fan_in_barrier(_graph(), "join", {"child": obs})
    assert result.pending_ids == ("child",)
    assert result.missing_ids == ()
    assert not result.is_complete


def test_terminal_success_without_declared_outputs_satisfies() -> None:
    obs = FanInChildObservation("child", terminal=True, successful=True)
    result = evaluate_fan_in_barrier(_graph(), "join", {"child": obs})
    assert result.successful_ids == ("child",)
    assert result.failed_ids == ()
    assert result.is_complete
    assert result.is_satisfied


def test_terminal_failure_is_complete_but_not_satisfied() -> None:
    obs = FanInChildObservation("child", terminal=True)
    result = evaluate_fan_in_barrier(_graph(), "join", {"child": obs})
    assert result.failed_ids == ("child",)
    assert result.is_complete
    assert not result.is_satisfied


def test_skipped_child_without_declared_outputs_satisfies_ge5_semantics() -> None:
    obs = FanInChildObservation("child", terminal=True, skipped=True)
    result = evaluate_fan_in_barrier(_graph(), "join", {"child": obs})
    assert result.skipped_ids == ("child",)
    assert result.is_complete
    assert result.is_satisfied


def test_successful_child_missing_declared_output_is_silent() -> None:
    obs = FanInChildObservation("child", terminal=True, successful=True)
    result = evaluate_fan_in_barrier(
        _graph(child_outputs=("artifact:a",)), "join", {"child": obs}
    )
    assert result.silent_ids == ("child",)
    assert result.output_gaps == (("child", ("artifact:a",)),)
    assert not result.is_complete
    assert not result.is_satisfied


def test_skipped_child_with_declared_output_missing_is_silent() -> None:
    obs = FanInChildObservation("child", terminal=True, skipped=True)
    result = evaluate_fan_in_barrier(
        _graph(child_outputs=("artifact:a",)), "join", {"child": obs}
    )
    assert result.skipped_ids == ("child",)
    assert result.silent_ids == ("child",)
    assert not result.is_complete
    assert not result.is_satisfied


def test_partial_output_gap_is_exact_and_deterministic() -> None:
    obs = FanInChildObservation(
        "child",
        terminal=True,
        successful=True,
        observed_outputs=("artifact:c", "artifact:a", "extra"),
    )
    result = evaluate_fan_in_barrier(
        _graph(child_outputs=("artifact:a", "artifact:b", "artifact:c")),
        "join",
        {"child": obs},
    )
    assert result.output_gaps == (("child", ("artifact:b",)),)
    assert result.silent_ids == ("child",)


def test_duplicate_edge_types_count_one_child_and_extra_observation_is_ignored() -> None:
    graph = _graph(duplicate_edge=True)
    result = evaluate_fan_in_barrier(
        graph,
        "join",
        {
            "child": FanInChildObservation("child", terminal=True, successful=True),
            "unrelated": FanInChildObservation("unrelated", terminal=False),
        },
    )
    assert result.expected_ids == ("child",)
    assert result.successful_ids == ("child",)
    assert result.is_satisfied


def test_observation_rejects_success_or_skip_before_terminal() -> None:
    with pytest.raises(ValueError, match="terminal"):
        FanInChildObservation("child", terminal=False, successful=True)
    with pytest.raises(ValueError, match="terminal"):
        FanInChildObservation("child", terminal=False, skipped=True)


def test_observation_rejects_success_and_skip_together() -> None:
    with pytest.raises(ValueError, match="both"):
        FanInChildObservation("child", terminal=True, successful=True, skipped=True)


def test_observation_map_key_must_match_observation_identity() -> None:
    graph = _graph()
    with pytest.raises(ValueError, match="identity"):
        evaluate_fan_in_barrier(
            graph,
            "join",
            {"child": FanInChildObservation("other", terminal=False)},
        )


def test_fan_out_parent_tracks_all_outgoing_children_once() -> None:
    graph = build_graph(
        [_node("parent"), _node("a"), _node("b")],
        [
            TaskEdge("parent", "a", DependencyType.DATA),
            TaskEdge("parent", "a", DependencyType.VERIFICATION),
            TaskEdge("parent", "b", DependencyType.ORDERING),
        ],
    )
    observations = {
        "a": FanInChildObservation("a", terminal=True, successful=True),
        "b": FanInChildObservation("b", terminal=False),
    }
    from a_conductor.graph.barriers import evaluate_fan_out_barrier

    result = evaluate_fan_out_barrier(graph, "parent", observations)
    assert result.expected_ids == ("a", "b")
    assert result.successful_ids == ("a",)
    assert result.pending_ids == ("b",)
    assert not result.is_complete


def test_fan_out_leaf_is_vacuously_complete_and_satisfied() -> None:
    from a_conductor.graph.barriers import evaluate_fan_out_barrier

    graph = build_graph([_node("leaf")], [])
    result = evaluate_fan_out_barrier(graph, "leaf", {})
    assert result.expected_ids == ()
    assert result.is_complete
    assert result.is_satisfied


def test_observed_output_refs_are_normalized_before_matching() -> None:
    obs = FanInChildObservation(
        "child",
        terminal=True,
        successful=True,
        observed_outputs=("  artifact:a  ",),
    )
    result = evaluate_fan_in_barrier(
        _graph(child_outputs=("artifact:a",)), "join", {"child": obs}
    )
    assert result.output_gaps == ()
    assert result.silent_ids == ()
    assert result.is_satisfied


def test_blank_declared_output_ref_fails_closed() -> None:
    obs = FanInChildObservation("child", terminal=True, successful=True)
    graph = _graph(child_outputs=("   ",))
    with pytest.raises(ValueError, match="expected_outputs"):
        evaluate_fan_in_barrier(graph, "join", {"child": obs})
