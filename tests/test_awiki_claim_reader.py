from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from a_conductor.awiki_claim_reader import (
    AWikiClaimReader,
    ClaimBindingError,
    ClaimTaskBinding,
)
from a_conductor.native_execution import NativeCommandResult
from a_conductor.project_identity import GitReadResult


HEAD = "a" * 40
SOURCE_HEAD = "b" * 40


class Git:
    def show_toplevel(self, root):
        return GitReadResult(True, str(root))

    def head(self, root):
        return GitReadResult(True, SOURCE_HEAD if root.name == "source" else HEAD)

    def branch(self, root):
        return GitReadResult(True, "feat/claim")


class Runner:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []
        self.exit_code = 0
        self.timed_out = False
        self.truncated = False
        self.dirty = False
        self.after_read = lambda: None

    def run(self, spec):
        self.calls.append(spec)
        if "status" in spec.argv:
            stdout = " M conductor/state.py" if self.dirty else ""
            exit_code = 0
        else:
            stdout = json.dumps(self.payload)
            exit_code = self.exit_code
            self.after_read()
        return NativeCommandResult(
            executable=spec.argv[0], argument_count=len(spec.argv) - 1,
            exit_code=exit_code, timed_out=self.timed_out,
            stdout=stdout, stderr="private payload must not escape",
            stdout_sha256="0" * 64, stderr_sha256="0" * 64,
            stdout_truncated=self.truncated, stderr_truncated=False,
        )


@pytest.fixture
def lane(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    binding = ClaimTaskBinding(
        task_id="WO-P1-551", claim_id="awiki-claim-" + "c" * 20,
        generation=1, repository="aase7en/A-Wiki-Conductor",
        worktree=str(target), branch="feat/claim", head_sha=HEAD,
        agent="claim-lane", scope=("src/a_conductor/awiki_claim_reader.py",),
    )
    payload = {
        "schema": "awiki-claim-reader/v1", "authority_source": "COLLAB.md+Git",
        "repository": binding.repository, "task_id": binding.task_id,
        "claim_id": binding.claim_id, "generation": binding.generation,
        "agent": binding.agent, "claimed_at": "2026-11-06",
        "scope": list(binding.scope), "branch": binding.branch,
        "branch_head_sha": HEAD, "worktree_binding": "CONSUMER_VERIFY_REQUIRED",
    }
    runner = Runner(payload)
    git = Git()
    reader = AWikiClaimReader(
        authority_root=source, authority_head=SOURCE_HEAD,
        runner=runner, git=git,
    )
    return reader, binding, runner, git


def denied(reader, binding, code):
    with pytest.raises(ClaimBindingError) as error:
        reader.require_binding(binding)
    assert error.value.code == code
    assert str(error.value) == code
    assert error.value.__cause__ is None


def test_valid_current_claim_satisfies_only_claim_precondition(lane):
    reader, binding, runner, _ = lane
    assert reader.require_binding(binding) == binding
    call = next(call for call in runner.calls if "-c" in call.argv and "-I" in call.argv)
    assert call.mutation_intent is False
    assert call.argv[-2:] == (binding.worktree, binding.task_id)
    assert all(call.mutation_intent is False for call in runner.calls)


def test_no_claim_refuses_typed(lane):
    reader, binding, runner, _ = lane
    runner.payload = {"ok": False, "error": "CLAIM_NOT_FOUND: WO-P1-551"}
    runner.exit_code = 1
    denied(reader, binding, "CLAIM_NOT_FOUND")


@pytest.mark.parametrize(("field", "value", "code"), [
    ("branch_head_sha", "d" * 40, "CLAIM_HEAD_MISMATCH"),
    ("agent", "another-owner", "CLAIM_OWNER_CONFLICT"),
    ("task_id", "WO-P1-551-other", "CLAIM_TASK_MISMATCH"),
    ("repository", "aase7en/A-Wiki", "CLAIM_REPOSITORY_MISMATCH"),
    ("branch", "main", "CLAIM_BRANCH_MISMATCH"),
    ("claim_id", "awiki-claim-" + "d" * 20, "CLAIM_ID_MISMATCH"),
    ("generation", 2, "CLAIM_GENERATION_MISMATCH"),
    ("generation", True, "CLAIM_RESPONSE_INVALID"),
    ("scope", ["src/**"], "CLAIM_SCOPE_MISMATCH"),
    ("scope", [], "CLAIM_SCOPE_MISMATCH"),
    ("worktree_binding", "VERIFIED", "CLAIM_RESPONSE_INVALID"),
    ("schema", "awiki-claim-reader/v2", "CLAIM_RESPONSE_INVALID"),
    ("authority_source", "TTL", "CLAIM_RESPONSE_INVALID"),
])
def test_foreign_stale_and_unbound_claims_refuse(lane, field, value, code):
    reader, binding, runner, _ = lane
    runner.payload[field] = value
    denied(reader, binding, code)


@pytest.mark.parametrize("error", [
    "CLAIM_AMBIGUOUS", "GIT_HISTORY_SHALLOW", "BRANCH_HEAD_UNRESOLVED",
])
def test_canonical_failures_remain_typed(lane, error):
    reader, binding, runner, _ = lane
    runner.payload = {"ok": False, "error": error + ": private detail"}
    runner.exit_code = 1
    denied(reader, binding, error)


@pytest.mark.parametrize("payload", [None, [], True, {}, {"ok": True}])
def test_malformed_reader_response_refuses(lane, payload):
    reader, binding, runner, _ = lane
    runner.payload = payload
    denied(reader, binding, "CLAIM_RESPONSE_INVALID")


def test_unknown_reader_error_does_not_leak_payload(lane):
    reader, binding, runner, _ = lane
    runner.payload = {"ok": False, "error": "private unknown diagnostic"}
    runner.exit_code = 1
    denied(reader, binding, "CLAIM_READER_FAILED")


@pytest.mark.parametrize("flag", ["timed_out", "truncated"])
def test_transport_uncertainty_refuses(lane, flag):
    reader, binding, runner, _ = lane
    setattr(runner, flag, True)
    denied(reader, binding, "CLAIM_READER_UNAVAILABLE")


def test_consumer_subdirectory_is_not_worktree_proof(lane):
    reader, binding, _, git = lane
    original = git.show_toplevel
    git.show_toplevel = lambda root: (
        GitReadResult(True, str(root.parent)) if root.name == "target" else original(root)
    )
    denied(reader, binding, "CLAIM_WORKTREE_MISMATCH")


def test_consumer_head_drift_during_reader_call_refuses(lane):
    reader, binding, runner, git = lane
    original = git.head
    runner.after_read = lambda: setattr(git, "head", lambda root: (
        GitReadResult(True, "e" * 40) if root.name == "target" else original(root)
    ))
    denied(reader, binding, "CLAIM_WORKTREE_HEAD_MISMATCH")


def test_authority_revision_drift_refuses(lane):
    reader, binding, _, git = lane
    original = git.head
    git.head = lambda root: (
        GitReadResult(True, "e" * 40) if root.name == "source" else original(root)
    )
    denied(reader, binding, "CLAIM_READER_REVISION_MISMATCH")


def test_dirty_authority_code_is_not_accepted(lane):
    reader, binding, runner, _ = lane
    runner.dirty = True
    denied(reader, binding, "CLAIM_READER_DIRTY")


@pytest.mark.parametrize(("field", "value"), [
    ("generation", True), ("generation", 0), ("head_sha", "a" * 7),
    ("scope", ("../outside",)), ("scope", ("/absolute",)),
    ("scope", ("C:/absolute",)), ("scope", ("src/../outside",)),
    ("scope", ()), ("worktree", "relative"), ("agent", ""),
    ("scope", ([],)), ("scope", ("same", "same")), ("agent", "unknown"),
])
def test_invalid_expected_binding_is_not_authority(lane, field, value):
    reader, binding, _, _ = lane
    denied(reader, replace(binding, **{field: value}), "CLAIM_BINDING_INVALID")


def test_consumer_branch_mismatch_refuses(lane):
    reader, binding, _, git = lane
    git.branch = lambda root: GitReadResult(True, "other")
    denied(reader, binding, "CLAIM_WORKTREE_BRANCH_MISMATCH")


def test_authority_dirtied_during_read_refuses(lane):
    reader, binding, runner, _ = lane
    runner.after_read = lambda: setattr(runner, "dirty", True)
    denied(reader, binding, "CLAIM_READER_DIRTY")


def test_runner_exception_is_bounded_without_diagnostic_leak(lane):
    reader, binding, runner, _ = lane

    def broken(spec):
        raise RuntimeError("private diagnostic")

    runner.run = broken
    denied(reader, binding, "CLAIM_READER_UNAVAILABLE")


def test_json_decoder_failure_is_typed(lane):
    reader, binding, runner, _ = lane
    original = runner.run
    runner.run = lambda spec: (
        original(spec) if "status" in spec.argv else replace(original(spec), stdout="not-json")
    )
    denied(reader, binding, "CLAIM_RESPONSE_INVALID")


def test_actual_git_and_isolated_python_transport(tmp_path):
    """Real process/Git binding over a synthetic upstream API fixture, not live admission."""
    source = tmp_path / "source with spaces"
    target = tmp_path / "target with spaces"

    def git(root, *args):
        return subprocess.run(
            ["git", "-C", str(root), *args], check=True, capture_output=True,
            text=True, encoding="utf-8",
        ).stdout.strip()

    for root in (source, target):
        root.mkdir()
        git(root, "init", "-b", "feat/claim")
    module = source / "conductor"
    module.mkdir()
    (module / "__init__.py").write_text("", encoding="utf-8")
    # The fixture supplies the API only; no COLLAB parser is copied into AWC.
    (module / "state.py").write_text(
        "import json\n"
        "class ClaimLookupError(ValueError): pass\n"
        "def read_canonical_claim(root, task_id):\n"
        "    if task_id == 'missing': raise ClaimLookupError('CLAIM_NOT_FOUND: missing')\n"
        "    return json.loads((root / 'claim.json').read_text(encoding='utf-8'))\n",
        encoding="utf-8",
    )
    for root in (source, target):
        git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "add", ".")
        git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "--allow-empty", "-m", "fixture")
    binding = ClaimTaskBinding(
        task_id="WO-P1-551", claim_id="awiki-claim-" + "c" * 20,
        generation=1, repository="aase7en/A-Wiki-Conductor",
        worktree=str(target), branch="feat/claim", head_sha=git(target, "rev-parse", "HEAD"),
        agent="claim-lane", scope=("src/claim.py",),
    )
    payload = {
        "schema": "awiki-claim-reader/v1", "authority_source": "COLLAB.md+Git",
        "worktree_binding": "CONSUMER_VERIFY_REQUIRED", "task_id": binding.task_id,
        "claim_id": binding.claim_id, "generation": 1, "repository": binding.repository,
        "agent": binding.agent, "scope": list(binding.scope), "branch": binding.branch,
        "branch_head_sha": binding.head_sha,
    }
    (target / "claim.json").write_text(json.dumps(payload), encoding="utf-8")
    reader = AWikiClaimReader(
        authority_root=source, authority_head=git(source, "rev-parse", "HEAD"),
        python_executable=sys.executable,
    )
    assert reader.require_binding(binding) == binding
    denied(reader, replace(binding, task_id="missing"), "CLAIM_NOT_FOUND")
    assert git(source, "status", "--short") == ""
    assert not (module / "__pycache__").exists()
