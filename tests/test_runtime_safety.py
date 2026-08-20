import pytest

from a_conductor.runtime_safety import (
    PortBindingState,
    ProcessObservation,
    ProcessOwnership,
    TunnelBindingState,
    WorktreeBindingState,
    classify_port_binding,
    classify_process_ownership,
    classify_tunnel_binding,
    classify_worktree_binding,
)


def test_process_ownership_absent_without_pid_metadata() -> None:
    observation = ProcessObservation(
        pid_metadata_present=False,
        pid=None,
        process_exists=None,
        executable_matches=None,
        profile_matches=None,
    )

    assert classify_process_ownership(observation) is ProcessOwnership.ABSENT


@pytest.mark.parametrize("pid", [None, 0, -1])
def test_invalid_pid_metadata_is_mismatch(pid) -> None:
    observation = ProcessObservation(
        pid_metadata_present=True,
        pid=pid,
        process_exists=None,
        executable_matches=None,
        profile_matches=None,
    )

    assert classify_process_ownership(observation) is ProcessOwnership.MISMATCH


def test_missing_recorded_process_is_stale() -> None:
    observation = ProcessObservation(
        pid_metadata_present=True,
        pid=1234,
        process_exists=False,
        executable_matches=None,
        profile_matches=None,
    )

    assert classify_process_ownership(observation) is ProcessOwnership.STALE


@pytest.mark.parametrize(
    ("executable_matches", "profile_matches"),
    [(False, True), (True, False), (False, False)],
)
def test_live_process_with_wrong_fingerprint_is_mismatch(
    executable_matches: bool,
    profile_matches: bool,
) -> None:
    observation = ProcessObservation(
        pid_metadata_present=True,
        pid=1234,
        process_exists=True,
        executable_matches=executable_matches,
        profile_matches=profile_matches,
    )

    assert classify_process_ownership(observation) is ProcessOwnership.MISMATCH


def test_live_process_with_incomplete_fingerprint_is_unknown() -> None:
    observation = ProcessObservation(
        pid_metadata_present=True,
        pid=1234,
        process_exists=True,
        executable_matches=True,
        profile_matches=None,
    )

    assert classify_process_ownership(observation) is ProcessOwnership.UNKNOWN


def test_live_process_with_matching_fingerprint_is_owned() -> None:
    observation = ProcessObservation(
        pid_metadata_present=True,
        pid=1234,
        process_exists=True,
        executable_matches=True,
        profile_matches=True,
    )

    assert classify_process_ownership(observation) is ProcessOwnership.OWNED


@pytest.mark.parametrize(
    ("listening", "owning_pid", "expected_pid", "expected"),
    [
        (False, None, None, PortBindingState.FREE),
        (True, 100, 100, PortBindingState.OWNED),
        (True, 200, 100, PortBindingState.COLLISION),
        (True, 200, None, PortBindingState.COLLISION),
        (True, None, 100, PortBindingState.UNKNOWN),
        (None, None, 100, PortBindingState.UNKNOWN),
    ],
)
def test_port_binding_classification(
    listening,
    owning_pid,
    expected_pid,
    expected,
) -> None:
    assert classify_port_binding(
        listening=listening,
        owning_pid=owning_pid,
        expected_pid=expected_pid,
    ) is expected


def test_tunnel_binding_is_free_when_unowned() -> None:
    assert classify_tunnel_binding(
        binding_ref="binding-01",
        active_owner_worker_id=None,
        requesting_worker_id="a-worker-01",
    ) is TunnelBindingState.FREE


def test_tunnel_binding_is_owned_when_same_worker_holds_it() -> None:
    assert classify_tunnel_binding(
        binding_ref="binding-01",
        active_owner_worker_id="a-worker-01",
        requesting_worker_id="a-worker-01",
    ) is TunnelBindingState.OWNED


def test_tunnel_binding_collision_when_another_worker_holds_it() -> None:
    assert classify_tunnel_binding(
        binding_ref="binding-01",
        active_owner_worker_id="a-worker-02",
        requesting_worker_id="a-worker-01",
    ) is TunnelBindingState.COLLISION


def test_worktree_is_available_when_unassigned() -> None:
    assert classify_worktree_binding(
        worktree_key="repo::worktree-a",
        active_mutating_worker_id=None,
        requesting_worker_id="a-worker-01",
    ) is WorktreeBindingState.AVAILABLE


def test_worktree_is_owned_when_same_worker_holds_mutation_assignment() -> None:
    assert classify_worktree_binding(
        worktree_key="repo::worktree-a",
        active_mutating_worker_id="a-worker-01",
        requesting_worker_id="a-worker-01",
    ) is WorktreeBindingState.OWNED


def test_worktree_conflict_when_another_worker_holds_mutation_assignment() -> None:
    assert classify_worktree_binding(
        worktree_key="repo::worktree-a",
        active_mutating_worker_id="a-worker-02",
        requesting_worker_id="a-worker-01",
    ) is WorktreeBindingState.CONFLICT


@pytest.mark.parametrize(
    ("function", "kwargs"),
    [
        (
            classify_tunnel_binding,
            {
                "binding_ref": " ",
                "active_owner_worker_id": None,
                "requesting_worker_id": "a-worker-01",
            },
        ),
        (
            classify_worktree_binding,
            {
                "worktree_key": "",
                "active_mutating_worker_id": None,
                "requesting_worker_id": "a-worker-01",
            },
        ),
    ],
)
def test_binding_classifiers_reject_blank_resource_identity(function, kwargs) -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        function(**kwargs)
