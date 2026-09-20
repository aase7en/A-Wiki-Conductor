"""Read-only observation layer tests: injectable ports, UNKNOWN vs absent,
protected-root matching, freshness recheck, fingerprint stamping."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from a_conductor.worktree_lifecycle import (
    WtlMergeFoldFact,
    WtlRemoteEvidence,
    WtlWorktreeFacts,
    wtl_input_fingerprint,
)
from a_conductor.worktree_lifecycle_observation import (
    StrictGitObservationPort,
    WtlObservationService,
)
from a_conductor.windows_observer import CommandResult

HEAD_A = "0123456789abcdef0123456789abcdef01234567"
HEAD_B = "fedcba9876543210fedcba9876543210fedcba98"
WORKTREE = r"A:\repo\wt-a"
WORKTREE_KEY = r"a:\repo\wt-a"
FIXED_NOW = datetime(2026, 9, 20, 6, 0, 0, tzinfo=timezone.utc)


class FakeGitPort:
    def __init__(
        self,
        *,
        heads: tuple[str | None, ...] = (HEAD_A, HEAD_A),
        branch: str | None = "feat/example",
        status: tuple[str, ...] | None = (),
    ) -> None:
        self._heads = list(heads)
        self.branch = branch
        self.status = status
        self.calls: list[str] = []

    def read_head(self, worktree: str) -> str | None:
        self.calls.append("read_head")
        return self._heads.pop(0) if self._heads else None

    def read_branch(self, worktree: str) -> str | None:
        self.calls.append("read_branch")
        return self.branch

    def read_status_porcelain(self, worktree: str) -> tuple[str, ...] | None:
        self.calls.append("read_status_porcelain")
        return self.status


class FakeCollector:
    def __init__(self, value) -> None:
        self.value = value
        self.calls: list[str] = []

    def __call__(self, worktree_key: str):
        self.calls.append(worktree_key)
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


class FakeRemotePort:
    def __init__(self, value) -> None:
        self.value = value

    def __call__(self, worktree_key: str, branch: str | None, head: str | None):
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


def service(
    *,
    git: FakeGitPort | None = None,
    leases=None,
    executions=None,
    processes=None,
    reviews=None,
    merge_fold=None,
    remote=None,
) -> WtlObservationService:
    return WtlObservationService(
        git_port=git or FakeGitPort(),
        lease_collector=leases,
        execution_collector=executions,
        process_collector=processes,
        review_freeze_collector=reviews,
        merge_fold_collector=merge_fold,
        remote_evidence_port=remote,
        now=lambda: FIXED_NOW,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_collect_happy_path_builds_stamped_facts() -> None:
    git = FakeGitPort(status=(" M src/x.py", "?? .serena/"))
    leases = FakeCollector(())
    merge_fold = FakeCollector(
        WtlMergeFoldFact(True, True, True, HEAD_B)
    )
    remote = FakeRemotePort(WtlRemoteEvidence(False, False, False))
    bundle = service(
        git=git,
        leases=leases,
        merge_fold=merge_fold,
        remote=remote,
    ).collect(WORKTREE)

    assert isinstance(bundle, WtlWorktreeFacts)
    assert bundle.worktree_key == WORKTREE_KEY
    assert bundle.head == HEAD_A
    assert bundle.head_recheck == HEAD_A
    assert bundle.branch == "feat/example"
    assert bundle.detached is False
    assert bundle.tracked_dirty is True
    assert any(path == ".serena" for path in bundle.untracked_paths)
    assert bundle.leases == ()
    assert bundle.merge_fold == WtlMergeFoldFact(True, True, True, HEAD_B)
    assert bundle.remote == WtlRemoteEvidence(False, False, False)
    assert bundle.observed_at == "2026-09-20T06:00:00.000000Z"
    assert bundle.input_fingerprint == wtl_input_fingerprint(bundle)
    assert git.calls.count("read_head") == 2


def test_collect_separates_tracked_and_untracked_evidence() -> None:
    git = FakeGitPort(status=("M  src/staged.py", " D src/gone.py", "?? notes.txt"))
    bundle = service(git=git).collect(WORKTREE)
    assert bundle.tracked_dirty is True
    assert bundle.untracked_paths == ("notes.txt",)


def test_collect_clean_status_observes_absent_not_unknown() -> None:
    git = FakeGitPort(status=())
    bundle = service(git=git).collect(WORKTREE)
    assert bundle.tracked_dirty is False
    assert bundle.untracked_paths == ()


def test_collect_detached_head() -> None:
    git = FakeGitPort(branch="HEAD")
    bundle = service(git=git).collect(WORKTREE)
    assert bundle.detached is True
    assert bundle.branch is None


# ---------------------------------------------------------------------------
# Fail-closed observation gaps (UNKNOWN, never invented absence)
# ---------------------------------------------------------------------------


def test_status_read_failure_yields_unknown_dirty_state() -> None:
    git = FakeGitPort(status=None)
    bundle = service(git=git).collect(WORKTREE)
    assert bundle.tracked_dirty is None
    assert bundle.untracked_paths is None


def test_head_read_failure_yields_unknown_head() -> None:
    git = FakeGitPort(heads=(None, None))
    bundle = service(git=git).collect(WORKTREE)
    assert bundle.head is None
    assert bundle.head_recheck is None


def test_branch_read_failure_yields_unknown_branch() -> None:
    git = FakeGitPort(branch=None)
    bundle = service(git=git).collect(WORKTREE)
    assert bundle.branch is None
    assert bundle.detached is None


def test_head_recheck_drift_is_captured() -> None:
    git = FakeGitPort(heads=(HEAD_A, HEAD_B))
    bundle = service(git=git).collect(WORKTREE)
    assert bundle.head == HEAD_A
    assert bundle.head_recheck == HEAD_B


def test_missing_collector_means_unknown_not_absent() -> None:
    bundle = service().collect(WORKTREE)
    assert bundle.leases is None
    assert bundle.durable_executions is None
    assert bundle.process_observations is None
    assert bundle.review_freezes is None
    assert bundle.merge_fold is None
    assert bundle.remote is None


def test_collector_none_result_is_preserved_as_unknown() -> None:
    bundle = service(
        leases=FakeCollector(None),
        merge_fold=FakeCollector(None),
        remote=FakeRemotePort(None),
    ).collect(WORKTREE)
    assert bundle.leases is None
    assert bundle.merge_fold is None
    assert bundle.remote is None


def test_collector_empty_result_is_preserved_as_observed_absent() -> None:
    bundle = service(
        leases=FakeCollector(()),
        executions=FakeCollector(()),
        processes=FakeCollector(()),
        reviews=FakeCollector(()),
    ).collect(WORKTREE)
    assert bundle.leases == ()
    assert bundle.durable_executions == ()
    assert bundle.process_observations == ()
    assert bundle.review_freezes == ()


def test_raising_collector_fails_closed_to_unknown() -> None:
    bundle = service(
        leases=FakeCollector(RuntimeError("lease store unreadable")),
        remote=FakeRemotePort(RuntimeError("remote unavailable")),
    ).collect(WORKTREE)
    assert bundle.leases is None
    assert bundle.remote is None


def test_collectors_receive_the_normalized_worktree_key() -> None:
    leases = FakeCollector(())
    service(leases=leases).collect(WORKTREE)
    assert leases.calls == [WORKTREE_KEY]


# ---------------------------------------------------------------------------
# Protected root identity
# ---------------------------------------------------------------------------


def test_protected_root_matches_canonical_root_via_windows_key_seam() -> None:
    bundle = service().collect(
        WORKTREE,
        repo_root=r"a:\REPO\wt-a",
    )
    assert bundle.protected_root is True


def test_protected_root_matches_instance_list_regardless_of_case_and_slashes() -> None:
    bundle = service().collect(
        WORKTREE,
        protected_worktrees=(r"A:/REPO/WT-A", r"A:\repo\wt-b"),
    )
    assert bundle.protected_root is True


def test_unprotected_worktree_observes_false() -> None:
    bundle = service().collect(
        WORKTREE,
        repo_root=r"A:\repo",
        protected_worktrees=(r"A:\repo\wt-b",),
    )
    assert bundle.protected_root is False


def test_absent_protection_input_is_unknown_never_false() -> None:
    bundle = service().collect(WORKTREE)
    assert bundle.protected_root is None


# ---------------------------------------------------------------------------
# Fingerprint semantics
# ---------------------------------------------------------------------------


def test_fingerprint_is_deterministic_for_identical_observations() -> None:
    git = FakeGitPort(status=(" M x.py",))
    first = service(git=git).collect(WORKTREE)
    second = service(git=FakeGitPort(status=(" M x.py",))).collect(WORKTREE)
    assert first.input_fingerprint == second.input_fingerprint


def test_fingerprint_changes_when_evidence_changes() -> None:
    clean = service(git=FakeGitPort(status=())).collect(WORKTREE)
    dirty = service(git=FakeGitPort(status=(" M x.py",))).collect(WORKTREE)
    assert clean.input_fingerprint != dirty.input_fingerprint


def test_stamped_facts_survive_replacement_roundtrip() -> None:
    bundle = service().collect(WORKTREE)
    restamped = replace(bundle, tracked_dirty=True)
    assert restamped.input_fingerprint == bundle.input_fingerprint
    assert wtl_input_fingerprint(restamped) != bundle.input_fingerprint


# ---------------------------------------------------------------------------
# Read-only discipline
# ---------------------------------------------------------------------------


def test_collect_performs_only_read_operations() -> None:
    git = FakeGitPort()
    service(git=git).collect(WORKTREE)
    assert set(git.calls) <= {"read_head", "read_branch", "read_status_porcelain"}


def test_service_rejects_non_callable_git_port() -> None:
    with pytest.raises(ValueError):
        WtlObservationService(git_port=object())


# ---------------------------------------------------------------------------
# StrictGitObservationPort (native read-only Git seam)
# ---------------------------------------------------------------------------


class RecordingRunner:
    def __init__(self, *, results: dict[str, CommandResult] | None = None) -> None:
        self.argvs: list[tuple[str, ...]] = []
        self._results = results or {}

    def run(self, argv: tuple[str, ...], timeout_seconds: int) -> CommandResult:
        self.argvs.append(argv)
        key = " ".join(argv[6:])
        if key in self._results:
            return self._results[key]
        return CommandResult(0, "", "")


def test_strict_port_head_reads_use_lock_free_read_only_argv() -> None:
    runner = RecordingRunner(
        results={"rev-parse HEAD": CommandResult(0, HEAD_A, "")}
    )
    port = StrictGitObservationPort(runner=runner)
    assert port.read_head(WORKTREE) == HEAD_A
    argv = runner.argvs[0]
    assert argv[0] == "git"
    assert "--no-optional-locks" in argv
    assert "-C" in argv
    assert argv[argv.index("-C") + 1] == WORKTREE
    assert not any(
        flag in argv
        for flag in ("add", "commit", "reset", "clean", "stash", "checkout", "rebase", "push")
    )


def test_strict_port_status_reads_porcelain_v1_with_all_untracked() -> None:
    runner = RecordingRunner(
        results={
            "status --porcelain=v1 --untracked-files=all": CommandResult(
                0, "?? .serena/\n M x.py\n", ""
            )
        }
    )
    port = StrictGitObservationPort(runner=runner)
    lines = port.read_status_porcelain(WORKTREE)
    assert lines == ("?? .serena/", " M x.py")


def test_strict_port_returns_none_on_failure_or_garbage() -> None:
    runner = RecordingRunner(
        results={
            "rev-parse HEAD": CommandResult(128, "", "fatal: not a git repository"),
            "rev-parse --abbrev-ref HEAD": CommandResult(128, "", "fatal"),
            "status --porcelain=v1 --untracked-files=all": CommandResult(1, "x", "err"),
        }
    )
    port = StrictGitObservationPort(runner=runner)
    assert port.read_head(WORKTREE) is None
    assert port.read_branch(WORKTREE) is None
    assert port.read_status_porcelain(WORKTREE) is None


def test_strict_port_rejects_non_hex_head_output() -> None:
    runner = RecordingRunner(
        results={"rev-parse HEAD": CommandResult(0, "not-a-head", "")}
    )
    port = StrictGitObservationPort(runner=runner)
    assert port.read_head(WORKTREE) is None


def test_strict_port_validates_constructor_arguments() -> None:
    with pytest.raises(ValueError):
        StrictGitObservationPort(git_executable="   ")
    with pytest.raises(ValueError):
        StrictGitObservationPort(timeout_seconds=0)
